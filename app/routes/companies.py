"""Company CRUD routes: list, create, detail."""
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR, VALID_MARKETS
from app.io import arenas as arenas_io
from app.io import company as company_io
from app.io import journal as journal_io
from app.io import portfolio as portfolio_io
from app.io import quotes as quotes_io
from app.io import watchlist as watchlist_io
from app.templating import register_filters

router = APIRouter(prefix="/companies", tags=["companies"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))
register_filters(templates)


@router.get("")
def list_page(request: Request):
    rows = company_io.list_companies()
    # annotate: which tickers are already in watchlist (any stage) / portfolio
    wl_by_ticker: dict[str, list[str]] = {}
    for stage in watchlist_io.STAGES:
        for r in watchlist_io.read_watchlist(stage):
            t = r.get("ticker", "")
            if t:
                wl_by_ticker.setdefault(t, []).append(stage)
    positions = {
        (r.get("market", ""), r.get("ticker", ""))
        for r in portfolio_io.read_positions()
    }
    for row in rows:
        row["_wl_stages"] = wl_by_ticker.get(row["ticker"], [])
        row["_in_portfolio"] = (row["market"], row["ticker"]) in positions
    return templates.TemplateResponse(
        request,
        "companies/list.html",
        {"rows": rows},
    )


@router.get("/new")
def new_form(request: Request):
    return templates.TemplateResponse(
        request,
        "companies/new.html",
        {
            "markets": VALID_MARKETS,
        },
    )


@router.post("/new")
def new_submit(
    ticker: str = Form(...),
    market: str = Form(...),
    name: str = Form(...),
    industry_slugs: str = Form(""),
    currency: str = Form("USD"),
):
    slugs = [s.strip() for s in industry_slugs.split(",") if s.strip()]
    try:
        path = company_io.create_company(
            ticker=ticker,
            market=market,
            name=name,
            industry_slugs=slugs,
            currency=currency,
        )
    except (ValueError, FileExistsError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    key = path.name
    return RedirectResponse(url=f"/companies/{key}", status_code=303)


@router.get("/{key}")
def detail_page(request: Request, key: str):
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    meta = company_io.read_meta(ticker, market)
    if not meta:
        raise HTTPException(status_code=404, detail="company not found")

    rows = company_io.list_companies()
    row = next((r for r in rows if r["key"] == key), None)
    decisions = journal_io.list_entries(ticker=ticker, market=market)[:10]
    profiles = company_io.list_profiles(ticker, market)
    arena_rows = arenas_io.company_summary(ticker, market)

    # which watchlist stages / portfolio this company is already in
    watchlist_stages = [
        s
        for s in watchlist_io.STAGES
        if any(r.get("ticker") == ticker for r in watchlist_io.read_watchlist(s))
    ]
    in_portfolio = any(
        r.get("ticker") == ticker and r.get("market") == market
        for r in portfolio_io.read_positions()
    )

    from datetime import date as _date
    latest_quote = quotes_io.latest_for(ticker)
    prev_quote = quotes_io.second_latest_for(ticker)
    freshness = quotes_io.freshness(ticker)
    return templates.TemplateResponse(
        request,
        "companies/detail.html",
        {
            "key": key,
            "ticker": ticker,
            "market": market,
            "meta": meta,
            "row": row,
            "decisions": decisions,
            "journal_actions": journal_io.ACTIONS,
            "profiles": profiles,
            "arena_rows": arena_rows,
            "watchlist_stages": watchlist_stages,
            "in_portfolio": in_portfolio,
            "source_types": watchlist_io.SOURCE_TYPES,
            "today": _date.today().isoformat(),
            "latest_quote": latest_quote,
            "prev_quote": prev_quote,
            "freshness": freshness,
        },
    )


# --- meta.md editor ----------------------------------------------------------


@router.get("/{key}/meta")
def meta_edit(request: Request, key: str):
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    doc = company_io.read_meta_with_body(ticker, market)
    if not doc["exists"]:
        raise HTTPException(status_code=404, detail="company not found")
    return templates.TemplateResponse(
        request,
        "companies/meta_edit.html",
        {
            "key": key,
            "ticker": ticker,
            "market": market,
            "doc": doc,
        },
    )


@router.post("/{key}/meta")
async def meta_save(request: Request, key: str):
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    form = await request.form()
    themes_raw = str(form.get("themes", "")).strip()
    themes = [t.strip() for t in themes_raw.split(",") if t.strip()] if themes_raw else []
    slugs_raw = str(form.get("industry_slugs", "")).strip()
    industry_slugs = [s.strip() for s in slugs_raw.split(",") if s.strip()] if slugs_raw else []
    fm = {
        "name": str(form.get("name", "")).strip() or ticker,
        "industry_slugs": industry_slugs,
        "themes": themes,
        "listed_date": str(form.get("listed_date", "")).strip() or None,
        "currency": str(form.get("currency", "")).strip() or "USD",
        "website": str(form.get("website", "")).strip() or None,
    }
    fm = {k: v for k, v in fm.items() if v not in (None, "", [])}
    body = str(form.get("body", ""))
    try:
        company_io.write_meta(ticker, market, fm, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RedirectResponse(url=f"/companies/{key}", status_code=303)


# --- profile-YYYY.md editor --------------------------------------------------


@router.get("/{key}/profile/{year}/view")
def profile_view(request: Request, key: str, year: int):
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    doc = company_io.read_profile(ticker, market, year)
    if not doc.get("exists"):
        raise HTTPException(status_code=404, detail="profile not found")

    import markdown as _md

    body_html = _md.markdown(
        doc.get("body") or "", extensions=["tables", "fenced_code"]
    )
    return templates.TemplateResponse(
        request,
        "companies/profile_view.html",
        {
            "key": key,
            "ticker": ticker,
            "market": market,
            "year": year,
            "fm": doc.get("frontmatter") or {},
            "body_html": body_html,
        },
    )


@router.get("/{key}/profile/{year}")
def profile_edit(request: Request, key: str, year: int):
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    doc = company_io.read_profile(ticker, market, year)
    sources = company_io.list_sources(ticker, market)
    return templates.TemplateResponse(
        request,
        "companies/profile_edit.html",
        {
            "key": key,
            "ticker": ticker,
            "market": market,
            "year": year,
            "doc": doc,
            "sources": sources,
        },
    )


@router.post("/{key}/profile/{year}")
async def profile_save(request: Request, key: str, year: int):
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    form = await request.form()
    fm = {
        "source_file": str(form.get("source_file", "")).strip(),
        "source": str(form.get("source", "annual_report")).strip() or "annual_report",
    }
    body = str(form.get("body", ""))
    try:
        company_io.write_profile(ticker, market, year, fm, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RedirectResponse(url=f"/companies/{key}", status_code=303)

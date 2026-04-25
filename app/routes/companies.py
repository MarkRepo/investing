"""Company CRUD routes: list, create, detail."""
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR, VALID_MARKETS, VALID_SECTORS
from app.io import arenas as arenas_io
from app.io import company as company_io
from app.io import journal as journal_io

router = APIRouter(prefix="/companies", tags=["companies"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def list_page(request: Request):
    rows = company_io.list_companies()
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
            "sectors": VALID_SECTORS,
        },
    )


@router.post("/new")
def new_submit(
    ticker: str = Form(...),
    market: str = Form(...),
    name: str = Form(...),
    sector: str = Form(...),
    currency: str = Form("USD"),
):
    try:
        path = company_io.create_company(
            ticker=ticker,
            market=market,
            name=name,
            sector=sector,
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
            "sectors": VALID_SECTORS,
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
    fm = {
        "name": str(form.get("name", "")).strip() or ticker,
        "industry_primary": str(form.get("industry_primary", "")).strip() or None,
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

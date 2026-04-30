"""Company CRUD routes: list, create, detail."""
import markdown as _md
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import config as cfg
from app.config import APP_TEMPLATES_DIR, VALID_MARKETS
from app.io import arenas as arenas_io
from app.io import company as company_io
from app.io import industry as industry_io
from app.io import journal as journal_io
from app.io import portfolio as portfolio_io
from app.io import quotes as quotes_io
from app.io import narrative_proposals as narrative_io
from app.io import watchlist as watchlist_io
from app.io.claim_registry import ClaimRegistry
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

    # 8 company-layer narratives (Plan 3 digest writes here, Phase 3B flags here)
    scope_ref = f"{market}_{ticker}"
    company_flags = narrative_io.read_narrative_flags("company", scope_ref, base=cfg.COMPANIES_DIR.parent)
    flags_by_dimension = {}
    for flag in company_flags:
        flags_by_dimension.setdefault(flag.get("dimension"), []).append(flag)
    narratives = []
    for dim in cfg.COMPANY_DIMENSIONS:
        md = company_io.read_narrative(ticker, market, dim)
        has_content = md.strip() and ("### 来源" in md or "proposal_id:" in md)
        dim_flags = flags_by_dimension.get(dim, [])
        narratives.append({
            "dim": dim,
            "label": _COMPANY_DIM_LABEL.get(dim, dim),
            "has_content": bool(has_content),
            "html": _md.markdown(md, extensions=["tables", "fenced_code"]) if md else "",
            "flags": dim_flags,
            "needs_review": bool(dim_flags),
        })

    # Industry back-links via meta.industry_slugs (if present)
    industry_links = []
    for slug in meta.get("industry_slugs") or []:
        try:
            im = industry_io.read_meta(slug)
            industry_links.append({"slug": slug, "name": im.get("name") or slug})
        except FileNotFoundError:
            industry_links.append({"slug": slug, "name": None})

    # Load company claims from ClaimRegistry
    registry = ClaimRegistry(cfg.BASE_PATH)
    raw_claims = registry.list_claims(scope_type="company", scope_ref=scope_ref)
    claims = []
    for claim in raw_claims:
        # Derive source ids: supporting_source_ids > evidence[].source_id > claim.source_id
        supporting_source_ids = claim.get("supporting_source_ids") or []
        if not supporting_source_ids:
            supporting_source_ids = [
                ev["source_id"]
                for ev in claim.get("supporting_evidence", [])
                if ev.get("source_id")
            ]
        if not supporting_source_ids and claim.get("source_id"):
            supporting_source_ids = [claim["source_id"]]
        claims.append({
            "claim_id": claim.get("claim_id", ""),
            "claim_text": claim.get("claim_text", ""),
            "claim_type": claim.get("claim_type", ""),
            "dimension_hint": claim.get("dimension_hint", ""),
            "confidence": claim.get("confidence", ""),
            "supporting_source_ids": supporting_source_ids,
        })

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
            "arena_rows": arena_rows,
            "watchlist_stages": watchlist_stages,
            "in_portfolio": in_portfolio,
            "source_types": watchlist_io.SOURCE_TYPES,
            "today": _date.today().isoformat(),
            "latest_quote": latest_quote,
            "prev_quote": prev_quote,
            "freshness": freshness,
            "narratives": narratives,
            "industry_links": industry_links,
            "claims": claims,
        },
    )


_COMPANY_DIM_LABEL = {
    "business_model": "商业模式",
    "moat": "护城河",
    "growth_engine": "增长引擎",
    "management": "管理层",
    "financial_profile": "财务画像",
    "catalysts": "催化剂",
    "risks": "风险",
    "valuation": "估值",
}


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



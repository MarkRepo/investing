"""Company CRUD routes: list, create, detail."""
import os
from pathlib import Path
import markdown as _md
import yaml
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import config as cfg
from app.config import APP_TEMPLATES_DIR, VALID_MARKETS
from app.io import company as company_io
from app.io import industry as industry_io
from app.io import journal as journal_io
from app.io import portfolio as portfolio_io
from app.io import quotes as quotes_io
from app.io import narrative_proposals as narrative_io
from app.io import watchlist as watchlist_io
from app.io.claim_registry import ClaimRegistry
from app.templating import register_filters

# --- Prism topic mapping: company key -> (slug, variant) ---

_PRISM_TOPIC_MAP: dict[str, tuple[str, str]] | None = None


def _build_prism_topic_map() -> dict[str, tuple[str, str]]:
    """Scan prism/topics/ for company-type topics and build a key->slug,variant map."""
    base = Path(cfg.BASE_PATH) / "prism" / "topics"
    if not base.exists():
        return {}
    m: dict[str, tuple[str, str]] = {}
    for slug in base.iterdir():
        if not slug.is_dir():
            continue
        for variant in slug.iterdir():
            tf = variant / "topic.yaml"
            if not tf.exists():
                continue
            with open(tf) as f:
                t = yaml.safe_load(f)
            if t and t.get("type") == "company":
                sc = t.get("scope", {})
                ticker = sc.get("ticker", "")
                market = sc.get("market", "")
                if ticker and market:
                    key = ticker if "_" in ticker else f"{market}_{ticker}"
                    m[key] = (slug.name, variant.name)
    return m


def _get_prism_redirect(key: str) -> str | None:
    """Return /prism/{slug}/{variant} path if the company has a prism topic, else None."""
    global _PRISM_TOPIC_MAP
    if _PRISM_TOPIC_MAP is None:
        _PRISM_TOPIC_MAP = _build_prism_topic_map()
    if key in _PRISM_TOPIC_MAP:
        slug, variant = _PRISM_TOPIC_MAP[key]
        return f"/prism/{slug}/{variant}"
    return None

router = APIRouter(prefix="/companies", tags=["companies"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))
register_filters(templates)


@router.get("")
def list_page(request: Request):
    """Legacy list page is retired — companies are now indexed via /prism."""
    return RedirectResponse(url="/prism", status_code=302)


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

    # Redirect to prism page if the company has a prism topic
    prism_path = _get_prism_redirect(key)
    if prism_path:
        return RedirectResponse(url=prism_path, status_code=302)

    rows = company_io.list_companies()
    row = next((r for r in rows if r["key"] == key), None)
    decisions = journal_io.list_entries(ticker=ticker, market=market)[:10]
    
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
    claims = [
        {
            "claim_id": claim.get("claim_id", ""),
            "claim_text": claim.get("claim_text", ""),
            "claim_type": claim.get("claim_type", ""),
            "dimension_hint": claim.get("dimension_hint", ""),
            "confidence": claim.get("confidence", ""),
            "source_ids": _claim_source_ids(claim),
        }
        for claim in raw_claims
    ]

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


def _claim_source_ids(claim: dict) -> list[str]:
    """Collect all source IDs referenced by a claim (sorted, deduplicated)."""
    ids: set[str] = set(claim.get("supporting_source_ids") or [])
    for evidence in claim.get("evidence", []) or []:
        if evidence.get("source_id"):
            ids.add(evidence["source_id"])
    for evidence in claim.get("supporting_evidence", []) or []:
        if evidence.get("source_id"):
            ids.add(evidence["source_id"])
    if claim.get("source_id"):
        ids.add(claim["source_id"])
    return sorted(ids)


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



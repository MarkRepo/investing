"""Investment lens read-only aggregation views — /lens/{scope}/{slug_or_key}."""
from __future__ import annotations

import markdown as _md
import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app import config as cfg
from app.config import APP_TEMPLATES_DIR
from app.io import arenas as arenas_io
from app.io import company as company_io
from app.io import industry as industry_io
from app.io.claim_registry import ClaimRegistry
from app.io.investment_lens import fetch_lens_material

router = APIRouter(prefix="/lens", tags=["investment_lens"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))

# Chinese labels for all 8+7+9 lens fields.
FIELD_LABELS: dict[str, str] = {
    # industry 8
    "thesis": "核心论点",
    "demand": "需求",
    "supply_competition": "供给与竞争",
    "profit_pool": "利润池",
    "unit_economics": "单位经济",
    "stage_gates": "阶段门槛",
    "catalysts_timeline": "催化剂时间线",
    "risks_disconfirming_evidence": "风险与反证",
    # arena 7
    "battlefield_definition": "战场定义",
    "players_positions": "玩家与位置",
    "winning_variables": "决胜变量",
    "evidence_scoreboard": "证据计分板",
    # stage_gates shared above
    "inflection_points": "拐点",
    "company_implications": "公司影响",
    # company 9
    "business_exposure": "业务敞口",
    "thesis_fit": "论点契合",
    "moat_execution": "护城河执行",
    "financial_quality": "财务质量",
    "growth_drivers": "增长驱动",
    "stage_gate_status": "阶段门槛状态",
    "valuation_expectations": "估值预期",
    "catalysts_risks": "催化剂与风险",
    "open_questions": "待答问题",
}


def _list_insights(slug: str) -> list[dict[str, str]]:
    """Return all insight files for an industry slug."""
    insights_dir = cfg.INDUSTRIES_DIR / slug / "insights"
    if not insights_dir.is_dir():
        return []
    results = []
    for f in sorted(insights_dir.iterdir()):
        if f.suffix == ".md" and f.stem not in ("INSIGHTS",):
            results.append({"sha8": f.stem, "path": str(f)})
    return results


@router.get("")
def lens_index(request: Request):
    industries = industry_io.list_industries()
    arenas = arenas_io.list_arenas()
    companies = company_io.list_companies()
    return templates.TemplateResponse(
        request,
        "investment_lens/index.html",
        {
            "industries": industries,
            "arenas": arenas,
            "companies": companies,
        },
    )


@router.get("/industry/{slug}")
def industry_lens(request: Request, slug: str):
    try:
        meta = industry_io.read_meta(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"industry {slug!r} not found")

    registry = ClaimRegistry(base=cfg.BASE_PATH / "data")
    fields = cfg.VIEW_DIMENSIONS["investment_lens"]["industry"]
    materials = {
        f: fetch_lens_material("industry", slug, f, registry=registry, base=cfg.BASE_PATH)
        for f in fields
    }
    insights = _list_insights(slug)
    return templates.TemplateResponse(
        request,
        "investment_lens/industry.html",
        {
            "slug": slug,
            "meta": meta,
            "fields": fields,
            "materials": materials,
            "field_labels": FIELD_LABELS,
            "insights": insights,
        },
    )


@router.get("/industry/{slug}/insights/{bundle_sha8}")
def industry_insight(request: Request, slug: str, bundle_sha8: str):
    """Render a single INSIGHTS.md file as HTML."""
    try:
        meta = industry_io.read_meta(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"industry {slug!r} not found")

    insight_path = cfg.INDUSTRIES_DIR / slug / "insights" / f"{bundle_sha8}.md"
    if not insight_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"insight {bundle_sha8!r} not found for industry {slug!r}",
        )

    raw = insight_path.read_text(encoding="utf-8")

    # Split YAML frontmatter if present
    body: str = raw
    fm: dict[str, str] = {}
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
            except Exception:
                fm = {}
            body = parts[2].lstrip("\n")

    html_body = _md.markdown(body, extensions=["tables", "fenced_code", "toc"])
    insights = _list_insights(slug)

    return templates.TemplateResponse(
        request,
        "investment_lens/insight.html",
        {
            "slug": slug,
            "bundle_sha8": bundle_sha8,
            "meta": meta,
            "frontmatter": fm,
            "html_body": html_body,
            "insights": insights,
        },
    )


@router.get("/industry/{slug}/narrative")
def industry_narrative(request: Request, slug: str):
    """Render render_views-generated narrative.md as HTML."""
    try:
        meta = industry_io.read_meta(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"industry {slug!r} not found")

    narrative_path = cfg.DATA_DIR / "industries" / slug / "narrative.md"
    if not narrative_path.is_file():
        raise HTTPException(status_code=404, detail=f"narrative.md not found for {slug!r} — run render_views first")

    raw = narrative_path.read_text(encoding="utf-8")
    fm: dict[str, str] = {}
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
            except Exception:
                fm = {}
            body = parts[2].lstrip("\n")

    html_body = _md.markdown(body, extensions=["tables", "fenced_code", "toc"])
    return templates.TemplateResponse(
        request,
        "investment_lens/insight.html",
        {
            "slug": slug,
            "bundle_sha8": "narrative",
            "meta": meta,
            "frontmatter": fm,
            "html_body": html_body,
            "insights": _list_insights(slug),
        },
    )


@router.get("/company/{key}/dashboard")
def company_dashboard(request: Request, key: str):
    """Render render_views-generated dashboard.md as HTML."""
    parts = key.split("_", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail=f"invalid company key format: {key!r}")
    market, ticker = parts[0], parts[1]

    try:
        meta = company_io.read_meta(ticker, market)
    except Exception:
        meta = {}

    dashboard_path = cfg.DATA_DIR / "companies" / key / "dashboard.md"
    if not dashboard_path.is_file():
        raise HTTPException(status_code=404, detail=f"dashboard.md not found for {key!r} — run render_views first")

    raw = dashboard_path.read_text(encoding="utf-8")
    fm: dict[str, str] = {}
    body = raw
    if raw.startswith("---"):
        parts_md = raw.split("---", 2)
        if len(parts_md) >= 3:
            try:
                fm = yaml.safe_load(parts_md[1]) or {}
            except Exception:
                fm = {}
            body = parts_md[2].lstrip("\n")

    html_body = _md.markdown(body, extensions=["tables", "fenced_code", "toc"])
    return templates.TemplateResponse(
        request,
        "investment_lens/insight.html",
        {
            "slug": key,
            "bundle_sha8": "dashboard",
            "meta": {"name": meta.get("name", key)} if meta else {"name": key},
            "frontmatter": fm,
            "html_body": html_body,
            "insights": [],
        },
    )


@router.get("/arena/{slug}")
def arena_lens(request: Request, slug: str):
    info = arenas_io.read_arena(slug)
    if not info.get("exists"):
        raise HTTPException(status_code=404, detail=f"arena {slug!r} not found")

    meta = info.get("definition_fm") or {}

    registry = ClaimRegistry(base=cfg.BASE_PATH / "data")
    fields = cfg.VIEW_DIMENSIONS["investment_lens"]["arena"]
    materials = {
        f: fetch_lens_material("arena", slug, f, registry=registry, base=cfg.BASE_PATH)
        for f in fields
    }
    return templates.TemplateResponse(
        request,
        "investment_lens/arena.html",
        {
            "slug": slug,
            "meta": meta,
            "fields": fields,
            "materials": materials,
            "field_labels": FIELD_LABELS,
        },
    )


@router.get("/company/{key}")
def company_lens(request: Request, key: str):
    # key is like "SSE_603011" → market=SSE, ticker=603011
    parts = key.split("_", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail=f"invalid company key format: {key!r}")
    market, ticker = parts[0], parts[1]

    try:
        meta = company_io.read_meta(ticker, market)
    except Exception:
        meta = {}

    registry = ClaimRegistry(base=cfg.BASE_PATH / "data")
    fields = cfg.VIEW_DIMENSIONS["investment_lens"]["company"]
    materials = {
        f: fetch_lens_material("company", key, f, registry=registry, base=cfg.BASE_PATH)
        for f in fields
    }
    return templates.TemplateResponse(
        request,
        "investment_lens/company.html",
        {
            "key": key,
            "market": market,
            "ticker": ticker,
            "meta": meta,
            "fields": fields,
            "materials": materials,
            "field_labels": FIELD_LABELS,
        },
    )

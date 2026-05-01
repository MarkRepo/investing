"""Investment lens read-only aggregation views — /lens/{scope}/{slug_or_key}."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
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
    return templates.TemplateResponse(
        request,
        "investment_lens/industry.html",
        {
            "slug": slug,
            "meta": meta,
            "fields": fields,
            "materials": materials,
            "field_labels": FIELD_LABELS,
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

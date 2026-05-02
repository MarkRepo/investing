"""Industry (行业维度) read views — slug + 11 narrative dimensions.

Plan 4 T7: lifts the 501 stubs left from the Plan 1 slug migration.
Edit UI is out of scope for Plan 4 (read-only).
"""
import markdown as _md
from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app import config as cfg
from app.config import APP_TEMPLATES_DIR
from app.io import arenas as arenas_io
from app.io import company as company_io
from app.io import figure_contexts as fc_io
from app.io import industry as industry_io
from app.io import narrative_proposals as narrative_io

router = APIRouter(prefix="/industries", tags=["industries"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def index(request: Request):
    rows = industry_io.list_industries()
    return templates.TemplateResponse(
        request,
        "industries/index.html",
        {"rows": rows},
    )


@router.get("/{slug}")
def industry_detail(request: Request, slug: str):
    try:
        meta = industry_io.read_meta(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"industry {slug!r} not found")

    industry_flags = narrative_io.read_narrative_flags("industry", slug, base=cfg.INDUSTRIES_DIR.parent)
    flags_by_dimension = {}
    for flag in industry_flags:
        flags_by_dimension.setdefault(flag.get("dimension"), []).append(flag)
    narratives = []
    for dim in cfg.INDUSTRY_DIMENSIONS:
        md = industry_io.read_narrative(slug, dim)
        has_content = md.strip() and not _is_skeleton_only(md)
        dim_flags = flags_by_dimension.get(dim, [])
        narratives.append({
            "dim": dim,
            "label": _INDUSTRY_DIM_LABEL.get(dim, dim),
            "has_content": bool(has_content),
            "html": _md.markdown(md, extensions=["tables", "fenced_code"]) if md else "",
            "flags": dim_flags,
            "needs_review": bool(dim_flags),
        })

    figure_contexts = fc_io.read_figure_contexts(slug)

    linked_arenas = meta.get("linked_arenas") or []
    arena_meta = []
    for arena_slug in linked_arenas:
        info = arenas_io.read_arena(arena_slug)
        arena_meta.append({
            "slug": arena_slug,
            "exists": info.get("exists", False),
            "name": (info.get("definition_fm") or {}).get("name") or arena_slug,
        })

    raw_tickers = meta.get("linked_tickers") or []
    linked_tickers = []
    for t in raw_tickers:
        ticker, market = t.get("ticker"), t.get("market")
        name = t.get("name")
        if not name and ticker and market:
            try:
                cm = company_io.read_meta(ticker, market)
                name = (cm or {}).get("name")
            except Exception:
                pass
        linked_tickers.append({**t, "name": name or f"{market}_{ticker}"})

    return templates.TemplateResponse(
        request,
        "industries/detail.html",
        {
            "slug": slug,
            "meta": meta,
            "narratives": narratives,
            "figure_contexts": figure_contexts,
            "linked_arenas": arena_meta,
            "linked_tickers": linked_tickers,
        },
    )


def _is_skeleton_only(md: str) -> bool:
    """A narrative is 'skeleton-only' if it just contains the initial `# 标题`
    line from create_industry — no digest blocks appended yet."""
    stripped = md.strip()
    if not stripped.startswith("#"):
        return False
    # Real narratives have either "### 来源 ..." (old digest format) or
    # "supported_by_claims:" (narrative_apply endgame format).
    return "### 来源" not in stripped and "supported_by_claims:" not in stripped


_INDUSTRY_DIM_LABEL = {
    "definition": "行业定义",
    "market_size": "市场规模与增长",
    "lifecycle": "生命周期",
    "value_chain": "价值链",
    "competition": "竞争结构",
    "drivers": "需求驱动",
    "technology": "技术演进",
    "regulation": "监管与政策",
    "benchmark": "基准对标",
    "risks": "风险",
    "valuation": "估值习惯",
}

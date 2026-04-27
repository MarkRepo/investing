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

router = APIRouter(prefix="/industries", tags=["industries"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def index(request: Request):
    rows = industry_io.list_industries()
    for r in rows:
        r["observations_count"] = len(industry_io.read_observations(r["slug"]))
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

    observations = industry_io.read_observations(slug)
    # Sort observations by added_at desc; rows lacking added_at sink to bottom.
    observations.sort(key=lambda r: r.get("added_at") or "", reverse=True)

    narratives = []
    for dim in cfg.INDUSTRY_DIMENSIONS:
        md = industry_io.read_narrative(slug, dim)
        has_content = md.strip() and not _is_skeleton_only(md)
        narratives.append({
            "dim": dim,
            "label": _INDUSTRY_DIM_LABEL.get(dim, dim),
            "has_content": bool(has_content),
            "html": _md.markdown(md, extensions=["tables", "fenced_code"]) if md else "",
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
            "observations": observations[:50],
            "observations_total": len(observations),
            "narratives": narratives,
            "figure_contexts": figure_contexts,
            "linked_arenas": arena_meta,
            "linked_tickers": linked_tickers,
        },
    )


@router.get("/{slug}/observations")
def industry_observations(request: Request, slug: str):
    """Cross-source aggregation view (spec §6.2).

    Renders structured facts grouped by (dimension, field, timeframe[, segment])
    with median/range/spread stats; spread > 30% is flagged red.
    """
    try:
        meta = industry_io.read_meta(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"industry {slug!r} not found")

    agg = industry_io.aggregate_observations(slug)
    # Tab organization: by dimension; within a dim bundle numeric + segment + enum groups.
    groups_by_dim: dict[str, dict] = {}
    for kind in ("numeric", "segment", "enum"):
        for g in agg[kind]:
            dim = g["dimension"]
            bucket = groups_by_dim.setdefault(dim, {"numeric": [], "segment": [], "enum": []})
            bucket[kind].append(g)
    # Order dims per INDUSTRY_DIMENSIONS; include only dims with any group.
    ordered_dims = [d for d in cfg.INDUSTRY_DIMENSIONS if d in groups_by_dim]
    divergent_count = sum(1 for g in agg["numeric"] + agg["segment"] if g["divergent"])

    return templates.TemplateResponse(
        request,
        "industries/observations.html",
        {
            "slug": slug,
            "meta": meta,
            "ordered_dims": ordered_dims,
            "groups_by_dim": groups_by_dim,
            "dim_labels": _INDUSTRY_DIM_LABEL,
            "n_groups": sum(len(agg[k]) for k in ("numeric", "segment", "enum")),
            "n_divergent": divergent_count,
        },
    )


def _is_skeleton_only(md: str) -> bool:
    """A narrative is 'skeleton-only' if it just contains the initial `# 标题`
    line from create_industry — no digest blocks appended yet."""
    stripped = md.strip()
    if not stripped.startswith("#"):
        return False
    # Real narratives have a "### 来源 ..." block appended by append_narrative_block.
    return "### 来源" not in stripped


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

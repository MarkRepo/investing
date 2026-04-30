"""Arena (行业竞技场) pages: index + detail."""
import markdown as _md
from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app import config as cfg
from app.config import APP_TEMPLATES_DIR
from app.io import arenas as arenas_io
from app.io import industry as industry_io
from app.io import narrative_proposals as narrative_io

router = APIRouter(prefix="/arenas", tags=["arenas"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def index(request: Request):
    rows = arenas_io.list_arenas()
    # enrich with checklist size
    for r in rows:
        cl = arenas_io.read_checklist(r["slug"])
        r["checklist_count"] = len(cl.get("items") or []) if cl else 0
        r["participants_count"] = len(r.get("participants") or [])
    return templates.TemplateResponse(
        request,
        "arenas/index.html",
        {"rows": rows},
    )


@router.get("/{slug}")
def detail(request: Request, slug: str):
    data = arenas_io.read_arena(slug)
    if not data["exists"]:
        raise HTTPException(status_code=404, detail=f"arena {slug!r} not found")

    definition_html = _md.markdown(
        data["definition_body"] or "", extensions=["tables", "fenced_code"]
    )
    checklist = data["checklist"] or {}
    items = checklist.get("items") or []
    changelog = checklist.get("changelog") or []
    participants = data["definition_fm"].get("participants") or []
    industry_slug = data["definition_fm"].get("industry")

    narrative_flags = narrative_io.read_narrative_flags("arena", slug)
    flags_by_dimension = {}
    for flag in narrative_flags:
        flags_by_dimension.setdefault(flag.get("dimension"), []).append(flag)

    parsed = arenas_io.parse_notes(slug)
    by_ticker = parsed["by_ticker"]

    # build per-item, per-participant cells so the template can iterate cleanly
    per_item = []
    for it in items:
        qid = it["id"]
        rows = []
        for p in participants:
            key = f"{p['market']}_{p['ticker']}"
            ans = by_ticker.get(key, {}).get("answers", {}).get(qid)
            rows.append(
                {
                    "market": p["market"],
                    "ticker": str(p["ticker"]),
                    "name": p.get("name") or "",
                    "answer": ans,
                }
            )
        per_item.append({"item": it, "rows": rows})

    # 5 narrative dims (excluding definition, which is above as definition_html)
    narratives = []
    for dim in cfg.ARENA_DIMENSIONS:
        if dim == "definition":
            continue
        md = arenas_io.read_narrative(slug, dim)
        has_content = md.strip() and "### 来源" in md
        dim_flags = flags_by_dimension.get(dim, [])
        narratives.append({
            "dim": dim,
            "label": _ARENA_DIM_LABEL.get(dim, dim),
            "has_content": bool(has_content),
            "html": _md.markdown(md, extensions=["tables", "fenced_code"]) if md else "",
            "flags": dim_flags,
            "needs_review": bool(dim_flags),
        })

    # Industry back-link: arena.definition_fm.industry → /industries/{slug}
    industry_info = None
    if industry_slug:
        try:
            industry_meta = industry_io.read_meta(industry_slug)
            industry_info = {
                "slug": industry_slug,
                "name": industry_meta.get("name") or industry_slug,
            }
        except FileNotFoundError:
            industry_info = {"slug": industry_slug, "name": None}

    return templates.TemplateResponse(
        request,
        "arenas/detail.html",
        {
            "slug": slug,
            "fm": data["definition_fm"],
            "definition_html": definition_html,
            "checklist_version": checklist.get("version"),
            "changelog": changelog,
            "per_item": per_item,
            "participants": participants,
            "narratives": narratives,
            "industry_info": industry_info,
        },
    )


_ARENA_DIM_LABEL = {
    "participants": "参与者与相对位置",
    "decisive_factors": "博弈规则与胜负手",
    "trajectory": "演进轨迹与触发事件",
    "narratives": "多空叙事",
    "investment_view": "决策启示",
}

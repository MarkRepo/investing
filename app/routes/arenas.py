"""Arena (行业竞技场) pages: index + detail."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import arenas as arenas_io

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

    import markdown as _md

    definition_html = _md.markdown(
        data["definition_body"] or "", extensions=["tables", "fenced_code"]
    )
    checklist = data["checklist"] or {}
    items = checklist.get("items") or []
    changelog = checklist.get("changelog") or []
    participants = data["definition_fm"].get("participants") or []

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
        },
    )

"""Research insights views — /insights/{scope}/{slug}."""
from __future__ import annotations

import markdown as _md
import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app import config as cfg
from app.config import APP_TEMPLATES_DIR
from app.io import industry as industry_io
from app.io import mineru_summaries as ms_io

router = APIRouter(prefix="/insights", tags=["insights"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


def _list_insights(slug: str) -> list[dict]:
    """Return all insight files for an industry slug, newest first."""
    insights_dir = cfg.INDUSTRIES_DIR / slug / "insights"
    if not insights_dir.is_dir():
        return []
    results = []
    for f in sorted(insights_dir.iterdir(), reverse=True):
        if f.suffix == ".md" and f.stem not in ("INSIGHTS",):
            entry: dict = {"sha8": f.stem, "source_id": "", "source_title": "", "model": ""}
            try:
                text = f.read_text(encoding="utf-8")
                if text.startswith("---"):
                    parts = text.split("---", 2)
                    if len(parts) >= 3:
                        fm = yaml.safe_load(parts[1]) or {}
                        entry["source_id"] = fm.get("source_id", "")
                        entry["source_title"] = fm.get("source_title", "")
                        entry["model"] = fm.get("model", "")
            except Exception:
                pass
            results.append(entry)
    return results


def _parse_md_file(path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    fm: dict = {}
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
            except Exception:
                fm = {}
            body = parts[2].lstrip("\n")
    return fm, body


@router.get("")
def insights_index(request: Request):
    industries = industry_io.list_industries()
    rows = []
    for ind in industries:
        count = len(_list_insights(ind["slug"]))
        if count:
            rows.append({**ind, "insight_count": count})
    return templates.TemplateResponse(
        request,
        "insights/index.html",
        {"rows": rows},
    )


@router.get("/industry/{slug}")
def industry_insights(request: Request, slug: str):
    try:
        meta = industry_io.read_meta(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"industry {slug!r} not found")

    insights = _list_insights(slug)
    mineru_map = ms_io.source_id_to_best_report_id()
    for ins in insights:
        ins["mineru_report_id"] = mineru_map.get(ins["source_id"], "")

    # Cross-report synthesis: future feature, not yet implemented.
    # Will read from industries/{slug}/cross_synthesis.md when available.

    return templates.TemplateResponse(
        request,
        "insights/industry.html",
        {
            "slug": slug,
            "meta": meta,
            "insights": insights,
        },
    )


@router.get("/industry/{slug}/{sha8}")
def industry_insight_detail(request: Request, slug: str, sha8: str):
    try:
        meta = industry_io.read_meta(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"industry {slug!r} not found")

    insight_path = cfg.INDUSTRIES_DIR / slug / "insights" / f"{sha8}.md"
    if not insight_path.is_file():
        raise HTTPException(status_code=404, detail=f"insight {sha8!r} not found")

    fm, body = _parse_md_file(insight_path)
    html_body = _md.markdown(body, extensions=["tables", "fenced_code", "toc"])
    insights = _list_insights(slug)
    mineru_map = ms_io.source_id_to_best_report_id()
    mineru_report_id = mineru_map.get(fm.get("source_id", ""), "")

    return templates.TemplateResponse(
        request,
        "insights/detail.html",
        {
            "slug": slug,
            "sha8": sha8,
            "meta": meta,
            "frontmatter": fm,
            "html_body": html_body,
            "insights": insights,
            "mineru_report_id": mineru_report_id,
            "back_url": f"/insights/industry/{slug}",
        },
    )

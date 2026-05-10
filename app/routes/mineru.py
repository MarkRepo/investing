"""MinerU report summary browser — index + detail + raw view."""
from __future__ import annotations

import re
from pathlib import Path

import markdown as _md
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import mineru_summaries as ms_io

router = APIRouter(prefix="/digest", tags=["digest"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


def _get_image_dir(report_id: str) -> Path | None:
    """Resolve the images directory for a report under ~/MinerU/."""
    try:
        meta, _ = ms_io.read_summary(report_id)
    except FileNotFoundError:
        return None
    source_dir = meta.get("source_dir")
    if not source_dir:
        return None
    img_dir = ms_io.MINERU_ROOT / source_dir / "images"
    return img_dir if img_dir.is_dir() else None


@router.get("/{report_id}/images/{filename:path}")
def serve_image(report_id: str, filename: str):
    """Serve images from ~/MinerU/{source_dir}/images/."""
    img_dir = _get_image_dir(report_id)
    if not img_dir:
        raise HTTPException(status_code=404, detail="images not available")
    file_path = img_dir / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="image not found")
    return FileResponse(file_path)


def _rewrite_image_paths(md_text: str, report_id: str) -> str:
    """Rewrite relative image/ paths to route through the image proxy."""
    def _repl(m):
        prefix = m.group(1) or ""  # "![" alt "](" or "<img src="
        rest = m.group(2)          # the path part
        if rest.startswith(("http://", "https://", "/")):
            return m.group(0)      # absolute URL, leave as-is
        return f'{prefix}/digest/{report_id}/images/{rest}'

    # Match ![alt](images/xxx) and <img src="images/xxx"
    md_text = re.sub(r'(!\[[^\]]*\]\()(.+?)(\))', lambda m: f'{m.group(1)}/digest/{report_id}/images/{m.group(2).lstrip("images/")}{m.group(3)}' if m.group(2).startswith('images/') else m.group(0), md_text)
    md_text = re.sub(r'(<img\b[^>]*src=")(images/[^"]+)(")', lambda m: f'{m.group(1)}/digest/{report_id}/{m.group(2)}{m.group(3)}', md_text)
    return md_text


_MODEL_PRIORITY = {"sonnet46": 0, "gemini-3.1-pro": 1, "qwen36plus": 2}
_COMPARE_MODELS = {"对比报告", "对比分析"}


@router.get("")
def index(request: Request):
    all_entries = ms_io.list_summaries()

    compare_reports: list[dict] = []
    # groups: source_pdf → list of entries, sorted by model priority
    groups: dict[str, list[dict]] = {}

    for r in all_entries:
        model = r.get("model") or "qwen3"
        if model == "qwen3":
            continue
        if model in _COMPARE_MODELS:
            compare_reports.append(r)
            continue
        if model not in _MODEL_PRIORITY:
            continue
        source_dir = r.get("source_dir", "")
        pdf = ms_io.get_pdf_path(source_dir) if source_dir else None
        r["pdf_url"] = f"/digest/{r['report_id']}/pdf" if pdf else ""
        pdf_key = r.get("source_pdf", r["report_id"])
        groups.setdefault(pdf_key, []).append(r)

    # sort each group by model priority
    for entries in groups.values():
        entries.sort(key=lambda e: _MODEL_PRIORITY.get(e.get("model", ""), 99))

    # summary_groups: list of {title, topic, source_pdf, pdf_url, summaries}
    summary_groups = []
    for pdf_key, entries in sorted(groups.items(), key=lambda kv: kv[1][0].get("title", "")):
        best = entries[0]
        summary_groups.append({
            "title": best.get("title", pdf_key),
            "topic": best.get("topic", ""),
            "source_pdf": pdf_key,
            "pdf_url": best.get("pdf_url", ""),
            "summaries": entries,
        })

    return templates.TemplateResponse(
        request,
        "mineru/index.html",
        {"summary_groups": summary_groups, "compare_reports": compare_reports},
    )


@router.get("/{report_id}/pdf")
def serve_pdf(report_id: str):
    try:
        meta, _ = ms_io.read_summary(report_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"summary {report_id!r} not found")
    source_dir = meta.get("source_dir", "")
    pdf_path = ms_io.get_pdf_path(source_dir) if source_dir else None
    if not pdf_path:
        raise HTTPException(status_code=404, detail="PDF not available")
    return FileResponse(pdf_path, media_type="application/pdf")


@router.get("/{report_id}")
def detail(request: Request, report_id: str):
    try:
        meta, body = ms_io.read_summary(report_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"summary {report_id!r} not found")
    html = _md.markdown(body, extensions=["tables", "fenced_code", "toc"])
    return templates.TemplateResponse(
        request,
        "mineru/detail.html",
        {"meta": meta, "summary_html": html},
    )


@router.get("/{report_id}/raw", response_class=HTMLResponse)
def raw_view(request: Request, report_id: str):
    meta, _ = ms_io.read_summary(report_id)
    source_dir = meta.get("source_dir")
    if not source_dir:
        raise HTTPException(status_code=404, detail="source_dir not available")
    md_path = ms_io.get_full_md_path(source_dir)
    if not md_path or not md_path.exists():
        raise HTTPException(status_code=404, detail=f"full.md not found for {source_dir}")
    raw_text = md_path.read_text(encoding="utf-8")
    raw_text = _rewrite_image_paths(raw_text, report_id)
    html = _md.markdown(raw_text, extensions=["tables", "fenced_code"])
    return templates.TemplateResponse(
        request,
        "mineru/raw.html",
        {"meta": meta, "summary_html": html},
    )

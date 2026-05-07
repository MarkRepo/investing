"""Prism research system views — /prism."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from prism.scripts import outputs as outputs_io
from prism.scripts import topic as topic_io
from prism.scripts import manifest as manifest_io

router = APIRouter(prefix="/prism", tags=["prism"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def prism_index(request: Request):
    topics = topic_io.list_topics()
    return templates.TemplateResponse(
        request,
        "prism/index.html",
        {"topics": topics},
    )


@router.get("/{slug}")
def prism_detail(request: Request, slug: str):
    try:
        topic = topic_io.read_topic(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r} not found")

    outputs = outputs_io.list_outputs(slug)

    try:
        manifest = manifest_io.read_manifest(slug)
        mat_counts = manifest_io.material_count(slug)
    except FileNotFoundError:
        manifest = {"materials": []}
        mat_counts = {"total": 0, "processed": 0, "unprocessed": 0}

    return templates.TemplateResponse(
        request,
        "prism/detail.html",
        {
            "topic": topic,
            "outputs": outputs,
            "manifest": manifest,
            "mat_counts": mat_counts,
        },
    )


@router.get("/{slug}/output/{output_key}")
def prism_output(request: Request, slug: str, output_key: str):
    try:
        topic = topic_io.read_topic(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r} not found")

    try:
        html_body = outputs_io.read_output_html(slug, output_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Output {output_key!r} not yet generated")

    outputs = outputs_io.list_outputs(slug)
    current_output = next((o for o in outputs if o["key"] == output_key), None)

    return templates.TemplateResponse(
        request,
        "prism/output.html",
        {
            "topic": topic,
            "output_key": output_key,
            "current_output": current_output,
            "html_body": html_body,
            "outputs": outputs,
        },
    )

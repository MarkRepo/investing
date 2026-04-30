"""Bundle browser: list and detail views for ingest bundles."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import bundle_registry

router = APIRouter(prefix="/bundles", tags=["bundles"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def index(request: Request, type: str | None = None,
          institution: str | None = None, industry: str | None = None):
    filters: dict = {}
    if type:
        filters["type"] = type
    if institution:
        filters["institution"] = institution
    if industry:
        filters["industry"] = industry
    bundles = bundle_registry.list_bundles(filters or None)
    return templates.TemplateResponse(
        request,
        "bundles/index.html",
        {"bundles": bundles, "filters": filters},
    )


@router.get("/{source_id}")
def detail(request: Request, source_id: str):
    entry = bundle_registry.get_bundle(source_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"bundle {source_id!r} not found")
    try:
        bundle = bundle_registry.load_bundle_json(source_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"bundle file for {source_id!r} not found")
    return templates.TemplateResponse(
        request,
        "bundles/detail.html",
        {"entry": entry, "bundle": bundle},
    )

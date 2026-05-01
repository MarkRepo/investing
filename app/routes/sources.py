"""Source file viewer: serve source files directly."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

import app.config as cfg
from app.config import APP_TEMPLATES_DIR
from app.io import bundle_registry

router = APIRouter(prefix="/sources", tags=["sources"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


def _resolve(source_id: str):
    entry = bundle_registry.get_bundle(source_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"source {source_id!r} not found")
    source_file_path = entry.get("source_file_path", "")
    source_path = cfg.BASE_PATH / source_file_path
    if not source_path.exists():
        raise HTTPException(status_code=404, detail=f"source file not found: {source_file_path}")
    return source_path, entry


@router.get("/{source_id}/raw")
def source_raw(source_id: str):
    source_path, _ = _resolve(source_id)
    return FileResponse(str(source_path))


@router.get("/{source_id}/file")
def source_file(request: Request, source_id: str):
    source_path, entry = _resolve(source_id)
    is_pdf = str(source_path).lower().endswith(".pdf")
    return templates.TemplateResponse(
        request, "sources/file.html",
        {"entry": entry, "source_path": str(source_path), "is_pdf": is_pdf},
    )

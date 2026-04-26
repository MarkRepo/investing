"""Industry (行业维度) routes — SLUG-BASED, UI migration pending.

The old sector-based UI (landscape.md / players.md / competence-map.md) was
retired in Plan 1 Task 11 along with the sector-based IO. Routes here are
stubbed pending the new slug+11-dim UI (tracked in spec §D). The router object
and URL prefix are kept intact so ``main.py``'s ``include_router`` still works.
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import industry as industry_io

router = APIRouter(prefix="/industries", tags=["industries"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def index(request: Request):
    raise HTTPException(
        status_code=501,
        detail="industries UI temporarily offline — pending industry.py slug migration",
    )


@router.get("/{slug}")
def industry_detail(request: Request, slug: str):
    # New API available: industry_io.read_meta(slug) / industry_io.list_industries()
    raise HTTPException(
        status_code=501,
        detail="industries UI temporarily offline — pending industry.py slug migration",
    )


@router.get("/{slug}/{kind}")
def file_edit(request: Request, slug: str, kind: str):
    raise HTTPException(
        status_code=501,
        detail="industries UI temporarily offline — pending industry.py slug migration",
    )


@router.post("/{slug}/{kind}")
async def save(request: Request, slug: str, kind: str):
    raise HTTPException(
        status_code=501,
        detail="industries UI temporarily offline — pending industry.py slug migration",
    )

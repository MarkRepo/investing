"""Industry (行业维度) routes — landscape/players/competence-map."""
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import config as cfg
from app.config import APP_TEMPLATES_DIR
from app.io import competence_map as cmap
from app.io import industry as industry_io

router = APIRouter(prefix="/industries", tags=["industries"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def index(request: Request):
    return templates.TemplateResponse(
        request,
        "industries/index.html",
        {"sectors": industry_io.list_sectors(), "files": industry_io.FILES},
    )


@router.get("/{sector}")
def sector_detail(request: Request, sector: str):
    if sector not in cfg.VALID_SECTORS:
        raise HTTPException(status_code=404, detail="unknown sector")
    files = {kind: industry_io.read(sector, kind) for kind in industry_io.FILES}
    # competence-map page shows aggregated stats as a sidebar hint
    from datetime import date as date_cls
    year = date_cls.today().year
    derived = cmap.yearly_map(year)
    derived_for_sector = next((r for r in derived["by_sector"] if r["sector"] == sector), None)
    return templates.TemplateResponse(
        request,
        "industries/sector.html",
        {
            "sector": sector,
            "files": files,
            "derived": derived_for_sector,
            "derived_year": year,
        },
    )


@router.get("/{sector}/{kind}")
def file_edit(request: Request, sector: str, kind: str):
    if sector not in cfg.VALID_SECTORS:
        raise HTTPException(status_code=404, detail="unknown sector")
    if kind not in industry_io.FILES:
        raise HTTPException(status_code=404, detail="unknown file")
    doc = industry_io.read(sector, kind)
    return templates.TemplateResponse(
        request,
        "industries/edit.html",
        {"sector": sector, "kind": kind, "doc": doc},
    )


@router.post("/{sector}/{kind}")
async def save(request: Request, sector: str, kind: str):
    if sector not in cfg.VALID_SECTORS:
        raise HTTPException(status_code=404, detail="unknown sector")
    if kind not in industry_io.FILES:
        raise HTTPException(status_code=404, detail="unknown file")
    form = await request.form()
    body = str(form.get("body", ""))
    fm: dict = {}
    if kind == "landscape":
        source_type = str(form.get("source_type", "")).strip()
        if source_type:
            fm["source_type"] = source_type
    industry_io.write(sector, kind, fm, body)
    return RedirectResponse(url=f"/industries/{sector}", status_code=303)

"""Yearly competence map routes: /competence-map."""
from datetime import date as date_cls

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import competence_map as cmap_io

router = APIRouter(prefix="/competence-map", tags=["competence-map"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
def index(request: Request, year: int | None = None):
    years = cmap_io.available_years()
    chosen = year or (years[0] if years else date_cls.today().year)
    data = cmap_io.yearly_map(chosen)
    return templates.TemplateResponse(
        request,
        "competence_map/index.html",
        {
            "years": years,
            "chosen": chosen,
            "data": data,
        },
    )

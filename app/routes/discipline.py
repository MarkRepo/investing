"""Self-discipline dashboard."""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import discipline

router = APIRouter(prefix="/discipline", tags=["discipline"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def index(request: Request):
    payload = discipline.summary()
    return templates.TemplateResponse(request, "discipline/index.html", payload)

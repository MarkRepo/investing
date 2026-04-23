"""Search routes."""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import search as search_io

router = APIRouter(prefix="/search", tags=["search"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))

_SCOPES = ("all", "companies", "watchlist", "journal", "portfolio")


@router.get("")
def page(request: Request, q: str = "", scope: str = "all"):
    if scope not in _SCOPES:
        scope = "all"
    results = search_io.search(q, scope=scope) if q else []
    return templates.TemplateResponse(
        request,
        "search/results.html",
        {"q": q, "scope": scope, "scopes": _SCOPES, "results": results},
    )

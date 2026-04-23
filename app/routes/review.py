"""Quarterly review routes: /review and /review/{YYYY-Qn}."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import review as review_io

router = APIRouter(prefix="/review", tags=["review"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
def index(request: Request):
    quarters = review_io.list_quarters()
    return templates.TemplateResponse(
        request,
        "review/index.html",
        {
            "quarters": quarters,
            "current": review_io.current_quarter(),
        },
    )


@router.get("/{quarter}", response_class=HTMLResponse)
def detail(request: Request, quarter: str):
    if "-Q" not in quarter:
        raise HTTPException(status_code=400, detail="quarter must look like YYYY-Qn")
    summary = review_io.quarter_summary(quarter)
    return templates.TemplateResponse(
        request,
        "review/detail.html",
        {"summary": summary},
    )

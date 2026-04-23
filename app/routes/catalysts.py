"""Catalyst calendar routes: /catalysts."""
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import catalysts as cat_io

router = APIRouter(prefix="/catalysts", tags=["catalysts"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def index(request: Request):
    rows = cat_io.list_all()
    return templates.TemplateResponse(
        request,
        "catalysts/index.html",
        {
            "rows": rows,
            "upcoming": cat_io.upcoming(),
            "kinds": cat_io.VALID_KINDS,
            "error": None,
        },
    )


@router.post("/add")
def add(
    request: Request,
    date: str = Form(...),
    title: str = Form(...),
    kind: str = Form("other"),
    ticker: str = Form(""),
    industry: str = Form(""),
    note: str = Form(""),
):
    try:
        cat_io.add({
            "date": date,
            "ticker": ticker,
            "industry": industry,
            "kind": kind,
            "title": title,
            "note": note,
        })
    except ValueError as e:
        rows = cat_io.list_all()
        return templates.TemplateResponse(
            request,
            "catalysts/index.html",
            {
                "rows": rows,
                "upcoming": cat_io.upcoming(),
                "kinds": cat_io.VALID_KINDS,
                "error": str(e),
            },
            status_code=400,
        )
    return RedirectResponse(url="/catalysts", status_code=303)


@router.post("/delete/{index}")
def delete(index: int):
    try:
        cat_io.delete(index)
    except IndexError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return RedirectResponse(url="/catalysts", status_code=303)

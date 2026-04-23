"""Earnings-review routes.

List pending reviews (new financials periods since the V0's last_reviewed_period),
and render a compare page with V0 §5/§6/§7 + recent financials side by side.
"""
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import company as company_io
from app.io import earnings_review as er

router = APIRouter(prefix="/earnings-review", tags=["earnings-review"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


def _parse_key(key: str) -> tuple[str, str]:
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    return market, ticker


@router.get("")
def list_page(request: Request):
    rows = er.pending_reviews()
    return templates.TemplateResponse(
        request,
        "earnings_review/list.html",
        {"rows": rows},
    )


@router.get("/{key}")
def detail(request: Request, key: str):
    market, ticker = _parse_key(key)
    meta = company_io.read_meta(ticker, market)
    if not meta:
        raise HTTPException(status_code=404, detail="company not found")
    summary = er.company_summary(ticker, market)
    return templates.TemplateResponse(
        request,
        "earnings_review/detail.html",
        {"key": key, "ticker": ticker, "market": market, "meta": meta, "s": summary},
    )


@router.post("/{key}/mark")
def mark(key: str, period: str = Form(...)):
    market, ticker = _parse_key(key)
    if not company_io.read_meta(ticker, market):
        raise HTTPException(status_code=404, detail="company not found")
    er.mark_reviewed(ticker, market, period)
    return RedirectResponse(url="/earnings-review", status_code=303)

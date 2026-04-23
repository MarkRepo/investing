"""V0 edit + preview routes."""
from datetime import date

import markdown as md
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import v0 as v0io

router = APIRouter(prefix="/companies/{key}/v0", tags=["v0"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


def _parse_key(key: str) -> tuple[str, str]:
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    return market, ticker


@router.get("")
def edit_page(request: Request, key: str):
    market, ticker = _parse_key(key)
    try:
        doc = v0io.read_v0(ticker, market)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="v0.md missing") from e

    sections = v0io.split_sections(doc["body"])
    return templates.TemplateResponse(
        request,
        "v0/edit.html",
        {
            "key": key,
            "ticker": ticker,
            "market": market,
            "fm": doc["frontmatter"],
            "sections": sections,
            "section_titles": v0io.SECTION_TITLES,
        },
    )


@router.post("")
def save(
    key: str,
    entry_date: str = Form(""),
    position_size_pct: float = Form(0),
    status: str = Form("draft"),
    sec1: str = Form(""),
    sec2: str = Form(""),
    sec3: str = Form(""),
    sec4: str = Form(""),
    sec5: str = Form(""),
    sec6: str = Form(""),
    sec7: str = Form(""),
):
    market, ticker = _parse_key(key)
    existing = v0io.read_v0(ticker, market)
    fm = dict(existing["frontmatter"])
    fm["ticker"] = ticker
    fm["market"] = market
    fm["entry_date"] = entry_date or None
    fm["position_size_pct"] = position_size_pct
    fm["status"] = status
    fm["last_reviewed"] = date.today().isoformat()

    sections = {1: sec1, 2: sec2, 3: sec3, 4: sec4, 5: sec5, 6: sec6, 7: sec7}
    body = v0io.join_sections(sections, ticker)
    v0io.write_v0(ticker, market, fm, body)

    return RedirectResponse(url=f"/companies/{key}/v0", status_code=303)


@router.get("/preview")
def preview(request: Request, key: str):
    market, ticker = _parse_key(key)
    try:
        doc = v0io.read_v0(ticker, market)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="v0.md missing") from e

    html = md.markdown(
        doc["body"],
        extensions=["extra", "sane_lists"],
    )
    return templates.TemplateResponse(
        request,
        "v0/preview.html",
        {
            "key": key,
            "ticker": ticker,
            "market": market,
            "fm": doc["frontmatter"],
            "html": html,
        },
    )

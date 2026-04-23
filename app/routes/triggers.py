"""Per-company price trigger CRUD."""
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import company as company_io
from app.io import prices as prices_io
from app.io import triggers as triggers_io

router = APIRouter(prefix="/companies/{key}/triggers", tags=["triggers"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


def _parse_key(key: str) -> tuple[str, str]:
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    return market, ticker


@router.get("")
def page(request: Request, key: str):
    market, ticker = _parse_key(key)
    meta = company_io.read_meta(ticker, market)
    if not meta:
        raise HTTPException(status_code=404, detail="company not found")
    rows = triggers_io.list_for_ticker(ticker)
    latest = prices_io.latest_price_for(ticker)
    return templates.TemplateResponse(
        request,
        "companies/triggers.html",
        {
            "key": key, "ticker": ticker, "market": market, "meta": meta,
            "rows": rows,
            "latest_price": latest,
            "actions": triggers_io.ALL_ACTIONS,
            "buy_actions": triggers_io.BUY_ACTIONS + triggers_io.STOP_ACTIONS,
            "sell_actions": triggers_io.SELL_ACTIONS,
        },
    )


@router.post("")
def create(
    key: str,
    trigger_price: float = Form(...),
    action: str = Form(...),
):
    market, ticker = _parse_key(key)
    if not company_io.read_meta(ticker, market):
        raise HTTPException(status_code=404, detail="company not found")
    try:
        triggers_io.create(ticker, trigger_price, action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RedirectResponse(url=f"/companies/{key}/triggers", status_code=303)


@router.post("/{trigger_id}/delete")
def delete(key: str, trigger_id: int):
    _parse_key(key)
    triggers_io.delete(trigger_id)
    return RedirectResponse(url=f"/companies/{key}/triggers", status_code=303)


@router.post("/{trigger_id}/reset")
def reset(key: str, trigger_id: int):
    _parse_key(key)
    triggers_io.reset(trigger_id)
    return RedirectResponse(url=f"/companies/{key}/triggers", status_code=303)

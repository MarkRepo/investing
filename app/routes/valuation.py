"""Valuation routes."""
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import regime as regime_io
from app.io import valuation as val

router = APIRouter(prefix="/companies/{key}/valuation", tags=["valuation"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


def _parse_key(key: str) -> tuple[str, str]:
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    return market, ticker


def _signal_from_fm(fm: dict) -> dict | None:
    try:
        current = float(fm.get("current_price") or 0)
        bull = float(fm.get("bull_price") or 0)
        base = float(fm.get("base_price") or 0)
        bear = float(fm.get("bear_price") or 0)
    except (TypeError, ValueError):
        return None
    if min(bull, base, bear) <= 0 or current <= 0:
        return None
    return val.five_tier_signal(current=current, bull=bull, base=base, bear=bear)


@router.get("")
def edit_page(request: Request, key: str):
    market, ticker = _parse_key(key)
    try:
        doc = val.read_valuation(ticker, market)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="valuation.md missing") from e
    signal = _signal_from_fm(doc["frontmatter"])
    regime_latest = regime_io.latest()
    regime_fm = regime_latest["frontmatter"] if regime_latest else {}
    suggested = val.discount_rate_suggest(
        regime_fm.get("ust_10y_yield"),
        regime_fm.get("verdict"),
    )
    return templates.TemplateResponse(
        request,
        "valuation/edit.html",
        {
            "key": key, "ticker": ticker, "market": market,
            "fm": doc["frontmatter"], "body": doc["body"],
            "signal": signal,
            "regime_fm": regime_fm,
            "suggested_rate": suggested,
        },
    )


@router.post("")
def save(
    key: str,
    valuation_date: str = Form(...),
    bull_price: float = Form(0),
    base_price: float = Form(0),
    bear_price: float = Form(0),
    prob_bull: float = Form(0.25),
    prob_base: float = Form(0.5),
    prob_bear: float = Form(0.25),
    current_price: float = Form(0),
    discount_rate: float = Form(0.09),
    body: str = Form(""),
):
    market, ticker = _parse_key(key)

    try:
        weighted = val.compute_weighted(
            bull_price, base_price, bear_price, prob_bull, prob_base, prob_bear,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    implied_return = (
        (base_price - current_price) / current_price if current_price else 0
    )

    fm = {
        "ticker": ticker, "market": market, "valuation_date": valuation_date,
        "bull_price": bull_price, "base_price": base_price, "bear_price": bear_price,
        "prob_bull": prob_bull, "prob_base": prob_base, "prob_bear": prob_bear,
        "weighted_expected": round(weighted, 4),
        "current_price": current_price,
        "implied_return_to_base": round(implied_return, 4),
        "discount_rate": discount_rate,
    }
    val.write_valuation(ticker, market, fm, body)
    return RedirectResponse(url=f"/companies/{key}/valuation", status_code=303)

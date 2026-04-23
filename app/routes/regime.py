"""Market regime routes: /regime (list), /regime/{quarter} (edit)."""
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import regime as regime_io

router = APIRouter(prefix="/regime", tags=["regime"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
def index(request: Request):
    quarters = regime_io.list_quarters()
    latest = regime_io.latest()
    return templates.TemplateResponse(
        request,
        "regime/index.html",
        {
            "quarters": quarters,
            "latest": latest,
            "current": regime_io.current_quarter(),
            "verdicts": regime_io.VERDICTS,
            "sentiments": regime_io.SENTIMENTS,
            "reactions": regime_io.REACTIONS,
        },
    )


@router.get("/{quarter}", response_class=HTMLResponse)
def edit(request: Request, quarter: str):
    try:
        doc = regime_io.read(quarter) or {"frontmatter": {}, "body": ""}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return templates.TemplateResponse(
        request,
        "regime/edit.html",
        {
            "quarter": quarter,
            "fm": doc["frontmatter"],
            "body": doc["body"],
            "verdicts": regime_io.VERDICTS,
            "sentiments": regime_io.SENTIMENTS,
            "reactions": regime_io.REACTIONS,
            "error": None,
        },
    )


def _to_float(v: str | None) -> float | None:
    v = (v or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


@router.post("/{quarter}", response_class=HTMLResponse)
def save(
    request: Request,
    quarter: str,
    valuation_percentile: str = Form(""),
    credit_spread_bps: str = Form(""),
    vix_level: str = Form(""),
    ust_10y_yield: str = Form(""),
    retail_sentiment: str = Form(""),
    macro_reaction: str = Form(""),
    verdict: str = Form(""),
    position_hint: str = Form(""),
    cash_floor_hint: str = Form(""),
    body: str = Form(""),
):
    fm = {
        "valuation_percentile": _to_float(valuation_percentile),
        "credit_spread_bps": _to_float(credit_spread_bps),
        "vix_level": _to_float(vix_level),
        "ust_10y_yield": _to_float(ust_10y_yield),
        "retail_sentiment": retail_sentiment or None,
        "macro_reaction": macro_reaction or None,
        "verdict": verdict or None,
        "position_hint": position_hint or "",
        "cash_floor_hint": _to_float(cash_floor_hint),
    }
    try:
        regime_io.write(quarter, fm, body)
    except ValueError as e:
        return templates.TemplateResponse(
            request,
            "regime/edit.html",
            {
                "quarter": quarter,
                "fm": fm,
                "body": body,
                "verdicts": regime_io.VERDICTS,
                "sentiments": regime_io.SENTIMENTS,
                "reactions": regime_io.REACTIONS,
                "error": str(e),
            },
            status_code=400,
        )
    return RedirectResponse(url=f"/regime/{quarter}", status_code=303)

"""Financials page + manual refresh.

GET  /financials/{key}         → render page (all periods)
POST /financials/{key}/refresh → pull fresh from API, return JSON
GET  /companies/{key}/financials → 301 redirect to /financials/{key}
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import company as company_io
from app.io import financials as fin_io
from scripts import fetch_financials_cn, fetch_financials_us

router = APIRouter(tags=["financials"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


def _parse_key(key: str) -> tuple[str, str]:
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    return market, ticker


# ── redirect for old URLs ──────────────────────────────────────────────────

@router.get("/companies/{key}/financials")
def legacy_redirect(key: str):
    return RedirectResponse(url=f"/financials/{key}", status_code=301)


# ── main routes ───────────────────────────────────────────────────────────

@router.get("/financials")
def index(request: Request):
    """No key → redirect to first company, or show empty state."""
    companies = company_io.list_companies()
    if companies:
        return RedirectResponse(url=f"/financials/{companies[0]['key']}", status_code=302)
    return templates.TemplateResponse(request, "companies/financials_empty.html", {})


@router.get("/financials/{key}")
def page(request: Request, key: str):
    market, ticker = _parse_key(key)
    meta = company_io.read_meta(ticker, market)
    if not meta:
        raise HTTPException(status_code=404, detail="company not found")

    conn = fin_io.connect()
    try:
        fin_io.upsert_company(conn, {**meta, "ticker": ticker, "market": market})
        rows = fin_io.list_periods_with_ratios(conn, ticker, market=market)
    finally:
        conn.close()

    all_companies = sorted(
        company_io.list_companies(),
        key=lambda c: (c.get("market", ""), c.get("ticker", "")),
    )

    return templates.TemplateResponse(
        request,
        "companies/financials.html",
        {
            "key": key, "ticker": ticker, "market": market,
            "meta": meta, "rows": rows,
            "all_companies": all_companies,
        },
    )


@router.post("/financials/{key}/refresh")
def refresh(key: str):
    market, ticker = _parse_key(key)
    if not company_io.read_meta(ticker, market):
        raise HTTPException(status_code=404, detail="company not found")
    try:
        if market == "US":
            n = fetch_financials_us.run_for_ticker(ticker, market)
        elif market in ("SSE", "SZSE", "BSE"):
            n = fetch_financials_cn.run_for_ticker(ticker, market)
        else:
            return JSONResponse({"ok": False, "error": f"unsupported market {market}"}, status_code=400)
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": f"{type(e).__name__}: {e}"},
            status_code=500,
        )
    return {"ok": True, "periods_added": n}

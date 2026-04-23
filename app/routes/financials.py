"""Financials routes: show historical table + CSV import.

The page shows whatever is in SQLite for the given ticker. CSV import is the
primary way to populate it (manual entry → CSV, later report-parsing → CSV).
"""
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import company as company_io
from app.io import financials as fin_io

router = APIRouter(prefix="/companies/{key}/financials", tags=["financials"])
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

    # Mirror meta into SQLite companies table (read-through cache).
    conn = fin_io.connect()
    try:
        fin_io.upsert_company(conn, {**meta, "ticker": ticker, "market": market})
    finally:
        conn.close()

    rows = fin_io.list_periods_with_ratios(ticker)
    return templates.TemplateResponse(
        request,
        "companies/financials.html",
        {
            "key": key, "ticker": ticker, "market": market,
            "meta": meta, "rows": rows,
            "columns": fin_io.FINANCIAL_COLUMNS,
        },
    )


@router.post("/import")
async def import_csv(key: str, file: UploadFile = File(...)):
    market, ticker = _parse_key(key)
    if not company_io.read_meta(ticker, market):
        raise HTTPException(status_code=404, detail="company not found")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail=f"CSV must be UTF-8: {e}") from e

    try:
        fin_io.import_financials_csv(ticker, text, source_file=file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RedirectResponse(url=f"/companies/{key}/financials", status_code=303)

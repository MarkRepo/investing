"""Quotes pages: index (picker redirect), detail (panel + K/intraday), refresh,
chart JSON. Intraday is loaded on detail GET; daily history comes from the DB.

POST /prices/<key>/refresh is the manual bring-to-latest trigger shared with
the EOD cron via ``run_for_ticker``.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict
from datetime import date as date_cls
from datetime import timedelta
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import company as company_io
from app.io import quotes as quotes_io
from app.io.adapters import get_adapter
from app.io.adapters.base import AdapterError
from app.templating import register_filters

router = APIRouter(prefix="/prices", tags=["prices"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))
register_filters(templates)


def _parse_key(key: str) -> tuple[str, str]:
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    return market, ticker


@router.get("")
def index(request: Request):
    companies = company_io.list_companies()
    if not companies:
        return templates.TemplateResponse(request, "prices/empty.html", {})
    first = companies[0]["key"]
    return RedirectResponse(f"/prices/{first}", status_code=302)


@router.get("/{key}")
def detail(request: Request, key: str):
    market, ticker = _parse_key(key)
    meta = company_io.read_meta(ticker, market)
    if not meta:
        raise HTTPException(status_code=404, detail="company not found")

    latest = quotes_io.latest_for(ticker)
    prev = quotes_io.second_latest_for(ticker)
    kline = quotes_io.history_for(ticker, limit=5000)
    freshness = quotes_io.freshness(ticker)
    all_companies = company_io.list_companies()
    # Intraday is loaded async via GET /prices/<key>/intraday so switching
    # companies doesn't wait on a sina/yfinance round-trip.
    has_data = latest is not None
    return templates.TemplateResponse(
        request,
        "prices/index.html",
        {
            "meta": meta,
            "key": key,
            "ticker": ticker,
            "market": market,
            "latest_quote": latest,
            "prev_quote": prev,
            "kline": kline,
            "has_data": has_data,
            "freshness": freshness,
            "all_companies": all_companies,
        },
    )


@router.get("/{key}/intraday")
def intraday(key: str):
    """Today's 1-min bars. Called by the page JS after mount, not server-rendered."""
    market, ticker = _parse_key(key)
    if not company_io.read_meta(ticker, market):
        raise HTTPException(status_code=404, detail="company not found")
    if quotes_io.latest_for(ticker) is None:
        return {"bars": [], "error": None}
    try:
        bars = get_adapter(market).fetch_intraday_today(ticker, market)
        quotes_io.mark_errors_resolved(ticker)  # source reachable
        return {"bars": bars, "error": None}
    except AdapterError as e:
        quotes_io.record_error(ticker, market, phase="intraday", error=str(e))
        return {"bars": [], "error": str(e)}


@router.post("/{key}/refresh")
def refresh(key: str):
    """Adaptive manual refresh — bring daily history up-to-date + fetch snapshot.

    On empty history: backfills ``backfill_years`` years.
    On stale history: incremental fetch from last_date+1.
    Always tries a snapshot for the "today" row too; snapshot failure is a
    separate bucket from daily failure.
    """
    from scripts.fetch_quotes_eod import run_for_ticker

    market, ticker = _parse_key(key)
    if not company_io.read_meta(ticker, market):
        raise HTTPException(status_code=404, detail="company not found")

    daily = run_for_ticker(ticker, market)

    snapshot: Optional[dict] = None
    snap_err: Optional[str] = None
    try:
        snap = get_adapter(market).fetch_snapshot(ticker, market)
        quotes_io.upsert(snap)
        snapshot = asdict(snap)
        # snapshot reached the source OK — clear any stale errors still on file
        quotes_io.mark_errors_resolved(ticker)
    except AdapterError as e:
        snap_err = str(e)
        quotes_io.record_error(ticker, market, phase="snapshot", error=str(e))

    ok = (daily["status"] != "error") or (snapshot is not None)
    return {
        "ok": ok,
        "quotes_added": daily["quotes_added"],
        "daily_error": daily["error"],
        "snapshot_error": snap_err,
        "snapshot": snapshot,
        "latest": quotes_io.latest_for(ticker),
        "prev": quotes_io.second_latest_for(ticker),
        "kline": quotes_io.history_for(ticker, limit=5000),
        "freshness": quotes_io.freshness(ticker),
    }


@router.get("/{key}/chart")
def chart(key: str, period: Literal["1d", "1w", "1M"] = "1d"):
    """Return OHLCV JSON. ``period=1d`` is raw; 1w/1M are aggregated."""
    market, ticker = _parse_key(key)
    if not company_io.read_meta(ticker, market):
        raise HTTPException(status_code=404, detail="company not found")
    rows = quotes_io.history_for(ticker, limit=5000)
    if period == "1d":
        return {"period": period, "ohlcv": rows}
    return {"period": period, "ohlcv": _aggregate(rows, period)}


def _aggregate(rows: list[dict], period: str) -> list[dict]:
    """Group daily bars into weekly/monthly buckets.

    Week key = Monday of that ISO week; Month key = first-of-month. High is
    the max, low is the min, close is the last day's close, volume is summed.
    """
    buckets: "OrderedDict[str, dict]" = OrderedDict()
    for r in rows:
        d = date_cls.fromisoformat(r["date"])
        if period == "1w":
            key = (d - timedelta(days=d.weekday())).isoformat()
        else:
            key = d.replace(day=1).isoformat()

        if key not in buckets:
            buckets[key] = {
                "date": key,
                "open": r.get("open"),
                "high": r.get("high"),
                "low": r.get("low"),
                "close": r.get("close"),
                "volume": r.get("volume") or 0,
            }
            continue

        b = buckets[key]
        if r.get("high") is not None:
            b["high"] = max(b["high"], r["high"]) if b["high"] is not None else r["high"]
        if r.get("low") is not None:
            b["low"] = min(b["low"], r["low"]) if b["low"] is not None else r["low"]
        if r.get("close") is not None:
            b["close"] = r["close"]
        b["volume"] = (b["volume"] or 0) + (r.get("volume") or 0)
    return list(buckets.values())

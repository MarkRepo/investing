#!/usr/bin/env python3
"""End-of-day quote fetcher.

Usage:
  python -m scripts.fetch_quotes_eod                        # all companies
  python -m scripts.fetch_quotes_eod --markets US           # US only
  python -m scripts.fetch_quotes_eod --tickers 600519,AAPL  # specific tickers
  python -m scripts.fetch_quotes_eod --backfill-years 10    # longer history

Also exports ``run_for_ticker`` which the manual refresh route shares.
"""
from __future__ import annotations

import argparse
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from app.io import company as company_io
from app.io import quotes as quotes_io
from app.io.adapters import get_adapter
from app.io.adapters.base import AdapterError


def run_for_ticker(
    ticker: str,
    market: str,
    backfill_years: int = 5,
    base: Optional[Path] = None,
    today: Optional[date] = None,
) -> dict:
    """Bring ``ticker`` up to date; returns ``{status, quotes_added, error}``.

    - If the ticker has no history, backfills ``backfill_years`` years.
    - If history exists, fetches from ``last_date + 1`` to today.
    - If already current, returns ``status="uptodate"`` without calling the API.
    - On adapter error, records to ``quotes_fetch_errors`` and returns error.
    - On success with rows written, clears any prior unresolved errors.
    """
    today = today or date.today()
    last = quotes_io.last_date_for(ticker, base=base)
    if last:
        start = date.fromisoformat(last) + timedelta(days=1)
    else:
        start = today - timedelta(days=365 * backfill_years)
    end = today
    if start > end:
        return {"status": "uptodate", "quotes_added": 0, "error": None}

    try:
        adapter = get_adapter(market)
        quotes = adapter.fetch_daily(ticker, market, start, end)
        for q in quotes:
            quotes_io.upsert(q, base=base)
        # adapter call succeeded — clear any stale errors (daily/snapshot/intraday),
        # not just when new rows were written. Source is reachable now.
        quotes_io.mark_errors_resolved(ticker, base=base)
        return {"status": "ok", "quotes_added": len(quotes), "error": None}
    except AdapterError as e:
        quotes_io.record_error(ticker, market, phase="eod", error=str(e), base=base)
        return {"status": "error", "quotes_added": 0, "error": str(e)}


def run_eod(
    tickers: Optional[list[str]] = None,
    markets: Optional[list[str]] = None,
    backfill_years: int = 5,
    base: Optional[Path] = None,
    sleep_between: bool = True,
) -> dict:
    """Iterate companies/ and pull each. Returns aggregate counts."""
    companies = company_io.list_companies(base=base)
    if markets:
        companies = [c for c in companies if c["market"] in markets]
    if tickers:
        tset = set(tickers)
        companies = [c for c in companies if c["ticker"] in tset]

    ok = err = uptodate = 0
    for c in companies:
        r = run_for_ticker(
            c["ticker"], c["market"],
            backfill_years=backfill_years, base=base,
        )
        if r["status"] == "ok":
            ok += 1
        elif r["status"] == "error":
            err += 1
        else:
            uptodate += 1
        if sleep_between:
            time.sleep(0.3 if c["market"] == "US" else 0.1)

    return {
        "ok": ok, "errors": err, "uptodate": uptodate,
        "total": len(companies),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tickers", help="comma-separated ticker list")
    p.add_argument("--markets", help="comma-separated market list (SSE,SZSE,BSE,US)")
    p.add_argument("--backfill-years", type=int, default=5,
                   help="history window for new tickers (default 5)")
    args = p.parse_args()

    tickers = args.tickers.split(",") if args.tickers else None
    markets = args.markets.split(",") if args.markets else None

    result = run_eod(
        tickers=tickers, markets=markets,
        backfill_years=args.backfill_years,
    )
    print(
        f"EOD: {result['ok']} ok / "
        f"{result['errors']} errors / "
        f"{result['uptodate']} up-to-date "
        f"({result['total']} total)"
    )


if __name__ == "__main__":
    main()

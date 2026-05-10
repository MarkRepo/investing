"""Financials cache helper — DB-first lookup, fetch+store on miss.

Used by prism workflow 03 to get financial data for annual reports
without parsing PDFs. Checks local DB first; only calls akshare if
data is missing or stale.

Usage:
    python -m scripts.financials_cache SSE_688066
    python -m scripts.financials_cache SSE_688066 --periods 6
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from datetime import date

from app import config as cfg
from scripts.fetch_financials_cn import run_for_ticker as _fetch_cn

log = logging.getLogger("financials_cache")

# Columns most useful for investment analysis (skip raw balance sheet detail)
_KEY_COLS = [
    "period", "period_type",
    "total_revenue", "operating_revenue",
    "net_income", "net_income_to_parent",
    "rd_expense", "selling_expense", "admin_expense",
    "operating_income", "operating_cashflow", "capex",
    "total_assets", "total_equity", "total_liabilities",
    "cash_and_equivalents", "short_term_debt", "long_term_debt",
    "accounts_receivable", "contract_liabilities",
]


def _bare_ticker(market_ticker: str) -> str:
    """'SSE_688066' → '688066'"""
    return market_ticker.split("_", 1)[-1]


def _market(market_ticker: str) -> str:
    """'SSE_688066' → 'SSE'"""
    return market_ticker.split("_", 1)[0]


def _is_fresh(conn: sqlite3.Connection, ticker: str) -> bool:
    """Return True if DB has data and the most recent period is within this fiscal year."""
    row = conn.execute(
        "SELECT period FROM financials_cn WHERE ticker=? ORDER BY period DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    if not row:
        return False
    period = row[0]   # e.g. '2026Q1' or '2025A'
    try:
        year = int(period[:4])
    except (ValueError, TypeError):
        return False
    return year >= date.today().year - 1


def get(
    market_ticker: str,
    periods: int = 6,
    force_refresh: bool = False,
) -> list[dict]:
    """Return key financial data for the last N periods.

    Checks DB first. Fetches from akshare and stores to DB if stale or missing.
    """
    ticker = _bare_ticker(market_ticker)
    market = _market(market_ticker)

    conn = sqlite3.connect(cfg.FINANCIALS_DB)
    try:
        if force_refresh or not _is_fresh(conn, ticker):
            log.info("Financials stale or missing for %s — fetching from API…", market_ticker)
            conn.close()
            _fetch_cn(ticker, market)
            conn = sqlite3.connect(cfg.FINANCIALS_DB)
        else:
            log.info("Financials for %s found in DB (fresh)", market_ticker)

        cols = ", ".join(_KEY_COLS)
        rows = conn.execute(
            f"SELECT {cols} FROM financials_cn WHERE ticker=? "
            f"ORDER BY period DESC LIMIT ?",
            (ticker, periods),
        ).fetchall()

        return [dict(zip(_KEY_COLS, row)) for row in rows]
    finally:
        conn.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Get financial data (DB-first, fetch on miss)")
    parser.add_argument("ticker", help="Market_Ticker, e.g. SSE_688066")
    parser.add_argument("--periods", type=int, default=6)
    parser.add_argument("--refresh", action="store_true", help="Force API refresh")
    args = parser.parse_args()

    data = get(args.ticker, args.periods, args.refresh)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()

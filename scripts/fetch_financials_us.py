"""Fetch US financials via yfinance → financials_us.

yfinance.Ticker exposes:
  - income_stmt, balance_sheet, cashflow       (annual; 4 columns)
  - quarterly_income_stmt, quarterly_balance_sheet, quarterly_cashflow
Each DataFrame has financial-line names as index, pd.Timestamp columns.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from app import config as cfg
from app.io import financials as fin

log = logging.getLogger("fetch_financials_us")

# Only snake_case column names that actually exist in financials_us are written.
_US_COL_SET = set(fin.US_COLUMNS)


def period_for_stmt(ts: pd.Timestamp, period_type: str) -> str:
    mm = ts.month
    year = ts.year
    if period_type == "annual":
        return f"{year}A"
    q_num = (mm - 1) // 3 + 1
    return f"{year}Q{q_num}"


def _stmt_to_rows(
    df: pd.DataFrame, ticker: str, period_type: str
) -> dict[str, dict]:
    """DataFrame → {period: {snake_col: value}}. Index is Title Case labels."""
    if df is None or df.empty:
        return {}
    out: dict[str, dict] = {}
    for col_ts in df.columns:
        if not isinstance(col_ts, pd.Timestamp):
            continue
        period = period_for_stmt(col_ts, period_type)
        row: dict[str, Any] = {
            "ticker": ticker,
            "period": period,
            "period_type": period_type,
            "report_date": col_ts.date().isoformat(),
            "source": "yfinance",
        }
        for idx, val in df[col_ts].items():
            snake = cfg.us_col_to_snake(str(idx))
            if snake not in _US_COL_SET:
                continue
            try:
                row[snake] = None if pd.isna(val) else float(val)
            except (TypeError, ValueError):
                row[snake] = None
        out[period] = row
    return out


def _merge(
    income: pd.DataFrame, balance: pd.DataFrame, cashflow: pd.DataFrame,
    ticker: str, period_type: str,
) -> dict[str, dict]:
    i = _stmt_to_rows(income, ticker, period_type)
    b = _stmt_to_rows(balance, ticker, period_type)
    c = _stmt_to_rows(cashflow, ticker, period_type)
    periods = sorted(set(i) | set(b) | set(c), reverse=True)
    out: dict[str, dict] = {}
    for p in periods:
        r: dict[str, Any] = {}
        for src in (i.get(p, {}), b.get(p, {}), c.get(p, {})):
            r.update(src)
        if "period" in r:
            out[p] = r
    return out


def run_for_ticker(ticker: str, market: str, base: Path | None = None) -> int:
    """Fetch yfinance statements → financials_us. Serves US and HKEX.

    HKEX is queried via the ``.HK`` symbol (``cfg.to_yf_symbol``) but rows are
    stored under the bare code (``01801``). NOTE on currency: HK statements come
    back in the company's reporting currency (often CNY for HK-listed mainland
    biotech), while the quotes pipe stores HK price/market_cap in HKD — do NOT
    cross them (e.g. HKD price × CNY revenue). Intra-statement ratios
    (margin/ROIC/debt-to-equity/OCF quality) are currency-neutral and safe.
    """
    if market not in ("US", "HKEX"):
        raise ValueError(
            f"fetch_financials_us only supports US/HKEX, got {market!r}"
        )
    t = yf.Ticker(cfg.to_yf_symbol(ticker, market))
    annuals = _merge(t.income_stmt, t.balance_sheet, t.cashflow, ticker, "annual")
    quarters = _merge(
        t.quarterly_income_stmt, t.quarterly_balance_sheet, t.quarterly_cashflow,
        ticker, "quarterly",
    )
    rows = list(annuals.values()) + list(quarters.values())
    if not rows:
        log.warning("%s: yfinance returned no statements", ticker)
        return 0
    conn = fin.connect(base=base)
    try:
        n = fin.upsert_financials_us(conn, rows)
        fin.recompute_ratios(conn, ticker, market=market)
        log.info("%s: upserted %d periods", ticker, n)
        return n
    finally:
        conn.close()


def _iter_us_companies() -> list[str]:
    out = []
    for f in cfg.COMPANIES_DIR.glob("US_*/_meta.yaml"):
        key = f.parent.name
        if "_" in key:
            _, ticker = key.split("_", 1)
            out.append(ticker)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fetch US financials into financials_us")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("key", nargs="?", help="e.g. US_HIMS")
    g.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    targets: list[str]
    if args.key:
        _, t = args.key.split("_", 1)
        targets = [t]
    else:
        targets = _iter_us_companies()

    fails = 0
    for t in targets:
        try:
            run_for_ticker(t, "US")
        except Exception as e:
            log.error("US_%s: %s: %s", t, type(e).__name__, e)
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

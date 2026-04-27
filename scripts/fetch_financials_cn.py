"""Fetch CN A-share financials via akshare Sina → financials_cn."""
from __future__ import annotations

import argparse
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import akshare as ak
import pandas as pd

from app import config as cfg
from app.io import financials as fin

log = logging.getLogger("fetch_financials_cn")

_MARKET_PREFIX = {"SSE": "sh", "SZSE": "sz", "BSE": "bj"}
_PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
               "http_proxy", "https_proxy", "all_proxy")


@contextmanager
def _no_proxy():
    saved = {k: os.environ.pop(k, None) for k in _PROXY_KEYS}
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def sina_symbol(ticker: str, market: str) -> str:
    prefix = _MARKET_PREFIX.get(market)
    if not prefix:
        raise ValueError(f"fetch_financials_cn: unsupported market {market!r}")
    return f"{prefix}{ticker}"


def derive_period(report_date: str, report_type: str) -> tuple[str, str]:
    """报告日 + 类型 → (period, period_type). Accepts 'YYYY-MM-DD' or 'YYYYMMDD'."""
    d = str(report_date).strip()
    if "-" in d:
        d = d[:10]
        year, mm = d[:4], d[5:7]
    else:
        d = d[:8]
        year, mm = d[:4], d[4:6]
    t = (report_type or "").strip()
    if mm == "12" and "年报" in t:
        return (f"{year}A", "annual")
    q = {"03": "Q1", "06": "Q2", "09": "Q3", "12": "Q4"}.get(mm)
    if not q:
        raise ValueError(f"unrecognized month in report_date {report_date!r}")
    return (f"{year}{q}", "quarterly")


def _df_to_rows(df: pd.DataFrame, ticker: str, market: str) -> dict[str, dict]:
    """Translate one statement DataFrame into period→row dict using CN_COL_MAP."""
    if df is None or df.empty:
        return {}
    if "报告日" not in df.columns:
        log.warning("DataFrame has no 报告日 column; skipping")
        return {}
    out: dict[str, dict] = {}
    for _, r in df.iterrows():
        rd = str(r["报告日"])[:10]
        rtype = str(r.get("类型", "")).strip()
        try:
            period, ptype = derive_period(rd, rtype)
        except ValueError as e:
            log.warning("skip row for %s: %s", ticker, e)
            continue
        row: dict[str, Any] = {
            "ticker": ticker,
            "period": period,
            "period_type": ptype,
            "report_date": rd,
            "source": "akshare",
        }
        for col, val in r.items():
            if col in ("报告日", "类型"):
                continue
            snake = cfg.CN_COL_MAP.get(col)
            if snake is None:
                log.warning("%s: unmapped CN column %r (value=%r)", ticker, col, val)
                continue
            if snake.startswith("_"):
                continue
            try:
                row[snake] = None if pd.isna(val) else float(val)
            except (TypeError, ValueError):
                row[snake] = None
        out[period] = row
    return out


def _merge_statements(
    income: pd.DataFrame, balance: pd.DataFrame, cashflow: pd.DataFrame,
    ticker: str, market: str,
) -> list[dict]:
    i = _df_to_rows(income, ticker, market)
    b = _df_to_rows(balance, ticker, market)
    c = _df_to_rows(cashflow, ticker, market)
    periods = sorted(set(i) | set(b) | set(c), reverse=True)
    merged = []
    for p in periods:
        row: dict[str, Any] = {}
        for src in (i.get(p, {}), b.get(p, {}), c.get(p, {})):
            row.update(src)
        if "period" in row and "ticker" in row:
            merged.append(row)
    return merged


def run_for_ticker(ticker: str, market: str, base: Path | None = None) -> int:
    """Fetch 3 statements from akshare Sina, upsert into financials_cn,
    recompute ratios. Returns # periods written."""
    symbol = sina_symbol(ticker, market)
    with _no_proxy():
        income = ak.stock_financial_report_sina(stock=symbol, symbol="利润表")
        balance = ak.stock_financial_report_sina(stock=symbol, symbol="资产负债表")
        cashflow = ak.stock_financial_report_sina(stock=symbol, symbol="现金流量表")
    rows = _merge_statements(income, balance, cashflow, ticker, market)
    if not rows:
        log.warning("%s: no statements returned", ticker)
        return 0
    conn = fin.connect(base=base)
    try:
        n = fin.upsert_financials_cn(conn, rows)
        fin.recompute_ratios(conn, ticker, market=market)
        log.info("%s: upserted %d periods (via %s)", ticker, n, symbol)
        return n
    finally:
        conn.close()


# ---- CLI --------------------------------------------------------------------


def _iter_companies(market_filter: str | None) -> list[tuple[str, str]]:
    """Read meta dir and yield (ticker, market) for CN markets."""
    out = []
    for f in cfg.COMPANIES_DIR.glob("*/_meta.yaml"):
        key = f.parent.name
        if "_" not in key:
            continue
        market, ticker = key.split("_", 1)
        if market not in _MARKET_PREFIX:
            continue
        if market_filter and market != market_filter:
            continue
        out.append((ticker, market))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fetch CN financials into financials_cn")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("key", nargs="?", help="e.g. SSE_600519")
    g.add_argument("--all", action="store_true")
    g.add_argument("--market", choices=("SSE", "SZSE", "BSE"))
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    targets: list[tuple[str, str]] = []
    if args.key:
        market, ticker = args.key.split("_", 1)
        targets = [(ticker, market)]
    elif args.all:
        targets = _iter_companies(None)
    elif args.market:
        targets = _iter_companies(args.market)

    fails = 0
    for t, m in targets:
        try:
            run_for_ticker(t, m)
        except Exception as e:
            log.error("%s_%s: %s: %s", m, t, type(e).__name__, e)
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

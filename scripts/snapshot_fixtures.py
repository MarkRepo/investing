#!/usr/bin/env python3
"""Regenerate adapter fixtures from real sources.

Usage:
  python -m scripts.snapshot_fixtures            # both
  python -m scripts.snapshot_fixtures akshare    # just akshare
  python -m scripts.snapshot_fixtures yfinance   # just yfinance

Run manually when upstream schemas change or when you want a fresh sample.
Writes into tests/fixtures/adapters/{akshare,yfinance}/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

FIX_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "adapters"


def snapshot_akshare(ticker: str = "600519", market: str = "SSE") -> None:
    import akshare as ak
    from app.io.adapters.akshare_adapter import _sina_symbol
    out = FIX_DIR / "akshare"
    out.mkdir(parents=True, exist_ok=True)

    sina_sym = _sina_symbol(ticker, market)

    # 1-month daily via sina
    ak.stock_zh_a_daily(
        symbol=sina_sym, start_date="20260401", end_date="20260424", adjust="",
    ).to_csv(out / f"daily_{sina_sym}.csv", index=False)

    # value_em from eastmoney data center (different host, usually reachable)
    ak.stock_value_em(symbol=ticker).tail(20).to_csv(
        out / f"value_em_{ticker}.csv", index=False,
    )

    # intraday 1-min via sina
    ak.stock_zh_a_minute(symbol=sina_sym, period="1", adjust="").head(50).to_csv(
        out / f"minute_{sina_sym}.csv", index=False,
    )
    print(f"[akshare] fixtures written → {out}")


def snapshot_yfinance(ticker: str = "HIMS") -> None:
    import yfinance as yf
    out = FIX_DIR / "yfinance"
    out.mkdir(parents=True, exist_ok=True)

    t = yf.Ticker(ticker)
    (out / f"info_{ticker}.json").write_text(
        json.dumps(t.info or {}, indent=2, default=str)
    )
    t.history(period="1mo", auto_adjust=False).to_csv(out / f"history_{ticker}.csv")
    t.history(period="1d", interval="1m", auto_adjust=False).to_csv(
        out / f"intraday_{ticker}.csv"
    )
    print(f"[yfinance] fixtures written → {out}")


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which not in ("akshare", "yfinance", "both"):
        print(f"unknown target: {which}")
        sys.exit(2)
    if which in ("akshare", "both"):
        snapshot_akshare()
    if which in ("yfinance", "both"):
        snapshot_yfinance()


if __name__ == "__main__":
    main()

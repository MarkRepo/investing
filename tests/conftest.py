"""Shared test fixtures. Keep module-scoped setup here (esp. adapter mocks)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

FIX_DIR = Path(__file__).parent / "fixtures" / "adapters"


@pytest.fixture
def mock_akshare(monkeypatch):
    """Replace the real akshare endpoints with fixture-backed fakes.

    Reads from ``tests/fixtures/adapters/akshare/``:
      - ``daily_<sina_symbol>.csv`` → stock_zh_a_daily
      - ``value_em_<ticker>.csv``   → stock_value_em
      - ``minute_<sina_symbol>.csv``→ stock_zh_a_minute
    """
    def _daily(symbol, start_date, end_date, adjust):
        path = FIX_DIR / "akshare" / f"daily_{symbol}.csv"
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path)

    def _value_em(symbol):
        path = FIX_DIR / "akshare" / f"value_em_{symbol}.csv"
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path)

    def _minute(symbol, period, adjust):
        path = FIX_DIR / "akshare" / f"minute_{symbol}.csv"
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path)

    import akshare as ak
    monkeypatch.setattr(ak, "stock_zh_a_daily", _daily)
    monkeypatch.setattr(ak, "stock_value_em", _value_em)
    monkeypatch.setattr(ak, "stock_zh_a_minute", _minute)


@pytest.fixture
def mock_yfinance(monkeypatch):
    """Replace yf.Ticker with a fixture-backed fake.

    The fake Ticker's ``info``, ``fast_info``, and ``history()`` read from
    ``tests/fixtures/adapters/yfinance/``.
    """
    class _FakeTicker:
        def __init__(self, symbol: str):
            self.symbol = symbol

        @property
        def info(self):
            path = FIX_DIR / "yfinance" / f"info_{self.symbol}.json"
            if not path.exists():
                return {}
            return json.loads(path.read_text())

        @property
        def fast_info(self):
            return self.info  # close enough for the fields we read

        def history(self, period=None, start=None, end=None, interval="1d",
                    auto_adjust=False):
            if interval == "1m":
                path = FIX_DIR / "yfinance" / f"intraday_{self.symbol}.csv"
            else:
                path = FIX_DIR / "yfinance" / f"history_{self.symbol}.csv"
            if not path.exists():
                return pd.DataFrame()
            df = pd.read_csv(path, index_col=0, parse_dates=True)
            return df

    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", _FakeTicker)

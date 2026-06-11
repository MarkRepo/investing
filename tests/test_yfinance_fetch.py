"""yfinance 取数通道：fetch_by_yfinance 解析（mock yfinance，零网络）。

覆盖：按日期取最新收盘、自定义 field、index 乱序仍取 max、ticker 格式守卫拦注入、
列缺失/空 DataFrame/缺 ticker 的诚实降级。
"""
from __future__ import annotations

import pandas as pd
import pytest

from prism.scripts import yfinance_fetch as yff


class FakeTicker:
    def __init__(self, df):
        self._df = df

    def history(self, period="5d"):
        return self._df


class FakeYf:
    """mock yfinance：Ticker(sym).history() 回注入的 DataFrame。"""

    def __init__(self, df):
        self._df = df
        self.last_ticker = None

    def Ticker(self, ticker):
        self.last_ticker = ticker
        return FakeTicker(self._df)


def _df(closes, dates, **extra):
    idx = pd.to_datetime(dates)
    return pd.DataFrame({"Open": [c - 1 for c in closes], "Close": closes, **extra}, index=idx)


def test_picks_latest_close_by_date():
    yf = FakeYf(_df([76.98, 77.03, 73.95], ["2026-06-08", "2026-06-09", "2026-06-10"]))
    v, d = yff.fetch_by_yfinance({"ticker": "^MOVE", "field": "Close"}, yf_module=yf)
    assert abs(v - 73.95) < 1e-9 and d == "2026-06-10"
    assert yf.last_ticker == "^MOVE"


def test_default_field_is_close():
    yf = FakeYf(_df([10.0, 12.0], ["2026-06-09", "2026-06-10"]))
    v, d = yff.fetch_by_yfinance({"ticker": "^MOVE"}, yf_module=yf)  # 无 field → Close
    assert v == 12.0 and d == "2026-06-10"


def test_custom_field():
    yf = FakeYf(_df([10.0, 12.0], ["2026-06-09", "2026-06-10"]))
    v, _ = yff.fetch_by_yfinance({"ticker": "DX-Y.NYB", "field": "Open"}, yf_module=yf)
    assert v == 11.0  # Open = Close-1


def test_unsorted_index_still_picks_max_date():
    yf = FakeYf(_df([73.95, 76.98, 77.03], ["2026-06-10", "2026-06-08", "2026-06-09"]))
    v, d = yff.fetch_by_yfinance({"ticker": "^MOVE"}, yf_module=yf)
    assert abs(v - 73.95) < 1e-9 and d == "2026-06-10"


def test_ticker_format_guard_blocks_injection():
    yf = FakeYf(_df([1.0], ["2026-06-10"]))
    with pytest.raises(ValueError, match="格式非法"):
        yff.fetch_by_yfinance({"ticker": "rm -rf /"}, yf_module=yf)


def test_missing_ticker_raises():
    yf = FakeYf(_df([1.0], ["2026-06-10"]))
    with pytest.raises(ValueError, match="缺 ticker"):
        yff.fetch_by_yfinance({"field": "Close"}, yf_module=yf)


def test_missing_field_column_raises():
    yf = FakeYf(_df([1.0], ["2026-06-10"]))
    with pytest.raises(ValueError, match="无此列"):
        yff.fetch_by_yfinance({"ticker": "^MOVE", "field": "Nonexistent"}, yf_module=yf)


def test_empty_dataframe_returns_none():
    yf = FakeYf(pd.DataFrame())
    assert yff.fetch_by_yfinance({"ticker": "^MOVE"}, yf_module=yf) == (None, None)


def test_accepts_valid_yahoo_symbols():
    yf = FakeYf(_df([1.0], ["2026-06-10"]))
    for sym in ("^MOVE", "^TNX", "DX-Y.NYB", "GC=F", "EURUSD=X", "BTC-USD"):
        v, _ = yff.fetch_by_yfinance({"ticker": sym}, yf_module=yf)
        assert v == 1.0

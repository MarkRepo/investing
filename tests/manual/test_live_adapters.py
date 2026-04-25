"""Contract tests against real akshare/yfinance endpoints.

Marked ``live`` so pytest -m "not live" (our default) skips them. Run:

    pytest -m live

Expect flakes in China / rate-limit windows. These tests exist to catch
upstream schema drift — if a column gets renamed, the fixture-based tests
above will pass but production will break.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.live


def test_akshare_daily_has_expected_columns():
    import akshare as ak
    df = ak.stock_zh_a_daily(
        symbol="sh600519", start_date="20260401", end_date="20260424", adjust="",
    )
    assert not df.empty
    for col in ["date", "open", "high", "low", "close", "volume", "amount",
                "outstanding_share", "turnover"]:
        assert col in df.columns, f"akshare daily missing {col}"


def test_akshare_minute_has_expected_columns():
    import akshare as ak
    df = ak.stock_zh_a_minute(symbol="sh600519", period="1", adjust="")
    assert not df.empty
    for col in ["day", "open", "high", "low", "close", "volume"]:
        assert col in df.columns, f"akshare minute missing {col}"


def test_akshare_value_em_has_expected_columns():
    import akshare as ak
    df = ak.stock_value_em(symbol="600519")
    assert not df.empty
    needed = {"数据日期", "总市值", "流通市值", "总股本", "流通股本",
              "PE(TTM)", "PE(静)", "市净率", "PEG值", "市销率"}
    missing = needed - set(df.columns)
    assert not missing, f"akshare value_em missing: {missing}"


def test_yfinance_info_has_expected_keys():
    import yfinance as yf
    info = yf.Ticker("AAPL").info
    for key in ["trailingPE", "marketCap", "floatShares",
                "fiftyTwoWeekHigh", "fiftyTwoWeekLow"]:
        assert key in info, f"yfinance info missing {key}"


def test_yfinance_history_has_expected_columns():
    import yfinance as yf
    hist = yf.Ticker("AAPL").history(period="5d", auto_adjust=False)
    assert not hist.empty
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        assert col in hist.columns, f"yfinance history missing {col}"


def test_akshare_fetch_daily_end_to_end():
    """Smoke-test our adapter against a real ticker end-to-end."""
    from datetime import date, timedelta
    from app.io.adapters import akshare_adapter as akad
    end = date.today()
    start = end - timedelta(days=10)
    rows = akad.fetch_daily("600519", "SSE", start, end)
    assert rows, "expected at least one daily row"
    latest = rows[-1]
    assert latest.close > 0
    assert latest.high_52w is not None  # spot-attached


def test_yfinance_fetch_daily_end_to_end():
    from datetime import date, timedelta
    from app.io.adapters import yfinance_adapter as yfad
    end = date.today()
    start = end - timedelta(days=10)
    rows = yfad.fetch_daily("AAPL", "US", start, end)
    assert rows, "expected at least one daily row"
    latest = rows[-1]
    assert latest.close > 0
    assert latest.pe_ttm is not None or latest.market_cap is not None

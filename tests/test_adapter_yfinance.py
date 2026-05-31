"""Tests for app.io.adapters.yfinance_adapter."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from app.io.adapters import yfinance_adapter as yfad
from app.io.adapters.base import AdapterError


# ---------- fetch_daily ----------


def test_fetch_daily_maps_ohlcv(mock_yfinance):
    rows = yfad.fetch_daily("HIMS", "US", date(2026, 4, 20), date(2026, 4, 24))
    assert len(rows) == 5
    first = rows[0]
    assert first.ticker == "HIMS"
    assert first.market == "US"
    assert first.date == "2026-04-20"
    assert first.open == 35.50
    assert first.high == 36.00
    assert first.low == 35.20
    assert first.close == 35.80
    assert first.volume == 4_200_000
    # amount = close * volume (yfinance doesn't provide a native dollar turnover)
    assert first.amount == pytest.approx(35.80 * 4_200_000)


def test_fetch_daily_historical_rows_have_no_point_in_time_fields(mock_yfinance):
    rows = yfad.fetch_daily("HIMS", "US", date(2026, 4, 20), date(2026, 4, 24))
    for r in rows[:-1]:
        assert r.pe_ttm is None
        assert r.pb is None
        assert r.ps is None
        assert r.market_cap is None
        assert r.high_52w is None
        assert r.low_52w is None
        assert r.dividend_yield is None
        # float_shares is constant & OK to always populate
        assert r.float_shares == 215_000_000


def test_fetch_daily_latest_row_has_info_fields(mock_yfinance):
    rows = yfad.fetch_daily("HIMS", "US", date(2026, 4, 20), date(2026, 4, 24))
    latest = rows[-1]
    assert latest.date == "2026-04-24"
    assert latest.pe_ttm == 45.3
    assert latest.pe_forward == 38.1
    assert latest.pb == 12.5
    assert latest.ps == 8.2
    assert latest.peg == 1.8
    assert latest.market_cap == 7_800_000_000
    assert latest.shares_outstanding == 220_000_000
    assert latest.float_shares == 215_000_000
    assert latest.high_52w == 42.50
    assert latest.low_52w == 12.30
    # dividendYield 0.0 → still 0.0%
    assert latest.dividend_yield == 0.0


def test_fetch_daily_turnover_rate_formula(mock_yfinance):
    """turnover = volume / float_shares * 100 on every row with both present."""
    rows = yfad.fetch_daily("HIMS", "US", date(2026, 4, 20), date(2026, 4, 24))
    for r in rows:
        expected = r.volume / 215_000_000 * 100.0
        assert r.turnover_rate == pytest.approx(expected)


def test_fetch_daily_float_market_cap_on_latest(mock_yfinance):
    rows = yfad.fetch_daily("HIMS", "US", date(2026, 4, 20), date(2026, 4, 24))
    latest = rows[-1]
    assert latest.float_market_cap == pytest.approx(215_000_000 * 36.25)


def test_fetch_daily_dividend_yield_percent_conversion(monkeypatch, mock_yfinance):
    """yfinance dividendYield is a decimal (0.03 = 3%); adapter multiplies by 100."""
    import yfinance as yf
    real_ticker = yf.Ticker

    class _Ticker(real_ticker):
        @property
        def info(self):
            base = super().info
            return {**base, "dividendYield": 0.025}  # 2.5%

    monkeypatch.setattr(yf, "Ticker", _Ticker)
    rows = yfad.fetch_daily("HIMS", "US", date(2026, 4, 20), date(2026, 4, 24))
    assert rows[-1].dividend_yield == pytest.approx(2.5)


def test_fetch_daily_upstream_error(monkeypatch, mock_yfinance):
    import yfinance as yf
    class _Broken:
        def __init__(self, _): pass
        def history(self, **_kw):
            raise ConnectionError("429")
        @property
        def info(self):
            return {}
    monkeypatch.setattr(yf, "Ticker", _Broken)
    with pytest.raises(AdapterError) as exc:
        yfad.fetch_daily("HIMS", "US", date(2026, 4, 20), date(2026, 4, 24))
    assert "HIMS" in str(exc.value)


def test_fetch_daily_empty_returns_empty(monkeypatch, mock_yfinance):
    import yfinance as yf
    class _Empty:
        def __init__(self, _): pass
        def history(self, **_kw):
            return pd.DataFrame()
        @property
        def info(self):
            return {}
    monkeypatch.setattr(yf, "Ticker", _Empty)
    assert yfad.fetch_daily("HIMS", "US", date(2026, 4, 20), date(2026, 4, 24)) == []


# ---------- fetch_intraday_today ----------


def test_fetch_intraday_returns_hhmm_price_volume(mock_yfinance):
    bars = yfad.fetch_intraday_today("HIMS", "US")
    assert len(bars) == 3
    assert bars[0] == ("09:30", 36.05, 15000)


def test_fetch_intraday_error_raises(monkeypatch, mock_yfinance):
    import yfinance as yf
    class _Broken:
        def __init__(self, _): pass
        def history(self, **_kw):
            raise TimeoutError("x")
    monkeypatch.setattr(yf, "Ticker", _Broken)
    with pytest.raises(AdapterError):
        yfad.fetch_intraday_today("HIMS", "US")


# ---------- fetch_snapshot ----------


def test_fetch_snapshot_reads_fast_info_and_info(mock_yfinance):
    q = yfad.fetch_snapshot("HIMS", "US")
    assert q.ticker == "HIMS"
    assert q.close == 36.25
    assert q.open == 36.00
    assert q.volume == 4_800_000
    assert q.pe_ttm == 45.3
    assert q.market_cap == 7_800_000_000
    assert q.high_52w == 42.50
    assert q.turnover_rate == pytest.approx(4_800_000 / 215_000_000 * 100.0)


def test_fetch_snapshot_error(monkeypatch, mock_yfinance):
    import yfinance as yf
    class _Broken:
        def __init__(self, _): pass
        @property
        def fast_info(self):
            raise RuntimeError("down")
        @property
        def info(self):
            return {}
    monkeypatch.setattr(yf, "Ticker", _Broken)
    with pytest.raises(AdapterError):
        yfad.fetch_snapshot("HIMS", "US")


# ---------- HKEX support (queries .HK, stores bare code + HKEX market) ----------


def _hk_ticker_factory(seen: list[str]):
    """Return a fake yf.Ticker that records the symbol it was constructed with."""
    class _HKTicker:
        def __init__(self, symbol):
            seen.append(symbol)
            self.symbol = symbol

        @property
        def info(self):
            return {
                "trailingPE": 154.35,
                "priceToSalesTrailing12Months": 11.08,
                "priceToBook": 6.1,
                "marketCap": 144_580_870_144,
                "sharesOutstanding": 1_600_000_000,
                "fiftyTwoWeekHigh": 90.0,
                "fiftyTwoWeekLow": 30.0,
                "currency": "HKD",
            }

        @property
        def fast_info(self):
            return {"last_price": 83.35, "open": 82.0, "day_high": 84.0,
                    "day_low": 81.5, "last_volume": 5_000_000}

        def history(self, period=None, start=None, end=None, interval="1d",
                    auto_adjust=False):
            idx = pd.to_datetime(["2026-05-28", "2026-05-29"])
            return pd.DataFrame(
                {"Open": [82.0, 82.5], "High": [84.0, 84.2], "Low": [81.0, 81.5],
                 "Close": [83.0, 83.35], "Volume": [4_800_000, 5_000_000]},
                index=idx,
            )
    return _HKTicker


def test_fetch_snapshot_hkex_queries_dot_hk_and_keeps_bare_code(monkeypatch):
    import yfinance as yf
    seen: list[str] = []
    monkeypatch.setattr(yf, "Ticker", _hk_ticker_factory(seen))

    q = yfad.fetch_snapshot("01801", "HKEX")
    # queried yfinance with the 4-digit .HK symbol
    assert seen == ["1801.HK"]
    # stored Quote keeps the bare code and the HKEX market
    assert q.ticker == "01801"
    assert q.market == "HKEX"
    assert q.pe_ttm == 154.35
    assert q.ps == 11.08
    assert q.market_cap == 144_580_870_144
    assert q.source == "yfinance"


def test_fetch_daily_hkex_queries_dot_hk_and_keeps_bare_code(monkeypatch):
    import yfinance as yf
    seen: list[str] = []
    monkeypatch.setattr(yf, "Ticker", _hk_ticker_factory(seen))

    rows = yfad.fetch_daily("06160", "HKEX", date(2026, 5, 28), date(2026, 5, 29))
    assert seen == ["6160.HK"]
    assert rows
    assert all(r.ticker == "06160" and r.market == "HKEX" for r in rows)
    # point-in-time fields land on the latest row
    assert rows[-1].pe_ttm == 154.35
    assert rows[-1].ps == 11.08

"""Tests for app.io.adapters.akshare_adapter.

Uses the ``mock_akshare`` conftest fixture to replace the real Sina +
eastmoney-data-center endpoints with CSV fixtures. The adapter uses:

  - ``stock_zh_a_daily``  (sina)      → OHLCV + turnover ratio
  - ``stock_value_em``    (eastmoney) → PE/PB/PS/PEG/market cap history
  - ``stock_zh_a_minute`` (sina)      → intraday
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from app.io.adapters import akshare_adapter as akad
from app.io.adapters.base import AdapterError

FIX_DIR = Path(__file__).parent / "fixtures" / "adapters" / "akshare"


# ---------- fetch_daily ----------


def test_fetch_daily_maps_ohlcv(mock_akshare):
    rows = akad.fetch_daily("600519", "SSE", date(2026, 4, 20), date(2026, 4, 24))
    assert len(rows) == 5
    first = rows[0]
    assert first.ticker == "600519"
    assert first.market == "SSE"
    assert first.date == "2026-04-20"
    assert first.open == 1680.0
    assert first.high == 1695.0
    assert first.low == 1675.0
    assert first.close == 1690.0
    # Sina reports volume in raw shares; no ×100 adjustment
    assert first.volume == 1_800_000
    assert first.amount == pytest.approx(3_042_000_000.0)
    # turnover is ratio in sina (0.001438) → adapter stores percent
    assert first.turnover_rate == pytest.approx(0.1438)


def test_fetch_daily_attaches_valuation_per_day(mock_akshare):
    rows = akad.fetch_daily("600519", "SSE", date(2026, 4, 20), date(2026, 4, 24))
    d20 = next(r for r in rows if r.date == "2026-04-20")
    assert d20.pe_ttm == 20.10
    assert d20.pe_static == 19.50
    assert d20.pb == 8.50
    assert d20.ps == 7.00
    assert d20.peg == 0.85
    assert d20.market_cap == 2123175600000.0
    assert d20.float_market_cap == 2123175600000.0
    assert d20.shares_outstanding == 1256197800


def test_fetch_daily_52w_computed_from_history_on_latest_row(mock_akshare):
    rows = akad.fetch_daily("600519", "SSE", date(2026, 4, 20), date(2026, 4, 24))
    latest = rows[-1]
    assert latest.date == "2026-04-24"
    # Fixture highs: 1695 / 1700 / 1705 / 1708 / 1702.50 → max 1708
    assert latest.high_52w == 1708.0
    # Fixture lows: 1675 / 1688 / 1692 / 1693 / 1685 → min 1675
    assert latest.low_52w == 1675.0
    for r in rows[:-1]:
        assert r.high_52w is None
        assert r.low_52w is None


def test_fetch_daily_uses_outstanding_share_fallback(mock_akshare, monkeypatch):
    """If value_em is missing that date, float_shares falls back to sina's outstanding_share."""
    import akshare as ak
    monkeypatch.setattr(ak, "stock_value_em", lambda symbol: pd.DataFrame())
    rows = akad.fetch_daily("600519", "SSE", date(2026, 4, 20), date(2026, 4, 24))
    for r in rows:
        assert r.float_shares == 1252269950
        # PE/PB None without value_em
        assert r.pe_ttm is None


def test_fetch_daily_bse_uses_bj_prefix(mock_akshare, monkeypatch):
    """BSE market should call sina with bj-prefixed ticker."""
    captured: list = []

    def _daily(symbol, start_date, end_date, adjust):
        captured.append(symbol)
        return pd.DataFrame()

    import akshare as ak
    monkeypatch.setattr(ak, "stock_zh_a_daily", _daily)
    akad.fetch_daily("920118", "BSE", date(2026, 4, 20), date(2026, 4, 24))
    assert captured == ["bj920118"]


def test_fetch_daily_unsupported_market_raises(mock_akshare):
    with pytest.raises(AdapterError) as exc:
        akad.fetch_daily("0700", "HKEX", date(2026, 4, 20), date(2026, 4, 24))
    assert "HKEX" in str(exc.value)


def test_fetch_daily_upstream_error_raises_adapter_error(monkeypatch, mock_akshare):
    import akshare as ak
    def _boom(**_kw):
        raise ConnectionError("429 too many requests")
    monkeypatch.setattr(ak, "stock_zh_a_daily", _boom)
    with pytest.raises(AdapterError) as exc:
        akad.fetch_daily("600519", "SSE", date(2026, 4, 20), date(2026, 4, 24))
    assert "600519" in str(exc.value)
    assert "ConnectionError" in str(exc.value)


def test_fetch_daily_empty_returns_empty(monkeypatch, mock_akshare):
    import akshare as ak
    monkeypatch.setattr(ak, "stock_zh_a_daily", lambda **_kw: pd.DataFrame())
    assert akad.fetch_daily("600519", "SSE", date(2026, 4, 20), date(2026, 4, 24)) == []


# ---------- fetch_intraday_today ----------


def test_fetch_intraday_picks_latest_session(mock_akshare):
    """Fixture has bars on 2026-04-24 and 2026-04-25 — adapter returns only
    the most-recent date present. No dependency on system clock: on weekends
    we want the last trading day, not 'today'."""
    bars = akad.fetch_intraday_today("600519", "SSE")
    # Fixture: 2 bars on 2026-04-24, 3 bars on 2026-04-25 → keep the 3.
    assert len(bars) == 3
    assert bars[0] == ("09:30", 1697.5, 5500)


def test_fetch_intraday_error_raises(monkeypatch, mock_akshare):
    import akshare as ak
    monkeypatch.setattr(
        ak, "stock_zh_a_minute",
        lambda **_kw: (_ for _ in ()).throw(TimeoutError("nope")),
    )
    with pytest.raises(AdapterError) as exc:
        akad.fetch_intraday_today("600519", "SSE")
    assert "600519" in str(exc.value)


def test_fetch_intraday_empty_returns_empty(monkeypatch, mock_akshare):
    import akshare as ak
    monkeypatch.setattr(ak, "stock_zh_a_minute", lambda **_kw: pd.DataFrame())
    assert akad.fetch_intraday_today("600519", "SSE") == []


# ---------- fetch_snapshot ----------


def test_fetch_snapshot_returns_latest_daily_row(mock_akshare, monkeypatch):
    # EOD date == today → no fallback needed
    class _FakeDate(date):
        @classmethod
        def today(cls):
            return date(2026, 4, 24)

    monkeypatch.setattr(akad, "date", _FakeDate)
    q = akad.fetch_snapshot("600519", "SSE")
    assert q.ticker == "600519"
    assert q.date == "2026-04-24"
    assert q.close == 1698.50
    assert q.high_52w == 1708.0
    assert q.source == "akshare"


def test_fetch_snapshot_no_data_raises(monkeypatch, mock_akshare):
    import akshare as ak
    monkeypatch.setattr(ak, "stock_zh_a_daily", lambda **_kw: pd.DataFrame())
    with pytest.raises(AdapterError) as exc:
        akad.fetch_snapshot("999999", "SSE")
    assert "999999" in str(exc.value)


def test_fetch_snapshot_falls_back_to_intraday_when_eod_is_stale(mock_akshare, monkeypatch):
    """When EOD last row < today and minute feed has today's bars, return
    synthesized intraday Quote tagged source='akshare-intraday'."""
    import akshare as ak
    today_val = date(2026, 4, 27)

    class _FakeDate(date):
        @classmethod
        def today(cls):
            return today_val

    monkeypatch.setattr(akad, "date", _FakeDate)
    # Swap minute fixture to one with today's date
    def _minute_today(symbol, period, adjust):
        return pd.read_csv(FIX_DIR / "minute_sh600519_today.csv")
    monkeypatch.setattr(ak, "stock_zh_a_minute", _minute_today)

    q = akad.fetch_snapshot("600519", "SSE")
    assert q.date == "2026-04-27"
    assert q.source == "akshare-intraday"
    # close = last bar close
    assert q.close == 1710.0
    # high = max of bar closes, low = min of bar closes
    assert q.high == 1710.0
    assert q.low == pytest.approx(1706.5)
    # volume = sum of all bars
    assert q.volume == 6200 + 5800 + 5100
    # fundamentals carried forward from last EOD row (2026-04-24)
    assert q.pe_ttm is not None
    assert q.pb is not None


def test_fetch_snapshot_falls_back_to_eod_when_minute_feed_not_today(mock_akshare, monkeypatch):
    """When minute feed's latest day != today (holiday/weekend), return last EOD row."""
    today_val = date(2026, 4, 27)

    class _FakeDate(date):
        @classmethod
        def today(cls):
            return today_val

    monkeypatch.setattr(akad, "date", _FakeDate)
    # Default mock_akshare minute fixture has 2026-04-25 as latest — not today
    q = akad.fetch_snapshot("600519", "SSE")
    assert q.date == "2026-04-24"
    assert q.source == "akshare"


def test_fetch_snapshot_falls_back_to_eod_when_minute_feed_fails(mock_akshare, monkeypatch):
    """When minute feed raises, gracefully return last EOD row."""
    import akshare as ak
    today_val = date(2026, 4, 27)

    class _FakeDate(date):
        @classmethod
        def today(cls):
            return today_val

    monkeypatch.setattr(akad, "date", _FakeDate)
    monkeypatch.setattr(ak, "stock_zh_a_minute", lambda **_kw: (_ for _ in ()).throw(TimeoutError("down")))
    q = akad.fetch_snapshot("600519", "SSE")
    assert q.date == "2026-04-24"
    assert q.source == "akshare"

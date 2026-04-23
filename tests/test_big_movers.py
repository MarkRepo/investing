"""Tests for prices.big_movers (single-day ±15% alert, DESIGN §3.8)."""
from datetime import date, timedelta

import pytest

from app import config as cfg
from app.io import prices as prices_io


@pytest.fixture
def base(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cfg, "FINANCIALS_DB", tmp_path / "data" / "financials.db")
    return tmp_path


def test_big_movers_empty(base):
    assert prices_io.big_movers(base=base) == []


def test_daily_move_pct_requires_two_closes(base):
    prices_io.upsert_close(ticker="AAA", close=100.0, d=date(2026, 4, 22), base=base)
    assert prices_io.daily_move_pct("AAA", base=base) is None


def test_daily_move_pct_computes(base):
    prices_io.upsert_close(ticker="AAA", close=100.0, d=date(2026, 4, 21), base=base)
    prices_io.upsert_close(ticker="AAA", close=115.0, d=date(2026, 4, 22), base=base)
    res = prices_io.daily_move_pct("AAA", base=base)
    assert res is not None
    pct, latest, prev = res
    assert pct == pytest.approx(15.0)
    assert latest == "2026-04-22"
    assert prev == "2026-04-21"


def test_big_movers_flags_above_threshold(base):
    prices_io.upsert_close(ticker="UP", close=100.0, d=date(2026, 4, 21), base=base)
    prices_io.upsert_close(ticker="UP", close=120.0, d=date(2026, 4, 22), base=base)  # +20%
    prices_io.upsert_close(ticker="DOWN", close=100.0, d=date(2026, 4, 21), base=base)
    prices_io.upsert_close(ticker="DOWN", close=82.0, d=date(2026, 4, 22), base=base)  # -18%
    prices_io.upsert_close(ticker="FLAT", close=100.0, d=date(2026, 4, 21), base=base)
    prices_io.upsert_close(ticker="FLAT", close=103.0, d=date(2026, 4, 22), base=base)  # +3% (below)
    movers = prices_io.big_movers(threshold_pct=15.0, base=base)
    tickers = {m["ticker"] for m in movers}
    assert tickers == {"UP", "DOWN"}
    # Sorted by absolute move
    assert movers[0]["ticker"] == "UP"


def test_big_movers_threshold_respected(base):
    prices_io.upsert_close(ticker="X", close=100.0, d=date(2026, 4, 21), base=base)
    prices_io.upsert_close(ticker="X", close=110.0, d=date(2026, 4, 22), base=base)  # +10%
    assert prices_io.big_movers(threshold_pct=15.0, base=base) == []
    assert prices_io.big_movers(threshold_pct=5.0, base=base)[0]["ticker"] == "X"

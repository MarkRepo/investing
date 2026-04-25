"""Tests for app.io.quotes read/write + compat shims."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app.io import financials as fin_io
from app.io import quotes as quotes_io
from app.io.adapters.base import Quote


def _make_quote(
    ticker: str = "TEST",
    date: str = "2026-04-25",
    market: str = "SSE",
    close: float = 100.0,
    volume: int | None = 10000,
    **over,
) -> Quote:
    base = dict(
        ticker=ticker, date=date, market=market,
        open=close - 1, high=close + 1, low=close - 2, close=close,
        volume=volume, amount=(volume * close) if volume else None,
        turnover_rate=0.1,
        pe_ttm=20.0, pe_static=None, pe_forward=None,
        pb=3.0, ps=None, peg=None,
        dividend_yield=2.5,
        market_cap=1e10, float_market_cap=1e10,
        shares_outstanding=1e8, float_shares=1e8,
        high_52w=120.0, low_52w=80.0,
        source="test", fetched_at="2026-04-25T16:30:00",
    )
    base.update(over)
    return Quote(**base)


def _insert_raw(
    base: Path,
    ticker: str,
    date: str,
    market: str = "SSE",
    close: float = 100.0,
    volume: int | None = None,
):
    conn = fin_io.connect(base=base)
    try:
        conn.execute(
            """
            INSERT INTO quotes_daily (ticker, date, market, close, volume, source, fetched_at)
            VALUES (?, ?, ?, ?, ?, 'test', ?)
            """,
            (ticker, date, market, close, volume, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


# ---------- upsert ----------


def test_upsert_roundtrip_all_fields(tmp_path: Path):
    q = _make_quote()
    quotes_io.upsert(q, base=tmp_path)

    got = quotes_io.latest_for("TEST", base=tmp_path)
    assert got is not None
    assert got["ticker"] == "TEST"
    assert got["date"] == "2026-04-25"
    assert got["market"] == "SSE"
    assert got["close"] == 100.0
    assert got["open"] == 99.0
    assert got["volume"] == 10000
    assert got["turnover_rate"] == 0.1
    assert got["pe_ttm"] == 20.0
    assert got["pb"] == 3.0
    assert got["dividend_yield"] == 2.5
    assert got["high_52w"] == 120.0
    assert got["source"] == "test"


def test_upsert_idempotent_and_overwrites(tmp_path: Path):
    quotes_io.upsert(_make_quote(close=100.0), base=tmp_path)
    quotes_io.upsert(_make_quote(close=105.0, pe_ttm=25.0), base=tmp_path)

    got = quotes_io.latest_for("TEST", base=tmp_path)
    assert got["close"] == 105.0
    assert got["pe_ttm"] == 25.0


def test_upsert_sets_volume_ratio_5d_null_when_fewer_than_5_history(tmp_path: Path):
    # 4 prior rows with volume → still < 5 required → ratio = None
    for i, d in enumerate(["2026-04-19", "2026-04-20", "2026-04-21", "2026-04-22"]):
        _insert_raw(tmp_path, "TEST", d, volume=1000 + i)

    quotes_io.upsert(_make_quote(date="2026-04-25", volume=2000), base=tmp_path)
    got = quotes_io.latest_for("TEST", base=tmp_path)
    assert got["volume_ratio_5d"] is None


def test_upsert_sets_volume_ratio_5d_when_5_history(tmp_path: Path):
    for i, d in enumerate(["2026-04-18", "2026-04-19", "2026-04-20", "2026-04-21", "2026-04-22"]):
        _insert_raw(tmp_path, "TEST", d, volume=1000)  # avg = 1000

    quotes_io.upsert(_make_quote(date="2026-04-25", volume=2500), base=tmp_path)
    got = quotes_io.latest_for("TEST", base=tmp_path)
    assert got["volume_ratio_5d"] == pytest.approx(2.5)


def test_upsert_volume_ratio_null_when_volume_is_none(tmp_path: Path):
    for i, d in enumerate(["2026-04-18", "2026-04-19", "2026-04-20", "2026-04-21", "2026-04-22"]):
        _insert_raw(tmp_path, "TEST", d, volume=1000)

    quotes_io.upsert(_make_quote(date="2026-04-25", volume=None), base=tmp_path)
    got = quotes_io.latest_for("TEST", base=tmp_path)
    assert got["volume_ratio_5d"] is None


def test_upsert_volume_ratio_skips_null_volumes_in_history(tmp_path: Path):
    """Only rows with volume IS NOT NULL count toward the 5-session average."""
    # 4 rows with volume + 1 row with NULL volume = 4 qualifying → ratio None
    _insert_raw(tmp_path, "TEST", "2026-04-18", volume=None)
    for d, v in [
        ("2026-04-19", 1000), ("2026-04-20", 1000),
        ("2026-04-21", 1000), ("2026-04-22", 1000),
    ]:
        _insert_raw(tmp_path, "TEST", d, volume=v)

    quotes_io.upsert(_make_quote(date="2026-04-25", volume=2000), base=tmp_path)
    got = quotes_io.latest_for("TEST", base=tmp_path)
    assert got["volume_ratio_5d"] is None


# ---------- reads ----------


def test_last_date_for_empty(tmp_path: Path):
    assert quotes_io.last_date_for("TEST", base=tmp_path) is None


def test_last_date_for_max(tmp_path: Path):
    _insert_raw(tmp_path, "TEST", "2026-04-20")
    _insert_raw(tmp_path, "TEST", "2026-04-23")
    _insert_raw(tmp_path, "TEST", "2026-04-21")
    assert quotes_io.last_date_for("TEST", base=tmp_path) == "2026-04-23"


def test_latest_for_and_second_latest_for(tmp_path: Path):
    _insert_raw(tmp_path, "TEST", "2026-04-20", close=100.0)
    _insert_raw(tmp_path, "TEST", "2026-04-22", close=110.0)
    _insert_raw(tmp_path, "TEST", "2026-04-21", close=105.0)

    latest = quotes_io.latest_for("TEST", base=tmp_path)
    prev = quotes_io.second_latest_for("TEST", base=tmp_path)
    assert latest["date"] == "2026-04-22" and latest["close"] == 110.0
    assert prev["date"] == "2026-04-21" and prev["close"] == 105.0


def test_latest_for_missing_returns_none(tmp_path: Path):
    assert quotes_io.latest_for("NOPE", base=tmp_path) is None
    assert quotes_io.second_latest_for("NOPE", base=tmp_path) is None


def test_history_for_returns_ascending(tmp_path: Path):
    _insert_raw(tmp_path, "TEST", "2026-04-22", close=110.0)
    _insert_raw(tmp_path, "TEST", "2026-04-20", close=100.0)
    _insert_raw(tmp_path, "TEST", "2026-04-21", close=105.0)

    h = quotes_io.history_for("TEST", base=tmp_path)
    assert [r["date"] for r in h] == ["2026-04-20", "2026-04-21", "2026-04-22"]
    assert [r["close"] for r in h] == [100.0, 105.0, 110.0]


def test_history_for_respects_limit(tmp_path: Path):
    for d in ["2026-04-19", "2026-04-20", "2026-04-21", "2026-04-22"]:
        _insert_raw(tmp_path, "TEST", d)

    h = quotes_io.history_for("TEST", limit=2, base=tmp_path)
    # limit applies BEFORE reverse → returns last 2 ascending
    assert [r["date"] for r in h] == ["2026-04-21", "2026-04-22"]


# ---------- compat shims ----------


def test_latest_price_for(tmp_path: Path):
    assert quotes_io.latest_price_for("NOPE", base=tmp_path) is None
    _insert_raw(tmp_path, "TEST", "2026-04-22", close=99.5)
    assert quotes_io.latest_price_for("TEST", base=tmp_path) == ("2026-04-22", 99.5)


def test_latest_prices_map(tmp_path: Path):
    _insert_raw(tmp_path, "A", "2026-04-21", close=10.0)
    _insert_raw(tmp_path, "A", "2026-04-22", close=11.0)
    _insert_raw(tmp_path, "B", "2026-04-22", close=20.0)

    m = quotes_io.latest_prices_map(base=tmp_path)
    assert m == {"A": ("2026-04-22", 11.0), "B": ("2026-04-22", 20.0)}


def test_daily_move_pct_requires_two_rows(tmp_path: Path):
    assert quotes_io.daily_move_pct("NOPE", base=tmp_path) is None
    _insert_raw(tmp_path, "TEST", "2026-04-22", close=100.0)
    assert quotes_io.daily_move_pct("TEST", base=tmp_path) is None


def test_daily_move_pct_up_and_down(tmp_path: Path):
    _insert_raw(tmp_path, "TEST", "2026-04-21", close=100.0)
    _insert_raw(tmp_path, "TEST", "2026-04-22", close=115.0)
    pct, latest, prev = quotes_io.daily_move_pct("TEST", base=tmp_path)
    assert pct == pytest.approx(15.0)
    assert latest == "2026-04-22"
    assert prev == "2026-04-21"


def test_daily_move_pct_guards_divide_by_zero(tmp_path: Path):
    _insert_raw(tmp_path, "TEST", "2026-04-21", close=0.0)
    _insert_raw(tmp_path, "TEST", "2026-04-22", close=10.0)
    assert quotes_io.daily_move_pct("TEST", base=tmp_path) is None


def test_big_movers_filters_and_sorts(tmp_path: Path):
    _insert_raw(tmp_path, "UP", "2026-04-21", close=100.0)
    _insert_raw(tmp_path, "UP", "2026-04-22", close=120.0)   # +20%
    _insert_raw(tmp_path, "DOWN", "2026-04-21", close=100.0)
    _insert_raw(tmp_path, "DOWN", "2026-04-22", close=82.0)  # -18%
    _insert_raw(tmp_path, "FLAT", "2026-04-21", close=100.0)
    _insert_raw(tmp_path, "FLAT", "2026-04-22", close=103.0)  # +3% below 15

    movers = quotes_io.big_movers(threshold_pct=15.0, base=tmp_path)
    assert [m["ticker"] for m in movers] == ["UP", "DOWN"]  # sorted by |pct| desc
    assert movers[0]["pct"] == pytest.approx(20.0)
    assert movers[1]["pct"] == pytest.approx(-18.0)


def test_big_movers_empty_on_empty_db(tmp_path: Path):
    assert quotes_io.big_movers(base=tmp_path) == []


def test_big_movers_threshold_applied(tmp_path: Path):
    _insert_raw(tmp_path, "X", "2026-04-21", close=100.0)
    _insert_raw(tmp_path, "X", "2026-04-22", close=110.0)
    assert quotes_io.big_movers(threshold_pct=15.0, base=tmp_path) == []
    r = quotes_io.big_movers(threshold_pct=5.0, base=tmp_path)
    assert len(r) == 1 and r[0]["ticker"] == "X"


def test_list_distinct_tickers(tmp_path: Path):
    assert quotes_io.list_distinct_tickers(base=tmp_path) == []
    _insert_raw(tmp_path, "B", "2026-04-22")
    _insert_raw(tmp_path, "A", "2026-04-22")
    _insert_raw(tmp_path, "A", "2026-04-21")
    assert quotes_io.list_distinct_tickers(base=tmp_path) == ["A", "B"]

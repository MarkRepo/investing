"""Tests for app.io.quotes error-tracking + freshness."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from app.io import financials as fin_io
from app.io import quotes as quotes_io


def _insert_raw_quote(base: Path, ticker: str, date_iso: str, market: str = "SSE"):
    conn = fin_io.connect(base=base)
    try:
        conn.execute(
            "INSERT INTO quotes_daily (ticker, date, market, close, source, fetched_at) "
            "VALUES (?, ?, ?, ?, 'test', ?)",
            (ticker, date_iso, market, 100.0, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_error(base: Path, ticker: str, market: str, attempted_at: str,
                  phase: str = "eod", error: str = "boom", resolved_at=None):
    source = "yfinance" if market == "US" else "akshare"
    conn = fin_io.connect(base=base)
    try:
        conn.execute(
            """
            INSERT INTO quotes_fetch_errors
                (ticker, market, attempted_at, source, phase, error, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ticker, market, attempted_at, source, phase, error, resolved_at),
        )
        conn.commit()
    finally:
        conn.close()


# ---------- record_error / mark_errors_resolved / unresolved_fetch_errors ----------


def test_record_error_writes_row_with_derived_source(tmp_path: Path):
    quotes_io.record_error("600519", "SSE", phase="eod", error="429", base=tmp_path)
    quotes_io.record_error("AAPL", "US", phase="eod", error="timeout", base=tmp_path)

    conn = fin_io.connect(base=tmp_path)
    try:
        rows = conn.execute(
            "SELECT ticker, market, source, phase, error, resolved_at FROM quotes_fetch_errors"
        ).fetchall()
    finally:
        conn.close()
    by_ticker = {r["ticker"]: dict(r) for r in rows}
    assert by_ticker["600519"]["source"] == "akshare"
    assert by_ticker["AAPL"]["source"] == "yfinance"
    assert all(r["resolved_at"] is None for r in rows)


def test_mark_errors_resolved_flips_unresolved_only(tmp_path: Path):
    quotes_io.record_error("A", "SSE", phase="eod", error="x", base=tmp_path)
    quotes_io.record_error("A", "SSE", phase="eod", error="y", base=tmp_path)
    quotes_io.record_error("B", "SSE", phase="eod", error="z", base=tmp_path)  # other ticker

    n = quotes_io.mark_errors_resolved("A", base=tmp_path)
    assert n == 2

    # second call is a no-op
    assert quotes_io.mark_errors_resolved("A", base=tmp_path) == 0

    # B still unresolved
    unresolved = quotes_io.unresolved_fetch_errors(base=tmp_path)
    assert [r["ticker"] for r in unresolved] == ["B"]


def test_unresolved_fetch_errors_aggregates_per_ticker(tmp_path: Path):
    t1 = "2026-04-20T10:00:00"
    t2 = "2026-04-22T10:00:00"
    t3 = "2026-04-24T10:00:00"
    _insert_error(tmp_path, "A", "SSE", t1, phase="eod", error="old err")
    _insert_error(tmp_path, "A", "SSE", t2, phase="snapshot", error="mid err")
    _insert_error(tmp_path, "A", "SSE", t3, phase="eod", error="latest err")
    _insert_error(tmp_path, "B", "US", "2026-04-23T10:00:00", phase="eod", error="b err")

    rows = quotes_io.unresolved_fetch_errors(base=tmp_path)
    assert len(rows) == 2
    by_ticker = {r["ticker"]: r for r in rows}
    assert by_ticker["A"]["count"] == 3
    assert by_ticker["A"]["attempted_at"] == t3
    assert by_ticker["B"]["source"] == "yfinance"


def test_unresolved_fetch_errors_empty(tmp_path: Path):
    assert quotes_io.unresolved_fetch_errors(base=tmp_path) == []


def test_unresolved_fetch_errors_excludes_resolved(tmp_path: Path):
    _insert_error(tmp_path, "A", "SSE", "2026-04-20T10:00:00",
                  resolved_at="2026-04-21T10:00:00")
    assert quotes_io.unresolved_fetch_errors(base=tmp_path) == []


# ---------- freshness ----------


TODAY = date(2026, 4, 25)


def test_freshness_no_data_is_red(tmp_path: Path):
    f = quotes_io.freshness("NOPE", base=tmp_path, today=TODAY)
    assert f["status"] == "red"
    assert f["last_date"] is None
    assert f["days_since"] is None
    assert f["last_error"] is None


def test_freshness_fresh_no_error_is_green(tmp_path: Path):
    _insert_raw_quote(tmp_path, "TEST", "2026-04-24")  # 1 day old
    f = quotes_io.freshness("TEST", base=tmp_path, today=TODAY)
    assert f["status"] == "green"
    assert f["days_since"] == 1


def test_freshness_3_days_no_error_is_green(tmp_path: Path):
    _insert_raw_quote(tmp_path, "TEST", "2026-04-22")  # 3 days
    f = quotes_io.freshness("TEST", base=tmp_path, today=TODAY)
    assert f["status"] == "green"


def test_freshness_4_days_no_error_is_yellow(tmp_path: Path):
    _insert_raw_quote(tmp_path, "TEST", "2026-04-21")  # 4 days
    f = quotes_io.freshness("TEST", base=tmp_path, today=TODAY)
    assert f["status"] == "yellow"


def test_freshness_7_days_no_error_is_red(tmp_path: Path):
    _insert_raw_quote(tmp_path, "TEST", "2026-04-18")  # 7 days
    f = quotes_io.freshness("TEST", base=tmp_path, today=TODAY)
    assert f["status"] == "red"


def test_freshness_fresh_data_with_recent_error_is_yellow(tmp_path: Path):
    """Data is 1 day old but there's an unresolved error from yesterday."""
    _insert_raw_quote(tmp_path, "TEST", "2026-04-24")
    _insert_error(tmp_path, "TEST", "SSE", "2026-04-24T12:00:00")  # 1 day old err
    f = quotes_io.freshness("TEST", base=tmp_path, today=TODAY)
    assert f["status"] == "yellow"
    assert f["last_error"]["error"] == "boom"


def test_freshness_error_3_days_old_is_red(tmp_path: Path):
    _insert_raw_quote(tmp_path, "TEST", "2026-04-24")  # fresh data
    _insert_error(tmp_path, "TEST", "SSE", "2026-04-22T12:00:00")  # 3-day-old err
    f = quotes_io.freshness("TEST", base=tmp_path, today=TODAY)
    assert f["status"] == "red"


def test_freshness_resolved_error_is_ignored(tmp_path: Path):
    _insert_raw_quote(tmp_path, "TEST", "2026-04-24")
    _insert_error(tmp_path, "TEST", "SSE", "2026-04-20T12:00:00",
                  resolved_at="2026-04-21T12:00:00")
    f = quotes_io.freshness("TEST", base=tmp_path, today=TODAY)
    assert f["status"] == "green"
    assert f["last_error"] is None


def test_freshness_picks_latest_unresolved_error(tmp_path: Path):
    _insert_raw_quote(tmp_path, "TEST", "2026-04-24")
    _insert_error(tmp_path, "TEST", "SSE", "2026-04-22T10:00:00", error="old")
    _insert_error(tmp_path, "TEST", "SSE", "2026-04-24T10:00:00", error="new")
    f = quotes_io.freshness("TEST", base=tmp_path, today=TODAY)
    assert f["last_error"]["error"] == "new"

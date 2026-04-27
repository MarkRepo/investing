"""Schema tests for quotes_daily and quotes_fetch_errors tables.

Verifies that app.io.financials.connect() creates the two tables required
by the quotes subsystem without touching existing tables.
"""
from pathlib import Path

from app.io import financials as fin


QUOTES_DAILY_COLUMNS = {
    "ticker", "date", "market",
    "open", "high", "low", "close",
    "volume", "amount",
    "turnover_rate", "volume_ratio_5d",
    "pe_ttm", "pe_static", "pe_forward",
    "pb", "ps", "peg",
    "dividend_yield",
    "market_cap", "float_market_cap",
    "shares_outstanding", "float_shares",
    "high_52w", "low_52w",
    "source", "fetched_at",
}

FETCH_ERRORS_COLUMNS = {
    "id", "ticker", "market", "attempted_at",
    "source", "phase", "error", "resolved_at",
}


def _table_info(conn, table: str) -> list[dict]:
    return [dict(r) for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _has_table(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _has_index(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def test_connect_creates_quotes_daily(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        assert _has_table(conn, "quotes_daily")
        info = _table_info(conn, "quotes_daily")
        cols = {c["name"] for c in info}
        assert cols == QUOTES_DAILY_COLUMNS, f"unexpected columns: {cols ^ QUOTES_DAILY_COLUMNS}"

        # PK is (ticker, date) — both columns have pk > 0
        pk_cols = {c["name"] for c in info if c["pk"] > 0}
        assert pk_cols == {"ticker", "date"}

        # close NOT NULL (business invariant; the rest are nullable)
        notnull = {c["name"] for c in info if c["notnull"]}
        assert "close" in notnull
        assert "ticker" in notnull
        assert "date" in notnull
        assert "market" in notnull
    finally:
        conn.close()


def test_connect_creates_quotes_fetch_errors(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        assert _has_table(conn, "quotes_fetch_errors")
        info = _table_info(conn, "quotes_fetch_errors")
        cols = {c["name"] for c in info}
        assert cols == FETCH_ERRORS_COLUMNS

        # id is AUTOINCREMENT PK
        pk_cols = [c for c in info if c["pk"] > 0]
        assert len(pk_cols) == 1 and pk_cols[0]["name"] == "id"

        assert _has_index(conn, "idx_fetch_errors_unresolved")
    finally:
        conn.close()


def test_connect_is_idempotent(tmp_path: Path):
    conn1 = fin.connect(base=tmp_path)
    conn1.close()
    # second connect on the same db must not raise
    conn2 = fin.connect(base=tmp_path)
    try:
        assert _has_table(conn2, "quotes_daily")
        assert _has_table(conn2, "quotes_fetch_errors")
    finally:
        conn2.close()


def test_existing_tables_still_exist(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        for name in ("companies", "financials_cn", "financials_us", "ratios", "price_triggers", "benchmark", "prices"):
            assert _has_table(conn, name), f"pre-existing table {name} missing after connect()"
    finally:
        conn.close()


def test_quotes_daily_accepts_minimal_insert(tmp_path: Path):
    """Smoke-check: close + keys are enough; other columns default to NULL."""
    conn = fin.connect(base=tmp_path)
    try:
        conn.execute(
            "INSERT INTO quotes_daily (ticker, date, market, close) VALUES (?, ?, ?, ?)",
            ("TEST", "2026-04-25", "SSE", 100.0),
        )
        conn.commit()
        r = conn.execute(
            "SELECT ticker, date, market, close, open, volume_ratio_5d FROM quotes_daily"
        ).fetchone()
        assert dict(r) == {
            "ticker": "TEST", "date": "2026-04-25", "market": "SSE",
            "close": 100.0, "open": None, "volume_ratio_5d": None,
        }
    finally:
        conn.close()


def test_quotes_daily_pk_conflict(tmp_path: Path):
    """Re-inserting the same (ticker, date) raises IntegrityError (UPSERT handled by io layer)."""
    import sqlite3
    conn = fin.connect(base=tmp_path)
    try:
        conn.execute(
            "INSERT INTO quotes_daily (ticker, date, market, close) VALUES (?, ?, ?, ?)",
            ("TEST", "2026-04-25", "SSE", 100.0),
        )
        conn.commit()
        try:
            conn.execute(
                "INSERT INTO quotes_daily (ticker, date, market, close) VALUES (?, ?, ?, ?)",
                ("TEST", "2026-04-25", "SSE", 101.0),
            )
            raised = False
        except sqlite3.IntegrityError:
            raised = True
        assert raised
    finally:
        conn.close()

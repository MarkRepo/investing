"""Daily quotes IO — reads/writes to ``quotes_daily`` + ``quotes_fetch_errors``.

Adapters produce ``Quote`` instances; this layer owns persistence, computes
``volume_ratio_5d`` from history, and exposes the read APIs used by routes.

Compat shims mirror the old ``app.io.prices`` API (latest_prices_map,
latest_price_for, daily_move_pct, big_movers) so existing callers only need
to swap their import.
"""
from __future__ import annotations

import sqlite3
from datetime import date as date_cls
from datetime import datetime
from pathlib import Path

from app.io import financials as fin_io
from app.io.adapters.base import Quote


# ---------- write ----------


def upsert(
    q: Quote,
    base: Path | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Write one Quote, computing volume_ratio_5d from prior rows."""
    owns = conn is None
    conn = conn or fin_io.connect(base=base)
    try:
        vr5 = _compute_volume_ratio_5d(conn, q.ticker, q.date, q.volume)
        conn.execute(
            """
            INSERT INTO quotes_daily (
                ticker, date, market,
                open, high, low, close,
                volume, amount,
                turnover_rate, volume_ratio_5d,
                pe_ttm, pe_static, pe_forward,
                pb, ps, peg, dividend_yield,
                market_cap, float_market_cap,
                shares_outstanding, float_shares,
                high_52w, low_52w,
                source, fetched_at
            ) VALUES (
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?
            )
            ON CONFLICT(ticker, date) DO UPDATE SET
                market=excluded.market,
                open=excluded.open, high=excluded.high, low=excluded.low, close=excluded.close,
                volume=excluded.volume, amount=excluded.amount,
                turnover_rate=excluded.turnover_rate,
                volume_ratio_5d=excluded.volume_ratio_5d,
                pe_ttm=excluded.pe_ttm, pe_static=excluded.pe_static, pe_forward=excluded.pe_forward,
                pb=excluded.pb, ps=excluded.ps, peg=excluded.peg,
                dividend_yield=excluded.dividend_yield,
                market_cap=excluded.market_cap, float_market_cap=excluded.float_market_cap,
                shares_outstanding=excluded.shares_outstanding, float_shares=excluded.float_shares,
                high_52w=excluded.high_52w, low_52w=excluded.low_52w,
                source=excluded.source, fetched_at=excluded.fetched_at
            """,
            (
                q.ticker, q.date, q.market,
                q.open, q.high, q.low, q.close,
                q.volume, q.amount,
                q.turnover_rate, vr5,
                q.pe_ttm, q.pe_static, q.pe_forward,
                q.pb, q.ps, q.peg, q.dividend_yield,
                q.market_cap, q.float_market_cap,
                q.shares_outstanding, q.float_shares,
                q.high_52w, q.low_52w,
                q.source, q.fetched_at,
            ),
        )
        conn.commit()
    finally:
        if owns:
            conn.close()


def _compute_volume_ratio_5d(
    conn: sqlite3.Connection,
    ticker: str,
    date_iso: str,
    volume: int | None,
) -> float | None:
    """volume / avg(prev 5 sessions with non-null volume). None if <5 prior rows."""
    if volume is None:
        return None
    rows = conn.execute(
        """
        SELECT volume FROM quotes_daily
        WHERE ticker = ? AND date < ? AND volume IS NOT NULL
        ORDER BY date DESC LIMIT 5
        """,
        (ticker, date_iso),
    ).fetchall()
    if len(rows) < 5:
        return None
    avg = sum(r["volume"] for r in rows) / 5
    if avg <= 0:
        return None
    return volume / avg


# ---------- read ----------


def last_date_for(ticker: str, base: Path | None = None) -> str | None:
    """Latest ISO date present for ticker, or None if empty."""
    conn = fin_io.connect(base=base)
    try:
        r = conn.execute(
            "SELECT MAX(date) AS d FROM quotes_daily WHERE ticker = ?",
            (ticker,),
        ).fetchone()
        return r["d"] if r else None
    finally:
        conn.close()


def latest_for(ticker: str, base: Path | None = None) -> dict | None:
    conn = fin_io.connect(base=base)
    try:
        r = conn.execute(
            "SELECT * FROM quotes_daily WHERE ticker = ? ORDER BY date DESC LIMIT 1",
            (ticker,),
        ).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def second_latest_for(ticker: str, base: Path | None = None) -> dict | None:
    conn = fin_io.connect(base=base)
    try:
        r = conn.execute(
            "SELECT * FROM quotes_daily WHERE ticker = ? ORDER BY date DESC LIMIT 1 OFFSET 1",
            (ticker,),
        ).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def history_for(
    ticker: str, limit: int = 252, base: Path | None = None
) -> list[dict]:
    """Return OHLCV rows for the last ``limit`` sessions, ascending by date."""
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute(
            """
            SELECT date, open, high, low, close, volume
            FROM quotes_daily
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (ticker, limit),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]
    finally:
        conn.close()


# ---------- compat shims (old app.io.prices API) ----------


def latest_price_for(
    ticker: str, base: Path | None = None
) -> tuple[str, float] | None:
    r = latest_for(ticker, base=base)
    return (r["date"], r["close"]) if r else None


def latest_prices_map(base: Path | None = None) -> dict[str, tuple[str, float]]:
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute(
            """
            SELECT q.ticker, q.date, q.close
            FROM quotes_daily q
            JOIN (
                SELECT ticker, MAX(date) AS md FROM quotes_daily GROUP BY ticker
            ) m ON q.ticker = m.ticker AND q.date = m.md
            """
        ).fetchall()
        return {r["ticker"]: (r["date"], r["close"]) for r in rows}
    finally:
        conn.close()


def daily_move_pct(
    ticker: str, base: Path | None = None
) -> tuple[float, str, str] | None:
    """Return (pct_change, latest_date, prev_date) or None if <2 rows."""
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute(
            "SELECT date, close FROM quotes_daily WHERE ticker = ? ORDER BY date DESC LIMIT 2",
            (ticker,),
        ).fetchall()
    finally:
        conn.close()
    if len(rows) < 2:
        return None
    latest_d, latest_c = rows[0]["date"], float(rows[0]["close"])
    prev_d, prev_c = rows[1]["date"], float(rows[1]["close"])
    if prev_c <= 0:
        return None
    return (latest_c - prev_c) / prev_c * 100.0, latest_d, prev_d


def list_distinct_tickers(base: Path | None = None) -> list[str]:
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute(
            "SELECT DISTINCT ticker FROM quotes_daily ORDER BY ticker"
        ).fetchall()
        return [r["ticker"] for r in rows]
    finally:
        conn.close()


def big_movers(
    threshold_pct: float = 15.0, base: Path | None = None
) -> list[dict]:
    out: list[dict] = []
    for t in list_distinct_tickers(base=base):
        res = daily_move_pct(t, base=base)
        if res is None:
            continue
        pct, latest_d, prev_d = res
        if abs(pct) >= threshold_pct:
            out.append({
                "ticker": t,
                "pct": pct,
                "latest_date": latest_d,
                "prev_date": prev_d,
            })
    out.sort(key=lambda r: abs(r["pct"]), reverse=True)
    return out


# ---------- errors + freshness ----------


def record_error(
    ticker: str,
    market: str,
    phase: str,
    error: str,
    base: Path | None = None,
    attempted_at: str | None = None,
) -> None:
    """Append an unresolved fetch error row.

    ``phase`` is adapter-facing: "eod" / "snapshot" / "intraday". ``source``
    is derived from market so callers don't have to remember the mapping.
    """
    source = "yfinance" if market == "US" else "akshare"
    conn = fin_io.connect(base=base)
    try:
        conn.execute(
            """
            INSERT INTO quotes_fetch_errors
                (ticker, market, attempted_at, source, phase, error)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                ticker, market,
                attempted_at or datetime.now().isoformat(),
                source, phase, error,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def mark_errors_resolved(
    ticker: str,
    base: Path | None = None,
    resolved_at: str | None = None,
) -> int:
    """Flip all unresolved rows for ticker to resolved. Returns count flipped."""
    conn = fin_io.connect(base=base)
    try:
        cur = conn.execute(
            """
            UPDATE quotes_fetch_errors
            SET resolved_at = ?
            WHERE ticker = ? AND resolved_at IS NULL
            """,
            (resolved_at or datetime.now().isoformat(), ticker),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def unresolved_fetch_errors(base: Path | None = None) -> list[dict]:
    """Return one summary row per ticker with unresolved errors.

    Each row: ``{ticker, market, source, phase, error, attempted_at, count}``
    — ``error`` / ``phase`` / ``source`` / ``market`` are from the most-recent
    attempt for that ticker; ``count`` is how many unresolved rows remain.
    """
    conn = fin_io.connect(base=base)
    try:
        # Grab the most recent unresolved row per ticker, plus count of
        # unresolved rows for that ticker. SQLite's MAX() trick picks the
        # row whose attempted_at matches the MAX, giving us latest attempt.
        rows = conn.execute(
            """
            SELECT ticker, market, source, phase, error,
                   MAX(attempted_at) AS attempted_at,
                   COUNT(*) AS count
            FROM quotes_fetch_errors
            WHERE resolved_at IS NULL
            GROUP BY ticker
            ORDER BY attempted_at DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def freshness(
    ticker: str,
    base: Path | None = None,
    today: date_cls | None = None,
) -> dict:
    """Return a status bundle used by templates.

    Traffic-light rules:
      - no data                         → red
      - latest ≥ 7 days old (no error)  → red
      - unresolved error ≥ 3 days old   → red
      - latest > 3 days old OR error <3d → yellow
      - otherwise                       → green
    """
    today = today or date_cls.today()
    last_d = last_date_for(ticker, base=base)
    if last_d:
        days_since = (today - date_cls.fromisoformat(last_d)).days
    else:
        days_since = None

    conn = fin_io.connect(base=base)
    try:
        err_row = conn.execute(
            """
            SELECT error, attempted_at FROM quotes_fetch_errors
            WHERE ticker = ? AND resolved_at IS NULL
            ORDER BY attempted_at DESC LIMIT 1
            """,
            (ticker,),
        ).fetchone()
    finally:
        conn.close()

    has_err = err_row is not None
    err_age = None
    if has_err:
        err_age = (today - date_cls.fromisoformat(err_row["attempted_at"][:10])).days

    if last_d is None:
        status = "red"
    elif has_err and err_age is not None and err_age >= 3:
        status = "red"
    elif days_since is not None and days_since >= 7:
        status = "red"
    elif not has_err and days_since is not None and days_since <= 3:
        status = "green"
    else:
        status = "yellow"

    return {
        "status": status,
        "last_date": last_d,
        "days_since": days_since,
        "last_error": (
            {"error": err_row["error"], "attempted_at": err_row["attempted_at"]}
            if has_err else None
        ),
    }

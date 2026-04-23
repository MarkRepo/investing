"""Daily closing price entry (manual, no external API).

Rationale: we don't want an automated yfinance/Alpha Vantage dependency for
V1 — pricing is cheap to enter by hand when you own <20 stocks, and keeping
it manual means the system never silently stops working when an API rate-
limits or changes shape. If you want to use yfinance later, add a
``app/io/price_sources/yfinance.py`` that calls ``upsert_close`` — the rest
of the stack doesn't care where the number came from.

Parsing: ``parse_freeform`` accepts a lenient "one line per ticker" format
so you can paste text from anywhere. Whitespace or comma separated, optional
currency symbol.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import date as date_cls
from pathlib import Path
from typing import Iterable

from app.io import financials as fin_io

_LINE_RE = re.compile(
    r"""^\s*
        ([A-Za-z0-9._]+)        # ticker (no dash — avoids ambiguity with negatives)
        [\s,\t]+                # separator
        [$￥¥]?                  # optional currency sign
        (-?\d+(?:\.\d+)?)       # number (signed integer or decimal)
        \s*$""",
    re.VERBOSE,
)


def parse_freeform(text: str) -> tuple[list[tuple[str, float]], list[dict]]:
    """Parse one (ticker, close) pair per line. Returns ``(rows, errors)``.

    Lenient by design: blank lines and comment lines starting with ``#`` are
    skipped. Duplicate tickers in one paste are allowed; last one wins
    (downstream upsert will dedupe by primary key anyway).
    """
    rows: list[tuple[str, float]] = []
    errors: list[dict] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        m = _LINE_RE.match(s)
        if not m:
            errors.append({"line": i, "text": raw, "error": "cannot parse"})
            continue
        ticker = m.group(1).upper()
        try:
            close = float(m.group(2))
        except ValueError:
            errors.append({"line": i, "text": raw, "error": "bad number"})
            continue
        if close <= 0:
            errors.append({"line": i, "text": raw, "error": "price must be > 0"})
            continue
        rows.append((ticker, close))
    return rows, errors


def upsert_close(
    ticker: str,
    close: float,
    d: date_cls,
    conn: sqlite3.Connection | None = None,
    base: Path | None = None,
) -> None:
    owns = conn is None
    conn = conn or fin_io.connect(base=base)
    try:
        conn.execute(
            """
            INSERT INTO prices (ticker, date, close) VALUES (?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET close = excluded.close
            """,
            (ticker.strip().upper(), d.isoformat(), close),
        )
        conn.commit()
    finally:
        if owns:
            conn.close()


def upsert_closes(
    rows: Iterable[tuple[str, float]],
    d: date_cls,
    base: Path | None = None,
) -> int:
    """Batch version. Returns number of rows written."""
    conn = fin_io.connect(base=base)
    try:
        n = 0
        for ticker, close in rows:
            upsert_close(ticker, close, d, conn=conn)
            n += 1
        return n
    finally:
        conn.close()


def latest_price_for(
    ticker: str, base: Path | None = None, conn: sqlite3.Connection | None = None
) -> tuple[str, float] | None:
    """Return (date_iso, close) for the most recent price, or None."""
    owns = conn is None
    conn = conn or fin_io.connect(base=base)
    try:
        row = conn.execute(
            "SELECT date, close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 1",
            (ticker.strip().upper(),),
        ).fetchone()
        if row is None:
            return None
        return row["date"], row["close"]
    finally:
        if owns:
            conn.close()


def latest_prices_map(base: Path | None = None) -> dict[str, tuple[str, float]]:
    """Return ``{ticker: (date, close)}`` with the latest row per ticker."""
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute(
            """
            SELECT p.ticker, p.date, p.close
            FROM prices p
            JOIN (SELECT ticker, MAX(date) AS md FROM prices GROUP BY ticker) m
            ON p.ticker = m.ticker AND p.date = m.md
            """
        ).fetchall()
        return {r["ticker"]: (r["date"], r["close"]) for r in rows}
    finally:
        conn.close()


def history_for(
    ticker: str, base: Path | None = None, limit: int = 30
) -> list[dict]:
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute(
            "SELECT date, close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT ?",
            (ticker.strip().upper(), limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def daily_move_pct(
    ticker: str, base: Path | None = None
) -> tuple[float, str, str] | None:
    """Return (pct_change, latest_date, prev_date) or None if <2 closes exist.

    pct_change is (latest - prev) / prev * 100 — positive = up, negative = down.
    """
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute(
            "SELECT date, close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 2",
            (ticker.upper(),),
        ).fetchall()
    finally:
        conn.close()
    if len(rows) < 2:
        return None
    latest_date = rows[0]["date"]
    latest_close = float(rows[0]["close"])
    prev_date = rows[1]["date"]
    prev_close = float(rows[1]["close"])
    if prev_close <= 0:
        return None
    return (latest_close - prev_close) / prev_close * 100.0, latest_date, prev_date


def big_movers(
    threshold_pct: float = 15.0, base: Path | None = None
) -> list[dict]:
    """Return all distinct tickers whose most recent session moved ≥ threshold.

    Returns ``[{ticker, pct, latest_date, prev_date}]`` sorted by |pct| desc.
    """
    out: list[dict] = []
    for t in list_distinct_tickers(base=base):
        res = daily_move_pct(t, base=base)
        if res is None:
            continue
        pct, latest_date, prev_date = res
        if abs(pct) >= threshold_pct:
            out.append({
                "ticker": t,
                "pct": pct,
                "latest_date": latest_date,
                "prev_date": prev_date,
            })
    out.sort(key=lambda r: abs(r["pct"]), reverse=True)
    return out


def list_distinct_tickers(base: Path | None = None) -> list[str]:
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute("SELECT DISTINCT ticker FROM prices ORDER BY ticker").fetchall()
        return [r["ticker"] for r in rows]
    finally:
        conn.close()

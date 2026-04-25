"""Monthly portfolio performance vs benchmark (DESIGN §V3).

Inputs:
- ``benchmark`` table in SQLite (date, symbol, close) — manually entered
  closes for SPY / CSI300 / etc.
- ``prices`` table for current holdings.
- ``portfolio/positions.md`` for current holdings.

Outputs:
- monthly return series for benchmark
- monthly return series for portfolio (mark-to-market on month-end close)
- cumulative spread (portfolio − benchmark)

Caveats:
- Portfolio returns here are a **snapshot approximation**: we use current
  positions × month-end price, not the accounting-correct time-weighted
  return with contribution/withdrawal flows. Good enough for monthly
  "am I keeping up with SPY" sanity checks; don't report these numbers to
  anyone as official performance.
- Requires enough month-end benchmark closes AND month-end prices to be
  useful. We don't interpolate.
"""
from __future__ import annotations

import calendar
import re
import sqlite3
from datetime import date as date_cls
from pathlib import Path

from app.io import financials as fin_io
from app.io import portfolio as portfolio_io

_LINE_RE = re.compile(
    r"""^\s*
        (\d{4}-\d{2}-\d{2})     # date
        [\s,\t]+
        ([A-Za-z0-9.^=]+)       # symbol (^GSPC, 000300.SS, SPY, etc.)
        [\s,\t]+
        [$￥¥]?
        (\d+(?:\.\d+)?)         # close (must be positive)
        \s*$""",
    re.VERBOSE,
)


def parse_benchmark_freeform(text: str) -> tuple[list[tuple[str, str, float]], list[dict]]:
    """Parse ``date  symbol  close`` per line. Returns ``(rows, errors)``.

    Lenient format (comma/tab/space separators; blank and ``#`` lines skipped).
    Symbols are uppercased. Close must be > 0.
    """
    rows: list[tuple[str, str, float]] = []
    errors: list[dict] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        m = _LINE_RE.match(s)
        if not m:
            errors.append({"line": i, "text": raw, "error": "cannot parse"})
            continue
        d, symbol, close_s = m.group(1), m.group(2).upper(), m.group(3)
        try:
            close = float(close_s)
        except ValueError:
            errors.append({"line": i, "text": raw, "error": "bad number"})
            continue
        if close <= 0:
            errors.append({"line": i, "text": raw, "error": "close must be > 0"})
            continue
        rows.append((d, symbol, close))
    return rows, errors


def upsert_benchmark_closes(
    rows: list[tuple[str, str, float]], base: Path | None = None
) -> int:
    conn = fin_io.connect(base=base)
    try:
        n = 0
        for d, symbol, close in rows:
            conn.execute(
                """
                INSERT INTO benchmark (date, symbol, close) VALUES (?, ?, ?)
                ON CONFLICT(date, symbol) DO UPDATE SET close = excluded.close
                """,
                (d, symbol, close),
            )
            n += 1
        conn.commit()
        return n
    finally:
        conn.close()


def list_benchmark_symbols(base: Path | None = None) -> list[str]:
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute("SELECT DISTINCT symbol FROM benchmark ORDER BY symbol").fetchall()
        return [r["symbol"] for r in rows]
    finally:
        conn.close()


def _month_key(iso: str) -> str:
    return iso[:7]


def _month_end_close(
    conn: sqlite3.Connection, symbol: str, year: int, month: int
) -> tuple[str, float] | None:
    last_day = calendar.monthrange(year, month)[1]
    end = date_cls(year, month, last_day).isoformat()
    start = date_cls(year, month, 1).isoformat()
    row = conn.execute(
        """
        SELECT date, close FROM benchmark
        WHERE symbol = ? AND date >= ? AND date <= ?
        ORDER BY date DESC LIMIT 1
        """,
        (symbol, start, end),
    ).fetchone()
    return (row["date"], row["close"]) if row else None


def _price_month_end_close(
    conn: sqlite3.Connection, ticker: str, year: int, month: int
) -> tuple[str, float] | None:
    last_day = calendar.monthrange(year, month)[1]
    end = date_cls(year, month, last_day).isoformat()
    start = date_cls(year, month, 1).isoformat()
    row = conn.execute(
        """
        SELECT date, close FROM quotes_daily
        WHERE ticker = ? AND date >= ? AND date <= ?
        ORDER BY date DESC LIMIT 1
        """,
        (ticker, start, end),
    ).fetchone()
    return (row["date"], row["close"]) if row else None


def benchmark_monthly(
    symbol: str, base: Path | None = None
) -> list[dict]:
    """Return ``[{month: YYYY-MM, close, ret_mom_pct}, ...]`` sorted ascending.

    ``ret_mom_pct`` is the month-over-month return of the benchmark close.
    First month has ret_mom_pct = None.
    """
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute(
            "SELECT date, close FROM benchmark WHERE symbol = ? ORDER BY date",
            (symbol,),
        ).fetchall()
    finally:
        conn.close()

    by_month: dict[str, tuple[str, float]] = {}
    for r in rows:
        key = _month_key(r["date"])
        prev = by_month.get(key)
        if prev is None or r["date"] > prev[0]:
            by_month[key] = (r["date"], r["close"])

    out = []
    prev_close: float | None = None
    for key in sorted(by_month):
        d, close = by_month[key]
        if prev_close is None or prev_close == 0:
            ret = None
        else:
            ret = (close - prev_close) / prev_close * 100.0
        out.append({"month": key, "date": d, "close": close, "ret_mom_pct": ret})
        prev_close = close
    return out


def portfolio_monthly(base: Path | None = None) -> list[dict]:
    """Month-end mark-to-market of *current* positions.

    NOT true time-weighted return: uses today's shares × month-end close for
    every month. Only as accurate as your position history (if you bought
    halfway through a month, returns before that month are hypothetical).

    Returns ``[{month, mv, ret_mom_pct}, ...]``.
    """
    positions = portfolio_io.read_positions(base=base)
    holdings: list[tuple[str, float]] = []
    for p in positions:
        try:
            shares = float(p.get("shares") or 0)
        except (TypeError, ValueError):
            shares = 0.0
        if shares <= 0:
            continue
        ticker = p.get("ticker", "").strip().upper()
        if ticker:
            holdings.append((ticker, shares))
    if not holdings:
        return []

    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute("SELECT MIN(date) AS a, MAX(date) AS b FROM quotes_daily").fetchone()
        if not rows or not rows["a"]:
            return []
        start = date_cls.fromisoformat(rows["a"])
        end = date_cls.fromisoformat(rows["b"])
        months: list[tuple[int, int]] = []
        y, m = start.year, start.month
        while (y, m) <= (end.year, end.month):
            months.append((y, m))
            m += 1
            if m > 12:
                m = 1
                y += 1

        out = []
        prev_mv: float | None = None
        for y, m in months:
            mv = 0.0
            any_priced = False
            for ticker, shares in holdings:
                px = _price_month_end_close(conn, ticker, y, m)
                if px:
                    mv += shares * px[1]
                    any_priced = True
            if not any_priced:
                continue
            key = f"{y:04d}-{m:02d}"
            if prev_mv is None or prev_mv == 0:
                ret = None
            else:
                ret = (mv - prev_mv) / prev_mv * 100.0
            out.append({"month": key, "mv": mv, "ret_mom_pct": ret})
            prev_mv = mv
        return out
    finally:
        conn.close()


def compare(
    benchmark_symbol: str, base: Path | None = None
) -> dict:
    """Aligned monthly comparison portfolio vs benchmark.

    Returns ``{rows: [...], cum_portfolio_pct, cum_benchmark_pct, spread_pct}``.
    Rows only include months present in BOTH series; spread starts at 0.
    """
    b = {r["month"]: r for r in benchmark_monthly(benchmark_symbol, base=base)}
    p = {r["month"]: r for r in portfolio_monthly(base=base)}
    shared = sorted(set(b) & set(p))
    rows = []
    cum_p = 0.0
    cum_b = 0.0
    for month in shared:
        pr = p[month].get("ret_mom_pct")
        br = b[month].get("ret_mom_pct")
        if pr is not None:
            cum_p = (1 + cum_p / 100) * (1 + pr / 100) * 100 - 100
        if br is not None:
            cum_b = (1 + cum_b / 100) * (1 + br / 100) * 100 - 100
        rows.append({
            "month": month,
            "portfolio_ret_pct": pr,
            "benchmark_ret_pct": br,
            "cum_portfolio_pct": cum_p,
            "cum_benchmark_pct": cum_b,
            "spread_pct": cum_p - cum_b,
        })
    return {
        "rows": rows,
        "cum_portfolio_pct": cum_p,
        "cum_benchmark_pct": cum_b,
        "spread_pct": cum_p - cum_b,
    }

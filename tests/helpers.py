"""Shared test helpers used across multiple suites."""
from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime
from pathlib import Path

from app.io import financials as fin_io


def insert_quote(
    base: Path,
    ticker: str,
    date,
    *,
    market: str = "SSE",
    close: float = 100.0,
    volume: int | None = None,
    source: str = "test",
) -> None:
    """Directly insert one quotes_daily row. Bypasses io.quotes for simplicity.

    ``date`` may be a ``datetime.date`` or an ISO string.
    """
    date_iso = date.isoformat() if isinstance(date, date_cls) else str(date)
    conn = fin_io.connect(base=base)
    try:
        conn.execute(
            """
            INSERT INTO quotes_daily
                (ticker, date, market, close, volume, source, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET
                close = excluded.close,
                volume = excluded.volume
            """,
            (
                ticker.upper(), date_iso, market, close, volume, source,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

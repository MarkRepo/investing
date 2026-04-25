"""Shared types for quote adapters.

Adapter implementations (akshare_adapter, yfinance_adapter) live in sibling
modules. The io/quotes.py layer writes Quote instances; routes read them back
from the DB and render.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable


class AdapterError(Exception):
    """Adapter-layer exception wrapping upstream errors (network, parse, etc)."""


@dataclass(frozen=True)
class Quote:
    """One row in quotes_daily, as produced by an adapter.

    Field semantics:
    - date: ISO yyyy-mm-dd
    - dividend_yield: percent (3.0 == 3%)
    - turnover_rate: percent (volume / float_shares * 100)
    - volume_ratio_5d is NOT set here; io.quotes.upsert fills it from history.
    - source: adapter identifier (akshare / yfinance); mirrors the module attr.
    """

    ticker: str
    date: str
    market: str
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: int | None
    amount: float | None
    turnover_rate: float | None
    pe_ttm: float | None
    pe_static: float | None
    pe_forward: float | None
    pb: float | None
    ps: float | None
    peg: float | None
    dividend_yield: float | None
    market_cap: float | None
    float_market_cap: float | None
    shares_outstanding: float | None
    float_shares: float | None
    high_52w: float | None
    low_52w: float | None
    source: str
    fetched_at: str


@runtime_checkable
class QuoteAdapter(Protocol):
    """Interface adapter modules satisfy (duck-typed at module level).

    Implementations expose a module-level ``source`` str and three fetch fns.
    """

    source: str

    def fetch_daily(
        self, ticker: str, market: str, start: date, end: date
    ) -> list[Quote]: ...

    def fetch_intraday_today(
        self, ticker: str, market: str
    ) -> list[tuple[str, float, int]]: ...

    def fetch_snapshot(self, ticker: str, market: str) -> Quote: ...

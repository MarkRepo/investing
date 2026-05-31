"""Quote adapter registry.

Lazy import of concrete adapters so this package can be imported without
akshare/yfinance being installed (e.g. in narrow unit-test scopes). The
concrete module is resolved on first use.
"""
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from app.io.adapters.base import AdapterError, Quote, QuoteAdapter

__all__ = ["AdapterError", "Quote", "QuoteAdapter", "get_adapter"]


def get_adapter(market: str) -> "QuoteAdapter":
    """Return the adapter module for a given market.

    ``US`` / ``HKEX`` → yfinance (yfinance natively serves HK via ``.HK``
    symbols); CN markets (SSE/SZSE/BSE) → akshare.
    """
    if market in ("US", "HKEX"):
        mod_name = "app.io.adapters.yfinance_adapter"
    else:
        mod_name = "app.io.adapters.akshare_adapter"
    return importlib.import_module(mod_name)  # type: ignore[return-value]


if TYPE_CHECKING:  # pragma: no cover - purely for editor hints
    from app.io.adapters import akshare_adapter, yfinance_adapter  # noqa: F401

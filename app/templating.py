"""Shared Jinja filters for number formatting in quote panels.

Registered per-route (via ``register_filters(templates)``) because
FastAPI's ``Jinja2Templates`` creates a fresh environment each time.
"""
from __future__ import annotations

from typing import Any


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def fmt_price(v: Any) -> str:
    """Price with 2 decimals; empty string on None."""
    f = _to_float(v)
    return "" if f is None else f"{f:,.2f}"


def fmt_big(v: Any, market: str = "US") -> str:
    """Format a large number with market-appropriate units.

    - CN markets (SSE/SZSE/BSE/HKEX): ``12.34亿`` / ``3,456.7万`` / raw
    - US:                            ``$12.34B`` / ``$456.7M`` / ``$1.2K``

    Returns empty string for None. Keeps raw value (rounded to int) if it
    doesn't clear the smallest bucket.
    """
    f = _to_float(v)
    if f is None:
        return ""
    a = abs(f)
    if market == "US":
        if a >= 1e12:
            return f"${f/1e12:,.2f}T"
        if a >= 1e9:
            return f"${f/1e9:,.2f}B"
        if a >= 1e6:
            return f"${f/1e6:,.1f}M"
        if a >= 1e3:
            return f"${f/1e3:,.1f}K"
        return f"${f:,.0f}"
    # CN family
    if a >= 1e12:
        return f"{f/1e12:,.2f}万亿"
    if a >= 1e8:
        return f"{f/1e8:,.2f}亿"
    if a >= 1e4:
        return f"{f/1e4:,.1f}万"
    return f"{f:,.0f}"


def fmt_int(v: Any) -> str:
    """Integer with thousands separators (for raw share counts)."""
    f = _to_float(v)
    return "" if f is None else f"{int(f):,}"


def register_filters(templates) -> None:
    """Attach the quote-panel filters to a ``Jinja2Templates`` instance."""
    env = templates.env
    env.filters["fmt_price"] = fmt_price
    env.filters["fmt_big"] = fmt_big
    env.filters["fmt_int"] = fmt_int

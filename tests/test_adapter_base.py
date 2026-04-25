"""Tests for app.io.adapters base types + registry."""
from __future__ import annotations

from datetime import date

import pytest

from app.io.adapters import AdapterError, Quote, get_adapter
from app.io.adapters import akshare_adapter, yfinance_adapter


def _make_quote(**over) -> Quote:
    defaults = dict(
        ticker="TEST", date="2026-04-25", market="SSE",
        open=100.0, high=101.0, low=99.0, close=100.5,
        volume=10000, amount=1_005_000.0,
        turnover_rate=0.1,
        pe_ttm=20.0, pe_static=None, pe_forward=None,
        pb=3.0, ps=None, peg=None,
        dividend_yield=2.5,
        market_cap=1e10, float_market_cap=1e10,
        shares_outstanding=1e8, float_shares=1e8,
        high_52w=120.0, low_52w=80.0,
        source="akshare", fetched_at="2026-04-25T16:30:00",
    )
    defaults.update(over)
    return Quote(**defaults)


def test_quote_is_frozen():
    q = _make_quote()
    with pytest.raises((AttributeError, Exception)):
        q.close = 999.0  # type: ignore[misc]


def test_quote_equality_by_fields():
    a = _make_quote()
    b = _make_quote()
    assert a == b
    c = _make_quote(close=200.0)
    assert a != c


def test_get_adapter_us_returns_yfinance():
    assert get_adapter("US") is yfinance_adapter


def test_get_adapter_a_markets_return_akshare():
    for m in ("SSE", "SZSE", "BSE"):
        assert get_adapter(m) is akshare_adapter, f"market={m}"


def test_get_adapter_unknown_defaults_to_akshare():
    # Non-US markets currently route to akshare; a less-common code shouldn't error.
    assert get_adapter("HKEX") is akshare_adapter


def test_adapter_module_has_source_attr():
    assert akshare_adapter.source == "akshare"
    assert yfinance_adapter.source == "yfinance"


def test_adapter_error_is_exception():
    with pytest.raises(AdapterError):
        raise AdapterError("boom")


def test_adapter_modules_expose_protocol_fns():
    """Once T5/T6 fill in real implementations, the three fetch fns exist."""
    for mod in (akshare_adapter, yfinance_adapter):
        assert callable(getattr(mod, "fetch_daily", None))
        assert callable(getattr(mod, "fetch_intraday_today", None))
        assert callable(getattr(mod, "fetch_snapshot", None))

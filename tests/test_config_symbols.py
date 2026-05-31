"""Tests for app.config.to_yf_symbol — bare ticker + market → yfinance symbol."""
from __future__ import annotations

import pytest

from app import config as cfg


@pytest.mark.parametrize(
    "ticker,expected",
    [
        ("01801", "1801.HK"),   # Innovent — 5-digit zero-pad → 4-digit
        ("00700", "0700.HK"),   # Tencent — strip one leading zero, keep 4
        ("06160", "6160.HK"),   # BeiGene HK
        ("09988", "9988.HK"),   # Alibaba HK
        ("1801", "1801.HK"),    # already 4-digit
    ],
)
def test_hkex_maps_to_four_digit_hk_suffix(ticker, expected):
    assert cfg.to_yf_symbol(ticker, "HKEX") == expected


def test_us_returns_ticker_unchanged():
    assert cfg.to_yf_symbol("AAPL", "US") == "AAPL"
    assert cfg.to_yf_symbol("HIMS", "US") == "HIMS"


def test_other_markets_unchanged():
    # Defensive: non-HKEX markets pass through verbatim.
    assert cfg.to_yf_symbol("600276", "SSE") == "600276"

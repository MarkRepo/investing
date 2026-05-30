"""Market data utility for Prism workflows.

Reads quote data from local DB, always refreshes before returning —
company analysis is infrequent enough that one fetch per lookup is cheap,
and stale prices are worse than redundant API calls.
"""
from __future__ import annotations

from datetime import date as date_cls
from pathlib import Path
from typing import Any

from app.io import quotes as quotes_io
from prism.scripts.topic import read_topic


def _resolve_ticker(slug: str, variant: str) -> tuple[str, str] | None:
    """Read topic.yaml and return (ticker, market) or None."""
    try:
        topic = read_topic(slug, variant)
    except Exception:
        return None
    scope = topic.get("scope") or {}
    ticker = scope.get("ticker", "")
    if not ticker:
        return None
    # Handle old format "SZSE_000426"
    if "_" in ticker:
        market, code = ticker.split("_", 1)
        return code, market
    market = scope.get("market", "")
    if market and ticker:
        return ticker, market
    return None


def _is_fresh(ticker: str) -> bool:
    """Always returns False — market data is always refreshed on demand.

    Company analysis is infrequent enough that the cost of one fetch per
    lookup is negligible. This guarantees the latest available price every time.
    """
    return False


def _refresh(ticker: str, market: str) -> bool:
    """Fetch latest quote data and store to DB. Returns True on success."""
    try:
        from scripts.fetch_quotes_eod import run_for_ticker
        run_for_ticker(ticker, market)
        return True
    except Exception:
        return False


def get_quote(slug: str, variant: str) -> dict[str, Any]:
    """Get current market data for a Prism company topic.

    Returns a dict with keys: ticker, market, date, close, prev_close,
    change_pct, pe_ttm, pb, ps, market_cap, float_market_cap,
    high_52w, low_52w, source, fresh.

    If local data is stale or missing, fetches from adapter and stores to DB.
    """
    resolved = _resolve_ticker(slug, variant)
    if not resolved:
        return {"error": "no ticker in topic scope"}

    ticker, market = resolved

    if not _is_fresh(ticker):
        _refresh(ticker, market)

    latest = quotes_io.latest_for(ticker)
    if not latest:
        return {"error": f"no quote data for {ticker}", "ticker": ticker, "market": market}

    prev = quotes_io.second_latest_for(ticker)
    prev_close = (prev or {}).get("close")
    change_pct = None
    if prev_close and prev_close > 0 and latest.get("close"):
        change_pct = round((latest["close"] - prev_close) / prev_close * 100, 2)

    return {
        "ticker": ticker,
        "market": market,
        "date": latest.get("date"),
        "close": latest.get("close"),
        "prev_close": prev_close,
        "change_pct": change_pct,
        "pe_ttm": latest.get("pe_ttm"),
        "pe_static": latest.get("pe_static"),
        "pb": latest.get("pb"),
        "ps": latest.get("ps"),
        "market_cap": latest.get("market_cap"),
        "float_market_cap": latest.get("float_market_cap"),
        "high_52w": latest.get("high_52w"),
        "low_52w": latest.get("low_52w"),
        "source": latest.get("source"),
        "fresh": True,
    }


def get_valuation_context(slug: str, variant: str) -> str:
    """Return a markdown snippet with current valuation data for 决策链环②定价锚（_company_case / _valuation_models）.

    Designed to be injected into the workflow prompt context.
    """
    q = get_quote(slug, variant)
    if q.get("error"):
        return f"*(行情数据不可用: {q['error']})*"

    lines = [
        "## 当前市场数据 (自动获取)",
        "",
        f"- **日期**: {q['date']}",
        f"- **最新价**: {q['close']} 元",
        f"- **涨跌幅**: {q['change_pct']}%",
        f"- **PE(TTM)**: {q['pe_ttm']}",
        f"- **PB**: {q['pb']}",
        f"- **PS**: {q['ps']}",
        f"- **总市值**: {q['market_cap']:.0f} 元" if q.get("market_cap") else "",
        f"- **52周高**: {q['high_52w']}",
        f"- **52周低**: {q['low_52w']}",
        f"- **数据来源**: {q['source']}",
        "",
    ]
    return "\n".join(lines)
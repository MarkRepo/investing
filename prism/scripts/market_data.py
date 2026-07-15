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
    """Fetch latest quote data and store to DB. Returns True on success.

    依赖/解释器缺失（ImportError）与"真的没行情"是两类故障，必须区分：
    前者几乎总是「用了系统 python3 而非 .venv/bin/python」——jinja2/pandas/
    yfinance 只装在 .venv。静默吞掉会伪装成"no quote data"，导致改用 stale
    findings 倍数（cn-momenta 2026-06 即栽在此）。故对 ImportError 大声告警、
    不沉默。返回契约仍为 bool，调用方不变。
    """
    try:
        from scripts.fetch_quotes_eod import run_for_ticker
        run_for_ticker(ticker, market)
        return True
    except ImportError as e:
        import sys
        print(
            f"[market_data] ⚠️ 依赖缺失（{e}）——几乎可以肯定是用了系统 python3 "
            f"而非 .venv/bin/python。行情/财务依赖只装在 .venv。"
            f"请用 `cd <repo> && .venv/bin/python ...` 重跑。"
            f"此次 {ticker}/{market} 返回的'no quote data'是假象，不是真没源。",
            file=sys.stderr,
        )
        return False
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


# ---------------------------------------------------------------------------
# F13: peer 级（只有 ticker、无 slug）倍数入口。
# industry/arena funnel 环②/Step 1.2 用它对"代表龙头 ticker"批量拿 PE/PS/市值，
# 无需先建 company topic。底层与 get_quote 同链路（_refresh→fetch_quotes_eod→
# get_adapter；US/HKEX→yfinance、CN→akshare），HKEX 实测可取（HKD 计价）。
# ---------------------------------------------------------------------------

def _currency_label(market: str) -> str:
    """市值/价格计价货币标签（HKEX→HKD、美股→USD、A股→元）。"""
    if market == "HKEX":
        return "HKD"
    if market in ("US", "NASDAQ", "NYSE"):
        return "USD"
    return "元"


def get_quote_by_ticker(ticker: str, market: str) -> dict[str, Any]:
    """Ticker 级行情/倍数（无需 slug）。always-refresh，与 get_quote 同口径。

    用于 peer-matrix / 行业龙头横比：peer 只有 ticker、还没注册 company topic。
    返回 dict 含 currency（按 market 区分 HKD/USD/元）。无数据时返回 {'error',...}。
    """
    _refresh(ticker, market)  # _is_fresh 恒 False → 每次拉最新
    latest = quotes_io.latest_for(ticker)
    if not latest:
        return {"error": f"no quote data for {ticker}", "ticker": ticker, "market": market}
    return {
        "ticker": ticker,
        "market": market,
        "currency": _currency_label(market),
        "date": latest.get("date"),
        "close": latest.get("close"),
        "pe_ttm": latest.get("pe_ttm"),
        "pe_static": latest.get("pe_static"),
        "pb": latest.get("pb"),
        "ps": latest.get("ps"),
        "market_cap": latest.get("market_cap"),
        "high_52w": latest.get("high_52w"),
        "low_52w": latest.get("low_52w"),
        "source": latest.get("source"),
    }


def get_valuation_context_by_tickers(tickers: list[dict[str, str]]) -> str:
    """多龙头估值锚 markdown 块（喂 industry/arena 决策链环②/Step 1.2）。

    tickers: [{'ticker': '600276', 'market': 'SSE', 'name': '恒瑞'}, ...]
    （name 选填，仅展示用）。每行 PE(TTM)/PS/市值，市值按 market 标 HKD/USD/元。
    取不到的标 *(取不到)* 而非静默漏——契合 F13 "拉不到要 log 不静默跳"。
    """
    if not tickers:
        return "*(未提供 ticker)*"
    lines = ["## 代表龙头当前估值倍数 (本地 market_data 自动获取)", ""]
    for t in tickers:
        ticker = t.get("ticker", "")
        market = t.get("market", "")
        name = t.get("name") or ticker
        if not ticker or not market:
            lines.append(f"- **{name}**: *(缺 ticker/market，跳过)*")
            continue
        q = get_quote_by_ticker(ticker, market)
        if q.get("error"):
            lines.append(f"- **{name}** ({ticker}/{market}): *(取不到: {q['error']})*")
            continue
        ccy = q["currency"]
        mc = f"{q['market_cap']:.0f} {ccy}" if q.get("market_cap") else "n/a"
        lines.append(
            f"- **{name}** ({ticker}/{market}): "
            f"PE(TTM) {q.get('pe_ttm')} / PS {q.get('ps')} / PB {q.get('pb')} / "
            f"市值 {mc} / 价 {q.get('close')} {ccy}（{q.get('date')}，源 {q.get('source')}）"
        )
    lines.append("")
    return "\n".join(lines)
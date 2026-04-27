"""akshare adapter — A/SZSE/BSE market quotes.

Primary source is Sina (``stock_zh_a_daily`` + ``stock_zh_a_minute``) because
eastmoney's push2*.eastmoney.com endpoints are frequently blocked / rate-
limited depending on network path. Historical valuation (PE/PB/PS/PEG + market
cap) still comes from eastmoney's ``stock_value_em`` (data.eastmoney.com) —
a different host that's reliable.

Volume in Sina's daily feed is already in raw shares; ``turnover`` is a ratio
(0.002 = 0.2%), which we convert to percent.

52-week high/low is computed from the fetched history (max/min close of last
252 sessions) since the eastmoney "spot" endpoint isn't reachable here.

CN data sources are unreachable through the user's default Clash/VPN proxy,
so every akshare call is wrapped in ``_no_proxy()`` — it scrubs ``HTTP_PROXY``
/ ``HTTPS_PROXY`` / ``ALL_PROXY`` (both cases) from ``os.environ`` for the
duration of the call and restores them afterward. yfinance calls elsewhere
are unaffected.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any

import akshare as ak
import pandas as pd

from app.io.adapters.base import AdapterError, Quote

source = "akshare"

_PROXY_ENV_KEYS = (
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
)


@contextmanager
def _no_proxy():
    """Temporarily drop proxy env vars so akshare's underlying requests
    session talks directly to sina/eastmoney. Restored in the finally block
    whether the call succeeds or raises.
    """
    saved = {k: os.environ.pop(k, None) for k in _PROXY_ENV_KEYS}
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v

# Market → Sina ticker prefix. Sina expects "sh600519" / "sz000001" / "bj920118".
_MARKET_PREFIX = {"SSE": "sh", "SZSE": "sz", "BSE": "bj"}


def _sina_symbol(ticker: str, market: str) -> str:
    prefix = _MARKET_PREFIX.get(market)
    if not prefix:
        raise AdapterError(f"akshare: unsupported market {market!r} for ticker {ticker}")
    return f"{prefix}{ticker}"


def _f(val: Any) -> float | None:
    """Coerce an akshare cell to float | None, treating NaN/empty as None."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def _value_history(ticker: str) -> dict[str, dict]:
    """ISO date → {PE(TTM), PE(静), 市净率, PEG值, 市销率, 总市值, ...}.

    Per-stock historical valuation from eastmoney's data-center endpoint.
    Degrades to {} on any upstream failure; daily rows just lose valuation.
    """
    try:
        with _no_proxy():
            df = ak.stock_value_em(symbol=ticker)
    except Exception:
        return {}
    if df is None or df.empty:
        return {}
    out: dict[str, dict] = {}
    for _, r in df.iterrows():
        d = str(r["数据日期"])
        out[d] = dict(r)
    return out


def fetch_daily(
    ticker: str, market: str, start: date, end: date
) -> list[Quote]:
    """Pull one Quote per trading session in [start, end] (inclusive)."""
    symbol = _sina_symbol(ticker, market)
    try:
        with _no_proxy():
            hist = ak.stock_zh_a_daily(
                symbol=symbol,
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                adjust="",
            )
    except Exception as e:
        raise AdapterError(
            f"akshare.stock_zh_a_daily({ticker}): {type(e).__name__}: {e}"
        ) from e
    if hist is None or hist.empty:
        return []

    val_hist = _value_history(ticker)

    # Normalize column name — sina returns `date`
    date_col = "date" if "date" in hist.columns else "day"
    hist = hist.sort_values(date_col).reset_index(drop=True)

    # 52w high/low from the last 252 rows of this fetch (attach to latest only).
    recent = hist.tail(252)
    high_52w = _f(recent["high"].max()) if "high" in recent.columns else None
    low_52w = _f(recent["low"].min()) if "low" in recent.columns else None

    latest_idx = len(hist) - 1
    now_iso = datetime.now().isoformat()

    out: list[Quote] = []
    for i, row in hist.iterrows():
        d = str(row[date_col])
        # Sina formats date as YYYY-MM-DD; keep as-is
        vol = _f(row.get("volume"))
        volume = int(vol) if vol is not None else None
        close_f = _f(row.get("close")) or 0.0
        # turnover in sina is a ratio (0.002 = 0.2%); adapter stores percent
        turnover_raw = _f(row.get("turnover"))
        turnover_pct = (turnover_raw * 100.0) if turnover_raw is not None else None

        val = val_hist.get(d, {})
        total_mc = _f(val.get("总市值"))
        float_mc = _f(val.get("流通市值"))
        shares_out = _f(val.get("总股本"))
        float_shares_day = _f(val.get("流通股本")) or _f(row.get("outstanding_share"))

        is_latest = (i == latest_idx)
        out.append(Quote(
            ticker=ticker, date=d, market=market,
            open=_f(row.get("open")),
            high=_f(row.get("high")),
            low=_f(row.get("low")),
            close=close_f,
            volume=volume,
            amount=_f(row.get("amount")),
            turnover_rate=turnover_pct,
            pe_ttm=_f(val.get("PE(TTM)")),
            pe_static=_f(val.get("PE(静)")),
            pe_forward=None,
            pb=_f(val.get("市净率")),
            ps=_f(val.get("市销率")),
            peg=_f(val.get("PEG值")),
            dividend_yield=None,
            market_cap=total_mc,
            float_market_cap=float_mc,
            shares_outstanding=shares_out,
            float_shares=float_shares_day,
            high_52w=high_52w if is_latest else None,
            low_52w=low_52w if is_latest else None,
            source="akshare",
            fetched_at=now_iso,
        ))
    return out


def _fetch_minute_bars(
    ticker: str, market: str
) -> tuple[str, list[tuple[str, float, int]]] | None:
    """Return (latest_day_iso, [(HH:MM, close, volume), ...]) or None on failure.

    Silently returns None on any upstream error — intended for the snapshot
    fallback path where a minute-feed failure should degrade to EOD gracefully.
    """
    symbol = _sina_symbol(ticker, market)
    try:
        with _no_proxy():
            df = ak.stock_zh_a_minute(symbol=symbol, period="1", adjust="")
    except Exception:
        return None
    if df is None or df.empty:
        return None
    return _parse_minute_df(df)


def _parse_minute_df(
    df: "pd.DataFrame",
) -> tuple[str, list[tuple[str, float, int]]] | None:
    """Extract (latest_day_iso, bars) from a minute DataFrame."""
    day_prefixes = df["day"].astype(str).str.slice(0, 10)
    latest_day = day_prefixes.max()
    df = df[day_prefixes == latest_day]
    bars: list[tuple[str, float, int]] = []
    for _, r in df.iterrows():
        ts = str(r["day"])
        hhmm = ts[11:16] if len(ts) >= 16 else ts
        c = _f(r.get("close"))
        v = _f(r.get("volume"))
        if c is None or v is None:
            continue
        bars.append((hhmm, c, int(v)))
    if not bars:
        return None
    return (latest_day, bars)


def fetch_intraday_today(
    ticker: str, market: str
) -> list[tuple[str, float, int]]:
    """Return [(HH:MM, price, volume), ...] for the most-recent session via Sina.

    Sina's 1-min feed carries several sessions; we pick the last date present
    and return its bars. This means on weekends / holidays / before the
    session opens, the caller sees the *previous* trading day's intraday
    rather than an empty chart.
    """
    symbol = _sina_symbol(ticker, market)
    try:
        with _no_proxy():
            df = ak.stock_zh_a_minute(symbol=symbol, period="1", adjust="")
    except Exception as e:
        raise AdapterError(
            f"akshare.stock_zh_a_minute({ticker}): {type(e).__name__}: {e}"
        ) from e
    if df is None or df.empty:
        return []
    result = _parse_minute_df(df)
    return result[1] if result else []


def fetch_snapshot(ticker: str, market: str) -> Quote:
    """One-shot current snapshot.

    Primary path: fetch EOD daily rows from Sina; return the latest row.
    Intraday fallback: if the latest EOD row is not from today (Sina hasn't
    published the close yet), try the 1-min feed. When today's minute bars are
    available, synthesize a Quote with live OHLCV and carried-forward
    fundamentals (pe/pb/shares) from the last EOD row. Source is tagged
    "akshare-intraday" so callers can distinguish. The upsert later will
    overwrite this row once EOD publishes.
    """
    today = date.today()
    end = today
    start = end.replace(day=1) if end.day > 3 else end.replace(year=end.year, month=max(1, end.month - 1), day=1)
    rows = fetch_daily(ticker, market, start, end)
    if not rows:
        raise AdapterError(f"akshare: no recent data for {ticker}")
    last = rows[-1]
    if last.date == today.isoformat():
        return last

    # EOD hasn't published today — try minute feed for live intraday data.
    minute_result = _fetch_minute_bars(ticker, market)
    if minute_result is None:
        return last
    minute_day, bars = minute_result
    if minute_day != today.isoformat() or not bars:
        return last

    # Synthesize today's Quote from intraday bars + carried-forward fundamentals.
    closes = [c for _, c, _ in bars]
    volumes = [v for _, _, v in bars]
    open_price = _f(bars[0][1])  # first bar close ≈ open approximation
    close_price = closes[-1]
    high_price = max(closes)
    low_price = min(closes)
    total_volume = sum(volumes)
    shares = last.shares_outstanding
    market_cap = (close_price * shares) if shares else last.market_cap
    return Quote(
        ticker=ticker, date=today.isoformat(), market=market,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=total_volume,
        amount=None,
        turnover_rate=None,
        pe_ttm=last.pe_ttm,
        pe_static=last.pe_static,
        pe_forward=None,
        pb=last.pb,
        ps=last.ps,
        peg=last.peg,
        dividend_yield=None,
        market_cap=market_cap,
        float_market_cap=last.float_market_cap,
        shares_outstanding=shares,
        float_shares=last.float_shares,
        high_52w=last.high_52w,
        low_52w=last.low_52w,
        source="akshare-intraday",
        fetched_at=datetime.now().isoformat(),
    )

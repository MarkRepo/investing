"""yfinance adapter — US + HKEX market quotes via yfinance.

HKEX is served through yfinance's ``.HK`` symbols (see ``cfg.to_yf_symbol``);
the ticker stored on the Quote stays the bare code (``01801``) while the query
uses ``1801.HK``. HK quotes (price / PE / PS / market_cap) come back in HKD.

Endpoints:
- ``Ticker.history(start, end)``              → OHLCV history
- ``Ticker.info``                              → valuation / share counts /
                                                 52w high-low (point-in-time)
- ``Ticker.history(period="1d", interval="1m")`` → today's intraday
- ``Ticker.fast_info``                         → snapshot (cheaper than .info)

Fields we can't get historically from yfinance (PE/PB/52w/etc. are only
current) land on the latest daily row; older rows keep them as None.
``amount`` is estimated as close × volume since yfinance doesn't return
native dollar turnover.
``dividendYield`` comes back as a decimal (0.03 == 3%); we convert to %.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import yfinance as yf

from app import config as cfg
from app.io.adapters.base import AdapterError, Quote

source = "yfinance"


def _f(val) -> float | None:
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


def fetch_daily(
    ticker: str, market: str, start: date, end: date
) -> list[Quote]:
    try:
        t = yf.Ticker(cfg.to_yf_symbol(ticker, market))
        # yfinance end is exclusive; add a day so we include the requested end.
        hist = t.history(start=start, end=end + timedelta(days=1), auto_adjust=False)
        info = t.info or {}
    except Exception as e:
        raise AdapterError(
            f"yfinance.fetch_daily({ticker}): {type(e).__name__}: {e}"
        ) from e
    if hist is None or hist.empty:
        return []

    float_shares = _f(info.get("floatShares"))
    shares_out = _f(info.get("sharesOutstanding"))
    now_iso = datetime.now().isoformat()

    dates = [idx.strftime("%Y-%m-%d") for idx in hist.index]
    latest_str = dates[-1]

    out: list[Quote] = []
    for idx, h in hist.iterrows():
        d = idx.strftime("%Y-%m-%d")
        is_latest = (d == latest_str)
        vol = _f(h.get("Volume"))
        volume = int(vol) if vol is not None else None
        close_f = _f(h.get("Close")) or 0.0

        turnover = None
        if volume is not None and float_shares:
            turnover = volume / float_shares * 100.0

        out.append(Quote(
            ticker=ticker, date=d, market=market,
            open=_f(h.get("Open")),
            high=_f(h.get("High")),
            low=_f(h.get("Low")),
            close=close_f,
            volume=volume,
            amount=(close_f * volume) if volume is not None else None,
            turnover_rate=turnover,
            pe_ttm=_f(info.get("trailingPE")) if is_latest else None,
            pe_static=None,
            pe_forward=_f(info.get("forwardPE")) if is_latest else None,
            pb=_f(info.get("priceToBook")) if is_latest else None,
            ps=_f(info.get("priceToSalesTrailing12Months")) if is_latest else None,
            peg=_f(info.get("trailingPegRatio")) if is_latest else None,
            dividend_yield=(
                ((_f(info.get("dividendYield")) or 0.0) * 100.0)
                if is_latest else None
            ),
            market_cap=_f(info.get("marketCap")) if is_latest else None,
            float_market_cap=(
                (float_shares * close_f) if (is_latest and float_shares) else None
            ),
            shares_outstanding=shares_out if is_latest else None,
            float_shares=float_shares,
            high_52w=_f(info.get("fiftyTwoWeekHigh")) if is_latest else None,
            low_52w=_f(info.get("fiftyTwoWeekLow")) if is_latest else None,
            source="yfinance",
            fetched_at=now_iso,
        ))
    return out


def fetch_intraday_today(
    ticker: str, market: str
) -> list[tuple[str, float, int]]:
    """Return the most-recent session's 1-min bars.

    Pulls a 5-day window so weekend/holiday loads still have something to
    show — we filter to the last session present in the response.
    """
    try:
        df = yf.Ticker(cfg.to_yf_symbol(ticker, market)).history(
            period="5d", interval="1m", auto_adjust=False
        )
    except Exception as e:
        raise AdapterError(
            f"yfinance.fetch_intraday({ticker}): {type(e).__name__}: {e}"
        ) from e
    if df is None or df.empty:
        return []
    # Keep only the last trading day present in the index.
    last_day = df.index[-1].date() if len(df.index) else None
    if last_day is not None:
        df = df[df.index.date == last_day]
    out: list[tuple[str, float, int]] = []
    for idx, r in df.iterrows():
        close = _f(r.get("Close"))
        vol = _f(r.get("Volume"))
        if close is None or vol is None:
            continue
        out.append((idx.strftime("%H:%M"), close, int(vol)))
    return out


def fetch_snapshot(ticker: str, market: str) -> Quote:
    try:
        t = yf.Ticker(cfg.to_yf_symbol(ticker, market))
        fi = t.fast_info
        info = t.info or {}
        # Use history to learn the most recent *real* trading day. yfinance's
        # fast_info.last_price during weekends / holidays still returns last
        # close, but has no date field — naively stamping date.today() creates
        # a bogus row with Friday's close on Saturday.
        hist = t.history(period="5d", auto_adjust=False)
    except Exception as e:
        raise AdapterError(
            f"yfinance.fetch_snapshot({ticker}): {type(e).__name__}: {e}"
        ) from e

    # fast_info may not support dict-access in every version; probe.
    def _fi(key, default=None):
        try:
            return fi[key]
        except (KeyError, TypeError):
            return getattr(fi, key, default)

    close_f = _f(_fi("last_price")) or _f(info.get("regularMarketPrice")) or 0.0
    float_shares = _f(info.get("floatShares"))
    volume = _fi("last_volume")
    try:
        volume = int(volume) if volume is not None else None
    except (TypeError, ValueError):
        volume = None

    # Real trading date — last index in history if present, else today.
    snap_date = (
        hist.index[-1].date().isoformat()
        if hist is not None and not hist.empty
        else date.today().isoformat()
    )

    return Quote(
        ticker=ticker, date=snap_date, market=market,
        open=_f(_fi("open", close_f)),
        high=_f(_fi("day_high", close_f)),
        low=_f(_fi("day_low", close_f)),
        close=close_f,
        volume=volume,
        amount=(close_f * volume) if volume is not None else None,
        turnover_rate=(volume / float_shares * 100.0) if (volume and float_shares) else None,
        pe_ttm=_f(info.get("trailingPE")),
        pe_static=None,
        pe_forward=_f(info.get("forwardPE")),
        pb=_f(info.get("priceToBook")),
        ps=_f(info.get("priceToSalesTrailing12Months")),
        peg=_f(info.get("trailingPegRatio")),
        dividend_yield=(_f(info.get("dividendYield")) or 0.0) * 100.0,
        market_cap=_f(info.get("marketCap")),
        float_market_cap=(float_shares * close_f) if float_shares else None,
        shares_outstanding=_f(info.get("sharesOutstanding")),
        float_shares=float_shares,
        high_52w=_f(info.get("fiftyTwoWeekHigh")),
        low_52w=_f(info.get("fiftyTwoWeekLow")),
        source="yfinance",
        fetched_at=datetime.now().isoformat(),
    )

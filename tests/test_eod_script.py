"""Tests for scripts.fetch_quotes_eod.

Uses a fake adapter injected via monkeypatching ``get_adapter`` so tests
don't hit akshare/yfinance.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from app.io import quotes as quotes_io
from app.io.adapters.base import AdapterError, Quote
from scripts import fetch_quotes_eod as eod


def _make_quote(ticker, d, market="SSE", close=100.0):
    return Quote(
        ticker=ticker, date=d, market=market,
        open=close - 1, high=close + 1, low=close - 2, close=close,
        volume=10000, amount=close * 10000,
        turnover_rate=0.1,
        pe_ttm=None, pe_static=None, pe_forward=None,
        pb=None, ps=None, peg=None,
        dividend_yield=None,
        market_cap=None, float_market_cap=None,
        shares_outstanding=None, float_shares=None,
        high_52w=None, low_52w=None,
        source="fake", fetched_at=datetime.now().isoformat(),
    )


class _FakeAdapter:
    """Records fetch_daily calls and returns preset rows/exceptions."""
    def __init__(self, rows=None, raises=None):
        self._rows = rows or []
        self._raises = raises
        self.calls: list[tuple] = []

    def fetch_daily(self, ticker, market, start, end):
        self.calls.append((ticker, market, start, end))
        if self._raises:
            raise self._raises
        return self._rows

    def fetch_intraday_today(self, *a, **kw):
        return []

    def fetch_snapshot(self, *a, **kw):
        raise AdapterError("snapshot not mocked")


def _patch_adapter(monkeypatch, adapter):
    monkeypatch.setattr(eod, "get_adapter", lambda _market: adapter)


def _make_company_dir(base: Path, market: str, ticker: str, name: str | None = None):
    """Lay down a minimal companies/<market>_<ticker>/meta.md for list_companies()."""
    d = base / "companies" / f"{market}_{ticker}"
    d.mkdir(parents=True, exist_ok=True)
    meta = f"""---
ticker: {ticker}
market: {market}
name: {name or ticker}
---
"""
    (d / "meta.md").write_text(meta)


# ---------- run_for_ticker ----------


def test_run_for_ticker_empty_db_backfills(tmp_path, monkeypatch):
    rows = [_make_quote("600519", f"2026-04-{d:02d}") for d in (20, 21, 22, 23, 24)]
    fake = _FakeAdapter(rows=rows)
    _patch_adapter(monkeypatch, fake)

    r = eod.run_for_ticker(
        "600519", "SSE", backfill_years=5, base=tmp_path,
        today=date(2026, 4, 25),
    )
    assert r["status"] == "ok"
    assert r["quotes_added"] == 5
    # adapter got called with start ≈ today - 5y
    ticker, market, start, end = fake.calls[0]
    assert ticker == "600519"
    assert market == "SSE"
    assert end == date(2026, 4, 25)
    assert start <= date(2021, 4, 26) and start >= date(2021, 4, 24)

    # rows were actually written
    assert quotes_io.last_date_for("600519", base=tmp_path) == "2026-04-24"


def test_run_for_ticker_incremental_starts_day_after_last(tmp_path, monkeypatch):
    # Seed with one prior row
    seed_rows = [_make_quote("600519", "2026-04-20")]
    _FakeAdapter(seed_rows)  # unused; seed via io
    for q in seed_rows:
        quotes_io.upsert(q, base=tmp_path)

    fake = _FakeAdapter(rows=[_make_quote("600519", "2026-04-21"),
                              _make_quote("600519", "2026-04-22")])
    _patch_adapter(monkeypatch, fake)

    r = eod.run_for_ticker(
        "600519", "SSE", base=tmp_path, today=date(2026, 4, 22),
    )
    assert r["status"] == "ok"
    _, _, start, end = fake.calls[0]
    assert start == date(2026, 4, 21)
    assert end == date(2026, 4, 22)


def test_run_for_ticker_uptodate_skips_adapter(tmp_path, monkeypatch):
    # last_date == today → no fetch
    quotes_io.upsert(_make_quote("600519", "2026-04-25"), base=tmp_path)
    fake = _FakeAdapter(rows=[])
    _patch_adapter(monkeypatch, fake)

    r = eod.run_for_ticker(
        "600519", "SSE", base=tmp_path, today=date(2026, 4, 25),
    )
    assert r["status"] == "uptodate"
    assert r["quotes_added"] == 0
    assert fake.calls == []


def test_run_for_ticker_adapter_error_records(tmp_path, monkeypatch):
    fake = _FakeAdapter(raises=AdapterError("akshare.stock_zh_a_hist(600519): 429"))
    _patch_adapter(monkeypatch, fake)

    r = eod.run_for_ticker(
        "600519", "SSE", base=tmp_path, today=date(2026, 4, 25),
    )
    assert r["status"] == "error"
    assert "429" in r["error"]

    errs = quotes_io.unresolved_fetch_errors(base=tmp_path)
    assert len(errs) == 1
    assert errs[0]["ticker"] == "600519"
    assert errs[0]["phase"] == "eod"


def test_run_for_ticker_success_resolves_prior_error(tmp_path, monkeypatch):
    # Seed with a prior unresolved error
    quotes_io.record_error("600519", "SSE", phase="eod", error="old", base=tmp_path)

    fake = _FakeAdapter(rows=[_make_quote("600519", "2026-04-25")])
    _patch_adapter(monkeypatch, fake)

    r = eod.run_for_ticker(
        "600519", "SSE", base=tmp_path, today=date(2026, 4, 25),
    )
    assert r["status"] == "ok"
    assert r["quotes_added"] == 1
    assert quotes_io.unresolved_fetch_errors(base=tmp_path) == []


# ---------- run_eod ----------


def test_run_eod_processes_all_companies(tmp_path, monkeypatch):
    _make_company_dir(tmp_path, "SSE", "600519")
    _make_company_dir(tmp_path, "US", "AAPL")

    call_log: list[str] = []

    def _mocked_run(ticker, market, **_kw):
        call_log.append(f"{market}:{ticker}")
        return {"status": "ok", "quotes_added": 3, "error": None}

    monkeypatch.setattr(eod, "run_for_ticker", _mocked_run)

    result = eod.run_eod(base=tmp_path, sleep_between=False)
    assert result == {"ok": 2, "errors": 0, "uptodate": 0, "total": 2}
    assert set(call_log) == {"SSE:600519", "US:AAPL"}


def test_run_eod_filters_by_market(tmp_path, monkeypatch):
    _make_company_dir(tmp_path, "SSE", "600519")
    _make_company_dir(tmp_path, "US", "AAPL")

    called: list[str] = []
    monkeypatch.setattr(
        eod, "run_for_ticker",
        lambda t, m, **_: (called.append(f"{m}:{t}"),
                           {"status": "ok", "quotes_added": 1, "error": None})[1],
    )

    result = eod.run_eod(markets=["US"], base=tmp_path, sleep_between=False)
    assert result["total"] == 1
    assert called == ["US:AAPL"]


def test_run_eod_filters_by_ticker(tmp_path, monkeypatch):
    _make_company_dir(tmp_path, "SSE", "600519")
    _make_company_dir(tmp_path, "SSE", "600000")

    called: list[str] = []
    monkeypatch.setattr(
        eod, "run_for_ticker",
        lambda t, m, **_: (called.append(t),
                           {"status": "ok", "quotes_added": 1, "error": None})[1],
    )

    result = eod.run_eod(tickers=["600519"], base=tmp_path, sleep_between=False)
    assert result["total"] == 1
    assert called == ["600519"]


def test_run_eod_mixed_results(tmp_path, monkeypatch):
    _make_company_dir(tmp_path, "SSE", "GOOD")
    _make_company_dir(tmp_path, "SSE", "BAD")
    _make_company_dir(tmp_path, "SSE", "STALE")

    outcomes = {
        "GOOD":  {"status": "ok",       "quotes_added": 5, "error": None},
        "BAD":   {"status": "error",    "quotes_added": 0, "error": "boom"},
        "STALE": {"status": "uptodate", "quotes_added": 0, "error": None},
    }
    monkeypatch.setattr(eod, "run_for_ticker",
                        lambda t, m, **_: outcomes[t])

    result = eod.run_eod(base=tmp_path, sleep_between=False)
    assert result == {"ok": 1, "errors": 1, "uptodate": 1, "total": 3}

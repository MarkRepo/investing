"""T10 tests: /prices, /prices/<key>, /prices/<key>/refresh, /chart."""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.io import quotes as quotes_io
from app.io.adapters.base import AdapterError, Quote
from tests.helpers import insert_quote


@pytest.fixture
def client(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parent.parent
    shutil.copytree(repo / "templates", tmp_path / "templates")
    (tmp_path / "companies").mkdir()
    (tmp_path / "watchlist").mkdir()
    (tmp_path / "portfolio").mkdir()
    (tmp_path / "portfolio" / "rules.md").write_text("# rules\n")
    (tmp_path / "journal" / "decisions").mkdir(parents=True)
    (tmp_path / "industries").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "macro" / "regime").mkdir(parents=True)
    shutil.copytree(repo / "controlled-vocab", tmp_path / "controlled-vocab")

    monkeypatch.chdir(tmp_path)
    from app import config as cfg
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(cfg, "TEMPLATES_DIR", tmp_path / "templates")
    monkeypatch.setattr(cfg, "WATCHLIST_DIR", tmp_path / "watchlist")
    monkeypatch.setattr(cfg, "PORTFOLIO_DIR", tmp_path / "portfolio")
    monkeypatch.setattr(cfg, "JOURNAL_DIR", tmp_path / "journal")
    monkeypatch.setattr(cfg, "INDUSTRIES_DIR", tmp_path / "industries")
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cfg, "FINANCIALS_DB", tmp_path / "data" / "financials.db")
    monkeypatch.setattr(cfg, "CONTROLLED_VOCAB_DIR", tmp_path / "controlled-vocab")
    monkeypatch.setattr(
        cfg, "SECTOR_VOCAB_DIR", tmp_path / "controlled-vocab" / "competence-sector"
    )

    from main import app
    return TestClient(app)


class _FakeAdapter:
    def __init__(self, intraday_rows=None, snapshot=None,
                 intraday_raises=None, snapshot_raises=None):
        self.intraday_rows = intraday_rows or []
        self.snapshot = snapshot
        self.intraday_raises = intraday_raises
        self.snapshot_raises = snapshot_raises

    def fetch_daily(self, *a, **kw):
        return []

    def fetch_intraday_today(self, *a, **kw):
        if self.intraday_raises:
            raise self.intraday_raises
        return self.intraday_rows

    def fetch_snapshot(self, *a, **kw):
        if self.snapshot_raises:
            raise self.snapshot_raises
        if self.snapshot is None:
            raise AdapterError("no snapshot")
        return self.snapshot


def _make_quote(ticker, date_iso, close=100.0, market="US"):
    return Quote(
        ticker=ticker, date=date_iso, market=market,
        open=close - 1, high=close + 1, low=close - 2, close=close,
        volume=10000, amount=close * 10000,
        turnover_rate=0.1,
        pe_ttm=None, pe_static=None, pe_forward=None,
        pb=None, ps=None, peg=None, dividend_yield=None,
        market_cap=None, float_market_cap=None,
        shares_outstanding=None, float_shares=None,
        high_52w=None, low_52w=None,
        source="fake", fetched_at=datetime.now().isoformat(),
    )


def _create_company(client, ticker="TR", market="US", name="tr"):
    client.post("/companies/new",
                data={"ticker": ticker, "market": market, "name": name,
                      "sector": "saas", "currency": "USD"})


# ---------- index ----------


def test_index_empty_when_no_companies(client):
    r = client.get("/prices", follow_redirects=False)
    assert r.status_code == 200
    assert "还没有公司" in r.text


def test_index_redirects_to_first_company(client):
    _create_company(client, "AA", "US", "aa")
    _create_company(client, "BB", "US", "bb")
    r = client.get("/prices", follow_redirects=False)
    assert r.status_code == 302
    # list_companies sorts by directory name ("US_AA" < "US_BB")
    assert r.headers["location"].startswith("/prices/US_")


# ---------- detail ----------


def test_detail_with_data(client, tmp_path, monkeypatch):
    _create_company(client, "TR", "US", "tr")
    insert_quote(tmp_path, ticker="TR", date="2026-04-23", market="US", close=100.0)
    insert_quote(tmp_path, ticker="TR", date="2026-04-24", market="US", close=105.0)

    # stub out adapter so intraday doesn't hit network
    from app.routes import prices as prices_route
    monkeypatch.setattr(prices_route, "get_adapter",
                        lambda _m: _FakeAdapter(intraday_rows=[]))

    r = client.get("/prices/US_TR")
    assert r.status_code == 200
    assert "US:TR" in r.text
    assert "105.00" in r.text
    assert "数据至 2026-04-24" in r.text
    # chart containers present
    assert "kline-chart" in r.text
    # company picker carries all companies
    assert 'value="US_TR"' in r.text


def test_detail_does_not_call_adapter_on_page_load(client, tmp_path, monkeypatch):
    """Page GET must stay DB-only so switching companies is fast."""
    _create_company(client, "TR", "US", "tr")
    insert_quote(tmp_path, ticker="TR", date="2026-04-24", market="US", close=100.0)
    called = {"intraday": 0}
    class _NoCalls(_FakeAdapter):
        def fetch_intraday_today(self, *a, **kw):
            called["intraday"] += 1
            return []
    from app.routes import prices as prices_route
    monkeypatch.setattr(prices_route, "get_adapter", lambda _m: _NoCalls())

    r = client.get("/prices/US_TR")
    assert r.status_code == 200
    assert called["intraday"] == 0  # the async endpoint owns that call


def test_intraday_endpoint_skips_when_no_data(client, tmp_path, monkeypatch):
    _create_company(client, "NEW", "US", "new")
    called = {"intraday": 0}
    class _NoCalls(_FakeAdapter):
        def fetch_intraday_today(self, *a, **kw):
            called["intraday"] += 1
            return []
    from app.routes import prices as prices_route
    monkeypatch.setattr(prices_route, "get_adapter", lambda _m: _NoCalls())

    r = client.get("/prices/US_NEW/intraday")
    assert r.status_code == 200
    assert r.json() == {"bars": [], "error": None}
    assert called["intraday"] == 0


def test_intraday_endpoint_error_writes_error_row(client, tmp_path, monkeypatch):
    _create_company(client, "TR", "US", "tr")
    insert_quote(tmp_path, ticker="TR", date="2026-04-24", market="US", close=100.0)

    from app.routes import prices as prices_route
    monkeypatch.setattr(
        prices_route, "get_adapter",
        lambda _m: _FakeAdapter(intraday_raises=AdapterError("429")),
    )

    r = client.get("/prices/US_TR/intraday")
    assert r.status_code == 200
    payload = r.json()
    assert payload["bars"] == []
    assert "429" in payload["error"]
    errs = quotes_io.unresolved_fetch_errors(base=tmp_path)
    assert any(e["phase"] == "intraday" for e in errs)


def test_detail_unknown_key_404(client):
    r = client.get("/prices/US_NOPE")
    assert r.status_code == 404


# ---------- refresh ----------


def test_refresh_success(client, tmp_path, monkeypatch):
    _create_company(client, "TR", "US", "tr")
    # daily: return 2 rows
    rows = [_make_quote("TR", "2026-04-23"), _make_quote("TR", "2026-04-24", close=105.0)]

    from scripts import fetch_quotes_eod as eod
    from app.routes import prices as prices_route
    monkeypatch.setattr(eod, "get_adapter",
                        lambda _m: type("_A", (), {
                            "fetch_daily": lambda self, *a, **kw: rows,
                        })())
    monkeypatch.setattr(
        prices_route, "get_adapter",
        lambda _m: _FakeAdapter(snapshot=_make_quote("TR", "2026-04-24", close=106.0)),
    )

    r = client.post("/prices/US_TR/refresh")
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    assert j["quotes_added"] == 2
    assert j["daily_error"] is None
    assert j["snapshot_error"] is None
    assert j["latest"]["close"] == 106.0


def test_refresh_daily_error_but_snapshot_ok(client, tmp_path, monkeypatch):
    _create_company(client, "TR", "US", "tr")

    from scripts import fetch_quotes_eod as eod
    from app.routes import prices as prices_route

    class _DailyBroken:
        def fetch_daily(self, *a, **kw):
            raise AdapterError("daily 429")

    monkeypatch.setattr(eod, "get_adapter", lambda _m: _DailyBroken())
    monkeypatch.setattr(
        prices_route, "get_adapter",
        lambda _m: _FakeAdapter(snapshot=_make_quote("TR", "2026-04-24", close=100.0)),
    )

    r = client.post("/prices/US_TR/refresh")
    j = r.json()
    assert j["ok"] is True
    assert "429" in j["daily_error"]
    assert j["snapshot_error"] is None


def test_refresh_both_fail(client, tmp_path, monkeypatch):
    _create_company(client, "TR", "US", "tr")

    from scripts import fetch_quotes_eod as eod
    from app.routes import prices as prices_route

    class _AllBroken:
        def fetch_daily(self, *a, **kw):
            raise AdapterError("daily down")

    monkeypatch.setattr(eod, "get_adapter", lambda _m: _AllBroken())
    monkeypatch.setattr(
        prices_route, "get_adapter",
        lambda _m: _FakeAdapter(snapshot_raises=AdapterError("snap down")),
    )

    r = client.post("/prices/US_TR/refresh")
    j = r.json()
    assert j["ok"] is False
    assert "daily down" in j["daily_error"]
    assert "snap down" in j["snapshot_error"]


def test_refresh_unknown_key_404(client):
    r = client.post("/prices/US_NOPE/refresh")
    assert r.status_code == 404


# ---------- chart ----------


def test_chart_1d_returns_raw(client, tmp_path):
    _create_company(client, "TR", "US", "tr")
    insert_quote(tmp_path, ticker="TR", date="2026-04-22", market="US", close=100.0)
    insert_quote(tmp_path, ticker="TR", date="2026-04-23", market="US", close=110.0)

    r = client.get("/prices/US_TR/chart?period=1d")
    assert r.status_code == 200
    j = r.json()
    assert j["period"] == "1d"
    assert len(j["ohlcv"]) == 2
    assert j["ohlcv"][-1]["date"] == "2026-04-23"


def test_chart_weekly_aggregates(client, tmp_path):
    _create_company(client, "TR", "US", "tr")
    # Mon 2026-04-20 through Fri 2026-04-24 all fall in same ISO week
    for d, c in [("2026-04-20", 100.0), ("2026-04-21", 101.0),
                 ("2026-04-22", 102.0), ("2026-04-23", 103.0),
                 ("2026-04-24", 104.0)]:
        insert_quote(tmp_path, ticker="TR", date=d, market="US", close=c)

    r = client.get("/prices/US_TR/chart?period=1w")
    j = r.json()
    assert j["period"] == "1w"
    assert len(j["ohlcv"]) == 1
    assert j["ohlcv"][0]["date"] == "2026-04-20"  # Monday
    assert j["ohlcv"][0]["close"] == 104.0        # last in bucket


def test_chart_monthly_aggregates(client, tmp_path):
    _create_company(client, "TR", "US", "tr")
    for d, c in [("2026-03-31", 100.0), ("2026-04-01", 110.0), ("2026-04-30", 115.0)]:
        insert_quote(tmp_path, ticker="TR", date=d, market="US", close=c)

    r = client.get("/prices/US_TR/chart?period=1M")
    j = r.json()
    buckets = {r["date"]: r for r in j["ohlcv"]}
    assert set(buckets.keys()) == {"2026-03-01", "2026-04-01"}
    assert buckets["2026-04-01"]["close"] == 115.0


def test_chart_unknown_key_404(client):
    r = client.get("/prices/US_NOPE/chart?period=1d")
    assert r.status_code == 404

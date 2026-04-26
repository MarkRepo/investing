"""T9 integration tests: home alert card + list row button + detail panel."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.io import quotes as quotes_io
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
    (tmp_path / "regime").mkdir()
    (tmp_path / "macro" / "regime").mkdir(parents=True)
    (tmp_path / "data").mkdir()
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
    from main import app
    return TestClient(app)


def _seed_company(tmp_path: Path, ticker="TR", market="US", name="tr"):
    """Use the HTTP POST to lay down a real company dir."""
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    c.post(
        "/companies/new",
        data={"ticker": ticker, "market": market, "name": name,
              "industry_slugs": "saas", "currency": "USD"},
    )


# ---------- home alert card ----------


def test_home_alert_hidden_when_no_errors(client, tmp_path):
    r = client.get("/")
    assert r.status_code == 200
    assert "行情拉取失败" not in r.text


def test_home_alert_shows_unresolved_errors(client, tmp_path):
    quotes_io.record_error(
        "600519", "SSE", phase="eod",
        error="429 rate limit", base=tmp_path,
    )
    r = client.get("/")
    assert r.status_code == 200
    assert "行情拉取失败" in r.text
    assert "600519" in r.text
    assert "429 rate limit" in r.text


def test_home_alert_skips_resolved_errors(client, tmp_path):
    quotes_io.record_error("X", "SSE", phase="eod", error="e", base=tmp_path)
    quotes_io.mark_errors_resolved("X", base=tmp_path)
    r = client.get("/")
    assert "行情拉取失败" not in r.text


# ---------- list row 行情 button ----------


def test_list_rows_have_quotes_button(client, tmp_path):
    client.post("/companies/new",
                data={"ticker": "TR", "market": "US", "name": "tr",
                      "industry_slugs": "saas", "currency": "USD"})
    r = client.get("/companies")
    assert r.status_code == 200
    # button text "行情" linking to /prices/<key>
    assert 'href="/prices/US_TR"' in r.text
    assert ">行情<" in r.text


# ---------- detail panel ----------


def test_detail_panel_hidden_when_no_quote(client, tmp_path):
    client.post("/companies/new",
                data={"ticker": "TR", "market": "US", "name": "tr",
                      "industry_slugs": "saas", "currency": "USD"})
    r = client.get("/companies/US_TR")
    assert r.status_code == 200
    # freshness is always returned, so panel renders but shows "尚无数据"
    assert "最新行情" in r.text
    assert "尚无数据" in r.text


def test_detail_panel_shows_latest_quote(client, tmp_path):
    client.post("/companies/new",
                data={"ticker": "TR", "market": "US", "name": "tr",
                      "industry_slugs": "saas", "currency": "USD"})
    insert_quote(tmp_path, ticker="TR", date="2026-04-24",
                 market="US", close=123.45)

    r = client.get("/companies/US_TR")
    assert "最新行情" in r.text
    assert "123.45" in r.text
    assert "2026-04-24" in r.text
    # status-bar link back to prices page
    assert 'href="/prices/US_TR"' in r.text


def test_detail_panel_shows_prev_move_pct(client, tmp_path):
    client.post("/companies/new",
                data={"ticker": "TR", "market": "US", "name": "tr",
                      "industry_slugs": "saas", "currency": "USD"})
    insert_quote(tmp_path, ticker="TR", date="2026-04-23",
                 market="US", close=100.0)
    insert_quote(tmp_path, ticker="TR", date="2026-04-24",
                 market="US", close=110.0)

    r = client.get("/companies/US_TR")
    assert "110.00" in r.text
    assert "+10.00%" in r.text

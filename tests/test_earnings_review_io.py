"""Tests for app.io.earnings_review.

We create a couple of companies with V0 files in ``companies/`` (not through
the HTTP layer), then seed financials via the real module, then exercise the
pending logic.
"""
from pathlib import Path

import pytest

from app.io import earnings_review as er
from app.io import financials as fin
from app.io import v0 as v0_io


def _sample_us_rows(ticker: str) -> list[dict]:
    """Three periods of minimal US financials for earnings-review tests."""
    common = {"ticker": ticker, "report_date": "2024-12-31", "source": "yfinance"}
    return [
        {
            **common,
            "period": "2024Q3", "period_type": "quarterly",
            "report_date": "2024-09-30",
            "total_revenue": 900.0, "gross_profit": 360.0,
            "operating_income": 170.0, "net_income": 120.0,
            "total_assets": 4800.0, "total_equity": 1950.0,
            "operating_cash_flow": 160.0,
        },
        {
            **common,
            "period": "2024Q4", "period_type": "quarterly",
            "report_date": "2024-12-31",
            "total_revenue": 1000.0, "gross_profit": 400.0,
            "operating_income": 200.0, "net_income": 150.0,
            "total_assets": 5000.0, "total_equity": 2000.0,
            "operating_cash_flow": 180.0,
        },
        {
            **common,
            "period": "2024A", "period_type": "annual",
            "report_date": "2024-12-31",
            "total_revenue": 3500.0, "gross_profit": 1400.0,
            "operating_income": 700.0, "net_income": 500.0,
            "total_assets": 5000.0, "total_equity": 2000.0,
            "operating_cash_flow": 650.0,
        },
    ]


def _seed_us(base: Path, ticker: str) -> None:
    conn = fin.connect(base=base)
    try:
        fin.upsert_financials_us(conn, _sample_us_rows(ticker))
        fin.recompute_ratios(conn, ticker, market="US")
    finally:
        conn.close()


@pytest.fixture
def env(tmp_path: Path, monkeypatch):
    from app import config as cfg
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cfg, "FINANCIALS_DB", tmp_path / "data" / "financials.db")
    (tmp_path / "companies").mkdir()
    (tmp_path / "data").mkdir()
    return tmp_path


def _make_v0(env: Path, ticker: str, market: str = "US", **extra_fm) -> None:
    fm = {"ticker": ticker, "market": market, "status": "active", **extra_fm}
    v0_io.write_v0(ticker, market, fm, body="", base=env)


def test_no_financials_means_not_pending(env):
    _make_v0(env, "A")
    assert er.pending_reviews(base=env) == []


def test_financials_but_no_review_is_pending(env):
    _make_v0(env, "A")
    _seed_us(env, "A")
    out = er.pending_reviews(base=env)
    assert len(out) == 1
    assert out[0]["ticker"] == "A"
    assert out[0]["latest_period"] == "2024A"
    assert out[0]["last_reviewed_period"] is None


def test_review_equal_to_latest_is_not_pending(env):
    _make_v0(env, "A", last_reviewed_period="2024A")
    _seed_us(env, "A")
    assert er.pending_reviews(base=env) == []


def test_review_older_than_latest_is_pending(env):
    _make_v0(env, "A", last_reviewed_period="2024Q3")
    _seed_us(env, "A")
    out = er.pending_reviews(base=env)
    assert len(out) == 1
    assert out[0]["latest_period"] == "2024A"
    assert out[0]["last_reviewed_period"] == "2024Q3"


def test_mark_reviewed_persists_and_clears_pending(env):
    _make_v0(env, "A")
    _seed_us(env, "A")
    assert len(er.pending_reviews(base=env)) == 1

    er.mark_reviewed("A", "US", "2024A", base=env)

    doc = v0_io.read_v0("A", "US", base=env)
    assert doc["frontmatter"]["last_reviewed_period"] == "2024A"
    assert er.pending_reviews(base=env) == []


def test_active_positions_sort_before_others(env):
    _make_v0(env, "A", status="draft")
    _make_v0(env, "B", status="active")
    _seed_us(env, "A")
    _seed_us(env, "B")
    out = er.pending_reviews(base=env)
    assert [r["ticker"] for r in out] == ["B", "A"]


def test_company_summary_shape(env):
    _make_v0(env, "A", last_reviewed_period="2024Q3")
    _seed_us(env, "A")
    s = er.company_summary("A", "US", base=env)
    assert s["pending"] is True
    assert s["latest_period"] == "2024A"
    assert s["last_reviewed_period"] == "2024Q3"
    assert len(s["financials"]) == 3
    # V0 body was empty, so sections are empty strings
    assert s["v0_section_5"] == ""


def test_marked_is_idempotent(env):
    _make_v0(env, "A")
    _seed_us(env, "A")
    er.mark_reviewed("A", "US", "2024A", base=env)
    er.mark_reviewed("A", "US", "2024A", base=env)
    assert v0_io.read_v0("A", "US", base=env)["frontmatter"]["last_reviewed_period"] == "2024A"

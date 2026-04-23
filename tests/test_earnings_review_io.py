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


SAMPLE_CSV = """period,period_type,revenue,gross_profit,operating_income,net_income,total_assets,total_equity,operating_cashflow,shares_outstanding
2024Q4,quarterly,1000,400,200,150,5000,2000,180,100
2024Q3,quarterly,900,360,170,120,4800,1950,160,100
2024A,annual,3500,1400,700,500,5000,2000,650,100
"""


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
    fin.import_financials_csv("A", SAMPLE_CSV, base=env)
    out = er.pending_reviews(base=env)
    assert len(out) == 1
    assert out[0]["ticker"] == "A"
    assert out[0]["latest_period"] == "2024A"
    assert out[0]["last_reviewed_period"] is None


def test_review_equal_to_latest_is_not_pending(env):
    _make_v0(env, "A", last_reviewed_period="2024A")
    fin.import_financials_csv("A", SAMPLE_CSV, base=env)
    assert er.pending_reviews(base=env) == []


def test_review_older_than_latest_is_pending(env):
    _make_v0(env, "A", last_reviewed_period="2024Q3")
    fin.import_financials_csv("A", SAMPLE_CSV, base=env)
    out = er.pending_reviews(base=env)
    assert len(out) == 1
    assert out[0]["latest_period"] == "2024A"
    assert out[0]["last_reviewed_period"] == "2024Q3"


def test_mark_reviewed_persists_and_clears_pending(env):
    _make_v0(env, "A")
    fin.import_financials_csv("A", SAMPLE_CSV, base=env)
    assert len(er.pending_reviews(base=env)) == 1

    er.mark_reviewed("A", "US", "2024A", base=env)

    doc = v0_io.read_v0("A", "US", base=env)
    assert doc["frontmatter"]["last_reviewed_period"] == "2024A"
    assert er.pending_reviews(base=env) == []


def test_active_positions_sort_before_others(env):
    _make_v0(env, "A", status="draft")
    _make_v0(env, "B", status="active")
    fin.import_financials_csv("A", SAMPLE_CSV, base=env)
    fin.import_financials_csv("B", SAMPLE_CSV, base=env)
    out = er.pending_reviews(base=env)
    assert [r["ticker"] for r in out] == ["B", "A"]


def test_company_summary_shape(env):
    _make_v0(env, "A", last_reviewed_period="2024Q3")
    fin.import_financials_csv("A", SAMPLE_CSV, base=env)
    s = er.company_summary("A", "US", base=env)
    assert s["pending"] is True
    assert s["latest_period"] == "2024A"
    assert s["last_reviewed_period"] == "2024Q3"
    assert len(s["financials"]) == 3
    # V0 body was empty, so sections are empty strings
    assert s["v0_section_5"] == ""


def test_marked_is_idempotent(env):
    _make_v0(env, "A")
    fin.import_financials_csv("A", SAMPLE_CSV, base=env)
    er.mark_reviewed("A", "US", "2024A", base=env)
    er.mark_reviewed("A", "US", "2024A", base=env)
    assert v0_io.read_v0("A", "US", base=env)["frontmatter"]["last_reviewed_period"] == "2024A"

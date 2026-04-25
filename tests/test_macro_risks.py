"""Tests for extreme-risk pre-trigger checks (DESIGN §3.8)."""
from datetime import date, timedelta
from pathlib import Path

import pytest

from app import config as cfg
from app.io import financials as fin_io
from app.io import macro_risks as mr
from app.io import performance as perf_io
from app.io import regime as regime_io
from tests.helpers import insert_quote


@pytest.fixture
def base(tmp_path, monkeypatch):
    (tmp_path / "companies").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "macro" / "regime").mkdir(parents=True)
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cfg, "FINANCIALS_DB", tmp_path / "data" / "financials.db")
    return tmp_path


def _add_company(base: Path, ticker: str, sector: str) -> None:
    d = base / "companies" / f"US_{ticker}"
    d.mkdir()
    (d / "meta.md").write_text(
        f"---\nticker: {ticker}\nmarket: US\nsector: {sector}\n---\n",
        encoding="utf-8",
    )


# --- VIX sustained ----------------------------------------------------------


def test_vix_not_enough_data(base):
    # fewer than 7 sessions → None
    rows = [("2026-04-21", "VIX", 45.0), ("2026-04-22", "VIX", 46.0)]
    perf_io.upsert_benchmark_closes(rows, base=base)
    assert mr.check_vix_sustained(base=base) is None


def test_vix_spike_triggers(base):
    today = date(2026, 4, 22)
    rows = [
        ((today - timedelta(days=i)).isoformat(), "VIX", 42.0 + i)
        for i in range(7)
    ]
    perf_io.upsert_benchmark_closes(rows, base=base)
    v = mr.check_vix_sustained(base=base)
    assert v is not None
    assert v["kind"] == "vix_sustained_spike"
    assert v["actual"] >= 40.0


def test_vix_one_dip_no_trigger(base):
    today = date(2026, 4, 22)
    rows = [
        ((today - timedelta(days=i)).isoformat(), "VIX", 42.0)
        for i in range(7)
    ]
    # Replace one session with 35 (dip below threshold)
    rows[3] = (rows[3][0], "VIX", 35.0)
    perf_io.upsert_benchmark_closes(rows, base=base)
    assert mr.check_vix_sustained(base=base) is None


# --- credit widening --------------------------------------------------------


def test_credit_widening_trigger(base):
    regime_io.write("2026-Q1", {
        "quarter": "2026-Q1", "credit_spread_bps": 80,
        "vix_level": 18, "verdict": "neutral",
        "retail_sentiment": "neutral", "macro_reaction": "tolerant",
        "valuation_percentile": 50,
    }, "", base=base)
    regime_io.write("2026-Q2", {
        "quarter": "2026-Q2", "credit_spread_bps": 220,
        "vix_level": 35, "verdict": "cold",
        "retail_sentiment": "fearful", "macro_reaction": "sensitive",
        "valuation_percentile": 30,
    }, "", base=base)
    v = mr.check_credit_widening(base=base)
    assert v is not None
    assert v["kind"] == "credit_widening"
    assert v["actual"] == pytest.approx(140.0)


def test_credit_widening_none_when_flat(base):
    regime_io.write("2026-Q1", {
        "quarter": "2026-Q1", "credit_spread_bps": 80,
        "vix_level": 18, "verdict": "neutral",
        "retail_sentiment": "neutral", "macro_reaction": "tolerant",
        "valuation_percentile": 50,
    }, "", base=base)
    regime_io.write("2026-Q2", {
        "quarter": "2026-Q2", "credit_spread_bps": 90,
        "vix_level": 20, "verdict": "neutral",
        "retail_sentiment": "neutral", "macro_reaction": "tolerant",
        "valuation_percentile": 52,
    }, "", base=base)
    assert mr.check_credit_widening(base=base) is None


def test_credit_widening_needs_two_quarters(base):
    # Only one quarter → None
    regime_io.write("2026-Q1", {
        "quarter": "2026-Q1", "credit_spread_bps": 300,
        "vix_level": 25, "verdict": "cold",
        "retail_sentiment": "fearful", "macro_reaction": "sensitive",
        "valuation_percentile": 40,
    }, "", base=base)
    assert mr.check_credit_widening(base=base) is None


# --- sector crash -----------------------------------------------------------


def test_sector_crash_trigger(base):
    for ticker in ("AAA", "BBB", "CCC"):
        _add_company(base, ticker, "saas")
    _add_company(base, "CTRL", "consumer")  # unaffected sector

    today = date(2026, 4, 22)
    ref_day = today - timedelta(days=10)
    # three SaaS tickers crash ≥ 20%
    for ticker in ("AAA", "BBB", "CCC"):
        insert_quote(base=base, ticker=ticker, close=100.0, date=ref_day)
        insert_quote(base=base, ticker=ticker, close=75.0, date=today)
    # control stock flat
    insert_quote(base=base, ticker="CTRL", close=50.0, date=ref_day)
    insert_quote(base=base, ticker="CTRL", close=50.0, date=today)

    vs = mr.check_sector_crash(today=today, base=base)
    assert len(vs) == 1
    assert vs[0]["kind"] == "sector_crash"
    assert vs[0]["entity"] == "saas"
    assert set(vs[0]["tickers"]) == {"AAA", "BBB", "CCC"}


def test_sector_crash_needs_three_names(base):
    for ticker in ("AAA", "BBB"):
        _add_company(base, ticker, "saas")

    today = date(2026, 4, 22)
    ref_day = today - timedelta(days=10)
    for ticker in ("AAA", "BBB"):
        insert_quote(base=base, ticker=ticker, close=100.0, date=ref_day)
        insert_quote(base=base, ticker=ticker, close=70.0, date=today)

    vs = mr.check_sector_crash(today=today, base=base)
    assert vs == []


def test_sector_crash_ignores_minor_dips(base):
    for ticker in ("A", "B", "C"):
        _add_company(base, ticker, "saas")
    today = date(2026, 4, 22)
    ref_day = today - timedelta(days=10)
    for ticker in ("A", "B", "C"):
        insert_quote(base=base, ticker=ticker, close=100.0, date=ref_day)
        insert_quote(base=base, ticker=ticker, close=90.0, date=today)
    vs = mr.check_sector_crash(today=today, base=base)
    assert vs == []


# --- aggregate --------------------------------------------------------------


def test_all_extreme_risks_quiet_when_empty(base):
    assert mr.all_extreme_risks(base=base) == []

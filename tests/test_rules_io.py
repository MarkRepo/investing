"""Tests for portfolio rules IO and evaluation."""
from pathlib import Path

import pytest

from app import config as cfg
from app.io import rules as rules_io


@pytest.fixture
def base(tmp_path, monkeypatch):
    (tmp_path / "portfolio").mkdir()
    (tmp_path / "companies").mkdir()
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "PORTFOLIO_DIR", tmp_path / "portfolio")
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    return tmp_path


def _add_company(
    base: Path, market: str, ticker: str, sector: str, themes: list[str] | None = None
) -> None:
    d = base / "companies" / f"{market}_{ticker}"
    d.mkdir()
    lines = [
        "---",
        f"ticker: {ticker}",
        f"market: {market}",
        f"sector: {sector}",
    ]
    if themes:
        lines.append(f"themes: [{', '.join(themes)}]")
    lines.extend(["---", ""])
    (d / "meta.md").write_text("\n".join(lines), encoding="utf-8")


def test_write_and_read_roundtrip(base):
    rules_io.write({"max_single_pct": 20, "min_cash_pct": 10}, "说明正文", base=base)
    state = rules_io.read(base=base)
    assert state["limits"]["max_single_pct"] == 20.0
    assert state["limits"]["min_cash_pct"] == 10.0
    assert "说明正文" in state["body"]


def test_write_rejects_out_of_range(base):
    with pytest.raises(ValueError):
        rules_io.write({"max_single_pct": 150}, "", base=base)


def test_write_rejects_non_numeric(base):
    with pytest.raises(ValueError):
        rules_io.write({"max_single_pct": "abc"}, "", base=base)


def test_evaluate_no_rules_means_no_violations(base):
    positions = [{"ticker": "AAA", "market": "US", "position_pct": "40"}]
    res = rules_io.evaluate(positions, base=base)
    assert res["violations"] == []
    assert res["totals"]["total_pct"] == 40.0


def test_evaluate_flags_oversized_position(base):
    rules_io.write({"max_single_pct": 20}, "", base=base)
    positions = [{"ticker": "AAA", "market": "US", "position_pct": "30"}]
    res = rules_io.evaluate(positions, base=base)
    assert len(res["violations"]) == 1
    v = res["violations"][0]
    assert v["kind"] == "single_position"
    assert v["entity"] == "US:AAA"
    assert v["actual"] == 30.0


def test_evaluate_flags_sector_over_limit(base):
    rules_io.write({"max_sector_pct": 30}, "", base=base)
    _add_company(base, "US", "AAA", "saas")
    _add_company(base, "US", "BBB", "saas")
    positions = [
        {"ticker": "AAA", "market": "US", "position_pct": "20"},
        {"ticker": "BBB", "market": "US", "position_pct": "15"},
    ]
    res = rules_io.evaluate(positions, base=base)
    sector_vs = [v for v in res["violations"] if v["kind"] == "sector_exposure"]
    assert len(sector_vs) == 1
    assert sector_vs[0]["entity"] == "saas"
    assert sector_vs[0]["actual"] == pytest.approx(35.0)


def test_evaluate_flags_cash_floor(base):
    rules_io.write({"min_cash_pct": 20}, "", base=base)
    positions = [{"ticker": "AAA", "market": "US", "position_pct": "85"}]
    res = rules_io.evaluate(positions, base=base)
    cash_vs = [v for v in res["violations"] if v["kind"] == "cash_floor"]
    assert len(cash_vs) == 1
    assert cash_vs[0]["actual"] == pytest.approx(15.0)


def test_unclassified_companies_bucket(base):
    rules_io.write({"max_sector_pct": 30}, "", base=base)
    # No meta files → everything bucketed as (unclassified)
    positions = [
        {"ticker": "AAA", "market": "US", "position_pct": "20"},
        {"ticker": "BBB", "market": "US", "position_pct": "15"},
    ]
    res = rules_io.evaluate(positions, base=base)
    assert "(unclassified)" in res["totals"]["by_sector"]
    sector_vs = [v for v in res["violations"] if v["kind"] == "sector_exposure"]
    assert sector_vs and sector_vs[0]["entity"] == "(unclassified)"


def test_evaluate_flags_theme_over_limit(base):
    rules_io.write({"max_theme_pct": 40}, "", base=base)
    _add_company(base, "US", "AI1", "saas", themes=["ai", "platforms"])
    _add_company(base, "US", "AI2", "saas", themes=["ai"])
    _add_company(base, "US", "CLN", "cyclical", themes=["clean_energy"])
    positions = [
        {"ticker": "AI1", "market": "US", "position_pct": "25"},
        {"ticker": "AI2", "market": "US", "position_pct": "20"},
        {"ticker": "CLN", "market": "US", "position_pct": "10"},
    ]
    res = rules_io.evaluate(positions, base=base)
    theme_vs = [v for v in res["violations"] if v["kind"] == "theme_exposure"]
    assert len(theme_vs) == 1
    assert theme_vs[0]["entity"] == "ai"
    assert theme_vs[0]["actual"] == pytest.approx(45.0)
    # by_theme surfaces all themes
    assert res["totals"]["by_theme"]["ai"] == pytest.approx(45.0)
    assert res["totals"]["by_theme"]["platforms"] == pytest.approx(25.0)
    assert res["totals"]["by_theme"]["clean_energy"] == pytest.approx(10.0)


def test_theme_unset_means_no_theme_violations(base):
    rules_io.write({"max_theme_pct": 10}, "", base=base)
    _add_company(base, "US", "PLAIN", "saas")  # no themes
    positions = [{"ticker": "PLAIN", "market": "US", "position_pct": "25"}]
    res = rules_io.evaluate(positions, base=base)
    theme_vs = [v for v in res["violations"] if v["kind"] == "theme_exposure"]
    assert theme_vs == []

"""Tests for monthly performance comparison IO."""
from datetime import date
from pathlib import Path

import pytest

from app import config as cfg
from app.io import performance as perf
from app.io import prices


@pytest.fixture
def fixture_base(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    (tmp_path / "portfolio").mkdir()
    (tmp_path / "portfolio" / "positions.md").write_text(
        "# 当前持仓\n\n"
        "| ticker | market | entry_date | avg_cost | shares | position_pct | v0_link |\n"
        "|---|---|---|---|---|---|---|\n"
        "| AAPL | US | 2025-01-05 | 150 | 10 | 5 | /c/US_AAPL/v0 |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cfg, "FINANCIALS_DB", tmp_path / "data" / "financials.db")
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "PORTFOLIO_DIR", tmp_path / "portfolio")
    return tmp_path


def test_parse_benchmark_accepts_valid_rows():
    rows, errs = perf.parse_benchmark_freeform(
        """
        2025-01-31  SPY 500
        2025-02-28,SPY,510
        # comment ignored
        """
    )
    assert errs == []
    assert rows == [("2025-01-31", "SPY", 500.0), ("2025-02-28", "SPY", 510.0)]


def test_parse_benchmark_flags_bad_rows():
    rows, errs = perf.parse_benchmark_freeform(
        """
        2025-01-31 SPY 0
        bad line
        2025-02-28 SPY -1
        """
    )
    assert rows == []
    errors = {e["error"] for e in errs}
    assert "close must be > 0" in errors
    assert "cannot parse" in errors


def test_benchmark_monthly_computes_mom(fixture_base):
    perf.upsert_benchmark_closes([
        ("2025-01-31", "SPY", 500.0),
        ("2025-02-28", "SPY", 510.0),
        ("2025-03-31", "SPY", 520.0),
    ], base=fixture_base)
    months = perf.benchmark_monthly("SPY", base=fixture_base)
    assert [m["month"] for m in months] == ["2025-01", "2025-02", "2025-03"]
    assert months[0]["ret_mom_pct"] is None
    assert months[1]["ret_mom_pct"] == pytest.approx(2.0)


def test_portfolio_monthly_marks_current_shares(fixture_base):
    prices.upsert_close("AAPL", 150, date(2025, 1, 31), base=fixture_base)
    prices.upsert_close("AAPL", 160, date(2025, 2, 28), base=fixture_base)
    months = perf.portfolio_monthly(base=fixture_base)
    assert [m["month"] for m in months] == ["2025-01", "2025-02"]
    assert months[0]["mv"] == 1500.0
    assert months[1]["ret_mom_pct"] == pytest.approx((1600 - 1500) / 1500 * 100)


def test_compare_spreads_are_cumulative(fixture_base):
    perf.upsert_benchmark_closes([
        ("2025-01-31", "SPY", 500.0),
        ("2025-02-28", "SPY", 510.0),
    ], base=fixture_base)
    prices.upsert_close("AAPL", 150, date(2025, 1, 31), base=fixture_base)
    prices.upsert_close("AAPL", 165, date(2025, 2, 28), base=fixture_base)
    res = perf.compare("SPY", base=fixture_base)
    assert len(res["rows"]) == 2
    # portfolio +10%, benchmark +2%, spread +8%
    last = res["rows"][-1]
    assert last["portfolio_ret_pct"] == pytest.approx(10.0)
    assert last["benchmark_ret_pct"] == pytest.approx(2.0)
    assert last["spread_pct"] == pytest.approx(8.0)


def test_compare_only_shared_months(fixture_base):
    # Benchmark covers Jan/Feb; prices only Feb → shared = {Feb} only
    perf.upsert_benchmark_closes([
        ("2025-01-31", "SPY", 500.0),
        ("2025-02-28", "SPY", 510.0),
    ], base=fixture_base)
    prices.upsert_close("AAPL", 160, date(2025, 2, 28), base=fixture_base)
    res = perf.compare("SPY", base=fixture_base)
    assert len(res["rows"]) == 1
    assert res["rows"][0]["month"] == "2025-02"


def test_compare_empty_without_holdings(fixture_base):
    perf.upsert_benchmark_closes([("2025-01-31", "SPY", 500.0)], base=fixture_base)
    (fixture_base / "portfolio" / "positions.md").write_text(
        "# 当前持仓\n\n"
        "| ticker | market | entry_date | avg_cost | shares | position_pct | v0_link |\n"
        "|---|---|---|---|---|---|---|\n",
        encoding="utf-8",
    )
    res = perf.compare("SPY", base=fixture_base)
    assert res["rows"] == []

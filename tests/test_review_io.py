"""Tests for quarterly review aggregation."""
from datetime import date
from pathlib import Path

import pytest

from app import config as cfg
from app.io import journal as journal_io
from app.io import review as review_io


@pytest.fixture
def fixture_base(tmp_path, monkeypatch):
    (tmp_path / "journal" / "decisions").mkdir(parents=True)
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "JOURNAL_DIR", tmp_path / "journal")
    return tmp_path


def _make_entry(base: Path, d: date, ticker: str, action: str, process: dict, result: float | None):
    paths = journal_io.create_entry(d, ticker, "US", action, base=base)
    doc = journal_io.read_entry(paths.entry_id, base=base)
    fm = dict(doc["frontmatter"])
    fm.update(process)
    if result is not None:
        fm["result_quality"] = result
    journal_io.write_entry(paths.entry_id, fm, doc["body"], base=base)
    return paths.entry_id


def test_list_quarters_groups_by_fiscal_quarter(fixture_base):
    _make_entry(fixture_base, date(2026, 1, 5), "AAPL", "buy", {"process_quality": 4}, None)
    _make_entry(fixture_base, date(2026, 4, 5), "MSFT", "buy", {"process_quality": 3}, None)
    _make_entry(fixture_base, date(2025, 12, 30), "GOOG", "pass", {"process_quality": 2}, 3)
    qs = review_io.list_quarters(base=fixture_base)
    assert qs == ["2026-Q2", "2026-Q1", "2025-Q4"]


def test_quarter_summary_averages_and_mismatch(fixture_base):
    # Good process (4) + bad result (1) → should flag as good_process_bad_result
    _make_entry(
        fixture_base, date(2026, 1, 10), "GOOD", "buy",
        {"process_quality": 4, "process_rigor": 4, "process_rule_adherence": 4, "process_emotional_control": 4},
        1,
    )
    # Bad process (2) + good result (5) → should flag as bad_process_good_result
    _make_entry(
        fixture_base, date(2026, 2, 20), "LUCKY", "buy",
        {"process_quality": 2, "process_rigor": 2, "process_rule_adherence": 2, "process_emotional_control": 2},
        5,
    )
    # Unfilled result
    _make_entry(
        fixture_base, date(2026, 3, 5), "PEND", "buy",
        {"process_quality": 3, "process_rigor": 3, "process_rule_adherence": 3, "process_emotional_control": 3},
        None,
    )
    s = review_io.quarter_summary("2026-Q1", base=fixture_base)
    assert s["count"] == 3
    assert s["avg_process"] == pytest.approx(3.0)
    assert len(s["mismatches"]["good_process_bad_result"]) == 1
    assert s["mismatches"]["good_process_bad_result"][0]["ticker"] == "GOOD"
    assert len(s["mismatches"]["bad_process_good_result"]) == 1
    assert s["mismatches"]["bad_process_good_result"][0]["ticker"] == "LUCKY"
    assert len(s["mismatches"]["unfilled_result"]) == 1
    assert s["mismatches"]["unfilled_result"][0]["ticker"] == "PEND"


def test_quarter_summary_excludes_other_quarters(fixture_base):
    _make_entry(fixture_base, date(2025, 12, 1), "OLD", "buy", {"process_quality": 4}, 4)
    _make_entry(fixture_base, date(2026, 1, 5), "NEW", "buy", {"process_quality": 3}, 3)
    s = review_io.quarter_summary("2026-Q1", base=fixture_base)
    tickers = [r["ticker"] for r in s["entries"]]
    assert tickers == ["NEW"]


def test_by_action_groups(fixture_base):
    _make_entry(fixture_base, date(2026, 1, 5), "AAPL", "buy", {"process_quality": 4}, 4)
    _make_entry(fixture_base, date(2026, 2, 5), "MSFT", "pass", {"process_quality": 3}, 3)
    _make_entry(fixture_base, date(2026, 3, 5), "GOOG", "buy", {"process_quality": 5}, 5)
    s = review_io.quarter_summary("2026-Q1", base=fixture_base)
    assert s["by_action"]["buy"]["count"] == 2
    assert s["by_action"]["pass"]["count"] == 1
    assert s["by_action"]["buy"]["avg_process"] == pytest.approx(4.5)

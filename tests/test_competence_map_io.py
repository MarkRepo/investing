"""Tests for yearly competence map aggregation."""
from datetime import date
from pathlib import Path

import pytest

from app import config as cfg
from app.io import competence_map as cmap
from app.io import journal as journal_io


@pytest.fixture
def base(tmp_path, monkeypatch):
    (tmp_path / "companies").mkdir()
    (tmp_path / "journal" / "decisions").mkdir(parents=True)
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(cfg, "JOURNAL_DIR", tmp_path / "journal")
    return tmp_path


def _add_company(base: Path, market: str, ticker: str, sector: str) -> None:
    d = base / "companies" / f"{market}_{ticker}"
    d.mkdir()
    (d / "meta.md").write_text(
        f"---\nticker: {ticker}\nmarket: {market}\nsector: {sector}\n---\n",
        encoding="utf-8",
    )


def _add_journal(base: Path, d: date, market: str, ticker: str, action: str, process: float, result: float | None):
    paths = journal_io.create_entry(d, ticker, market, action, base=base)
    doc = journal_io.read_entry(paths.entry_id, base=base)
    fm = dict(doc["frontmatter"])
    fm["process_quality"] = process
    fm["process_rigor"] = process
    fm["process_rule_adherence"] = process
    fm["process_emotional_control"] = process
    if result is not None:
        fm["result_quality"] = result
    journal_io.write_entry(paths.entry_id, fm, doc["body"], base=base)


def test_aggregation_groups_by_sector(base):
    _add_company(base, "US", "AAA", "consumer")
    _add_company(base, "US", "BBB", "consumer")
    _add_company(base, "US", "CCC", "saas")
    _add_journal(base, date(2026, 1, 5), "US", "AAA", "buy", 4, 5)
    _add_journal(base, date(2026, 2, 10), "US", "BBB", "buy", 4, 3)
    _add_journal(base, date(2026, 3, 1), "US", "CCC", "buy", 3, 1)
    r = cmap.yearly_map(2026, base=base)
    assert r["total"] == 3
    sectors = {s["sector"]: s for s in r["by_sector"]}
    assert sectors["consumer"]["count"] == 2
    assert sectors["consumer"]["avg_result"] == pytest.approx(4.0)
    assert sectors["saas"]["count"] == 1


def test_unclassified_bucket_when_no_meta(base):
    _add_journal(base, date(2026, 1, 5), "US", "XXX", "buy", 3, 3)
    r = cmap.yearly_map(2026, base=base)
    assert r["by_sector"][0]["sector"] == cmap.UNCLASSIFIED


def test_hit_rate_only_counts_buy_add(base):
    _add_company(base, "US", "AAA", "consumer")
    _add_company(base, "US", "BBB", "consumer")
    _add_journal(base, date(2026, 1, 5), "US", "AAA", "buy", 4, 5)   # hit
    _add_journal(base, date(2026, 2, 1), "US", "BBB", "buy", 3, 2)   # miss
    _add_journal(base, date(2026, 3, 1), "US", "AAA", "pass", 3, None)  # excluded
    r = cmap.yearly_map(2026, base=base)
    consumer = next(s for s in r["by_sector"] if s["sector"] == "consumer")
    assert consumer["hit_rate"] == pytest.approx(0.5)


def test_gap_is_result_minus_process(base):
    _add_company(base, "US", "AAA", "saas")
    _add_journal(base, date(2026, 1, 5), "US", "AAA", "buy", 2, 5)
    r = cmap.yearly_map(2026, base=base)
    assert r["by_sector"][0]["gap"] == pytest.approx(3.0)


def test_year_filter(base):
    _add_company(base, "US", "AAA", "saas")
    _add_journal(base, date(2025, 5, 1), "US", "AAA", "buy", 3, 3)
    _add_journal(base, date(2026, 5, 1), "US", "AAA", "buy", 4, 4)
    r = cmap.yearly_map(2026, base=base)
    assert r["total"] == 1
    assert cmap.available_years(base=base) == [2026, 2025]

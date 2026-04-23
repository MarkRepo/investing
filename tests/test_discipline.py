"""Tests for self-discipline dashboard."""
from datetime import date
from pathlib import Path

import pytest

from app import config as cfg
from app.io import discipline
from app.io import journal as journal_io


@pytest.fixture
def base(tmp_path, monkeypatch):
    (tmp_path / "journal" / "decisions").mkdir(parents=True)
    (tmp_path / "journal" / "quarterly-reviews").mkdir()
    (tmp_path / "companies").mkdir()
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "JOURNAL_DIR", tmp_path / "journal")
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    return tmp_path


def _make_entry(
    base: Path, date_str: str, ticker: str, action: str,
    with_v0_snapshot: bool = True, body_extra: str = "",
) -> str:
    entry_date = date.fromisoformat(date_str)
    paths = journal_io.create_entry(
        entry_date=entry_date,
        ticker=ticker,
        market="US",
        action=action,
        price=10,
        position_change=5,
        v0_snapshot_path="companies/US_X/v0.md@abc" if with_v0_snapshot else "",
        v0_snapshot_hash_="abc123" if with_v0_snapshot else "",
        base=base,
    )
    if body_extra:
        text = paths.file_path.read_text(encoding="utf-8")
        paths.file_path.write_text(text + "\n" + body_extra, encoding="utf-8")
    return paths.entry_id


# --- no-V0 buys -------------------------------------------------------------


def test_no_v0_snapshot_buys_empty(base):
    assert discipline.no_v0_snapshot_buys(base=base) == []


def test_no_v0_snapshot_buys_flags_only_buys_without_snapshot(base):
    _make_entry(base, "2026-04-01", "AAA", "buy", with_v0_snapshot=False)
    _make_entry(base, "2026-04-02", "BBB", "buy", with_v0_snapshot=True)
    _make_entry(base, "2026-04-03", "CCC", "add", with_v0_snapshot=False)
    _make_entry(base, "2026-04-04", "DDD", "sell", with_v0_snapshot=False)  # sells don't count
    out = discipline.no_v0_snapshot_buys(base=base)
    tickers = {e["ticker"] for e in out}
    assert tickers == {"AAA", "CCC"}


# --- emotional sells --------------------------------------------------------


def test_emotional_sells_flags_noise_keywords(base):
    # A sell referencing "央行加息" (noise list) vs a clean sell
    _make_entry(base, "2026-04-01", "AAA", "sell", body_extra="因为央行加息+利率上行，卖出")
    _make_entry(base, "2026-04-02", "BBB", "sell", body_extra="单位经济恶化，GMV 连续 3 季度负增长")
    out = discipline.emotional_sells(base=base)
    tickers = {e["ticker"] for e in out}
    assert "AAA" in tickers
    assert "BBB" not in tickers


def test_emotional_sells_ignores_buys(base):
    _make_entry(base, "2026-04-01", "X", "buy", body_extra="宏观利率 VIX 都不影响")
    assert discipline.emotional_sells(base=base) == []


# --- review gaps ------------------------------------------------------------


def test_review_gaps_no_reviews(base):
    today = date(2026, 10, 15)  # Q4
    gaps = discipline.review_gaps(today=today, base=base)
    assert gaps["consecutive_missing"] >= 2
    assert gaps["red_flag"] is True
    current = [r for r in gaps["recent"] if r["is_current"]]
    assert current and current[0]["quarter"] == "2026-Q4"


def test_review_gaps_all_reviewed(base):
    (base / "journal" / "quarterly-reviews" / "2026-Q1.md").write_text("ok")
    (base / "journal" / "quarterly-reviews" / "2026-Q2.md").write_text("ok")
    today = date(2026, 8, 15)  # Q3
    gaps = discipline.review_gaps(today=today, base=base)
    assert gaps["consecutive_missing"] == 0
    assert gaps["red_flag"] is False


def test_review_gaps_one_gap_not_red(base):
    (base / "journal" / "quarterly-reviews" / "2026-Q1.md").write_text("ok")
    today = date(2026, 8, 15)  # Q3; Q2 missing, Q1 present
    gaps = discipline.review_gaps(today=today, base=base)
    assert gaps["consecutive_missing"] == 1
    assert gaps["red_flag"] is False


# --- summary -----------------------------------------------------------------


def test_summary_shape(base):
    payload = discipline.summary(today=date(2026, 4, 1), base=base)
    assert "no_v0_count" in payload
    assert "emotional_sell_count" in payload
    assert "review_gaps" in payload
    assert "noise_keywords" in payload

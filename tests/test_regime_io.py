"""Tests for regime (市场钟摆) IO."""
from pathlib import Path

import pytest

from app import config as cfg
from app.io import regime as regime_io


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    return tmp_path


def test_write_and_read_roundtrip(base):
    fm = {
        "valuation_percentile": 78,
        "credit_spread_bps": 95,
        "vix_level": 14.5,
        "retail_sentiment": "greedy",
        "macro_reaction": "tolerant",
        "verdict": "hot",
        "position_hint": "控制新开仓",
        "cash_floor_hint": 20,
    }
    regime_io.write("2026-Q2", fm, "# 说明\n估值接近 2021 年高位", base=base)
    doc = regime_io.read("2026-Q2", base=base)
    assert doc["frontmatter"]["verdict"] == "hot"
    assert doc["frontmatter"]["quarter"] == "2026-Q2"
    assert "2021" in doc["body"]


def test_list_quarters_sorted_desc(base):
    regime_io.write("2025-Q4", {"verdict": "cold"}, "", base=base)
    regime_io.write("2026-Q1", {"verdict": "neutral"}, "", base=base)
    regime_io.write("2026-Q2", {"verdict": "hot"}, "", base=base)
    assert regime_io.list_quarters(base=base) == ["2026-Q2", "2026-Q1", "2025-Q4"]


def test_latest_returns_most_recent(base):
    regime_io.write("2025-Q4", {"verdict": "cold"}, "", base=base)
    regime_io.write("2026-Q1", {"verdict": "neutral"}, "", base=base)
    latest = regime_io.latest(base=base)
    assert latest["frontmatter"]["quarter"] == "2026-Q1"


def test_write_rejects_bad_quarter(base):
    with pytest.raises(ValueError):
        regime_io.write("2026Q1", {"verdict": "hot"}, "", base=base)


def test_write_rejects_bad_verdict(base):
    with pytest.raises(ValueError):
        regime_io.write("2026-Q1", {"verdict": "boiling"}, "", base=base)


def test_write_rejects_bad_percentile(base):
    with pytest.raises(ValueError):
        regime_io.write("2026-Q1", {"valuation_percentile": 150}, "", base=base)


def test_pointer_file_auto_refreshed(base):
    regime_io.write("2026-Q1", {"verdict": "neutral", "valuation_percentile": 50}, "", base=base)
    pointer = base / "macro" / "regime.md"
    assert pointer.exists()
    text = pointer.read_text(encoding="utf-8")
    assert "2026-Q1" in text
    assert "neutral" in text

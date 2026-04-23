"""Tests for catalyst calendar IO."""
from datetime import date
from pathlib import Path

import pytest

from app import config as cfg
from app.io import catalysts as cat_io


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    return tmp_path


def test_add_then_list(base):
    cat_io.add({"date": "2026-05-10", "kind": "earnings", "ticker": "US_HIMS", "title": "Q1"}, base=base)
    cat_io.add({"date": "2026-04-25", "kind": "fda", "ticker": "US_HIMS", "title": "GLP-1 ruling"}, base=base)
    rows = cat_io.list_all(base=base)
    assert [r["date"] for r in rows] == ["2026-04-25", "2026-05-10"]


def test_add_rejects_bad_date(base):
    with pytest.raises(ValueError):
        cat_io.add({"date": "tomorrow", "kind": "earnings", "title": "x"}, base=base)


def test_add_rejects_bad_kind(base):
    with pytest.raises(ValueError):
        cat_io.add({"date": "2026-05-10", "kind": "pizza", "title": "x"}, base=base)


def test_add_requires_title(base):
    with pytest.raises(ValueError):
        cat_io.add({"date": "2026-05-10", "kind": "earnings", "title": ""}, base=base)


def test_upcoming_within_window(base):
    today = date(2026, 4, 20)
    cat_io.add({"date": "2026-04-22", "kind": "earnings", "ticker": "US_A", "title": "A Q1"}, base=base)
    cat_io.add({"date": "2026-04-30", "kind": "earnings", "ticker": "US_B", "title": "B Q1"}, base=base)
    cat_io.add({"date": "2026-05-15", "kind": "earnings", "ticker": "US_C", "title": "C Q1"}, base=base)
    cat_io.add({"date": "2026-04-10", "kind": "earnings", "ticker": "US_D", "title": "past"}, base=base)
    u = cat_io.upcoming(base=base, within_days=7, today=today)
    tickers = [r["ticker"] for r in u]
    assert tickers == ["US_A"]
    # Wider window catches both
    u2 = cat_io.upcoming(base=base, within_days=15, today=today)
    assert [r["ticker"] for r in u2] == ["US_A", "US_B"]


def test_delete_by_index(base):
    cat_io.add({"date": "2026-04-22", "kind": "earnings", "ticker": "US_A", "title": "first"}, base=base)
    cat_io.add({"date": "2026-04-30", "kind": "earnings", "ticker": "US_B", "title": "second"}, base=base)
    cat_io.delete(0, base=base)  # deletes first (sorted)
    remaining = [r["ticker"] for r in cat_io.list_all(base=base)]
    assert remaining == ["US_B"]


def test_delete_out_of_range(base):
    with pytest.raises(IndexError):
        cat_io.delete(5, base=base)

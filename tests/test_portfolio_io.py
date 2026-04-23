from datetime import date
from pathlib import Path

import pytest

from app.io import portfolio, v0 as v0io


def _write_draft_v0(base: Path, ticker: str, market: str) -> None:
    base_companies = base / "companies" / f"{market}_{ticker}"
    base_companies.mkdir(parents=True)
    (base_companies / "v0.md").write_text(
        "---\n"
        f"ticker: {ticker}\n"
        f"market: {market}\n"
        "entry_date:\n"
        "position_size_pct: 0\n"
        "status: draft\n"
        "last_reviewed: 2026-04-01\n"
        "---\n\n"
        "# V0\n"
    )


def _setup(tmp_path: Path) -> None:
    (tmp_path / "portfolio").mkdir()


def test_upsert_and_read(tmp_path):
    _setup(tmp_path)
    portfolio.upsert_position(
        {
            "ticker": "HIMS",
            "market": "US",
            "entry_date": "2026-04-23",
            "avg_cost": "19",
            "shares": "100",
            "position_pct": "5",
            "v0_link": "/companies/US_HIMS/v0",
        },
        base=tmp_path,
    )
    rows = portfolio.read_positions(base=tmp_path)
    assert [r["ticker"] for r in rows] == ["HIMS"]
    assert rows[0]["position_pct"] == "5"


def test_upsert_replaces_existing_row(tmp_path):
    _setup(tmp_path)
    base = {"ticker": "HIMS", "market": "US", "entry_date": "2026-04-23", "avg_cost": "19",
            "shares": "100", "position_pct": "5", "v0_link": ""}
    portfolio.upsert_position(base, base=tmp_path)
    base["shares"] = "200"
    base["position_pct"] = "10"
    portfolio.upsert_position(base, base=tmp_path)

    rows = portfolio.read_positions(base=tmp_path)
    assert len(rows) == 1
    assert rows[0]["shares"] == "200"


def test_total_position_pct(tmp_path):
    _setup(tmp_path)
    portfolio.upsert_position(
        {"ticker": "A", "market": "US", "position_pct": "5"}, base=tmp_path
    )
    portfolio.upsert_position(
        {"ticker": "B", "market": "US", "position_pct": "10"}, base=tmp_path
    )
    assert portfolio.total_position_pct(portfolio.read_positions(base=tmp_path)) == pytest.approx(15.0)


def test_upsert_flips_draft_v0_to_active(tmp_path):
    _setup(tmp_path)
    _write_draft_v0(tmp_path, "HIMS", "US")

    portfolio.upsert_position(
        {"ticker": "HIMS", "market": "US", "entry_date": "2026-04-23", "position_pct": "5"},
        base=tmp_path,
    )
    doc = v0io.read_v0("HIMS", "US", base=tmp_path)
    assert doc["frontmatter"]["status"] == "active"
    assert doc["frontmatter"]["entry_date"] == "2026-04-23"
    assert doc["frontmatter"]["position_size_pct"] == 5.0


def test_upsert_does_not_overwrite_active_v0(tmp_path):
    _setup(tmp_path)
    base_companies = tmp_path / "companies" / "US_HIMS"
    base_companies.mkdir(parents=True)
    (base_companies / "v0.md").write_text(
        "---\n"
        "ticker: HIMS\nmarket: US\nentry_date: 2026-01-01\n"
        "position_size_pct: 10\nstatus: active\nlast_reviewed: 2026-03-01\n"
        "---\n\n# V0\n"
    )
    portfolio.upsert_position(
        {"ticker": "HIMS", "market": "US", "entry_date": "2026-04-23", "position_pct": "25"},
        base=tmp_path,
    )
    doc = v0io.read_v0("HIMS", "US", base=tmp_path)
    # Original active V0 should be untouched (we only promote draft -> active)
    assert str(doc["frontmatter"]["entry_date"]) == "2026-01-01"
    assert doc["frontmatter"]["position_size_pct"] == 10


def test_upsert_without_v0_is_noop_on_v0(tmp_path):
    _setup(tmp_path)
    # no v0.md exists for this ticker; upsert should still succeed
    portfolio.upsert_position(
        {"ticker": "NEW", "market": "US", "position_pct": "3"}, base=tmp_path
    )
    rows = portfolio.read_positions(base=tmp_path)
    assert rows[0]["ticker"] == "NEW"

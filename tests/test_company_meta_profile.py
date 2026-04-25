"""Tests for meta.md / profile-YYYY.md IO extensions."""
from pathlib import Path

import pytest

from app.io import company


def _make_company(tmp_path: Path, market: str = "US", ticker: str = "HIMS") -> Path:
    d = tmp_path / "companies" / f"{market}_{ticker}"
    (d / "sources").mkdir(parents=True)
    (d / "meta.md").write_text(
        "---\nticker: HIMS\nmarket: US\nname: Hims\nindustry_primary: consumer\n---\n\n# Hims\n",
        encoding="utf-8",
    )
    return d


# --- meta.md ----------------------------------------------------------------


def test_read_meta_with_body(tmp_path):
    _make_company(tmp_path)
    doc = company.read_meta_with_body("HIMS", "US", base=tmp_path)
    assert doc["exists"] is True
    assert doc["frontmatter"]["name"] == "Hims"
    assert "# Hims" in doc["body"]


def test_write_meta_round_trip(tmp_path):
    _make_company(tmp_path)
    company.write_meta(
        "HIMS", "US",
        {
            "name": "Hims & Hers",
            "industry_primary": "consumer",
            "themes": ["weight_loss", "telehealth"],
            "currency": "USD",
        },
        "# Hims & Hers\n\n稳定事实...\n",
        base=tmp_path,
    )
    doc = company.read_meta_with_body("HIMS", "US", base=tmp_path)
    assert doc["frontmatter"]["name"] == "Hims & Hers"
    assert doc["frontmatter"]["themes"] == ["weight_loss", "telehealth"]
    assert "稳定事实" in doc["body"]


def test_write_meta_rejects_bad_sector(tmp_path):
    _make_company(tmp_path)
    with pytest.raises(ValueError, match="industry_primary"):
        company.write_meta(
            "HIMS", "US",
            {"industry_primary": "unknown", "name": "x"},
            "body",
            base=tmp_path,
        )


def test_write_meta_coerces_themes_string(tmp_path):
    _make_company(tmp_path)
    company.write_meta(
        "HIMS", "US",
        {"themes": "ai, weight_loss, clean_energy"},
        "body",
        base=tmp_path,
    )
    doc = company.read_meta_with_body("HIMS", "US", base=tmp_path)
    assert doc["frontmatter"]["themes"] == ["ai", "weight_loss", "clean_energy"]


def test_write_meta_rejects_bad_themes(tmp_path):
    _make_company(tmp_path)
    with pytest.raises(ValueError, match="themes"):
        company.write_meta("HIMS", "US", {"themes": [1, 2]}, "body", base=tmp_path)


def test_write_meta_accepts_arenas_list(tmp_path):
    _make_company(tmp_path)
    company.write_meta(
        "HIMS", "US",
        {"arenas": ["us-telehealth", "us-glp1-compounding"]},
        "body",
        base=tmp_path,
    )
    doc = company.read_meta_with_body("HIMS", "US", base=tmp_path)
    assert doc["frontmatter"]["arenas"] == ["us-telehealth", "us-glp1-compounding"]


def test_write_meta_coerces_arenas_string(tmp_path):
    _make_company(tmp_path)
    company.write_meta(
        "HIMS", "US",
        {"arenas": "a1, a2, a3"},
        "body",
        base=tmp_path,
    )
    doc = company.read_meta_with_body("HIMS", "US", base=tmp_path)
    assert doc["frontmatter"]["arenas"] == ["a1", "a2", "a3"]


def test_write_meta_rejects_bad_arenas(tmp_path):
    _make_company(tmp_path)
    with pytest.raises(ValueError, match="arenas"):
        company.write_meta("HIMS", "US", {"arenas": [1, 2]}, "body", base=tmp_path)


# --- profile-YYYY.md ---------------------------------------------------------


def test_list_profiles_empty(tmp_path):
    _make_company(tmp_path)
    assert company.list_profiles("HIMS", "US", base=tmp_path) == []


def test_write_profile_requires_source(tmp_path):
    _make_company(tmp_path)
    with pytest.raises(ValueError, match="source_file is required"):
        company.write_profile(
            "HIMS", "US", 2026,
            {},
            "body",
            base=tmp_path,
        )


def test_write_profile_rejects_missing_source_file(tmp_path):
    _make_company(tmp_path)
    with pytest.raises(ValueError, match="not found"):
        company.write_profile(
            "HIMS", "US", 2026,
            {"source_file": "sources/fake.md"},
            "body",
            base=tmp_path,
        )


def test_write_profile_with_valid_source(tmp_path):
    d = _make_company(tmp_path)
    (d / "sources" / "2026-annual.md").write_text("# 年报\n", encoding="utf-8")
    company.write_profile(
        "HIMS", "US", 2026,
        {"source_file": "sources/2026-annual.md"},
        "## 业务构成\n订阅 + GLP-1。\n",
        base=tmp_path,
    )
    doc = company.read_profile("HIMS", "US", 2026, base=tmp_path)
    assert doc["exists"] is True
    assert doc["frontmatter"]["source_file"] == "sources/2026-annual.md"
    assert doc["frontmatter"]["year"] == 2026
    assert "订阅 + GLP-1" in doc["body"]

    profiles = company.list_profiles("HIMS", "US", base=tmp_path)
    assert len(profiles) == 1
    assert profiles[0]["year"] == 2026
    assert profiles[0]["source_file"] == "sources/2026-annual.md"


def test_write_profile_accepts_bare_filename(tmp_path):
    d = _make_company(tmp_path)
    (d / "sources" / "2025-annual.md").write_text("# 年报\n", encoding="utf-8")
    company.write_profile(
        "HIMS", "US", 2025,
        {"source_file": "2025-annual.md"},
        "body",
        base=tmp_path,
    )
    doc = company.read_profile("HIMS", "US", 2025, base=tmp_path)
    assert doc["frontmatter"]["source_file"] == "sources/2025-annual.md"


def test_list_sources(tmp_path):
    d = _make_company(tmp_path)
    (d / "sources" / "a.md").write_text("")
    (d / "sources" / "b.pdf").write_text("")
    assert company.list_sources("HIMS", "US", base=tmp_path) == ["a.md", "b.pdf"]

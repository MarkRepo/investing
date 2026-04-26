"""Tests for meta.md / profile-YYYY.md IO extensions."""
from pathlib import Path

import pytest

from app.io import company


def _make_company(tmp_path: Path, market: str = "US", ticker: str = "HIMS") -> Path:
    d = tmp_path / "companies" / f"{market}_{ticker}"
    (d / "sources").mkdir(parents=True)
    (d / "meta.md").write_text(
        "---\nticker: HIMS\nmarket: US\nname: Hims\nindustry_slugs: []\n---\n\n# Hims\n",
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
            "industry_slugs": ["us-telehealth", "us-glp1-compounding"],
            "themes": ["weight_loss", "telehealth"],
            "currency": "USD",
        },
        "# Hims & Hers\n\n稳定事实...\n",
        base=tmp_path,
    )
    doc = company.read_meta_with_body("HIMS", "US", base=tmp_path)
    assert doc["frontmatter"]["name"] == "Hims & Hers"
    assert doc["frontmatter"]["industry_slugs"] == [
        "us-telehealth",
        "us-glp1-compounding",
    ]
    assert doc["frontmatter"]["themes"] == ["weight_loss", "telehealth"]
    assert "稳定事实" in doc["body"]


def test_write_meta_coerces_industry_slugs_string(tmp_path):
    _make_company(tmp_path)
    company.write_meta(
        "HIMS", "US",
        {"industry_slugs": "us-telehealth, us-glp1-compounding", "name": "Hims"},
        "body",
        base=tmp_path,
    )
    doc = company.read_meta_with_body("HIMS", "US", base=tmp_path)
    assert doc["frontmatter"]["industry_slugs"] == [
        "us-telehealth",
        "us-glp1-compounding",
    ]


def test_write_meta_rejects_bad_industry_slugs(tmp_path):
    _make_company(tmp_path)
    with pytest.raises(ValueError, match="industry_slugs"):
        company.write_meta(
            "HIMS", "US",
            {"industry_slugs": [1, 2], "name": "x"},
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


def test_list_sources(tmp_path):
    d = _make_company(tmp_path)
    (d / "sources" / "a.md").write_text("")
    (d / "sources" / "b.pdf").write_text("")
    assert company.list_sources("HIMS", "US", base=tmp_path) == ["a.md", "b.pdf"]

from datetime import date
from pathlib import Path

import pytest
import yaml

from app.io import company as company_io


def _fake_templates(tmp_path: Path) -> Path:
    d = tmp_path / "templates"
    d.mkdir()
    # Minimal templates sufficient for create_company to render
    (d / "meta.md.tmpl").write_text(
        "---\nticker: {{ ticker }}\nmarket: {{ market }}\nname: {{ name }}\n"
        "industry_slugs: {{ industry_slugs | default([]) | tojson }}\n"
        "currency: {{ currency }}\n---\n\n# {{ ticker }}\n"
    )
    (d / "v0.md.tmpl").write_text(
        "---\nticker: {{ ticker }}\nmarket: {{ market }}\nstatus: draft\n"
        "last_reviewed: {{ today }}\n---\n\n# V0: {{ ticker }}\n"
    )
    (d / "valuation.md.tmpl").write_text(
        "---\nticker: {{ ticker }}\nmarket: {{ market }}\nvaluation_date: {{ today }}\n---\n\n# val\n"
    )
    (d / "trade-log.md.tmpl").write_text(
        "---\nticker: {{ ticker }}\nmarket: {{ market }}\n---\n\n# trade-log\n"
    )
    return d


def test_create_company_lays_down_all_files(tmp_path):
    tpl = _fake_templates(tmp_path)
    path = company_io.create_company(
        ticker="HIMS",
        market="US",
        name="Hims & Hers",
        industry_slugs=["us-telehealth"],
        currency="USD",
        base=tmp_path,
        templates_dir=tpl,
        today=date(2026, 4, 23),
    )

    assert path == tmp_path / "companies" / "US_HIMS"
    assert path.is_dir()
    assert (path / "sources").is_dir()
    assert (path / "meta.md").exists()
    assert (path / "v0.md").exists()
    assert (path / "valuation.md").exists()
    assert (path / "trade-log.md").exists()
    # per-company claims.jsonl is prohibited endgame artifact; must NOT be created
    assert not (path / "claims.jsonl").exists()


def test_create_company_inserts_frontmatter(tmp_path):
    tpl = _fake_templates(tmp_path)
    path = company_io.create_company(
        ticker="HIMS",
        market="US",
        name="Hims & Hers",
        industry_slugs=["us-telehealth"],
        currency="USD",
        base=tmp_path,
        templates_dir=tpl,
        today=date(2026, 4, 23),
    )
    meta = (path / "meta.md").read_text()
    assert "ticker: HIMS" in meta
    assert "us-telehealth" in meta
    assert "currency: USD" in meta

    v0 = (path / "v0.md").read_text()
    assert "ticker: HIMS" in v0
    assert "status: draft" in v0


def test_create_company_defaults_empty_industry_slugs(tmp_path):
    tpl = _fake_templates(tmp_path)
    path = company_io.create_company(
        ticker="HIMS",
        market="US",
        name="Hims & Hers",
        currency="USD",
        base=tmp_path,
        templates_dir=tpl,
        today=date(2026, 4, 23),
    )
    meta = (path / "meta.md").read_text()
    # Empty list should render as `[]`
    assert "industry_slugs: []" in meta


def test_create_company_refuses_overwrite(tmp_path):
    tpl = _fake_templates(tmp_path)
    company_io.create_company(
        ticker="HIMS",
        market="US",
        name="x",
        industry_slugs=[],
        currency="USD",
        base=tmp_path,
        templates_dir=tpl,
        today=date(2026, 4, 23),
    )
    with pytest.raises(FileExistsError):
        company_io.create_company(
            ticker="HIMS",
            market="US",
            name="x",
            industry_slugs=[],
            currency="USD",
            base=tmp_path,
            templates_dir=tpl,
            today=date(2026, 4, 23),
        )


def test_create_company_rejects_unknown_market(tmp_path):
    tpl = _fake_templates(tmp_path)
    with pytest.raises(ValueError):
        company_io.create_company(
            ticker="X",
            market="LSE",
            name="x",
            industry_slugs=[],
            currency="USD",
            base=tmp_path,
            templates_dir=tpl,
            today=date(2026, 4, 23),
        )

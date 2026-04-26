from datetime import date
from pathlib import Path

import pytest

from app import config as cfg
from app.io import company as company_io


def _fake_templates(tmp_path: Path) -> Path:
    """Minimal template dir sufficient for create_company to render."""
    d = tmp_path / "templates"
    d.mkdir()
    (d / "meta.md.tmpl").write_text(
        "---\nticker: {{ ticker }}\nmarket: {{ market }}\nname: {{ name }}\n"
        "industry_slugs: {{ industry_slugs | default([]) | tojson }}\n"
        "currency: {{ currency }}\n---\n\n# {{ ticker }}\n"
    )
    (d / "v0.md.tmpl").write_text(
        "---\nticker: {{ ticker }}\nmarket: {{ market }}\nstatus: draft\n"
        "last_reviewed: {{ today }}\n---\n\n# V0: {{ ticker }}\n"
    )
    (d / "competence-check.md.tmpl").write_text(
        "---\nticker: {{ ticker }}\nmarket: {{ market }}\n"
        "check_date: {{ today }}\nin_competence: false\n---\n\n# competence\n"
    )
    (d / "valuation.md.tmpl").write_text(
        "---\nticker: {{ ticker }}\nmarket: {{ market }}\nvaluation_date: {{ today }}\n---\n\n# val\n"
    )
    (d / "trade-log.md.tmpl").write_text(
        "---\nticker: {{ ticker }}\nmarket: {{ market }}\n---\n\n# trade-log\n"
    )
    (d / "profile-YYYY.md.tmpl").write_text(
        "---\nticker: {{ ticker }}\nmarket: {{ market }}\nyear: {{ year }}\n---\n\n# profile\n"
    )
    return d


def test_create_company_creates_narrative_skeletons(tmp_path):
    tpl = _fake_templates(tmp_path)
    company_io.create_company(
        ticker="TEST", market="US", name="Test Co",
        industry_slugs=["test-ind"],
        base=tmp_path, templates_dir=tpl,
    )
    narr_dir = tmp_path / "companies" / "US_TEST" / "narratives"
    assert narr_dir.is_dir()
    for dim in cfg.COMPANY_DIMENSIONS:
        assert (narr_dir / f"{dim.replace('_', '-')}.md").is_file()


def test_read_narrative_returns_skeleton(tmp_path):
    tpl = _fake_templates(tmp_path)
    company_io.create_company(
        ticker="TEST", market="US", name="Test Co",
        industry_slugs=[], base=tmp_path, templates_dir=tpl,
    )
    md = company_io.read_narrative("TEST", "US", "moat", base=tmp_path)
    assert md.startswith("# ")


def test_append_narrative_block(tmp_path):
    tpl = _fake_templates(tmp_path)
    company_io.create_company(
        ticker="T", market="US", name="T Co",
        industry_slugs=[], base=tmp_path, templates_dir=tpl,
    )
    company_io.append_narrative_block(
        ticker="T", market="US", dim="moat", block="主要护城河是技术专利。",
        source_meta={"institution": "10-K", "date": "2024-12-31",
                     "sha8": "deadbeef", "source_id": "年报-2024-deadbeef"},
        base=tmp_path,
    )
    md = company_io.read_narrative("T", "US", "moat", base=tmp_path)
    assert "### 来源 10-K 2024-12-31 (sha8=deadbeef)" in md
    assert "主要护城河是技术专利" in md


def test_append_narrative_rejects_unknown_dim(tmp_path):
    tpl = _fake_templates(tmp_path)
    company_io.create_company(
        ticker="T", market="US", name="T",
        industry_slugs=[], base=tmp_path, templates_dir=tpl,
    )
    with pytest.raises(ValueError, match="unknown"):
        company_io.append_narrative_block(
            "T", "US", "bogus", "x",
            {"institution":"a","date":"b","sha8":"c","source_id":"d"}, base=tmp_path,
        )

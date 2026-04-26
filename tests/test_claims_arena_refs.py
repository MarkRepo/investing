import json
from pathlib import Path
import pytest

from app import config as cfg
from app.io import claims as claims_io


def _minimal_batch(claims: list[dict]) -> str:
    header = {
        "ticker": "T", "market": "US",
        "source_id": "test-1", "source_file": "x.pdf",
        "extracted_by": "test", "extracted_at": "2026-04-26T00:00:00",
    }
    return json.dumps({"header": header, "claims": claims})  # shape mirrors real batch


def test_validate_batch_accepts_arena_refs_empty_default(fake_subjects):
    # subjects fixture: minimal valid subject for test
    batch = _minimal_batch([{
        "claim_text": "X",
        "subject_tag": "test:tag",
        "polarity": "neutral",
        "claim_type": "qualitative",
    }])
    header, valid, errors = claims_io.validate_batch(batch, subjects=fake_subjects)
    assert errors == []
    assert valid[0].get("arena_refs", []) == []
    assert valid[0].get("company_dimension_hint") is None


def test_validate_batch_accepts_arena_refs_provided(fake_subjects):
    batch = _minimal_batch([{
        "claim_text": "X",
        "subject_tag": "test:tag",
        "polarity": "neutral",
        "claim_type": "qualitative",
        "arena_refs": ["arena-a", "arena-b"],
        "company_dimension_hint": "moat",
    }])
    header, valid, errors = claims_io.validate_batch(batch, subjects=fake_subjects)
    assert errors == []
    assert valid[0]["arena_refs"] == ["arena-a", "arena-b"]
    assert valid[0]["company_dimension_hint"] == "moat"


def test_validate_batch_rejects_company_dimension_hint_not_in_whitelist(fake_subjects):
    batch = _minimal_batch([{
        "claim_text": "X",
        "subject_tag": "test:tag",
        "polarity": "neutral",
        "claim_type": "qualitative",
        "company_dimension_hint": "not_a_real_dim",
    }])
    header, valid, errors = claims_io.validate_batch(batch, subjects=fake_subjects)
    # accept the claim but record an error for the bad dim hint, OR reject outright;
    # choice: reject (strict whitelist on optional field when provided)
    assert errors, "bad dim hint should raise validation error"


@pytest.fixture
def fake_subjects():
    # validate_batch uses s["id"] as subject tag lookup
    return [{"id": "test:tag", "label": "test tag"}]


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


def test_filter_by_arena_scans_all_companies(tmp_path, fake_subjects, monkeypatch):
    tpl = _fake_templates(tmp_path)
    # base for create_company is the project root; companies_dir = base/companies
    from app.io import company as company_io
    company_io.create_company(
        ticker="A", market="US", name="AA",
        industry_slugs=[], base=tmp_path, templates_dir=tpl,
    )
    company_io.create_company(
        ticker="B", market="US", name="BB",
        industry_slugs=[], base=tmp_path, templates_dir=tpl,
    )

    claims_a = [
        {"claim_text": "x", "subject_tag": "test:tag",
         "polarity": "neutral", "claim_type": "qualitative",
         "arena_refs": ["arena-1"]},
    ]
    claims_b = [
        {"claim_text": "y", "subject_tag": "test:tag",
         "polarity": "neutral", "claim_type": "qualitative",
         "arena_refs": ["arena-2"]},
        {"claim_text": "z", "subject_tag": "test:tag",
         "polarity": "neutral", "claim_type": "qualitative",
         "arena_refs": ["arena-1", "arena-2"]},
    ]
    header_a = {"ticker": "A", "market": "US", "source_id": "sa",
                "source_file": "", "extracted_by": "t", "extracted_at": "2026-04-26T00:00:00"}
    header_b = dict(header_a, ticker="B", source_id="sb")
    claims_io.append_batch("A", "US", claims_a, header=header_a, base=tmp_path)
    claims_io.append_batch("B", "US", claims_b, header=header_b, base=tmp_path)

    result = claims_io.filter_by_arena("arena-1", base=tmp_path)
    texts = {c["claim_text"] for c in result}
    assert texts == {"x", "z"}


def test_filter_by_company_dimension(tmp_path, fake_subjects):
    tpl = _fake_templates(tmp_path)
    from app.io import company as company_io
    company_io.create_company(
        ticker="A", market="US", name="AA",
        industry_slugs=[], base=tmp_path, templates_dir=tpl,
    )
    claims_data = [
        {"claim_text": "x", "subject_tag": "test:tag", "polarity": "neutral",
         "claim_type": "qualitative", "company_dimension_hint": "moat"},
        {"claim_text": "y", "subject_tag": "test:tag", "polarity": "neutral",
         "claim_type": "qualitative", "company_dimension_hint": "risks"},
    ]
    header = {"ticker": "A", "market": "US", "source_id": "s",
              "source_file": "", "extracted_by": "t", "extracted_at": "2026-04-26T00:00:00"}
    claims_io.append_batch("A", "US", claims_data, header=header, base=tmp_path)
    result = claims_io.filter_by_company_dimension("A", "US", "moat", base=tmp_path)
    assert len(result) == 1
    assert result[0]["claim_text"] == "x"

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

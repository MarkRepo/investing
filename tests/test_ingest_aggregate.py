"""Unit tests for scripts.ingest_aggregate."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from app import config as cfg
from app.io import claims as claims_io
from scripts import ingest_aggregate as agg


# ---------- load_json_tolerant ----------------------------------------------


def test_load_json_tolerant_bare():
    assert agg.load_json_tolerant('{"a": 1}') == {"a": 1}


def test_load_json_tolerant_markdown_fence():
    raw = "```json\n{\"section\": \"mdna\", \"claims\": []}\n```"
    assert agg.load_json_tolerant(raw) == {"section": "mdna", "claims": []}


def test_load_json_tolerant_markdown_fence_no_lang():
    raw = "some prefix\n```\n{\"a\": 2}\n```\ntrailing"
    assert agg.load_json_tolerant(raw) == {"a": 2}


def test_load_json_tolerant_embedded_in_prose():
    raw = "Here is the result: {\"b\": 3}. Done."
    assert agg.load_json_tolerant(raw) == {"b": 3}


def test_load_json_tolerant_rejects_empty():
    with pytest.raises(ValueError):
        agg.load_json_tolerant("")


# ---------- normalize_claim -------------------------------------------------


def test_normalize_claim_polarity_synonyms():
    assert agg.normalize_claim({"polarity": "positive"})["polarity"] == "bull"
    assert agg.normalize_claim({"polarity": "negative"})["polarity"] == "bear"
    assert agg.normalize_claim({"polarity": "neutral"})["polarity"] == "neutral"


def test_normalize_claim_pass_through_canonical():
    for p in ("bull", "bear", "neutral"):
        assert agg.normalize_claim({"polarity": p})["polarity"] == p


def test_normalize_claim_unknown_polarity_defaults_neutral():
    assert agg.normalize_claim({"polarity": "up"})["polarity"] == "neutral"
    assert agg.normalize_claim({})["polarity"] == "neutral"


def test_normalize_claim_evidence_text_wrapped():
    c = agg.normalize_claim({"polarity": "bull", "evidence_text": "quote"})
    assert c["evidence"] == [{"text": "quote", "type": "primary"}]
    assert "evidence_text" not in c


def test_normalize_claim_existing_evidence_preserved():
    ev = [{"text": "x", "type": "secondary"}]
    c = agg.normalize_claim({"polarity": "bull", "evidence": ev})
    assert c["evidence"] is ev


def test_normalize_claim_no_evidence_defaults_empty_list():
    c = agg.normalize_claim({"polarity": "bull"})
    assert c["evidence"] == []


# ---------- normalize_period ------------------------------------------------


def test_normalize_period_fy_to_annual():
    assert agg.normalize_period("FY2025") == "2025A"


def test_normalize_period_quarterly_unchanged():
    assert agg.normalize_period("2025Q1") == "2025Q1"


def test_normalize_period_annual_unchanged():
    assert agg.normalize_period("2025A") == "2025A"


def test_normalize_period_random_string_unchanged():
    # We don't want to corrupt things we don't recognize.
    assert agg.normalize_period("H1_2025") == "H1_2025"


# ---------- dedup_claims ----------------------------------------------------


def test_dedup_exact_duplicate_dropped():
    c = {"claim_text": "revenue grew 59%", "subject_tag": "revenue_growth", "timeframe": "FY2025"}
    out = agg.dedup_claims([c, dict(c)])
    assert len(out) == 1


def test_dedup_different_timeframe_kept():
    base = {"claim_text": "revenue grew 59%", "subject_tag": "revenue_growth"}
    out = agg.dedup_claims(
        [{**base, "timeframe": "FY2025"}, {**base, "timeframe": "FY2024"}]
    )
    assert len(out) == 2


def test_dedup_uses_60char_prefix():
    shared = "x" * 60
    out = agg.dedup_claims(
        [
            {"claim_text": shared + " one",  "subject_tag": "x", "timeframe": "t"},
            {"claim_text": shared + " two",  "subject_tag": "x", "timeframe": "t"},
        ]
    )
    assert len(out) == 1


# ---------- aggregate -------------------------------------------------------


def _sample_subagent(**overrides):
    base = {
        "claims": [],
        "profile_fragments": {},
        "meta_updates": {},
        "flags": [],
    }
    base.update(overrides)
    return base


def test_aggregate_concats_claims_and_normalizes():
    outputs = {
        "mdna": _sample_subagent(
            claims=[{"claim_text": "a", "polarity": "positive", "subject_tag": "revenue_growth", "evidence_text": "q"}]
        ),
        "overview": _sample_subagent(
            claims=[{"claim_text": "b", "polarity": "bull", "subject_tag": "revenue_mix"}]
        ),
    }
    m = agg.aggregate(outputs)
    assert len(m["claims"]) == 2
    # normalization happened
    assert m["claims"][0]["polarity"] == "bull"
    assert m["claims"][0]["evidence"] == [{"text": "q", "type": "primary"}]


def test_aggregate_profile_fragments_prefer_longer():
    outputs = {
        "a": _sample_subagent(profile_fragments={"§1": "short"}),
        "b": _sample_subagent(profile_fragments={"§1": "a much longer description"}),
    }
    m = agg.aggregate(outputs)
    assert m["profile_fragments"]["§1"] == "a much longer description"


def test_aggregate_meta_updates_first_writer_wins():
    outputs = {
        "a": _sample_subagent(meta_updates={"website": "hims.com"}),
        "b": _sample_subagent(meta_updates={"website": "other.com"}),
    }
    m = agg.aggregate(outputs)
    assert m["meta_updates"] == {"website": "hims.com"}


def test_aggregate_detects_empty_subagent():
    outputs = {
        "a": _sample_subagent(claims=[{"claim_text": "x", "polarity": "bull", "subject_tag": "s"}]),
        "empty_one": _sample_subagent(),
    }
    m = agg.aggregate(outputs)
    assert m["empty_subagents"] == ["empty_one"]


def test_aggregate_flags_kept_per_subagent():
    outputs = {
        "a": _sample_subagent(flags=["flag1", "flag2"]),
        "b": _sample_subagent(flags=["flag3"]),
    }
    m = agg.aggregate(outputs)
    assert m["flags_by_subagent"] == {"a": ["flag1", "flag2"], "b": ["flag3"]}


def test_aggregate_merges_competence_findings():
    outputs = {
        "mdna": _sample_subagent(
            competence_findings={
                "answered": [
                    {"q_id": "q1", "level": "vague", "answer_text": "a", "evidence_quote": "e1"}
                ],
                "proposed_additions": [{"proposed_question": "Q?"}],
            }
        ),
        "thesis__lvl1": _sample_subagent(
            competence_findings={
                "answered": [
                    {"q_id": "q2", "level": "specific", "answer_text": "b", "evidence_quote": "e2"}
                ],
                "proposed_additions": [],
            }
        ),
    }
    m = agg.aggregate(outputs)
    assert len(m["competence_findings"]["answered"]) == 2
    assert len(m["competence_findings"]["proposed_additions"]) == 1
    q_ids = {a["q_id"] for a in m["competence_findings"]["answered"]}
    assert q_ids == {"q1", "q2"}


def test_aggregate_competence_findings_default_empty():
    """A subagent that omits competence_findings (old-style) should not break."""
    outputs = {"a": {"claims": [], "flags": []}}
    m = agg.aggregate(outputs)
    assert m["competence_findings"] == {"answered": [], "proposed_additions": []}


def test_aggregate_detects_empty_subagent_even_with_only_competence():
    """A subagent that only produces competence_findings is NOT empty."""
    outputs = {
        "thesis": _sample_subagent(
            competence_findings={
                "answered": [{"q_id": "q1", "level": "specific"}],
                "proposed_additions": [],
            }
        ),
    }
    m = agg.aggregate(outputs)
    assert m["empty_subagents"] == []


# ---------- cross-checks ----------------------------------------------------


def test_period_consistency_pass():
    m = {
        "claims": [
            {"timeframe": "FY2025"},
            {"timeframe": "FY2025"},
            {"timeframe": "FY2024"},
        ]
    }
    assert agg.check_period_consistency(m, expected="FY2025") == []


def test_period_consistency_flags_mismatch():
    m = {
        "claims": [
            {"timeframe": "FY2024"},
            {"timeframe": "FY2024"},
            {"timeframe": "FY2025"},
        ]
    }
    issues = agg.check_period_consistency(m, expected="FY2025")
    assert len(issues) == 1
    assert "FY2024" in issues[0]


def test_period_consistency_no_timeframes_is_flagged():
    assert agg.check_period_consistency({"claims": [{}]}, expected="FY2025") == [
        "no claim carries a timeframe"
    ]


def test_empty_sections_report():
    m = {"empty_subagents": ["risk-factors", "governance"]}
    issues = agg.check_empty_sections(m)
    assert len(issues) == 2
    assert "risk-factors" in issues[0]


# ---------- build_claims_batch -----------------------------------------------


def test_build_claims_batch_has_flat_header():
    """Regression: header fields MUST be flat at the top level, not nested
    under "header". The nested form silently discards source_id."""
    batch = agg.build_claims_batch(
        [{"claim_text": "x"}],
        source_id="10-K-FY2025-abc",
        source_file="foo.htm",
        extracted_by="claude-opus-4-7",
        extracted_at="2026-04-24T00:00:00+00:00",
    )
    assert batch["source_id"] == "10-K-FY2025-abc"
    assert batch["source_file"] == "foo.htm"
    assert batch["claims"] == [{"claim_text": "x"}]
    assert "header" not in batch


def test_build_claims_batch_roundtrips_through_parse_batch_json():
    batch = agg.build_claims_batch(
        [{"claim_text": "x", "subject_tag": "revenue_growth",
          "polarity": "bull", "claim_type": "quantitative"}],
        source_id="id", source_file="f", extracted_by="e",
        extracted_at="2026-04-24T00:00:00+00:00",
    )
    header, claims_out = claims_io.parse_batch_json(json.dumps(batch))
    assert header["source_id"] == "id"
    assert len(claims_out) == 1


# ---------- write_claims (integration) --------------------------------------


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(cfg, "CONTROLLED_VOCAB_DIR", tmp_path / "controlled-vocab")
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cfg, "FINANCIALS_DB", tmp_path / "data" / "financials.db")
    (tmp_path / "companies" / "US_HIMS").mkdir(parents=True)
    vocab = tmp_path / "controlled-vocab"
    vocab.mkdir()
    (vocab / "subjects.yaml").write_text(
        yaml.safe_dump(
            {
                "subjects": [
                    {"id": "revenue_growth", "name": "Revenue growth"},
                    {"id": "revenue_mix", "name": "Revenue mix"},
                ]
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_write_claims_succeeds_and_attaches_source_id(env):
    claim = {
        "claim_text": "FY2025 revenue grew 59%",
        "subject_tag": "revenue_growth",
        "polarity": "bull",
        "claim_type": "quantitative",
        "timeframe": "FY2025",
    }
    n, errors = agg.write_claims(
        "HIMS", "US", [claim],
        source_id="10-K-FY2025-abc12345",
        source_file="10-K.htm",
        extracted_by="claude-opus-4-7",
        extracted_at="2026-04-24T00:00:00+00:00",
        base=env,
    )
    assert errors == []
    assert n == 1
    got = claims_io.read_claims("HIMS", "US", base=env)
    assert len(got) == 1
    assert got[0]["source_id"] == "10-K-FY2025-abc12345"
    assert got[0]["ticker"] == "HIMS"


def test_write_claims_partial_success_writes_valid_only(env):
    bad_claim = {
        "claim_text": "x",
        "subject_tag": "not_in_vocab",  # not in our subjects.yaml
        "polarity": "bull",
        "claim_type": "quantitative",
    }
    good_claim = {
        "claim_text": "y",
        "subject_tag": "revenue_growth",
        "polarity": "bull",
        "claim_type": "quantitative",
    }
    n, errors = agg.write_claims(
        "HIMS", "US", [bad_claim, good_claim],
        source_id="id", source_file="f",
        extracted_by="e", extracted_at="2026-04-24T00:00:00+00:00",
        base=env,
    )
    # Partial success: 1 good claim written, 1 bad claim rejected.
    assert n == 1
    assert len(errors) == 1
    assert errors[0]["index"] == 0  # bad_claim was first
    got = claims_io.read_claims("HIMS", "US", base=env)
    assert len(got) == 1
    assert got[0]["claim_text"] == "y"

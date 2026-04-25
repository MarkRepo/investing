"""Unit tests for scripts.ingest_aggregate."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from app import config as cfg
from app.io import claims as claims_io
from app.io import financials as fin_io
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
        "financial_rows": [],
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


def _merged_with_total_revenue_claim(claim_text: str, revenue_csv_usd: float, tf: str = "FY2025"):
    return {
        "financial_rows": [{"period": tf, "revenue": revenue_csv_usd}],
        "claims": [
            {
                "claim_text": claim_text,
                "claim_type": "quantitative",
                "subject_tag": "revenue_growth",
                "timeframe": tf,
            }
        ],
        "empty_subagents": [],
    }


def test_revenue_consistency_pass_within_tolerance():
    # Claim says $2,347.6M total revenue, CSV says $2,347,637,000 → match
    m = _merged_with_total_revenue_claim(
        "FY2025 total revenue reached $2,347.6M, up 59%", 2_347_637_000
    )
    assert agg.check_revenue_consistency(m) == []


def test_revenue_consistency_fails_outside_tolerance():
    # Claim says $2,500M total revenue vs CSV $2,347M → > 2% diff → fails
    m = _merged_with_total_revenue_claim(
        "FY2025 total revenue was $2,500.0M", 2_347_637_000
    )
    issues = agg.check_revenue_consistency(m)
    assert len(issues) == 1
    assert "diff" in issues[0]


def test_revenue_consistency_ignores_segment_revenue():
    # Segment-level revenue should NOT be compared against total revenue,
    # even though it trivially mismatches.
    m = _merged_with_total_revenue_claim(
        "FY2025 United States Revenue was $2,213.6M", 2_347_637_000
    )
    assert agg.check_revenue_consistency(m) == []


def test_revenue_consistency_handles_fy_to_annual_lookup():
    # CSV uses 2025A, claim timeframe is FY2025 — should still match.
    m = {
        "financial_rows": [{"period": "2025A", "revenue": 2_347_637_000}],
        "claims": [
            {
                "claim_text": "FY2025 total revenue reached $2,347.6M",
                "claim_type": "quantitative",
                "subject_tag": "revenue_growth",
                "timeframe": "FY2025",
            }
        ],
        "empty_subagents": [],
    }
    assert agg.check_revenue_consistency(m) == []


def test_revenue_consistency_skips_qualitative_claims():
    m = _merged_with_total_revenue_claim(
        "total revenue grew strongly", 2_347_637_000
    )
    m["claims"][0]["claim_type"] = "qualitative"
    assert agg.check_revenue_consistency(m) == []


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


def test_financials_required_missing_revenue():
    m = {"financial_rows": [{"period": "2025A", "revenue": None, "net_income": 100}]}
    issues = agg.check_financials_required(m)
    assert any("missing revenue" in i for i in issues)


def test_financials_required_missing_net_income():
    m = {"financial_rows": [{"period": "2025A", "revenue": 100, "net_income": None}]}
    issues = agg.check_financials_required(m)
    assert any("missing net_income" in i for i in issues)


def test_financials_required_pass():
    m = {"financial_rows": [{"period": "2025A", "revenue": 100, "net_income": 10}]}
    assert agg.check_financials_required(m) == []


# ---------- build_claims_batch / build_financials_csv -----------------------


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


def test_build_financials_csv_normalizes_period_and_handles_none():
    rows = [
        {"period": "FY2025", "period_type": "annual", "revenue": 100, "net_income": 10},
        {"period": "FY2024", "period_type": "annual", "revenue": 80, "net_income": None},
    ]
    csv_text = agg.build_financials_csv(rows)
    lines = csv_text.splitlines()  # handles CRLF from csv.writer
    header = lines[0].split(",")
    assert "period" in header and "revenue" in header and "shares_outstanding" in header
    # FY2025 → 2025A normalization
    assert "2025A" in csv_text
    assert "FY2025" not in csv_text
    # net_income None → empty field
    row_2024 = next(row for row in lines if row.startswith("2024A"))
    # net_income column's value should be empty (``,,`` or trailing ``,``)
    fields = row_2024.split(",")
    ni_idx = header.index("net_income")
    assert fields[ni_idx] == ""


# ---------- write_financials / write_claims (integration) -------------------


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


def test_write_financials_round_trip(env):
    rows = [
        {"period": "FY2025", "period_type": "annual",
         "revenue": 2_347_637_000, "net_income": 128_365_000},
        {"period": "FY2024", "period_type": "annual",
         "revenue": 1_476_514_000, "net_income": 126_038_000},
    ]
    n = agg.write_financials("HIMS", rows, source_file="10-K.htm", base=env)
    assert n == 2
    got = fin_io.list_financials("HIMS", base=env)
    periods = {r["period"] for r in got}
    assert periods == {"2025A", "2024A"}
    row_2025 = next(r for r in got if r["period"] == "2025A")
    assert row_2025["revenue"] == 2_347_637_000


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


def test_write_claims_validation_error_blocks_all_writes(env):
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
    assert n == 0
    assert errors  # non-empty
    # Nothing got written — regression guard for partial writes.
    got = claims_io.read_claims("HIMS", "US", base=env)
    assert got == []

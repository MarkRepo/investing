from pathlib import Path

import pytest

from app.io import claims


@pytest.fixture
def env(tmp_path, monkeypatch):
    from app import config as cfg
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    (tmp_path / "companies" / "US_HIMS").mkdir(parents=True)
    return tmp_path


def test_append_and_read(env):
    claims.append_claim(
        "HIMS", "US",
        {
            "claim_text": "2026 Q1 订阅用户同比 +30%",
            "subject_tag": "revenue_growth",
            "polarity": "bull",
            "claim_type": "quantitative",
            "source_id": "ms-2026-04-10",
        },
        base=env,
    )
    claims.append_claim(
        "HIMS", "US",
        {
            "claim_text": "监管风险：FDA compound drug 豁免可能撤回",
            "subject_tag": "regulatory_risk",
            "polarity": "bear",
            "claim_type": "qualitative",
        },
        base=env,
    )
    got = claims.read_claims("HIMS", "US", base=env)
    assert len(got) == 2
    assert got[0]["id"] == "HIMS-0001"
    assert got[1]["id"] == "HIMS-0002"
    assert got[0]["ticker"] == "HIMS"


def test_append_rejects_bad_polarity(env):
    with pytest.raises(ValueError):
        claims.append_claim(
            "HIMS", "US",
            {"claim_text": "x", "subject_tag": "catalyst", "polarity": "up", "claim_type": "qualitative"},
            base=env,
        )


def test_append_requires_text_and_tag(env):
    with pytest.raises(ValueError):
        claims.append_claim(
            "HIMS", "US",
            {"claim_text": "", "subject_tag": "catalyst", "polarity": "bull", "claim_type": "qualitative"},
            base=env,
        )
    with pytest.raises(ValueError):
        claims.append_claim(
            "HIMS", "US",
            {"claim_text": "x", "subject_tag": "", "polarity": "bull", "claim_type": "qualitative"},
            base=env,
        )


def test_consensus_map_aggregation(env):
    items = [
        {"subject_tag": "revenue_growth", "polarity": "bull"},
        {"subject_tag": "revenue_growth", "polarity": "bull"},
        {"subject_tag": "revenue_growth", "polarity": "bear"},
        {"subject_tag": "catalyst", "polarity": "neutral"},
    ]
    agg = claims.consensus_map(items)
    assert agg[0]["subject_tag"] == "revenue_growth"
    assert agg[0]["bull"] == 2
    assert agg[0]["bear"] == 1
    assert agg[1]["subject_tag"] == "catalyst"
    assert agg[1]["neutral"] == 1


def test_save_source_markdown(env):
    dest = claims.save_source_markdown(
        "HIMS", "US", "2026-04-10-morgan-stanley.md",
        b"---\ntitle: MS Note\n---\n\n# body\n",
        base=env,
    )
    assert dest.exists()
    assert dest.read_text(encoding="utf-8").startswith("---")

    listed = claims.list_sources("HIMS", "US", base=env)
    assert listed[0]["name"] == "2026-04-10-morgan-stanley.md"


def test_save_source_rejects_path_traversal(env):
    dest = claims.save_source_markdown(
        "HIMS", "US", "../../evil.md", b"x", base=env,
    )
    # Filename is sanitized to basename; no dir traversal.
    assert dest.name == "evil.md"
    assert dest.parent.name == "sources"


# --- Batch import -----------------------------------------------------------

SUBJECTS = [
    {"id": "revenue_growth", "label": "收入增长"},
    {"id": "gross_margin", "label": "毛利率"},
    {"id": "regulatory_risk", "label": "监管风险"},
]


GOOD_BATCH = """
{
  "source_id": "MS-2026-04-10",
  "source_file": "morgan-stanley-hims-2026-04-10.md",
  "extracted_by": "claude-opus-4-7",
  "claims": [
    {
      "claim_text": "2026Q1 付费用户同比 +30%",
      "subject_tag": "revenue_growth",
      "polarity": "bull",
      "claim_type": "quantitative",
      "timeframe": "2026Q1",
      "evidence_text": "公司披露 Q1 付费用户 220 万 vs 去年同期 170 万"
    },
    {
      "claim_text": "GLP-1 compound 豁免可能撤回",
      "subject_tag": "regulatory_risk",
      "polarity": "bear",
      "claim_type": "qualitative"
    }
  ]
}
"""


def test_validate_batch_happy(env):
    header, valid, errors = claims.validate_batch(GOOD_BATCH, SUBJECTS)
    assert header["source_id"] == "MS-2026-04-10"
    assert header["source_file"] == "morgan-stanley-hims-2026-04-10.md"
    assert len(valid) == 2
    assert not errors


def test_validate_batch_accepts_bare_array(env):
    raw = """[
      {"claim_text": "x", "subject_tag": "revenue_growth", "polarity": "bull", "claim_type": "qualitative"}
    ]"""
    header, valid, errors = claims.validate_batch(raw, SUBJECTS)
    assert header == {}
    assert len(valid) == 1
    assert not errors


def test_validate_batch_flags_unknown_subject(env):
    raw = """[
      {"claim_text": "x", "subject_tag": "made_up_tag", "polarity": "bull", "claim_type": "qualitative"}
    ]"""
    _, valid, errors = claims.validate_batch(raw, SUBJECTS)
    assert len(valid) == 0
    assert len(errors) == 1
    assert "not in controlled-vocab" in errors[0]["errors"][0]
    assert errors[0]["index"] == 0


def test_validate_batch_multiple_errors_per_claim(env):
    raw = """[
      {"claim_text": "", "subject_tag": "revenue_growth", "polarity": "up", "claim_type": "bogus"}
    ]"""
    _, valid, errors = claims.validate_batch(raw, SUBJECTS)
    assert not valid
    assert len(errors) == 1
    msgs = errors[0]["errors"]
    assert any("missing claim_text" in m for m in msgs)
    assert any("polarity" in m for m in msgs)
    assert any("claim_type" in m for m in msgs)


def test_validate_batch_rejects_malformed_json(env):
    with pytest.raises(ValueError, match="not valid JSON"):
        claims.validate_batch("{not json}", SUBJECTS)


def test_validate_batch_rejects_wrong_shape(env):
    with pytest.raises(ValueError, match="claims' array"):
        claims.validate_batch('{"source_id": "x"}', SUBJECTS)
    with pytest.raises(ValueError, match="object or array"):
        claims.validate_batch('"bare string"', SUBJECTS)


def test_validate_batch_empty_input(env):
    with pytest.raises(ValueError, match="empty"):
        claims.validate_batch("   ", SUBJECTS)


def test_validate_batch_defaults_time_type_to_actual(env):
    raw = """[
      {"claim_text": "x", "subject_tag": "revenue_growth", "polarity": "bull", "claim_type": "qualitative"}
    ]"""
    _, valid, errors = claims.validate_batch(raw, SUBJECTS)
    assert not errors
    assert valid[0]["time_type"] == "actual"


def test_validate_batch_accepts_forecast_time_type(env):
    raw = """[
      {"claim_text": "2026Q2 预计营收 +20%", "subject_tag": "revenue_growth",
       "polarity": "bull", "claim_type": "qualitative", "time_type": "forecast"}
    ]"""
    _, valid, errors = claims.validate_batch(raw, SUBJECTS)
    assert not errors
    assert valid[0]["time_type"] == "forecast"


def test_validate_batch_rejects_bad_time_type(env):
    raw = """[
      {"claim_text": "x", "subject_tag": "revenue_growth", "polarity": "bull",
       "claim_type": "qualitative", "time_type": "historical"}
    ]"""
    _, valid, errors = claims.validate_batch(raw, SUBJECTS)
    assert not valid
    assert len(errors) == 1
    assert any("time_type" in m for m in errors[0]["errors"])


def test_append_batch_persists_time_type(env):
    raw = """[
      {"claim_text": "FY2024 历史营收 100", "subject_tag": "revenue_growth",
       "polarity": "bull", "claim_type": "qualitative"},
      {"claim_text": "2026Q2 预测毛利率 45%", "subject_tag": "revenue_growth",
       "polarity": "bull", "claim_type": "qualitative", "time_type": "forecast"}
    ]"""
    _, valid, errors = claims.validate_batch(raw, SUBJECTS)
    assert not errors
    claims.append_batch("HIMS", "US", valid, header={"source_id": "s1"}, base=env)
    got = claims.read_claims("HIMS", "US", base=env)
    assert got[0]["time_type"] == "actual"
    assert got[1]["time_type"] == "forecast"


def test_append_batch_propagates_header_and_ids(env):
    header, valid, errors = claims.validate_batch(GOOD_BATCH, SUBJECTS)
    assert not errors
    ids = claims.append_batch("HIMS", "US", valid, header=header, base=env)
    assert ids == ["HIMS-0001", "HIMS-0002"]

    got = claims.read_claims("HIMS", "US", base=env)
    assert got[0]["source_id"] == "MS-2026-04-10"
    assert got[0]["source_file"] == "morgan-stanley-hims-2026-04-10.md"
    assert got[0]["extracted_by"] == "claude-opus-4-7"
    # evidence_text got normalized into evidence list
    assert got[0]["evidence"][0]["text"].startswith("公司披露 Q1")
    assert "evidence_text" not in got[0]


def test_append_batch_continues_id_sequence(env):
    # Pre-seed one manual claim
    claims.append_claim(
        "HIMS", "US",
        {"claim_text": "seed", "subject_tag": "revenue_growth",
         "polarity": "bull", "claim_type": "qualitative"},
        base=env,
    )
    header, valid, _ = claims.validate_batch(GOOD_BATCH, SUBJECTS)
    ids = claims.append_batch("HIMS", "US", valid, header=header, base=env)
    assert ids == ["HIMS-0002", "HIMS-0003"]


def test_append_batch_preserves_claim_source_over_header(env):
    raw = """{
      "source_id": "HEADER-SRC",
      "claims": [
        {"claim_text": "x", "subject_tag": "revenue_growth", "polarity": "bull",
         "claim_type": "qualitative", "source_id": "CLAIM-SRC"}
      ]
    }"""
    header, valid, _ = claims.validate_batch(raw, SUBJECTS)
    claims.append_batch("HIMS", "US", valid, header=header, base=env)
    got = claims.read_claims("HIMS", "US", base=env)
    # Claim-level source_id wins when both present
    assert got[0]["source_id"] == "CLAIM-SRC"

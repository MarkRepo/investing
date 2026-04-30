from app.io.claim_matching import (
    char_bigram_jaccard,
    dimension_boost,
    is_type_compatible,
    match_candidate,
)


def _claim(**overrides):
    claim = {
        "claim_id": "clm-company-0001",
        "claim_text": "茅台品牌溢价来自白酒消费文化",
        "scope_type": "company",
        "scope_ref": "SSE_600519",
        "claim_type": "judgment",
        "dimension_hint": "moat",
        "status": "active",
        "confidence": "medium_high",
        "as_of": "2024-12-31",
        "supporting_evidence": [{"source_id": "src-old"}],
    }
    claim.update(overrides)
    return claim


def test_char_bigram_jaccard_for_cjk_text():
    assert char_bigram_jaccard("品牌溢价", "品牌韧性") == 1 / 5


def test_type_compatibility_whitelist():
    assert is_type_compatible("thesis", "judgment") is True
    assert is_type_compatible("judgment", "thesis") is True
    assert is_type_compatible("risk", "scenario") is True
    assert is_type_compatible("scenario", "risk") is True
    assert is_type_compatible("risk", "judgment") is False


def test_dimension_boost_exact_and_prefix():
    assert dimension_boost("moat", "moat") == 0.15
    assert dimension_boost("moat.brand", "moat.channel") == 0.05
    assert dimension_boost("demand", "moat") == 0.0


def test_match_candidate_filters_retired_and_incompatible_and_returns_top3():
    candidate = {
        "candidate_id": "cc-001",
        "claim_text": "茅台品牌溢价来自白酒文化根基",
        "scope_type": "company",
        "scope_ref": "SSE_600519",
        "claim_type": "thesis",
        "dimension_hint": "moat",
    }
    claims = [
        _claim(claim_id="clm-company-0001", claim_text="茅台品牌溢价来自白酒消费文化"),
        _claim(claim_id="clm-company-0002", claim_text="完全不同的渠道库存问题", dimension_hint="channel"),
        _claim(claim_id="clm-company-0003", claim_text="茅台品牌溢价来自白酒文化", status="retired"),
        _claim(claim_id="clm-company-0004", claim_type="risk", claim_text="茅台品牌溢价来自白酒文化"),
        _claim(claim_id="clm-company-0005", claim_text="品牌溢价和白酒文化相关"),
        _claim(claim_id="clm-company-0006", claim_text="白酒消费文化支撑品牌溢价"),
    ]

    matches = match_candidate(candidate, claims)

    assert [m["claim_id"] for m in matches] == ["clm-company-0001", "clm-company-0005", "clm-company-0006"]
    assert matches[0]["score"] >= matches[1]["score"]
    assert "same_dimension=moat" in matches[0]["reasons"]
    assert "type_compatible=thesis~judgment" in matches[0]["reasons"]
    assert matches[0]["existing_claim_snapshot"]["supporting_source_ids"] == ["src-old"]


def test_match_candidate_drops_all_when_best_score_below_threshold():
    candidate = {
        "candidate_id": "cc-001",
        "claim_text": "海外需求快速增长",
        "scope_type": "company",
        "scope_ref": "SSE_600519",
        "claim_type": "judgment",
        "dimension_hint": "demand",
    }

    assert match_candidate(candidate, [_claim(claim_text="渠道库存承压")]) == []

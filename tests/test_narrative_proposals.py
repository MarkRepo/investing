from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from app.io.narrative_proposals import (
    PROPOSAL_VERSION,
    build_proposal_file,
    map_claim_dimension,
)


def _create_claim(
    registry,
    *,
    claim_text="侵入式脑机接口商业化主要依赖医疗场景验证",
    scope_type="arena",
    scope_ref="cn-bci-industrialization",
    dimension_hint="competitive_position",
    status="active",
    source_id="src-001",
):
    evidence = build_evidence_entry(
        source_id=source_id,
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    claim = registry.create_claim(
        claim_text=claim_text,
        scope_type=scope_type,
        scope_ref=scope_ref,
        claim_type="judgment",
        dimension_hint=dimension_hint,
        confidence="medium_high",
        as_of="2024-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    if status != "active":
        claim["status"] = status
        registry._rewrite_claim(claim)
    return claim


def test_map_claim_dimension_known_values():
    assert map_claim_dimension("competitive_position") == "participants"
    assert map_claim_dimension("technology") == "decisive_factors"
    assert map_claim_dimension("stage_gate") == "trajectory"
    assert map_claim_dimension("risk") == "narratives"
    assert map_claim_dimension("valuation") == "investment_view"


def test_build_proposal_file_groups_active_arena_claims_by_dimension(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)

    result = build_proposal_file(
        registry=registry,
        arena_slug="cn-bci-industrialization",
        source_id="src-001",
        generated_at="2026-04-30T12:00:00+00:00",
        existing_excerpt_loader=lambda arena, dim: f"existing {arena} {dim}",
    )

    assert result["proposal_version"] == PROPOSAL_VERSION
    assert result["source_id"] == "src-001"
    assert result["scope_type"] == "arena"
    assert result["unmapped_claims"] == []
    assert result["summary_stats"] == {
        "total_proposals": 1,
        "arena_count": 1,
        "dimension_count": 1,
        "unsupported_candidates_skipped": 0,
    }
    proposal = result["proposals"][0]
    assert proposal["proposal_id"] == "np-001"
    assert proposal["arena_slug"] == "cn-bci-industrialization"
    assert proposal["dimension"] == "participants"
    assert proposal["body"] is None
    assert proposal["supported_by_claims"] == [claim["claim_id"]]
    assert proposal["source_ids"] == ["src-001"]
    assert proposal["existing_narrative_excerpt"] == "existing cn-bci-industrialization participants"
    assert proposal["decision"] is None
    assert proposal["decision_reason"] is None
    assert proposal["edited_title"] is None
    assert proposal["edited_body"] is None
    assert proposal["evidence_summary"] == [
        {
            "claim_id": claim["claim_id"],
            "claim_text": "侵入式脑机接口商业化主要依赖医疗场景验证",
            "confidence": "medium_high",
            "as_of": "2024-12-31",
            "evidence_source_ids": ["src-001"],
        }
    ]


def test_build_proposal_file_filters_non_active_non_arena_and_other_source(tmp_path):
    registry = ClaimRegistry(tmp_path)
    _create_claim(registry, status="retired")
    _create_claim(registry, scope_type="company", scope_ref="SSE_600519")
    _create_claim(registry, source_id="src-other")

    result = build_proposal_file(
        registry=registry,
        arena_slug="cn-bci-industrialization",
        source_id="src-001",
        generated_at="2026-04-30T12:00:00+00:00",
        existing_excerpt_loader=lambda arena, dim: "",
    )

    assert result["proposals"] == []
    assert result["unmapped_claims"] == []
    assert result["summary_stats"] == {
        "total_proposals": 0,
        "arena_count": 0,
        "dimension_count": 0,
        "unsupported_candidates_skipped": 0,
    }


def test_build_proposal_file_records_unmapped_claims_without_proposals(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry, dimension_hint="unmapped_dimension")

    result = build_proposal_file(
        registry=registry,
        arena_slug="cn-bci-industrialization",
        source_id="src-001",
        generated_at="2026-04-30T12:00:00+00:00",
        existing_excerpt_loader=lambda arena, dim: "",
    )

    assert result["proposals"] == []
    assert result["unmapped_claims"] == [
        {
            "claim_id": claim["claim_id"],
            "claim_text": claim["claim_text"],
            "dimension_hint": "unmapped_dimension",
            "reason": "unmapped dimension_hint",
        }
    ]
    assert result["summary_stats"]["unsupported_candidates_skipped"] == 1

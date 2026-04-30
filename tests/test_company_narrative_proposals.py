from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from app.io.narrative_proposals import (
    CLAIM_DIMENSION_TO_COMPANY_NARRATIVE,
    apply_proposal_file,
    build_proposal_file,
    map_claim_dimension,
    validate_proposal_decisions,
)


def _create_claim(
    registry,
    *,
    claim_text="茅台白酒业务毛利率长期稳定在 90% 以上",
    scope_type="company",
    scope_ref="SSE_600519",
    dimension_hint="moat",
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
        as_of="2025-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    if status != "active":
        claim["status"] = status
        registry._rewrite_claim(claim)
    return claim


def test_map_company_dimension_hints():
    assert map_claim_dimension("moat", "company") == "moat"
    assert map_claim_dimension("financial_profile", "company") == "financial_profile"
    assert map_claim_dimension("catalysts", "company") == "catalysts"
    assert map_claim_dimension("thesis", "company") == "business_model"
    assert map_claim_dimension("risk", "company") == "risks"
    assert CLAIM_DIMENSION_TO_COMPANY_NARRATIVE["valuation"] == "valuation"


def test_build_company_proposal_file_groups_active_claims(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)

    result = build_proposal_file(
        registry=registry,
        source_id="src-001",
        generated_at="2026-04-30T12:00:00+00:00",
        scope_type="company",
        scope_ref="SSE_600519",
        existing_excerpt_loader=lambda scope_type, scope_ref, dim: f"existing {scope_type} {scope_ref} {dim}",
    )

    assert result["scope_type"] == "company"
    assert result["scope_ref"] == "SSE_600519"
    assert result["unmapped_claims"] == []
    assert result["summary_stats"] == {
        "total_proposals": 1,
        "scope_count": 1,
        "dimension_count": 1,
        "unsupported_candidates_skipped": 0,
    }
    proposal = result["proposals"][0]
    assert proposal["scope_type"] == "company"
    assert proposal["scope_ref"] == "SSE_600519"
    assert "arena_slug" not in proposal
    assert proposal["dimension"] == "moat"
    assert proposal["supported_by_claims"] == [claim["claim_id"]]
    assert proposal["existing_narrative_excerpt"] == "existing company SSE_600519 moat"


def test_build_company_proposal_file_filters_non_company_and_other_source(tmp_path):
    registry = ClaimRegistry(tmp_path)
    _create_claim(registry, status="retired")
    _create_claim(registry, scope_type="arena", scope_ref="cn-bci-industrialization")
    _create_claim(registry, source_id="src-other")

    result = build_proposal_file(
        registry=registry,
        source_id="src-001",
        generated_at="2026-04-30T12:00:00+00:00",
        scope_type="company",
        scope_ref="SSE_600519",
        existing_excerpt_loader=lambda scope_type, scope_ref, dim: "",
    )

    assert result["proposals"] == []
    assert result["unmapped_claims"] == []


def test_validate_company_proposal_rejects_arena_definition_semantics(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)
    data = {
        "source_id": "src-001",
        "proposal_version": "phase3a-v1",
        "scope_type": "company",
        "scope_ref": "SSE_600519",
        "proposals": [
            {
                "proposal_id": "np-001",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "dimension": "definition",
                "title": "bad",
                "body": "body",
                "supported_by_claims": [claim["claim_id"]],
                "source_ids": ["src-001"],
                "decision": "approve",
                "decision_reason": "ok",
            }
        ],
    }
    errors = validate_proposal_decisions(data, registry)
    assert any("invalid narrative dimension 'definition' for scope company" in e for e in errors)


def test_apply_company_proposal_writes_to_narratives_subdir(tmp_path):
    import json
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)
    narr_dir = tmp_path / "companies" / "SSE_600519" / "narratives"
    narr_dir.mkdir(parents=True)
    (narr_dir / "moat.md").write_text("# moat · 贵州茅台\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    data = {
        "source_id": "src-001",
        "proposal_version": "phase3a-v1",
        "scope_type": "company",
        "scope_ref": "SSE_600519",
        "proposals": [
            {
                "proposal_id": "np-001",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "dimension": "moat",
                "title": "品牌与经销体系的双重护城河",
                "body": "茅台的护城河来自品牌与渠道的双重稳定性。",
                "supported_by_claims": [claim["claim_id"]],
                "source_ids": ["src-001"],
                "decision": "approve",
                "decision_reason": "claim 支撑明确",
            }
        ],
    }
    pending.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    result = apply_proposal_file(
        data=data,
        registry=registry,
        base=tmp_path,
        pending_path=pending,
        today="2026-04-30",
        now="2026-04-30T12:00:00+00:00",
    )

    assert result == {"applied": 1, "rejected": 0, "deferred": 0}
    text = (narr_dir / "moat.md").read_text(encoding="utf-8")
    assert "### 品牌与经销体系的双重护城河" in text
    assert "茅台的护城河来自品牌与渠道的双重稳定性。" in text
    assert f"supported_by_claims: [{claim['claim_id']}]" in text
    archived = tmp_path / "data" / "pending" / "archive" / pending.name
    assert archived.exists()

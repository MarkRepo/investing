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


from app.io.narrative_proposals import (
    apply_proposal_file,
    validate_proposal_decisions,
)


def _proposal_file(claim_id):
    return {
        "source_id": "src-001",
        "generated_at": "2026-04-30T12:00:00+00:00",
        "proposal_version": "phase3a-v1",
        "scope_type": "arena",
        "proposals": [
            {
                "proposal_id": "np-001",
                "arena_slug": "cn-bci-industrialization",
                "dimension": "participants",
                "title": "参与者格局变化",
                "body": "医疗场景仍是脑机接口商业化的主要验证路径。",
                "supported_by_claims": [claim_id],
                "source_ids": ["src-001"],
                "evidence_summary": [],
                "existing_narrative_excerpt": "",
                "decision": "approve",
                "decision_reason": "claim 支撑明确",
                "edited_title": None,
                "edited_body": None,
            }
        ],
        "unmapped_claims": [],
        "summary_stats": {},
    }


def test_validate_proposal_decisions_rejects_missing_body_and_placeholder(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)
    data = _proposal_file(claim["claim_id"])
    data["proposals"][0]["body"] = None

    errors = validate_proposal_decisions(data, registry)
    assert "np-001: approve requires non-empty body" in errors

    data["proposals"][0]["body"] = "待填写"
    errors = validate_proposal_decisions(data, registry)
    assert "np-001: body must not be placeholder text" in errors


def test_validate_proposal_decisions_rejects_retired_claim_and_definition(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry, status="retired")
    data = _proposal_file(claim["claim_id"])
    data["proposals"][0]["dimension"] = "definition"

    errors = validate_proposal_decisions(data, registry)

    assert "np-001: dimension definition cannot be written by narrative proposals" in errors
    assert f"np-001: supported claim {claim['claim_id']} is not active" in errors


def test_apply_proposal_file_appends_markdown_audit_and_archives(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)
    arena_dir = tmp_path / "arenas" / "cn-bci-industrialization"
    arena_dir.mkdir(parents=True)
    target = arena_dir / "participants.md"
    target.write_text("# 参与者与相对位置 · 脑机接口\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    data = _proposal_file(claim["claim_id"])
    pending.write_text(__import__("json").dumps(data, ensure_ascii=False), encoding="utf-8")

    result = apply_proposal_file(
        data=data,
        registry=registry,
        base=tmp_path,
        pending_path=pending,
        today="2026-04-30",
        now="2026-04-30T12:00:00+00:00",
    )

    assert result == {"applied": 1, "rejected": 0, "deferred": 0}
    text = target.read_text(encoding="utf-8")
    assert "### 参与者格局变化" in text
    assert "status: active" in text
    assert "last_written: 2026-04-30" in text
    assert f"supported_by_claims: [{claim['claim_id']}]" in text
    assert "source_ids: [src-001]" in text
    assert "proposal_id: np-001" in text
    assert "医疗场景仍是脑机接口商业化的主要验证路径。" in text
    audit_lines = (tmp_path / "data" / "audit" / "narrative-events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(audit_lines) == 1
    archived = tmp_path / "data" / "pending" / "archive" / pending.name
    assert archived.exists()
    assert not pending.exists()


def test_apply_proposal_file_uses_edited_body(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)
    arena_dir = tmp_path / "arenas" / "cn-bci-industrialization"
    arena_dir.mkdir(parents=True)
    (arena_dir / "participants.md").write_text("# x\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    data = _proposal_file(claim["claim_id"])
    data["proposals"][0]["decision"] = "edit"
    data["proposals"][0]["edited_title"] = "编辑后的标题"
    data["proposals"][0]["edited_body"] = "编辑后的正文。"
    pending.write_text(__import__("json").dumps(data, ensure_ascii=False), encoding="utf-8")

    result = apply_proposal_file(
        data=data,
        registry=registry,
        base=tmp_path,
        pending_path=pending,
        today="2026-04-30",
        now="2026-04-30T12:00:00+00:00",
    )

    assert result["applied"] == 1
    text = (arena_dir / "participants.md").read_text(encoding="utf-8")
    assert "### 编辑后的标题" in text
    assert "编辑后的正文。" in text
    assert "医疗场景仍是脑机接口商业化的主要验证路径。" not in text


from app.io.narrative_proposals import (
    SCOPE_CONFIGS,
    dimension_path,
    flags_path,
    narrative_dims_for_scope,
)


def test_scope_configs_cover_arena_and_company():
    assert "arena" in SCOPE_CONFIGS
    assert "company" in SCOPE_CONFIGS
    assert "definition" not in narrative_dims_for_scope("arena")
    # company has no "definition" dim, all 8 COMPANY_DIMENSIONS are allowed
    from app import config as cfg
    assert set(narrative_dims_for_scope("company")) == set(cfg.COMPANY_DIMENSIONS)


def test_dimension_path_for_arena_and_company(tmp_path):
    arena_path = dimension_path(tmp_path, "arena", "cn-bci-industrialization", "participants")
    assert arena_path == tmp_path / "arenas" / "cn-bci-industrialization" / "participants.md"

    company_path = dimension_path(tmp_path, "company", "SSE_600519", "moat")
    assert company_path == tmp_path / "companies" / "SSE_600519" / "narratives" / "moat.md"

    company_kebab = dimension_path(tmp_path, "company", "SSE_600519", "growth_engine")
    assert company_kebab.name == "growth-engine.md"


def test_flags_path_for_arena_and_company(tmp_path):
    arena_flags = flags_path(tmp_path, "arena", "cn-bci-industrialization")
    assert arena_flags == tmp_path / "arenas" / "cn-bci-industrialization" / "narrative-flags.jsonl"

    company_flags = flags_path(tmp_path, "company", "SSE_600519")
    assert company_flags == tmp_path / "companies" / "SSE_600519" / "narrative-flags.jsonl"

from app.io.narrative_proposals import (
    CLAIM_DIMENSION_TO_INDUSTRY_NARRATIVE,
)


def test_scope_configs_cover_industry():
    from app.io.narrative_proposals import SCOPE_CONFIGS, narrative_dims_for_scope
    assert "industry" in SCOPE_CONFIGS
    dims = narrative_dims_for_scope("industry")
    assert "definition" not in dims
    from app import config as cfg
    assert set(dims) == {d for d in cfg.INDUSTRY_DIMENSIONS if d != "definition"}


def test_dimension_path_for_industry(tmp_path):
    from app.io.narrative_proposals import dimension_path
    path = dimension_path(tmp_path, "industry", "cn-power-equipment", "market_size")
    assert path == tmp_path / "industries" / "cn-power-equipment" / "market-size.md"

    path2 = dimension_path(tmp_path, "industry", "cn-power-equipment", "value_chain")
    assert path2.name == "value-chain.md"


def test_flags_path_for_industry(tmp_path):
    from app.io.narrative_proposals import flags_path
    path = flags_path(tmp_path, "industry", "cn-power-equipment")
    assert path == tmp_path / "industries" / "cn-power-equipment" / "narrative-flags.jsonl"


def test_industry_dimension_mapping_spot_checks():
    from app.io.narrative_proposals import map_claim_dimension
    assert map_claim_dimension("market_size", "industry") == "market_size"
    assert map_claim_dimension("stage_gate", "industry") == "lifecycle"
    assert map_claim_dimension("supply_chain", "industry") == "value_chain"
    assert map_claim_dimension("competition", "industry") == "competition"
    assert map_claim_dimension("regulation", "industry") == "regulation"
    assert map_claim_dimension("benchmark", "industry") == "benchmark"
    assert map_claim_dimension("risk", "industry") == "risks"
    assert map_claim_dimension("valuation", "industry") == "valuation"
    assert CLAIM_DIMENSION_TO_INDUSTRY_NARRATIVE["thesis"] == "drivers"

import json

from app.io.claim_registry import ClaimRegistry, build_evidence_entry


def test_create_claim_writes_scope_file_and_counter(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )

    claim = registry.create_claim(
        claim_text="茅台品牌溢价具备韧性",
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2024-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="match-src-001.json#cc-001",
        now="2026-04-30T12:00:00+00:00",
    )

    assert claim["claim_id"] == "clm-company-0001"
    assert claim["status"] == "active"
    assert claim["user_override"] is None
    assert claim["schema_version"] == "phase2-v1"
    assert claim["supporting_evidence"] == [evidence]
    assert claim["state_log"] == [
        {
            "timestamp": "2026-04-30T12:00:00+00:00",
            "from_status": None,
            "to_status": "active",
            "trigger": "created",
            "trigger_ref": "match-src-001.json#cc-001",
        }
    ]

    lines = (tmp_path / "claims" / "companies.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["claim_id"] == "clm-company-0001"
    counters = json.loads((tmp_path / "claims" / ".counters.json").read_text(encoding="utf-8"))
    assert counters == {"company": 1}


def test_registry_loads_existing_claim_by_id_and_scope(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=[],
        direction="neutral",
        now="2026-04-30T12:00:00+00:00",
    )
    created = registry.create_claim(
        claim_text="行业需求存在波动",
        scope_type="industry",
        scope_ref="cn-power-equipment",
        claim_type="risk",
        dimension_hint="demand",
        confidence="medium",
        as_of="2024-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="match-src-001.json#cc-001",
        now="2026-04-30T12:00:00+00:00",
    )

    reloaded = ClaimRegistry(tmp_path)

    assert reloaded.find_by_id(created["claim_id"])["claim_text"] == "行业需求存在波动"
    assert [c["claim_id"] for c in reloaded.claims_for_scope("industry", "cn-power-equipment")] == [created["claim_id"]]

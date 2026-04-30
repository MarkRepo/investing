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


def _seed_company_claim(registry, *, claim_text="原命题", confidence="medium_high"):
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    return registry.create_claim(
        claim_text=claim_text,
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence=confidence,
        as_of="2024-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="match-src-001.json#cc-001",
        now="2026-04-30T12:00:00+00:00",
    )


def test_append_evidence_does_not_change_confidence_or_state_log(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _seed_company_claim(registry, confidence="high")
    evidence = build_evidence_entry(
        source_id="src-002",
        block_ids=["ib-002"],
        fact_ids=["fact-002"],
        direction="refutes",
        now="2026-04-30T13:00:00+00:00",
    )

    updated = registry.append_evidence(
        claim["claim_id"],
        evidence,
        now="2026-04-30T13:00:00+00:00",
    )

    assert updated["confidence"] == "high"
    assert updated["status"] == "active"
    assert len(updated["supporting_evidence"]) == 2
    assert updated["supporting_evidence"][1] == evidence
    assert len(updated["state_log"]) == 1


def test_split_retires_original_and_creates_new_claims_without_migrating_history(tmp_path):
    registry = ClaimRegistry(tmp_path)
    original = _seed_company_claim(registry)
    new_claims = registry.split_claim(
        original["claim_id"],
        new_claim_specs=[
            {
                "claim_text": "新命题 A",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "claim_type": "judgment",
                "dimension_hint": "moat",
                "confidence": "medium",
                "as_of": "2024-12-31",
                "evidence": build_evidence_entry(
                    source_id="src-002",
                    block_ids=["ib-002"],
                    fact_ids=["fact-002"],
                    direction="supports",
                    now="2026-04-30T13:00:00+00:00",
                ),
            }
        ],
        now="2026-04-30T13:00:00+00:00",
    )

    retired = registry.find_by_id(original["claim_id"])
    assert retired["status"] == "retired"
    assert retired["supporting_evidence"] == original["supporting_evidence"]
    assert retired["state_log"][-1]["trigger"] == "split"
    assert retired["state_log"][-1]["split_to_claim_ids"] == [new_claims[0]["claim_id"]]
    assert new_claims[0]["state_log"][0]["trigger"] == "split_from"
    assert new_claims[0]["state_log"][0]["trigger_ref"] == original["claim_id"]
    assert new_claims[0]["supporting_evidence"][0]["source_id"] == "src-002"
    assert len(new_claims[0]["supporting_evidence"]) == 1


def test_audit_event_appends_jsonl(tmp_path):
    registry = ClaimRegistry(tmp_path)

    registry.append_audit_event(
        {
            "event_type": "candidate_skipped",
            "source_id": "src-001",
            "candidate_id": "cc-001",
        }
    )

    events = (tmp_path / "audit" / "claim-events.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(events[0]) == {
        "event_type": "candidate_skipped",
        "source_id": "src-001",
        "candidate_id": "cc-001",
    }


def test_check_integrity_detects_counter_mismatch(tmp_path):
    registry = ClaimRegistry(tmp_path)
    _seed_company_claim(registry)
    (tmp_path / "claims" / ".counters.json").write_text('{"company": 9}\n', encoding="utf-8")

    warnings = ClaimRegistry(tmp_path).check_integrity()

    assert warnings == ["counter mismatch for company: counter=9 max_id=1"]


def test_list_claims_filters_by_scope(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence_company = build_evidence_entry(
        source_id="src-company-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    company_claim = registry.create_claim(
        claim_text="公司具备主题相关性",
        scope_type="company",
        scope_ref="SSE_603011",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2024-12-31",
        evidence=evidence_company,
        trigger="created",
        trigger_ref="match-src-company-001.json#cc-001",
        now="2026-04-30T12:00:00+00:00",
    )
    evidence_industry = build_evidence_entry(
        source_id="src-industry-001",
        block_ids=["ib-002"],
        fact_ids=[],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    registry.create_claim(
        claim_text="核聚变行业处于快速成长阶段",
        scope_type="industry",
        scope_ref="cn-nuclear-fusion",
        claim_type="judgment",
        dimension_hint="lifecycle",
        confidence="medium",
        as_of="2024-12-31",
        evidence=evidence_industry,
        trigger="created",
        trigger_ref="match-src-industry-001.json#cc-001",
        now="2026-04-30T12:00:00+00:00",
    )

    rows = registry.list_claims(scope_type="company", scope_ref="SSE_603011")

    assert len(rows) == 1
    assert rows[0]["claim_id"] == company_claim["claim_id"]

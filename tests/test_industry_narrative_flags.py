import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from app.io.narrative_proposals import read_narrative_flags, scan_narrative_flags
from scripts import industry_narrative_flags


def _claim(registry, *, status="active", direction="supports"):
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction=direction,
        now="2026-04-30T12:00:00+00:00",
    )
    claim = registry.create_claim(
        claim_text="中国变压器行业进入容量扩张中后期",
        scope_type="industry",
        scope_ref="cn-power-equipment",
        claim_type="judgment",
        dimension_hint="lifecycle",
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


def _write_segment(tmp_path, claim_id, dim="lifecycle"):
    slug_dir = tmp_path / "industries" / "cn-power-equipment"
    slug_dir.mkdir(parents=True, exist_ok=True)
    (slug_dir / f"{dim.replace('_', '-')}.md").write_text(
        "# heading\n\n"
        "### 容量扩张中后期\n\n"
        "status: active\n"
        "last_written: 2026-04-30\n"
        f"supported_by_claims: [{claim_id}]\n"
        "source_ids: [src-001]\n"
        "proposal_id: np-001\n\n"
        "正文。\n",
        encoding="utf-8",
    )


def test_scan_industry_flags_no_flag_for_active(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry)
    _write_segment(tmp_path, claim["claim_id"])

    flags = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="industry",
        scope_ref="cn-power-equipment",
        now="2026-04-30T12:00:00+00:00",
    )

    assert flags == []
    assert read_narrative_flags("industry", "cn-power-equipment", base=tmp_path) == []


def test_scan_industry_flags_writes_critical_for_retired(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, status="retired")
    _write_segment(tmp_path, claim["claim_id"])

    flags = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="industry",
        scope_ref="cn-power-equipment",
        now="2026-04-30T12:00:00+00:00",
    )

    assert len(flags) == 1
    assert flags[0]["flag_level"] == "critical"
    assert flags[0]["reason"] == "supporting claim retired"
    assert flags[0]["scope_type"] == "industry"
    assert flags[0]["scope_ref"] == "cn-power-equipment"


def test_scan_industry_flags_dedups_on_rerun(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, direction="refutes")
    _write_segment(tmp_path, claim["claim_id"])

    first = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="industry",
        scope_ref="cn-power-equipment",
        now="2026-04-30T12:00:00+00:00",
    )
    second = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="industry",
        scope_ref="cn-power-equipment",
        now="2026-04-30T12:01:00+00:00",
    )

    assert len(first) == 1
    assert first[0]["flag_level"] == "significant"
    assert second == []


def test_industry_narrative_flags_cli(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, status="retired")
    _write_segment(tmp_path, claim["claim_id"])

    rc = industry_narrative_flags.cmd_flags(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            industry="cn-power-equipment",
        )
    )

    assert rc == 0
    flag_file = tmp_path / "industries" / "cn-power-equipment" / "narrative-flags.jsonl"
    rows = [json.loads(line) for line in flag_file.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["reason"] == "supporting claim retired"

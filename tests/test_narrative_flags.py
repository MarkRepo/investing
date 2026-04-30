import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from app.io.narrative_proposals import read_narrative_flags, scan_narrative_flags
from scripts import narrative_flags


def _claim(registry, *, status="active", direction="supports"):
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction=direction,
        now="2026-04-30T12:00:00+00:00",
    )
    claim = registry.create_claim(
        claim_text="医疗场景支撑脑机接口商业化验证",
        scope_type="arena",
        scope_ref="cn-bci-industrialization",
        claim_type="judgment",
        dimension_hint="competitive_position",
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


def _write_segment(tmp_path, claim_id):
    arena_dir = tmp_path / "arenas" / "cn-bci-industrialization"
    arena_dir.mkdir(parents=True)
    (arena_dir / "participants.md").write_text(
        "# participants\n\n"
        "### 参与者格局\n\n"
        "status: active\n"
        "last_written: 2026-04-30\n"
        f"supported_by_claims: [{claim_id}]\n"
        "source_ids: [src-001]\n"
        "proposal_id: np-001\n\n"
        "正文。\n",
        encoding="utf-8",
    )


def test_scan_narrative_flags_no_flag_for_active_supporting_claim(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry)
    _write_segment(tmp_path, claim["claim_id"])

    flags = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        arena_slug="cn-bci-industrialization",
        now="2026-04-30T12:00:00+00:00",
    )

    assert flags == []
    assert read_narrative_flags("cn-bci-industrialization", base=tmp_path) == []


def test_scan_narrative_flags_writes_critical_for_retired_and_missing(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, status="retired")
    _write_segment(tmp_path, claim["claim_id"])
    with (tmp_path / "arenas" / "cn-bci-industrialization" / "participants.md").open("a", encoding="utf-8") as f:
        f.write("\n### Missing\n\nsupported_by_claims: [clm-arena-9999]\nproposal_id: np-002\n\nbody\n")

    flags = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        arena_slug="cn-bci-industrialization",
        now="2026-04-30T12:00:00+00:00",
    )

    assert [f["flag_level"] for f in flags] == ["critical", "critical"]
    assert {f["reason"] for f in flags} == {"supporting claim retired", "supporting claim missing"}
    stored = read_narrative_flags("cn-bci-industrialization", base=tmp_path)
    assert len(stored) == 2
    assert stored[0]["flag_id"] == "nf-0001"
    assert stored[1]["flag_id"] == "nf-0002"


def test_scan_narrative_flags_writes_significant_for_refuting_evidence_and_dedups(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, direction="refutes")
    _write_segment(tmp_path, claim["claim_id"])

    first = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        arena_slug="cn-bci-industrialization",
        now="2026-04-30T12:00:00+00:00",
    )
    second = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        arena_slug="cn-bci-industrialization",
        now="2026-04-30T12:01:00+00:00",
    )

    assert len(first) == 1
    assert first[0]["flag_level"] == "significant"
    assert first[0]["reason"] == "supporting claim has refuting evidence"
    assert second == []
    assert len(read_narrative_flags("cn-bci-industrialization", base=tmp_path)) == 1


def test_narrative_flags_cli(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, status="retired")
    _write_segment(tmp_path, claim["claim_id"])

    rc = narrative_flags.cmd_flags(
        Namespace(registry_base=str(tmp_path), base=str(tmp_path), arena="cn-bci-industrialization")
    )

    assert rc == 0
    rows = [json.loads(line) for line in (tmp_path / "arenas" / "cn-bci-industrialization" / "narrative-flags.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["reason"] == "supporting claim retired"

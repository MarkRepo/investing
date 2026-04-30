import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import narrative_apply, narrative_flags, narrative_propose


def test_phase3a_propose_apply_flag_flow(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
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
    arena_dir = tmp_path / "arenas" / "cn-bci-industrialization"
    arena_dir.mkdir(parents=True)
    (arena_dir / "participants.md").write_text("# participants\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"

    rc = narrative_propose.cmd_propose(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            source_id="src-001",
            arena="cn-bci-industrialization",
            out=str(pending),
        )
    )
    assert rc == 0

    data = json.loads(pending.read_text(encoding="utf-8"))
    data["proposals"][0]["title"] = "参与者格局"
    data["proposals"][0]["body"] = "医疗场景是主要验证路径。"
    data["proposals"][0]["decision"] = "approve"
    data["proposals"][0]["decision_reason"] = "claim 支撑明确"
    pending.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    rc = narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )
    assert rc == 0
    assert "医疗场景是主要验证路径。" in (arena_dir / "participants.md").read_text(encoding="utf-8")

    claim["status"] = "retired"
    registry._rewrite_claim(claim)
    rc = narrative_flags.cmd_flags(
        Namespace(registry_base=str(tmp_path), base=str(tmp_path), arena="cn-bci-industrialization")
    )
    assert rc == 0
    flags = (arena_dir / "narrative-flags.jsonl").read_text(encoding="utf-8")
    assert "supporting claim retired" in flags

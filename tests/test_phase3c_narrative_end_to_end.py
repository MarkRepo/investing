import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import (
    industry_narrative_apply,
    industry_narrative_flags,
    industry_narrative_propose,
)


def test_phase3c_propose_apply_flag_flow(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
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
    slug_dir = tmp_path / "industries" / "cn-power-equipment"
    slug_dir.mkdir(parents=True)
    (slug_dir / "lifecycle.md").write_text("# lifecycle\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"

    rc = industry_narrative_propose.cmd_propose(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            source_id="src-001",
            industry="cn-power-equipment",
            out=str(pending),
        )
    )
    assert rc == 0

    data = json.loads(pending.read_text(encoding="utf-8"))
    data["proposals"][0]["title"] = "容量扩张中后期"
    data["proposals"][0]["body"] = "下游电网投资周期推动容量扩张进入中后期。"
    data["proposals"][0]["decision"] = "approve"
    data["proposals"][0]["decision_reason"] = "claim 支撑明确"
    pending.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    rc = industry_narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )
    assert rc == 0
    assert "下游电网投资周期推动容量扩张进入中后期。" in (slug_dir / "lifecycle.md").read_text(encoding="utf-8")

    claim["status"] = "retired"
    registry._rewrite_claim(claim)
    rc = industry_narrative_flags.cmd_flags(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            industry="cn-power-equipment",
        )
    )
    assert rc == 0
    flags = (slug_dir / "narrative-flags.jsonl").read_text(encoding="utf-8")
    assert "supporting claim retired" in flags

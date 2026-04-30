import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import (
    company_narrative_apply,
    company_narrative_flags,
    company_narrative_propose,
)


def test_phase3b_propose_apply_flag_flow(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    claim = registry.create_claim(
        claim_text="品牌力支撑长期毛利率",
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2025-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    narr_dir = tmp_path / "companies" / "SSE_600519" / "narratives"
    narr_dir.mkdir(parents=True)
    (narr_dir / "moat.md").write_text("# moat\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"

    rc = company_narrative_propose.cmd_propose(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            source_id="src-001",
            market="SSE",
            ticker="600519",
            out=str(pending),
        )
    )
    assert rc == 0

    data = json.loads(pending.read_text(encoding="utf-8"))
    data["proposals"][0]["title"] = "护城河"
    data["proposals"][0]["body"] = "品牌与经销体系是长期双重护城河。"
    data["proposals"][0]["decision"] = "approve"
    data["proposals"][0]["decision_reason"] = "claim 支撑明确"
    pending.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    rc = company_narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )
    assert rc == 0
    assert "品牌与经销体系是长期双重护城河。" in (narr_dir / "moat.md").read_text(encoding="utf-8")

    claim["status"] = "retired"
    registry._rewrite_claim(claim)
    rc = company_narrative_flags.cmd_flags(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            market="SSE",
            ticker="600519",
        )
    )
    assert rc == 0
    flags = (tmp_path / "companies" / "SSE_600519" / "narrative-flags.jsonl").read_text(encoding="utf-8")
    assert "supporting claim retired" in flags

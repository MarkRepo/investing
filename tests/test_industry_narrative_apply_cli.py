import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import industry_narrative_apply, industry_narrative_propose


def _seed_industry_claim(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    return registry.create_claim(
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


def test_industry_narrative_propose_writes_pending_json(tmp_path):
    claim = _seed_industry_claim(tmp_path)
    slug_dir = tmp_path / "industries" / "cn-power-equipment"
    slug_dir.mkdir(parents=True)
    (slug_dir / "lifecycle.md").write_text("# lifecycle\n\nold lifecycle text", encoding="utf-8")
    out = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"

    rc = industry_narrative_propose.cmd_propose(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            source_id="src-001",
            industry="cn-power-equipment",
            out=str(out),
        )
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["scope_type"] == "industry"
    assert data["scope_ref"] == "cn-power-equipment"
    proposal = data["proposals"][0]
    assert proposal["scope_type"] == "industry"
    assert proposal["scope_ref"] == "cn-power-equipment"
    assert proposal["supported_by_claims"] == [claim["claim_id"]]
    assert proposal["existing_narrative_excerpt"].endswith("old lifecycle text")


def test_industry_narrative_apply_returns_nonzero_for_invalid_file(tmp_path, capsys):
    _seed_industry_claim(tmp_path)
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    pending.write_text(
        json.dumps(
            {
                "source_id": "src-001",
                "proposal_version": "phase3a-v1",
                "scope_type": "industry",
                "scope_ref": "cn-power-equipment",
                "proposals": [
                    {
                        "proposal_id": "np-001",
                        "scope_type": "industry",
                        "scope_ref": "cn-power-equipment",
                        "dimension": "lifecycle",
                        "decision": "approve",
                        "decision_reason": "ok",
                        "body": None,
                        "supported_by_claims": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rc = industry_narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )

    assert rc == 1
    captured = capsys.readouterr()
    assert "supported_by_claims required" in captured.err
    assert pending.exists()


def test_industry_narrative_apply_applies_valid_file(tmp_path):
    claim = _seed_industry_claim(tmp_path)
    slug_dir = tmp_path / "industries" / "cn-power-equipment"
    slug_dir.mkdir(parents=True)
    (slug_dir / "lifecycle.md").write_text("# lifecycle\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    pending.write_text(
        json.dumps(
            {
                "source_id": "src-001",
                "proposal_version": "phase3a-v1",
                "scope_type": "industry",
                "scope_ref": "cn-power-equipment",
                "proposals": [
                    {
                        "proposal_id": "np-001",
                        "scope_type": "industry",
                        "scope_ref": "cn-power-equipment",
                        "dimension": "lifecycle",
                        "title": "容量扩张中后期",
                        "body": "下游电网投资周期推动容量扩张进入中后期。",
                        "supported_by_claims": [claim["claim_id"]],
                        "source_ids": ["src-001"],
                        "decision": "approve",
                        "decision_reason": "claim 支撑明确",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    rc = industry_narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )

    assert rc == 0
    text = (slug_dir / "lifecycle.md").read_text(encoding="utf-8")
    assert "下游电网投资周期推动容量扩张进入中后期。" in text
    assert (tmp_path / "data" / "pending" / "archive" / pending.name).exists()

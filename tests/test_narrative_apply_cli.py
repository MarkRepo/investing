import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import narrative_apply, narrative_propose


def _seed_claim(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    return registry.create_claim(
        claim_text="脑机接口商业化依赖医疗场景验证",
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


def test_narrative_propose_cli_writes_pending_json(tmp_path):
    claim = _seed_claim(tmp_path)
    arena_dir = tmp_path / "arenas" / "cn-bci-industrialization"
    arena_dir.mkdir(parents=True)
    (arena_dir / "participants.md").write_text("# participants\n\nold text", encoding="utf-8")
    out = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"

    rc = narrative_propose.cmd_propose(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            source_id="src-001",
            arena="cn-bci-industrialization",
            out=str(out),
        )
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source_id"] == "src-001"
    assert data["proposals"][0]["supported_by_claims"] == [claim["claim_id"]]
    assert data["proposals"][0]["existing_narrative_excerpt"].endswith("old text")


def test_narrative_apply_cli_returns_nonzero_for_invalid_file(tmp_path, capsys):
    _seed_claim(tmp_path)
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    pending.write_text(
        json.dumps(
            {
                "source_id": "src-001",
                "proposal_version": "phase3a-v1",
                "scope_type": "arena",
                "proposals": [
                    {
                        "proposal_id": "np-001",
                        "arena_slug": "cn-bci-industrialization",
                        "dimension": "participants",
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

    rc = narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )

    assert rc == 1
    captured = capsys.readouterr()
    assert "supported_by_claims required" in captured.err
    assert pending.exists()


def test_narrative_apply_cli_applies_valid_file(tmp_path):
    claim = _seed_claim(tmp_path)
    arena_dir = tmp_path / "arenas" / "cn-bci-industrialization"
    arena_dir.mkdir(parents=True)
    (arena_dir / "participants.md").write_text("# participants\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    pending.write_text(
        json.dumps(
            {
                "source_id": "src-001",
                "proposal_version": "phase3a-v1",
                "scope_type": "arena",
                "proposals": [
                    {
                        "proposal_id": "np-001",
                        "arena_slug": "cn-bci-industrialization",
                        "dimension": "participants",
                        "title": "参与者格局",
                        "body": "医疗场景是主要验证路径。",
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

    rc = narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )

    assert rc == 0
    assert "医疗场景是主要验证路径。" in (arena_dir / "participants.md").read_text(encoding="utf-8")
    assert (tmp_path / "data" / "pending" / "archive" / pending.name).exists()

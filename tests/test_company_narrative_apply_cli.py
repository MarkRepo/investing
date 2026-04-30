import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import company_narrative_apply, company_narrative_propose


def _seed_company_claim(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    return registry.create_claim(
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


def test_company_narrative_propose_writes_pending_json(tmp_path):
    claim = _seed_company_claim(tmp_path)
    narr_dir = tmp_path / "companies" / "SSE_600519" / "narratives"
    narr_dir.mkdir(parents=True)
    (narr_dir / "moat.md").write_text("# moat\n\nold moat text", encoding="utf-8")
    out = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"

    rc = company_narrative_propose.cmd_propose(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            source_id="src-001",
            market="SSE",
            ticker="600519",
            out=str(out),
        )
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["scope_type"] == "company"
    assert data["scope_ref"] == "SSE_600519"
    proposal = data["proposals"][0]
    assert proposal["scope_type"] == "company"
    assert proposal["scope_ref"] == "SSE_600519"
    assert proposal["supported_by_claims"] == [claim["claim_id"]]
    assert proposal["existing_narrative_excerpt"].endswith("old moat text")


def test_company_narrative_apply_returns_nonzero_for_invalid_file(tmp_path, capsys):
    _seed_company_claim(tmp_path)
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    pending.write_text(
        json.dumps(
            {
                "source_id": "src-001",
                "proposal_version": "phase3a-v1",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "proposals": [
                    {
                        "proposal_id": "np-001",
                        "scope_type": "company",
                        "scope_ref": "SSE_600519",
                        "dimension": "moat",
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

    rc = company_narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )

    assert rc == 1
    captured = capsys.readouterr()
    assert "supported_by_claims required" in captured.err
    assert pending.exists()


def test_company_narrative_apply_applies_valid_file(tmp_path):
    claim = _seed_company_claim(tmp_path)
    narr_dir = tmp_path / "companies" / "SSE_600519" / "narratives"
    narr_dir.mkdir(parents=True)
    (narr_dir / "moat.md").write_text("# moat\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    pending.write_text(
        json.dumps(
            {
                "source_id": "src-001",
                "proposal_version": "phase3a-v1",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "proposals": [
                    {
                        "proposal_id": "np-001",
                        "scope_type": "company",
                        "scope_ref": "SSE_600519",
                        "dimension": "moat",
                        "title": "护城河",
                        "body": "品牌与经销体系是长期稳定的双重护城河。",
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

    rc = company_narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )

    assert rc == 0
    text = (narr_dir / "moat.md").read_text(encoding="utf-8")
    assert "品牌与经销体系是长期稳定的双重护城河。" in text
    assert (tmp_path / "data" / "pending" / "archive" / pending.name).exists()

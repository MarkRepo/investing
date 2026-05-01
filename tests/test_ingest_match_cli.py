import json
import os
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import ingest_match

_REPO_ROOT = Path(__file__).parent.parent


def _bundle():
    return {
        "source_digest": {"source_id": "src-001", "source_date": "2024-12-31"},
        "claim_candidates": [
            {
                "candidate_id": "cc-001",
                "claim_text": "茅台品牌溢价来自白酒文化根基",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "claim_type": "judgment",
                "dimension_hint": "moat",
                "confidence": "medium_high",
                "as_of": "2024-12-31",
                "direction_on_source": "supports",
                "supporting_block_ids": ["ib-001"],
            }
        ],
    }


def test_cmd_match_writes_pending_file_with_empty_registry(tmp_path):
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(_bundle()), encoding="utf-8")
    out = tmp_path / "pending" / "match-src-001.json"

    rc = ingest_match.cmd_match(
        Namespace(bundle=str(bundle_path), registry_base=str(tmp_path), out=str(out))
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source_id"] == "src-001"
    assert data["bundle_ref"] == str(bundle_path)
    assert data["matching_engine_version"] == "phase2-v1"
    assert data["decisions_required"][0]["candidate_id"] == "cc-001"
    assert data["decisions_required"][0]["top_matches"] == []
    assert data["decisions_required"][0]["decision"] is None
    assert data["summary_stats"] == {
        "total_candidates": 1,
        "with_matches": 0,
        "no_matches_suggest_new": 1,
        "high_confidence_matches": 0,
    }


def test_cmd_match_uses_scope_filtered_registry_claims(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-old",
        block_ids=["ib-old"],
        fact_ids=["fact-old"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    registry.create_claim(
        claim_text="茅台品牌溢价来自白酒消费文化",
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2023-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    registry.create_claim(
        claim_text="茅台品牌溢价来自白酒消费文化",
        scope_type="company",
        scope_ref="SZSE_000858",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2023-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(_bundle()), encoding="utf-8")
    out = tmp_path / "pending" / "match-src-001.json"

    rc = ingest_match.cmd_match(
        Namespace(bundle=str(bundle_path), registry_base=str(tmp_path), out=str(out))
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    matches = data["decisions_required"][0]["top_matches"]
    assert [m["claim_id"] for m in matches] == ["clm-company-0001"]
    assert data["summary_stats"]["with_matches"] == 1


def test_ingest_match_writes_auto_and_pending_decisions(tmp_path):
    bundle = {
        "source_digest": {"source_id": "src-split", "source_date": "2024-12-31"},
        "claim_candidates": [
            {
                "candidate_id": "cc-001",
                "claim_text": "高置信度声明",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "claim_type": "judgment",
                "dimension_hint": "moat",
                "confidence": "high",
                "as_of": "2024-12-31",
                "direction_on_source": "supports",
                "supporting_block_ids": ["ib-001"],
            },
            {
                "candidate_id": "cc-002",
                "claim_text": "中置信度声明",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "claim_type": "judgment",
                "dimension_hint": "moat",
                "confidence": "medium",
                "as_of": "2024-12-31",
                "direction_on_source": "supports",
                "supporting_block_ids": ["ib-002"],
            },
        ],
    }
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    auto_path = tmp_path / "auto" / "match-src-split-auto.json"
    pending_path = tmp_path / "pending" / "match-src-split-pending.json"

    result = subprocess.run(
        [
            sys.executable,
            str(_REPO_ROOT / "scripts" / "ingest_match.py"),
            "--bundle", str(bundle_path),
            "--registry-base", str(tmp_path),
            "--auto-out", str(auto_path),
            "--pending-out", str(pending_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        env={**os.environ, "PYTHONPATH": str(_REPO_ROOT)},
    )
    assert result.returncode == 0, result.stderr

    auto_data = json.loads(auto_path.read_text(encoding="utf-8"))
    pending_data = json.loads(pending_path.read_text(encoding="utf-8"))

    assert [r["candidate_id"] for r in auto_data["decisions_required"]] == ["cc-001"]
    assert [r["candidate_id"] for r in pending_data["decisions_required"]] == ["cc-002"]

    assert auto_data["decisions_required"][0]["confidence"] == "high"
    assert pending_data["decisions_required"][0]["confidence"] == "medium"

    # high-confidence row with no top_matches → auto-approved as "new"
    auto_row = auto_data["decisions_required"][0]
    assert auto_row["top_matches"] == []
    assert auto_row["decision"] == "new"
    assert auto_row["decision_reason"] is not None


def test_auto_apply_no_decision_when_top_matches_exist(tmp_path):
    """High-confidence candidate with existing matches must NOT be auto-approved."""
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-old",
        block_ids=["ib-old"],
        fact_ids=["fact-old"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    registry.create_claim(
        claim_text="高置信度声明",
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="high",
        as_of="2024-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    bundle = {
        "source_digest": {"source_id": "src-match", "source_date": "2024-12-31"},
        "claim_candidates": [
            {
                "candidate_id": "cc-001",
                "claim_text": "高置信度声明",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "claim_type": "judgment",
                "dimension_hint": "moat",
                "confidence": "high",
                "as_of": "2024-12-31",
                "direction_on_source": "supports",
                "supporting_block_ids": ["ib-001"],
            }
        ],
    }
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    auto_path = tmp_path / "auto.json"

    rc = ingest_match.cmd_match(
        Namespace(bundle=str(bundle_path), registry_base=str(tmp_path), auto_out=str(auto_path))
    )
    assert rc == 0
    auto_data = json.loads(auto_path.read_text(encoding="utf-8"))
    auto_row = auto_data["decisions_required"][0]
    assert len(auto_row["top_matches"]) > 0
    # must NOT be auto-approved when there are existing matches to consider
    assert auto_row["decision"] is None

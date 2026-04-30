import json
import os
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import ingest_apply

_REPO_ROOT = Path(__file__).parent.parent


def _bundle():
    return {
        "source_digest": {"source_id": "src-001", "source_date": "2024-12-31"},
        "insight_blocks": [{"id": "ib-001", "title": "品牌", "dimension_hint": "moat"}],
        "atomic_facts": [
            {"fact_id": "fact-001", "linked_block_id": "ib-001", "fact_text": "事实", "confidence": "medium"}
        ],
        "claim_candidates": [],
        "company_candidates": [],
    }


def _decision(candidate, **overrides):
    row = {
        "candidate_id": candidate["candidate_id"],
        "candidate_payload": candidate,
        "top_matches": [],
        "decision": "new",
        "decision_reason": "形成新命题",
        "direction_on_claim": None,
        "target_claim_id": None,
        "split_instructions": None,
    }
    row.update(overrides)
    return row


def _candidate(**overrides):
    candidate = {
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
    candidate.update(overrides)
    return candidate


def _write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_apply_new_creates_claim_and_pending_files(tmp_path):
    bundle = _bundle()
    candidate = _candidate()
    match = {
        "source_id": "src-001",
        "decisions_required": [_decision(candidate)],
    }
    bundle_path = tmp_path / "bundle.json"
    match_path = tmp_path / "pending" / "match-src-001.json"
    match_path.parent.mkdir()
    _write_json(bundle_path, bundle)
    _write_json(match_path, match)

    rc = ingest_apply.cmd_apply(
        Namespace(match=str(match_path), bundle=str(bundle_path), registry_base=str(tmp_path))
    )

    assert rc == 0
    claim = json.loads((tmp_path / "claims" / "companies.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert claim["claim_id"] == "clm-company-0001"
    assert claim["supporting_evidence"][0]["fact_ids"] == ["fact-001"]
    assert claim["supporting_evidence"][0]["direction"] == "supports"
    assert (tmp_path / "pending" / "archive-writes-src-001.json").exists()
    assert (tmp_path / "pending" / "arenas-src-001.jsonl").exists()


def test_apply_attach_appends_evidence_without_state_log_or_confidence_change(tmp_path):
    registry = ClaimRegistry(tmp_path)
    existing = registry.create_claim(
        claim_text="茅台品牌溢价来自白酒消费文化",
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="high",
        as_of="2023-12-31",
        evidence=build_evidence_entry(
            source_id="src-old",
            block_ids=["ib-old"],
            fact_ids=["fact-old"],
            direction="supports",
            now="2026-04-30T12:00:00+00:00",
        ),
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    candidate = _candidate()
    match = {
        "source_id": "src-001",
        "decisions_required": [
            _decision(
                candidate,
                decision="attach",
                decision_reason="同一命题的新证据",
                direction_on_claim="weakens",
                target_claim_id=existing["claim_id"],
            )
        ],
    }
    bundle_path = tmp_path / "bundle.json"
    match_path = tmp_path / "pending" / "match-src-001.json"
    match_path.parent.mkdir(exist_ok=True)
    _write_json(bundle_path, _bundle())
    _write_json(match_path, match)

    rc = ingest_apply.cmd_apply(
        Namespace(match=str(match_path), bundle=str(bundle_path), registry_base=str(tmp_path))
    )

    assert rc == 0
    updated = ClaimRegistry(tmp_path).find_by_id(existing["claim_id"])
    assert updated["confidence"] == "high"
    assert len(updated["state_log"]) == 1
    assert updated["supporting_evidence"][1]["direction"] == "refutes"


def test_apply_fails_before_writing_when_decision_missing(tmp_path):
    candidate = _candidate()
    match = {"source_id": "src-001", "decisions_required": [_decision(candidate, decision=None)]}
    bundle_path = tmp_path / "bundle.json"
    match_path = tmp_path / "pending" / "match-src-001.json"
    match_path.parent.mkdir()
    _write_json(bundle_path, _bundle())
    _write_json(match_path, match)

    rc = ingest_apply.cmd_apply(
        Namespace(match=str(match_path), bundle=str(bundle_path), registry_base=str(tmp_path))
    )

    assert rc == 1
    assert not (tmp_path / "claims").exists()


def test_apply_skip_only_writes_audit_event(tmp_path):
    candidate = _candidate()
    match = {
        "source_id": "src-001",
        "decisions_required": [_decision(candidate, decision="skip", decision_reason="证据太弱")],
    }
    bundle_path = tmp_path / "bundle.json"
    match_path = tmp_path / "pending" / "match-src-001.json"
    match_path.parent.mkdir()
    _write_json(bundle_path, _bundle())
    _write_json(match_path, match)

    rc = ingest_apply.cmd_apply(
        Namespace(match=str(match_path), bundle=str(bundle_path), registry_base=str(tmp_path))
    )

    assert rc == 0
    assert not (tmp_path / "claims" / "companies.jsonl").exists()
    event = json.loads((tmp_path / "audit" / "claim-events.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert event["event_type"] == "candidate_skipped"


def test_apply_split_retires_original_and_creates_new_claim(tmp_path):
    registry = ClaimRegistry(tmp_path)
    original = registry.create_claim(
        claim_text="原命题",
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2023-12-31",
        evidence=build_evidence_entry(
            source_id="src-old",
            block_ids=["ib-old"],
            fact_ids=["fact-old"],
            direction="supports",
            now="2026-04-30T12:00:00+00:00",
        ),
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    candidate = _candidate()
    match = {
        "source_id": "src-001",
        "decisions_required": [
            _decision(
                candidate,
                decision="split",
                decision_reason="原命题过宽，需要拆分",
                split_instructions={
                    "retire_target_claim_id": original["claim_id"],
                    "new_claims": [
                        {
                            "claim_text": "拆分后的命题",
                            "evidence_subset": {"block_ids": ["ib-001"], "fact_ids": ["fact-001"]},
                        }
                    ],
                },
            )
        ],
    }
    bundle_path = tmp_path / "bundle.json"
    match_path = tmp_path / "pending" / "match-src-001.json"
    match_path.parent.mkdir(exist_ok=True)
    _write_json(bundle_path, _bundle())
    _write_json(match_path, match)

    rc = ingest_apply.cmd_apply(
        Namespace(match=str(match_path), bundle=str(bundle_path), registry_base=str(tmp_path))
    )

    assert rc == 0
    reloaded = ClaimRegistry(tmp_path)
    retired = reloaded.find_by_id(original["claim_id"])
    assert retired["status"] == "retired"
    assert retired["supporting_evidence"][0]["source_id"] == "src-old"
    new_claim = reloaded.find_by_id("clm-company-0002")
    assert new_claim["claim_text"] == "拆分后的命题"
    assert new_claim["supporting_evidence"][0]["fact_ids"] == ["fact-001"]
    assert new_claim["state_log"][0]["trigger"] == "split_from"


def test_apply_accepts_multiple_decision_files_and_writes_applied_jsonl(tmp_path):

    candidate_001 = _candidate(candidate_id="cc-001", scope_type="company", scope_ref="SSE_600519")
    candidate_002 = _candidate(
        candidate_id="cc-002",
        claim_text="五粮液规模优势降低成本",
        scope_type="industry",
        scope_ref="liquor",
    )

    bundle = _bundle()
    bundle["claim_candidates"] = [candidate_001, candidate_002]

    auto_match = {
        "source_id": "src-001",
        "decisions_required": [_decision(candidate_001)],
    }
    pending_match = {
        "source_id": "src-001",
        "decisions_required": [_decision(candidate_002)],
    }

    bundle_path = tmp_path / "bundle.json"
    auto_path = tmp_path / "auto-match.json"
    pending_path = tmp_path / "pending-match.json"
    applied_path = tmp_path / "applied.jsonl"

    _write_json(bundle_path, bundle)
    _write_json(auto_path, auto_match)
    _write_json(pending_path, pending_match)

    result = subprocess.run(
        [
            sys.executable,
            str(_REPO_ROOT / "scripts" / "ingest_apply.py"),
            "--bundle", str(bundle_path),
            "--registry-base", str(tmp_path),
            "--decisions", str(auto_path),
            "--decisions", str(pending_path),
            "--applied-out", str(applied_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        env={**os.environ, "PYTHONPATH": str(_REPO_ROOT)},
    )

    assert result.returncode == 0, result.stderr

    assert applied_path.exists()
    rows = [json.loads(line) for line in applied_path.read_text(encoding="utf-8").splitlines()]
    candidate_ids = {row["candidate_id"] for row in rows}
    assert "cc-001" in candidate_ids
    assert "cc-002" in candidate_ids

    valid_scope_types = {"industry", "arena", "company", "cross_cutting"}
    for row in rows:
        assert "claim_id" in row
        assert row["scope_type"] in valid_scope_types
        assert "scope_ref" in row
        assert "action" in row


def test_archive_writes_include_suggested_target_from_dimension_mapping(tmp_path):
    candidate = _candidate()
    match = {"source_id": "src-001", "decisions_required": [_decision(candidate)]}
    bundle = _bundle()
    bundle["source_digest"]["scope_type"] = "company"
    bundle["source_digest"]["scope_ref"] = "SSE_600519"
    bundle_path = tmp_path / "bundle.json"
    match_path = tmp_path / "pending" / "match-src-001.json"
    match_path.parent.mkdir()
    _write_json(bundle_path, bundle)
    _write_json(match_path, match)

    rc = ingest_apply.cmd_apply(
        Namespace(match=str(match_path), bundle=str(bundle_path), registry_base=str(tmp_path))
    )

    assert rc == 0
    writes = json.loads((tmp_path / "pending" / "archive-writes-src-001.json").read_text(encoding="utf-8"))
    assert writes["writes"][0]["suggested_target"] == {
        "archive_layer": 8,
        "archive_path": "archive/layer8/company/SSE_600519/moat.jsonl",
        "action": "append",
    }

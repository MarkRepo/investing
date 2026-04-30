import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import ingest_apply


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

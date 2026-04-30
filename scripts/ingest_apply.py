from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.io.claim_registry import ClaimRegistry, build_evidence_entry

VALID_DECISIONS = {"attach", "new", "split", "skip"}
DIRECTION_ON_CLAIM_TO_EVIDENCE = {
    "strengthens": "supports",
    "weakens": "refutes",
    "neutral": "neutral",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fact_ids_for_blocks(bundle: dict[str, Any], block_ids: list[str]) -> list[str]:
    block_set = set(block_ids)
    fact_ids = []
    for fact in bundle.get("atomic_facts", []) or []:
        if fact.get("linked_block_id") in block_set and fact.get("fact_id"):
            fact_ids.append(fact["fact_id"])
    return fact_ids


def validate_match_decisions(match: dict[str, Any], registry: ClaimRegistry) -> list[str]:
    errors: list[str] = []
    for row in match.get("decisions_required", []) or []:
        candidate_id = row.get("candidate_id", "<unknown>")
        decision = row.get("decision")
        if decision not in VALID_DECISIONS:
            errors.append(f"{candidate_id}: invalid or missing decision")
            continue
        if not row.get("decision_reason"):
            errors.append(f"{candidate_id}: missing decision_reason")
        if decision == "new":
            if row.get("direction_on_claim") or row.get("split_instructions"):
                errors.append(f"{candidate_id}: new must not set direction_on_claim or split_instructions")
        elif decision == "attach":
            target_claim_id = row.get("target_claim_id")
            if not target_claim_id or registry.find_by_id(target_claim_id) is None:
                errors.append(f"{candidate_id}: attach target claim not found")
            if row.get("direction_on_claim") not in DIRECTION_ON_CLAIM_TO_EVIDENCE:
                errors.append(f"{candidate_id}: attach direction_on_claim invalid")
        elif decision == "split":
            instructions = row.get("split_instructions") or {}
            target_claim_id = instructions.get("retire_target_claim_id")
            target = registry.find_by_id(target_claim_id) if target_claim_id else None
            if target is None or target.get("status") != "active":
                errors.append(f"{candidate_id}: split retire target not active")
            if not instructions.get("new_claims"):
                errors.append(f"{candidate_id}: split new_claims empty")
    return errors


def _candidate_evidence(bundle: dict[str, Any], source_id: str, candidate: dict[str, Any], direction: str, now: str) -> dict[str, Any]:
    block_ids = candidate.get("supporting_block_ids", []) or []
    return build_evidence_entry(
        source_id=source_id,
        block_ids=block_ids,
        fact_ids=_fact_ids_for_blocks(bundle, block_ids),
        direction=direction,
        now=now,
    )


def _apply_new(registry: ClaimRegistry, bundle: dict[str, Any], source_id: str, row: dict[str, Any], now: str) -> dict[str, Any]:
    candidate = row["candidate_payload"]
    evidence = _candidate_evidence(bundle, source_id, candidate, candidate.get("direction_on_source", "neutral"), now)
    return registry.create_claim(
        claim_text=candidate["claim_text"],
        scope_type=candidate["scope_type"],
        scope_ref=candidate.get("scope_ref", ""),
        claim_type=candidate["claim_type"],
        dimension_hint=candidate.get("dimension_hint", ""),
        confidence=candidate["confidence"],
        as_of=candidate["as_of"],
        evidence=evidence,
        trigger="created",
        trigger_ref=f"match-{source_id}.json#{row['candidate_id']}",
        now=now,
    )


def _apply_attach(registry: ClaimRegistry, bundle: dict[str, Any], source_id: str, row: dict[str, Any], now: str) -> None:
    candidate = row["candidate_payload"]
    direction = DIRECTION_ON_CLAIM_TO_EVIDENCE[row["direction_on_claim"]]
    evidence = _candidate_evidence(bundle, source_id, candidate, direction, now)
    registry.append_evidence(row["target_claim_id"], evidence, now=now)


def derive_archive_writes(bundle: dict[str, Any], source_id: str) -> dict[str, Any]:
    writes = []
    blocks = {block.get("id"): block for block in bundle.get("insight_blocks", []) or []}
    for fact in bundle.get("atomic_facts", []) or []:
        linked_block = blocks.get(fact.get("linked_block_id"), {})
        writes.append(
            {
                "fact_id": fact.get("fact_id"),
                "fact_payload": fact,
                "linked_block": linked_block,
                "linked_claim_ids": [],
                "suggested_target": None,
                "alternative_targets": [],
                "decision": None,
                "decision_reason": None,
                "final_targets": None,
            }
        )
    return {"source_id": source_id, "writes": writes}


def derive_arena_candidates(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for idx, candidate in enumerate(bundle.get("arena_candidates", []) or []):
        row = dict(candidate)
        row.setdefault("candidate_id", f"arena-{idx + 1:03d}")
        row.setdefault("merge_suggestions", [])
        rows.append(row)
    for candidate in bundle.get("company_candidates", []) or []:
        if candidate.get("scope") == "arena":
            row = dict(candidate)
            row.setdefault("candidate_id", f"arena-{len(rows) + 1:03d}")
            row.setdefault("merge_suggestions", [])
            rows.append(row)
    return rows


def _write_pending_files(base: Path, source_id: str, bundle: dict[str, Any]) -> None:
    pending = base / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    (pending / f"archive-writes-{source_id}.json").write_text(
        json.dumps(derive_archive_writes(bundle, source_id), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    arena_lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in derive_arena_candidates(bundle)]
    (pending / f"arenas-{source_id}.jsonl").write_text("\n".join(arena_lines) + ("\n" if arena_lines else ""), encoding="utf-8")


def cmd_apply(args: argparse.Namespace) -> int:
    base = Path(args.registry_base)
    match = json.loads(Path(args.match).read_text(encoding="utf-8"))
    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    registry = ClaimRegistry(base)
    errors = validate_match_decisions(match, registry)
    if errors:
        for error in errors:
            print(f"✗ {error}")
        return 1

    source_id = match.get("source_id", "")
    now = _now()
    for row in match.get("decisions_required", []) or []:
        decision = row["decision"]
        if decision == "new":
            claim = _apply_new(registry, bundle, source_id, row, now)
            registry.append_audit_event({"event_type": "claim_created", "source_id": source_id, "candidate_id": row["candidate_id"], "claim_id": claim["claim_id"]})
        elif decision == "attach":
            _apply_attach(registry, bundle, source_id, row, now)
            registry.append_audit_event({"event_type": "evidence_attached", "source_id": source_id, "candidate_id": row["candidate_id"], "claim_id": row["target_claim_id"]})
        elif decision == "skip":
            registry.append_audit_event({"event_type": "candidate_skipped", "source_id": source_id, "candidate_id": row["candidate_id"]})
        elif decision == "split":
            raise NotImplementedError("split is implemented in Task D3")
    _write_pending_files(base, source_id, bundle)
    print(f"✓ applied match decisions from {args.match}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ingest_apply")
    parser.add_argument("--match", required=True)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--registry-base", default="data")
    args = parser.parse_args(argv)
    return cmd_apply(args)


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.io.archive_mapping import suggest_archive_target
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
    source_digest = bundle.get("source_digest") or {}
    for fact in bundle.get("atomic_facts", []) or []:
        linked_block = blocks.get(fact.get("linked_block_id"), {})
        suggested_target = suggest_archive_target(
            source_digest.get("scope_type", "company"),
            source_digest.get("scope_ref", ""),
            linked_block.get("dimension_hint", ""),
        )
        writes.append(
            {
                "fact_id": fact.get("fact_id"),
                "fact_payload": fact,
                "linked_block": linked_block,
                "linked_claim_ids": [],
                "suggested_target": suggested_target,
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


def _apply_split(registry: ClaimRegistry, source_id: str, row: dict[str, Any], now: str) -> list[dict[str, Any]]:
    candidate = row["candidate_payload"]
    instructions = row["split_instructions"]
    specs = []
    for new_claim in instructions["new_claims"]:
        evidence_subset = new_claim["evidence_subset"]
        evidence = build_evidence_entry(
            source_id=source_id,
            block_ids=evidence_subset.get("block_ids", []),
            fact_ids=evidence_subset.get("fact_ids", []),
            direction=candidate.get("direction_on_source", "neutral"),
            now=now,
        )
        specs.append(
            {
                "claim_text": new_claim["claim_text"],
                "scope_type": candidate["scope_type"],
                "scope_ref": candidate.get("scope_ref", ""),
                "claim_type": candidate["claim_type"],
                "dimension_hint": candidate.get("dimension_hint", ""),
                "confidence": candidate["confidence"],
                "as_of": candidate["as_of"],
                "evidence": evidence,
            }
        )
    return registry.split_claim(instructions["retire_target_claim_id"], new_claim_specs=specs, now=now)


def cmd_apply(args: argparse.Namespace) -> int:
    base = Path(args.registry_base)
    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    registry = ClaimRegistry(base)

    # Resolve all decision file paths (--decisions repeated, --match deprecated alias)
    match_val = getattr(args, "match", None)
    decisions_val = getattr(args, "decisions", None) or []
    match_list = [match_val] if (match_val and not isinstance(match_val, list)) else (match_val or [])
    decision_paths = [Path(p) for p in match_list + decisions_val]

    if not decision_paths:
        print("error: at least one --decisions file is required", flush=True)
        return 2

    # Load all match files and validate all before writing anything
    all_matches: list[dict] = []
    for dp in decision_paths:
        match_data = json.loads(dp.read_text(encoding="utf-8"))
        all_matches.append(match_data)
        errors = validate_match_decisions(match_data, registry)
        if errors:
            for error in errors:
                print(f"✗ {error}")
            return 1

    source_id = bundle.get("source_digest", {}).get("source_id", "")
    now = _now()
    applied_rows: list[dict] = []

    for match in all_matches:
        file_source_id = match.get("source_id", source_id)
        for row in match.get("decisions_required", []) or []:
            decision = row["decision"]
            candidate = row.get("candidate_payload", {})
            if decision == "new":
                claim = _apply_new(registry, bundle, file_source_id, row, now)
                registry.append_audit_event({"event_type": "claim_created", "source_id": file_source_id, "candidate_id": row["candidate_id"], "claim_id": claim["claim_id"]})
                applied_rows.append({
                    "source_id": bundle["source_digest"]["source_id"],
                    "candidate_id": row["candidate_id"],
                    "claim_id": claim["claim_id"],
                    "scope_type": candidate.get("scope_type", ""),
                    "scope_ref": candidate.get("scope_ref", ""),
                    "action": row["decision"],
                })
            elif decision == "attach":
                _apply_attach(registry, bundle, file_source_id, row, now)
                registry.append_audit_event({"event_type": "evidence_attached", "source_id": file_source_id, "candidate_id": row["candidate_id"], "claim_id": row["target_claim_id"]})
                applied_rows.append({
                    "source_id": bundle["source_digest"]["source_id"],
                    "candidate_id": row["candidate_id"],
                    "claim_id": row["target_claim_id"],
                    "scope_type": candidate.get("scope_type", ""),
                    "scope_ref": candidate.get("scope_ref", ""),
                    "action": row["decision"],
                })
            elif decision == "skip":
                registry.append_audit_event({"event_type": "candidate_skipped", "source_id": file_source_id, "candidate_id": row["candidate_id"]})
            elif decision == "split":
                new_claims = _apply_split(registry, file_source_id, row, now)
                registry.append_audit_event(
                    {
                        "event_type": "claim_split",
                        "source_id": file_source_id,
                        "candidate_id": row["candidate_id"],
                        "retired_claim_id": row["split_instructions"]["retire_target_claim_id"],
                        "new_claim_ids": [claim["claim_id"] for claim in new_claims],
                    }
                )
                for claim in new_claims:
                    applied_rows.append({
                        "source_id": bundle["source_digest"]["source_id"],
                        "candidate_id": row["candidate_id"],
                        "claim_id": claim["claim_id"],
                        "scope_type": candidate.get("scope_type", ""),
                        "scope_ref": candidate.get("scope_ref", ""),
                        "action": row["decision"],
                    })

    _write_pending_files(base, source_id, bundle)

    applied_out = getattr(args, "applied_out", None)
    if applied_out:
        out_path = Path(applied_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in applied_rows) + ("\n" if applied_rows else ""),
            encoding="utf-8",
        )

    decision_files_desc = ", ".join(str(p) for p in decision_paths)
    print(f"✓ applied match decisions from {decision_files_desc}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ingest_apply")
    parser.add_argument("--match", action="append", default=[], help="deprecated alias for --decisions")
    parser.add_argument("--decisions", action="append", default=[], help="decision file from ingest_match; may be repeated")
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--applied-out", help="write applied claim summary JSONL")
    args = parser.parse_args(argv)
    decision_paths = args.match + args.decisions
    if not decision_paths:
        parser.error("at least one --decisions file is required")
    return cmd_apply(args)


if __name__ == "__main__":
    raise SystemExit(main())

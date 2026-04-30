from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.io.claim_matching import MATCHING_ENGINE_VERSION, match_candidate
from app.io.claim_registry import ClaimRegistry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _candidate_id(candidate: dict[str, Any], idx: int) -> str:
    return candidate.get("candidate_id") or f"cc-{idx + 1:03d}"


def _claims_for_candidate(registry: ClaimRegistry, candidate: dict[str, Any]) -> list[dict[str, Any]]:
    scope_type = candidate.get("scope_type", "")
    scope_ref = candidate.get("scope_ref", "")
    if scope_type == "cross_cutting":
        return registry.all_claims_for_scope_type("cross_cutting")
    return registry.claims_for_scope(scope_type, scope_ref)


def build_match_file(bundle: dict[str, Any], *, bundle_ref: str, registry: ClaimRegistry, generated_at: str) -> dict[str, Any]:
    source_id = (bundle.get("source_digest") or {}).get("source_id", "")
    decisions = []
    with_matches = 0
    high_confidence_matches = 0
    candidates = bundle.get("claim_candidates", []) or []
    for idx, candidate in enumerate(candidates):
        candidate_payload = dict(candidate)
        candidate_payload.setdefault("candidate_id", _candidate_id(candidate, idx))
        matches = match_candidate(candidate_payload, _claims_for_candidate(registry, candidate_payload))
        if matches:
            with_matches += 1
        if any(match.get("high_confidence") for match in matches):
            high_confidence_matches += 1
        decisions.append(
            {
                "candidate_id": candidate_payload["candidate_id"],
                "candidate_payload": candidate_payload,
                "top_matches": matches,
                "decision": None,
                "decision_reason": None,
                "direction_on_claim": None,
                "target_claim_id": None,
                "split_instructions": None,
                "confidence": candidate_payload.get("confidence", "medium"),
            }
        )
    return {
        "source_id": source_id,
        "generated_at": generated_at,
        "bundle_ref": bundle_ref,
        "matching_engine_version": MATCHING_ENGINE_VERSION,
        "decisions_required": decisions,
        "summary_stats": {
            "total_candidates": len(candidates),
            "with_matches": with_matches,
            "no_matches_suggest_new": len(candidates) - with_matches,
            "high_confidence_matches": high_confidence_matches,
        },
    }


def _write_match(match_file: dict[str, Any], path: Path, rows: list[dict[str, Any]] | None = None) -> None:
    out = dict(match_file)
    if rows is not None:
        out = dict(match_file, decisions_required=rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_match(args: argparse.Namespace) -> int:
    bundle_path = Path(args.bundle)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    registry = ClaimRegistry(Path(args.registry_base))
    match_file = build_match_file(
        bundle,
        bundle_ref=str(bundle_path),
        registry=registry,
        generated_at=_now(),
    )
    rows = match_file["decisions_required"]
    out_arg = getattr(args, "out", None)
    auto_out_arg = getattr(args, "auto_out", None)
    pending_out_arg = getattr(args, "pending_out", None)
    if not any([out_arg, auto_out_arg, pending_out_arg]):
        import sys
        print("error: one of --out, --auto-out, or --pending-out is required", file=sys.stderr)
        return 2
    if out_arg:
        _write_match(match_file, Path(out_arg))
        print(f"✓ match file written to {out_arg}")
    if auto_out_arg:
        auto_rows = [r for r in rows if r.get("confidence") == "high"]
        _write_match(match_file, Path(auto_out_arg), auto_rows)
        print(f"✓ auto match file written to {auto_out_arg}")
    if pending_out_arg:
        pending_rows = [r for r in rows if r.get("confidence") != "high"]
        _write_match(match_file, Path(pending_out_arg), pending_rows)
        print(f"✓ pending match file written to {pending_out_arg}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ingest_match")
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--out", help="legacy single match output path")
    parser.add_argument("--auto-out", help="write high-confidence decisions here")
    parser.add_argument("--pending-out", help="write medium/low-confidence decisions here")
    args = parser.parse_args(argv)
    if not any([args.out, args.auto_out, args.pending_out]):
        parser.error("one of --out, --auto-out, or --pending-out is required")
    return cmd_match(args)


if __name__ == "__main__":
    raise SystemExit(main())

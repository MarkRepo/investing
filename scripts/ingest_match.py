from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.io.claim_matching import MATCHING_ENGINE_VERSION, match_candidate
from app.io.claim_registry import ClaimRegistry
from app.io.scope_utils import split_scope


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── v3 jaccard matching ───────────────────────────────────────────────────────


def tokenize_zh(s: str) -> set[str]:
    """Chinese chars tokenized individually; ASCII alphanumeric as words (len>=2)."""
    s = s.lower().strip()
    tokens: set[str] = set()
    for ch in s:
        if "一" <= ch <= "鿿":
            tokens.add(ch)
    for w in re.findall(r"[a-z0-9]+", s):
        if len(w) >= 2:
            tokens.add(w)
    return tokens


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def match_against_registry_v3(claim: dict[str, Any], registry: ClaimRegistry) -> list[dict[str, Any]]:
    """Return top-5 registry candidates by jaccard(semantic_key) within the same scope."""
    scope_type, scope_ref = split_scope(claim["scope"])
    if scope_type == "cross_cutting":
        existing = registry.all_claims_for_scope_type("cross_cutting")
    else:
        existing = registry.claims_for_scope(scope_type, scope_ref)
    new_tokens = tokenize_zh(claim.get("semantic_key", ""))
    scored = []
    for ec in existing:
        sc = jaccard(new_tokens, tokenize_zh(ec.get("semantic_key", "")))
        scored.append({
            "claim_id": ec["claim_id"],
            "text": ec.get("text", ""),
            "semantic_key": ec.get("semantic_key", ""),
            "direction": ec.get("direction", 0),
            "score": sc,
            "same_direction": ec.get("direction") == claim.get("direction"),
        })
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:5]


def decide_route_v3(claim: dict[str, Any], top_matches: list[dict[str, Any]]) -> tuple[str, str]:
    """Return (route, reason). route ∈ {auto_apply, pending_review}."""
    # risk always forced review
    if claim.get("type") == "risk":
        return "pending_review", "risk_class_forced_review"
    # negative direction (non-risk) always pending
    if claim.get("direction") == -1 and claim.get("type") != "risk":
        return "pending_review", "negative_direction_forced_review"
    # high jaccard + same direction + high confidence → auto_apply attach
    if top_matches and top_matches[0]["score"] >= 0.6 and top_matches[0]["same_direction"]:
        if claim.get("confidence") == "high":
            return "auto_apply", f"high_jaccard_attach_to_{top_matches[0]['claim_id']}"
        return "pending_review", f"medium_conf_attach_candidate_{top_matches[0]['claim_id']}"
    # no match + high confidence → auto_apply new
    if not top_matches or top_matches[0]["score"] < 0.3:
        if claim.get("confidence") == "high":
            return "auto_apply", "new_high_confidence"
        return "pending_review", "new_low_confidence"
    # ambiguous match
    return "pending_review", "ambiguous_match"


def cmd_match_v3(args: argparse.Namespace, bundle: dict[str, Any]) -> int:
    registry = ClaimRegistry(Path(args.registry_base))
    auto_rows: list[dict[str, Any]] = []
    pending_rows: list[dict[str, Any]] = []

    for claim in bundle.get("claims", []):
        top_matches = match_against_registry_v3(claim, registry)
        route, reason = decide_route_v3(claim, top_matches)
        row: dict[str, Any] = {
            "bundle_local_id": claim["id"],
            "claim_text": claim["text"],
            "scope": claim["scope"],
            "type": claim["type"],
            "direction": claim["direction"],
            "confidence": claim["confidence"],
            "semantic_key": claim.get("semantic_key", ""),
            "top_matches": top_matches,
            "decision": None,
            "decision_reason": None,
            "target_claim_id": None,
        }
        if route == "auto_apply":
            if top_matches and top_matches[0]["score"] >= 0.6 and top_matches[0]["same_direction"]:
                row["decision"] = "attach"
                row["target_claim_id"] = top_matches[0]["claim_id"]
                row["decision_reason"] = reason
            else:
                row["decision"] = "new"
                row["decision_reason"] = reason
            auto_rows.append(row)
        else:
            row["decision_reason"] = reason
            pending_rows.append(row)

    auto_out = getattr(args, "auto_out", None)
    pending_out = getattr(args, "pending_out", None)

    if auto_out:
        out_path = Path(auto_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(auto_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"✓ v3 auto ({len(auto_rows)}) → {auto_out}")
    if pending_out:
        out_path = Path(pending_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(pending_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"✓ v3 pending ({len(pending_rows)}) → {pending_out}")
    return 0


# ── v2 path (preserved for backward compat) ───────────────────────────────────


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
        decisions.append({
            "candidate_id": candidate_payload["candidate_id"],
            "candidate_payload": candidate_payload,
            "top_matches": matches,
            "decision": None,
            "decision_reason": None,
            "direction_on_claim": None,
            "target_claim_id": None,
            "split_instructions": None,
            "confidence": candidate_payload.get("confidence", "medium"),
        })
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

    if bundle.get("schema_version") == "v3":
        return cmd_match_v3(args, bundle)

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
        for r in auto_rows:
            if not r["top_matches"]:
                r["decision"] = "new"
                r["decision_reason"] = "auto-approved: high confidence, no existing claim matches"
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
    parser.add_argument("--out", help="legacy single match output path (v2)")
    parser.add_argument("--auto-out", help="write high-confidence / auto decisions here")
    parser.add_argument("--pending-out", help="write pending-review decisions here")
    args = parser.parse_args(argv)
    if not any([args.out, args.auto_out, args.pending_out]):
        parser.error("one of --out, --auto-out, or --pending-out is required")
    return cmd_match(args)


if __name__ == "__main__":
    raise SystemExit(main())

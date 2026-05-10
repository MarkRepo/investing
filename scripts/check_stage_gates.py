#!/usr/bin/env python3
"""Stage Gate Watcher — check newly applied claims against all uncrossed stage gates.

Usage:
    .venv/bin/python -m scripts.check_stage_gates \
        --applied /tmp/ingest-<sha8>-applied.jsonl \
        --context-out /tmp/sg-check-ctx.json

The script collects all uncrossed stage gates from existing bundles and the newly
applied claims, then writes a context JSON. The main agent dispatches a general-purpose
subagent to review each gate against the new claims and write alerts.

Alert format (data/stage_gate_alerts.jsonl):
    {"gate_id": "sg-001", "gate_title": "...", "triggered_by_claims": [...],
     "triggered_at": "ISO", "requires_human_review": true, "reviewed": false}

CRITICAL: Alerts NEVER auto-flip gate.crossed=true. Human approval required.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _load_bundle_registry(base: Path) -> list[dict]:
    path = base / "data" / "bundle_registry.jsonl"
    return _read_jsonl(path)


def collect_uncrossed_gates(base: Path) -> list[dict]:
    """Collect all uncrossed stage gates from all bundles listed in registry."""
    gates: list[dict] = []
    seen_gate_ids: set[str] = set()

    for entry in _load_bundle_registry(base):
        bundle_path_str = entry.get("bundle_path", "")
        if not bundle_path_str:
            continue
        bundle_path = base / bundle_path_str
        if not bundle_path.exists():
            continue

        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        source_id = (bundle.get("source_digest") or {}).get("source_id", "")

        for sg in bundle.get("stage_gates", []) or []:
            if sg.get("crossed") is not False:
                continue
            gate_id = sg.get("id", "")
            if gate_id in seen_gate_ids:
                continue
            seen_gate_ids.add(gate_id)
            gates.append({
                "gate_id": gate_id,
                "gate_type": sg.get("gate_type", ""),
                "title": sg.get("title", ""),
                "what_would_cross_it": sg.get("what_would_cross_it", []),
                "source_bundle": source_id,
                "source_bundle_path": bundle_path_str,
            })

    return gates


def build_context(base: Path, applied_path: Path | None, generated_at: str) -> dict:
    """Build context for subagent review."""
    gates = collect_uncrossed_gates(base)

    # Read applied claims
    applied_claims: list[dict] = []
    if applied_path:
        applied_claims = _read_jsonl(applied_path)

    # Read full claim texts from registry for applied claims
    from app.io.claim_registry import ClaimRegistry
    registry = ClaimRegistry(base)
    claim_details: list[dict] = []
    for ac in applied_claims:
        claim_id = ac.get("claim_id", "")
        if claim_id:
            claim = registry.find_by_id(claim_id)
            if claim:
                claim_details.append({
                    "claim_id": claim["claim_id"],
                    "claim_text": claim.get("claim_text", ""),
                    "scope_type": claim.get("scope_type", ""),
                    "scope_ref": claim.get("scope_ref", ""),
                    "claim_type": claim.get("claim_type", ""),
                    "dimension_hint": claim.get("dimension_hint", ""),
                    "confidence": claim.get("confidence", ""),
                })

    return {
        "generated_at": generated_at,
        "uncrossed_stage_gates": gates,
        "new_applied_claims": claim_details,
        "total_gates": len(gates),
        "total_new_claims": len(claim_details),
    }


def cmd_check(args: argparse.Namespace) -> int:
    base = Path(args.base)
    applied_path = Path(args.applied) if getattr(args, "applied", None) else None
    generated_at = _now()

    context = build_context(base, applied_path, generated_at)

    out_path = Path(args.context_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Stage gate check context written to {out_path}")
    print(f"  Uncrossed gates: {context['total_gates']}")
    print(f"  New claims to check: {context['total_new_claims']}")
    print(f"  Alerts file: data/stage_gate_alerts.jsonl")
    print()
    print("Dispatch a general-purpose subagent with this task:")
    print("  1. Read the context JSON")
    print("  2. For each uncrossed gate, review new claims against gate.what_would_cross_it")
    print("  3. If a gate is triggered, append an alert to data/stage_gate_alerts.jsonl")
    print("  4. Alert format: {gate_id, gate_title, triggered_by_claims: [claim_ids],")
    print("     triggered_at, requires_human_review: true, reviewed: false}")
    print("  5. NEVER auto-flip gate.crossed=true — all alerts require human review")

    if context["total_gates"] == 0:
        print()
        print("No uncrossed gates found — nothing to check.")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_stage_gates")
    parser.add_argument("--base", default=".", help="Project root")
    parser.add_argument("--applied", help="Path to applied.jsonl from ingest_apply")
    parser.add_argument("--context-out", required=True, help="Write check context JSON here")
    args = parser.parse_args(argv)
    return cmd_check(args)


if __name__ == "__main__":
    raise SystemExit(main())

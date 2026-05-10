#!/usr/bin/env python3
"""Claim decay checker — scan all claims and report fresh/aged/stale/invalidated status.

Usage:
    .venv/bin/python -m scripts.claim_decay_check              # all claims, report only
    .venv/bin/python -m scripts.claim_decay_check --audit      # write audit events
    .venv/bin/python -m scripts.claim_decay_check --scope company --ref SSE_688122

Default half-life by claim_type (months):
    thesis: 24, judgment: 12, risk: 6, gate_assessment: 12, scenario: 18

Archetype multipliers: technology_driven=0.75, consumer_driven=1.25, cyclical=1.00,
    financial=1.00, real_asset=1.50, other=1.00

Status rules:
    age < half_life               → fresh
    age < half_life * 2           → aged
    age >= half_life * 2          → stale
    decay_rule.invalidated_by set → invalidated
"""

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from app.io.claim_registry import ClaimRegistry

# --- Constants ---

DEFAULT_HALF_LIFE: dict[str, int] = {
    "thesis": 24,
    "judgment": 12,
    "risk": 6,
    "gate_assessment": 12,
    "scenario": 18,
}

ARCHETYPE_MULTIPLIER: dict[str, float] = {
    "technology_driven": 0.75,
    "consumer_driven": 1.25,
    "cyclical": 1.00,
    "financial": 1.00,
    "real_asset": 1.50,
    "other": 1.00,
}

FRESH = "fresh"
AGED = "aged"
STALE = "stale"
INVALIDATED = "invalidated"


# --- Public API (also imported by narrative_proposals) ---

def compute_decay_status(
    claim: dict,
    *,
    as_of: date | None = None,
    archetype: str | None = None,
) -> str:
    """Compute decay status for a single claim. Pure function, no side effects.

    Returns one of: fresh, aged, stale, invalidated.
    """
    # Check invalidated_by first
    decay_rule = claim.get("decay_rule")
    if isinstance(decay_rule, dict) and decay_rule.get("invalidated_by"):
        return INVALIDATED

    if as_of is None:
        as_of_str = claim.get("as_of", "")
        if not as_of_str:
            return FRESH  # No date → can't age
        as_of = date.fromisoformat(as_of_str[:10])

    claim_type = claim.get("claim_type", "judgment")
    half_life_months = DEFAULT_HALF_LIFE.get(claim_type, 12)

    if archetype and archetype in ARCHETYPE_MULTIPLIER:
        half_life_months = int(half_life_months * ARCHETYPE_MULTIPLIER[archetype])

    today = date.today()
    age_months = ((today.year - as_of.year) * 12 + (today.month - as_of.month))

    if age_months < half_life_months:
        return FRESH
    if age_months < half_life_months * 2:
        return AGED
    return STALE


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- CLI ---

def cmd_check(args: argparse.Namespace) -> int:
    base = Path(args.base)
    registry = ClaimRegistry(base)
    write_audit = args.audit

    # Filter by scope if requested
    if args.scope and args.ref:
        claims = registry.claims_for_scope(args.scope, args.ref)
        scope_label = f"{args.scope}/{args.ref}"
    elif args.scope:
        claims = registry.all_claims_for_scope_type(args.scope)
        scope_label = args.scope
    else:
        claims = registry.list_claims()
        scope_label = "all"

    now = _now()
    statuses: dict[str, list[dict]] = {
        FRESH: [], AGED: [], STALE: [], INVALIDATED: [],
    }

    for claim in claims:
        status = compute_decay_status(claim)
        statuses[status].append({
            "claim_id": claim["claim_id"],
            "claim_text": claim.get("claim_text", "")[:80],
            "as_of": claim.get("as_of", ""),
            "claim_type": claim.get("claim_type", ""),
            "scope_ref": claim.get("scope_ref", ""),
        })

        if write_audit and status in (AGED, STALE, INVALIDATED):
            registry.append_audit_event({
                "event": "decay_status_change",
                "claim_id": claim["claim_id"],
                "new_decay_status": status,
                "checked_at": now,
                "previous_decay_status": claim.get("decay_status", FRESH),
            })

    total = len(claims)
    fresh_n = len(statuses[FRESH])
    aged_n = len(statuses[AGED])
    stale_n = len(statuses[STALE])
    invalidated_n = len(statuses[INVALIDATED])

    print(f"# Claim Decay Check — {scope_label}")
    print(f"  Total: {total}")
    print(f"  Fresh:   {fresh_n} ({fresh_n * 100 // max(1, total)}%)")
    print(f"  Aged:    {aged_n} ({aged_n * 100 // max(1, total)}%)")
    print(f"  Stale:   {stale_n} ({stale_n * 100 // max(1, total)}%)")
    print(f"  Invalid: {invalidated_n}")
    print()

    if stale_n > 0:
        print("## Stale claims (will be excluded from narrative unless re-evidenced):")
        for s in statuses[STALE]:
            print(f"  - [{s['claim_id']}] {s['claim_text']}")
        print()

    if invalidated_n > 0:
        print("## Invalidated claims (manually marked, removed from narrative):")
        for i in statuses[INVALIDATED]:
            print(f"  - [{i['claim_id']}] {i['claim_text']}")
        print()

    if write_audit:
        print(f"Audit events written to data/audit/claim-events.jsonl")

    # If --json flag, output machine-readable JSON
    if args.json_out:
        out = {
            "checked_at": now,
            "scope": scope_label,
            "total": total,
            "fresh": fresh_n, "aged": aged_n, "stale": stale_n, "invalidated": invalidated_n,
            "stale_claims": statuses[STALE],
            "invalidated_claims": statuses[INVALIDATED],
        }
        path = Path(args.json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"JSON report written to {path}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="claim_decay_check")
    parser.add_argument("--base", default=".", help="Project root")
    parser.add_argument("--scope", choices=["industry", "arena", "company", "cross_cutting"],
                        help="Filter by scope type")
    parser.add_argument("--ref", help="Filter by scope ref (e.g. SSE_688122)")
    parser.add_argument("--audit", action="store_true", help="Write decay events to audit log")
    parser.add_argument("--json-out", help="Write machine-readable JSON report")
    args = parser.parse_args(argv)
    return cmd_check(args)


if __name__ == "__main__":
    raise SystemExit(main())

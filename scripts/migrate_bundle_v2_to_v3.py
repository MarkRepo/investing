"""Migrate v2 bundles to v3 format.

Usage:
    .venv/bin/python -m scripts.migrate_bundle_v2_to_v3 \\
        --bundles "industries/*/bundles/*.json" \\
        --output-suffix "-v3"
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path
from typing import Any

# ── Mapping tables ─────────────────────────────────────────────────────────────

_SOURCE_TYPE_MAP: dict[str | None, str] = {
    "industry_report": "industry_report",
    "annual": "annual",
    "quarterly": "quarterly",
    "sell_side": "sell_side",
    "company_report": "company_report",
    None: "industry_report",
}

_CLAIM_TYPE_MAP: dict[str | None, str] = {
    "thesis": "thesis",
    "judgment": "judgment",
    "risk": "risk",
    "scenario": "judgment",
    "gate_assessment": "judgment",
    None: "judgment",
}

_CONFIDENCE_MAP: dict[str | None, str] = {
    "high": "high",
    "medium_high": "medium",
    "medium": "medium",
    "medium_low": "medium",
    "low": "low",
    None: "medium",
}


# ── Helper functions ───────────────────────────────────────────────────────────


def _extract_institution(source_id: str) -> str:
    """Extract institution from source_id.

    Format is typically: 行研-{institution}-{date}-{sha8}
    or {institution}-{...}
    """
    parts = source_id.split("-")
    if len(parts) >= 2 and parts[0] in ("行研", "年报", "季报"):
        return parts[1]
    return ""


def _map_direction(claim: dict[str, Any]) -> int:
    """Map v2 direction_on_source + claim_type to v3 direction int."""
    claim_type = claim.get("claim_type")
    if claim_type == "risk":
        return -1
    direction_on_source = claim.get("direction_on_source", "")
    if direction_on_source == "supports":
        return 1
    if direction_on_source == "refutes":
        return -1
    return 0


def _build_evidence(
    claim: dict[str, Any],
    ib_to_facts: dict[str, list[dict[str, Any]]],
    block_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build evidence list from supporting_block_ids."""
    evidence: list[dict[str, Any]] = []

    for bid in claim.get("supporting_block_ids", []):
        for fact in ib_to_facts.get(bid, []):
            evidence.append(
                {
                    "quote": fact.get("evidence_quote", ""),
                    "page": fact.get("source_page"),
                    "why": fact.get("fact_text", "")[:30],
                }
            )
            if len(evidence) >= 3:
                break
        if len(evidence) >= 3:
            break

    # Fallback: no atomic_facts — use block summary
    if not evidence and claim.get("supporting_block_ids"):
        for bid in claim["supporting_block_ids"][:1]:
            block = block_map.get(bid, {})
            if block.get("summary"):
                evidence.append(
                    {
                        "quote": block["summary"][:100],
                        "page": None,
                        "why": "from block summary",
                    }
                )

    return evidence


def _build_touches(v2: dict[str, Any]) -> dict[str, list[str]]:
    """Collect scope refs from claim_candidates."""
    industries: set[str] = set()
    companies: set[str] = set()
    arenas: set[str] = set()

    for cc in v2.get("claim_candidates", []):
        st = cc.get("scope_type", "")
        sr = cc.get("scope_ref", "")
        if not sr:
            continue
        if st == "industry":
            industries.add(sr)
        elif st == "company":
            companies.add(sr)
        elif st == "arena":
            arenas.add(sr)

    return {
        "industries": sorted(industries),
        "companies": sorted(companies),
        "arenas": sorted(arenas),
        "brands": [],
    }


def _build_scope_str(claim: dict[str, Any]) -> str:
    """Build v3 scope string from v2 scope_type / scope_ref."""
    scope_type = claim.get("scope_type", "")
    scope_ref = claim.get("scope_ref", "")

    if scope_type == "cross_cutting" or not scope_type:
        return "cross_cutting"
    if scope_type in ("industry", "arena", "company"):
        if scope_ref:
            return f"{scope_type}/{scope_ref}"
        return "cross_cutting"
    # Unknown scope_type — fall back
    return "cross_cutting"


def _build_threads(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group claims by scope into threads so C8 passes."""
    # Group claim ids by scope prefix (industry, arena, company, cross_cutting)
    buckets: dict[str, list[str]] = {}
    for c in claims:
        scope = c.get("scope", "cross_cutting")
        if "/" in scope:
            key = scope  # e.g. "industry/cn-pet-industry"
        else:
            key = "cross_cutting"
        buckets.setdefault(key, []).append(c["id"])

    threads = []
    for scope_key, cids in buckets.items():
        if "/" in scope_key:
            _, ref = scope_key.split("/", 1)
            title = ref
        else:
            title = "cross_cutting"
        threads.append({"title": title, "claim_ids": cids})

    # Ensure at least one thread exists (edge case: empty claims list)
    if not threads and claims:
        threads.append({"title": "main", "claim_ids": [c["id"] for c in claims]})

    return threads


# ── Core conversion ────────────────────────────────────────────────────────────


def convert_v2_to_v3(v2: dict[str, Any]) -> dict[str, Any]:
    """Convert a v2 bundle dict to v3 format."""
    sd = v2.get("source_digest", {})

    source_id = sd.get("source_id", "")
    source_title = sd.get("source_title", "")
    source_date = sd.get("source_date", "1970-01-01") or "1970-01-01"
    source_type_raw = sd.get("source_type")
    source_type = _SOURCE_TYPE_MAP.get(source_type_raw, "industry_report")

    institution = _extract_institution(source_id)

    # Build lookup structures
    atomic_facts: list[dict[str, Any]] = v2.get("atomic_facts", [])
    ib_to_facts: dict[str, list[dict[str, Any]]] = {}
    for fact in atomic_facts:
        bid = fact.get("linked_block_id", "")
        if bid:
            ib_to_facts.setdefault(bid, []).append(fact)

    insight_blocks: list[dict[str, Any]] = v2.get("insight_blocks", [])
    block_map: dict[str, dict[str, Any]] = {b["id"]: b for b in insight_blocks if "id" in b}

    # Build touches
    touches = _build_touches(v2)

    # Determine primary_scope
    if touches["industries"]:
        primary_scope = {"kind": "industry", "ref": touches["industries"][0]}
    elif touches["companies"]:
        primary_scope = {"kind": "company", "ref": touches["companies"][0]}
    else:
        primary_scope = {"kind": "industry", "ref": ""}

    # Convert claims
    claims: list[dict[str, Any]] = []
    for idx, cc in enumerate(v2.get("claim_candidates", []), start=1):
        cid = f"c{idx}"
        claim_type_raw = cc.get("claim_type")
        claim_type = _CLAIM_TYPE_MAP.get(claim_type_raw, "judgment")
        direction = _map_direction(cc)
        confidence_raw = cc.get("confidence")
        confidence = _CONFIDENCE_MAP.get(confidence_raw, "medium")
        scope = _build_scope_str(cc)
        semantic_nucleus = cc.get("semantic_nucleus", "") or ""
        semantic_key = semantic_nucleus[:15] if semantic_nucleus else ""
        # Fallback semantic_key from claim_text if empty
        if not semantic_key:
            claim_text = cc.get("claim_text", "")
            semantic_key = claim_text[:15] if claim_text else f"claim_{idx}"
        as_of = cc.get("as_of") or source_date
        evidence = _build_evidence(cc, ib_to_facts, block_map)

        claims.append(
            {
                "id": cid,
                "text": cc.get("claim_text", ""),
                "type": claim_type,
                "scope": scope,
                "direction": direction,
                "confidence": confidence,
                "evidence": evidence,
                "relations": [],
                "semantic_key": semantic_key,
                "as_of": as_of,
            }
        )

    # Build threads from claims (required by C8)
    threads = _build_threads(claims)

    # Build summary
    synthesis = v2.get("synthesis", {})
    cannot_conclude_raw = synthesis.get("cannot_conclude", [])
    if isinstance(cannot_conclude_raw, list):
        cannot_conclude = [str(x) for x in cannot_conclude_raw]
    elif isinstance(cannot_conclude_raw, str):
        cannot_conclude = [cannot_conclude_raw] if cannot_conclude_raw else []
    else:
        cannot_conclude = []

    summary = {
        "one_liner": synthesis.get("one_sentence", "") or "",
        "threads": threads,
        "cannot_conclude": cannot_conclude,
    }

    # Build notes
    coverage = sd.get("coverage_review", {})
    skipped_sections = coverage.get("skipped_sections", 0)
    skipped_list = [f"skipped_sections_count={skipped_sections}"] if skipped_sections else []

    notes = {
        "skipped_sections": skipped_list,
        "weak_evidence": [],
    }

    return {
        "schema_version": "v3",
        "meta": {
            "source_id": source_id,
            "source_title": source_title,
            "institution": institution,
            "published_at": source_date,
            "source_type": source_type,
            "primary_scope": primary_scope,
            "touches": touches,
        },
        "claims": claims,
        "summary": summary,
        "notes": notes,
    }


# ── CLI ────────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Migrate v2 bundles to v3 format",
    )
    parser.add_argument(
        "--bundles",
        default="industries/*/bundles/*.json",
        help="Glob pattern for bundle files (default: industries/*/bundles/*.json)",
    )
    parser.add_argument(
        "--output-suffix",
        default="-v3",
        metavar="SUFFIX",
        help="Suffix for output files (default: -v3). Use = to pass values starting with '-', e.g. --output-suffix=-v3",
    )
    args = parser.parse_args(argv)

    suffix = args.output_suffix  # e.g. "-v3"
    pattern = args.bundles

    # Expand glob relative to cwd
    paths = sorted(glob.glob(pattern, recursive=True))

    converted = 0
    skipped = 0

    for path_str in paths:
        p = Path(path_str)

        # Skip files that already have the output suffix
        if p.stem.endswith(suffix):
            skipped += 1
            continue

        # Skip files whose stem ends with any variant of v3 suffix
        if suffix.lstrip("-") in p.stem:
            skipped += 1
            continue

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"skip (read error): {p} — {exc}", file=sys.stderr)
            skipped += 1
            continue

        # Skip files that are already v3
        if data.get("schema_version") == "v3":
            skipped += 1
            continue

        # Skip files that don't look like v2 bundles
        if "source_digest" not in data and "claim_candidates" not in data:
            skipped += 1
            continue

        # Determine output path
        out_path = p.parent / (p.stem + suffix + p.suffix)

        # Convert
        try:
            v3 = convert_v2_to_v3(data)
        except Exception as exc:  # noqa: BLE001
            print(f"skip (conversion error): {p} — {exc}", file=sys.stderr)
            skipped += 1
            continue

        out_path.write_text(
            json.dumps(v3, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        n_claims = len(v3.get("claims", []))
        print(f"converted: {p} → {n_claims} claims")
        converted += 1

    if converted == 0 and skipped == 0:
        print("no bundle files matched the glob pattern")

    return 0


if __name__ == "__main__":
    sys.exit(main())

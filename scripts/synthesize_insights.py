#!/usr/bin/env python3
"""Synthesize INSIGHTS.md from a v3 bundle (bundle-only, no registry dependency).

Insights capture the narrative logic of a single report — the argument chain as
expressed in that bundle. Registry is intentionally NOT used here to avoid
cross-report contamination of the per-report narrative.

Usage:
    # Prepare context JSON and show target path:
    .venv/bin/python -m scripts.synthesize_insights \\
        --bundle <source_dir>/bundles/<sha8>.json \\
        --context-out /tmp/<sha8>-synthesis-ctx.json

    # Override output path:
    .venv/bin/python -m scripts.synthesize_insights \\
        --bundle <path> --out industries/<slug>/insights/<sha8>.md

After running --context-out, dispatch a general-purpose subagent with
docs/prompts/synthesize-insights.md + the context JSON to produce INSIGHTS.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bundle_sha8(path: Path) -> str:
    return path.stem


def build_context(bundle: dict, generated_at: str) -> dict:
    """Build synthesis context purely from a v3 bundle — no registry access."""
    meta = bundle.get("meta", {})
    claims_list = bundle.get("claims", [])

    # bundle-local id → claim for relation resolution
    claim_map: dict[str, dict] = {c["id"]: c for c in claims_list}

    def _resolve(local_id: str) -> str:
        c = claim_map.get(local_id)
        return c.get("text", local_id) if c else local_id

    claim_items = []
    for c in claims_list:
        evidence = c.get("evidence", [])
        first_ev = evidence[0] if evidence else {}
        relations_resolved = [
            {
                "kind": rel.get("kind", ""),
                "to_id": rel.get("to", ""),
                "to_text": _resolve(rel.get("to", "")),
            }
            for rel in c.get("relations", [])
        ]
        claim_items.append({
            "claim_id": c["id"],
            "text": c.get("text", ""),
            "type": c.get("type", ""),
            "direction": c.get("direction"),
            "confidence": c.get("confidence", ""),
            "semantic_key": c.get("semantic_key", ""),
            "first_quote": first_ev.get("quote", ""),
            "first_page": first_ev.get("page", ""),
            "relations_resolved": relations_resolved,
        })

    summary = bundle.get("summary", {})
    threads = []
    for thread in summary.get("threads", []):
        thread_claims = []
        for local_id in thread.get("claim_ids", []):
            c = claim_map.get(local_id)
            if c:
                thread_claims.append({
                    "claim_id": local_id,
                    "text": c.get("text", ""),
                    "type": c.get("type", ""),
                    "direction": c.get("direction"),
                    "confidence": c.get("confidence", ""),
                })
        if thread_claims:
            threads.append({"title": thread.get("title", ""), "claims": thread_claims})

    notes = bundle.get("notes", {})

    return {
        "generated_at": generated_at,
        "source_id": meta.get("source_id", ""),
        "source_title": meta.get("source_title", ""),
        "source_type": meta.get("source_type", ""),
        "institution": meta.get("institution", ""),
        "as_of": meta.get("published_at", ""),
        "one_liner": summary.get("one_liner", ""),
        "threads": threads,
        "cannot_conclude": summary.get("cannot_conclude", []),
        "weak_evidence": notes.get("weak_evidence", []),
        "claims": claim_items,
    }


def _derive_out_path(bundle: dict, sha8: str, out_base: str) -> Path:
    """Derive default output path from bundle meta.primary_scope."""
    meta = bundle.get("meta", {})
    primary_scope = meta.get("primary_scope", "")
    base = Path(out_base)
    dir_map = {"industry": "industries", "arena": "arenas", "company": "companies"}
    if isinstance(primary_scope, dict):
        scope_type = primary_scope.get("kind", "")
        scope_ref = primary_scope.get("ref", "")
    elif isinstance(primary_scope, str) and "/" in primary_scope:
        scope_type, scope_ref = primary_scope.split("/", 1)
    else:
        return Path(f"/tmp/insights-{sha8}.md")
    if scope_type in dir_map and scope_ref:
        return base / dir_map[scope_type] / scope_ref / "insights" / f"{sha8}.md"
    return Path(f"/tmp/insights-{sha8}.md")


def cmd_synthesize(args: argparse.Namespace) -> int:
    bundle_path = Path(args.bundle)
    if not bundle_path.exists():
        print(f"Error: bundle not found: {bundle_path}", file=sys.stderr)
        return 1

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    sha8 = _bundle_sha8(bundle_path)
    generated_at = _now()

    context = build_context(bundle, generated_at)
    out_path = Path(args.out) if args.out else _derive_out_path(bundle, sha8, args.out_base or ".")

    if args.context_out:
        ctx_path = Path(args.context_out)
        ctx_path.parent.mkdir(parents=True, exist_ok=True)
        ctx_path.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Synthesis context written to {ctx_path}")
        print(f"Dispatch subagent with docs/prompts/synthesize-insights.md + this context")
        print(f"Target output path: {out_path}")
        return 0

    ctx_path = out_path.parent / f"{sha8}-synthesis-ctx.json"
    ctx_path.parent.mkdir(parents=True, exist_ok=True)
    ctx_path.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Synthesis context: {ctx_path}")
    print(f"Target output:     {out_path}")
    print(f"Claims:            {len(context['claims'])}  Threads: {len(context['threads'])}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="synthesize_insights")
    parser.add_argument("--bundle", required=True, help="Path to v3 bundle JSON")
    parser.add_argument("--out-base", default=".", help="Base path for output")
    parser.add_argument("--out", help="Override output path for INSIGHTS.md")
    parser.add_argument("--context-out", help="Write synthesis context JSON here and exit")
    args = parser.parse_args(argv)
    return cmd_synthesize(args)


if __name__ == "__main__":
    raise SystemExit(main())

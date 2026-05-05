"""Ingest QA for bundle v3.

Subcommands:
  review-bundle   validate a v3 bundle (C1-C9 checks)
  evaluation init generate evaluation skeleton from a v3 or v2 bundle
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.io.scope_utils import is_valid_scope

# ── QAItem helpers ────────────────────────────────────────────────────────────

_VALID_TYPES = {"thesis", "judgment", "risk", "catalyst"}
_VALID_CONF = {"high", "medium", "low"}
_VALID_SOURCE_TYPES = {"industry_report", "company_report", "annual", "quarterly", "sell_side", "transcript"}
_VALID_REL_KINDS = {"because_of", "leads_to", "tension_with", "refines"}


def _err(code: str, detail: str = "") -> dict[str, Any]:
    return {"level": "error", "code": code, "detail": detail}


def _warn(code: str, detail: str = "") -> dict[str, Any]:
    return {"level": "warning", "code": code, "detail": detail}


# ── C1-C9 v3 bundle checks ────────────────────────────────────────────────────


def check_v3_bundle(bundle: dict[str, Any], mineru_md_text: str | None = None) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    # C1: schema_version
    if bundle.get("schema_version") != "v3":
        issues.append(_err("schema_version_mismatch", f"expected 'v3', got {bundle.get('schema_version')!r}"))
        return issues  # remaining checks are meaningless

    # C2: required top-level keys
    for k in ("meta", "claims", "summary", "notes"):
        if k not in bundle:
            issues.append(_err(f"missing_top_key:{k}"))

    if "meta" not in bundle or "claims" not in bundle:
        return issues

    # C3: meta field completeness
    meta = bundle.get("meta", {})
    for k in ("source_id", "institution", "published_at", "source_type", "primary_scope", "touches"):
        if not meta.get(k):
            issues.append(_err(f"meta_missing:{k}"))
    if meta.get("source_type") not in _VALID_SOURCE_TYPES:
        issues.append(_err("invalid_source_type", str(meta.get("source_type"))))

    # C4: claims count vs. estimated page count
    claims = bundle.get("claims", [])
    if not claims:
        issues.append(_err("no_claims"))
    if mineru_md_text:
        pages = max(1, len(mineru_md_text) // 1500)
        ratio = len(claims) / pages
        if ratio < 0.25:
            issues.append(_warn("under_extraction", f"{len(claims)} claims for ~{pages} pages (ratio={ratio:.2f})"))
        elif ratio > 2.0:
            issues.append(_warn("over_extraction", f"{len(claims)} claims for ~{pages} pages (ratio={ratio:.2f})"))

    # C5: per-claim field validity
    all_ids: set[str] = set()
    for c in claims:
        cid = c.get("id", "")
        if not cid or cid in all_ids:
            issues.append(_err(f"claim_id_invalid_or_dup:{cid!r}"))
        all_ids.add(cid)
        if c.get("type") not in _VALID_TYPES:
            issues.append(_err(f"{cid}.type_invalid", str(c.get("type"))))
        if c.get("direction") not in (-1, 0, 1):
            issues.append(_err(f"{cid}.direction_invalid", str(c.get("direction"))))
        if c.get("confidence") not in _VALID_CONF:
            issues.append(_err(f"{cid}.confidence_invalid", str(c.get("confidence"))))
        scope = c.get("scope", "")
        if not is_valid_scope(scope):
            issues.append(_err(f"{cid}.scope_invalid", scope))
        if not c.get("evidence"):
            issues.append(_err(f"{cid}.no_evidence"))
        for i, e in enumerate(c.get("evidence", [])):
            if not e.get("quote"):
                issues.append(_err(f"{cid}.evidence[{i}].no_quote"))
            if not e.get("why"):
                issues.append(_err(f"{cid}.evidence[{i}].no_why"))
        sk = c.get("semantic_key", "")
        if not sk or len(sk) > 20:
            issues.append(_err(f"{cid}.semantic_key_invalid", repr(sk)))
        if c.get("type") == "risk" and c.get("direction") == 1:
            issues.append(_warn(f"{cid}.risk_with_positive_direction"))

    # C6: relations referential integrity
    for c in claims:
        for i, r in enumerate(c.get("relations", [])):
            if r.get("to") not in all_ids:
                issues.append(_err(f"{c['id']}.relations[{i}].broken_ref", str(r.get("to"))))
            if r.get("kind") not in _VALID_REL_KINDS:
                issues.append(_err(f"{c['id']}.relations[{i}].invalid_kind", str(r.get("kind"))))

    # C7: isolated claim ratio
    referenced = {r["to"] for c in claims for r in c.get("relations", []) if r.get("to") in all_ids}
    isolated = [c["id"] for c in claims if not c.get("relations") and c["id"] not in referenced]
    if claims and len(isolated) / len(claims) > 0.20:
        issues.append(_warn("excessive_isolated_claims", f"{len(isolated)}/{len(claims)} isolated"))

    # C8: summary fields
    sm = bundle.get("summary", {})
    if not sm.get("one_liner"):
        issues.append(_err("summary_missing_one_liner"))
    if not sm.get("threads"):
        issues.append(_err("summary_missing_threads"))
    for t in sm.get("threads", []):
        for cid in t.get("claim_ids", []):
            if cid not in all_ids:
                issues.append(_err(f"thread_unknown_claim:{cid}"))

    # C9: scope.ref consistency with meta.touches (warning only)
    touches = meta.get("touches", {})
    touch_inds = set(touches.get("industries", []))
    touch_cos = set(touches.get("companies", []))
    touch_arenas = set(touches.get("arenas", []))
    for c in claims:
        s = c.get("scope", "")
        if s.startswith("industry/"):
            ref = s[len("industry/"):]
            if ref not in touch_inds:
                issues.append(_warn(f"{c['id']}.scope_not_in_touches", ref))
        elif s.startswith("company/"):
            ref = s[len("company/"):]
            if ref not in touch_cos:
                issues.append(_warn(f"{c['id']}.scope_not_in_touches", ref))
        elif s.startswith("arena/"):
            ref = s[len("arena/"):]
            if ref not in touch_arenas:
                issues.append(_warn(f"{c['id']}.scope_not_in_touches", ref))

    return issues


# ── CLI commands ──────────────────────────────────────────────────────────────


def cmd_review_bundle(args: argparse.Namespace) -> int:
    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))

    if bundle.get("schema_version") != "v3":
        print(f"✗ schema_version_mismatch: expected 'v3', got {bundle.get('schema_version')!r}")
        return 1

    mineru_md: str | None = None
    if getattr(args, "mineru_md", None):
        mineru_md = Path(args.mineru_md).read_text(encoding="utf-8")

    issues = check_v3_bundle(bundle, mineru_md)
    errors = [i for i in issues if i["level"] == "error"]
    warnings = [i for i in issues if i["level"] == "warning"]

    for i in issues:
        prefix = "✗" if i["level"] == "error" else "⚠"
        detail = f" — {i['detail']}" if i.get("detail") else ""
        print(f"{prefix} {i['code']}{detail}")

    if not issues:
        print("✓ review-bundle passed (0 issues)")
    elif not errors:
        print(f"✓ review-bundle passed ({len(warnings)} warnings)")
    else:
        print(f"✗ review-bundle failed ({len(errors)} errors, {len(warnings)} warnings)")

    return 1 if errors else 0


def _matching_metrics_v2(match: dict[str, Any] | None) -> dict[str, Any]:
    """Build matching metrics from a v2 match file (decisions_required format)."""
    if not match:
        return {}
    rows = match.get("decisions_required", []) or []
    decisions: dict[str, int] = {"attach": 0, "new": 0, "split": 0, "skip": 0}
    for row in rows:
        d = row.get("decision")
        if d in decisions:
            decisions[d] += 1
    return {"total_candidates": len(rows), "decisions": decisions}


def cmd_evaluation_init(args: argparse.Namespace) -> int:
    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    is_v3 = bundle.get("schema_version") == "v3"
    match = json.loads(Path(args.match).read_text(encoding="utf-8")) if getattr(args, "match", None) else None

    if is_v3:
        issues = check_v3_bundle(bundle)
        source_id = bundle.get("meta", {}).get("source_id", "")
        matching_metrics: dict[str, Any] = {}
        if match:
            rows = match if isinstance(match, list) else match.get("decisions_required", [])
            decisions_count: dict[str, int] = {"attach": 0, "new": 0, "skip": 0}
            for r in rows:
                d = r.get("decision", "")
                if d in decisions_count:
                    decisions_count[d] += 1
            matching_metrics = {"total_candidates": len(rows), "decisions": decisions_count}
    else:
        issues = []  # v2 checks removed; run review-bundle separately
        source_id = (bundle.get("source_digest") or {}).get("source_id", "")
        matching_metrics = _matching_metrics_v2(match)

    evaluation = {
        "bundle_ref": source_id,
        "schema_version": "v3" if is_v3 else "v2",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "evaluator": "",
        "method_layers_run": ["L1"],
        "l1_issues": issues,
        "matching_metrics": matching_metrics,
        "overall_notes": "",
    }
    Path(args.out).write_text(
        json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"✓ evaluation skeleton written to {args.out}")
    return 0


# ── main ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ingest_qa")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_review = sub.add_parser("review-bundle", help="validate v3 bundle (C1-C9)")
    p_review.add_argument("--bundle", required=True)
    p_review.add_argument("--mineru-md", help="full-clean.md for page-ratio check")
    p_review.set_defaults(func=cmd_review_bundle)

    p_eval = sub.add_parser("evaluation", help="evaluation workflow")
    eval_sub = p_eval.add_subparsers(dest="eval_cmd", required=True)
    p_eval_init = eval_sub.add_parser("init", help="generate evaluation skeleton")
    p_eval_init.add_argument("--bundle", required=True)
    p_eval_init.add_argument("--preprocess", help="v2 preprocess JSON (optional)")
    p_eval_init.add_argument("--match", help="auto_apply JSON for matching metrics")
    p_eval_init.add_argument("--out", required=True)
    p_eval_init.set_defaults(func=cmd_evaluation_init)

    args = p.parse_args(argv)
    if args.cmd == "evaluation":
        return args.func(args)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

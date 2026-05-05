"""render_views.py — Mechanical view rendering from ClaimRegistry.

Renders narrative.md / dashboard.md / INSIGHTS.md files from ClaimRegistry data.
No LLM calls — pure data extraction and template filling.

Usage:
    .venv/bin/python -m scripts.render_views \\
        --registry-base . \\
        [--scope industry|arena|company|brand|all] \\
        [--ref <slug_or_ticker>] \\
        [--bundle <bundle_path>]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dir_symbol(direction: int | None) -> str:
    if direction == 1:
        return "+"
    if direction == -1:
        return "-"
    return "~"


def _truncate(text: str, n: int) -> str:
    return text[:n] if len(text) > n else text


def _load_bundle(bundle_path: Path) -> dict[str, Any]:
    """Load a bundle JSON file."""
    return json.loads(bundle_path.read_text(encoding="utf-8"))


def _bundle_sha8(bundle_path: Path) -> str:
    """Extract 8-char identifier from bundle filename.

    e.g. 'kpmg-2025-abcd1234.json' -> 'abcd1234'
    If the stem is exactly 8 hex chars, return it directly.
    Otherwise return the full stem (no extension).
    """
    stem = bundle_path.stem
    # If stem looks like a sha (8 hex chars)
    if len(stem) == 8 and all(c in "0123456789abcdef" for c in stem.lower()):
        return stem
    # Otherwise return the full stem
    return stem


# ── Narrative rendering (industry / arena / brand) ────────────────────────────

def _render_narrative(
    *,
    scope_type: str,
    scope_ref: str,
    claims: list[dict],
    one_liner: str,
    cannot_conclude: list[str],
    base: Path,
) -> str:
    """Build the narrative.md / brief.md content from claims."""
    now = _now_iso()
    claim_count = len(claims)
    source_ids: set[str] = set()
    for c in claims:
        for s in c.get("sources", []):
            src = s.get("source_id")
            if src:
                source_ids.add(src)
        for e in c.get("evidence", []):
            src = e.get("source_id")
            if src:
                source_ids.add(src)
    source_count = len(source_ids)

    lines: list[str] = []

    # Frontmatter
    lines += [
        "---",
        f"scope_type: {scope_type}",
        f"scope_ref: {scope_ref}",
        f"last_rendered: {now}",
        f"claim_count: {claim_count}",
        f"source_count: {source_count}",
        "---",
        "",
        f"# {scope_ref}",
        "",
        "## 一句话主线",
        one_liner or "",
        "",
    ]

    # Organize claims by type
    type_order = ["thesis", "judgment", "catalyst", "risk"]
    type_labels = {
        "thesis": "Thesis",
        "judgment": "Judgment",
        "catalyst": "Catalyst",
        "risk": "Risk",
    }
    by_type: dict[str, list[dict]] = {}
    for c in claims:
        ctype = c.get("type", "thesis")
        by_type.setdefault(ctype, []).append(c)

    lines.append("## 主要论点")
    lines.append("")

    for ctype in type_order:
        group = by_type.get(ctype, [])
        if not group:
            continue
        label = type_labels.get(ctype, ctype.capitalize())
        lines.append(f"### {label}（{len(group)} 条）")
        lines.append("")
        for c in group:
            text = c.get("text") or c.get("claim_text", "")
            skey = c.get("semantic_key", "")
            direction = c.get("direction")
            confidence = c.get("confidence", "")
            evidence = c.get("evidence", [])
            first_quote = ""
            if evidence:
                first_quote = _truncate(evidence[0].get("quote", ""), 80)

            dir_sym = _dir_symbol(direction)
            lines.append(f"- **{text}** [{skey}]")
            lines.append(f"  方向: {dir_sym}  置信: {confidence}")
            lines.append(f'  证据: "{first_quote}"')
            lines.append("")

    # Handle claim types not in type_order
    other_types = [t for t in by_type if t not in type_order]
    for ctype in sorted(other_types):
        group = by_type[ctype]
        label = ctype.capitalize()
        lines.append(f"### {label}（{len(group)} 条）")
        lines.append("")
        for c in group:
            text = c.get("text") or c.get("claim_text", "")
            skey = c.get("semantic_key", "")
            direction = c.get("direction")
            confidence = c.get("confidence", "")
            evidence = c.get("evidence", [])
            first_quote = ""
            if evidence:
                first_quote = _truncate(evidence[0].get("quote", ""), 80)
            dir_sym = _dir_symbol(direction)
            lines.append(f"- **{text}** [{skey}]")
            lines.append(f"  方向: {dir_sym}  置信: {confidence}")
            lines.append(f'  证据: "{first_quote}"')
            lines.append("")

    # Relations section
    lines += ["## 关系链路", ""]
    all_relations: list[str] = []
    for c in claims:
        c_text = c.get("text") or c.get("claim_text", "")
        for rel in c.get("relations", [])[:3]:
            to_id = rel.get("to", "")
            kind = rel.get("kind", "")
            # Try to resolve the 'to' claim text
            to_text = to_id  # fallback to raw id
            for other in claims:
                if other.get("claim_id") == to_id:
                    to_text = other.get("text") or other.get("claim_text", to_id)
                    break
            all_relations.append(f"{_truncate(c_text, 40)} → {kind} → {_truncate(to_text, 40)}")
        if len(all_relations) >= 3:
            break

    if all_relations:
        for r in all_relations[:3]:
            lines.append(f"- {r}")
    else:
        lines.append("（暂无关系数据）")
    lines.append("")

    # Cannot conclude
    lines += ["## 不能由现有研报得出的结论", ""]
    if cannot_conclude:
        for item in cannot_conclude[:5]:
            lines.append(f"- {item}")
    else:
        lines.append("（暂无）")
    lines.append("")

    return "\n".join(lines)


def render_industry_or_arena(
    *,
    scope_type: str,
    scope_ref: str,
    registry: Any,
    base: Path,
    bundles_dir: Path | None = None,
) -> Path:
    """Render narrative.md for an industry or arena scope."""
    claims = registry.claims_for_scope(scope_type, scope_ref)

    # Find one_liner from bundle files if possible
    one_liner = _find_one_liner(scope_type, scope_ref, base)
    cannot_conclude = _gather_cannot_conclude(scope_type, scope_ref, base)

    content = _render_narrative(
        scope_type=scope_type,
        scope_ref=scope_ref,
        claims=claims,
        one_liner=one_liner,
        cannot_conclude=cannot_conclude,
        base=base,
    )

    if scope_type == "industry":
        out_path = base / "industries" / scope_ref / "narrative.md"
    elif scope_type == "arena":
        out_path = base / "arenas" / scope_ref / "narrative.md"
    else:
        out_path = base / scope_type / scope_ref / "narrative.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return out_path


def render_brand(
    *,
    scope_ref: str,
    registry: Any,
    base: Path,
) -> Path:
    """Render brief.md for a brand scope."""
    claims = registry.claims_for_scope("brand", scope_ref)

    one_liner = _find_one_liner("brand", scope_ref, base)
    cannot_conclude = _gather_cannot_conclude("brand", scope_ref, base)

    content = _render_narrative(
        scope_type="brand",
        scope_ref=scope_ref,
        claims=claims,
        one_liner=one_liner,
        cannot_conclude=cannot_conclude,
        base=base,
    )

    out_path = base / "brands" / scope_ref / "brief.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return out_path


# ── Dashboard rendering (company) ────────────────────────────────────────────

def render_company(
    *,
    scope_ref: str,
    registry: Any,
    base: Path,
) -> Path:
    """Render dashboard.md for a company scope."""
    claims = registry.claims_for_scope("company", scope_ref)
    now = _now_iso()

    source_ids: set[str] = set()
    for c in claims:
        for s in c.get("sources", []):
            src = s.get("source_id")
            if src:
                source_ids.add(src)
        for e in c.get("evidence", []):
            src = e.get("source_id")
            if src:
                source_ids.add(src)
    source_count = len(source_ids)

    lines: list[str] = [
        "---",
        f"ticker: {scope_ref}",
        f"last_rebuilt: {now}",
        f"source_count: {source_count}",
        "---",
        "",
        f"# {scope_ref} — 多源观点面板",
        "",
        "## 观点矩阵",
        "| source_id | as_of | type | text | direction | confidence |",
        "|---|---|---|---|---|---|",
    ]

    for c in claims:
        ctype = c.get("type", "")
        text = c.get("text") or c.get("claim_text", "")
        direction = _dir_symbol(c.get("direction"))
        confidence = c.get("confidence", "")
        # Get source info
        sources = c.get("sources", [])
        if sources:
            source_id = sources[0].get("source_id", "")
            as_of = sources[0].get("as_of", "")
        else:
            evidence = c.get("evidence", [])
            source_id = evidence[0].get("source_id", "") if evidence else ""
            as_of = evidence[0].get("as_of", "") if evidence else ""
        lines.append(
            f"| {source_id} | {as_of} | {ctype} | {_truncate(text, 50)} | {direction} | {confidence} |"
        )

    lines += ["", "## 风险一览", ""]
    risk_claims = [c for c in claims if c.get("type") == "risk"]
    if risk_claims:
        for c in risk_claims:
            text = c.get("text") or c.get("claim_text", "")
            lines.append(f"- {text}")
    else:
        lines.append("（暂无风险论点）")
    lines.append("")

    content = "\n".join(lines)
    out_path = base / "companies" / scope_ref / "dashboard.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return out_path


# ── INSIGHTS.md rendering (per bundle) ───────────────────────────────────────

def render_bundle_insights(bundle_path: Path) -> Path:
    """Render an INSIGHTS.md for a single bundle JSON file."""
    bundle = _load_bundle(bundle_path)
    now = _now_iso()

    sha8 = _bundle_sha8(bundle_path)

    # Extract meta — support both old (source_digest) and new (meta) layouts
    meta = bundle.get("meta", {})
    source_digest = bundle.get("source_digest", {})

    source_id = meta.get("source_id") or source_digest.get("source_id", "")
    source_title = meta.get("source_title") or source_digest.get("source_title", source_id)

    synth = bundle.get("synthesis", {})
    one_liner = synth.get("one_sentence") or synth.get("one_liner", "")

    cannot_conclude = synth.get("cannot_conclude", [])

    # Threads: summary.threads or synthesized from synthesis sections
    threads = synth.get("threads", [])

    # Claims from bundle
    raw_claims = bundle.get("claims", []) or bundle.get("claim_candidates", [])

    lines: list[str] = [
        "---",
        f"source_id: {source_id}",
        f"synthesized_at: {now}",
        "---",
        "",
        f"# {source_title}",
        "",
        f"> {one_liner}",
        "",
        "## 主要叙事线",
        "",
    ]

    if threads:
        for thread in threads:
            title = thread.get("title", "")
            claim_ids = thread.get("claim_ids", [])
            lines.append(f"### {title}")
            lines.append("")
            # Resolve claim texts from bundle claims
            claim_map = {c.get("id", c.get("candidate_id", "")): c for c in raw_claims}
            for cid in claim_ids:
                claim = claim_map.get(cid)
                if claim:
                    text = claim.get("text") or claim.get("claim_text", cid)
                    lines.append(f"- {text}")
            lines.append("")
    else:
        # Build a synthetic narrative from what_we_know / what_is_plausible
        what_we_know = synth.get("what_we_know", [])
        what_plausible = synth.get("what_is_plausible", [])
        if what_we_know:
            lines.append("### 已知事实")
            lines.append("")
            for item in what_we_know:
                lines.append(f"- {item}")
            lines.append("")
        if what_plausible:
            lines.append("### 合理推断")
            lines.append("")
            for item in what_plausible:
                lines.append(f"- {item}")
            lines.append("")

    lines += ["## 关键证据", ""]

    # Collect evidence from high-confidence claims
    evidence_items: list[dict] = []
    for c in raw_claims:
        if c.get("confidence") in ("high", "medium_high"):
            evidence = c.get("evidence", [])
            if evidence:
                ev = evidence[0]
                quote = ev.get("quote", "")
                page = ev.get("page", "")
                if quote:
                    evidence_items.append({"quote": quote, "page": page})
        if len(evidence_items) >= 8:
            break

    if evidence_items:
        for ev in evidence_items[:8]:
            page_str = f" (p.{ev['page']})" if ev.get("page") else ""
            lines.append(f'- "{_truncate(ev["quote"], 120)}"{page_str}')
    else:
        lines.append("（暂无高置信度证据）")
    lines.append("")

    lines += ["## 不能得出的结论", ""]
    if cannot_conclude:
        for item in cannot_conclude:
            lines.append(f"- {item}")
    else:
        lines.append("（暂无）")
    lines.append("")

    content = "\n".join(lines)

    # Write to bundle_dir/insights/{sha8}.md
    insights_dir = bundle_path.parent / "insights"
    insights_dir.mkdir(parents=True, exist_ok=True)
    out_path = insights_dir / f"{sha8}.md"
    out_path.write_text(content, encoding="utf-8")
    return out_path


# ── Helper: find one_liner from bundle files ──────────────────────────────────

def _iter_bundle_files(scope_type: str, scope_ref: str, base: Path):
    """Yield bundle JSON files for a given scope."""
    if scope_type == "industry":
        bundles_dir = base / "industries" / scope_ref / "bundles"
    elif scope_type == "arena":
        bundles_dir = base / "arenas" / scope_ref / "bundles"
    elif scope_type == "company":
        bundles_dir = base / "companies" / scope_ref / "bundles"
    elif scope_type == "brand":
        bundles_dir = base / "brands" / scope_ref / "bundles"
    else:
        return

    if not bundles_dir.exists():
        return

    for f in sorted(bundles_dir.glob("*.json")):
        if f.stem.endswith("-evaluation"):
            continue
        yield f


def _find_one_liner(scope_type: str, scope_ref: str, base: Path) -> str:
    """Find the most recent bundle's one_liner for a scope."""
    for bundle_path in sorted(_iter_bundle_files(scope_type, scope_ref, base), reverse=True):
        try:
            bundle = _load_bundle(bundle_path)
            synth = bundle.get("synthesis", {})
            one_liner = synth.get("one_sentence") or synth.get("one_liner", "")
            if one_liner:
                return one_liner
        except Exception:
            continue
    return ""


def _gather_cannot_conclude(scope_type: str, scope_ref: str, base: Path) -> list[str]:
    """Gather and deduplicate cannot_conclude items across all bundles for a scope."""
    seen: set[str] = set()
    items: list[str] = []
    for bundle_path in _iter_bundle_files(scope_type, scope_ref, base):
        try:
            bundle = _load_bundle(bundle_path)
            synth = bundle.get("synthesis", {})
            for item in synth.get("cannot_conclude", []):
                if item not in seen:
                    seen.add(item)
                    items.append(item)
                    if len(items) >= 5:
                        return items
        except Exception:
            continue
    return items


# ── Enumerate all scope refs in registry ──────────────────────────────────────

def _all_scope_pairs(registry: Any) -> list[tuple[str, str]]:
    """Return all (scope_type, scope_ref) pairs present in the registry."""
    return sorted(registry._by_scope.keys())


# ── Main rendering dispatch ────────────────────────────────────────────────────

def render_scope(
    *,
    scope_type: str,
    scope_ref: str,
    registry: Any,
    base: Path,
) -> Path | None:
    """Render the view file for a single scope. Returns output path or None if skipped."""
    if scope_type == "industry":
        return render_industry_or_arena(
            scope_type="industry", scope_ref=scope_ref, registry=registry, base=base
        )
    elif scope_type == "arena":
        return render_industry_or_arena(
            scope_type="arena", scope_ref=scope_ref, registry=registry, base=base
        )
    elif scope_type == "brand":
        return render_brand(scope_ref=scope_ref, registry=registry, base=base)
    elif scope_type == "company":
        return render_company(scope_ref=scope_ref, registry=registry, base=base)
    elif scope_type == "cross_cutting":
        # cross_cutting has no directory target — skip
        return None
    else:
        print(f"[render_views] unknown scope_type {scope_type!r}, skipping", file=sys.stderr)
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mechanical view renderer from ClaimRegistry (no LLM)."
    )
    parser.add_argument("--registry-base", default=".", help="Base path for registry (default: .)")
    parser.add_argument(
        "--scope",
        choices=["industry", "arena", "company", "brand", "all"],
        default="all",
        help="Scope type to render (default: all)",
    )
    parser.add_argument("--ref", default=None, help="Specific scope_ref (slug or ticker)")
    parser.add_argument(
        "--bundle",
        default=None,
        help="Path to a bundle JSON file; renders INSIGHTS.md to bundle's insights/ dir",
    )
    args = parser.parse_args(argv)

    base = Path(args.registry_base).resolve()

    # Bundle-only mode
    if args.bundle:
        bundle_path = Path(args.bundle).resolve()
        if not bundle_path.exists():
            print(f"[render_views] bundle not found: {bundle_path}", file=sys.stderr)
            return 1
        out = render_bundle_insights(bundle_path)
        print(f"[render_views] wrote {out}")
        return 0

    # Load registry
    from app.io.claim_registry import ClaimRegistry
    registry = ClaimRegistry(base)

    rendered = 0
    skipped = 0

    if args.scope == "all" and args.ref is None:
        pairs = _all_scope_pairs(registry)
        if not pairs:
            print("[render_views] registry is empty — nothing to render")
            return 0
        for scope_type, scope_ref in pairs:
            out = render_scope(
                scope_type=scope_type, scope_ref=scope_ref, registry=registry, base=base
            )
            if out:
                print(f"[render_views] wrote {out}")
                rendered += 1
            else:
                skipped += 1
    elif args.scope == "all" and args.ref is not None:
        print("[render_views] --ref cannot be used with --scope all", file=sys.stderr)
        return 1
    else:
        scope_type = args.scope
        if args.ref:
            out = render_scope(
                scope_type=scope_type, scope_ref=args.ref, registry=registry, base=base
            )
            if out:
                print(f"[render_views] wrote {out}")
                rendered += 1
        else:
            # Render all refs for this scope_type
            from app.io.claim_registry import SCOPE_FILES
            all_claims = registry.all_claims_for_scope_type(scope_type)
            refs: set[str] = {c.get("scope_ref", "") for c in all_claims}
            refs.discard("")
            if not refs:
                print(f"[render_views] no claims for scope_type={scope_type!r}")
                return 0
            for ref in sorted(refs):
                out = render_scope(
                    scope_type=scope_type, scope_ref=ref, registry=registry, base=base
                )
                if out:
                    print(f"[render_views] wrote {out}")
                    rendered += 1
                else:
                    skipped += 1

    print(f"[render_views] done — rendered={rendered} skipped={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.io.claim_registry import ClaimRegistry
from app.io.narrative_proposals import build_proposal_file, dimension_path, now_iso


def _existing_excerpt(base: Path, scope_type: str, scope_ref: str, dimension: str) -> str:
    """Read existing narrative markdown via dimension_path (no scope IO module imports)."""
    path = dimension_path(base, scope_type, scope_ref, dimension)
    if not path.exists():
        return ""
    md = path.read_text(encoding="utf-8")
    return md[-1200:] if len(md) > 1200 else md


def cmd_propose(args: argparse.Namespace) -> int:
    base = Path(args.base)
    # Resolve scope/ref: prefer explicit --scope/--ref, fall back to --arena alias.
    scope = getattr(args, "scope", None)
    ref = getattr(args, "ref", None)
    arena = getattr(args, "arena", None)
    if arena:
        scope = "arena"
        ref = arena
    registry = ClaimRegistry(Path(args.registry_base))
    data = build_proposal_file(
        registry=registry,
        source_id=args.source_id,
        generated_at=now_iso(),
        scope_type=scope,
        scope_ref=ref,
        existing_excerpt_loader=lambda st, sr, dim: _existing_excerpt(base, st, sr, dim),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ narrative proposals written to {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="narrative_propose")
    parser.add_argument("--registry-base", default=".")
    parser.add_argument("--base", default=".")
    parser.add_argument("--source-id", required=True)
    parser.add_argument(
        "--scope",
        choices=["industry", "arena", "company"],
        help="scope type (industry, arena, or company)",
    )
    parser.add_argument("--ref", help="scope ref slug, e.g. cn-nuclear-fusion")
    parser.add_argument("--arena", help="[deprecated] arena slug; equivalent to --scope arena --ref <slug>")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    # Normalize: --arena is a deprecated alias for --scope arena --ref <slug>
    scope = args.scope
    ref = args.ref
    if args.arena:
        scope = "arena"
        ref = args.arena
    if not scope or not ref:
        parser.error("--scope and --ref are required (or use deprecated --arena <slug>)")

    # Patch back so cmd_propose can read them uniformly
    args.scope = scope
    args.ref = ref

    return cmd_propose(args)


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
from pathlib import Path

from app.io.claim_registry import ClaimRegistry
from app.io.narrative_proposals import scan_narrative_flags


def cmd_flags(args: argparse.Namespace) -> int:
    # Resolve scope/ref: prefer explicit --scope/--ref, fall back to --arena alias.
    scope = getattr(args, "scope", None)
    ref = getattr(args, "ref", None)
    arena = getattr(args, "arena", None)
    if arena:
        scope = "arena"
        ref = arena
    registry = ClaimRegistry(Path(args.registry_base))
    flags = scan_narrative_flags(
        registry=registry,
        base=Path(args.base),
        scope_type=scope,
        scope_ref=ref,
    )
    print(f"✓ narrative flags generated: {len(flags)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="narrative_flags")
    parser.add_argument("--registry-base", default=".")
    parser.add_argument("--base", default=".")
    parser.add_argument("--source-id", help="source ID (informational, not used for filtering)")
    parser.add_argument(
        "--scope",
        choices=["industry", "arena", "company"],
        help="scope type (industry, arena, or company)",
    )
    parser.add_argument("--ref", help="scope ref slug, e.g. cn-nuclear-fusion")
    parser.add_argument("--arena", help="[deprecated] arena slug; equivalent to --scope arena --ref <slug>")
    args = parser.parse_args(argv)

    # Normalize: --arena is a deprecated alias for --scope arena --ref <slug>
    scope = args.scope
    ref = args.ref
    if args.arena:
        scope = "arena"
        ref = args.arena
    if not scope or not ref:
        parser.error("--scope and --ref are required (or use deprecated --arena <slug>)")

    # Patch back so cmd_flags can read them uniformly
    args.scope = scope
    args.ref = ref

    return cmd_flags(args)


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
from pathlib import Path

from app.io.claim_registry import ClaimRegistry
from app.io.narrative_proposals import scan_narrative_flags


def cmd_flags(args: argparse.Namespace) -> int:
    slug = args.industry.strip()
    registry = ClaimRegistry(Path(args.registry_base))
    flags = scan_narrative_flags(
        registry=registry,
        base=Path(args.base),
        scope_type="industry",
        scope_ref=slug,
    )
    print(f"✓ industry narrative flags generated: {len(flags)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="industry_narrative_flags")
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--base", default=".")
    parser.add_argument("--industry", required=True, help="industry slug, e.g. cn-power-equipment")
    args = parser.parse_args(argv)
    return cmd_flags(args)


if __name__ == "__main__":
    raise SystemExit(main())

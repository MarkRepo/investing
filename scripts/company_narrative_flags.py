from __future__ import annotations

import argparse
from pathlib import Path

from app.io.claim_registry import ClaimRegistry
from app.io.narrative_proposals import scan_narrative_flags


def cmd_flags(args: argparse.Namespace) -> int:
    scope_ref = f"{args.market.strip()}_{args.ticker.strip()}"
    registry = ClaimRegistry(Path(args.registry_base))
    flags = scan_narrative_flags(
        registry=registry,
        base=Path(args.base),
        scope_type="company",
        scope_ref=scope_ref,
    )
    print(f"✓ company narrative flags generated: {len(flags)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="company_narrative_flags")
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--base", default=".")
    parser.add_argument("--market", required=True)
    parser.add_argument("--ticker", required=True)
    args = parser.parse_args(argv)
    return cmd_flags(args)


if __name__ == "__main__":
    raise SystemExit(main())

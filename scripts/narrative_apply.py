from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.io.claim_registry import ClaimRegistry
from app.io.narrative_proposals import apply_proposal_file


def cmd_apply(args: argparse.Namespace) -> int:
    pending_path = Path(args.proposals)
    data = json.loads(pending_path.read_text(encoding="utf-8"))
    registry = ClaimRegistry(Path(args.registry_base))
    try:
        counts = apply_proposal_file(
            data=data,
            registry=registry,
            base=Path(args.base),
            pending_path=pending_path,
        )
    except ValueError as exc:
        for line in str(exc).splitlines():
            print(f"✗ {line}", file=sys.stderr)
        return 1
    print(
        "✓ narrative proposals applied: "
        f"applied={counts['applied']} rejected={counts['rejected']} deferred={counts['deferred']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="narrative_apply")
    parser.add_argument("--proposals", required=True)
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--base", default=".")
    args = parser.parse_args(argv)
    return cmd_apply(args)


if __name__ == "__main__":
    raise SystemExit(main())

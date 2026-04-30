from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.io import arenas as arenas_io
from app.io.claim_registry import ClaimRegistry
from app.io.narrative_proposals import build_proposal_file, now_iso


def _existing_excerpt(base: Path, arena_slug: str, dimension: str) -> str:
    md = arenas_io.read_narrative(arena_slug, dimension, base=base)
    return md[-1200:] if len(md) > 1200 else md


def cmd_propose(args: argparse.Namespace) -> int:
    base = Path(args.base)
    registry = ClaimRegistry(Path(args.registry_base))
    data = build_proposal_file(
        registry=registry,
        source_id=args.source_id,
        generated_at=now_iso(),
        scope_type="arena",
        scope_ref=args.arena,
        existing_excerpt_loader=lambda scope_type, scope_ref, dim: _existing_excerpt(base, scope_ref, dim),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ narrative proposals written to {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="narrative_propose")
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--base", default=".")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--arena", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    return cmd_propose(args)


if __name__ == "__main__":
    raise SystemExit(main())

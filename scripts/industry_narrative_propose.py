from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.io import industry as industry_io
from app.io.claim_registry import ClaimRegistry
from app.io.narrative_proposals import build_proposal_file, now_iso


def _existing_excerpt(base: Path, slug: str, dimension: str) -> str:
    md = industry_io.read_narrative(slug, dimension, base=base)
    return md[-1200:] if len(md) > 1200 else md


def cmd_propose(args: argparse.Namespace) -> int:
    base = Path(args.base)
    slug = args.industry.strip()
    registry = ClaimRegistry(Path(args.registry_base))
    data = build_proposal_file(
        registry=registry,
        source_id=args.source_id,
        generated_at=now_iso(),
        scope_type="industry",
        scope_ref=slug,
        existing_excerpt_loader=lambda _st, _sr, dim: _existing_excerpt(base, slug, dim),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ industry narrative proposals written to {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="industry_narrative_propose")
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--base", default=".")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--industry", required=True, help="industry slug, e.g. cn-power-equipment")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    return cmd_propose(args)


if __name__ == "__main__":
    raise SystemExit(main())

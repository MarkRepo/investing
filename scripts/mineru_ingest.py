#!/usr/bin/env python3
"""MinerU ingest helper — convert a MinerU output directory into a lightweight JSON for ingest QA.

Usage:
    .venv/bin/python -m scripts.mineru_ingest <mineru_output_dir> --out /tmp/ingest-<sha8>-mineru.json

MinerU (desktop app) produces a directory containing full.md + images/.
This script wraps paths, runs heading-level rebuild, and validates tokens.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def compute_sha8(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:8]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("mineru_dir", help="MinerU output directory (contains full.md + images/)")
    p.add_argument("--out", required=True, help="Output JSON path")
    p.add_argument("--pdf", help="Original PDF path (for sha8 computation)")
    p.add_argument("--no-rebuild-headings", action="store_true", help="Skip heading level rebuild")
    p.add_argument("--archetype", choices=["technology_driven", "consumer_driven", "cyclical", "financial", "real_asset", "other"],
                   help="Industry archetype for suspicious token detection")
    args = p.parse_args()

    mineru_dir = Path(args.mineru_dir).resolve()
    if not mineru_dir.is_dir():
        print(f"Error: {mineru_dir} is not a directory", file=sys.stderr)
        return 1

    # Prefer cleaned output (full-clean.md + keep_images/) if available
    full_md = mineru_dir / "full-clean.md"
    if full_md.exists():
        images_dir = mineru_dir / "keep_images"
        source_label = "full-clean.md (cleaned)"
    else:
        full_md = mineru_dir / "full.md"
        images_dir = mineru_dir / "images"
        source_label = "full.md (raw)"

    if not full_md.exists():
        print(f"Error: neither full-clean.md nor full.md found in {mineru_dir}", file=sys.stderr)
        return 1

    # --- Step: Rebuild heading levels (P0.4) ---
    if not args.no_rebuild_headings:
        from scripts.rebuild_heading_levels import rebuild_levels as rebuild_headings
        result = rebuild_headings(full_md)
        full_md.write_text(result, encoding="utf-8")
        h1_count = len(re.findall(r'(?m)^#\s', result))
        h2_count = len(re.findall(r'(?m)^##\s', result))
        h3_count = len(re.findall(r'(?m)^###\s', result))
        total = h1_count + h2_count + h3_count
        h1_pct = f"{h1_count / total * 100:.0f}%" if total else "N/A"
        print(f"  Heading levels rebuilt: H1={h1_count} H2={h2_count} H3={h3_count} (H1 {h1_pct})")

    # --- Step: Run suspicious token validation (P0.2) ---
    from scripts.validate_mineru import scan_file
    suspicious = scan_file(full_md, archetype=args.archetype)
    tokens_out = mineru_dir / "suspicious_tokens.json"
    tokens_out.write_text(json.dumps(suspicious, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  Suspicious tokens: {len(suspicious['flags'])} flags written to {tokens_out}")

    # Compute sha8 from original PDF if provided, otherwise from md
    sha8_source = Path(args.pdf) if args.pdf else (mineru_dir / "full.md" if (mineru_dir / "full.md").exists() else full_md)
    sha8 = compute_sha8(sha8_source)

    result = {
        "_mineru_md": str(full_md),
        "_mineru_images": str(images_dir) if images_dir.is_dir() else None,
        "_suspicious_tokens": str(tokens_out),
        "meta": {
            "source_dir": str(mineru_dir),
            "sha8": sha8,
            "source_label": source_label,
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written {out} (sha8={sha8}, {source_label})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

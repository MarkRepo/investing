"""One-shot migration — write `aggregated_from` frontmatter for legacy
`findings_ws-aggregate-K#.md` files that reference real mat_ids in body but
lack the explicit list in their frontmatter.

Background: workflow 04 in cn-commercial-space wrote 7 aggregate findings;
only K1/K2 had `aggregated_from`. The rest left the list implicit in body
prose (`[mat-f82bf3]` markers), which broke
`outputs.list_affected_outputs`'s aggregate expansion (introduced 2026-05-26).

Run once, then archive (or just leave in `_migrations/`):

    python3 -m prism.scripts._migrations.migrate_aggregate_findings cn-commercial-space claude-opus-4-7

Idempotent: re-runs are no-ops once frontmatter is filled.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

from prism.scripts.findings import _FRONTMATTER_RE, _read_frontmatter
from prism.scripts.manifest import read_manifest

_MAT_PATTERN = re.compile(r"mat-[a-f0-9]{6}")


def _topic_outputs_dir(slug: str, variant: str) -> Path:
    return Path(__file__).resolve().parents[2] / "topics" / slug / variant / "outputs"


def migrate(slug: str, variant: str, dry_run: bool = False) -> dict:
    out_dir = _topic_outputs_dir(slug, variant)
    if not out_dir.is_dir():
        raise FileNotFoundError(f"outputs dir missing: {out_dir}")

    try:
        manifest_mats = {m["id"] for m in read_manifest(slug, variant).get("materials") or []}
    except FileNotFoundError:
        manifest_mats = set()

    summary: dict = {"checked": 0, "updated": [], "skipped_present": [], "skipped_empty": [], "filtered_unknown": {}}

    # 兼容两种命名：canonical `findings_ws-aggregate-K#.md` 和 legacy `findings_mat-ws-K#.md`
    # 用 frontmatter mat_id 字段过滤，只处理 mat_id 以 'ws-aggregate-' 起头的文件。
    candidates = sorted(set(
        list(out_dir.glob("findings_ws-aggregate-*.md")) +
        list(out_dir.glob("findings_mat-ws-*.md"))
    ))
    for fp in candidates:
        fm = _read_frontmatter(fp)
        mid = (fm.get("mat_id") or "").strip()
        if not mid.startswith("ws-aggregate-"):
            continue
        summary["checked"] += 1
        text = fp.read_text(encoding="utf-8")
        existing = fm.get("aggregated_from")
        if existing and isinstance(existing, list) and len(existing) > 0:
            summary["skipped_present"].append(fp.name)
            continue

        # grep body for mat-[a-f0-9]{6}
        m_fm = _FRONTMATTER_RE.match(text)
        body = text[m_fm.end():] if m_fm else text
        raw_hits = _MAT_PATTERN.findall(body)
        # dedup keep order
        seen: set[str] = set()
        ordered: list[str] = []
        for h in raw_hits:
            if h not in seen:
                seen.add(h)
                ordered.append(h)

        # filter against manifest
        kept = [h for h in ordered if h in manifest_mats] if manifest_mats else ordered
        unknown = [h for h in ordered if manifest_mats and h not in manifest_mats]
        if unknown:
            summary["filtered_unknown"][fp.name] = unknown

        if not kept:
            summary["skipped_empty"].append(fp.name)
            continue

        # write back frontmatter
        if dry_run:
            summary["updated"].append({"file": fp.name, "n_mats": len(kept), "preview": kept[:5]})
            continue

        new_fm = dict(fm)
        new_fm["aggregated_from"] = kept
        new_fm_yaml = yaml.dump(new_fm, allow_unicode=True, sort_keys=False).strip()
        if m_fm:
            new_text = f"---\n{new_fm_yaml}\n---\n{text[m_fm.end():]}"
        else:
            new_text = f"---\n{new_fm_yaml}\n---\n\n{text}"
        fp.write_text(new_text, encoding="utf-8")
        summary["updated"].append({"file": fp.name, "n_mats": len(kept)})

    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug")
    ap.add_argument("variant")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    summary = migrate(args.slug, args.variant, dry_run=args.dry_run)
    print(f"checked: {summary['checked']}")
    print(f"updated: {len(summary['updated'])}")
    for u in summary["updated"]:
        print(f"  ✓ {u}")
    if summary["skipped_present"]:
        print(f"skipped (already has aggregated_from): {len(summary['skipped_present'])}")
        for f in summary["skipped_present"]:
            print(f"  - {f}")
    if summary["skipped_empty"]:
        print(f"skipped (no mat- pattern in body): {len(summary['skipped_empty'])}")
        for f in summary["skipped_empty"]:
            print(f"  - {f}")
    if summary["filtered_unknown"]:
        print("filtered out unknown mat_ids (not in manifest — likely typos or stale):")
        for fname, ids in summary["filtered_unknown"].items():
            print(f"  {fname}: {ids}")

    # Optionally run list_affected_outputs for the user to see post-state
    try:
        from prism.scripts.outputs import list_affected_outputs
        post = list_affected_outputs(args.slug, args.variant)
        print("\npost-migration list_affected_outputs:")
        for k, v in post.items():
            n_new = len(v.get("new_mat_ids") or [])
            print(f"  {k}: {v['reason']} (+{n_new} new)")
    except Exception as e:
        print(f"(could not run list_affected_outputs: {e})", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())

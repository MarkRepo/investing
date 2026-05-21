"""Findings discovery — own + parent material reuse.

The single source of truth for "which findings does this topic synthesize from".
Used by workflow 04 (synthesize) and workflow 10 (peer-matrix).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from prism.scripts.topic import _topic_path, _read_yaml


def _own_findings_dir(slug: str, variant: str) -> Path:
    return _topic_path(slug, variant).parent / "outputs"


def list_all_findings(slug: str, variant: str) -> list[dict[str, Any]]:
    """Return all findings paths for synthesis: own + parent_materials.

    Each entry: {mat_id, path (Path), source_slug, source_variant, addresses, note, reuse}
    - reuse=False: own finding under outputs/findings_<mat_id>.md
    - reuse=True: parent's finding referenced via topic.yaml parent_materials
    """
    topic_path = _topic_path(slug, variant)
    if not topic_path.exists():
        raise FileNotFoundError(f"Topic not found: {slug}/{variant}")
    data = _read_yaml(topic_path)

    out: list[dict[str, Any]] = []

    own_dir = _own_findings_dir(slug, variant)
    if own_dir.is_dir():
        for p in sorted(own_dir.glob("findings_mat-*.md")):
            mat_id = p.stem.replace("findings_", "")
            out.append({
                "mat_id": mat_id,
                "path": p,
                "source_slug": slug,
                "source_variant": variant,
                "addresses": [],
                "note": "",
                "reuse": False,
            })

    for ref in data.get("parent_materials") or []:
        psrc = ref.get("parent_slug")
        pvar = ref.get("parent_variant", variant)
        mat_id = ref.get("mat_id")
        if not (psrc and mat_id):
            continue
        finding_path = _topic_path(psrc, pvar).parent / "outputs" / f"findings_{mat_id}.md"
        if not finding_path.exists():
            continue
        out.append({
            "mat_id": mat_id,
            "path": finding_path,
            "source_slug": psrc,
            "source_variant": pvar,
            "addresses": ref.get("addresses", []),
            "note": ref.get("note", ""),
            "reuse": True,
        })

    return out


def format_findings_for_prompt(slug: str, variant: str) -> str:
    """Render the findings list as a markdown bullet block for dispatch prompts."""
    items = list_all_findings(slug, variant)
    own = [x for x in items if not x["reuse"]]
    reuse = [x for x in items if x["reuse"]]
    lines: list[str] = []
    if own:
        lines.append(f"**自有 findings（{len(own)} 份）**：")
        for x in own:
            lines.append(f"- {x['path']}")
    if reuse:
        lines.append("")
        lines.append(f"**父级复用 findings（{len(reuse)} 份）**：")
        for x in reuse:
            addr = f" addresses={x['addresses']}" if x["addresses"] else ""
            note = f" note={x['note']}" if x["note"] else ""
            lines.append(f"- {x['path']} (mat_id={x['mat_id']}, source={x['source_slug']}){addr}{note}")
    return "\n".join(lines)

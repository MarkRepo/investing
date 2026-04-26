"""figure_contexts IO (spec §4.8).

Per-industry JSONL of research-report figure captions + surrounding text.
Written by scripts.preprocess_report at ingest time; consumed by digest
prompts (main agent reads these and prioritizes extraction from captions).

Schema (one row per figure):
    {id, page, caption, surrounding_text, section_name, source_id}
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app import config as cfg

REQUIRED_KEYS = ("id", "page", "caption", "surrounding_text", "section_name", "source_id")


def _path(slug: str, base: Path | None) -> Path:
    root = base or cfg.INDUSTRIES_DIR
    return root / slug / "figure_contexts.jsonl"


def read_figure_contexts(slug: str, base: Path | None = None) -> list[dict]:
    path = _path(slug, base)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _validate(row: dict) -> None:
    for k in REQUIRED_KEYS:
        if k not in row:
            raise ValueError(f"figure_context row missing required key: {k}")


def append_figure_contexts(
    slug: str, rows: Iterable[dict], base: Path | None = None
) -> int:
    path = _path(slug, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    for r in rows:
        _validate(r)
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


def filter_by_source_id(slug: str, source_id: str, base: Path | None = None) -> list[dict]:
    return [r for r in read_figure_contexts(slug, base=base) if r.get("source_id") == source_id]


def filter_by_section(slug: str, section_name: str, base: Path | None = None) -> list[dict]:
    return [r for r in read_figure_contexts(slug, base=base) if r.get("section_name") == section_name]

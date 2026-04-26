"""Slug-based industry IO (spec §4.1, §4.2).

Replaces the old sector-based landscape.md/players.md layout. Each industry
is one slug directory containing:

- meta.yaml        (slug, name, scope, linked_arenas, linked_tickers, created, last_updated)
- observations.jsonl  (structured facts, one per line)
- 11 narrative .md files (one per INDUSTRY_DIMENSIONS dim, kebab-case names)
- sources/         (archived original PDFs)
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Iterable

import yaml

from app import config as cfg

# Single-char slugs allowed for tests; up to 64 chars total.
_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$")


# ---------- Paths ----------

def _industries_dir(base: Path | None) -> Path:
    return base or cfg.INDUSTRIES_DIR


def _slug_dir(slug: str, base: Path | None) -> Path:
    return _industries_dir(base) / slug


def _meta_path(slug: str, base: Path | None) -> Path:
    return _slug_dir(slug, base) / "meta.yaml"


def _observations_path(slug: str, base: Path | None) -> Path:
    return _slug_dir(slug, base) / "observations.jsonl"


def _narrative_path(slug: str, dim: str, base: Path | None) -> Path:
    if dim not in cfg.INDUSTRY_DIMENSIONS:
        raise ValueError(f"unknown industry dim {dim!r}; must be one of {cfg.INDUSTRY_DIMENSIONS}")
    return _slug_dir(slug, base) / f"{dim.replace('_', '-')}.md"


# ---------- Validation ----------

def _validate_slug(slug: str) -> None:
    if not slug or not _SLUG_RE.match(slug):
        raise ValueError(
            f"invalid industry slug {slug!r}; must match [a-z0-9][a-z0-9-]*[a-z0-9], len 1-64"
        )


# ---------- Meta ----------

def create_industry(
    slug: str,
    name: str,
    scope: str,
    base: Path | None = None,
    today: date | None = None,
) -> Path:
    """Create a new industry slug directory with 11-dim narrative skeletons,
    empty observations.jsonl, meta.yaml, and sources/ dir.

    Raises ValueError on bad slug, FileExistsError if dir already exists.
    """
    _validate_slug(slug)
    if not name.strip():
        raise ValueError("name must be non-empty")
    today = today or date.today()

    slug_dir = _slug_dir(slug, base)
    if slug_dir.exists():
        raise FileExistsError(f"industry dir already exists: {slug_dir}")
    slug_dir.mkdir(parents=True)
    (slug_dir / "sources").mkdir()

    meta = {
        "slug": slug,
        "name": name,
        "scope": scope,
        "linked_arenas": [],
        "linked_tickers": [],
        "created": today.isoformat(),
        "last_updated": today.isoformat(),
    }
    _meta_path(slug, base).write_text(
        yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    # 11 narrative skeleton files
    _CN_TITLES = {
        "definition": "定义与边界",
        "market_size": "市场规模与增长",
        "lifecycle": "生命周期阶段",
        "value_chain": "产业链分析",
        "competition": "竞争结构",
        "drivers": "增长驱动与催化",
        "technology": "技术与产品",
        "regulation": "监管与政策",
        "benchmark": "关键经营指标基准值",
        "risks": "主要风险",
        "valuation": "投资视角与估值锚",
    }
    for dim in cfg.INDUSTRY_DIMENSIONS:
        header = f"# {_CN_TITLES[dim]} · {name}\n\n*slug: {slug} · 维度: {dim}*\n\n"
        _narrative_path(slug, dim, base).write_text(header, encoding="utf-8")

    # empty observations.jsonl
    _observations_path(slug, base).write_text("", encoding="utf-8")

    return slug_dir


def read_meta(slug: str, base: Path | None = None) -> dict:
    path = _meta_path(slug, base)
    if not path.exists():
        raise FileNotFoundError(f"industry not found: {slug}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_meta(slug: str, meta: dict, base: Path | None = None, today: date | None = None) -> None:
    meta = {**meta, "last_updated": (today or date.today()).isoformat()}
    _meta_path(slug, base).write_text(
        yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def list_industries(base: Path | None = None) -> list[dict]:
    """Return [{slug, name, scope, linked_arenas_count, linked_tickers_count, last_updated}, ...]."""
    root = _industries_dir(base)
    if not root.exists():
        return []
    result = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        meta_path = child / "meta.yaml"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        result.append({
            "slug": meta.get("slug", child.name),
            "name": meta.get("name", child.name),
            "scope": meta.get("scope", ""),
            "linked_arenas_count": len(meta.get("linked_arenas") or []),
            "linked_tickers_count": len(meta.get("linked_tickers") or []),
            "last_updated": meta.get("last_updated"),
        })
    return result


# ---------- Observations ----------

_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


def read_observations(slug: str, base: Path | None = None) -> list[dict]:
    path = _observations_path(slug, base)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def append_observations(
    slug: str, rows: Iterable[dict], base: Path | None = None
) -> int:
    """Append rows to observations.jsonl. Returns count written."""
    path = _observations_path(slug, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def dedup_observations(rows: Iterable[dict]) -> list[dict]:
    """Dedup on (field, timeframe, source_id); when collision, keep highest
    confidence ('high' > 'medium' > 'low'). Rows missing any key pass through."""
    buckets: dict[tuple, dict] = {}
    passthrough: list[dict] = []
    for row in rows:
        key_parts = (row.get("field"), row.get("timeframe"), row.get("source_id"))
        if None in key_parts:
            passthrough.append(row)
            continue
        existing = buckets.get(key_parts)
        if existing is None:
            buckets[key_parts] = row
            continue
        existing_rank = _CONFIDENCE_RANK.get(existing.get("confidence", "low"), 0)
        new_rank = _CONFIDENCE_RANK.get(row.get("confidence", "low"), 0)
        if new_rank > existing_rank:
            buckets[key_parts] = row
    return list(buckets.values()) + passthrough


def filter_observations_by_arena(
    slug: str, arena_slug: str, base: Path | None = None
) -> list[dict]:
    """Return observations whose arena_refs include arena_slug."""
    return [
        row for row in read_observations(slug, base=base)
        if arena_slug in (row.get("arena_refs") or [])
    ]


def filter_observations_by_segment(
    slug: str, segment: str, base: Path | None = None
) -> list[dict]:
    return [
        row for row in read_observations(slug, base=base)
        if row.get("segment") == segment
    ]


# ---------- Narrative ----------

_NARRATIVE_BLOCK_TEMPLATE = """
### 来源 {institution} {date} (sha8={sha8})
source_id: {source_id}

{block}
"""


def read_narrative(slug: str, dim: str, base: Path | None = None) -> str:
    path = _narrative_path(slug, dim, base)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def append_narrative_block(
    slug: str,
    dim: str,
    block: str,
    source_meta: dict,
    base: Path | None = None,
) -> None:
    """Append a source-labeled block to narrative .md. source_meta must contain
    institution / date / sha8 / source_id. Never modifies existing content."""
    path = _narrative_path(slug, dim, base)  # raises on unknown dim
    for key in ("institution", "date", "sha8", "source_id"):
        if key not in source_meta:
            raise ValueError(f"source_meta missing {key}")
    rendered = _NARRATIVE_BLOCK_TEMPLATE.format(
        institution=source_meta["institution"],
        date=source_meta["date"],
        sha8=source_meta["sha8"],
        source_id=source_meta["source_id"],
        block=block.rstrip(),
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(rendered)

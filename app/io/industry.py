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
    return Path(base) / "industries" if base else cfg.INDUSTRIES_DIR


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


# ---------- Cross-source aggregation (spec §6.2) ----------

_DIVERGENCE_THRESHOLD = 0.30


def _row_summary(r: dict) -> dict:
    return {
        "value": r.get("value"),
        "unit": r.get("unit"),
        "timeframe": r.get("timeframe"),
        "source_id": r.get("source_id"),
        "source_note": r.get("source_note"),
        "confidence": r.get("confidence"),
    }


def _compute_spread(values: list[float]) -> tuple[float, float, float, float | None]:
    """Return (median, min, max, spread) where spread=(max-min)/|median|.
    spread is None when median is 0 (avoid div-by-zero)."""
    vs = sorted(values)
    n = len(vs)
    median = vs[n // 2] if n % 2 == 1 else (vs[n // 2 - 1] + vs[n // 2]) / 2
    mn, mx = vs[0], vs[-1]
    spread = (mx - mn) / abs(median) if median else None
    return median, mn, mx, spread


def aggregate_observations(slug: str, base: Path | None = None) -> dict:
    """Group observations for cross-source rendering (spec §6.2).

    Returns ``{"numeric": [...], "segment": [...], "enum": [...]}``.

    - numeric: atomic numeric facts grouped by (dimension, field, timeframe, unit).
      Each group: rows, median, min_value, max_value, spread, divergent (spread>0.30),
      n_sources, n_rows.
    - segment: metric_type='segment' numeric facts grouped by (…, segment). Same shape.
    - enum: non-numeric facts grouped by (dimension, field, timeframe).
      Each group: rows, values (sorted distinct list), consistent (len==1).

    Single-source groups still compute stats (spread=0, divergent=False); the
    template decides whether to show the divergence banner based on n_sources.
    Rows with value=None or missing dimension/field are skipped.
    """
    rows = read_observations(slug, base=base)
    numeric: dict[tuple, dict] = {}
    segment: dict[tuple, dict] = {}
    enum: dict[tuple, dict] = {}
    for r in rows:
        dim = r.get("dimension")
        field = r.get("field")
        if not dim or not field:
            continue
        timeframe = r.get("timeframe")
        unit = r.get("unit")
        value = r.get("value")
        seg = r.get("segment")
        metric_type = r.get("metric_type") or "atomic"
        is_numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
        if metric_type == "segment" and is_numeric and seg:
            key = (dim, field, timeframe, unit, seg)
            bucket = segment.setdefault(key, {
                "dimension": dim, "field": field, "timeframe": timeframe,
                "unit": unit, "segment": seg, "rows": [],
            })
            bucket["rows"].append(_row_summary(r))
        elif is_numeric:
            key = (dim, field, timeframe, unit)
            bucket = numeric.setdefault(key, {
                "dimension": dim, "field": field, "timeframe": timeframe,
                "unit": unit, "rows": [],
            })
            bucket["rows"].append(_row_summary(r))
        elif isinstance(value, str) and value.strip():
            key = (dim, field, timeframe)
            bucket = enum.setdefault(key, {
                "dimension": dim, "field": field, "timeframe": timeframe,
                "rows": [],
            })
            bucket["rows"].append({**_row_summary(r), "value": value})

    def _finalize_numeric(b: dict) -> dict:
        vs = [row["value"] for row in b["rows"]]
        median, mn, mx, spread = _compute_spread(vs)
        b["median"] = median
        b["min_value"] = mn
        b["max_value"] = mx
        b["spread"] = spread
        b["divergent"] = spread is not None and spread > _DIVERGENCE_THRESHOLD
        b["n_sources"] = len({row["source_id"] for row in b["rows"]})
        b["n_rows"] = len(b["rows"])
        return b

    numeric_out = [_finalize_numeric(b) for b in numeric.values()]
    segment_out = [_finalize_numeric(b) for b in segment.values()]
    enum_out = []
    for b in enum.values():
        distinct = sorted({row["value"] for row in b["rows"]})
        b["values"] = distinct
        b["consistent"] = len(distinct) == 1
        b["n_sources"] = len({row["source_id"] for row in b["rows"]})
        b["n_rows"] = len(b["rows"])
        enum_out.append(b)
    numeric_out.sort(key=lambda b: (b["dimension"], b["field"], b["timeframe"] or ""))
    segment_out.sort(key=lambda b: (b["dimension"], b["field"], b["segment"], b["timeframe"] or ""))
    enum_out.sort(key=lambda b: (b["dimension"], b["field"], b["timeframe"] or ""))
    return {"numeric": numeric_out, "segment": segment_out, "enum": enum_out}


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


def find_by_company(ticker: str, market: str, base: Path | None = None) -> list[str]:
    """Return list of industry slugs whose linked_tickers include (market, ticker)."""
    root = _industries_dir(base)
    if not root.exists():
        return []
    matches = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        meta_path = child / "meta.yaml"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        for t in meta.get("linked_tickers") or []:
            if t.get("ticker") == ticker and t.get("market") == market:
                matches.append(meta.get("slug", child.name))
                break
    return matches


def find_by_arena(arena_slug: str, base: Path | None = None) -> str | None:
    """Return industry slug whose linked_arenas contains arena_slug, or None."""
    root = _industries_dir(base)
    if not root.exists():
        return None
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        meta_path = child / "meta.yaml"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        if arena_slug in (meta.get("linked_arenas") or []):
            return meta.get("slug", child.name)
    return None

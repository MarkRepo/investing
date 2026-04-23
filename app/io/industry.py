"""Industry (行业维度) facts layer — DESIGN §2.4 / §3.1.

Each sector has three files under ``industries/{sector}/``:
- ``landscape.md`` — 行业事实（供给/需求/周期/监管）
- ``players.md``   — 参与者清单（头部公司 + 相对强项）
- ``competence-map.md`` — 你对该行业能力圈的演进（用户手写 + 聚合 journal 数据）

All three are markdown with YAML frontmatter. ``sector`` is one of
``cfg.VALID_SECTORS``. ``competence-map.md`` rendering also surfaces derived
stats (from ``competence_map.yearly_map``) alongside the hand-written body.
"""
from __future__ import annotations

from datetime import date as date_cls
from pathlib import Path

import yaml

from app import config as cfg

FILES = ("landscape", "players", "competence-map")

_FRONTMATTER_KEYS = {
    "landscape": ("sector", "last_updated", "source_type"),
    "players": ("sector", "last_updated"),
    "competence-map": ("sector", "last_updated"),
}

_DEFAULT_BODY = {
    "landscape": (
        "## 供需\n\n\n## 成本曲线 / 产能周期\n\n\n## 监管\n\n\n"
        "## 上下游议价力\n\n\n## 关键指标（看哪几个数字）\n\n\n"
    ),
    "players": (
        "| ticker | market | name | position | 相对强项 | 备注 |\n"
        "|---|---|---|---|---|---|\n"
    ),
    "competence-map": (
        "## 我在这个行业懂什么\n\n\n## 我不懂什么（研究缺口）\n\n\n"
        "## 踩过的坑 / 赢过的仗\n\n\n"
    ),
}


def _root(base: Path | None) -> Path:
    return Path(base) / "industries" if base else cfg.INDUSTRIES_DIR


def _sector_dir(sector: str, base: Path | None) -> Path:
    if sector not in cfg.VALID_SECTORS:
        raise ValueError(f"unknown sector {sector!r}; valid: {cfg.VALID_SECTORS}")
    return _root(base) / sector


def _file_path(sector: str, kind: str, base: Path | None) -> Path:
    if kind not in FILES:
        raise ValueError(f"kind must be one of {FILES}, got {kind!r}")
    return _sector_dir(sector, base) / f"{kind}.md"


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm = yaml.safe_load(text[3:end].strip()) or {}
    return fm, text[end + len("\n---") :].lstrip("\n")


def _emit_frontmatter(fm: dict, kind: str) -> str:
    ordered: dict = {}
    for k in _FRONTMATTER_KEYS[kind]:
        if k in fm and fm[k] not in (None, ""):
            ordered[k] = fm[k]
    for k, v in fm.items():
        if k not in ordered and v not in (None, ""):
            ordered[k] = v
    return "---\n" + yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False).rstrip() + "\n---\n"


def list_sectors(base: Path | None = None) -> list[dict]:
    """Return one row per known sector with a presence flag per file."""
    root = _root(base)
    out: list[dict] = []
    for sector in cfg.VALID_SECTORS:
        d = root / sector
        row = {"sector": sector, "present": {kind: (d / f"{kind}.md").exists() for kind in FILES}}
        out.append(row)
    return out


def read(sector: str, kind: str, base: Path | None = None) -> dict:
    path = _file_path(sector, kind, base)
    if not path.exists():
        return {"frontmatter": {}, "body": _DEFAULT_BODY[kind], "exists": False, "path": str(path)}
    fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    return {"frontmatter": fm, "body": body, "exists": True, "path": str(path)}


def write(
    sector: str,
    kind: str,
    frontmatter: dict,
    body: str,
    base: Path | None = None,
) -> Path:
    path = _file_path(sector, kind, base)
    fm = {**frontmatter, "sector": sector}
    fm.setdefault("last_updated", date_cls.today().isoformat())
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _emit_frontmatter(fm, kind) + "\n" + body.lstrip()
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")
    return path

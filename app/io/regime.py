"""Market regime (钟摆) quarterly snapshot (DESIGN §2.2, §V3).

Storage: one markdown file per quarter under ``macro/regime/YYYY-Qn.md`` with
structured YAML frontmatter. Plus ``macro/regime.md`` as a pointer to the most
recent quarter (auto-regenerated on write).

Frontmatter fields:
- ``quarter``: "2026-Q1"
- ``valuation_percentile``: 0-100 (SPX or market of choice; higher = more expensive)
- ``credit_spread_bps``: investment grade - treasury, in bps
- ``vix_level``: VIX closing level at time of snapshot
- ``retail_sentiment``: "greedy" / "neutral" / "fearful"
- ``macro_reaction``: "tolerant" / "sensitive" (market reaction to data surprises)
- ``verdict``: "hot" / "neutral" / "cold" / "panic" — your 4-zone classification
- ``position_hint``: free-form sentence on what the verdict implies for position sizing
- ``cash_floor_hint``: recommended minimum cash % (integer)

The hints do NOT auto-mutate portfolio rules; they surface on /portfolio and
/valuation pages to nudge you, not trample your explicit decisions.
"""
from __future__ import annotations

import re
from datetime import date as date_cls
from pathlib import Path

import yaml

from app import config as cfg

VERDICTS = ("hot", "neutral", "cold", "panic")
SENTIMENTS = ("greedy", "neutral", "fearful")
REACTIONS = ("tolerant", "sensitive")

FRONTMATTER_KEYS = (
    "quarter",
    "valuation_percentile",
    "credit_spread_bps",
    "vix_level",
    "ust_10y_yield",
    "retail_sentiment",
    "macro_reaction",
    "verdict",
    "position_hint",
    "cash_floor_hint",
)

_QUARTER_RE = re.compile(r"^\d{4}-Q[1-4]$")


def _root(base: Path | None) -> Path:
    return (Path(base) / "macro") if base else (cfg.BASE_PATH / "macro")


def _regime_dir(base: Path | None) -> Path:
    return _root(base) / "regime"


def _pointer_path(base: Path | None) -> Path:
    return _root(base) / "regime.md"


def _quarter_path(quarter: str, base: Path | None) -> Path:
    if not _QUARTER_RE.match(quarter):
        raise ValueError(f"quarter must be YYYY-Qn, got {quarter!r}")
    return _regime_dir(base) / f"{quarter}.md"


def current_quarter(today: date_cls | None = None) -> str:
    d = today or date_cls.today()
    q = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{q}"


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm = yaml.safe_load(text[3:end].strip()) or {}
    return fm, text[end + len("\n---") :].lstrip("\n")


def _emit(fm: dict, body: str) -> str:
    ordered = {}
    for k in FRONTMATTER_KEYS:
        if k in fm:
            ordered[k] = fm[k]
    for k, v in fm.items():
        if k not in ordered:
            ordered[k] = v
    fm_text = yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False).rstrip()
    return f"---\n{fm_text}\n---\n\n{body.strip()}\n"


def _validate(fm: dict) -> None:
    if fm.get("verdict") and fm["verdict"] not in VERDICTS:
        raise ValueError(f"verdict must be one of {VERDICTS}")
    if fm.get("retail_sentiment") and fm["retail_sentiment"] not in SENTIMENTS:
        raise ValueError(f"retail_sentiment must be one of {SENTIMENTS}")
    if fm.get("macro_reaction") and fm["macro_reaction"] not in REACTIONS:
        raise ValueError(f"macro_reaction must be one of {REACTIONS}")
    vp = fm.get("valuation_percentile")
    if vp is not None:
        try:
            vp_f = float(vp)
        except (TypeError, ValueError) as e:
            raise ValueError("valuation_percentile must be numeric") from e
        if not 0 <= vp_f <= 100:
            raise ValueError("valuation_percentile must be 0..100")


def list_quarters(base: Path | None = None) -> list[str]:
    d = _regime_dir(base)
    if not d.exists():
        return []
    return sorted([p.stem for p in d.glob("*.md") if _QUARTER_RE.match(p.stem)], reverse=True)


def read(quarter: str, base: Path | None = None) -> dict | None:
    path = _quarter_path(quarter, base)
    if not path.exists():
        return None
    fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    return {"frontmatter": fm, "body": body, "path": path}


def latest(base: Path | None = None) -> dict | None:
    quarters = list_quarters(base=base)
    if not quarters:
        return None
    return read(quarters[0], base=base)


def write(quarter: str, fm: dict, body: str, base: Path | None = None) -> Path:
    if not _QUARTER_RE.match(quarter):
        raise ValueError(f"quarter must be YYYY-Qn, got {quarter!r}")
    fm = {**fm, "quarter": quarter}
    _validate(fm)
    path = _quarter_path(quarter, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_emit(fm, body), encoding="utf-8")
    _refresh_pointer(base=base)
    return path


def _refresh_pointer(base: Path | None) -> None:
    """Rewrite ``macro/regime.md`` to point at the latest quarter."""
    quarters = list_quarters(base=base)
    target = _pointer_path(base)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not quarters:
        target.write_text("# 市场钟摆\n\n尚未有任何季度快照。\n", encoding="utf-8")
        return
    latest_q = quarters[0]
    doc = read(latest_q, base=base) or {"frontmatter": {}, "body": ""}
    fm = doc["frontmatter"]
    lines = [
        f"# 市场钟摆 · 最新快照 {latest_q}",
        "",
        f"- 估值分位：{fm.get('valuation_percentile', '—')}",
        f"- VIX：{fm.get('vix_level', '—')}",
        f"- 信用利差：{fm.get('credit_spread_bps', '—')} bps",
        f"- 散户情绪：{fm.get('retail_sentiment', '—')}",
        f"- 宏观反应：{fm.get('macro_reaction', '—')}",
        f"- **判断：{fm.get('verdict', '—')}**",
        f"- 仓位提示：{fm.get('position_hint', '—')}",
        f"- 现金下限建议：{fm.get('cash_floor_hint', '—')}%",
        "",
        f"历史快照见 `macro/regime/*.md`",
        "",
    ]
    target.write_text("\n".join(lines), encoding="utf-8")

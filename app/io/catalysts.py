"""Catalyst calendar: earnings dates + industry events.

Storage: ``macro/catalysts.md`` — single markdown table. Rows are hand-entered
(earnings date from IR page, industry events from news). No external API.

Why markdown and not SQLite: catalysts list is short (10-50 rows at a time),
editing as a table in a markdown viewer is pleasant, and we already commit the
whole repo to git. SQLite would be over-engineering for this scale.

Schema:
| date | ticker | industry | kind | title | note |

- date: YYYY-MM-DD
- ticker: ``market_ticker`` (e.g. US_HIMS) or empty if industry-wide
- industry: industry id (e.g. ``baijiu``) or empty if company-specific
- kind: ``earnings | investor_day | fda | regulatory | industry_data | other``
- title: one-line description
- note: optional context
"""
from __future__ import annotations

from datetime import date as date_cls
from pathlib import Path

from app import config as cfg

COLUMNS = ("date", "ticker", "industry", "kind", "title", "note")
VALID_KINDS = ("earnings", "investor_day", "fda", "regulatory", "industry_data", "other")

_PREAMBLE = "# 催化剂日历\n\n手工维护。财报日期看 IR 页面，行业事件看新闻。\n\n"


def _path(base: Path | None) -> Path:
    root = (Path(base) / "macro") if base else (cfg.BASE_PATH / "macro")
    return root / "catalysts.md"


def _parse(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells == list(COLUMNS):
            continue
        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue
        if len(cells) != len(COLUMNS):
            continue
        rows.append(dict(zip(COLUMNS, cells)))
    return rows


def _emit(rows: list[dict]) -> str:
    header = "| " + " | ".join(COLUMNS) + " |"
    sep = "|" + "|".join(["---"] * len(COLUMNS)) + "|"
    body = [header, sep]
    for r in rows:
        body.append("| " + " | ".join(str(r.get(c, "")) for c in COLUMNS) + " |")
    return _PREAMBLE + "\n".join(body) + "\n"


def list_all(base: Path | None = None) -> list[dict]:
    path = _path(base)
    if not path.exists():
        return []
    rows = _parse(path.read_text(encoding="utf-8"))
    rows.sort(key=lambda r: r.get("date") or "")
    return rows


def upcoming(base: Path | None = None, within_days: int = 7, today: date_cls | None = None) -> list[dict]:
    today = today or date_cls.today()
    cutoff = today.toordinal() + within_days
    out = []
    for r in list_all(base=base):
        try:
            d = date_cls.fromisoformat(r.get("date") or "")
        except ValueError:
            continue
        if today.toordinal() <= d.toordinal() <= cutoff:
            r2 = dict(r)
            r2["days_to"] = d.toordinal() - today.toordinal()
            out.append(r2)
    return out


def add(entry: dict, base: Path | None = None) -> Path:
    """Append a new catalyst row. Validates kind and requires date + title."""
    d = (entry.get("date") or "").strip()
    if not d:
        raise ValueError("date required")
    try:
        date_cls.fromisoformat(d)
    except ValueError as e:
        raise ValueError(f"date must be YYYY-MM-DD, got {d!r}") from e
    kind = (entry.get("kind") or "").strip() or "other"
    if kind not in VALID_KINDS:
        raise ValueError(f"kind must be one of {VALID_KINDS}, got {kind!r}")
    title = (entry.get("title") or "").strip()
    if not title:
        raise ValueError("title required")
    row = {c: str(entry.get(c, "")).strip() for c in COLUMNS}
    row["kind"] = kind
    rows = list_all(base=base)
    rows.append(row)
    rows.sort(key=lambda r: r.get("date") or "")
    path = _path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_emit(rows), encoding="utf-8")
    return path


def delete(index: int, base: Path | None = None) -> Path:
    """Delete by 0-based index in the sorted list (which is how the UI shows them)."""
    rows = list_all(base=base)
    if not (0 <= index < len(rows)):
        raise IndexError(f"index {index} out of range (have {len(rows)} rows)")
    rows.pop(index)
    path = _path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_emit(rows), encoding="utf-8")
    return path

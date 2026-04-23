"""Quarterly review aggregation: process vs result scoring.

DESIGN §2.1 / §3.5: "过程 ≠ 结果。" A decision is judged primarily by its
*process* quality; the *result* is noisy. Over time, aggregate them:
- High process + low result → probably unlucky, keep the policy.
- Low process + high result → dangerous, don't repeat.
"""
from __future__ import annotations

from datetime import date as date_cls
from pathlib import Path
from statistics import mean

from app.io import journal as journal_io

_PROCESS_FIELDS = (
    "process_quality",
    "process_rigor",
    "process_rule_adherence",
    "process_emotional_control",
)
_RESULT_FIELDS = ("result_quality",)


def quarter_key(d: date_cls) -> str:
    q = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{q}"


def _as_float(v) -> float | None:
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x


def _avg(values: list[float | None]) -> float | None:
    nums = [v for v in values if v is not None]
    return mean(nums) if nums else None


def _entry_process_score(fm: dict) -> float | None:
    return _avg([_as_float(fm.get(k)) for k in _PROCESS_FIELDS])


def _entry_result_score(fm: dict) -> float | None:
    return _avg([_as_float(fm.get(k)) for k in _RESULT_FIELDS])


def list_quarters(base: Path | None = None) -> list[str]:
    entries = journal_io.list_entries(base=base)
    qs = set()
    for fm in entries:
        d = fm.get("date")
        if not d:
            continue
        try:
            qs.add(quarter_key(date_cls.fromisoformat(d)))
        except ValueError:
            continue
    return sorted(qs, reverse=True)


def current_quarter(today: date_cls | None = None) -> str:
    return quarter_key(today or date_cls.today())


def quarter_summary(
    quarter: str, base: Path | None = None
) -> dict:
    """Aggregate a quarter.

    Returns:
        {
          "quarter": "2026-Q1",
          "entries": [...decorated frontmatter dicts...],
          "count": N,
          "avg_process": float | None,
          "avg_result": float | None,
          "by_action": {"buy": {"count", "avg_process", "avg_result"}, ...},
          "mismatches": {
              "good_process_bad_result": [...],
              "bad_process_good_result": [...],
              "unfilled_result": [...]
          }
        }
    """
    entries = journal_io.list_entries(base=base)
    rows: list[dict] = []
    for fm in entries:
        d = fm.get("date")
        if not d:
            continue
        try:
            if quarter_key(date_cls.fromisoformat(d)) != quarter:
                continue
        except ValueError:
            continue
        p = _entry_process_score(fm)
        r = _entry_result_score(fm)
        rows.append({
            "id": fm.get("id"),
            "date": d,
            "ticker": fm.get("ticker"),
            "market": fm.get("market"),
            "action": fm.get("action"),
            "process": p,
            "result": r,
        })
    rows.sort(key=lambda x: (x["date"], x["ticker"] or ""))

    by_action: dict = {}
    for r in rows:
        a = r.get("action") or "?"
        by_action.setdefault(a, []).append(r)
    action_stats = {}
    for a, rs in by_action.items():
        action_stats[a] = {
            "count": len(rs),
            "avg_process": _avg([r["process"] for r in rs]),
            "avg_result": _avg([r["result"] for r in rs]),
        }

    good_pr_bad_res = [r for r in rows if (r["process"] or 0) >= 4 and (r["result"] is not None) and r["result"] <= 2]
    bad_pr_good_res = [r for r in rows if (r["process"] is not None) and r["process"] <= 2 and (r["result"] or 0) >= 4]
    unfilled = [r for r in rows if r["result"] is None and r["action"] in ("buy", "add", "trim", "sell")]

    return {
        "quarter": quarter,
        "entries": rows,
        "count": len(rows),
        "avg_process": _avg([r["process"] for r in rows]),
        "avg_result": _avg([r["result"] for r in rows]),
        "by_action": action_stats,
        "mismatches": {
            "good_process_bad_result": good_pr_bad_res,
            "bad_process_good_result": bad_pr_good_res,
            "unfilled_result": unfilled,
        },
    }

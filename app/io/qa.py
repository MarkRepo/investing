"""QA warnings & gap-report IO.

每家公司一个 ``qa_warnings.jsonl``（append-only）+ 一个 ``qa_gaps.md`` 快照。

Warning schema::

    {
      "id": "<stable hash of scope+source_id+rule+target>",
      "scope": "BSE_920118",
      "source_id": "研报-…-09fe9bc6",
      "rule": "fidelity",
      "target": "claim:#10",
      "severity": "warn",
      "detail": "evidence_quote 在原文里找不到…",
      "fix_hint": "回到原 section 读该事实附近 …",
      "status": "open" | "resolved" | "dismissed",
      "created_at": "2026-04-25T…",
      "resolved_at": null,
      "resolved_note": null
    }

幂等键 = ``(scope, source_id, rule, target)``。相同键重复写入跳过。
状态更新通过读全文件 → 修改匹配行 → 重写实现（文件规模小，这样比 event-sourcing 简单）。
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app import config as cfg


# --- paths -------------------------------------------------------------------


def _company_dir(ticker: str, market: str, base: Path | None = None) -> Path:
    root = Path(base) if base else cfg.BASE_PATH
    return root / "companies" / f"{market}_{ticker}"


def _warnings_path(ticker: str, market: str, base: Path | None = None) -> Path:
    return _company_dir(ticker, market, base) / "qa_warnings.jsonl"


def _gap_path(ticker: str, market: str, base: Path | None = None) -> Path:
    return _company_dir(ticker, market, base) / "qa_gaps.md"


# --- fix hints ---------------------------------------------------------------

FIX_HINTS: dict[str, str] = {
    "fidelity": (
        "evidence_quote 可能是跨段拼接或改写。回到原 section 找该事实附近 500 字，"
        "确认是否连续直引；必要时重跑对应 subagent 并在 prompt 里强调 evidence 必须连续出自一段原文。"
    ),
    "empty_evidence": (
        "answered 必须同时有 answer_text 和 evidence_quote。补齐 evidence_quote，"
        "或诚实降级为 unanswered（IO 会在 append_notes 时自动剔除）。"
    ),
    "self_contradict_specific": (
        "answer_text 自己说信息不全（含'未提及/未披露/未明确'等）。"
        "编辑 competence-notes.md 把该 q_id 的 level 从 specific 降级为 vague。"
    ),
    "polarity_mismatch": (
        "复核 polarity：若 claim_text 真含负向方向（毛利下降/营收下滑/需求承压），polarity 改 bear；"
        "若上下文中负面词指向成本/费用/负债（费用率下降是利好），此条 dismiss 即可（已知规则误报）。"
    ),
    "proposed_dup": (
        "proposed_question 与 existing checklist item 高度重合。"
        "若已 approve 为新 item，把 merged.json 里的 proposed_additions 对应条目剔除（或在 aggregate 加后处理）；"
        "否则考虑把 proposed_question 作为补充合并到 existing item 的 why_matters。"
    ),
    "checklist_company_contamination": (
        "checklist question 里写死了某 participant 名字。下次 ingest 之前先改 checklist："
        "把公司名替换为'本公司'或直接删除；替换后 question 仍应可被 arena 里的其它 participant 回答，"
        "否则这是单公司尽调题，不该放在 arena checklist 里。"
    ),
}


# --- helpers -----------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _stable_id(scope: str, source_id: str, rule: str, target: str) -> str:
    key = f"{scope}|{source_id}|{rule}|{target}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def make_warning(
    *,
    scope: str,
    source_id: str | None,
    rule: str,
    target: str,
    detail: str,
    severity: str = "warn",
    fix_hint: str | None = None,
) -> dict[str, Any]:
    sid = source_id or ""
    return {
        "id": _stable_id(scope, sid, rule, target),
        "scope": scope,
        "source_id": source_id,
        "rule": rule,
        "target": target,
        "severity": severity,
        "detail": detail,
        "fix_hint": fix_hint or FIX_HINTS.get(rule, ""),
        "status": "open",
        "created_at": _now_iso(),
        "resolved_at": None,
        "resolved_note": None,
    }


# --- warnings io -------------------------------------------------------------


def read_warnings(
    ticker: str,
    market: str,
    *,
    status: str | None = None,
    base: Path | None = None,
) -> list[dict[str, Any]]:
    path = _warnings_path(ticker, market, base)
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if status and obj.get("status") != status:
            continue
        out.append(obj)
    return out


def _write_all(path: Path, warnings: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(w, ensure_ascii=False) for w in warnings]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def append_warnings(
    ticker: str,
    market: str,
    warnings: list[dict[str, Any]],
    *,
    base: Path | None = None,
) -> dict[str, int]:
    """Append warnings. Dedups on ``id``; re-opens a ``dismissed`` record if seen again.

    Returns counts: ``{"added": N, "skipped_dup": M, "reopened": K}``.
    """
    path = _warnings_path(ticker, market, base)
    existing = read_warnings(ticker, market, base=base)
    existing_by_id = {w["id"]: w for w in existing}
    added = skipped = reopened = 0

    for w in warnings:
        wid = w["id"]
        prev = existing_by_id.get(wid)
        if prev is None:
            existing.append(w)
            existing_by_id[wid] = w
            added += 1
        else:
            if prev.get("status") == "dismissed":
                # Don't reopen dismissed warnings automatically; users dismissed them for a reason.
                skipped += 1
            elif prev.get("status") == "resolved":
                # Same issue detected again after a resolve: create a new "open" record
                # by slightly mutating the id (suffix with timestamp).
                new_w = dict(w)
                new_w["id"] = wid + "-" + _now_iso()[:13]
                existing.append(new_w)
                existing_by_id[new_w["id"]] = new_w
                reopened += 1
            else:
                skipped += 1

    _write_all(path, existing)
    return {"added": added, "skipped_dup": skipped, "reopened": reopened}


def update_status(
    ticker: str,
    market: str,
    warning_id: str,
    status: str,
    *,
    note: str | None = None,
    base: Path | None = None,
) -> bool:
    """Mark a warning as ``resolved`` / ``dismissed`` / ``open``. Returns True if found."""
    if status not in ("open", "resolved", "dismissed"):
        raise ValueError(f"invalid status: {status}")
    path = _warnings_path(ticker, market, base)
    existing = read_warnings(ticker, market, base=base)
    hit = False
    for w in existing:
        if w["id"] == warning_id:
            w["status"] = status
            w["resolved_at"] = _now_iso() if status != "open" else None
            w["resolved_note"] = note
            hit = True
            break
    if hit:
        _write_all(path, existing)
    return hit


# --- gap snapshot io ---------------------------------------------------------


def write_gap_markdown(
    ticker: str,
    market: str,
    markdown: str,
    *,
    base: Path | None = None,
) -> Path:
    path = _gap_path(ticker, market, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    stamped = f"<!-- generated_at: {_now_iso()} -->\n" + markdown.rstrip() + "\n"
    path.write_text(stamped, encoding="utf-8")
    return path


def read_gap_markdown(
    ticker: str, market: str, *, base: Path | None = None
) -> tuple[str, str | None]:
    """Return ``(markdown, generated_at)``. Markdown excludes the header comment."""
    path = _gap_path(ticker, market, base)
    if not path.exists():
        return "", None
    text = path.read_text(encoding="utf-8")
    generated_at = None
    if text.startswith("<!--"):
        end = text.find("-->")
        if end != -1:
            head = text[:end]
            if "generated_at:" in head:
                generated_at = head.split("generated_at:", 1)[1].strip().strip("<!-")
            text = text[end + 3 :].lstrip("\n")
    return text, generated_at


# --- cross-company summary ---------------------------------------------------


def list_all_companies_with_qa(base: Path | None = None) -> list[tuple[str, str]]:
    """Walk ``companies/`` and return (ticker, market) pairs that have qa files."""
    root = (Path(base) if base else cfg.BASE_PATH) / "companies"
    if not root.exists():
        return []
    out = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        name = d.name
        if "_" not in name:
            continue
        market, ticker = name.split("_", 1)
        if (d / "qa_warnings.jsonl").exists() or (d / "qa_gaps.md").exists():
            out.append((ticker, market))
    return out


def summarize_by_company(base: Path | None = None) -> list[dict[str, Any]]:
    """Return one row per company with qa files, with open/resolved/dismissed counts."""
    rows = []
    for (ticker, market) in list_all_companies_with_qa(base):
        warnings = read_warnings(ticker, market, base=base)
        counts = {"open": 0, "resolved": 0, "dismissed": 0}
        by_rule: dict[str, int] = {}
        for w in warnings:
            counts[w.get("status", "open")] = counts.get(w.get("status", "open"), 0) + 1
            if w.get("status") == "open":
                by_rule[w["rule"]] = by_rule.get(w["rule"], 0) + 1
        _, gap_generated = read_gap_markdown(ticker, market, base=base)
        rows.append({
            "ticker": ticker,
            "market": market,
            "key": f"{market}_{ticker}",
            "open": counts["open"],
            "resolved": counts["resolved"],
            "dismissed": counts["dismissed"],
            "total": sum(counts.values()),
            "open_by_rule": by_rule,
            "gap_generated_at": gap_generated,
        })
    rows.sort(key=lambda r: (-r["open"], r["key"]))
    return rows

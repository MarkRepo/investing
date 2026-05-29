"""Knowledge gap detector — zero LLM calls.

Reports (does NOT decide) which K# need more evidence, which web-search
materials are stale, and which claims have only training-knowledge basis.

LLM 自己看 report 决定继续搜还是停。
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from prism.scripts import topic as topic_io
from prism.scripts.manifest import list_expired_web_search, read_manifest

PRISM_ROOT = Path(__file__).resolve().parent.parent


def _addr_key(addr: str) -> str:
    return addr.split("@", 1)[0] if isinstance(addr, str) else ""


def _to_aware_dt(value) -> datetime | None:
    """把 ISO 字符串解析成 tz-aware datetime（naive 当 UTC）；失败返 None。"""
    if not value or not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _detect_relative_updated(slug: str, variant: str, topic: dict) -> list[dict]:
    """flag-only 诊断：本 topic 的 case 合成后，若某亲属（父/子）的成稿产出
    （case/thesis/sidecar）文件 mtime **晚于**本 topic case 的 last_updated → flag。

    不 gate、不进 uncovered_ks——只提示"亲属更新了，考虑复跑借用段"。受 §1.3 护栏：
    本 topic 质量校验永远本地，本 flag 不替本 topic 做质量判断。
    本 topic case 从未合成（无 last_updated）→ 无可过时的借用，返空。
    """
    our_type = topic.get("type", "")
    our_case_key = topic_io._CASE_BY_TYPE.get(our_type)
    if not our_case_key:
        return []
    state = (topic.get("outputs_state") or {}).get(our_case_key) or {}
    our_dt = _to_aware_dt(state.get("last_updated"))
    if our_dt is None:
        return []  # case 没合成过，无借用可过时

    try:
        rels = topic_io.get_relative_outputs(slug, variant)
    except Exception:
        return []

    flags: list[dict] = []
    relatives = []
    if rels.get("parent"):
        relatives.append(("parent", rels["parent"]))
    for c in rels.get("children") or []:
        relatives.append(("child", c))

    for role, rel in relatives:
        for okey, opath in (rel.get("outputs") or {}).items():
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(opath), tz=timezone.utc)
            except OSError:
                continue
            if mtime > our_dt:
                flags.append({
                    "relative_role": role,
                    "relative_slug": rel.get("slug"),
                    "relative_output": okey,
                    "relative_updated_at": mtime.isoformat(),
                    "our_output": our_case_key,
                    "our_synth_at": our_dt.isoformat(),
                })
    return flags


def detect_gaps(
    slug: str,
    variant: str,
    min_evidence: int = 2,
) -> dict:
    """Detect knowledge gaps in a topic's research.

    Returns:
        {
            'topic': {slug, variant, thesis_version},
            'uncovered_ks':       [K#, ...],     # 0 evidence
            'thin_evidence':      [K#, ...],     # < min_evidence
            'evidence_count':     {K#: int},
            'expired_web_materials': [...],      # web-search > 90d
            'training_only_claims': [...],       # placeholder, requires baseline
            'relative_updated': [...],           # 亲属成稿产出比本 topic case 新（flag-only）
        }
    """
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        return {"error": f"topic not found: {slug}/{variant}"}

    thesis_block = topic.get("thesis") or {}
    cur_v = thesis_block.get("current_version")

    ks: list[str] = []
    if cur_v is not None:
        try:
            from prism.scripts.outputs import extract_killer_questions
            ks = list(extract_killer_questions(slug, variant, cur_v))
        except Exception:
            ks = []

    try:
        manifest = read_manifest(slug, variant)
    except FileNotFoundError:
        manifest = {"materials": []}

    evidence_count: dict[str, int] = {k: 0 for k in ks}
    for m in manifest.get("materials") or []:
        addrs = m.get("addresses") or []
        seen_keys = {_addr_key(a) for a in addrs}
        for k in seen_keys:
            if k in evidence_count:
                evidence_count[k] += 1

    uncovered = [k for k in ks if evidence_count[k] == 0]
    thin = [k for k in ks if 0 < evidence_count[k] < min_evidence]

    expired = list_expired_web_search(slug, variant) if manifest.get("materials") else []

    training_only: list[str] = []

    relative_updated = _detect_relative_updated(slug, variant, topic)

    return {
        "topic": {
            "slug": slug,
            "variant": variant,
            "thesis_version": cur_v,
        },
        "uncovered_ks": uncovered,
        "thin_evidence": thin,
        "evidence_count": evidence_count,
        "expired_web_materials": [
            {"id": m["id"], "filename": m["filename"],
             "expire_at": (m.get("search_meta") or {}).get("expire_at")}
            for m in expired
        ],
        "training_only_claims": training_only,
        "relative_updated": relative_updated,
    }


def format_summary(report: dict) -> str:
    """Human-readable summary for 主 agent 在对话里展示给用户。"""
    if "error" in report:
        return f"⚠ {report['error']}"
    lines = []
    t = report["topic"]
    lines.append(
        f"📊 Gap report: {t['slug']}/{t['variant']} "
        f"(thesis_v{t['thesis_version']})"
    )
    if report["uncovered_ks"]:
        lines.append(
            f"  ❌ 0 evidence: {', '.join(report['uncovered_ks'])}"
        )
    if report["thin_evidence"]:
        ec = report["evidence_count"]
        thin_str = ", ".join(f"{k}({ec[k]})" for k in report["thin_evidence"])
        lines.append(f"  ⚠ thin: {thin_str}")
    if report["expired_web_materials"]:
        lines.append(
            f"  ⏰ expired web-search: {len(report['expired_web_materials'])} 条 (>90d)"
        )
    rel_upd = report.get("relative_updated") or []
    if rel_upd:
        lines.append(
            f"  🔗 relative-updated: {len(rel_upd)} 条（亲属产出比本 topic case 新，考虑复跑借用段）"
        )
    if not (report["uncovered_ks"] or report["thin_evidence"]
            or report["expired_web_materials"] or rel_upd):
        lines.append("  ✅ no gaps detected")
    return "\n".join(lines)

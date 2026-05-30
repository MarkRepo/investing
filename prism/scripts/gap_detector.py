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


def _detect_ring_inputs(topic: dict, manifest: dict) -> dict:
    """A 轴：决策链输入合同覆盖（**不依赖具体拆解**，可靠）。

    按 topic.type 取输入合同，逐项查"是否被实收材料的 rings 标签覆盖"：
      - 材料强制项（质性，api_satisfiable=False）无材料 → uncovered_ring_inputs（可靠红信号）
      - api_satisfiable 项无材料 → 多为合成期自动拉（api_pending，非红）；
        但若需 financial/market 数据却连 ticker 都没有 → 真缺口（无法自动拉、无材料）
    legacy 守门：旧 topic（无 decomposition 且无任一材料带 rings）→ status='n/a'，不刷红误报。
    **训练知识不计入任何项**（只认实收材料 / 可拉 API）。
    """
    from prism.scripts.input_contract import (
        required_inputs, is_api_satisfiable, API_SOURCES,
    )

    topic_type = topic.get("type", "")
    items = required_inputs(topic_type)
    if not items:
        return {"ring_axis_status": "n/a", "ring_coverage": {},
                "uncovered_ring_inputs": [], "api_pending_inputs": []}

    mats = manifest.get("materials") or []
    coverage: dict[str, int] = {}
    for m in mats:
        for r in m.get("rings") or []:
            coverage[r] = coverage.get(r, 0) + 1

    any_rings = bool(coverage)
    has_decomp = (topic.get("decomposition") or {}).get("current_version") is not None
    if not any_rings and not has_decomp:
        # 旧 topic：拆解/rings 都没接入过 → ring 轴不适用，避免误报
        return {"ring_axis_status": "n/a",
                "ring_coverage": {it["code"]: 0 for it in items},
                "uncovered_ring_inputs": [], "api_pending_inputs": []}

    scope = topic.get("scope") or {}
    has_ticker = bool(scope.get("ticker") or scope.get("extra_tickers"))
    ring_coverage: dict[str, int] = {}
    uncovered: list[dict] = []
    api_pending: list[dict] = []

    for it in items:
        code = it["code"]
        cnt = coverage.get(code, 0)
        ring_coverage[code] = cnt
        if cnt > 0:
            continue
        entry = {"code": code, "ring": it["ring"], "label": it["label"],
                 "served_by": it.get("served_by") or [], "hard": bool(it.get("hard"))}
        if is_api_satisfiable(it):
            needs_quote = bool(set(it.get("served_by") or []) & {"financial_data", "market_data"})
            if needs_quote and not has_ticker:
                entry["reason"] = "无材料且无 ticker，无法自动拉数"
                uncovered.append(entry)
            else:
                api_pending.append(entry)  # 合成期自动拉，信息项非红
        else:
            entry["reason"] = "材料强制项，无任何材料覆盖"
            uncovered.append(entry)

    return {"ring_axis_status": "active", "ring_coverage": ring_coverage,
            "uncovered_ring_inputs": uncovered, "api_pending_inputs": api_pending}


def detect_gaps(
    slug: str,
    variant: str,
    min_evidence: int = 2,
) -> dict:
    """Detect knowledge gaps in a topic's research.

    双轴：
      A 轴（ring 输入覆盖，**不依赖拆解**，可靠）：决策链输入合同各类目是否被实收材料覆盖。
      B 轴（K# 覆盖，thesis 脊柱）：uncovered_ks / thin_evidence（B 轴单独兜不住命门正确性，
            靠 04 写作 delta 重拆补）。

    Returns:
        {
            'topic': {slug, variant, thesis_version},
            # B 轴（K# 脊柱）
            'uncovered_ks':       [K#, ...],     # 0 evidence
            'thin_evidence':      [K#, ...],     # < min_evidence
            'evidence_count':     {K#: int},
            # A 轴（ring 输入合同）
            'ring_axis_status':   'active' | 'n/a',   # 'n/a' = 旧 topic 守门
            'ring_coverage':      {code: int},        # 各合同类目的材料计数
            'uncovered_ring_inputs': [{code,ring,label,served_by,hard,reason}, ...],
            'api_pending_inputs':    [{code,ring,label,served_by}, ...],  # 合成期自动拉，非红
            # 其它
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

    ring = _detect_ring_inputs(topic, manifest)

    return {
        "topic": {
            "slug": slug,
            "variant": variant,
            "thesis_version": cur_v,
        },
        "uncovered_ks": uncovered,
        "thin_evidence": thin,
        "evidence_count": evidence_count,
        "ring_axis_status": ring["ring_axis_status"],
        "ring_coverage": ring["ring_coverage"],
        "uncovered_ring_inputs": ring["uncovered_ring_inputs"],
        "api_pending_inputs": ring["api_pending_inputs"],
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
    # A 轴：ring 输入合同
    uri = report.get("uncovered_ring_inputs") or []
    if uri:
        def _fmt(e):
            mark = "🔴" if e.get("hard") else ""
            return f"{e['code']}(环{e['ring']}{mark})"
        lines.append("  🧩 缺输入: " + ", ".join(_fmt(e) for e in uri))
    api_pending = report.get("api_pending_inputs") or []
    if api_pending:
        lines.append(
            f"  📈 待合成期拉数: {', '.join(e['code'] for e in api_pending)}（financial/market 自动）"
        )
    if report.get("ring_axis_status") == "n/a":
        lines.append("  🧩 ring 轴: n/a（旧 topic，未接入拆解/rings）")
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
            or report["expired_web_materials"] or rel_upd or uri):
        lines.append("  ✅ no gaps detected")
    return "\n".join(lines)

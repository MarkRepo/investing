"""prism doctor — 不变量状态机报告（零 LLM，纯只读函数组合）。

用法：
    python3 -c "
    from prism.scripts.doctor import doctor
    import json
    print(json.dumps(doctor('{slug}', '{variant}'), ensure_ascii=False, indent=2))
    "

返回 JSON-serializable dict，包含 arc / satisfied / unmet / blockers / diagnostics /
prescan_status / suggested_next / floor 字段（见 _arc.md §doctor 报告样例）。

实现原则：零 LLM、零新业务逻辑——只组合现有只读函数（见计划第 4 部分）。
"""
from __future__ import annotations

import re
from pathlib import Path


# --------------------------------------------------------------------------- #
# 常量                                                                         #
# --------------------------------------------------------------------------- #

_ALL_INV = ["I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8"]

_CASE_BY_TYPE = {
    "company": "c_investment_case",
    "industry": "i_industry_case",
    "arena": "a_arena_case",
    "macro": "m_regime_read",
}

_SIDECAR_BY_TYPE = {
    "company": "07_decision_kit.yaml",
    "industry": "industry_to_arenas.yaml",
    "arena": "peer_matrix.yaml",
    "macro": "transmission_map.yaml",
}


# --------------------------------------------------------------------------- #
# 主函数                                                                        #
# --------------------------------------------------------------------------- #

def doctor(slug: str, variant: str) -> dict:
    """评估 I1-I8 满足情况，返回 JSON-serializable dict。

    设计约束：
    - 零 LLM、零新业务逻辑
    - 只读，不修改任何状态
    - topic 不存在时返回 {"error": ...}，不 raise
    """
    from prism.scripts.topic import (
        PRISM_ROOT,
        read_topic,
        get_critic_verdict,
        pending_unfetched_todos,
        empty_undecided_todos,
        primer_quality_gate,
        get_current_prescan_status,
    )
    from prism.scripts.manifest import read_manifest, list_unprocessed
    from prism.scripts.gap_detector import snapshot_gaps

    _topics_root: Path = PRISM_ROOT / "topics"
    _variant_dir: Path = _topics_root / slug / variant
    _outputs_dir: Path = _variant_dir / "outputs"

    # ------------------------------------------------------------------ #
    # Read topic                                                           #
    # ------------------------------------------------------------------ #
    try:
        topic = read_topic(slug, variant)
    except FileNotFoundError:
        return {"error": f"Topic not found: {slug}/{variant}"}

    topic_type = topic.get("type", "")
    satisfied: list[str] = []
    unmet: list[dict] = []

    # ------------------------------------------------------------------ #
    # I1 · 立题                                                           #
    # ------------------------------------------------------------------ #
    i1_issues: list[str] = []

    if topic_type not in ("company", "industry", "arena", "macro"):
        i1_issues.append(f"type 无效或未设: {topic_type!r}")

    scope = topic.get("scope") or {}
    question = (scope.get("question") or "").strip()
    if not question:
        i1_issues.append("scope.question 为空")
    elif len(question) > 25 and not (topic.get("search_terms") or []):
        i1_issues.append("question >25字 但 search_terms 为空")

    if topic_type == "company":
        if not topic.get("ticker"):
            i1_issues.append("company 缺 ticker")
        if not topic.get("short_name"):
            i1_issues.append("company 缺 short_name")

    if not i1_issues:
        satisfied.append("I1")
    else:
        unmet.append({"id": "I1", "detail": "; ".join(i1_issues)})

    # ------------------------------------------------------------------ #
    # I2 · 定向                                                           #
    # ------------------------------------------------------------------ #
    i2_issues: list[str] = []

    thesis_v0_path = _variant_dir / "thesis_v0.md"
    if not thesis_v0_path.exists():
        i2_issues.append("thesis_v0.md 不存在")
    else:
        content = thesis_v0_path.read_text(encoding="utf-8", errors="replace")
        if not re.search(r"\bK\d+\b", content):
            i2_issues.append("thesis_v0 未含可证伪 K#（搜不到 K\\d 模式）")

    if not (_variant_dir / "decomposition_v0.md").exists():
        i2_issues.append("decomposition_v0.md 不存在")

    if not i2_issues:
        satisfied.append("I2")
    else:
        unmet.append({"id": "I2", "detail": "; ".join(i2_issues)})

    # ------------------------------------------------------------------ #
    # I3 · 路线                                                           #
    # ------------------------------------------------------------------ #
    i3_issues: list[str] = []

    if not (_variant_dir / "roadmap.yaml").exists():
        i3_issues.append("roadmap.yaml 不存在")

    if not (topic.get("search_terms") or []):
        i3_issues.append("search_terms 为空")

    if not i3_issues:
        satisfied.append("I3")
    else:
        unmet.append({"id": "I3", "detail": "; ".join(i3_issues)})

    # ------------------------------------------------------------------ #
    # I4 · 收料                                                           #
    # ------------------------------------------------------------------ #
    i4_issues: list[str] = []

    pending_fetch = pending_unfetched_todos(slug, variant)
    empty_undecided = empty_undecided_todos(slug, variant)

    if pending_fetch:
        tasks = [t.get("task", "?")[:40] for t in pending_fetch[:3]]
        suffix = f" (+ {len(pending_fetch) - 3} 条)" if len(pending_fetch) > 3 else ""
        i4_issues.append(
            f"{len(pending_fetch)} 条 todo 未有效尝试 (unattempted/error): "
            f"{', '.join(tasks)}{suffix}"
        )

    if empty_undecided:
        tasks = [t.get("task", "?")[:40] for t in empty_undecided[:3]]
        suffix = f" (+ {len(empty_undecided) - 3} 条)" if len(empty_undecided) > 3 else ""
        i4_issues.append(
            f"{len(empty_undecided)} 条 empty todo 待用户决策 (waived/will_collect): "
            f"{', '.join(tasks)}{suffix}"
        )

    if not i4_issues:
        satisfied.append("I4")
    else:
        unmet.append({"id": "I4", "detail": "; ".join(i4_issues)})

    # ------------------------------------------------------------------ #
    # I5 · 抽料                                                           #
    # ------------------------------------------------------------------ #
    i5_issues: list[str] = []

    unprocessed: list[dict] = []
    try:
        unprocessed = list_unprocessed(slug, variant)
    except Exception as exc:
        i5_issues.append(f"list_unprocessed 异常: {exc}")

    if unprocessed:
        names = [m.get("filename", m.get("id", "?"))[:35] for m in unprocessed[:3]]
        suffix = f" (+ {len(unprocessed) - 3} 份)" if len(unprocessed) > 3 else ""
        i5_issues.append(
            f"{len(unprocessed)} 份资料未处理: {', '.join(names)}{suffix}"
        )

    # findings index check (only relevant if there are materials)
    findings_index = _outputs_dir / "_findings_index.md"
    if not findings_index.exists() and not unprocessed:
        try:
            mats = read_manifest(slug, variant).get("materials", [])
            actionable = [m for m in mats if m.get("addresses") and
                          m.get("addresses") != ["scope"]]
            if actionable:
                i5_issues.append("_findings_index.md 不存在（有已处理资料但无索引）")
        except Exception:
            pass

    if not i5_issues:
        satisfied.append("I5")
    else:
        unmet.append({"id": "I5", "detail": "; ".join(i5_issues)})

    # ------------------------------------------------------------------ #
    # I6 · 合成                                                           #
    # ------------------------------------------------------------------ #
    i6_issues: list[str] = []

    primer_path = _outputs_dir / "00_primer.md"
    if not primer_path.exists():
        i6_issues.append("00_primer.md 不存在")
    else:
        try:
            gate = primer_quality_gate(slug, variant)
            if not gate.get("ok"):
                warnings = gate.get("warnings", [])
                i6_issues.append(
                    f"primer 未过深度门禁: {', '.join(str(w) for w in warnings[:3])}"
                )
        except Exception as exc:
            i6_issues.append(f"primer_quality_gate 异常: {exc}")

    case_key = _CASE_BY_TYPE.get(topic_type)
    if case_key and not (_outputs_dir / f"{case_key}.md").exists():
        i6_issues.append(f"{case_key}.md 不存在")

    sidecar = _SIDECAR_BY_TYPE.get(topic_type)
    if sidecar and not (_outputs_dir / sidecar).exists():
        i6_issues.append(f"sidecar {sidecar} 不存在")

    # thesis_v1+ existence check
    thesis_versions = _list_thesis_versions(_variant_dir)
    if not any(v >= 1 for v in thesis_versions):
        i6_issues.append("thesis_v1 不存在（合成后需升版为 Scheme C 全快照）")

    if not i6_issues:
        satisfied.append("I6")
    else:
        unmet.append({"id": "I6", "detail": "; ".join(i6_issues)})

    # ------------------------------------------------------------------ #
    # I7 · 评审                                                           #
    # ------------------------------------------------------------------ #
    i7_issues: list[str] = []

    verdict_data = get_critic_verdict(slug, variant)
    if not verdict_data or verdict_data.get("verdict") not in (
        "approve", "request-rewrite", "request-more"
    ):
        i7_issues.append(
            "critic_verdict 未设（需 set_critic_verdict 落评审结论）"
        )

    if not i7_issues:
        satisfied.append("I7")
    else:
        unmet.append({"id": "I7", "detail": "; ".join(i7_issues)})

    # ------------------------------------------------------------------ #
    # I8 · 监控                                                           #
    # ------------------------------------------------------------------ #
    i8_issues: list[str] = []

    monitoring_tier = topic.get("monitoring_tier")
    if monitoring_tier not in ("deep", "watch", "dormant"):
        i8_issues.append(
            f"monitoring_tier 未设或无效: {monitoring_tier!r} "
            f"（需 set_monitoring_tier 选 deep/watch/dormant）"
        )

    if not i8_issues:
        satisfied.append("I8")
    else:
        unmet.append({"id": "I8", "detail": "; ".join(i8_issues)})

    # ------------------------------------------------------------------ #
    # Compute arc (first unsatisfied invariant)                           #
    # ------------------------------------------------------------------ #
    arc = "done"
    for inv_id in _ALL_INV:
        if inv_id not in satisfied:
            arc = inv_id
            break

    # ------------------------------------------------------------------ #
    # Blockers (from I4 sources, surfaced for quick action)               #
    # ------------------------------------------------------------------ #
    blockers: list[dict] = []
    for t in pending_fetch:
        blockers.append({
            "type": "pending_unfetched",
            "task": t.get("task", ""),
            "fetch_status": t.get("fetch_status", ""),
            "priority": t.get("priority", ""),
            "addresses": t.get("addresses", []),
        })
    for t in empty_undecided:
        blockers.append({
            "type": "empty_undecided",
            "task": t.get("task", ""),
            "priority": t.get("priority", ""),
            "addresses": t.get("addresses", []),
        })

    # ------------------------------------------------------------------ #
    # Diagnostics (gap_detector精简快照)                                  #
    # ------------------------------------------------------------------ #
    try:
        diag = snapshot_gaps(slug, variant)
    except Exception as exc:
        diag = {"error": str(exc)}

    # ------------------------------------------------------------------ #
    # Prescan status                                                       #
    # ------------------------------------------------------------------ #
    try:
        prescan_info = get_current_prescan_status(slug, variant)
        prescan_status = prescan_info.get("status", "null")
    except Exception:
        prescan_status = "null"

    # ------------------------------------------------------------------ #
    # Floor violations (F3 check: mineru not started)                     #
    # ------------------------------------------------------------------ #
    floor_violations: list[str] = []
    try:
        manifest = read_manifest(slug, variant)
        for m in manifest.get("materials", []):
            if m.get("mineru_state") == "needs":
                floor_violations.append(f"F3: {m.get('filename', m.get('id'))} 待跑 mineru vlm")
    except Exception:
        pass

    # ------------------------------------------------------------------ #
    # Suggested next (simple rule templates)                               #
    # ------------------------------------------------------------------ #
    suggested_next = _suggest_next(arc, pending_fetch, empty_undecided, unprocessed)

    return {
        "topic": {
            "slug": slug,
            "variant": variant,
            "type": topic_type,
            "display_name": topic.get("display_name", ""),
            "stage": topic.get("stage", ""),
        },
        "arc": arc,
        "satisfied": satisfied,
        "unmet": unmet,
        "blockers": blockers,
        "diagnostics": diag,
        "prescan_status": prescan_status,
        "suggested_next": suggested_next,
        "floor": floor_violations,
    }


# --------------------------------------------------------------------------- #
# 辅助函数                                                                     #
# --------------------------------------------------------------------------- #

def _list_thesis_versions(variant_dir: Path) -> list[int]:
    """列出 variant 目录下所有 thesis_v{N}.md 的版本号，升序。"""
    versions = []
    for p in variant_dir.glob("thesis_v*.md"):
        m = re.match(r"thesis_v(\d+)\.md$", p.name)
        if m:
            try:
                versions.append(int(m.group(1)))
            except ValueError:
                pass
    return sorted(versions)


def _suggest_next(
    arc: str,
    pending_fetch: list[dict],
    empty_undecided: list[dict],
    unprocessed: list[dict],
) -> str:
    if arc == "done":
        return "所有不变量已满足 → 进入监控循环（I8 daily-monitor）"
    if arc == "I1":
        return "补全 topic.yaml 基本字段 (type / question / search_terms / ticker+short_name) → 满足 I1"
    if arc == "I2":
        return "写 thesis_v0.md（含 ≥1 可证伪 K#）+ decomposition_v0.md → 满足 I2"
    if arc == "I3":
        return "建 roadmap.yaml (K# → L4 狩猎清单) + 补 search_terms → 满足 I3"
    if arc == "I4":
        parts = []
        if pending_fetch:
            n = len(pending_fetch)
            parts.append(f"处置 {n} 条 unattempted/error todos（prism search + mark_todo_fetch）")
        if empty_undecided:
            n = len(empty_undecided)
            parts.append(f"AskUserQuestion 决策 {n} 条 empty todos（waived/will_collect）")
        return " + ".join(parts) + " → 满足 I4" if parts else "核对 todos fetch_status → 满足 I4"
    if arc == "I5":
        if unprocessed:
            n = len(unprocessed)
            ids = [m.get("id", "?") for m in unprocessed[:3]]
            more = f" (+ {n - 3} 份)" if n > 3 else ""
            return f"抽 {', '.join(ids)}{more} ({n} 份) → mark_processed + build_findings_index → 满足 I5"
        return "重建 findings index (build_findings_index) → 满足 I5"
    if arc == "I6":
        return "写 primer + case + sidecar + thesis_v1 (Scheme C 全快照) → set_output_status fresh → 满足 I6"
    if arc == "I7":
        return "跑 critic 评审 → set_critic_verdict(approve/request-rewrite/request-more) → 满足 I7"
    if arc == "I8":
        return "set_monitoring_tier(deep/watch/dormant) → 满足 I8"
    return f"处理 {arc}"

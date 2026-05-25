"""Create, read, and update topic.yaml files. Zero LLM calls."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

PRISM_ROOT = Path(__file__).resolve().parent.parent

# 基础输出 keys（所有 type 都有）
_BASE_OUTPUT_KEYS = [
    "01_business_panorama",
    "02_cycle_positioning",
    "03_narrative_ecology",
    "04_implied_expectations",
    "05_historical_mirrors",
    "06_risk_blindspots",
    "07_decision_kit",
    "08_living_feed",
]

# 按 topic.type 的输出 keys
_INDUSTRY_EXTRA_KEYS = ["09_industry_to_arenas"]
_ARENA_EXTRA_KEYS = ["10_peer_matrix"]
_COMPANY_EXTRA_KEYS = ["00_quality_screen"]

_DEFAULT_OUTPUT_STATE = {
    "version": 0, "last_updated": None, "status": "pending", "data_freshness": None,
    # 04-synthesize 写入：本 output 上次合成时引用的 manifest mat_ids。
    # list_affected_outputs 据此判定有无新材料，决定是否要重写本 output。
    "referenced_mat_ids": None,
    # 单份产出失败时由 set_output_error 写入：{"at": iso_ts, "message": str}。
    # 成功调 set_output_referenced_mats 时会自动清空，做到"再跑一遍就抹掉错误"。
    "last_error": None,
}


def _infer_market(ticker: str, geo: str) -> str:
    """推断股票代码所属市场。CN 股根据首位数推断，其他默认 US。

    若 ticker 是旧格式（SZSE_300073 / SHA_688499 / SSE_600519），
    剥离前缀后再推断，避免落入兜底 US 分支。
    """
    if not ticker:
        return ""
    if "_" in ticker:
        ticker = ticker.split("_", 1)[1]
    if geo != "CN":
        return "US"
    if ticker[:1] in ("6", "9", "5"):
        return "SSE"
    elif ticker[:1] in ("0", "3"):
        return "SZSE"
    elif ticker[:1] == "8":
        return "BSE"
    return "US"


def _outputs_for_type(topic_type: str) -> list[str]:
    if topic_type == "industry":
        return _BASE_OUTPUT_KEYS + _INDUSTRY_EXTRA_KEYS
    elif topic_type == "arena":
        return _BASE_OUTPUT_KEYS + _ARENA_EXTRA_KEYS
    elif topic_type == "company":
        return ["00_quality_screen"] + _BASE_OUTPUT_KEYS
    else:
        return _BASE_OUTPUT_KEYS


def next_stage(topic_type: str, current_stage: str) -> str | None:
    if current_stage in ("done", "quarantined"):
        return None

    # reopen stage：thesis 升版后 reverse-check 发现 roadmap 漏 K#，回到补 material
    if current_stage == "01-roadmap-reopen":
        return "02-gather-materials"

    if topic_type == "industry":
        flow = [
            "00-init",
            "01-roadmap",
            "02-gather-materials",
            "03-extracting",
            "04-synthesizing",
            "09-arena-shortlist",
            "done",
        ]
    elif topic_type == "arena":
        flow = [
            "00-init",
            "01-roadmap",
            "02-gather-materials",
            "03-extracting",
            "04-synthesizing",
            "10-peer-matrix",
            "done",
        ]
    elif topic_type == "company":
        # 修 7: 04 后强制走 critic-review；verdict='approve' 才到 done
        flow = [
            "00-init",
            "01-roadmap",
            "02-gather-materials",
            "03-extracting",
            "00-quality-screen",
            "04-synthesizing",
            "04-post-synthesis",
            "05-critic-review",
            "done",
        ]
    else:
        flow = [
            "00-init",
            "01-roadmap",
            "02-gather-materials",
            "03-extracting",
            "04-synthesizing",
            "04-post-synthesis",
            "05-critic-review",
            "done",
        ]

    try:
        idx = flow.index(current_stage)
        if idx + 1 < len(flow):
            return flow[idx + 1]
        return None
    except ValueError:
        for stage in flow:
            if stage > current_stage:
                return stage
        return None


def _topics_dir() -> Path:
    return PRISM_ROOT / "topics"


def _topic_path(slug: str, variant: str) -> Path:
    if not variant:
        raise ValueError("必须显式指定 variant，例如 'sonnet' 或 'qwen3.6-plus'")
    return _topics_dir() / slug / variant / "topic.yaml"


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_topic(
    slug: str,
    display_name: str,
    topic_type: str,
    question: str,
    geo: str,
    depth: str,
    variant: str,
    ticker: str | None = None,
    parent_topic: str | None = None,
    concepts: list[str] | None = None,
    monitoring_tier: str = "dormant",
) -> Path:
    path = _topic_path(slug, variant)
    if path.exists():
        raise FileExistsError(f"Topic already exists: {slug}/{variant}")
    scope = {
        "geo": geo,
        "question": question,
        "depth": depth,
    }
    if ticker:
        scope["ticker"] = ticker
        scope["market"] = _infer_market(ticker, geo)
    data = {
        "slug": slug,
        "display_name": display_name,
        "type": topic_type,
        "created": _now_iso(),
        "status": "active",
        "stage": "00-init",
        "parent_topic": parent_topic,
        "monitoring_tier": monitoring_tier,
        "concepts": concepts or [],
        "scope": scope,
        "outputs_state": {key: dict(_DEFAULT_OUTPUT_STATE) for key in _outputs_for_type(topic_type)},
        "parent_materials": [],
        "next_actions": ["运行 workflow 01-build-roadmap"],
        "user_todos": [],
        "monitoring": {"enabled": False, "cadence": "daily"},
    }
    _write_yaml(path, data)
    (path.parent / "outputs").mkdir(exist_ok=True)
    (path.parent.parent / "inbox").mkdir(exist_ok=True)
    return path


def read_topic(slug: str, variant: str) -> dict:
    path = _topic_path(slug, variant)
    if not path.exists():
        raise FileNotFoundError(f"Topic not found: {slug}/{variant}")
    data = _read_yaml(path)
    data.setdefault("parent_topic", None)
    data.setdefault("monitoring_tier", "dormant")
    data.setdefault("concepts", [])
    # 修 7: critic-review verdict 状态。set_critic_verdict 写入，next_stage 决定不依赖此字段
    # （verdict-驱动的跳转在 workflow 05 里用 set_stage 显式做）。
    data.setdefault("critic", None)
    if "outputs_state" in data:
        for key, state in data["outputs_state"].items():
            state.setdefault("data_freshness", None)
            state.setdefault("referenced_mat_ids", None)
            state.setdefault("last_error", None)
    if "user_todos" in data and data["user_todos"]:
        try:
            data["user_todos"] = [_normalize_todo(t) for t in data["user_todos"]]
        except Exception:
            pass
    return data


def update_topic(slug: str, variant: str, **fields) -> None:
    data = read_topic(slug, variant)
    data.update(fields)
    _write_yaml(_topic_path(slug, variant), data)


def set_stage(slug: str, stage: str, variant: str) -> None:
    update_topic(slug, variant, stage=stage)


def set_output_status(slug: str, output_key: str, status: str, variant: str, version: int | None = None) -> None:
    data = read_topic(slug, variant)
    entry = data["outputs_state"].setdefault(output_key, dict(_DEFAULT_OUTPUT_STATE))
    entry["status"] = status
    entry["last_updated"] = _now_iso()
    if version is not None:
        entry["version"] = version
    _write_yaml(_topic_path(slug, variant), data)


def set_output_referenced_mats(slug: str, output_key: str, mat_ids: list[str], variant: str) -> None:
    """记录某 output 本次合成所引用的 manifest mat_ids（去重排序）。
    04-synthesize 写完一份 output 后调用，让下次跑 list_affected_outputs 能判定增量。
    成功调用会清空 last_error——再跑一遍即抹掉之前的失败记录。
    """
    data = read_topic(slug, variant)
    entry = data["outputs_state"].setdefault(output_key, dict(_DEFAULT_OUTPUT_STATE))
    entry["referenced_mat_ids"] = sorted(set(mat_ids))
    entry["last_updated"] = _now_iso()
    entry["last_error"] = None
    _write_yaml(_topic_path(slug, variant), data)


def set_output_error(slug: str, output_key: str, message: str, variant: str) -> None:
    """标记某 output 本次合成失败。04-synthesize 单份产出 except 时调用，
    让其余 10 份继续跑（修 9: workflow resume）。下次再跑该 output 成功后
    set_output_referenced_mats 会清空此字段。
    """
    data = read_topic(slug, variant)
    entry = data["outputs_state"].setdefault(output_key, dict(_DEFAULT_OUTPUT_STATE))
    entry["last_error"] = {"at": _now_iso(), "message": str(message)[:500]}
    _write_yaml(_topic_path(slug, variant), data)


def list_failed_outputs(slug: str, variant: str) -> list[dict]:
    """返回所有有 last_error 的 output（用于"哪些产出需要重跑"）。"""
    data = read_topic(slug, variant)
    out = []
    for key, state in (data.get("outputs_state") or {}).items():
        err = state.get("last_error")
        if err:
            out.append({"output_key": key, "last_error": err})
    return out


_VALID_CRITIC_VERDICTS = ("approve", "request-rewrite", "request-more")


def set_critic_verdict(
    slug: str, variant: str, verdict: str, summary: str = "", thesis_version: int | None = None
) -> dict:
    """workflow 05-critic-review Step 7 调用。记录评审结论 + 自动按 verdict 跳转 stage。

    verdict:
      - 'approve'         → set_stage('done')      研究完结，可进 06-daily-monitor
      - 'request-rewrite' → set_stage('04-synthesizing')  04 部分 output 需要重写
      - 'request-more'    → set_stage('02-gather-materials')  缺 material，回 02

    返回写入的 critic dict（含 next_stage 字段供主 agent 汇报）。
    """
    if verdict not in _VALID_CRITIC_VERDICTS:
        raise ValueError(
            f"Invalid verdict: {verdict!r}. Must be one of {_VALID_CRITIC_VERDICTS}"
        )
    data = read_topic(slug, variant)
    critic = {
        "verdict": verdict,
        "summary": summary,
        "at": _now_iso(),
        "thesis_version": thesis_version,
    }
    next_st = {
        "approve": "done",
        "request-rewrite": "04-synthesizing",
        "request-more": "02-gather-materials",
    }[verdict]
    critic["next_stage"] = next_st
    data["critic"] = critic
    data["stage"] = next_st
    _write_yaml(_topic_path(slug, variant), data)
    return critic


def get_critic_verdict(slug: str, variant: str) -> dict | None:
    """返回当前 critic 状态；未评审过返回 None。"""
    return read_topic(slug, variant).get("critic")


def set_next_actions(slug: str, actions: list[str], variant: str) -> None:
    update_topic(slug, variant, next_actions=actions)


_VALID_INFO_TIERS = ("public", "half_public", "hard")
_VALID_PRIORITIES = ("P0", "P1", "P2")
_VALID_TODO_STATUSES = ("pending", "in_progress", "done")

# address 格式: 裸 'K1' 或带事件锚 'K1@2026Q2-earnings'。事件锚解决 K# 粒度过粗问题
# （参 feedback_addresses_granularity）。匹配规则：
#  - todo address 裸 'K1' → 任何同 key 的 mat address 都覆盖（向后兼容）
#  - todo address 'K1@evt' → mat address 必须也是 'K1@evt' 才覆盖（严格事件匹配）
#  - mat  address 'K1@evt' 仅覆盖同事件的 todo；裸 K1 todo 仍接受（视为通配）
_ADDR_RE = re.compile(r"^[KQ]\d+(@[A-Za-z0-9_\-]+)?$")


def _addr_key(addr: str) -> str:
    """提取 address 的 K#/Q# 部分（去掉 @event 后缀）。"""
    return addr.split("@", 1)[0] if isinstance(addr, str) else ""


def _addr_event(addr: str) -> str | None:
    """提取 address 的 @event 部分；裸 K# 返回 None。"""
    if isinstance(addr, str) and "@" in addr:
        return addr.split("@", 1)[1]
    return None


def addresses_match(todo_addrs: list[str], mat_addrs: list[str]) -> bool:
    """判定 mat 是否覆盖 todo 的某个 address。规则见 _ADDR_RE 注释。

    返回 True 当且仅当存在 (t, m) ∈ todo×mat 满足：
      key(t) == key(m) 且 (event(t) is None 或 event(t) == event(m))
    """
    for t in todo_addrs or []:
        tk, te = _addr_key(t), _addr_event(t)
        if not tk:
            continue
        for m in mat_addrs or []:
            mk, me = _addr_key(m), _addr_event(m)
            if tk != mk:
                continue
            if te is None or te == me:
                return True
    return False


def _normalize_todo(item) -> dict:
    """接受 str 或 dict，规范化为统一 schema。

    str → {task: str, info_tier: 'public', priority: 'P1', addresses: [], status: 'pending'}
    dict → 校验字段，缺省值补全
    可选扩展字段：covered_by (list[mat_id])、coverage_note (str)
    """
    if isinstance(item, str):
        return {
            "task": item,
            "priority": "P1",
            "info_tier": "public",
            "addresses": [],
            "source_hint": "",
            "status": "pending",
        }
    if not isinstance(item, dict) or "task" not in item:
        raise ValueError(f"todo 必须是 str 或含 task 字段的 dict，得到: {item!r}")
    tier = item.get("info_tier", "public")
    if tier not in _VALID_INFO_TIERS:
        raise ValueError(f"info_tier 必须是 {_VALID_INFO_TIERS}，得到: {tier!r}")
    priority = item.get("priority", "P1")
    if priority not in _VALID_PRIORITIES:
        raise ValueError(f"priority 必须是 {_VALID_PRIORITIES}，得到: {priority!r}")
    status = item.get("status", "pending")
    if status not in _VALID_TODO_STATUSES:
        raise ValueError(f"status 必须是 {_VALID_TODO_STATUSES}，得到: {status!r}")
    addresses = item.get("addresses", [])
    if not isinstance(addresses, list):
        raise ValueError(f"addresses 必须是 list，得到: {addresses!r}")
    for a in addresses:
        if not isinstance(a, str) or not _ADDR_RE.match(a):
            raise ValueError(
                f"address 格式必须是 'K#' / 'Q#' 或 'K#@event-slug'（event-slug ∈ [A-Za-z0-9_-]），得到: {a!r}"
            )
    out = {
        "task": item["task"],
        "priority": priority,
        "info_tier": tier,
        "addresses": addresses,
        "source_hint": item.get("source_hint", ""),
        "status": status,
    }
    covered_by = item.get("covered_by")
    if covered_by:
        if not isinstance(covered_by, list):
            raise ValueError(f"covered_by 必须是 list[str]，得到: {covered_by!r}")
        out["covered_by"] = list(covered_by)
    coverage_note = item.get("coverage_note")
    if coverage_note:
        out["coverage_note"] = str(coverage_note)
    archive_candidate = item.get("archive_candidate")
    if archive_candidate:
        out["archive_candidate"] = str(archive_candidate)
    return out


def set_user_todos(slug: str, todos: list, variant: str) -> None:
    """接受 list[str | dict]，每项规范化为统一 schema 后写入。"""
    normalized = [_normalize_todo(t) for t in todos]
    update_topic(slug, variant, user_todos=normalized)


def thesis_coverage(slug: str, variant: str, expected_keys: list[str]) -> dict:
    """对给定的一组期望 keys（如 K1..K5），统计每个 key 被多少 todo 攻打。

    返回：{
        'by_key': {'K1': [todo, ...], 'K2': [], ...},  # 每个 key 对应的 todo 列表（按出现顺序）
        'uncovered': ['K3', 'K5'],                      # 没有任何 todo 引用的 key
        'covered': ['K1', 'K2', 'K4'],
        'coverage_pct': 60,
    }
    """
    data = read_topic(slug, variant)
    todos = data.get("user_todos", []) or []
    by_key: dict[str, list] = {k: [] for k in expected_keys}
    for t in todos:
        if not isinstance(t, dict):
            continue
        # 支持 K1 和 K1@event 两种格式：都映射回 K1 桶
        for addr in t.get("addresses", []) or []:
            k = _addr_key(addr)
            if k in by_key:
                by_key[k].append(t)
    uncovered = [k for k in expected_keys if not by_key[k]]
    covered = [k for k in expected_keys if by_key[k]]
    pct = round(100 * len(covered) / len(expected_keys)) if expected_keys else 0
    return {
        "by_key": by_key,
        "uncovered": uncovered,
        "covered": covered,
        "coverage_pct": pct,
    }


def update_user_todo_status(
    slug: str,
    variant: str,
    task_substring: str,
    status: str,
    covered_by: list[str] | None = None,
    coverage_note: str | None = None,
) -> None:
    """根据 task 字段子串匹配，更新对应 todo 的 status。

    可选参数：
      covered_by: 追加到 todo.covered_by 的 material id 列表（去重合并）
      coverage_note: 覆盖原 coverage_note；常用于 web-search 自动覆盖说明
    """
    if status not in _VALID_TODO_STATUSES:
        raise ValueError(f"status 必须是 {_VALID_TODO_STATUSES}")
    data = read_topic(slug, variant)
    todos = data.get("user_todos", [])
    hit = False
    for t in todos:
        if isinstance(t, dict) and task_substring in t.get("task", ""):
            t["status"] = status
            if covered_by:
                existing = set(t.get("covered_by") or [])
                t["covered_by"] = sorted(existing | set(covered_by))
            if coverage_note:
                t["coverage_note"] = coverage_note
            hit = True
    if not hit:
        raise ValueError(f"未找到包含 {task_substring!r} 的 todo")
    update_topic(slug, variant, user_todos=todos)


def set_concepts(slug: str, concepts: list[str], variant: str) -> None:
    update_topic(slug, variant, concepts=concepts)


def set_monitoring_tier(slug: str, tier: str, variant: str) -> None:
    if tier not in ("deep", "watch", "dormant"):
        raise ValueError(f"Invalid tier: {tier}, must be deep/watch/dormant")
    update_topic(slug, variant, monitoring_tier=tier)


def set_thesis(slug: str, variant: str, version: int, summary: str, stage_set_at: str) -> dict | None:
    """记录 LLM 在特定阶段的 thesis 表态。完整 markdown 写到 thesis_v{N}.md。

    summary: 一句话核心 thesis（≤120 字），用于 yaml/web 列表展示
    stage_set_at: thesis 表态时的研究阶段（如 01-roadmap-pending、04-synthesizing）

    副作用：升版后自动跑 reverse-check（version>=1 且 roadmap 存在时）：
      若 thesis 的 K# 在 roadmap.L4/material 中未闭环，自动写 "roadmap 需补 Kx" todo，
      并把 stage 翻成 '01-roadmap-reopen'。返回 reverse-check 结果（含 newly_added_todos）。
      version=0 或 roadmap 未建时跳过。
    """
    data = read_topic(slug, variant)
    thesis = data.setdefault("thesis", {"current_version": None, "last_updated": None, "history": []})
    thesis["current_version"] = version
    thesis["last_updated"] = _now_iso()
    thesis["history"].append({
        "version": version,
        "stage_set_at": stage_set_at,
        "set_at": _now_iso(),
        "summary": summary,
    })
    _write_yaml(_topic_path(slug, variant), data)

    if version >= 1:
        # 先做 K# 回收（标记上版有本版无的 K#），再做 reverse-check（标记本版缺的 K#）
        archived = mark_outdated_ks(slug, variant, version)
        rev = reverse_check_roadmap_coverage(slug, variant, version)
        if isinstance(rev, dict):
            rev["outdated_ks_marked"] = archived
        return rev
    return None


def mark_outdated_ks(slug: str, variant: str, version: int) -> list[str]:
    """对比 thesis_v{version} 与 thesis_v{version-1} 的 K#，找出上版有本版无的（被 thesis 收回）。
    给 active user_todos（addresses 含该 K#）加 archive_candidate 标记，让用户/UI 知道这条已过时。

    返回被标记的 outdated K# 列表（即便没有匹配 todo 也返回，便于诊断）。
    finding / roadmap entry 暂不自动改（避免覆盖手动编辑）；后续考虑加 lint 提醒。
    """
    if version < 1:
        return []
    from . import outputs as outputs_io
    curr_ks = set(outputs_io.extract_killer_questions(slug, variant, version))
    prev_ks = set(outputs_io.extract_killer_questions(slug, variant, version - 1))
    outdated = sorted(prev_ks - curr_ks, key=lambda k: int(k[1:]) if k[1:].isdigit() else 999)
    if not outdated:
        return []
    data = read_topic(slug, variant)
    todos = data.get("user_todos") or []
    note = f"thesis v{version} 已移除该 K#（上版 K# 集合：{sorted(prev_ks)}，本版：{sorted(curr_ks)}）"
    touched = False
    for t in todos:
        if not isinstance(t, dict) or t.get("status") == "done":
            continue
        addrs_keys = {_addr_key(a) for a in (t.get("addresses") or [])}
        if addrs_keys & set(outdated):
            t["archive_candidate"] = note
            touched = True
    if touched:
        update_topic(slug, variant, user_todos=todos)
    return outdated


def reverse_check_roadmap_coverage(slug: str, variant: str, version: int) -> dict:
    """对 thesis_v{version} 跑 roadmap 覆盖反查；缺口写 todo + 翻 stage。

    返回：{
        'triggered': bool,                    # 是否真的执行了反查（roadmap 存在且有 K#）
        'ok': bool,                            # 全部闭环
        'uncovered_in_l4': [...],
        'uncovered_in_material': [...],
        'newly_added_todos': [task, ...],     # 本次新增的 todo task 字符串
        'stage_flipped_to': str | None,        # 若翻了 stage 则记录目标
    }
    """
    from . import outputs as outputs_io  # 延迟引入避免循环
    cov = outputs_io.validate_roadmap_thesis_coverage(slug, variant, version)
    if not cov.get("roadmap_exists") or not cov.get("thesis_ks"):
        return {
            "triggered": False, "ok": cov.get("ok", False),
            "uncovered_in_l4": cov.get("uncovered_in_l4", []),
            "uncovered_in_material": cov.get("uncovered_in_material", []),
            "newly_added_todos": [], "stage_flipped_to": None,
        }
    if cov["ok"]:
        return {
            "triggered": True, "ok": True,
            "uncovered_in_l4": [], "uncovered_in_material": [],
            "newly_added_todos": [], "stage_flipped_to": None,
        }

    uncovered = sorted(
        set(cov["uncovered_in_l4"]) | set(cov["uncovered_in_material"]),
        key=lambda k: int(k[1:]) if k[1:].isdigit() else 999,
    )
    data = read_topic(slug, variant)
    todos = list(data.get("user_todos") or [])

    # 已存在的 active reverse-check todo（pending/in_progress）按 K# key 去重（忽略 @event）；
    # status=done 视为真闭环，若该 K# 后续又缺，下次允许重新写新 todo 再提醒。
    existing_reopen = set()
    for t in todos:
        if not isinstance(t, dict):
            continue
        hint = (t.get("source_hint") or "")
        if "reverse-check" in hint and t.get("status") != "done":
            for a in (t.get("addresses") or []):
                existing_reopen.add(_addr_key(a))

    added: list[str] = []
    for k in uncovered:
        if k in existing_reopen:
            continue
        in_l4 = k in cov["uncovered_in_l4"]
        in_mat = k in cov["uncovered_in_material"]
        miss_parts = []
        if in_l4:
            miss_parts.append("L4-hunting")
        if in_mat:
            miss_parts.append("tier-material")
        miss_str = " + ".join(miss_parts)
        task = f"roadmap 需补 {k}：thesis v{version} 升版后 {k} 在 {miss_str} 中未闭环"
        todos.append({
            "task": task,
            "priority": "P1",
            "info_tier": "public",
            "addresses": [k],
            "source_hint": f"auto-generated by set_thesis reverse-check (v{version})",
            "status": "pending",
        })
        added.append(task)

    if added:
        update_topic(slug, variant, user_todos=todos)

    stage_flipped = None
    # 仅当当前 stage 已过 01-roadmap（说明确实是后期升版漏补）才翻
    current_stage = data.get("stage", "")
    if current_stage not in ("00-init", "01-roadmap", "01-roadmap-reopen", "quarantined"):
        set_stage(slug, "01-roadmap-reopen", variant)
        stage_flipped = "01-roadmap-reopen"

    return {
        "triggered": True, "ok": False,
        "uncovered_in_l4": cov["uncovered_in_l4"],
        "uncovered_in_material": cov["uncovered_in_material"],
        "newly_added_todos": added,
        "stage_flipped_to": stage_flipped,
    }


def set_data_freshness(slug: str, output_key: str, freshness: str, variant: str) -> None:
    data = read_topic(slug, variant)
    entry = data["outputs_state"].setdefault(output_key, dict(_DEFAULT_OUTPUT_STATE))
    entry["data_freshness"] = freshness
    entry["last_updated"] = _now_iso()
    _write_yaml(_topic_path(slug, variant), data)


def list_variants(slug: str) -> list[str]:
    """List all model variant names under a topic slug."""
    slug_dir = _topics_dir() / slug
    if not slug_dir.is_dir():
        return []
    variants = []
    for sub in slug_dir.iterdir():
        if sub.is_dir() and (sub / "topic.yaml").is_file():
            variants.append(sub.name)
    return sorted(variants)


def list_topics(variant: str | None = None) -> list[dict]:
    """List all topics.

    Without variant: list all variants from all topics.
    With variant: only scan that variant under each topic slug.
    """
    root = _topics_dir()
    if not root.exists():
        return []
    results = []
    for slug_dir in root.iterdir():
        if not slug_dir.is_dir():
            continue
        if variant:
            path = slug_dir / variant / "topic.yaml"
            if path.is_file():
                try:
                    topic = _read_yaml(path)
                    topic["variant"] = variant
                    results.append(topic)
                except Exception:
                    pass
        else:
            for sub in slug_dir.iterdir():
                if sub.is_dir() and (sub / "topic.yaml").is_file():
                    try:
                        topic = _read_yaml(sub / "topic.yaml")
                        topic["variant"] = sub.name
                        results.append(topic)
                    except Exception:
                        pass
    results.sort(key=lambda t: t.get("created", ""), reverse=True)
    return results


def get_parent_materials_dir(slug: str, variant: str) -> Path | None:
    """If this topic has a parent_topic, return the parent's shared materials directory."""
    try:
        topic = read_topic(slug, variant)
        parent = topic.get("parent_topic")
        if parent:
            return _topics_dir() / parent / "materials"
    except Exception:
        pass
    return None


def list_parent_materials(slug: str, variant: str) -> list[str]:
    """List material filenames from the parent topic's materials directory."""
    parent_dir = get_parent_materials_dir(slug, variant)
    if parent_dir and parent_dir.is_dir():
        return sorted([p.name for p in parent_dir.iterdir() if p.is_file()])
    return []


def set_parent_materials(slug: str, variant: str, items: list[dict]) -> None:
    """Set parent_materials field on topic.

    Each item: {parent_slug, parent_variant (optional, defaults to current),
    mat_id, addresses (list[str], optional), note (optional)}.
    Idempotent: full replacement.
    """
    path = _topic_path(slug, variant)
    data = _read_yaml(path)
    cleaned = []
    for it in items:
        entry = {
            "parent_slug": it["parent_slug"],
            "parent_variant": it.get("parent_variant", variant),
            "mat_id": it["mat_id"],
        }
        if it.get("addresses"):
            entry["addresses"] = list(it["addresses"])
        if it.get("note"):
            entry["note"] = it["note"]
        cleaned.append(entry)
    data["parent_materials"] = cleaned
    _write_yaml(path, data)


def add_parent_material(
    slug: str,
    variant: str,
    parent_slug: str,
    mat_id: str,
    addresses: list[str] | None = None,
    note: str | None = None,
    parent_variant: str | None = None,
) -> None:
    """Append a single parent material reference (idempotent on mat_id)."""
    path = _topic_path(slug, variant)
    data = _read_yaml(path)
    items = data.get("parent_materials") or []
    items = [x for x in items if x.get("mat_id") != mat_id]
    entry = {
        "parent_slug": parent_slug,
        "parent_variant": parent_variant or variant,
        "mat_id": mat_id,
    }
    if addresses:
        entry["addresses"] = list(addresses)
    if note:
        entry["note"] = note
    items.append(entry)
    data["parent_materials"] = items
    _write_yaml(path, data)


def find_child_topics(parent_slug: str, variant: str | None = None) -> list[dict]:
    """Find all topics whose parent_topic matches parent_slug."""
    children = []
    for t in list_topics(variant=variant):
        if t.get("parent_topic") == parent_slug:
            children.append(t)
    return children


def baseline_knowledge_path(slug: str, variant: str) -> Path:
    return _topic_path(slug, variant).parent / "baseline_knowledge.md"


def read_baseline_knowledge(slug: str, variant: str) -> str | None:
    """Return the baseline knowledge markdown content, or None if not written yet."""
    p = baseline_knowledge_path(slug, variant)
    if not p.is_file():
        return None
    return p.read_text(encoding="utf-8")


def has_baseline_knowledge(slug: str, variant: str) -> bool:
    return baseline_knowledge_path(slug, variant).is_file()
"""宏观层评估快照（regime_eval_log.yaml）的零-LLM CRUD + diff + 重估简报组装。

评估快照是「输入→判断」可溯源的脊梁：每次（重）写 regime_read 时，LLM 经 append_evaluation
落一条 evaluation（input_snapshot 列全所有输入 + conclusions 按结论挂输入）。之后 diff/简报
全由本模块零-LLM 派生。判断永远人在对话里触发，本模块不含任何 LLM 调用。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from prism.scripts import macro_registry as reg

_PRISM_ROOT = Path(__file__).resolve().parent.parent

VALID_ROLE = ("load_bearing", "confirming", "background")

NUMERIC_DIRECTIONS = ("up", "down", "flat", "up_or_flat", "down_or_flat")


def _valid_expected_words() -> set:
    """合法 expected 方向词：数值型 + 全部立场轴方向词（复用 registry 单一真相）。"""
    words = set(NUMERIC_DIRECTIONS)
    for pair in reg.STANCE_DIRECTION.values():
        words.update(pair)
    return words


def _log_path(slug: str, variant: str) -> Path:
    if not variant:
        raise ValueError("必须显式指定 variant")
    return _PRISM_ROOT / "topics" / slug / variant / "outputs" / "regime_eval_log.yaml"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def read_eval_log(slug: str, variant: str) -> dict:
    """读评估日志；缺文件返回空骨架（不抛，让 web 优雅显示"未生成首份快照"）。"""
    path = _log_path(slug, variant)
    if not path.exists():
        return {"slug": slug, "variant": variant, "evaluations": [], "reeval_pending": None}
    data = _read_yaml(path)
    data.setdefault("evaluations", [])
    data.setdefault("reeval_pending", None)
    return data


def latest_evaluation(slug: str, variant: str) -> dict | None:
    evals = read_eval_log(slug, variant).get("evaluations") or []
    return evals[-1] if evals else None


def _validate_evaluation(evaluation: dict, input_names: set) -> list:
    """校验一条 evaluation 的不变量。返回错误列表（空=通过）。"""
    errors = []
    snap = evaluation.get("input_snapshot") or []
    snap_names = set()
    for i, s in enumerate(snap):
        nm = s.get("name")
        if nm is None:                    # 漏 name 键 → 不让 None 混入名册（否则悬空检查失灵）
            errors.append(f"input_snapshot[{i}] 缺 name 键")
        else:
            snap_names.add(nm)
    missing = input_names - snap_names
    if missing:
        errors.append(f"input_snapshot 漏列输入: {sorted(missing)}")
    valid_dirs = _valid_expected_words()
    snap_by_name = {s.get("name"): s for s in snap if s.get("name") is not None}
    for c in evaluation.get("conclusions") or []:
        cid = c.get("id", "<无 id>")
        for b in c.get("based_on") or []:
            inp = b.get("input")
            if inp is None:               # 漏 input 键 → 显式拒，不靠 None 是否在名册里碰运气
                errors.append(f"[{cid}] based_on 缺 input 键")
            elif inp not in snap_names:
                errors.append(f"[{cid}] based_on 悬空引用: {inp!r} 不在 input_snapshot")
            if b.get("role") not in VALID_ROLE:
                errors.append(f"[{cid}] role 非法: {b.get('role')!r}")
            exp = b.get("expected")
            if exp is not None and exp not in valid_dirs:
                errors.append(f"[{cid}] expected 非法方向词: {exp!r}")
            if b.get("role") == "load_bearing" and exp is None and inp is not None:
                row = snap_by_name.get(inp) or {}
                has_numeric = isinstance(row.get("value"), (int, float))
                has_stance = row.get("stance") is not None
                if has_numeric or has_stance:
                    errors.append(f"[{cid}] load_bearing 边 {inp!r} 缺 expected 方向预测")
    return errors


def append_evaluation(slug: str, variant: str, evaluation: dict) -> int:
    """追加一条 evaluation（校验不变量后落盘，version 自增，清 reeval_pending）。零 LLM。

    evaluation: {evaluated_at?, note?, input_snapshot:[{name,value,as_of,used}], conclusions:[...]}
    校验失败抛 ValueError，不落盘（保持快照可信）。
    """
    registry = reg.read_registry(slug, variant)
    input_names = {e["name"] for e in registry.get("inputs") or []}
    errors = _validate_evaluation(evaluation, input_names)
    if errors:
        raise ValueError("评估快照不变量校验失败:\n" + "\n".join(errors))
    log = read_eval_log(slug, variant)
    version = len(log["evaluations"]) + 1
    entry = {"version": version, "evaluated_at": evaluation.get("evaluated_at") or _now_iso()}
    if evaluation.get("note"):
        entry["note"] = evaluation["note"]
    entry["input_snapshot"] = evaluation.get("input_snapshot") or []
    entry["conclusions"] = evaluation.get("conclusions") or []
    log["evaluations"].append(entry)
    log["reeval_pending"] = None
    log["slug"], log["variant"], log["updated"] = slug, variant, _now_iso()
    _write_yaml(_log_path(slug, variant), log)
    return version


def conclusion_labels(slug: str, variant: str) -> dict:
    """最近评估里 {结论 id: 中文 label}；无评估 / 无 label 的项不收 → {}（调用方回落 id）。"""
    latest = latest_evaluation(slug, variant)
    if not latest:
        return {}
    out = {}
    for c in latest.get("conclusions") or []:
        cid, label = c.get("id"), c.get("label")
        if cid and label:
            out[cid] = label
    return out


def snapshot_inputs(slug: str, variant: str) -> list:
    """枚举全部 registry 输入，组 append_evaluation 的 input_snapshot 骨架（零 LLM）。

    返回 [{name, value, as_of, used:False}]，policy 项另带 stance。used 默认 False，
    由 record_evaluation 据 conclusions.based_on 标 True。消除 headless 手工列全 ~114 条的漏列面。
    """
    registry = reg.read_registry(slug, variant)
    out = []
    for e in registry.get("inputs") or []:
        obs = e.get("observed") or {}
        row = {"name": e["name"], "value": obs.get("value"),
               "as_of": obs.get("as_of"), "used": False}
        if e.get("stance_scale"):
            row["stance"] = obs.get("stance")
        out.append(row)
    return out


def record_evaluation(slug: str, variant: str, conclusions: list, *, note: str | None = None) -> int:
    """便利写回：用 snapshot_inputs 自动列全输入 + 据 based_on 标 used，再走 append_evaluation。

    降低 headless 闭环手工拼 input_snapshot 的漏列/悬空风险；不变量校验仍由 append_evaluation 全程把关
    （列全 + based_on 不悬空 + role 合法），并自动清 reeval_pending、version 自增、写 evaluated_at。
    """
    used_names = {b.get("input")
                  for c in (conclusions or [])
                  for b in (c.get("based_on") or []) if b.get("input")}
    snapshot = snapshot_inputs(slug, variant)
    for s in snapshot:
        if s["name"] in used_names:
            s["used"] = True
    evaluation = {"input_snapshot": snapshot, "conclusions": conclusions or []}
    if note:
        evaluation["note"] = note
    return append_evaluation(slug, variant, evaluation)


def conclusions_for_input(evaluation: dict, name: str) -> list:
    """based_on 反查：该输入支撑哪些 conclusion id。"""
    out = []
    for c in evaluation.get("conclusions") or []:
        if any(b.get("input") == name for b in c.get("based_on") or []):
            out.append(c.get("id"))
    return out


def assemble_reeval_brief(slug: str, variant: str) -> dict:
    """零-LLM 组装重估简报：变化项 + 到期/越带 + 受影响结论 + 未抓盲区清单。

    未抓清单是诚实盲区提示（这些输入无法判断是否变化）。供 S5 展示与对话重判消费。
    """
    diff = diff_since_last(slug, variant)
    changed = [d for d in diff if d["changed"]]
    breached = [d for d in diff if d["breached"]]
    unfetched = [d["name"] for d in diff if d["live_value"] is None]
    registry = reg.read_registry(slug, variant)
    scan = reg.scan_macro_inputs(registry)
    due = [e["name"] for e in scan["due_event"] + scan["due_policy"]]
    alert = [e["name"] for e in scan["alert_series"]]
    affected = sorted({c for d in (changed + breached) for c in d["conclusions"]})
    labels = conclusion_labels(slug, variant)
    affected_labels = [labels.get(cid, cid) for cid in affected]   # 缺 label 回落 id
    return {"changed": changed, "breached": breached, "due": due,
            "alert": alert, "unfetched": unfetched, "affected_conclusions": affected,
            "affected_conclusion_labels": affected_labels}


def stamp_reeval_pending(slug: str, variant: str, brief: dict) -> None:
    """盖「待重判」戳（写 reeval_pending）。append_evaluation 时自动清空。零 LLM。"""
    log = read_eval_log(slug, variant)
    log["reeval_pending"] = {"stamped_at": _now_iso(), "brief": brief}
    log["slug"], log["variant"], log["updated"] = slug, variant, _now_iso()
    _write_yaml(_log_path(slug, variant), log)


def _stance_direction(scale, prev, cur):
    """policy 立场方向：按档位索引差取轴方向词。无变化 / 缺档 / 未知轴 → None。"""
    levels = reg.STANCE_SCALES.get(scale)
    if not levels or prev is None or cur is None or prev == cur:
        return None
    try:
        delta = levels.index(cur) - levels.index(prev)
    except ValueError:
        return None
    up, down = reg.STANCE_DIRECTION[scale]
    return up if delta > 0 else down


def diff_since_last(slug: str, variant: str) -> list:
    """对登记表每条输入，比对现 observed.value 与 latest 快照值。零 LLM。

    返回每条 {name, snapshot_value, live_value, delta, changed, breached, used, conclusions}。
    无快照 → changed=None（"首次评估，无基准"）。非数值按字符串比 changed。
    """
    registry = reg.read_registry(slug, variant)
    latest = latest_evaluation(slug, variant)
    snap_by_name = {}
    if latest:
        snap_by_name = {s["name"]: s for s in latest.get("input_snapshot") or []}
    out = []
    for e in registry.get("inputs") or []:
        name = e["name"]
        live = (e.get("observed") or {}).get("value")
        snap = snap_by_name.get(name) or {}
        snap_val = snap.get("value")
        row = {
            "name": name, "snapshot_value": snap_val, "live_value": live,
            "delta": None, "changed": None if latest is None else False,
            "breached": False, "used": bool(snap.get("used")),
            "conclusions": conclusions_for_input(latest, name) if latest else [],
            "stance": None, "snapshot_stance": None, "direction": None,
        }
        scale = e.get("stance_scale")
        if scale:                                  # policy 输入：走立场比对，不碰数值
            live_stance = (e.get("observed") or {}).get("stance")
            snap_stance = snap.get("stance")
            row["snapshot_value"] = None
            row["live_value"] = None
            row["stance"] = live_stance
            row["snapshot_stance"] = snap_stance
            if latest is not None:
                row["changed"] = live_stance != snap_stance
                row["direction"] = _stance_direction(scale, snap_stance, live_stance)
            out.append(row)
            continue
        if latest is not None:
            if isinstance(live, (int, float)) and isinstance(snap_val, (int, float)):
                row["delta"] = live - snap_val
                row["changed"] = row["delta"] != 0
                row["breached"] = reg._reading_breaches(
                    {**e, "observed": {"value": live, "prev_value": snap_val}})
            else:
                row["changed"] = live != snap_val
        out.append(row)
    return out

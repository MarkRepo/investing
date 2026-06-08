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
    snap_names = {s.get("name") for s in snap}
    missing = input_names - snap_names
    if missing:
        errors.append(f"input_snapshot 漏列输入: {sorted(missing)}")
    for c in evaluation.get("conclusions") or []:
        cid = c.get("id", "<无 id>")
        for b in c.get("based_on") or []:
            if b.get("input") not in snap_names:
                errors.append(f"[{cid}] based_on 悬空引用: {b.get('input')!r} 不在 input_snapshot")
            if b.get("role") not in VALID_ROLE:
                errors.append(f"[{cid}] role 非法: {b.get('role')!r}")
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
    return {"changed": changed, "breached": breached, "due": due,
            "alert": alert, "unfetched": unfetched, "affected_conclusions": affected}


def stamp_reeval_pending(slug: str, variant: str, brief: dict) -> None:
    """盖「待重判」戳（写 reeval_pending）。append_evaluation 时自动清空。零 LLM。"""
    log = read_eval_log(slug, variant)
    log["reeval_pending"] = {"stamped_at": _now_iso(), "brief": brief}
    log["slug"], log["variant"], log["updated"] = slug, variant, _now_iso()
    _write_yaml(_log_path(slug, variant), log)


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
        }
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

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

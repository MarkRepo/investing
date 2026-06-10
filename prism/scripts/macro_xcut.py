"""宏观层横切接入（零-LLM）：company 侧 macro_stamp 反查锚 CRUD + 体制变扫失鲜
+ 覆盖看门狗 + 新持仓自注册。判断永远人在对话触发；本模块只做文件读写与派生。

依赖方向（无环）：macro_xcut → {macro_registry, eval_snapshot, topic, monitor}；
monitor 不 import macro_xcut。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from prism.scripts import macro_registry as reg
from prism.scripts import eval_snapshot as es
from prism.scripts import topic as topic_mod
from prism.scripts import monitor

_PRISM_ROOT = Path(__file__).resolve().parent.parent

VALID_ROLE = ("load_bearing", "confirming", "background")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp_path(slug: str, variant: str) -> Path:
    return _PRISM_ROOT / "topics" / slug / variant / "outputs" / "macro_stamp.yaml"


def read_macro_stamp(slug: str, variant: str) -> dict:
    """读 company 侧宏观印章；缺文件返回 {}（让调用方优雅显示"未接入"而非抛）。"""
    p = _stamp_path(slug, variant)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _validate_stamp(stamp: dict) -> list:
    errors = []
    for i, d in enumerate(stamp.get("depends_on_states") or []):
        if not d.get("conclusion"):
            errors.append(f"depends_on_states[{i}] 缺 conclusion")
        if d.get("role") not in VALID_ROLE:
            errors.append(f"depends_on_states[{i}] role 非法: {d.get('role')!r}")
    return errors


def write_macro_stamp(slug: str, variant: str, stamp: dict) -> Path:
    """校验不变量后落盘 macro_stamp.yaml；补默认 stale/stale_reason/stamped_at。"""
    errors = _validate_stamp(stamp)
    if errors:
        raise ValueError("macro_stamp 校验失败:\n" + "\n".join(errors))
    out = dict(stamp)
    out["slug"], out["variant"] = slug, variant
    out.setdefault("stamped_at", _now_iso())
    out.setdefault("stale", False)
    out.setdefault("stale_reason", None)
    p = _stamp_path(slug, variant)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.dump(out, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p

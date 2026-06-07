"""宏观层输入登记表（macro_inputs.yaml）的零-LLM CRUD + 机制纪律 validator。

与 manifest.py（materials 库）刻意分离：manifest 存"资料/搜索 hit"，本模块存
"会影响利率/流动性/汇率判断的输入"及其机制边（spec §2.2）。登记与抓取解耦——
本模块只管登记 + 观测值落盘 + 机制校验；FRED 自动抓等是第二期的事。

登记表 schema：
  slug, variant, updated, inputs: [ {input entry}, ... ]
每条 input entry（spec §2.2 + 运行时观测位）：
  name           中文输入名（唯一键）
  tier           "A"|"B"|"C"
  cadence_type   "event"|"series"|"policy"   (事/行/述)
  targets        ["rates"|"liquidity"|"fx", ...]
  mechanism      "CD"|"CF"|"CO"|"CR"
  causal_sentence  一句话因果链（CD/CF 必填）
  lag            领先/同步/滞后 + 时长（自由文本）
  importance     "load_bearing"|"confirming"|"background"
  source         FRED / web / PBoC / ... / TBD
  fetch_method   fred-api / llm-web / manual / TBD
  state          "已有"|"新增"|"改"
  alert_series   bool（仅 series 可为 true）
  monitoring     {enabled: bool}            缺省视为 enabled=true
  alert_band     {delta: float} 或 {z: float}   仅 alert_series 用
  observed       {value, prev_value, z, as_of, next_due, last_proposed_value}  运行时位（fetcher/monitor 写）
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

_PRISM_ROOT = Path(__file__).resolve().parent.parent

VALID_TIER = ("A", "B", "C")
VALID_CADENCE = ("event", "series", "policy")
VALID_MECHANISM = ("CD", "CF", "CO", "CR")
VALID_IMPORTANCE = ("load_bearing", "confirming", "background")
VALID_TARGET = ("rates", "liquidity", "fx")


def _registry_path(slug: str, variant: str) -> Path:
    if not variant:
        raise ValueError("必须显式指定 variant")
    return _PRISM_ROOT / "topics" / slug / variant / "macro_inputs.yaml"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def create_registry(slug: str, variant: str) -> Path:
    path = _registry_path(slug, variant)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_yaml(path, {"slug": slug, "variant": variant, "updated": _now_iso(), "inputs": []})
    return path


def read_registry(slug: str, variant: str) -> dict:
    path = _registry_path(slug, variant)
    if not path.exists():
        raise FileNotFoundError(f"macro_inputs.yaml not found: {slug}/{variant}")
    return _read_yaml(path)

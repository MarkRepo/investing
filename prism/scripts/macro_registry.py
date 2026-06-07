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


def upsert_input(slug: str, variant: str, entry: dict) -> None:
    """按 name 唯一键 upsert 一条 input（无校验，校验交 validate_registry）。零 LLM。"""
    if not entry.get("name"):
        raise ValueError("input entry 必须有 name")
    data = read_registry(slug, variant)
    for i, existing in enumerate(data["inputs"]):
        if existing["name"] == entry["name"]:
            data["inputs"][i] = {**existing, **entry}
            break
    else:
        data["inputs"].append(entry)
    data["updated"] = _now_iso()
    _write_yaml(_registry_path(slug, variant), data)


def validate_registry(slug: str, variant: str) -> list[str]:
    """校验登记表的机制纪律（spec §2.2/§2.1）。返回错误串列表（空=通过）。零 LLM。

    规则：
      - 枚举合法：tier/cadence_type/mechanism/importance/targets。
      - tier A ⟹ mechanism ∈ {CD, CF}（CO/CR 只能 B/C）。
      - mechanism ∈ {CD, CF} ⟹ causal_sentence 非空。
      - alert_series=True ⟹ cadence_type == "series"。
      - name 不可重复。
    """
    data = read_registry(slug, variant)
    errors: list[str] = []
    seen: set[str] = set()
    for e in data["inputs"]:
        name = e.get("name", "<无名>")
        if name in seen:
            errors.append(f"[{name}] name 重复")
        seen.add(name)
        if e.get("tier") not in VALID_TIER:
            errors.append(f"[{name}] tier 非法: {e.get('tier')!r}")
        if e.get("cadence_type") not in VALID_CADENCE:
            errors.append(f"[{name}] cadence_type 非法: {e.get('cadence_type')!r}")
        if e.get("mechanism") not in VALID_MECHANISM:
            errors.append(f"[{name}] mechanism 非法: {e.get('mechanism')!r}")
        if e.get("importance") not in VALID_IMPORTANCE:
            errors.append(f"[{name}] importance 非法: {e.get('importance')!r}")
        for t in e.get("targets") or []:
            if t not in VALID_TARGET:
                errors.append(f"[{name}] target 非法: {t!r}")
        # 因果纪律
        if e.get("tier") == "A" and e.get("mechanism") in VALID_MECHANISM and e.get("mechanism") not in ("CD", "CF"):
            errors.append(f"[{name}] tier A 必须 mechanism ∈ CD/CF，得到 {e.get('mechanism')!r}")
        if e.get("mechanism") in ("CD", "CF") and not (e.get("causal_sentence") or "").strip():
            errors.append(f"[{name}] mechanism={e.get('mechanism')} 必须填 causal_sentence")
        if e.get("alert_series") and e.get("cadence_type") != "series":
            errors.append(f"[{name}] alert_series=True 仅允许 cadence_type=series")
    return errors


def record_observation(
    slug: str, variant: str, name: str, *,
    value: float | None = None, as_of: str | None = None,
    z: float | None = None, next_due: str | None = None,
) -> None:
    """把一次观测写进某 input 的 observed；旧 value 滚成 prev_value。零 LLM。

    fetcher（第二期）每次抓到新值调本函数；monitor 据 observed 判越带/到期。
    value 给定时滚动 prev_value；z/next_due 给定则覆盖对应位。
    """
    data = read_registry(slug, variant)
    for e in data["inputs"]:
        if e["name"] == name:
            obs = dict(e.get("observed") or {})
            if value is not None:
                if "value" in obs:
                    obs["prev_value"] = obs["value"]
                obs["value"] = value
            if as_of is not None:
                obs["as_of"] = as_of
            if z is not None:
                obs["z"] = z
            if next_due is not None:
                obs["next_due"] = next_due
            obs["checked_at"] = _now_iso()
            # 维护连续越带计数（min_streak 用）
            if value is not None:
                breached = _reading_breaches({**e, "observed": obs})
                obs["streak"] = (obs.get("streak", 0) + 1) if breached else 0
            e["observed"] = obs
            data["updated"] = _now_iso()
            _write_yaml(_registry_path(slug, variant), data)
            return
    raise ValueError(f"input {name!r} 不在登记表中")


def _parse_date(s):
    from datetime import date as _date
    if not s:
        return None
    try:
        return _date.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


def _reading_breaches(entry: dict) -> bool:
    """单次读数是否越带：delta / z / level(+direction) 任一命中。"""
    band = entry.get("alert_band") or {}
    obs = entry.get("observed") or {}
    v, p = obs.get("value"), obs.get("prev_value")
    if "delta" in band and v is not None and p is not None:
        if abs(v - p) >= band["delta"]:
            return True
    if "z" in band:
        z = obs.get("z")
        if z is not None and abs(z) >= band["z"]:
            return True
    if "level" in band and v is not None:
        d = band.get("direction", "above")
        if d == "above" and v >= band["level"]:
            return True
        if d == "below" and v <= band["level"]:
            return True
        if d == "abs_above" and abs(v) >= band["level"]:
            return True
    return False


def _series_breached(entry: dict) -> bool:
    """alert_series 是否报警：当前读数越带 且 连续越带天数≥min_streak（默认1）。
    streak 由 record_observation 维护；未维护时默认 1（向后兼容旧 delta/z 行为）。"""
    if not _reading_breaches(entry):
        return False
    band = entry.get("alert_band") or {}
    obs = entry.get("observed") or {}
    return obs.get("streak", 1) >= band.get("min_streak", 1)


def scan_macro_inputs(registry: dict, today=None) -> dict:
    """纯函数：把登记表分桶。不读文件。零 LLM。

    返回 {due_event, due_policy, alert_series, unparseable}，每项是 input entry 的浅拷贝。
    规则：
      - monitoring.enabled is False → 跳过。
      - cadence_type=event/policy：observed.next_due 可解析且 ≤ today → due_*；不可解析 → unparseable。
      - cadence_type=series 且 alert_series=True 且 _series_breached → alert_series。
      - 其余（含非 alert 的 series 小动）→ 不进任何桶。
    """
    from datetime import date as _date
    today = today or _date.today()
    out = {"due_event": [], "due_policy": [], "alert_series": [], "unparseable": []}
    for e in registry.get("inputs") or []:
        if (e.get("monitoring") or {}).get("enabled") is False:
            continue
        ctype = e.get("cadence_type")
        if ctype in ("event", "policy"):
            nd_raw = (e.get("observed") or {}).get("next_due")
            if nd_raw is None:
                continue  # 还没排期，不报
            d = _parse_date(nd_raw)
            if d is None:
                out["unparseable"].append(dict(e))
            elif d <= today:
                out["due_event" if ctype == "event" else "due_policy"].append(dict(e))
        elif ctype == "series" and e.get("alert_series") and _series_breached(e):
            out["alert_series"].append(dict(e))
    return out

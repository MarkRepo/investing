"""机械翻牌 sidecar 决策字段（signpost.triggered / kill.status）。零 LLM。

daily-monitor 闭环的"回写层"：headless 判读产出 proposal，用户 confirm 后由本模块
把翻牌结果机械落进 company 的 07_decision_kit.yaml。**不做任何 LLM 判断**——只校验
+ 定位 + 改值 + dump。

为何独立成文件（不并进 topic.py / outputs.py）：那二者是 topic.yaml / manifest 元数据
中枢，本模块碰的是 sidecar 决策链业务字段（signposts/kill_criteria），语义边界不同。

幂等核心 —— signpost 无稳定 id 且 date 可能重复（同日多事件），用 sha1(date|event)[:8]
作 locator；kill 用现成 id。confirm 时按 locator 重查目标项，被 04/05 重排/删则报
StaleProposal 拒绝，绝不盲写 idx。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

PRISM_ROOT = Path(__file__).resolve().parent.parent

# signpost.triggered 三态：未触发 / 偏多兑现 / 偏空兑现（不用 bool，保留方向）
_VALID_SIGNPOST = (None, "bull", "bear")
# kill.status 枚举
_VALID_KILL = ("pending", "triggered_bull", "triggered_bear", "cleared")

# expected_current 乐观锁哨兵：区分"不校验"(默认 _UNSET) 与"期望当前值为 None"(显式传 None)
_UNSET = object()


class StaleProposal(Exception):
    """proposal 与 sidecar 现状不符（被 04/05 重排/删，或值已变）——拒绝盲写。"""


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _decision_kit_path(slug: str, variant: str) -> Path:
    return PRISM_ROOT / "topics" / slug / variant / "outputs" / "07_decision_kit.yaml"


def signpost_locator(date, event: str) -> str:
    """signpost 稳定定位符：sha1(date|event)[:8]。

    date 可能是 str 或 datetime.date——统一 str() 后参与 hash，确保 propose/confirm 一致。
    """
    raw = f"{date}|{event}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]


def set_signpost_triggered(
    slug: str,
    variant: str,
    locator_hash: str,
    value,
    expected_current=_UNSET,
) -> dict:
    """翻 signpost.triggered。零 LLM。

    locator_hash : signpost_locator(date, event) 的结果
    value        : None | "bull" | "bear"
    expected_current : 乐观锁。默认 _UNSET=不校验；显式传值（含 None）则要求当前值匹配，
                       否则 StaleProposal（防 04/05 race）。

    返回被改 signpost 的浅拷贝（含 date/event/triggered）。
    定位不到 → StaleProposal。
    """
    if value not in _VALID_SIGNPOST:
        raise ValueError(f"signpost triggered 必须 ∈ {_VALID_SIGNPOST}，得到 {value!r}")
    path = _decision_kit_path(slug, variant)
    if not path.exists():
        raise FileNotFoundError(f"sidecar 不存在: {path}")
    data = _read_yaml(path)
    signposts = data.get("signposts") or []
    target = None
    for sp in signposts:
        if signpost_locator(sp.get("date"), sp.get("event", "")) == locator_hash:
            target = sp
            break
    if target is None:
        raise StaleProposal(
            f"signpost locator {locator_hash} 在 {slug}/{variant} 已不存在"
            f"（被 04/05 重排/删？）"
        )
    if expected_current is not _UNSET and target.get("triggered") != expected_current:
        raise StaleProposal(
            f"signpost {locator_hash} 当前 triggered={target.get('triggered')!r} "
            f"≠ 期望 {expected_current!r}（已被改动，需重评）"
        )
    target["triggered"] = value
    _write_yaml(path, data)
    return {"date": target.get("date"), "event": target.get("event"), "triggered": value}


def set_kill_status(
    slug: str,
    variant: str,
    kill_id: str,
    status: str,
    expected_current=_UNSET,
) -> dict:
    """翻 kill_criteria[].status。零 LLM。

    kill_id : kill_criteria 项的现成 id
    status  : pending | triggered_bull | triggered_bear | cleared
    expected_current : 乐观锁，同 set_signpost_triggered。

    返回被改 kill 的浅拷贝（含 id/description/status）。
    定位不到 → StaleProposal。
    """
    if status not in _VALID_KILL:
        raise ValueError(f"kill status 必须 ∈ {_VALID_KILL}，得到 {status!r}")
    path = _decision_kit_path(slug, variant)
    if not path.exists():
        raise FileNotFoundError(f"sidecar 不存在: {path}")
    data = _read_yaml(path)
    kills = data.get("kill_criteria") or []
    target = None
    for k in kills:
        if k.get("id") == kill_id:
            target = k
            break
    if target is None:
        raise StaleProposal(
            f"kill id {kill_id!r} 在 {slug}/{variant} 已不存在（被 04/05 重排/删？）"
        )
    if expected_current is not _UNSET and target.get("status") != expected_current:
        raise StaleProposal(
            f"kill {kill_id!r} 当前 status={target.get('status')!r} "
            f"≠ 期望 {expected_current!r}（已被改动，需重评）"
        )
    target["status"] = status
    _write_yaml(path, data)
    return {"id": kill_id, "description": target.get("description"), "status": status}

"""宏观判断台账战绩（零-LLM·全派生不存盘）：单边裁决 + 整版战绩卡 + 跨版边台账。

每条 regime 结论写时对承重输入许 expected 方向预测（见 eval_snapshot）；本模块拿实际序列
机械裁决 hit/miss/neutral，连续可算、按需重算（镜像 diff_since_last 哲学）。判断永远人在
对话触发，本模块零 LLM。

依赖方向（无环）：eval_score → {eval_snapshot, macro_registry}。
"""
from __future__ import annotations

from datetime import datetime, timezone

from prism.scripts import eval_snapshot as es
from prism.scripts import macro_registry as reg


def score_edge(expected, snapshot_value, live_value, scale=None, tol=0.0):
    """单条承重边裁决：hit / miss / neutral。零 LLM。

    缺 expected / 缺基准（snapshot 或 live 为 None）→ neutral（不计命中/失手）。
    立场型（scale 给定）走 _stance_direction：无移动/不可比 → neutral（保守不冤判）。
    数值型按方向；flat 与 _or_flat 边界用容差 tol（默认 0.0，由 alert_band.delta 供）。
    """
    if not expected or live_value is None or snapshot_value is None:
        return "neutral"
    if scale:                                  # 立场/政策轴
        observed = es._stance_direction(scale, snapshot_value, live_value)
        if observed is None:
            return "neutral"
        return "hit" if observed == expected else "miss"
    if not (isinstance(snapshot_value, (int, float)) and isinstance(live_value, (int, float))):
        return "neutral"
    delta = live_value - snapshot_value
    if expected == "up":
        return "hit" if delta > 0 else "miss"
    if expected == "down":
        return "hit" if delta < 0 else "miss"
    if expected == "flat":
        return "hit" if abs(delta) <= tol else "miss"
    if expected == "up_or_flat":
        return "hit" if delta >= -tol else "miss"
    if expected == "down_or_flat":
        return "hit" if delta <= tol else "miss"
    return "neutral"

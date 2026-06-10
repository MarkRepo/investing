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


def _days_since(iso) -> int | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


def _edge_baseline(entry, snap_row, scale):
    """取 (snapshot 值, 现 live 值)：立场取 stance，数值取 value。"""
    if scale:
        return snap_row.get("stance"), (entry.get("observed") or {}).get("stance")
    return snap_row.get("value"), (entry.get("observed") or {}).get("value")


def score_evaluation(slug: str, variant: str, version: int | None = None) -> dict:
    """对某版评估（默认最新版）的承重边逐条裁决 → 每结论占对率 + 整版战绩卡 + 天数。零 LLM。

    拿「该版 expected」vs「现 observed 序列」，连续可算、按需重算（不存盘）。
    只给 load_bearing 边记战绩（本期范围）；neutral 不计入占对率分母。
    """
    log = es.read_eval_log(slug, variant)
    evals = log.get("evaluations") or []
    if not evals:
        return {"version": None, "scored": False, "reason": "no_evaluation", "conclusions": []}
    if version is None:
        ev = evals[-1]
    else:
        ev = next((e for e in evals if e.get("version") == version), None)
        if ev is None:
            return {"version": version, "scored": False, "reason": "version_not_found",
                    "conclusions": []}
    registry = reg.read_registry(slug, variant)
    entry_by_name = {e["name"]: e for e in registry.get("inputs") or []}
    snap_by_name = {s.get("name"): s for s in ev.get("input_snapshot") or []}
    conclusions_out, tot_hit, tot_miss, tot_neu = [], 0, 0, 0
    for c in ev.get("conclusions") or []:
        edges, c_hit, c_miss, c_neu = [], 0, 0, 0
        for b in c.get("based_on") or []:
            if b.get("role") != "load_bearing":
                continue
            name = b.get("input")
            entry = entry_by_name.get(name) or {}
            scale = entry.get("stance_scale")
            tol = (entry.get("alert_band") or {}).get("delta", 0.0) or 0.0
            snap_v, live_v = _edge_baseline(entry, snap_by_name.get(name) or {}, scale)
            verdict = score_edge(b.get("expected"), snap_v, live_v, scale=scale, tol=tol)
            edges.append({"input": name, "expected": b.get("expected"), "verdict": verdict,
                          "snapshot_value": snap_v, "live_value": live_v})
            c_hit += verdict == "hit"
            c_miss += verdict == "miss"
            c_neu += verdict == "neutral"
        denom = c_hit + c_miss
        conclusions_out.append({
            "id": c.get("id"), "label": c.get("label"), "state": c.get("state"),
            "hits": c_hit, "misses": c_miss, "neutrals": c_neu,
            "hit_rate": (c_hit / denom) if denom else None, "edges": edges})
        tot_hit += c_hit
        tot_miss += c_miss
        tot_neu += c_neu
    tot_denom = tot_hit + tot_miss
    return {"version": ev.get("version"), "scored": True,
            "evaluated_at": ev.get("evaluated_at"), "days": _days_since(ev.get("evaluated_at")),
            "hits": tot_hit, "misses": tot_miss, "neutrals": tot_neu,
            "hit_rate": (tot_hit / tot_denom) if tot_denom else None,
            "conclusions": conclusions_out}


def _track_label(hits: int, misses: int) -> str:
    denom = hits + misses
    if denom == 0:
        return "无裁定"
    rate = hits / denom
    if denom >= 2 and rate < 0.5:
        return "降级候选"
    if rate >= 0.7:
        return "可靠"
    return "观察"


def edge_ledger(slug: str, variant: str) -> list:
    """跨所有评估版本按 (conclusion_id, input) 累计 hit/miss/neutral → 降级候选浮出。零 LLM。

    每版 expected 的「实现值」取下一版快照；末版用当前 live observed。只算 load_bearing 边。
    返回按 hit_rate 升序（差的在前；None 垫底），每行 {conclusion_id, input, hits, misses,
    neutrals, hit_rate, track}。
    """
    log = es.read_eval_log(slug, variant)
    evals = log.get("evaluations") or []
    registry = reg.read_registry(slug, variant)
    entry_by_name = {e["name"]: e for e in registry.get("inputs") or []}
    acc: dict = {}
    for i, ev in enumerate(evals):
        snap_by_name = {s.get("name"): s for s in ev.get("input_snapshot") or []}
        nxt_by_name = ({s.get("name"): s for s in evals[i + 1].get("input_snapshot") or []}
                       if i + 1 < len(evals) else None)
        for c in ev.get("conclusions") or []:
            cid = c.get("id")
            for b in c.get("based_on") or []:
                if b.get("role") != "load_bearing" or not b.get("expected"):
                    continue
                name = b.get("input")
                entry = entry_by_name.get(name) or {}
                scale = entry.get("stance_scale")
                tol = (entry.get("alert_band") or {}).get("delta", 0.0) or 0.0
                snap_row = snap_by_name.get(name) or {}
                snap_v = snap_row.get("stance") if scale else snap_row.get("value")
                if nxt_by_name is not None:                       # 实现值=下一版快照
                    nrow = nxt_by_name.get(name) or {}
                    live_v = nrow.get("stance") if scale else nrow.get("value")
                else:                                             # 末版=当前 live
                    obs = entry.get("observed") or {}
                    live_v = obs.get("stance") if scale else obs.get("value")
                verdict = score_edge(b.get("expected"), snap_v, live_v, scale=scale, tol=tol)
                a = acc.setdefault((cid, name), {"hits": 0, "misses": 0, "neutrals": 0})
                a[{"hit": "hits", "miss": "misses", "neutral": "neutrals"}[verdict]] += 1
    out = []
    for (cid, name), a in acc.items():
        denom = a["hits"] + a["misses"]
        out.append({"conclusion_id": cid, "input": name,
                    "hits": a["hits"], "misses": a["misses"], "neutrals": a["neutrals"],
                    "hit_rate": (a["hits"] / denom) if denom else None,
                    "track": _track_label(a["hits"], a["misses"])})
    out.sort(key=lambda r: (r["hit_rate"] is None, r["hit_rate"] if r["hit_rate"] is not None else 1.0))
    return out

"""Prism 可观测性观测层（纯被动 · 零 LLM）。

run_probes(slug, variant) 从已有产物残留重建流程质量诊断。
探针族：produce(产出) / quality(质量) / pitfall(坑)。
quality.tier: 1=机械重建 / 2=机械代理 / 3=纯判断挂复核旗。
status: pass / fail / flag / na。

spec: prism/specs/observability.md
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

import yaml as _yaml

from prism.scripts import outputs as outputs_io
from prism.scripts import topic as topic_io
from prism.scripts.gap_detector import detect_gaps
from prism.scripts.topic import get_current_prescan_status
from prism.scripts.web_prescan import list_search_log
from prism.scripts.manifest import read_manifest


@dataclass
class Probe:
    probe_id: str
    label: str
    stage: str
    family: str            # produce | quality | pitfall
    status: str            # pass | fail | flag | na
    signal: str
    tier: int | None = None
    detail: str = ""
    action: str = ""


def _active_todos(topic: dict) -> list[dict]:
    return [t for t in (topic.get("user_todos") or [])
            if isinstance(t, dict) and t.get("status") in ("pending", "in_progress")]


def _cross_cutting(slug: str, variant: str, topic: dict, gaps: dict) -> list[Probe]:
    out: list[Probe] = []
    active = _active_todos(topic)

    # CC1: active todo 都带 addresses（H2）
    missing = [t.get("task", "?") for t in active if not t.get("addresses")]
    out.append(Probe(
        "CC1", "active todo 都带 addresses", "cross-cutting", "pitfall",
        "fail" if missing else "pass", "todo.addresses 字段", tier=1,
        detail=("丢字段: " + "; ".join(missing)) if missing else "全带",
        action="补 addresses" if missing else "",
    ))

    # CC3: autofetch 欠账（unattempted/error）
    debt = gaps.get("autofetch_debt") or []
    out.append(Probe(
        "CC3", "autofetch 欠账", "cross-cutting", "pitfall",
        "fail" if debt else "pass", "gap_detector.autofetch_debt", tier=1,
        detail=f"{len(debt)} 条欠尝试" if debt else "无欠账",
        action="error→重试 / unattempted→去抓" if debt else "",
    ))

    # CC4: empty 待用户决（硬闸门）
    empty = gaps.get("empty_pending_decision") or []
    out.append(Probe(
        "CC4", "empty 待用户决", "cross-cutting", "pitfall",
        "fail" if empty else "pass", "empty_undecided_todos", tier=1,
        detail=f"{len(empty)} 条待决" if empty else "无待决",
        action="走 empty 硬闸门" if empty else "",
    ))

    # CC6: P0 pending 进 04/05 前已收敛
    stage = topic.get("stage", "")
    late = stage.startswith(("04", "05", "done"))
    p0_pending = [t.get("task", "?") for t in active
                  if t.get("priority") == "P0" and t.get("status") == "pending"]
    cc6_fail = late and bool(p0_pending)
    out.append(Probe(
        "CC6", "P0 pending 进 04/05 前已收敛", "cross-cutting", "pitfall",
        "fail" if cc6_fail else "pass", "P0 todo.status + stage", tier=1,
        detail=("未收敛: " + "; ".join(p0_pending)) if cc6_fail else "已收敛或未到 04",
        action="收敛 P0（done/重试/waived）" if cc6_fail else "",
    ))
    return out


def _stage_05(slug, variant, topic, gaps) -> list[Probe]:
    out: list[Probe] = []
    critic = topic.get("critic") or {}
    verdict = critic.get("verdict")
    score = critic.get("score")

    # 05.X1: failed prescan 却 approve（纯机械可逮）
    ps = get_current_prescan_status(slug, variant)  # {'status', 'failure_reason', 'version'}
    prescan_failed = (isinstance(ps, dict) and ps.get("status") == "failed")
    x1_fail = prescan_failed and verdict == "approve"
    out.append(Probe(
        "05.X1", "failed prescan 却 approve", "05-critic-review", "pitfall",
        "fail" if x1_fail else ("na" if verdict is None else "pass"),
        "prescan_status + verdict", tier=1,
        detail="时敏论断未校准就 approve" if x1_fail else "",
        action="按脆弱处理，最高 request-more" if x1_fail else "",
    ))

    # 05.Q2: verdict 与评分一致（评分低却 approve = 放水）
    # 注：critic 当前无 score 字段，此探针在真实 topic 上多为 na/pass，待 critic 加 score 后自动激活。
    q2_fail = verdict == "approve" and isinstance(score, (int, float)) and score < 4
    out.append(Probe(
        "05.Q2", "verdict 与评分一致", "05-critic-review", "quality",
        "fail" if q2_fail else ("na" if verdict is None else "pass"),
        "score vs verdict", tier=1,
        detail=f"score={score} 却 approve" if q2_fail else "",
        action="复核是否放水" if q2_fail else "",
    ))

    # 05.Q1: 反方真 steelman —— 纯判断，05 到了就挂旗
    out.append(Probe(
        "05.Q1", "反方真 steelman 还是走过场", "05-critic-review", "quality",
        "na" if verdict is None else "flag", "—", tier=3,
        detail="被动层判不了，需人复核 critic 是否攻最强论证",
        action="人复核" if verdict else "",
    ))

    # 05.Q3: request-more todo 只列搜不到的 + 必带 addresses
    if verdict != "request-more":
        out.append(Probe(
            "05.Q3", "request-more todo 必带 addresses + 限搜不到",
            "05-critic-review", "quality", "na",
            "verdict + todo addresses/fetch_status", tier=1,
            detail="verdict 非 request-more"))
    else:
        active = _active_todos(topic)
        pend = [t for t in active if t.get("status") == "pending"]
        bad = [t.get("task", "?") for t in pend
               if not t.get("addresses") or t.get("fetch_status") != "empty"]
        out.append(Probe(
            "05.Q3", "request-more todo 必带 addresses + 限搜不到",
            "05-critic-review", "quality",
            "na" if not pend else ("fail" if bad else "pass"),
            "verdict + todo addresses/fetch_status", tier=1,
            detail=("不合规: " + "; ".join(bad)) if bad else "request-more todo 合规",
            action="补 addresses / 限定为搜不到项" if bad else "",
        ))
    return out


def _cross_cutting_extra(slug, variant, topic) -> list[Probe]:
    out: list[Probe] = []
    active = _active_todos(topic)

    # CC2: 假 pending（pending 但 covered_by≠∅ 或 fetch_status=fetched）
    fake = [t.get("task", "?") for t in active if t.get("status") == "pending"
            and (t.get("covered_by") or t.get("fetch_status") == "fetched")]
    out.append(Probe(
        "CC2", "无待补料假 pending", "cross-cutting", "pitfall",
        "fail" if fake else "pass", "pending + covered_by/fetch_status", tier=1,
        detail=("应翻 done: " + "; ".join(fake)) if fake else "无假 pending",
        action="update_user_todo_status → done" if fake else "",
    ))

    # 01.Q1: public/half 是否真过自动获取（fetch_status≠unattempted）
    unatt = [t.get("task", "?") for t in active
             if t.get("info_tier", "public") in ("public", "half_public")
             and t.get("fetch_status", "unattempted") == "unattempted"]
    out.append(Probe(
        "01.Q1", "5.6 跑了（public/half 真过自动获取）", "01-roadmap", "quality",
        "fail" if unatt else "pass", "fetch_status≠unattempted", tier=1,
        detail=("未尝试: " + "; ".join(unatt)) if unatt else "都尝试过",
        action="去抓（CC3）" if unatt else "",
    ))
    return out


def _b5prime(slug, variant, topic) -> list[Probe]:
    """本轮收料卷积（执行轨迹被动版）：搜 N 轮 → 入库 M 份料 → 降级 K 条。零建设。"""
    # 搜索轮次
    try:
        log = list_search_log(slug, variant)
    except Exception:
        log = []
    log = log if isinstance(log, list) else []
    rounds = len(log)
    registered = sum(1 for e in log
                     if isinstance(e, dict) and e.get("disposition", "registered") == "registered")
    skipped = rounds - registered
    # 入库料
    try:
        mats = (read_manifest(slug, variant).get("materials") or [])
    except Exception:
        mats = []
    # 降级决定：fetch_status∈{empty,error} 或 disposition∈{waived,will_collect}
    downgraded = [t for t in (topic.get("user_todos") or []) if isinstance(t, dict)
                  and (t.get("fetch_status") in ("empty", "error")
                       or t.get("disposition") in ("waived", "will_collect"))]
    detail = (f"搜 {rounds} 轮（入库 {registered} / 跳过 {skipped}）"
              f" → 入库 {len(mats)} 份料 → 降级 {len(downgraded)} 条")
    return [Probe(
        "B5prime", "本轮收料卷积（执行轨迹被动版）", "cross-cutting", "produce",
        "pass", "web_search_log + manifest + fetch_status", tier=1,
        detail=detail,
    )]


def _stage_02(slug, variant, topic) -> list[Probe]:
    """02.Q2 K# 红项 / 02.Q3 ring 输入 hard 项 进 03 前是否被处理（吃 B1 stage_history diff）。"""
    hist = topic.get("stage_history") or []

    def snap(stage_prefix):
        return next((h.get("gap_snapshot", {}) for h in hist
                     if h.get("stage", "").startswith(stage_prefix)), None)

    s02, s03 = snap("02"), snap("03")
    out: list[Probe] = []

    # 02.Q2：K# 脊柱红项 02→03 是否带着硬升
    if s02 is None or s03 is None:
        out.append(Probe("02.Q2", "gap 红项被处理 vs 无视硬升", "02-gather-materials",
                         "quality", "na", "stage_history diff", tier=1,
                         detail="无 02/03 快照（旧 topic 或未到）"))
    else:
        carried = sorted(set(s02.get("uncovered_ks") or []) & set(s03.get("uncovered_ks") or []))
        out.append(Probe(
            "02.Q2", "gap 红项被处理 vs 无视硬升", "02-gather-materials", "quality",
            "fail" if carried else "pass", "stage_history diff", tier=1,
            detail=("红着硬升: " + ", ".join(carried)) if carried else "红项进 03 前已清",
            action="补料或诚实标缺" if carried else "",
        ))

    # 02.Q3：uncovered_ring_inputs（输入脊柱）红项 02→03 是否显式处理
    if s02 is None or s03 is None:
        out.append(Probe("02.Q3", "uncovered_ring 升前显式处理", "02-gather-materials",
                         "quality", "na", "stage_history diff", tier=1,
                         detail="无 02/03 快照（旧 topic 或未到）"))
    else:
        carried_r = sorted(set(s02.get("uncovered_ring_inputs") or [])
                           & set(s03.get("uncovered_ring_inputs") or []))
        out.append(Probe(
            "02.Q3", "uncovered_ring 升前显式处理", "02-gather-materials", "quality",
            "fail" if carried_r else "pass", "stage_history diff", tier=1,
            detail=("红着硬升: " + ", ".join(carried_r)) if carried_r else "ring 输入红项进 03 前已清",
            action="补料或诚实标缺" if carried_r else "",
        ))
    return out


def _read_sidecar(slug, variant) -> dict:
    """读决策链 sidecar（07/09/10 任一存在者）。失败/缺文件返回 {}。"""
    d = topic_io.PRISM_ROOT / "topics" / slug / variant / "outputs"
    for name in ("07_decision_kit.yaml", "industry_to_arenas.yaml", "peer_matrix.yaml"):
        p = d / name
        if p.is_file():
            try:
                return _yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except Exception:
                return {}
    return {}


def _stage_04(slug, variant, topic, gaps) -> list[Probe]:
    """04.Q1 断链(B2) + 04.Q3 诚实缺口(B3) + 04.Q2 ④delta锚②(B4) + 04.X1 硬合成 + 04.X2 mirror。"""
    sc = _read_sidecar(slug, variant)
    cl = sc.get("chain_links")
    if not cl:
        q1 = Probe("04.Q1", "断链（6环结构+交叉引用）", "04-synthesizing", "quality",
                   "na", "sidecar chain_links", tier=1, detail="无 chain_links（未合成或旧产出）")
    else:
        missing = [r for r in (1, 2, 3, 4, 5, 6) if r not in (cl.get("rings_present") or [])]
        broken = [k for k in ("r4_anchors_r2", "r6_takes_r4_ev", "r5_has_kill_signpost")
                  if cl.get(k) is False]
        fail = bool(missing or broken)
        q1 = Probe("04.Q1", "断链（6环结构+交叉引用）", "04-synthesizing", "quality",
                   "fail" if fail else "pass", "sidecar chain_links", tier=1,
                   detail=(f"缺环 {missing}; 断 {broken}".strip("; ")) if fail else "链完整",
                   action="补环/补交叉引用" if fail else "")

    # 04.Q3: 诚实缺口标记（检测侧）—— 有 honest_gaps 字段即视为诚实标了
    hg = sc.get("honest_gaps")
    q3 = Probe("04.Q3", "缺口诚实标 vs 冒充实证", "04-synthesizing", "quality",
               "na" if not sc else ("pass" if hg is not None else "flag"),
               "sidecar honest_gaps", tier=2,
               detail="有诚实缺口列表" if hg else "无 honest_gaps，冒充侧需人复核",
               action="" if hg else "人复核是否冒充实证")

    # 04.Q2：环④ delta 是否锚回环② 同一指标（B4 字段）。② 代理：对齐也只挂旗给人。
    mi = sc.get("market_implied") or {}
    dl = sc.get("my_vs_market_delta") or {}
    if not mi and not dl:
        q2 = Probe("04.Q2", "环④锚回②的 delta", "04-synthesizing", "quality",
                   "na", "sidecar market_implied/my_vs_market_delta", tier=2,
                   detail="无 B4 字段（未合成或非估值型 topic）")
    else:
        mi_m, dl_m = mi.get("metric"), dl.get("metric")
        aligned = bool(mi_m) and mi_m == dl_m
        q2 = Probe("04.Q2", "环④锚回②的 delta", "04-synthesizing", "quality",
                   "flag" if aligned else "fail",
                   "sidecar market_implied/my_vs_market_delta", tier=2,
                   detail=(f"delta 锚同指标 {mi_m}，待人确认真锚回②" if aligned
                           else f"②/④ 指标不一致: 市场隐含={mi_m} vs delta={dl_m}"),
                   action="" if aligned else "对齐 ②反推指标与 ④delta 指标")

    # 04.X1：双轴红没补就写占位（硬合成）。gap 红 + case 含占位串。
    case = _case_text(slug, variant)
    red_ks = list((gaps or {}).get("uncovered_ks") or [])
    if case is None:
        x1 = Probe("04.X1", "无硬合成（红没补就占位）", "04-synthesizing", "pitfall",
                   "na", "gap 红 + case 占位串", tier=1, detail="无 case 产出")
    else:
        ph = [s for s in ("未充分论证", "未论证", "待补", "占位", "TODO") if s in case]
        hard = bool(red_ks) and bool(ph)
        x1 = Probe("04.X1", "无硬合成（红没补就占位）", "04-synthesizing", "pitfall",
                   "fail" if hard else "pass", "gap 红 + case 占位串", tier=1,
                   detail=(f"双轴红({','.join(red_ks)}) 且 case 含占位 {ph}" if hard
                           else ("case 无占位串" if not ph else "case 有占位但 gap 不红")),
                   action="补料或诚实标缺，勿写占位" if hard else "")

    # 04.X2：*-mirror false-red 抑制 —— 诚实 na（盲点显式化）
    x2 = Probe("04.X2", "*-mirror 标红抑制（复用起手属预期）", "04-synthesizing", "pitfall",
               "na", "mirror todo 红 + variant 复用关系", tier=1,
               detail="需 variant 复用关系(model_registry 桥接)+mirror todo 联判，未结构暴露——盲点显式化")
    return [q1, q3, q2, x1, x2]


def _stage_03(slug, variant) -> list[Probe]:
    """03.Q1 findings 标 source/confidence + 03.Q3 冲突证据被识别（B6 标记）。

    findings 真实落在 outputs/findings_*.md（非 findings/ 目录）；frontmatter 用
    source_type（溯源）+ quality（可信度）。
    """
    files = _findings_files(slug, variant)
    if not files:
        return [
            Probe("03.Q1", "findings 标了 source/confidence", "03-extracting", "quality",
                  "na", "findings frontmatter", tier=1, detail="无 findings"),
            Probe("03.Q3", "冲突证据被识别", "03-extracting", "quality",
                  "na", "findings conflict 标记", tier=2, detail="无 findings"),
        ]
    texts = [(f.name, f.read_text(encoding="utf-8")) for f in files]

    # 03.Q1：每份 finding 都标了 溯源(source/source_type) + 可信度(confidence/quality)
    def _has(t, keys):
        return any(re.search(rf"(?m)^{k}\s*:", t) for k in keys)
    missing = [n for n, t in texts
               if not (_has(t, ("source_type", "source")) and _has(t, ("quality", "confidence")))]
    q1 = Probe(
        "03.Q1", "findings 标了 source/confidence", "03-extracting", "quality",
        "fail" if missing else "pass", "findings frontmatter", tier=1,
        detail=("缺溯源/可信度: " + "; ".join(missing)) if missing else f"{len(texts)} 份均标全",
        action="补 source_type/quality frontmatter" if missing else "",
    )

    # 03.Q3：冲突标记（B6）
    has_conflict_marker = any("conflicts_with" in t for _, t in texts)
    q3 = Probe("03.Q3", "冲突证据被识别", "03-extracting", "quality",
               "pass" if has_conflict_marker else "flag",
               "findings conflict 标记", tier=2,
               detail="有冲突标记" if has_conflict_marker else "无标记，需人复核是否和稀泥",
               action="" if has_conflict_marker else "人复核冲突处理")
    return [q1, q3]


# ───────────────────────── Task 8 helpers（纯读，零写）─────────────────────────

def _findings_files(slug, variant) -> list:
    """findings 真实落在 outputs/findings_*.md（非 findings/ 目录）。"""
    d = topic_io.PRISM_ROOT / "topics" / slug / variant / "outputs"
    return sorted(d.glob("findings_*.md")) if d.is_dir() else []


def _latest_decomposition_text(slug, variant) -> str | None:
    vers = outputs_io.list_decomposition_files(slug, variant)
    if not vers:
        return None
    p = topic_io.PRISM_ROOT / "topics" / slug / variant / f"decomposition_v{vers[-1]}.md"
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return None


def _case_text(slug, variant) -> str | None:
    d = topic_io.PRISM_ROOT / "topics" / slug / variant / "outputs"
    for stem in ("c_investment_case", "i_industry_case", "a_arena_case"):
        p = d / f"{stem}.md"
        if p.is_file():
            try:
                return p.read_text(encoding="utf-8")
            except Exception:
                return None
    return None


def _material_addr_map(slug, variant) -> dict:
    try:
        mats = read_manifest(slug, variant).get("materials") or []
    except Exception:
        mats = []
    return {m.get("id"): (m.get("addresses") or []) for m in mats if isinstance(m, dict)}


def _has_financial_material(slug, variant) -> bool:
    try:
        mats = read_manifest(slug, variant).get("materials") or []
    except Exception:
        return False
    fin_doc = {"annual_report", "financials", "10-K", "10-Q", "6-K", "quarterly", "earnings"}
    fin_src = {"financial-data", "filing", "annual-report"}
    return any(isinstance(m, dict) and ((m.get("doc_type") or "") in fin_doc
                                        or (m.get("source_type") or "") in fin_src)
               for m in mats)


def _monitor_entries(slug) -> list:
    p = topic_io.PRISM_ROOT / "monitor_queue.yaml"
    if not p.is_file():
        return []
    try:
        data = _yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("pending") or data.get("proposals") or data.get("queue") or []
    else:
        items = []
    return [e for e in items if isinstance(e, dict) and e.get("slug") == slug]


def _cc5(slug, variant, topic) -> list[Probe]:
    """CC5 假覆盖：带 @event 锚的 covered todo 的覆盖料必须事件锚匹配（② 代理 → 挂旗）。

    仅对**带 @event 锚**的 todo 适用——addresses_match_event_anchored 对裸 K# 一律 False，
    裸 K# 覆盖走 loose 匹配是常态、非假覆盖，纳入会系统性误报。
    """
    amap = _material_addr_map(slug, variant)
    anchored = [t for t in (topic.get("user_todos") or [])
                if isinstance(t, dict) and t.get("covered_by")
                and any("@" in a for a in (t.get("addresses") or []))]
    bad = []
    for t in anchored:
        ok = any(topic_io.addresses_match_event_anchored(
                    t.get("addresses") or [], amap.get(mid) or [])
                 for mid in t.get("covered_by"))
        if not ok:
            bad.append(t.get("task", "?"))
    status = "na" if not anchored else ("flag" if bad else "pass")
    return [Probe(
        "CC5", "无假覆盖（addresses 粒度过粗）", "cross-cutting", "pitfall",
        status, "addresses_match_event_anchored", tier=2,
        detail=("粒度过粗疑似假覆盖: " + "; ".join(bad)) if bad else
               ("无 covered todo" if status == "na" else "覆盖事件锚一致"),
        action="人复核覆盖是否粒度过粗，按事件锚收紧或补对口料" if bad else "",
    )]


def _stage_00(slug, variant, topic) -> list[Probe]:
    out: list[Probe] = []

    # 00.Q1：prescan 跑了且未 failed
    ps = get_current_prescan_status(slug, variant)
    st = ps.get("status") if isinstance(ps, dict) else None
    out.append(Probe(
        "00.Q1", "prescan 跑了且未 failed", "00-scope", "quality",
        "na" if not st else ("fail" if st == "failed" else "pass"),
        "prescan_status", tier=1,
        detail=(f"prescan_status={st}" if st else "无 prescan 记录"),
        action="时敏论断按脆弱处理" if st == "failed" else "",
    ))

    dtext = _latest_decomposition_text(slug, variant)

    # 00.Q2：K# 可证伪 / 有数字赌注 —— ③ 纯判断，有拆解就挂旗
    out.append(Probe(
        "00.Q2", "K# 可证伪 / 有数字赌注", "00-scope", "quality",
        "na" if not dtext else "flag", "decomposition K#（代理）", tier=3,
        detail="被动层判不了可证伪性，需人看 K# 是否带数字赌注" if dtext else "无 decomposition",
        action="人复核 K# 可证伪" if dtext else "",
    ))

    # 00.Q4：命门标了置信度。spec 假设"结构化 confidence tag"，现实是完全自由表述
    # （置信度：X / v0:中→v1:X / 已解（偏空）/ 维持低置信 / 中高→高，跨 topic 三种以上格式）
    # → 与 05.Q2（无 score 字段）同理，机械判不可靠，降级为代理 flag 请人扫一眼，不伪造 fail。
    has_meridian = bool(dtext) and bool(re.search(r"命门\s*\d", dtext))
    out.append(Probe(
        "00.Q4", "命门标了置信度", "00-scope", "quality",
        "na" if not has_meridian else "flag", "decomposition 命门（自由表述代理）", tier=2,
        detail=("命门置信度为自由表述（置信度:/v→v/已解/低置信…），机械判不可靠，需人确认每条命门均标"
                if has_meridian else "无 decomposition 或无命门"),
        action="人扫一眼命门是否都标了置信度" if has_meridian else "",
    ))

    # 00.X1：废弃 Q#/V# 第三维残留 —— 诚实 na（Q# 被合法复用，机械扫描必误报）
    out.append(Probe(
        "00.X1", "无废弃 Q#/V# 第三维残留", "00-scope", "pitfall",
        "na", "文本扫 Q#/V#（不可靠）", tier=1,
        detail="Q#/V# 第三维已并入 B 轴；Q# 被 prescan/命门合法复用，机械扫描必误报——盲点显式化",
    ))
    return out


def _stage_01(slug, variant, topic) -> list[Probe]:
    out: list[Probe] = []
    active = _active_todos(topic)

    # 01.Q2：三项真·欠供都排了 todo —— 诚实 na（无法机械枚举"那三项"）
    out.append(Probe(
        "01.Q2", "三项真·欠供都排了 todo", "01-roadmap", "quality",
        "na", "roadmap ring code（无枚举锚）", tier=1,
        detail="'三项真欠供'需 roadmap 显式标注才可机械核对——盲点显式化",
    ))

    # 01.Q3：剩余 pending 只剩 hard + 无果
    pend = [t for t in active if t.get("status") == "pending"]
    bad = [t.get("task", "?") for t in pend
           if not (t.get("fetch_status") == "empty" or t.get("info_tier") == "hard")]
    out.append(Probe(
        "01.Q3", "剩余 pending 只剩 hard+无果", "01-roadmap", "quality",
        "na" if not pend else ("fail" if bad else "pass"),
        "pending fetch_status=empty / info_tier=hard", tier=1,
        detail=("可继续推进却挂着: " + "; ".join(bad)) if bad else
               ("无 pending" if not pend else "剩余 pending 均 hard/无果"),
        action="去抓或降级（CC3）" if bad else "",
    ))

    # 01.X3：ticker 填了（仅 company；ticker 空且无财报料 → flag）。
    # type=company / ticker 落在 scope.ticker（非顶层）。
    if topic.get("type") != "company":
        out.append(Probe("01.X3", "ticker 填了", "01-roadmap", "pitfall",
                         "na", "scope.ticker + manifest 财报", tier=1, detail="非 company topic"))
    else:
        ticker = ((topic.get("scope") or {}).get("ticker") or "").strip()
        fin = _has_financial_material(slug, variant)
        flag = (not ticker) and (not fin)
        out.append(Probe(
            "01.X3", "ticker 填了", "01-roadmap", "pitfall",
            "flag" if flag else "pass", "ticker + manifest 财报", tier=1,
            detail=("company 但 ticker 空且无财报料（财报管线跑不了）" if flag
                    else ("ticker 空但已有财报料" if not ticker else f"ticker={ticker}")),
            action="补 ticker" if flag else "",
        ))
    return out


def _stage_06(slug, variant) -> list[Probe]:
    """06.Q1：巡检提案是否锚环⑤ signpost/kill 而非泛新闻（② 代理 → 挂旗）。"""
    entries = _monitor_entries(slug)
    return [Probe(
        "06.Q1", "巡检对环⑤ signpost/kill 而非泛新闻", "06-monitoring", "quality",
        "na" if not entries else "flag", "monitor_queue 提案 vs signpost", tier=2,
        detail=(f"{len(entries)} 条巡检提案待人核对是否锚环⑤" if entries else "无巡检提案"),
        action="人复核提案是否对 signpost/kill" if entries else "",
    )]


def run_probes(slug: str, variant: str) -> dict:
    topic = topic_io.read_topic(slug, variant)
    try:
        gaps = detect_gaps(slug, variant)
    except Exception as e:  # 诊断层绝不因底层异常炸掉
        gaps = {"error": str(e)}

    probes: list[Probe] = []
    probes += _cross_cutting(slug, variant, topic, gaps)
    probes += _cross_cutting_extra(slug, variant, topic)
    probes += _cc5(slug, variant, topic)
    probes += _b5prime(slug, variant, topic)
    probes += _stage_00(slug, variant, topic)
    probes += _stage_01(slug, variant, topic)
    probes += _stage_02(slug, variant, topic)
    probes += _stage_03(slug, variant)
    probes += _stage_04(slug, variant, topic, gaps)
    probes += _stage_05(slug, variant, topic, gaps)
    probes += _stage_06(slug, variant)

    rows = [asdict(p) for p in probes]
    summary = {
        "fail": sum(1 for p in rows if p["status"] == "fail"),
        "flag": sum(1 for p in rows if p["status"] == "flag"),
        "pass": sum(1 for p in rows if p["status"] == "pass"),
        "na":   sum(1 for p in rows if p["status"] == "na"),
    }
    return {"slug": slug, "variant": variant, "probes": rows, "summary": summary}

"""Knowledge gap detector — zero LLM calls.

Reports (does NOT decide) which K# need more evidence, which web-search
materials are stale, and which claims have only training-knowledge basis.

LLM 自己看 report 决定继续搜还是停。
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

from prism.scripts import topic as topic_io
from prism.scripts.manifest import (
    _DEFAULT_EXCLUDED_TRIGGERED_BY,
    list_expired_web_search,
    read_manifest,
)

PRISM_ROOT = Path(__file__).resolve().parent.parent


def _addr_key(addr: str) -> str:
    return addr.split("@", 1)[0] if isinstance(addr, str) else ""


# K# 脊柱标签形如 K1 / Q3（可带 @anchor）；scope/background/fact-NN 是 prescan 占位。
_KNUM_RE = re.compile(r"^[KQ]\d+$")


def _is_knum(addr: str) -> bool:
    return bool(_KNUM_RE.match(_addr_key(addr)))


def _to_aware_dt(value) -> datetime | None:
    """把 ISO 字符串解析成 tz-aware datetime（naive 当 UTC）；失败返 None。"""
    if not value or not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _detect_relative_updated(slug: str, variant: str, topic: dict) -> list[dict]:
    """flag-only 诊断：本 topic 的 case 合成后，若某亲属（父/子）的成稿产出
    （case/thesis/sidecar）文件 mtime **晚于**本 topic case 的 last_updated → flag。

    不 gate、不进 uncovered_ks——只提示"亲属更新了，考虑复跑借用段"。受 §1.3 护栏：
    本 topic 质量校验永远本地，本 flag 不替本 topic 做质量判断。
    本 topic case 从未合成（无 last_updated）→ 无可过时的借用，返空。
    """
    our_type = topic.get("type", "")
    our_case_key = topic_io._CASE_BY_TYPE.get(our_type)
    if not our_case_key:
        return []
    state = (topic.get("outputs_state") or {}).get(our_case_key) or {}
    our_dt = _to_aware_dt(state.get("last_updated"))
    if our_dt is None:
        return []  # case 没合成过，无借用可过时

    try:
        rels = topic_io.get_relative_outputs(slug, variant)
    except Exception:
        return []

    flags: list[dict] = []
    relatives = []
    if rels.get("parent"):
        relatives.append(("parent", rels["parent"]))
    for c in rels.get("children") or []:
        relatives.append(("child", c))

    for role, rel in relatives:
        for okey, opath in (rel.get("outputs") or {}).items():
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(opath), tz=timezone.utc)
            except OSError:
                continue
            if mtime > our_dt:
                flags.append({
                    "relative_role": role,
                    "relative_slug": rel.get("slug"),
                    "relative_output": okey,
                    "relative_updated_at": mtime.isoformat(),
                    "our_output": our_case_key,
                    "our_synth_at": our_dt.isoformat(),
                })
    return flags


def _detect_ring_inputs(topic: dict, manifest: dict, min_evidence: int = 2,
                        findings: list | None = None) -> dict:
    """A 轴：决策链输入合同覆盖（**不依赖具体拆解**，可靠）。

    按 topic.type 取输入合同，逐项查"是否被实收材料的 rings 标签覆盖"：
      - 材料强制项（质性，api_satisfiable=False）无材料 → uncovered_ring_inputs（可靠红信号）
        · 其中 hard 项（三项真·欠供）若 0 < 计数 < min_evidence → thin_ring_inputs（黄，薄输入）：
          单条弱料足以让 hard 项"假装补齐"，三态把"有料但不足"从绿色里揪出来。
        · 非 hard 材料强制项维持二元（有料即覆盖）——rings 粒度比 K# 还粗，开 thin 噪声大。
      - api_satisfiable 项无材料 → 多为合成期自动拉（api_pending，非红）；
        但若需 financial/market 数据却连 ticker 都没有 → 真缺口（无法自动拉、无材料）
    legacy 守门：旧 topic（无 decomposition 且无任一材料带 rings）→ status='n/a'，不刷红误报。
    **训练知识不计入任何项**（只认实收材料 / 可拉 API）。
    """
    from prism.scripts.input_contract import (
        required_inputs, is_api_satisfiable, API_SOURCES,
    )

    topic_type = topic.get("type", "")
    items = required_inputs(topic_type)
    if not items:
        return {"ring_axis_status": "n/a", "ring_coverage": {},
                "uncovered_ring_inputs": [], "thin_ring_inputs": [],
                "api_pending_inputs": []}

    mats = manifest.get("materials") or []
    coverage: dict[str, int] = {}
    for m in mats:
        for r in m.get("rings") or []:
            coverage[r] = coverage.get(r, 0) + 1
    # finding 层 rings 并入计数（比照 B 轴 material∪findings 修法，修 F15）：
    # 02-doc 明示的补救"03 在 finding frontmatter 补 rings"原对 A 轴完全无效——
    # 旧实现只数材料层 rings。叠加 F10（材料层被标 company rings）→ industry A 轴
    # 经任何文档路径都补不绿。并入 finding rings 后该补救对 A 轴生效。
    for f in findings or []:
        for r in f.get("rings") or []:
            coverage[r] = coverage.get(r, 0) + 1

    any_rings = bool(coverage)
    has_decomp = (topic.get("decomposition") or {}).get("current_version") is not None
    if not any_rings and not has_decomp:
        # 旧 topic：拆解/rings 都没接入过 → ring 轴不适用，避免误报
        return {"ring_axis_status": "n/a",
                "ring_coverage": {it["code"]: 0 for it in items},
                "uncovered_ring_inputs": [], "thin_ring_inputs": [],
                "api_pending_inputs": []}

    scope = topic.get("scope") or {}
    has_ticker = bool(scope.get("ticker") or scope.get("extra_tickers"))
    ring_coverage: dict[str, int] = {}
    uncovered: list[dict] = []
    thin: list[dict] = []
    api_pending: list[dict] = []

    for it in items:
        code = it["code"]
        cnt = coverage.get(code, 0)
        ring_coverage[code] = cnt
        entry = {"code": code, "ring": it["ring"], "label": it["label"],
                 "served_by": it.get("served_by") or [], "hard": bool(it.get("hard"))}
        if is_api_satisfiable(it):
            if cnt > 0:
                continue
            needs_quote = bool(set(it.get("served_by") or []) & {"financial_data", "market_data"})
            if needs_quote and not has_ticker:
                entry["reason"] = "无材料且无 ticker，无法自动拉数"
                uncovered.append(entry)
            else:
                api_pending.append(entry)  # 合成期自动拉，信息项非红
        else:
            # 材料强制项
            if cnt == 0:
                entry["reason"] = "材料强制项，无任何材料覆盖"
                uncovered.append(entry)
            elif it.get("hard") and cnt < min_evidence:
                # hard 项有料但不足阈值 → 薄输入（黄），堵单条弱料假装补齐
                entry["count"] = cnt
                entry["min_evidence"] = min_evidence
                thin.append(entry)
            # else: 覆盖充分（非 hard 有料 / hard ≥ 阈值）

    return {"ring_axis_status": "active", "ring_coverage": ring_coverage,
            "uncovered_ring_inputs": uncovered, "thin_ring_inputs": thin,
            "api_pending_inputs": api_pending}


def detect_gaps(
    slug: str,
    variant: str,
    min_evidence: int = 2,
) -> dict:
    """Detect knowledge gaps in a topic's research.

    双轴：
      A 轴（ring 输入覆盖，**不依赖拆解**，可靠）：决策链输入合同各类目是否被实收材料覆盖。
      B 轴（K# 覆盖，thesis 脊柱）：uncovered_ks / thin_evidence（B 轴单独兜不住命门正确性，
            靠 04 写作 delta 重拆补）。

    Returns:
        {
            'topic': {slug, variant, thesis_version},
            # B 轴（K# 脊柱）
            'uncovered_ks':       [K#, ...],     # 0 evidence
            'thin_evidence':      [K#, ...],     # < min_evidence
            'evidence_count':     {K#: int},
            # A 轴（ring 输入合同）
            'ring_axis_status':   'active' | 'n/a',   # 'n/a' = 旧 topic 守门
            'ring_coverage':      {code: int},        # 各合同类目的材料计数
            'uncovered_ring_inputs': [{code,ring,label,served_by,hard,reason}, ...],
            'thin_ring_inputs':      [{code,ring,label,served_by,hard,count,min_evidence}, ...],
                                  # hard 材料强制项有料但 < min_evidence（黄，薄输入）
            'api_pending_inputs':    [{code,ring,label,served_by}, ...],  # 合成期自动拉，非红
            # 其它
            'expired_web_materials': [...],      # web-search > 90d
            'training_only_claims': [...],       # placeholder, requires baseline
            'relative_updated': [...],           # 亲属成稿产出比本 topic case 新（flag-only）
            'prescan_untagged': [...],           # thesis 已就位但材料只挂 scope/占位、缺 K#（flag-only）
            'single_source': [...],              # K# 覆盖达标但来源单一(单 source_type/域名)，注意力路由器非裁决
        }
    """
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        return {"error": f"topic not found: {slug}/{variant}"}

    thesis_block = topic.get("thesis") or {}
    cur_v = thesis_block.get("current_version")

    ks: list[str] = []
    if cur_v is not None:
        try:
            from prism.scripts.outputs import extract_killer_questions
            ks = list(extract_killer_questions(slug, variant, cur_v))
        except Exception:
            ks = []

    try:
        manifest = read_manifest(slug, variant)
    except FileNotFoundError:
        manifest = {"materials": []}

    # B 轴证据计数：按 K# 统计"不同来源材料"数（mat_id 去重）。
    # 证据在两层打 addresses 标签——manifest 材料层（粗）+ findings 层（细，03 抽取产出）；
    # 取并集、按来源 mat_id 去重（同一材料与其 finding 不重复计）。
    # 修复旧 bug：旧实现只数材料层 addresses，漏掉只在 findings 层打标的 topic（B 轴误报 K# 全 0）。
    # 含 reuse（父 parent_materials）findings：父证据经 parent_materials 已加载进合成上下文，是
    #   可用证据；reuse 护栏（本地复核/降信心）是合成期职责（funnel §1.3 + critic），非 gap 检测职责。
    #   实测多数 arena/company topic 的 K# 覆盖正来自父级 findings——排除 reuse 会让其误报全红。
    ev_sources: dict[str, set] = {k: set() for k in ks}
    mat_meta: dict[str, dict] = {}
    for m in manifest.get("materials") or []:
        mid = m.get("id") or f"mat:{m.get('filename')}"
        mat_meta[mid] = {
            "source_type": m.get("source_type"),
            "domain": (m.get("search_meta") or {}).get("domain"),
        }
        for a in (m.get("addresses") or []):
            k = _addr_key(a)
            if k in ev_sources:
                ev_sources[k].add(mid)
    findings: list = []
    try:
        from prism.scripts.findings import list_all_findings
        findings = list(list_all_findings(slug, variant))
    except Exception:
        findings = []
    for f in findings:
        fid = f.get("mat_id") or str(f.get("path"))
        for a in (f.get("addresses") or []):
            k = _addr_key(a)
            if k in ev_sources:
                ev_sources[k].add(fid)
    evidence_count: dict[str, int] = {k: len(v) for k, v in ev_sources.items()}

    uncovered = [k for k in ks if evidence_count[k] == 0]
    thin = [k for k in ks if 0 < evidence_count[k] < min_evidence]

    # 单源 tripwire（**注意力路由器，非充分性裁决**）：覆盖达标(≥min_evidence、不在
    # uncovered/thin)但支撑材料塌缩到单一 source_type 或单一域名 → flag。它只能廉价地把
    # "假绿候选"(多条但近亲)指给 critic 去**读内容**判是否真独立，不替代质性判断。
    # 来源类型全未知则不判（无从塌缩）。与 uncovered/thin 互斥：只扫绿区。
    single_source: list[dict] = []
    for k in ks:
        cnt = evidence_count[k]
        if cnt < min_evidence:
            continue  # uncovered/thin 已另报，不重复
        stypes = {mat_meta.get(mid, {}).get("source_type") for mid in ev_sources[k]}
        stypes.discard(None)
        domain_list = [mat_meta.get(mid, {}).get("domain") for mid in ev_sources[k]]
        domain_set = {d for d in domain_list if d}
        reasons: list[str] = []
        if len(stypes) == 1:
            reasons.append(f"全部来自单一来源类型 {next(iter(stypes))}")
        # 单域名仅在"每条都带域名(全 web)且塌缩到一个"时才报，避免 web+非web 混料误判
        if cnt >= 2 and len(domain_set) == 1 and all(domain_list):
            reasons.append(f"全部来自单一域名 {next(iter(domain_set))}")
        if reasons:
            single_source.append({
                "k": k, "count": cnt,
                "source_types": sorted(stypes),
                "domains": sorted(domain_set),
                "reason": "；".join(reasons),
            })

    # 坑③ prescan-addresses-scope：thesis 已就位，但仍有材料只挂 scope/background/fact-*
    # 等 prescan 占位、无任何 K# 脊柱标签 → 自动点名提醒补标（flag-only，不 gate）。
    # thesis 未就位（cur_v is None）时 prescan 占位是正常起手态，不点名。
    prescan_untagged: list[dict] = []
    if cur_v is not None:
        for m in manifest.get("materials") or []:
            # Role α prescan 料（00/01 prescan 入库）合法只挂 scope 占位且豁免抽取——
            # 不点名待补 K#（否则每轮报永久假缺口，cn-adc 实测噪音）。
            tb = (m.get("search_meta") or {}).get("triggered_by", "unknown")
            if tb in _DEFAULT_EXCLUDED_TRIGGERED_BY:
                continue
            addrs = m.get("addresses") or []
            if addrs and not any(_is_knum(a) for a in addrs):
                prescan_untagged.append({
                    "id": m.get("id"),
                    "filename": m.get("filename"),
                    "addresses": list(addrs),
                })

    expired = list_expired_web_search(slug, variant) if manifest.get("materials") else []

    training_only: list[str] = []

    relative_updated = _detect_relative_updated(slug, variant, topic)

    ring = _detect_ring_inputs(topic, manifest, min_evidence, findings=findings)

    # auto-fetch 规约可观测：欠账（未/失败尝试）+ 待用户处置的 empty。
    # 谓词须与 topic.pending_unfetched_todos / empty_undecided_todos 保持一致：
    #   debt = active & fetch_status∈{unattempted,error} & 非 reverse-check
    #   empty_pending = active & fetch_status='empty' & disposition='undecided'
    autofetch_debt: list[dict] = []
    empty_pending: list[dict] = []
    for td in (topic.get("user_todos") or []):
        if not isinstance(td, dict):
            continue
        if td.get("status") not in ("pending", "in_progress"):
            continue
        fs = td.get("fetch_status", "unattempted")
        if fs in ("unattempted", "error") and "reverse-check" not in (td.get("source_hint") or ""):
            autofetch_debt.append({
                "task": td.get("task", ""),
                "fetch_status": fs,
                "info_tier": td.get("info_tier", "public"),
                "addresses": list(td.get("addresses") or []),
            })
        if fs == "empty" and td.get("disposition", "undecided") == "undecided":
            empty_pending.append({
                "task": td.get("task", ""),
                "info_tier": td.get("info_tier", "public"),
                "addresses": list(td.get("addresses") or []),
            })

    return {
        "topic": {
            "slug": slug,
            "variant": variant,
            "thesis_version": cur_v,
        },
        "uncovered_ks": uncovered,
        "thin_evidence": thin,
        "evidence_count": evidence_count,
        "ring_axis_status": ring["ring_axis_status"],
        "ring_coverage": ring["ring_coverage"],
        "uncovered_ring_inputs": ring["uncovered_ring_inputs"],
        "thin_ring_inputs": ring["thin_ring_inputs"],
        "api_pending_inputs": ring["api_pending_inputs"],
        "expired_web_materials": [
            {"id": m["id"], "filename": m["filename"],
             "expire_at": (m.get("search_meta") or {}).get("expire_at")}
            for m in expired
        ],
        "training_only_claims": training_only,
        "relative_updated": relative_updated,
        "prescan_untagged": prescan_untagged,
        "single_source": single_source,
        "autofetch_debt": autofetch_debt,
        "empty_pending_decision": empty_pending,
    }


def format_summary(report: dict) -> str:
    """Human-readable summary for 主 agent 在对话里展示给用户。"""
    if "error" in report:
        return f"⚠ {report['error']}"
    lines = []
    t = report["topic"]
    lines.append(
        f"📊 Gap report: {t['slug']}/{t['variant']} "
        f"(thesis_v{t['thesis_version']})"
    )
    if report["uncovered_ks"]:
        lines.append(
            f"  ❌ 0 evidence: {', '.join(report['uncovered_ks'])}"
        )
    if report["thin_evidence"]:
        ec = report["evidence_count"]
        thin_str = ", ".join(f"{k}({ec[k]})" for k in report["thin_evidence"])
        lines.append(f"  ⚠ thin: {thin_str}")
    # A 轴：ring 输入合同
    uri = report.get("uncovered_ring_inputs") or []
    if uri:
        def _fmt(e):
            mark = "🔴" if e.get("hard") else ""
            return f"{e['code']}(环{e['ring']}{mark})"
        lines.append("  🧩 缺输入: " + ", ".join(_fmt(e) for e in uri))
    thin_ri = report.get("thin_ring_inputs") or []
    if thin_ri:
        lines.append(
            "  🟡 薄输入(hard): "
            + ", ".join(f"{e['code']}({e['count']}/{e['min_evidence']})" for e in thin_ri)
        )
    api_pending = report.get("api_pending_inputs") or []
    if api_pending:
        lines.append(
            "  📈 结构化输入(API自供,非缺口): "
            + ", ".join(e["code"] for e in api_pending)
        )
        lines.append(
            "     └ 合成期由环①/②按需取数(缓存命中则免拉)，不计材料覆盖、无需补料"
        )
    if report.get("ring_axis_status") == "n/a":
        lines.append("  🧩 ring 轴: n/a（旧 topic，未接入拆解/rings）")
    if report["expired_web_materials"]:
        lines.append(
            f"  ⏰ expired web-search: {len(report['expired_web_materials'])} 条 (>90d)"
        )
    rel_upd = report.get("relative_updated") or []
    if rel_upd:
        lines.append(
            f"  🔗 relative-updated: {len(rel_upd)} 条（亲属产出比本 topic case 新，考虑复跑借用段）"
        )
    untagged = report.get("prescan_untagged") or []
    if untagged:
        lines.append(
            f"  🏷 待补 K# 标签: {len(untagged)} 条（thesis 已就位，材料仍只挂 prescan 占位；"
            f"跑 backfill_addresses_by_mapping / retag_by_filename 补 K#）"
        )
    ss = report.get("single_source") or []
    if ss:
        lines.append(
            "  🟠 单源(覆盖达标但来源单一·注意力路由器非裁决,需 critic 读内容核是否真独立): "
            + ", ".join(f"{e['k']}({e['count']}条·{e['reason']})" for e in ss)
        )
    # auto-fetch 规约：欠账与待用户决策（绝不隐藏，每个 checkpoint 都现）
    debt = report.get("autofetch_debt") or []
    if debt:
        n_err = sum(1 for d in debt if d.get("fetch_status") == "error")
        n_un = len(debt) - n_err
        lines.append(
            f"  🟤 auto-fetch 欠账: {len(debt)} 条（error={n_err} 需重试 / unattempted={n_un} 需首次尝试）"
        )
    empty_pending = report.get("empty_pending_decision") or []
    if empty_pending:
        lines.append(
            f"  🟠 待你决定是否跳过: {len(empty_pending)} 条（自动抓已确认公开无源 → waive 跳过 / will_collect 我来收）"
        )
    if not (report["uncovered_ks"] or report["thin_evidence"]
            or report["expired_web_materials"] or rel_upd or uri or thin_ri
            or untagged or ss or debt or empty_pending):
        lines.append("  ✅ no gaps detected")
    return "\n".join(lines)


def snapshot_gaps(slug: str, variant: str) -> dict:
    """进入 stage 时的精简 gap 快照（B1 承重墙用）。失败返回空，绝不抛。

    供 topic.set_stage 在切换 stage 时盖进 stage_history[N].gap_snapshot，
    让被动观测层算"红项被处理 vs 红着硬升"（02.Q2/Q3）。spec: observability.md §4.1。
    """
    try:
        g = detect_gaps(slug, variant)
    except Exception:
        return {}
    if "error" in g:
        return {}
    return {
        "uncovered_ks": list(g.get("uncovered_ks") or []),
        "uncovered_ring_inputs": [i.get("code") for i in (g.get("uncovered_ring_inputs") or [])],
        "autofetch_debt": len(g.get("autofetch_debt") or []),
        "empty_pending_decision": len(g.get("empty_pending_decision") or []),
    }

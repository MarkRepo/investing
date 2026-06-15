"""Prism research system views — /prism.

Navigation: topic → model → content
  /prism                              — all topics (grouped by slug)
  /prism/dashboard                    — investment decision dashboard
  /prism/{slug}                       — variant picker (redirect if only 1)
  /prism/{slug}/compare/{output_key}  — side-by-side model comparison
  /prism/{slug}/{variant}             — topic detail for a model
  /prism/{slug}/{variant}/{output_key} — output viewer
"""
from __future__ import annotations

import random
from collections import defaultdict

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.config import APP_TEMPLATES_DIR
from prism.scripts import manifest as manifest_io
from prism.scripts import outputs as outputs_io
from prism.scripts import topic as topic_io
from prism.scripts import wechat_export as wechat_export

router = APIRouter(prefix="/prism", tags=["prism"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


def _fmt_shanghai(iso: str | None) -> str:
    """ISO 时间串 → 上海时区 'YYYY-MM-DD HH:MM'。存储为 UTC（macro_registry._now_iso），展示按 Asia/Shanghai。"""
    if not iso:
        return ""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    try:
        return datetime.fromisoformat(iso).astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(iso)[:16].replace("T", " ")


templates.env.filters["shanghai"] = _fmt_shanghai


def _scope_ticker(scope: dict) -> str:
    """Extract display ticker from scope dict."""
    raw = scope.get("ticker", "")
    if not raw:
        return ""
    # If ticker is "SZSE_000426" format, return just the code part
    if "_" in raw:
        return raw.split("_", 1)[1]
    return raw


def _make_market_ticker(scope: dict) -> str:
    """Build "MARKET_TICKER" format for price/financials routes.

    Handles both new format (separate ticker + market fields) and
    old format (ticker already contains market prefix like "SZSE_000426").
    """
    ticker = scope.get("ticker", "")
    if not ticker:
        return ""
    # Old format: ticker already contains underscore
    if "_" in ticker:
        return ticker
    # New format: market is separate field
    market = scope.get("market", "")
    if market and ticker:
        return f"{market}_{ticker}"
    return ""

# Output key → label mapping for dropdowns（决策链产出；旧 8 维 01-07 已退休、不再列）
_OUTPUT_OPTIONS = [
    ("00_primer", "领域入门"),
    ("c_investment_case", "投资 case（决策链）"),
    ("i_industry_case", "行业 case（决策链）"),
    ("a_arena_case", "竞技场 case（决策链）"),
    ("m_regime_read", "宏观体制读数"),
    ("08_living_feed", "信息流时间线"),
    ("industry_to_arenas", "产业→竞技场选拔"),
]


_TYPE_LABEL = {"company": "公司", "arena": "竞技场", "industry": "行业", "macro": "宏观层"}
_TYPE_EMOJI = {"company": "🏢", "arena": "🥊", "industry": "🏭", "macro": "🌐"}
# 树内排序：行业 < 竞技场 < 公司 < 宏观层（同级内再按 created 倒序）
_TYPE_ORDER = {"industry": 0, "arena": 1, "company": 2, "macro": 3}


def _sort_topic_nodes(lst: list[dict]) -> None:
    """同级排序：先 created 倒序，再按类型档（稳定排序保留同档时序）。原地排序。"""
    lst.sort(key=lambda c: c["created"], reverse=True)
    lst.sort(key=lambda c: _TYPE_ORDER.get(c["type"], 9))


def build_topic_forest(all_topics: list[dict]) -> dict:
    """把 list_topics() 的扁平 variant 列表收成 产业→竞技场→公司 森林。

    每个 slug 一个节点（信息取首个 variant，多 variant 收成芯片列表），按
    parent_topic 挂树。无父级（或父级 slug 不存在）的为根：行业 / 有子节点的根
    进 tree_roots；其余无子散户主题进 standalone——不丢任何节点。

    返回 {tree_roots, standalone, total}，纯函数、无 I/O，便于测试。
    """
    grouped: dict[str, list[dict]] = defaultdict(list)
    for t in all_topics:
        grouped[t["slug"]].append(t)

    nodes: dict[str, dict] = {}
    for slug, variants in grouped.items():
        info = variants[0]
        topic_type = info.get("type", "industry")
        scope = info.get("scope") or {}
        nodes[slug] = {
            "slug": slug,
            "display_name": info.get("display_name", slug),
            "type": topic_type,
            "type_label": _TYPE_LABEL.get(topic_type, topic_type),
            "emoji": _TYPE_EMOJI.get(topic_type, "•"),
            "parent": info.get("parent_topic"),
            "created": info.get("created", ""),
            "ticker": _scope_ticker(scope),
            "market_ticker": _make_market_ticker(scope),
            "children": [],
            "variants": [{
                "name": v["variant"],
                "stage": v.get("stage", ""),
                "status": v.get("status", ""),
                # 读者向阶段进度（替代曾经在数退休产出槽的 n/m 数字）
                "progress": topic_io.stage_progress(v.get("stage", "")),
                # daily-monitor 引入未消化重大变更 → chip 叠加「待复评」覆盖标记
                # （不改 stage，跑过 04/05 后 pending_review_unresolved 自动判消）
                "needs_review": bool(topic_io.pending_review_unresolved(v)),
            } for v in variants],
        }

    # 挂树：parent 存在则归到 parent.children，否则（None 或指向缺失 slug）为根
    roots: list[dict] = []
    for node in nodes.values():
        parent = node["parent"]
        if parent and parent in nodes:
            nodes[parent]["children"].append(node)
        else:
            roots.append(node)

    for node in nodes.values():
        _sort_topic_nodes(node["children"])

    # 根分区：行业 or 有子 → 树区；其余无子散户 → 独立主题区
    tree_roots = [r for r in roots if r["type"] == "industry" or r["children"]]
    standalone = [r for r in roots if r["type"] != "industry" and not r["children"]]
    _sort_topic_nodes(tree_roots)
    _sort_topic_nodes(standalone)
    return {"tree_roots": tree_roots, "standalone": standalone, "total": len(nodes)}


@router.get("")
def prism_index(request: Request):
    """List all topics as an 产业→竞技场→公司 tree, linked via topic.yaml `parent_topic`."""
    forest = build_topic_forest(topic_io.list_topics())
    return templates.TemplateResponse(request, "prism/index.html", forest)


@router.get("/dashboard")
def prism_dashboard(request: Request, refresh: bool = False):
    """Investment decision dashboard — /prism/dashboard."""
    from pathlib import Path
    dashboard_path = Path(__file__).resolve().parent.parent.parent / "prism" / "dashboard.md"

    if refresh or not dashboard_path.exists():
        try:
            from prism.scripts.dashboard import build
            build()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Dashboard build failed: {e}")

    if not dashboard_path.exists():
        raise HTTPException(status_code=404, detail="dashboard.md not found — try ?refresh=true")

    raw = dashboard_path.read_text(encoding="utf-8")
    # Strip leading h1 — the template renders its own title
    lines = raw.splitlines()
    if lines and lines[0].startswith("# "):
        raw = "\n".join(lines[1:]).lstrip("\n")
    body_html = outputs_io.render_markdown(raw)

    from prism.scripts import monitor
    pending = [p for p in monitor.load_queue() if p.get("status") == "awaiting_confirm"]

    return templates.TemplateResponse(
        request,
        "prism/dashboard.html",
        {
            "body_html": body_html,
            "pending_proposals": pending,
            "watchlist": _enrich_watchlist(monitor.load_watchlist()),
        },
    )


def _enrich_watchlist(watches: list[dict]) -> list[dict]:
    """给每条 watch 配人读标签(把 locator hash 还原成事件名),供 dashboard 列表展示。"""
    from prism.scripts import monitor, sidecar_edit
    out = []
    for w in watches:
        slug, variant = w.get("slug"), w.get("variant")
        scope, kind, loc = w.get("scope"), w.get("kind"), w.get("locator")
        label = "整个 topic（全部 event + 价格破位）"
        if scope == "event":
            if kind == "price":
                label = "价格破位"
            else:
                sidecar = monitor._load_company_sidecar(slug, variant) or {}
                if kind == "signpost":
                    for sp in sidecar.get("signposts") or []:
                        if sidecar_edit.signpost_locator(sp.get("date"), sp.get("event", "")) == loc:
                            label = f"路标 · {sp.get('date')} {sp.get('event')}"
                            break
                    else:
                        label = f"路标 · {loc}（已不在 sidecar）"
                elif kind == "kill":
                    k = next((k for k in sidecar.get("kill_criteria") or [] if k.get("id") == loc), None)
                    label = f"Kill · {k.get('description')}" if k else f"Kill · {loc}（已不在 sidecar）"
        out.append({**w, "label": label})
    return out


@router.get("/{slug}")
def prism_topic(request: Request, slug: str):
    """Show variant picker for a topic, or redirect if only one variant."""
    variants = topic_io.list_variants(slug)
    if not variants:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r} not found")
    if len(variants) == 1:
        return RedirectResponse(
            url=f"/prism/{slug}/{variants[0]}",
            status_code=302,
        )

    # Load each variant's topic.yaml for summary
    variant_data = []
    for v in variants:
        try:
            data = topic_io.read_topic(slug, v)
            variant_data.append({
                "name": v,
                "stage": data.get("stage", ""),
                "status": data.get("status", ""),
                "progress": topic_io.stage_progress(data.get("stage", "")),
                "needs_review": bool(topic_io.pending_review_unresolved(data)),
                "canonical": bool(data.get("canonical")),
            })
        except Exception:
            variant_data.append({"name": v, "stage": "", "status": "",
                                 "progress": topic_io.stage_progress(""),
                                 "canonical": False})

    # 从首个 variant 读 display_name + type；type 决定"对比产出"默认指向哪份 case
    # （决策链按 type 三选一；旧的硬编码 01_business_panorama 已随旧 8 维退休删除）。
    display_name = slug
    topic_type = "industry"
    try:
        _data = topic_io.read_topic(slug, variants[0])
        display_name = _data.get("display_name", slug)
        topic_type = _data.get("type", "industry")
    except Exception:
        pass
    _CASE_BY_TYPE = {
        "company": "c_investment_case",
        "industry": "i_industry_case",
        "arena": "a_arena_case",
        "macro": "m_regime_read",
    }
    compare_key = _CASE_BY_TYPE.get(topic_type, "08_living_feed")

    return templates.TemplateResponse(
        request,
        "prism/variants.html",
        {
            "slug": slug,
            "display_name": display_name,
            "variants": variant_data,
            "compare_key": compare_key,
        },
    )


@router.get("/{slug}/compare/{output_key}")
def prism_compare(
    request: Request,
    slug: str,
    output_key: str,
    source1: str = Query(default=""),
    source2: str = Query(default=""),
):
    """Side-by-side comparison of the same output from two models."""
    all_variants = topic_io.list_variants(slug)
    if not all_variants:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r} not found")

    # Default: pick first two variants if not specified
    if not source1 and len(all_variants) >= 1:
        source1 = all_variants[0]
    if not source2 and len(all_variants) >= 2:
        source2 = all_variants[1]
    if not source1 or not source2:
        raise HTTPException(status_code=400, detail="Need at least 2 variants to compare")

    # Validate variants exist
    if source1 not in all_variants:
        raise HTTPException(status_code=404, detail=f"Variant {source1!r} not found")
    if source2 not in all_variants:
        raise HTTPException(status_code=404, detail=f"Variant {source2!r} not found")

    # Load topic display name
    try:
        topic = topic_io.read_topic(slug, source1)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{source1!r} not found")

    # Load both outputs
    html1 = html2 = None
    meta1 = meta2 = None
    try:
        html1 = outputs_io.read_output_html(slug, output_key, source1)
        outputs1 = outputs_io.list_outputs(slug, source1)
        meta1 = next((o for o in outputs1 if o["key"] == output_key), None)
    except FileNotFoundError:
        pass

    try:
        html2 = outputs_io.read_output_html(slug, output_key, source2)
        outputs2 = outputs_io.list_outputs(slug, source2)
        meta2 = next((o for o in outputs2 if o["key"] == output_key), None)
    except FileNotFoundError:
        pass

    # Find output label
    output_label = output_key
    for key, label in _OUTPUT_OPTIONS:
        if key == output_key:
            output_label = label
            break

    return templates.TemplateResponse(
        request,
        "prism/compare.html",
        {
            "slug": slug,
            "output_key": output_key,
            "output_label": output_label,
            "source1": source1,
            "source2": source2,
            "topic": topic,
            "html1": html1,
            "html2": html2,
            "meta1": meta1,
            "meta2": meta2,
            "all_variants": all_variants,
            "output_options": _OUTPUT_OPTIONS,
        },
    )


@router.get("/{slug}/{variant}")
def prism_detail(request: Request, slug: str, variant: str):
    """Topic detail dashboard for a specific model variant."""
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")

    outputs = outputs_io.list_outputs(slug, variant)

    try:
        manifest = manifest_io.read_manifest(slug, variant)
        mat_counts = manifest_io.material_count(slug, variant)
        mineru_counts = manifest_io.mineru_state_counts(slug, variant)
    except FileNotFoundError:
        manifest = {"materials": []}
        mat_counts = {"total": 0, "processed": 0, "unprocessed": 0, "self_total": 0, "parent_total": 0}
        mineru_counts = {}

    all_variants = topic_io.list_variants(slug)
    thesis_versions = outputs_io.list_thesis_files(slug, variant)

    # P4 coverage: 基于 current_version thesis 里的 K# 计算 todo 覆盖情况
    coverage = None
    roadmap_coverage = None
    manifest_coverage = None
    k_status = None
    cur_v = (topic.get("thesis") or {}).get("current_version")
    if cur_v is not None:
        ks = outputs_io.extract_killer_questions(slug, variant, cur_v)
        if ks:
            coverage = topic_io.thesis_coverage(slug, variant, ks)
            coverage["all_keys"] = ks
            # G5: K# 验证进度（仅 v>=1 才有意义；v0 全部按 unverified）
            k_status = outputs_io.extract_k_status(slug, variant, cur_v)
        # roadmap coverage（计划）
        roadmap_coverage = outputs_io.validate_roadmap_thesis_coverage(slug, variant, cur_v)
        # manifest coverage（实际收集）
        manifest_coverage = outputs_io.validate_manifest_coverage(slug, variant, cur_v)

    monitor_ctx = _monitor_context(slug, variant)

    # 横切（3a）：company 详情页显示宏观背景印章（含 stale 提示）。非 company 不显示。
    macro_stamp = None
    if topic.get("type") == "company":
        from prism.scripts import macro_xcut
        macro_stamp = macro_xcut.read_macro_stamp(slug, variant) or None

    # industry/arena 的 05 评审非强制——合成完(04-post-synthesis/05-critic-review)即可
    # 在 web 直接点「完成」跳 done(对话里跑评审是另一条路)。company 必须真评审,无此按钮。
    can_mark_done = (
        topic.get("type") in ("industry", "arena")
        and topic.get("stage") in ("04-post-synthesis", "05-critic-review")
    )

    return templates.TemplateResponse(
        request,
        "prism/detail.html",
        {
            "topic": topic,
            "can_mark_done": can_mark_done,
            "macro_stamp": macro_stamp,
            "outputs": outputs,
            "manifest": manifest,
            "mat_counts": mat_counts,
            "variant": variant,
            "all_variants": all_variants,
            "thesis_versions": thesis_versions,
            "coverage": coverage,
            "roadmap_coverage": roadmap_coverage,
            "manifest_coverage": manifest_coverage,
            "k_status": k_status,
            "mineru_counts": mineru_counts,
            "prism_key": _make_market_ticker(topic.get("scope") or {}),
            "now_iso": _now_iso_z(),
            "stage_progress": topic_io.stage_progress(topic.get("stage", "")),
            "stage_phase_names": topic_io.STAGE_PHASE_NAMES,
            **monitor_ctx,
        },
    )


@router.post("/{slug}/{variant}/mark-done")
def prism_mark_done(slug: str, variant: str):
    """industry/arena 评审可选——用户在 web 点「完成」直接置 stage=done。

    守卫:仅 industry/arena 且当前处于合成完/评审阶段才放行;company 必须走真评审
    (05 verdict=approve)才能 done,故拒绝。完成后 303 重定向回详情页。
    """
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")
    if topic.get("type") not in ("industry", "arena"):
        raise HTTPException(status_code=400, detail="仅 industry/arena 可在 web 直接完成;company 须走 05 评审")
    if topic.get("stage") not in ("04-post-synthesis", "05-critic-review"):
        raise HTTPException(status_code=400, detail=f"当前阶段 {topic.get('stage')!r} 不可直接完成(需先完成合成)")
    topic_io.set_stage(slug, "done", variant)
    return RedirectResponse(url=f"/prism/{slug}/{variant}", status_code=303)


@router.post("/{slug}/{variant}/set-canonical")
def prism_set_canonical(slug: str, variant: str):
    """把此 variant 标为 dashboard / monitor 默认引用的 canonical。

    同 slug 其他 variant 的 canonical 字段会被清掉（set_canonical 内部处理）。
    成功后重建 dashboard.md 并 303 回 variants 选择页。
    """
    try:
        topic_io.set_canonical(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")
    try:
        from prism.scripts.dashboard import build
        build()
    except Exception:
        # dashboard 重建失败不影响 canonical 设置本身——下次访问 /prism/dashboard 会再触发
        pass
    return RedirectResponse(url=f"/prism/{slug}", status_code=303)


def _monitor_context(slug: str, variant: str) -> dict:
    """监控关注上下文:本 topic 的可监控 event(带 locator)+ 当前关注状态。

    供 detail.html 渲染两级关注控件(topic 级勾选 + 每条 signpost/kill 勾选)。
    """
    from prism.scripts import monitor, sidecar_edit
    watches = [w for w in monitor.load_watchlist() if w.get("slug") == slug]
    topic_watched = any(w.get("scope") == "topic" for w in watches)
    watched_locators = {
        w.get("locator") for w in watches
        if w.get("scope") == "event" and w.get("locator")
    }
    signposts, kills = [], []
    sidecar = monitor._load_company_sidecar(slug, variant)
    if sidecar:
        for sp in sidecar.get("signposts") or []:
            loc = sidecar_edit.signpost_locator(sp.get("date"), sp.get("event", ""))
            signposts.append({
                "locator": loc, "date": str(sp.get("date")), "event": sp.get("event"),
                "triggered": sp.get("triggered"),
                "watched": topic_watched or loc in watched_locators,
            })
        for k in sidecar.get("kill_criteria") or []:
            kid = k.get("id")
            kills.append({
                "locator": kid, "description": k.get("description"),
                "status": k.get("status"),
                "watched": topic_watched or kid in watched_locators,
            })
    pending_review = None
    try:
        from prism.scripts.topic import get_pending_thesis_review
        pending_review = get_pending_thesis_review(slug, variant)
    except Exception:
        pending_review = None
    return {
        "monitor_topic_watched": topic_watched,
        "monitor_signposts": signposts,
        "monitor_kills": kills,
        "pending_thesis_review": pending_review,
    }


def _now_iso_z() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


@router.get("/{slug}/{variant}/diag")
def prism_diag(request: Request, slug: str, variant: str):
    """诊断 / debug tab：workflow 链路上的中间产物 + 实时 gap 诊断。

    读者向详情页（prism_detail）只展示最终产物 + thesis；这里把拆解、收料来源
    证据、逐料抽取、gap_detector、critic 裁决全部铺开，供 debug 与可审计。
    每段缺失即优雅降级，只要 topic 存在就不 404。
    """
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")
    # 宏观层不走 拆解→收料→抽取→gap→critic 工作流，诊断页对它全是空壳；其等价诊断视图是「输入源」表
    if topic.get("type") == "macro":
        raise HTTPException(status_code=404, detail="宏观层不适用诊断 / debug（等价视图为输入源表 macro-inputs）")

    # ① 拆解 decomposition（取最新版；保留版本列表供切换）
    decomp_versions = outputs_io.list_decomposition_files(slug, variant)
    decomp_html = None
    decomp_version = None
    if decomp_versions:
        decomp_version = decomp_versions[-1]
        decomp_html = outputs_io.read_decomposition_html(slug, variant, decomp_version)

    # ② roadmap 计划原文
    roadmap_text = outputs_io.read_roadmap_yaml(slug, variant)

    # ③ 收料·来源证据
    try:
        manifest = manifest_io.read_manifest(slug, variant)
    except FileNotFoundError:
        manifest = {"materials": []}
    from prism.scripts.manifest import list_expired_web_search
    expired_ids = {m.get("id") for m in list_expired_web_search(slug, variant)} if manifest.get("materials") else set()

    # ④ 逐料 findings
    findings = outputs_io.collect_findings(slug, variant)
    # ③ 行「是否有抽取笔记」判定集：findings 文件名是 findings_mat-XXX，剥前缀对回来源 id
    finding_ids = {f["mat_id"].replace("findings_", "") for f in findings["files"]}

    # ③′ 复用父级资料（不在本 manifest，从 topic.yaml parent_materials 读父 manifest 渲染）
    parent_materials = outputs_io.collect_parent_materials(slug, variant)

    # ⑤ gap_detector 实时诊断
    from prism.scripts.gap_detector import detect_gaps
    try:
        gap = detect_gaps(slug, variant)
    except Exception as e:  # 诊断本身失败不该拖垮整页
        gap = {"error": str(e)}

    # ⑥ critic 裁决层（05-critic-review.md + case 头承重充分性横幅）
    critic = outputs_io.collect_critic_artifacts(slug, variant)

    # 合成阶段内部备忘（canonical 辅助产物）
    synthesis_brief = outputs_io.read_synthesis_brief_html(slug, variant)

    return templates.TemplateResponse(
        request,
        "prism/diagnostics.html",
        {
            "topic": topic,
            "variant": variant,
            "decomp_versions": decomp_versions,
            "decomp_version": decomp_version,
            "decomp_html": decomp_html,
            "roadmap_text": roadmap_text,
            "manifest": manifest,
            "expired_ids": expired_ids,
            "findings": findings,
            "finding_ids": finding_ids,
            "parent_materials": parent_materials,
            "synthesis_brief": synthesis_brief,
            "gap": gap,
            "critic": critic,
            "material_trust": outputs_io.material_trust,
        },
    )


@router.get("/{slug}/{variant}/checkup")
def prism_checkup(request: Request, slug: str, variant: str):
    """体检 tab：被动可观测层（observability）—— 流程质量探针机械重建。

    纯被动·零 LLM：从已有产物残渣算 pass/fail/flag/na，不重跑研究、不调模型。
    topic 不存在则 404；探针自身缺残留优雅降级为 na，整层失败也不拖垮整页。
    spec: observability.md §6。
    """
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")
    # 宏观层无标准工作流残渣，体检探针几乎全 na；其等价诊断视图是「输入源」表
    if topic.get("type") == "macro":
        raise HTTPException(status_code=404, detail="宏观层不适用体检（等价视图为输入源表 macro-inputs）")
    from prism.scripts.observability_render import build_view
    try:
        view = build_view(slug, variant)
    except Exception as e:  # 体检本身失败不该拖垮整页
        view = {
            "summary": {"pass": 0, "fail": 0, "flag": 0, "na": 0},
            "groups": [], "flags": [], "badge": {}, "error": str(e),
        }
    return templates.TemplateResponse(
        request,
        "prism/checkup.html",
        {"topic": topic, "variant": variant, "view": view},
    )


@router.get("/{slug}/{variant}/web-search-log")
def prism_web_search_log(request: Request, slug: str, variant: str):
    """Render the web-search log for a topic variant."""
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")
    from prism.scripts.web_prescan import list_search_log
    from prism.scripts.manifest import (
        list_by_source_type, list_stale_web_search, list_expired_web_search,
    )
    entries = list_search_log(slug, variant)
    ws_mats = list_by_source_type(slug, variant, "web-search")
    stale = list_stale_web_search(slug, variant)
    expired = list_expired_web_search(slug, variant)
    return templates.TemplateResponse(
        request,
        "prism/web_search_log.html",
        {
            "topic": topic,
            "variant": variant,
            "entries": entries,
            "ws_mats": ws_mats,
            "n_stale": len(stale),
            "n_expired": len(expired),
            "now_iso": _now_iso_z(),
        },
    )


@router.get("/{slug}/{variant}/thesis/{version}")
def prism_thesis(request: Request, slug: str, variant: str, version: int):
    """View a specific thesis version (thesis_v{N}.md)."""
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")

    try:
        html_body = outputs_io.read_thesis_html(slug, variant, version)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Thesis v{version} not yet written")

    all_variants = topic_io.list_variants(slug)
    thesis_versions = outputs_io.list_thesis_files(slug, variant)

    # P3 reverse refs: 每个 K# 对应攻它的 todo
    ks = outputs_io.extract_killer_questions(slug, variant, version)
    coverage = topic_io.thesis_coverage(slug, variant, ks) if ks else None
    if coverage:
        coverage["all_keys"] = ks

    return templates.TemplateResponse(
        request,
        "prism/thesis.html",
        {
            "topic": topic,
            "version": version,
            "html_body": html_body,
            "variant": variant,
            "all_variants": all_variants,
            "thesis_versions": thesis_versions,
            "coverage": coverage,
        },
    )


@router.get("/{slug}/{variant}/macro-inputs")
def prism_macro_inputs(request: Request, slug: str, variant: str):
    """宏观输入源信息表（仅 macro topic）。必须声明在 /{output_key} 通配之前。"""
    from prism.scripts import macro_registry as macro_reg
    from prism.scripts import eval_snapshot as es
    from app import macro_jobs
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")
    if topic.get("type") != "macro":
        raise HTTPException(status_code=404, detail="非宏观主题")
    try:
        registry = macro_reg.read_registry(slug, variant)
        inputs = registry.get("inputs", [])
    except FileNotFoundError:
        registry = {"inputs": []}
        inputs = []
    log = es.read_eval_log(slug, variant)
    diff = {d["name"]: d for d in es.diff_since_last(slug, variant)} if inputs else {}
    # 在途 job（刷新后状态一致）+ 到期待手动拉取提示（定时巡检不再自动拉 LLM）
    jobs = macro_jobs.status(slug, variant)
    due = set(macro_reg.due_llm_monitor_names(registry)) if inputs else set()
    # 各行上次取数的落盘 meta（cost/时间）→ 表里只读展示「上次 $X · 时间」，补 cost 闪一下就没的审计缺口
    last_meta = {}
    cached = set()                       # 有落盘输出的行 → 即便 job 已超 TTL，也常驻「查看输出」（读缓存）
    for e in inputs:
        m = macro_jobs.read_meta(slug, variant, e["name"])
        if m is None:
            continue
        cached.add(e["name"])
        if m.get("cost") is not None:
            last_meta[e["name"]] = {"cost": m.get("cost"), "ended_at": m.get("ended_at")}
    # 本轮重判覆盖汇总：最新评估版本 + used 计数 + 承重漏判（load_bearing 却未参与），暴露在表头上方
    evals = log.get("evaluations") or []
    latest_eval = evals[-1] if evals else None
    coverage_summary = None
    if latest_eval:
        lb_inputs = [e for e in inputs if e.get("importance") == "load_bearing"]
        lb_unused = [e["name"] for e in lb_inputs
                     if not (diff.get(e["name"]) or {}).get("used")]
        coverage_summary = {
            "version": latest_eval.get("version"),
            "evaluated_at": latest_eval.get("evaluated_at"),
            "used": sum(1 for d in diff.values() if d.get("used")),
            "total": len(inputs),
            "lb_total": len(lb_inputs),
            "lb_unused": lb_unused,
        }
    from prism.scripts import input_glossary as ig
    grouped_inputs = ig.group_by_family(inputs)
    return templates.TemplateResponse(request, "prism/macro_inputs.html", {
        "topic": topic, "variant": variant, "inputs": inputs,
        "grouped_inputs": grouped_inputs,
        "diff": diff, "reeval_pending": log.get("reeval_pending"),
        "jobs": jobs, "due": due, "last_meta": last_meta, "cached": cached,
        "coverage_summary": coverage_summary,
        "clabels": es.conclusion_labels(slug, variant),   # 结论 id→中文 label（受影响结论展示）
        "reeval_cached": macro_jobs.read_meta(slug, variant, macro_jobs.REEVAL_NAME) is not None,
    })


@router.post("/{slug}/{variant}/macro-inputs/monitoring")
def prism_macro_monitoring(slug: str, variant: str, name: str = Form(...),
                           enabled: str = Form(...), anchor: str = Form("")):
    """切换某输入的 monitoring.enabled（零 LLM）。输入不存在 → 404。

    anchor：切换的行锚点，重定向后浏览器滚回该行（避免每次点都跳页顶）。
    """
    from prism.scripts import macro_registry as macro_reg
    try:
        registry = macro_reg.read_registry(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="登记表不存在")
    if not any(e["name"] == name for e in registry.get("inputs") or []):
        raise HTTPException(status_code=404, detail=f"输入 {name!r} 不存在")
    macro_reg.upsert_input(slug, variant, {"name": name, "monitoring": {"enabled": enabled == "true"}})
    frag = f"#{anchor}" if anchor else ""
    return RedirectResponse(f"/prism/{slug}/{variant}/macro-inputs{frag}", status_code=303)


@router.post("/{slug}/{variant}/macro-inputs/fetch-llm")
async def prism_macro_fetch_llm(slug: str, variant: str, request: Request,
                                names: list[str] = Form(default=[]), anchor: str = Form(""),
                                force: bool = Form(False), plan: bool = Form(False)):
    """web 手动拉起 headless LLM 取数：每个合格输入一个**后台 job**，立即返回（不阻塞）。

    点击即返回 job ids；服务端 app.macro_jobs 持有在途真相（刷新后仍正确），并发由 Semaphore 闸。
    names 为空时默认全部 llm/scriptable_todo 项。非 macro 主题 / 登记表缺失 → 404。
    Accept: application/json → 202 + {started, jobs:{name:job_id}}（前端起轮询/弹框 SSE）；
    否则 303 回锚点（无 JS 回退，job 仍在后台跑）。

    plan=true（脚本取文类的两段式）：只做预抓+去重判定、**不起 LLM job**，返回
    {would_start, skipped_unchanged}。前端据此「仅在 would_start 非空（内容有变、确需 LLM）时才弹确认」，
    确认后再以 plan=false 提交真正起 job。检索/固定页类无廉价预检，前端仍先确认后直接 plan=false 提交。
    """
    import asyncio
    from prism.scripts import macro_registry as macro_reg
    from app import macro_jobs
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")
    if topic.get("type") != "macro":
        raise HTTPException(status_code=404, detail="非宏观主题")
    try:
        registry = macro_reg.read_registry(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="登记表不存在")
    by_name = {e["name"]: e for e in registry.get("inputs") or []}
    eligible = [n for n, e in by_name.items()
                if e.get("availability") in ("llm", "scriptable_todo")]
    picked = [n for n in names if n in eligible] if names else eligible
    # 取文项（带 text_fetch）：先同步刷新各自的本地缓存再起 LLM job。逐条按 text_fetch 路由抓，
    # 拿回该项自己的 fingerprint——不再假设全局单源同一指纹（多取文源时各源指纹独立）。
    needs_prefetch = [n for n in picked if by_name[n].get("text_fetch")]
    prefetch_warn: str | None = None
    fingerprints: dict[str, str] = {}   # {name: 本次取数的稳定指纹}，去重门据此判内容是否变化
    if needs_prefetch:
        from prism.scripts import textfetch as _textfetch
        loop = asyncio.get_event_loop()
        for n in needs_prefetch:
            try:
                _fres = await loop.run_in_executor(
                    None, _textfetch.fetch_entry, slug, variant, by_name[n])
                _fp = (_fres or {}).get("fingerprint")
                if _fp:
                    fingerprints[n] = _fp
            except Exception as _exc:
                prefetch_warn = str(_exc)  # 网络失败不阻塞 LLM（降级读旧缓存或 web fetch）
    # 去重门：内容未变（新指纹 == 上次判读指纹）且未强制 → 跳过 LLM，沿用上次 observed、仅记 verified_at
    skipped_unchanged: list[str] = []
    if not force:
        survivors = []
        for n in picked:
            new_fp = fingerprints.get(n)
            obs = by_name[n].get("observed") or {}
            old_fp = obs.get("fingerprint")
            if new_fp and old_fp and new_fp == old_fp and obs:
                skipped_unchanged.append(n)
                macro_reg.mark_verified(slug, variant, n, fingerprint=new_fp)
            else:
                if new_fp:
                    by_name[n]["_pending_fingerprint"] = new_fp   # 透传给 _apply_payload 落盘
                survivors.append(n)
        picked = survivors
    else:
        for n in picked:                 # 强制：仍把指纹塞进 entry，判读后照常落盘更新
            if fingerprints.get(n):
                by_name[n]["_pending_fingerprint"] = fingerprints[n]
    # plan 模式：只回报「将起哪些 / 已因未变跳过哪些」，不起 job。前端据此决定是否弹确认。
    if plan:
        plan_resp: dict = {"would_start": picked, "skipped_unchanged": skipped_unchanged}
        if prefetch_warn is not None:
            plan_resp["prefetch_warn"] = prefetch_warn
        return JSONResponse(plan_resp, status_code=202)
    jobs = {n: macro_jobs.launch(slug, variant, n, entry=by_name[n]).id for n in picked}
    if "application/json" in (request.headers.get("accept") or ""):
        resp: dict = {"started": picked, "jobs": jobs, "skipped_unchanged": skipped_unchanged}
        if prefetch_warn is not None:
            resp["prefetch_warn"] = prefetch_warn
        return JSONResponse(resp, status_code=202)
    frag = f"#{anchor}" if anchor else ""
    return RedirectResponse(f"/prism/{slug}/{variant}/macro-inputs{frag}", status_code=303)


@router.get("/{slug}/{variant}/macro-inputs/jobs")
def prism_macro_jobs_status(slug: str, variant: str):
    """前端轮询：返回该主题在途/近期 job 的状态 {name: {status, job_id, started_at, inflight}}。"""
    from app import macro_jobs
    return JSONResponse(macro_jobs.status(slug, variant))


@router.get("/{slug}/{variant}/macro-inputs/jobs/{job_id}/stream")
async def prism_macro_job_stream(slug: str, variant: str, job_id: str):
    """SSE：实时推送某 job 的 claude 输出行（先重放缓冲再续播，终态收尾后结束）。未知 job → 404。

    关弹框 = 浏览器关 EventSource，只断流、不杀后台 job；重开新建 EventSource 从缓冲重放再续。
    """
    from app import macro_jobs
    if macro_jobs.get(job_id) is None:
        raise HTTPException(status_code=404, detail="job 不存在或已过期")

    async def _sse():
        async for line in macro_jobs.subscribe(job_id):
            yield macro_jobs._sse_data(line)   # 多行回答按 SSE 规范逐行加 data: 前缀（避免裸 \n 截断）

    return StreamingResponse(_sse(), media_type="text/event-stream")


@router.get("/{slug}/{variant}/macro-inputs/output")
def prism_macro_job_output(slug: str, variant: str, name: str):
    """读某行落盘的取数输出（.log 全文 + meta 概要）。供「查看输出」在 job 超 TTL/重启后看缓存。

    无缓存 → 404。在途 job 的实时输出走 SSE /stream（此处只服务已落盘的终态缓存）。
    """
    from app import macro_jobs
    text = macro_jobs.read_log(slug, variant, name)
    if text is None:
        raise HTTPException(status_code=404, detail="无缓存输出")
    meta = macro_jobs.read_meta(slug, variant, name) or {}
    return JSONResponse({"name": name, "text": text,
                         "status": meta.get("status"), "model": meta.get("model"),
                         "cost": meta.get("cost"), "ended_at": meta.get("ended_at")})


@router.post("/{slug}/{variant}/macro-inputs/fetch-script")
def prism_macro_fetch_script(slug: str, variant: str, request: Request,
                             name: str = Form(...), anchor: str = Form("")):
    """web 手动跑单条 scripted 项的脚本抓取（零 LLM：fred-api / recipe）。

    自动巡检每天 6:00 已抓全部 scripted；本端点让用户对某条立即重抓、不必等次日。
    输入须 availability=='scripted'；否则 400。非 macro 主题 / 登记表缺失 / 输入不存在 → 404。
    Accept: application/json → 回 {method, fetched, summary}；否则 303 回锚点（无 JS 回退）。
    """
    from prism.scripts import macro_registry as macro_reg
    from prism.scripts import fred_fetch, recipe_fetch
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")
    if topic.get("type") != "macro":
        raise HTTPException(status_code=404, detail="非宏观主题")
    try:
        registry = macro_reg.read_registry(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="登记表不存在")
    entry = next((e for e in registry.get("inputs") or [] if e["name"] == name), None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"输入 {name!r} 不存在")
    if entry.get("availability") != "scripted":
        raise HTTPException(status_code=400, detail="仅 scripted 项可脚本抓取")
    method = entry.get("fetch_method")
    if method == "fred-api":
        summary = fred_fetch.run_fred_fetch(slug, variant, only={name})
    elif method == "recipe":
        summary = recipe_fetch.run_recipe_fetch(slug, variant, only={name})
    elif method == "akshare":
        from prism.scripts import akshare_fetch
        summary = akshare_fetch.run_akshare_fetch(slug, variant, only={name})
    elif method == "yfinance":
        from prism.scripts import yfinance_fetch
        summary = yfinance_fetch.run_yfinance_fetch(slug, variant, only={name})
    elif method == "macromicro":
        from prism.scripts import macromicro_fetch
        summary = macromicro_fetch.run_macromicro_fetch(slug, variant, only={name})
    elif method == "barchart":
        from prism.scripts import barchart_fetch
        summary = barchart_fetch.run_barchart_fetch(slug, variant, only={name})
    elif method == "ecb":
        from prism.scripts import ecb_fetch
        summary = ecb_fetch.run_ecb_fetch(slug, variant, only={name})
    elif method == "cftc":
        from prism.scripts import cftc_fetch
        summary = cftc_fetch.run_cftc_fetch(slug, variant, only={name})
    elif method == "fedwatch":
        from prism.scripts import fedwatch_fetch
        summary = fedwatch_fetch.run_fedwatch_fetch(slug, variant, only={name})
    elif method == "fomc_sep":
        from prism.scripts import fomc_sep_fetch
        summary = fomc_sep_fetch.run_fomc_sep_fetch(slug, variant, only={name})
    else:
        raise HTTPException(status_code=400, detail=f"该项无脚本抓取通道（fetch_method={method!r}）")
    fetched = (summary.get("fetched", 0) or 0) + (summary.get("derived", 0) or 0)
    if "application/json" in (request.headers.get("accept") or ""):
        return JSONResponse({"method": method, "fetched": fetched, "summary": summary})
    frag = f"#{anchor}" if anchor else ""
    return RedirectResponse(f"/prism/{slug}/{variant}/macro-inputs{frag}", status_code=303)


@router.post("/{slug}/{variant}/macro-inputs/fetch-script-all")
def prism_macro_fetch_script_all(slug: str, variant: str, request: Request, anchor: str = Form("")):
    """批量「刷新脚本项」：跑全量 fred + recipe + akshare + 取文（零 LLM、零成本）。LLM 判读项一律行内单条手动拉。

    「取文」= 下载原文存本地缓存的脚本通道，登记表驱动：扫所有带 text_fetch 的输入、按其值路由到
    对应 fetcher（见 textfetch.run_textfetch）。加新取文源无需改本路由。各通道失败吞掉、不毁整批
    （其余通道仍生效）。非 macro 主题 / 登记表缺失 → 404。
    Accept: application/json → {fred, recipe, akshare, yfinance, text, fetched}；否则 303 回锚点。
    """
    from prism.scripts import (fred_fetch, recipe_fetch, textfetch, akshare_fetch,
                               yfinance_fetch, macromicro_fetch, barchart_fetch, ecb_fetch,
                               cftc_fetch, fedwatch_fetch, fomc_sep_fetch)
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")
    if topic.get("type") != "macro":
        raise HTTPException(status_code=404, detail="非宏观主题")
    # 顺序要紧：recipe 含「按名派生」（如 CIP 基差 = 多腿合成），须在所有腿通道之后跑，才能读到当轮新腿。
    # 故 fred → akshare → yfinance → macromicro → barchart → ecb → **recipe**（最后）→ text。
    fred_sum = fred_fetch.run_fred_fetch(slug, variant)
    # akshare（中国宏观）：脚本数值通道；整通道失败吞掉不毁整批
    try:
        akshare_sum = akshare_fetch.run_akshare_fetch(slug, variant)
    except Exception as _exc:
        akshare_sum = {"_error": str(_exc), "fetched": 0}
    # yfinance（市场行情：MOVE/DXY/^TNX 等专有指数）：脚本数值通道；整通道失败吞掉不毁整批
    try:
        yfin_sum = yfinance_fetch.run_yfinance_fetch(slug, variant)
    except Exception as _exc:
        yfin_sum = {"_error": str(_exc), "fetched": 0}
    # macromicro（FRED/akshare/yfinance 都缺的专有序列，如日频 JPY 3M OIS）：脚本数值通道；失败吞掉不毁整批
    try:
        mm_sum = macromicro_fetch.run_macromicro_fetch(slug, variant)
    except Exception as _exc:
        mm_sum = {"_error": str(_exc), "fetched": 0}
    # barchart（外汇 3M 远期点，CIP 基差远期腿）：脚本数值通道；失败吞掉不毁整批
    try:
        bc_sum = barchart_fetch.run_barchart_fetch(slug, variant)
    except Exception as _exc:
        bc_sum = {"_error": str(_exc), "fetched": 0}
    # ecb（日频 EUR 3M OIS 混合，CIP 基差欧元腿）：脚本数值通道；失败吞掉不毁整批
    try:
        ecb_sum = ecb_fetch.run_ecb_fetch(slug, variant)
    except Exception as _exc:
        ecb_sum = {"_error": str(_exc), "fetched": 0}
    # cftc（杠杆基金净头寸+z 拥挤度，basis-trade 代理）：脚本数值通道；失败吞掉不毁整批
    try:
        cftc_sum = cftc_fetch.run_cftc_fetch(slug, variant)
    except Exception as _exc:
        cftc_sum = {"_error": str(_exc), "fetched": 0}
    # fedwatch（CME ZQ 反解隐含政策路径：前瞻降息预期/概率）：脚本数值通道；失败吞掉不毁整批
    try:
        fedwatch_sum = fedwatch_fetch.run_fedwatch_fetch(slug, variant)
    except Exception as _exc:
        fedwatch_sum = {"_error": str(_exc), "fetched": 0}
    # fomc_sep（点阵图近年中位联邦基金利率：Fed 自己昭示的政策路径，与 fedwatch 隐含路径互补）：脚本数值通道；失败吞掉不毁整批
    try:
        fomc_sep_sum = fomc_sep_fetch.run_fomc_sep_fetch(slug, variant)
    except Exception as _exc:
        fomc_sep_sum = {"_error": str(_exc), "fetched": 0}
    # recipe：含 CIP 基差等按名派生，须在上述各腿之后跑（读最新 observed 合成）
    recipe_sum = recipe_fetch.run_recipe_fetch(slug, variant)
    # 取文：登记表驱动，逐条按 text_fetch 路由；整通道失败吞掉不毁整批（其余仍生效）
    try:
        text_sum = textfetch.run_textfetch(slug, variant)
    except Exception as _exc:
        text_sum = {"_error": str(_exc)}
    fred_n = (fred_sum.get("fetched", 0) or 0) + (fred_sum.get("derived", 0) or 0)
    recipe_n = (recipe_sum.get("fetched", 0) or 0) + (recipe_sum.get("derived", 0) or 0)
    akshare_n = akshare_sum.get("fetched", 0) or 0
    yfin_n = yfin_sum.get("fetched", 0) or 0
    mm_n = mm_sum.get("fetched", 0) or 0
    bc_n = bc_sum.get("fetched", 0) or 0
    ecb_n = ecb_sum.get("fetched", 0) or 0
    cftc_n = cftc_sum.get("fetched", 0) or 0
    fedwatch_n = fedwatch_sum.get("fetched", 0) or 0
    fomc_sep_n = fomc_sep_sum.get("fetched", 0) or 0
    text_n = sum(1 for r in text_sum.values() if isinstance(r, dict) and r.get("ok"))
    if "application/json" in (request.headers.get("accept") or ""):
        return JSONResponse({"fred": fred_n, "recipe": recipe_n, "akshare": akshare_n,
                             "yfinance": yfin_n, "macromicro": mm_n, "barchart": bc_n,
                             "ecb": ecb_n, "cftc": cftc_n, "fedwatch": fedwatch_n,
                             "fomc_sep": fomc_sep_n, "text": text_n,
                             "fetched": fred_n + recipe_n + akshare_n + yfin_n + mm_n + bc_n + ecb_n + cftc_n + fedwatch_n + fomc_sep_n + text_n,
                             "fred_summary": fred_sum, "recipe_summary": recipe_sum,
                             "akshare_summary": akshare_sum, "yfinance_summary": yfin_sum,
                             "macromicro_summary": mm_sum, "barchart_summary": bc_sum,
                             "ecb_summary": ecb_sum, "cftc_summary": cftc_sum,
                             "fedwatch_summary": fedwatch_sum, "fomc_sep_summary": fomc_sep_sum,
                             "text_summary": text_sum})
    frag = f"#{anchor}" if anchor else ""
    return RedirectResponse(f"/prism/{slug}/{variant}/macro-inputs{frag}", status_code=303)


@router.post("/{slug}/{variant}/macro-inputs/jobs/say")
async def prism_macro_job_say(slug: str, variant: str,
                              name: str = Form(...), message: str = Form(...),
                              model: str = Form("")):
    """弹框续问 / 换模型重判：macro_jobs.say 用已存 session_id `--resume` 续上同一上下文（不重搜）。

    say 返回 None（内存无 job 且无落盘 meta = 无可续会话）→ 404；否则 202 {job_id}，前端重连 SSE 看续播。
    """
    from app import macro_jobs
    job = await macro_jobs.say(slug, variant, name, message, model=(model or None))
    if job is None:
        raise HTTPException(status_code=404, detail="无可续会话（请先拉取一次再重判）")
    return JSONResponse({"job_id": job.id}, status_code=202)


@router.post("/{slug}/{variant}/reeval")
async def prism_reeval(slug: str, variant: str, request: Request,
                       model: str = Form("")):
    """组装重估简报 + 盖戳（零 LLM）+ 拉起一个真实合成 job（跑 _macro_regime 全流程）。

    简报照旧零 LLM；真重判由后台 headless（全能力会话、默认 opus4.8）落地，弹框可看流式 + 续问驱动。
    Accept: application/json → 202 + 简报计数 + job_id/name/model（前端弹输出框）；否则 303 回 #reeval-brief。
    """
    from prism.scripts import eval_snapshot as es
    from app import macro_jobs
    brief = es.assemble_reeval_brief(slug, variant)
    es.stamp_reeval_pending(slug, variant, brief)
    model = model or macro_jobs.REEVAL_MODEL
    job = macro_jobs.launch_reeval(slug, variant, model=model)
    if "application/json" in (request.headers.get("accept") or ""):
        return JSONResponse({"changed": len(brief.get("changed") or []),
                             "breached": len(brief.get("breached") or []),
                             "due": len(brief.get("due") or []),
                             "affected": brief.get("affected_conclusions") or [],
                             "job_id": job.id, "name": macro_jobs.REEVAL_NAME,
                             "model": model}, status_code=202)
    return RedirectResponse(f"/prism/{slug}/{variant}/macro-inputs#reeval-brief", status_code=303)


@router.get("/{slug}/{variant}/transmission-map")
def prism_transmission_map(request: Request, slug: str, variant: str):
    """传导地图（L4 持仓暴露表，仅 macro topic）。

    transmission_map.yaml 是 .yaml 产物、无 markdown 视图，故专路直读渲染。
    必须声明在 /{output_key} 通配之前（同 macro-inputs）。
    """
    from prism.scripts import macro_registry as macro_reg
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")
    if topic.get("type") != "macro":
        raise HTTPException(status_code=404, detail="非宏观主题")
    tmap = macro_reg.read_transmission_map(slug, variant)
    return templates.TemplateResponse(request, "prism/transmission_map.html", {
        "topic": topic, "variant": variant,
        "regime": tmap.get("regime") or {},
        "holdings": tmap.get("holdings") or [],
        "categorical_tail": tmap.get("categorical_tail") or [],
        "generated": tmap.get("generated"),
    })


@router.get("/{slug}/{variant}/eval-trace")
def prism_eval_trace(request: Request, slug: str, variant: str):
    """评估溯源（结论←输入←因果句 + diff，仅 macro topic）。
    必须声明在 /{output_key} 通配之前（同 macro-inputs / transmission-map）。"""
    from prism.scripts import eval_snapshot as es
    from prism.scripts import eval_score as sc
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")
    if topic.get("type") != "macro":
        raise HTTPException(status_code=404, detail="非宏观主题")
    return templates.TemplateResponse(request, "prism/eval_trace.html", {
        "topic": topic, "variant": variant,
        "evaluation": es.latest_evaluation(slug, variant),
        "diff": {d["name"]: d for d in es.diff_since_last(slug, variant)},
        "score": sc.score_evaluation(slug, variant),
        "ledger": {(r["conclusion_id"], r["input"]): r for r in sc.edge_ledger(slug, variant)},
    })


@router.get("/{slug}/{variant}/{output_key}/wechat")
def prism_output_wechat(request: Request, slug: str, variant: str, output_key: str):
    """某产出的微信公众号版（纯显示层清洗 + 内联样式 + 复制按钮）。仅 primer/case 开放。"""
    if output_key not in wechat_export.WECHAT_OUTPUT_KEYS:
        raise HTTPException(status_code=404, detail="公众号版仅支持 primer / case 产出")
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")
    try:
        article_html = wechat_export.to_wechat_html(slug, variant, output_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Output {output_key!r} not yet generated")
    outputs = outputs_io.list_outputs(slug, variant)
    current_output = next((o for o in outputs if o["key"] == output_key), None)
    return templates.TemplateResponse(
        request,
        "prism/wechat.html",
        {
            "topic": topic,
            "output_key": output_key,
            "current_output": current_output,
            "variant": variant,
            "article_html": article_html,
        },
    )


@router.get("/{slug}/{variant}/{output_key}")
def prism_output(request: Request, slug: str, variant: str, output_key: str):
    """View a specific output for a model variant."""
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")

    try:
        html_body = outputs_io.read_output_html(slug, output_key, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Output {output_key!r} not yet generated")

    outputs = outputs_io.list_outputs(slug, variant)
    current_output = next((o for o in outputs if o["key"] == output_key), None)
    all_variants = topic_io.list_variants(slug)

    return templates.TemplateResponse(
        request,
        "prism/output.html",
        {
            "topic": topic,
            "output_key": output_key,
            "current_output": current_output,
            "html_body": html_body,
            "outputs": outputs,
            "variant": variant,
            "all_variants": all_variants,
        },
    )


# ── daily-monitor POST endpoints ──────────────────────────────────────────────
# 照搬 prices.py/financials.py 的 POST→JSON{ok}→前端 location.reload() 模式。

class WatchAddBody(BaseModel):
    slug: str
    scope: str = "topic"          # topic | event
    kind: str | None = None       # event 时: signpost | kill | price
    locator: str | None = None    # event signpost/kill 的定位符
    variant: str | None = None    # 省略则用 canonical


class WatchRemoveBody(BaseModel):
    slug: str
    scope: str | None = None
    kind: str | None = None
    locator: str | None = None


class ConfirmBody(BaseModel):
    proposal_id: str | None = None
    all: bool = False


class DiscardBody(BaseModel):
    proposal_id: str


@router.post("/monitor/run")
async def monitor_run():
    """手动「立即巡检」——触发与每日 6:00 同一个 monitor cycle。"""
    from app.monitor_runtime import run_monitor_cycle
    result = await run_monitor_cycle(trigger="manual")
    return {"ok": True, "result": result}


@router.post("/watchlist/add")
def watchlist_add(body: WatchAddBody):
    from prism.scripts import monitor
    try:
        entry = monitor.add_watch(
            body.slug, scope=body.scope, kind=body.kind,
            locator=body.locator, variant=body.variant,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "watch": entry}


@router.post("/watchlist/remove")
def watchlist_remove(body: WatchRemoveBody):
    from prism.scripts import monitor
    removed = monitor.remove_watch(
        body.slug, scope=body.scope, kind=body.kind, locator=body.locator,
    )
    return {"ok": True, "removed": removed}


@router.post("/monitor/confirm")
def monitor_confirm(body: ConfirmBody):
    """确认翻牌:单条(proposal_id)或全部(all=true)。机械回写,零 LLM。"""
    from prism.scripts import monitor
    if body.all:
        return {"ok": True, **monitor.confirm_all()}
    if not body.proposal_id:
        raise HTTPException(status_code=400, detail="需要 proposal_id 或 all=true")
    try:
        return {"ok": True, **monitor.confirm_flip(body.proposal_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/monitor/discard")
def monitor_discard(body: DiscardBody):
    from prism.scripts import monitor
    try:
        return {"ok": True, **monitor.discard_flip(body.proposal_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
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

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.config import APP_TEMPLATES_DIR
from prism.scripts import manifest as manifest_io
from prism.scripts import outputs as outputs_io
from prism.scripts import topic as topic_io

router = APIRouter(prefix="/prism", tags=["prism"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


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
    ("08_living_feed", "信息流时间线"),
    ("industry_to_arenas", "产业→竞技场选拔"),
]


_TYPE_LABEL = {"company": "公司", "arena": "竞技场", "industry": "行业"}
_TYPE_EMOJI = {"company": "🏢", "arena": "🥊", "industry": "🏭"}
# 树内排序：行业 < 竞技场 < 公司（同级内再按 created 倒序）
_TYPE_ORDER = {"industry": 0, "arena": 1, "company": 2}


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
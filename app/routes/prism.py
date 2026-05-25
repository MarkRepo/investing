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

import markdown as _md
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

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

# Output key → label mapping for dropdowns
_OUTPUT_OPTIONS = [
    ("01_business_panorama", "商业全景"),
    ("02_cycle_positioning", "周期定位"),
    ("03_narrative_ecology", "叙事谱系"),
    ("04_implied_expectations", "隐含预期与观点光谱"),
    ("05_historical_mirrors", "历史镜像"),
    ("06_risk_blindspots", "风险盲点"),
    ("07_decision_kit", "决策辅助"),
    ("08_living_feed", "信息流时间线"),
    ("09_industry_to_arenas", "产业→竞技场选拔"),
]


@router.get("")
def prism_index(request: Request):
    """List all topics grouped by slug, showing available model variants."""
    all_topics = topic_io.list_topics()
    # Group by slug
    grouped: dict[str, list[dict]] = defaultdict(list)
    for t in all_topics:
        grouped[t["slug"]].append(t)
    # Build topic summaries, grouped by type
    TYPE_ORDER = {"company": 0, "arena": 1, "industry": 2}
    TYPE_LABEL = {"company": "公司", "arena": "竞技场", "industry": "行业"}

    groups: dict[str, list[dict]] = defaultdict(list)
    for slug, variants in grouped.items():
        info = variants[0]
        topic_type = info.get("type", "industry")
        groups[topic_type].append({
            "slug": slug,
            "display_name": info.get("display_name", slug),
            "type": topic_type,
            "created": info.get("created", ""),
            "ticker": _scope_ticker(scope := info.get("scope") or {}),
            "market_ticker": _make_market_ticker(scope),
            "variants": [{
                "name": v["variant"],
                "stage": v.get("stage", ""),
                "status": v.get("status", ""),
                "fresh_count": sum(
                    1 for s in v.get("outputs_state", {}).values()
                    if s.get("status") == "fresh"
                ),
                "total_count": len(v.get("outputs_state", {})),
            } for v in variants],
        })

    # Sort each group by created desc
    for g in groups.values():
        g.sort(key=lambda t: t["created"], reverse=True)

    # Ordered groups for template
    ordered_groups = []
    for tp in sorted(groups.keys(), key=lambda k: TYPE_ORDER.get(k, 99)):
        ordered_groups.append({
            "type": tp,
            "label": TYPE_LABEL.get(tp, tp),
            "topics": groups[tp],
        })

    return templates.TemplateResponse(
        request,
        "prism/index.html",
        {"topic_groups": ordered_groups},
    )


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
    body_html = _md.markdown(raw, extensions=["tables", "fenced_code"])

    return templates.TemplateResponse(
        request,
        "prism/dashboard.html",
        {"body_html": body_html},
    )


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
                "fresh_count": sum(
                    1 for s in data.get("outputs_state", {}).values()
                    if s.get("status") == "fresh"
                ),
                "total_count": len(data.get("outputs_state", {})),
            })
        except Exception:
            variant_data.append({"name": v, "stage": "", "status": "", "fresh_count": 0, "total_count": 8})

    display_name = variant_data[0].get("display_name", slug) if variant_data else slug
    # Try to get display_name from first variant's full data
    try:
        display_name = topic_io.read_topic(slug, variants[0]).get("display_name", slug)
    except Exception:
        display_name = slug

    return templates.TemplateResponse(
        request,
        "prism/variants.html",
        {
            "slug": slug,
            "display_name": display_name,
            "variants": variant_data,
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

    return templates.TemplateResponse(
        request,
        "prism/detail.html",
        {
            "topic": topic,
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
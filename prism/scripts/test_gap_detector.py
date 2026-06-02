"""Tests for gap_detector."""
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from prism.scripts import topic as topic_io
from prism.scripts.manifest import add_material, create_manifest


@pytest.fixture
def tmp_topic_with_findings(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.gap_detector.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.outputs._PRISM_ROOT", tmpdir)
    slug, variant = "test-gap", "test"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(
        slug=slug, display_name="T", topic_type="company",
        question="Q?", geo="US", depth="quick", variant=variant,
        short_name="T",
        ticker="US_T",
    )
    create_manifest(slug, variant)
    yield slug, variant, tmpdir
    shutil.rmtree(tmpdir)


def _write_thesis(tmpdir: Path, slug: str, variant: str, body: str) -> None:
    p = tmpdir / "topics" / slug / variant / "thesis_v0.md"
    p.write_text(body, encoding="utf-8")


def test_gap_detects_uncovered_k(tmp_topic_with_findings):
    """K# without any material → gap reports it as uncovered."""
    from prism.scripts.gap_detector import detect_gaps

    slug, variant, tmpdir = tmp_topic_with_findings
    _write_thesis(tmpdir, slug, variant,
                  "## Killer Question\n\nK1: Does X happen?\nK2: Does Y happen?\n")
    topic_io.set_thesis(slug, variant, version=0, summary="t",
                        stage_set_at="01-roadmap-pending")
    add_material(slug=slug, filename="m1.md", source_type="web-article",
                 variant=variant, addresses=["K1"])

    report = detect_gaps(slug, variant)
    assert "K2" in report["uncovered_ks"]
    assert "K1" not in report["uncovered_ks"]


def test_gap_detects_thin_evidence(tmp_topic_with_findings):
    """K# with < min_evidence material → flagged as thin."""
    from prism.scripts.gap_detector import detect_gaps

    slug, variant, tmpdir = tmp_topic_with_findings
    _write_thesis(tmpdir, slug, variant, "K1: X?\n")
    topic_io.set_thesis(slug, variant, version=0, summary="t",
                        stage_set_at="01-roadmap-pending")
    add_material(slug=slug, filename="m1.md", source_type="web-article",
                 variant=variant, addresses=["K1"])

    report = detect_gaps(slug, variant, min_evidence=2)
    assert "K1" in report["thin_evidence"]


def test_gap_counts_findings_layer_addresses(tmp_topic_with_findings):
    """B 轴 bug 回归：证据只在 findings 层打 addresses（材料层无）时，K# 不应误报未覆盖。

    旧实现只数 manifest 材料层 addresses，漏掉只在 03 抽取阶段按 findings 打标的 topic，
    导致 B 轴误报 K# 全 0。修复后 materials ∪ own findings 取并集计数。
    """
    from prism.scripts.gap_detector import detect_gaps

    slug, variant, tmpdir = tmp_topic_with_findings
    _write_thesis(tmpdir, slug, variant, "K1: X?\nK2: Y?\n")
    topic_io.set_thesis(slug, variant, version=0, summary="t",
                        stage_set_at="01-roadmap-pending")
    # 材料层不打 addresses（模拟只在 findings 层打标的 topic）
    add_material(slug=slug, filename="m1.md", source_type="web-article", variant=variant)
    # findings 层打 addresses=[K1]
    out_dir = tmpdir / "topics" / slug / variant / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "findings_mat-t1.md").write_text(
        "---\naddresses:\n  - K1\n---\n- 数据点\n", encoding="utf-8")

    report = detect_gaps(slug, variant)
    assert "K1" not in report["uncovered_ks"], "findings 层 addresses 应计入覆盖"
    assert "K2" in report["uncovered_ks"], "无任何层覆盖的 K# 仍报 uncovered"
    assert report["evidence_count"]["K1"] >= 1


def test_gap_dedups_material_and_its_finding(tmp_topic_with_findings):
    """同一 mat_id 在材料层与 findings 层都打 K1 → 只计 1 个来源（去重，不假性满足 ≥2）。"""
    from prism.scripts.gap_detector import detect_gaps
    from prism.scripts.manifest import read_manifest

    slug, variant, tmpdir = tmp_topic_with_findings
    _write_thesis(tmpdir, slug, variant, "K1: X?\n")
    topic_io.set_thesis(slug, variant, version=0, summary="t",
                        stage_set_at="01-roadmap-pending")
    add_material(slug=slug, filename="m1.md", source_type="web-article",
                 variant=variant, addresses=["K1"])
    mid = read_manifest(slug, variant)["materials"][0]["id"]
    out_dir = tmpdir / "topics" / slug / variant / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"findings_{mid}.md").write_text(
        "---\naddresses:\n  - K1\n---\n- 数据点\n", encoding="utf-8")

    report = detect_gaps(slug, variant, min_evidence=2)
    assert report["evidence_count"]["K1"] == 1, "材料与其 finding 同源应去重为 1"
    assert "K1" in report["thin_evidence"]


def test_gap_counts_reuse_parent_findings(tmp_topic_with_findings):
    """reuse（父 parent_materials）findings 的 addresses 应计入 B 轴覆盖。

    实测多数 arena/company topic 的 K# 覆盖来自父级 findings；排除 reuse 会让其误报全红。
    """
    from prism.scripts.gap_detector import detect_gaps

    slug, variant, tmpdir = tmp_topic_with_findings
    _write_thesis(tmpdir, slug, variant, "K1: X?\nK2: Y?\n")
    topic_io.set_thesis(slug, variant, version=0, summary="t",
                        stage_set_at="01-roadmap-pending")
    # 建父 topic + 父 finding 文件（reuse 引用要求文件存在）
    pslug, pvar = "parent-ind", "test"
    (tmpdir / "topics" / pslug / pvar).mkdir(parents=True)
    topic_io.create_topic(slug=pslug, display_name="P", topic_type="industry",
                          question="Q?", geo="US", depth="quick", variant=pvar,
                          short_name="P")
    pout = tmpdir / "topics" / pslug / pvar / "outputs"
    pout.mkdir(parents=True, exist_ok=True)
    (pout / "findings_mat-p1.md").write_text(
        "---\naddresses:\n  - K1\n---\n- 父数据点\n", encoding="utf-8")
    # 子 topic 引用父 finding 覆盖 K1（own 材料/findings 均无 addresses）
    topic_io.set_parent_materials(slug, variant, [
        {"parent_slug": pslug, "parent_variant": pvar, "mat_id": "mat-p1",
         "addresses": ["K1"]},
    ])

    report = detect_gaps(slug, variant)
    assert "K1" not in report["uncovered_ks"], "reuse 父 finding 应计入覆盖"
    assert "K2" in report["uncovered_ks"]
    assert report["evidence_count"]["K1"] >= 1


def test_gap_ring_axis_counts_finding_layer_rings(tmp_topic_with_findings):
    """F15：ring A 轴并入 finding 层 rings（比照 B 轴 material∪findings）。

    industry 主题：材料层不带 industry rings（模拟 F10 误标/收料期未标），但 03 在 finding
    frontmatter 补了 value-chain-profit-pool（材料强制项）+ industry-financial-arc。
    旧实现只数材料层 rings → 这俩永报 uncovered（A 轴失灵）；修后 finding rings 被计入。
    """
    from prism.scripts.gap_detector import detect_gaps

    slug, variant, tmpdir = tmp_topic_with_findings
    # 在同一 monkeypatched tmpdir 下建 industry 主题
    islug, ivar = "test-ind", "test"
    (tmpdir / "topics" / islug / ivar).mkdir(parents=True)
    topic_io.create_topic(slug=islug, display_name="Ind", topic_type="industry",
                          question="Q?", geo="CN", depth="quick", variant=ivar,
                          short_name="Ind")
    create_manifest(islug, ivar)
    # 材料层不带 industry rings
    add_material(slug=islug, filename="m1.md", source_type="annual-report", variant=ivar)
    # finding 层带 industry rings（含一个材料强制项 value-chain-profit-pool）
    iout = tmpdir / "topics" / islug / ivar / "outputs"
    iout.mkdir(parents=True, exist_ok=True)
    (iout / "findings_mat-i1.md").write_text(
        "---\nrings:\n  - value-chain-profit-pool\n  - industry-financial-arc\n---\n- 点\n",
        encoding="utf-8")

    report = detect_gaps(islug, ivar)
    assert report["ring_axis_status"] == "active"
    assert report["ring_coverage"].get("value-chain-profit-pool", 0) >= 1
    assert report["ring_coverage"].get("industry-financial-arc", 0) >= 1
    uncovered_codes = {u["code"] for u in report["uncovered_ring_inputs"]}
    assert "value-chain-profit-pool" not in uncovered_codes, "finding 层 ring 应让材料强制项脱离 uncovered"


def test_gap_detects_stale_web_search(tmp_topic_with_findings):
    """web-search material > 90d expire → flagged as stale claims."""
    from prism.scripts.gap_detector import detect_gaps
    from prism.scripts.manifest import make_search_meta

    slug, variant, tmpdir = tmp_topic_with_findings
    _write_thesis(tmpdir, slug, variant, "K1: X?\n")
    topic_io.set_thesis(slug, variant, version=0, summary="t",
                        stage_set_at="01-roadmap-pending")
    old_dt = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    sm = make_search_meta(query="q", url="https://reuters.com/x",
                          domain="reuters.com", domain_tier="whitelist",
                          searched_at=old_dt)
    add_material(slug=slug, filename="m1.md", source_type="web-search",
                 variant=variant, addresses=["K1"], search_meta=sm)

    report = detect_gaps(slug, variant)
    assert len(report["expired_web_materials"]) == 1


def test_gap_summary_string(tmp_topic_with_findings):
    """detect_gaps returns a human-readable summary."""
    from prism.scripts.gap_detector import detect_gaps, format_summary

    slug, variant, _ = tmp_topic_with_findings
    report = detect_gaps(slug, variant)
    summary = format_summary(report)
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_ring_axis_legacy_na(tmp_topic_with_findings):
    """旧 topic（无 decomposition 且无 rings 材料）→ ring 轴 n/a，不刷红。"""
    from prism.scripts.gap_detector import detect_gaps

    slug, variant, _ = tmp_topic_with_findings
    add_material(slug=slug, filename="m1.md", source_type="web-article",
                 variant=variant, addresses=["K1"])  # 只有 addresses，无 rings
    report = detect_gaps(slug, variant)
    assert report["ring_axis_status"] == "n/a"
    assert report["uncovered_ring_inputs"] == []


def test_ring_axis_active_uncovered_and_api(tmp_topic_with_findings):
    """接入拆解后 ring 轴 active：材料强制项无料→uncovered(hard 标记)；
    api_satisfiable 项有 ticker→api_pending(非红)；已打 rings 的项→covered。"""
    from prism.scripts.gap_detector import detect_gaps

    slug, variant, _ = tmp_topic_with_findings
    # 激活 ring 轴
    topic_io.set_decomposition(slug, variant, version=0, summary="命门",
                               stage_set_at="00-research-pending")
    # consensus 收到料 → covered
    add_material(slug=slug, filename="c.md", source_type="sell-side-note",
                 variant=variant, rings=["consensus"])
    report = detect_gaps(slug, variant)
    assert report["ring_axis_status"] == "active"
    codes = {e["code"] for e in report["uncovered_ring_inputs"]}
    assert "consensus" not in codes          # covered
    assert "mgmt-capital-alloc" in codes     # 材料强制项，无料
    assert "historical-mirror" in codes
    # hard 标记正确
    hard_uncovered = {e["code"] for e in report["uncovered_ring_inputs"] if e["hard"]}
    assert {"mgmt-capital-alloc", "historical-mirror"} <= hard_uncovered
    # financial-arc / valuation-anchor 是 api_satisfiable + 有 ticker → api_pending，不在 uncovered
    api_codes = {e["code"] for e in report["api_pending_inputs"]}
    assert "financial-arc" in api_codes
    assert "financial-arc" not in codes
    assert report["ring_coverage"]["consensus"] == 1


def test_ring_axis_hard_thin_below_threshold(tmp_topic_with_findings):
    """hard 材料强制项被恰好 1 份料覆盖（< min_evidence=2）→ 进 thin_ring_inputs（黄），
    不进 uncovered（红）也不算 covered（绿）；非 hard 材料强制项 1 份料即覆盖，不进 thin。"""
    from prism.scripts.gap_detector import detect_gaps

    slug, variant, _ = tmp_topic_with_findings
    topic_io.set_decomposition(slug, variant, version=0, summary="命门",
                               stage_set_at="00-research-pending")
    # hard 项 consensus 恰好 1 份料；非 hard 材料强制项 bull-bear 也 1 份料
    add_material(slug=slug, filename="c.md", source_type="sell-side-note",
                 variant=variant, rings=["consensus"])
    add_material(slug=slug, filename="bb.md", source_type="sell-side-note",
                 variant=variant, rings=["bull-bear"])

    report = detect_gaps(slug, variant, min_evidence=2)
    thin_codes = {e["code"] for e in report["thin_ring_inputs"]}
    uncovered_codes = {e["code"] for e in report["uncovered_ring_inputs"]}
    assert "consensus" in thin_codes, "hard 项 1 份料 → 薄输入"
    assert "consensus" not in uncovered_codes, "有料就不是 uncovered"
    # 薄输入条目带计数与阈值
    consensus_entry = next(e for e in report["thin_ring_inputs"] if e["code"] == "consensus")
    assert consensus_entry["count"] == 1
    assert consensus_entry["min_evidence"] == 2
    assert consensus_entry["hard"] is True
    # 非 hard 材料强制项 1 份料 → 覆盖，不进 thin 也不进 uncovered
    assert "bull-bear" not in thin_codes, "非 hard 项不开 thin"
    assert "bull-bear" not in uncovered_codes


def test_ring_axis_hard_meets_threshold_is_covered(tmp_topic_with_findings):
    """hard 项达到 min_evidence 份料 → 既不 uncovered 也不 thin（绿）。"""
    from prism.scripts.gap_detector import detect_gaps

    slug, variant, _ = tmp_topic_with_findings
    topic_io.set_decomposition(slug, variant, version=0, summary="命门",
                               stage_set_at="00-research-pending")
    add_material(slug=slug, filename="c1.md", source_type="sell-side-note",
                 variant=variant, rings=["consensus"])
    add_material(slug=slug, filename="c2.md", source_type="sell-side-note",
                 variant=variant, rings=["consensus"])

    report = detect_gaps(slug, variant, min_evidence=2)
    thin_codes = {e["code"] for e in report["thin_ring_inputs"]}
    uncovered_codes = {e["code"] for e in report["uncovered_ring_inputs"]}
    assert "consensus" not in thin_codes
    assert "consensus" not in uncovered_codes
    assert report["ring_coverage"]["consensus"] == 2


def test_ring_axis_api_no_ticker_is_gap(tmp_topic_with_findings, monkeypatch):
    """api_satisfiable 项但无 ticker → 无法自动拉 → 计入 uncovered。"""
    from prism.scripts.gap_detector import detect_gaps

    slug, variant, _ = tmp_topic_with_findings
    # 抹掉 scope.ticker（ticker 存在 scope 下）
    data = topic_io.read_topic(slug, variant)
    scope = data.get("scope") or {}
    scope.pop("ticker", None)
    scope.pop("extra_tickers", None)
    topic_io.update_topic(slug, variant, scope=scope)
    topic_io.set_decomposition(slug, variant, version=0, summary="命门",
                               stage_set_at="00-research-pending")
    report = detect_gaps(slug, variant)
    codes = {e["code"] for e in report["uncovered_ring_inputs"]}
    assert "financial-arc" in codes          # 无 ticker → 真缺口


def test_prescan_untagged_flagged_when_thesis_ready(tmp_topic_with_findings):
    """坑③：thesis 已就位但材料只挂 scope 占位、无 K# → prescan_untagged 点名。"""
    from prism.scripts.gap_detector import detect_gaps, format_summary

    slug, variant, tmpdir = tmp_topic_with_findings
    _write_thesis(tmpdir, slug, variant, "K1: X?\n")
    topic_io.set_thesis(slug, variant, version=0, summary="t",
                        stage_set_at="01-roadmap-pending")
    add_material(slug=slug, filename="prescan1.md", source_type="web-search",
                 variant=variant, addresses=["scope"])

    report = detect_gaps(slug, variant)
    flagged = report["prescan_untagged"]
    assert len(flagged) == 1
    assert flagged[0]["filename"] == "prescan1.md"
    assert "scope" in flagged[0]["addresses"]
    assert "🏷 待补 K# 标签" in format_summary(report)


def test_prescan_untagged_skips_materials_with_knum(tmp_topic_with_findings):
    """带 K# 的材料不上 prescan_untagged 榜。"""
    from prism.scripts.gap_detector import detect_gaps

    slug, variant, tmpdir = tmp_topic_with_findings
    _write_thesis(tmpdir, slug, variant, "K1: X?\n")
    topic_io.set_thesis(slug, variant, version=0, summary="t",
                        stage_set_at="01-roadmap-pending")
    add_material(slug=slug, filename="tagged.md", source_type="web-article",
                 variant=variant, addresses=["K1"])
    # 混合：含 K# 即视为已标，不点名
    add_material(slug=slug, filename="mixed.md", source_type="web-article",
                 variant=variant, addresses=["scope", "K1@anchor"])

    report = detect_gaps(slug, variant)
    assert report["prescan_untagged"] == []


def test_prescan_untagged_empty_without_thesis(tmp_topic_with_findings):
    """thesis 未就位（起手态）→ prescan 占位属正常，不点名。"""
    from prism.scripts.gap_detector import detect_gaps

    slug, variant, _ = tmp_topic_with_findings
    add_material(slug=slug, filename="prescan1.md", source_type="web-search",
                 variant=variant, addresses=["scope"])

    report = detect_gaps(slug, variant)
    assert report["prescan_untagged"] == []


def test_baseline_path_helpers(tmp_topic_with_findings):
    from prism.scripts.topic import (
        baseline_knowledge_path,
        has_baseline_knowledge,
        read_baseline_knowledge,
    )
    slug, variant, _ = tmp_topic_with_findings
    assert not has_baseline_knowledge(slug, variant)
    assert read_baseline_knowledge(slug, variant) is None
    p = baseline_knowledge_path(slug, variant)
    p.write_text("baseline test", encoding="utf-8")
    assert has_baseline_knowledge(slug, variant)
    assert read_baseline_knowledge(slug, variant) == "baseline test"

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

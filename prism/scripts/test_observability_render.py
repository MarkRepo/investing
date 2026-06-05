"""Tests for observability_render — Trace → 诊断页 markdown。"""
import tempfile
from pathlib import Path

import pytest

from prism.scripts import topic as topic_io
from prism.scripts import observability_render as render


@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.gap_detector.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.outputs._PRISM_ROOT", tmpdir)
    slug, variant = "rnd-test", "test"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(slug=slug, display_name="T", topic_type="company",
                          question="Q?", geo="US", depth="quick", variant=variant,
                          short_name="T", ticker="US_T")
    return slug, variant


def test_render_contains_sections(tmp_topic):
    slug, variant = tmp_topic
    md = render.render_diagnostic_page(slug, variant)
    assert "# 诊断" in md
    assert "体检条" in md or "体检" in md
    assert "贯穿" in md
    assert "复核旗" in md


def test_render_flag_summary_lists_flags(tmp_topic):
    slug, variant = tmp_topic
    topic_io.set_critic_verdict(slug, variant, verdict="approve")
    md = render.render_diagnostic_page(slug, variant)
    assert "05.Q1" in md   # steelman flag 进复核旗汇总


def test_build_view_structure(tmp_topic):
    """build_view 出结构化分组（供 web 体检 tab），字段齐、分组顺序对。"""
    slug, variant = tmp_topic
    view = render.build_view(slug, variant)
    assert set(view["summary"]) >= {"pass", "fail", "flag", "na"}
    assert view["groups"], "应至少有一组"
    assert view["groups"][0]["title"].startswith("贯穿")
    p = view["groups"][0]["probes"][0]
    assert {"status", "probe_id", "label", "detail", "action"} <= set(p)
    assert view["badge"]["pass"] == "🟢"
    # 分组顺序：贯穿在最前，Stage 单调递增
    stage_titles = [g["title"] for g in view["groups"] if g["title"].startswith("Stage")]
    assert stage_titles == sorted(stage_titles)


def test_build_view_flags_are_flag_status(tmp_topic):
    """flags 列表只含 status==flag，且 05.Q1 steelman 在内。"""
    slug, variant = tmp_topic
    topic_io.set_critic_verdict(slug, variant, verdict="approve")
    view = render.build_view(slug, variant)
    assert view["flags"], "approve 后至少有 steelman flag"
    assert all(p["status"] == "flag" for p in view["flags"])
    assert any(p["probe_id"] == "05.Q1" for p in view["flags"])

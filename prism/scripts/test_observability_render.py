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

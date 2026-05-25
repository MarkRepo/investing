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

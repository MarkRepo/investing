"""Tests for outputs.list_affected_outputs aggregate expansion + triggered_by filter.

Covers the 2026-05-26 web-search refactor (Step 3 + Step 2 of the plan):
  - aggregate mat_id (ws-aggregate-*) auto expansion via finding frontmatter
  - exclude_triggered_by default filter (Role α prescan exclusion)
  - fallback when aggregated_from missing (preserves virtual ID → stale)
  - legacy filename convention (findings_mat-ws-K# vs findings_ws-aggregate-K#)
"""
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from prism.scripts import topic as topic_io
from prism.scripts.manifest import create_manifest, add_material, mark_processed, make_search_meta
from prism.scripts.outputs import list_affected_outputs


@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    # outputs.py uses module-level _PRISM_ROOT
    monkeypatch.setattr("prism.scripts.outputs._PRISM_ROOT", tmpdir)
    slug = "test-slug"
    variant = "test-variant"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(
        slug=slug, display_name="Test", topic_type="company",
        question="Q?", geo="US", depth="quick", variant=variant,
        short_name="Test", ticker="US_TEST",
    )
    create_manifest(slug, variant)
    yield slug, variant, tmpdir
    shutil.rmtree(tmpdir)


def _write_aggregate_finding(tmpdir: Path, slug: str, variant: str,
                              mat_id: str, aggregated_from: list[str],
                              filename_suffix: str | None = None) -> Path:
    """Write a findings_{mat_id}.md (or legacy findings_mat-ws-{suffix}.md)."""
    out_dir = tmpdir / "topics" / slug / variant / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    fm = {
        "mat_id": mat_id,
        "source_type": "web-search-aggregate",
        "addresses": ["K1"],
        "aggregated_from": aggregated_from,
    }
    fname = f"findings_mat-ws-{filename_suffix}.md" if filename_suffix else f"findings_{mat_id}.md"
    p = out_dir / fname
    p.write_text(f"---\n{yaml.dump(fm, allow_unicode=True, sort_keys=False)}---\n\nbody\n",
                 encoding="utf-8")
    return p


def _add_real_processed_mat(slug: str, variant: str, mat_id_marker: str,
                             triggered_by: str = "02-step0") -> str:
    """Add a fake processed mat with given triggered_by. Returns mat_id."""
    sm = make_search_meta(
        query="q", url=f"https://example.com/{mat_id_marker}",
        domain="example.com", domain_tier="other",
        triggered_by=triggered_by,
    )
    mat_id = add_material(
        slug=slug, filename=f"{mat_id_marker}.md",
        source_type="web-search", variant=variant,
        addresses=["K1"], search_meta=sm,
    )
    mark_processed(slug, mat_id, variant)
    return mat_id


def test_real_mats_only_fresh(tmp_topic):
    """No aggregate ID — pure real mat_ids, all covered → fresh."""
    slug, variant, _ = tmp_topic
    m1 = _add_real_processed_mat(slug, variant, "a", triggered_by="02-step0")
    m2 = _add_real_processed_mat(slug, variant, "b", triggered_by="02-step0")
    topic_io.set_output_referenced_mats(slug, "01_business_panorama", [m1, m2], variant)
    result = list_affected_outputs(slug, variant)
    assert result["01_business_panorama"]["reason"] == "fresh"
    assert result["01_business_panorama"]["new_mat_ids"] == []


def test_aggregate_id_expands_via_frontmatter(tmp_topic):
    """ws-aggregate-K# in referenced_mat_ids → expand via aggregated_from → fresh."""
    slug, variant, tmpdir = tmp_topic
    m1 = _add_real_processed_mat(slug, variant, "a")
    m2 = _add_real_processed_mat(slug, variant, "b")
    _write_aggregate_finding(tmpdir, slug, variant, "ws-aggregate-K1",
                              aggregated_from=[m1, m2])
    # Output references the aggregate ID + nothing else
    topic_io.set_output_referenced_mats(slug, "01_business_panorama",
                                         ["ws-aggregate-K1"], variant)
    result = list_affected_outputs(slug, variant)
    assert result["01_business_panorama"]["reason"] == "fresh", (
        f"Expected fresh after aggregate expansion, got {result['01_business_panorama']}"
    )


def test_aggregate_id_legacy_filename(tmp_topic):
    """Legacy naming: ws-aggregate-K1 stored as findings_mat-ws-K1.md (cn-commercial-space pattern)."""
    slug, variant, tmpdir = tmp_topic
    m1 = _add_real_processed_mat(slug, variant, "a")
    _write_aggregate_finding(tmpdir, slug, variant, "ws-aggregate-K1",
                              aggregated_from=[m1],
                              filename_suffix="K1")  # filename: findings_mat-ws-K1.md
    topic_io.set_output_referenced_mats(slug, "01_business_panorama",
                                         ["ws-aggregate-K1"], variant)
    result = list_affected_outputs(slug, variant)
    assert result["01_business_panorama"]["reason"] == "fresh"


def test_aggregate_fallback_when_no_aggregated_from(tmp_topic):
    """Aggregate finding exists but aggregated_from missing → preserve virtual ID → stale."""
    slug, variant, tmpdir = tmp_topic
    m1 = _add_real_processed_mat(slug, variant, "a")
    # Write aggregate finding without aggregated_from
    out_dir = tmpdir / "topics" / slug / variant / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "findings_ws-aggregate-K1.md").write_text(
        "---\nmat_id: ws-aggregate-K1\n---\nbody\n", encoding="utf-8"
    )
    topic_io.set_output_referenced_mats(slug, "01_business_panorama",
                                         ["ws-aggregate-K1"], variant)
    result = list_affected_outputs(slug, variant)
    # Unresolved virtual ID + un-referenced real mat → stale
    assert result["01_business_panorama"]["reason"] == "stale"


def test_aggregate_finding_missing_falls_back(tmp_topic):
    """Aggregate finding file absent entirely → preserve virtual ID → stale."""
    slug, variant, _ = tmp_topic
    topic_io.set_output_referenced_mats(slug, "01_business_panorama",
                                         ["ws-aggregate-K1"], variant)
    result = list_affected_outputs(slug, variant)
    assert result["01_business_panorama"]["reason"] == "stale"


def test_exclude_triggered_by_default_skips_prescan_mats(tmp_topic):
    """Default exclude_triggered_by drops 00/01-prescan mats from processed_ids."""
    slug, variant, _ = tmp_topic
    # Two prescan mats and one 02-step0 mat
    p1 = _add_real_processed_mat(slug, variant, "p1", triggered_by="00-prescan")
    p2 = _add_real_processed_mat(slug, variant, "p2", triggered_by="01-prescan")
    s1 = _add_real_processed_mat(slug, variant, "s1", triggered_by="02-step0")
    # Output only references the 02-step0 mat
    topic_io.set_output_referenced_mats(slug, "01_business_panorama", [s1], variant)
    result = list_affected_outputs(slug, variant)
    # Prescan mats excluded → output is fresh
    assert result["01_business_panorama"]["reason"] == "fresh"
    # Sanity: pass exclude_triggered_by=() and see prescan mats trigger stale
    result_no_excl = list_affected_outputs(slug, variant, exclude_triggered_by=())
    assert result_no_excl["01_business_panorama"]["reason"] == "stale"
    assert set(result_no_excl["01_business_panorama"]["new_mat_ids"]) == {p1, p2}


def test_new_mats_trigger_stale_with_aggregate_present(tmp_topic):
    """Adding a new real mat after synthesis → stale, even if aggregate covers old ones."""
    slug, variant, tmpdir = tmp_topic
    m1 = _add_real_processed_mat(slug, variant, "a")
    _write_aggregate_finding(tmpdir, slug, variant, "ws-aggregate-K1",
                              aggregated_from=[m1])
    topic_io.set_output_referenced_mats(slug, "01_business_panorama",
                                         ["ws-aggregate-K1"], variant)
    # Now add a new mat (post-synthesis)
    m_new = _add_real_processed_mat(slug, variant, "new")
    result = list_affected_outputs(slug, variant)
    assert result["01_business_panorama"]["reason"] == "stale"
    assert m_new in result["01_business_panorama"]["new_mat_ids"]

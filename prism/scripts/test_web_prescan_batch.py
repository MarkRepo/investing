"""Tests for register_web_search_batch helper."""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts import topic as topic_io
from prism.scripts.manifest import create_manifest, read_manifest


@pytest.fixture
def tmp_topic(monkeypatch):
    """Create a tmp topic with manifest, redirect PRISM_ROOT to tmp dir."""
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    slug = "test-slug"
    variant = "test-variant"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(
        slug=slug, display_name="Test", topic_type="company",
        question="Q?", geo="US", depth="quick", variant=variant,
        ticker="US_TEST",
    )
    create_manifest(slug, variant)
    yield slug, variant, tmpdir
    shutil.rmtree(tmpdir)


def test_batch_registers_high_mid_skips_low(tmp_topic):
    """High and mid hits are registered; low is skipped."""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    hits = [
        {"title": "Reuters report", "url": "https://reuters.com/x", "snippet": "..."},
        {"title": "Random blog", "url": "https://random.example/x", "snippet": "..."},
        {"title": "Sohu news", "url": "https://sohu.com/x", "snippet": "..."},
    ]
    summary = register_web_search_batch(
        slug=slug, variant=variant,
        query="Test query",
        addresses=["K1"],
        triggered_by="01-prescan",
        hits=hits,
    )
    assert summary["n_high"] >= 1
    assert summary["n_low"] >= 1
    mat_ids = [m for m in summary["mat_ids"] if m]
    manifest = read_manifest(slug, variant)
    assert len(manifest["materials"]) == len(mat_ids)


def test_batch_appends_search_log(tmp_topic):
    """Batch call appends one log entry with totals."""
    from prism.scripts.web_prescan import register_web_search_batch, list_search_log

    slug, variant, _ = tmp_topic
    register_web_search_batch(
        slug=slug, variant=variant, query="Q", addresses=["K1"],
        triggered_by="02-step0",
        hits=[{"title": "T", "url": "https://reuters.com/a", "snippet": "s"}],
    )
    entries = list_search_log(slug, variant)
    assert len(entries) == 1
    assert entries[0]["triggered_by"] == "02-step0"
    assert entries[0]["query"] == "Q"


def test_batch_resolves_matching_todos(tmp_topic):
    """Todos with matching addresses get auto-resolved."""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    topic_io.set_user_todos(slug, [
        {"task": "find K1 evidence", "priority": "P0",
         "info_tier": "public", "addresses": ["K1"]},
    ], variant)
    summary = register_web_search_batch(
        slug=slug, variant=variant, query="Q", addresses=["K1"],
        triggered_by="02-step0",
        hits=[{"title": "T", "url": "https://reuters.com/a", "snippet": "s"}],
    )
    assert len(summary["resolved_todos"]) == 1
    assert summary["resolved_todos"][0]["task"] == "find K1 evidence"


def test_batch_with_explicit_confidence_overrides(tmp_topic):
    """Caller can override confidence per hit."""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    hits = [
        {"title": "T", "url": "https://random.example/a", "snippet": "s",
         "confidence": 0.95, "domain_tier": "llm-judged-official"},
    ]
    summary = register_web_search_batch(
        slug=slug, variant=variant, query="Q", addresses=["K1"],
        triggered_by="01-prescan", hits=hits,
    )
    assert summary["n_high"] == 1

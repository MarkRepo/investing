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
        short_name="Test",
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


def test_triggered_by_persists_to_search_meta(tmp_topic):
    """register_web_search_batch threads triggered_by into mat.search_meta."""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    register_web_search_batch(
        slug=slug, variant=variant, query="Q", addresses=["K1"],
        triggered_by="02-step0",
        hits=[{"title": "T", "url": "https://reuters.com/a", "snippet": "s"}],
    )
    manifest = read_manifest(slug, variant)
    assert len(manifest["materials"]) == 1
    sm = manifest["materials"][0].get("search_meta") or {}
    assert sm.get("triggered_by") == "02-step0"


def test_inline_finding_auto_for_synth_trigger(tmp_topic):
    """triggered_by='04-synth' auto-writes findings_{mat_id}.md + mark_processed."""
    from prism.scripts.web_prescan import register_web_search_batch
    from prism.scripts.manifest import list_unprocessed

    slug, variant, tmpdir = tmp_topic
    summary = register_web_search_batch(
        slug=slug, variant=variant, query="missing data",
        addresses=["K1"], triggered_by="04-synth",
        hits=[{"title": "T", "url": "https://reuters.com/a", "snippet": "s"}],
    )
    assert summary["n_high"] == 1
    paths = summary["inline_finding_paths"]
    assert len(paths) == 1
    fp = Path(paths[0])
    assert fp.exists()
    text = fp.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "source_type: web-search-inline" in text
    # mat now mark_processed → not in unprocessed list
    assert list_unprocessed(slug, variant) == []


def test_inline_finding_off_by_default_for_prescan(tmp_topic):
    """triggered_by='02-step0' (not in _INLINE_FINDING_TRIGGERS) → no inline finding."""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    summary = register_web_search_batch(
        slug=slug, variant=variant, query="Q", addresses=["K1"],
        triggered_by="02-step0",
        hits=[{"title": "T", "url": "https://reuters.com/a", "snippet": "s"}],
    )
    assert summary["inline_finding_paths"] == []


def test_inline_finding_explicit_override(tmp_topic):
    """inline_finding=True forces inline finding even outside auto-trigger set."""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    summary = register_web_search_batch(
        slug=slug, variant=variant, query="Q", addresses=["K1"],
        triggered_by="02-step0", inline_finding=True,
        hits=[{"title": "T", "url": "https://reuters.com/a", "snippet": "s"}],
    )
    assert len(summary["inline_finding_paths"]) == 1


def test_inline_finding_skips_existing_file(tmp_topic):
    """Already-written finding (handcrafted) not overwritten by auto-inline."""
    from prism.scripts.web_prescan import register_web_search_batch, register_inline_finding

    slug, variant, tmpdir = tmp_topic
    # Pre-create a finding with a known mat_id won't work without knowing it,
    # so we register first with auto-inline off, then re-call with same URL.
    summary1 = register_web_search_batch(
        slug=slug, variant=variant, query="Q", addresses=["K1"],
        triggered_by="02-step0", inline_finding=False,
        hits=[{"title": "T", "url": "https://reuters.com/a", "snippet": "s"}],
    )
    mat_id = summary1["mat_ids"][0]
    assert mat_id
    # Manually write a richer finding
    fp = register_inline_finding(
        slug=slug, variant=variant, mat_id=mat_id,
        content="# my handcrafted finding", addresses=["K1"],
    )
    handcrafted = fp.read_text(encoding="utf-8")
    # Now re-trigger via 04-synth (same URL → dedup hits + auto-inline should skip overwrite)
    register_web_search_batch(
        slug=slug, variant=variant, query="Q2", addresses=["K1"],
        triggered_by="04-synth",
        hits=[{"title": "T", "url": "https://reuters.com/a", "snippet": "different snippet"}],
    )
    assert fp.read_text(encoding="utf-8") == handcrafted


def test_runtime_whitelist_promote_then_classify(tmp_topic, monkeypatch):
    """promote_to_whitelist makes classify_domain return 'whitelist' for that host."""
    from prism.scripts import web_prescan
    slug, variant, tmpdir = tmp_topic

    # Redirect runtime whitelist file to tmp + clear cache
    fake_path = tmpdir / "data" / "_runtime_whitelist.yaml"
    monkeypatch.setattr(web_prescan, "_RUNTIME_WHITELIST_PATH", fake_path)
    monkeypatch.setattr(web_prescan, "_runtime_whitelist_cache", None)

    # Pre-promote: classify returns 'other'
    assert web_prescan.classify_domain("https://news.examplevertical.com/foo") == "other"

    web_prescan.promote_to_whitelist(
        host="examplevertical.com",
        reason="行业垂直媒体",
        evidence_mat_ids=["mat-aaaaaa"],
    )
    # After promote: classify returns 'whitelist' (endswith match)
    assert web_prescan.classify_domain("https://news.examplevertical.com/foo") == "whitelist"
    assert web_prescan.classify_domain("https://examplevertical.com/x") == "whitelist"

    # demote round-trip
    assert web_prescan.demote_from_whitelist("examplevertical.com") is True
    assert web_prescan.classify_domain("https://examplevertical.com/x") == "other"


def test_runtime_whitelist_promote_validation(tmp_topic, monkeypatch):
    """promote_to_whitelist refuses empty host / reason / evidence."""
    from prism.scripts import web_prescan
    slug, variant, tmpdir = tmp_topic
    fake_path = tmpdir / "data" / "_runtime_whitelist.yaml"
    monkeypatch.setattr(web_prescan, "_RUNTIME_WHITELIST_PATH", fake_path)
    monkeypatch.setattr(web_prescan, "_runtime_whitelist_cache", None)

    with pytest.raises(ValueError):
        web_prescan.promote_to_whitelist("", "r", ["mat-x"])
    with pytest.raises(ValueError):
        web_prescan.promote_to_whitelist("h.com", "", ["mat-x"])
    with pytest.raises(ValueError):
        web_prescan.promote_to_whitelist("h.com", "r", [])

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
    monkeypatch.setattr("prism.scripts.web_prescan._STATE_DIR", tmpdir / "state" / "whitelist")
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


def test_batch_threads_rings_to_material(tmp_topic):
    """batch 传 rings → 登记的材料带上 rings（web-source 进 ring 轴）。"""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    register_web_search_batch(
        slug=slug, variant=variant, query="consensus eps",
        addresses=["K1"], triggered_by="04-synth",
        hits=[{"title": "Reuters consensus", "url": "https://reuters.com/c", "snippet": "x"}],
        rings=["consensus"],
    )
    manifest = read_manifest(slug, variant)
    web_mats = [m for m in manifest["materials"] if m["source_type"] == "web-search"]
    assert web_mats and web_mats[0].get("rings") == ["consensus"]


def test_failure_mode_none_when_at_least_one_in(tmp_topic):
    """至少 1 hit 入库时 failure_mode='none' / silent_failure=False。"""
    from prism.scripts.web_prescan import register_web_search_batch
    slug, variant, _ = tmp_topic
    s = register_web_search_batch(
        slug=slug, variant=variant, query="Q",
        addresses=["K1"], triggered_by="01-prescan",
        hits=[{"title": "Reuters", "url": "https://reuters.com/a", "snippet": "x"}],
    )
    assert s["failure_mode"] == "none"
    assert s["silent_failure"] is False


def test_failure_mode_upstream_empty_when_hits_zero(tmp_topic):
    """hits=[] → failure_mode='upstream_empty'（疑似 WebSearch 限流）。"""
    from prism.scripts.web_prescan import register_web_search_batch
    slug, variant, _ = tmp_topic
    s = register_web_search_batch(
        slug=slug, variant=variant, query="Q",
        addresses=["K1"], triggered_by="01-prescan", hits=[],
    )
    assert s["failure_mode"] == "upstream_empty"
    assert s["silent_failure"] is True


def test_failure_mode_all_low_band_when_hits_all_drop(tmp_topic):
    """hits>0 但全 non-WHITELIST → failure_mode='all_low_band'（H2 救回信号，不是限流）。"""
    from prism.scripts.web_prescan import register_web_search_batch
    slug, variant, _ = tmp_topic
    s = register_web_search_batch(
        slug=slug, variant=variant, query="Q",
        addresses=["K1"], triggered_by="01-prescan",
        hits=[
            {"title": "Blog A", "url": "https://random-no-tier.example/a", "snippet": "x"},
            {"title": "Blog B", "url": "https://another-blog.example/b", "snippet": "y"},
        ],
    )
    assert s["failure_mode"] == "all_low_band"
    assert s["silent_failure"] is True
    assert s["n_low"] == 2
    assert len(s["dropped_hits"]) == 2


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


def test_auto_resolve_hard_todo_bare_k_not_closed(tmp_topic):
    """F9：hard 深料 todo + 裸 K# web 命中 → 只标 in_progress，不假闭环 done。"""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    topic_io.set_user_todos(slug, [
        {"task": "历史行业镜鉴 industry-mirror", "priority": "P0",
         "info_tier": "hard", "addresses": ["K1"]},
    ], variant)
    summary = register_web_search_batch(
        slug=slug, variant=variant, query="Q", addresses=["K1"],
        triggered_by="01-prescan",
        hits=[{"title": "T", "url": "https://reuters.com/a", "snippet": "s"}],
    )
    assert summary["resolved_todos"] == [], "hard 深料裸 K# 命中不得闭环"
    todo = topic_io.read_topic(slug, variant)["user_todos"][0]
    assert todo["status"] == "in_progress"
    assert todo.get("covered_by"), "应记部分覆盖 covered_by"
    assert "事件锚" in (todo.get("coverage_note") or "")


def test_auto_resolve_hard_todo_event_anchored_closes(tmp_topic):
    """F9：hard 深料 todo 'K#@evt' + 同事件 mat 强命中 → done。"""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    topic_io.set_user_todos(slug, [
        {"task": "2026Q2 业绩会纪要", "priority": "P0",
         "info_tier": "hard", "addresses": ["K1@2026Q2-earnings"]},
    ], variant)
    summary = register_web_search_batch(
        slug=slug, variant=variant, query="Q", addresses=["K1@2026Q2-earnings"],
        triggered_by="01-prescan",
        hits=[{"title": "T", "url": "https://reuters.com/a", "snippet": "s"}],
    )
    assert len(summary["resolved_todos"]) == 1
    assert topic_io.read_topic(slug, variant)["user_todos"][0]["status"] == "done"


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




# ───────────────── 占位/编造 URL 守卫（修 [fabricated-url]）─────────────────

def test_looks_like_placeholder_url_unit():
    """纯函数：占位特征命中返原因串，真实 URL 返 None。"""
    from prism.scripts.web_prescan import _looks_like_placeholder_url

    assert _looks_like_placeholder_url("https://gov.cn/2026-xxxx/weichai.shtml")
    assert _looks_like_placeholder_url("https://example.com/a")
    assert _looks_like_placeholder_url("https://example.org/path")
    assert _looks_like_placeholder_url("https://site.com/.../trunc")
    assert _looks_like_placeholder_url("https://site.com/…")
    assert _looks_like_placeholder_url("https://<host>/a")
    assert _looks_like_placeholder_url("https://site.com/{id}")
    assert _looks_like_placeholder_url("https://your-domain.com/a")
    assert _looks_like_placeholder_url("https://placeholder.io/a")
    # 真实 URL 不误伤
    assert _looks_like_placeholder_url("https://reuters.com/business/x-2026-01") is None
    assert _looks_like_placeholder_url("https://sse.com.cn/disclosure/688518.html") is None
    assert _looks_like_placeholder_url("") is None


def test_batch_raises_on_placeholder_url(tmp_topic):
    """batch 里混入编造 URL（含 xxxx）→ register_web_search_result raise，整批中止。"""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    hits = [
        {"title": "潍柴招标", "url": "https://gov.cn/2026-xxxx/weichai.shtml", "snippet": "s"},
    ]
    with pytest.raises(ValueError, match="占位/编造 URL"):
        register_web_search_batch(
            slug=slug, variant=variant, query="Q", addresses=["K1"],
            triggered_by="04-synth", hits=hits,
        )


def test_single_register_raises_on_placeholder_url(tmp_topic):
    """单条入口同样守卫（batch 之外的直接调用也覆盖）。"""
    from prism.scripts.web_prescan import register_web_search_result

    slug, variant, _ = tmp_topic
    with pytest.raises(ValueError, match="占位/编造 URL"):
        register_web_search_result(
            slug=slug, variant=variant, query="Q",
            url="https://example.com/fabricated", title="T", snippet="s",
            addresses=["K1"],
        )

"""#4 — check_prescan_health 状态感知（复用/继承）测试

materials 是 slug 级共享、web_search_log 是 per-variant：复用/手动投料/重启会"料在、log 空"。
本趟 log 空时回退查 manifest 是否有网搜料 → 有则 'inherited' 而非误报 'failed'。
"""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts.topic import create_topic
from prism.scripts.manifest import add_material, create_manifest
from prism.scripts.web_prescan import check_prescan_health

VARIANT = "v"


@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.outputs._PRISM_ROOT", tmpdir)
    create_topic(
        slug="rc", display_name="X", topic_type="company",
        question="Q?", geo="CN", depth="quick", variant=VARIANT,
        ticker="SSE_688331", short_name="X",
    )
    create_manifest("rc", VARIANT)
    yield tmpdir
    shutil.rmtree(tmpdir)


def test_inherited_when_log_empty_but_web_material_present(tmp_topic):
    """本趟未跑 prescan query，但 manifest 有 web-search 料 → 'inherited' 不是 'failed'。"""
    add_material(slug="rc", filename="hit.md", source_type="web-search", variant=VARIANT)
    r = check_prescan_health("rc", VARIANT, expected_queries=5)
    assert r["status"] == "inherited"
    assert r["queries_run"] == 0
    assert r["queries_with_hits"] == 1
    assert r["failure_reason"] is None
    assert "note" in r


def test_inherited_recognizes_search_meta_even_if_source_type_differs(tmp_topic):
    """复用致 source_type 非 web-search，但带 search_meta 也算网搜料（兜底 mat_id churn）。"""
    add_material(
        slug="rc", filename="reused.md", source_type="reference", variant=VARIANT,
        confidence=0.6,
        search_meta={"query": "q", "url": "http://x", "searched_at": "2026-01-01",
                     "stale_at": "2026-02-01", "expire_at": "2026-03-01",
                     "domain": "x.com", "domain_tier": "mid"},
    )
    r = check_prescan_health("rc", VARIANT, expected_queries=5)
    assert r["status"] == "inherited"


def test_failed_when_log_empty_and_no_web_material(tmp_topic):
    """真·两手空空（只有年报、无任何网搜料、log 也空）→ 仍诚实判 'failed'。"""
    add_material(slug="rc", filename="20-F.htm", source_type="annual-report", variant=VARIANT)
    r = check_prescan_health("rc", VARIANT, expected_queries=5)
    assert r["status"] == "failed"
    assert r["queries_run"] == 0


def test_failed_when_completely_empty(tmp_topic):
    """连材料都没有 → 'failed'。"""
    r = check_prescan_health("rc", VARIANT, expected_queries=5)
    assert r["status"] == "failed"

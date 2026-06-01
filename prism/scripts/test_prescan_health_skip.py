"""prescan-health 假阴性修复测试（2026-06）

主 agent 跑了 prescan query 但主动没 register（top hit 已在库/已覆盖）时，须用
log_search_skipped 留痕。check_prescan_health 据 disposition 区分：
  - 'skipped-duplicate'/'skipped-covered' → 算校准命中（不再被误判未搜到）
  - 'skipped-lowtier'                     → 不算命中（诚实的未校准）
"""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts.topic import create_topic
from prism.scripts.manifest import create_manifest
from prism.scripts.web_prescan import (
    append_search_log,
    check_prescan_health,
    log_search_skipped,
)

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


def _log_registered_hit(query: str):
    """模拟一条 register_web_search_batch 入库成功的 prescan query。"""
    append_search_log(
        slug="rc", variant=VARIANT, query=query, n_results=5,
        n_high=1, n_mid=0, n_low=4, triggered_by="00-prescan",
    )


def test_covered_skip_counts_as_hit(tmp_topic):
    """报告场景：7 条都跑了，4 条入库 + 3 条因已覆盖主动跳过 → 7/7 = full（不再误判 partial）。"""
    for i in range(4):
        _log_registered_hit(f"q{i}")
    for i in range(3):
        log_search_skipped(
            slug="rc", variant=VARIANT, query=f"dup{i}",
            triggered_by="00-prescan", n_results=5, reason="skipped-covered",
        )
    r = check_prescan_health("rc", VARIANT, expected_queries=7)
    assert r["status"] == "full"
    assert r["queries_run"] == 7
    assert r["queries_with_hits"] == 7
    assert r["queries_skipped_covered"] == 3
    assert r["hit_rate"] == 1.0


def test_lowtier_skip_does_not_count_as_hit(tmp_topic):
    """低 tier 垃圾跳过是诚实的未校准：4 入库 + 3 lowtier 跳过 → 4/7 = partial。"""
    for i in range(4):
        _log_registered_hit(f"q{i}")
    for i in range(3):
        log_search_skipped(
            slug="rc", variant=VARIANT, query=f"junk{i}",
            triggered_by="00-prescan", n_results=5, reason="skipped-lowtier",
        )
    r = check_prescan_health("rc", VARIANT, expected_queries=7)
    assert r["status"] == "partial"
    assert r["queries_run"] == 7
    assert r["queries_with_hits"] == 4
    assert r["queries_skipped_covered"] == 0
    assert r["hit_rate"] == round(4 / 7, 3)


def test_invalid_reason_rejected(tmp_topic):
    """reason 必须是枚举之一，防自由文本绕过分类。"""
    with pytest.raises(ValueError):
        log_search_skipped(
            slug="rc", variant=VARIANT, query="q",
            triggered_by="00-prescan", n_results=5, reason="whatever",
        )


def test_backward_compat_entries_without_disposition(tmp_topic):
    """老 log entry 无 disposition 字段 → 仍按 n_high/n_mid 判，行为不变。"""
    _log_registered_hit("q0")
    _log_registered_hit("q1")
    r = check_prescan_health("rc", VARIANT, expected_queries=2)
    assert r["status"] == "full"
    assert r["queries_with_hits"] == 2
    assert r["queries_skipped_covered"] == 0

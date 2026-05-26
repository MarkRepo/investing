"""H5 — prescan_status 顶层污染消除回归。

H5 修订：
- set_thesis 不再写 thesis 顶层 prescan_status / prescan_failure_reason，只写 history[N]
- 新增 get_current_prescan_status helper，从 history[current_version] 读
- 新增 set_prescan_log helper + 顶层 topic.prescan_log 数组
- thesis.prescan_status 顶层在 set_thesis 时被一次性 pop（迁移）
"""
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from prism.scripts.topic import (
    create_topic,
    get_current_prescan_status,
    read_topic,
    set_prescan_log,
    set_thesis,
)
from prism.scripts.manifest import create_manifest

VARIANT = "v"


@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.outputs._PRISM_ROOT", tmpdir)
    yield tmpdir
    shutil.rmtree(tmpdir)


def _make_topic(slug="rc", **kwargs):
    defaults = dict(
        slug=slug, display_name="X", topic_type="company",
        question="Q?", geo="CN", depth="quick", variant=VARIANT,
        ticker="SSE_688331", short_name="X",
    )
    defaults.update(kwargs)
    create_topic(**defaults)
    create_manifest(slug, VARIANT)


# ---------------------------------------------------------------------------
# 1. set_thesis 不再写顶层 (H5 核心修法)
# ---------------------------------------------------------------------------

def test_set_thesis_does_not_write_top_level_prescan_status(tmp_topic):
    """set_thesis(prescan_status=...) 只写 history[N]，不写 thesis 顶层。"""
    _make_topic()
    set_thesis("rc", VARIANT, version=0, summary="t0", stage_set_at="00-init",
               prescan_status="full")
    data = read_topic("rc", VARIANT)
    thesis = data["thesis"]

    # 顶层不应有
    assert "prescan_status" not in thesis, (
        f"H5 修订要求 thesis 顶层不写 prescan_status，实际: {thesis.get('prescan_status')!r}"
    )
    assert "prescan_failure_reason" not in thesis

    # history[0] 必须有
    assert thesis["history"][0]["prescan_status"] == "full"


def test_set_thesis_failure_writes_history_only(tmp_topic):
    _make_topic()
    set_thesis("rc", VARIANT, version=0, summary="t0", stage_set_at="00-init",
               prescan_status="failed", prescan_failure_reason="WebSearch 限流",
               force_failed=True)
    thesis = read_topic("rc", VARIANT)["thesis"]
    assert "prescan_status" not in thesis
    assert "prescan_failure_reason" not in thesis
    assert thesis["history"][0]["prescan_status"] == "failed"
    assert thesis["history"][0]["prescan_failure_reason"] == "WebSearch 限流"


def test_set_thesis_migrates_legacy_top_level_field(tmp_topic):
    """老 yaml 顶层有 prescan_status，下次 set_thesis 时一次性清除。"""
    _make_topic()
    # 模拟老 yaml：手工写入顶层字段
    topic_path = tmp_topic / "topics" / "rc" / VARIANT / "topic.yaml"
    data = yaml.safe_load(topic_path.read_text(encoding="utf-8"))
    data["thesis"] = {
        "current_version": None,
        "last_updated": None,
        "history": [],
        "prescan_status": "failed",          # 老污染源
        "prescan_failure_reason": "stale",   # 老污染源
    }
    topic_path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")

    # 下一次 set_thesis 触发 migration
    set_thesis("rc", VARIANT, version=0, summary="new", stage_set_at="00-init",
               prescan_status="partial")
    thesis = read_topic("rc", VARIANT)["thesis"]
    assert "prescan_status" not in thesis, "老顶层字段应被 H5 migration 移除"
    assert "prescan_failure_reason" not in thesis
    assert thesis["history"][0]["prescan_status"] == "partial"


# ---------------------------------------------------------------------------
# 2. get_current_prescan_status helper
# ---------------------------------------------------------------------------

def test_get_current_prescan_status_no_thesis(tmp_topic):
    _make_topic()
    info = get_current_prescan_status("rc", VARIANT)
    assert info == {"status": None, "failure_reason": None, "version": None}


def test_get_current_prescan_status_returns_history_value(tmp_topic):
    _make_topic()
    set_thesis("rc", VARIANT, version=0, summary="t0", stage_set_at="00-init",
               prescan_status="full")
    info = get_current_prescan_status("rc", VARIANT)
    assert info == {"status": "full", "failure_reason": None, "version": 0}


def test_get_current_prescan_status_upgrades_with_version(tmp_topic):
    """v0=full → v1=partial：helper 取 v1（current_version 指向）。"""
    _make_topic()
    set_thesis("rc", VARIANT, version=0, summary="t0", stage_set_at="00-init",
               prescan_status="full")
    # 写 thesis_v1.md 让升版能通过
    (tmp_topic / "topics" / "rc" / VARIANT / "thesis_v1.md").write_text(
        "# v1\n\n- K1\n", encoding="utf-8",
    )
    set_thesis("rc", VARIANT, version=1, summary="t1", stage_set_at="04-synth",
               prescan_status="partial",
               prescan_failure_reason="部分 query 静默")
    info = get_current_prescan_status("rc", VARIANT)
    assert info["status"] == "partial"
    assert info["version"] == 1
    assert info["failure_reason"] == "部分 query 静默"


# ---------------------------------------------------------------------------
# 3. set_prescan_log — 后续轮次 prescan 独立留痕
# ---------------------------------------------------------------------------

def test_set_prescan_log_appends_to_topic_array(tmp_topic):
    _make_topic()
    entry = set_prescan_log("rc", VARIANT,
                            status="failed",
                            triggered_by="01-prescan",
                            hit_rate=0.2, queries_run=10, queries_with_hits=2,
                            failure_reason="WebSearch 限流静默返空")
    assert entry["status"] == "failed"
    assert entry["triggered_by"] == "01-prescan"
    assert entry["hit_rate"] == 0.2
    assert entry["queries_run"] == 10
    assert entry["queries_with_hits"] == 2
    assert entry["failure_reason"] == "WebSearch 限流静默返空"
    assert "round_at" in entry

    data = read_topic("rc", VARIANT)
    assert data["prescan_log"] == [entry]


def test_set_prescan_log_does_not_touch_thesis(tmp_topic):
    """后续轮次 prescan 失败 → 不污染 thesis 写时状态。"""
    _make_topic()
    set_thesis("rc", VARIANT, version=0, summary="t0", stage_set_at="00-init",
               prescan_status="full")
    # 模拟 workflow 01 Step 8 末尾 prescan 失败
    set_prescan_log("rc", VARIANT,
                    status="failed",
                    triggered_by="01-prescan",
                    failure_reason="WebSearch 静默返空")

    info = get_current_prescan_status("rc", VARIANT)
    # thesis_v0 写时状态保持 'full' 不被污染
    assert info["status"] == "full", (
        f"thesis 写时状态被污染！实际={info['status']}（应为 full）"
    )
    assert info["failure_reason"] is None

    # prescan_log 独立留痕
    data = read_topic("rc", VARIANT)
    assert data["prescan_log"][-1]["status"] == "failed"
    assert data["prescan_log"][-1]["triggered_by"] == "01-prescan"


def test_set_prescan_log_invalid_status_raises(tmp_topic):
    _make_topic()
    with pytest.raises(ValueError, match="status="):
        set_prescan_log("rc", VARIANT, status="weird", triggered_by="x")


def test_set_prescan_log_failed_requires_reason(tmp_topic):
    _make_topic()
    with pytest.raises(ValueError, match="failure_reason"):
        set_prescan_log("rc", VARIANT, status="failed", triggered_by="01-prescan")


def test_set_prescan_log_multi_rounds_accumulate(tmp_topic):
    _make_topic()
    set_prescan_log("rc", VARIANT, status="full", triggered_by="01-prescan", hit_rate=1.0)
    set_prescan_log("rc", VARIANT, status="partial", triggered_by="02-step0", hit_rate=0.7)
    set_prescan_log("rc", VARIANT, status="failed", triggered_by="06-daily-monitor",
                    failure_reason="API down", hit_rate=0.0)
    data = read_topic("rc", VARIANT)
    assert len(data["prescan_log"]) == 3
    assert [e["triggered_by"] for e in data["prescan_log"]] == [
        "01-prescan", "02-step0", "06-daily-monitor",
    ]


# ---------------------------------------------------------------------------
# 4. 集成场景：workflow 01 Step 8 失败不影响 critic 读取
# ---------------------------------------------------------------------------

def test_workflow01_step8_failure_does_not_break_critic_read(tmp_topic):
    """完整复现：thesis_v0 写时 full → workflow 01 Step 8 prescan 失败 → critic 读到 full。"""
    _make_topic()
    # workflow 00 Step 5.0：写 thesis_v0 + 标 prescan='full'
    set_thesis("rc", VARIANT, version=0, summary="thesis v0", stage_set_at="00-init",
               prescan_status="full")

    # workflow 01 Step 8：末尾再 prescan，WebSearch 限流失败
    set_prescan_log("rc", VARIANT,
                    status="failed", triggered_by="01-prescan",
                    failure_reason="WebSearch 静默返空", hit_rate=0.0)

    # workflow 05 Step 0.0 critic 读"thesis 写时状态"
    info = get_current_prescan_status("rc", VARIANT)
    # H5 前：会读到 'failed'（被污染），critic 误 BLOCK
    # H5 后：仍读到 'full'（绑 history[0]），critic 正常推进
    assert info["status"] == "full"

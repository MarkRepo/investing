"""macro topic 接进 daily-monitor：scan 多出 macro_due/macro_alert 桶。"""
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from prism.scripts import topic as topic_io
from prism.scripts import macro_registry as mr
from prism.scripts import monitor

SLUG = "global-macro-rates-liquidity"
VARIANT = "opus4.8"


@pytest.fixture
def macro_monitor_env(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.dashboard.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.monitor.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.monitor.WATCHLIST_PATH", tmpdir / "watchlist.yaml")
    monkeypatch.setattr("prism.scripts.monitor.QUEUE_PATH", tmpdir / "monitor_queue.yaml")
    monkeypatch.setattr("prism.scripts.macro_registry._PRISM_ROOT", tmpdir)
    (tmpdir / "topics").mkdir()
    topic_io.create_topic(
        slug=SLUG, display_name="宏观层", topic_type="macro",
        question="Q", geo="GLOBAL", depth="deep", variant=VARIANT,
        search_terms=["利率"],
    )
    mr.create_registry(SLUG, VARIANT)
    # 一条到期 event + 一条越带 alert series
    mr.upsert_input(SLUG, VARIANT, {
        "name": "NFP", "tier": "A", "cadence_type": "event", "targets": ["rates"],
        "mechanism": "CD", "causal_sentence": "x", "importance": "load_bearing",
        "source": "FRED", "fetch_method": "fred-api", "state": "改",
        "alert_series": False, "monitoring": {"enabled": True},
        "observed": {"next_due": "2026-06-01"},
    })
    mr.upsert_input(SLUG, VARIANT, {
        "name": "HY OAS", "tier": "B", "cadence_type": "series", "targets": ["liquidity"],
        "mechanism": "CO", "importance": "load_bearing", "source": "FRED",
        "fetch_method": "fred-api", "state": "改", "alert_series": True,
        "alert_band": {"delta": 75.0}, "monitoring": {"enabled": True},
        "observed": {"value": 400.0, "prev_value": 300.0},
    })
    yield SLUG, VARIANT, tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_macro_not_scanned_without_watch(macro_monitor_env):
    scan = monitor.scan_due_events(within_days=14)
    assert scan["macro_due"] == []
    assert scan["macro_alert"] == []


def test_macro_scanned_when_watched(macro_monitor_env):
    slug, variant, _ = macro_monitor_env
    monitor.add_watch(slug, scope="topic", variant=variant)
    scan = monitor.scan_due_events(within_days=14)
    assert {x["name"] for x in scan["macro_due"]} == {"NFP"}
    assert {x["name"] for x in scan["macro_alert"]} == {"HY OAS"}
    nfp = next(x for x in scan["macro_due"] if x["name"] == "NFP")
    assert nfp["slug"] == slug and nfp["variant"] == variant


def test_macro_watched_but_no_registry_surfaces(macro_monitor_env):
    slug, variant, tmpdir = macro_monitor_env
    monitor.add_watch(slug, scope="topic", variant=variant)
    (tmpdir / "topics" / slug / variant / "macro_inputs.yaml").unlink()
    scan = monitor.scan_due_events(within_days=14)
    assert scan["macro_due"] == [] and scan["macro_alert"] == []
    assert any(s.get("reason") == "no_macro_registry"
               and s["slug"] == slug for s in scan["skipped_no_sidecar"])


def test_propose_macro_updates_writes_queue(macro_monitor_env):
    slug, variant, _ = macro_monitor_env
    monitor.add_watch(slug, scope="topic", variant=variant)
    res = monitor.propose_macro_updates(within_days=14)
    assert res["added"] == 2  # NFP(due) + HY OAS(alert)
    q = {p["locator"]: p for p in monitor.load_queue()}
    assert "NFP" in q and "HY OAS" in q
    assert q["NFP"]["kind"] == "macro_input"
    # load_bearing → 建议重判
    assert q["NFP"]["requires_thesis_review"] is True
    assert q["NFP"]["living_feed_entry"]  # 预写文案非空


def test_confirm_macro_input_appends_living_feed(macro_monitor_env):
    slug, variant, tmpdir = macro_monitor_env
    monitor.add_watch(slug, scope="topic", variant=variant)
    monitor.propose_macro_updates(within_days=14)
    pid = {p["locator"]: p["proposal_id"] for p in monitor.load_queue()}["HY OAS"]
    out = monitor.confirm_flip(pid)
    assert out["status"] == "confirmed"
    feed = (tmpdir / "topics" / slug / variant / "outputs" / "08_living_feed.md").read_text(encoding="utf-8")
    assert "HY OAS" in feed


import json
import subprocess
import sys


def test_cli_macro_command(macro_monitor_env, monkeypatch):
    # CLI 直接调进程内函数即可验证命令分支存在；这里验证函数签名稳定
    slug, variant, _ = macro_monitor_env
    monitor.add_watch(slug, scope="topic", variant=variant)
    res = monitor.propose_macro_updates(within_days=14)
    assert "scanned_macro" in res


# ── 第二期 Task 10：monitor 周期内零-LLM FRED 抓取 ──

import asyncio


def test_run_monitor_cycle_invokes_fred_fetch(monkeypatch, macro_monitor_env):
    import app.monitor_runtime as mrt
    from prism.scripts import fred_fetch
    called = {}

    def fake_run(s, v):
        called["hit"] = (s, v)
        return {"fetched": 1, "derived": 0, "skipped": 0, "failed": 0}

    monkeypatch.setattr(fred_fetch, "run_fred_fetch", fake_run)
    monkeypatch.setenv("FRED_API_KEY", "k")
    asyncio.run(mrt.run_monitor_cycle())
    # 抓取按 macro topic 的 slug/variant 触发（来自 fixture 创建的宏观主题）
    assert called.get("hit") == (SLUG, VARIANT)


def test_fred_fetch_failure_does_not_break_cycle(monkeypatch, macro_monitor_env):
    import app.monitor_runtime as mrt
    from prism.scripts import fred_fetch

    def boom(s, v):
        raise RuntimeError("FRED down")

    monkeypatch.setattr(fred_fetch, "run_fred_fetch", boom)
    monkeypatch.setenv("FRED_API_KEY", "k")
    # 不抛即通过
    asyncio.run(mrt.run_monitor_cycle())


def test_run_monitor_cycle_invokes_recipe_fetch(monkeypatch, macro_monitor_env):
    import app.monitor_runtime as mrt
    from prism.scripts import fred_fetch, recipe_fetch
    called = {}

    monkeypatch.setattr(fred_fetch, "run_fred_fetch",
                        lambda s, v: {"fetched": 0, "derived": 0, "skipped": 0, "failed": 0})

    def fake_recipe(s, v):
        called["hit"] = (s, v)
        return {"fetched": 0, "skipped_todo": 0, "skipped_llm": 0, "failed": 0}

    monkeypatch.setattr(recipe_fetch, "run_recipe_fetch", fake_recipe)
    monkeypatch.setenv("FRED_API_KEY", "k")
    asyncio.run(mrt.run_monitor_cycle())
    assert called.get("hit") == (SLUG, VARIANT)


def test_recipe_fetch_failure_does_not_break_cycle(monkeypatch, macro_monitor_env):
    import app.monitor_runtime as mrt
    from prism.scripts import fred_fetch, recipe_fetch

    monkeypatch.setattr(fred_fetch, "run_fred_fetch",
                        lambda s, v: {"fetched": 0, "derived": 0, "skipped": 0, "failed": 0})

    def boom(s, v):
        raise RuntimeError("recipe source down")

    monkeypatch.setattr(recipe_fetch, "run_recipe_fetch", boom)
    monkeypatch.setenv("FRED_API_KEY", "k")
    # 不抛即通过
    asyncio.run(mrt.run_monitor_cycle())


# --- 统一 headless LLM 取数 ---

def test_build_macro_llm_prompt_native_search_and_json_return(macro_monitor_env):
    import app.monitor_runtime as mrt
    entries = [
        {"name": "固定页项", "availability": "llm", "source_url": "https://x/idx"},
        {"name": "检索项", "availability": "llm"},
    ]
    p = mrt._build_macro_llm_prompt(SLUG, VARIANT, entries)
    # 仍逐条列名 + 区分固定页/检索取法
    assert "固定页项" in p and "检索项" in p
    assert "固定页起点" in p and "检索式" in p
    # 原生检索：用 WebSearch/WebFetch，砍掉 MCP adaptor
    assert "WebSearch" in p
    assert "tavily" not in p and "exa" not in p and "serper" not in p
    # 去 Bash 回合：不调 macro_record/Bash，末尾只吐一个 JSON 数组
    assert "macro_record" not in p
    assert "json" in p.lower()
    assert "--acq-note" not in p and "--scriptable" not in p
    # JSON 字段约定（Python 落盘解析依赖这些键）
    for field in ("name", "value", "as_of", "evidence", "acq_note", "scriptable"):
        assert field in p


def test_cycle_does_not_launch_llm_only_reminds(monkeypatch, macro_monitor_env):
    """巡检对到期 llm/event 项**不拉任何 headless**，只在 cycle 结果给 macro_due_reminder 提示。

    出于成本/耗时：定时路径只跑 scripted（fred/recipe），LLM 取数改为用户手动点拉。
    """
    import app.monitor_runtime as mrt
    from prism.scripts import fred_fetch, recipe_fetch, claude_runner
    monkeypatch.setattr(fred_fetch, "run_fred_fetch",
                        lambda s, v: {"fetched": 0, "derived": 0, "skipped": 0, "failed": 0})
    monkeypatch.setattr(recipe_fetch, "run_recipe_fetch",
                        lambda s, v: {"fetched": 0, "skipped_todo": 0, "skipped_llm": 0, "failed": 0})
    # 开监控的 llm series 项 → due_llm_monitor_names 选中（series 恒取）
    mr.upsert_input(SLUG, VARIANT, {
        "name": "MOVE", "tier": "B", "cadence_type": "series", "targets": ["rates"],
        "mechanism": "CO", "importance": "confirming",
        "availability": "llm", "monitoring": {"enabled": True}})

    calls = {"n": 0}

    async def boom_streaming(*a, **k):
        calls["n"] += 1
        return ("ok", 0)

    async def boom_async(*a, **k):
        calls["n"] += 1
        return (0, "", "")

    monkeypatch.setattr(claude_runner, "run_headless_streaming", boom_streaming)
    monkeypatch.setattr(claude_runner, "run_headless_async", boom_async)
    monkeypatch.setenv("FRED_API_KEY", "k")
    result = asyncio.run(mrt.run_monitor_cycle())

    assert "MOVE" in result.get("macro_due_reminder", [])   # 出提示
    assert "macro_llm" not in result                        # 不再自动拉
    assert calls["n"] == 0                                   # 零 headless、零 token（本 fixture 无 company 到期）


def test_confirm_macro_regime_is_informational(tmp_path, monkeypatch):
    import yaml
    from prism.scripts import monitor
    from prism.scripts import topic as topic_mod
    monkeypatch.setattr(monitor, "PRISM_ROOT", tmp_path)
    monkeypatch.setattr(monitor, "QUEUE_PATH", tmp_path / "monitor_queue.yaml")
    monkeypatch.setattr(topic_mod, "PRISM_ROOT", tmp_path)
    d = tmp_path / "topics" / "pdd" / "v" / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    monitor.propose_flips([{
        "slug": "pdd", "variant": "v", "kind": "macro_regime", "locator": "fx_cny",
        "proposed_value": "regime_shift", "living_feed_entry": "## t 宏观体制变化\nx",
        "rationale": "r", "requires_thesis_review": True}])
    pid = monitor.load_queue()[0]["proposal_id"]
    res = monitor.confirm_flip(pid)
    assert res["status"] == "confirmed"
    # 信息型：living_feed 被追加，无 sidecar 翻牌报错
    feed = (d / "08_living_feed.md")
    assert feed.exists() and "宏观体制变化" in feed.read_text(encoding="utf-8")

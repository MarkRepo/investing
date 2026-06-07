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

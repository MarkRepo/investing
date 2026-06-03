"""Tests for monitor.scan_due_events — bucketing, date edge cases, watchlist gate."""
from prism.scripts import monitor
from prism.scripts.conftest import SLUG, VARIANT


def test_scan_empty_without_watchlist(monitor_env):
    """No watch → scan returns all-empty (watchlist is the gate)."""
    scan = monitor.scan_due_events(within_days=14)
    assert scan["due_signposts"] == []
    assert scan["due_kills"] == []


def test_scan_topic_watch_buckets(monitor_env):
    slug, variant, _ = monitor_env
    monitor.add_watch(slug, scope="topic")
    scan = monitor.scan_due_events(within_days=14)

    # due: overdue signpost only (others are far future / bad date)
    due_events = {s["event"] for s in scan["due_signposts"]}
    assert "overdue event" in due_events
    assert "far future" not in due_events
    # due kill: kill_due (overdue), not kill_future
    due_kills = {k["locator"] for k in scan["due_kills"]}
    assert "kill_due" in due_kills
    assert "kill_future" not in due_kills


def test_scan_unparseable_surfaced_not_dropped(monitor_env):
    slug, variant, _ = monitor_env
    monitor.add_watch(slug, scope="topic")
    scan = monitor.scan_due_events(within_days=14)
    fields = {(u["field"], u.get("event") or u.get("locator")) for u in scan["unparseable"]}
    assert ("signpost", "bad date event") in fields
    assert ("kill", "kill_baddate") in fields


def test_scan_no_false_price_breach_in_hold_zone(monitor_env):
    slug, variant, _ = monitor_env
    monitor.add_watch(slug, scope="topic")
    scan = monitor.scan_due_events(within_days=14)
    assert scan["price_breach"] == []  # 73.64 is in hold, not buy zone


def test_scan_price_breach_when_in_buy_zone(monitor_env, monkeypatch):
    slug, variant, _ = monitor_env
    monitor.add_watch(slug, scope="topic")
    monkeypatch.setattr("prism.scripts.market_data.get_quote",
                        lambda s, v: {"close": 50.0, "date": "2026-06-03"})
    scan = monitor.scan_due_events(within_days=14)
    assert len(scan["price_breach"]) == 1
    assert scan["price_breach"][0]["zone"] == "strong_buy"


def test_scan_price_unavailable_on_error(monitor_env, monkeypatch):
    slug, variant, _ = monitor_env
    monitor.add_watch(slug, scope="topic")
    monkeypatch.setattr("prism.scripts.market_data.get_quote",
                        lambda s, v: {"error": "halted"})
    scan = monitor.scan_due_events(within_days=14)
    assert scan["price_breach"] == []
    assert any(p["slug"] == slug for p in scan["price_unavailable"])


def test_scan_event_scope_only_that_locator(monitor_env):
    slug, variant, _ = monitor_env
    from prism.scripts import sidecar_edit as se
    loc = se.signpost_locator("2026-05-01", "overdue event")
    monitor.add_watch(slug, scope="event", kind="signpost", locator=loc)
    scan = monitor.scan_due_events(within_days=14)
    # only the watched signpost can appear; kill not watched → none
    assert all(s["locator"] == loc for s in scan["due_signposts"])
    assert scan["due_kills"] == []


def test_scan_skips_missing_sidecar(monitor_env, monkeypatch):
    slug, variant, tmpdir = monitor_env
    monitor.add_watch(slug, scope="topic")
    # delete sidecar
    (tmpdir / "topics" / slug / variant / "outputs" / "07_decision_kit.yaml").unlink()
    scan = monitor.scan_due_events(within_days=14)
    assert any(s["slug"] == slug for s in scan["skipped_no_sidecar"])

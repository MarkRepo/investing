"""Tests for watchlist — add/remove, two-level granularity, idempotency."""
import pytest

from prism.scripts import monitor
from prism.scripts.conftest import SLUG, VARIANT


def test_add_topic_scope(monitor_env):
    slug, variant, _ = monitor_env
    e = monitor.add_watch(slug, scope="topic")
    assert e["scope"] == "topic" and e["variant"] == variant
    assert len(monitor.load_watchlist()) == 1


def test_add_is_idempotent(monitor_env):
    slug, _, _ = monitor_env
    monitor.add_watch(slug, scope="topic")
    monitor.add_watch(slug, scope="topic")
    assert len(monitor.load_watchlist()) == 1


def test_event_scope_requires_kind(monitor_env):
    slug, _, _ = monitor_env
    with pytest.raises(ValueError):
        monitor.add_watch(slug, scope="event")  # no kind


def test_event_signpost_requires_locator(monitor_env):
    slug, _, _ = monitor_env
    with pytest.raises(ValueError):
        monitor.add_watch(slug, scope="event", kind="signpost")  # no locator


def test_two_level_coexist(monitor_env):
    slug, _, _ = monitor_env
    monitor.add_watch(slug, scope="topic")
    monitor.add_watch(slug, scope="event", kind="kill", locator="kill_due")
    assert len(monitor.load_watchlist()) == 2


def test_remove_by_slug_clears_all(monitor_env):
    slug, _, _ = monitor_env
    monitor.add_watch(slug, scope="topic")
    monitor.add_watch(slug, scope="event", kind="kill", locator="kill_due")
    removed = monitor.remove_watch(slug)
    assert removed == 2
    assert monitor.load_watchlist() == []


def test_remove_precise(monitor_env):
    slug, _, _ = monitor_env
    monitor.add_watch(slug, scope="topic")
    monitor.add_watch(slug, scope="event", kind="kill", locator="kill_due")
    removed = monitor.remove_watch(slug, scope="event", kind="kill", locator="kill_due")
    assert removed == 1
    remaining = monitor.load_watchlist()
    assert len(remaining) == 1 and remaining[0]["scope"] == "topic"


def test_add_unknown_slug_raises(monitor_env):
    with pytest.raises(ValueError):
        monitor.add_watch("no-such-slug", scope="topic")

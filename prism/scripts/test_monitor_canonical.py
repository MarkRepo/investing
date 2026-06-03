"""Test monitor picks the SAME canonical variant the dashboard renders."""
from prism.scripts import dashboard, monitor
from prism.scripts.conftest import SLUG, VARIANT


def test_canonical_aligns_dashboard_and_monitor(monitor_env):
    slug, variant, _ = monitor_env
    # dashboard's public resolver
    assert dashboard.canonical_variant(slug) == variant
    # monitor.add_watch (variant omitted) must lock the same variant
    entry = monitor.add_watch(slug, scope="topic")
    assert entry["variant"] == variant


def test_canonical_none_for_unknown_slug(monitor_env):
    assert dashboard.canonical_variant("does-not-exist") is None

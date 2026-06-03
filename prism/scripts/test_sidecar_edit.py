"""Tests for sidecar_edit — signpost/kill flips with locator + optimistic lock."""
import pytest

from prism.scripts import sidecar_edit as se
from prism.scripts.conftest import SLUG, VARIANT


def test_signpost_locator_disambiguates_same_date():
    l1 = se.signpost_locator("2026-08-01", "Rule 605")
    l2 = se.signpost_locator("2026-08-01", "SCHW Q2")
    assert l1 != l2


def test_flip_only_the_matched_dup_date_signpost(monitor_env):
    slug, variant, _ = monitor_env
    loc = se.signpost_locator("2026-08-01", "SCHW Q2")
    res = se.set_signpost_triggered(slug, variant, loc, "bear")
    assert res["event"] == "SCHW Q2"
    assert res["triggered"] == "bear"
    # the other 2026-08-01 (Rule 605) must remain untouched
    import yaml
    p = (se.PRISM_ROOT / "topics" / slug / variant / "outputs" / "07_decision_kit.yaml")
    sps = yaml.safe_load(p.read_text())["signposts"]
    rule605 = next(s for s in sps if s["event"] == "Rule 605")
    assert rule605["triggered"] is None


def test_signpost_three_state_validation(monitor_env):
    slug, variant, _ = monitor_env
    loc = se.signpost_locator("2026-05-01", "overdue event")
    se.set_signpost_triggered(slug, variant, loc, "bull")
    with pytest.raises(ValueError):
        se.set_signpost_triggered(slug, variant, loc, "maybe")  # not in {None,bull,bear}


def test_optimistic_lock_rejects_on_mismatch(monitor_env):
    slug, variant, _ = monitor_env
    loc = se.signpost_locator("2026-05-01", "overdue event")
    # current triggered is None; expecting "bull" → stale
    with pytest.raises(se.StaleProposal):
        se.set_signpost_triggered(slug, variant, loc, "bear", expected_current="bull")


def test_locator_not_found_is_stale(monitor_env):
    slug, variant, _ = monitor_env
    with pytest.raises(se.StaleProposal):
        se.set_signpost_triggered(slug, variant, "deadbeef", "bull")


def test_kill_status_enum_and_flip(monitor_env):
    slug, variant, _ = monitor_env
    res = se.set_kill_status(slug, variant, "kill_due", "triggered_bear",
                             expected_current="pending")
    assert res["status"] == "triggered_bear"
    with pytest.raises(ValueError):
        se.set_kill_status(slug, variant, "kill_due", "exploded")  # bad enum


def test_kill_not_found_is_stale(monitor_env):
    slug, variant, _ = monitor_env
    with pytest.raises(se.StaleProposal):
        se.set_kill_status(slug, variant, "no_such_kill", "cleared")

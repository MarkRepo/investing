"""Tests for monitor queue — propose idempotency, confirm, discard, stale, living_feed."""
from prism.scripts import monitor, sidecar_edit
from prism.scripts.conftest import SLUG, VARIANT


def _signpost_proposal(slug, variant, locator, value="bull"):
    return {
        "slug": slug, "variant": variant, "kind": "signpost", "locator": locator,
        "proposed_value": value, "expected_current": None,
        "evidence_urls": ["https://example.com/x"],
        "living_feed_entry": "## 2026-06-03 test event\n**关键信息**：x",
        "rationale": "test", "requires_thesis_review": False,
    }


def test_propose_is_idempotent_by_target(monitor_env):
    slug, variant, _ = monitor_env
    loc = sidecar_edit.signpost_locator("2026-05-01", "overdue event")
    monitor.propose_flips([_signpost_proposal(slug, variant, loc, "bull")])
    monitor.propose_flips([_signpost_proposal(slug, variant, loc, "bear")])  # same target
    pending = monitor.load_queue()
    assert len(pending) == 1
    assert pending[0]["proposed_value"] == "bear"  # overwritten


def test_confirm_writes_back_and_appends_feed(monitor_env):
    slug, variant, tmpdir = monitor_env
    loc = sidecar_edit.signpost_locator("2026-05-01", "overdue event")
    monitor.propose_flips([_signpost_proposal(slug, variant, loc, "bull")])
    pid = monitor.load_queue()[0]["proposal_id"]
    res = monitor.confirm_flip(pid)
    assert res["status"] == "confirmed"

    # sidecar flipped
    import yaml
    p = tmpdir / "topics" / slug / variant / "outputs" / "07_decision_kit.yaml"
    sps = yaml.safe_load(p.read_text())["signposts"]
    assert next(s for s in sps if s["event"] == "overdue event")["triggered"] == "bull"
    # living_feed appended
    feed = tmpdir / "topics" / slug / variant / "outputs" / "08_living_feed.md"
    assert feed.exists() and "test event" in feed.read_text()


def test_repeat_confirm_is_noop(monitor_env):
    slug, variant, tmpdir = monitor_env
    loc = sidecar_edit.signpost_locator("2026-05-01", "overdue event")
    monitor.propose_flips([_signpost_proposal(slug, variant, loc)])
    pid = monitor.load_queue()[0]["proposal_id"]
    monitor.confirm_flip(pid)
    feed = tmpdir / "topics" / slug / variant / "outputs" / "08_living_feed.md"
    body_after_first = feed.read_text()
    res2 = monitor.confirm_flip(pid)
    assert res2.get("noop") is True
    assert feed.read_text() == body_after_first  # no double-append


def test_stale_proposal_when_expected_current_mismatch(monitor_env):
    slug, variant, _ = monitor_env
    loc = sidecar_edit.signpost_locator("2026-05-01", "overdue event")
    p = _signpost_proposal(slug, variant, loc, "bull")
    p["expected_current"] = "bear"  # but actual is None → stale
    monitor.propose_flips([p])
    pid = monitor.load_queue()[0]["proposal_id"]
    res = monitor.confirm_flip(pid)
    assert res["status"] == "stale"


def test_discard(monitor_env):
    slug, variant, _ = monitor_env
    loc = sidecar_edit.signpost_locator("2026-05-01", "overdue event")
    monitor.propose_flips([_signpost_proposal(slug, variant, loc)])
    pid = monitor.load_queue()[0]["proposal_id"]
    monitor.discard_flip(pid)
    assert monitor.load_queue()[0]["status"] == "discarded"


def test_propose_skips_confirmed(monitor_env):
    slug, variant, _ = monitor_env
    loc = sidecar_edit.signpost_locator("2026-05-01", "overdue event")
    monitor.propose_flips([_signpost_proposal(slug, variant, loc)])
    pid = monitor.load_queue()[0]["proposal_id"]
    monitor.confirm_flip(pid)
    r = monitor.propose_flips([_signpost_proposal(slug, variant, loc, "bear")])
    assert r["skipped_confirmed"] == 1  # confirmed not overwritten


def test_thesis_review_stamp_and_autoclear(monitor_env):
    """confirm 带 requires_thesis_review 的 kill → 盖戳;跑过 05(critic.at 晚于 since)→ 自动消。"""
    slug, variant, _ = monitor_env
    from prism.scripts import topic as topic_io
    monitor.propose_flips([{
        "slug": slug, "variant": variant, "kind": "kill", "locator": "kill_due",
        "proposed_value": "triggered_bear", "expected_current": "pending",
        "evidence_urls": ["https://example.com/k"],
        "living_feed_entry": "## 2026-06-03 kill 触发\n**关键信息**：x",
        "rationale": "kill 触发", "requires_thesis_review": True,
    }])
    pid = monitor.load_queue()[0]["proposal_id"]
    monitor.confirm_flip(pid)
    marker = topic_io.get_pending_thesis_review(slug, variant)
    assert marker is not None and marker["locator"] == "kill_due"
    # 破位确认后跑过一次 05(critic.at 远晚于 since)→ 视为已消化
    topic_io.update_topic(slug, variant, critic={"at": "2099-01-01T00:00:00+00:00", "verdict": "approve"})
    assert topic_io.get_pending_thesis_review(slug, variant) is None


def test_no_stamp_when_review_not_required(monitor_env):
    """普通 bull 翻牌(requires_thesis_review=False)不该盖戳。"""
    slug, variant, _ = monitor_env
    from prism.scripts import topic as topic_io
    loc = sidecar_edit.signpost_locator("2026-05-01", "overdue event")
    monitor.propose_flips([_signpost_proposal(slug, variant, loc, "bull")])
    pid = monitor.load_queue()[0]["proposal_id"]
    monitor.confirm_flip(pid)
    assert topic_io.get_pending_thesis_review(slug, variant) is None


def test_confirm_registers_evidence_to_websearch(monitor_env):
    """confirm 把 proposal.evidence 注册进 web_search 库,addressed 到 signpost 锚点,
    triggered_by=06-daily-monitor;重复 confirm 不重注册。这是"巡检不白做"的机械保证。"""
    slug, variant, _ = monitor_env
    from prism.scripts import manifest as manifest_io
    manifest_io.create_manifest(slug, variant)  # register_web_search 需要 manifest
    loc = sidecar_edit.signpost_locator("2026-05-01", "overdue event")
    p = _signpost_proposal(slug, variant, loc, "bear")
    p["requires_thesis_review"] = True
    p["evidence"] = [{
        "title": "SEC final rule on odd-lot data",
        "url": "https://www.sec.gov/files/rules/final/2024/34-99626.pdf",
        "snippet": "odd-lot quotes now public via SIP",
        "domain_tier": "whitelist",  # 强制高 band,测试不依赖域名分类 overlay
    }]
    monitor.propose_flips([p])
    pid = monitor.load_queue()[0]["proposal_id"]
    res = monitor.confirm_flip(pid)
    assert res["status"] == "confirmed"
    assert res.get("evidence_register_error") is None

    q = next(x for x in monitor.load_queue() if x["proposal_id"] == pid)
    assert q.get("evidence_registered") is True
    assert q.get("registered_mat_ids")  # 至少 1 条入库
    assert q.get("evidence_anchor", "").startswith("signpost:overdue event")

    # 幂等:重复 confirm 为 noop,不重注册
    res2 = monitor.confirm_flip(pid)
    assert res2.get("noop") is True


def test_price_breach_proposal_confirms_feed_only(monitor_env, monkeypatch):
    slug, variant, tmpdir = monitor_env
    monitor.add_watch(slug, scope="topic")
    monkeypatch.setattr("prism.scripts.market_data.get_quote",
                        lambda s, v: {"close": 50.0, "date": "2026-06-03"})
    monitor.propose_price_breaches(within_days=14)
    price = next(p for p in monitor.load_queue() if p["kind"] == "price")
    monitor.confirm_flip(price["proposal_id"])
    feed = tmpdir / "topics" / slug / variant / "outputs" / "08_living_feed.md"
    assert "价格破位" in feed.read_text()

"""Tests for observability probe layer."""
import tempfile
from pathlib import Path

import pytest

from prism.scripts import topic as topic_io
from prism.scripts import observability as obs


@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.gap_detector.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.outputs._PRISM_ROOT", tmpdir)
    slug, variant = "obs-test", "test"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(
        slug=slug, display_name="T", topic_type="company",
        question="Q?", geo="US", depth="quick", variant=variant,
        short_name="T", ticker="US_T",
    )
    return slug, variant


def _probe(probes, pid):
    return next((p for p in probes if p["probe_id"] == pid), None)


def test_run_probes_returns_trace_shape(tmp_topic):
    slug, variant = tmp_topic
    trace = obs.run_probes(slug, variant)
    assert trace["slug"] == slug and trace["variant"] == variant
    assert isinstance(trace["probes"], list)
    assert "summary" in trace


def test_cc1_addresses_missing_fails(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "有 addr", "priority": "P0", "addresses": ["K1"]},
        {"task": "缺 addr", "priority": "P1"},  # 无 addresses
    ], variant=variant)
    p = _probe(obs.run_probes(slug, variant)["probes"], "CC1")
    assert p["status"] == "fail"
    assert "缺 addr" in p["detail"]


def test_cc3_autofetch_debt_flags_unattempted(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "没抓过", "priority": "P0", "addresses": ["K1"], "info_tier": "public"},
    ], variant=variant)
    p = _probe(obs.run_probes(slug, variant)["probes"], "CC3")
    assert p["status"] == "fail"


def test_cc4_empty_undecided_flags(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "公开无源", "priority": "P0", "addresses": ["K1"]},
    ], variant=variant)
    topic_io.mark_todo_fetch(slug, variant, "公开无源", "empty", note="搜空")
    p = _probe(obs.run_probes(slug, variant)["probes"], "CC4")
    assert p["status"] == "fail"


def test_cc6_p0_pending_at_stage04_flags(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "P0 没收敛", "priority": "P0", "addresses": ["K1"]},
    ], variant=variant)
    topic_io.set_stage(slug, "04-synthesizing", variant)
    p = _probe(obs.run_probes(slug, variant)["probes"], "CC6")
    assert p["status"] == "fail"


def test_05x1_failed_prescan_approve_flags(tmp_topic):
    slug, variant = tmp_topic
    # failed prescan 残留：直接注入 thesis.history（set_thesis(failed) 要 force_failed
    # + reverse-check 副作用，单测注入更干净）。get_current_prescan_status 从 history 取。
    topic_io.update_topic(slug, variant, thesis={
        "current_version": 1,
        "history": [{"version": 1, "prescan_status": "failed"}],
    })
    topic_io.set_critic_verdict(slug, variant, verdict="approve")
    p = _probe(obs.run_probes(slug, variant)["probes"], "05.X1")
    assert p["status"] == "fail"


def test_05q2_low_score_approve_flags(tmp_topic):
    slug, variant = tmp_topic
    # critic 当前无 score 字段（set_critic_verdict 不存 score）；直接注入 critic 验探针逻辑。
    topic_io.update_topic(slug, variant, critic={"verdict": "approve", "score": 2})
    p = _probe(obs.run_probes(slug, variant)["probes"], "05.Q2")
    assert p["status"] == "fail"


def test_cc2_fake_pending_flags(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "已覆盖却 pending", "priority": "P1", "addresses": ["K1"],
         "covered_by": ["mat-x"]},
    ], variant=variant)
    p = _probe(obs.run_probes(slug, variant)["probes"], "CC2")
    assert p["status"] == "fail"


def test_01q1_public_unattempted_flags(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "public 没抓", "priority": "P1", "addresses": ["K1"],
         "info_tier": "public"},
    ], variant=variant)
    p = _probe(obs.run_probes(slug, variant)["probes"], "01.Q1")
    assert p["status"] == "fail"


def test_05q1_steelman_flag_when_reviewed(tmp_topic):
    slug, variant = tmp_topic
    topic_io.set_critic_verdict(slug, variant, verdict="approve")
    p = _probe(obs.run_probes(slug, variant)["probes"], "05.Q1")
    assert p["status"] == "flag"  # 纯判断，05 到了就挂复核旗（未到则 na）


def test_b5prime_rollup(tmp_topic):
    slug, variant = tmp_topic
    from prism.scripts.web_prescan import append_search_log
    # 真实签名: (slug, variant, query, n_results, n_high, n_mid, n_low, triggered_by, disposition=)
    append_search_log(slug, variant, query="q1", n_results=5, n_high=1,
                      n_mid=0, n_low=4, triggered_by="01-prescan")
    append_search_log(slug, variant, query="q2", n_results=3, n_high=0,
                      n_mid=0, n_low=3, triggered_by="01-prescan")
    topic_io.append_user_todos(slug, [
        {"task": "降级了", "priority": "P1", "addresses": ["K1"]},
    ], variant=variant)
    topic_io.mark_todo_fetch(slug, variant, "降级了", "empty", note="搜空")
    p = _probe(obs.run_probes(slug, variant)["probes"], "B5prime")
    assert p["status"] == "pass"          # 卷积探针始终 pass（信息面板）
    assert "搜" in p["detail"] and "降级" in p["detail"]


def test_02q2_red_gap_carried_forward_fails(tmp_topic):
    slug, variant = tmp_topic
    # 伪造 stage_history：02 进入红 K3，03 进入仍红 K3 → 硬升
    topic_io.update_topic(slug, variant, stage_history=[
        {"stage": "02-gather-materials", "entered_at": "t0", "exited_at": "t1",
         "gap_snapshot": {"uncovered_ks": ["K3"]}},
        {"stage": "03-extracting", "entered_at": "t1", "exited_at": None,
         "gap_snapshot": {"uncovered_ks": ["K3"]}},
    ])
    p = _probe(obs.run_probes(slug, variant)["probes"], "02.Q2")
    assert p["status"] == "fail"
    assert "K3" in p["detail"]


def test_02q2_red_gap_resolved_passes(tmp_topic):
    slug, variant = tmp_topic
    topic_io.update_topic(slug, variant, stage_history=[
        {"stage": "02-gather-materials", "entered_at": "t0", "exited_at": "t1",
         "gap_snapshot": {"uncovered_ks": ["K3"]}},
        {"stage": "03-extracting", "entered_at": "t1", "exited_at": None,
         "gap_snapshot": {"uncovered_ks": []}},
    ])
    p = _probe(obs.run_probes(slug, variant)["probes"], "02.Q2")
    assert p["status"] == "pass"


def _write_sidecar(slug, variant, tmproot, payload):
    import yaml
    d = tmproot / "topics" / slug / variant / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    (d / "07_decision_kit.yaml").write_text(
        yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")


def test_04q1_broken_chain_fails(tmp_topic):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_sidecar(slug, variant, t.PRISM_ROOT, {
        "slug": slug, "variant": variant, "topic_type": "company",
        "chain_links": {"rings_present": [1, 2, 3, 4, 6],   # 缺 5
                        "r4_anchors_r2": True, "r6_takes_r4_ev": True,
                        "r5_has_kill_signpost": False},
    })
    p = _probe(obs.run_probes(slug, variant)["probes"], "04.Q1")
    assert p["status"] == "fail"
    assert "5" in p["detail"]


def test_04q1_intact_chain_passes(tmp_topic):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_sidecar(slug, variant, t.PRISM_ROOT, {
        "chain_links": {"rings_present": [1, 2, 3, 4, 5, 6],
                        "r4_anchors_r2": True, "r6_takes_r4_ev": True,
                        "r5_has_kill_signpost": True},
    })
    p = _probe(obs.run_probes(slug, variant)["probes"], "04.Q1")
    assert p["status"] == "pass"


def test_04q3_honest_gaps_present_passes(tmp_topic):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_sidecar(slug, variant, t.PRISM_ROOT, {
        "chain_links": {"rings_present": [1, 2, 3, 4, 5, 6],
                        "r4_anchors_r2": True, "r6_takes_r4_ev": True,
                        "r5_has_kill_signpost": True},
        "honest_gaps": [{"ring": 5, "kind": "data-missing", "note": "无 Q2 业绩会"}],
    })
    p = _probe(obs.run_probes(slug, variant)["probes"], "04.Q3")
    assert p["status"] == "pass"


def test_04q3_no_honest_gaps_flags(tmp_topic):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_sidecar(slug, variant, t.PRISM_ROOT, {
        "chain_links": {"rings_present": [1, 2, 3, 4, 5, 6]},
    })
    p = _probe(obs.run_probes(slug, variant)["probes"], "04.Q3")
    assert p["status"] == "flag"


def test_03q3_no_findings_is_na(tmp_topic):
    slug, variant = tmp_topic
    p = _probe(obs.run_probes(slug, variant)["probes"], "03.Q3")
    assert p["status"] in ("na", "flag")


def _write_finding(slug, variant, tmproot, name, body):
    # findings 真实落在 outputs/findings_*.md（非 findings/ 目录）。
    d = tmproot / "topics" / slug / variant / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(body, encoding="utf-8")


def test_03q3_conflict_marker_passes(tmp_topic):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_finding(slug, variant, t.PRISM_ROOT, "findings_mat-aaa111.md",
                   "---\nsource_type: x\nquality: high\nconflicts_with: [f2]\n"
                   "conflict_note: 增速口径不一\n---\n正文")
    p = _probe(obs.run_probes(slug, variant)["probes"], "03.Q3")
    assert p["status"] == "pass"


def test_03q3_findings_no_marker_flags(tmp_topic):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_finding(slug, variant, t.PRISM_ROOT, "findings_mat-bbb222.md",
                   "---\nsource_type: x\nquality: high\n---\n正文")
    p = _probe(obs.run_probes(slug, variant)["probes"], "03.Q3")
    assert p["status"] == "flag"


# ───────────────────────── Task 8 探针补全 ─────────────────────────

def _write_decomposition(slug, variant, tmproot, version, body):
    p = tmproot / "topics" / slug / variant / f"decomposition_v{version}.md"
    p.write_text(body, encoding="utf-8")


def _write_case(slug, variant, tmproot, stem, body):
    d = tmproot / "topics" / slug / variant / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.md").write_text(body, encoding="utf-8")


# CC5 假覆盖（仅 @event 锚 todo）----
def test_cc5_bare_k_covered_is_na(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "裸覆盖", "priority": "P1", "addresses": ["K1"], "covered_by": ["mat-x"]},
    ], variant=variant)
    p = _probe(obs.run_probes(slug, variant)["probes"], "CC5")
    assert p["status"] == "na"  # 裸 K# 不进 CC5


def test_cc5_event_anchored_false_coverage_flags(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "事件锚假覆盖", "priority": "P0", "addresses": ["K1@Q2-earnings"],
         "covered_by": ["mat-nomatch"]},  # 覆盖料不在 manifest / 事件锚不匹配
    ], variant=variant)
    p = _probe(obs.run_probes(slug, variant)["probes"], "CC5")
    assert p["status"] == "flag"


# 00.Q1 prescan ----
def test_00q1_failed_prescan_fails(tmp_topic):
    slug, variant = tmp_topic
    topic_io.update_topic(slug, variant, thesis={
        "current_version": 1, "history": [{"version": 1, "prescan_status": "failed"}]})
    p = _probe(obs.run_probes(slug, variant)["probes"], "00.Q1")
    assert p["status"] == "fail"


def test_00q1_ok_prescan_passes(tmp_topic):
    slug, variant = tmp_topic
    topic_io.update_topic(slug, variant, thesis={
        "current_version": 1, "history": [{"version": 1, "prescan_status": "passed"}]})
    p = _probe(obs.run_probes(slug, variant)["probes"], "00.Q1")
    assert p["status"] == "pass"


# 00.Q2 / 00.Q4 / 00.X1 ----
def test_00q2_flags_with_decomposition(tmp_topic):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_decomposition(slug, variant, t.PRISM_ROOT, 0,
                         "# d\n## 一、命门\n- **命门1 ｜ x**（置信度：中）\n")
    p = _probe(obs.run_probes(slug, variant)["probes"], "00.Q2")
    assert p["status"] == "flag"


def test_00q2_na_without_decomposition(tmp_topic):
    slug, variant = tmp_topic
    p = _probe(obs.run_probes(slug, variant)["probes"], "00.Q2")
    assert p["status"] == "na"


def test_00q4_flags_when_meridian_present(tmp_topic):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_decomposition(slug, variant, t.PRISM_ROOT, 0,
                         "# d\n### 命门1 ｜ x（v0:中 → v1:高）\n")
    p = _probe(obs.run_probes(slug, variant)["probes"], "00.Q4")
    assert p["status"] == "flag"  # 自由表述代理 → 挂旗请人确认


def test_00x1_always_na(tmp_topic):
    slug, variant = tmp_topic
    p = _probe(obs.run_probes(slug, variant)["probes"], "00.X1")
    assert p["status"] == "na"  # 盲点显式化


# 01.Q2 / 01.Q3 / 01.X3 ----
def test_01q2_always_na(tmp_topic):
    slug, variant = tmp_topic
    p = _probe(obs.run_probes(slug, variant)["probes"], "01.Q2")
    assert p["status"] == "na"


def test_01q3_continuable_pending_fails(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "可抓却挂着", "priority": "P1", "addresses": ["K1"], "info_tier": "public"},
    ], variant=variant)  # fetch_status 默认 unattempted、非 empty/hard
    p = _probe(obs.run_probes(slug, variant)["probes"], "01.Q3")
    assert p["status"] == "fail"


def test_01q3_only_hard_pending_passes(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "硬料", "priority": "P1", "addresses": ["K1"], "info_tier": "hard"},
    ], variant=variant)
    p = _probe(obs.run_probes(slug, variant)["probes"], "01.Q3")
    assert p["status"] == "pass"


def test_01x3_company_empty_ticker_flags(tmp_topic):
    slug, variant = tmp_topic
    sc = topic_io.read_topic(slug, variant).get("scope") or {}
    sc["ticker"] = ""  # ticker 落在 scope.ticker
    topic_io.update_topic(slug, variant, scope=sc)
    p = _probe(obs.run_probes(slug, variant)["probes"], "01.X3")
    assert p["status"] == "flag"


def test_01x3_company_with_ticker_passes(tmp_topic):
    slug, variant = tmp_topic
    p = _probe(obs.run_probes(slug, variant)["probes"], "01.X3")
    assert p["status"] == "pass"  # fixture ticker=US_T


# 02.Q3 uncovered_ring 硬升 ----
def test_02q3_ring_carried_forward_fails(tmp_topic):
    slug, variant = tmp_topic
    topic_io.update_topic(slug, variant, stage_history=[
        {"stage": "02-gather-materials", "entered_at": "t0", "exited_at": "t1",
         "gap_snapshot": {"uncovered_ring_inputs": ["mgmt-capital-alloc"]}},
        {"stage": "03-extracting", "entered_at": "t1", "exited_at": None,
         "gap_snapshot": {"uncovered_ring_inputs": ["mgmt-capital-alloc"]}}])
    p = _probe(obs.run_probes(slug, variant)["probes"], "02.Q3")
    assert p["status"] == "fail"
    assert "mgmt-capital-alloc" in p["detail"]


def test_02q3_ring_resolved_passes(tmp_topic):
    slug, variant = tmp_topic
    topic_io.update_topic(slug, variant, stage_history=[
        {"stage": "02-gather-materials", "entered_at": "t0", "exited_at": "t1",
         "gap_snapshot": {"uncovered_ring_inputs": ["x"]}},
        {"stage": "03-extracting", "entered_at": "t1", "exited_at": None,
         "gap_snapshot": {"uncovered_ring_inputs": []}}])
    p = _probe(obs.run_probes(slug, variant)["probes"], "02.Q3")
    assert p["status"] == "pass"


# 03.Q1 findings 溯源/可信度 ----
def test_03q1_source_confidence_passes(tmp_topic):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_finding(slug, variant, t.PRISM_ROOT, "findings_mat-ccc333.md",
                   "---\nsource_type: web\nquality: high\n---\n正文")
    p = _probe(obs.run_probes(slug, variant)["probes"], "03.Q1")
    assert p["status"] == "pass"


def test_03q1_missing_confidence_fails(tmp_topic):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_finding(slug, variant, t.PRISM_ROOT, "findings_mat-ddd444.md",
                   "---\nsource_type: web\n---\n正文")  # 无 quality/confidence
    p = _probe(obs.run_probes(slug, variant)["probes"], "03.Q1")
    assert p["status"] == "fail"


# 04.Q2 ④delta 锚回 ② ----
def test_04q2_aligned_metric_flags(tmp_topic):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_sidecar(slug, variant, t.PRISM_ROOT, {
        "market_implied": {"metric": "rev_cagr", "value": 0.18},
        "my_vs_market_delta": {"metric": "rev_cagr", "delta": "+7pct"}})
    p = _probe(obs.run_probes(slug, variant)["probes"], "04.Q2")
    assert p["status"] == "flag"  # 对齐也只挂旗（② 代理）


def test_04q2_mismatched_metric_fails(tmp_topic):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_sidecar(slug, variant, t.PRISM_ROOT, {
        "market_implied": {"metric": "rev_cagr"},
        "my_vs_market_delta": {"metric": "margin"}})
    p = _probe(obs.run_probes(slug, variant)["probes"], "04.Q2")
    assert p["status"] == "fail"


def test_04q2_na_without_b4(tmp_topic):
    slug, variant = tmp_topic
    p = _probe(obs.run_probes(slug, variant)["probes"], "04.Q2")
    assert p["status"] == "na"


# 04.X1 硬合成 ----
def test_04x1_red_gap_and_placeholder_fails(tmp_topic, monkeypatch):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_case(slug, variant, t.PRISM_ROOT, "c_investment_case", "正文 未充分论证 占位")
    monkeypatch.setattr(obs, "detect_gaps", lambda s, v: {"uncovered_ks": ["K3"]})
    p = _probe(obs.run_probes(slug, variant)["probes"], "04.X1")
    assert p["status"] == "fail"


def test_04x1_placeholder_but_gap_green_passes(tmp_topic, monkeypatch):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_case(slug, variant, t.PRISM_ROOT, "c_investment_case", "正文 未充分论证")
    monkeypatch.setattr(obs, "detect_gaps", lambda s, v: {"uncovered_ks": []})
    p = _probe(obs.run_probes(slug, variant)["probes"], "04.X1")
    assert p["status"] == "pass"  # 有占位但 gap 不红


def test_04x1_na_without_case(tmp_topic):
    slug, variant = tmp_topic
    p = _probe(obs.run_probes(slug, variant)["probes"], "04.X1")
    assert p["status"] == "na"


def test_04x2_always_na(tmp_topic):
    slug, variant = tmp_topic
    p = _probe(obs.run_probes(slug, variant)["probes"], "04.X2")
    assert p["status"] == "na"  # 盲点显式化


# 05.Q3 request-more todo ----
def test_05q3_na_when_not_request_more(tmp_topic):
    slug, variant = tmp_topic
    topic_io.set_critic_verdict(slug, variant, verdict="approve")
    p = _probe(obs.run_probes(slug, variant)["probes"], "05.Q3")
    assert p["status"] == "na"


def test_05q3_request_more_missing_addresses_fails(tmp_topic):
    slug, variant = tmp_topic
    topic_io.update_topic(slug, variant, critic={"verdict": "request-more"})
    topic_io.append_user_todos(slug, [
        {"task": "缺addr补料", "priority": "P0"},  # 无 addresses
    ], variant=variant)
    p = _probe(obs.run_probes(slug, variant)["probes"], "05.Q3")
    assert p["status"] == "fail"


# 06.Q1 巡检 ----
def test_06q1_na_without_monitor_queue(tmp_topic):
    slug, variant = tmp_topic
    p = _probe(obs.run_probes(slug, variant)["probes"], "06.Q1")
    assert p["status"] == "na"


def test_06q1_flags_with_monitor_entry(tmp_topic):
    slug, variant = tmp_topic
    import yaml
    import prism.scripts.topic as t
    (t.PRISM_ROOT / "monitor_queue.yaml").write_text(
        yaml.safe_dump({"pending": [{"slug": slug, "kind": "signpost"}]}, allow_unicode=True),
        encoding="utf-8")
    p = _probe(obs.run_probes(slug, variant)["probes"], "06.Q1")
    assert p["status"] == "flag"

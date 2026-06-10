"""评估快照（regime_eval_log.yaml）零-LLM CRUD + diff + 重估简报 的测试。"""
import pytest

from prism.scripts import eval_snapshot as es
from prism.scripts import macro_registry as reg


@pytest.fixture
def tmp_topic(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(es, "_PRISM_ROOT", tmp_path)
    slug, variant = "m", "v"
    reg.create_registry(slug, variant)
    reg.upsert_input(slug, variant, {
        "name": "A", "tier": "A", "cadence_type": "event", "mechanism": "CD",
        "causal_sentence": "x", "importance": "load_bearing"})
    reg.upsert_input(slug, variant, {"name": "B", "cadence_type": "series", "importance": "background"})
    return slug, variant


def _ev_all(extra_conclusions=None):
    """列全 A、B 两条输入的最小 evaluation（满足"必须列全"不变量）。"""
    return {
        "input_snapshot": [
            {"name": "A", "value": 3.0, "as_of": "2026-05-01", "used": True},
            {"name": "B", "value": None, "as_of": None, "used": False},
        ],
        "conclusions": extra_conclusions if extra_conclusions is not None else [
            {"id": "rates", "label": "利率", "state": "紧",
             "based_on": [{"input": "A", "role": "load_bearing", "expected": "up_or_flat"}],
             "causal": "A→紧"}],
    }


def test_read_eval_log_missing_returns_skeleton(tmp_topic):
    slug, variant = tmp_topic
    log = es.read_eval_log(slug, variant)
    assert log["evaluations"] == []
    assert log["reeval_pending"] is None


def test_append_evaluation_writes_and_increments(tmp_topic):
    slug, variant = tmp_topic
    assert es.append_evaluation(slug, variant, _ev_all()) == 1
    assert es.append_evaluation(slug, variant, _ev_all()) == 2
    latest = es.latest_evaluation(slug, variant)
    assert latest["version"] == 2
    assert latest["conclusions"][0]["id"] == "rates"


def test_append_rejects_missing_input(tmp_topic):
    slug, variant = tmp_topic
    ev = {"input_snapshot": [{"name": "A", "value": 1, "used": True}], "conclusions": []}
    with pytest.raises(ValueError, match="漏列"):
        es.append_evaluation(slug, variant, ev)


def test_append_rejects_dangling_based_on(tmp_topic):
    slug, variant = tmp_topic
    ev = _ev_all([{"id": "x", "based_on": [{"input": "ZZZ", "role": "load_bearing"}]}])
    with pytest.raises(ValueError, match="悬空"):
        es.append_evaluation(slug, variant, ev)


def test_append_rejects_bad_role(tmp_topic):
    slug, variant = tmp_topic
    ev = _ev_all([{"id": "x", "based_on": [{"input": "A", "role": "bogus"}]}])
    with pytest.raises(ValueError, match="role"):
        es.append_evaluation(slug, variant, ev)


def test_append_rejects_snapshot_row_missing_name(tmp_topic):
    """快照行漏 name 键 → 拒绝（否则 None 混入名册，会让悬空检查失灵）。"""
    slug, variant = tmp_topic
    ev = _ev_all()
    ev["input_snapshot"].append({"value": 1, "used": False})   # 漏 name 键
    with pytest.raises(ValueError, match="缺 name"):
        es.append_evaluation(slug, variant, ev)


def test_append_rejects_based_on_missing_input_even_with_nameless_row(tmp_topic):
    """漏 input 键的 based_on 不能因为存在漏 name 的快照行而蒙混过关（None==None 漏洞）。"""
    slug, variant = tmp_topic
    ev = _ev_all([{"id": "x", "label": "l", "state": "s", "causal": "c",
                   "based_on": [{"role": "load_bearing"}]}])   # 漏 input 键
    with pytest.raises(ValueError, match="缺 input"):
        es.append_evaluation(slug, variant, ev)


def test_conclusions_for_input_reverse_index(tmp_topic):
    slug, variant = tmp_topic
    es.append_evaluation(slug, variant, _ev_all())
    latest = es.latest_evaluation(slug, variant)
    assert es.conclusions_for_input(latest, "A") == ["rates"]
    assert es.conclusions_for_input(latest, "B") == []


def test_diff_no_snapshot_is_first(tmp_topic):
    slug, variant = tmp_topic
    diff = es.diff_since_last(slug, variant)
    assert {d["name"] for d in diff} == {"A", "B"}
    assert all(d["changed"] is None for d in diff)


def test_diff_detects_numeric_change_and_conclusions(tmp_topic):
    slug, variant = tmp_topic
    es.append_evaluation(slug, variant, _ev_all())
    reg.record_observation(slug, variant, "A", value=3.5)
    diff = {d["name"]: d for d in es.diff_since_last(slug, variant)}
    assert diff["A"]["changed"] is True
    assert diff["A"]["delta"] == pytest.approx(0.5)
    assert diff["A"]["snapshot_value"] == 3.0
    assert diff["A"]["live_value"] == 3.5
    assert diff["A"]["conclusions"] == ["rates"]
    assert diff["A"]["used"] is True
    assert diff["B"]["changed"] is False        # 两端都 None → 未变
    assert diff["B"]["used"] is False


def test_assemble_brief_lists_changed_unfetched_affected(tmp_topic):
    slug, variant = tmp_topic
    es.append_evaluation(slug, variant, _ev_all())
    reg.record_observation(slug, variant, "A", value=4.0)   # A 变了，支撑 rates
    brief = es.assemble_reeval_brief(slug, variant)
    assert "A" in [c["name"] for c in brief["changed"]]
    assert "B" in brief["unfetched"]                        # B 从未抓到值
    assert "rates" in brief["affected_conclusions"]
    assert set(brief) == {"changed", "breached", "due", "alert", "unfetched",
                          "affected_conclusions", "affected_conclusion_labels"}


def test_stamp_and_clear_reeval_pending(tmp_topic):
    slug, variant = tmp_topic
    es.append_evaluation(slug, variant, _ev_all())
    es.stamp_reeval_pending(slug, variant, {"changed": [], "affected_conclusions": []})
    assert es.read_eval_log(slug, variant)["reeval_pending"] is not None
    es.append_evaluation(slug, variant, _ev_all())          # 新评估落地清戳
    assert es.read_eval_log(slug, variant)["reeval_pending"] is None


def test_snapshot_inputs_lists_all_registry_inputs(tmp_topic):
    slug, variant = tmp_topic
    reg.record_observation(slug, variant, "A", value=3.0, as_of="2026-05-01")
    by = {s["name"]: s for s in es.snapshot_inputs(slug, variant)}
    assert set(by) == {"A", "B"}
    assert by["A"]["value"] == 3.0
    assert by["A"]["as_of"] == "2026-05-01"
    assert by["A"]["used"] is False          # 默认未用，调用方/record_evaluation 据 based_on 标
    assert by["B"]["value"] is None


def test_snapshot_inputs_policy_carries_stance(tmp_topic):
    slug, variant = tmp_topic
    reg.upsert_input(slug, variant, {
        "name": "C", "tier": "B", "cadence_type": "policy", "mechanism": "CO",
        "importance": "confirming", "stance_scale": "hawk_dove",
        "observed": {"stance": "偏鹰", "evidence": "x"}})
    by = {s["name"]: s for s in es.snapshot_inputs(slug, variant)}
    assert by["C"]["stance"] == "偏鹰"


def test_record_evaluation_builds_snapshot_and_clears_pending(tmp_topic):
    slug, variant = tmp_topic
    reg.record_observation(slug, variant, "A", value=3.0, as_of="2026-05-01")
    es.stamp_reeval_pending(slug, variant, {"changed": [], "affected_conclusions": []})
    conclusions = [{"id": "rates", "label": "利率体制", "state": "紧",
                    "based_on": [{"input": "A", "role": "load_bearing", "expected": "up_or_flat"}],
                    "causal": "A→紧"}]
    assert es.record_evaluation(slug, variant, conclusions, note="重估") == 1
    log = es.read_eval_log(slug, variant)
    assert log["reeval_pending"] is None                  # 闭环自动清戳
    latest = es.latest_evaluation(slug, variant)
    snap = {s["name"]: s for s in latest["input_snapshot"]}
    assert set(snap) == {"A", "B"}                        # input_snapshot 列全
    assert snap["A"]["used"] is True                      # based_on 命中 → used
    assert snap["B"]["used"] is False
    assert latest["conclusions"][0]["id"] == "rates"
    assert latest.get("note") == "重估"


def test_conclusion_labels_maps_id_to_label(tmp_topic):
    slug, variant = tmp_topic
    assert es.conclusion_labels(slug, variant) == {}      # 无评估 → 空
    es.append_evaluation(slug, variant, _ev_all())
    assert es.conclusion_labels(slug, variant) == {"rates": "利率"}


def test_brief_includes_chinese_labels(tmp_topic):
    slug, variant = tmp_topic
    es.append_evaluation(slug, variant, _ev_all())
    reg.record_observation(slug, variant, "A", value=4.0)
    brief = es.assemble_reeval_brief(slug, variant)
    assert brief["affected_conclusions"] == ["rates"]
    assert brief["affected_conclusion_labels"] == ["利率"]    # id→中文 label


def test_diff_policy_stance_direction(tmp_topic):
    slug, variant = tmp_topic
    reg.upsert_input(slug, variant, {
        "name": "C", "tier": "B", "cadence_type": "policy", "mechanism": "CO",
        "importance": "confirming", "stance_scale": "hawk_dove",
        "observed": {"stance": "偏鹰", "evidence": "x"}})
    ev = _ev_all()
    ev["input_snapshot"].append(                       # 上次 C 为 中性
        {"name": "C", "stance": "中性", "as_of": "2026-05-01", "used": True})
    es.append_evaluation(slug, variant, ev)
    diff = {d["name"]: d for d in es.diff_since_last(slug, variant)}
    assert diff["C"]["changed"] is True
    assert diff["C"]["snapshot_stance"] == "中性"
    assert diff["C"]["stance"] == "偏鹰"
    assert diff["C"]["direction"] == "更鹰"
    assert diff["C"]["delta"] is None                  # policy 不算数值 delta
    assert diff["C"]["breached"] is False              # policy 无报警带
    assert diff["A"]["stance"] is None                 # 数值输入立场字段为 None
    assert diff["A"]["direction"] is None


def test_load_bearing_numeric_edge_requires_expected(tmp_topic):
    """承重边且该输入有数值 → 缺 expected 报错。"""
    slug, variant = tmp_topic
    ev = _ev_all([{"id": "rates", "label": "利率", "state": "紧", "causal": "c",
                   "based_on": [{"input": "A", "role": "load_bearing"}]}])  # A 有数值、缺 expected
    with pytest.raises(ValueError, match="expected"):
        es.append_evaluation(slug, variant, ev)


def test_expected_illegal_direction_word_rejected(tmp_topic):
    slug, variant = tmp_topic
    ev = _ev_all([{"id": "rates", "label": "利率", "state": "紧", "causal": "c",
                   "based_on": [{"input": "A", "role": "load_bearing", "expected": "sideways"}]}])
    with pytest.raises(ValueError, match="方向词"):
        es.append_evaluation(slug, variant, ev)


def test_load_bearing_nonnumeric_edge_expected_optional(tmp_topic):
    """承重边但该输入无数值无立场（B 是 None）→ expected 可空，不报错。"""
    slug, variant = tmp_topic
    ev = _ev_all([{"id": "x", "label": "x", "state": "s", "causal": "c",
                   "based_on": [{"input": "B", "role": "load_bearing"}]}])  # B value=None
    assert es.append_evaluation(slug, variant, ev) == 1


def test_confirming_edge_expected_optional(tmp_topic):
    """confirming 边永不强制 expected。"""
    slug, variant = tmp_topic
    ev = _ev_all([{"id": "x", "label": "x", "state": "s", "causal": "c",
                   "based_on": [{"input": "A", "role": "confirming"}]}])
    assert es.append_evaluation(slug, variant, ev) == 1


def test_stance_load_bearing_edge_requires_expected(tmp_topic):
    """承重边且该输入有 stance → 缺 expected 报错。"""
    slug, variant = tmp_topic
    ev = {
        "input_snapshot": [
            {"name": "A", "value": 3.0, "as_of": "2026-05-01", "used": False},
            {"name": "B", "value": None, "used": False},
            {"name": "C", "stance": "偏鹰", "as_of": "2026-05-01", "used": True},
        ],
        "conclusions": [{"id": "p", "label": "政策", "state": "鹰", "causal": "c",
                         "based_on": [{"input": "C", "role": "load_bearing"}]}],  # 缺 expected
    }
    reg.upsert_input(slug, variant, {
        "name": "C", "tier": "B", "cadence_type": "policy", "mechanism": "CO",
        "importance": "load_bearing", "stance_scale": "hawk_dove",
        "observed": {"stance": "偏鹰", "evidence": "x"}})
    with pytest.raises(ValueError, match="expected"):
        es.append_evaluation(slug, variant, ev)


def test_prior_verdict_written_on_new_entry_not_old(tmp_topic):
    """prior_verdict 落新条目，不改旧条目（append-only 不可变）。"""
    slug, variant = tmp_topic
    es.append_evaluation(slug, variant, _ev_all())                       # v1：无 verdict
    conclusions = [{"id": "rates", "label": "利率", "state": "紧", "causal": "c",
                    "based_on": [{"input": "A", "role": "load_bearing", "expected": "up_or_flat"}]}]
    v2 = es.record_evaluation(slug, variant, conclusions,
                              prior_verdict=[{"conclusion_id": "rates", "verdict": "held",
                                              "note": "利率确按预测维持"}])
    assert v2 == 2
    evals = es.read_eval_log(slug, variant)["evaluations"]
    assert "prior_verdict" not in evals[0]                               # 旧条目没动
    assert evals[1]["prior_verdict"][0]["verdict"] == "held"             # 新条目带裁定


def test_prior_verdict_illegal_value_rejected(tmp_topic):
    slug, variant = tmp_topic
    conclusions = [{"id": "rates", "label": "利率", "state": "紧", "causal": "c",
                    "based_on": [{"input": "A", "role": "load_bearing", "expected": "up_or_flat"}]}]
    with pytest.raises(ValueError, match="verdict"):
        es.record_evaluation(slug, variant, conclusions,
                             prior_verdict=[{"conclusion_id": "rates", "verdict": "bogus"}])

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
             "based_on": [{"input": "A", "role": "load_bearing"}], "causal": "A→紧"}],
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

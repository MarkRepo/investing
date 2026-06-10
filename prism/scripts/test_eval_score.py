"""战绩派生（eval_score）零-LLM 测试：score_edge 三态 + score_evaluation + edge_ledger。"""
import pytest

from prism.scripts import eval_score as sc
from prism.scripts import eval_snapshot as es
from prism.scripts import macro_registry as reg


def test_score_edge_numeric_up_hit_and_miss():
    assert sc.score_edge("up", 3.0, 3.5) == "hit"
    assert sc.score_edge("up", 3.0, 2.5) == "miss"
    assert sc.score_edge("down", 3.0, 2.5) == "hit"


def test_score_edge_flat_uses_tolerance():
    assert sc.score_edge("flat", 3.0, 3.05, tol=0.1) == "hit"     # 容差内
    assert sc.score_edge("flat", 3.0, 3.5, tol=0.1) == "miss"     # 越界


def test_score_edge_up_or_flat():
    assert sc.score_edge("up_or_flat", 3.0, 3.0) == "hit"
    assert sc.score_edge("up_or_flat", 3.0, 3.5) == "hit"
    assert sc.score_edge("up_or_flat", 3.0, 2.5) == "miss"


def test_score_edge_missing_baseline_is_neutral():
    assert sc.score_edge("up", None, 3.5) == "neutral"
    assert sc.score_edge("up", 3.0, None) == "neutral"
    assert sc.score_edge(None, 3.0, 3.5) == "neutral"


def test_score_edge_stance_axis():
    # hawk_dove: 中性 → 偏鹰 = "更鹰"
    assert sc.score_edge("更鹰", "中性", "偏鹰", scale="hawk_dove") == "hit"
    assert sc.score_edge("更鹰", "中性", "偏鸽", scale="hawk_dove") == "miss"
    assert sc.score_edge("更鹰", "中性", "中性", scale="hawk_dove") == "neutral"  # 无移动→保守


@pytest.fixture
def tmp_macro(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(es, "_PRISM_ROOT", tmp_path)
    slug, variant = "m", "v"
    reg.create_registry(slug, variant)
    reg.upsert_input(slug, variant, {
        "name": "A", "tier": "A", "cadence_type": "series", "mechanism": "CD",
        "causal_sentence": "x", "importance": "load_bearing"})
    return slug, variant


def test_score_evaluation_counts_hits(tmp_macro):
    slug, variant = tmp_macro
    reg.record_observation(slug, variant, "A", value=3.0, as_of="2026-01-01")
    es.record_evaluation(slug, variant, [
        {"id": "rates", "label": "利率", "state": "升", "causal": "c",
         "based_on": [{"input": "A", "role": "load_bearing", "expected": "up"}]}],
        note="v1")
    reg.record_observation(slug, variant, "A", value=3.6)        # 实际走高 → 命中 up
    out = sc.score_evaluation(slug, variant)
    assert out["scored"] is True
    assert out["version"] == 1
    assert out["hits"] == 1 and out["misses"] == 0
    assert out["conclusions"][0]["hit_rate"] == 1.0
    assert out["conclusions"][0]["edges"][0]["verdict"] == "hit"
    assert isinstance(out["days"], int) and out["days"] >= 0


def test_score_evaluation_no_eval_returns_unscored(tmp_macro):
    slug, variant = tmp_macro
    out = sc.score_evaluation(slug, variant)
    assert out["scored"] is False and out["conclusions"] == []


def test_score_evaluation_unfetched_edge_is_neutral(tmp_macro):
    slug, variant = tmp_macro
    es.record_evaluation(slug, variant, [
        {"id": "rates", "label": "利率", "state": "升", "causal": "c",
         "based_on": [{"input": "A", "role": "load_bearing"}]}],  # A 无 observed 值→快照/现值 None
        note="v1")
    out = sc.score_evaluation(slug, variant)
    assert out["conclusions"][0]["edges"][0]["verdict"] == "neutral"
    assert out["hit_rate"] is None                                # 无命中也无失手

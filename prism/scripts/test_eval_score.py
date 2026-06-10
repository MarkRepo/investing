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

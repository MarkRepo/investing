"""macro type 接入回归：schema / 默认产出集 / case+sidecar 映射 / 排除 tier 漏斗 / 默认 stage flow。"""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts.topic import (
    create_topic,
    read_topic,
    next_stage,
    suggest_relatives,
    _outputs_for_type,
    _CASE_BY_TYPE,
    _SIDECAR_BY_TYPE,
    _TYPE_TIER,
)


@pytest.fixture
def tmp_topics(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    (tmpdir / "topics").mkdir()
    yield tmpdir
    shutil.rmtree(tmpdir)


def test_macro_creates_without_ticker(tmp_topics):
    create_topic(
        slug="global-macro-rates-liquidity", display_name="宏观层",
        topic_type="macro", question="利率/流动性/汇率体制趋势",
        geo="GLOBAL", depth="deep", variant="opus4.8",
        search_terms=["利率", "流动性", "汇率"],
    )
    data = read_topic("global-macro-rates-liquidity", "opus4.8")
    assert data["type"] == "macro"
    assert "ticker" not in data["scope"]


def test_macro_canonical_outputs(tmp_topics):
    assert _outputs_for_type("macro") == ["00_primer", "m_regime_read"]


def test_macro_case_and_sidecar_mapping():
    assert _CASE_BY_TYPE["macro"] == "m_regime_read"
    assert _SIDECAR_BY_TYPE["macro"] == "transmission_map.yaml"


def test_macro_not_in_tier_hierarchy():
    assert "macro" not in _TYPE_TIER


def test_macro_uses_default_stage_flow():
    assert next_stage("macro", "00-init") == "01-roadmap"
    assert next_stage("macro", "04-post-synthesis") == "05-critic-review"
    assert next_stage("macro", "05-critic-review") == "done"


def test_macro_never_suggested_as_relative(tmp_topics):
    create_topic(
        slug="global-macro-rates-liquidity", display_name="宏观层",
        topic_type="macro", question="Q", geo="GLOBAL", depth="deep",
        variant="v", search_terms=["利率"],
    )
    create_topic(
        slug="cn-test-co", display_name="X", topic_type="company",
        question="Q", geo="CN", depth="deep", variant="v",
        short_name="X", ticker="SSE_600519",
    )
    res = suggest_relatives("cn-test-co", "v")
    slugs = [c["slug"] for c in res["parent_candidates"] + res["child_candidates"]]
    assert "global-macro-rates-liquidity" not in slugs

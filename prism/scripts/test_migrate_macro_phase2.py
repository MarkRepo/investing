import copy
import pytest
from prism.scripts import macro_registry as reg
from prism.scripts import migrate_macro_phase2 as mig

SLUG, VAR = "global-macro-rates-liquidity", "opus4.8"


@pytest.fixture
def live_registry():
    """真登记表的内存副本，避免落盘污染。"""
    return copy.deepcopy(reg.read_registry(SLUG, VAR))


def test_add_fred_series_ids_covers_all_fred_inputs(live_registry):
    out = mig.add_fred_series_ids(live_registry)
    fred_inputs = [e for e in out["inputs"] if e.get("fetch_method") == "fred-api"]
    # 迁移后：每条 fred-api 输入都有非空 fred_series_id
    missing = [e["name"] for e in fred_inputs if not e.get("fred_series_id")]
    assert missing == [], f"未映射: {missing}"


def test_gold_reclassified_to_web(live_registry):
    out = mig.add_fred_series_ids(live_registry)
    gold = next(e for e in out["inputs"] if e["name"] == "黄金")
    assert gold["fetch_method"] == "llm-web"


def test_net_liquidity_marked_derived(live_registry):
    out = mig.add_fred_series_ids(live_registry)
    nl = next(e for e in out["inputs"] if e["name"] == "净流动性(=资产−TGA−RRP)")
    assert nl["fred_series_id"] == "__DERIVED__"

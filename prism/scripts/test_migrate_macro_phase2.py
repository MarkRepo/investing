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


# ── Task 5：6 条报警带 ──

EXPECTED_BANDS = {
    "HY OAS": {"level": 450, "direction": "above", "level_alarm": 550},
    "MOVE 债市波动率": {"level": 120, "direction": "above", "level_alarm": 140},
    "跨币种基差(EUR/JPY-USD)": {"level": -40, "direction": "below", "level_alarm": -60},
    "USDJPY / 日元 carry": {"delta": 3.0, "level": 158, "direction": "above", "level_alarm": 160},
    "DR007/R007": {"level": 2.2, "direction": "above", "level_alarm": 2.5, "min_streak": 2},
    "CNH-CNY 价差": {"level": 0.015, "direction": "abs_above", "level_alarm": 0.030},
}


def test_set_alert_bands_exact(live_registry):
    out = mig.set_alert_bands(live_registry)
    by = {e["name"]: e for e in out["inputs"]}
    for name, band in EXPECTED_BANDS.items():
        assert by[name]["alert_band"] == band, name


def test_only_six_alert_series_have_bands_changed(live_registry):
    out = mig.set_alert_bands(live_registry)
    changed = {e["name"] for e in out["inputs"] if e.get("name") in EXPECTED_BANDS}
    assert changed == set(EXPECTED_BANDS)

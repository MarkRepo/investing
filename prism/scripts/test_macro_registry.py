"""macro 输入登记表（macro_inputs.yaml）CRUD + 机制纪律 validator。零 LLM。"""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts import macro_registry as mr

SLUG = "global-macro-rates-liquidity"
VARIANT = "opus4.8"


@pytest.fixture
def reg_env(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.macro_registry._PRISM_ROOT", tmpdir)
    (tmpdir / "topics" / SLUG / VARIANT).mkdir(parents=True)
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_create_and_read_roundtrip(reg_env):
    path = mr.create_registry(SLUG, VARIANT)
    assert path.exists()
    data = mr.read_registry(SLUG, VARIANT)
    assert data["slug"] == SLUG
    assert data["variant"] == VARIANT
    assert data["inputs"] == []


def _good_A_entry():
    return {
        "name": "非农就业 NFP", "tier": "A", "cadence_type": "event",
        "targets": ["rates", "fx"], "mechanism": "CD",
        "causal_sentence": "就业超预期 → Fed 维持限制性政策更久 → 短端利率↑",
        "lag": "同步", "importance": "load_bearing",
        "source": "FRED", "fetch_method": "fred-api", "availability": "scripted", "state": "改",
        "alert_series": False,
    }


def test_upsert_input_adds_and_is_idempotent(reg_env):
    mr.create_registry(SLUG, VARIANT)
    mr.upsert_input(SLUG, VARIANT, _good_A_entry())
    data = mr.read_registry(SLUG, VARIANT)
    assert [i["name"] for i in data["inputs"]] == ["非农就业 NFP"]
    # 同名再 upsert → 覆盖字段，不新增一行
    e = _good_A_entry()
    e["importance"] = "confirming"
    mr.upsert_input(SLUG, VARIANT, e)
    data = mr.read_registry(SLUG, VARIANT)
    assert len(data["inputs"]) == 1
    assert data["inputs"][0]["importance"] == "confirming"


def test_validator_passes_clean_registry(reg_env):
    mr.create_registry(SLUG, VARIANT)
    mr.upsert_input(SLUG, VARIANT, _good_A_entry())
    errors = mr.validate_registry(SLUG, VARIANT)
    assert errors == []


def test_tier_A_requires_causal_mechanism(reg_env):
    mr.create_registry(SLUG, VARIANT)
    bad = _good_A_entry()
    bad["mechanism"] = "CO"          # tier A 不允许 CO
    mr.upsert_input(SLUG, VARIANT, bad)
    errors = mr.validate_registry(SLUG, VARIANT)
    assert any("tier A" in e and "CD/CF" in e for e in errors)


def test_causal_mechanism_requires_sentence(reg_env):
    mr.create_registry(SLUG, VARIANT)
    bad = _good_A_entry()
    bad["causal_sentence"] = ""       # CD 必须有因果句
    mr.upsert_input(SLUG, VARIANT, bad)
    errors = mr.validate_registry(SLUG, VARIANT)
    assert any("causal_sentence" in e for e in errors)


def test_alert_series_only_on_series(reg_env):
    mr.create_registry(SLUG, VARIANT)
    bad = _good_A_entry()             # cadence_type=event 不能 alert_series
    bad["alert_series"] = True
    mr.upsert_input(SLUG, VARIANT, bad)
    errors = mr.validate_registry(SLUG, VARIANT)
    assert any("alert_series" in e and "series" in e for e in errors)


def test_enum_validation(reg_env):
    mr.create_registry(SLUG, VARIANT)
    bad = _good_A_entry()
    bad["tier"] = "Z"
    mr.upsert_input(SLUG, VARIANT, bad)
    errors = mr.validate_registry(SLUG, VARIANT)
    assert any("tier" in e for e in errors)


def test_validator_flags_duplicate_name(reg_env):
    mr.create_registry(SLUG, VARIANT)
    mr.upsert_input(SLUG, VARIANT, _good_A_entry())
    # 直接改盘构造重复 name（upsert 会去重，故绕过它）
    data = mr.read_registry(SLUG, VARIANT)
    data["inputs"].append(dict(data["inputs"][0]))
    mr._write_yaml(mr._registry_path(SLUG, VARIANT), data)
    errors = mr.validate_registry(SLUG, VARIANT)
    assert any("重复" in e for e in errors)


def test_record_observation_rolls_prev_value(reg_env):
    mr.create_registry(SLUG, VARIANT)
    mr.upsert_input(SLUG, VARIANT, _good_A_entry())
    mr.record_observation(SLUG, VARIANT, "非农就业 NFP", value=150.0, as_of="2026-05-02")
    mr.record_observation(SLUG, VARIANT, "非农就业 NFP", value=90.0, as_of="2026-06-06")
    obs = {i["name"]: i["observed"] for i in mr.read_registry(SLUG, VARIANT)["inputs"]}["非农就业 NFP"]
    assert obs["value"] == 90.0
    assert obs["prev_value"] == 150.0
    assert obs["as_of"] == "2026-06-06"


def test_record_observation_unknown_name_raises(reg_env):
    mr.create_registry(SLUG, VARIANT)
    with pytest.raises(ValueError):
        mr.record_observation(SLUG, VARIANT, "不存在", value=1.0, as_of="2026-06-06")


from datetime import date


def test_scan_macro_inputs_buckets():
    reg = {"inputs": [
        # event 到期（next_due 已过）
        {"name": "NFP", "cadence_type": "event", "tier": "A", "importance": "load_bearing",
         "monitoring": {"enabled": True}, "observed": {"next_due": "2026-06-01"}},
        # event 未到期
        {"name": "零售", "cadence_type": "event", "monitoring": {"enabled": True},
         "observed": {"next_due": "2026-12-31"}},
        # policy 到期
        {"name": "FOMC声明", "cadence_type": "policy", "tier": "A", "importance": "load_bearing",
         "monitoring": {"enabled": True}, "observed": {"next_due": "2026-06-05"}},
        # series alert_series 越 delta 带
        {"name": "HY OAS", "cadence_type": "series", "alert_series": True, "tier": "B",
         "importance": "load_bearing", "monitoring": {"enabled": True},
         "alert_band": {"delta": 75.0}, "observed": {"value": 400.0, "prev_value": 300.0}},
        # series alert_series 未越带
        {"name": "MOVE", "cadence_type": "series", "alert_series": True,
         "monitoring": {"enabled": True}, "alert_band": {"z": 2.0},
         "observed": {"z": 1.0}},
        # series 非 alert（即便大动也不进桶）
        {"name": "比特币", "cadence_type": "series", "alert_series": False,
         "monitoring": {"enabled": True}, "observed": {"value": 100.0, "prev_value": 10.0}},
        # 日期坏 → unparseable
        {"name": "坏日期", "cadence_type": "event", "monitoring": {"enabled": True},
         "observed": {"next_due": "soon"}},
        # monitoring 关 → 跳过
        {"name": "关掉的", "cadence_type": "event", "monitoring": {"enabled": False},
         "observed": {"next_due": "2026-06-01"}},
    ]}
    out = mr.scan_macro_inputs(reg, today=date(2026, 6, 7))
    assert {x["name"] for x in out["due_event"]} == {"NFP"}
    assert {x["name"] for x in out["due_policy"]} == {"FOMC声明"}
    assert {x["name"] for x in out["alert_series"]} == {"HY OAS"}
    assert {u["name"] for u in out["unparseable"]} == {"坏日期"}


# ── 报警带 schema 扩展（第二期 Task 4）：level/direction/min_streak ──

def _entry(band, observed):
    return {"name": "x", "alert_band": band, "observed": observed}


def test_breach_level_above():
    e = _entry({"level": 450, "direction": "above"}, {"value": 460})
    assert mr._series_breached(e) is True
    e2 = _entry({"level": 450, "direction": "above"}, {"value": 440})
    assert mr._series_breached(e2) is False


def test_breach_level_below():
    e = _entry({"level": -40, "direction": "below"}, {"value": -55})
    assert mr._series_breached(e) is True
    e2 = _entry({"level": -40, "direction": "below"}, {"value": -30})
    assert mr._series_breached(e2) is False


def test_breach_abs_above():
    e = _entry({"level": 0.015, "direction": "abs_above"}, {"value": -0.02})
    assert mr._series_breached(e) is True
    e2 = _entry({"level": 0.015, "direction": "abs_above"}, {"value": 0.01})
    assert mr._series_breached(e2) is False


def test_breach_min_streak_requires_consecutive():
    # 当前读数越带，但 streak=1 < min_streak=2 → 不报警
    e = _entry({"level": 2.2, "direction": "above", "min_streak": 2}, {"value": 2.3, "streak": 1})
    assert mr._series_breached(e) is False
    e2 = _entry({"level": 2.2, "direction": "above", "min_streak": 2}, {"value": 2.3, "streak": 2})
    assert mr._series_breached(e2) is True


def test_delta_band_still_works():  # 回归：旧 delta/z 行为不变
    e = _entry({"delta": 3.0}, {"value": 160, "prev_value": 156})
    assert mr._series_breached(e) is True

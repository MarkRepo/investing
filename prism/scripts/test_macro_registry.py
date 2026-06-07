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
        "source": "FRED", "fetch_method": "fred-api", "state": "改",
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

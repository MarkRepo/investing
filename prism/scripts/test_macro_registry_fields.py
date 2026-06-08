"""β：登记表新字段 authority / availability 的枚举校验（可空，给值则须合法）。"""
import pytest
from prism.scripts import macro_registry as reg


@pytest.fixture
def tmp_reg(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path)
    reg.create_registry("m", "v")
    return "m", "v"


def _base(extra):
    return {"name": "X", "tier": "B", "cadence_type": "series",
            "mechanism": "CO", "importance": "confirming", **extra}


def test_valid_authority_availability_pass(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"authority": "official", "availability": "scripted"}))
    assert reg.validate_registry(slug, variant) == []


def test_bad_authority_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"authority": "bogus"}))
    assert any("authority" in e for e in reg.validate_registry(slug, variant))


def test_bad_availability_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"availability": "maybe"}))
    assert any("availability" in e for e in reg.validate_registry(slug, variant))


def test_absent_fields_ok(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({}))
    assert reg.validate_registry(slug, variant) == []


def test_recipe_json_default_requires_json_path(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"fetch_recipe": {"url": "https://x", "parse": {}}}))
    assert any("json_path" in e for e in reg.validate_registry(slug, variant))


def test_recipe_csv_requires_value_column(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base(
        {"fetch_recipe": {"kind": "csv", "url": "https://x", "parse": {"date_column": "DATE"}}}))
    assert any("value_column" in e for e in reg.validate_registry(slug, variant))


def test_recipe_unknown_kind_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base(
        {"fetch_recipe": {"kind": "xml", "url": "https://x", "parse": {}}}))
    assert any("kind" in e for e in reg.validate_registry(slug, variant))


def test_recipe_valid_csv_passes(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base(
        {"fetch_recipe": {"kind": "csv", "url": "https://x", "parse": {"value_column": "Value"}}}))
    assert reg.validate_registry(slug, variant) == []

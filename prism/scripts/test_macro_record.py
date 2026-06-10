"""macro_record CLI：headless LLM 取数落盘 + 可选 promote 闸门。"""
import pytest

from prism.scripts import macro_registry as reg
from prism.scripts import macro_record


@pytest.fixture
def tmp_reg(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path)
    reg.create_registry("m", "v")
    return "m", "v"


def _llm_entry(name="X"):
    return {"name": name, "tier": "B", "cadence_type": "series",
            "mechanism": "CO", "importance": "confirming", "availability": "llm"}


def test_records_value_and_evidence(tmp_reg, capsys):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _llm_entry())
    rc = macro_record.main([slug, variant, "X", "--value", "12.3",
                            "--as-of", "2026-06-05", "--evidence", "ISM 官网"])
    assert rc == 0
    e = next(i for i in reg.read_registry(slug, variant)["inputs"] if i["name"] == "X")
    assert e["observed"]["value"] == 12.3
    assert e["observed"]["as_of"] == "2026-06-05"
    assert e["observed"]["evidence"] == "ISM 官网"
    assert e["availability"] == "llm"   # 未加 --scriptable，不升档


def test_scriptable_promotes_with_value(tmp_reg, capsys):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _llm_entry())
    macro_record.main([slug, variant, "X", "--value", "9.0",
                       "--scriptable", "--note", "可由 JSON 端点直拉"])
    e = next(i for i in reg.read_registry(slug, variant)["inputs"] if i["name"] == "X")
    assert e["availability"] == "scriptable_todo"
    assert e["note"] == "可由 JSON 端点直拉"
    assert "promoted_to_scriptable_todo=True" in capsys.readouterr().out


def test_scriptable_no_value_does_not_promote(tmp_reg, capsys):
    """只 evidence 无 value → 闸门拦下，不升档。"""
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _llm_entry())
    macro_record.main([slug, variant, "X", "--evidence", "只有定性引文",
                       "--scriptable", "--note", "n"])
    e = next(i for i in reg.read_registry(slug, variant)["inputs"] if i["name"] == "X")
    assert e["availability"] == "llm"
    assert "promoted_to_scriptable_todo=False" in capsys.readouterr().out


def test_acq_note_recorded_even_without_promote(tmp_reg):
    """--acq-note 即使未 promote（判定不可脚本化）也写 observed.acq_note。"""
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _llm_entry())
    macro_record.main([slug, variant, "X", "--value", "1.5",
                       "--as-of", "2026-06-05", "--evidence", "官网",
                       "--acq-note", "无固定端点，须人工检索，不可脚本化"])
    e = next(i for i in reg.read_registry(slug, variant)["inputs"] if i["name"] == "X")
    assert e["observed"]["acq_note"] == "无固定端点，须人工检索，不可脚本化"
    assert e["availability"] == "llm"   # 未加 --scriptable

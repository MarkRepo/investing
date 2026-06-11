import tempfile, shutil
from pathlib import Path
import pytest
from prism.scripts import macro_registry as mr


@pytest.fixture
def reg(monkeypatch):
    tmp = Path(tempfile.mkdtemp())
    monkeypatch.setattr(mr, "_PRISM_ROOT", tmp)
    slug, variant = "t-macro", "v"
    mr.create_registry(slug, variant)
    yield slug, variant
    shutil.rmtree(tmp)


def _good_entry(**over):
    e = {
        "name": "JOLTS", "tier": "A", "cadence_type": "event",
        "targets": ["rates"], "mechanism": "CD", "importance": "confirming",
        "causal_sentence": "空缺度量松紧→反应函数→利率。",
        "family": "增长就业",
        "gloss": {"define": "BLS 月度职位空缺/离职率调查",
                   "read": "空缺/离职越高=就业越紧",
                   "use": "离职回落=就业降温→Fed 有降息空间→利好成长"},
    }
    e.update(over)
    return e


def test_valid_family_and_gloss_pass(reg):
    slug, variant = reg
    mr.upsert_input(slug, variant, _good_entry())
    assert mr.validate_registry(slug, variant) == []


def test_unknown_family_rejected(reg):
    slug, variant = reg
    mr.upsert_input(slug, variant, _good_entry(family="瞎写的族"))
    errs = mr.validate_registry(slug, variant)
    assert any("family" in e for e in errs)


def test_partial_gloss_rejected(reg):
    slug, variant = reg
    mr.upsert_input(slug, variant, _good_entry(gloss={"define": "x"}))
    errs = mr.validate_registry(slug, variant)
    assert any("gloss" in e for e in errs)


def test_inputs_missing_gloss_lists_incomplete(reg):
    slug, variant = reg
    mr.upsert_input(slug, variant, _good_entry(name="有词条"))
    bare = _good_entry(name="缺词条")
    bare.pop("gloss"); bare.pop("family")
    mr.upsert_input(slug, variant, bare)
    missing = mr.inputs_missing_gloss(mr.read_registry(slug, variant))
    assert missing == ["缺词条"]

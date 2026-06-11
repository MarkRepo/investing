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


def test_build_body_groups_by_family_order(reg):
    slug, variant = reg
    from prism.scripts import input_glossary as ig
    mr.upsert_input(slug, variant, _good_entry(name="核心PCE", family="通胀",
        gloss={"define": "Fed 首选通胀尺", "read": "通胀粘不粘", "use": "超预期→偏鹰→压成长"}))
    mr.upsert_input(slug, variant, _good_entry(name="JOLTS", family="增长就业"))
    body = ig.build_body(mr.read_registry(slug, variant))
    # 族系标题按 CANONICAL_FAMILIES 顺序：增长就业 在 通胀 之前
    assert body.index("### 增长就业") < body.index("### 通胀")
    # 三层都渲染
    assert "BLS 月度职位空缺" in body and "离职回落" in body


def test_build_body_marks_missing(reg):
    slug, variant = reg
    from prism.scripts import input_glossary as ig
    bare = _good_entry(name="缺条"); bare.pop("gloss"); bare.pop("family")
    mr.upsert_input(slug, variant, bare)
    body = ig.build_body(mr.read_registry(slug, variant))
    assert "尚缺 1 条" in body and "缺条" in body

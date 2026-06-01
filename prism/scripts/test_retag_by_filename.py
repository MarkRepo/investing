"""#1 — retag_by_filename 测试

按 filename 或 mat_id 一次性批量 merge addresses + rings，免 N 次 add_material。
"""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts.topic import create_topic
from prism.scripts.manifest import (
    add_material,
    create_manifest,
    read_manifest,
    retag_by_filename,
)

VARIANT = "v"


@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.outputs._PRISM_ROOT", tmpdir)
    create_topic(
        slug="rc", display_name="X", topic_type="company",
        question="Q?", geo="CN", depth="quick", variant=VARIANT,
        ticker="SSE_688331", short_name="X",
    )
    create_manifest("rc", VARIANT)
    yield tmpdir
    shutil.rmtree(tmpdir)


def _add(filename, **kw):
    return add_material(slug="rc", filename=filename, source_type="annual-report",
                        variant=VARIANT, **kw)


def test_retag_by_filename_sets_both_addresses_and_rings(tmp_topic):
    _add("20-F.htm")
    r = retag_by_filename("rc", VARIANT, {
        "20-F.htm": {"addresses": ["K1", "K4"], "rings": ["bull-bear", "financial-arc"]},
    })
    assert r["updated_count"] == 1
    m = read_manifest("rc", VARIANT)["materials"][0]
    assert set(m["addresses"]) == {"K1", "K4"}
    assert set(m["rings"]) == {"bull-bear", "financial-arc"}


def test_retag_by_mat_id(tmp_topic):
    mid = _add("a.htm")
    r = retag_by_filename("rc", VARIANT, {mid: {"rings": ["mgmt-capital-alloc"]}})
    assert r["changed_mat_ids"] == [mid]
    m = read_manifest("rc", VARIANT)["materials"][0]
    assert m["rings"] == ["mgmt-capital-alloc"]
    assert "addresses" not in m or not m.get("addresses")  # 只给 rings，不动 addresses


def test_retag_merges_not_overwrites(tmp_topic):
    _add("a.htm", addresses=["K2"], rings=["consensus"])
    retag_by_filename("rc", VARIANT, {
        "a.htm": {"addresses": ["K1"], "rings": ["bull-bear"]},
    })
    m = read_manifest("rc", VARIANT)["materials"][0]
    assert set(m["addresses"]) == {"K1", "K2"}
    assert set(m["rings"]) == {"bull-bear", "consensus"}


def test_retag_idempotent(tmp_topic):
    _add("a.htm")
    spec = {"a.htm": {"addresses": ["K1"], "rings": ["bull-bear"]}}
    r1 = retag_by_filename("rc", VARIANT, spec)
    r2 = retag_by_filename("rc", VARIANT, spec)
    assert r1["updated_count"] == 1
    assert r2["updated_count"] == 0


def test_retag_batch_multiple_materials_one_call(tmp_topic):
    """32 条逐条调 → 一次批量。"""
    _add("a.htm"); _add("b.htm"); _add("c.htm")
    r = retag_by_filename("rc", VARIANT, {
        "a.htm": {"rings": ["bull-bear"]},
        "b.htm": {"rings": ["consensus"]},
        "c.htm": {"addresses": ["K5"]},
    })
    assert r["updated_count"] == 3
    mats = {m["filename"]: m for m in read_manifest("rc", VARIANT)["materials"]}
    assert mats["a.htm"]["rings"] == ["bull-bear"]
    assert mats["b.htm"]["rings"] == ["consensus"]
    assert mats["c.htm"]["addresses"] == ["K5"]


def test_retag_reports_unmatched_keys(tmp_topic):
    _add("a.htm")
    r = retag_by_filename("rc", VARIANT, {
        "a.htm": {"rings": ["bull-bear"]},
        "ghost.htm": {"rings": ["consensus"]},  # 无此文件
    })
    assert r["unmatched_keys"] == ["ghost.htm"]


def test_retag_validates_spec_must_be_dict(tmp_topic):
    _add("a.htm")
    with pytest.raises(ValueError, match="必须是 dict"):
        retag_by_filename("rc", VARIANT, {"a.htm": ["K1"]})


def test_retag_validates_field_must_be_list_str(tmp_topic):
    _add("a.htm")
    with pytest.raises(ValueError, match="必须是 list"):
        retag_by_filename("rc", VARIANT, {"a.htm": {"rings": "bull-bear"}})


def test_retag_mapping_type_guard(tmp_topic):
    with pytest.raises(TypeError):
        retag_by_filename("rc", VARIANT, "not a dict")

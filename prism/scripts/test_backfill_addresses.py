"""H7 — backfill_addresses_by_mapping 测试

prescan 在 thesis 写之前跑，标 fact-NN；thesis 写完后主 agent 提供
fact→K# 映射，helper 自动把 K# 合并到 manifest material addresses。
"""
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from prism.scripts.topic import create_topic
from prism.scripts.manifest import (
    add_material,
    create_manifest,
    read_manifest,
    backfill_addresses_by_mapping,
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


def _add(filename, addresses):
    return add_material(
        slug="rc", filename=filename, source_type="web-search",
        variant=VARIANT, addresses=addresses,
    )


def test_backfill_basic_mapping(tmp_topic):
    """fact-04 → K3 + K1 单条 backfill。"""
    mid = _add("a.md", ["fact-04"])
    r = backfill_addresses_by_mapping("rc", VARIANT, {"fact-04": ["K3", "K1"]})
    assert r["updated_count"] == 1
    assert r["changed_mat_ids"] == [mid]

    m = read_manifest("rc", VARIANT)["materials"][0]
    # K# 合并，原 fact 占位保留
    assert set(m["addresses"]) == {"fact-04", "K1", "K3"}


def test_backfill_preserves_existing_addresses(tmp_topic):
    """已有 scope / 其他 K# 不应被覆盖。"""
    _add("a.md", ["fact-04", "scope", "K2"])
    backfill_addresses_by_mapping("rc", VARIANT, {"fact-04": ["K3"]})
    m = read_manifest("rc", VARIANT)["materials"][0]
    assert set(m["addresses"]) == {"fact-04", "scope", "K2", "K3"}


def test_backfill_idempotent(tmp_topic):
    """重复跑结果一致 + 第二次 updated_count=0。"""
    _add("a.md", ["fact-04"])
    r1 = backfill_addresses_by_mapping("rc", VARIANT, {"fact-04": ["K3"]})
    r2 = backfill_addresses_by_mapping("rc", VARIANT, {"fact-04": ["K3"]})
    assert r1["updated_count"] == 1
    assert r2["updated_count"] == 0
    m = read_manifest("rc", VARIANT)["materials"][0]
    assert set(m["addresses"]) == {"fact-04", "K3"}


def test_backfill_multiple_facts_one_material(tmp_topic):
    """同一 material 多个 fact-NN → 合并所有 K#。"""
    _add("a.md", ["fact-04", "fact-17"])
    backfill_addresses_by_mapping("rc", VARIANT, {
        "fact-04": ["K3"],
        "fact-17": ["K4"],
    })
    m = read_manifest("rc", VARIANT)["materials"][0]
    assert set(m["addresses"]) == {"fact-04", "fact-17", "K3", "K4"}


def test_backfill_does_not_touch_unrelated_materials(tmp_topic):
    """没匹配 mapping 键的 material 不动。"""
    mid_a = _add("a.md", ["fact-04"])
    mid_b = _add("b.md", ["scope"])              # 仅 scope，不在 mapping
    mid_c = _add("c.md", ["fact-99"])            # fact-99 不在 mapping
    r = backfill_addresses_by_mapping("rc", VARIANT, {"fact-04": ["K3"]})
    assert r["updated_count"] == 1
    assert r["changed_mat_ids"] == [mid_a]

    mats = {m["id"]: m for m in read_manifest("rc", VARIANT)["materials"]}
    assert set(mats[mid_a]["addresses"]) == {"fact-04", "K3"}
    assert mats[mid_b]["addresses"] == ["scope"]
    assert mats[mid_c]["addresses"] == ["fact-99"]


def test_backfill_reports_unmatched_mapping_keys(tmp_topic):
    """mapping 里有但 manifest 没用到的 key → 列入 unmatched_keys 诊断。"""
    _add("a.md", ["fact-04"])
    r = backfill_addresses_by_mapping("rc", VARIANT, {
        "fact-04": ["K3"],
        "fact-XX": ["K9"],   # 没人引用
    })
    assert r["unmatched_keys"] == ["fact-XX"]


def test_backfill_reports_unmapped_facts_in_manifest(tmp_topic):
    """manifest 有 fact-* 但 mapping 没覆盖 → 列入 unmapped_facts 诊断。"""
    _add("a.md", ["fact-04"])
    _add("b.md", ["fact-99"])
    _add("c.md", ["fact-77"])
    r = backfill_addresses_by_mapping("rc", VARIANT, {"fact-04": ["K3"]})
    assert r["unmapped_facts"] == ["fact-77", "fact-99"]


def test_backfill_validates_mapping_type(tmp_topic):
    with pytest.raises(TypeError):
        backfill_addresses_by_mapping("rc", VARIANT, "not a dict")


def test_backfill_validates_mapping_value_must_be_list(tmp_topic):
    with pytest.raises(ValueError, match="必须是 list"):
        backfill_addresses_by_mapping("rc", VARIANT, {"fact-04": "K3"})


def test_backfill_empty_mapping_no_op(tmp_topic):
    _add("a.md", ["fact-04"])
    r = backfill_addresses_by_mapping("rc", VARIANT, {})
    assert r["updated_count"] == 0


def test_backfill_supports_arbitrary_placeholder_keys(tmp_topic):
    """不限于 fact-*；Q1/Q2/任何字符串都可作为 mapping key。"""
    _add("a.md", ["Q3"])
    r = backfill_addresses_by_mapping("rc", VARIANT, {"Q3": ["K2"]})
    assert r["updated_count"] == 1
    m = read_manifest("rc", VARIANT)["materials"][0]
    assert set(m["addresses"]) == {"Q3", "K2"}


def test_backfill_preserves_material_order_and_other_fields(tmp_topic):
    """manifest 整体结构不动，只改 addresses + updated。"""
    _add("a.md", ["fact-04"])
    _add("b.md", ["fact-17"])
    before = read_manifest("rc", VARIANT)
    backfill_addresses_by_mapping("rc", VARIANT, {
        "fact-04": ["K3"], "fact-17": ["K4"],
    })
    after = read_manifest("rc", VARIANT)
    # 顺序保持
    assert [m["id"] for m in after["materials"]] == [m["id"] for m in before["materials"]]
    # 其他字段保留
    for b, a in zip(before["materials"], after["materials"]):
        assert a["filename"] == b["filename"]
        assert a["source_type"] == b["source_type"]

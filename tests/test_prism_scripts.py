"""Tests for prism/scripts/ — topic, manifest, outputs helpers."""
from __future__ import annotations

import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# topic.py tests
# ---------------------------------------------------------------------------

@pytest.fixture
def topics_root(tmp_path, monkeypatch):
    """Redirect prism/scripts/topic.py to use tmp_path as the prism root."""
    import prism.scripts.topic as t
    monkeypatch.setattr(t, "_PRISM_ROOT", tmp_path)
    (tmp_path / "topics").mkdir()
    return tmp_path


def test_create_topic_writes_yaml(topics_root):
    from prism.scripts import topic as t

    path = t.create_topic(
        slug="cn-pet",
        display_name="中国宠物行业",
        topic_type="industry",
        question="中国宠物行业的投资机会在哪里",
        geo="CN",
        depth="deep",
    )

    assert path.exists()
    data = t.read_topic("cn-pet")
    assert data["slug"] == "cn-pet"
    assert data["display_name"] == "中国宠物行业"
    assert data["type"] == "industry"
    assert data["scope"]["geo"] == "CN"
    assert data["scope"]["depth"] == "deep"
    assert data["status"] == "active"
    assert data["stage"] == "00-init"
    # All 8 outputs present and pending
    assert len(data["outputs_state"]) == 8
    for v in data["outputs_state"].values():
        assert v["status"] == "pending"
        assert v["version"] == 0
        assert v["last_updated"] is None


def test_create_topic_raises_if_exists(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    with pytest.raises(FileExistsError):
        t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")


def test_read_topic_raises_if_missing(topics_root):
    from prism.scripts import topic as t

    with pytest.raises(FileNotFoundError):
        t.read_topic("nonexistent")


def test_set_stage(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    t.set_stage("cn-pet", "02-gather-materials")
    assert t.read_topic("cn-pet")["stage"] == "02-gather-materials"


def test_set_output_status(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    t.set_output_status("cn-pet", "01_business_panorama", "fresh", version=1)
    data = t.read_topic("cn-pet")
    out = data["outputs_state"]["01_business_panorama"]
    assert out["status"] == "fresh"
    assert out["version"] == 1
    assert out["last_updated"] is not None


def test_set_next_actions(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    t.set_next_actions("cn-pet", ["运行 workflow 02", "上传资料"])
    assert t.read_topic("cn-pet")["next_actions"] == ["运行 workflow 02", "上传资料"]


def test_set_user_todos(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    t.set_user_todos("cn-pet", ["下载年报"])
    assert t.read_topic("cn-pet")["user_todos"] == ["下载年报"]


def test_list_topics_returns_all(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    t.create_topic("cn-space", "中国商业航天", "arena", "q2", "CN", "standard")
    topics = t.list_topics()
    slugs = [tp["slug"] for tp in topics]
    assert "cn-pet" in slugs
    assert "cn-space" in slugs


# ---------------------------------------------------------------------------
# manifest.py tests
# ---------------------------------------------------------------------------

@pytest.fixture
def manifest_root(tmp_path, monkeypatch):
    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    monkeypatch.setattr(t, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(m, "_PRISM_ROOT", tmp_path)
    (tmp_path / "topics").mkdir()
    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    return tmp_path


def test_create_manifest(manifest_root):
    from prism.scripts import manifest as m

    path = m.create_manifest("cn-pet")
    assert path.exists()
    data = m.read_manifest("cn-pet")
    assert data["slug"] == "cn-pet"
    assert data["materials"] == []


def test_add_material_returns_id(manifest_root):
    from prism.scripts import manifest as m

    m.create_manifest("cn-pet")
    mat_id = m.add_material("cn-pet", "report.md", "sell-side-note")
    assert mat_id.startswith("mat-")
    data = m.read_manifest("cn-pet")
    assert len(data["materials"]) == 1
    assert data["materials"][0]["filename"] == "report.md"
    assert data["materials"][0]["processed"] is False


def test_mark_processed(manifest_root):
    from prism.scripts import manifest as m

    m.create_manifest("cn-pet")
    mat_id = m.add_material("cn-pet", "report.md", "sell-side-note")
    m.mark_processed("cn-pet", mat_id)
    assert m.read_manifest("cn-pet")["materials"][0]["processed"] is True


def test_list_unprocessed(manifest_root):
    from prism.scripts import manifest as m

    m.create_manifest("cn-pet")
    m.add_material("cn-pet", "a.md", "sell-side-note")
    id2 = m.add_material("cn-pet", "b.md", "annual-report")
    m.mark_processed("cn-pet", id2)
    unprocessed = m.list_unprocessed("cn-pet")
    assert len(unprocessed) == 1
    assert unprocessed[0]["filename"] == "a.md"


def test_material_count(manifest_root):
    from prism.scripts import manifest as m

    m.create_manifest("cn-pet")
    id1 = m.add_material("cn-pet", "a.md", "sell-side-note")
    m.add_material("cn-pet", "b.md", "sell-side-note")
    m.mark_processed("cn-pet", id1)
    counts = m.material_count("cn-pet")
    assert counts == {"total": 2, "processed": 1, "unprocessed": 1}


# ---------------------------------------------------------------------------
# outputs.py tests
# ---------------------------------------------------------------------------

_OUTPUT_LABELS = {
    "01_business_panorama": "商业全景",
    "02_cycle_positioning": "周期定位",
    "03_narrative_ecology": "叙事谱系",
    "04_implied_expectations": "隐含预期与观点光谱",
    "05_historical_mirrors": "历史镜像",
    "06_risk_blindspots": "风险盲点",
    "07_decision_kit": "决策辅助",
    "08_living_feed": "信息流时间线",
}


@pytest.fixture
def outputs_root(tmp_path, monkeypatch):
    import prism.scripts.topic as t
    import prism.scripts.outputs as o
    monkeypatch.setattr(t, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(o, "_PRISM_ROOT", tmp_path)
    (tmp_path / "topics").mkdir()
    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    return tmp_path


def test_list_outputs_returns_8(outputs_root):
    from prism.scripts import outputs as o

    result = o.list_outputs("cn-pet")
    assert len(result) == 8
    keys = [r["key"] for r in result]
    assert keys == list(_OUTPUT_LABELS.keys())


def test_list_outputs_file_exists_false_initially(outputs_root):
    from prism.scripts import outputs as o

    result = o.list_outputs("cn-pet")
    for r in result:
        assert r["file_exists"] is False
        assert r["status"] == "pending"


def test_list_outputs_file_exists_true_after_write(outputs_root, tmp_path):
    from prism.scripts import outputs as o
    import prism.scripts.topic as t

    # Simulate Claude writing the output file
    out_path = tmp_path / "topics" / "cn-pet" / "outputs" / "01_business_panorama.md"
    out_path.write_text("# 商业全景\n\n内容。", encoding="utf-8")
    t.set_output_status("cn-pet", "01_business_panorama", "fresh", version=1)

    result = o.list_outputs("cn-pet")
    panorama = next(r for r in result if r["key"] == "01_business_panorama")
    assert panorama["file_exists"] is True
    assert panorama["status"] == "fresh"


def test_read_output_html_converts_markdown(outputs_root, tmp_path):
    from prism.scripts import outputs as o

    out_path = tmp_path / "topics" / "cn-pet" / "outputs" / "01_business_panorama.md"
    out_path.write_text("# 标题\n\n**加粗**文本。", encoding="utf-8")

    html = o.read_output_html("cn-pet", "01_business_panorama")
    assert "<h1>" in html
    assert "<strong>" in html


def test_read_output_html_raises_if_missing(outputs_root):
    from prism.scripts import outputs as o

    with pytest.raises(FileNotFoundError):
        o.read_output_html("cn-pet", "01_business_panorama")

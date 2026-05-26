"""Tests for prism/scripts/ — topic, manifest, outputs helpers.

Note 2026-05-26: 全文重写以适配 variant 重构 + topic.PRISM_ROOT 命名（旧版引用
`_PRISM_ROOT` 已失效）。company 类型测试用真 ticker（修 H1 后无 ticker 会 raise）。
"""
from __future__ import annotations

import pytest

VARIANT = "sonnet"


# ---------------------------------------------------------------------------
# topic.py tests
# ---------------------------------------------------------------------------

@pytest.fixture
def topics_root(tmp_path, monkeypatch):
    """Redirect prism/scripts/topic.py to use tmp_path as the prism root.

    topic.py 模块属性名为 PRISM_ROOT（无下划线），不同于 manifest/outputs 的 _PRISM_ROOT。
    """
    import prism.scripts.topic as t
    monkeypatch.setattr(t, "PRISM_ROOT", tmp_path)
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
        variant=VARIANT,
    )

    assert path.exists()
    data = t.read_topic("cn-pet", VARIANT)
    assert data["slug"] == "cn-pet"
    assert data["display_name"] == "中国宠物行业"
    assert data["type"] == "industry"
    assert data["scope"]["geo"] == "CN"
    assert data["scope"]["depth"] == "deep"
    assert data["status"] == "active"
    assert data["stage"] == "00-init"
    # industry 输出包含 8 base + 1 industry_extra = 9
    assert len(data["outputs_state"]) == 9
    for v in data["outputs_state"].values():
        assert v["status"] == "pending"
        assert v["version"] == 0
        assert v["last_updated"] is None


def test_create_topic_raises_if_exists(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep", VARIANT)
    with pytest.raises(FileExistsError):
        t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep", VARIANT)


def test_read_topic_raises_if_missing(topics_root):
    from prism.scripts import topic as t

    with pytest.raises(FileNotFoundError):
        t.read_topic("nonexistent", VARIANT)


def test_set_stage(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep", VARIANT)
    t.set_stage("cn-pet", "02-gather-materials", VARIANT)
    assert t.read_topic("cn-pet", VARIANT)["stage"] == "02-gather-materials"


def test_set_output_status(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep", VARIANT)
    t.set_output_status("cn-pet", "01_business_panorama", "fresh", VARIANT, version=1)
    data = t.read_topic("cn-pet", VARIANT)
    out = data["outputs_state"]["01_business_panorama"]
    assert out["status"] == "fresh"
    assert out["version"] == 1
    assert out["last_updated"] is not None


def test_set_next_actions(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep", VARIANT)
    t.set_next_actions("cn-pet", ["运行 workflow 02", "上传资料"], VARIANT)
    assert t.read_topic("cn-pet", VARIANT)["next_actions"] == ["运行 workflow 02", "上传资料"]


def test_set_user_todos(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep", VARIANT)
    t.set_user_todos("cn-pet", ["下载年报"], VARIANT)
    todos = t.read_topic("cn-pet", VARIANT)["user_todos"]
    # _normalize_todo 把 str 升级成 dict
    assert len(todos) == 1
    assert todos[0]["task"] == "下载年报"
    assert todos[0]["status"] == "pending"


def test_list_topics_returns_all(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep", VARIANT)
    t.create_topic("cn-space", "中国商业航天", "arena", "q2", "CN", "standard", VARIANT)
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
    monkeypatch.setattr(t, "PRISM_ROOT", tmp_path)
    monkeypatch.setattr(m, "_PRISM_ROOT", tmp_path)
    (tmp_path / "topics").mkdir()
    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep", VARIANT)
    return tmp_path


def test_create_manifest(manifest_root):
    from prism.scripts import manifest as m

    path = m.create_manifest("cn-pet", VARIANT)
    assert path.exists()
    data = m.read_manifest("cn-pet", VARIANT)
    assert data["slug"] == "cn-pet"
    assert data["materials"] == []


def test_add_material_returns_id(manifest_root):
    from prism.scripts import manifest as m

    m.create_manifest("cn-pet", VARIANT)
    mat_id = m.add_material("cn-pet", "report.md", "sell-side-note", VARIANT)
    assert mat_id.startswith("mat-")
    data = m.read_manifest("cn-pet", VARIANT)
    assert len(data["materials"]) == 1
    assert data["materials"][0]["filename"] == "report.md"
    assert data["materials"][0]["processed"] is False


def test_mark_processed(manifest_root):
    from prism.scripts import manifest as m

    m.create_manifest("cn-pet", VARIANT)
    mat_id = m.add_material("cn-pet", "report.md", "sell-side-note", VARIANT)
    m.mark_processed("cn-pet", mat_id, VARIANT)
    assert m.read_manifest("cn-pet", VARIANT)["materials"][0]["processed"] is True


def test_list_unprocessed(manifest_root):
    from prism.scripts import manifest as m

    m.create_manifest("cn-pet", VARIANT)
    m.add_material("cn-pet", "a.md", "sell-side-note", VARIANT)
    id2 = m.add_material("cn-pet", "b.md", "annual-report", VARIANT)
    m.mark_processed("cn-pet", id2, VARIANT)
    unprocessed = m.list_unprocessed("cn-pet", VARIANT)
    assert len(unprocessed) == 1
    assert unprocessed[0]["filename"] == "a.md"


def test_material_count(manifest_root):
    from prism.scripts import manifest as m

    m.create_manifest("cn-pet", VARIANT)
    id1 = m.add_material("cn-pet", "a.md", "sell-side-note", VARIANT)
    m.add_material("cn-pet", "b.md", "sell-side-note", VARIANT)
    m.mark_processed("cn-pet", id1, VARIANT)
    counts = m.material_count("cn-pet", VARIANT)
    # 当前实现还返回 self_total/parent_total（父子 topic 共享 materials 用），用 subset 校验
    assert counts["total"] == 2
    assert counts["processed"] == 1
    assert counts["unprocessed"] == 1


# ---------------------------------------------------------------------------
# outputs.py tests
# ---------------------------------------------------------------------------

@pytest.fixture
def outputs_root(tmp_path, monkeypatch):
    import prism.scripts.topic as t
    import prism.scripts.outputs as o
    monkeypatch.setattr(t, "PRISM_ROOT", tmp_path)
    monkeypatch.setattr(o, "_PRISM_ROOT", tmp_path)
    (tmp_path / "topics").mkdir()
    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep", VARIANT)
    return tmp_path


def test_list_outputs_returns_8_base(outputs_root):
    """list_outputs 当前只列 8 个 base outputs（不含 industry/arena/company extra）。

    industry 类型的 outputs_state 实际有 9 个（含 09_industry_to_arenas），
    但 list_outputs() 接口只暴露 8 个标准 panel——这是当前 web 路由的契约。
    """
    from prism.scripts import outputs as o

    result = o.list_outputs("cn-pet", VARIANT)
    assert len(result) == 8
    keys = [r["key"] for r in result]
    for base in ("01_business_panorama", "08_living_feed"):
        assert base in keys


def test_list_outputs_file_exists_false_initially(outputs_root):
    from prism.scripts import outputs as o

    result = o.list_outputs("cn-pet", VARIANT)
    for r in result:
        assert r["file_exists"] is False
        assert r["status"] == "pending"


def test_list_outputs_file_exists_true_after_write(outputs_root, tmp_path):
    from prism.scripts import outputs as o
    import prism.scripts.topic as t

    out_path = tmp_path / "topics" / "cn-pet" / VARIANT / "outputs" / "01_business_panorama.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("# 商业全景\n\n内容。", encoding="utf-8")
    t.set_output_status("cn-pet", "01_business_panorama", "fresh", VARIANT, version=1)

    result = o.list_outputs("cn-pet", VARIANT)
    panorama = next(r for r in result if r["key"] == "01_business_panorama")
    assert panorama["file_exists"] is True
    assert panorama["status"] == "fresh"


def test_read_output_html_converts_markdown(outputs_root, tmp_path):
    from prism.scripts import outputs as o

    out_path = tmp_path / "topics" / "cn-pet" / VARIANT / "outputs" / "01_business_panorama.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("# 标题\n\n**加粗**文本。", encoding="utf-8")

    html = o.read_output_html("cn-pet", "01_business_panorama", VARIANT)
    assert "<h1>" in html
    assert "<strong>" in html


def test_read_output_html_raises_if_missing(outputs_root):
    from prism.scripts import outputs as o

    with pytest.raises(FileNotFoundError):
        o.read_output_html("cn-pet", "01_business_panorama", VARIANT)

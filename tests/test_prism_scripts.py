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

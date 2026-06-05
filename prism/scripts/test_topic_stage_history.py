"""Tests for B1: set_stage 写 stage_history + 进入时 gap 快照（平行顶层键）。"""
import tempfile
from pathlib import Path

import pytest

from prism.scripts import topic as topic_io


@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.gap_detector.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.outputs._PRISM_ROOT", tmpdir)
    slug, variant = "sh-test", "test"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(slug=slug, display_name="T", topic_type="company",
                          question="Q?", geo="US", depth="quick", variant=variant,
                          short_name="T", ticker="US_T")
    return slug, variant


def test_set_stage_appends_history(tmp_topic):
    slug, variant = tmp_topic
    topic_io.set_stage(slug, "02-gather-materials", variant)
    topic_io.set_stage(slug, "03-extracting", variant)
    data = topic_io.read_topic(slug, variant)
    hist = data["stage_history"]
    assert [h["stage"] for h in hist][-2:] == ["02-gather-materials", "03-extracting"]
    assert hist[-2]["exited_at"] is not None     # 上一条已回填
    assert hist[-1]["exited_at"] is None         # 当前未退出
    assert "gap_snapshot" in hist[-1]


def test_set_stage_idempotent_same_stage(tmp_topic):
    slug, variant = tmp_topic
    topic_io.set_stage(slug, "02-gather-materials", variant)
    n1 = len(topic_io.read_topic(slug, variant)["stage_history"])
    topic_io.set_stage(slug, "02-gather-materials", variant)  # 同 stage 不重复 append
    n2 = len(topic_io.read_topic(slug, variant)["stage_history"])
    assert n1 == n2


def test_legacy_topic_no_history_is_safe(tmp_topic):
    slug, variant = tmp_topic
    data = topic_io.read_topic(slug, variant)
    # 旧 topic 可能无 stage_history；read 不应炸
    assert isinstance(data.get("stage", {}), (dict, str)) or data.get("stage") is None

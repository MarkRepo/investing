"""F17: primer depth/critic 机械门禁 —— set_output_status('00_primer','fresh') 软降级。"""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts import topic as topic_io


@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    slug, variant = "test-primer", "test"
    (tmpdir / "topics" / slug / variant / "outputs").mkdir(parents=True)
    topic_io.create_topic(
        slug=slug, display_name="T", topic_type="industry",
        question="Q?", geo="CN", depth="deep", variant=variant, short_name="T",
    )
    yield slug, variant, tmpdir
    shutil.rmtree(tmpdir)


def _write_primer(tmpdir, slug, variant, *, depth, body):
    p = tmpdir / "topics" / slug / variant / "outputs" / "00_primer.md"
    p.write_text(f"---\ndepth: {depth}\n---\n{body}", encoding="utf-8")


def test_primer_gate_outline_downgraded(tmp_topic):
    """深度不足的 outline 自标 deep → set_output_status fresh 被降级 draft。"""
    slug, variant, tmpdir = tmp_topic
    _write_primer(tmpdir, slug, variant, depth="deep", body="# 提纲\n" + "短" * 200)
    topic_io.set_output_status(slug, "00_primer", "fresh", variant, version=1)
    st = topic_io.read_topic(slug, variant)["outputs_state"]["00_primer"]
    assert st["status"] == "draft", "deep 但太短应降级"
    assert st["primer_gate"]["downgraded_from"] == "fresh"
    assert any("字" in w for w in st["primer_gate"]["warnings"])


def test_primer_gate_full_passes(tmp_topic):
    """够长 + 争议节 + 自检节 + critic_passed → fresh 保持 fresh。"""
    slug, variant, tmpdir = tmp_topic
    body = ("# 入门\n" + "正文内容详尽。" * 1000
            + "\n## 争议\n1. 争议一\n## 自检清单\n- 读完应能 X\n")
    _write_primer(tmpdir, slug, variant, depth="deep", body=body)
    topic_io.set_output_critic_passed(slug, variant, "00_primer")  # 先置 critic flag
    topic_io.set_output_status(slug, "00_primer", "fresh", variant, version=1)
    st = topic_io.read_topic(slug, variant)["outputs_state"]["00_primer"]
    assert st["status"] == "fresh"
    assert "primer_gate" not in st


def test_primer_gate_missing_critic_downgrades(tmp_topic):
    """够长够结构但没置 critic_passed → 仍降级（critic 不可省落成机械 flag）。"""
    slug, variant, tmpdir = tmp_topic
    body = ("# 入门\n" + "正文内容详尽。" * 1000 + "\n## 争议\n争议\n## 自检\n- X\n")
    _write_primer(tmpdir, slug, variant, depth="deep", body=body)
    topic_io.set_output_status(slug, "00_primer", "fresh", variant, version=1)
    st = topic_io.read_topic(slug, variant)["outputs_state"]["00_primer"]
    assert st["status"] == "draft"
    assert any("critic" in w for w in st["primer_gate"]["warnings"])


def test_primer_gate_shallow_not_gated(tmp_topic):
    """depth=shallow 诚实标浅 → 不设字数地板，fresh 保持。"""
    slug, variant, tmpdir = tmp_topic
    _write_primer(tmpdir, slug, variant, depth="shallow", body="# 浅 primer\n短内容")
    topic_io.set_output_status(slug, "00_primer", "fresh", variant, version=1)
    st = topic_io.read_topic(slug, variant)["outputs_state"]["00_primer"]
    assert st["status"] == "fresh"


def test_set_output_status_nonprimer_unchanged(tmp_topic):
    """回归护栏：非 00_primer 的 fresh 不过门禁，字节不变。"""
    slug, variant, _ = tmp_topic
    topic_io.set_output_status(slug, "i_industry_case", "fresh", variant, version=2)
    st = topic_io.read_topic(slug, variant)["outputs_state"]["i_industry_case"]
    assert st["status"] == "fresh"
    assert st["version"] == 2
    assert "primer_gate" not in st

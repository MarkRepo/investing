"""早期 ingest：register_inbox_materials 单桶登记 topic 家底元数据（零正文读取、幂等）。"""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts import topic as topic_io
from prism.scripts.manifest import (
    create_manifest,
    read_manifest,
    register_inbox_materials,
)


@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    slug, variant = "test-ingest", "test"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(
        slug=slug, display_name="T", topic_type="company",
        question="Q?", geo="US", depth="quick", variant=variant,
        short_name="T", ticker="US_T",
    )
    create_manifest(slug, variant)
    yield slug, variant, tmpdir
    shutil.rmtree(tmpdir)


def _inbox(tmpdir, slug) -> Path:
    d = tmpdir / "topics" / slug / "inbox"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_registers_topic_inbox_and_materials(tmp_topic):
    slug, variant, tmpdir = tmp_topic
    inbox = _inbox(tmpdir, slug)
    (inbox / "report.pdf").write_text("x", encoding="utf-8")
    (inbox / "2025_HK02228_annual_X.pdf").write_text("x", encoding="utf-8")
    (inbox / "note.md").write_text("x", encoding="utf-8")
    (inbox / "data.csv").write_text("a,b", encoding="utf-8")
    (inbox / "page.html").write_text("<p>x</p>", encoding="utf-8")
    # 顶层文件之外的子目录文件不应被登记（避开 mineru / sec 派生物）
    sub = inbox / "sub"
    sub.mkdir()
    (sub / "ignore_me.md").write_text("x", encoding="utf-8")
    # 隐藏文件忽略
    (inbox / ".hidden").write_text("x", encoding="utf-8")

    registered = register_inbox_materials(slug, variant)
    by_name = {r["filename"]: r["source_type"] for r in registered}

    assert by_name == {
        "report.pdf": "sell-side-note",
        "2025_HK02228_annual_X.pdf": "annual-report",
        "note.md": "manual-note",
        "data.csv": "data",
        "page.html": "web-article",
    }
    # 子目录文件 / 隐藏文件未登记
    mats = {m["filename"] for m in read_manifest(slug, variant)["materials"]}
    assert "ignore_me.md" not in mats
    assert ".hidden" not in mats
    # addresses 留空（待下游补）
    for m in read_manifest(slug, variant)["materials"]:
        assert not m.get("addresses")


def test_idempotent_second_run_registers_nothing(tmp_topic):
    slug, variant, tmpdir = tmp_topic
    inbox = _inbox(tmpdir, slug)
    (inbox / "a.md").write_text("x", encoding="utf-8")
    (inbox / "b.pdf").write_text("x", encoding="utf-8")

    first = register_inbox_materials(slug, variant)
    assert len(first) == 2
    n_after_first = len(read_manifest(slug, variant)["materials"])

    second = register_inbox_materials(slug, variant)
    assert second == [], "重扫不得重登已登记文件"
    assert len(read_manifest(slug, variant)["materials"]) == n_after_first


def test_zero_content_read(tmp_topic):
    """登记纯元数据——不读正文。放非 UTF-8 二进制文件，若函数试图 decode 会炸；
    它必须照常登记，证明零正文读取。"""
    slug, variant, tmpdir = tmp_topic
    inbox = _inbox(tmpdir, slug)
    (inbox / "binary.pdf").write_bytes(b"\xff\xfe\x00\x01not-utf8\x80\x81")

    registered = register_inbox_materials(slug, variant)
    assert any(r["filename"] == "binary.pdf" for r in registered)

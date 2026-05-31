"""F14: material_count.unprocessed_actionable 排除 Role α prescan web 料。"""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts import topic as topic_io
from prism.scripts.manifest import (
    add_material,
    create_manifest,
    make_search_meta,
    material_count,
)


def _sm(triggered_by: str) -> dict:
    return make_search_meta(query="q", url=f"https://reuters.com/{triggered_by}",
                            domain="reuters.com", domain_tier="whitelist",
                            triggered_by=triggered_by)


@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    slug, variant = "test-mc", "test"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(
        slug=slug, display_name="T", topic_type="company",
        question="Q?", geo="US", depth="quick", variant=variant,
        short_name="T", ticker="US_T",
    )
    create_manifest(slug, variant)
    yield slug, variant, tmpdir
    shutil.rmtree(tmpdir)


def test_material_count_actionable_excludes_role_alpha(tmp_topic):
    """Role α（01-prescan）web 料不计入 unprocessed_actionable，但计入全量 unprocessed。"""
    slug, variant, _ = tmp_topic
    # 1 份 Role β（02-step0）真材料 — 可处理
    add_material(slug=slug, filename="real.md", source_type="web-article",
                 variant=variant, addresses=["K1"], search_meta=_sm("02-step0"))
    # 2 份 Role α（01/00-prescan）prescan web 料 — 不该计入 actionable
    add_material(slug=slug, filename="p1.md", source_type="web-search",
                 variant=variant, addresses=["K1"], search_meta=_sm("01-prescan"))
    add_material(slug=slug, filename="p2.md", source_type="web-search",
                 variant=variant, addresses=["K1"], search_meta=_sm("00-prescan"))

    c = material_count(slug, variant)
    assert c["total"] == 3
    assert c["unprocessed"] == 3, "全量未处理含 Role α（向后兼容）"
    assert c["unprocessed_actionable"] == 1, "可处理未处理仅 Role β 那份"


def test_material_count_actionable_zero_triggers_advance(tmp_topic):
    """全是 Role α 料时 actionable=0 → 03 advance gate（==0）成立、可升 04。"""
    slug, variant, _ = tmp_topic
    add_material(slug=slug, filename="p1.md", source_type="web-search",
                 variant=variant, addresses=["K1"], search_meta=_sm("01-prescan"))
    c = material_count(slug, variant)
    assert c["unprocessed"] == 1
    assert c["unprocessed_actionable"] == 0

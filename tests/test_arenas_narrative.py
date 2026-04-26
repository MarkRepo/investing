from pathlib import Path
import pytest

from app import config as cfg
from app.io import arenas as arenas_io


def test_write_definition_accepts_industry_and_battleground_focus(tmp_path):
    base = tmp_path
    arenas_io.write_definition(
        slug="test-arena",
        name="测试战场",
        definition_text="def body",
        industry="cn-cmp-material",
        battleground_focus="国产 CMP 抛光液挑战 Dupont/Cabot/Versum",
        base=base,
    )
    result = arenas_io.read_definition("test-arena", base=base)
    fm = result["frontmatter"]
    assert fm["industry"] == "cn-cmp-material"
    assert fm["battleground_focus"] == "国产 CMP 抛光液挑战 Dupont/Cabot/Versum"


def test_write_definition_industry_and_focus_optional(tmp_path):
    """Existing arenas without these fields must still work."""
    base = tmp_path
    arenas_io.write_definition(slug="legacy", name="Legacy", definition_text="x", base=base)
    r = arenas_io.read_definition("legacy", base=base)
    assert r["frontmatter"].get("industry") is None or r["frontmatter"].get("industry") == ""


def test_arena_narrative_skeleton_files_on_write_definition(tmp_path):
    """When definition is written for a NEW arena, 5 additional narrative
    skeleton .md files are created (dim != 'definition')."""
    base = tmp_path
    arenas_io.write_definition(
        slug="a1", name="Arena 1", definition_text="body",
        industry="ind-x", battleground_focus="focus",
        base=base,
    )
    slug_dir = base / "arenas" / "a1"
    for dim in cfg.ARENA_DIMENSIONS:
        if dim == "definition":
            continue  # definition.md is the existing file
        assert (slug_dir / f"{dim.replace('_', '-')}.md").is_file()


def test_arena_read_narrative_returns_content(tmp_path):
    base = tmp_path
    arenas_io.write_definition(slug="a", name="A", definition_text="x",
                               industry="i", battleground_focus="f", base=base)
    content = arenas_io.read_narrative("a", "participants", base=base)
    assert isinstance(content, str)
    assert content.startswith("# ")  # skeleton header present


def test_arena_append_narrative_block_appends(tmp_path):
    base = tmp_path
    arenas_io.write_definition(slug="a", name="A", definition_text="x",
                               industry="i", battleground_focus="f", base=base)
    arenas_io.append_narrative_block(
        slug="a", dim="narratives", block="Bull 情景：挑战者赢",
        source_meta={"institution": "X","date": "2026-01-01","sha8": "abcdef12","source_id": "sid"},
        base=base,
    )
    md = arenas_io.read_narrative("a", "narratives", base=base)
    assert "### 来源 X 2026-01-01 (sha8=abcdef12)" in md
    assert "Bull 情景：挑战者赢" in md


def test_arena_append_narrative_rejects_unknown_dim(tmp_path):
    base = tmp_path
    arenas_io.write_definition(slug="a", name="A", definition_text="x", base=base)
    with pytest.raises(ValueError, match="unknown"):
        arenas_io.append_narrative_block(
            "a", "bogus", "x", {"institution":"a","date":"b","sha8":"c","source_id":"d"},
            base=base,
        )


def test_find_by_industry_lists_arenas(tmp_path):
    base = tmp_path
    arenas_io.write_definition(slug="a1", name="A1", definition_text="x",
                               industry="ind-x", battleground_focus="f", base=base)
    arenas_io.write_definition(slug="a2", name="A2", definition_text="x",
                               industry="ind-y", battleground_focus="f", base=base)
    arenas_io.write_definition(slug="a3", name="A3", definition_text="x",
                               industry="ind-x", battleground_focus="f", base=base)

    result = arenas_io.find_by_industry("ind-x", base=base)
    assert set(result) == {"a1", "a3"}
    assert arenas_io.find_by_industry("ind-z", base=base) == []

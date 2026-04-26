from pathlib import Path
import pytest

from app.io import arenas as arenas_io


def test_write_definition_accepts_industry_and_battleground_focus(tmp_path):
    base = tmp_path / "arenas"
    base.mkdir()
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
    base = tmp_path / "arenas"
    base.mkdir()
    arenas_io.write_definition(slug="legacy", name="Legacy", definition_text="x", base=base)
    r = arenas_io.read_definition("legacy", base=base)
    assert r["frontmatter"].get("industry") is None or r["frontmatter"].get("industry") == ""

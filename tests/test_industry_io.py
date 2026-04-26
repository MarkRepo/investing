from pathlib import Path
import pytest
import yaml

from app import config as cfg
from app.io import industry as industry_io


def test_create_industry_builds_skeleton(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()

    industry_io.create_industry(
        slug="cn-cmp-material",
        name="中国化学机械抛光材料",
        scope="CMP 抛光液 + 抛光垫 + 调节液，国产替代主题",
        base=base,
    )

    slug_dir = base / "cn-cmp-material"
    assert slug_dir.is_dir()
    # 11 narrative .md (kebab-case filenames)
    for dim in cfg.INDUSTRY_DIMENSIONS:
        md_path = slug_dir / f"{dim.replace('_', '-')}.md"
        assert md_path.is_file(), f"missing {md_path}"
        assert md_path.read_text(encoding="utf-8").startswith("# ")  # skeleton header
    # meta.yaml
    meta = yaml.safe_load((slug_dir / "meta.yaml").read_text(encoding="utf-8"))
    assert meta["slug"] == "cn-cmp-material"
    assert meta["name"] == "中国化学机械抛光材料"
    assert meta["linked_arenas"] == []
    assert meta["linked_tickers"] == []
    # observations.jsonl created empty
    assert (slug_dir / "observations.jsonl").is_file()
    assert (slug_dir / "observations.jsonl").read_text() == ""
    # sources/ dir
    assert (slug_dir / "sources").is_dir()


def test_create_industry_rejects_invalid_slug(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    with pytest.raises(ValueError, match="slug"):
        industry_io.create_industry(slug="Bad Slug!", name="x", scope="y", base=base)
    with pytest.raises(ValueError, match="slug"):
        industry_io.create_industry(slug="", name="x", scope="y", base=base)


def test_create_industry_refuses_overwrite(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    with pytest.raises(FileExistsError):
        industry_io.create_industry(slug="x", name="X2", scope="y2", base=base)


def test_read_meta_write_meta_roundtrip(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    meta = industry_io.read_meta("x", base=base)
    meta["linked_tickers"] = [{"market": "SSE", "ticker": "600519", "name": "茅台"}]
    industry_io.write_meta("x", meta, base=base)
    meta2 = industry_io.read_meta("x", base=base)
    assert meta2["linked_tickers"][0]["ticker"] == "600519"

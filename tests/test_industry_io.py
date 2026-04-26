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


def test_append_observations_writes_jsonl(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    rows = [
        {"id": "o1", "dimension": "market_size", "field": "tam_global",
         "value": 33.8, "unit": "usd_bn", "timeframe": "2025",
         "time_type": "actual", "metric_type": "atomic",
         "source_id": "s1", "confidence": "high",
         "claim_text": "2025 TAM 33.8B", "evidence": "...",
         "extracted_by": "x", "extracted_at": "2026-04-26T00:00:00"},
    ]
    n = industry_io.append_observations("x", rows, base=base)
    assert n == 1

    read = industry_io.read_observations("x", base=base)
    assert len(read) == 1
    assert read[0]["id"] == "o1"
    assert read[0]["value"] == 33.8


def test_dedup_observations_keeps_highest_confidence():
    rows = [
        {"field": "tam_global", "timeframe": "2025", "source_id": "s1", "confidence": "low", "id": "a"},
        {"field": "tam_global", "timeframe": "2025", "source_id": "s1", "confidence": "high", "id": "b"},
        {"field": "tam_global", "timeframe": "2025", "source_id": "s2", "confidence": "low", "id": "c"},
    ]
    out = industry_io.dedup_observations(rows)
    ids = {r["id"] for r in out}
    # dedup on (field, timeframe, source_id); s1 keeps "high"=b, s2 keeps c
    assert ids == {"b", "c"}


def test_append_observations_is_additive(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    industry_io.append_observations("x", [{"id": "1", "field": "f"}], base=base)
    industry_io.append_observations("x", [{"id": "2", "field": "g"}], base=base)
    read = industry_io.read_observations("x", base=base)
    assert [r["id"] for r in read] == ["1", "2"]


def test_filter_observations_by_arena(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    industry_io.append_observations("x", [
        {"id": "a", "arena_refs": ["arena-1"]},
        {"id": "b", "arena_refs": ["arena-2"]},
        {"id": "c", "arena_refs": ["arena-1", "arena-2"]},
        {"id": "d", "arena_refs": []},
        {"id": "e"},  # no arena_refs field at all
    ], base=base)

    rows = industry_io.filter_observations_by_arena("x", "arena-1", base=base)
    assert {r["id"] for r in rows} == {"a", "c"}


def test_filter_observations_by_segment(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    industry_io.append_observations("x", [
        {"id": "a", "segment": "slurry"},
        {"id": "b", "segment": "pad"},
        {"id": "c", "segment": "slurry"},
        {"id": "d", "segment": None},
    ], base=base)
    rows = industry_io.filter_observations_by_segment("x", "slurry", base=base)
    assert {r["id"] for r in rows} == {"a", "c"}

from pathlib import Path
import pytest
import yaml

from app import config as cfg
from app.io import industry as industry_io


def test_create_industry_builds_skeleton(tmp_path):
    base = tmp_path

    industry_io.create_industry(
        slug="cn-cmp-material",
        name="中国化学机械抛光材料",
        scope="CMP 抛光液 + 抛光垫 + 调节液，国产替代主题",
        base=base,
    )

    slug_dir = base / "industries" / "cn-cmp-material"
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
    # observations.jsonl is prohibited endgame artifact; must NOT be created
    assert not (slug_dir / "observations.jsonl").exists()
    # sources/ dir
    assert (slug_dir / "sources").is_dir()


def test_create_industry_rejects_invalid_slug(tmp_path):
    base = tmp_path
    with pytest.raises(ValueError, match="slug"):
        industry_io.create_industry(slug="Bad Slug!", name="x", scope="y", base=base)
    with pytest.raises(ValueError, match="slug"):
        industry_io.create_industry(slug="", name="x", scope="y", base=base)


def test_create_industry_refuses_overwrite(tmp_path):
    base = tmp_path
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    with pytest.raises(FileExistsError):
        industry_io.create_industry(slug="x", name="X2", scope="y2", base=base)


def test_read_meta_write_meta_roundtrip(tmp_path):
    base = tmp_path
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    meta = industry_io.read_meta("x", base=base)
    meta["linked_tickers"] = [{"market": "SSE", "ticker": "600519", "name": "茅台"}]
    industry_io.write_meta("x", meta, base=base)
    meta2 = industry_io.read_meta("x", base=base)
    assert meta2["linked_tickers"][0]["ticker"] == "600519"


def test_append_observations_writes_jsonl(tmp_path):
    base = tmp_path
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
    base = tmp_path
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    industry_io.append_observations("x", [{"id": "1", "field": "f"}], base=base)
    industry_io.append_observations("x", [{"id": "2", "field": "g"}], base=base)
    read = industry_io.read_observations("x", base=base)
    assert [r["id"] for r in read] == ["1", "2"]


def test_filter_observations_by_arena(tmp_path):
    base = tmp_path
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
    base = tmp_path
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    industry_io.append_observations("x", [
        {"id": "a", "segment": "slurry"},
        {"id": "b", "segment": "pad"},
        {"id": "c", "segment": "slurry"},
        {"id": "d", "segment": None},
    ], base=base)
    rows = industry_io.filter_observations_by_segment("x", "slurry", base=base)
    assert {r["id"] for r in rows} == {"a", "c"}


def test_read_narrative_returns_skeleton_header(tmp_path):
    base = tmp_path
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    md = industry_io.read_narrative("x", "market_size", base=base)
    assert md.startswith("# 市场规模与增长")


def test_append_narrative_block_writes_source_section(tmp_path):
    base = tmp_path
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)

    block = "2025 年 TAM 达 33.8 亿美元。"
    industry_io.append_narrative_block(
        slug="x", dim="market_size", block=block,
        source_meta={"institution": "国金证券", "date": "2026-03-10",
                     "sha8": "abc12345", "source_id": "行研-国金证券-2026-03-10-abc12345"},
        base=base,
    )
    md = industry_io.read_narrative("x", "market_size", base=base)
    assert "### 来源 国金证券 2026-03-10 (sha8=abc12345)" in md
    assert "source_id: 行研-国金证券-2026-03-10-abc12345" in md
    assert "2025 年 TAM 达 33.8 亿美元" in md


def test_append_narrative_block_append_only(tmp_path):
    base = tmp_path
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    sm = {"institution": "A", "date": "2026-01-01", "sha8": "11111111", "source_id": "s1"}
    industry_io.append_narrative_block("x", "market_size", "first", sm, base=base)
    sm2 = {"institution": "B", "date": "2026-02-01", "sha8": "22222222", "source_id": "s2"}
    industry_io.append_narrative_block("x", "market_size", "second", sm2, base=base)
    md = industry_io.read_narrative("x", "market_size", base=base)
    idx_a = md.find("first")
    idx_b = md.find("second")
    assert 0 < idx_a < idx_b  # chronological order preserved


def test_append_narrative_block_rejects_unknown_dim(tmp_path):
    base = tmp_path
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    with pytest.raises(ValueError, match="unknown"):
        industry_io.append_narrative_block(
            "x", "bogus_dim", "x", {"institution":"a","date":"b","sha8":"c","source_id":"d"},
            base=base,
        )


def test_find_by_company_scans_linked_tickers(tmp_path):
    base = tmp_path
    industry_io.create_industry(slug="a", name="A", scope="", base=base)
    industry_io.create_industry(slug="b", name="B", scope="", base=base)
    # put ticker 600519 in industry A only
    meta_a = industry_io.read_meta("a", base=base)
    meta_a["linked_tickers"] = [
        {"market": "SSE", "ticker": "600519", "name": "茅台"},
        {"market": "US", "ticker": "AAPL", "name": "Apple"},
    ]
    industry_io.write_meta("a", meta_a, base=base)
    meta_b = industry_io.read_meta("b", base=base)
    meta_b["linked_tickers"] = [{"market": "SSE", "ticker": "000858", "name": "五粮液"}]
    industry_io.write_meta("b", meta_b, base=base)

    slugs = industry_io.find_by_company("600519", "SSE", base=base)
    assert slugs == ["a"]
    slugs2 = industry_io.find_by_company("unknown", "SSE", base=base)
    assert slugs2 == []


def test_find_by_arena_via_definition_frontmatter(tmp_path, monkeypatch):
    """find_by_arena reads arena.definition.md frontmatter.industry.
    Uses arenas.find_by_industry inverse lookup OR scans industry meta linked_arenas."""
    base = tmp_path
    industry_io.create_industry(slug="ind1", name="I1", scope="", base=base)
    meta = industry_io.read_meta("ind1", base=base)
    meta["linked_arenas"] = ["arena-x", "arena-y"]
    industry_io.write_meta("ind1", meta, base=base)

    assert industry_io.find_by_arena("arena-x", base=base) == "ind1"
    assert industry_io.find_by_arena("arena-z", base=base) is None


# --- Plan 5 T10: cross-source aggregation (spec §6.2) ------------------------


def _append_rows(base, slug, rows):
    industry_io.create_industry(slug=slug, name=slug, scope="", base=base)
    industry_io.append_observations(slug, rows, base=base)


def test_aggregate_numeric_group_computes_stats(tmp_path):
    """Two sources quoting same field+timeframe+unit → one numeric group with
    median/min/max/spread."""
    rows = [
        {"dimension": "market_size", "field": "tam_global", "timeframe": "2025",
         "unit": "亿美元", "value": 34.0, "metric_type": "atomic",
         "source_id": "src-huajing", "source_note": "华经"},
        {"dimension": "market_size", "field": "tam_global", "timeframe": "2025",
         "unit": "亿美元", "value": 29.6, "metric_type": "atomic",
         "source_id": "src-frost", "source_note": "弗若斯特沙利文"},
    ]
    _append_rows(tmp_path, "cn-cmp", rows)
    agg = industry_io.aggregate_observations("cn-cmp", base=tmp_path)
    assert len(agg["numeric"]) == 1
    g = agg["numeric"][0]
    assert g["field"] == "tam_global"
    assert g["n_rows"] == 2
    assert g["n_sources"] == 2
    assert g["min_value"] == 29.6
    assert g["max_value"] == 34.0
    # median of two values = mean
    assert abs(g["median"] - 31.8) < 1e-9
    # spread = (34 - 29.6) / 31.8 ≈ 0.138
    assert abs(g["spread"] - (4.4 / 31.8)) < 1e-9
    assert g["divergent"] is False


def test_aggregate_numeric_divergent_flag_above_threshold(tmp_path):
    """spread > 0.30 → divergent=True (red badge condition)."""
    rows = [
        {"dimension": "market_size", "field": "tam_china", "timeframe": "2025",
         "unit": "亿美元", "value": 10.0, "metric_type": "atomic",
         "source_id": "a", "source_note": "A"},
        {"dimension": "market_size", "field": "tam_china", "timeframe": "2025",
         "unit": "亿美元", "value": 25.0, "metric_type": "atomic",
         "source_id": "b", "source_note": "B"},
    ]
    _append_rows(tmp_path, "cn-cmp", rows)
    agg = industry_io.aggregate_observations("cn-cmp", base=tmp_path)
    g = agg["numeric"][0]
    assert g["divergent"] is True
    # spread = 15 / 17.5 ≈ 0.857 > 0.30
    assert g["spread"] > 0.30


def test_aggregate_segment_groups_by_segment(tmp_path):
    """metric_type='segment' rows split by segment, not merged."""
    rows = [
        {"dimension": "competition", "field": "share_by_player", "timeframe": "2024",
         "unit": "%", "value": 11.0, "metric_type": "segment", "segment": "SSE_688019",
         "source_id": "a", "source_note": "A"},
        {"dimension": "competition", "field": "share_by_player", "timeframe": "2024",
         "unit": "%", "value": 9.0, "metric_type": "segment", "segment": "SSE_688019",
         "source_id": "b", "source_note": "B"},
        {"dimension": "competition", "field": "share_by_player", "timeframe": "2024",
         "unit": "%", "value": 7.0, "metric_type": "segment", "segment": "SZSE_300054",
         "source_id": "a", "source_note": "A"},
    ]
    _append_rows(tmp_path, "cn-cmp", rows)
    agg = industry_io.aggregate_observations("cn-cmp", base=tmp_path)
    assert len(agg["segment"]) == 2
    by_seg = {g["segment"]: g for g in agg["segment"]}
    assert by_seg["SSE_688019"]["n_rows"] == 2
    assert by_seg["SSE_688019"]["n_sources"] == 2
    assert by_seg["SZSE_300054"]["n_rows"] == 1
    assert by_seg["SZSE_300054"]["n_sources"] == 1


def test_aggregate_enum_detects_divergence(tmp_path):
    """Two sources disagree on lifecycle.stage → consistent=False."""
    rows = [
        {"dimension": "lifecycle", "field": "stage", "timeframe": "2025",
         "value": "Growth", "metric_type": "atomic",
         "source_id": "a", "source_note": "A"},
        {"dimension": "lifecycle", "field": "stage", "timeframe": "2025",
         "value": "Shakeout", "metric_type": "atomic",
         "source_id": "b", "source_note": "B"},
        {"dimension": "lifecycle", "field": "stage", "timeframe": "2024",
         "value": "Growth", "metric_type": "atomic",
         "source_id": "a", "source_note": "A"},
    ]
    _append_rows(tmp_path, "cn-cmp", rows)
    agg = industry_io.aggregate_observations("cn-cmp", base=tmp_path)
    assert len(agg["enum"]) == 2
    by_tf = {g["timeframe"]: g for g in agg["enum"]}
    assert by_tf["2025"]["values"] == ["Growth", "Shakeout"]
    assert by_tf["2025"]["consistent"] is False
    assert by_tf["2024"]["consistent"] is True


def test_aggregate_single_source_group_has_zero_spread(tmp_path):
    """Single-source group: spread=0, divergent=False, n_sources=1."""
    rows = [
        {"dimension": "market_size", "field": "tam_global", "timeframe": "2025",
         "unit": "亿美元", "value": 34.0, "metric_type": "atomic",
         "source_id": "sole", "source_note": "Sole"},
    ]
    _append_rows(tmp_path, "cn-cmp", rows)
    agg = industry_io.aggregate_observations("cn-cmp", base=tmp_path)
    g = agg["numeric"][0]
    assert g["n_sources"] == 1
    assert g["spread"] == 0.0
    assert g["divergent"] is False


def test_aggregate_skips_rows_with_null_value_or_missing_dim(tmp_path):
    """Rows with value=None or missing dimension/field are excluded from all
    buckets (they're narrative-only or schema-invalid)."""
    rows = [
        {"dimension": "market_size", "field": "tam_global", "timeframe": "2025",
         "unit": "亿美元", "value": None, "claim_text": "unstructured note",
         "source_id": "a", "source_note": "A"},
        {"dimension": None, "field": "tam_global", "timeframe": "2025",
         "value": 34.0, "source_id": "b", "source_note": "B"},
    ]
    _append_rows(tmp_path, "cn-cmp", rows)
    agg = industry_io.aggregate_observations("cn-cmp", base=tmp_path)
    assert agg["numeric"] == []
    assert agg["segment"] == []
    assert agg["enum"] == []

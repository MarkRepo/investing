from pathlib import Path

from scripts import ingest_aggregate as agg


def test_route_key_facts_splits_by_target_layer():
    key_facts = [
        {"idx": 1, "target_layer": "industry", "dimension_hint": "market_size",
         "target_refs": {"industry_slug": "cn-cmp-material"}},
        {"idx": 2, "target_layer": "industry", "dimension_hint": "competition",
         "target_refs": {"industry_slug": "cn-cmp-material"}},
        {"idx": 3, "target_layer": "arena", "dimension_hint": "participants",
         "target_refs": {"arena_slug": "cn-cmp-slurry-domestic-substitution"}},
        {"idx": 4, "target_layer": "company", "dimension_hint": "moat",
         "target_refs": {"ticker": "688019", "market": "SSE"}},
        {"idx": 5, "target_layer": "cross", "dimension_hint": "competition",
         "field_hint": "share_by_player",
         "target_refs": {"industry_slug": "cn-cmp-material", "ticker": "688019"}},
    ]
    buckets = agg.route_key_facts(key_facts)
    assert [f["idx"] for f in buckets["industry"]] == [1, 2, 5]  # cross goes to industry by default
    assert [f["idx"] for f in buckets["arena"]] == [3]
    assert [f["idx"] for f in buckets["company"]] == [4]


def test_route_key_facts_drops_malformed():
    key_facts = [
        {"idx": 1, "target_layer": "industry"},  # no target_refs
        {"idx": 2, "target_layer": "bogus", "target_refs": {"industry_slug": "x"}},
    ]
    buckets = agg.route_key_facts(key_facts)
    assert sum(len(v) for v in buckets.values()) == 0


def test_route_key_facts_cross_layer_also_tagged_as_company():
    """Cross-layer facts (target_layer=cross) with a ticker should ALSO appear
    in the company bucket (so company page shows the share_by_player claim)."""
    key_facts = [
        {"idx": 5, "target_layer": "cross", "dimension_hint": "competition",
         "field_hint": "share_by_player",
         "target_refs": {"industry_slug": "i", "ticker": "688019", "market": "SSE"}},
    ]
    buckets = agg.route_key_facts(key_facts)
    assert any(f["idx"] == 5 for f in buckets["industry"])
    assert any(f["idx"] == 5 for f in buckets["company"])


def test_fact_to_observation_maps_standard_fields():
    fact = {
        "idx": 1, "fact_text": "2025 TAM 33.8B USD",
        "evidence_quote": "...原文 ...",
        "target_layer": "industry",
        "target_refs": {"industry_slug": "cn-cmp-material"},
        "dimension_hint": "market_size",
        "field_hint": "tam_global",
        "value_numeric": 33.8,
        "unit": "usd_bn",
        "timeframe": "2025",
        "time_type": "actual",
        "metric_type": "atomic",
        "arena_refs": [],
        "confidence": "high",
    }
    source_meta = {
        "source_id": "行研-国金证券-2026-03-10-abc12345",
        "institution": "国金证券",
        "date": "2026-03-10",
        "sha8": "abc12345",
        "source_file": "cmp.pdf",
        "source_note": "引用 Market Growth Reports",
    }
    row = agg.fact_to_observation(fact, source_meta, extracted_by="claude-opus-4-7",
                                  extracted_at="2026-04-26T00:00:00Z")
    assert row["dimension"] == "market_size"
    assert row["field"] == "tam_global"
    assert row["value"] == 33.8
    assert row["unit"] == "usd_bn"
    assert row["timeframe"] == "2025"
    assert row["source_id"] == "行研-国金证券-2026-03-10-abc12345"
    assert row["confidence"] == "high"
    assert row["evidence"].startswith("...原文")
    assert row["id"].startswith("cmp-")  # ID convention: {industry-prefix}-{nnnn}


def test_write_industry_observations_roundtrip(tmp_path):
    from app.io import industry as industry_io
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="cn-cmp-material", name="CMP", scope="", base=base)

    facts = [{
        "idx": 1, "fact_text": "TAM 33.8B",
        "evidence_quote": "原文",
        "target_layer": "industry",
        "target_refs": {"industry_slug": "cn-cmp-material"},
        "dimension_hint": "market_size",
        "field_hint": "tam_global",
        "value_numeric": 33.8, "unit": "usd_bn",
        "timeframe": "2025", "time_type": "actual",
        "metric_type": "atomic",
        "confidence": "high",
    }]
    source_meta = {"source_id": "s1", "institution": "X", "date": "2026-01-01",
                   "sha8": "abcd1234", "source_file": "x.pdf"}
    n = agg.write_industry_observations(
        facts, source_meta,
        extracted_by="t", extracted_at="2026-04-26T00:00:00Z",
        base=base,
    )
    assert n == 1
    rows = industry_io.read_observations("cn-cmp-material", base=base)
    assert len(rows) == 1
    assert rows[0]["field"] == "tam_global"
    assert rows[0]["value"] == 33.8

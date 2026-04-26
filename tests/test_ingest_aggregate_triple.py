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

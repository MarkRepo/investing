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


def test_write_industry_narrative_appends_block(tmp_path):
    from app.io import industry as industry_io
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="", base=base)

    narratives = {"x": {"market_size": "TAM 34B, CAGR 9%", "technology": "铜抛光液演进"}}
    source_meta = {"source_id": "s1", "institution": "国金", "date": "2026-03-10",
                   "sha8": "abcd1234"}
    agg.write_industry_narrative(narratives, source_meta, base=base)

    md = industry_io.read_narrative("x", "market_size", base=base)
    assert "TAM 34B" in md
    assert "来源 国金 2026-03-10" in md

    md_t = industry_io.read_narrative("x", "technology", base=base)
    assert "铜抛光液" in md_t


def test_write_arena_narrative_appends_block(tmp_path):
    from app.io import arenas as arenas_io
    base = tmp_path / "arenas"
    base.mkdir()
    arenas_io.write_definition(slug="a1", name="A1", definition_text="x",
                                industry="i", battleground_focus="f", base=base)
    narratives = {"a1": {"participants": "安集 vs Dupont"}}
    source_meta = {"source_id": "s1", "institution": "X", "date": "2026-01-01",
                   "sha8": "abcd1234"}
    agg.write_arena_narrative(narratives, source_meta, base=base)
    md = arenas_io.read_narrative("a1", "participants", base=base)
    assert "安集 vs Dupont" in md


def test_write_company_narrative_appends_block(tmp_path):
    from app.io import company as company_io
    base = tmp_path / "companies"
    base.mkdir()
    company_io.create_company(ticker="600519", market="SSE", name="Moutai",
                              industry_slugs=[], base=base)
    narratives = {"SSE_600519": {"moat": "品牌+渠道+产能"}}
    source_meta = {"source_id": "年报-2024-deadbeef", "institution": "年报",
                   "date": "2024-12-31", "sha8": "deadbeef"}
    agg.write_company_narrative(narratives, source_meta, base=base)
    md = company_io.read_narrative("600519", "SSE", "moat", base=base)
    assert "品牌+渠道" in md


def test_write_narrative_skips_empty_string(tmp_path):
    """Empty narrative dims must not trigger an 'empty block' append —
    empty str/None means 'dim not covered by this report'."""
    from app.io import industry as industry_io
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="", base=base)
    narratives = {"x": {"market_size": "", "technology": None, "lifecycle": "Mature"}}
    source_meta = {"source_id": "s1", "institution": "X", "date": "2026-01-01",
                   "sha8": "abcd1234"}
    agg.write_industry_narrative(narratives, source_meta, base=base)
    md_m = industry_io.read_narrative("x", "market_size", base=base)
    md_t = industry_io.read_narrative("x", "technology", base=base)
    md_l = industry_io.read_narrative("x", "lifecycle", base=base)
    # skeleton only for empty; new block only for lifecycle
    assert "来源" not in md_m
    assert "来源" not in md_t
    assert "Mature" in md_l


def test_facts_to_claims_converts_fields():
    facts = [{
        "idx": 1,
        "fact_text": "FY2025 营收 1,688 亿元，同比 +14.3%",
        "evidence_quote": "...",
        "target_layer": "company",
        "target_refs": {"ticker": "600519", "market": "SSE"},
        "dimension_hint": "financial_profile",
        "subject_tag_hint": "revenue_growth",
        "company_dimension_hint": "financial_profile",
        "timeframe": "FY2025",
        "confidence": "high",
        "arena_refs": ["arena-x"],
    }]
    claims = agg.facts_to_claims(facts)
    assert len(claims) == 1
    c = claims[0]
    assert c["claim_text"] == "FY2025 营收 1,688 亿元，同比 +14.3%"
    assert c["subject_tag"] == "revenue_growth"
    assert c["company_dimension_hint"] == "financial_profile"
    assert c["arena_refs"] == ["arena-x"]
    # evidence must be [{text, type}] (claim schema)
    assert isinstance(c["evidence"], list)
    assert c["evidence"][0]["text"].startswith("...") or c["evidence"][0]["text"] == "..."


def test_facts_to_claims_groups_by_company():
    facts = [
        {"idx": 1, "target_layer": "company",
         "target_refs": {"ticker": "600519", "market": "SSE"},
         "fact_text": "A", "evidence_quote": "ea",
         "subject_tag_hint": "tag1", "company_dimension_hint": "moat"},
        {"idx": 2, "target_layer": "company",
         "target_refs": {"ticker": "000858", "market": "SSE"},
         "fact_text": "B", "evidence_quote": "eb",
         "subject_tag_hint": "tag1", "company_dimension_hint": "moat"},
    ]
    groups = agg.group_company_facts(facts)
    assert set(groups.keys()) == {("600519", "SSE"), ("000858", "SSE")}
    assert len(groups[("600519", "SSE")]) == 1
    assert len(groups[("000858", "SSE")]) == 1


def test_e2e_industry_digest_full_pipeline(tmp_path):
    """Simulate the full Plan 3 workflow (except the LLM call):
       1. create industry via autobuild helper
       2. receive digest JSON
       3. route_key_facts → three buckets
       4. write each bucket to the right layer via helpers
       5. assert disk state"""
    from app.io import industry as industry_io
    from app.io import arenas as arenas_io
    from app.io import company as company_io
    from app.io import figure_contexts as fc_io

    # Each IO module has a different convention for what "base" means:
    # - industry_io: base IS the industries dir
    # - arenas_io: base is project root, creates base/"arenas"/slug/
    # - company_io: base is project root, creates base/"companies"/market_ticker/
    # - ensure_company_exists(base=X): X is treated as the companies dir itself
    #   (internally passes X.parent to create_company, which appends "companies/")

    ind_base = tmp_path / "industries"
    ind_base.mkdir()

    # For ensure_company_exists: pass the companies dir itself (T16 convention)
    comp_dir_for_ensure = tmp_path / "companies"
    comp_dir_for_ensure.mkdir()

    # For write_company_narrative and read_narrative: pass project root
    project_root = tmp_path

    # For bootstrap_arena and read_definition: pass project root (arenas_io convention)

    # Step 1: autobuild industry
    agg.ensure_industry_exists(
        slug="cn-cmp-material", name="CMP", scope="半导体抛光",
        base=ind_base,
    )

    # Step 2: simulated digest JSON
    digest = {
        "key_facts": [
            {"idx": 1, "target_layer": "industry",
             "target_refs": {"industry_slug": "cn-cmp-material"},
             "dimension_hint": "market_size", "field_hint": "tam_global",
             "value_numeric": 33.8, "unit": "usd_bn",
             "timeframe": "2025", "time_type": "actual",
             "metric_type": "atomic", "confidence": "high",
             "fact_text": "2025 TAM 33.8B USD",
             "evidence_quote": "...原文引用..."},
            {"idx": 2, "target_layer": "company",
             "target_refs": {"ticker": "688019", "market": "SSE"},
             "dimension_hint": "moat",
             "subject_tag_hint": "moat", "company_dimension_hint": "moat",
             "fact_text": "安集 CMP 抛光液技术领先",
             "evidence_quote": "原文 X",
             "confidence": "high"},
        ],
        "narratives": {
            "industry": {"cn-cmp-material": {
                "market_size": "2025 年全球 CMP 市场 ~34 亿美元，CAGR 9%。"
            }},
            "arena": {},
            "company": {"SSE_688019": {
                "moat": "安集的核心护城河是 CMP 抛光液的多年工艺积累。"
            }},
        },
        "proposed_arenas": [
            {"tentative_slug": "cn-cmp-slurry-domestic-substitution",
             "battleground_focus": "国产 CMP 抛光液挑战 Dupont",
             "tentative_participants": [
                 {"name": "安集", "role": "challenger"},
                 {"name": "Dupont", "role": "incumbent"},
             ],
             "parent_industry_slug": "cn-cmp-material"},
        ],
    }

    source_meta = {"source_id": "行研-国金-2026-03-10-abcd1234",
                   "institution": "国金", "date": "2026-03-10",
                   "sha8": "abcd1234", "source_file": "cmp.pdf"}

    # Step 3: route
    buckets = agg.route_key_facts(digest["key_facts"])

    # Step 4a: write observations
    n_obs = agg.write_industry_observations(
        buckets["industry"], source_meta,
        extracted_by="t", extracted_at="2026-04-26T00:00:00Z",
        base=ind_base,
    )
    assert n_obs == 1

    # Step 4b: write industry narrative
    # Note: digest shape is narratives.industry.{slug}.{dim}; our writer expects
    # {slug:{dim:block}} so pass the inner dict directly.
    n_nar = agg.write_industry_narrative(
        digest["narratives"]["industry"],
        source_meta, base=ind_base,
    )
    assert n_nar == 1

    # Step 4c: autobuild company + write company narrative
    # ensure_company_exists expects the companies dir (T16 convention),
    # while write_company_narrative expects project root (company_io convention).
    agg.ensure_company_exists(
        ticker="688019", market="SSE", name="安集科技",
        industry_slugs=["cn-cmp-material"], currency="CNY",
        base=comp_dir_for_ensure,
    )
    n_cn = agg.write_company_narrative(
        digest["narratives"]["company"],
        source_meta, base=project_root,
    )
    assert n_cn == 1

    # Step 4d: bootstrap proposed arena (simulate user approval)
    proposals = agg.propose_arena_bootstrap(digest["proposed_arenas"])
    assert len(proposals) == 1
    # bootstrap_arena passes base directly to arenas_io.write_definition,
    # which prepends "arenas/" — so pass project root, not an arenas subdir.
    agg.bootstrap_arena(proposals[0], base=project_root)

    # Assertions — disk state
    assert len(industry_io.read_observations("cn-cmp-material", base=ind_base)) == 1
    assert "CAGR 9%" in industry_io.read_narrative(
        "cn-cmp-material", "market_size", base=ind_base)
    assert "护城河" in company_io.read_narrative("688019", "SSE", "moat", base=project_root)
    arena_def = arenas_io.read_definition("cn-cmp-slurry-domestic-substitution",
                                          base=project_root)
    assert arena_def["frontmatter"]["industry"] == "cn-cmp-material"
    assert arena_def["frontmatter"]["battleground_focus"] == "国产 CMP 抛光液挑战 Dupont"


def test_write_figure_contexts_attaches_source_id(tmp_path):
    from app.io import industry as industry_io
    from app.io import figure_contexts as fc_io
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="cn-cmp-material", name="X", scope="", base=base)

    preprocess_contexts = [
        {"id": "fig-001", "page": None,
         "caption": "图表1: 全球市场规模",
         "surrounding_text": "2025 市场规模 33.8 亿美元",
         "section_name": "market_size"},
    ]
    source_meta = {"source_id": "行研-X-2026-03-10-abcd1234", "institution": "X",
                   "date": "2026-03-10", "sha8": "abcd1234"}
    n = agg.write_figure_contexts(
        slug="cn-cmp-material",
        contexts=preprocess_contexts,
        source_meta=source_meta,
        base=base,
    )
    assert n == 1
    rows = fc_io.read_figure_contexts("cn-cmp-material", base=base)
    assert rows[0]["source_id"] == "行研-X-2026-03-10-abcd1234"
    assert rows[0]["caption"].startswith("图表1")

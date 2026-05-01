"""Tests for app/io/investment_lens.py — fetcher unit tests using tmp_path fixtures."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.io.claim_registry import ClaimRegistry
from app.io.investment_lens import (
    BundleExcerpt,
    ClaimCard,
    LensMaterial,
    NarrativeExcerpt,
    bundles_for_scope,
    fetch_lens_material,
    load_bundle,
)


# ---------------------------------------------------------------------------
# Mini fixture builder
# ---------------------------------------------------------------------------

MINI_BUNDLE = {
    "bundle_version": "v2-phase1",
    "synthesis": {
        "one_sentence": "Test industry thesis sentence.",
        "cannot_conclude": ["Cannot conclude X.", "Cannot conclude Y."],
        "investment_questions": ["Question A?", "Question B?"],
        "what_we_know": ["We know alpha."],
        "what_is_plausible": ["Beta is plausible."],
        "what_needs_verification": ["Verify gamma."],
        "evidence_strength": "medium",
    },
    "insight_blocks": [
        {
            "id": "ib-001",
            "title": "Market size insight",
            "summary": "Global market size is X.",
            "archive_routing_hints": {
                "dimension_hint": "market_size",
                "target_layer": "industry",
                "entity_hints": [],
            },
            "evidence_strength": "medium_high",
            "block_type": "market_size",
            "source_page_range": "1",
            "reasoning_chain": [],
            "block_relations": [],
        },
        {
            "id": "ib-002",
            "title": "Competition insight",
            "summary": "Market is concentrated.",
            "archive_routing_hints": {
                "dimension_hint": "competition",
                "target_layer": "industry",
                "entity_hints": [],
            },
            "evidence_strength": "medium",
            "block_type": "competition",
            "source_page_range": "2",
            "reasoning_chain": [],
            "block_relations": [],
        },
        {
            "id": "ib-003",
            "title": "Technology insight",
            "summary": "Key tech is REBCO.",
            "archive_routing_hints": {
                "dimension_hint": "technology",
                "target_layer": "industry",
                "entity_hints": [],
            },
            "evidence_strength": "medium",
            "block_type": "technology",
            "source_page_range": "3",
            "reasoning_chain": [],
            "block_relations": [],
        },
    ],
    "atomic_facts": [
        {
            "fact_id": "fact-001",
            "fact_text": "Market fact alpha.",
            "linked_block_id": "ib-001",
            "confidence": "high",
            "evidence_quote": "quote alpha",
            "source_page": 1,
        },
        {
            "fact_id": "fact-002",
            "fact_text": "Competition fact beta.",
            "linked_block_id": "ib-002",
            "confidence": "medium",
            "evidence_quote": "quote beta",
            "source_page": 2,
        },
    ],
    "stage_gates": [
        {
            "id": "sg-001",
            "title": "First stage gate",
            "gate_type": "demand_validation",
            "crossed": False,
            "linked_block_ids": ["ib-001"],
            "what_would_cross_it": ["Criterion A", "Criterion B"],
        },
    ],
    "arena_candidates": [
        {
            "candidate_id": "ac-001",
            "tentative_slug": "test-arena",
            "name": "Test Arena",
            "battleground_focus": "Focus on arena battleground.",
            "participant_tickers": ["SSE_123456"],
            "confidence": "medium",
            "linked_block_ids": [],
            "verification_questions": [],
            "parent_industry_slug": "test-industry",
        },
    ],
    "company_candidates": [
        {
            "ticker": "603011",
            "market": "SSE",
            "name": "Test Co A",
            "exposure_type": "direct_supplier",
            "confidence": "medium",
            "source_block_ids": ["ib-001"],
            "verification_questions": ["Q1?", "Q2?"],
        },
        {
            "ticker": "600363",
            "market": "SSE",
            "name": "Test Co B",
            "exposure_type": "upstream",
            "confidence": "low",
            "source_block_ids": ["ib-002"],
            "verification_questions": ["QA?"],
        },
    ],
    "claim_candidates": [],
}


def _build_fixture(tmp_path: Path) -> tuple[Path, ClaimRegistry]:
    """Build a minimal fixture tree under tmp_path."""
    base = tmp_path

    # Bundle registry
    registry_path = base / "data" / "bundle_registry.jsonl"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "source_id": "行研-test-2025-01-01-abcd1234",
        "sha8": "abcd1234",
        "source_type": "industry_report",
        "institution": "Test Institution",
        "publish_date": "2025-01-01",
        "bundle_path": "industries/test-industry/bundles/abcd1234.json",
        "source_file_path": "industries/test-industry/sources/test.pdf",
        "ingested_at": "2026-01-01T00:00:00+00:00",
        "touched": {
            "industries": ["test-industry"],
            "arenas": ["test-arena"],
            "companies": ["SSE_603011", "SSE_600363"],
        },
    }
    registry_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")

    # Bundle JSON
    bundle_path = base / "industries" / "test-industry" / "bundles" / "abcd1234.json"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps(MINI_BUNDLE), encoding="utf-8")

    # Claims
    claims_dir = base / "data" / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)

    industry_claims = [
        {
            "claim_id": "clm-industry-0001",
            "claim_text": "Thesis claim for test.",
            "claim_type": "thesis",
            "dimension_hint": "technology",
            "scope_type": "industry",
            "scope_ref": "test-industry",
            "status": "active",
            "confidence": "medium_high",
            "as_of": "2025-01-01",
            "supporting_evidence": [
                {"source_id": "行研-test-2025-01-01-abcd1234", "direction": "supports", "weight": 1.0, "block_ids": [], "fact_ids": [], "added_at": "2026-01-01T00:00:00+00:00", "added_by": "ingest"}
            ],
            "related_claims": [],
            "state_log": [],
            "review_by": None,
            "user_override": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "last_updated": "2026-01-01T00:00:00+00:00",
            "schema_version": "phase2-v1",
        },
        {
            "claim_id": "clm-industry-0002",
            "claim_text": "Market size claim.",
            "claim_type": "judgment",
            "dimension_hint": "market_size",
            "scope_type": "industry",
            "scope_ref": "test-industry",
            "status": "active",
            "confidence": "medium",
            "as_of": "2025-01-01",
            "supporting_evidence": [
                {"source_id": "行研-test-2025-01-01-abcd1234", "direction": "supports", "weight": 1.0, "block_ids": [], "fact_ids": [], "added_at": "2026-01-01T00:00:00+00:00", "added_by": "ingest"},
                {"source_id": "行研-test-2025-01-01-abcd1234", "direction": "neutral", "weight": 0.5, "block_ids": [], "fact_ids": [], "added_at": "2026-01-01T00:00:00+00:00", "added_by": "ingest"},
            ],
            "related_claims": [],
            "state_log": [],
            "review_by": None,
            "user_override": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "last_updated": "2026-01-01T00:00:00+00:00",
            "schema_version": "phase2-v1",
        },
        {
            "claim_id": "clm-industry-0003",
            "claim_text": "Risk claim.",
            "claim_type": "risk",
            "dimension_hint": "risks",
            "scope_type": "industry",
            "scope_ref": "test-industry",
            "status": "active",
            "confidence": "medium",
            "as_of": "2025-01-01",
            "supporting_evidence": [],
            "related_claims": [],
            "state_log": [],
            "review_by": None,
            "user_override": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "last_updated": "2026-01-01T00:00:00+00:00",
            "schema_version": "phase2-v1",
        },
    ]
    (claims_dir / "industries.jsonl").write_text(
        "\n".join(json.dumps(c) for c in industry_claims) + "\n", encoding="utf-8"
    )

    arena_claims = [
        {
            "claim_id": "clm-arena-0001",
            "claim_text": "Arena judgment claim.",
            "claim_type": "judgment",
            "dimension_hint": "technology",
            "scope_type": "arena",
            "scope_ref": "test-arena",
            "status": "active",
            "confidence": "high",
            "as_of": "2025-01-01",
            "supporting_evidence": [
                {"source_id": "行研-test-2025-01-01-abcd1234", "direction": "supports", "weight": 1.0, "block_ids": [], "fact_ids": [], "added_at": "2026-01-01T00:00:00+00:00", "added_by": "ingest"}
            ],
            "related_claims": [],
            "state_log": [],
            "review_by": None,
            "user_override": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "last_updated": "2026-01-01T00:00:00+00:00",
            "schema_version": "phase2-v1",
        },
    ]
    (claims_dir / "arenas.jsonl").write_text(
        "\n".join(json.dumps(c) for c in arena_claims) + "\n", encoding="utf-8"
    )

    company_claims = [
        {
            "claim_id": "clm-company-0001",
            "claim_text": "Company thesis claim.",
            "claim_type": "thesis",
            "dimension_hint": "business_model",
            "scope_type": "company",
            "scope_ref": "SSE_603011",
            "status": "active",
            "confidence": "medium",
            "as_of": "2025-01-01",
            "supporting_evidence": [],
            "related_claims": [],
            "state_log": [],
            "review_by": None,
            "user_override": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "last_updated": "2026-01-01T00:00:00+00:00",
            "schema_version": "phase2-v1",
        },
    ]
    (claims_dir / "companies.jsonl").write_text(
        "\n".join(json.dumps(c) for c in company_claims) + "\n", encoding="utf-8"
    )
    (claims_dir / "cross_cutting.jsonl").write_text("", encoding="utf-8")
    (claims_dir / ".counters.json").write_text(
        json.dumps({"industry": 3, "arena": 1, "company": 1}), encoding="utf-8"
    )

    # Archive narrative files
    # Industry: market_size.md  (for "demand" field)
    ind_dir = base / "industries" / "test-industry"
    ind_dir.mkdir(parents=True, exist_ok=True)
    (ind_dir / "market-size.md").write_text(
        "# Market Size\n\n### 来源 test-section\n\nSome content here.\n\n### 另一段\n\nMore content.\n",
        encoding="utf-8",
    )
    # Industry: drivers.md (for "catalysts_timeline" field)
    (ind_dir / "drivers.md").write_text(
        "# Drivers\n\n### 来源 drivers-section\n\nDrivers content.\n",
        encoding="utf-8",
    )

    # Arena: trajectory.md (for "stage_gates" and "inflection_points")
    arena_dir = base / "arenas" / "test-arena"
    arena_dir.mkdir(parents=True, exist_ok=True)
    (arena_dir / "trajectory.md").write_text(
        "# Trajectory\n\n### 来源 traj-section\n\nTrajectory content.\n",
        encoding="utf-8",
    )

    # Company: narrative files
    company_dir = base / "companies" / "SSE_603011" / "narratives"
    company_dir.mkdir(parents=True, exist_ok=True)
    (company_dir / "business-model.md").write_text(
        "# Business Model\n\n### 来源 biz-section\n\nBusiness model content.\n",
        encoding="utf-8",
    )
    (company_dir / "moat.md").write_text(
        "# Moat\n\n### 来源 moat-section\n\nMoat content.\n",
        encoding="utf-8",
    )

    registry = ClaimRegistry(base=base / "data")
    return base, registry


# ---------------------------------------------------------------------------
# bundles_for_scope
# ---------------------------------------------------------------------------

def test_bundles_for_scope_found(tmp_path):
    base, _ = _build_fixture(tmp_path)
    entries = bundles_for_scope("industry", "test-industry", base)
    assert len(entries) == 1
    assert entries[0]["sha8"] == "abcd1234"


def test_bundles_for_scope_not_found(tmp_path):
    base, _ = _build_fixture(tmp_path)
    entries = bundles_for_scope("industry", "nonexistent-industry", base)
    assert entries == []


def test_bundles_for_scope_arena(tmp_path):
    base, _ = _build_fixture(tmp_path)
    entries = bundles_for_scope("arena", "test-arena", base)
    assert len(entries) == 1


def test_bundles_for_scope_company(tmp_path):
    base, _ = _build_fixture(tmp_path)
    entries = bundles_for_scope("company", "SSE_603011", base)
    assert len(entries) == 1


def test_load_bundle(tmp_path):
    base, _ = _build_fixture(tmp_path)
    entries = bundles_for_scope("industry", "test-industry", base)
    bundle = load_bundle(entries[0], base)
    assert "synthesis" in bundle
    assert bundle["synthesis"]["one_sentence"] == "Test industry thesis sentence."


# ---------------------------------------------------------------------------
# Industry 8 dims — fetch_lens_material
# ---------------------------------------------------------------------------

def test_industry_thesis(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("industry", "test-industry", "thesis", registry=registry, base=base)
    assert isinstance(mat, LensMaterial)
    # should have synthesis.one_sentence as bundle excerpt
    assert len(mat.bundle_excerpts) >= 1
    assert "thesis sentence" in mat.bundle_excerpts[0].text.lower()
    # should have thesis claims
    assert len(mat.claims) >= 1
    assert mat.claims[0].claim_type == "thesis"


def test_industry_demand(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("industry", "test-industry", "demand", registry=registry, base=base)
    # insight_blocks with market_size + atomic_facts pointing to market_size block
    assert len(mat.bundle_excerpts) >= 1
    assert len(mat.claims) >= 1  # market_size claim
    assert len(mat.narrative_excerpts) == 1
    assert mat.narrative_excerpts[0].dimension == "market_size"
    assert mat.narrative_excerpts[0].headline_count >= 1


def test_industry_supply_competition(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("industry", "test-industry", "supply_competition", registry=registry, base=base)
    # competition insight block present
    assert len(mat.bundle_excerpts) >= 1


def test_industry_profit_pool(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("industry", "test-industry", "profit_pool", registry=registry, base=base)
    assert isinstance(mat, LensMaterial)
    assert mat.scope_type == "industry"


def test_industry_unit_economics(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("industry", "test-industry", "unit_economics", registry=registry, base=base)
    assert isinstance(mat, LensMaterial)


def test_industry_stage_gates(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("industry", "test-industry", "stage_gates", registry=registry, base=base)
    assert len(mat.bundle_excerpts) >= 1
    assert "First stage gate" in mat.bundle_excerpts[0].text


def test_industry_catalysts_timeline(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("industry", "test-industry", "catalysts_timeline", registry=registry, base=base)
    # technology insight block should be picked up
    assert len(mat.bundle_excerpts) >= 1
    assert len(mat.narrative_excerpts) == 1
    assert mat.narrative_excerpts[0].dimension == "drivers"


def test_industry_risks_disconfirming_evidence(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("industry", "test-industry", "risks_disconfirming_evidence", registry=registry, base=base)
    # synthesis.cannot_conclude should produce 2 excerpts
    assert len(mat.bundle_excerpts) >= 2
    # risk claim
    assert any(c.claim_type == "risk" for c in mat.claims)


# ---------------------------------------------------------------------------
# Arena 7 dims — fetch_lens_material
# ---------------------------------------------------------------------------

def test_arena_battlefield_definition(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("arena", "test-arena", "battlefield_definition", registry=registry, base=base)
    # arena_candidates[slug=?] should find ac-001 with tentative_slug=test-arena
    assert len(mat.bundle_excerpts) >= 1
    assert "Focus on arena battleground" in mat.bundle_excerpts[0].text


def test_arena_players_positions(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("arena", "test-arena", "players_positions", registry=registry, base=base)
    assert isinstance(mat, LensMaterial)


def test_arena_winning_variables(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("arena", "test-arena", "winning_variables", registry=registry, base=base)
    # technology insight block matches
    assert len(mat.bundle_excerpts) >= 1


def test_arena_evidence_scoreboard(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("arena", "test-arena", "evidence_scoreboard", registry=registry, base=base)
    # atomic_facts with competition/participants blocks (none in mini fixture for this exact dim)
    # but claims with judgment should appear
    assert any(c.claim_type == "judgment" for c in mat.claims)


def test_arena_stage_gates(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("arena", "test-arena", "stage_gates", registry=registry, base=base)
    assert len(mat.bundle_excerpts) >= 1
    assert len(mat.narrative_excerpts) == 1


def test_arena_inflection_points(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("arena", "test-arena", "inflection_points", registry=registry, base=base)
    assert isinstance(mat, LensMaterial)
    assert len(mat.narrative_excerpts) == 1


def test_arena_company_implications(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("arena", "test-arena", "company_implications", registry=registry, base=base)
    # company_candidates[] — all 2 candidates
    assert len(mat.bundle_excerpts) == 2


# ---------------------------------------------------------------------------
# Company 9 dims — fetch_lens_material
# ---------------------------------------------------------------------------

def test_company_business_exposure(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("company", "SSE_603011", "business_exposure", registry=registry, base=base)
    # company_candidates[ticker=?] — SSE_603011
    assert len(mat.bundle_excerpts) >= 1
    assert "direct_supplier" in mat.bundle_excerpts[0].text
    assert len(mat.narrative_excerpts) == 1
    assert mat.narrative_excerpts[0].dimension == "business_model"


def test_company_thesis_fit(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("company", "SSE_603011", "thesis_fit", registry=registry, base=base)
    # synthesis.one_sentence + company_candidates[ticker=?]
    assert len(mat.bundle_excerpts) >= 2
    assert any(c.claim_type == "thesis" for c in mat.claims)


def test_company_moat_execution(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("company", "SSE_603011", "moat_execution", registry=registry, base=base)
    assert isinstance(mat, LensMaterial)
    assert len(mat.narrative_excerpts) == 1
    assert mat.narrative_excerpts[0].dimension == "moat"


def test_company_financial_quality(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("company", "SSE_603011", "financial_quality", registry=registry, base=base)
    assert isinstance(mat, LensMaterial)


def test_company_growth_drivers(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("company", "SSE_603011", "growth_drivers", registry=registry, base=base)
    assert isinstance(mat, LensMaterial)


def test_company_stage_gate_status(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("company", "SSE_603011", "stage_gate_status", registry=registry, base=base)
    # stage_gates[]
    assert len(mat.bundle_excerpts) >= 1


def test_company_valuation_expectations(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("company", "SSE_603011", "valuation_expectations", registry=registry, base=base)
    assert isinstance(mat, LensMaterial)


def test_company_catalysts_risks(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("company", "SSE_603011", "catalysts_risks", registry=registry, base=base)
    assert isinstance(mat, LensMaterial)


def test_company_open_questions(tmp_path):
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("company", "SSE_603011", "open_questions", registry=registry, base=base)
    # synthesis.investment_questions → 2 items
    assert len(mat.bundle_excerpts) >= 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_bundles(tmp_path):
    """bundles_for_scope returns empty → LensMaterial has no bundle_excerpts."""
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("industry", "nonexistent", "thesis", registry=registry, base=base)
    assert mat.bundle_excerpts == []
    assert mat.claims == []
    assert mat.narrative_excerpts == []


def test_missing_narrative_returns_empty(tmp_path):
    """Missing archive narrative file → narrative_excerpts empty."""
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("industry", "test-industry", "profit_pool", registry=registry, base=base)
    # profit_pool archive_narrative_dim = "value_chain", which doesn't exist in fixture
    assert mat.narrative_excerpts == []


def test_invalid_field_raises(tmp_path):
    base, registry = _build_fixture(tmp_path)
    with pytest.raises(ValueError, match="No FIELD_SOURCES"):
        fetch_lens_material("industry", "test-industry", "nonexistent_field", registry=registry, base=base)


def test_claim_evidence_count(tmp_path):
    """ClaimCard.evidence_count = len(supporting_evidence)."""
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("industry", "test-industry", "demand", registry=registry, base=base)
    # clm-industry-0002 has market_size dim and 2 evidence entries
    mkt_claims = [c for c in mat.claims if c.claim_id == "clm-industry-0002"]
    assert len(mkt_claims) == 1
    assert mkt_claims[0].evidence_count == 2


def test_narrative_excerpt_headline_count(tmp_path):
    """NarrativeExcerpt.headline_count counts '### ' occurrences."""
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("industry", "test-industry", "demand", registry=registry, base=base)
    ne = mat.narrative_excerpts[0]
    # market-size.md has 2 ### sections
    assert ne.headline_count == 2


def test_lens_material_to_dict(tmp_path):
    """LensMaterial.to_dict() is JSON-serializable and has expected keys."""
    import json
    base, registry = _build_fixture(tmp_path)
    mat = fetch_lens_material("industry", "test-industry", "thesis", registry=registry, base=base)
    d = mat.to_dict()
    serialized = json.dumps(d)  # should not raise
    assert "bundle_excerpts" in d
    assert "claims" in d
    assert "narrative_excerpts" in d
    parsed = json.loads(serialized)
    assert parsed["scope_type"] == "industry"
    assert parsed["field"] == "thesis"

"""Investment lens fetcher — aggregates bundle / claim / narrative material.

Each lens field draws from three data sources:
  - Bundle excerpts  (synthesis / insight_blocks / atomic_facts / stage_gates /
                      arena_candidates / company_candidates)
  - Accumulated claims via ClaimRegistry
  - Existing archive narrative files
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app import config as cfg
from app.io.claim_registry import ClaimRegistry


# ---------------------------------------------------------------------------
# Field → data source mapping
# ---------------------------------------------------------------------------

FIELD_SOURCES: dict[tuple[str, str], dict[str, Any]] = {
    # ---- Industry 8 dims ----
    ("industry", "thesis"): dict(
        bundle_paths=["synthesis.one_sentence"],
        claim_filter={"claim_type": ["thesis"]},
        archive_narrative_dim=None,
    ),
    ("industry", "demand"): dict(
        bundle_paths=[
            "insight_blocks[dimension_hint=market_size|demand]",
            "atomic_facts[block_dim=market_size|demand]",
        ],
        claim_filter={"dimension_hint": ["market_size", "demand"]},
        archive_narrative_dim="market_size",
    ),
    ("industry", "supply_competition"): dict(
        bundle_paths=["insight_blocks[dimension_hint=competition|value_chain|lifecycle]"],
        claim_filter={"dimension_hint": ["competition", "value_chain", "lifecycle"]},
        archive_narrative_dim="competition",
    ),
    ("industry", "profit_pool"): dict(
        bundle_paths=["insight_blocks[dimension_hint=value_chain|financial_profile]"],
        claim_filter={"dimension_hint": ["value_chain", "financial_profile"]},
        archive_narrative_dim="value_chain",
    ),
    ("industry", "unit_economics"): dict(
        bundle_paths=["insight_blocks[dimension_hint=financial_profile|benchmark]"],
        claim_filter={"dimension_hint": ["financial_profile", "benchmark"]},
        archive_narrative_dim="benchmark",
    ),
    ("industry", "stage_gates"): dict(
        bundle_paths=["stage_gates[]"],
        claim_filter={"claim_type": ["gate_assessment"]},
        archive_narrative_dim=None,
    ),
    ("industry", "catalysts_timeline"): dict(
        bundle_paths=["insight_blocks[dimension_hint=drivers|technology|catalysts]"],
        claim_filter={"dimension_hint": ["drivers", "technology", "catalysts"]},
        archive_narrative_dim="drivers",
    ),
    ("industry", "risks_disconfirming_evidence"): dict(
        bundle_paths=[
            "synthesis.cannot_conclude",
            "insight_blocks[dimension_hint=risks]",
        ],
        claim_filter={"claim_type": ["risk"], "dimension_hint": ["risks"]},
        archive_narrative_dim="risks",
    ),
    # ---- Arena 7 dims ----
    ("arena", "battlefield_definition"): dict(
        bundle_paths=["arena_candidates[slug=?]"],
        claim_filter=None,
        archive_narrative_dim="definition",
    ),
    ("arena", "players_positions"): dict(
        bundle_paths=["insight_blocks[dimension_hint=competition|participants]"],
        claim_filter={"dimension_hint": ["competition", "participants", "competitive_position"]},
        archive_narrative_dim="participants",
    ),
    ("arena", "winning_variables"): dict(
        bundle_paths=["insight_blocks[dimension_hint=technology|competition|moat]"],
        claim_filter={"dimension_hint": ["technology", "competition", "moat"]},
        archive_narrative_dim="decisive_factors",
    ),
    ("arena", "evidence_scoreboard"): dict(
        bundle_paths=["atomic_facts[block_dim=competition|participants]"],
        claim_filter={"claim_type": ["judgment"]},
        archive_narrative_dim="narratives",
    ),
    ("arena", "stage_gates"): dict(
        bundle_paths=["stage_gates[]"],
        claim_filter={"claim_type": ["gate_assessment"]},
        archive_narrative_dim="trajectory",
    ),
    ("arena", "inflection_points"): dict(
        bundle_paths=["insight_blocks[dimension_hint=lifecycle|stage_gate|drivers]"],
        claim_filter={"claim_type": ["scenario", "judgment"]},
        archive_narrative_dim="trajectory",
    ),
    ("arena", "company_implications"): dict(
        bundle_paths=["company_candidates[]"],
        claim_filter=None,
        archive_narrative_dim="investment_view",
    ),
    # ---- Company 9 dims ----
    ("company", "business_exposure"): dict(
        bundle_paths=["company_candidates[ticker=?]"],
        claim_filter={"dimension_hint": ["business_model"]},
        archive_narrative_dim="business_model",
    ),
    ("company", "thesis_fit"): dict(
        bundle_paths=["synthesis.one_sentence", "company_candidates[ticker=?]"],
        claim_filter={"claim_type": ["thesis", "judgment"]},
        archive_narrative_dim="business_model",
    ),
    ("company", "moat_execution"): dict(
        bundle_paths=["insight_blocks[dimension_hint=competition|technology|moat]"],
        claim_filter={"dimension_hint": ["competition", "technology", "moat", "competitive_position"]},
        archive_narrative_dim="moat",
    ),
    ("company", "financial_quality"): dict(
        bundle_paths=["insight_blocks[dimension_hint=financial_profile]"],
        claim_filter={"dimension_hint": ["financial_profile"]},
        archive_narrative_dim="financial_profile",
    ),
    ("company", "growth_drivers"): dict(
        bundle_paths=["insight_blocks[dimension_hint=drivers|catalysts|growth_engine]"],
        claim_filter={"dimension_hint": ["drivers", "catalysts", "growth_engine"]},
        archive_narrative_dim="growth_engine",
    ),
    ("company", "stage_gate_status"): dict(
        bundle_paths=["stage_gates[]"],
        claim_filter={"claim_type": ["gate_assessment"]},
        archive_narrative_dim=None,
    ),
    ("company", "valuation_expectations"): dict(
        bundle_paths=["insight_blocks[dimension_hint=valuation|financial_profile]"],
        claim_filter={"dimension_hint": ["valuation", "financial_profile"]},
        archive_narrative_dim="valuation",
    ),
    ("company", "catalysts_risks"): dict(
        bundle_paths=["insight_blocks[dimension_hint=catalysts|risks]"],
        claim_filter={"claim_type": ["risk"], "dimension_hint": ["catalysts", "risks"]},
        archive_narrative_dim="catalysts",
    ),
    ("company", "open_questions"): dict(
        bundle_paths=["synthesis.investment_questions"],
        claim_filter=None,
        archive_narrative_dim=None,
    ),
}


# ---------------------------------------------------------------------------
# Data-class outputs
# ---------------------------------------------------------------------------

@dataclass
class BundleExcerpt:
    source_id: str
    publish_date: str
    source_type: str
    path_in_bundle: str
    text: str
    confidence: str | None
    bundle_sha8: str


@dataclass
class ClaimCard:
    claim_id: str
    claim_text: str
    claim_type: str
    confidence: str
    status: str
    evidence_count: int
    as_of: str


@dataclass
class NarrativeExcerpt:
    scope_type: str
    scope_ref: str
    dimension: str
    path: str
    headline_count: int


@dataclass
class LensMaterial:
    scope_type: str
    scope_ref: str
    field: str
    bundle_excerpts: list[BundleExcerpt] = field(default_factory=list)
    claims: list[ClaimCard] = field(default_factory=list)
    narrative_excerpts: list[NarrativeExcerpt] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope_type": self.scope_type,
            "scope_ref": self.scope_ref,
            "field": self.field,
            "bundle_excerpts": [vars(e) for e in self.bundle_excerpts],
            "claims": [vars(c) for c in self.claims],
            "narrative_excerpts": [vars(n) for n in self.narrative_excerpts],
        }


# ---------------------------------------------------------------------------
# Bundle registry helpers
# ---------------------------------------------------------------------------

def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def bundles_for_scope(scope_type: str, scope_ref: str, base: Path) -> list[dict[str, Any]]:
    """Scan data/bundle_registry.jsonl for entries touching scope_ref, sorted newest-first."""
    base = Path(base)
    registry_path = base / "data" / "bundle_registry.jsonl"
    entries = _read_jsonl(registry_path)
    matched = []
    for entry in entries:
        touched = entry.get("touched", {})
        # Map scope_type to touched key: "industry"→"industries", "arena"→"arenas", "company"→"companies"
        _SCOPE_TO_TOUCHED = {"industry": "industries", "arena": "arenas", "company": "companies"}
        touched_key = _SCOPE_TO_TOUCHED.get(scope_type, scope_type + "s")
        touched_list = touched.get(touched_key, [])
        if scope_ref in touched_list:
            matched.append(entry)
    # Sort by publish_date descending (newest first)
    matched.sort(key=lambda e: e.get("publish_date", ""), reverse=True)
    return matched


def load_bundle(entry: dict[str, Any], base: Path) -> dict[str, Any]:
    """Read bundle JSON from entry['bundle_path']."""
    path = Path(base) / entry["bundle_path"]
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Bundle path dispatcher
# ---------------------------------------------------------------------------

def _dispatch_bundle_path(
    path_spec: str,
    bundle: dict[str, Any],
    entry: dict[str, Any],
    scope_type: str,
    scope_ref: str,
) -> list[BundleExcerpt]:
    """
    Dispatch a bundle_path spec to actual BundleExcerpt objects.

    Supported spec forms:
      synthesis.X            → bundle["synthesis"][X]  (str or list)
      stage_gates[]          → bundle["stage_gates"] all items
      insight_blocks[dimension_hint=X|Y]
                             → insight_blocks where archive_routing_hints.dimension_hint ∈ {X,Y}
      atomic_facts[block_dim=X|Y]
                             → atomic_facts where linked_block_id's block dimension_hint ∈ {X,Y}
      arena_candidates[slug=?]
                             → arena_candidate where tentative_slug == scope_ref
      company_candidates[ticker=?]
                             → company_candidate where {market}_{ticker} == scope_ref
      company_candidates[]   → all company_candidates
    """
    source_id = entry.get("source_id", "")
    publish_date = entry.get("publish_date", "")
    source_type = entry.get("source_type", "")
    sha8 = entry.get("sha8", "")
    excerpts: list[BundleExcerpt] = []

    # synthesis.X
    if path_spec.startswith("synthesis."):
        key = path_spec[len("synthesis."):]
        synthesis = bundle.get("synthesis", {})
        if not isinstance(synthesis, dict):
            return excerpts
        value = synthesis.get(key)
        if value is None:
            return excerpts
        items = value if isinstance(value, list) else [value]
        for i, item in enumerate(items):
            if item and str(item).strip():
                excerpts.append(BundleExcerpt(
                    source_id=source_id,
                    publish_date=publish_date,
                    source_type=source_type,
                    path_in_bundle=f"synthesis.{key}[{i}]" if isinstance(value, list) else f"synthesis.{key}",
                    text=str(item).strip(),
                    confidence=None,
                    bundle_sha8=sha8,
                ))
        return excerpts

    # stage_gates[]
    if path_spec == "stage_gates[]":
        for i, gate in enumerate(bundle.get("stage_gates", [])):
            title = gate.get("title", "")
            crossed = gate.get("crossed", False)
            what = gate.get("what_would_cross_it", [])
            text = title
            if what:
                text += " | " + "; ".join(what[:2])
            excerpts.append(BundleExcerpt(
                source_id=source_id,
                publish_date=publish_date,
                source_type=source_type,
                path_in_bundle=f"stage_gates[{i}]",
                text=text,
                confidence="crossed" if crossed else "not_crossed",
                bundle_sha8=sha8,
            ))
        return excerpts

    # insight_blocks[dimension_hint=X|Y]
    if path_spec.startswith("insight_blocks[dimension_hint="):
        dims_str = path_spec[len("insight_blocks[dimension_hint="):-1]
        allowed_dims = set(dims_str.split("|"))
        # Build a block_id → dimension_hint lookup for atomic_facts usage
        for i, block in enumerate(bundle.get("insight_blocks", [])):
            hints = block.get("archive_routing_hints", {})
            dim = hints.get("dimension_hint", "")
            if dim in allowed_dims:
                summary = block.get("summary", "") or block.get("title", "")
                confidence = block.get("evidence_strength")
                excerpts.append(BundleExcerpt(
                    source_id=source_id,
                    publish_date=publish_date,
                    source_type=source_type,
                    path_in_bundle=f"insight_blocks[{i}]({block.get('id', '')})",
                    text=summary,
                    confidence=confidence,
                    bundle_sha8=sha8,
                ))
        return excerpts

    # atomic_facts[block_dim=X|Y]
    if path_spec.startswith("atomic_facts[block_dim="):
        dims_str = path_spec[len("atomic_facts[block_dim="):-1]
        allowed_dims = set(dims_str.split("|"))
        # Build block_id → dimension_hint index
        block_dim: dict[str, str] = {}
        for block in bundle.get("insight_blocks", []):
            hints = block.get("archive_routing_hints", {})
            dim = hints.get("dimension_hint", "")
            block_dim[block.get("id", "")] = dim
        for i, fact in enumerate(bundle.get("atomic_facts", [])):
            linked = fact.get("linked_block_id", "")
            if block_dim.get(linked, "") in allowed_dims:
                excerpts.append(BundleExcerpt(
                    source_id=source_id,
                    publish_date=publish_date,
                    source_type=source_type,
                    path_in_bundle=f"atomic_facts[{i}]({fact.get('fact_id', '')})",
                    text=fact.get("fact_text", ""),
                    confidence=fact.get("confidence"),
                    bundle_sha8=sha8,
                ))
        return excerpts

    # arena_candidates[slug=?]
    if path_spec == "arena_candidates[slug=?]":
        for i, ac in enumerate(bundle.get("arena_candidates", [])):
            if ac.get("tentative_slug") == scope_ref:
                focus = ac.get("battleground_focus", "")
                tickers = ac.get("participant_tickers", [])
                text = focus
                if tickers:
                    text += " | tickers: " + ", ".join(tickers)
                excerpts.append(BundleExcerpt(
                    source_id=source_id,
                    publish_date=publish_date,
                    source_type=source_type,
                    path_in_bundle=f"arena_candidates[{i}]({ac.get('candidate_id', '')})",
                    text=text,
                    confidence=ac.get("confidence"),
                    bundle_sha8=sha8,
                ))
        return excerpts

    # company_candidates[ticker=?]
    if path_spec == "company_candidates[ticker=?]":
        for i, cc in enumerate(bundle.get("company_candidates", [])):
            key = cc.get("market", "") + "_" + cc.get("ticker", "")
            if key == scope_ref:
                questions = cc.get("verification_questions", [])
                text = cc.get("exposure_type", "") or ""
                if questions:
                    text += " | Q: " + "; ".join(questions[:2])
                excerpts.append(BundleExcerpt(
                    source_id=source_id,
                    publish_date=publish_date,
                    source_type=source_type,
                    path_in_bundle=f"company_candidates[{i}]({cc.get('ticker', '')})",
                    text=text,
                    confidence=cc.get("confidence"),
                    bundle_sha8=sha8,
                ))
        return excerpts

    # company_candidates[]
    if path_spec == "company_candidates[]":
        for i, cc in enumerate(bundle.get("company_candidates", [])):
            name = cc.get("name", cc.get("ticker", ""))
            market = cc.get("market", "")
            ticker = cc.get("ticker", "")
            exposure = cc.get("exposure_type", "")
            text = f"{name} ({market}_{ticker}) — {exposure}"
            excerpts.append(BundleExcerpt(
                source_id=source_id,
                publish_date=publish_date,
                source_type=source_type,
                path_in_bundle=f"company_candidates[{i}]({ticker})",
                text=text,
                confidence=cc.get("confidence"),
                bundle_sha8=sha8,
            ))
        return excerpts

    # Unknown spec — return empty
    return excerpts


# ---------------------------------------------------------------------------
# Claim filter
# ---------------------------------------------------------------------------

def _filter_claims(
    claims: list[dict[str, Any]],
    claim_filter: dict[str, list[str]] | None,
) -> list[ClaimCard]:
    if claim_filter is None:
        return []

    allowed_claim_types = set(claim_filter.get("claim_type", []))
    allowed_dims = set(claim_filter.get("dimension_hint", []))

    results: list[ClaimCard] = []
    for claim in claims:
        # Must be active
        if claim.get("status") != "active":
            continue
        ct = claim.get("claim_type", "")
        dh = claim.get("dimension_hint", "")
        # Match: if both filters present, either dimension OR type can match (union)
        if allowed_claim_types and allowed_dims:
            if ct not in allowed_claim_types and dh not in allowed_dims:
                continue
        elif allowed_claim_types:
            if ct not in allowed_claim_types:
                continue
        elif allowed_dims:
            if dh not in allowed_dims:
                continue
        evidence_count = len(claim.get("supporting_evidence", []))
        results.append(ClaimCard(
            claim_id=claim["claim_id"],
            claim_text=claim.get("claim_text", ""),
            claim_type=ct,
            confidence=claim.get("confidence", ""),
            status=claim.get("status", ""),
            evidence_count=evidence_count,
            as_of=claim.get("as_of", ""),
        ))
    return results


# ---------------------------------------------------------------------------
# Archive narrative reader
# ---------------------------------------------------------------------------

def _read_archive_narrative(
    scope_type: str,
    scope_ref: str,
    dimension: str,
    base: Path,
) -> NarrativeExcerpt | None:
    """Read archive narrative file and return an excerpt, or None if empty/missing."""
    from app.io import industry as industry_io
    from app.io import arenas as arenas_io
    from app.io import company as company_io

    try:
        if scope_type == "industry":
            content = industry_io.read_narrative(scope_ref, dimension, base=base)
            rel_path = f"industries/{scope_ref}/{dimension.replace('_', '-')}.md"
        elif scope_type == "arena":
            content = arenas_io.read_narrative(scope_ref, dimension, base=base)
            rel_path = f"arenas/{scope_ref}/{dimension.replace('_', '-')}.md"
        elif scope_type == "company":
            # scope_ref is like "SSE_603011" → market=SSE, ticker=603011
            parts = scope_ref.split("_", 1)
            if len(parts) != 2:
                return None
            market, ticker = parts[0], parts[1]
            content = company_io.read_narrative(ticker, market, dimension, base=base)
            rel_path = f"companies/{scope_ref}/narratives/{dimension.replace('_', '-')}.md"
        else:
            return None
    except Exception:
        return None

    if not content or not content.strip():
        return None

    # Count ### headlines
    headline_count = content.count("\n### ") + (1 if content.startswith("### ") else 0)

    return NarrativeExcerpt(
        scope_type=scope_type,
        scope_ref=scope_ref,
        dimension=dimension,
        path=rel_path,
        headline_count=headline_count,
    )


# ---------------------------------------------------------------------------
# Core fetcher
# ---------------------------------------------------------------------------

def fetch_lens_material(
    scope_type: str,
    scope_ref: str,
    field: str,
    *,
    registry: ClaimRegistry,
    base: Path,
) -> LensMaterial:
    """Fetch all lens material for a given (scope_type, scope_ref, field) triple."""
    key = (scope_type, field)
    if key not in FIELD_SOURCES:
        raise ValueError(f"No FIELD_SOURCES mapping for ({scope_type!r}, {field!r})")

    sources = FIELD_SOURCES[key]
    base = Path(base)

    # ---- 1. Bundle excerpts ----
    bundle_excerpts: list[BundleExcerpt] = []
    entries = bundles_for_scope(scope_type, scope_ref, base)
    for entry in entries:
        bundle = load_bundle(entry, base)
        if not bundle:
            continue
        for path_spec in sources["bundle_paths"]:
            excerpts = _dispatch_bundle_path(path_spec, bundle, entry, scope_type, scope_ref)
            bundle_excerpts.extend(excerpts)

    # ---- 2. Claims ----
    raw_claims = registry.claims_for_scope(scope_type, scope_ref)
    claim_cards = _filter_claims(raw_claims, sources.get("claim_filter"))

    # ---- 3. Archive narrative ----
    narrative_excerpts: list[NarrativeExcerpt] = []
    archive_dim = sources.get("archive_narrative_dim")
    if archive_dim:
        ne = _read_archive_narrative(scope_type, scope_ref, archive_dim, base)
        if ne:
            narrative_excerpts.append(ne)

    return LensMaterial(
        scope_type=scope_type,
        scope_ref=scope_ref,
        field=field,
        bundle_excerpts=bundle_excerpts,
        claims=claim_cards,
        narrative_excerpts=narrative_excerpts,
    )

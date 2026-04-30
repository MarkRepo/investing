from __future__ import annotations

import json
import re
import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app import config as cfg
from app.io.claim_registry import ClaimRegistry

PROPOSAL_VERSION = "phase3a-v1"
VALID_DECISIONS = {"approve", "edit", "reject", "defer"}
NARRATIVE_DIMS = tuple(dim for dim in cfg.ARENA_DIMENSIONS if dim != "definition")
CLAIM_DIMENSION_TO_ARENA_NARRATIVE = {
    "participants": "participants",
    "competition": "participants",
    "competitive_position": "participants",
    "moat": "decisive_factors",
    "technology": "decisive_factors",
    "supply_chain": "decisive_factors",
    "winning_variables": "decisive_factors",
    "catalysts": "trajectory",
    "stage_gate": "trajectory",
    "regulation": "trajectory",
    "thesis": "narratives",
    "judgment": "narratives",
    "risk": "narratives",
    "scenario": "narratives",
    "valuation": "investment_view",
    "investment_view": "investment_view",
}
PLACEHOLDER_PATTERNS = ("待 Claude", "待填写", "TODO", "TBD", "<body>")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def map_claim_dimension(dimension_hint: str) -> str | None:
    return CLAIM_DIMENSION_TO_ARENA_NARRATIVE.get(dimension_hint)


def _claim_source_ids(claim: dict[str, Any]) -> list[str]:
    source_ids: list[str] = []
    for evidence in claim.get("supporting_evidence", []) or []:
        source_id = evidence.get("source_id")
        if source_id and source_id not in source_ids:
            source_ids.append(source_id)
    return source_ids


def _claim_has_source(claim: dict[str, Any], source_id: str) -> bool:
    return source_id in _claim_source_ids(claim)


def _evidence_summary(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "claim_id": claim["claim_id"],
            "claim_text": claim.get("claim_text", ""),
            "confidence": claim.get("confidence"),
            "as_of": claim.get("as_of"),
            "evidence_source_ids": _claim_source_ids(claim),
        }
        for claim in claims
    ]


def build_proposal_file(
    *,
    registry: ClaimRegistry,
    arena_slug: str,
    source_id: str,
    generated_at: str,
    existing_excerpt_loader: Callable[[str, str], str],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    unmapped: list[dict[str, Any]] = []
    for claim in registry.claims_for_scope("arena", arena_slug):
        if claim.get("status") != "active":
            continue
        if not _claim_has_source(claim, source_id):
            continue
        dimension = map_claim_dimension(claim.get("dimension_hint", ""))
        if dimension is None:
            unmapped.append(
                {
                    "claim_id": claim["claim_id"],
                    "claim_text": claim.get("claim_text", ""),
                    "dimension_hint": claim.get("dimension_hint", ""),
                    "reason": "unmapped dimension_hint",
                }
            )
            continue
        grouped.setdefault(dimension, []).append(claim)

    proposals = []
    for idx, dimension in enumerate(sorted(grouped), start=1):
        claims = grouped[dimension]
        supported_by_claims = [claim["claim_id"] for claim in claims]
        source_ids: list[str] = []
        for claim in claims:
            for claim_source_id in _claim_source_ids(claim):
                if claim_source_id not in source_ids:
                    source_ids.append(claim_source_id)
        proposals.append(
            {
                "proposal_id": f"np-{idx:03d}",
                "arena_slug": arena_slug,
                "dimension": dimension,
                "title": f"Draft narrative for {dimension}",
                "body": None,
                "supported_by_claims": supported_by_claims,
                "source_ids": source_ids,
                "evidence_summary": _evidence_summary(claims),
                "existing_narrative_excerpt": existing_excerpt_loader(arena_slug, dimension),
                "decision": None,
                "decision_reason": None,
                "edited_title": None,
                "edited_body": None,
            }
        )

    return {
        "source_id": source_id,
        "generated_at": generated_at,
        "proposal_version": PROPOSAL_VERSION,
        "scope_type": "arena",
        "proposals": proposals,
        "unmapped_claims": unmapped,
        "summary_stats": {
            "total_proposals": len(proposals),
            "arena_count": 1 if proposals else 0,
            "dimension_count": len({proposal["dimension"] for proposal in proposals}),
            "unsupported_candidates_skipped": len(unmapped),
        },
    }

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


def _is_placeholder(text: str) -> bool:
    return any(pattern in text for pattern in PLACEHOLDER_PATTERNS)


def _validate_body(proposal_id: str, body: Any, field_name: str) -> list[str]:
    if not isinstance(body, str) or not body.strip():
        return [f"{proposal_id}: {field_name} requires non-empty body"]
    if _is_placeholder(body):
        return [f"{proposal_id}: body must not be placeholder text"]
    return []


def validate_proposal_decisions(data: dict[str, Any], registry: ClaimRegistry) -> list[str]:
    errors: list[str] = []
    for proposal in data.get("proposals", []) or []:
        proposal_id = proposal.get("proposal_id", "<unknown>")
        decision = proposal.get("decision")
        if decision not in VALID_DECISIONS:
            errors.append(f"{proposal_id}: invalid or missing decision")
            continue
        if not str(proposal.get("decision_reason") or "").strip():
            errors.append(f"{proposal_id}: missing decision_reason")
        dimension = proposal.get("dimension")
        if dimension == "definition":
            errors.append(f"{proposal_id}: dimension definition cannot be written by narrative proposals")
        elif dimension not in NARRATIVE_DIMS:
            errors.append(f"{proposal_id}: invalid narrative dimension {dimension!r}")
        if decision in {"approve", "edit"}:
            claim_ids = proposal.get("supported_by_claims") or []
            if not claim_ids:
                errors.append(f"{proposal_id}: supported_by_claims required")
            for claim_id in claim_ids:
                claim = registry.find_by_id(claim_id)
                if claim is None:
                    errors.append(f"{proposal_id}: supported claim {claim_id} not found")
                elif claim.get("status") != "active":
                    errors.append(f"{proposal_id}: supported claim {claim_id} is not active")
            if decision == "approve":
                errors.extend(_validate_body(proposal_id, proposal.get("body"), "approve"))
            else:
                errors.extend(_validate_body(proposal_id, proposal.get("edited_body"), "edit"))
    return errors


def _dimension_path(base: Path, arena_slug: str, dimension: str) -> Path:
    return base / "arenas" / arena_slug / f"{dimension.replace('_', '-')}.md"


def _format_list(values: list[str]) -> str:
    return "[" + ", ".join(values) + "]"


def _render_markdown_block(proposal: dict[str, Any], *, today: str) -> str:
    decision = proposal["decision"]
    title = proposal.get("title") or "Untitled narrative"
    body = proposal.get("body") or ""
    if decision == "edit":
        title = proposal.get("edited_title") or title
        body = proposal.get("edited_body") or ""
    lines = [
        f"### {title}",
        "",
        "status: active",
        f"last_written: {today}",
        f"supported_by_claims: {_format_list(proposal.get('supported_by_claims') or [])}",
        f"source_ids: {_format_list(proposal.get('source_ids') or [])}",
        f"proposal_id: {proposal['proposal_id']}",
        "",
        body.strip(),
        "",
    ]
    return "\n".join(lines)


def append_audit_event(base: Path, event: dict[str, Any]) -> None:
    path = base / "data" / "audit" / "narrative-events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def archive_pending_file(pending_path: Path, base: Path) -> Path:
    archive_dir = base / "data" / "pending" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived = archive_dir / pending_path.name
    shutil.move(str(pending_path), str(archived))
    return archived


def apply_proposal_file(
    *,
    data: dict[str, Any],
    registry: ClaimRegistry,
    base: Path,
    pending_path: Path,
    today: str | None = None,
    now: str | None = None,
) -> dict[str, int]:
    errors = validate_proposal_decisions(data, registry)
    if errors:
        raise ValueError("\n".join(errors))
    today = today or date.today().isoformat()
    now = now or now_iso()
    counts = {"applied": 0, "rejected": 0, "deferred": 0}
    source_id = data.get("source_id", "")
    for proposal in data.get("proposals", []) or []:
        decision = proposal["decision"]
        if decision in {"approve", "edit"}:
            path = _dimension_path(base, proposal["arena_slug"], proposal["dimension"])
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(_render_markdown_block(proposal, today=today))
            counts["applied"] += 1
            event_type = "narrative_applied"
        elif decision == "reject":
            counts["rejected"] += 1
            event_type = "narrative_rejected"
        else:
            counts["deferred"] += 1
            event_type = "narrative_deferred"
        append_audit_event(
            base,
            {
                "event_type": event_type,
                "source_id": source_id,
                "proposal_id": proposal.get("proposal_id"),
                "arena_slug": proposal.get("arena_slug"),
                "dimension": proposal.get("dimension"),
                "decision_reason": proposal.get("decision_reason"),
                "created_at": now,
            },
        )
    archive_pending_file(pending_path, base)
    return counts

from __future__ import annotations

import inspect
import json
import shutil
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app import config as cfg
from app.io.claim_registry import ClaimRegistry

PROPOSAL_VERSION = "phase3a-v1"
VALID_DECISIONS = {"approve", "edit", "reject", "defer"}
PLACEHOLDER_PATTERNS = ("待 Claude", "待填写", "TODO", "TBD", "<body>")

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

CLAIM_DIMENSION_TO_COMPANY_NARRATIVE = {
    "business_model": "business_model",
    "thesis": "business_model",
    "moat": "moat",
    "competition": "moat",
    "competitive_position": "moat",
    "technology": "moat",
    "supply_chain": "moat",
    "winning_variables": "moat",
    "growth_engine": "growth_engine",
    "management": "management",
    "financial_profile": "financial_profile",
    "catalysts": "catalysts",
    "stage_gate": "catalysts",
    "regulation": "risks",
    "risk": "risks",
    "risks": "risks",
    "scenario": "risks",
    "valuation": "valuation",
    "investment_view": "valuation",
    "judgment": "valuation",
}


@dataclass(frozen=True)
class ScopeConfig:
    scope_type: str
    narrative_dims: tuple[str, ...]
    mapping: dict[str, str]
    top_dir: str
    narrative_subdir: str | None


SCOPE_CONFIGS: dict[str, ScopeConfig] = {
    "arena": ScopeConfig(
        scope_type="arena",
        narrative_dims=tuple(d for d in cfg.ARENA_DIMENSIONS if d != "definition"),
        mapping=CLAIM_DIMENSION_TO_ARENA_NARRATIVE,
        top_dir="arenas",
        narrative_subdir=None,
    ),
    "company": ScopeConfig(
        scope_type="company",
        narrative_dims=tuple(cfg.COMPANY_DIMENSIONS),
        mapping=CLAIM_DIMENSION_TO_COMPANY_NARRATIVE,
        top_dir="companies",
        narrative_subdir="narratives",
    ),
}

# Phase 3A compatibility: old name still imported by Phase 3A tests.
NARRATIVE_DIMS = SCOPE_CONFIGS["arena"].narrative_dims


def _scope(scope_type: str) -> ScopeConfig:
    if scope_type not in SCOPE_CONFIGS:
        raise ValueError(f"unsupported scope_type: {scope_type}")
    return SCOPE_CONFIGS[scope_type]


def narrative_dims_for_scope(scope_type: str) -> tuple[str, ...]:
    return _scope(scope_type).narrative_dims


def map_claim_dimension(dimension_hint: str, scope_type: str = "arena") -> str | None:
    return _scope(scope_type).mapping.get(dimension_hint)


def dimension_path(base: Path, scope_type: str, scope_ref: str, dimension: str) -> Path:
    scope = _scope(scope_type)
    scope_dir = Path(base) / scope.top_dir / scope_ref
    if scope.narrative_subdir:
        scope_dir = scope_dir / scope.narrative_subdir
    return scope_dir / f"{dimension.replace('_', '-')}.md"


def flags_path(base: Path, scope_type: str, scope_ref: str) -> Path:
    scope = _scope(scope_type)
    return Path(base) / scope.top_dir / scope_ref / "narrative-flags.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _call_excerpt_loader(loader: Callable, scope_type: str, scope_ref: str, dimension: str) -> str:
    """Call excerpt loader with 3 args (scope_type, scope_ref, dim) or 2 args (scope_ref, dim)."""
    try:
        sig = inspect.signature(loader)
        n_params = len(sig.parameters)
    except (ValueError, TypeError):
        n_params = 3
    if n_params >= 3:
        return loader(scope_type, scope_ref, dimension)
    return loader(scope_ref, dimension)


def build_proposal_file(
    *,
    registry: ClaimRegistry,
    source_id: str,
    generated_at: str,
    existing_excerpt_loader: Callable[[str, str, str], str],
    scope_type: str = "arena",
    scope_ref: str | None = None,
    arena_slug: str | None = None,
) -> dict[str, Any]:
    if scope_ref is None:
        scope_ref = arena_slug
    if scope_ref is None:
        raise ValueError("scope_ref (or arena_slug for arena scope) is required")
    scope = _scope(scope_type)

    grouped: dict[str, list[dict[str, Any]]] = {}
    unmapped: list[dict[str, Any]] = []
    for claim in registry.claims_for_scope(scope_type, scope_ref):
        if claim.get("status") != "active":
            continue
        if not _claim_has_source(claim, source_id):
            continue
        dimension = scope.mapping.get(claim.get("dimension_hint", ""))
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

    proposals: list[dict[str, Any]] = []
    for idx, dimension in enumerate(sorted(grouped), start=1):
        claims = grouped[dimension]
        supported_by_claims = [claim["claim_id"] for claim in claims]
        source_ids: list[str] = []
        for claim in claims:
            for claim_source_id in _claim_source_ids(claim):
                if claim_source_id not in source_ids:
                    source_ids.append(claim_source_id)
        proposal = {
            "proposal_id": f"np-{idx:03d}",
            "scope_type": scope_type,
            "scope_ref": scope_ref,
            "dimension": dimension,
            "title": f"Draft narrative for {dimension}",
            "body": None,
            "supported_by_claims": supported_by_claims,
            "source_ids": source_ids,
            "evidence_summary": _evidence_summary(claims),
            "existing_narrative_excerpt": _call_excerpt_loader(existing_excerpt_loader, scope_type, scope_ref, dimension),
            "decision": None,
            "decision_reason": None,
            "edited_title": None,
            "edited_body": None,
        }
        if scope_type == "arena":
            # Phase 3A compatibility: keep arena_slug on arena proposals.
            proposal["arena_slug"] = scope_ref
        proposals.append(proposal)

    result: dict[str, Any] = {
        "source_id": source_id,
        "generated_at": generated_at,
        "proposal_version": PROPOSAL_VERSION,
        "scope_type": scope_type,
        "scope_ref": scope_ref,
        "proposals": proposals,
        "unmapped_claims": unmapped,
        "summary_stats": {
            "total_proposals": len(proposals),
            "dimension_count": len({proposal["dimension"] for proposal in proposals}),
            "unsupported_candidates_skipped": len(unmapped),
        },
    }
    if scope_type == "arena":
        # Phase 3A compatibility: keep legacy arena_count key (no scope_count).
        result["summary_stats"]["arena_count"] = 1 if proposals else 0
    else:
        result["summary_stats"]["scope_count"] = 1 if proposals else 0
    return result


def _is_placeholder(text: str) -> bool:
    return any(pattern in text for pattern in PLACEHOLDER_PATTERNS)


def _validate_body(proposal_id: str, body: Any, field_name: str) -> list[str]:
    if not isinstance(body, str) or not body.strip():
        return [f"{proposal_id}: {field_name} requires non-empty body"]
    if _is_placeholder(body):
        return [f"{proposal_id}: body must not be placeholder text"]
    return []


def _proposal_scope(proposal: dict[str, Any], data_scope_type: str) -> tuple[str, str]:
    scope_type = proposal.get("scope_type") or data_scope_type
    if scope_type == "arena" and proposal.get("arena_slug") and not proposal.get("scope_ref"):
        return scope_type, proposal["arena_slug"]
    return scope_type, proposal.get("scope_ref", "")


def validate_proposal_decisions(data: dict[str, Any], registry: ClaimRegistry) -> list[str]:
    errors: list[str] = []
    data_scope_type = data.get("scope_type") or "arena"
    for proposal in data.get("proposals", []) or []:
        proposal_id = proposal.get("proposal_id", "<unknown>")
        decision = proposal.get("decision")
        if decision not in VALID_DECISIONS:
            errors.append(f"{proposal_id}: invalid or missing decision")
            continue
        if not str(proposal.get("decision_reason") or "").strip():
            errors.append(f"{proposal_id}: missing decision_reason")
        scope_type, _scope_ref = _proposal_scope(proposal, data_scope_type)
        if scope_type not in SCOPE_CONFIGS:
            errors.append(f"{proposal_id}: invalid scope_type {scope_type!r}")
            continue
        scope = SCOPE_CONFIGS[scope_type]
        dimension = proposal.get("dimension")
        if scope_type == "arena" and dimension == "definition":
            errors.append(f"{proposal_id}: dimension definition cannot be written by narrative proposals")
        elif dimension not in scope.narrative_dims:
            errors.append(f"{proposal_id}: invalid narrative dimension {dimension!r} for scope {scope_type}")
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
    path = Path(base) / "data" / "audit" / "narrative-events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def archive_pending_file(pending_path: Path, base: Path) -> Path:
    archive_dir = Path(base) / "data" / "pending" / "archive"
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
    data_scope_type = data.get("scope_type") or "arena"
    for proposal in data.get("proposals", []) or []:
        decision = proposal["decision"]
        scope_type, scope_ref = _proposal_scope(proposal, data_scope_type)
        if decision in {"approve", "edit"}:
            path = dimension_path(Path(base), scope_type, scope_ref, proposal["dimension"])
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
            Path(base),
            {
                "event_type": event_type,
                "source_id": source_id,
                "proposal_id": proposal.get("proposal_id"),
                "scope_type": scope_type,
                "scope_ref": scope_ref,
                "dimension": proposal.get("dimension"),
                "decision_reason": proposal.get("decision_reason"),
                "created_at": now,
            },
        )
    archive_pending_file(Path(pending_path), Path(base))
    return counts


def read_narrative_flags(
    scope_type_or_arena_slug: str,
    scope_ref: str | None = None,
    base: Path | None = None,
    include_dismissed: bool = False,
) -> list[dict[str, Any]]:
    """Read flags for a scope.

    Backward-compatible signature: Phase 3A callers pass a single positional
    arena slug — this is treated as scope_type="arena", scope_ref=<slug>.
    """
    if scope_ref is None:
        scope_type, scope_ref_val = "arena", scope_type_or_arena_slug
    else:
        scope_type, scope_ref_val = scope_type_or_arena_slug, scope_ref
    root = Path(base) if base is not None else cfg.ARENAS_DIR.parent
    path = flags_path(root, scope_type, scope_ref_val)
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if include_dismissed:
        return rows
    return [row for row in rows if not row.get("dismissed")]


def _next_flag_id(existing: list[dict[str, Any]], offset: int) -> str:
    max_id = 0
    for flag in existing:
        flag_id = flag.get("flag_id", "")
        if flag_id.startswith("nf-"):
            try:
                max_id = max(max_id, int(flag_id.rsplit("-", 1)[1]))
            except ValueError:
                pass
    return f"nf-{max_id + offset:04d}"


def _parse_claim_ids(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def _scan_segments(base: Path, scope_type: str, scope_ref: str) -> list[dict[str, Any]]:
    scope = _scope(scope_type)
    segments: list[dict[str, Any]] = []
    for dimension in scope.narrative_dims:
        path = dimension_path(base, scope_type, scope_ref, dimension)
        if not path.exists():
            continue
        current_proposal_id: str | None = None
        current_claim_ids: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("### "):
                current_proposal_id = None
                current_claim_ids = []
                continue
            if stripped.startswith("supported_by_claims:"):
                value = stripped.split(":", 1)[1].strip()
                if value.startswith("[") and value.endswith("]"):
                    current_claim_ids = _parse_claim_ids(value[1:-1])
            elif stripped.startswith("proposal_id:"):
                current_proposal_id = stripped.split(":", 1)[1].strip()
                if current_claim_ids:
                    proposal_id = current_proposal_id or "unknown"
                    for claim_id in current_claim_ids:
                        segments.append(
                            {
                                "dimension": dimension,
                                "segment_ref": f"{path.name}#{proposal_id}",
                                "claim_id": claim_id,
                            }
                        )
    return segments


def _claim_has_refuting_evidence(claim: dict[str, Any]) -> bool:
    return any(
        evidence.get("direction") == "refutes"
        for evidence in claim.get("supporting_evidence", []) or []
    )


def _flag_for_segment(segment: dict[str, Any], registry: ClaimRegistry) -> tuple[str, str] | None:
    claim_id = segment["claim_id"]
    claim = registry.find_by_id(claim_id)
    if claim is None:
        return "critical", "supporting claim missing"
    if claim.get("status") == "retired":
        return "critical", "supporting claim retired"
    if claim.get("status") != "active":
        return "critical", "supporting claim not active"
    if _claim_has_refuting_evidence(claim):
        return "significant", "supporting claim has refuting evidence"
    return None


def scan_narrative_flags(
    *,
    registry: ClaimRegistry,
    base: Path,
    scope_type: str = "arena",
    scope_ref: str | None = None,
    arena_slug: str | None = None,
    now: str | None = None,
) -> list[dict[str, Any]]:
    if scope_ref is None:
        scope_ref = arena_slug
    if scope_ref is None:
        raise ValueError("scope_ref (or arena_slug for arena scope) is required")
    now = now or now_iso()
    existing = read_narrative_flags(scope_type, scope_ref, base=base, include_dismissed=True)
    existing_keys = {
        (flag.get("dimension"), flag.get("segment_ref"), flag.get("supported_by_claim"), flag.get("reason"))
        for flag in existing
        if not flag.get("dismissed")
    }
    new_flags: list[dict[str, Any]] = []
    for segment in _scan_segments(Path(base), scope_type, scope_ref):
        level_reason = _flag_for_segment(segment, registry)
        if level_reason is None:
            continue
        level, reason = level_reason
        key = (segment["dimension"], segment["segment_ref"], segment["claim_id"], reason)
        if key in existing_keys:
            continue
        flag = {
            "flag_id": _next_flag_id(existing, len(new_flags) + 1),
            "created_at": now,
            "dimension": segment["dimension"],
            "segment_ref": segment["segment_ref"],
            "supported_by_claim": segment["claim_id"],
            "scope_type": scope_type,
            "scope_ref": scope_ref,
            "flag_level": level,
            "reason": reason,
            "dismissed": False,
            "superseded_by": None,
        }
        new_flags.append(flag)
    if new_flags:
        path = flags_path(Path(base), scope_type, scope_ref)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            for flag in new_flags:
                f.write(json.dumps(flag, ensure_ascii=False, sort_keys=True) + "\n")
    return new_flags

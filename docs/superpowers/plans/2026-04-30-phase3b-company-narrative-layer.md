# Phase 3B Company Investment Narrative Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Phase 3A narrative machinery to the **company** scope: claim-driven pending company narrative proposals, approved Markdown writes, manual narrative review flags, and minimal company detail page flag display. Phase 3A arena behavior must remain intact.

**Architecture:** Refactor `app/io/narrative_proposals.py` once to become scope-aware via a small `SCOPE_CONFIGS` registry (keyed by `scope_type ∈ {"arena", "company"}`). Arena tests continue to pass against the same external API. Add a `company` entry that points to `companies/<key>/narratives/<dim-kebab>.md` (the existing company narrative directory). Add three thin CLI wrappers in `scripts/` mirroring the Phase 3A trio. Wire `app/routes/companies.py` and `detail.html` to render per-dimension flags.

**Tech Stack:** Python 3 stdlib (`argparse`, `json`, `pathlib`, `datetime`, `re`, `shutil`), pytest, JSON/JSONL, Markdown files, existing FastAPI/Jinja company route/template.

---

## 0. Mandatory guardrails

Before every task, re-read this section. If implementation drifts into a forbidden item, stop and revert that drift before continuing.

**Allowed Phase 3B outputs:**
- `data/pending/narrative-proposals-<source_id>.json` (with `scope_type == "company"`)
- `data/pending/archive/narrative-proposals-<source_id>.json`
- `data/audit/narrative-events.jsonl` appends
- `companies/<market>_<ticker>/narratives/<dim-kebab>.md` appends for approved/edit proposals only
- `companies/<market>_<ticker>/narrative-flags.jsonl`
- minimal company detail page flag display
- refactored `app/io/narrative_proposals.py` with arena behavior preserved

**Forbidden in this plan:**
- Do not call `anthropic`, `openai`, browser automation, or any LLM API from Python.
- Do not generate final narrative prose automatically in Python.
- Do not auto-rewrite existing company narrative Markdown.
- Do not touch `companies/<key>/meta.md`, `companies/<key>/v0.md`, `companies/<key>/profile-*.md`, `companies/<key>/valuation.md`, or `companies/<key>/trade-log.md`.
- Do not implement industry 11 narrative (Phase 3C).
- Do not implement memo frontmatter reverse references (deferred).
- Do not implement review queue, cron, event adapters, daemons, or periodic scans.
- Do not modify `app/io/claims.py`.
- Do not modify `companies/<key>/claims.jsonl` (V0 legacy data).
- Do not add proposal approval/editing UI.
- Do not add dismiss behavior for flags.
- Do not change Phase 3A arena JSON contract, CLI flags, or route behavior.

**Verification after each implementation task:**

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl' 'companies/*/meta.md' 'companies/*/v0.md' 'companies/*/profile-*.md' 'companies/*/valuation.md' 'companies/*/trade-log.md'
```

Expected: no diff. If there is a diff, revert it before continuing.

**Phase 3A regression guard after each implementation task:**

```bash
.venv/bin/python -m pytest \
  tests/test_narrative_proposals.py \
  tests/test_narrative_apply_cli.py \
  tests/test_narrative_flags.py \
  tests/test_arenas_narrative_flags.py \
  tests/test_phase3a_narrative_end_to_end.py \
  -q
```

Expected: PASS. If any Phase 3A test fails, stop and fix before moving on.

---

## 1. File map

### Create

- `app/io/narrative_proposals.py` — **modify in place** to add scope-aware helpers (not a new file; listed here because its public surface grows).
- `scripts/company_narrative_propose.py` — company propose CLI.
- `scripts/company_narrative_apply.py` — company apply CLI.
- `scripts/company_narrative_flags.py` — company flag CLI.
- `tests/test_company_narrative_proposals.py` — company proposal generation + apply unit tests.
- `tests/test_company_narrative_apply_cli.py` — company apply/propose CLI tests.
- `tests/test_company_narrative_flags.py` — company flag scan/read tests.
- `tests/test_companies_narrative_flags.py` — company route/template flag display test.
- `tests/test_phase3b_narrative_end_to_end.py` — company e2e test.

### Modify

- `app/io/narrative_proposals.py` — introduce `SCOPE_CONFIGS`; make functions scope-aware; keep arena defaults.
- `scripts/narrative_propose.py` — use refactored API (no flag change).
- `scripts/narrative_apply.py` — use refactored API (no flag change).
- `scripts/narrative_flags.py` — use refactored API (no flag change).
- `app/routes/arenas.py` — update `read_narrative_flags` call to pass scope_type explicitly (`"arena"`).
- `app/routes/companies.py` — read company narrative flags; pass per-dimension flags to template.
- `app/templates/companies/detail.html` — show `needs review` badges and flag details.

### Do not modify

- `app/io/claims.py`
- `app/io/claim_registry.py`
- `companies/*/claims.jsonl`
- `companies/*/meta.md`
- `companies/*/v0.md`
- `companies/*/profile-*.md`
- `companies/*/valuation.md`
- `companies/*/trade-log.md`
- `scripts/ingest_aggregate.py`, `scripts/ingest_match.py`, `scripts/ingest_apply.py`, `scripts/preprocess_report.py`
- `industries/**`
- `arenas/**` except test tmp dirs created inside pytest
- `app/routes/industries.py`, `app/templates/industries/**`

---

## 2. Data contracts to use exactly

### 2.1 Company scope_ref format

Company `scope_ref` values are `"<MARKET>_<TICKER>"`, matching the existing `companies/` directory names. Examples: `"SSE_600519"`, `"BSE_920118"`, `"US_AAPL"`. This is the same format used by `companies/<scope_ref>/claims.jsonl` V0 legacy files and by `claims/companies.jsonl` Phase 2 entries.

### 2.2 Proposal file shape

`scripts/company_narrative_propose.py` writes this structure:

```python
{
    "source_id": "src-001",
    "generated_at": "2026-04-30T12:00:00+00:00",
    "proposal_version": "phase3a-v1",
    "scope_type": "company",
    "scope_ref": "SSE_600519",
    "proposals": [
        {
            "proposal_id": "np-001",
            "scope_type": "company",
            "scope_ref": "SSE_600519",
            "dimension": "moat",
            "title": "Draft narrative for moat",
            "body": None,
            "supported_by_claims": ["clm-company-0001"],
            "source_ids": ["src-001"],
            "evidence_summary": [
                {
                    "claim_id": "clm-company-0001",
                    "claim_text": "...",
                    "confidence": "medium_high",
                    "as_of": "2025-12-31",
                    "evidence_source_ids": ["src-001"],
                }
            ],
            "existing_narrative_excerpt": "...",
            "decision": None,
            "decision_reason": None,
            "edited_title": None,
            "edited_body": None,
        }
    ],
    "unmapped_claims": [],
    "summary_stats": {
        "total_proposals": 1,
        "scope_count": 1,
        "dimension_count": 1,
        "unsupported_candidates_skipped": 0,
    },
}
```

The top-level file keeps `proposal_version == "phase3a-v1"` (the schema didn't change — only the scope added). The **old** `arena_slug` key used in Phase 3A proposals stays on arena proposals; **new** company proposals use `scope_type` + `scope_ref` instead. Top-level arena proposals also gain `scope_ref` in Task A2 below (the arena proposal generator starts emitting both `arena_slug` and `scope_ref` for forward compatibility; Phase 3A tests still assert on `arena_slug`, which remains). The `summary_stats` key `arena_count` is renamed to `scope_count` globally — see Task A2 for the test update.

### 2.3 Decision rules

Same as Phase 3A. Additional constraint for company:
- dimension must be in `cfg.COMPANY_DIMENSIONS` (all 8 are allowed; unlike arena, company has no `definition` dim to exclude).

### 2.4 Markdown append format

Same exact block as Phase 3A:

```markdown
### {title}

status: active
last_written: {YYYY-MM-DD}
supported_by_claims: [{claim_id_1}, {claim_id_2}]
source_ids: [{source_id_1}, {source_id_2}]
proposal_id: {proposal_id}

{body}
```

Target path for company: `companies/<market>_<ticker>/narratives/<dim-kebab>.md`, where `dim-kebab = dim.replace("_", "-")`. Note the extra `narratives/` segment — this matches `app/io/company.py::_narrative_path()`.

### 2.5 Flag file shape

Same line shape as Phase 3A. Path for company: `companies/<market>_<ticker>/narrative-flags.jsonl` (sibling of `narratives/`, **not** inside the `narratives/` subdirectory). Dedup key: `(dimension, segment_ref, supported_by_claim, reason)`.

### 2.6 Company dimension mapping

```python
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
```

Any `dimension_hint` not present here goes to `unmapped_claims[]` with `reason == "unmapped dimension_hint"`. Do not invent silent defaults.

---

## Part A: Scope-aware refactor (arena preserved)

### Task A1: Add failing scope-aware API tests

**Files:**
- Modify: `tests/test_narrative_proposals.py`
- Modify later: `app/io/narrative_proposals.py`

- [ ] **Step 1: Append scope-surface tests**

Append this to `tests/test_narrative_proposals.py`:

```python
from app.io.narrative_proposals import (
    SCOPE_CONFIGS,
    dimension_path,
    flags_path,
    narrative_dims_for_scope,
)


def test_scope_configs_cover_arena_and_company():
    assert "arena" in SCOPE_CONFIGS
    assert "company" in SCOPE_CONFIGS
    assert "definition" not in narrative_dims_for_scope("arena")
    # company has no "definition" dim, all 8 COMPANY_DIMENSIONS are allowed
    from app import config as cfg
    assert set(narrative_dims_for_scope("company")) == set(cfg.COMPANY_DIMENSIONS)


def test_dimension_path_for_arena_and_company(tmp_path):
    arena_path = dimension_path(tmp_path, "arena", "cn-bci-industrialization", "participants")
    assert arena_path == tmp_path / "arenas" / "cn-bci-industrialization" / "participants.md"

    company_path = dimension_path(tmp_path, "company", "SSE_600519", "moat")
    assert company_path == tmp_path / "companies" / "SSE_600519" / "narratives" / "moat.md"

    company_kebab = dimension_path(tmp_path, "company", "SSE_600519", "growth_engine")
    assert company_kebab.name == "growth-engine.md"


def test_flags_path_for_arena_and_company(tmp_path):
    arena_flags = flags_path(tmp_path, "arena", "cn-bci-industrialization")
    assert arena_flags == tmp_path / "arenas" / "cn-bci-industrialization" / "narrative-flags.jsonl"

    company_flags = flags_path(tmp_path, "company", "SSE_600519")
    assert company_flags == tmp_path / "companies" / "SSE_600519" / "narrative-flags.jsonl"
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_narrative_proposals.py -q
```

Expected: FAIL with `ImportError` for `SCOPE_CONFIGS`, `dimension_path`, `flags_path`, or `narrative_dims_for_scope`.

- [ ] **Step 3: Commit tests only**

```bash
git add tests/test_narrative_proposals.py
git commit -m "test(narrative): define scope-aware surface"
```

### Task A2: Refactor narrative_proposals.py to scope-aware

**Files:**
- Modify: `app/io/narrative_proposals.py`
- Modify: `app/routes/arenas.py`
- Test: `tests/test_narrative_proposals.py`

- [ ] **Step 1: Replace the contents of `app/io/narrative_proposals.py` with this refactored version**

```python
from __future__ import annotations

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
            "existing_narrative_excerpt": existing_excerpt_loader(scope_type, scope_ref, dimension),
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
            "scope_count": 1 if proposals else 0,
            "dimension_count": len({proposal["dimension"] for proposal in proposals}),
            "unsupported_candidates_skipped": len(unmapped),
        },
    }
    if scope_type == "arena":
        # Phase 3A compatibility: keep legacy arena_count key.
        result["summary_stats"]["arena_count"] = result["summary_stats"]["scope_count"]
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
    arena slug — this is treated as `scope_type="arena"`, `scope_ref=<slug>`.
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
```

- [ ] **Step 2: Update `scripts/narrative_propose.py` to pass `scope_type="arena"` and new loader signature**

Open `scripts/narrative_propose.py` and replace the body of `cmd_propose` with:

```python
def cmd_propose(args: argparse.Namespace) -> int:
    base = Path(args.base)
    registry = ClaimRegistry(Path(args.registry_base))
    data = build_proposal_file(
        registry=registry,
        source_id=args.source_id,
        generated_at=now_iso(),
        scope_type="arena",
        scope_ref=args.arena,
        existing_excerpt_loader=lambda scope_type, scope_ref, dim: _existing_excerpt(base, scope_ref, dim),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ narrative proposals written to {out}")
    return 0
```

The `_existing_excerpt(base, arena_slug, dim)` helper is unchanged — only its call site changes.

- [ ] **Step 3: Update `scripts/narrative_flags.py` to pass `scope_type="arena"`**

Open `scripts/narrative_flags.py` and replace the body of `cmd_flags` with:

```python
def cmd_flags(args: argparse.Namespace) -> int:
    registry = ClaimRegistry(Path(args.registry_base))
    flags = scan_narrative_flags(
        registry=registry,
        base=Path(args.base),
        scope_type="arena",
        scope_ref=args.arena,
    )
    print(f"✓ narrative flags generated: {len(flags)}")
    return 0
```

- [ ] **Step 4: Update `app/routes/arenas.py` flag read to pass scope_type**

Open `app/routes/arenas.py`. Replace the line

```python
    narrative_flags = narrative_io.read_narrative_flags(slug)
```

with

```python
    narrative_flags = narrative_io.read_narrative_flags("arena", slug)
```

- [ ] **Step 5: Run Phase 3A tests (arena regression must stay green)**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_narrative_proposals.py \
  tests/test_narrative_apply_cli.py \
  tests/test_narrative_flags.py \
  tests/test_arenas_narrative_flags.py \
  tests/test_phase3a_narrative_end_to_end.py \
  -q
```

Expected: PASS. If a test fails, fix the refactor — do NOT edit the Phase 3A tests.

- [ ] **Step 6: Run guardrail diffs**

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl' 'companies/*/meta.md' 'companies/*/v0.md' 'companies/*/profile-*.md' 'companies/*/valuation.md' 'companies/*/trade-log.md'
```

Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add app/io/narrative_proposals.py scripts/narrative_propose.py scripts/narrative_flags.py app/routes/arenas.py tests/test_narrative_proposals.py
git commit -m "refactor(narrative): make narrative_proposals scope-aware"
```

---

## Part B: Company scope

### Task B1: Add failing company proposal generation tests

**Files:**
- Create: `tests/test_company_narrative_proposals.py`

- [ ] **Step 1: Write tests**

Create `tests/test_company_narrative_proposals.py` with this content:

```python
from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from app.io.narrative_proposals import (
    CLAIM_DIMENSION_TO_COMPANY_NARRATIVE,
    apply_proposal_file,
    build_proposal_file,
    map_claim_dimension,
    validate_proposal_decisions,
)


def _create_claim(
    registry,
    *,
    claim_text="茅台白酒业务毛利率长期稳定在 90% 以上",
    scope_type="company",
    scope_ref="SSE_600519",
    dimension_hint="moat",
    status="active",
    source_id="src-001",
):
    evidence = build_evidence_entry(
        source_id=source_id,
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    claim = registry.create_claim(
        claim_text=claim_text,
        scope_type=scope_type,
        scope_ref=scope_ref,
        claim_type="judgment",
        dimension_hint=dimension_hint,
        confidence="medium_high",
        as_of="2025-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    if status != "active":
        claim["status"] = status
        registry._rewrite_claim(claim)
    return claim


def test_map_company_dimension_hints():
    assert map_claim_dimension("moat", "company") == "moat"
    assert map_claim_dimension("financial_profile", "company") == "financial_profile"
    assert map_claim_dimension("catalysts", "company") == "catalysts"
    assert map_claim_dimension("thesis", "company") == "business_model"
    assert map_claim_dimension("risk", "company") == "risks"
    assert CLAIM_DIMENSION_TO_COMPANY_NARRATIVE["valuation"] == "valuation"


def test_build_company_proposal_file_groups_active_claims(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)

    result = build_proposal_file(
        registry=registry,
        source_id="src-001",
        generated_at="2026-04-30T12:00:00+00:00",
        scope_type="company",
        scope_ref="SSE_600519",
        existing_excerpt_loader=lambda scope_type, scope_ref, dim: f"existing {scope_type} {scope_ref} {dim}",
    )

    assert result["scope_type"] == "company"
    assert result["scope_ref"] == "SSE_600519"
    assert result["unmapped_claims"] == []
    assert result["summary_stats"] == {
        "total_proposals": 1,
        "scope_count": 1,
        "dimension_count": 1,
        "unsupported_candidates_skipped": 0,
    }
    proposal = result["proposals"][0]
    assert proposal["scope_type"] == "company"
    assert proposal["scope_ref"] == "SSE_600519"
    assert "arena_slug" not in proposal
    assert proposal["dimension"] == "moat"
    assert proposal["supported_by_claims"] == [claim["claim_id"]]
    assert proposal["existing_narrative_excerpt"] == "existing company SSE_600519 moat"


def test_build_company_proposal_file_filters_non_company_and_other_source(tmp_path):
    registry = ClaimRegistry(tmp_path)
    _create_claim(registry, status="retired")
    _create_claim(registry, scope_type="arena", scope_ref="cn-bci-industrialization")
    _create_claim(registry, source_id="src-other")

    result = build_proposal_file(
        registry=registry,
        source_id="src-001",
        generated_at="2026-04-30T12:00:00+00:00",
        scope_type="company",
        scope_ref="SSE_600519",
        existing_excerpt_loader=lambda scope_type, scope_ref, dim: "",
    )

    assert result["proposals"] == []
    assert result["unmapped_claims"] == []


def test_validate_company_proposal_rejects_arena_definition_semantics(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)
    data = {
        "source_id": "src-001",
        "proposal_version": "phase3a-v1",
        "scope_type": "company",
        "scope_ref": "SSE_600519",
        "proposals": [
            {
                "proposal_id": "np-001",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "dimension": "definition",
                "title": "bad",
                "body": "body",
                "supported_by_claims": [claim["claim_id"]],
                "source_ids": ["src-001"],
                "decision": "approve",
                "decision_reason": "ok",
            }
        ],
    }
    errors = validate_proposal_decisions(data, registry)
    assert any("invalid narrative dimension 'definition' for scope company" in e for e in errors)


def test_apply_company_proposal_writes_to_narratives_subdir(tmp_path):
    import json
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)
    narr_dir = tmp_path / "companies" / "SSE_600519" / "narratives"
    narr_dir.mkdir(parents=True)
    (narr_dir / "moat.md").write_text("# moat · 贵州茅台\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    data = {
        "source_id": "src-001",
        "proposal_version": "phase3a-v1",
        "scope_type": "company",
        "scope_ref": "SSE_600519",
        "proposals": [
            {
                "proposal_id": "np-001",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "dimension": "moat",
                "title": "品牌与经销体系的双重护城河",
                "body": "茅台的护城河来自品牌与渠道的双重稳定性。",
                "supported_by_claims": [claim["claim_id"]],
                "source_ids": ["src-001"],
                "decision": "approve",
                "decision_reason": "claim 支撑明确",
            }
        ],
    }
    pending.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    result = apply_proposal_file(
        data=data,
        registry=registry,
        base=tmp_path,
        pending_path=pending,
        today="2026-04-30",
        now="2026-04-30T12:00:00+00:00",
    )

    assert result == {"applied": 1, "rejected": 0, "deferred": 0}
    text = (narr_dir / "moat.md").read_text(encoding="utf-8")
    assert "### 品牌与经销体系的双重护城河" in text
    assert "茅台的护城河来自品牌与渠道的双重稳定性。" in text
    assert f"supported_by_claims: [{claim['claim_id']}]" in text
    archived = tmp_path / "data" / "pending" / "archive" / pending.name
    assert archived.exists()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_company_narrative_proposals.py -q
```

Expected: FAIL because `CLAIM_DIMENSION_TO_COMPANY_NARRATIVE` and/or company support in `build_proposal_file`/`validate_proposal_decisions` aren't wired. (If Task A2 already added them as designed, some tests may pass — in that case still commit the tests first, then continue.)

- [ ] **Step 3: Commit tests only**

```bash
git add tests/test_company_narrative_proposals.py
git commit -m "test(narrative): define company proposal generation"
```

### Task B2: Make company tests pass

**Files:**
- Modify (only if needed): `app/io/narrative_proposals.py`
- Test: `tests/test_company_narrative_proposals.py`

- [ ] **Step 1: Run the tests**

```bash
.venv/bin/python -m pytest tests/test_company_narrative_proposals.py -q
```

Expected: PASS. The refactor in Task A2 already added company support; this task is a verification step.

- [ ] **Step 2: Run Phase 3A regression**

```bash
.venv/bin/python -m pytest tests/test_narrative_proposals.py tests/test_arenas_narrative_flags.py -q
```

Expected: PASS.

- [ ] **Step 3: Run guardrail diff**

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl' 'companies/*/meta.md' 'companies/*/v0.md' 'companies/*/profile-*.md' 'companies/*/valuation.md' 'companies/*/trade-log.md'
```

Expected: no output.

- [ ] **Step 4: Commit (empty if no code change needed)**

If no code changes were needed, skip this commit. Otherwise:

```bash
git add app/io/narrative_proposals.py
git commit -m "feat(narrative): cover company scope in generator"
```

---

## Part C: Company CLI wrappers

### Task C1: Add failing company CLI tests

**Files:**
- Create: `tests/test_company_narrative_apply_cli.py`
- Create: `tests/test_company_narrative_flags.py`

- [ ] **Step 1: Write `tests/test_company_narrative_apply_cli.py`**

```python
import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import company_narrative_apply, company_narrative_propose


def _seed_company_claim(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    return registry.create_claim(
        claim_text="品牌力支撑长期毛利率",
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2025-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )


def test_company_narrative_propose_writes_pending_json(tmp_path):
    claim = _seed_company_claim(tmp_path)
    narr_dir = tmp_path / "companies" / "SSE_600519" / "narratives"
    narr_dir.mkdir(parents=True)
    (narr_dir / "moat.md").write_text("# moat\n\nold moat text", encoding="utf-8")
    out = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"

    rc = company_narrative_propose.cmd_propose(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            source_id="src-001",
            market="SSE",
            ticker="600519",
            out=str(out),
        )
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["scope_type"] == "company"
    assert data["scope_ref"] == "SSE_600519"
    proposal = data["proposals"][0]
    assert proposal["scope_type"] == "company"
    assert proposal["scope_ref"] == "SSE_600519"
    assert proposal["supported_by_claims"] == [claim["claim_id"]]
    assert proposal["existing_narrative_excerpt"].endswith("old moat text")


def test_company_narrative_apply_returns_nonzero_for_invalid_file(tmp_path, capsys):
    _seed_company_claim(tmp_path)
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    pending.write_text(
        json.dumps(
            {
                "source_id": "src-001",
                "proposal_version": "phase3a-v1",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "proposals": [
                    {
                        "proposal_id": "np-001",
                        "scope_type": "company",
                        "scope_ref": "SSE_600519",
                        "dimension": "moat",
                        "decision": "approve",
                        "decision_reason": "ok",
                        "body": None,
                        "supported_by_claims": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rc = company_narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )

    assert rc == 1
    captured = capsys.readouterr()
    assert "supported_by_claims required" in captured.err
    assert pending.exists()


def test_company_narrative_apply_applies_valid_file(tmp_path):
    claim = _seed_company_claim(tmp_path)
    narr_dir = tmp_path / "companies" / "SSE_600519" / "narratives"
    narr_dir.mkdir(parents=True)
    (narr_dir / "moat.md").write_text("# moat\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    pending.write_text(
        json.dumps(
            {
                "source_id": "src-001",
                "proposal_version": "phase3a-v1",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "proposals": [
                    {
                        "proposal_id": "np-001",
                        "scope_type": "company",
                        "scope_ref": "SSE_600519",
                        "dimension": "moat",
                        "title": "护城河",
                        "body": "品牌与经销体系是长期稳定的双重护城河。",
                        "supported_by_claims": [claim["claim_id"]],
                        "source_ids": ["src-001"],
                        "decision": "approve",
                        "decision_reason": "claim 支撑明确",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    rc = company_narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )

    assert rc == 0
    text = (narr_dir / "moat.md").read_text(encoding="utf-8")
    assert "品牌与经销体系是长期稳定的双重护城河。" in text
    assert (tmp_path / "data" / "pending" / "archive" / pending.name).exists()
```

- [ ] **Step 2: Write `tests/test_company_narrative_flags.py`**

```python
import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from app.io.narrative_proposals import read_narrative_flags, scan_narrative_flags
from scripts import company_narrative_flags


def _claim(registry, *, status="active", direction="supports"):
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction=direction,
        now="2026-04-30T12:00:00+00:00",
    )
    claim = registry.create_claim(
        claim_text="品牌力支撑长期毛利率",
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2025-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    if status != "active":
        claim["status"] = status
        registry._rewrite_claim(claim)
    return claim


def _write_segment(tmp_path, claim_id, dim="moat"):
    narr_dir = tmp_path / "companies" / "SSE_600519" / "narratives"
    narr_dir.mkdir(parents=True, exist_ok=True)
    (narr_dir / f"{dim.replace('_', '-')}.md").write_text(
        "# heading\n\n"
        "### 护城河\n\n"
        "status: active\n"
        "last_written: 2026-04-30\n"
        f"supported_by_claims: [{claim_id}]\n"
        "source_ids: [src-001]\n"
        "proposal_id: np-001\n\n"
        "正文。\n",
        encoding="utf-8",
    )


def test_scan_company_flags_no_flag_for_active(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry)
    _write_segment(tmp_path, claim["claim_id"])

    flags = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="company",
        scope_ref="SSE_600519",
        now="2026-04-30T12:00:00+00:00",
    )

    assert flags == []
    assert read_narrative_flags("company", "SSE_600519", base=tmp_path) == []


def test_scan_company_flags_writes_critical_for_retired(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, status="retired")
    _write_segment(tmp_path, claim["claim_id"])

    flags = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="company",
        scope_ref="SSE_600519",
        now="2026-04-30T12:00:00+00:00",
    )

    assert len(flags) == 1
    assert flags[0]["flag_level"] == "critical"
    assert flags[0]["reason"] == "supporting claim retired"
    assert flags[0]["scope_type"] == "company"
    assert flags[0]["scope_ref"] == "SSE_600519"
    stored = read_narrative_flags("company", "SSE_600519", base=tmp_path)
    assert len(stored) == 1


def test_scan_company_flags_dedups_on_rerun(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, direction="refutes")
    _write_segment(tmp_path, claim["claim_id"])

    first = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="company",
        scope_ref="SSE_600519",
        now="2026-04-30T12:00:00+00:00",
    )
    second = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="company",
        scope_ref="SSE_600519",
        now="2026-04-30T12:01:00+00:00",
    )

    assert len(first) == 1
    assert first[0]["flag_level"] == "significant"
    assert second == []


def test_company_narrative_flags_cli(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, status="retired")
    _write_segment(tmp_path, claim["claim_id"])

    rc = company_narrative_flags.cmd_flags(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            market="SSE",
            ticker="600519",
        )
    )

    assert rc == 0
    flag_file = tmp_path / "companies" / "SSE_600519" / "narrative-flags.jsonl"
    rows = [json.loads(line) for line in flag_file.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["reason"] == "supporting claim retired"
```

- [ ] **Step 3: Run and verify failure**

```bash
.venv/bin/python -m pytest tests/test_company_narrative_apply_cli.py tests/test_company_narrative_flags.py -q
```

Expected: FAIL with import errors for `scripts.company_narrative_apply`, `scripts.company_narrative_propose`, and `scripts.company_narrative_flags`.

- [ ] **Step 4: Commit tests only**

```bash
git add tests/test_company_narrative_apply_cli.py tests/test_company_narrative_flags.py
git commit -m "test(narrative): define company CLI behavior"
```

### Task C2: Implement company CLI wrappers

**Files:**
- Create: `scripts/company_narrative_propose.py`
- Create: `scripts/company_narrative_apply.py`
- Create: `scripts/company_narrative_flags.py`

- [ ] **Step 1: Create `scripts/company_narrative_propose.py`**

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.io import company as company_io
from app.io.claim_registry import ClaimRegistry
from app.io.narrative_proposals import build_proposal_file, now_iso


def _existing_excerpt(base: Path, market: str, ticker: str, dimension: str) -> str:
    md = company_io.read_narrative(ticker, market, dimension, base=base)
    return md[-1200:] if len(md) > 1200 else md


def cmd_propose(args: argparse.Namespace) -> int:
    base = Path(args.base)
    market = args.market.strip()
    ticker = args.ticker.strip()
    scope_ref = f"{market}_{ticker}"
    registry = ClaimRegistry(Path(args.registry_base))
    data = build_proposal_file(
        registry=registry,
        source_id=args.source_id,
        generated_at=now_iso(),
        scope_type="company",
        scope_ref=scope_ref,
        existing_excerpt_loader=lambda _st, _sr, dim: _existing_excerpt(base, market, ticker, dim),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ company narrative proposals written to {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="company_narrative_propose")
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--base", default=".")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--market", required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    return cmd_propose(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Create `scripts/company_narrative_apply.py`**

```python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.io.claim_registry import ClaimRegistry
from app.io.narrative_proposals import apply_proposal_file


def cmd_apply(args: argparse.Namespace) -> int:
    pending_path = Path(args.proposals)
    data = json.loads(pending_path.read_text(encoding="utf-8"))
    if data.get("scope_type") != "company":
        print(f"✗ expected scope_type=company, got {data.get('scope_type')!r}", file=sys.stderr)
        return 1
    registry = ClaimRegistry(Path(args.registry_base))
    try:
        counts = apply_proposal_file(
            data=data,
            registry=registry,
            base=Path(args.base),
            pending_path=pending_path,
        )
    except ValueError as exc:
        for line in str(exc).splitlines():
            print(f"✗ {line}", file=sys.stderr)
        return 1
    print(
        "✓ company narrative proposals applied: "
        f"applied={counts['applied']} rejected={counts['rejected']} deferred={counts['deferred']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="company_narrative_apply")
    parser.add_argument("--proposals", required=True)
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--base", default=".")
    args = parser.parse_args(argv)
    return cmd_apply(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Create `scripts/company_narrative_flags.py`**

```python
from __future__ import annotations

import argparse
from pathlib import Path

from app.io.claim_registry import ClaimRegistry
from app.io.narrative_proposals import scan_narrative_flags


def cmd_flags(args: argparse.Namespace) -> int:
    scope_ref = f"{args.market.strip()}_{args.ticker.strip()}"
    registry = ClaimRegistry(Path(args.registry_base))
    flags = scan_narrative_flags(
        registry=registry,
        base=Path(args.base),
        scope_type="company",
        scope_ref=scope_ref,
    )
    print(f"✓ company narrative flags generated: {len(flags)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="company_narrative_flags")
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--base", default=".")
    parser.add_argument("--market", required=True)
    parser.add_argument("--ticker", required=True)
    args = parser.parse_args(argv)
    return cmd_flags(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run company CLI tests**

```bash
.venv/bin/python -m pytest tests/test_company_narrative_apply_cli.py tests/test_company_narrative_flags.py -q
```

Expected: PASS.

- [ ] **Step 5: Run Phase 3A regression**

```bash
.venv/bin/python -m pytest \
  tests/test_narrative_proposals.py \
  tests/test_narrative_apply_cli.py \
  tests/test_narrative_flags.py \
  tests/test_arenas_narrative_flags.py \
  tests/test_phase3a_narrative_end_to_end.py \
  -q
```

Expected: PASS.

- [ ] **Step 6: Run guardrail diff**

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl' 'companies/*/meta.md' 'companies/*/v0.md' 'companies/*/profile-*.md' 'companies/*/valuation.md' 'companies/*/trade-log.md'
```

Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add scripts/company_narrative_propose.py scripts/company_narrative_apply.py scripts/company_narrative_flags.py
git commit -m "feat(narrative): add company proposal CLI workflow"
```

---

## Part D: Company detail page flag display

### Task D1: Add failing company flag display test

**Files:**
- Create: `tests/test_companies_narrative_flags.py`

- [ ] **Step 1: Write route/template test**

Create `tests/test_companies_narrative_flags.py` with this content:

```python
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.io import company as company_io
from app.routes import companies as companies_route


def test_company_detail_displays_narrative_flags(tmp_path, monkeypatch):
    # Redirect company IO to tmp_path.
    monkeypatch.setattr(companies_route.cfg, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(company_io.cfg, "COMPANIES_DIR", tmp_path / "companies")
    company_io.create_company(
        ticker="600519",
        market="SSE",
        name="贵州茅台",
        industry_slugs=[],
        currency="CNY",
        base=tmp_path,
    )
    flags_path = tmp_path / "companies" / "SSE_600519" / "narrative-flags.jsonl"
    flags_path.write_text(
        json.dumps(
            {
                "flag_id": "nf-0001",
                "created_at": "2026-04-30T12:00:00+00:00",
                "dimension": "moat",
                "segment_ref": "moat.md#np-001",
                "supported_by_claim": "clm-company-0001",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "flag_level": "critical",
                "reason": "supporting claim retired",
                "dismissed": False,
                "superseded_by": None,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    app = FastAPI()
    app.include_router(companies_route.router)
    client = TestClient(app)

    response = client.get("/companies/SSE_600519")

    assert response.status_code == 200
    assert "needs review" in response.text
    assert "supporting claim retired" in response.text
    assert "clm-company-0001" in response.text
```

- [ ] **Step 2: Run and verify failure**

```bash
.venv/bin/python -m pytest tests/test_companies_narrative_flags.py -q
```

Expected: FAIL — the company page does not yet read or render flags.

- [ ] **Step 3: Commit tests only**

```bash
git add tests/test_companies_narrative_flags.py
git commit -m "test(company): define narrative flag display"
```

### Task D2: Wire flags into company route and template

**Files:**
- Modify: `app/routes/companies.py`
- Modify: `app/templates/companies/detail.html`

- [ ] **Step 1: Add import in `app/routes/companies.py`**

Near the existing `from app.io import ...` block, add:

```python
from app.io import narrative_proposals as narrative_io
```

- [ ] **Step 2: Read flags in the detail view**

In `app/routes/companies.py`, inside the company detail handler, replace the existing narratives block

```python
    # 8 company-layer narratives (Plan 3 digest writes here)
    narratives = []
    for dim in cfg.COMPANY_DIMENSIONS:
        md = company_io.read_narrative(ticker, market, dim)
        has_content = md.strip() and "### 来源" in md
        narratives.append({
            "dim": dim,
            "label": _COMPANY_DIM_LABEL.get(dim, dim),
            "has_content": bool(has_content),
            "html": _md.markdown(md, extensions=["tables", "fenced_code"]) if md else "",
        })
```

with:

```python
    # 8 company-layer narratives (Plan 3 digest writes here, Phase 3B flags here)
    scope_ref = f"{market}_{ticker}"
    company_flags = narrative_io.read_narrative_flags("company", scope_ref)
    flags_by_dimension = {}
    for flag in company_flags:
        flags_by_dimension.setdefault(flag.get("dimension"), []).append(flag)
    narratives = []
    for dim in cfg.COMPANY_DIMENSIONS:
        md = company_io.read_narrative(ticker, market, dim)
        has_content = md.strip() and ("### 来源" in md or "proposal_id:" in md)
        dim_flags = flags_by_dimension.get(dim, [])
        narratives.append({
            "dim": dim,
            "label": _COMPANY_DIM_LABEL.get(dim, dim),
            "has_content": bool(has_content),
            "html": _md.markdown(md, extensions=["tables", "fenced_code"]) if md else "",
            "flags": dim_flags,
            "needs_review": bool(dim_flags),
        })
```

- [ ] **Step 3: Update template `app/templates/companies/detail.html`**

Replace the narrative block (lines around 27–41 in the current file) with:

```jinja2
<h2>8 维叙述（narratives）</h2>
{% for n in narratives %}
  <details {% if n.has_content %}open{% endif %}>
    <summary>
      <strong>{{ n.label }}</strong>
      <span class="hint">({{ n.dim }})</span>
      {% if not n.has_content %}<span class="badge badge-draft">空</span>{% endif %}
      {% if n.needs_review %}<span class="badge badge-draft">needs review</span>{% endif %}
    </summary>
    {% if n.flags %}
      <div class="narrative-flags">
        <strong>Review flags</strong>
        <ul>
          {% for flag in n.flags %}
          <li>
            <span class="badge badge-draft">{{ flag.flag_level }}</span>
            {{ flag.reason }} · {{ flag.supported_by_claim }} · {{ flag.segment_ref }} · {{ flag.created_at }}
          </li>
          {% endfor %}
        </ul>
      </div>
    {% endif %}
    {% if n.has_content %}
      <div class="narrative">{{ n.html|safe }}</div>
    {% else %}
      <p class="hint"><em>尚无来源块。下一次 ingest（年报 / 研报）会 append。</em></p>
    {% endif %}
  </details>
{% endfor %}
```

- [ ] **Step 4: Run company flag display test**

```bash
.venv/bin/python -m pytest tests/test_companies_narrative_flags.py -q
```

Expected: PASS.

- [ ] **Step 5: Run nearby company regression tests**

```bash
.venv/bin/python -m pytest tests/test_companies_routes.py tests/test_company_io.py tests/test_arenas_narrative_flags.py -q 2>/dev/null || \
.venv/bin/python -m pytest -k "compan" -q
```

Expected: PASS (or "no tests matched" if the first form misses; the second form covers anything company-related).

- [ ] **Step 6: Run guardrail diff**

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl' 'companies/*/meta.md' 'companies/*/v0.md' 'companies/*/profile-*.md' 'companies/*/valuation.md' 'companies/*/trade-log.md'
```

Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add app/routes/companies.py app/templates/companies/detail.html
git commit -m "feat(company): show narrative review flags"
```

---

## Part E: End-to-end verification

### Task E1: Add and run the company e2e test

**Files:**
- Create: `tests/test_phase3b_narrative_end_to_end.py`

- [ ] **Step 1: Write e2e test**

Create `tests/test_phase3b_narrative_end_to_end.py` with this content:

```python
import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import (
    company_narrative_apply,
    company_narrative_flags,
    company_narrative_propose,
)


def test_phase3b_propose_apply_flag_flow(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    claim = registry.create_claim(
        claim_text="品牌力支撑长期毛利率",
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2025-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    narr_dir = tmp_path / "companies" / "SSE_600519" / "narratives"
    narr_dir.mkdir(parents=True)
    (narr_dir / "moat.md").write_text("# moat\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"

    rc = company_narrative_propose.cmd_propose(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            source_id="src-001",
            market="SSE",
            ticker="600519",
            out=str(pending),
        )
    )
    assert rc == 0

    data = json.loads(pending.read_text(encoding="utf-8"))
    data["proposals"][0]["title"] = "护城河"
    data["proposals"][0]["body"] = "品牌与经销体系是长期双重护城河。"
    data["proposals"][0]["decision"] = "approve"
    data["proposals"][0]["decision_reason"] = "claim 支撑明确"
    pending.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    rc = company_narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )
    assert rc == 0
    assert "品牌与经销体系是长期双重护城河。" in (narr_dir / "moat.md").read_text(encoding="utf-8")

    claim["status"] = "retired"
    registry._rewrite_claim(claim)
    rc = company_narrative_flags.cmd_flags(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            market="SSE",
            ticker="600519",
        )
    )
    assert rc == 0
    flags = (tmp_path / "companies" / "SSE_600519" / "narrative-flags.jsonl").read_text(encoding="utf-8")
    assert "supporting claim retired" in flags
```

- [ ] **Step 2: Run e2e test**

```bash
.venv/bin/python -m pytest tests/test_phase3b_narrative_end_to_end.py -q
```

Expected: PASS.

- [ ] **Step 3: Run all Phase 3A + 3B tests together**

```bash
.venv/bin/python -m pytest \
  tests/test_narrative_proposals.py \
  tests/test_narrative_apply_cli.py \
  tests/test_narrative_flags.py \
  tests/test_arenas_narrative_flags.py \
  tests/test_phase3a_narrative_end_to_end.py \
  tests/test_company_narrative_proposals.py \
  tests/test_company_narrative_apply_cli.py \
  tests/test_company_narrative_flags.py \
  tests/test_companies_narrative_flags.py \
  tests/test_phase3b_narrative_end_to_end.py \
  -q
```

Expected: PASS.

- [ ] **Step 4: Run nearby regression tests**

```bash
.venv/bin/python -m pytest \
  tests/test_claim_registry.py \
  tests/test_claim_matching.py \
  tests/test_ingest_match_cli.py \
  tests/test_ingest_apply_cli.py \
  tests/test_arenas_narrative.py \
  -q
```

Expected: PASS.

- [ ] **Step 5: Run guardrail diffs**

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl' 'companies/*/meta.md' 'companies/*/v0.md' 'companies/*/profile-*.md' 'companies/*/valuation.md' 'companies/*/trade-log.md'
```

Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add tests/test_phase3b_narrative_end_to_end.py
git commit -m "test(narrative): cover Phase 3B company flow"
```

---

## 3. Manual smoke test after implementation

Run this only after all tasks pass.

- [ ] **Step 1: Find a company claim source**

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
path = Path('data/claims/companies.jsonl')
if not path.exists():
    print('no data/claims/companies.jsonl')
    raise SystemExit(0)
for line in path.read_text(encoding='utf-8').splitlines():
    if not line.strip():
        continue
    claim = json.loads(line)
    if claim.get('status') == 'active' and claim.get('supporting_evidence'):
        ref = claim.get('scope_ref', '')
        print(ref, claim['supporting_evidence'][0]['source_id'], claim['claim_id'])
        break
PY
```

Expected: either prints `<MARKET_TICKER> source_id claim_id`, or says no company claim data. If no data exists, skip manual smoke and rely on tests.

- [ ] **Step 2: Generate a real pending proposal**

Split the output `scope_ref` into `MARKET` / `TICKER` (on the first `_`), then:

```bash
.venv/bin/python scripts/company_narrative_propose.py \
  --registry-base data \
  --base . \
  --source-id <source_id> \
  --market <MARKET> \
  --ticker <TICKER> \
  --out data/pending/narrative-proposals-<source_id>.json
```

Expected: writes a pending JSON file with `scope_type=="company"`. Inspect it manually; each proposal's `body` should be `null`.

- [ ] **Step 3: Do not apply real pending file unless user approves**

Stop here unless the user explicitly asks to fill and apply a real company narrative proposal. Applying writes to `companies/<MARKET>_<TICKER>/narratives/*.md`.

---

## 4. Final verification before reporting complete

- [ ] Run all Phase 3A + 3B tests:

```bash
.venv/bin/python -m pytest \
  tests/test_narrative_proposals.py \
  tests/test_narrative_apply_cli.py \
  tests/test_narrative_flags.py \
  tests/test_arenas_narrative_flags.py \
  tests/test_phase3a_narrative_end_to_end.py \
  tests/test_company_narrative_proposals.py \
  tests/test_company_narrative_apply_cli.py \
  tests/test_company_narrative_flags.py \
  tests/test_companies_narrative_flags.py \
  tests/test_phase3b_narrative_end_to_end.py \
  -q
```

- [ ] Run nearby regression tests:

```bash
.venv/bin/python -m pytest \
  tests/test_claim_registry.py \
  tests/test_claim_matching.py \
  tests/test_ingest_match_cli.py \
  tests/test_ingest_apply_cli.py \
  tests/test_arenas_narrative.py \
  -q
```

- [ ] Run guardrail diff:

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl' 'companies/*/meta.md' 'companies/*/v0.md' 'companies/*/profile-*.md' 'companies/*/valuation.md' 'companies/*/trade-log.md'
```

Expected: no output.

- [ ] Check no Python LLM imports were added:

```bash
grep -R "anthropic\|openai" app scripts tests | grep -v __pycache__ || true
```

Expected: no Phase 3B files contain `anthropic` or `openai`.

- [ ] Check working tree summary:

```bash
git status --short
```

Expected: only intended Phase 3B files changed, plus any commits created during task execution.

---

## 5. Self-review against spec

Spec coverage:
- Scope-aware refactor (Task A2) keeps Phase 3A arena JSON contract, CLI flags, route behavior, and test suite intact while introducing a `SCOPE_CONFIGS` registry.
- Company proposal generation (Tasks B1/B2) emits `scope_type="company"` / `scope_ref="<MARKET>_<TICKER>"` pending files with a dedicated mapping.
- Company decision validation rejects arena-only semantics (e.g., `dimension="definition"` for company scope triggers a clear "invalid narrative dimension for scope company" error).
- Company Markdown appends (Task B2 validation of company apply) land in `companies/<key>/narratives/<dim-kebab>.md` — the existing narrative subdirectory — without touching `meta.md`, `v0.md`, `profile-*.md`, `valuation.md`, `trade-log.md`, or legacy `claims.jsonl`.
- Company flags (Task C1 tests + Task B2 generic `scan_narrative_flags`) live at `companies/<key>/narrative-flags.jsonl` with the same dedup key as arena.
- Company CLI (Task C2) mirrors arena trio: `--market` + `--ticker` builds `scope_ref`.
- Company detail page (Task D2) reads flags and shows `needs review` plus flag details per dimension.
- End-to-end (Task E1) exercises propose → approve → apply → retire claim → scan flags.
- Guardrails (Section 0, Part E) forbid LLM imports, V0 claim mutation, non-narrative company file edits, and industry scope.

Placeholder scan: every code step includes a concrete code block. No `TODO`, `TBD`, or "add tests for the above" instructions.

Type / name consistency: `SCOPE_CONFIGS`, `narrative_dims_for_scope`, `dimension_path`, `flags_path`, `build_proposal_file(..., scope_type=, scope_ref=)`, `validate_proposal_decisions`, `apply_proposal_file`, `read_narrative_flags(scope_type, scope_ref, base=)`, `scan_narrative_flags(..., scope_type=, scope_ref=)`, `cmd_propose`, `cmd_apply`, `cmd_flags` appear with the same signatures across implementation tasks and test files.

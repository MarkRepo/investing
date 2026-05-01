# Phase 3A Arena Investment Narrative Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Phase 3A: claim-driven pending arena narrative proposals, approved Markdown writes, manual narrative review flags, and minimal arena page flag display.

**Architecture:** Add one focused IO module, `app/io/narrative_proposals.py`, that owns proposal generation, decision validation, Markdown append, flag scanning, and flag reads. Add three thin CLI wrappers in `scripts/` for propose/apply/flags. Reuse Phase 2 `ClaimRegistry` as the source of truth for active arena claims; Python never writes narrative prose with an LLM and never rewrites existing narrative text.

**Tech Stack:** Python 3 stdlib (`argparse`, `json`, `pathlib`, `datetime`, `re`, `shutil`), pytest, JSON/JSONL, Markdown files, existing FastAPI/Jinja arena route/template.

---

## 0. Mandatory guardrails

Before every task, re-read this section. If implementation drifts into a forbidden item, stop and revert that drift before continuing.

**Allowed Phase 3A outputs:**
- `data/pending/narrative-proposals-<source_id>.json`
- `data/pending/archive/narrative-proposals-<source_id>.json`
- `data/audit/narrative-events.jsonl`
- `arenas/<slug>/<dimension-kebab>.md` appends for approved/edit proposals only
- `arenas/<slug>/narrative-flags.jsonl`
- minimal arena detail page display of flags

**Forbidden in this plan:**
- Do not call `anthropic`, `openai`, browser automation, or any LLM API from Python.
- Do not generate final narrative prose automatically in Python.
- Do not auto-rewrite existing arena narrative Markdown.
- Do not modify `arenas/<slug>/definition.md` from proposal apply.
- Do not implement industry 8 or company 9 narrative.
- Do not implement review queue, cron, event adapters, daemons, or periodic scans.
- Do not modify `app/io/claims.py`.
- Do not modify `companies/*/claims.jsonl`.
- Do not add proposal approval/editing UI.
- Do not add dismiss behavior for flags.

**Verification after each implementation task:**

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl'
```

Expected: no diff. If there is a diff, revert it before continuing.

---

## 1. File map

### Create

- `app/io/narrative_proposals.py` — Phase 3A proposal/flag domain logic: generation, validation, append, audit, flag scan/read.
- `scripts/narrative_propose.py` — CLI wrapper: registry + source + arena → pending proposal JSON.
- `scripts/narrative_apply.py` — CLI wrapper: filled proposal JSON → arena Markdown appends + audit + archive pending file.
- `scripts/narrative_flags.py` — CLI wrapper: arena Markdown + claim registry → `narrative-flags.jsonl`.
- `tests/test_narrative_proposals.py` — proposal generation and validation unit tests.
- `tests/test_narrative_apply_cli.py` — apply CLI tests.
- `tests/test_narrative_flags.py` — flag scan/read tests.
- `tests/test_arenas_narrative_flags.py` — arena route/template flag display tests.

### Modify

- `app/routes/arenas.py` — read narrative flags and pass per-dimension flags to template.
- `app/templates/arenas/detail.html` — show `needs review` badges and flag details.

### Do not modify

- `app/io/claims.py`
- `companies/*/claims.jsonl`
- `scripts/ingest_aggregate.py`
- `scripts/ingest_match.py`
- `scripts/ingest_apply.py`
- `scripts/preprocess_report.py`
- `industries/**`
- `companies/**` except test tmp dirs created inside pytest

---

## 2. Data contracts to use exactly

### 2.1 Proposal file shape

`scripts/narrative_propose.py` writes this structure:

```python
{
    "source_id": "src-001",
    "generated_at": "2026-04-30T12:00:00+00:00",
    "proposal_version": "phase3a-v1",
    "scope_type": "arena",
    "proposals": [
        {
            "proposal_id": "np-001",
            "arena_slug": "cn-bci-industrialization",
            "dimension": "participants",
            "title": "Draft narrative for participants",
            "body": None,
            "supported_by_claims": ["clm-arena-0001"],
            "source_ids": ["src-001"],
            "evidence_summary": [
                {
                    "claim_id": "clm-arena-0001",
                    "claim_text": "...",
                    "confidence": "medium_high",
                    "as_of": "2024-12-31",
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
        "arena_count": 1,
        "dimension_count": 1,
        "unsupported_candidates_skipped": 0,
    },
}
```

### 2.2 Decision rules

Valid decisions: `approve`, `edit`, `reject`, `defer`.

Validation rules:
- every proposal must have a valid decision before apply;
- every decision must have non-empty `decision_reason`;
- `approve` must have non-empty `body`;
- `edit` must have non-empty `edited_body`;
- `approve`/`edit` body must not be obvious placeholder text: `待 Claude`, `待填写`, `TODO`, `TBD`, `<body>`;
- `approve`/`edit` must have non-empty `supported_by_claims`;
- every supported claim must exist in registry and have `status == "active"`;
- dimension must be an arena narrative dimension and must not be `definition`.

### 2.3 Markdown append format

Use this exact block for approved/edit proposals:

```markdown
### {title}

status: active
last_written: {YYYY-MM-DD}
supported_by_claims: [{claim_id_1}, {claim_id_2}]
source_ids: [{source_id_1}, {source_id_2}]
proposal_id: {proposal_id}

{body}
```

The target path is `arenas/<slug>/<dimension-kebab>.md`, where `dimension-kebab = dimension.replace("_", "-")`.

### 2.4 Flag file shape

`arenas/<slug>/narrative-flags.jsonl` uses one JSON object per line:

```python
{
    "flag_id": "nf-0001",
    "created_at": "2026-04-30T12:00:00+00:00",
    "dimension": "participants",
    "segment_ref": "participants.md#np-001",
    "supported_by_claim": "clm-arena-0001",
    "flag_level": "critical",
    "reason": "supporting claim retired",
    "dismissed": False,
    "superseded_by": None,
}
```

Do not duplicate active flags with the same `(dimension, segment_ref, supported_by_claim, reason)`.

---

## Part A: Proposal module core

### Task A1: Add failing proposal generation tests

**Files:**
- Create: `tests/test_narrative_proposals.py`
- Create later: `app/io/narrative_proposals.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_narrative_proposals.py` with this content:

```python
from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from app.io.narrative_proposals import (
    PROPOSAL_VERSION,
    build_proposal_file,
    map_claim_dimension,
)


def _create_claim(
    registry,
    *,
    claim_text="侵入式脑机接口商业化主要依赖医疗场景验证",
    scope_type="arena",
    scope_ref="cn-bci-industrialization",
    dimension_hint="competitive_position",
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
        as_of="2024-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    if status != "active":
        claim["status"] = status
        registry._rewrite_claim(claim)
    return claim


def test_map_claim_dimension_known_values():
    assert map_claim_dimension("competitive_position") == "participants"
    assert map_claim_dimension("technology") == "decisive_factors"
    assert map_claim_dimension("stage_gate") == "trajectory"
    assert map_claim_dimension("risk") == "narratives"
    assert map_claim_dimension("valuation") == "investment_view"


def test_build_proposal_file_groups_active_arena_claims_by_dimension(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)

    result = build_proposal_file(
        registry=registry,
        arena_slug="cn-bci-industrialization",
        source_id="src-001",
        generated_at="2026-04-30T12:00:00+00:00",
        existing_excerpt_loader=lambda arena, dim: f"existing {arena} {dim}",
    )

    assert result["proposal_version"] == PROPOSAL_VERSION
    assert result["source_id"] == "src-001"
    assert result["scope_type"] == "arena"
    assert result["unmapped_claims"] == []
    assert result["summary_stats"] == {
        "total_proposals": 1,
        "arena_count": 1,
        "dimension_count": 1,
        "unsupported_candidates_skipped": 0,
    }
    proposal = result["proposals"][0]
    assert proposal["proposal_id"] == "np-001"
    assert proposal["arena_slug"] == "cn-bci-industrialization"
    assert proposal["dimension"] == "participants"
    assert proposal["body"] is None
    assert proposal["supported_by_claims"] == [claim["claim_id"]]
    assert proposal["source_ids"] == ["src-001"]
    assert proposal["existing_narrative_excerpt"] == "existing cn-bci-industrialization participants"
    assert proposal["decision"] is None
    assert proposal["decision_reason"] is None
    assert proposal["edited_title"] is None
    assert proposal["edited_body"] is None
    assert proposal["evidence_summary"] == [
        {
            "claim_id": claim["claim_id"],
            "claim_text": "侵入式脑机接口商业化主要依赖医疗场景验证",
            "confidence": "medium_high",
            "as_of": "2024-12-31",
            "evidence_source_ids": ["src-001"],
        }
    ]


def test_build_proposal_file_filters_non_active_non_arena_and_other_source(tmp_path):
    registry = ClaimRegistry(tmp_path)
    _create_claim(registry, status="retired")
    _create_claim(registry, scope_type="company", scope_ref="SSE_600519")
    _create_claim(registry, source_id="src-other")

    result = build_proposal_file(
        registry=registry,
        arena_slug="cn-bci-industrialization",
        source_id="src-001",
        generated_at="2026-04-30T12:00:00+00:00",
        existing_excerpt_loader=lambda arena, dim: "",
    )

    assert result["proposals"] == []
    assert result["unmapped_claims"] == []
    assert result["summary_stats"] == {
        "total_proposals": 0,
        "arena_count": 0,
        "dimension_count": 0,
        "unsupported_candidates_skipped": 0,
    }


def test_build_proposal_file_records_unmapped_claims_without_proposals(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry, dimension_hint="unmapped_dimension")

    result = build_proposal_file(
        registry=registry,
        arena_slug="cn-bci-industrialization",
        source_id="src-001",
        generated_at="2026-04-30T12:00:00+00:00",
        existing_excerpt_loader=lambda arena, dim: "",
    )

    assert result["proposals"] == []
    assert result["unmapped_claims"] == [
        {
            "claim_id": claim["claim_id"],
            "claim_text": claim["claim_text"],
            "dimension_hint": "unmapped_dimension",
            "reason": "unmapped dimension_hint",
        }
    ]
    assert result["summary_stats"]["unsupported_candidates_skipped"] == 1
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_narrative_proposals.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.io.narrative_proposals'`.

- [ ] **Step 3: Commit tests only**

```bash
git add tests/test_narrative_proposals.py
git commit -m "test(narrative): define arena proposal generation"
```

### Task A2: Implement proposal generation

**Files:**
- Create: `app/io/narrative_proposals.py`
- Test: `tests/test_narrative_proposals.py`

- [ ] **Step 1: Add implementation**

Create `app/io/narrative_proposals.py` with this content:

```python
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
```

- [ ] **Step 2: Run tests and verify pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_narrative_proposals.py -q
```

Expected: PASS.

- [ ] **Step 3: Run guardrail diff**

Run:

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl'
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add app/io/narrative_proposals.py tests/test_narrative_proposals.py
git commit -m "feat(narrative): build arena proposal skeletons"
```

---

## Part B: Proposal validation and apply logic

### Task B1: Add failing apply validation and append tests

**Files:**
- Modify: `tests/test_narrative_proposals.py`
- Modify later: `app/io/narrative_proposals.py`

- [ ] **Step 1: Append tests**

Append this content to `tests/test_narrative_proposals.py`:

```python
from app.io.narrative_proposals import (
    apply_proposal_file,
    validate_proposal_decisions,
)


def _proposal_file(claim_id):
    return {
        "source_id": "src-001",
        "generated_at": "2026-04-30T12:00:00+00:00",
        "proposal_version": "phase3a-v1",
        "scope_type": "arena",
        "proposals": [
            {
                "proposal_id": "np-001",
                "arena_slug": "cn-bci-industrialization",
                "dimension": "participants",
                "title": "参与者格局变化",
                "body": "医疗场景仍是脑机接口商业化的主要验证路径。",
                "supported_by_claims": [claim_id],
                "source_ids": ["src-001"],
                "evidence_summary": [],
                "existing_narrative_excerpt": "",
                "decision": "approve",
                "decision_reason": "claim 支撑明确",
                "edited_title": None,
                "edited_body": None,
            }
        ],
        "unmapped_claims": [],
        "summary_stats": {},
    }


def test_validate_proposal_decisions_rejects_missing_body_and_placeholder(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)
    data = _proposal_file(claim["claim_id"])
    data["proposals"][0]["body"] = None

    errors = validate_proposal_decisions(data, registry)
    assert "np-001: approve requires non-empty body" in errors

    data["proposals"][0]["body"] = "待填写"
    errors = validate_proposal_decisions(data, registry)
    assert "np-001: body must not be placeholder text" in errors


def test_validate_proposal_decisions_rejects_retired_claim_and_definition(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry, status="retired")
    data = _proposal_file(claim["claim_id"])
    data["proposals"][0]["dimension"] = "definition"

    errors = validate_proposal_decisions(data, registry)

    assert "np-001: dimension definition cannot be written by narrative proposals" in errors
    assert f"np-001: supported claim {claim['claim_id']} is not active" in errors


def test_apply_proposal_file_appends_markdown_audit_and_archives(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)
    arena_dir = tmp_path / "arenas" / "cn-bci-industrialization"
    arena_dir.mkdir(parents=True)
    target = arena_dir / "participants.md"
    target.write_text("# 参与者与相对位置 · 脑机接口\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    data = _proposal_file(claim["claim_id"])
    pending.write_text(__import__("json").dumps(data, ensure_ascii=False), encoding="utf-8")

    result = apply_proposal_file(
        data=data,
        registry=registry,
        base=tmp_path,
        pending_path=pending,
        today="2026-04-30",
        now="2026-04-30T12:00:00+00:00",
    )

    assert result == {"applied": 1, "rejected": 0, "deferred": 0}
    text = target.read_text(encoding="utf-8")
    assert "### 参与者格局变化" in text
    assert "status: active" in text
    assert "last_written: 2026-04-30" in text
    assert f"supported_by_claims: [{claim['claim_id']}]" in text
    assert "source_ids: [src-001]" in text
    assert "proposal_id: np-001" in text
    assert "医疗场景仍是脑机接口商业化的主要验证路径。" in text
    audit_lines = (tmp_path / "data" / "audit" / "narrative-events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(audit_lines) == 1
    archived = tmp_path / "data" / "pending" / "archive" / pending.name
    assert archived.exists()
    assert not pending.exists()


def test_apply_proposal_file_uses_edited_body(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)
    arena_dir = tmp_path / "arenas" / "cn-bci-industrialization"
    arena_dir.mkdir(parents=True)
    (arena_dir / "participants.md").write_text("# x\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    data = _proposal_file(claim["claim_id"])
    data["proposals"][0]["decision"] = "edit"
    data["proposals"][0]["edited_title"] = "编辑后的标题"
    data["proposals"][0]["edited_body"] = "编辑后的正文。"
    pending.write_text(__import__("json").dumps(data, ensure_ascii=False), encoding="utf-8")

    result = apply_proposal_file(
        data=data,
        registry=registry,
        base=tmp_path,
        pending_path=pending,
        today="2026-04-30",
        now="2026-04-30T12:00:00+00:00",
    )

    assert result["applied"] == 1
    text = (arena_dir / "participants.md").read_text(encoding="utf-8")
    assert "### 编辑后的标题" in text
    assert "编辑后的正文。" in text
    assert "医疗场景仍是脑机接口商业化的主要验证路径。" not in text
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_narrative_proposals.py -q
```

Expected: FAIL with `ImportError` for `apply_proposal_file` or `validate_proposal_decisions`.

- [ ] **Step 3: Commit tests only**

```bash
git add tests/test_narrative_proposals.py
git commit -m "test(narrative): define proposal apply behavior"
```

### Task B2: Implement proposal validation and apply

**Files:**
- Modify: `app/io/narrative_proposals.py`
- Test: `tests/test_narrative_proposals.py`

- [ ] **Step 1: Append implementation**

Append this code to `app/io/narrative_proposals.py`:

```python

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
```

- [ ] **Step 2: Run tests and verify pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_narrative_proposals.py -q
```

Expected: PASS.

- [ ] **Step 3: Run guardrail diff**

Run:

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl'
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add app/io/narrative_proposals.py tests/test_narrative_proposals.py
git commit -m "feat(narrative): apply approved arena proposals"
```

---

## Part C: CLI wrappers

### Task C1: Add failing CLI tests

**Files:**
- Create: `tests/test_narrative_apply_cli.py`
- Create later: `scripts/narrative_propose.py`
- Create later: `scripts/narrative_apply.py`

- [ ] **Step 1: Write CLI tests**

Create `tests/test_narrative_apply_cli.py` with this content:

```python
import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import narrative_apply, narrative_propose


def _seed_claim(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    return registry.create_claim(
        claim_text="脑机接口商业化依赖医疗场景验证",
        scope_type="arena",
        scope_ref="cn-bci-industrialization",
        claim_type="judgment",
        dimension_hint="competitive_position",
        confidence="medium_high",
        as_of="2024-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )


def test_narrative_propose_cli_writes_pending_json(tmp_path):
    claim = _seed_claim(tmp_path)
    arena_dir = tmp_path / "arenas" / "cn-bci-industrialization"
    arena_dir.mkdir(parents=True)
    (arena_dir / "participants.md").write_text("# participants\n\nold text", encoding="utf-8")
    out = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"

    rc = narrative_propose.cmd_propose(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            source_id="src-001",
            arena="cn-bci-industrialization",
            out=str(out),
        )
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source_id"] == "src-001"
    assert data["proposals"][0]["supported_by_claims"] == [claim["claim_id"]]
    assert data["proposals"][0]["existing_narrative_excerpt"].endswith("old text")


def test_narrative_apply_cli_returns_nonzero_for_invalid_file(tmp_path, capsys):
    _seed_claim(tmp_path)
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    pending.write_text(
        json.dumps(
            {
                "source_id": "src-001",
                "proposal_version": "phase3a-v1",
                "scope_type": "arena",
                "proposals": [
                    {
                        "proposal_id": "np-001",
                        "arena_slug": "cn-bci-industrialization",
                        "dimension": "participants",
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

    rc = narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )

    assert rc == 1
    captured = capsys.readouterr()
    assert "supported_by_claims required" in captured.err
    assert pending.exists()


def test_narrative_apply_cli_applies_valid_file(tmp_path):
    claim = _seed_claim(tmp_path)
    arena_dir = tmp_path / "arenas" / "cn-bci-industrialization"
    arena_dir.mkdir(parents=True)
    (arena_dir / "participants.md").write_text("# participants\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    pending.write_text(
        json.dumps(
            {
                "source_id": "src-001",
                "proposal_version": "phase3a-v1",
                "scope_type": "arena",
                "proposals": [
                    {
                        "proposal_id": "np-001",
                        "arena_slug": "cn-bci-industrialization",
                        "dimension": "participants",
                        "title": "参与者格局",
                        "body": "医疗场景是主要验证路径。",
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

    rc = narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )

    assert rc == 0
    assert "医疗场景是主要验证路径。" in (arena_dir / "participants.md").read_text(encoding="utf-8")
    assert (tmp_path / "data" / "pending" / "archive" / pending.name).exists()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_narrative_apply_cli.py -q
```

Expected: FAIL with import errors for `scripts.narrative_apply` and `scripts.narrative_propose`.

- [ ] **Step 3: Commit tests only**

```bash
git add tests/test_narrative_apply_cli.py
git commit -m "test(narrative): define proposal CLI behavior"
```

### Task C2: Implement CLI wrappers

**Files:**
- Create: `scripts/narrative_propose.py`
- Create: `scripts/narrative_apply.py`
- Test: `tests/test_narrative_apply_cli.py`

- [ ] **Step 1: Create `scripts/narrative_propose.py`**

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.io import arenas as arenas_io
from app.io.claim_registry import ClaimRegistry
from app.io.narrative_proposals import build_proposal_file, now_iso


def _existing_excerpt(base: Path, arena_slug: str, dimension: str) -> str:
    md = arenas_io.read_narrative(arena_slug, dimension, base=base)
    return md[-1200:] if len(md) > 1200 else md


def cmd_propose(args: argparse.Namespace) -> int:
    base = Path(args.base)
    registry = ClaimRegistry(Path(args.registry_base))
    data = build_proposal_file(
        registry=registry,
        arena_slug=args.arena,
        source_id=args.source_id,
        generated_at=now_iso(),
        existing_excerpt_loader=lambda arena, dim: _existing_excerpt(base, arena, dim),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ narrative proposals written to {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="narrative_propose")
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--base", default=".")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--arena", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    return cmd_propose(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Create `scripts/narrative_apply.py`**

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
        "✓ narrative proposals applied: "
        f"applied={counts['applied']} rejected={counts['rejected']} deferred={counts['deferred']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="narrative_apply")
    parser.add_argument("--proposals", required=True)
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--base", default=".")
    args = parser.parse_args(argv)
    return cmd_apply(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run CLI tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_narrative_apply_cli.py -q
```

Expected: PASS.

- [ ] **Step 4: Run proposal tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_narrative_proposals.py -q
```

Expected: PASS.

- [ ] **Step 5: Run guardrail diff**

Run:

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl'
```

Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add scripts/narrative_propose.py scripts/narrative_apply.py tests/test_narrative_apply_cli.py
git commit -m "feat(narrative): add proposal CLI workflow"
```

---

## Part D: Narrative flags

### Task D1: Add failing flag tests

**Files:**
- Create: `tests/test_narrative_flags.py`
- Modify later: `app/io/narrative_proposals.py`
- Create later: `scripts/narrative_flags.py`

- [ ] **Step 1: Write flag tests**

Create `tests/test_narrative_flags.py` with this content:

```python
import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from app.io.narrative_proposals import read_narrative_flags, scan_narrative_flags
from scripts import narrative_flags


def _claim(registry, *, status="active", direction="supports"):
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction=direction,
        now="2026-04-30T12:00:00+00:00",
    )
    claim = registry.create_claim(
        claim_text="医疗场景支撑脑机接口商业化验证",
        scope_type="arena",
        scope_ref="cn-bci-industrialization",
        claim_type="judgment",
        dimension_hint="competitive_position",
        confidence="medium_high",
        as_of="2024-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    if status != "active":
        claim["status"] = status
        registry._rewrite_claim(claim)
    return claim


def _write_segment(tmp_path, claim_id):
    arena_dir = tmp_path / "arenas" / "cn-bci-industrialization"
    arena_dir.mkdir(parents=True)
    (arena_dir / "participants.md").write_text(
        "# participants\n\n"
        "### 参与者格局\n\n"
        "status: active\n"
        "last_written: 2026-04-30\n"
        f"supported_by_claims: [{claim_id}]\n"
        "source_ids: [src-001]\n"
        "proposal_id: np-001\n\n"
        "正文。\n",
        encoding="utf-8",
    )


def test_scan_narrative_flags_no_flag_for_active_supporting_claim(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry)
    _write_segment(tmp_path, claim["claim_id"])

    flags = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        arena_slug="cn-bci-industrialization",
        now="2026-04-30T12:00:00+00:00",
    )

    assert flags == []
    assert read_narrative_flags("cn-bci-industrialization", base=tmp_path) == []


def test_scan_narrative_flags_writes_critical_for_retired_and_missing(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, status="retired")
    _write_segment(tmp_path, claim["claim_id"])
    with (tmp_path / "arenas" / "cn-bci-industrialization" / "participants.md").open("a", encoding="utf-8") as f:
        f.write("\n### Missing\n\nsupported_by_claims: [clm-arena-9999]\nproposal_id: np-002\n\nbody\n")

    flags = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        arena_slug="cn-bci-industrialization",
        now="2026-04-30T12:00:00+00:00",
    )

    assert [f["flag_level"] for f in flags] == ["critical", "critical"]
    assert {f["reason"] for f in flags} == {"supporting claim retired", "supporting claim missing"}
    stored = read_narrative_flags("cn-bci-industrialization", base=tmp_path)
    assert len(stored) == 2
    assert stored[0]["flag_id"] == "nf-0001"
    assert stored[1]["flag_id"] == "nf-0002"


def test_scan_narrative_flags_writes_significant_for_refuting_evidence_and_dedups(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, direction="refutes")
    _write_segment(tmp_path, claim["claim_id"])

    first = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        arena_slug="cn-bci-industrialization",
        now="2026-04-30T12:00:00+00:00",
    )
    second = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        arena_slug="cn-bci-industrialization",
        now="2026-04-30T12:01:00+00:00",
    )

    assert len(first) == 1
    assert first[0]["flag_level"] == "significant"
    assert first[0]["reason"] == "supporting claim has refuting evidence"
    assert second == []
    assert len(read_narrative_flags("cn-bci-industrialization", base=tmp_path)) == 1


def test_narrative_flags_cli(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, status="retired")
    _write_segment(tmp_path, claim["claim_id"])

    rc = narrative_flags.cmd_flags(
        Namespace(registry_base=str(tmp_path), base=str(tmp_path), arena="cn-bci-industrialization")
    )

    assert rc == 0
    rows = [json.loads(line) for line in (tmp_path / "arenas" / "cn-bci-industrialization" / "narrative-flags.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["reason"] == "supporting claim retired"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_narrative_flags.py -q
```

Expected: FAIL with import errors for `read_narrative_flags`, `scan_narrative_flags`, or `scripts.narrative_flags`.

- [ ] **Step 3: Commit tests only**

```bash
git add tests/test_narrative_flags.py
git commit -m "test(narrative): define review flag behavior"
```

### Task D2: Implement flag scanning and CLI

**Files:**
- Modify: `app/io/narrative_proposals.py`
- Create: `scripts/narrative_flags.py`
- Test: `tests/test_narrative_flags.py`

- [ ] **Step 1: Append flag implementation to module**

Append this code to `app/io/narrative_proposals.py`:

```python

def _flags_path(base: Path, arena_slug: str) -> Path:
    return base / "arenas" / arena_slug / "narrative-flags.jsonl"


def read_narrative_flags(arena_slug: str, base: Path | None = None, include_dismissed: bool = False) -> list[dict[str, Any]]:
    root = Path(base) if base is not None else cfg.BASE_PATH
    path = _flags_path(root, arena_slug)
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


def _scan_segments(base: Path, arena_slug: str) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    arena_dir = base / "arenas" / arena_slug
    for dimension in NARRATIVE_DIMS:
        path = arena_dir / f"{dimension.replace('_', '-')}.md"
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
    arena_slug: str,
    now: str | None = None,
) -> list[dict[str, Any]]:
    now = now or now_iso()
    existing = read_narrative_flags(arena_slug, base=base, include_dismissed=True)
    existing_keys = {
        (flag.get("dimension"), flag.get("segment_ref"), flag.get("supported_by_claim"), flag.get("reason"))
        for flag in existing
        if not flag.get("dismissed")
    }
    new_flags: list[dict[str, Any]] = []
    for segment in _scan_segments(base, arena_slug):
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
            "flag_level": level,
            "reason": reason,
            "dismissed": False,
            "superseded_by": None,
        }
        new_flags.append(flag)
    if new_flags:
        path = _flags_path(base, arena_slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            for flag in new_flags:
                f.write(json.dumps(flag, ensure_ascii=False, sort_keys=True) + "\n")
    return new_flags
```

- [ ] **Step 2: Create `scripts/narrative_flags.py`**

```python
from __future__ import annotations

import argparse
from pathlib import Path

from app.io.claim_registry import ClaimRegistry
from app.io.narrative_proposals import scan_narrative_flags


def cmd_flags(args: argparse.Namespace) -> int:
    registry = ClaimRegistry(Path(args.registry_base))
    flags = scan_narrative_flags(
        registry=registry,
        base=Path(args.base),
        arena_slug=args.arena,
    )
    print(f"✓ narrative flags generated: {len(flags)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="narrative_flags")
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--base", default=".")
    parser.add_argument("--arena", required=True)
    args = parser.parse_args(argv)
    return cmd_flags(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run flag tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_narrative_flags.py -q
```

Expected: PASS.

- [ ] **Step 4: Run related tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_narrative_proposals.py tests/test_narrative_apply_cli.py tests/test_narrative_flags.py -q
```

Expected: PASS.

- [ ] **Step 5: Run guardrail diff**

Run:

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl'
```

Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add app/io/narrative_proposals.py scripts/narrative_flags.py tests/test_narrative_flags.py
git commit -m "feat(narrative): flag stale arena segments"
```

---

## Part E: Arena page flag display

### Task E1: Add failing arena flag display tests

**Files:**
- Create: `tests/test_arenas_narrative_flags.py`
- Modify later: `app/routes/arenas.py`
- Modify later: `app/templates/arenas/detail.html`

- [ ] **Step 1: Write route/template tests**

Create `tests/test_arenas_narrative_flags.py` with this content:

```python
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import arenas as arenas_route
from app.io import arenas as arenas_io


def test_arena_detail_displays_narrative_flags(tmp_path, monkeypatch):
    monkeypatch.setattr(arenas_route.arenas_io.cfg, "ARENAS_DIR", tmp_path / "arenas")
    arenas_io.write_definition(
        slug="cn-bci-industrialization",
        name="脑机接口产业化",
        definition_text="定义",
        base=tmp_path,
    )
    flags_path = tmp_path / "arenas" / "cn-bci-industrialization" / "narrative-flags.jsonl"
    flags_path.write_text(
        json.dumps(
            {
                "flag_id": "nf-0001",
                "created_at": "2026-04-30T12:00:00+00:00",
                "dimension": "participants",
                "segment_ref": "participants.md#np-001",
                "supported_by_claim": "clm-arena-0001",
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
    app.include_router(arenas_route.router)
    client = TestClient(app)

    response = client.get("/arenas/cn-bci-industrialization")

    assert response.status_code == 200
    assert "needs review" in response.text
    assert "supporting claim retired" in response.text
    assert "clm-arena-0001" in response.text
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_arenas_narrative_flags.py -q
```

Expected: FAIL because the page does not display flags yet.

- [ ] **Step 3: Commit tests only**

```bash
git add tests/test_arenas_narrative_flags.py
git commit -m "test(arena): define narrative flag display"
```

### Task E2: Wire flags into arena route and template

**Files:**
- Modify: `app/routes/arenas.py`
- Modify: `app/templates/arenas/detail.html`
- Test: `tests/test_arenas_narrative_flags.py`

- [ ] **Step 1: Modify route imports**

In `app/routes/arenas.py`, add this import near the other IO imports:

```python
from app.io import narrative_proposals as narrative_io
```

- [ ] **Step 2: Modify route narrative construction**

In `app/routes/arenas.py`, inside `detail()`, after `industry_slug = data["definition_fm"].get("industry")`, add:

```python
    narrative_flags = narrative_io.read_narrative_flags(slug)
    flags_by_dimension = {}
    for flag in narrative_flags:
        flags_by_dimension.setdefault(flag.get("dimension"), []).append(flag)
```

Then replace the existing `narratives.append({...})` block with:

```python
        dim_flags = flags_by_dimension.get(dim, [])
        narratives.append({
            "dim": dim,
            "label": _ARENA_DIM_LABEL.get(dim, dim),
            "has_content": bool(has_content),
            "html": _md.markdown(md, extensions=["tables", "fenced_code"]) if md else "",
            "flags": dim_flags,
            "needs_review": bool(dim_flags),
        })
```

- [ ] **Step 3: Modify template summary display**

In `app/templates/arenas/detail.html`, inside the narrative `<summary>` block after the empty badge line:

```jinja2
      {% if n.needs_review %}<span class="badge badge-draft">needs review</span>{% endif %}
```

- [ ] **Step 4: Modify template flag detail display**

In `app/templates/arenas/detail.html`, inside each narrative `<details>` block before `{% if n.has_content %}`, add:

```jinja2
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
```

- [ ] **Step 5: Run arena flag test**

Run:

```bash
.venv/bin/python -m pytest tests/test_arenas_narrative_flags.py -q
```

Expected: PASS.

- [ ] **Step 6: Run existing arena tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_arenas_narrative.py tests/test_arenas_narrative_flags.py -q
```

Expected: PASS.

- [ ] **Step 7: Run guardrail diff**

Run:

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl'
```

Expected: no output.

- [ ] **Step 8: Commit**

```bash
git add app/routes/arenas.py app/templates/arenas/detail.html tests/test_arenas_narrative_flags.py
git commit -m "feat(arena): show narrative review flags"
```

---

## Part F: End-to-end verification

### Task F1: Add and run a minimal end-to-end test

**Files:**
- Create: `tests/test_phase3a_narrative_end_to_end.py`

- [ ] **Step 1: Write end-to-end test**

Create `tests/test_phase3a_narrative_end_to_end.py` with this content:

```python
import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import narrative_apply, narrative_flags, narrative_propose


def test_phase3a_propose_apply_flag_flow(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    claim = registry.create_claim(
        claim_text="医疗场景支撑脑机接口商业化验证",
        scope_type="arena",
        scope_ref="cn-bci-industrialization",
        claim_type="judgment",
        dimension_hint="competitive_position",
        confidence="medium_high",
        as_of="2024-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    arena_dir = tmp_path / "arenas" / "cn-bci-industrialization"
    arena_dir.mkdir(parents=True)
    (arena_dir / "participants.md").write_text("# participants\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"

    rc = narrative_propose.cmd_propose(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            source_id="src-001",
            arena="cn-bci-industrialization",
            out=str(pending),
        )
    )
    assert rc == 0

    data = json.loads(pending.read_text(encoding="utf-8"))
    data["proposals"][0]["title"] = "参与者格局"
    data["proposals"][0]["body"] = "医疗场景是主要验证路径。"
    data["proposals"][0]["decision"] = "approve"
    data["proposals"][0]["decision_reason"] = "claim 支撑明确"
    pending.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    rc = narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )
    assert rc == 0
    assert "医疗场景是主要验证路径。" in (arena_dir / "participants.md").read_text(encoding="utf-8")

    claim["status"] = "retired"
    registry._rewrite_claim(claim)
    rc = narrative_flags.cmd_flags(
        Namespace(registry_base=str(tmp_path), base=str(tmp_path), arena="cn-bci-industrialization")
    )
    assert rc == 0
    flags = (arena_dir / "narrative-flags.jsonl").read_text(encoding="utf-8")
    assert "supporting claim retired" in flags
```

- [ ] **Step 2: Run end-to-end test**

Run:

```bash
.venv/bin/python -m pytest tests/test_phase3a_narrative_end_to_end.py -q
```

Expected: PASS.

- [ ] **Step 3: Run all Phase 3A tests**

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

Expected: PASS.

- [ ] **Step 4: Run nearby regression tests**

Run:

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

- [ ] **Step 5: Run guardrail diff**

Run:

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl'
```

Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add tests/test_phase3a_narrative_end_to_end.py
git commit -m "test(narrative): cover Phase 3A flow"
```

---

## 3. Manual smoke test after implementation

Run this only after all tasks pass.

- [ ] **Step 1: Find an arena claim source**

Run:

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
path = Path('data/claims/arenas.jsonl')
if not path.exists():
    print('no data/claims/arenas.jsonl')
    raise SystemExit(0)
for line in path.read_text(encoding='utf-8').splitlines():
    if not line.strip():
        continue
    claim = json.loads(line)
    if claim.get('status') == 'active' and claim.get('supporting_evidence'):
        print(claim['scope_ref'], claim['supporting_evidence'][0]['source_id'], claim['claim_id'])
        break
PY
```

Expected: either prints `arena_slug source_id claim_id`, or says no arena claim data. If no data exists, skip manual smoke and rely on tests.

- [ ] **Step 2: Generate a real pending proposal**

Replace `<arena_slug>` and `<source_id>` with Step 1 output:

```bash
.venv/bin/python scripts/narrative_propose.py \
  --registry-base data \
  --base . \
  --source-id <source_id> \
  --arena <arena_slug> \
  --out data/pending/narrative-proposals-<source_id>.json
```

Expected: writes a pending JSON file. Inspect it manually; `body` should be `null`.

- [ ] **Step 3: Do not apply real pending file unless user approves**

Stop here unless the user explicitly asks to fill and apply a real narrative proposal. Applying writes to `arenas/<slug>/*.md`.

---

## 4. Final verification before reporting complete

- [ ] Run all Phase 3A tests:

```bash
.venv/bin/python -m pytest \
  tests/test_narrative_proposals.py \
  tests/test_narrative_apply_cli.py \
  tests/test_narrative_flags.py \
  tests/test_arenas_narrative_flags.py \
  tests/test_phase3a_narrative_end_to_end.py \
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
git diff -- app/io/claims.py 'companies/*/claims.jsonl'
```

- [ ] Check no Python LLM imports were added:

```bash
grep -R "anthropic\|openai" app scripts tests | grep -v __pycache__ || true
```

Expected: no new Phase 3A files contain `anthropic` or `openai`.

- [ ] Check working tree summary:

```bash
git status --short
```

Expected: only intended Phase 3A files changed, plus any commits created during task execution.

---

## 5. Self-review against spec

Spec coverage:
- Pending proposals: Tasks A/C implement `data/pending/narrative-proposals-<source_id>.json`.
- Decision validation: Tasks B/C implement approve/edit/reject/defer validation and CLI errors.
- Markdown appends: Task B implements append-only writes to arena narrative dimensions excluding `definition`.
- Claim binding: Task B validates `supported_by_claims[]` and active claim status.
- Flags: Task D implements manual flag generation and dedup.
- UI: Task E implements arena detail display only, no approval UI.
- Tests and success criteria: Task F and final verification cover unit, CLI, route, and e2e behavior.
- Guardrails: Section 0 and final verification enforce no LLM calls, no V0 claim mutation, no industry/company narrative scope.

Placeholder scan: no task uses `TODO`, `TBD`, or unspecified “add tests” language as an implementation instruction. All code steps include concrete code blocks.

Type consistency: function names used by tests match implementation tasks: `build_proposal_file`, `map_claim_dimension`, `validate_proposal_decisions`, `apply_proposal_file`, `read_narrative_flags`, `scan_narrative_flags`, `cmd_propose`, `cmd_apply`, `cmd_flags`.

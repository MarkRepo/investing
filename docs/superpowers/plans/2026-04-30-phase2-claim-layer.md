# Phase 2 Claim Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 2 claim layer: JSONL claim registry, deterministic matching, manual decision apply flow, archive/arena pending gates, and Phase 2 evaluation extensions.

**Architecture:** Python scripts and focused `app/io/*` modules do deterministic JSON validation, matching, and file writes. Claude/human semantic judgment happens outside Python by editing `data/pending/match-<source_id>.json`; Python never calls an LLM API. Existing V0 claims (`app/io/claims.py` and `companies/*/claims.jsonl`) remain isolated and untouched.

**Tech Stack:** Python 3, stdlib `json`/`argparse`/`pathlib`/`tempfile`, pytest, JSONL files, Markdown prompts.

---

## 0. Mandatory guardrails

Before every task, re-read this section. If implementation drifts into any forbidden item, stop and revert that drift.

**Allowed Phase 2 outputs:**
- Claim statuses produced by code: only `active` and `retired`.
- Claim actions accepted from match decisions: `attach`, `new`, `split`, `skip`.
- Archive actions accepted: `new`, `append` only.
- Matching: pure Python rules only.
- Persistence: JSONL files under `data/claims/`, pending files under `data/pending/`, audit log under `data/audit/`.

**Forbidden in this plan:**
- Do not modify `app/io/claims.py`.
- Do not modify `companies/*/claims.jsonl`.
- Do not modify `app/templates/`, `static/`, or any web UI.
- Do not add SQLite, async jobs, daemons, caches, cron scans, or background workers.
- Do not call `anthropic`, `openai`, browser automation, or any LLM API from Python.
- Do not implement `review_due`, `weakened`, `strengthened`, or `conflicted` transitions.
- Do not change existing claim `confidence` during `attach`.
- Do not append `state_log` for `attach`.
- Do not migrate original historical evidence during `split`.
- Do not add archive `update`, `undo`, or `dry-run` commands.
- Do not add `user_override` CLI behavior.
- Do not implement Phase 3 narrative objects or Phase 4 event/review queue.

**Verification after each implementation task:**

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl' app/templates static
```

Expected: no diff for those paths. If there is a diff, revert it before continuing.

---

## 1. File map

### Create

- `app/io/claim_registry.py` — JSONL claim registry read/write, counters, action helpers, audit events.
- `app/io/claim_matching.py` — deterministic matching engine: scope/status/type filters, bigram Jaccard, dimension boost, top-3 output.
- `app/io/archive_mapping.py` — hardcoded Phase 2 `(scope_type, dimension_hint)` to archive target mapping.
- `scripts/ingest_match.py` — CLI: bundle + registry base → `data/pending/match-<source_id>.json`.
- `scripts/ingest_apply.py` — CLI: filled match file + bundle → registry updates + archive/arena pending files.
- `docs/prompts/ingest-claim-match.md` — human/Claude-in-dialog prompt for filling match decisions.
- `tests/test_claim_registry.py` — registry unit tests.
- `tests/test_claim_matching.py` — matching unit tests.
- `tests/test_ingest_match_cli.py` — match CLI tests.
- `tests/test_ingest_apply_cli.py` — apply CLI tests.
- `tests/test_archive_apply_cli.py` — archive CLI tests in `scripts/ingest_qa.py`.
- `tests/test_arena_approve_cli.py` — arena CLI tests in `scripts/ingest_qa.py`.
- `tests/test_phase2_end_to_end.py` — minimal match → decision → apply → evaluation chain.

### Modify

- `scripts/ingest_qa.py` — add archive QA/apply commands, arena review commands, Phase 2 `evaluation init --match` support.
- `tests/test_ingest_eval_cli.py` — extend expected dimensions and add `--match` metrics tests.
- `docs/prompts/ingest-eval-l2.md` — bump prompt version to `phase2-v1`, add two dimensions and `phase3_readiness`.

### Do not modify

- `app/io/claims.py`
- `companies/*/claims.jsonl`
- `app/templates/**`
- `static/**`
- `scripts/preprocess_report.py`
- `scripts/ingest_aggregate.py`
- `docs/superpowers/archive/**`

---

## 2. Data contracts to use exactly

### 2.1 Claim object shape

All new claims written by `app/io/claim_registry.py` must include these keys:

```python
CLAIM_SCHEMA_VERSION = "phase2-v1"
CLAIM_STATUSES_PHASE2 = {"active", "retired"}
CLAIM_TYPES = {"thesis", "judgment", "risk", "scenario", "gate_assessment"}
CONFIDENCE_VALUES = {"high", "medium_high", "medium", "medium_low", "low"}
SCOPE_FILES = {
    "industry": "industries.jsonl",
    "arena": "arenas.jsonl",
    "company": "companies.jsonl",
    "cross_cutting": "cross_cutting.jsonl",
}
```

A claim dict must use these field names:

```python
{
    "claim_id": "clm-company-0001",
    "claim_text": "...",
    "scope_type": "company",
    "scope_ref": "SSE_600519",
    "claim_type": "judgment",
    "dimension_hint": "moat",
    "status": "active",
    "confidence": "medium_high",
    "as_of": "2024-12-31",
    "review_by": None,
    "supporting_evidence": [
        {
            "source_id": "2024-annual-600519",
            "block_ids": ["ib-003"],
            "fact_ids": ["fact-012"],
            "direction": "supports",
            "weight": 1.0,
            "added_at": "2026-04-30T12:00:00+00:00",
            "added_by": "ingest",
        }
    ],
    "related_claims": [],
    "state_log": [
        {
            "timestamp": "2026-04-30T12:00:00+00:00",
            "from_status": None,
            "to_status": "active",
            "trigger": "created",
            "trigger_ref": "match-2024-annual-600519.json#cc-001",
        }
    ],
    "user_override": None,
    "created_at": "2026-04-30T12:00:00+00:00",
    "last_updated": "2026-04-30T12:00:00+00:00",
    "schema_version": "phase2-v1",
}
```

### 2.2 Match pending object shape

`scripts/ingest_match.py` writes:

```python
{
    "source_id": "2024-annual-600519",
    "generated_at": "2026-04-30T12:30:00+00:00",
    "bundle_ref": "path/to/bundle.json",
    "matching_engine_version": "phase2-v1",
    "decisions_required": [
        {
            "candidate_id": "cc-001",
            "candidate_payload": {},
            "top_matches": [],
            "decision": None,
            "decision_reason": None,
            "direction_on_claim": None,
            "target_claim_id": None,
            "split_instructions": None,
        }
    ],
    "summary_stats": {
        "total_candidates": 1,
        "with_matches": 0,
        "no_matches_suggest_new": 1,
        "high_confidence_matches": 0,
    },
}
```

`target_claim_id` is required for `attach`. For `split`, use `split_instructions.retire_target_claim_id`.

### 2.3 Candidate field names expected from bundle

Use these keys from each `bundle["claim_candidates"]` entry:

```python
{
    "candidate_id": "cc-001",
    "claim_text": "...",
    "scope_type": "company",
    "scope_ref": "SSE_600519",
    "claim_type": "judgment",
    "dimension_hint": "moat",
    "confidence": "medium_high",
    "as_of": "2024-12-31",
    "direction_on_source": "supports",
    "supporting_block_ids": ["ib-001"],
}
```

If `candidate_id` is missing, generate `cc-001`, `cc-002`, etc. Do not mutate the original bundle on disk.

---

## Part A: Claim registry

### Task A1: Add failing registry creation tests

**Files:**
- Create: `tests/test_claim_registry.py`
- Create later: `app/io/claim_registry.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_claim_registry.py` with exactly this initial content:

```python
import json

from app.io.claim_registry import ClaimRegistry, build_evidence_entry


def test_create_claim_writes_scope_file_and_counter(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )

    claim = registry.create_claim(
        claim_text="茅台品牌溢价具备韧性",
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2024-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="match-src-001.json#cc-001",
        now="2026-04-30T12:00:00+00:00",
    )

    assert claim["claim_id"] == "clm-company-0001"
    assert claim["status"] == "active"
    assert claim["user_override"] is None
    assert claim["schema_version"] == "phase2-v1"
    assert claim["supporting_evidence"] == [evidence]
    assert claim["state_log"] == [
        {
            "timestamp": "2026-04-30T12:00:00+00:00",
            "from_status": None,
            "to_status": "active",
            "trigger": "created",
            "trigger_ref": "match-src-001.json#cc-001",
        }
    ]

    lines = (tmp_path / "claims" / "companies.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["claim_id"] == "clm-company-0001"
    counters = json.loads((tmp_path / "claims" / ".counters.json").read_text(encoding="utf-8"))
    assert counters == {"company": 1}


def test_registry_loads_existing_claim_by_id_and_scope(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=[],
        direction="neutral",
        now="2026-04-30T12:00:00+00:00",
    )
    created = registry.create_claim(
        claim_text="行业需求存在波动",
        scope_type="industry",
        scope_ref="cn-power-equipment",
        claim_type="risk",
        dimension_hint="demand",
        confidence="medium",
        as_of="2024-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="match-src-001.json#cc-001",
        now="2026-04-30T12:00:00+00:00",
    )

    reloaded = ClaimRegistry(tmp_path)

    assert reloaded.find_by_id(created["claim_id"])["claim_text"] == "行业需求存在波动"
    assert [c["claim_id"] for c in reloaded.claims_for_scope("industry", "cn-power-equipment")] == [created["claim_id"]]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_claim_registry.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.io.claim_registry'`.

- [ ] **Step 3: Commit tests only**

Do not commit yet if the repo convention dislikes failing-test commits. If committing is acceptable in this session, use:

```bash
git add tests/test_claim_registry.py
git commit -m "test(claims): define registry creation behavior"
```

### Task A2: Implement minimal registry creation and loading

**Files:**
- Create: `app/io/claim_registry.py`
- Test: `tests/test_claim_registry.py`

- [ ] **Step 1: Add implementation**

Create `app/io/claim_registry.py`:

```python
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

CLAIM_SCHEMA_VERSION = "phase2-v1"
SCOPE_FILES = {
    "industry": "industries.jsonl",
    "arena": "arenas.jsonl",
    "company": "companies.jsonl",
    "cross_cutting": "cross_cutting.jsonl",
}
CLAIM_TYPES = {"thesis", "judgment", "risk", "scenario", "gate_assessment"}
CONFIDENCE_VALUES = {"high", "medium_high", "medium", "medium_low", "low"}
EVIDENCE_DIRECTIONS = {"supports", "refutes", "neutral"}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    _atomic_write_text(path, text)


def build_evidence_entry(
    *,
    source_id: str,
    block_ids: list[str],
    fact_ids: list[str],
    direction: str,
    now: str,
) -> dict[str, Any]:
    if direction not in EVIDENCE_DIRECTIONS:
        raise ValueError(f"invalid evidence direction: {direction}")
    return {
        "source_id": source_id,
        "block_ids": block_ids,
        "fact_ids": fact_ids,
        "direction": direction,
        "weight": 1.0,
        "added_at": now,
        "added_by": "ingest",
    }


class ClaimRegistry:
    def __init__(self, base: Path):
        self.base = Path(base)
        self.claims_dir = self.base / "claims"
        self.counters_path = self.claims_dir / ".counters.json"
        self._claims_by_id: dict[str, dict[str, Any]] = {}
        self._by_scope: dict[tuple[str, str], list[str]] = {}
        self._rows_by_scope_type: dict[str, list[dict[str, Any]]] = {}
        self._counters: dict[str, int] = {}
        self._load_all()

    def _load_all(self) -> None:
        if self.counters_path.exists():
            self._counters = json.loads(self.counters_path.read_text(encoding="utf-8"))
        for scope_type, filename in SCOPE_FILES.items():
            rows = _read_jsonl(self.claims_dir / filename)
            self._rows_by_scope_type[scope_type] = rows
            for claim in rows:
                claim_id = claim["claim_id"]
                self._claims_by_id[claim_id] = claim
                key = (claim["scope_type"], claim.get("scope_ref", ""))
                self._by_scope.setdefault(key, []).append(claim_id)

    def _claim_path(self, scope_type: str) -> Path:
        if scope_type not in SCOPE_FILES:
            raise ValueError(f"invalid scope_type: {scope_type}")
        return self.claims_dir / SCOPE_FILES[scope_type]

    def _next_id(self, scope_type: str) -> str:
        current = int(self._counters.get(scope_type, 0)) + 1
        self._counters[scope_type] = current
        return f"clm-{scope_type}-{current:04d}"

    def _persist_scope(self, scope_type: str) -> None:
        _write_jsonl(self._claim_path(scope_type), self._rows_by_scope_type.get(scope_type, []))
        _atomic_write_text(
            self.counters_path,
            json.dumps(self._counters, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        )

    def find_by_id(self, claim_id: str) -> dict[str, Any] | None:
        return self._claims_by_id.get(claim_id)

    def claims_for_scope(self, scope_type: str, scope_ref: str) -> list[dict[str, Any]]:
        ids = self._by_scope.get((scope_type, scope_ref), [])
        return [self._claims_by_id[claim_id] for claim_id in ids]

    def all_claims_for_scope_type(self, scope_type: str) -> list[dict[str, Any]]:
        if scope_type not in SCOPE_FILES:
            raise ValueError(f"invalid scope_type: {scope_type}")
        return list(self._rows_by_scope_type.get(scope_type, []))

    def create_claim(
        self,
        *,
        claim_text: str,
        scope_type: str,
        scope_ref: str,
        claim_type: str,
        dimension_hint: str,
        confidence: str,
        as_of: str,
        evidence: dict[str, Any],
        trigger: str,
        trigger_ref: str,
        now: str,
    ) -> dict[str, Any]:
        if claim_type not in CLAIM_TYPES:
            raise ValueError(f"invalid claim_type: {claim_type}")
        if confidence not in CONFIDENCE_VALUES:
            raise ValueError(f"invalid confidence: {confidence}")
        claim_id = self._next_id(scope_type)
        claim = {
            "claim_id": claim_id,
            "claim_text": claim_text,
            "scope_type": scope_type,
            "scope_ref": scope_ref,
            "claim_type": claim_type,
            "dimension_hint": dimension_hint,
            "status": "active",
            "confidence": confidence,
            "as_of": as_of,
            "review_by": None,
            "supporting_evidence": [evidence],
            "related_claims": [],
            "state_log": [
                {
                    "timestamp": now,
                    "from_status": None,
                    "to_status": "active",
                    "trigger": trigger,
                    "trigger_ref": trigger_ref,
                }
            ],
            "user_override": None,
            "created_at": now,
            "last_updated": now,
            "schema_version": CLAIM_SCHEMA_VERSION,
        }
        self._rows_by_scope_type.setdefault(scope_type, []).append(claim)
        self._claims_by_id[claim_id] = claim
        self._by_scope.setdefault((scope_type, scope_ref), []).append(claim_id)
        self._persist_scope(scope_type)
        return claim
```

- [ ] **Step 2: Run registry tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_claim_registry.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add app/io/claim_registry.py tests/test_claim_registry.py
git commit -m "feat(claims): add JSONL claim registry"
```

### Task A3: Add attach, split, audit, and integrity tests

**Files:**
- Modify: `tests/test_claim_registry.py`
- Modify later: `app/io/claim_registry.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/test_claim_registry.py`:

```python

def _seed_company_claim(registry, *, claim_text="原命题", confidence="medium_high"):
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    return registry.create_claim(
        claim_text=claim_text,
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence=confidence,
        as_of="2024-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="match-src-001.json#cc-001",
        now="2026-04-30T12:00:00+00:00",
    )


def test_append_evidence_does_not_change_confidence_or_state_log(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _seed_company_claim(registry, confidence="high")
    evidence = build_evidence_entry(
        source_id="src-002",
        block_ids=["ib-002"],
        fact_ids=["fact-002"],
        direction="refutes",
        now="2026-04-30T13:00:00+00:00",
    )

    updated = registry.append_evidence(
        claim["claim_id"],
        evidence,
        now="2026-04-30T13:00:00+00:00",
    )

    assert updated["confidence"] == "high"
    assert updated["status"] == "active"
    assert len(updated["supporting_evidence"]) == 2
    assert updated["supporting_evidence"][1] == evidence
    assert len(updated["state_log"]) == 1


def test_split_retires_original_and_creates_new_claims_without_migrating_history(tmp_path):
    registry = ClaimRegistry(tmp_path)
    original = _seed_company_claim(registry)
    new_claims = registry.split_claim(
        original["claim_id"],
        new_claim_specs=[
            {
                "claim_text": "新命题 A",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "claim_type": "judgment",
                "dimension_hint": "moat",
                "confidence": "medium",
                "as_of": "2024-12-31",
                "evidence": build_evidence_entry(
                    source_id="src-002",
                    block_ids=["ib-002"],
                    fact_ids=["fact-002"],
                    direction="supports",
                    now="2026-04-30T13:00:00+00:00",
                ),
            }
        ],
        now="2026-04-30T13:00:00+00:00",
    )

    retired = registry.find_by_id(original["claim_id"])
    assert retired["status"] == "retired"
    assert retired["supporting_evidence"] == original["supporting_evidence"]
    assert retired["state_log"][-1]["trigger"] == "split"
    assert retired["state_log"][-1]["split_to_claim_ids"] == [new_claims[0]["claim_id"]]
    assert new_claims[0]["state_log"][0]["trigger"] == "split_from"
    assert new_claims[0]["state_log"][0]["trigger_ref"] == original["claim_id"]
    assert new_claims[0]["supporting_evidence"][0]["source_id"] == "src-002"
    assert len(new_claims[0]["supporting_evidence"]) == 1


def test_audit_event_appends_jsonl(tmp_path):
    registry = ClaimRegistry(tmp_path)

    registry.append_audit_event(
        {
            "event_type": "candidate_skipped",
            "source_id": "src-001",
            "candidate_id": "cc-001",
        }
    )

    events = (tmp_path / "audit" / "claim-events.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(events[0]) == {
        "event_type": "candidate_skipped",
        "source_id": "src-001",
        "candidate_id": "cc-001",
    }


def test_check_integrity_detects_counter_mismatch(tmp_path):
    registry = ClaimRegistry(tmp_path)
    _seed_company_claim(registry)
    (tmp_path / "claims" / ".counters.json").write_text('{"company": 9}\n', encoding="utf-8")

    warnings = ClaimRegistry(tmp_path).check_integrity()

    assert warnings == ["counter mismatch for company: counter=9 max_id=1"]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_claim_registry.py -q
```

Expected: FAIL because `append_evidence`, `split_claim`, `append_audit_event`, and `check_integrity` do not exist.

### Task A4: Implement attach, split, audit, and integrity

**Files:**
- Modify: `app/io/claim_registry.py`
- Test: `tests/test_claim_registry.py`

- [ ] **Step 1: Add helper methods inside `ClaimRegistry`**

Add these methods to `ClaimRegistry` in `app/io/claim_registry.py`:

```python
    def _rewrite_claim(self, claim: dict[str, Any]) -> None:
        scope_type = claim["scope_type"]
        rows = self._rows_by_scope_type.get(scope_type, [])
        for idx, row in enumerate(rows):
            if row["claim_id"] == claim["claim_id"]:
                rows[idx] = claim
                self._claims_by_id[claim["claim_id"]] = claim
                self._persist_scope(scope_type)
                return
        raise KeyError(claim["claim_id"])

    def append_evidence(self, claim_id: str, evidence: dict[str, Any], *, now: str) -> dict[str, Any]:
        claim = self.find_by_id(claim_id)
        if claim is None:
            raise KeyError(claim_id)
        claim["supporting_evidence"].append(evidence)
        claim["last_updated"] = now
        self._rewrite_claim(claim)
        return claim

    def split_claim(
        self,
        claim_id: str,
        *,
        new_claim_specs: list[dict[str, Any]],
        now: str,
    ) -> list[dict[str, Any]]:
        original = self.find_by_id(claim_id)
        if original is None:
            raise KeyError(claim_id)
        if original.get("status") != "active":
            raise ValueError(f"cannot split non-active claim: {claim_id}")

        new_claims = []
        for spec in new_claim_specs:
            new_claim = self.create_claim(
                claim_text=spec["claim_text"],
                scope_type=spec["scope_type"],
                scope_ref=spec["scope_ref"],
                claim_type=spec["claim_type"],
                dimension_hint=spec["dimension_hint"],
                confidence=spec["confidence"],
                as_of=spec["as_of"],
                evidence=spec["evidence"],
                trigger="split_from",
                trigger_ref=claim_id,
                now=now,
            )
            new_claims.append(new_claim)

        original["status"] = "retired"
        original["last_updated"] = now
        original["state_log"].append(
            {
                "timestamp": now,
                "from_status": "active",
                "to_status": "retired",
                "trigger": "split",
                "trigger_ref": claim_id,
                "split_to_claim_ids": [claim["claim_id"] for claim in new_claims],
            }
        )
        self._rewrite_claim(original)
        return new_claims

    def append_audit_event(self, event: dict[str, Any]) -> None:
        path = self.base / "audit" / "claim-events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    def check_integrity(self) -> list[str]:
        warnings: list[str] = []
        seen_ids: set[str] = set()
        max_by_scope: dict[str, int] = {}
        for scope_type, rows in self._rows_by_scope_type.items():
            for claim in rows:
                claim_id = claim["claim_id"]
                if claim_id in seen_ids:
                    warnings.append(f"duplicate claim_id: {claim_id}")
                seen_ids.add(claim_id)
                suffix = int(claim_id.rsplit("-", 1)[1])
                max_by_scope[scope_type] = max(max_by_scope.get(scope_type, 0), suffix)
                for evidence in claim.get("supporting_evidence", []):
                    if not evidence.get("source_id"):
                        warnings.append(f"empty evidence source_id: {claim_id}")
                if claim.get("status") == "retired" and claim.get("state_log", [])[-1].get("trigger") != "split":
                    warnings.append(f"retired claim without split log: {claim_id}")
        for scope_type, max_id in max_by_scope.items():
            counter = int(self._counters.get(scope_type, 0))
            if counter != max_id:
                warnings.append(f"counter mismatch for {scope_type}: counter={counter} max_id={max_id}")
        return warnings
```

- [ ] **Step 2: Run registry tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_claim_registry.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add app/io/claim_registry.py tests/test_claim_registry.py
git commit -m "feat(claims): support evidence append and split"
```

---

## Part B: Matching engine

### Task B1: Add failing matching tests

**Files:**
- Create: `tests/test_claim_matching.py`
- Create later: `app/io/claim_matching.py`

- [ ] **Step 1: Write tests**

Create `tests/test_claim_matching.py`:

```python
from app.io.claim_matching import (
    char_bigram_jaccard,
    dimension_boost,
    is_type_compatible,
    match_candidate,
)


def _claim(**overrides):
    claim = {
        "claim_id": "clm-company-0001",
        "claim_text": "茅台品牌溢价来自白酒消费文化",
        "scope_type": "company",
        "scope_ref": "SSE_600519",
        "claim_type": "judgment",
        "dimension_hint": "moat",
        "status": "active",
        "confidence": "medium_high",
        "as_of": "2024-12-31",
        "supporting_evidence": [{"source_id": "src-old"}],
    }
    claim.update(overrides)
    return claim


def test_char_bigram_jaccard_for_cjk_text():
    assert char_bigram_jaccard("品牌溢价", "品牌韧性") == 1 / 5


def test_type_compatibility_whitelist():
    assert is_type_compatible("thesis", "judgment") is True
    assert is_type_compatible("judgment", "thesis") is True
    assert is_type_compatible("risk", "scenario") is True
    assert is_type_compatible("scenario", "risk") is True
    assert is_type_compatible("risk", "judgment") is False


def test_dimension_boost_exact_and_prefix():
    assert dimension_boost("moat", "moat") == 0.15
    assert dimension_boost("moat.brand", "moat.channel") == 0.05
    assert dimension_boost("demand", "moat") == 0.0


def test_match_candidate_filters_retired_and_incompatible_and_returns_top3():
    candidate = {
        "candidate_id": "cc-001",
        "claim_text": "茅台品牌溢价来自白酒文化根基",
        "scope_type": "company",
        "scope_ref": "SSE_600519",
        "claim_type": "thesis",
        "dimension_hint": "moat",
    }
    claims = [
        _claim(claim_id="clm-company-0001", claim_text="茅台品牌溢价来自白酒消费文化"),
        _claim(claim_id="clm-company-0002", claim_text="完全不同的渠道库存问题", dimension_hint="channel"),
        _claim(claim_id="clm-company-0003", claim_text="茅台品牌溢价来自白酒文化", status="retired"),
        _claim(claim_id="clm-company-0004", claim_type="risk", claim_text="茅台品牌溢价来自白酒文化"),
        _claim(claim_id="clm-company-0005", claim_text="品牌溢价和白酒文化相关"),
        _claim(claim_id="clm-company-0006", claim_text="白酒消费文化支撑品牌溢价"),
    ]

    matches = match_candidate(candidate, claims)

    assert [m["claim_id"] for m in matches] == ["clm-company-0001", "clm-company-0005", "clm-company-0006"]
    assert matches[0]["score"] >= matches[1]["score"]
    assert "same_dimension=moat" in matches[0]["reasons"]
    assert "type_compatible=thesis~judgment" in matches[0]["reasons"]
    assert matches[0]["existing_claim_snapshot"]["supporting_source_ids"] == ["src-old"]


def test_match_candidate_drops_all_when_best_score_below_threshold():
    candidate = {
        "candidate_id": "cc-001",
        "claim_text": "海外需求快速增长",
        "scope_type": "company",
        "scope_ref": "SSE_600519",
        "claim_type": "judgment",
        "dimension_hint": "demand",
    }

    assert match_candidate(candidate, [_claim(claim_text="渠道库存承压")]) == []
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_claim_matching.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.io.claim_matching'`.

### Task B2: Implement matching engine

**Files:**
- Create: `app/io/claim_matching.py`
- Test: `tests/test_claim_matching.py`

- [ ] **Step 1: Add implementation**

Create `app/io/claim_matching.py`:

```python
from __future__ import annotations

from typing import Any

MATCHING_ENGINE_VERSION = "phase2-v1"
TYPE_COMPATIBLE_PAIRS = {frozenset({"thesis", "judgment"}), frozenset({"risk", "scenario"})}
LOW_SCORE_THRESHOLD = 0.25
HIGH_CONFIDENCE_THRESHOLD = 0.80
TOP_K = 3


def _char_bigrams(text: str) -> set[str]:
    compact = "".join((text or "").split())
    if len(compact) < 2:
        return set()
    return {compact[i : i + 2] for i in range(len(compact) - 1)}


def char_bigram_jaccard(a: str, b: str) -> float:
    left = _char_bigrams(a)
    right = _char_bigrams(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def is_type_compatible(existing_type: str, candidate_type: str) -> bool:
    if existing_type == candidate_type:
        return True
    return frozenset({existing_type, candidate_type}) in TYPE_COMPATIBLE_PAIRS


def dimension_boost(existing_dimension: str, candidate_dimension: str) -> float:
    if existing_dimension == candidate_dimension and existing_dimension:
        return 0.15
    existing_prefix = (existing_dimension or "").split(".", 1)[0]
    candidate_prefix = (candidate_dimension or "").split(".", 1)[0]
    if existing_prefix and existing_prefix == candidate_prefix:
        return 0.05
    return 0.0


def _supporting_source_ids(claim: dict[str, Any]) -> list[str]:
    ids = []
    for evidence in claim.get("supporting_evidence", []) or []:
        source_id = evidence.get("source_id")
        if source_id and source_id not in ids:
            ids.append(source_id)
    return ids


def _snapshot(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_text": claim.get("claim_text", ""),
        "status": claim.get("status", ""),
        "confidence": claim.get("confidence", ""),
        "as_of": claim.get("as_of", ""),
        "supporting_source_ids": _supporting_source_ids(claim),
    }


def match_candidate(candidate: dict[str, Any], claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = []
    candidate_type = candidate.get("claim_type", "")
    candidate_dimension = candidate.get("dimension_hint", "")
    for claim in claims:
        if claim.get("status") == "retired":
            continue
        existing_type = claim.get("claim_type", "")
        if not is_type_compatible(existing_type, candidate_type):
            continue
        text_score = char_bigram_jaccard(candidate.get("claim_text", ""), claim.get("claim_text", ""))
        boost = dimension_boost(claim.get("dimension_hint", ""), candidate_dimension)
        score = 0.85 * text_score + boost
        if score < LOW_SCORE_THRESHOLD:
            continue
        reasons = [f"text_bigram_jaccard={text_score:.2f}"]
        if boost == 0.15:
            reasons.append(f"same_dimension={candidate_dimension}")
        elif boost == 0.05:
            reasons.append(f"same_dimension_prefix={candidate_dimension.split('.', 1)[0]}")
        if existing_type == candidate_type:
            reasons.append(f"type_match={candidate_type}")
        else:
            reasons.append(f"type_compatible={candidate_type}~{existing_type}")
        match = {
            "claim_id": claim["claim_id"],
            "score": round(score, 4),
            "high_confidence": score >= HIGH_CONFIDENCE_THRESHOLD,
            "reasons": reasons,
            "existing_claim_snapshot": _snapshot(claim),
        }
        scored.append(match)
    scored.sort(key=lambda item: (-item["score"], item["claim_id"]))
    return scored[:TOP_K]
```

- [ ] **Step 2: Run matching tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_claim_matching.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add app/io/claim_matching.py tests/test_claim_matching.py
git commit -m "feat(claims): add deterministic claim matching"
```

---

## Part C: `ingest_match.py` CLI

### Task C1: Add failing CLI tests

**Files:**
- Create: `tests/test_ingest_match_cli.py`
- Create later: `scripts/ingest_match.py`

- [ ] **Step 1: Write tests**

Create `tests/test_ingest_match_cli.py`:

```python
import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import ingest_match


def _bundle():
    return {
        "source_digest": {"source_id": "src-001", "source_date": "2024-12-31"},
        "claim_candidates": [
            {
                "candidate_id": "cc-001",
                "claim_text": "茅台品牌溢价来自白酒文化根基",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "claim_type": "judgment",
                "dimension_hint": "moat",
                "confidence": "medium_high",
                "as_of": "2024-12-31",
                "direction_on_source": "supports",
                "supporting_block_ids": ["ib-001"],
            }
        ],
    }


def test_cmd_match_writes_pending_file_with_empty_registry(tmp_path):
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(_bundle()), encoding="utf-8")
    out = tmp_path / "pending" / "match-src-001.json"

    rc = ingest_match.cmd_match(
        Namespace(bundle=str(bundle_path), registry_base=str(tmp_path), out=str(out))
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source_id"] == "src-001"
    assert data["bundle_ref"] == str(bundle_path)
    assert data["matching_engine_version"] == "phase2-v1"
    assert data["decisions_required"][0]["candidate_id"] == "cc-001"
    assert data["decisions_required"][0]["top_matches"] == []
    assert data["decisions_required"][0]["decision"] is None
    assert data["summary_stats"] == {
        "total_candidates": 1,
        "with_matches": 0,
        "no_matches_suggest_new": 1,
        "high_confidence_matches": 0,
    }


def test_cmd_match_uses_scope_filtered_registry_claims(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-old",
        block_ids=["ib-old"],
        fact_ids=["fact-old"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    registry.create_claim(
        claim_text="茅台品牌溢价来自白酒消费文化",
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2023-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    registry.create_claim(
        claim_text="茅台品牌溢价来自白酒消费文化",
        scope_type="company",
        scope_ref="SZSE_000858",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2023-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(_bundle()), encoding="utf-8")
    out = tmp_path / "pending" / "match-src-001.json"

    rc = ingest_match.cmd_match(
        Namespace(bundle=str(bundle_path), registry_base=str(tmp_path), out=str(out))
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    matches = data["decisions_required"][0]["top_matches"]
    assert [m["claim_id"] for m in matches] == ["clm-company-0001"]
    assert data["summary_stats"]["with_matches"] == 1
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_ingest_match_cli.py -q
```

Expected: FAIL because `scripts.ingest_match` does not exist.

### Task C2: Implement match CLI

**Files:**
- Create: `scripts/ingest_match.py`
- Test: `tests/test_ingest_match_cli.py`

- [ ] **Step 1: Add script**

Create `scripts/ingest_match.py`:

```python
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.io.claim_matching import MATCHING_ENGINE_VERSION, match_candidate
from app.io.claim_registry import ClaimRegistry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _candidate_id(candidate: dict[str, Any], idx: int) -> str:
    return candidate.get("candidate_id") or f"cc-{idx + 1:03d}"


def _claims_for_candidate(registry: ClaimRegistry, candidate: dict[str, Any]) -> list[dict[str, Any]]:
    scope_type = candidate.get("scope_type", "")
    scope_ref = candidate.get("scope_ref", "")
    if scope_type == "cross_cutting":
        return registry.all_claims_for_scope_type("cross_cutting")
    return registry.claims_for_scope(scope_type, scope_ref)


def build_match_file(bundle: dict[str, Any], *, bundle_ref: str, registry: ClaimRegistry, generated_at: str) -> dict[str, Any]:
    source_id = (bundle.get("source_digest") or {}).get("source_id", "")
    decisions = []
    with_matches = 0
    high_confidence_matches = 0
    candidates = bundle.get("claim_candidates", []) or []
    for idx, candidate in enumerate(candidates):
        candidate_payload = dict(candidate)
        candidate_payload.setdefault("candidate_id", _candidate_id(candidate, idx))
        matches = match_candidate(candidate_payload, _claims_for_candidate(registry, candidate_payload))
        if matches:
            with_matches += 1
        if any(match.get("high_confidence") for match in matches):
            high_confidence_matches += 1
        decisions.append(
            {
                "candidate_id": candidate_payload["candidate_id"],
                "candidate_payload": candidate_payload,
                "top_matches": matches,
                "decision": None,
                "decision_reason": None,
                "direction_on_claim": None,
                "target_claim_id": None,
                "split_instructions": None,
            }
        )
    return {
        "source_id": source_id,
        "generated_at": generated_at,
        "bundle_ref": bundle_ref,
        "matching_engine_version": MATCHING_ENGINE_VERSION,
        "decisions_required": decisions,
        "summary_stats": {
            "total_candidates": len(candidates),
            "with_matches": with_matches,
            "no_matches_suggest_new": len(candidates) - with_matches,
            "high_confidence_matches": high_confidence_matches,
        },
    }


def cmd_match(args: argparse.Namespace) -> int:
    bundle_path = Path(args.bundle)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    registry = ClaimRegistry(Path(args.registry_base))
    match_file = build_match_file(
        bundle,
        bundle_ref=str(bundle_path),
        registry=registry,
        generated_at=_now(),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(match_file, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ match file written to {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ingest_match")
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    return cmd_match(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_ingest_match_cli.py tests/test_claim_matching.py tests/test_claim_registry.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add scripts/ingest_match.py tests/test_ingest_match_cli.py
git commit -m "feat(ingest): write claim match pending files"
```

---

## Part D: Apply flow

### Task D1: Add failing apply tests for decisions and registry writes

**Files:**
- Create: `tests/test_ingest_apply_cli.py`
- Create later: `scripts/ingest_apply.py`

- [ ] **Step 1: Write tests**

Create `tests/test_ingest_apply_cli.py`:

```python
import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import ingest_apply


def _bundle():
    return {
        "source_digest": {"source_id": "src-001", "source_date": "2024-12-31"},
        "insight_blocks": [{"id": "ib-001", "title": "品牌", "dimension_hint": "moat"}],
        "atomic_facts": [
            {"fact_id": "fact-001", "linked_block_id": "ib-001", "fact_text": "事实", "confidence": "medium"}
        ],
        "claim_candidates": [],
        "company_candidates": [],
    }


def _decision(candidate, **overrides):
    row = {
        "candidate_id": candidate["candidate_id"],
        "candidate_payload": candidate,
        "top_matches": [],
        "decision": "new",
        "decision_reason": "形成新命题",
        "direction_on_claim": None,
        "target_claim_id": None,
        "split_instructions": None,
    }
    row.update(overrides)
    return row


def _candidate(**overrides):
    candidate = {
        "candidate_id": "cc-001",
        "claim_text": "茅台品牌溢价来自白酒文化根基",
        "scope_type": "company",
        "scope_ref": "SSE_600519",
        "claim_type": "judgment",
        "dimension_hint": "moat",
        "confidence": "medium_high",
        "as_of": "2024-12-31",
        "direction_on_source": "supports",
        "supporting_block_ids": ["ib-001"],
    }
    candidate.update(overrides)
    return candidate


def _write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_apply_new_creates_claim_and_pending_files(tmp_path):
    bundle = _bundle()
    candidate = _candidate()
    match = {
        "source_id": "src-001",
        "decisions_required": [_decision(candidate)],
    }
    bundle_path = tmp_path / "bundle.json"
    match_path = tmp_path / "pending" / "match-src-001.json"
    match_path.parent.mkdir()
    _write_json(bundle_path, bundle)
    _write_json(match_path, match)

    rc = ingest_apply.cmd_apply(
        Namespace(match=str(match_path), bundle=str(bundle_path), registry_base=str(tmp_path))
    )

    assert rc == 0
    claim = json.loads((tmp_path / "claims" / "companies.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert claim["claim_id"] == "clm-company-0001"
    assert claim["supporting_evidence"][0]["fact_ids"] == ["fact-001"]
    assert claim["supporting_evidence"][0]["direction"] == "supports"
    assert (tmp_path / "pending" / "archive-writes-src-001.json").exists()
    assert (tmp_path / "pending" / "arenas-src-001.jsonl").exists()


def test_apply_attach_appends_evidence_without_state_log_or_confidence_change(tmp_path):
    registry = ClaimRegistry(tmp_path)
    existing = registry.create_claim(
        claim_text="茅台品牌溢价来自白酒消费文化",
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="high",
        as_of="2023-12-31",
        evidence=build_evidence_entry(
            source_id="src-old",
            block_ids=["ib-old"],
            fact_ids=["fact-old"],
            direction="supports",
            now="2026-04-30T12:00:00+00:00",
        ),
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    candidate = _candidate()
    match = {
        "source_id": "src-001",
        "decisions_required": [
            _decision(
                candidate,
                decision="attach",
                decision_reason="同一命题的新证据",
                direction_on_claim="weakens",
                target_claim_id=existing["claim_id"],
            )
        ],
    }
    bundle_path = tmp_path / "bundle.json"
    match_path = tmp_path / "pending" / "match-src-001.json"
    match_path.parent.mkdir(exist_ok=True)
    _write_json(bundle_path, _bundle())
    _write_json(match_path, match)

    rc = ingest_apply.cmd_apply(
        Namespace(match=str(match_path), bundle=str(bundle_path), registry_base=str(tmp_path))
    )

    assert rc == 0
    updated = ClaimRegistry(tmp_path).find_by_id(existing["claim_id"])
    assert updated["confidence"] == "high"
    assert len(updated["state_log"]) == 1
    assert updated["supporting_evidence"][1]["direction"] == "refutes"


def test_apply_fails_before_writing_when_decision_missing(tmp_path):
    candidate = _candidate()
    match = {"source_id": "src-001", "decisions_required": [_decision(candidate, decision=None)]}
    bundle_path = tmp_path / "bundle.json"
    match_path = tmp_path / "pending" / "match-src-001.json"
    match_path.parent.mkdir()
    _write_json(bundle_path, _bundle())
    _write_json(match_path, match)

    rc = ingest_apply.cmd_apply(
        Namespace(match=str(match_path), bundle=str(bundle_path), registry_base=str(tmp_path))
    )

    assert rc == 1
    assert not (tmp_path / "claims").exists()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_ingest_apply_cli.py -q
```

Expected: FAIL because `scripts.ingest_apply` does not exist.

### Task D2: Implement apply validation, new, attach, and pending derivation

**Files:**
- Create: `scripts/ingest_apply.py`
- Test: `tests/test_ingest_apply_cli.py`

- [ ] **Step 1: Add script**

Create `scripts/ingest_apply.py`:

```python
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.io.claim_registry import ClaimRegistry, build_evidence_entry

VALID_DECISIONS = {"attach", "new", "split", "skip"}
DIRECTION_ON_CLAIM_TO_EVIDENCE = {
    "strengthens": "supports",
    "weakens": "refutes",
    "neutral": "neutral",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fact_ids_for_blocks(bundle: dict[str, Any], block_ids: list[str]) -> list[str]:
    block_set = set(block_ids)
    fact_ids = []
    for fact in bundle.get("atomic_facts", []) or []:
        if fact.get("linked_block_id") in block_set and fact.get("fact_id"):
            fact_ids.append(fact["fact_id"])
    return fact_ids


def validate_match_decisions(match: dict[str, Any], registry: ClaimRegistry) -> list[str]:
    errors: list[str] = []
    for row in match.get("decisions_required", []) or []:
        candidate_id = row.get("candidate_id", "<unknown>")
        decision = row.get("decision")
        if decision not in VALID_DECISIONS:
            errors.append(f"{candidate_id}: invalid or missing decision")
            continue
        if not row.get("decision_reason"):
            errors.append(f"{candidate_id}: missing decision_reason")
        if decision == "new":
            if row.get("direction_on_claim") or row.get("split_instructions"):
                errors.append(f"{candidate_id}: new must not set direction_on_claim or split_instructions")
        elif decision == "attach":
            target_claim_id = row.get("target_claim_id")
            if not target_claim_id or registry.find_by_id(target_claim_id) is None:
                errors.append(f"{candidate_id}: attach target claim not found")
            if row.get("direction_on_claim") not in DIRECTION_ON_CLAIM_TO_EVIDENCE:
                errors.append(f"{candidate_id}: attach direction_on_claim invalid")
        elif decision == "split":
            instructions = row.get("split_instructions") or {}
            target_claim_id = instructions.get("retire_target_claim_id")
            target = registry.find_by_id(target_claim_id) if target_claim_id else None
            if target is None or target.get("status") != "active":
                errors.append(f"{candidate_id}: split retire target not active")
            if not instructions.get("new_claims"):
                errors.append(f"{candidate_id}: split new_claims empty")
    return errors


def _candidate_evidence(bundle: dict[str, Any], source_id: str, candidate: dict[str, Any], direction: str, now: str) -> dict[str, Any]:
    block_ids = candidate.get("supporting_block_ids", []) or []
    return build_evidence_entry(
        source_id=source_id,
        block_ids=block_ids,
        fact_ids=_fact_ids_for_blocks(bundle, block_ids),
        direction=direction,
        now=now,
    )


def _apply_new(registry: ClaimRegistry, bundle: dict[str, Any], source_id: str, row: dict[str, Any], now: str) -> dict[str, Any]:
    candidate = row["candidate_payload"]
    evidence = _candidate_evidence(bundle, source_id, candidate, candidate.get("direction_on_source", "neutral"), now)
    return registry.create_claim(
        claim_text=candidate["claim_text"],
        scope_type=candidate["scope_type"],
        scope_ref=candidate.get("scope_ref", ""),
        claim_type=candidate["claim_type"],
        dimension_hint=candidate.get("dimension_hint", ""),
        confidence=candidate["confidence"],
        as_of=candidate["as_of"],
        evidence=evidence,
        trigger="created",
        trigger_ref=f"match-{source_id}.json#{row['candidate_id']}",
        now=now,
    )


def _apply_attach(registry: ClaimRegistry, bundle: dict[str, Any], source_id: str, row: dict[str, Any], now: str) -> None:
    candidate = row["candidate_payload"]
    direction = DIRECTION_ON_CLAIM_TO_EVIDENCE[row["direction_on_claim"]]
    evidence = _candidate_evidence(bundle, source_id, candidate, direction, now)
    registry.append_evidence(row["target_claim_id"], evidence, now=now)


def derive_archive_writes(bundle: dict[str, Any], source_id: str) -> dict[str, Any]:
    writes = []
    blocks = {block.get("id"): block for block in bundle.get("insight_blocks", []) or []}
    for fact in bundle.get("atomic_facts", []) or []:
        linked_block = blocks.get(fact.get("linked_block_id"), {})
        writes.append(
            {
                "fact_id": fact.get("fact_id"),
                "fact_payload": fact,
                "linked_block": linked_block,
                "linked_claim_ids": [],
                "suggested_target": None,
                "alternative_targets": [],
                "decision": None,
                "decision_reason": None,
                "final_targets": None,
            }
        )
    return {"source_id": source_id, "writes": writes}


def derive_arena_candidates(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for idx, candidate in enumerate(bundle.get("arena_candidates", []) or []):
        row = dict(candidate)
        row.setdefault("candidate_id", f"arena-{idx + 1:03d}")
        row.setdefault("merge_suggestions", [])
        rows.append(row)
    for candidate in bundle.get("company_candidates", []) or []:
        if candidate.get("scope") == "arena":
            row = dict(candidate)
            row.setdefault("candidate_id", f"arena-{len(rows) + 1:03d}")
            row.setdefault("merge_suggestions", [])
            rows.append(row)
    return rows


def _write_pending_files(base: Path, source_id: str, bundle: dict[str, Any]) -> None:
    pending = base / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    (pending / f"archive-writes-{source_id}.json").write_text(
        json.dumps(derive_archive_writes(bundle, source_id), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    arena_lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in derive_arena_candidates(bundle)]
    (pending / f"arenas-{source_id}.jsonl").write_text("\n".join(arena_lines) + ("\n" if arena_lines else ""), encoding="utf-8")


def cmd_apply(args: argparse.Namespace) -> int:
    base = Path(args.registry_base)
    match = json.loads(Path(args.match).read_text(encoding="utf-8"))
    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    registry = ClaimRegistry(base)
    errors = validate_match_decisions(match, registry)
    if errors:
        for error in errors:
            print(f"✗ {error}")
        return 1

    source_id = match.get("source_id", "")
    now = _now()
    for row in match.get("decisions_required", []) or []:
        decision = row["decision"]
        if decision == "new":
            claim = _apply_new(registry, bundle, source_id, row, now)
            registry.append_audit_event({"event_type": "claim_created", "source_id": source_id, "candidate_id": row["candidate_id"], "claim_id": claim["claim_id"]})
        elif decision == "attach":
            _apply_attach(registry, bundle, source_id, row, now)
            registry.append_audit_event({"event_type": "evidence_attached", "source_id": source_id, "candidate_id": row["candidate_id"], "claim_id": row["target_claim_id"]})
        elif decision == "skip":
            registry.append_audit_event({"event_type": "candidate_skipped", "source_id": source_id, "candidate_id": row["candidate_id"]})
        elif decision == "split":
            raise NotImplementedError("split is implemented in Task D3")
    _write_pending_files(base, source_id, bundle)
    print(f"✓ applied match decisions from {args.match}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ingest_apply")
    parser.add_argument("--match", required=True)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--registry-base", default="data")
    args = parser.parse_args(argv)
    return cmd_apply(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run apply tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_ingest_apply_cli.py -q
```

Expected: PASS for current three tests.

- [ ] **Step 3: Commit**

```bash
git add scripts/ingest_apply.py tests/test_ingest_apply_cli.py
git commit -m "feat(ingest): apply new and attach claim decisions"
```

### Task D3: Add and implement split/skip tests

**Files:**
- Modify: `tests/test_ingest_apply_cli.py`
- Modify: `scripts/ingest_apply.py`

- [ ] **Step 1: Append failing split/skip tests**

Append to `tests/test_ingest_apply_cli.py`:

```python

def test_apply_skip_only_writes_audit_event(tmp_path):
    candidate = _candidate()
    match = {
        "source_id": "src-001",
        "decisions_required": [_decision(candidate, decision="skip", decision_reason="证据太弱")],
    }
    bundle_path = tmp_path / "bundle.json"
    match_path = tmp_path / "pending" / "match-src-001.json"
    match_path.parent.mkdir()
    _write_json(bundle_path, _bundle())
    _write_json(match_path, match)

    rc = ingest_apply.cmd_apply(
        Namespace(match=str(match_path), bundle=str(bundle_path), registry_base=str(tmp_path))
    )

    assert rc == 0
    assert not (tmp_path / "claims" / "companies.jsonl").exists()
    event = json.loads((tmp_path / "audit" / "claim-events.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert event["event_type"] == "candidate_skipped"


def test_apply_split_retires_original_and_creates_new_claim(tmp_path):
    registry = ClaimRegistry(tmp_path)
    original = registry.create_claim(
        claim_text="原命题",
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2023-12-31",
        evidence=build_evidence_entry(
            source_id="src-old",
            block_ids=["ib-old"],
            fact_ids=["fact-old"],
            direction="supports",
            now="2026-04-30T12:00:00+00:00",
        ),
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    candidate = _candidate()
    match = {
        "source_id": "src-001",
        "decisions_required": [
            _decision(
                candidate,
                decision="split",
                decision_reason="原命题过宽，需要拆分",
                split_instructions={
                    "retire_target_claim_id": original["claim_id"],
                    "new_claims": [
                        {
                            "claim_text": "拆分后的命题",
                            "evidence_subset": {"block_ids": ["ib-001"], "fact_ids": ["fact-001"]},
                        }
                    ],
                },
            )
        ],
    }
    bundle_path = tmp_path / "bundle.json"
    match_path = tmp_path / "pending" / "match-src-001.json"
    match_path.parent.mkdir(exist_ok=True)
    _write_json(bundle_path, _bundle())
    _write_json(match_path, match)

    rc = ingest_apply.cmd_apply(
        Namespace(match=str(match_path), bundle=str(bundle_path), registry_base=str(tmp_path))
    )

    assert rc == 0
    reloaded = ClaimRegistry(tmp_path)
    retired = reloaded.find_by_id(original["claim_id"])
    assert retired["status"] == "retired"
    assert retired["supporting_evidence"][0]["source_id"] == "src-old"
    new_claim = reloaded.find_by_id("clm-company-0002")
    assert new_claim["claim_text"] == "拆分后的命题"
    assert new_claim["supporting_evidence"][0]["fact_ids"] == ["fact-001"]
    assert new_claim["state_log"][0]["trigger"] == "split_from"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_ingest_apply_cli.py::test_apply_split_retires_original_and_creates_new_claim -q
```

Expected: FAIL with `NotImplementedError: split is implemented in Task D3`.

- [ ] **Step 3: Implement split helper**

Add this function to `scripts/ingest_apply.py` above `cmd_apply`:

```python
def _apply_split(registry: ClaimRegistry, source_id: str, row: dict[str, Any], now: str) -> list[dict[str, Any]]:
    candidate = row["candidate_payload"]
    instructions = row["split_instructions"]
    specs = []
    for new_claim in instructions["new_claims"]:
        evidence_subset = new_claim["evidence_subset"]
        evidence = build_evidence_entry(
            source_id=source_id,
            block_ids=evidence_subset.get("block_ids", []),
            fact_ids=evidence_subset.get("fact_ids", []),
            direction=candidate.get("direction_on_source", "neutral"),
            now=now,
        )
        specs.append(
            {
                "claim_text": new_claim["claim_text"],
                "scope_type": candidate["scope_type"],
                "scope_ref": candidate.get("scope_ref", ""),
                "claim_type": candidate["claim_type"],
                "dimension_hint": candidate.get("dimension_hint", ""),
                "confidence": candidate["confidence"],
                "as_of": candidate["as_of"],
                "evidence": evidence,
            }
        )
    return registry.split_claim(instructions["retire_target_claim_id"], new_claim_specs=specs, now=now)
```

Replace the `split` branch in `cmd_apply`:

```python
        elif decision == "split":
            new_claims = _apply_split(registry, source_id, row, now)
            registry.append_audit_event(
                {
                    "event_type": "claim_split",
                    "source_id": source_id,
                    "candidate_id": row["candidate_id"],
                    "retired_claim_id": row["split_instructions"]["retire_target_claim_id"],
                    "new_claim_ids": [claim["claim_id"] for claim in new_claims],
                }
            )
```

- [ ] **Step 4: Run apply tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_ingest_apply_cli.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/ingest_apply.py tests/test_ingest_apply_cli.py
git commit -m "feat(ingest): apply split and skip decisions"
```

---

## Part E: Archive pending mapping and apply gate

### Task E1: Add archive mapping tests

**Files:**
- Create: `app/io/archive_mapping.py`
- Modify: `tests/test_ingest_apply_cli.py`

- [ ] **Step 1: Create mapping module**

Create `app/io/archive_mapping.py`:

```python
from __future__ import annotations

from typing import Any

DIMENSION_TO_ARCHIVE: dict[tuple[str, str], tuple[str, int]] = {
    ("company", "moat"): ("archive/layer8/company/{scope_ref}/moat.jsonl", 8),
    ("company", "demand"): ("archive/layer8/company/{scope_ref}/demand.jsonl", 8),
    ("industry", "demand"): ("archive/layer11/industry/{scope_ref}/demand.jsonl", 11),
    ("arena", "competition"): ("archive/layer6/arena/{scope_ref}/competition.jsonl", 6),
}


def suggest_archive_target(scope_type: str, scope_ref: str, dimension_hint: str) -> dict[str, Any] | None:
    mapping = DIMENSION_TO_ARCHIVE.get((scope_type, dimension_hint))
    if mapping is None:
        return None
    template, layer = mapping
    return {
        "archive_layer": layer,
        "archive_path": template.format(scope_ref=scope_ref),
        "action": "append",
    }
```

- [ ] **Step 2: Add test for suggested target**

Append to `tests/test_ingest_apply_cli.py`:

```python

def test_archive_writes_include_suggested_target_from_dimension_mapping(tmp_path):
    candidate = _candidate()
    match = {"source_id": "src-001", "decisions_required": [_decision(candidate)]}
    bundle = _bundle()
    bundle["source_digest"]["scope_type"] = "company"
    bundle["source_digest"]["scope_ref"] = "SSE_600519"
    bundle_path = tmp_path / "bundle.json"
    match_path = tmp_path / "pending" / "match-src-001.json"
    match_path.parent.mkdir()
    _write_json(bundle_path, bundle)
    _write_json(match_path, match)

    rc = ingest_apply.cmd_apply(
        Namespace(match=str(match_path), bundle=str(bundle_path), registry_base=str(tmp_path))
    )

    assert rc == 0
    writes = json.loads((tmp_path / "pending" / "archive-writes-src-001.json").read_text(encoding="utf-8"))
    assert writes["writes"][0]["suggested_target"] == {
        "archive_layer": 8,
        "archive_path": "archive/layer8/company/SSE_600519/moat.jsonl",
        "action": "append",
    }
```

- [ ] **Step 3: Run test and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_ingest_apply_cli.py::test_archive_writes_include_suggested_target_from_dimension_mapping -q
```

Expected: FAIL because `derive_archive_writes` does not use the mapping yet.

- [ ] **Step 4: Use mapping in `scripts/ingest_apply.py`**

Add import:

```python
from app.io.archive_mapping import suggest_archive_target
```

In `derive_archive_writes`, before appending each write, compute:

```python
        source_digest = bundle.get("source_digest") or {}
        suggested_target = suggest_archive_target(
            source_digest.get("scope_type", "company"),
            source_digest.get("scope_ref", ""),
            linked_block.get("dimension_hint", ""),
        )
```

Then set:

```python
                "suggested_target": suggested_target,
```

Do not add archive `update` behavior.

- [ ] **Step 5: Run tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_ingest_apply_cli.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/io/archive_mapping.py scripts/ingest_apply.py tests/test_ingest_apply_cli.py
git commit -m "feat(archive): suggest pending archive targets"
```

### Task E2: Add archive apply command tests in `ingest_qa.py`

**Files:**
- Create: `tests/test_archive_apply_cli.py`
- Modify later: `scripts/ingest_qa.py`

- [ ] **Step 1: Write tests**

Create `tests/test_archive_apply_cli.py`:

```python
import json
from argparse import Namespace

from scripts import ingest_qa as qa


def _writes(action="append"):
    return {
        "source_id": "src-001",
        "writes": [
            {
                "fact_id": "fact-001",
                "fact_payload": {"fact_id": "fact-001", "fact_text": "事实"},
                "final_targets": [
                    {
                        "archive_path": "archive/layer8/company/SSE_600519/moat.jsonl",
                        "action": action,
                    }
                ],
            }
        ],
    }


def test_check_archive_writes_rejects_update_action():
    warnings = qa.check_archive_writes_shape(_writes(action="update"))

    assert warnings[0]["rule"] == "archive_invalid_action"
    assert warnings[0]["severity"] == "error"


def test_cmd_archive_apply_appends_fact_payload(tmp_path):
    pending = tmp_path / "archive-writes-src-001.json"
    pending.write_text(json.dumps(_writes()), encoding="utf-8")

    rc = qa.cmd_archive_apply(Namespace(pending=str(pending), base=str(tmp_path)))

    assert rc == 0
    target = tmp_path / "archive" / "layer8" / "company" / "SSE_600519" / "moat.jsonl"
    rows = target.read_text(encoding="utf-8").splitlines()
    assert json.loads(rows[0]) == {"fact_id": "fact-001", "fact_text": "事实"}
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_archive_apply_cli.py -q
```

Expected: FAIL because `check_archive_writes_shape` and `cmd_archive_apply` do not exist.

### Task E3: Implement archive apply gate

**Files:**
- Modify: `scripts/ingest_qa.py`
- Test: `tests/test_archive_apply_cli.py`

- [ ] **Step 1: Add functions to `scripts/ingest_qa.py` before `cmd_evaluation_init`**

```python
def check_archive_writes_shape(data: dict) -> list[dict]:
    warnings: list[dict] = []
    for idx, write in enumerate(data.get("writes", []) or []):
        target = f"writes[{idx}]"
        if not write.get("fact_id"):
            warnings.append(_qa_warning("archive_missing_fact_id", "error", target, "fact_id is required."))
        final_targets = write.get("final_targets")
        if not final_targets:
            warnings.append(_qa_warning("archive_missing_final_targets", "error", target, "final_targets is required before apply."))
            continue
        for t_idx, final_target in enumerate(final_targets):
            t_ref = f"{target}.final_targets[{t_idx}]"
            action = final_target.get("action")
            if action not in {"new", "append"}:
                warnings.append(_qa_warning("archive_invalid_action", "error", t_ref, f"action {action!r} is not one of ['append', 'new']."))
            archive_path = final_target.get("archive_path", "")
            if not archive_path.startswith("archive/") or not archive_path.endswith(".jsonl"):
                warnings.append(_qa_warning("archive_invalid_path", "error", t_ref, f"archive_path {archive_path!r} must look like archive/.../*.jsonl."))
    return warnings


def cmd_archive_apply(args: argparse.Namespace) -> int:
    pending_path = Path(args.pending)
    base = Path(args.base)
    data = json.loads(pending_path.read_text(encoding="utf-8"))
    warnings = check_archive_writes_shape(data)
    errors = [w for w in warnings if w.get("severity") == "error"]
    if errors:
        for warning in errors:
            print(f"✗ {warning['rule']}: {warning['detail']}", file=sys.stderr)
        return 1
    for write in data.get("writes", []) or []:
        payload = write["fact_payload"]
        for final_target in write.get("final_targets", []) or []:
            target_path = base / final_target["archive_path"]
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with target_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"✓ archive writes applied from {pending_path}")
    return 0
```

- [ ] **Step 2: Add CLI parser**

In `main()` before `evaluation`, add:

```python
    p_archive = sub.add_parser("archive", help="archive pending write workflow")
    archive_sub = p_archive.add_subparsers(dest="archive_cmd", required=True)
    p_archive_apply = archive_sub.add_parser("apply", help="apply approved archive writes")
    p_archive_apply.add_argument("--pending", required=True)
    p_archive_apply.add_argument("--base", default=".")
    p_archive_apply.set_defaults(func=cmd_archive_apply)
```

- [ ] **Step 3: Run tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_archive_apply_cli.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add scripts/ingest_qa.py tests/test_archive_apply_cli.py
git commit -m "feat(archive): apply approved pending writes"
```

---

## Part F: Arena pending approval

### Task F1: Add arena CLI tests

**Files:**
- Create: `tests/test_arena_approve_cli.py`
- Modify later: `scripts/ingest_qa.py`

- [ ] **Step 1: Write tests**

Create `tests/test_arena_approve_cli.py`:

```python
import json
from argparse import Namespace

from scripts import ingest_qa as qa


def _pending(path):
    rows = [
        {
            "candidate_id": "arena-001",
            "slug": "cn-power-cable-polymer-material",
            "name": "电缆高分子材料",
            "battleground_focus": "高压电缆材料国产化",
            "core_participants": ["SSE_600522"],
            "merge_suggestions": [],
        }
    ]
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_arena_approve_creates_skeleton_and_archives_pending(tmp_path):
    pending = tmp_path / "data" / "pending" / "arenas-src-001.jsonl"
    pending.parent.mkdir(parents=True)
    _pending(pending)

    rc = qa.cmd_arena_approve(Namespace(pending=str(pending), base=str(tmp_path), id="arena-001"))

    assert rc == 0
    arena_dir = tmp_path / "arenas" / "cn-power-cable-polymer-material"
    assert (arena_dir / "name.yaml").exists()
    assert (arena_dir / "battleground_focus.md").read_text(encoding="utf-8") == "高压电缆材料国产化\n"
    assert "SSE_600522" in (arena_dir / "core_participants.yaml").read_text(encoding="utf-8")
    assert not pending.exists()
    assert (tmp_path / "data" / "pending" / "archive" / "arenas-src-001.jsonl").exists()


def test_arena_reject_archives_pending_with_rejected_marker(tmp_path):
    pending = tmp_path / "data" / "pending" / "arenas-src-001.jsonl"
    pending.parent.mkdir(parents=True)
    _pending(pending)

    rc = qa.cmd_arena_reject(Namespace(pending=str(pending), base=str(tmp_path), id="arena-001"))

    assert rc == 0
    archived = tmp_path / "data" / "pending" / "archive" / "arenas-src-001.jsonl"
    row = json.loads(archived.read_text(encoding="utf-8").splitlines()[0])
    assert row["candidate_id"] == "arena-001"
    assert row["decision"] == "rejected"


def test_arena_merge_archives_pending_with_target(tmp_path):
    pending = tmp_path / "data" / "pending" / "arenas-src-001.jsonl"
    pending.parent.mkdir(parents=True)
    _pending(pending)

    rc = qa.cmd_arena_merge(Namespace(pending=str(pending), base=str(tmp_path), id="arena-001", target_slug="existing-arena"))

    assert rc == 0
    archived = tmp_path / "data" / "pending" / "archive" / "arenas-src-001.jsonl"
    row = json.loads(archived.read_text(encoding="utf-8").splitlines()[0])
    assert row["decision"] == "merged"
    assert row["merge_target"] == "existing-arena"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_arena_approve_cli.py -q
```

Expected: FAIL because arena command functions do not exist.

### Task F2: Implement arena approve/reject/merge

**Files:**
- Modify: `scripts/ingest_qa.py`
- Test: `tests/test_arena_approve_cli.py`

- [ ] **Step 1: Add helper functions before `cmd_evaluation_init`**

```python
def _read_jsonl_file(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _archive_arena_pending(pending_path: Path, rows: list[dict], base: Path) -> None:
    archive_dir = base / "data" / "pending" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived = archive_dir / pending_path.name
    archived.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    pending_path.unlink()


def _mark_arena_candidate(args: argparse.Namespace, decision: str, merge_target: str | None = None) -> int:
    pending_path = Path(args.pending)
    base = Path(args.base)
    rows = _read_jsonl_file(pending_path)
    found = False
    for row in rows:
        if row.get("candidate_id") == args.id:
            row["decision"] = decision
            if merge_target:
                row["merge_target"] = merge_target
            found = True
    if not found:
        print(f"✗ arena candidate not found: {args.id}", file=sys.stderr)
        return 1
    _archive_arena_pending(pending_path, rows, base)
    print(f"✓ arena candidate {args.id} {decision}")
    return 0


def cmd_arena_approve(args: argparse.Namespace) -> int:
    pending_path = Path(args.pending)
    base = Path(args.base)
    rows = _read_jsonl_file(pending_path)
    target = next((row for row in rows if row.get("candidate_id") == args.id), None)
    if target is None:
        print(f"✗ arena candidate not found: {args.id}", file=sys.stderr)
        return 1
    slug = target["slug"]
    arena_dir = base / "arenas" / slug
    arena_dir.mkdir(parents=True, exist_ok=True)
    (arena_dir / "name.yaml").write_text(
        f"slug: {slug}\nname: {target.get('name', '')}\nfirst_seen_source: {pending_path.name}\n",
        encoding="utf-8",
    )
    (arena_dir / "battleground_focus.md").write_text(f"{target.get('battleground_focus', '')}\n", encoding="utf-8")
    participants = target.get("core_participants", []) or []
    (arena_dir / "core_participants.yaml").write_text("".join(f"- {p}\n" for p in participants), encoding="utf-8")
    target["decision"] = "approved"
    _archive_arena_pending(pending_path, rows, base)
    print(f"✓ arena approved: {slug}")
    return 0


def cmd_arena_reject(args: argparse.Namespace) -> int:
    return _mark_arena_candidate(args, "rejected")


def cmd_arena_merge(args: argparse.Namespace) -> int:
    return _mark_arena_candidate(args, "merged", args.target_slug)
```

- [ ] **Step 2: Add CLI parser**

In `main()` before `evaluation`, add:

```python
    p_arena = sub.add_parser("arena", help="arena candidate approval workflow")
    arena_sub = p_arena.add_subparsers(dest="arena_cmd", required=True)
    p_arena_approve = arena_sub.add_parser("approve", help="approve arena candidate")
    p_arena_approve.add_argument("--pending", required=True)
    p_arena_approve.add_argument("--base", default=".")
    p_arena_approve.add_argument("id")
    p_arena_approve.set_defaults(func=cmd_arena_approve)
    p_arena_reject = arena_sub.add_parser("reject", help="reject arena candidate")
    p_arena_reject.add_argument("--pending", required=True)
    p_arena_reject.add_argument("--base", default=".")
    p_arena_reject.add_argument("id")
    p_arena_reject.set_defaults(func=cmd_arena_reject)
    p_arena_merge = arena_sub.add_parser("merge", help="merge arena candidate into existing arena")
    p_arena_merge.add_argument("--pending", required=True)
    p_arena_merge.add_argument("--base", default=".")
    p_arena_merge.add_argument("id")
    p_arena_merge.add_argument("target_slug")
    p_arena_merge.set_defaults(func=cmd_arena_merge)
```

- [ ] **Step 3: Run tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_arena_approve_cli.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add scripts/ingest_qa.py tests/test_arena_approve_cli.py
git commit -m "feat(arena): approve pending arena candidates"
```

---

## Part G: Evaluation Phase 2 extension

### Task G1: Extend eval CLI tests for `--match`

**Files:**
- Modify: `tests/test_ingest_eval_cli.py`
- Modify later: `scripts/ingest_qa.py`

- [ ] **Step 1: Update existing expected dimensions**

In `tests/test_ingest_eval_cli.py`, update the dimension set assertion to exactly:

```python
    assert set(data["dimension_ratings"]) == {
        "coverage_fidelity",
        "reasoning_quality",
        "calibration",
        "narrative",
        "claim_extraction_quality",
        "matching_accuracy",
        "claim_lifecycle_discipline",
    }
```

Update prompt version assertion:

```python
    assert data["eval_prompt_version"] == "phase2-v1"
```

Update readiness assertions:

```python
    assert "system_fit" in data and "phase2_readiness" in data and "phase3_readiness" in data
    assert data["matching_metrics"] == {}
```

- [ ] **Step 2: Add match metrics test**

Append to `tests/test_ingest_eval_cli.py`:

```python

def test_evaluation_init_with_match_adds_matching_metrics(tmp_path):
    bpath = tmp_path / "bundle.json"
    bpath.write_text(json.dumps(_valid_bundle()), encoding="utf-8")
    ppath = tmp_path / "preprocess.json"
    ppath.write_text(json.dumps(_minimal_valid_preprocess()), encoding="utf-8")
    match = {
        "decisions_required": [
            {
                "candidate_id": "cc-001",
                "top_matches": [{"claim_id": "clm-company-0001", "score": 0.82, "high_confidence": True}],
                "decision": "new",
            },
            {
                "candidate_id": "cc-002",
                "top_matches": [{"claim_id": "clm-company-0002", "score": 0.27, "high_confidence": False}],
                "decision": "attach",
            },
            {
                "candidate_id": "cc-003",
                "top_matches": [],
                "decision": "split",
            },
        ]
    }
    mpath = tmp_path / "match.json"
    mpath.write_text(json.dumps(match), encoding="utf-8")
    out = tmp_path / "evaluation.json"

    rc = qa.cmd_evaluation_init(
        Namespace(bundle=str(bpath), preprocess=str(ppath), match=str(mpath), out=str(out))
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["matching_metrics"] == {
        "total_candidates": 3,
        "decisions": {"attach": 1, "new": 1, "split": 1, "skip": 0},
        "high_confidence_matches_not_attached": 1,
        "low_confidence_matches_attached": 1,
    }
```

Also update existing direct `Namespace(...)` calls to include `match=None`:

```python
Namespace(bundle=str(bpath), preprocess=str(ppath), match=None, out=str(out))
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_ingest_eval_cli.py -q
```

Expected: FAIL because `cmd_evaluation_init` does not handle `match`, Phase 2 dimensions, or `matching_metrics` yet.

### Task G2: Implement evaluation init extension

**Files:**
- Modify: `scripts/ingest_qa.py`
- Test: `tests/test_ingest_eval_cli.py`

- [ ] **Step 1: Add matching metrics helper before `cmd_evaluation_init`**

```python
def _matching_metrics(match: dict | None) -> dict:
    if not match:
        return {}
    rows = match.get("decisions_required", []) or []
    decisions = {"attach": 0, "new": 0, "split": 0, "skip": 0}
    high_confidence_not_attached = 0
    low_confidence_attached = 0
    for row in rows:
        decision = row.get("decision")
        if decision in decisions:
            decisions[decision] += 1
        matches = row.get("top_matches", []) or []
        has_high_confidence = any(m.get("high_confidence") or m.get("score", 0) >= 0.80 for m in matches)
        has_low_confidence = any(m.get("score", 0) < 0.30 for m in matches)
        if has_high_confidence and decision != "attach":
            high_confidence_not_attached += 1
        if has_low_confidence and decision == "attach":
            low_confidence_attached += 1
    return {
        "total_candidates": len(rows),
        "decisions": decisions,
        "high_confidence_matches_not_attached": high_confidence_not_attached,
        "low_confidence_matches_attached": low_confidence_attached,
    }
```

- [ ] **Step 2: Modify `cmd_evaluation_init`**

Inside `cmd_evaluation_init`, after reading preprocess, add:

```python
    match = json.loads(Path(args.match).read_text(encoding="utf-8")) if getattr(args, "match", None) else None
```

Change:

```python
        "eval_prompt_version": "phase1.5-v1",
```

to:

```python
        "eval_prompt_version": "phase2-v1",
```

Add two dimensions inside `dimension_ratings`:

```python
            "matching_accuracy": {"trend": None, "notes": ""},
            "claim_lifecycle_discipline": {"trend": None, "notes": ""},
```

After `phase2_readiness`, add:

```python
        "phase3_readiness": {"notes": ""},
        "matching_metrics": _matching_metrics(match),
```

- [ ] **Step 3: Add CLI argument**

In `main()`, under `p_eval_init.add_argument("--preprocess", required=True)`, add:

```python
    p_eval_init.add_argument("--match", help="Phase 2 match decision JSON")
```

- [ ] **Step 4: Run eval tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_ingest_eval_cli.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/ingest_qa.py tests/test_ingest_eval_cli.py
git commit -m "feat(eval): add Phase 2 matching metrics"
```

### Task G3: Update L2 eval prompt

**Files:**
- Modify: `docs/prompts/ingest-eval-l2.md`

- [ ] **Step 1: Update prompt version**

At the top of `docs/prompts/ingest-eval-l2.md`, set or replace the prompt version marker with:

```markdown
<!-- prompt_version: phase2-v1 -->
```

- [ ] **Step 2: Ensure dimension list includes exactly these seven keys**

The prompt must ask the model to fill these `dimension_ratings` keys:

```markdown
- coverage_fidelity
- reasoning_quality
- calibration
- narrative
- claim_extraction_quality
- matching_accuracy
- claim_lifecycle_discipline
```

- [ ] **Step 3: Add Phase 2 matching instructions**

Add this text near the dimension definitions:

```markdown
### Phase 2 matching dimensions

`matching_accuracy` evaluates whether each claim_candidate was matched to the right existing claim or correctly left as new. Penalize duplicate new claims when `top_matches` contained the same semantic claim, and penalize polluted attaches when a candidate was attached despite only weak or unrelated matches.

`claim_lifecycle_discipline` evaluates whether the chosen action (`attach`, `new`, `split`, `skip`) respected the Phase 2 lifecycle. Attach should append evidence without changing confidence/status; split should be reserved for an over-broad existing claim that must be retired and replaced; skip requires a concrete reason.

Also fill `phase3_readiness.notes`: can the current claim registry support Phase 3 narrative `supported_by_claims` references, or are claim IDs/coverage/matching decisions too unstable?
```

- [ ] **Step 4: Verify no old version remains**

Run:

```bash
grep -n "phase1.5-v1\|matching_accuracy\|claim_lifecycle_discipline\|phase3_readiness" docs/prompts/ingest-eval-l2.md
```

Expected: no `phase1.5-v1`; the three Phase 2 terms appear.

- [ ] **Step 5: Commit**

```bash
git add docs/prompts/ingest-eval-l2.md
git commit -m "docs(prompt): extend ingest eval for Phase 2"
```

---

## Part H: Match decision prompt

### Task H1: Add prompt for Claude-in-dialog matching decisions

**Files:**
- Create: `docs/prompts/ingest-claim-match.md`

- [ ] **Step 1: Create prompt file**

Create `docs/prompts/ingest-claim-match.md`:

```markdown
<!-- prompt_version: phase2-v1 -->

# Ingest Claim Match Decision Prompt

You are filling `data/pending/match-<source_id>.json` after Python produced deterministic top_matches. Do not call tools that modify the registry. Your job is semantic judgment only.

## Inputs

1. `match-<source_id>.json`
2. The original review bundle used to generate it
3. Optional surrounding project context supplied by the user

## Output rule

Return the same JSON object with only these fields changed inside each `decisions_required[]` item:

- `decision`: one of `attach`, `new`, `split`, `skip`
- `decision_reason`: one concise sentence
- `direction_on_claim`: required only for `attach`; one of `strengthens`, `weakens`, `neutral`
- `target_claim_id`: required only for `attach`
- `split_instructions`: required only for `split`

Do not change `candidate_payload`, `top_matches`, `summary_stats`, `source_id`, `generated_at`, `bundle_ref`, or `matching_engine_version`.

## Decision rules

Choose `attach` when the candidate is the same semantic claim as an existing top_match and only adds evidence. Set `target_claim_id` to the existing claim. Set `direction_on_claim` by judging how the new evidence affects the existing claim: `strengthens`, `weakens`, or `neutral`.

Choose `new` when no top_match is the same semantic claim. Do not set `direction_on_claim`. Do not set `split_instructions`.

Choose `split` only when an existing claim is too broad or conflates multiple ideas, and this candidate makes the split necessary. Set:

```json
{
  "retire_target_claim_id": "clm-company-0001",
  "new_claims": [
    {
      "claim_text": "specific replacement claim",
      "evidence_subset": {"block_ids": ["ib-001"], "fact_ids": ["fact-001"]}
    }
  ]
}
```

Choose `skip` when the candidate is too weak, duplicate noise, or not useful as a persistent claim. `decision_reason` must say why.

## Hard constraints

- Python apply will only produce claim statuses `active` and `retired`.
- Attach does not change confidence or state_log.
- Split does not migrate historical evidence from the retired claim.
- Do not invent claim IDs.
- Do not add archive decisions here; archive approval uses `archive-writes-<source_id>.json` later.
```

- [ ] **Step 2: Verify prompt markers**

Run:

```bash
grep -n "prompt_version: phase2-v1\|attach\|new\|split\|skip\|Do not invent claim IDs" docs/prompts/ingest-claim-match.md
```

Expected: all terms appear.

- [ ] **Step 3: Commit**

```bash
git add docs/prompts/ingest-claim-match.md
git commit -m "docs(prompt): add claim match decision prompt"
```

---

## Part I: End-to-end coverage and final guardrails

### Task I1: Add minimal Phase 2 end-to-end test

**Files:**
- Create: `tests/test_phase2_end_to_end.py`

- [ ] **Step 1: Write test**

Create `tests/test_phase2_end_to_end.py`:

```python
import json
from argparse import Namespace

from scripts import ingest_apply, ingest_match, ingest_qa


def test_phase2_minimal_match_apply_evaluation_chain(tmp_path):
    bundle = {
        "bundle_version": "v2-phase1",
        "source_digest": {
            "source_id": "src-001",
            "source_date": "2024-12-31",
            "scope_type": "company",
            "scope_ref": "SSE_600519",
        },
        "insight_blocks": [{"id": "ib-001", "title": "品牌", "dimension_hint": "moat"}],
        "atomic_facts": [{"fact_id": "fact-001", "linked_block_id": "ib-001", "fact_text": "事实", "evidence_quote": "原文 A。", "source_page": 1, "confidence": "medium"}],
        "claim_candidates": [
            {
                "candidate_id": "cc-001",
                "claim_text": "茅台品牌溢价来自白酒文化根基",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "claim_type": "judgment",
                "dimension_hint": "moat",
                "confidence": "medium_high",
                "as_of": "2024-12-31",
                "direction_on_source": "supports",
                "supporting_block_ids": ["ib-001"],
            }
        ],
        "company_candidates": [],
        "stage_gates": [],
        "synthesis": {"one_sentence": "s", "what_we_know": [], "what_is_plausible": [], "cannot_conclude": [], "investment_questions": []},
        "schema_fit_review": {"fits_current_schema": True, "missing_schema_fields": [], "extra_fields_needed": [], "notes": ""},
    }
    preprocess = {
        "meta": {"preprocess_version": "v2-phase1"},
        "sections": [{"name": "S1", "text": "原文 A。"}],
        "preprocess_metadata": {"page_count": 1, "extracted_pages": [{"page": 1, "text_quality": "ok"}], "extraction_warnings": []},
        "figure_contexts": [],
    }
    bundle_path = tmp_path / "bundle.json"
    preprocess_path = tmp_path / "preprocess.json"
    match_path = tmp_path / "pending" / "match-src-001.json"
    eval_path = tmp_path / "evaluation.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    preprocess_path.write_text(json.dumps(preprocess, ensure_ascii=False), encoding="utf-8")

    assert ingest_match.cmd_match(Namespace(bundle=str(bundle_path), registry_base=str(tmp_path), out=str(match_path))) == 0
    match = json.loads(match_path.read_text(encoding="utf-8"))
    match["decisions_required"][0]["decision"] = "new"
    match["decisions_required"][0]["decision_reason"] = "无可挂接旧命题"
    match_path.write_text(json.dumps(match, ensure_ascii=False), encoding="utf-8")

    assert ingest_apply.cmd_apply(Namespace(match=str(match_path), bundle=str(bundle_path), registry_base=str(tmp_path))) == 0
    assert ingest_qa.cmd_evaluation_init(Namespace(bundle=str(bundle_path), preprocess=str(preprocess_path), match=str(match_path), out=str(eval_path))) == 0

    claim_lines = (tmp_path / "claims" / "companies.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(claim_lines) == 1
    evaluation = json.loads(eval_path.read_text(encoding="utf-8"))
    assert evaluation["matching_metrics"]["decisions"]["new"] == 1
    assert (tmp_path / "pending" / "archive-writes-src-001.json").exists()
```

- [ ] **Step 2: Run test**

Run:

```bash
.venv/bin/python -m pytest tests/test_phase2_end_to_end.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_phase2_end_to_end.py
git commit -m "test(ingest): cover Phase 2 claim flow"
```

### Task I2: Run full focused suite and guardrail greps

**Files:**
- No code changes unless tests fail.

- [ ] **Step 1: Run focused Phase 2 tests**

```bash
.venv/bin/python -m pytest \
  tests/test_claim_registry.py \
  tests/test_claim_matching.py \
  tests/test_ingest_match_cli.py \
  tests/test_ingest_apply_cli.py \
  tests/test_archive_apply_cli.py \
  tests/test_arena_approve_cli.py \
  tests/test_ingest_eval_cli.py \
  tests/test_phase2_end_to_end.py \
  -q
```

Expected: all PASS.

- [ ] **Step 2: Run full test suite if focused suite passes**

```bash
.venv/bin/python -m pytest -q
```

Expected: all existing tests PASS. If unrelated pre-existing failures appear, capture exact failing test names and ask the user before broad refactors.

- [ ] **Step 3: Verify no forbidden code paths**

Run:

```bash
grep -R "anthropic\|openai\|sqlite3\|review_due\|weakened\|strengthened\|conflicted\|user_override" app/io/claim_registry.py app/io/claim_matching.py scripts/ingest_match.py scripts/ingest_apply.py scripts/ingest_qa.py
```

Expected:
- No `anthropic`, `openai`, or `sqlite3`.
- `user_override` appears only as a field set to `None` in `claim_registry.py`.
- `review_due`, `weakened`, `strengthened`, `conflicted` do not appear in new implementation files.

Run:

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl' app/templates static
```

Expected: no diff.

- [ ] **Step 4: Commit any test-fix changes**

Only if fixes were needed:

```bash
git add <changed-files>
git commit -m "fix(claims): stabilize Phase 2 claim flow"
```

---

## 3. Manual smoke command sequence after implementation

Run this only after all tasks pass. Use temporary files; do not write real project archive entries until the user has reviewed pending files.

```bash
.venv/bin/python scripts/ingest_match.py \
  --bundle /path/to/bundle.json \
  --registry-base data \
  --out data/pending/match-<source_id>.json
```

Then fill `decision`, `decision_reason`, `direction_on_claim`, `target_claim_id`, and `split_instructions` manually using `docs/prompts/ingest-claim-match.md`.

```bash
.venv/bin/python scripts/ingest_apply.py \
  --match data/pending/match-<source_id>.json \
  --bundle /path/to/bundle.json \
  --registry-base data
```

Then review generated pending files before applying:

```bash
.venv/bin/python scripts/ingest_qa.py evaluation init \
  --bundle /path/to/bundle.json \
  --preprocess /path/to/preprocess.json \
  --match data/pending/match-<source_id>.json \
  --out /path/to/evaluation.json
```

Do not run `archive apply` or `arena approve` on real project files until the user explicitly approves the pending file contents.

---

## 4. Self-review checklist for plan author

### Spec coverage

- Claim registry JSONL and counters: Part A.
- Scope-level files under `data/claims`: Part A.
- Matching engine scope/status/type/dimension/bigram/top-3 thresholds: Part B and C.
- Pending `match-<source_id>.json`: Part C.
- Manual Claude decision fields: Part H.
- Apply actions `new`, `attach`, `split`, `skip`: Part D.
- Attach does not change confidence/state_log: Task A3 and D1 tests.
- Split retires original and does not migrate history: Task A3 and D3 tests.
- Archive pending generation and apply gate with only `new`/`append`: Part E.
- Arena pending approve/reject/merge: Part F.
- Evaluation `--match`, new dimensions, `phase3_readiness`: Part G.
- No V0/web/LLM/SQLite/review queue/narrative scope: guardrails and Task I2 greps.

### Placeholder scan

This plan intentionally contains no `TBD`, no `TODO`, no “implement later,” and no unexpanded “write tests for the above.” The only `NotImplementedError` appears as an intentional failing midpoint in Task D2 and is removed in Task D3.

### Type and name consistency

- Registry class name is always `ClaimRegistry`.
- Evidence helper is always `build_evidence_entry`.
- Matching function is always `match_candidate`.
- Match pending field is always `decisions_required`.
- Attach target field is always `target_claim_id`.
- Split target field is always `split_instructions.retire_target_claim_id`.
- Evaluation helper is always `_matching_metrics`.

---

Plan complete and saved to `docs/superpowers/plans/2026-04-30-phase2-claim-layer.md`.

Two execution options:

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?

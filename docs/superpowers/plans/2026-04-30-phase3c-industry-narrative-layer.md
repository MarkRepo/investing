# Phase 3C Industry Investment Narrative Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** Phase 3B (`docs/superpowers/plans/2026-04-30-phase3b-company-narrative-layer.md`) must be merged first. This plan assumes `app/io/narrative_proposals.py` already exposes the scope-aware `SCOPE_CONFIGS` registry, `dimension_path`, `flags_path`, `build_proposal_file(..., scope_type=, scope_ref=)`, `read_narrative_flags(scope_type, scope_ref, base=)`, and `scan_narrative_flags(..., scope_type=, scope_ref=)` surface introduced there. If you're reading this before Phase 3B landed, stop and execute Phase 3B first.

**Goal:** Add the **industry** scope to the narrative machinery: claim-driven pending industry narrative proposals, approved Markdown writes, manual narrative review flags, and minimal industry detail page flag display. Phase 3A arena and Phase 3B company behavior must remain intact.

**Architecture:** Add an `"industry"` entry to the existing `SCOPE_CONFIGS` registry pointing at `industries/<slug>/<dim-kebab>.md`. Add an industry-specific claim→narrative mapping. Add three thin CLI wrappers in `scripts/` mirroring the existing arena and company trios. Wire `app/routes/industries.py` and `detail.html` to render per-dimension flags.

**Tech Stack:** Python 3 stdlib (`argparse`, `json`, `pathlib`, `datetime`, `shutil`), pytest, JSON/JSONL, Markdown files, existing FastAPI/Jinja industry route/template.

---

## 0. Mandatory guardrails

Before every task, re-read this section. If implementation drifts into a forbidden item, stop and revert that drift before continuing.

**Allowed Phase 3C outputs:**
- `data/pending/narrative-proposals-<source_id>.json` (with `scope_type == "industry"`)
- `data/pending/archive/narrative-proposals-<source_id>.json`
- `data/audit/narrative-events.jsonl` appends
- `industries/<slug>/<dim-kebab>.md` appends for approved/edit proposals (only the 10 non-definition dims)
- `industries/<slug>/narrative-flags.jsonl`
- minimal industry detail page flag display
- one `SCOPE_CONFIGS["industry"]` entry + one `CLAIM_DIMENSION_TO_INDUSTRY_NARRATIVE` constant in `app/io/narrative_proposals.py`

**Forbidden in this plan:**
- Do not call `anthropic`, `openai`, browser automation, or any LLM API from Python.
- Do not generate final narrative prose automatically in Python.
- Do not auto-rewrite existing industry narrative Markdown.
- Do not modify `industries/<slug>/definition.md` from proposal apply.
- Do not modify `industries/<slug>/meta.yaml`, `industries/<slug>/observations.jsonl`, `industries/<slug>/figure_contexts.jsonl`, `industries/<slug>/qa_warnings.jsonl`, or `industries/<slug>/sources/**`.
- Do not implement memo frontmatter reverse references (deferred).
- Do not implement review queue, cron, event adapters, daemons, or periodic scans.
- Do not modify `app/io/claims.py`.
- Do not modify `companies/**`.
- Do not modify `arenas/**` except test tmp dirs created inside pytest.
- Do not add proposal approval/editing UI.
- Do not add dismiss behavior for flags.
- Do not change Phase 3A arena or Phase 3B company JSON contracts, CLI flags, or route behavior.

**Verification after each implementation task:**

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl' 'industries/*/meta.yaml' 'industries/*/observations.jsonl' 'industries/*/definition.md' 'industries/*/figure_contexts.jsonl' 'industries/*/qa_warnings.jsonl'
```

Expected: no diff. If there is a diff, revert it before continuing.

**Phase 3A + 3B regression guard after each implementation task:**

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

Expected: PASS. If any previous-phase test fails, stop and fix before moving on.

---

## 1. File map

### Create

- `scripts/industry_narrative_propose.py` — industry propose CLI.
- `scripts/industry_narrative_apply.py` — industry apply CLI.
- `scripts/industry_narrative_flags.py` — industry flag CLI.
- `tests/test_industry_narrative_proposals.py` — industry proposal generation + apply unit tests.
- `tests/test_industry_narrative_apply_cli.py` — industry propose/apply CLI tests.
- `tests/test_industry_narrative_flags.py` — industry flag scan/read tests.
- `tests/test_industries_narrative_flags.py` — industry route/template flag display test.
- `tests/test_phase3c_narrative_end_to_end.py` — industry e2e test.

### Modify

- `app/io/narrative_proposals.py` — add `CLAIM_DIMENSION_TO_INDUSTRY_NARRATIVE` constant and `SCOPE_CONFIGS["industry"]` entry.
- `app/routes/industries.py` — read industry narrative flags; pass per-dimension flags to template.
- `app/templates/industries/detail.html` — show `needs review` badges and flag details.

### Do not modify

- `app/io/claims.py`
- `app/io/claim_registry.py`
- `companies/**`
- `arenas/**` except test tmp dirs created inside pytest
- `industries/<slug>/meta.yaml`
- `industries/<slug>/observations.jsonl`
- `industries/<slug>/figure_contexts.jsonl`
- `industries/<slug>/qa_warnings.jsonl`
- `industries/<slug>/definition.md`
- `industries/<slug>/sources/**`
- `app/routes/companies.py`, `app/routes/arenas.py`
- `app/templates/companies/**`, `app/templates/arenas/**`
- `scripts/narrative_propose.py`, `scripts/narrative_apply.py`, `scripts/narrative_flags.py`
- `scripts/company_narrative_*.py`

---

## 2. Data contracts to use exactly

### 2.1 Industry scope_ref format

Industry `scope_ref` values are the slug (e.g., `"cn-power-equipment"`, `"cn-cmp-material"`) — the same slug used by `industries/<slug>/` directories and by `claims/industries.jsonl` Phase 2 entries. Slugs are kebab-case, validated by `app.io.industry._validate_slug`.

### 2.2 Proposal file shape

`scripts/industry_narrative_propose.py` writes this structure:

```python
{
    "source_id": "src-001",
    "generated_at": "2026-04-30T12:00:00+00:00",
    "proposal_version": "phase3a-v1",
    "scope_type": "industry",
    "scope_ref": "cn-power-equipment",
    "proposals": [
        {
            "proposal_id": "np-001",
            "scope_type": "industry",
            "scope_ref": "cn-power-equipment",
            "dimension": "market_size",
            "title": "Draft narrative for market_size",
            "body": None,
            "supported_by_claims": ["clm-industry-0001"],
            "source_ids": ["src-001"],
            "evidence_summary": [
                {
                    "claim_id": "clm-industry-0001",
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

No `arena_slug` key on industry proposals or on the file root. `proposal_version` stays `"phase3a-v1"` — the schema didn't change between phases, only scopes were added.

### 2.3 Decision rules

Same as Phase 3A/3B. Additional constraints for industry:
- dimension must be in `cfg.INDUSTRY_DIMENSIONS`.
- dimension must NOT be `"definition"` (excluded — industry `definition.md` is maintained manually, like arena `definition.md`).

### 2.4 Markdown append format

Same exact block as arena/company. Target path for industry: `industries/<slug>/<dim-kebab>.md`, where `dim-kebab = dim.replace("_", "-")`. No `narratives/` subdirectory (industry uses the slug dir directly, like arena).

### 2.5 Flag file shape

Same line shape as arena/company. Path for industry: `industries/<slug>/narrative-flags.jsonl`. Dedup key: `(dimension, segment_ref, supported_by_claim, reason)`.

### 2.6 Industry dimension mapping

```python
CLAIM_DIMENSION_TO_INDUSTRY_NARRATIVE = {
    "market_size": "market_size",
    "tam": "market_size",
    "lifecycle": "lifecycle",
    "stage_gate": "lifecycle",
    "value_chain": "value_chain",
    "supply_chain": "value_chain",
    "competition": "competition",
    "competitive_position": "competition",
    "participants": "competition",
    "drivers": "drivers",
    "catalysts": "drivers",
    "technology": "technology",
    "regulation": "regulation",
    "benchmark": "benchmark",
    "winning_variables": "benchmark",
    "moat": "benchmark",
    "risk": "risks",
    "risks": "risks",
    "scenario": "risks",
    "valuation": "valuation",
    "investment_view": "valuation",
    "thesis": "drivers",
    "judgment": "drivers",
}
```

Any `dimension_hint` not present here goes to `unmapped_claims[]` with `reason == "unmapped dimension_hint"`. Do not invent silent defaults.

---

## Part A: Register industry scope

### Task A1: Add failing industry surface tests

**Files:**
- Modify: `tests/test_narrative_proposals.py`
- Modify later: `app/io/narrative_proposals.py`

- [ ] **Step 1: Append scope-surface tests for industry**

Append this to `tests/test_narrative_proposals.py`:

```python
from app.io.narrative_proposals import (
    CLAIM_DIMENSION_TO_INDUSTRY_NARRATIVE,
)


def test_scope_configs_cover_industry():
    from app.io.narrative_proposals import SCOPE_CONFIGS, narrative_dims_for_scope
    assert "industry" in SCOPE_CONFIGS
    dims = narrative_dims_for_scope("industry")
    assert "definition" not in dims
    from app import config as cfg
    assert set(dims) == {d for d in cfg.INDUSTRY_DIMENSIONS if d != "definition"}


def test_dimension_path_for_industry(tmp_path):
    from app.io.narrative_proposals import dimension_path
    path = dimension_path(tmp_path, "industry", "cn-power-equipment", "market_size")
    assert path == tmp_path / "industries" / "cn-power-equipment" / "market-size.md"

    path2 = dimension_path(tmp_path, "industry", "cn-power-equipment", "value_chain")
    assert path2.name == "value-chain.md"


def test_flags_path_for_industry(tmp_path):
    from app.io.narrative_proposals import flags_path
    path = flags_path(tmp_path, "industry", "cn-power-equipment")
    assert path == tmp_path / "industries" / "cn-power-equipment" / "narrative-flags.jsonl"


def test_industry_dimension_mapping_spot_checks():
    from app.io.narrative_proposals import map_claim_dimension
    assert map_claim_dimension("market_size", "industry") == "market_size"
    assert map_claim_dimension("stage_gate", "industry") == "lifecycle"
    assert map_claim_dimension("supply_chain", "industry") == "value_chain"
    assert map_claim_dimension("competition", "industry") == "competition"
    assert map_claim_dimension("regulation", "industry") == "regulation"
    assert map_claim_dimension("benchmark", "industry") == "benchmark"
    assert map_claim_dimension("risk", "industry") == "risks"
    assert map_claim_dimension("valuation", "industry") == "valuation"
    assert CLAIM_DIMENSION_TO_INDUSTRY_NARRATIVE["thesis"] == "drivers"
```

- [ ] **Step 2: Run and verify failure**

```bash
.venv/bin/python -m pytest tests/test_narrative_proposals.py -q
```

Expected: FAIL with `ImportError` for `CLAIM_DIMENSION_TO_INDUSTRY_NARRATIVE`, and/or `ValueError: unsupported scope_type: industry` for the path tests.

- [ ] **Step 3: Commit tests only**

```bash
git add tests/test_narrative_proposals.py
git commit -m "test(narrative): define industry scope surface"
```

### Task A2: Register industry scope

**Files:**
- Modify: `app/io/narrative_proposals.py`

- [ ] **Step 1: Add the industry mapping constant**

In `app/io/narrative_proposals.py`, immediately after the existing `CLAIM_DIMENSION_TO_COMPANY_NARRATIVE = {...}` block, add:

```python
CLAIM_DIMENSION_TO_INDUSTRY_NARRATIVE = {
    "market_size": "market_size",
    "tam": "market_size",
    "lifecycle": "lifecycle",
    "stage_gate": "lifecycle",
    "value_chain": "value_chain",
    "supply_chain": "value_chain",
    "competition": "competition",
    "competitive_position": "competition",
    "participants": "competition",
    "drivers": "drivers",
    "catalysts": "drivers",
    "technology": "technology",
    "regulation": "regulation",
    "benchmark": "benchmark",
    "winning_variables": "benchmark",
    "moat": "benchmark",
    "risk": "risks",
    "risks": "risks",
    "scenario": "risks",
    "valuation": "valuation",
    "investment_view": "valuation",
    "thesis": "drivers",
    "judgment": "drivers",
}
```

- [ ] **Step 2: Register the industry scope entry**

Inside the existing `SCOPE_CONFIGS: dict[str, ScopeConfig] = { ... }` literal, add one more entry after the `"company"` entry (still inside the same dict):

```python
    "industry": ScopeConfig(
        scope_type="industry",
        narrative_dims=tuple(d for d in cfg.INDUSTRY_DIMENSIONS if d != "definition"),
        mapping=CLAIM_DIMENSION_TO_INDUSTRY_NARRATIVE,
        top_dir="industries",
        narrative_subdir=None,
    ),
```

- [ ] **Step 3: Run surface tests**

```bash
.venv/bin/python -m pytest tests/test_narrative_proposals.py -q
```

Expected: PASS.

- [ ] **Step 4: Run Phase 3A + 3B regression**

```bash
.venv/bin/python -m pytest \
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

- [ ] **Step 5: Run guardrail diff**

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl' 'industries/*/meta.yaml' 'industries/*/observations.jsonl' 'industries/*/definition.md' 'industries/*/figure_contexts.jsonl' 'industries/*/qa_warnings.jsonl'
```

Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add app/io/narrative_proposals.py
git commit -m "feat(narrative): register industry scope"
```

---

## Part B: Industry proposal generation and apply

### Task B1: Add failing industry proposal tests

**Files:**
- Create: `tests/test_industry_narrative_proposals.py`

- [ ] **Step 1: Write tests**

Create `tests/test_industry_narrative_proposals.py` with this content:

```python
from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from app.io.narrative_proposals import (
    apply_proposal_file,
    build_proposal_file,
    validate_proposal_decisions,
)


def _create_claim(
    registry,
    *,
    claim_text="中国变压器行业进入容量扩张中后期",
    scope_type="industry",
    scope_ref="cn-power-equipment",
    dimension_hint="lifecycle",
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


def test_build_industry_proposal_file_groups_active_claims(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)

    result = build_proposal_file(
        registry=registry,
        source_id="src-001",
        generated_at="2026-04-30T12:00:00+00:00",
        scope_type="industry",
        scope_ref="cn-power-equipment",
        existing_excerpt_loader=lambda scope_type, scope_ref, dim: f"existing {scope_type} {scope_ref} {dim}",
    )

    assert result["scope_type"] == "industry"
    assert result["scope_ref"] == "cn-power-equipment"
    assert result["unmapped_claims"] == []
    assert result["summary_stats"] == {
        "total_proposals": 1,
        "scope_count": 1,
        "dimension_count": 1,
        "unsupported_candidates_skipped": 0,
    }
    proposal = result["proposals"][0]
    assert proposal["scope_type"] == "industry"
    assert proposal["scope_ref"] == "cn-power-equipment"
    assert "arena_slug" not in proposal
    assert proposal["dimension"] == "lifecycle"
    assert proposal["supported_by_claims"] == [claim["claim_id"]]
    assert proposal["existing_narrative_excerpt"] == "existing industry cn-power-equipment lifecycle"


def test_build_industry_proposal_file_filters_other_scopes_and_sources(tmp_path):
    registry = ClaimRegistry(tmp_path)
    _create_claim(registry, status="retired")
    _create_claim(registry, scope_type="arena", scope_ref="cn-bci-industrialization")
    _create_claim(registry, scope_type="company", scope_ref="SSE_600519")
    _create_claim(registry, source_id="src-other")

    result = build_proposal_file(
        registry=registry,
        source_id="src-001",
        generated_at="2026-04-30T12:00:00+00:00",
        scope_type="industry",
        scope_ref="cn-power-equipment",
        existing_excerpt_loader=lambda scope_type, scope_ref, dim: "",
    )

    assert result["proposals"] == []
    assert result["unmapped_claims"] == []


def test_validate_industry_proposal_rejects_definition_dimension(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)
    data = {
        "source_id": "src-001",
        "proposal_version": "phase3a-v1",
        "scope_type": "industry",
        "scope_ref": "cn-power-equipment",
        "proposals": [
            {
                "proposal_id": "np-001",
                "scope_type": "industry",
                "scope_ref": "cn-power-equipment",
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
    assert any("invalid narrative dimension 'definition' for scope industry" in e for e in errors)


def test_apply_industry_proposal_writes_to_slug_dir(tmp_path):
    import json
    registry = ClaimRegistry(tmp_path)
    claim = _create_claim(registry)
    slug_dir = tmp_path / "industries" / "cn-power-equipment"
    slug_dir.mkdir(parents=True)
    (slug_dir / "lifecycle.md").write_text("# lifecycle · 电力设备\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    data = {
        "source_id": "src-001",
        "proposal_version": "phase3a-v1",
        "scope_type": "industry",
        "scope_ref": "cn-power-equipment",
        "proposals": [
            {
                "proposal_id": "np-001",
                "scope_type": "industry",
                "scope_ref": "cn-power-equipment",
                "dimension": "lifecycle",
                "title": "行业进入容量扩张中后期",
                "body": "下游电网投资周期推动容量扩张进入中后期。",
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
    text = (slug_dir / "lifecycle.md").read_text(encoding="utf-8")
    assert "### 行业进入容量扩张中后期" in text
    assert "下游电网投资周期推动容量扩张进入中后期。" in text
    assert f"supported_by_claims: [{claim['claim_id']}]" in text
    archived = tmp_path / "data" / "pending" / "archive" / pending.name
    assert archived.exists()
```

- [ ] **Step 2: Run tests**

```bash
.venv/bin/python -m pytest tests/test_industry_narrative_proposals.py -q
```

Expected: PASS. (The scope-aware refactor in Phase 3B + Task A2 above already supplies all the code paths; this suite is a verification-by-test step.)

- [ ] **Step 3: Run Phase 3A + 3B regression**

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

- [ ] **Step 4: Run guardrail diff**

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl' 'industries/*/meta.yaml' 'industries/*/observations.jsonl' 'industries/*/definition.md' 'industries/*/figure_contexts.jsonl' 'industries/*/qa_warnings.jsonl'
```

Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add tests/test_industry_narrative_proposals.py
git commit -m "test(narrative): cover industry proposal generation"
```

---

## Part C: Industry CLI wrappers

### Task C1: Add failing industry CLI tests

**Files:**
- Create: `tests/test_industry_narrative_apply_cli.py`
- Create: `tests/test_industry_narrative_flags.py`

- [ ] **Step 1: Write `tests/test_industry_narrative_apply_cli.py`**

```python
import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import industry_narrative_apply, industry_narrative_propose


def _seed_industry_claim(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    return registry.create_claim(
        claim_text="中国变压器行业进入容量扩张中后期",
        scope_type="industry",
        scope_ref="cn-power-equipment",
        claim_type="judgment",
        dimension_hint="lifecycle",
        confidence="medium_high",
        as_of="2025-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )


def test_industry_narrative_propose_writes_pending_json(tmp_path):
    claim = _seed_industry_claim(tmp_path)
    slug_dir = tmp_path / "industries" / "cn-power-equipment"
    slug_dir.mkdir(parents=True)
    (slug_dir / "lifecycle.md").write_text("# lifecycle\n\nold lifecycle text", encoding="utf-8")
    out = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"

    rc = industry_narrative_propose.cmd_propose(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            source_id="src-001",
            industry="cn-power-equipment",
            out=str(out),
        )
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["scope_type"] == "industry"
    assert data["scope_ref"] == "cn-power-equipment"
    proposal = data["proposals"][0]
    assert proposal["scope_type"] == "industry"
    assert proposal["scope_ref"] == "cn-power-equipment"
    assert proposal["supported_by_claims"] == [claim["claim_id"]]
    assert proposal["existing_narrative_excerpt"].endswith("old lifecycle text")


def test_industry_narrative_apply_returns_nonzero_for_invalid_file(tmp_path, capsys):
    _seed_industry_claim(tmp_path)
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    pending.write_text(
        json.dumps(
            {
                "source_id": "src-001",
                "proposal_version": "phase3a-v1",
                "scope_type": "industry",
                "scope_ref": "cn-power-equipment",
                "proposals": [
                    {
                        "proposal_id": "np-001",
                        "scope_type": "industry",
                        "scope_ref": "cn-power-equipment",
                        "dimension": "lifecycle",
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

    rc = industry_narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )

    assert rc == 1
    captured = capsys.readouterr()
    assert "supported_by_claims required" in captured.err
    assert pending.exists()


def test_industry_narrative_apply_applies_valid_file(tmp_path):
    claim = _seed_industry_claim(tmp_path)
    slug_dir = tmp_path / "industries" / "cn-power-equipment"
    slug_dir.mkdir(parents=True)
    (slug_dir / "lifecycle.md").write_text("# lifecycle\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"
    pending.parent.mkdir(parents=True)
    pending.write_text(
        json.dumps(
            {
                "source_id": "src-001",
                "proposal_version": "phase3a-v1",
                "scope_type": "industry",
                "scope_ref": "cn-power-equipment",
                "proposals": [
                    {
                        "proposal_id": "np-001",
                        "scope_type": "industry",
                        "scope_ref": "cn-power-equipment",
                        "dimension": "lifecycle",
                        "title": "容量扩张中后期",
                        "body": "下游电网投资周期推动容量扩张进入中后期。",
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

    rc = industry_narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )

    assert rc == 0
    text = (slug_dir / "lifecycle.md").read_text(encoding="utf-8")
    assert "下游电网投资周期推动容量扩张进入中后期。" in text
    assert (tmp_path / "data" / "pending" / "archive" / pending.name).exists()
```

- [ ] **Step 2: Write `tests/test_industry_narrative_flags.py`**

```python
import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from app.io.narrative_proposals import read_narrative_flags, scan_narrative_flags
from scripts import industry_narrative_flags


def _claim(registry, *, status="active", direction="supports"):
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction=direction,
        now="2026-04-30T12:00:00+00:00",
    )
    claim = registry.create_claim(
        claim_text="中国变压器行业进入容量扩张中后期",
        scope_type="industry",
        scope_ref="cn-power-equipment",
        claim_type="judgment",
        dimension_hint="lifecycle",
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


def _write_segment(tmp_path, claim_id, dim="lifecycle"):
    slug_dir = tmp_path / "industries" / "cn-power-equipment"
    slug_dir.mkdir(parents=True, exist_ok=True)
    (slug_dir / f"{dim.replace('_', '-')}.md").write_text(
        "# heading\n\n"
        "### 容量扩张中后期\n\n"
        "status: active\n"
        "last_written: 2026-04-30\n"
        f"supported_by_claims: [{claim_id}]\n"
        "source_ids: [src-001]\n"
        "proposal_id: np-001\n\n"
        "正文。\n",
        encoding="utf-8",
    )


def test_scan_industry_flags_no_flag_for_active(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry)
    _write_segment(tmp_path, claim["claim_id"])

    flags = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="industry",
        scope_ref="cn-power-equipment",
        now="2026-04-30T12:00:00+00:00",
    )

    assert flags == []
    assert read_narrative_flags("industry", "cn-power-equipment", base=tmp_path) == []


def test_scan_industry_flags_writes_critical_for_retired(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, status="retired")
    _write_segment(tmp_path, claim["claim_id"])

    flags = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="industry",
        scope_ref="cn-power-equipment",
        now="2026-04-30T12:00:00+00:00",
    )

    assert len(flags) == 1
    assert flags[0]["flag_level"] == "critical"
    assert flags[0]["reason"] == "supporting claim retired"
    assert flags[0]["scope_type"] == "industry"
    assert flags[0]["scope_ref"] == "cn-power-equipment"


def test_scan_industry_flags_dedups_on_rerun(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, direction="refutes")
    _write_segment(tmp_path, claim["claim_id"])

    first = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="industry",
        scope_ref="cn-power-equipment",
        now="2026-04-30T12:00:00+00:00",
    )
    second = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="industry",
        scope_ref="cn-power-equipment",
        now="2026-04-30T12:01:00+00:00",
    )

    assert len(first) == 1
    assert first[0]["flag_level"] == "significant"
    assert second == []


def test_industry_narrative_flags_cli(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, status="retired")
    _write_segment(tmp_path, claim["claim_id"])

    rc = industry_narrative_flags.cmd_flags(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            industry="cn-power-equipment",
        )
    )

    assert rc == 0
    flag_file = tmp_path / "industries" / "cn-power-equipment" / "narrative-flags.jsonl"
    rows = [json.loads(line) for line in flag_file.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["reason"] == "supporting claim retired"
```

- [ ] **Step 3: Run and verify failure**

```bash
.venv/bin/python -m pytest tests/test_industry_narrative_apply_cli.py tests/test_industry_narrative_flags.py -q
```

Expected: FAIL with import errors for `scripts.industry_narrative_apply`, `scripts.industry_narrative_propose`, and `scripts.industry_narrative_flags`.

- [ ] **Step 4: Commit tests only**

```bash
git add tests/test_industry_narrative_apply_cli.py tests/test_industry_narrative_flags.py
git commit -m "test(narrative): define industry CLI behavior"
```

### Task C2: Implement industry CLI wrappers

**Files:**
- Create: `scripts/industry_narrative_propose.py`
- Create: `scripts/industry_narrative_apply.py`
- Create: `scripts/industry_narrative_flags.py`

- [ ] **Step 1: Create `scripts/industry_narrative_propose.py`**

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.io import industry as industry_io
from app.io.claim_registry import ClaimRegistry
from app.io.narrative_proposals import build_proposal_file, now_iso


def _existing_excerpt(base: Path, slug: str, dimension: str) -> str:
    md = industry_io.read_narrative(slug, dimension, base=base)
    return md[-1200:] if len(md) > 1200 else md


def cmd_propose(args: argparse.Namespace) -> int:
    base = Path(args.base)
    slug = args.industry.strip()
    registry = ClaimRegistry(Path(args.registry_base))
    data = build_proposal_file(
        registry=registry,
        source_id=args.source_id,
        generated_at=now_iso(),
        scope_type="industry",
        scope_ref=slug,
        existing_excerpt_loader=lambda _st, _sr, dim: _existing_excerpt(base, slug, dim),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ industry narrative proposals written to {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="industry_narrative_propose")
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--base", default=".")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--industry", required=True, help="industry slug, e.g. cn-power-equipment")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    return cmd_propose(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Create `scripts/industry_narrative_apply.py`**

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
    if data.get("scope_type") != "industry":
        print(f"✗ expected scope_type=industry, got {data.get('scope_type')!r}", file=sys.stderr)
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
        "✓ industry narrative proposals applied: "
        f"applied={counts['applied']} rejected={counts['rejected']} deferred={counts['deferred']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="industry_narrative_apply")
    parser.add_argument("--proposals", required=True)
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--base", default=".")
    args = parser.parse_args(argv)
    return cmd_apply(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Create `scripts/industry_narrative_flags.py`**

```python
from __future__ import annotations

import argparse
from pathlib import Path

from app.io.claim_registry import ClaimRegistry
from app.io.narrative_proposals import scan_narrative_flags


def cmd_flags(args: argparse.Namespace) -> int:
    slug = args.industry.strip()
    registry = ClaimRegistry(Path(args.registry_base))
    flags = scan_narrative_flags(
        registry=registry,
        base=Path(args.base),
        scope_type="industry",
        scope_ref=slug,
    )
    print(f"✓ industry narrative flags generated: {len(flags)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="industry_narrative_flags")
    parser.add_argument("--registry-base", default="data")
    parser.add_argument("--base", default=".")
    parser.add_argument("--industry", required=True, help="industry slug, e.g. cn-power-equipment")
    args = parser.parse_args(argv)
    return cmd_flags(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run industry CLI tests**

```bash
.venv/bin/python -m pytest tests/test_industry_narrative_apply_cli.py tests/test_industry_narrative_flags.py -q
```

Expected: PASS.

- [ ] **Step 5: Run Phase 3A + 3B + previous 3C tests**

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
  tests/test_industry_narrative_proposals.py \
  tests/test_industry_narrative_apply_cli.py \
  tests/test_industry_narrative_flags.py \
  -q
```

Expected: PASS.

- [ ] **Step 6: Run guardrail diff**

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl' 'industries/*/meta.yaml' 'industries/*/observations.jsonl' 'industries/*/definition.md' 'industries/*/figure_contexts.jsonl' 'industries/*/qa_warnings.jsonl'
```

Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add scripts/industry_narrative_propose.py scripts/industry_narrative_apply.py scripts/industry_narrative_flags.py
git commit -m "feat(narrative): add industry proposal CLI workflow"
```

---

## Part D: Industry detail page flag display

### Task D1: Add failing industry flag display test

**Files:**
- Create: `tests/test_industries_narrative_flags.py`

- [ ] **Step 1: Write route/template test**

Create `tests/test_industries_narrative_flags.py` with this content:

```python
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.io import industry as industry_io
from app.routes import industries as industries_route


def test_industry_detail_displays_narrative_flags(tmp_path, monkeypatch):
    monkeypatch.setattr(industry_io.cfg, "INDUSTRIES_DIR", tmp_path / "industries")
    monkeypatch.setattr(industries_route.cfg, "INDUSTRIES_DIR", tmp_path / "industries")
    industry_io.create_industry(
        slug="cn-power-equipment",
        name="中国电力设备",
        scope="CN",
        base=tmp_path,
    )
    flags_path = tmp_path / "industries" / "cn-power-equipment" / "narrative-flags.jsonl"
    flags_path.write_text(
        json.dumps(
            {
                "flag_id": "nf-0001",
                "created_at": "2026-04-30T12:00:00+00:00",
                "dimension": "lifecycle",
                "segment_ref": "lifecycle.md#np-001",
                "supported_by_claim": "clm-industry-0001",
                "scope_type": "industry",
                "scope_ref": "cn-power-equipment",
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
    app.include_router(industries_route.router)
    client = TestClient(app)

    response = client.get("/industries/cn-power-equipment")

    assert response.status_code == 200
    assert "needs review" in response.text
    assert "supporting claim retired" in response.text
    assert "clm-industry-0001" in response.text
```

- [ ] **Step 2: Run and verify failure**

```bash
.venv/bin/python -m pytest tests/test_industries_narrative_flags.py -q
```

Expected: FAIL — the industry page does not yet read or render flags.

- [ ] **Step 3: Commit tests only**

```bash
git add tests/test_industries_narrative_flags.py
git commit -m "test(industry): define narrative flag display"
```

### Task D2: Wire flags into industry route and template

**Files:**
- Modify: `app/routes/industries.py`
- Modify: `app/templates/industries/detail.html`

- [ ] **Step 1: Add import in `app/routes/industries.py`**

In `app/routes/industries.py`, near the existing `from app.io import ...` block, add:

```python
from app.io import narrative_proposals as narrative_io
```

- [ ] **Step 2: Read flags in the detail view**

In `app/routes/industries.py`, inside `industry_detail`, replace the existing narratives block

```python
    narratives = []
    for dim in cfg.INDUSTRY_DIMENSIONS:
        md = industry_io.read_narrative(slug, dim)
        has_content = md.strip() and not _is_skeleton_only(md)
        narratives.append({
            "dim": dim,
            "label": _INDUSTRY_DIM_LABEL.get(dim, dim),
            "has_content": bool(has_content),
            "html": _md.markdown(md, extensions=["tables", "fenced_code"]) if md else "",
        })
```

with:

```python
    industry_flags = narrative_io.read_narrative_flags("industry", slug)
    flags_by_dimension = {}
    for flag in industry_flags:
        flags_by_dimension.setdefault(flag.get("dimension"), []).append(flag)
    narratives = []
    for dim in cfg.INDUSTRY_DIMENSIONS:
        md = industry_io.read_narrative(slug, dim)
        has_content = md.strip() and not _is_skeleton_only(md)
        dim_flags = flags_by_dimension.get(dim, [])
        narratives.append({
            "dim": dim,
            "label": _INDUSTRY_DIM_LABEL.get(dim, dim),
            "has_content": bool(has_content),
            "html": _md.markdown(md, extensions=["tables", "fenced_code"]) if md else "",
            "flags": dim_flags,
            "needs_review": bool(dim_flags),
        })
```

- [ ] **Step 3: Update template `app/templates/industries/detail.html`**

Replace the existing 11-dim narrative block (lines around 31–45 in the current file) with:

```jinja2
<h2>11 维叙述</h2>
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
      <p class="hint"><em>尚无来源块。下一次该维度的 ingest 会 append。</em></p>
    {% endif %}
  </details>
{% endfor %}
```

- [ ] **Step 4: Run industry flag display test**

```bash
.venv/bin/python -m pytest tests/test_industries_narrative_flags.py -q
```

Expected: PASS.

- [ ] **Step 5: Run nearby industry regression tests**

```bash
.venv/bin/python -m pytest -k "industr" -q
```

Expected: PASS.

- [ ] **Step 6: Run guardrail diff**

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl' 'industries/*/meta.yaml' 'industries/*/observations.jsonl' 'industries/*/definition.md' 'industries/*/figure_contexts.jsonl' 'industries/*/qa_warnings.jsonl'
```

Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add app/routes/industries.py app/templates/industries/detail.html
git commit -m "feat(industry): show narrative review flags"
```

---

## Part E: End-to-end verification

### Task E1: Add and run the industry e2e test

**Files:**
- Create: `tests/test_phase3c_narrative_end_to_end.py`

- [ ] **Step 1: Write e2e test**

Create `tests/test_phase3c_narrative_end_to_end.py` with this content:

```python
import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import (
    industry_narrative_apply,
    industry_narrative_flags,
    industry_narrative_propose,
)


def test_phase3c_propose_apply_flag_flow(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    claim = registry.create_claim(
        claim_text="中国变压器行业进入容量扩张中后期",
        scope_type="industry",
        scope_ref="cn-power-equipment",
        claim_type="judgment",
        dimension_hint="lifecycle",
        confidence="medium_high",
        as_of="2025-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    slug_dir = tmp_path / "industries" / "cn-power-equipment"
    slug_dir.mkdir(parents=True)
    (slug_dir / "lifecycle.md").write_text("# lifecycle\n\n", encoding="utf-8")
    pending = tmp_path / "data" / "pending" / "narrative-proposals-src-001.json"

    rc = industry_narrative_propose.cmd_propose(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            source_id="src-001",
            industry="cn-power-equipment",
            out=str(pending),
        )
    )
    assert rc == 0

    data = json.loads(pending.read_text(encoding="utf-8"))
    data["proposals"][0]["title"] = "容量扩张中后期"
    data["proposals"][0]["body"] = "下游电网投资周期推动容量扩张进入中后期。"
    data["proposals"][0]["decision"] = "approve"
    data["proposals"][0]["decision_reason"] = "claim 支撑明确"
    pending.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    rc = industry_narrative_apply.cmd_apply(
        Namespace(proposals=str(pending), registry_base=str(tmp_path), base=str(tmp_path))
    )
    assert rc == 0
    assert "下游电网投资周期推动容量扩张进入中后期。" in (slug_dir / "lifecycle.md").read_text(encoding="utf-8")

    claim["status"] = "retired"
    registry._rewrite_claim(claim)
    rc = industry_narrative_flags.cmd_flags(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            industry="cn-power-equipment",
        )
    )
    assert rc == 0
    flags = (slug_dir / "narrative-flags.jsonl").read_text(encoding="utf-8")
    assert "supporting claim retired" in flags
```

- [ ] **Step 2: Run e2e test**

```bash
.venv/bin/python -m pytest tests/test_phase3c_narrative_end_to_end.py -q
```

Expected: PASS.

- [ ] **Step 3: Run all Phase 3A + 3B + 3C tests together**

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
  tests/test_industry_narrative_proposals.py \
  tests/test_industry_narrative_apply_cli.py \
  tests/test_industry_narrative_flags.py \
  tests/test_industries_narrative_flags.py \
  tests/test_phase3c_narrative_end_to_end.py \
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

- [ ] **Step 5: Run guardrail diff**

```bash
git diff -- app/io/claims.py 'companies/*/claims.jsonl' 'industries/*/meta.yaml' 'industries/*/observations.jsonl' 'industries/*/definition.md' 'industries/*/figure_contexts.jsonl' 'industries/*/qa_warnings.jsonl'
```

Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add tests/test_phase3c_narrative_end_to_end.py
git commit -m "test(narrative): cover Phase 3C industry flow"
```

---

## 3. Manual smoke test after implementation

Run this only after all tasks pass.

- [ ] **Step 1: Find an industry claim source**

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
path = Path('data/claims/industries.jsonl')
if not path.exists():
    print('no data/claims/industries.jsonl')
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

Expected: either prints `<industry_slug> source_id claim_id`, or says no industry claim data. If no data exists, skip manual smoke and rely on tests.

- [ ] **Step 2: Generate a real pending proposal**

Replace `<industry_slug>` and `<source_id>` with Step 1 output:

```bash
.venv/bin/python scripts/industry_narrative_propose.py \
  --registry-base data \
  --base . \
  --source-id <source_id> \
  --industry <industry_slug> \
  --out data/pending/narrative-proposals-<source_id>.json
```

Expected: writes a pending JSON file with `scope_type=="industry"`. Inspect it manually; each proposal's `body` should be `null`.

- [ ] **Step 3: Do not apply real pending file unless user approves**

Stop here unless the user explicitly asks to fill and apply a real industry narrative proposal. Applying writes to `industries/<slug>/<dim-kebab>.md`.

---

## 4. Final verification before reporting complete

- [ ] Run all narrative tests (3A + 3B + 3C):

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
  tests/test_industry_narrative_proposals.py \
  tests/test_industry_narrative_apply_cli.py \
  tests/test_industry_narrative_flags.py \
  tests/test_industries_narrative_flags.py \
  tests/test_phase3c_narrative_end_to_end.py \
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
git diff -- app/io/claims.py 'companies/*/claims.jsonl' 'industries/*/meta.yaml' 'industries/*/observations.jsonl' 'industries/*/definition.md' 'industries/*/figure_contexts.jsonl' 'industries/*/qa_warnings.jsonl'
```

Expected: no output.

- [ ] Check no Python LLM imports were added:

```bash
grep -R "anthropic\|openai" app scripts tests | grep -v __pycache__ || true
```

Expected: no Phase 3C files contain `anthropic` or `openai`.

- [ ] Check working tree summary:

```bash
git status --short
```

Expected: only intended Phase 3C files changed, plus any commits created during task execution.

---

## 5. Self-review against spec

Spec coverage:
- Industry scope registration (Task A2) adds one `SCOPE_CONFIGS["industry"]` entry and one mapping constant — no broad refactor, since the scope-aware infrastructure already exists.
- Industry proposal generation (Task B1) emits `scope_type="industry"` / `scope_ref=<slug>` pending files with a dedicated mapping.
- Industry decision validation rejects `dimension="definition"` (covered by Task A2's scope config excluding it, and Task B1's explicit test).
- Industry Markdown appends (Task B1 apply test) land in `industries/<slug>/<dim-kebab>.md` — the existing industry narrative files — without touching `meta.yaml`, `observations.jsonl`, `figure_contexts.jsonl`, `qa_warnings.jsonl`, `definition.md`, or `sources/`.
- Industry flags live at `industries/<slug>/narrative-flags.jsonl` with the same dedup key as arena and company.
- Industry CLI (Task C2) mirrors the arena/company trios with a single `--industry <slug>` flag.
- Industry detail page (Task D2) reads flags and shows `needs review` plus flag details per dimension.
- End-to-end (Task E1) exercises propose → approve → apply → retire claim → scan flags for industry scope.
- Guardrails (Section 0, Part E) forbid LLM imports, V0 claim mutation, non-narrative industry file edits, and any arena or company changes outside tests.

Placeholder scan: every code step includes a concrete code block. No `TODO`, `TBD`, or "add tests for the above" instructions.

Type / name consistency: `CLAIM_DIMENSION_TO_INDUSTRY_NARRATIVE`, `SCOPE_CONFIGS["industry"]`, `build_proposal_file(..., scope_type="industry", scope_ref=<slug>)`, `apply_proposal_file`, `read_narrative_flags("industry", <slug>, base=)`, `scan_narrative_flags(..., scope_type="industry", scope_ref=<slug>)`, `cmd_propose`, `cmd_apply`, `cmd_flags` all use the same signatures introduced in Phase 3B. No invented new functions.

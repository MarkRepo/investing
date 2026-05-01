# Ingest Endgame Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the digest-era ingest flow with the review-bundle → ClaimRegistry → narrative endgame flow, including bundle/source web browsing and removal of old per-company claims/observations.

**Architecture:** Keep `scripts/preprocess_report.py` as the source-text extractor. Extend the existing Phase 1 review-bundle schema/QA, Phase 2 match/apply scripts, and Phase 3 narrative scripts so all ingest workflows write claims to ClaimRegistry and then update 11/6/8 archive narratives from claims. Web reads bundles from a new bundle registry and claims from ClaimRegistry, not per-company `claims.jsonl` or industry `observations.jsonl`.

**Tech Stack:** Python 3, pytest, FastAPI/Jinja templates, JSON/JSONL file stores, existing `app/io/*` modules, Claude Code skill workflow markdown.

---

## Execution Notes for Sonnet

- Use `.venv/bin/python` for all Python commands in this repo.
- Do not call any LLM API from Python. LLM extraction/review remains in Claude conversation/workflow docs.
- Do not implement `investment_lens`; it is explicitly out of scope.
- Do not migrate old `companies/*/claims.jsonl`; this plan deletes them after web reads ClaimRegistry.
- Do not delete existing 11/6/8 archive narrative markdown files.
- Do not assume generic narrative CLIs already support `--scope --ref`; Task 6 adds that interface before workflow docs reference it.
- Prefer project-root ClaimRegistry (`claims/*.jsonl`). The current `ClaimRegistry(base)` stores claims at `base / "claims"`; therefore commands in workflow docs should pass `--registry-base .` unless a test explicitly uses `tmp_path`.

---

## File Structure Map

### Modify

- `docs/prompts/ingest-review-bundle.md` — add `arena_candidates[]` to prompt schema and hard constraints.
- `scripts/ingest_qa.py` — validate `arena_candidates[]` and arena-scoped claims that reference new arena candidates.
- `tests/test_ingest_review_bundle_qa.py` — add review-bundle QA coverage for arena candidates.
- `scripts/ingest_match.py` — add confidence field and split decisions into auto/pending output JSON files.
- `tests/test_ingest_match_cli.py` — update CLI expectations for split outputs.
- `scripts/ingest_apply.py` — accept repeated `--decisions`, keep `--match` as a deprecated alias if simple, and emit `applied.jsonl`.
- `tests/test_ingest_apply.py` — verify multi-file apply and applied summary output.
- `scripts/narrative_propose.py` — replace arena-only CLI with generic `--scope --ref` while preserving `--arena` alias if tests require it.
- `scripts/narrative_flags.py` — replace arena-only CLI with generic `--scope --ref` while preserving `--arena` alias if tests require it.
- `scripts/narrative_apply.py` — ensure it can consume mixed-scope proposal JSONL if it does not already.
- `tests/test_narrative_propose.py` / scope-specific narrative tests — add generic CLI coverage without deleting existing per-scope wrappers unless unused.
- `scripts/ingest_aggregate.py` — remove digest-only helpers, keep autobuild helpers, add company figure-context writer and arena-candidate adapter.
- `tests/test_ingest_aggregate*.py` — delete/update digest-only tests and add new helper tests.
- `.claude/skills/ingest/SKILL.md` — rewrite routing to endgame workflows.
- `.claude/skills/ingest/workflows/industry-research.md` — replace digest steps with endgame steps.
- `.claude/skills/ingest/workflows/annual-report.md` — replace digest steps with endgame steps.
- `.claude/skills/ingest/workflows/quarterly-report.md` — replace digest steps with endgame steps.
- `.claude/skills/ingest/workflows/sell-side-note.md` — replace digest steps and fully support `focus_type` branching.
- `app/io/claim_registry.py` — add `list_claims(scope_type=None, scope_ref=None)` helper if absent.
- `app/routes/companies.py` and company templates — render ClaimRegistry claims, not per-company `claims.jsonl`.
- `app/routes/industries.py` and industry templates — remove observations route/panel/count while preserving 11-dim narrative display.
- `app/routes/arenas.py` and arena templates — add source bundle badges where claims are shown.
- `app/main.py` or equivalent router registration file — include new bundle/source routers.
- `USER-GUIDE.md` — update ingest/web docs.

### Create

- `app/io/bundle_registry.py` — append/list/get helpers for `data/bundle_registry.jsonl` and bundle JSON loading.
- `tests/test_bundle_registry.py` — unit tests for bundle registry helpers.
- `app/routes/bundles.py` — `/bundles` and `/bundles/{source_id}` routes.
- `app/routes/sources.py` — `/sources/{source_id}/file` route.
- `app/templates/bundles/index.html` — bundle list.
- `app/templates/bundles/detail.html` — full expanded bundle detail.
- `app/templates/sources/file.html` — inline source viewer with PDF `<embed>`.
- `.claude/skills/ingest/workflows/_ingest-common.md` — shared 15-step endgame workflow.
- `tests/test_bundle_routes.py` — route tests for bundle pages.
- `tests/test_source_routes.py` — route tests for source viewer.
- `tests/test_web_claims_source_switch.py` — verifies company page reads ClaimRegistry.
- `tests/test_web_observations_panel_removed.py` — verifies observations UI/routes are gone.
- `data/bundle_registry.jsonl` — empty registry file.

### Move / Archive

- Move `.claude/skills/ingest/prompts/digest/*.md` to `docs/superpowers/archive/prompts-digest/`.
- Move old workflow files to `docs/superpowers/archive/workflows-digest-era/` before writing replacements.
- Move old `.claude/skills/ingest/SKILL.md` to `docs/superpowers/archive/SKILL-digest-era.md` before writing replacement.

### Delete

- `companies/*/claims.jsonl` — all old per-company claim files.
- `industries/*/observations.jsonl` — all old structured observation files.
- Digest-only tests that cannot be updated because their target functions are removed.

---

## Task 1: Extend review-bundle QA for `arena_candidates[]`

**Files:**
- Modify: `tests/test_ingest_review_bundle_qa.py`
- Modify: `scripts/ingest_qa.py`
- Modify: `docs/prompts/ingest-review-bundle.md`

- [ ] **Step 1: Add a valid arena candidate to the bundle fixture**

In `tests/test_ingest_review_bundle_qa.py`, update the existing `valid_bundle()` fixture so it includes both a company candidate using MARKET_TICKER format and one arena candidate. Preserve existing required fields.

```python
"company_candidates": [
    {
        "ticker": "SSE_603011",
        "market": "SSE",
        "name": "合锻智能",
        "exposure_type": "thematic_related",
        "confidence": "medium",
        "source_block_ids": ["ib-001"],
        "verification_questions": ["是否有聚变相关订单？"],
    }
],
"arena_candidates": [
    {
        "candidate_id": "ac-001",
        "tentative_slug": "cn-fusion-magnet-supply",
        "name": "中国聚变磁体供应竞争",
        "parent_industry_slug": "cn-nuclear-fusion",
        "battleground_focus": "围绕聚变装置磁体部件供应能力的竞争。",
        "participant_tickers": ["SSE_603011"],
        "linked_block_ids": ["ib-001", "ib-002"],
        "confidence": "high",
        "verification_questions": ["哪些公司已有已交付订单？"],
    }
],
```

If the fixture currently has only `ib-001`, add a minimal `ib-002` insight block and one linked atomic fact, using evidence quotes already present in the fixture text.

- [ ] **Step 2: Add failing tests for the five new QA rules**

Append tests with these exact names:

```python
def test_arena_candidate_requires_parent_industry():
    bundle = valid_bundle()
    bundle["arena_candidates"][0]["parent_industry_slug"] = ""
    errors, warnings = run_review_bundle_check(bundle)
    assert any(e["code"] == "arena_candidate_missing_parent_industry" for e in errors)


def test_arena_candidate_linked_blocks_must_exist():
    bundle = valid_bundle()
    bundle["arena_candidates"][0]["linked_block_ids"] = ["ib-missing"]
    errors, warnings = run_review_bundle_check(bundle)
    assert any(e["code"] == "arena_candidate_unknown_linked_block" for e in errors)


def test_arena_candidate_participants_must_match_company_candidates():
    bundle = valid_bundle()
    bundle["arena_candidates"][0]["participant_tickers"] = ["SSE_999999"]
    errors, warnings = run_review_bundle_check(bundle)
    assert any(e["code"] == "arena_candidate_participant_not_in_company_candidates" for e in errors)


def test_high_confidence_arena_candidate_requires_two_blocks():
    bundle = valid_bundle()
    bundle["arena_candidates"][0]["confidence"] = "high"
    bundle["arena_candidates"][0]["linked_block_ids"] = ["ib-001"]
    errors, warnings = run_review_bundle_check(bundle)
    assert any(w["code"] == "arena_candidate_overconfident" for w in warnings)


def test_arena_claim_ref_must_exist_or_be_candidate():
    bundle = valid_bundle()
    bundle["claim_candidates"].append(
        {
            "candidate_id": "cc-999",
            "claim_text": "不存在的 arena 需要被拒绝或先建候选。",
            "scope_type": "arena",
            "scope_ref": "cn-missing-arena",
            "claim_type": "thesis",
            "dimension_hint": "competition",
            "supporting_block_ids": ["ib-001"],
            "direction_on_source": "supports",
            "confidence": "medium",
            "as_of": bundle["source_digest"]["source_date"],
        }
    )
    errors, warnings = run_review_bundle_check(bundle)
    assert any(e["code"] == "claim_refs_nonexistent_arena" for e in errors)
```

Use the existing helper name in the file instead of `run_review_bundle_check` if the file already exposes a differently named wrapper around `check_ingest_review_bundle`.

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_ingest_review_bundle_qa.py -k "arena_candidate or arena_claim" -v
```

Expected: FAIL because `scripts/ingest_qa.py` does not yet emit the new rule codes.

- [ ] **Step 4: Implement arena-candidate checks in `scripts/ingest_qa.py`**

Inside the review-bundle checker, after existing `company_candidates` checks and after `block_ids` are computed, add logic equivalent to:

```python
arena_candidates = bundle.get("arena_candidates") or []
arena_candidate_slugs = {
    c.get("tentative_slug")
    for c in arena_candidates
    if isinstance(c, dict) and c.get("tentative_slug")
}
company_candidate_keys = set()
for company in bundle.get("company_candidates") or []:
    market = company.get("market")
    ticker = company.get("ticker")
    if market and ticker:
        company_candidate_keys.add(f"{market}_{ticker}")
        company_candidate_keys.add(str(ticker))

for idx, candidate in enumerate(arena_candidates):
    path = f"arena_candidates[{idx}]"
    if not candidate.get("parent_industry_slug"):
        errors.append({"code": "arena_candidate_missing_parent_industry", "path": path})

    linked = candidate.get("linked_block_ids") or []
    for block_id in linked:
        if block_id not in block_ids:
            errors.append({
                "code": "arena_candidate_unknown_linked_block",
                "path": f"{path}.linked_block_ids",
                "block_id": block_id,
            })

    for ticker in candidate.get("participant_tickers") or []:
        if ticker not in company_candidate_keys:
            errors.append({
                "code": "arena_candidate_participant_not_in_company_candidates",
                "path": f"{path}.participant_tickers",
                "ticker": ticker,
            })

    if candidate.get("confidence") == "high" and len(linked) < 2:
        warnings.append({"code": "arena_candidate_overconfident", "path": path})
```

Then extend claim-candidate validation:

```python
for idx, claim in enumerate(bundle.get("claim_candidates") or []):
    if claim.get("scope_type") == "arena":
        scope_ref = claim.get("scope_ref")
        if scope_ref and scope_ref not in existing_arena_slugs and scope_ref not in arena_candidate_slugs:
            errors.append({
                "code": "claim_refs_nonexistent_arena",
                "path": f"claim_candidates[{idx}].scope_ref",
                "scope_ref": scope_ref,
            })
```

If `scripts/ingest_qa.py` does not currently know `existing_arena_slugs`, implement this rule using only `arena_candidate_slugs` for now and name the variable `known_or_candidate_arena_slugs`. Do not read archive files inside the QA checker unless the checker already has a base path parameter.

- [ ] **Step 5: Update the prompt contract**

In `docs/prompts/ingest-review-bundle.md`, add the `arena_candidates` block immediately after `company_candidates` in the JSON skeleton, and add hard constraints matching the spec:

```markdown
- `arena_candidates[*].linked_block_ids` 必须全部指向已有 insight block。
- `arena_candidates[*].participant_tickers` 使用 MARKET_TICKER 格式，且必须能对应 `company_candidates` 中的候选。
- `arena_candidates[*].parent_industry_slug` 必填。
- `tentative_slug` 和 `name` 不要写成单家公司。
- `confidence=high` 至少需要 2 个 linked blocks。
```

- [ ] **Step 6: Run QA tests again**

Run:

```bash
.venv/bin/python -m pytest tests/test_ingest_review_bundle_qa.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add docs/prompts/ingest-review-bundle.md scripts/ingest_qa.py tests/test_ingest_review_bundle_qa.py
git commit -m "feat(ingest): validate arena candidates in review bundles"
```

---

## Task 2: Split ingest match decisions into auto and pending files

**Files:**
- Modify: `tests/test_ingest_match_cli.py`
- Modify: `scripts/ingest_match.py`

- [ ] **Step 1: Write the failing CLI test**

In `tests/test_ingest_match_cli.py`, update or add a test named:

```python
def test_ingest_match_writes_auto_and_pending_decisions(tmp_path):
```

The test should:

1. Write a bundle with two claim candidates: one `confidence="high"`, one `confidence="medium"`.
2. Run the CLI with explicit output paths.
3. Assert high-confidence rows go to auto output and medium/low rows go to pending output.

Use this command shape in the test:

```python
result = subprocess.run(
    [
        sys.executable,
        "scripts/ingest_match.py",
        "--bundle", str(bundle_path),
        "--registry-base", str(tmp_path),
        "--auto-out", str(auto_path),
        "--pending-out", str(pending_path),
    ],
    cwd=repo_root,
    text=True,
    capture_output=True,
)
```

Assert output JSON object shape, not JSONL, to avoid changing apply semantics more than necessary:

```python
auto = json.loads(auto_path.read_text())
pending = json.loads(pending_path.read_text())
assert [r["candidate_id"] for r in auto["decisions_required"]] == ["cc-001"]
assert [r["candidate_id"] for r in pending["decisions_required"]] == ["cc-002"]
assert auto["decisions_required"][0]["confidence"] == "high"
assert pending["decisions_required"][0]["confidence"] == "medium"
```

- [ ] **Step 2: Run the failing test**

```bash
.venv/bin/python -m pytest tests/test_ingest_match_cli.py::test_ingest_match_writes_auto_and_pending_decisions -v
```

Expected: FAIL because `--auto-out` and `--pending-out` do not exist yet.

- [ ] **Step 3: Update decision-row construction**

In `scripts/ingest_match.py`, when building each decision row, copy confidence from the candidate payload:

```python
"confidence": candidate_payload.get("confidence", "medium"),
```

Keep existing fields:

```python
"candidate_id": candidate_payload["candidate_id"],
"candidate_payload": candidate_payload,
"top_matches": matches,
"decision": None,
"decision_reason": None,
"direction_on_claim": None,
"target_claim_id": None,
"split_instructions": None,
```

- [ ] **Step 4: Add split output support while keeping old `--out` optional**

Change CLI args:

```python
parser.add_argument("--out", help="legacy single match output path")
parser.add_argument("--auto-out", help="write high-confidence decisions here")
parser.add_argument("--pending-out", help="write medium/low-confidence decisions here")
```

After building the match object:

```python
def _with_rows(match: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    copied = dict(match)
    copied["decisions_required"] = rows
    return copied

rows = match["decisions_required"]
auto_rows = [r for r in rows if r.get("confidence") == "high"]
pending_rows = [r for r in rows if r.get("confidence") != "high"]

if args.out:
    write_json(Path(args.out), match)
if args.auto_out:
    write_json(Path(args.auto_out), _with_rows(match, auto_rows))
if args.pending_out:
    write_json(Path(args.pending_out), _with_rows(match, pending_rows))
if not args.out and not args.auto_out and not args.pending_out:
    parser.error("one of --out, --auto-out, or --pending-out is required")
```

Use the file's existing JSON write helper if present.

- [ ] **Step 5: Run match tests**

```bash
.venv/bin/python -m pytest tests/test_ingest_match_cli.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/ingest_match.py tests/test_ingest_match_cli.py
git commit -m "feat(ingest): split match decisions by confidence"
```

---

## Task 3: Let ingest apply consume multiple decision files and emit `applied.jsonl`

**Files:**
- Modify: `tests/test_ingest_apply.py`
- Modify: `scripts/ingest_apply.py`

- [ ] **Step 1: Add failing test for multiple decision files**

In `tests/test_ingest_apply.py`, add:

```python
def test_apply_accepts_multiple_decision_files_and_writes_applied_jsonl(tmp_path):
```

Build two match JSON files with the same shape as `ingest_match.py` output. One file should have an `attach` or `new` decision, the other should have a `new` decision. Run:

```python
result = subprocess.run(
    [
        sys.executable,
        "scripts/ingest_apply.py",
        "--bundle", str(bundle_path),
        "--registry-base", str(tmp_path),
        "--decisions", str(auto_path),
        "--decisions", str(pending_path),
        "--applied-out", str(applied_path),
    ],
    cwd=repo_root,
    text=True,
    capture_output=True,
)
```

Assert:

```python
assert result.returncode == 0, result.stderr
rows = [json.loads(line) for line in applied_path.read_text().splitlines() if line.strip()]
assert {row["candidate_id"] for row in rows} == {"cc-001", "cc-002"}
assert all(row["claim_id"] for row in rows)
assert all(row["scope_type"] in {"industry", "arena", "company", "cross_cutting"} for row in rows)
```

- [ ] **Step 2: Run the failing test**

```bash
.venv/bin/python -m pytest tests/test_ingest_apply.py::test_apply_accepts_multiple_decision_files_and_writes_applied_jsonl -v
```

Expected: FAIL because repeated `--decisions` and `--applied-out` are not implemented.

- [ ] **Step 3: Add CLI args**

In `scripts/ingest_apply.py`:

```python
parser.add_argument("--match", action="append", default=[], help="deprecated alias for --decisions")
parser.add_argument("--decisions", action="append", default=[], help="decision file from ingest_match; may be repeated")
parser.add_argument("--applied-out", help="write applied claim summary JSONL")
```

Then normalize:

```python
decision_paths = [Path(p) for p in args.match + args.decisions]
if not decision_paths:
    parser.error("at least one --decisions file is required")
```

- [ ] **Step 4: Apply all decisions in order**

Refactor the current single-match logic into:

```python
applied_rows: list[dict[str, Any]] = []
for decision_path in decision_paths:
    match = json.loads(decision_path.read_text())
    errors = validate_match_decisions(match, registry)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    for row in match.get("decisions_required", []):
        result = apply_decision(row, bundle, registry)
        if result and result.get("claim_id"):
            applied_rows.append({
                "source_id": bundle["source_digest"]["source_id"],
                "candidate_id": row["candidate_id"],
                "claim_id": result["claim_id"],
                "scope_type": result["scope_type"],
                "scope_ref": result["scope_ref"],
                "action": row["decision"],
            })
```

If the existing code does not have `apply_decision`, extract the current per-row branch into a helper returning a dict with `claim_id`, `scope_type`, and `scope_ref` for `attach`, `new`, and `split`; return `None` for `skip`.

- [ ] **Step 5: Write applied JSONL**

```python
if args.applied_out:
    out = Path(args.applied_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for row in applied_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
```

- [ ] **Step 6: Run apply tests**

```bash
.venv/bin/python -m pytest tests/test_ingest_apply.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/ingest_apply.py tests/test_ingest_apply.py
git commit -m "feat(ingest): apply multiple decision files"
```

---

## Task 4: Add bundle registry IO

**Files:**
- Create: `app/io/bundle_registry.py`
- Create: `tests/test_bundle_registry.py`

- [ ] **Step 1: Write failing registry tests**

Create `tests/test_bundle_registry.py`:

```python
import json
from pathlib import Path

from app.io import bundle_registry


def _entry(source_id="source-1", source_type="industry_report"):
    return {
        "source_id": source_id,
        "sha8": "abcdef12",
        "source_type": source_type,
        "institution": "中银证券",
        "publish_date": "2025-04-10",
        "bundle_path": "industries/cn-nuclear-fusion/bundles/abcdef12.json",
        "source_file_path": "industries/cn-nuclear-fusion/sources/report.pdf",
        "ingested_at": "2026-04-30T08:15:00Z",
        "touched": {"industries": ["cn-nuclear-fusion"], "arenas": [], "companies": []},
    }


def test_append_and_get_bundle_registry_entry(tmp_path):
    entry = _entry()
    bundle_registry.append_registry(entry, base=tmp_path)

    assert bundle_registry.get_bundle("source-1", base=tmp_path) == entry


def test_list_bundles_filters_by_type_and_institution(tmp_path):
    bundle_registry.append_registry(_entry("source-1", "industry_report"), base=tmp_path)
    bundle_registry.append_registry(_entry("source-2", "annual_report"), base=tmp_path)

    rows = bundle_registry.list_bundles({"type": "industry_report", "institution": "中银证券"}, base=tmp_path)

    assert [r["source_id"] for r in rows] == ["source-1"]


def test_load_bundle_json_uses_registry_relative_path(tmp_path):
    entry = _entry()
    bundle_path = tmp_path / entry["bundle_path"]
    bundle_path.parent.mkdir(parents=True)
    bundle_path.write_text(json.dumps({"bundle_version": "v2-phase1"}), encoding="utf-8")
    bundle_registry.append_registry(entry, base=tmp_path)

    assert bundle_registry.load_bundle_json("source-1", base=tmp_path)["bundle_version"] == "v2-phase1"
```

- [ ] **Step 2: Run failing tests**

```bash
.venv/bin/python -m pytest tests/test_bundle_registry.py -v
```

Expected: FAIL because `app/io/bundle_registry.py` does not exist.

- [ ] **Step 3: Implement registry IO**

Create `app/io/bundle_registry.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app import config as cfg


def _base(base: Path | None = None) -> Path:
    return Path(base) if base is not None else cfg.BASE_DIR


def _registry_path(base: Path | None = None) -> Path:
    return _base(base) / "data" / "bundle_registry.jsonl"


def append_registry(entry: dict[str, Any], *, base: Path | None = None) -> None:
    path = _registry_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def list_bundles(filters: dict[str, str] | None = None, *, base: Path | None = None) -> list[dict[str, Any]]:
    path = _registry_path(base)
    if not path.exists():
        return []
    filters = filters or {}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if filters.get("type"):
        rows = [r for r in rows if r.get("source_type") == filters["type"]]
    if filters.get("institution"):
        rows = [r for r in rows if r.get("institution") == filters["institution"]]
    if filters.get("industry"):
        rows = [r for r in rows if filters["industry"] in (r.get("touched", {}).get("industries") or [])]
    return sorted(rows, key=lambda r: r.get("ingested_at", ""), reverse=True)


def get_bundle(source_id: str, *, base: Path | None = None) -> dict[str, Any] | None:
    for row in list_bundles(base=base):
        if row.get("source_id") == source_id:
            return row
    return None


def load_bundle_json(source_id: str, *, base: Path | None = None) -> dict[str, Any]:
    entry = get_bundle(source_id, base=base)
    if entry is None:
        raise FileNotFoundError(source_id)
    path = _base(base) / entry["bundle_path"]
    return json.loads(path.read_text(encoding="utf-8"))
```

If `app/config.py` uses a different project-root constant than `BASE_DIR`, use the existing constant.

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_bundle_registry.py -v
```

Expected: PASS.

- [ ] **Step 5: Create empty registry file**

Create `data/bundle_registry.jsonl` as an empty file.

- [ ] **Step 6: Commit**

```bash
git add app/io/bundle_registry.py tests/test_bundle_registry.py data/bundle_registry.jsonl
git commit -m "feat(web): add bundle registry store"
```

---

## Task 5: Add ingest aggregate endgame helpers and remove digest helpers

**Files:**
- Modify: `scripts/ingest_aggregate.py`
- Modify/Delete: `tests/test_ingest_aggregate.py`
- Modify/Delete: `tests/test_ingest_aggregate_triple.py`
- Modify/Delete: `tests/test_ingest_aggregate_autobuild.py`
- Create: `tests/test_ingest_aggregate_new.py`

- [ ] **Step 1: Write tests for the two retained/new helpers**

Create `tests/test_ingest_aggregate_new.py`:

```python
import json

from scripts import ingest_aggregate as agg


def test_write_figure_contexts_for_company(tmp_path):
    contexts = [
        {
            "page": 3,
            "kind": "figure",
            "caption": "图1：收入结构",
            "nearby_text": "公司披露收入结构。",
        }
    ]
    source_meta = {"source_id": "annual-1", "source_title": "2025 年报"}

    written = agg.write_figure_contexts_for_company(
        "SSE_603011",
        contexts,
        source_meta,
        base=tmp_path,
    )

    path = tmp_path / "companies" / "SSE_603011" / "figure_contexts.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert written == 1
    assert rows[0]["source_id"] == "annual-1"
    assert rows[0]["page"] == 3
    assert rows[0]["caption"] == "图1：收入结构"


def test_bootstrap_arena_from_candidate(tmp_path):
    candidate = {
        "tentative_slug": "cn-fusion-magnet-supply",
        "name": "中国聚变磁体供应竞争",
        "parent_industry_slug": "cn-nuclear-fusion",
        "battleground_focus": "围绕聚变装置磁体部件供应能力的竞争。",
    }

    agg.bootstrap_arena_from_candidate(candidate, base=tmp_path)

    definition = tmp_path / "arenas" / "cn-fusion-magnet-supply" / "definition.md"
    assert definition.exists()
    assert "中国聚变磁体供应竞争" in definition.read_text(encoding="utf-8")
```

- [ ] **Step 2: Remove or rewrite digest-only tests**

Delete tests that assert these removed functions exist:

- `route_key_facts`
- `derive_arena_facts`
- `group_company_facts`
- `facts_to_claims`
- `propose_arena_bootstrap`
- `write_industry_observations`
- `write_claims`
- `write_industry_narrative`
- `write_arena_narrative`
- `write_company_narrative`
- `load_json_tolerant`

If a test file contains only those tests, delete the whole file. If it also tests `ensure_industry_exists`, `ensure_company_exists`, `bootstrap_arena`, or `write_figure_contexts`, keep those tests and remove only digest-only cases.

- [ ] **Step 3: Run failing helper tests**

```bash
.venv/bin/python -m pytest tests/test_ingest_aggregate_new.py -v
```

Expected: FAIL because the new helper names do not exist.

- [ ] **Step 4: Implement `write_figure_contexts_for_company`**

In `scripts/ingest_aggregate.py`, add:

```python
def write_figure_contexts_for_company(
    market_ticker: str,
    contexts: list[dict],
    source_meta: dict,
    *,
    base: Path | None = None,
) -> int:
    companies_dir = (Path(base) / "companies") if base else Path("companies")
    out = companies_dir / market_ticker / "figure_contexts.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out.open("a", encoding="utf-8") as f:
        for context in contexts:
            row = dict(context)
            row.update({
                "source_id": source_meta.get("source_id"),
                "source_title": source_meta.get("source_title"),
                "source_date": source_meta.get("source_date"),
            })
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count
```

If the file already has a path helper for `write_figure_contexts`, reuse it instead of hardcoding `Path("companies")`.

- [ ] **Step 5: Implement `bootstrap_arena_from_candidate`**

Add:

```python
def bootstrap_arena_from_candidate(candidate: dict, *, base: Path | None = None) -> None:
    proposal = {
        "slug": candidate["tentative_slug"],
        "name": candidate["name"],
        "industry": candidate["parent_industry_slug"],
        "battleground_focus": candidate["battleground_focus"],
    }
    bootstrap_arena(proposal, base=base)
```

- [ ] **Step 6: Remove digest-only functions**

Delete these functions from `scripts/ingest_aggregate.py`:

```text
route_key_facts
derive_arena_facts
group_company_facts
facts_to_claims
propose_arena_bootstrap
load_json_tolerant
write_industry_observations
write_claims
write_industry_narrative
write_arena_narrative
write_company_narrative
```

After deletion, search within the file for digest-era field names and remove unreachable imports:

```text
key_facts
proposed_arenas
narratives
observations
```

Do not delete `ensure_industry_exists`, `ensure_company_exists`, `bootstrap_arena`, or `write_figure_contexts`.

- [ ] **Step 7: Run aggregate tests**

```bash
.venv/bin/python -m pytest tests/test_ingest_aggregate*.py -v
```

Expected: PASS for remaining aggregate tests.

- [ ] **Step 8: Commit**

```bash
git add scripts/ingest_aggregate.py tests/test_ingest_aggregate*.py
git commit -m "refactor(ingest): remove digest aggregate helpers"
```

---

## Task 6: Make narrative CLI wrappers scope-aware

**Files:**
- Modify: `scripts/narrative_propose.py`
- Modify: `scripts/narrative_flags.py`
- Modify: `scripts/narrative_apply.py` only if mixed-scope apply currently fails
- Modify/Create: narrative CLI tests matching existing test file names

- [ ] **Step 1: Add failing generic propose CLI test**

In the existing narrative propose CLI test file, add:

```python
def test_narrative_propose_accepts_scope_and_ref(tmp_path):
```

Run the CLI with:

```python
[
    sys.executable,
    "scripts/narrative_propose.py",
    "--source-id", "source-1",
    "--scope", "industry",
    "--ref", "cn-nuclear-fusion",
    "--registry-base", str(tmp_path),
    "--out", str(out_path),
]
```

Seed `ClaimRegistry(tmp_path)` with one industry claim before running, using the existing registry helper test pattern.

Assert the command exits 0 and creates `out_path`.

- [ ] **Step 2: Add failing generic flags CLI test**

In the existing narrative flags CLI test file, add:

```python
def test_narrative_flags_accepts_scope_and_ref(tmp_path):
```

Run:

```python
[
    sys.executable,
    "scripts/narrative_flags.py",
    "--source-id", "source-1",
    "--scope", "industry",
    "--ref", "cn-nuclear-fusion",
    "--registry-base", str(tmp_path),
]
```

Assert exit 0. If the flags CLI requires an output path, use the existing required argument pattern from the file.

- [ ] **Step 3: Run failing tests**

```bash
.venv/bin/python -m pytest tests/test_narrative* -k "scope_and_ref" -v
```

Expected: FAIL because generic wrappers are currently arena-only.

- [ ] **Step 4: Update `scripts/narrative_propose.py` parser**

Add args:

```python
parser.add_argument("--scope", choices=["industry", "arena", "company"])
parser.add_argument("--ref")
parser.add_argument("--arena", help="deprecated alias for --scope arena --ref <slug>")
parser.add_argument("--registry-base", default=".")
```

Normalize:

```python
scope = args.scope
ref = args.ref
if args.arena:
    scope = "arena"
    ref = args.arena
if not scope or not ref:
    parser.error("--scope and --ref are required")
```

Then call the existing proposal builder with `scope_type=scope` and `scope_ref=ref`.

- [ ] **Step 5: Update `scripts/narrative_flags.py` parser**

Apply the same `--scope --ref` normalization. Keep `--arena` as a deprecated alias if current tests use it.

- [ ] **Step 6: Verify mixed-scope apply**

Check whether `scripts/narrative_apply.py` already reads `scope_type` and `scope_ref` from each proposal row. If it assumes arena-only, write a failing test with one industry proposal and one company proposal in the same JSONL file, then update apply routing to dispatch by row scope:

```python
if row["scope_type"] == "industry":
    # industries/{slug}/{dimension}.md
elif row["scope_type"] == "arena":
    # arenas/{slug}/{dimension}.md
elif row["scope_type"] == "company":
    # companies/{key}/narratives/{dimension}.md
else:
    raise ValueError(f"unsupported scope_type: {row['scope_type']}")
```

- [ ] **Step 7: Run narrative tests**

```bash
.venv/bin/python -m pytest tests/test_narrative* -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add scripts/narrative_propose.py scripts/narrative_flags.py scripts/narrative_apply.py tests/test_narrative*.py
git commit -m "feat(narrative): support generic scope CLI"
```

---

## Task 7: Add ClaimRegistry list helper and switch company claims panel

**Files:**
- Modify: `app/io/claim_registry.py`
- Modify: `app/routes/companies.py`
- Modify: relevant `app/templates/companies/*.html`
- Create: `tests/test_web_claims_source_switch.py`

- [ ] **Step 1: Write failing ClaimRegistry helper test**

Add to the existing claim registry tests:

```python
def test_list_claims_filters_by_scope(tmp_path):
    registry = ClaimRegistry(tmp_path)
    company_claim = registry.create_claim(
        scope_type="company",
        scope_ref="SSE_603011",
        claim_text="公司具备主题相关性。",
        claim_type="thesis",
        dimension="business_model",
        confidence="medium",
        as_of="2025-04-10",
        source_id="source-1",
        evidence_refs=[],
    )
    registry.create_claim(
        scope_type="industry",
        scope_ref="cn-nuclear-fusion",
        claim_text="行业仍处早期。",
        claim_type="thesis",
        dimension="lifecycle",
        confidence="medium",
        as_of="2025-04-10",
        source_id="source-1",
        evidence_refs=[],
    )

    rows = registry.list_claims(scope_type="company", scope_ref="SSE_603011")

    assert [r["claim_id"] for r in rows] == [company_claim["claim_id"]]
```

Adjust `create_claim` arguments to the actual signature in `app/io/claim_registry.py`.

- [ ] **Step 2: Implement `list_claims`**

In `ClaimRegistry`:

```python
def list_claims(self, scope_type: str | None = None, scope_ref: str | None = None) -> list[dict[str, Any]]:
    if scope_type and scope_ref:
        return self.claims_for_scope(scope_type, scope_ref)
    if scope_type:
        return self.all_claims_for_scope_type(scope_type)
    rows: list[dict[str, Any]] = []
    for path in sorted(self.claims_dir.glob("*.jsonl")):
        rows.extend(self._read_claims_file(path))
    return rows
```

Use the file's existing private read helper name instead of `_read_claims_file` if different.

- [ ] **Step 3: Write failing web test for company page claims**

Create `tests/test_web_claims_source_switch.py`:

```python
def test_company_page_reads_claim_registry_claims(client, tmp_path, monkeypatch):
    # Use the app's existing test pattern for setting base/data dirs.
    # Create companies/SSE_603011/meta.json through app.io.company helper.
    # Seed ClaimRegistry(tmp_path) with a company claim.
    response = client.get("/companies/SSE_603011")
    assert response.status_code == 200
    html = response.text
    assert "公司具备主题相关性" in html
    assert "source-1" in html
```

Follow existing route-test fixtures for `client`, `tmp_path`, and config monkeypatching. Do not invent a second app factory if tests already provide one.

- [ ] **Step 4: Run failing tests**

```bash
.venv/bin/python -m pytest tests/test_web_claims_source_switch.py -v
```

Expected: FAIL because company route does not read ClaimRegistry yet.

- [ ] **Step 5: Update company route**

In `app/routes/companies.py`, load claims with:

```python
from app.io.claim_registry import ClaimRegistry

registry = ClaimRegistry(base or Path("."))
claims = registry.list_claims(scope_type="company", scope_ref=key)
```

Use the route file's existing base/config pattern; do not hardcode `Path(".")` if the app already has `request.app.state.base` or config helpers.

Pass `claims` to the template.

- [ ] **Step 6: Update company template**

Render claims with columns:

```html
<th>Claim</th>
<th>Type</th>
<th>Dimension</th>
<th>Confidence</th>
<th>Sources</th>
```

For sources, render each `supporting_source_ids` or evidence source id as a link if available:

```html
<a href="/bundles/{{ source_id }}">{{ source_id }}</a>
```

If the claim schema uses `evidence` rows rather than `supporting_source_ids`, derive source ids in the route before rendering.

- [ ] **Step 7: Run route tests**

```bash
.venv/bin/python -m pytest tests/test_web_claims_source_switch.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add app/io/claim_registry.py app/routes/companies.py app/templates/companies tests/test_web_claims_source_switch.py
git commit -m "feat(web): read company claims from ClaimRegistry"
```

---

## Task 8: Remove industry observations UI and routes

**Files:**
- Modify: `app/routes/industries.py`
- Modify: `app/templates/industries/detail.html`
- Modify: `app/templates/industries/index.html`
- Delete or stop using: `app/templates/industries/observations.html`
- Create: `tests/test_web_observations_panel_removed.py`

- [ ] **Step 1: Write failing observations-removal tests**

Create `tests/test_web_observations_panel_removed.py`:

```python
def test_industry_detail_no_longer_renders_observations_panel(client, tmp_path, monkeypatch):
    # Use existing industry route fixture pattern to create cn-nuclear-fusion meta/narratives.
    response = client.get("/industries/cn-nuclear-fusion")
    assert response.status_code == 200
    assert "observations" not in response.text.lower()
    assert "观察" not in response.text


def test_industry_observations_route_is_gone(client, tmp_path, monkeypatch):
    response = client.get("/industries/cn-nuclear-fusion/observations")
    assert response.status_code == 404
```

If the Chinese word `观察` appears in unrelated copy that should remain, assert absence of the specific DOM heading currently used in `app/templates/industries/detail.html` instead.

- [ ] **Step 2: Run failing tests**

```bash
.venv/bin/python -m pytest tests/test_web_observations_panel_removed.py -v
```

Expected: FAIL because the route/panel exists.

- [ ] **Step 3: Remove observations route and route data**

In `app/routes/industries.py`:

- Remove `observations_count` calculation on index rows.
- Remove `observations = industry_io.read_observations(slug)` from detail route.
- Remove `observations` and `observations_total` from template context.
- Delete the `@router.get("/{slug}/observations")` route.

Do not remove narrative, linked arenas, linked tickers, figure contexts, or flags data.

- [ ] **Step 4: Remove template panel and index column**

In `app/templates/industries/detail.html`, remove only the observations table/card and link to `/observations`.

In `app/templates/industries/index.html`, remove observations-count column and update copy from:

```text
11 维 narrative + observations.jsonl + figure_contexts
```

to:

```text
11 维 narrative + ClaimRegistry claims + figure_contexts
```

- [ ] **Step 5: Run tests**

```bash
.venv/bin/python -m pytest tests/test_web_observations_panel_removed.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/routes/industries.py app/templates/industries tests/test_web_observations_panel_removed.py
git commit -m "refactor(web): remove industry observations panel"
```

---

## Task 9: Add bundle and source web routes

**Files:**
- Create: `app/routes/bundles.py`
- Create: `app/routes/sources.py`
- Create: `app/templates/bundles/index.html`
- Create: `app/templates/bundles/detail.html`
- Create: `app/templates/sources/file.html`
- Modify: router registration file (`app/main.py` or existing equivalent)
- Create: `tests/test_bundle_routes.py`
- Create: `tests/test_source_routes.py`

- [ ] **Step 1: Write bundle route tests**

Create `tests/test_bundle_routes.py` using existing client/config fixtures:

```python
def test_bundles_index_lists_registry_entries(client, tmp_path, monkeypatch):
    # Arrange: write data/bundle_registry.jsonl with one entry.
    response = client.get("/bundles")
    assert response.status_code == 200
    assert "source-1" in response.text
    assert "industry_report" in response.text


def test_bundle_detail_renders_all_major_sections(client, tmp_path, monkeypatch):
    # Arrange: registry entry points to a bundle JSON containing source_digest,
    # insight_blocks, atomic_facts, synthesis, stage_gates, claim_candidates,
    # company_candidates, arena_candidates, schema_fit_review.
    response = client.get("/bundles/source-1")
    assert response.status_code == 200
    html = response.text
    assert "insight_blocks" in html
    assert "atomic_facts" in html
    assert "synthesis" in html
    assert "claim_candidates" in html
    assert "/sources/source-1/file" in html


def test_bundle_detail_404_for_unknown_source(client):
    response = client.get("/bundles/missing")
    assert response.status_code == 404
```

Use JSON fixture data that follows the current prompt schema plus `arena_candidates` from Task 1.

- [ ] **Step 2: Write source route tests**

Create `tests/test_source_routes.py`:

```python
def test_source_file_embeds_pdf(client, tmp_path, monkeypatch):
    # Arrange: registry source_file_path points to a small fake report.pdf file.
    response = client.get("/sources/source-1/file")
    assert response.status_code == 200
    assert "<embed" in response.text
    assert "/bundles/source-1" in response.text


def test_source_file_404_for_unknown_source(client):
    response = client.get("/sources/missing/file")
    assert response.status_code == 404
```

- [ ] **Step 3: Run failing route tests**

```bash
.venv/bin/python -m pytest tests/test_bundle_routes.py tests/test_source_routes.py -v
```

Expected: FAIL because routes do not exist.

- [ ] **Step 4: Implement `app/routes/bundles.py`**

```python
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.io import bundle_registry

router = APIRouter(prefix="/bundles", tags=["bundles"])


@router.get("", response_class=HTMLResponse)
def index(request: Request, type: str | None = None, institution: str | None = None, industry: str | None = None):
    filters = {k: v for k, v in {"type": type, "institution": institution, "industry": industry}.items() if v}
    bundles = bundle_registry.list_bundles(filters)
    return request.app.state.templates.TemplateResponse(
        "bundles/index.html",
        {"request": request, "bundles": bundles, "filters": filters},
    )


@router.get("/{source_id}", response_class=HTMLResponse)
def detail(source_id: str, request: Request):
    entry = bundle_registry.get_bundle(source_id)
    if entry is None:
        raise HTTPException(status_code=404)
    bundle = bundle_registry.load_bundle_json(source_id)
    return request.app.state.templates.TemplateResponse(
        "bundles/detail.html",
        {"request": request, "entry": entry, "bundle": bundle},
    )
```

If the app uses an imported `templates` object instead of `request.app.state.templates`, follow the existing route pattern.

- [ ] **Step 5: Implement `app/routes/sources.py`**

```python
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app import config as cfg
from app.io import bundle_registry

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/{source_id}/file", response_class=HTMLResponse)
def file_view(source_id: str, request: Request):
    entry = bundle_registry.get_bundle(source_id)
    if entry is None:
        raise HTTPException(status_code=404)
    source_path = Path(cfg.BASE_DIR) / entry["source_file_path"]
    if not source_path.exists():
        raise HTTPException(status_code=404)
    return request.app.state.templates.TemplateResponse(
        "sources/file.html",
        {"request": request, "entry": entry, "source_path": source_path, "is_pdf": source_path.suffix.lower() == ".pdf"},
    )
```

If static serving requires a dedicated download route, add it only if existing app patterns require it. Otherwise the template can point `<embed src="/{{ entry.source_file_path }}">` only if those files are already served statically; tests only assert the embed tag exists.

- [ ] **Step 6: Create templates**

`app/templates/bundles/index.html` should extend `base.html` and render a table with `source_id`, `source_type`, `institution`, `publish_date`, `ingested_at`, and links to detail/source.

`app/templates/bundles/detail.html` should render all major bundle fields expanded. A safe Sonnet-friendly template structure:

```html
<h1>{{ bundle.source_digest.source_id }}</h1>
<a href="/sources/{{ entry.source_id }}/file">查看源文件</a>

<h2>source_digest</h2>
<pre>{{ bundle.source_digest | tojson(indent=2) }}</pre>

<h2>insight_blocks</h2>
<pre>{{ bundle.insight_blocks | tojson(indent=2) }}</pre>

<h2>atomic_facts</h2>
<pre>{{ bundle.atomic_facts | tojson(indent=2) }}</pre>

<h2>synthesis</h2>
<pre>{{ bundle.synthesis | tojson(indent=2) }}</pre>

<h2>stage_gates</h2>
<pre>{{ bundle.stage_gates | tojson(indent=2) }}</pre>

<h2>claim_candidates</h2>
<pre>{{ bundle.claim_candidates | tojson(indent=2) }}</pre>

<h2>company_candidates</h2>
<pre>{{ bundle.company_candidates | tojson(indent=2) }}</pre>

<h2>arena_candidates</h2>
<pre>{{ bundle.arena_candidates | tojson(indent=2) }}</pre>

<h2>schema_fit_review</h2>
<pre>{{ bundle.schema_fit_review | tojson(indent=2) }}</pre>
```

`app/templates/sources/file.html` should include:

```html
<a href="/bundles/{{ entry.source_id }}">查看 review bundle</a>
{% if is_pdf %}
  <embed src="/{{ entry.source_file_path }}" type="application/pdf" width="100%" height="900px">
{% else %}
  <p>{{ entry.source_file_path }}</p>
{% endif %}
```

- [ ] **Step 7: Register routers**

In the app router registration file, add:

```python
from app.routes import bundles, sources

app.include_router(bundles.router)
app.include_router(sources.router)
```

Follow the existing import style.

- [ ] **Step 8: Run route tests**

```bash
.venv/bin/python -m pytest tests/test_bundle_routes.py tests/test_source_routes.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add app/routes/bundles.py app/routes/sources.py app/templates/bundles app/templates/sources tests/test_bundle_routes.py tests/test_source_routes.py app/main.py
git commit -m "feat(web): add bundle and source browsers"
```

If router registration is not in `app/main.py`, stage the actual modified registration file instead.

---

## Task 10: Add bundle source badges to claim displays

**Files:**
- Modify: `app/routes/companies.py`
- Modify: `app/routes/industries.py`
- Modify: `app/routes/arenas.py`
- Modify: relevant templates under `app/templates/companies/`, `app/templates/industries/`, `app/templates/arenas/`
- Add route tests to existing web test files

- [ ] **Step 1: Add failing test for source badge links**

In `tests/test_web_claims_source_switch.py`, extend the company claim test:

```python
assert "/bundles/source-1" in html
```

Add equivalent tests for industry/arena pages if those pages already render claims.

- [ ] **Step 2: Add a route helper to derive source ids**

In each route that renders claims, normalize claims before templating:

```python
def _claim_source_ids(claim: dict) -> list[str]:
    ids = set(claim.get("supporting_source_ids") or [])
    for evidence in claim.get("evidence", []) or []:
        if evidence.get("source_id"):
            ids.add(evidence["source_id"])
    if claim.get("source_id"):
        ids.add(claim["source_id"])
    return sorted(ids)

for claim in claims:
    claim["source_ids"] = _claim_source_ids(claim)
```

Put this helper in the smallest existing web utility module if one exists; otherwise keep it private in each route file for now.

- [ ] **Step 3: Render badge links**

In claim tables/cards:

```html
{% for source_id in claim.source_ids %}
  <a class="badge" href="/bundles/{{ source_id }}">{{ source_id }}</a>
{% endfor %}
```

Do not add a global `/claims` route.

- [ ] **Step 4: Run web tests**

```bash
.venv/bin/python -m pytest tests/test_web_claims_source_switch.py tests/test_bundle_routes.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routes app/templates tests/test_web_claims_source_switch.py
git commit -m "feat(web): link claims back to review bundles"
```

---

## Task 11: Rewrite ingest workflow docs to endgame path

**Files:**
- Move: `.claude/skills/ingest/workflows/*.md` to `docs/superpowers/archive/workflows-digest-era/`
- Move: `.claude/skills/ingest/prompts/digest/*.md` to `docs/superpowers/archive/prompts-digest/`
- Move: `.claude/skills/ingest/SKILL.md` to `docs/superpowers/archive/SKILL-digest-era.md`
- Create: `.claude/skills/ingest/workflows/_ingest-common.md`
- Create: `.claude/skills/ingest/workflows/industry-research.md`
- Create: `.claude/skills/ingest/workflows/annual-report.md`
- Create: `.claude/skills/ingest/workflows/quarterly-report.md`
- Create: `.claude/skills/ingest/workflows/sell-side-note.md`
- Create: `.claude/skills/ingest/SKILL.md`
- Modify/Create: workflow contract tests if they exist

- [ ] **Step 1: Archive old digest files**

Run file moves, not copies:

```bash
mkdir -p docs/superpowers/archive/prompts-digest docs/superpowers/archive/workflows-digest-era
git mv .claude/skills/ingest/prompts/digest/*.md docs/superpowers/archive/prompts-digest/
git mv .claude/skills/ingest/workflows/*.md docs/superpowers/archive/workflows-digest-era/
git mv .claude/skills/ingest/SKILL.md docs/superpowers/archive/SKILL-digest-era.md
```

If `_ingest-common.md` already exists because of a partial run, move only the four old workflow files.

- [ ] **Step 2: Create `_ingest-common.md`**

Write a common workflow with this exact skeleton and current CLI names:

```markdown
# Endgame Ingest Common Workflow

All ingest workflows use this path. Do not use digest prompts, `key_facts`, `route_key_facts`, `proposed_arenas`, per-company `claims.jsonl`, or `observations.jsonl`.

1. Run preprocess with `.venv/bin/python scripts/preprocess_report.py ...` and save `preprocess.json` next to the source working files.
2. Generate `bundle.json` in Claude conversation using `docs/prompts/ingest-review-bundle.md`; Python must not call an LLM API.
3. Run `.venv/bin/python scripts/ingest_qa.py review-bundle --bundle bundle.json --preprocess preprocess.json`.
4. Review `bundle.arena_candidates` with the user; approved candidates call `scripts.ingest_aggregate.bootstrap_arena_from_candidate`.
5. Ensure referenced industries exist with `ensure_industry_exists`.
6. Ensure `bundle.company_candidates` exist with `ensure_company_exists`; do not ask the user to create company meta manually.
7. Run `.venv/bin/python scripts/ingest_match.py --bundle bundle.json --registry-base . --auto-out auto_apply.json --pending-out pending_review.json`.
8. Review `pending_review.json` with the user; update decisions in that file. High-confidence `auto_apply.json` may be applied without user review.
9. Run `.venv/bin/python scripts/ingest_apply.py --bundle bundle.json --registry-base . --decisions auto_apply.json --decisions pending_review.json --applied-out applied.jsonl`.
10. Read `applied.jsonl`, group touched `(scope_type, scope_ref)`, and run `.venv/bin/python scripts/narrative_propose.py --source-id SOURCE_ID --scope SCOPE --ref REF --registry-base . --out proposals-SCOPE-REF.jsonl` for each touched ref.
11. Present all proposals to the user with `AskUserQuestion` multiSelect approve/skip only; do not edit proposals.
12. Merge approved proposal rows into `approved_proposals.jsonl` and run `.venv/bin/python scripts/narrative_apply.py --proposals approved_proposals.jsonl`.
13. Write `figure_contexts` to the source layer: industry reports to `industries/{slug}/figure_contexts.jsonl`, company-focused reports to `companies/{key}/figure_contexts.jsonl`.
14. Run `.venv/bin/python scripts/narrative_flags.py --source-id SOURCE_ID --scope SCOPE --ref REF --registry-base .` for each touched ref.
15. Persist bundle to `{source_dir}/bundles/{sha8}.json`, append `data/bundle_registry.jsonl`, and report source id, touched refs, applied claims, narrative writes, and bundle URL.
```

- [ ] **Step 3: Write workflow-specific files**

Create four short workflow files that include the common workflow and only define differences.

`industry-research.md` must state:

```markdown
- `source_type`: `industry_report`
- source file location: `industries/{primary_slug}/sources/`
- figure contexts location: `industries/{primary_slug}/figure_contexts.jsonl`
- before claim matching, ensure `primary_slug` and any `arena_candidates[*].parent_industry_slug` exist.
```

`annual-report.md` must state:

```markdown
- `source_type`: `annual_report`
- source file location: `companies/{market}_{ticker}/sources/`
- primary company is the detected ticker selected by the user or the only detected ticker.
- period format is `FYyyyy`.
- figure contexts location: `companies/{market}_{ticker}/figure_contexts.jsonl`.
```

`quarterly-report.md` must state:

```markdown
- `source_type`: `quarterly_report`
- source file location: `companies/{market}_{ticker}/sources/`
- period format is `FYyyyyQq`.
- figure contexts location: `companies/{market}_{ticker}/figure_contexts.jsonl`.
```

`sell-side-note.md` must state:

```markdown
- `source_type`: `sell_side_report`
- first classify `focus_type` as `company` or `industry` from report abstract and first three sections.
- if unclear, ask the user with `AskUserQuestion`.
- `focus_type=company`: source file and figure contexts go under `companies/{market}_{ticker}/`.
- `focus_type=industry`: source file and figure contexts go under `industries/{primary_slug}/`.
```

- [ ] **Step 4: Write new SKILL.md**

The new skill entry must route only by source type:

```markdown
# Ingest

Use this skill to ingest investment research source files into the review-bundle endgame pipeline.

Never use digest prompts or digest-era fields. The only supported path is:

`preprocess → review-bundle → review-bundle QA → ingest_match → ingest_apply → ClaimRegistry → narrative_propose → narrative_apply → narrative_flags → bundle registry`.

Route by source type:

- industry report → `workflows/industry-research.md`
- annual report → `workflows/annual-report.md`
- quarterly report → `workflows/quarterly-report.md`
- sell-side note → `workflows/sell-side-note.md`
```

- [ ] **Step 5: Update or delete digest prompt contract tests**

If `tests/test_digest_prompt_contracts.py` exists only to enforce old digest prompts, delete it. If a general ingest skill contract test exists, update it to assert:

```python
assert "key_facts" not in skill_text
assert "route_key_facts" not in skill_text
assert "review-bundle" in skill_text
assert "ingest_match" in skill_text
assert "ingest_apply" in skill_text
assert "ClaimRegistry" in skill_text
```

- [ ] **Step 6: Run workflow/doc tests**

```bash
.venv/bin/python -m pytest tests/test_digest_prompt_contracts.py tests/test_industry_research_workflow*.py -v
```

If deleted test files make this command invalid, run the remaining workflow-related tests discovered by:

```bash
.venv/bin/python -m pytest tests -k "workflow or digest_prompt or ingest_skill" -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/ingest docs/superpowers/archive tests
git commit -m "feat(ingest): replace digest workflows with endgame path"
```

---

## Task 12: Persist bundles from workflow-compatible helper

**Files:**
- Create or Modify: a small script/helper if one exists for ingest workflow utilities
- Add tests near bundle registry tests

- [ ] **Step 1: Add failing test for bundle persistence helper**

If there is an existing ingest utility script, add this test there; otherwise add to `tests/test_bundle_registry.py`:

```python
def test_persist_bundle_writes_co_located_bundle_and_registry(tmp_path):
    bundle = {
        "source_digest": {
            "source_id": "source-1",
            "source_type": "industry_report",
            "source_date": "2025-04-10",
        },
        "insight_blocks": [],
        "atomic_facts": [],
        "synthesis": {},
    }
    source_file = tmp_path / "industries" / "cn-nuclear-fusion" / "sources" / "report.pdf"
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(b"%PDF-1.4")

    entry = bundle_registry.persist_bundle(
        bundle,
        source_file_path=source_file,
        touched={"industries": ["cn-nuclear-fusion"], "arenas": [], "companies": []},
        base=tmp_path,
    )

    assert entry["bundle_path"] == "industries/cn-nuclear-fusion/bundles/" + entry["sha8"] + ".json"
    assert (tmp_path / entry["bundle_path"]).exists()
    assert bundle_registry.get_bundle("source-1", base=tmp_path)["source_id"] == "source-1"
```

- [ ] **Step 2: Implement `persist_bundle` in `app/io/bundle_registry.py`**

```python
import hashlib
from datetime import datetime, timezone


def persist_bundle(
    bundle: dict[str, Any],
    *,
    source_file_path: Path,
    touched: dict[str, list[str]],
    base: Path | None = None,
) -> dict[str, Any]:
    root = _base(base)
    source_file_path = Path(source_file_path)
    rel_source = source_file_path.relative_to(root) if source_file_path.is_absolute() else source_file_path
    raw = json.dumps(bundle, ensure_ascii=False, sort_keys=True).encode("utf-8")
    sha8 = hashlib.sha256(raw).hexdigest()[:8]
    bundle_rel = rel_source.parent.parent / "bundles" / f"{sha8}.json"
    bundle_abs = root / bundle_rel
    bundle_abs.parent.mkdir(parents=True, exist_ok=True)
    bundle_abs.write_bytes(raw)

    digest = bundle.get("source_digest", {})
    entry = {
        "source_id": digest["source_id"],
        "sha8": sha8,
        "source_type": digest.get("source_type", "unknown"),
        "institution": digest.get("institution", ""),
        "publish_date": digest.get("source_date", ""),
        "bundle_path": str(bundle_rel),
        "source_file_path": str(rel_source),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "touched": touched,
    }
    append_registry(entry, base=base)
    return entry
```

- [ ] **Step 3: Run bundle registry tests**

```bash
.venv/bin/python -m pytest tests/test_bundle_registry.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add app/io/bundle_registry.py tests/test_bundle_registry.py
git commit -m "feat(ingest): persist bundles beside sources"
```

---

## Task 13: Delete old per-company claims and industry observations data

**Files:**
- Delete: `companies/*/claims.jsonl`
- Delete: `industries/*/observations.jsonl`

- [ ] **Step 1: Verify web no longer depends on deleted data**

Run:

```bash
.venv/bin/python -m pytest tests/test_web_claims_source_switch.py tests/test_web_observations_panel_removed.py -v
```

Expected: PASS.

- [ ] **Step 2: Delete old data files**

Run:

```bash
find companies -name claims.jsonl -type f -delete
find industries -name observations.jsonl -type f -delete
```

This is authorized by the approved spec: old per-company claims are intentionally discarded and structured observations are deprecated.

- [ ] **Step 3: Confirm no old files remain**

Run:

```bash
find companies -name claims.jsonl -type f
find industries -name observations.jsonl -type f
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add -u companies industries
git commit -m "chore(data): remove legacy claims and observations"
```

---

## Task 14: Update user-facing docs

**Files:**
- Modify: `USER-GUIDE.md`
- Modify: any ingest docs that still mention digest fields

- [ ] **Step 1: Search for stale terms**

Run:

```bash
grep -R "key_facts\|proposed_arenas\|route_key_facts\|observations.jsonl\|companies/.*/claims.jsonl" -n USER-GUIDE.md docs .claude/skills/ingest tests || true
```

- [ ] **Step 2: Update docs**

In `USER-GUIDE.md`, document:

```markdown
## Ingest output

New ingest runs produce:

- a review bundle with `insight_blocks`, `atomic_facts`, `synthesis`, `claim_candidates`, `company_candidates`, and `arena_candidates`
- ClaimRegistry entries under `claims/*.jsonl`
- archive narrative updates in industry 11 dimensions, arena 6 dimensions, and company 8 dimensions after proposal approval
- bundle registry entries visible at `/bundles`

Old per-company `claims.jsonl` and industry `observations.jsonl` are no longer maintained.
```

Do not document `investment_lens` as implemented.

- [ ] **Step 3: Run stale-term search again**

```bash
grep -R "key_facts\|proposed_arenas\|route_key_facts\|companies/.*/claims.jsonl" -n USER-GUIDE.md docs .claude/skills/ingest tests || true
```

Expected: only archived digest docs under `docs/superpowers/archive/` may match.

- [ ] **Step 4: Commit**

```bash
git add USER-GUIDE.md docs .claude/skills/ingest tests
git commit -m "docs(ingest): document endgame ingest outputs"
```

---

## Task 15: Full regression and self-review

**Files:**
- No planned code changes unless tests reveal issues.

- [ ] **Step 1: Run focused ingest suite**

```bash
.venv/bin/python -m pytest \
  tests/test_ingest_review_bundle_qa.py \
  tests/test_ingest_match_cli.py \
  tests/test_ingest_apply.py \
  tests/test_bundle_registry.py \
  tests/test_ingest_aggregate_new.py \
  -v
```

Expected: PASS.

- [ ] **Step 2: Run narrative suite**

```bash
.venv/bin/python -m pytest tests/test_narrative* -v
```

Expected: PASS.

- [ ] **Step 3: Run web suite**

```bash
.venv/bin/python -m pytest \
  tests/test_bundle_routes.py \
  tests/test_source_routes.py \
  tests/test_web_claims_source_switch.py \
  tests/test_web_observations_panel_removed.py \
  -v
```

Expected: PASS.

- [ ] **Step 4: Run all tests**

```bash
.venv/bin/python -m pytest -v
```

Expected: PASS. If unrelated pre-existing failures appear, record exact failing tests and rerun the focused suites above to confirm this implementation is clean.

- [ ] **Step 5: Search for active digest references**

```bash
grep -R "key_facts\|route_key_facts\|proposed_arenas\|write_industry_observations\|facts_to_claims" -n \
  .claude/skills/ingest scripts app tests docs/prompts USER-GUIDE.md || true
```

Expected: no matches outside archived docs/specs that intentionally discuss the old path.

- [ ] **Step 6: Manual smoke route check**

Start the app using the repo's existing run command, then open these pages in a browser:

```text
/bundles
/industries/cn-nuclear-fusion
```

If there is no bundle data yet, `/bundles` may be empty but must render. Do not claim source PDF viewing is fully validated until a real bundle registry entry exists.

- [ ] **Step 7: Final commit if fixes were needed**

If Step 1-6 required fixes:

```bash
git add <changed files>
git commit -m "fix(ingest): stabilize endgame replacement"
```

---

## Self-Review Checklist

- Spec coverage:
  - Review-bundle `arena_candidates[]`: Task 1.
  - Match confidence and auto/pending split: Task 2.
  - Apply multiple decisions and `applied.jsonl`: Task 3.
  - Bundle registry and source co-location: Tasks 4 and 12.
  - Aggregate cleanup and figure contexts helpers: Task 5.
  - Generic narrative CLI used by workflows: Task 6.
  - ClaimRegistry web switch: Task 7.
  - Observations removal: Task 8.
  - Bundle/source browsing: Task 9.
  - Claim source badge links: Task 10.
  - Workflow/SKILL replacement and digest archival: Task 11.
  - Legacy data deletion: Task 13.
  - User docs: Task 14.
  - Regression: Task 15.
- No planned task implements `investment_lens`.
- No planned task migrates old per-company claims.
- No workflow step uses digest fields.
- The plan does not assume generic `narrative_propose --scope --ref` already exists; Task 6 implements it first.
- The plan uses `--registry-base .` for real workflow commands so ClaimRegistry writes project-root `claims/*.jsonl`.

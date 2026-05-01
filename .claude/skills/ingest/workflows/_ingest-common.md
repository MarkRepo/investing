# Endgame Ingest Common Workflow

> **Do NOT use digest prompts, key_facts, route_key_facts, proposed_arenas, per-company claims.jsonl written from digest JSON, or observations.jsonl.**
> The digest-era fields and flow are archived in `docs/superpowers/archive/`. The only supported path is described below.

---

## 15-Step Endgame Workflow

### Step 1 — Preprocess

Run `scripts.preprocess_report` to convert the source file (PDF/HTML/MD/TXT) into structured JSON:

```bash
.venv/bin/python -m scripts.preprocess_report <file> \
    --type {annual|quarterly|sell-side|industry} \
    --market {a-share|us} \
    --out /tmp/ingest-<sha8>-preprocess.json
```

Output fields: `meta`, `sections`, `figure_contexts`, `detected_tickers`, `report_abstract`.

**Known limits of preprocess — the controller must verify / patch before proceeding:**

- `meta.institution` is often `null` — read the report cover from `sections[0:5]` or `report_abstract` and fill it manually before building the source_id.
- `detected_tickers` order does not match cover-page company order; it also occasionally contains invalid strings (OCR noise). Always cross-check ticker↔company name from the cover, not from list position.

### Step 2 — Generate Bundle

Dispatch a **general-purpose subagent** (NOT Explore — Explore is read-only search) with `docs/prompts/ingest-review-bundle.md` as the LLM prompt and the full preprocessed JSON as input. The subagent returns a strict JSON bundle containing `bundle_version`, `source_digest`, `insight_blocks`, `atomic_facts`, `arena_candidates`, `company_candidates`, `claim_candidates`, `synthesis`, `stage_gates`, `schema_fit_review`.

Save to `/tmp/ingest-<sha8>-bundle.json`.

### Step 3 — Run ingest_qa review-bundle

```bash
.venv/bin/python -m scripts.ingest_qa review-bundle \
    --bundle /tmp/ingest-<sha8>-bundle.json \
    --preprocess /tmp/ingest-<sha8>-preprocess.json
```

Fix any reported warnings / errors in the bundle before proceeding. (A capable subagent will usually run this itself at the end of Step 2; rerun independently to confirm.)

### Step 4 — Review bundle.arena_candidates

Examine `bundle.arena_candidates`. For each candidate, decide via `AskUserQuestion`:
- associate with an existing arena slug
- create a new arena (`agg.bootstrap_arena_from_candidate`)
- skip (e.g. no listed participants, or topic out of scope)

Skipped arenas are not bootstrapped and should not appear in `touched.arenas` at Step 15. If a `claim_candidates[*]` references a skipped arena, it will fail `ingest_apply` — either re-label the claim scope or also skip that claim in Step 8.

### Step 5 — Ensure Industries

For each `industry_slug` referenced in the bundle, run:

```python
from scripts import ingest_aggregate as agg
agg.ensure_industry_exists(slug=..., name=..., scope=..., base=Path("."))
```

Autobuild missing industries; do not abort.

### Step 6 — Ensure Companies

For each approved `company_candidates` entry, run:

```python
agg.ensure_company_exists(
    ticker=..., market=..., name=...,
    industry_slugs=[...], base=Path("."),
)
```

Autobuild missing companies; do not abort.

### Step 7 — ingest_match

```bash
.venv/bin/python -m scripts.ingest_match \
    --bundle /tmp/ingest-<sha8>-bundle.json \
    --registry-base . \
    --auto-out /tmp/ingest-<sha8>-auto_apply.json \
    --pending-out /tmp/ingest-<sha8>-pending_review.json
```

**Split semantics:** `auto_apply` only catches `confidence=high` candidates. Everything else (`medium_high`, `medium`, `medium_low`, `low`) goes to `pending_review` — the pending bucket is therefore not just "medium/low", it is "not high". Don't expect `auto_apply` to be populated for first ingests or conservatively scored bundles.

### Step 8 — Review pending_review

Present `pending_review.json` to user via `AskUserQuestion`. For each row, set three fields:

- `decision`: `"new" | "attach" | "skip" | "split"`
- `decision_reason`: one-sentence justification
- **For `decision="new"`**: `direction_on_claim` and `split_instructions` MUST remain `null` (the match file pre-fills them; leave them alone). `ingest_apply` will reject the row otherwise.
- **For `decision="attach"`**: set `target_claim_id` and `direction_on_claim`.
- **For `decision="split"`**: set `split_instructions`.
- **For `decision="skip"`**: only `decision` + `decision_reason`.

Write the file back in place.

### Step 9 — ingest_apply

```bash
.venv/bin/python -m scripts.ingest_apply \
    --bundle /tmp/ingest-<sha8>-bundle.json \
    --registry-base . \
    --decisions /tmp/ingest-<sha8>-auto_apply.json \
    --decisions /tmp/ingest-<sha8>-pending_review.json \
    --applied-out /tmp/ingest-<sha8>-applied.jsonl
```

Writes approved claims into the ClaimRegistry (`claims/{scope_type}s.jsonl`). `applied.jsonl` lists every (claim_id, scope_type, scope_ref, action) — use it to derive the set of touched `(scope, ref)` pairs for Steps 10, 13, 14.

### Step 10 — narrative_propose (per touched scope)

`narrative_propose` is **per (scope, ref)** — not a single bulk call. Loop over every distinct `(scope_type, scope_ref)` in `applied.jsonl`. Cross-cutting scope has no narrative layer; skip it.

```bash
for each (scope, ref) in applied.jsonl where scope in {industry, arena, company}:
    .venv/bin/python -m scripts.narrative_propose \
        --scope {industry|arena|company} \
        --ref <slug_or_ticker> \
        --registry-base . \
        --base . \
        --source-id <source_id> \
        --out /tmp/ingest-<sha8>-proposals-<scope>-<ref>.json
```

Each file holds proposals with `body=null` — bodies are written in Step 11.

### Step 11 — Draft bodies, then approve/skip

`narrative_propose` emits proposal shells only (title default, body null, decision null). For each proposal:

1. Draft a Chinese `body` (150-300 字) grounded in the claim's evidence. Prefer dispatching a Sonnet subagent to draft all proposals across all files in one pass — provide it the bundle + proposal files + claim registry excerpts.
2. Set `decision` to `"approve"` or `"skip"`, with a one-sentence `decision_reason`.
3. Override the default `title` with a dimension-specific headline.
4. Leave `edited_title` / `edited_body` as `null`.

`narrative_apply` rejects proposals with empty bodies — do not approve blank proposals.

### Step 12 — narrative_apply (per proposal file)

```bash
for each proposals file written in Step 10:
    .venv/bin/python -m scripts.narrative_apply \
        --proposals /tmp/ingest-<sha8>-proposals-<scope>-<ref>.json \
        --registry-base . \
        --base .
```

Approved proposals append to the scope's dimension `.md` file with frontmatter; the proposals file gets moved to `data/pending/archive/`.

### Step 13 — Write figure_contexts to source layer

Figure contexts live on the **preprocess** JSON (not the bundle). If preprocess extracted any, write them to the industry or company source layer:

```python
from scripts import ingest_aggregate as agg

# for industry_report / industry-scoped source:
agg.write_figure_contexts(
    slug="<industry_slug>",
    rows=preprocess["figure_contexts"],
    source_meta=preprocess["meta"],
    base=Path("."),
)

# for annual/quarterly/sell-side company source:
agg.write_figure_contexts_for_company(
    "<MARKET_TICKER>",
    preprocess["figure_contexts"],
    preprocess["meta"],
    base=Path("."),
)
```

If `preprocess["figure_contexts"]` is empty (e.g. PDF without extractable figures), skip.

### Step 14 — narrative_flags (per touched scope)

Same loop as Step 10 — one call per touched `(scope, ref)`:

```bash
for each (scope, ref) in applied.jsonl where scope in {industry, arena, company}:
    .venv/bin/python -m scripts.narrative_flags \
        --scope {industry|arena|company} \
        --ref <slug_or_ticker> \
        --registry-base . \
        --base .
```

On a fresh ingest the expected count is **0 flags per scope** (all newly-written narrative frontmatter already lists `supported_by_claims`). Non-zero counts point to orphan narrative sections from before this ingest.

### Step 15 — Persist bundle + update registry

Use the `persist_bundle` helper — it co-locates the bundle JSON with the source file and appends a registry entry atomically.

```python
from app.io.bundle_registry import persist_bundle
from pathlib import Path

entry = persist_bundle(
    bundle,
    source_file_path=Path("<source_dir>/sources/<filename>"),
    touched={
        "industries": [...],  # industry_slugs touched (claim applied OR narrative written)
        "arenas":     [...],  # arena_slugs touched (approved in Step 4, excludes skipped)
        "companies":  [...],  # MARKET_TICKER format
    },
    base=Path("."),
)
```

The helper writes `<source_dir>/bundles/{bundle_sha8}.json` and appends to `data/bundle_registry.jsonl`. Note: the `sha8` in the registry entry is a hash of the bundle JSON content (not the source file's sha8), so don't confuse it with the sha8 used in `source_id`.

**Known gap:** `bundle.source_digest` has no `institution` field, so the registry's `institution` column will be empty string. If the `/bundles` page needs institution filtering, parse it from `source_id` (e.g. `行研-中银证券-2025-04-10-ad983472` → `中银证券`) until the schema adds a first-class field.

---

## Prohibited Fields and Paths

The following are **never used** in the endgame path:

- `key_facts` (digest-era field)
- `route_key_facts` (digest-era function)
- `proposed_arenas` (digest-era field)
- Per-company `claims.jsonl` (replaced by ClaimRegistry at `claims/{scope_type}s.jsonl`)
- `observations.jsonl` under `industries/{slug}/` (replaced by ClaimRegistry)
- Any prompt in `.claude/skills/ingest/prompts/digest/` (archived)
- Digest subagent (Explore returning JSON with `key_facts`)

# Ingest Common Workflow (v3)

> **Do NOT use digest prompts, key_facts, route_key_facts, proposed_arenas, per-company claims.jsonl written from digest JSON, or observations.jsonl.**
> The digest-era fields and flow are archived in `docs/superpowers/archive/`. The only supported path is described below.

---

## v3 Bundle Schema

- **schema_version**: `"v3"`
- **Top-level keys**: `meta`, `claims`, `summary`, `notes`
- **claim fields**: `id`, `text`, `type` (thesis/judgment/risk/catalyst), `scope`, `direction` (-1/0/1), `confidence` (high/medium/low — default `"medium"`), `evidence` (list of `{quote, page, why}`), `relations` (list of `{to, kind}`), `semantic_key` (≤20 chars), `as_of`
- **scope formats**: `industry/{slug}`, `company/{MARKET_TICKER}`, `arena/{slug}`, `brand:{name}`, `cross_cutting`
- **Decisions files**: JSON arrays (not wrapped in `decisions_required`)
- `--auto-out`: high-confidence/clear claims; `--pending-out`: risks/negatives/ambiguous

---

## 6-Step v3 Workflow

### Step 1 — Convert PDF (MinerU)

Use the MinerU desktop application to convert the PDF to a markdown output directory (contains `full.md` + `images/`). Then clean and wrap:

```bash
# Step 1a: clean decorative images, keep data charts
.venv/bin/python -m scripts.clean_mineru <mineru_output_dir>
# Output: full-clean.md + keep_images/ + delete_images/ + classify_report.json

# Step 1b: wrap paths as JSON for downstream use
.venv/bin/python -m scripts.mineru_ingest <mineru_output_dir> \
    --out /tmp/ingest-<sha8>-mineru.json
```

`mineru_ingest.py` auto-detects `full-clean.md` (preferred) or `full.md` (fallback).

Output: `{ _mineru_md, _mineru_images, meta }`.

### Step 2 — Generate Bundle (review-bundle)

Dispatch a **general-purpose subagent** with `docs/prompts/ingest-review-bundle.md` as the LLM prompt. Provide the `full.md` (or `full-clean.md`) file from the MinerU output directory.

The subagent returns a strict v3 JSON bundle. Save to `/tmp/ingest-<sha8>-bundle.json`, then persist to `industries/{slug}/bundles/{sha8}.json` (or `companies/{market}_{ticker}/bundles/{sha8}.json`).

CLI equivalent for re-running extraction:
```bash
.venv/bin/python -m scripts.ingest_qa review-bundle \
    --bundle <path> \
    --mineru-md <mineru_output_dir>/full.md
```

### Step 3 — QA (validate C1-C9)

Run `ingest_qa` to validate the bundle against C1-C9 checks:

```bash
.venv/bin/python -m scripts.ingest_qa review-bundle \
    --bundle /tmp/ingest-<sha8>-bundle.json
```

Fix any reported warnings or errors in the bundle before proceeding. A capable subagent will often run this at the end of Step 2; rerun independently to confirm.

**Common checks**: schema_version is "v3", required claim fields present, confidence values in {high/medium/low}, scope format valid, semantic_key ≤20 chars, evidence list non-empty.

### Step 4 — Match (ingest_match)

Score bundle claims against the existing ClaimRegistry to find duplicates, near-duplicates, and new claims:

```bash
.venv/bin/python -m scripts.ingest_match \
    --bundle /tmp/ingest-<sha8>-bundle.json \
    --registry-base data \
    --auto-out /tmp/ingest-<sha8>-auto.json \
    --pending-out /tmp/ingest-<sha8>-pending.json
```

**Split semantics**:
- `auto.json` — `confidence=high` claims with clear registry disposition; safe to apply without review.
- `pending.json` — risks, negatives, ambiguous, or any claim where confidence is not `"high"`. Always review this file with the user before applying.

**When `pending.json` is non-empty**: present it to the user via `AskUserQuestion`. For each row, the user confirms `decision` (`"new"` / `"attach"` / `"skip"` / `"split"`) and optionally `decision_reason`. Write the file back in place before proceeding to Step 5.

**First ingest of a new industry/company**: `top_matches` will be empty for all rows. Still present claims to the user — they may want to skip low-quality or out-of-scope claims. Do NOT silently bulk-approve without user acknowledgement.

### Step 5 — Apply (ingest_apply)

Write approved claims into the ClaimRegistry:

```bash
.venv/bin/python -m scripts.ingest_apply \
    --bundle /tmp/ingest-<sha8>-bundle.json \
    --decisions /tmp/ingest-<sha8>-auto.json \
    --decisions /tmp/ingest-<sha8>-pending.json \
    --registry-base data
```

Include both `--decisions` flags only when both files exist and are non-empty. Omit a flag if the corresponding file was not produced or is empty.

`ingest_apply` writes approved claims to `claims/{scope_type}s.jsonl` in the registry.

**Ensure industries and companies exist before applying**: for each `industry/{slug}` or `company/{MARKET_TICKER}` scope referenced in the bundle, run `agg.ensure_industry_exists` / `agg.ensure_company_exists` first. Never abort — autobuild missing entries.

### Step 6 — Verify (QA re-run)

Re-run `ingest_qa` to confirm the applied bundle is clean:

```bash
.venv/bin/python -m scripts.ingest_qa review-bundle \
    --bundle /tmp/ingest-<sha8>-bundle.json
```

Expect zero errors. Warnings about missing optional fields are acceptable. If errors appear, fix the underlying data and re-apply.

---

## Post-Apply: Persist Bundle + Registry

After Step 6 passes, persist the bundle to the registry:

```python
from app.io.bundle_registry import persist_bundle
from pathlib import Path

entry = persist_bundle(
    bundle,
    source_file_path=Path("<source_dir>/sources/<filename>"),
    touched={
        "industries": [...],  # industry_slugs touched
        "arenas":     [...],  # arena_slugs touched
        "companies":  [...],  # MARKET_TICKER format
    },
    base=Path("data"),
)
```

The helper writes `<source_dir>/bundles/{bundle_sha8}.json` and appends to `data/bundle_registry.jsonl`.

---

## Post-Apply: Synthesize Insights

Generate a human-readable insights memo from the bundle and applied claims:

```bash
.venv/bin/python -m scripts.synthesize_insights \
    --bundle industries/<slug>/bundles/<sha8>.json \
    --registry-base data \
    --out industries/<slug>/insights/<sha8>.md
```

Then dispatch a **general-purpose subagent** with `docs/prompts/synthesize-insights.md`, providing the context JSON path and the target output path.

---

## Prohibited Fields and Paths

The following are **never used** in the v3 path:

- `key_facts` (digest-era field)
- `route_key_facts` (digest-era function)
- `proposed_arenas` (digest-era field)
- v2 narrative scripts (removed in v3): the `narrative_*` family — propose, apply, flags
- v2 bundle fields (not in v3 schema): `insight_*` blocks, `atomic_*` facts, `block_type`
- v2 gate system (removed in v3): `check_stage_*` script and `stage_*` bundle keys
- `claim_candidates`, `arena_candidates` (v2 bundle keys — v3 uses top-level `claims` array)
- Per-company `claims.jsonl` (replaced by ClaimRegistry at `claims/{scope_type}s.jsonl`)
- `observations.jsonl` under `industries/{slug}/` (replaced by ClaimRegistry)
- Any prompt in `.claude/skills/ingest/prompts/digest/` (archived)
- Digest subagent (Explore returning JSON with `key_facts`)
- `scripts.preprocess_report` (v2 preprocess — use MinerU for PDFs)

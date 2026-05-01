# Endgame Ingest Common Workflow

> **Do NOT use digest prompts, key_facts, route_key_facts, proposed_arenas, per-company claims.jsonl written from digest JSON, or observations.jsonl.**
> The digest-era fields and flow are archived in `docs/superpowers/archive/`. The only supported path is described below.

---

## 15-Step Endgame Workflow

### Step 1 — Preprocess

Run `scripts.preprocess_report` to convert the source file (PDF/HTML/MD/TXT) into structured JSON:

```bash
python3 -m scripts.preprocess_report <file> \
    --type {annual|quarterly|sell-side|industry} \
    --market {a-share|us} \
    --out /tmp/ingest-<sha8>-preprocess.json
```

Output fields: `meta`, `sections`, `figure_contexts`, `detected_tickers`, `report_abstract`.

### Step 2 — Generate Bundle

Generate the review bundle using **`docs/prompts/ingest-review-bundle.md`** as the LLM prompt. Spawn an Explore subagent with the full preprocessed text injected. The subagent returns a structured bundle JSON containing `ingest_review_bundle`, `bundle_version`, `source_digest`, `insight_blocks`, `atomic_facts`, `arena_candidates`, `company_candidates`, `synthesis`, and `stage_gates`.

Save the bundle to `/tmp/ingest-<sha8>-bundle.json`.

### Step 3 — Run ingest_qa review-bundle

```bash
python3 -m scripts.ingest_qa review-bundle \
    --bundle /tmp/ingest-<sha8>-bundle.json
```

Surface any `stage_gates` failures and `schema_fit_review` warnings before proceeding.

### Step 4 — Review bundle.arena_candidates

Examine `bundle.arena_candidates`. For each candidate, decide whether to associate with an existing arena slug or propose a new one. AskUserQuestion if uncertain.

### Step 5 — Ensure Industries

For each `industry_slug` referenced in the bundle, run:

```python
from scripts import ingest_aggregate as agg
agg.ensure_industry_exists(slug=..., name=..., scope=...)
```

Autobuild missing industries; do not abort.

### Step 6 — Ensure Companies

For each `company_candidates` entry, run:

```python
agg.ensure_company_exists(ticker=..., market=..., name=..., industry_slugs=[...], currency=...)
```

Autobuild missing companies; do not abort.

### Step 7 — ingest_match

```bash
python3 -m scripts.ingest_match \
    --bundle /tmp/ingest-<sha8>-bundle.json \
    --registry-base . \
    --auto-out /tmp/ingest-<sha8>-auto_apply.json \
    --pending-out /tmp/ingest-<sha8>-pending_review.json
```

Claims and facts that match existing ClaimRegistry entries go to `auto_apply.json`; unresolved or conflicting ones go to `pending_review.json`.

### Step 8 — Review pending_review

Present `pending_review.json` to user. For each entry, AskUserQuestion with options:

- **approve** — include in apply
- **skip** — exclude from apply

Update the file with decisions.

### Step 9 — ingest_apply

```bash
python3 -m scripts.ingest_apply \
    --decisions /tmp/ingest-<sha8>-auto_apply.json \
    --decisions /tmp/ingest-<sha8>-pending_review.json \
    --applied-out /tmp/ingest-<sha8>-applied.jsonl
```

This writes approved claims/facts into ClaimRegistry and narrative layers.

### Step 10 — narrative_propose

```bash
python3 -m scripts.narrative_propose \
    --scope {company|industry} \
    --ref {market_ticker|industry_slug} \
    --bundle /tmp/ingest-<sha8>-bundle.json \
    --out /tmp/ingest-<sha8>-proposals.jsonl
```

Produces narrative update proposals based on the applied facts.

### Step 11 — AskUserQuestion: approve/skip proposals

Present each narrative proposal. AskUserQuestion with **approve** or **skip** only. Write approved proposals to `/tmp/ingest-<sha8>-approved_proposals.jsonl`.

### Step 12 — narrative_apply

```bash
python3 -m scripts.narrative_apply \
    --proposals /tmp/ingest-<sha8>-approved_proposals.jsonl
```

Writes approved narrative blocks to the appropriate dimension files.

### Step 13 — Write figure_contexts to source layer

```python
from app.io import figure_contexts as figure_contexts_io
figure_contexts_io.append_figure_contexts(
    slug=...,  # industry_slug or company key
    rows=bundle["figure_contexts"],
    source_meta=source_meta,
)
```

### Step 14 — narrative_flags

```bash
python3 -m scripts.narrative_flags \
    --scope {company|industry} \
    --ref {market_ticker|industry_slug} \
    --bundle /tmp/ingest-<sha8>-bundle.json
```

Flags any narrative sections that may need human review based on the new evidence.

### Step 15 — Persist bundle and update registry

Copy the bundle to the source directory:

```bash
cp /tmp/ingest-<sha8>-bundle.json {source_dir}/bundles/<sha8>-review-bundle.json
```

Append to `data/bundle_registry.jsonl`:

```python
import json, datetime
entry = {
    "sha8": sha8,
    "source_file": source_file,
    "source_type": source_type,
    "bundle_path": f"{source_dir}/bundles/{sha8}-review-bundle.json",
    "ingested_at": datetime.datetime.utcnow().isoformat() + "Z",
}
with open("data/bundle_registry.jsonl", "a") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

---

## Prohibited Fields and Paths

The following are **never used** in the endgame path:

- `key_facts` (digest-era field)
- `route_key_facts` (digest-era function)
- `proposed_arenas` (digest-era field)
- Per-company `claims.jsonl` written directly from digest JSON
- `observations.jsonl` written from digest observations
- Any prompt in `.claude/skills/ingest/prompts/digest/` (archived)
- Digest subagent (Explore returning JSON with `key_facts`)

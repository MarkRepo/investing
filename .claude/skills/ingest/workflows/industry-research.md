# Workflow: Industry Research Report

**source_type**: `industry_report`

## Source Location

```
industries/{primary_slug}/sources/{filename}
```

Save the original file with `claims_io.save_source_markdown` (or copy directly) into the industry sources directory.

## Figure Contexts Location

```
industries/{primary_slug}/figure_contexts.jsonl
```

## Pre-match Steps

Before running `ingest_match` (Step 7 of common workflow):

1. Identify or confirm `primary_slug` from the report title/abstract. If unclear, AskUserQuestion.
2. Ensure the `primary_slug` industry exists via `agg.ensure_industry_exists`.
3. For each `arena_candidates` entry in the bundle, confirm the parent industry matches `primary_slug` or a related industry before proceeding.
4. Run Steps 5–6 of the common workflow to ensure all referenced industries and companies exist.

## Workflow Reference

Follow all 15 steps in [`_ingest-common.md`](./_ingest-common.md).

- `--scope industry --ref {primary_slug}` for Steps 10 and 14.
- figure_contexts written to `industries/{primary_slug}/figure_contexts.jsonl` in Step 13.
- Bundle persisted to `industries/{primary_slug}/bundles/` in Step 15.

## Notes

- Industry reports may reference multiple companies (`company_candidates`). Ensure all referenced companies exist but do not force-assign narrative updates to companies outside the report's primary focus.
- Arena candidates from the bundle represent themes across the industry; handle them per Step 4 of the common workflow.

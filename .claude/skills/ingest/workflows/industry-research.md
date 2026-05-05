# Workflow: Industry Research Report

**source_type**: `industry_report`

## Source Location

```
industries/{primary_slug}/sources/{filename}
```

Save the original file with `claims_io.save_source_markdown` (or copy directly) into the industry sources directory.

## Pre-match Steps

Before running `ingest_match` (Step 4 of common workflow):

1. Identify or confirm `primary_slug` from the report title/abstract. If unclear, AskUserQuestion.
2. Ensure the `primary_slug` industry exists via `agg.ensure_industry_exists`.
3. For each arena-scoped claim in the bundle, verify the parent industry matches `primary_slug` or a related industry before proceeding.
4. Ensure all referenced industries and companies exist via `agg.ensure_industry_exists` / `agg.ensure_company_exists`.

## Workflow Reference

Follow the 6-step v3 workflow in [`_ingest-common.md`](./_ingest-common.md).

- Scope for match/apply: `industry/{primary_slug}`.
- Bundle persisted to `industries/{primary_slug}/bundles/` after Step 6.

## Notes

- Industry reports may reference multiple companies. Ensure all referenced companies exist but do not force-assign claims to companies outside the report's primary focus.
- Arena-scoped claims use scope format `arena/{slug}`; handle any new arena slugs by running `agg.ensure_industry_exists` for the parent industry first.

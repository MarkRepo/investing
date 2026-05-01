# Workflow: Sell-Side Research Note

**source_type**: `sell_side_report`

## Focus Type Classification

Before proceeding, classify the report's `focus_type` as **company** or **industry**:

1. Read the report abstract (`report_abstract` from preprocess output) and the first three section headings/text.
2. If the report is anchored to a single ticker (e.g., initiation of coverage, earnings update, target price revision) → `focus_type = company`.
3. If the report surveys a sector, theme, or competitive landscape without a single-company anchor → `focus_type = industry`.
4. If classification is still unclear after reading the abstract and first three sections → **AskUserQuestion** to confirm `focus_type`.

## Source Location by Focus Type

| focus_type | source directory |
|---|---|
| `company` | `companies/{market}_{ticker}/sources/` |
| `industry` | `industries/{primary_slug}/sources/` |

Save the original file with `claims_io.save_source_markdown(...)` for company focus, or copy directly for industry focus.

## Figure Contexts Location

| focus_type | figure_contexts |
|---|---|
| `company` | `companies/{market}_{ticker}/figure_contexts.jsonl` |
| `industry` | `industries/{primary_slug}/figure_contexts.jsonl` |

## Workflow Reference

Follow all 15 steps in [`_ingest-common.md`](./_ingest-common.md).

For **company** focus:
- `--scope company --ref {market}_{ticker}` for Steps 10 and 14.
- Bundle persisted to `companies/{market}_{ticker}/bundles/` in Step 15.

For **industry** focus:
- `--scope industry --ref {primary_slug}` for Steps 10 and 14.
- Bundle persisted to `industries/{primary_slug}/bundles/` in Step 15.

## Notes

- Sell-side notes often include target price (`target_price`) and valuation multiples. These are captured as `atomic_facts` in the review bundle and routed to `valuation` narrative dimension.
- Multi-company sell-side notes (sector comparisons) that are not anchored to a single primary ticker should be classified as `focus_type = industry` and routed through the industry-research workflow instead.
- Do not ingest a multi-company note as `focus_type = company`; if detected, AskUserQuestion to confirm the user wants to re-route to industry.

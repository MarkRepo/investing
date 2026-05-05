# Workflow: Sell-Side Research Note

**source_type**: `sell_side_report`

## Focus Type Classification

Before proceeding, classify the report's `focus_type` as **company** or **industry**:

1. Read the report abstract and the first three section headings/text from the MinerU markdown output.
2. If the report is anchored to a single ticker (e.g., initiation of coverage, earnings update, target price revision) → `focus_type = company`.
3. If the report surveys a sector, theme, or competitive landscape without a single-company anchor → `focus_type = industry`.
4. If classification is still unclear after reading the abstract and first three sections → **AskUserQuestion** to confirm `focus_type`.

## Source Location by Focus Type

| focus_type | source directory |
|---|---|
| `company` | `companies/{market}_{ticker}/sources/` |
| `industry` | `industries/{primary_slug}/sources/` |

Save the original file with `claims_io.save_source_markdown(...)` for company focus, or copy directly for industry focus.

## Workflow Reference

Follow the 6-step v3 workflow in [`_ingest-common.md`](./_ingest-common.md).

For **company** focus:
- Scope for match/apply: `company/{market}_{ticker}`.
- Bundle persisted to `companies/{market}_{ticker}/bundles/` after Step 6.

For **industry** focus:
- Scope for match/apply: `industry/{primary_slug}`.
- Bundle persisted to `industries/{primary_slug}/bundles/` after Step 6.

## Notes

- Sell-side notes often include target price and valuation multiples. These are captured as `type=judgment` claims in the v3 bundle and associated with the `valuation` context in claim text.
- Multi-company sell-side notes (sector comparisons) that are not anchored to a single primary ticker should be classified as `focus_type = industry` and routed through the industry-research workflow instead.
- Do not ingest a multi-company note as `focus_type = company`; if detected, AskUserQuestion to confirm the user wants to re-route to industry.

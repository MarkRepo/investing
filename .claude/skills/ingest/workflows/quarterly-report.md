# Workflow: Quarterly Report / 10-Q

**source_type**: `quarterly_report`

## Source Location

```
companies/{market}_{ticker}/sources/{filename}
```

Save the original file with `claims_io.save_source_markdown(ticker, market, filename, content)`.

## Primary Company

The primary company (`market` + `ticker`) must be detected from the file name and/or the report cover page. If ambiguous, AskUserQuestion to confirm before proceeding.

## Period

`FY{yyyy}Q{q}` (e.g., `FY2024Q3`). Detected from the report's cover page.

## Workflow Reference

Follow the 6-step v3 workflow in [`_ingest-common.md`](./_ingest-common.md).

- Scope for match/apply: `company/{market}_{ticker}`.
- Bundle persisted to `companies/{market}_{ticker}/bundles/` after Step 6.

## Notes

- Quarterly reports are single-company and narrower in scope than annual reports. The review bundle will typically have fewer claims.
- Do not update `business_model` or `moat` narrative dimensions from quarterly data alone; restrict proposals to `financial_profile`, `catalysts`, and `risks` unless the quarterly report contains material structural changes.
- Financial numbers are ingested via `scripts.fetch_financials_{cn,us}` separately.

# Workflow: Annual Report / 10-K / 20-F / Semi-Annual Report

**source_type**: `annual_report`

## Source Location

```
companies/{market}_{ticker}/sources/{filename}
```

Save the original file with `claims_io.save_source_markdown(ticker, market, filename, content)`.

## Primary Company

The primary company (`market` + `ticker`) must be detected from the file name and/or the report cover page. If ambiguous, AskUserQuestion to confirm before proceeding.

## Period

`FYyyyy` (e.g., `FY2024`). Detected from the report's cover page. Semi-annual reports use `FY{yyyy}H1` or `FY{yyyy}H2`.

## Workflow Reference

Follow the 6-step v3 workflow in [`_ingest-common.md`](./_ingest-common.md).

- Scope for match/apply: `company/{market}_{ticker}`.
- Bundle persisted to `companies/{market}_{ticker}/bundles/` after Step 6.

## Notes

- Annual reports are single-company. Do not apply claims to other tickers found in the bundle unless they are subsidiaries of the primary company.
- Financial numbers (revenue, margins, etc.) are ingested via `scripts.fetch_financials_{cn,us}` separately; do not attempt to write `financials.db` rows from the review bundle.

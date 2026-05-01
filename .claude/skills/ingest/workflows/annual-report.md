# Workflow: Annual Report / 10-K / 20-F / Semi-Annual Report

**source_type**: `annual_report`

## Source Location

```
companies/{market}_{ticker}/sources/{filename}
```

Save the original file with `claims_io.save_source_markdown(ticker, market, filename, content)`.

## Primary Company

The primary company (`market` + `ticker`) must be detected from the file name and/or the `detected_tickers` field in the preprocess output. If ambiguous, AskUserQuestion to confirm before proceeding.

## Period

`FYyyyy` (e.g., `FY2024`). Detected from the report's cover page or `meta.fiscal_year` in the preprocess output. Semi-annual reports use `FY{yyyy}H1` or `FY{yyyy}H2`.

## Figure Contexts Location

```
companies/{market}_{ticker}/figure_contexts.jsonl
```

## Workflow Reference

Follow all 15 steps in [`_ingest-common.md`](./_ingest-common.md).

- `--scope company --ref {market}_{ticker}` for Steps 10 and 14.
- figure_contexts written to `companies/{market}_{ticker}/figure_contexts.jsonl` in Step 13.
- Bundle persisted to `companies/{market}_{ticker}/bundles/` in Step 15.

## Notes

- Annual reports are single-company. Do not apply claims or narrative updates to other tickers found in `company_candidates` unless they are subsidiaries of the primary company.
- Financial numbers (revenue, margins, etc.) are ingested via `scripts.fetch_financials_{cn,us}` separately; do not attempt to write `financials.db` rows from the review bundle.

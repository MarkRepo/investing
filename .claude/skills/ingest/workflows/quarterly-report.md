# Workflow: Quarterly Report / 10-Q

**source_type**: `quarterly_report`

## Source Location

```
companies/{market}_{ticker}/sources/{filename}
```

Save the original file with `claims_io.save_source_markdown(ticker, market, filename, content)`.

## Primary Company

The primary company (`market` + `ticker`) must be detected from the file name and/or the `detected_tickers` field in the preprocess output. If ambiguous, AskUserQuestion to confirm before proceeding.

## Period

`FY{yyyy}Q{q}` (e.g., `FY2024Q3`). Detected from the report's cover page or `meta.reporting_period` in the preprocess output.

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

- Quarterly reports are single-company and narrower in scope than annual reports. The review bundle will typically have fewer `insight_blocks` and `atomic_facts`.
- Do not update `business_model` or `moat` narrative dimensions from quarterly data alone; restrict narrative proposals to `financial_profile`, `catalysts`, and `risks` unless the quarterly report contains material structural changes.
- Financial numbers are ingested via `scripts.fetch_financials_{cn,us}` separately.

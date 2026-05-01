---
name: ingest
description: 把一份财报（年报/季报/10-K/10-Q/20-F）、公司研报、或行业研报录入投资系统的三层知识系统（industry / arena / company）。触发词：ingest / 导入 / 录入 / 入库 / 10-K / 10-Q / 20-F / 年报 / 季报 / 半年报 / 研报 / 行业研报 / 行业深度 / Sector Report / Industry Report。适用于用户提供一个本地文件路径并说要把它"ingest / 导入 / 录入"到某家公司或某个行业。
allowed-tools: Bash Read Write Agent AskUserQuestion
argument-hint: "<file-path> [--key MARKET_TICKER | --industry INDUSTRY_SLUG]"
---

# Ingest

Use this skill to ingest investment research source files into the **review-bundle endgame pipeline**.

## Pipeline Overview

The only supported path is:

```
preprocess → review-bundle → review-bundle QA → ingest_match → ingest_apply → ClaimRegistry → narrative_propose → narrative_apply → narrative_flags → bundle registry
```

Never use digest prompts or digest-era fields. See the archived docs at `docs/superpowers/archive/` for historical reference only.

## Source Type Routing

Route the source file to one of four workflows based on its type:

| Source Type | Detected By | Workflow |
|---|---|---|
| Annual report / 10-K / 20-F / semi-annual | filename pattern or first page | `workflows/annual-report.md` |
| Quarterly report / 10-Q | filename pattern or first page | `workflows/quarterly-report.md` |
| Sell-side research note (company or industry focus) | abstract + first three sections | `workflows/sell-side-note.md` |
| Industry research report | anchored to a sector not a single ticker | `workflows/industry-research.md` |

If the source type cannot be determined from filename alone, read the first two pages before routing. If still unclear, AskUserQuestion.

## All Workflows Share the Common Skeleton

Every workflow follows the 15-step endgame skeleton defined in `workflows/_ingest-common.md`. Workflow-specific files add source_type, path conventions, and pre-match steps on top of the common skeleton.

## Key Resources

- **Common workflow**: `workflows/_ingest-common.md`
- **Review-bundle prompt**: `docs/prompts/ingest-review-bundle.md`
- **Preprocess script**: `scripts.preprocess_report`
- **Match script**: `scripts.ingest_match`
- **Apply script**: `scripts.ingest_apply`
- **Narrative scripts**: `scripts.narrative_propose`, `scripts.narrative_apply`, `scripts.narrative_flags`
- **ClaimRegistry**: written by `ingest_apply`; queried by web app and narrative scripts
- **Bundle registry**: `data/bundle_registry.jsonl`
- **Templates**: `.claude/skills/ingest/templates/`
- **Source ID rules**: `.claude/skills/ingest/source-id-rules.yaml`
- **Cross-check rules**: `.claude/skills/ingest/cross-checks.yaml`

## Autobuild Discipline

When an industry or company does not yet exist in the registry, autobuild it using `agg.ensure_industry_exists` / `agg.ensure_company_exists`. Never abort the flow and ask the user to go create the record elsewhere.

## Prohibited

- Digest prompts from `.claude/skills/ingest/prompts/digest/` (archived)
- `key_facts` field or `route_key_facts` function
- `proposed_arenas` digest field
- `observations.jsonl` written from digest output
- Digest subagent returning JSON with `key_facts`
- LLM calls inside Python scripts (all LLM judgment happens in the Claude conversation)
- Writing `profile-{year}.md` (deprecated; use narrative dimension files)
- Skipping `controlled-vocab/subjects.yaml` whitelist validation

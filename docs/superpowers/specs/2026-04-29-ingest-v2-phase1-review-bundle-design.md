# Ingest V2 Phase 1: Insight-Block Review Bundle Design

**Status**: design approved for implementation planning  
**Date**: 2026-04-29  
**Supersedes for Phase 1**: `docs/superpowers/plans/2026-04-29-ingest-v2-phase1-skeleton.md` from Task 3 onward  
**Builds on**: `docs/superpowers/specs/2026-04-28-insight-block-ingest-design.md`

---

## 1. Decision

Phase 1 targets **single-ingest digest correctness**, not repeated-ingest knowledge evolution.

The system should take one source report and produce a reviewable `ingest_review_bundle` that preserves the report's argument structure, facts, risks, company candidates, stage gates, and synthesis. Phase 1 must not write directly into the long-lived `industry / arena / company` archive.

```text
source report
  -> preprocess_report.py
  -> Claude extraction in conversation
  -> insight-block digest
  -> machine QA
  -> ingest_review_bundle.json
  -> user review

Phase 1 stops here. No archive write.
```

This keeps the first milestone focused: can the system understand one report without losing context or overclaiming?

## 2. Why the previous Phase 1 plan changes

The previous plan moved too quickly into:

- `knowledge_delta`
- claim strengthening / weakening
- approved merge
- repeated-ingest comparison
- archive updates

Those features require stable identity for facts, claims, entities, timeframes, scopes, and conflicts. That layer is not ready. Implementing it now risks building toy comparison helpers that pass unit tests but do not safely control the real archive writers.

Phase 1 should first make the digest trustworthy. Phase 2 can compare trustworthy bundles against the archive.

## 3. Existing work to keep

Task 1 and Task 2 are useful and remain in scope.

Current worktree commits:

- `1b2d9e7 feat(ingest): add phase1 preprocess page signals`
- `5da57a2 fix(ingest): wire page signals and extraction warnings into preprocess output`
- `86b8f87 feat(preprocess): add build_preprocess_output() for phase-1 metadata emission`

The page-level metadata is valuable because QA can use it to prevent high-confidence claims from risky pages.

### Required cleanup for existing work

Current preprocess output has two page-metadata locations:

```text
page_signals
extraction_warnings
preprocess_metadata.extracted_pages
preprocess_metadata.extraction_warnings
```

Phase 1 should use one canonical public location:

```yaml
preprocess_metadata:
  page_count: 2
  extracted_pages: []
  extraction_warnings: []
```

`sections`, `figure_contexts`, `detected_tickers`, and `report_abstract` must remain unchanged because existing QA and ingest code already consume them.

Also update:

```yaml
meta:
  preprocess_version: v2-phase1
```

## 4. Phase 1 output: `ingest_review_bundle`

The review bundle is a safe intermediate artifact. It is not an archive write payload.

```yaml
ingest_review_bundle:
  bundle_version: v2-phase1
  source_digest: {}
  insight_blocks: []
  atomic_facts: []
  stage_gates: []
  company_candidates: []
  synthesis: {}
  schema_fit_review: {}
  qa_warnings: []
  write_status: not_applicable_phase1
```

`write_status: not_applicable_phase1` is intentional. It makes the boundary explicit: Phase 1 does not merge.

## 5. `source_digest`

`source_digest` describes the source and the strength of what it can support.

```yaml
source_digest:
  source_id: 国金证券-储能-2026-04-29-abc12345
  source_file: 储能.pdf
  source_type: sellside_industry_report
  source_roles:
    primary: investment_thesis
    secondary:
      - technology_landscape
      - company_screening
  source_quality: medium_high
  evidence_strength: medium
  report_thesis: "..."
  covered_scopes:
    industries: []
    arenas: []
    companies: []
  preprocess_ref:
    preprocess_version: v2-phase1
    extraction_warnings: []
```

Rules:

- `source_quality` evaluates document usability, not truth.
- `evidence_strength` evaluates how strong a conclusion this source can support.
- Low evidence sources can generate questions and weak hypotheses, not strong investment conclusions.

## 6. `insight_blocks`

`insight_block` is the Phase 1 core. It preserves one complete argument or insight from the report.

```yaml
insight_blocks:
  - id: ib-001
    block_type: demand_driver
    title: "用户侧储能经济性取决于峰谷价差"
    source_page_range: "8-10"
    evidence_strength: medium
    summary: "..."
    reasoning_chain:
      - "峰谷价差扩大"
      - "套利空间增加"
      - "用户侧储能回收期缩短"
    assumptions: []
    counterpoints: []
    key_fact_ids: []
    routing:
      industry: []
      arena: []
      company: []
    generated_research_questions: []
```

Rules:

- Facts must hang from blocks, not float alone.
- Blocks preserve source logic. Archive dimensions are only routing hints in Phase 1.
- A company screening block is not a company thesis.

## 7. `atomic_facts`

Atomic facts are evidence units. They are useful only when linked back to blocks.

```yaml
atomic_facts:
  - fact_id: fact-001
    linked_block_id: ib-001
    fact_text: "2025 年用户侧储能新增装机 ..."
    evidence_quote: "..."
    source_page: 9
    target_layer: industry
    target_refs:
      industry_slug: cn-energy-storage
    dimension_hint: demand
    confidence: medium
    evidence_strength: medium
```

Rules:

- Every fact must have `linked_block_id`.
- Every fact must have `evidence_quote`.
- Facts from risky pages cannot be high confidence unless separately reviewed.

## 8. `stage_gates`

Stage gates prevent early industries from being treated as mature revenue stories.

```yaml
stage_gates:
  - id: sg-001
    gate_type: unit_economics
    title: "用户侧储能经济性闭环"
    current_state: "依赖峰谷价差和利用小时"
    crossed: false
    why_matters: "未闭环时不能外推为确定需求"
    evidence_strength: medium
    linked_block_ids: [ib-001]
    verification_questions: []
```

Rules:

- If a material gate is not crossed, `synthesis.cannot_conclude` must explain the limitation.
- For biomed, medtech, low-altitude economy, BCI, quantum, fusion, and other early domains, stage gates are mandatory when the report discusses commercialization.

## 9. `company_candidates`

Company candidates are research leads, not conclusions.

```yaml
company_candidates:
  - ticker: "688019"
    market: SSE
    name: "安集科技"
    exposure_type: direct_supplier
    source_block_ids: [ib-003]
    candidate_reason: "报告将其列为 CMP 抛光液供应商"
    evidence_strength: medium
    confidence: medium
    verification_questions:
      - "相关业务收入占比是多少？"
      - "客户认证和量产进展如何？"
```

Rules:

- Every candidate needs verification questions.
- `thematic_related` cannot be high confidence.
- Logo maps, value-chain diagrams, and stock tables default to review-needed evidence.
- Candidates do not write company narrative in Phase 1.

## 10. `synthesis`

Synthesis is the user's first reading surface. It is not a V0 investment memo.

```yaml
synthesis:
  one_sentence: "..."
  source_quality: medium_high
  evidence_strength: medium
  what_we_know: []
  what_is_plausible: []
  what_needs_verification: []
  investment_questions: []
  cannot_conclude: []
```

Rules:

- `what_we_know` needs evidence support.
- `what_is_plausible` can hold reasoned but unverified implications.
- `cannot_conclude` must block overreach from low-quality sources or uncrossed stage gates.
- Synthesis must not contain buy/sell conclusions.

## 11. QA rules

QA checks the structure and discipline of the bundle. It does not decide whether the investment view is true.

### 11.1 Bundle shape

Errors:

- Missing `source_digest`.
- Missing or empty `insight_blocks`.
- Missing `synthesis`.

### 11.2 Fact-block links

Errors:

- `atomic_fact.linked_block_id` missing.
- `linked_block_id` does not exist in `insight_blocks[].id`.
- `evidence_quote` missing.

### 11.3 Evidence fidelity

Warnings:

- `evidence_quote` cannot be found in preprocess text.
- If preprocess text is short, warning should mention PDF text loss as a possible cause.

### 11.4 Preprocess risk discipline

Warnings or errors:

- High-confidence fact from `text_quality=low` page.
- High-confidence fact from `image_heavy`, `chart_heavy`, or `table_heavy` page.
- High-confidence company candidate sourced only from a risky page.

### 11.5 Insight-block completeness

Warnings:

- Block missing `source_page_range`.
- Block missing `summary`.
- Argument-like block missing `reasoning_chain`.

### 11.6 Stage-gate discipline

Errors:

- Material uncrossed gate exists but `synthesis.cannot_conclude` is empty.
- Synthesis gives strong conclusion while key stage gate remains uncrossed.

### 11.7 Company-candidate discipline

Errors:

- Candidate missing `exposure_type`.
- Candidate missing `source_block_ids`.
- Candidate missing `verification_questions`.

Warnings:

- `thematic_related` candidate has high confidence.
- Candidate comes from company screening or stock table and is phrased as thesis.

### 11.8 Synthesis discipline

Warnings:

- Low evidence source produces strong one-sentence thesis.
- Candidate company appears in `one_sentence` as a confirmed beneficiary.
- `what_we_know` contains unsupported or low-confidence claims.

## 12. Suggested implementation units

Phase 1 should use small pure functions first.

```python
def check_review_bundle_shape(bundle: dict) -> list[dict]: ...
def check_fact_block_links(bundle: dict) -> list[dict]: ...
def check_fact_evidence_quotes(bundle: dict, preprocess: dict) -> list[dict]: ...
def check_preprocess_risk_confidence(bundle: dict, preprocess: dict) -> list[dict]: ...
def check_stage_gate_synthesis(bundle: dict) -> list[dict]: ...
def check_company_candidates(bundle: dict) -> list[dict]: ...
def check_synthesis_discipline(bundle: dict) -> list[dict]: ...

def check_ingest_review_bundle(bundle: dict, preprocess: dict) -> list[dict]:
    ...
```

A CLI can be added after the pure functions work:

```bash
python -m scripts.ingest_qa review-bundle \
  --bundle /tmp/review_bundle.json \
  --preprocess /tmp/preprocess.json
```

## 13. Tests

Add `tests/test_ingest_review_bundle_qa.py`.

Minimum cases:

1. Missing `insight_blocks` returns error.
2. Fact without `linked_block_id` returns error.
3. Fact linked to a nonexistent block returns error.
4. Fact without `evidence_quote` returns error.
5. Evidence quote not found in preprocess text returns warning.
6. High-confidence fact from chart-heavy page returns warning.
7. Uncrossed stage gate with empty `cannot_conclude` returns error.
8. Company candidate without verification questions returns error.
9. Low evidence source with strong synthesis returns warning.
10. Valid bundle returns no errors.

Keep existing tests for preprocess page signals. Add cleanup tests that ensure CLI output uses one canonical `preprocess_metadata` location and keeps existing top-level fields stable.

## 14. Out of scope for Phase 1

- `knowledge_delta`
- repeated-ingest comparison
- strengthened / weakened claim classification
- approved archive merge
- direct writes to `industries/`, `arenas/`, or `companies/`
- investment views
- schema proposal dashboard
- heavy canonicalization or entity graph

These move to Phase 2 after review bundles are reliable.

## 15. Phase 2 bridge

Phase 2 can consume review bundles like this:

```text
review_bundle + existing archive
  -> canonicalize entities
  -> compare facts and block-level claims
  -> produce knowledge_delta
  -> user approval
  -> archive writer gate
```

Phase 2 should not compare raw LLM output directly. It should compare QA-passed review bundles.

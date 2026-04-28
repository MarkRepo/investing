# Ingest V2 Phase 1 Review Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refocus ingest v2 Phase 1 on producing a QA-checked single-report insight-block review bundle without writing to the archive.

**Architecture:** Keep the existing preprocess pipeline and make `preprocess_metadata` the single public page-risk metadata location. Add pure QA functions in `scripts/ingest_qa.py` that validate `ingest_review_bundle` structure, fact links, evidence quotes, preprocess-risk confidence, stage-gate discipline, company-candidate discipline, and synthesis overclaiming. Add a `review-bundle` CLI command that reads a bundle and preprocess JSON, prints warnings, and exits non-zero when warnings/errors exist.

**Tech Stack:** Python 3, pytest, existing `scripts/preprocess_report.py`, existing `scripts/ingest_qa.py`, JSON files, no LLM API calls from scripts.

---

## File Map

**Create:**
- `tests/test_ingest_review_bundle_qa.py` — unit tests for Phase 1 review-bundle QA rules and CLI behavior.
- `docs/superpowers/plans/2026-04-29-ingest-v2-phase1-review-bundle.md` — this plan.

**Modify:**
- `scripts/preprocess_report.py` — normalize preprocess metadata output shape and version.
- `tests/test_preprocess_page_signals.py` — update expectations so `preprocess_metadata` is the only public page metadata location.
- `scripts/ingest_qa.py` — add review-bundle QA pure functions and CLI subcommand.

**Do not modify in this plan:**
- `scripts/ingest_aggregate.py`
- `app/io/*`
- `industries/`, `arenas/`, `companies/`
- HTML templates / CSS

---

### Task 1: Normalize preprocess metadata output

**Files:**
- Modify: `scripts/preprocess_report.py`
- Modify: `tests/test_preprocess_page_signals.py`

- [ ] **Step 1: Update failing tests for one canonical public metadata location**

In `tests/test_preprocess_page_signals.py`, update `test_build_result_wires_page_signals_and_warnings_for_pdf` so it asserts `build_result()` remains internal and does not expose public `preprocess_metadata` by itself:

```python
def test_build_result_wires_internal_page_signals_and_warnings_for_pdf():
    doc = FakeDoc([
        FakePage("表 数据 Chart CAGR"),
        FakePage("x"),
    ])
    template = {"form": "test-form"}
    sections = [{
        "name": "Section1",
        "heading_raw": "Section 1",
        "order": 1,
        "text": "Some content here.",
        "action": "keep",
        "reason": None,
    }]

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_path = Path(f.name)
        f.write(b"test pdf content")

    try:
        result = pr.build_result(
            file_path=temp_path,
            market="a-share",
            form_cli="annual",
            template=template,
            sections=sections,
            text_full="表 数据 Chart CAGR\nx",
            doc=doc,
        )

        assert result["meta"]["preprocess_version"] == "v2-phase1"
        assert "page_signals" in result
        assert "extraction_warnings" in result
        assert "preprocess_metadata" not in result
        assert len(result["page_signals"]) == 2
        assert len(result["extraction_warnings"]) > 0
    finally:
        temp_path.unlink()
```

Update `test_cli_output_includes_preprocess_metadata_for_pdf` so public CLI output has only `preprocess_metadata`:

```python
def test_cli_output_includes_only_preprocess_metadata_for_pdf():
    doc = FakeDoc([
        FakePage("表 数据 Chart CAGR"),
        FakePage("x"),
    ])
    template = {"form": "test-form"}
    sections = [{
        "name": "Section1",
        "heading_raw": "Section 1",
        "order": 1,
        "text": "Some content here.",
        "action": "keep",
        "reason": None,
    }]

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_path = Path(f.name)
        f.write(b"test pdf content")

    try:
        result = pr.build_result(
            file_path=temp_path,
            market="a-share",
            form_cli="annual",
            template=template,
            sections=sections,
            text_full="表 数据 Chart CAGR\nx",
            doc=doc,
        )

        output = pr.add_preprocess_metadata(result, doc)

        assert "preprocess_metadata" in output
        assert "page_signals" not in output
        assert "extraction_warnings" not in output
        assert output["meta"]["preprocess_version"] == "v2-phase1"
        assert "sections" in output
        assert "figure_contexts" in output
        assert "detected_tickers" in output
        assert "report_abstract" in output
        meta = output["preprocess_metadata"]
        assert meta["page_count"] == 2
        assert len(meta["extracted_pages"]) == 2
        assert len(meta["extraction_warnings"]) > 0
    finally:
        temp_path.unlink()
```

Keep `test_build_preprocess_output_includes_page_metadata` as-is except it should call `build_preprocess_output(result)` with no `doc` argument.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest tests/test_preprocess_page_signals.py -v
```

Expected: FAIL because `meta.preprocess_version` is still `v1` and `add_preprocess_metadata()` leaves top-level `page_signals` / `extraction_warnings` in output.

- [ ] **Step 3: Implement minimal preprocess output cleanup**

In `scripts/preprocess_report.py`, change `build_result()` metadata:

```python
"preprocess_version": "v2-phase1",
```

Replace `add_preprocess_metadata()` with:

```python
def add_preprocess_metadata(result: dict, doc=None) -> dict:
    preprocess_meta = build_preprocess_output(result, doc)
    public = dict(result)
    public.pop("page_signals", None)
    public.pop("extraction_warnings", None)
    public["preprocess_metadata"] = preprocess_meta
    return public
```

This preserves internal `build_result()` page signals while making CLI output use one public location.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest tests/test_preprocess_page_signals.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && git add scripts/preprocess_report.py tests/test_preprocess_page_signals.py && git commit -m "fix(preprocess): canonicalize phase1 metadata output"
```

---

### Task 2: Add review-bundle shape and fact-link QA

**Files:**
- Create: `tests/test_ingest_review_bundle_qa.py`
- Modify: `scripts/ingest_qa.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ingest_review_bundle_qa.py`:

```python
from scripts import ingest_qa as qa


def valid_bundle() -> dict:
    return {
        "bundle_version": "v2-phase1",
        "source_digest": {
            "source_id": "src-1",
            "source_quality": "medium_high",
            "evidence_strength": "medium",
        },
        "insight_blocks": [
            {
                "id": "ib-001",
                "block_type": "demand_driver",
                "title": "需求驱动",
                "source_page_range": "1-2",
                "summary": "需求增长来自政策和经济性。",
                "evidence_strength": "medium",
                "reasoning_chain": ["政策支持", "经济性改善"],
            }
        ],
        "atomic_facts": [
            {
                "fact_id": "fact-001",
                "linked_block_id": "ib-001",
                "fact_text": "2025 年新增装机提升。",
                "evidence_quote": "2025 年新增装机提升",
                "source_page": 1,
                "confidence": "medium",
            }
        ],
        "stage_gates": [],
        "company_candidates": [],
        "synthesis": {
            "one_sentence": "储能需求改善，但仍需验证经济性。",
            "evidence_strength": "medium",
            "what_we_know": ["新增装机提升。"],
            "what_is_plausible": [],
            "what_needs_verification": [],
            "investment_questions": [],
            "cannot_conclude": [],
        },
        "schema_fit_review": {},
    }


def test_check_review_bundle_shape_requires_source_blocks_and_synthesis():
    bundle = valid_bundle()
    bundle.pop("source_digest")
    bundle["insight_blocks"] = []
    bundle.pop("synthesis")

    warnings = qa.check_review_bundle_shape(bundle)

    assert [w["rule"] for w in warnings] == [
        "missing_source_digest",
        "missing_insight_blocks",
        "missing_synthesis",
    ]
    assert all(w["severity"] == "error" for w in warnings)


def test_check_fact_block_links_flags_missing_and_unknown_links_and_evidence():
    bundle = valid_bundle()
    bundle["atomic_facts"] = [
        {"fact_id": "fact-1", "fact_text": "孤立事实", "evidence_quote": "孤立事实"},
        {"fact_id": "fact-2", "linked_block_id": "ib-missing", "fact_text": "未知 block", "evidence_quote": "未知 block"},
        {"fact_id": "fact-3", "linked_block_id": "ib-001", "fact_text": "无证据"},
    ]

    warnings = qa.check_fact_block_links(bundle)

    assert [w["rule"] for w in warnings] == [
        "fact_missing_linked_block",
        "fact_unknown_linked_block",
        "fact_missing_evidence_quote",
    ]
    assert all(w["severity"] == "error" for w in warnings)


def test_check_ingest_review_bundle_valid_bundle_has_no_warnings():
    preprocess = {"sections": [{"action": "keep", "text": "2025 年新增装机提升"}], "preprocess_metadata": {"extracted_pages": []}}

    warnings = qa.check_ingest_review_bundle(valid_bundle(), preprocess)

    assert warnings == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest tests/test_ingest_review_bundle_qa.py -v
```

Expected: FAIL with `AttributeError` for missing `check_review_bundle_shape`.

- [ ] **Step 3: Implement shape and fact-link QA**

In `scripts/ingest_qa.py`, add after `check_figure_context_coverage()`:

```python
def _qa_warning(rule: str, severity: str, target: str, detail: str, fix_hint: str | None = None) -> dict:
    out = {
        "rule": rule,
        "severity": severity,
        "target": target,
        "detail": detail,
    }
    if fix_hint:
        out["fix_hint"] = fix_hint
    return out


def check_review_bundle_shape(bundle: dict) -> list[dict]:
    warnings = []
    if not bundle.get("source_digest"):
        warnings.append(_qa_warning(
            "missing_source_digest",
            "error",
            "source_digest",
            "review bundle 缺少 source_digest，无法判断资料类型和证据强度。",
            "补充 source_id、source_quality、evidence_strength 和 source_roles。",
        ))
    if not bundle.get("insight_blocks"):
        warnings.append(_qa_warning(
            "missing_insight_blocks",
            "error",
            "insight_blocks",
            "review bundle 没有 insight_blocks，无法保留原文论证链。",
            "重新抽取：先按原文论证单元切 block，再抽 facts。",
        ))
    if not bundle.get("synthesis"):
        warnings.append(_qa_warning(
            "missing_synthesis",
            "error",
            "synthesis",
            "review bundle 缺少 synthesis，用户没有首屏阅读入口。",
            "补充 one_sentence、what_we_know、what_needs_verification 和 cannot_conclude。",
        ))
    return warnings


def check_fact_block_links(bundle: dict) -> list[dict]:
    block_ids = {b.get("id") for b in bundle.get("insight_blocks") or [] if b.get("id")}
    warnings = []
    for idx, fact in enumerate(bundle.get("atomic_facts") or []):
        fact_id = fact.get("fact_id") or f"#{idx}"
        linked = fact.get("linked_block_id")
        if not linked:
            warnings.append(_qa_warning(
                "fact_missing_linked_block",
                "error",
                f"atomic_facts.{fact_id}",
                f"{fact_id} 没有 linked_block_id，无法回到原始论证上下文。",
                "把 fact 挂到对应 insight_block，或删除这个孤立 fact。",
            ))
        elif linked not in block_ids:
            warnings.append(_qa_warning(
                "fact_unknown_linked_block",
                "error",
                f"atomic_facts.{fact_id}",
                f"{fact_id} 指向不存在的 linked_block_id={linked}。",
                "修正 linked_block_id，或补回对应 insight_block。",
            ))
        if not (fact.get("evidence_quote") or "").strip():
            warnings.append(_qa_warning(
                "fact_missing_evidence_quote",
                "error",
                f"atomic_facts.{fact_id}",
                f"{fact_id} 缺少 evidence_quote，无法追溯原文证据。",
                "补充原文 quote；如果找不到证据，删除该 fact。",
            ))
    return warnings


def check_ingest_review_bundle(bundle: dict, preprocess: dict) -> list[dict]:
    warnings = []
    warnings += check_review_bundle_shape(bundle)
    warnings += check_fact_block_links(bundle)
    return warnings
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest tests/test_ingest_review_bundle_qa.py -v
```

Expected: PASS for the first three tests.

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && git add scripts/ingest_qa.py tests/test_ingest_review_bundle_qa.py && git commit -m "feat(ingest): validate review bundle shape and fact links"
```

---

### Task 3: Add evidence fidelity QA for atomic facts

**Files:**
- Modify: `scripts/ingest_qa.py`
- Test: `tests/test_ingest_review_bundle_qa.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_ingest_review_bundle_qa.py`:

```python
def test_check_fact_evidence_quotes_flags_missing_quote_in_preprocess_text():
    bundle = valid_bundle()
    bundle["atomic_facts"] = [
        {
            "fact_id": "fact-404",
            "linked_block_id": "ib-001",
            "fact_text": "找不到的事实",
            "evidence_quote": "这句原文不存在",
            "source_page": 1,
            "confidence": "medium",
        }
    ]
    preprocess = {"sections": [{"action": "keep", "text": "这里只包含其他原文。"}]}

    warnings = qa.check_fact_evidence_quotes(bundle, preprocess)

    assert len(warnings) == 1
    assert warnings[0]["rule"] == "evidence_quote_not_found"
    assert warnings[0]["severity"] == "warning"
    assert warnings[0]["target"] == "atomic_facts.fact-404"


def test_check_fact_evidence_quotes_accepts_quote_found_in_preprocess_text():
    bundle = valid_bundle()
    preprocess = {"sections": [{"action": "keep", "text": "报告称 2025 年新增装机提升。"}]}

    warnings = qa.check_fact_evidence_quotes(bundle, preprocess)

    assert warnings == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest tests/test_ingest_review_bundle_qa.py::test_check_fact_evidence_quotes_flags_missing_quote_in_preprocess_text -v
```

Expected: FAIL with `AttributeError` for missing `check_fact_evidence_quotes`.

- [ ] **Step 3: Implement evidence fidelity QA**

In `scripts/ingest_qa.py`, add:

```python
def _preprocess_haystack(preprocess: dict) -> str:
    parts = []
    for section in preprocess.get("sections") or []:
        if section.get("action") != "skip":
            parts.append(section.get("text") or "")
    return "\n".join(parts)


def check_fact_evidence_quotes(bundle: dict, preprocess: dict) -> list[dict]:
    haystack = _preprocess_haystack(preprocess)
    if not haystack:
        return []
    claims = []
    fact_ids = []
    for idx, fact in enumerate(bundle.get("atomic_facts") or []):
        quote = fact.get("evidence_quote")
        if not quote:
            continue
        fact_id = fact.get("fact_id") or f"#{idx}"
        claims.append({"id": fact_id, "evidence": [{"text": quote, "type": "primary"}]})
        fact_ids.append(fact_id)

    raw = check_evidence_fidelity(claims, haystack)
    warnings = []
    for item in raw:
        fact_id = item.get("claim_id") or "?"
        warnings.append(_qa_warning(
            "evidence_quote_not_found",
            "warning",
            f"atomic_facts.{fact_id}",
            item["detail"],
            "检查原文页码；如果来自图片/表格，降低 confidence 或标记人工复核。",
        ))
    return warnings
```

Update `check_ingest_review_bundle()`:

```python
warnings += check_fact_evidence_quotes(bundle, preprocess)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest tests/test_ingest_review_bundle_qa.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && git add scripts/ingest_qa.py tests/test_ingest_review_bundle_qa.py && git commit -m "feat(ingest): check review bundle evidence quotes"
```

---

### Task 4: Add preprocess-risk confidence QA

**Files:**
- Modify: `scripts/ingest_qa.py`
- Test: `tests/test_ingest_review_bundle_qa.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_ingest_review_bundle_qa.py`:

```python
def test_check_preprocess_risk_confidence_flags_high_confidence_fact_from_chart_page():
    bundle = valid_bundle()
    bundle["atomic_facts"][0]["confidence"] = "high"
    bundle["atomic_facts"][0]["source_page"] = 3
    preprocess = {
        "preprocess_metadata": {
            "extracted_pages": [
                {"page": 3, "text_quality": "high", "image_heavy": False, "chart_heavy": True, "table_heavy": False}
            ]
        }
    }

    warnings = qa.check_preprocess_risk_confidence(bundle, preprocess)

    assert len(warnings) == 1
    assert warnings[0]["rule"] == "high_confidence_fact_from_risky_page"
    assert warnings[0]["severity"] == "warning"
    assert warnings[0]["target"] == "atomic_facts.fact-001"


def test_check_preprocess_risk_confidence_flags_high_confidence_company_candidate_from_risky_page():
    bundle = valid_bundle()
    bundle["company_candidates"] = [
        {
            "ticker": "688019",
            "market": "SSE",
            "name": "安集科技",
            "confidence": "high",
            "source_page": 5,
            "exposure_type": "direct_supplier",
            "source_block_ids": ["ib-001"],
            "verification_questions": ["收入占比是多少？"],
        }
    ]
    preprocess = {
        "preprocess_metadata": {
            "extracted_pages": [
                {"page": 5, "text_quality": "low", "image_heavy": False, "chart_heavy": False, "table_heavy": False}
            ]
        }
    }

    warnings = qa.check_preprocess_risk_confidence(bundle, preprocess)

    assert len(warnings) == 1
    assert warnings[0]["rule"] == "high_confidence_candidate_from_risky_page"
    assert warnings[0]["target"] == "company_candidates.SSE_688019"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest tests/test_ingest_review_bundle_qa.py::test_check_preprocess_risk_confidence_flags_high_confidence_fact_from_chart_page -v
```

Expected: FAIL with `AttributeError` for missing `check_preprocess_risk_confidence`.

- [ ] **Step 3: Implement preprocess-risk confidence QA**

In `scripts/ingest_qa.py`, add:

```python
def _risky_pages(preprocess: dict) -> dict[int, dict]:
    pages = {}
    meta = preprocess.get("preprocess_metadata") or {}
    for page in meta.get("extracted_pages") or []:
        if (
            page.get("text_quality") == "low"
            or page.get("image_heavy")
            or page.get("chart_heavy")
            or page.get("table_heavy")
        ):
            pages[page.get("page")] = page
    return pages


def check_preprocess_risk_confidence(bundle: dict, preprocess: dict) -> list[dict]:
    risky = _risky_pages(preprocess)
    if not risky:
        return []
    warnings = []
    for idx, fact in enumerate(bundle.get("atomic_facts") or []):
        page = fact.get("source_page")
        if fact.get("confidence") == "high" and page in risky:
            fact_id = fact.get("fact_id") or f"#{idx}"
            warnings.append(_qa_warning(
                "high_confidence_fact_from_risky_page",
                "warning",
                f"atomic_facts.{fact_id}",
                f"{fact_id} 来自第 {page} 页高风险页面，但 confidence=high。",
                "降为 medium，或补充人工复核说明。",
            ))
    for idx, candidate in enumerate(bundle.get("company_candidates") or []):
        page = candidate.get("source_page")
        key = f"{candidate.get('market', '?')}_{candidate.get('ticker', idx)}"
        if candidate.get("confidence") == "high" and page in risky:
            warnings.append(_qa_warning(
                "high_confidence_candidate_from_risky_page",
                "warning",
                f"company_candidates.{key}",
                f"公司候选 {key} 来自第 {page} 页高风险页面，但 confidence=high。",
                "把候选降为 medium，或补充 verification_questions 和人工复核说明。",
            ))
    return warnings
```

Update `check_ingest_review_bundle()`:

```python
warnings += check_preprocess_risk_confidence(bundle, preprocess)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest tests/test_ingest_review_bundle_qa.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && git add scripts/ingest_qa.py tests/test_ingest_review_bundle_qa.py && git commit -m "feat(ingest): flag risky page high confidence outputs"
```

---

### Task 5: Add stage-gate and company-candidate discipline QA

**Files:**
- Modify: `scripts/ingest_qa.py`
- Test: `tests/test_ingest_review_bundle_qa.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_ingest_review_bundle_qa.py`:

```python
def test_check_stage_gate_synthesis_requires_cannot_conclude_for_uncrossed_gate():
    bundle = valid_bundle()
    bundle["stage_gates"] = [{"id": "sg-1", "title": "商业化", "crossed": False}]
    bundle["synthesis"]["cannot_conclude"] = []

    warnings = qa.check_stage_gate_synthesis(bundle)

    assert len(warnings) == 1
    assert warnings[0]["rule"] == "stage_gate_missing_cannot_conclude"
    assert warnings[0]["severity"] == "error"


def test_check_company_candidates_requires_exposure_blocks_and_questions():
    bundle = valid_bundle()
    bundle["company_candidates"] = [
        {"ticker": "688019", "market": "SSE", "name": "安集科技"}
    ]

    warnings = qa.check_company_candidates(bundle)

    assert [w["rule"] for w in warnings] == [
        "candidate_missing_exposure_type",
        "candidate_missing_source_blocks",
        "candidate_missing_verification_questions",
    ]
    assert all(w["severity"] == "error" for w in warnings)


def test_check_company_candidates_flags_thematic_related_high_confidence():
    bundle = valid_bundle()
    bundle["company_candidates"] = [
        {
            "ticker": "688019",
            "market": "SSE",
            "name": "安集科技",
            "exposure_type": "thematic_related",
            "source_block_ids": ["ib-001"],
            "verification_questions": ["收入占比是多少？"],
            "confidence": "high",
        }
    ]

    warnings = qa.check_company_candidates(bundle)

    assert len(warnings) == 1
    assert warnings[0]["rule"] == "thematic_related_high_confidence"
    assert warnings[0]["severity"] == "warning"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest tests/test_ingest_review_bundle_qa.py::test_check_stage_gate_synthesis_requires_cannot_conclude_for_uncrossed_gate -v
```

Expected: FAIL with `AttributeError` for missing `check_stage_gate_synthesis`.

- [ ] **Step 3: Implement stage-gate and company-candidate QA**

In `scripts/ingest_qa.py`, add:

```python
def check_stage_gate_synthesis(bundle: dict) -> list[dict]:
    gates = bundle.get("stage_gates") or []
    synthesis = bundle.get("synthesis") or {}
    has_uncrossed = any(g.get("crossed") is False for g in gates)
    cannot_conclude = synthesis.get("cannot_conclude") or []
    if has_uncrossed and not cannot_conclude:
        return [_qa_warning(
            "stage_gate_missing_cannot_conclude",
            "error",
            "synthesis.cannot_conclude",
            "存在未跨过的 stage gate，但 synthesis.cannot_conclude 为空。",
            "补充不能下结论的原因，例如商业化里程碑尚未实现。",
        )]
    return []


def _candidate_key(candidate: dict, idx: int) -> str:
    market = candidate.get("market")
    ticker = candidate.get("ticker")
    if market and ticker:
        return f"{market}_{ticker}"
    return f"#{idx}"


def check_company_candidates(bundle: dict) -> list[dict]:
    warnings = []
    for idx, candidate in enumerate(bundle.get("company_candidates") or []):
        key = _candidate_key(candidate, idx)
        target = f"company_candidates.{key}"
        if not candidate.get("exposure_type"):
            warnings.append(_qa_warning(
                "candidate_missing_exposure_type",
                "error",
                target,
                f"公司候选 {key} 缺少 exposure_type，无法区分真实收入暴露和主题相关。",
                "补充 direct_pure_play、direct_supplier、component_supplier 或 thematic_related。",
            ))
        if not candidate.get("source_block_ids"):
            warnings.append(_qa_warning(
                "candidate_missing_source_blocks",
                "error",
                target,
                f"公司候选 {key} 缺少 source_block_ids，无法追溯到 insight block。",
                "补充候选来自哪些 company_screening 或 value_chain block。",
            ))
        if not candidate.get("verification_questions"):
            warnings.append(_qa_warning(
                "candidate_missing_verification_questions",
                "error",
                target,
                f"公司候选 {key} 缺少 verification_questions，容易把标的池误写成公司结论。",
                "补充收入占比、客户性质、订单/产品阶段等验证问题。",
            ))
        if candidate.get("exposure_type") == "thematic_related" and candidate.get("confidence") == "high":
            warnings.append(_qa_warning(
                "thematic_related_high_confidence",
                "warning",
                target,
                f"公司候选 {key} 是 thematic_related，但 confidence=high。",
                "降为 medium；主题相关不能直接作为高置信公司 thesis。",
            ))
    return warnings
```

Update `check_ingest_review_bundle()`:

```python
warnings += check_stage_gate_synthesis(bundle)
warnings += check_company_candidates(bundle)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest tests/test_ingest_review_bundle_qa.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && git add scripts/ingest_qa.py tests/test_ingest_review_bundle_qa.py && git commit -m "feat(ingest): enforce stage gate and company candidate QA"
```

---

### Task 6: Add synthesis discipline QA

**Files:**
- Modify: `scripts/ingest_qa.py`
- Test: `tests/test_ingest_review_bundle_qa.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_ingest_review_bundle_qa.py`:

```python
def test_check_synthesis_discipline_flags_low_evidence_strong_thesis():
    bundle = valid_bundle()
    bundle["source_digest"]["evidence_strength"] = "low"
    bundle["synthesis"]["one_sentence"] = "该行业确定进入强投资周期。"

    warnings = qa.check_synthesis_discipline(bundle)

    assert len(warnings) == 1
    assert warnings[0]["rule"] == "low_evidence_strong_synthesis"
    assert warnings[0]["severity"] == "warning"


def test_check_synthesis_discipline_flags_candidate_in_one_sentence_as_beneficiary():
    bundle = valid_bundle()
    bundle["company_candidates"] = [
        {
            "ticker": "688019",
            "market": "SSE",
            "name": "安集科技",
            "exposure_type": "thematic_related",
            "source_block_ids": ["ib-001"],
            "verification_questions": ["收入占比是多少？"],
            "confidence": "medium",
        }
    ]
    bundle["synthesis"]["one_sentence"] = "安集科技将直接受益于行业增长。"

    warnings = qa.check_synthesis_discipline(bundle)

    assert len(warnings) == 1
    assert warnings[0]["rule"] == "candidate_overclaimed_in_synthesis"
    assert warnings[0]["severity"] == "warning"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest tests/test_ingest_review_bundle_qa.py::test_check_synthesis_discipline_flags_low_evidence_strong_thesis -v
```

Expected: FAIL with `AttributeError` for missing `check_synthesis_discipline`.

- [ ] **Step 3: Implement synthesis discipline QA**

In `scripts/ingest_qa.py`, add:

```python
_STRONG_SYNTHESIS_WORDS = ["确定", "强投资", "直接受益", "高确定性", "买入", "卖出"]


def check_synthesis_discipline(bundle: dict) -> list[dict]:
    warnings = []
    source = bundle.get("source_digest") or {}
    synthesis = bundle.get("synthesis") or {}
    one_sentence = synthesis.get("one_sentence") or ""
    evidence_strength = synthesis.get("evidence_strength") or source.get("evidence_strength")
    if evidence_strength in ("low", "medium_low") and _contains_any(one_sentence, _STRONG_SYNTHESIS_WORDS):
        warnings.append(_qa_warning(
            "low_evidence_strong_synthesis",
            "warning",
            "synthesis.one_sentence",
            "低证据强度资料给出了强结论式 synthesis。",
            "降级为市场框架、潜在机会或研究问题，不生成强投资判断。",
        ))
    for idx, candidate in enumerate(bundle.get("company_candidates") or []):
        name = candidate.get("name")
        if name and name in one_sentence and _contains_any(one_sentence, ["受益", "直接受益", "确定", "强投资"]):
            key = _candidate_key(candidate, idx)
            warnings.append(_qa_warning(
                "candidate_overclaimed_in_synthesis",
                "warning",
                "synthesis.one_sentence",
                f"synthesis 直接把候选公司 {key} 写成受益结论。",
                "改成待验证候选，并放入 what_needs_verification 或 investment_questions。",
            ))
    return warnings
```

Update `check_ingest_review_bundle()`:

```python
warnings += check_synthesis_discipline(bundle)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest tests/test_ingest_review_bundle_qa.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && git add scripts/ingest_qa.py tests/test_ingest_review_bundle_qa.py && git commit -m "feat(ingest): flag synthesis overclaims in review bundles"
```

---

### Task 7: Add review-bundle CLI command

**Files:**
- Modify: `scripts/ingest_qa.py`
- Test: `tests/test_ingest_review_bundle_qa.py`

- [ ] **Step 1: Write failing CLI tests**

Append to `tests/test_ingest_review_bundle_qa.py`:

```python
import json


def test_cmd_review_bundle_prints_no_warnings_for_valid_bundle(tmp_path, capsys):
    bundle_path = tmp_path / "bundle.json"
    preprocess_path = tmp_path / "preprocess.json"
    bundle_path.write_text(json.dumps(valid_bundle(), ensure_ascii=False), encoding="utf-8")
    preprocess_path.write_text(json.dumps({
        "sections": [{"action": "keep", "text": "2025 年新增装机提升"}],
        "preprocess_metadata": {"extracted_pages": []},
    }, ensure_ascii=False), encoding="utf-8")

    code = qa.main(["review-bundle", "--bundle", str(bundle_path), "--preprocess", str(preprocess_path)])

    captured = capsys.readouterr()
    assert code == 0
    assert "✓ review bundle QA passed" in captured.out


def test_cmd_review_bundle_prints_warnings_and_returns_one(tmp_path, capsys):
    bundle = valid_bundle()
    bundle["insight_blocks"] = []
    bundle_path = tmp_path / "bundle.json"
    preprocess_path = tmp_path / "preprocess.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    preprocess_path.write_text(json.dumps({"sections": []}, ensure_ascii=False), encoding="utf-8")

    code = qa.main(["review-bundle", "--bundle", str(bundle_path), "--preprocess", str(preprocess_path)])

    captured = capsys.readouterr()
    assert code == 1
    assert "# Review bundle QA" in captured.out
    assert "missing_insight_blocks" in captured.out
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest tests/test_ingest_review_bundle_qa.py::test_cmd_review_bundle_prints_no_warnings_for_valid_bundle -v
```

Expected: FAIL because `main()` does not accept argv and has no `review-bundle` subcommand.

- [ ] **Step 3: Make `main()` accept argv**

Change `scripts/ingest_qa.py`:

```python
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ingest_qa")
    sub = p.add_subparsers(dest="cmd", required=True)
    ...
    args = p.parse_args(argv)
    return args.func(args)
```

The existing `if __name__ == "__main__"` remains:

```python
if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Add `cmd_review_bundle()`**

In `scripts/ingest_qa.py`, add before `main()`:

```python
def cmd_review_bundle(args: argparse.Namespace) -> int:
    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    preprocess = json.loads(Path(args.preprocess).read_text(encoding="utf-8"))
    warnings = check_ingest_review_bundle(bundle, preprocess)
    if not warnings:
        print("✓ review bundle QA passed")
        return 0

    print(f"# Review bundle QA · {len(warnings)} warnings")
    print()
    by_rule: dict[str, list[dict]] = {}
    for warning in warnings:
        by_rule.setdefault(warning["rule"], []).append(warning)
    for rule, rows in by_rule.items():
        print(f"## {rule} ({len(rows)})")
        for row in rows:
            print(f"- [{row['severity']}] {row['target']}: {row['detail']}")
            if row.get("fix_hint"):
                print(f"  fix: {row['fix_hint']}")
        print()
    return 1
```

Add subparser inside `main()`:

```python
p_review = sub.add_parser("review-bundle", help="校验 ingest v2 phase1 review bundle")
p_review.add_argument("--bundle", required=True, help="ingest_review_bundle JSON path")
p_review.add_argument("--preprocess", required=True, help="preprocess JSON path")
p_review.set_defaults(func=cmd_review_bundle)
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest tests/test_ingest_review_bundle_qa.py -v
```

Expected: PASS.

- [ ] **Step 6: Run existing ingest QA tests to catch regressions**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest tests/test_ingest_qa_fidelity.py tests/test_ingest_qa_figure_coverage.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && git add scripts/ingest_qa.py tests/test_ingest_review_bundle_qa.py && git commit -m "feat(ingest): add review bundle QA command"
```

---

### Task 8: Run focused Phase 1 suite

**Files:**
- Test: `tests/test_preprocess_page_signals.py`
- Test: `tests/test_ingest_review_bundle_qa.py`
- Test: `tests/test_ingest_qa_fidelity.py`
- Test: `tests/test_ingest_qa_figure_coverage.py`

- [ ] **Step 1: Run focused suite**

Run:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && .venv/bin/pytest \
  tests/test_preprocess_page_signals.py \
  tests/test_ingest_review_bundle_qa.py \
  tests/test_ingest_qa_fidelity.py \
  tests/test_ingest_qa_figure_coverage.py -v
```

Expected: PASS.

- [ ] **Step 2: Fix any failing test by changing only the affected function**

If a failure occurs, patch only the function named in the traceback:

```text
scripts/preprocess_report.py
scripts/ingest_qa.py
```

Do not modify archive writers or app routes in this phase.

- [ ] **Step 3: Re-run focused suite**

Run the same command from Step 1.

Expected: PASS.

- [ ] **Step 4: Commit if fixes were needed**

If Step 2 changed files, commit:

```bash
cd /Users/yangqi/investing/.worktrees/ingest-v2-phase1 && git add scripts/preprocess_report.py scripts/ingest_qa.py tests/test_preprocess_page_signals.py tests/test_ingest_review_bundle_qa.py && git commit -m "test(ingest): verify phase1 review bundle QA"
```

---

## Spec Coverage Check

- Single-ingest digest correctness → Tasks 2-7.
- No archive writes → File map excludes `scripts/ingest_aggregate.py` and `app/io/*`; no task writes archive data.
- Canonical preprocess metadata → Task 1.
- Review bundle shape → Task 2.
- Fact-block links → Task 2.
- Evidence fidelity → Task 3.
- Preprocess risk discipline → Task 4.
- Stage-gate discipline → Task 5.
- Company-candidate discipline → Task 5.
- Synthesis discipline → Task 6.
- CLI review-bundle command → Task 7.
- Focused tests → Task 8.

No Phase 1 spec gap remains. Phase 2 items remain explicitly out of scope: `knowledge_delta`, repeated-ingest compare, approved merge, archive writes, investment views, schema proposal dashboard, and heavy canonicalization.

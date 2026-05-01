# Phase 1 Ingest V2 Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the minimum ingest v2 skeleton that can compare repeated ingest runs, surface risky extracted content, and only merge user-approved deltas into the knowledge base.

**Architecture:** Keep the existing insight-block digest as the extract core, then add a thin phase-1 shell around it: preprocess risk metadata, minimal claim/time validity fields, minimal QA guards, compare/delta output, and a write gate that only applies approved deltas. Reuse existing scripts (`scripts/preprocess_report.py`, `scripts/ingest_qa.py`, `scripts/ingest_aggregate.py`) and existing archive IO instead of introducing a new storage system.

**Tech Stack:** Python 3, pytest, PyMuPDF (`fitz`), existing `app/io/*` modules, existing FastAPI app for later review wiring.

---

## File Map

**Create:**
- `/Users/yangqi/investing/tests/test_preprocess_page_signals.py` — page-level risk metadata tests for report preprocess output
- `/Users/yangqi/investing/tests/test_ingest_aggregate_phase1_claims.py` — claim/time-validity normalization and delta comparison tests
- `/Users/yangqi/investing/tests/test_ingest_qa_phase1.py` — minimal phase-1 QA guard tests
- `/Users/yangqi/investing/tests/test_ingest_merge_phase1.py` — approved-delta-only merge tests
- `/Users/yangqi/investing/docs/superpowers/plans/2026-04-29-ingest-v2-phase1-skeleton.md` — this plan

**Modify:**
- `/Users/yangqi/investing/scripts/preprocess_report.py` — add page-level metadata + extraction warnings for phase 1 preprocess
- `/Users/yangqi/investing/scripts/ingest_aggregate.py` — add phase-1 claim normalization, validity fields, delta comparison, and approved merge helpers
- `/Users/yangqi/investing/scripts/ingest_qa.py` — add phase-1 ingest-v2 validation rules
- `/Users/yangqi/investing/docs/superpowers/specs/2026-04-28-ingest-v2-research-os-design.md` — already patched with phase split; no further changes in this plan

**Do not modify in this plan:**
- `/Users/yangqi/investing/app/routes/qa.py`
- `/Users/yangqi/investing/app/io/industry.py`
- `/Users/yangqi/investing/app/io/arenas.py`
- `/Users/yangqi/investing/app/io/company.py`
- HTML templates / CSS

---

## Task 1: Add phase-1 preprocess page signals

**Files:**
- Create: `/Users/yangqi/investing/tests/test_preprocess_page_signals.py`
- Modify: `/Users/yangqi/investing/scripts/preprocess_report.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_preprocess_page_signals.py`:

```python
from pathlib import Path

from scripts import preprocess_report as pr


class FakePage:
    def __init__(self, text: str):
        self._text = text

    def get_text(self, mode: str) -> str:
        assert mode == "text"
        return self._text


class FakeDoc:
    def __init__(self, pages: list[FakePage]):
        self._pages = pages

    def __len__(self) -> int:
        return len(self._pages)

    def load_page(self, idx: int) -> FakePage:
        return self._pages[idx]


def test_build_page_signals_flags_low_text_and_chart_pages():
    doc = FakeDoc([
        FakePage("图1 储能装机 CAGR 30%\\n2025E 100 2026E 130"),
        FakePage("短页"),
    ])

    pages = pr.build_page_signals(doc)

    assert [p["page"] for p in pages] == [1, 2]
    assert pages[0]["chart_heavy"] is True
    assert pages[0]["image_heavy"] is False
    assert pages[1]["text_quality"] == "low"


def test_collect_extraction_warnings_mentions_low_text_and_visual_pages():
    signals = [
        {"page": 1, "text_quality": "medium", "image_heavy": False, "chart_heavy": True, "table_heavy": False},
        {"page": 2, "text_quality": "low", "image_heavy": True, "chart_heavy": False, "table_heavy": False},
    ]

    warnings = pr.collect_extraction_warnings(signals)

    assert any("第 1 页" in w and "图表" in w for w in warnings)
    assert any("第 2 页" in w and "文本提取质量低" in w for w in warnings)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_preprocess_page_signals.py -v
```

Expected: FAIL with `AttributeError` for missing `build_page_signals` / `collect_extraction_warnings`.

- [ ] **Step 3: Write minimal implementation**

In `scripts/preprocess_report.py`, add:

```python
def _page_text_quality(text: str) -> str:
    stripped = re.sub(r"\s+", "", text or "")
    if len(stripped) < 30:
        return "low"
    if len(stripped) < 200:
        return "medium"
    return "high"


def build_page_signals(doc) -> list[dict]:
    pages: list[dict] = []
    for i in range(len(doc)):
        text = doc.load_page(i).get_text("text")
        pages.append({
            "page": i + 1,
            "text_quality": _page_text_quality(text),
            "image_heavy": False,
            "chart_heavy": any(k in text for k in ("图", "Chart", "CAGR")),
            "table_heavy": any(k in text for k in ("表", "Table")),
        })
    return pages


def collect_extraction_warnings(page_signals: list[dict]) -> list[str]:
    warnings: list[str] = []
    for page in page_signals:
        if page["text_quality"] == "low":
            warnings.append(f"第 {page['page']} 页文本提取质量低，需谨慎使用。")
        if page["chart_heavy"] or page["image_heavy"]:
            warnings.append(f"第 {page['page']} 页包含图表或图片密集内容，关键结论需复核。")
    return warnings
```

Then update the PDF branch of `extract_text` usage so the preprocess pipeline can access both whole-text output and page signals:

```python
def extract_pdf_text_and_signals(file_path: Path) -> tuple[str, list[dict], list[str]]:
    import fitz

    doc = fitz.open(str(file_path))
    parts = []
    for i in range(len(doc)):
        page = doc.load_page(i)
        parts.append(page.get_text("text"))
    page_signals = build_page_signals(doc)
    warnings = collect_extraction_warnings(page_signals)
    return "\n".join(parts), page_signals, warnings
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_preprocess_page_signals.py -v
```

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_preprocess_page_signals.py scripts/preprocess_report.py
git commit -m "feat(ingest): add phase1 preprocess page signals"
```

---

## Task 2: Emit phase-1 preprocess metadata in CLI output

**Files:**
- Modify: `/Users/yangqi/investing/scripts/preprocess_report.py`
- Test: `/Users/yangqi/investing/tests/test_preprocess_page_signals.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_preprocess_page_signals.py`:

```python
import json


def test_build_output_includes_page_signals_and_warnings(tmp_path):
    out = pr.build_preprocess_output(
        source_file=tmp_path / "demo.pdf",
        text="正文",
        page_signals=[
            {"page": 1, "text_quality": "medium", "image_heavy": False, "chart_heavy": True, "table_heavy": False}
        ],
        extraction_warnings=["第 1 页包含图表或图片密集内容，关键结论需复核。"],
        form="industry",
        market="a-share",
        template_name="a-share-industry.yaml",
    )

    assert out["page_count"] == 1
    assert out["extracted_pages"][0]["chart_heavy"] is True
    assert out["extraction_warnings"] == ["第 1 页包含图表或图片密集内容，关键结论需复核。"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_preprocess_page_signals.py::test_build_output_includes_page_signals_and_warnings -v
```

Expected: FAIL with `AttributeError` for missing `build_preprocess_output`.

- [ ] **Step 3: Write minimal implementation**

In `scripts/preprocess_report.py`, add:

```python
def build_preprocess_output(
    *,
    source_file: Path,
    text: str,
    page_signals: list[dict],
    extraction_warnings: list[str],
    form: str,
    market: str,
    template_name: str,
) -> dict:
    return {
        "source_file": str(source_file),
        "market": market,
        "form": form,
        "template": template_name,
        "page_count": len(page_signals),
        "text": text,
        "extracted_pages": page_signals,
        "extraction_warnings": extraction_warnings,
    }
```

Wire the CLI path to use `extract_pdf_text_and_signals()` for PDFs and return these fields in the JSON blob instead of only raw text.

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_preprocess_page_signals.py -v
```

Expected: PASS with `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_preprocess_page_signals.py scripts/preprocess_report.py
git commit -m "feat(ingest): emit phase1 preprocess metadata"
```

---

## Task 3: Normalize phase-1 claims and validity fields

**Files:**
- Create: `/Users/yangqi/investing/tests/test_ingest_aggregate_phase1_claims.py`
- Modify: `/Users/yangqi/investing/scripts/ingest_aggregate.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ingest_aggregate_phase1_claims.py`:

```python
from scripts import ingest_aggregate as agg


def test_normalize_phase1_claim_adds_validity_defaults():
    claim = agg.normalize_phase1_claim({
        "claim_id": "clm-001",
        "scope_type": "industry",
        "scope_ref": "cn-energy-storage",
        "claim_type": "thesis",
        "claim_text": "储能装机增长仍由电改驱动",
        "confidence": "medium",
    }, as_of="2026-04-29")

    assert claim["validity"]["as_of"] == "2026-04-29"
    assert claim["validity"]["stale_after_days"] == 90
    assert claim["status"] == "active"


def test_normalize_phase1_claim_keeps_existing_validity():
    claim = agg.normalize_phase1_claim({
        "claim_id": "clm-002",
        "scope_type": "industry",
        "scope_ref": "cn-energy-storage",
        "claim_type": "risk",
        "claim_text": "峰谷价差回落会削弱经济性",
        "validity": {"as_of": "2026-04-01", "stale_after_days": 30},
    }, as_of="2026-04-29")

    assert claim["validity"]["as_of"] == "2026-04-01"
    assert claim["validity"]["stale_after_days"] == 30
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_aggregate_phase1_claims.py -v
```

Expected: FAIL with `AttributeError` for missing `normalize_phase1_claim`.

- [ ] **Step 3: Write minimal implementation**

In `scripts/ingest_aggregate.py`, add:

```python
def normalize_phase1_claim(claim: dict, *, as_of: str) -> dict:
    out = dict(claim)
    validity = dict(out.get("validity") or {})
    validity.setdefault("as_of", as_of)
    validity.setdefault("stale_after_days", 90)
    out["validity"] = validity
    out.setdefault("status", "active")
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_aggregate_phase1_claims.py -v
```

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_ingest_aggregate_phase1_claims.py scripts/ingest_aggregate.py
git commit -m "feat(ingest): normalize phase1 claim validity"
```

---

## Task 4: Add minimal delta comparison for repeated ingest

**Files:**
- Modify: `/Users/yangqi/investing/scripts/ingest_aggregate.py`
- Test: `/Users/yangqi/investing/tests/test_ingest_aggregate_phase1_claims.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ingest_aggregate_phase1_claims.py`:

```python
def test_compare_phase1_digest_splits_new_updated_conflicting_facts_and_claims():
    existing = {
        "facts": [
            {"fact_id": "fact-1", "fact_text": "2025 装机 100GW", "metric": "installs", "value": 100},
        ],
        "claims": [
            {"claim_id": "clm-1", "claim_text": "储能经济性改善", "status": "active"},
        ],
    }
    incoming = {
        "facts": [
            {"fact_id": "fact-2", "fact_text": "2026 装机 130GW", "metric": "installs", "value": 130},
            {"fact_id": "fact-3", "fact_text": "2025 装机 90GW", "metric": "installs", "value": 90},
        ],
        "claims": [
            {"claim_id": "clm-2", "claim_text": "储能经济性改善", "status": "active"},
            {"claim_id": "clm-3", "claim_text": "储能经济性恶化", "status": "active"},
        ],
    }

    delta = agg.compare_phase1_digest(existing=existing, incoming=incoming)

    assert [f["fact_id"] for f in delta["new_facts"]] == ["fact-2"]
    assert [f["fact_id"] for f in delta["conflicting_facts"]] == ["fact-3"]
    assert [c["claim_id"] for c in delta["strengthened_claims"]] == ["clm-2"]
    assert [c["claim_id"] for c in delta["weakened_claims"]] == ["clm-3"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_aggregate_phase1_claims.py::test_compare_phase1_digest_splits_new_updated_conflicting_facts_and_claims -v
```

Expected: FAIL with `AttributeError` for missing `compare_phase1_digest`.

- [ ] **Step 3: Write minimal implementation**

In `scripts/ingest_aggregate.py`, add:

```python
def compare_phase1_digest(*, existing: dict, incoming: dict) -> dict:
    delta = {
        "new_facts": [],
        "updated_facts": [],
        "conflicting_facts": [],
        "strengthened_claims": [],
        "weakened_claims": [],
        "stage_gate_updates": [],
        "new_company_candidates": [],
    }

    existing_facts = {(f.get("metric"), f.get("value")): f for f in existing.get("facts") or []}
    existing_by_metric = {f.get("metric"): f for f in existing.get("facts") or []}
    for fact in incoming.get("facts") or []:
        key = (fact.get("metric"), fact.get("value"))
        if key in existing_facts:
            continue
        prior = existing_by_metric.get(fact.get("metric"))
        if prior is None:
            delta["new_facts"].append(fact)
        elif prior.get("value") != fact.get("value"):
            delta["conflicting_facts"].append(fact)
        else:
            delta["updated_facts"].append(fact)

    existing_claim_texts = {c.get("claim_text") for c in existing.get("claims") or []}
    for claim in incoming.get("claims") or []:
        text = claim.get("claim_text") or ""
        if text in existing_claim_texts:
            delta["strengthened_claims"].append(claim)
        elif any(word in text for word in ("恶化", "回落", "放缓", "不及预期")):
            delta["weakened_claims"].append(claim)
    return delta
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_aggregate_phase1_claims.py -v
```

Expected: PASS with `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_ingest_aggregate_phase1_claims.py scripts/ingest_aggregate.py
git commit -m "feat(ingest): add phase1 delta comparison"
```

---

## Task 5: Add phase-1 QA guards

**Files:**
- Create: `/Users/yangqi/investing/tests/test_ingest_qa_phase1.py`
- Modify: `/Users/yangqi/investing/scripts/ingest_qa.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ingest_qa_phase1.py`:

```python
from scripts import ingest_qa as qa


def test_check_stage_gate_guard_warns_on_strong_conclusion_without_crossing_gate():
    warnings = qa.check_stage_gate_guard({
        "stage_gates": [{"gate_type": "clinical_trial", "crossed": False}],
        "synthesis": {"conclusion_strength": "strong", "cannot_conclude": ""},
    })

    assert warnings[0]["rule"] == "stage_gate_guard"


def test_check_visual_evidence_guard_warns_on_high_confidence_mapping_from_visual_page():
    warnings = qa.check_visual_evidence_guard(
        page_signals=[{"page": 3, "image_heavy": True, "chart_heavy": False}],
        company_candidates=[{"name": "示例公司", "confidence": "high", "source_page": 3}],
    )

    assert warnings[0]["rule"] == "visual_company_mapping"


def test_check_fact_link_guard_warns_on_unlinked_fact():
    warnings = qa.check_fact_link_guard([
        {"fact_id": "fact-1", "fact_text": "储能装机提升"},
    ])

    assert warnings[0]["rule"] == "fact_missing_link"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_qa_phase1.py -v
```

Expected: FAIL with missing function errors.

- [ ] **Step 3: Write minimal implementation**

In `scripts/ingest_qa.py`, add:

```python
def check_stage_gate_guard(merged: dict) -> list[dict]:
    gates = merged.get("stage_gates") or []
    synthesis = merged.get("synthesis") or {}
    if any(not g.get("crossed") for g in gates) and synthesis.get("conclusion_strength") == "strong" and not synthesis.get("cannot_conclude"):
        return [{
            "rule": "stage_gate_guard",
            "detail": "stage gate 未跨过，但 synthesis 仍给出 strong conclusion 且缺少 cannot_conclude。",
        }]
    return []


def check_visual_evidence_guard(*, page_signals: list[dict], company_candidates: list[dict]) -> list[dict]:
    visual_pages = {p["page"] for p in page_signals if p.get("image_heavy") or p.get("chart_heavy")}
    out = []
    for candidate in company_candidates:
        if candidate.get("confidence") == "high" and candidate.get("source_page") in visual_pages:
            out.append({
                "rule": "visual_company_mapping",
                "detail": f"company candidate {candidate.get('name')} 来自视觉高风险页，不能直接高置信写入。",
            })
    return out


def check_fact_link_guard(facts: list[dict]) -> list[dict]:
    out = []
    for fact in facts:
        if not fact.get("linked_block_id"):
            out.append({
                "rule": "fact_missing_link",
                "detail": f"fact {fact.get('fact_id')} 缺 linked_block_id。",
            })
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_qa_phase1.py -v
```

Expected: PASS with `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_ingest_qa_phase1.py scripts/ingest_qa.py
git commit -m "feat(ingest): add phase1 QA guards"
```

---

## Task 6: Add approved-delta-only merge helper

**Files:**
- Create: `/Users/yangqi/investing/tests/test_ingest_merge_phase1.py`
- Modify: `/Users/yangqi/investing/scripts/ingest_aggregate.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ingest_merge_phase1.py`:

```python
from scripts import ingest_aggregate as agg


def test_apply_approved_phase1_delta_only_keeps_selected_items():
    delta = {
        "new_facts": [
            {"fact_id": "fact-1", "fact_text": "新事实"},
            {"fact_id": "fact-2", "fact_text": "未批准事实"},
        ],
        "strengthened_claims": [
            {"claim_id": "clm-1", "claim_text": "强化命题"},
        ],
        "conflicting_facts": [
            {"fact_id": "fact-3", "fact_text": "冲突事实"},
        ],
    }

    result = agg.apply_approved_phase1_delta(
        delta=delta,
        approvals={
            "new_facts": ["fact-1"],
            "strengthened_claims": ["clm-1"],
        },
    )

    assert [f["fact_id"] for f in result["applied_deltas"]["new_facts"]] == ["fact-1"]
    assert [c["claim_id"] for c in result["applied_deltas"]["strengthened_claims"]] == ["clm-1"]
    assert [f["fact_id"] for f in result["pending_conflicts"]["conflicting_facts"]] == ["fact-3"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_merge_phase1.py -v
```

Expected: FAIL with `AttributeError` for missing `apply_approved_phase1_delta`.

- [ ] **Step 3: Write minimal implementation**

In `scripts/ingest_aggregate.py`, add:

```python
def apply_approved_phase1_delta(*, delta: dict, approvals: dict[str, list[str]]) -> dict:
    applied = {}
    pending_conflicts = {}
    for bucket, rows in delta.items():
        approved_ids = set(approvals.get(bucket) or [])
        key_name = "claim_id" if "claim" in bucket else "fact_id"
        if bucket == "conflicting_facts":
            pending_conflicts[bucket] = list(rows)
            continue
        applied[bucket] = [row for row in rows if row.get(key_name) in approved_ids]
    return {
        "applied_deltas": applied,
        "pending_conflicts": pending_conflicts,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_merge_phase1.py -v
```

Expected: PASS with `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_ingest_merge_phase1.py scripts/ingest_aggregate.py
git commit -m "feat(ingest): gate phase1 merge on approvals"
```

---

## Task 7: Add a phase-1 orchestration helper for one ingest run

**Files:**
- Modify: `/Users/yangqi/investing/scripts/ingest_aggregate.py`
- Test: `/Users/yangqi/investing/tests/test_ingest_merge_phase1.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ingest_merge_phase1.py`:

```python
def test_build_phase1_run_result_combines_normalized_claims_delta_and_pending_conflicts():
    result = agg.build_phase1_run_result(
        incoming={
            "facts": [{"fact_id": "fact-2", "metric": "installs", "value": 130, "fact_text": "2026 装机 130GW"}],
            "claims": [{"claim_id": "clm-2", "claim_text": "储能经济性改善"}],
        },
        existing={
            "facts": [{"fact_id": "fact-1", "metric": "installs", "value": 100, "fact_text": "2025 装机 100GW"}],
            "claims": [{"claim_id": "clm-1", "claim_text": "储能经济性改善"}],
        },
        as_of="2026-04-29",
        approvals={"strengthened_claims": ["clm-2"]},
    )

    assert result["claims"][0]["validity"]["as_of"] == "2026-04-29"
    assert result["knowledge_delta"]["strengthened_claims"][0]["claim_id"] == "clm-2"
    assert result["merge_result"]["applied_deltas"]["strengthened_claims"][0]["claim_id"] == "clm-2"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_merge_phase1.py::test_build_phase1_run_result_combines_normalized_claims_delta_and_pending_conflicts -v
```

Expected: FAIL with missing function error.

- [ ] **Step 3: Write minimal implementation**

In `scripts/ingest_aggregate.py`, add:

```python
def build_phase1_run_result(*, incoming: dict, existing: dict, as_of: str, approvals: dict[str, list[str]]) -> dict:
    normalized_claims = [normalize_phase1_claim(c, as_of=as_of) for c in incoming.get("claims") or []]
    incoming_bundle = {**incoming, "claims": normalized_claims}
    delta = compare_phase1_digest(existing=existing, incoming=incoming_bundle)
    merge_result = apply_approved_phase1_delta(delta=delta, approvals=approvals)
    return {
        "claims": normalized_claims,
        "knowledge_delta": delta,
        "merge_result": merge_result,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_merge_phase1.py -v
```

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_ingest_merge_phase1.py scripts/ingest_aggregate.py
git commit -m "feat(ingest): assemble phase1 run result"
```

---

## Task 8: Run focused phase-1 test suite

**Files:**
- Test: `/Users/yangqi/investing/tests/test_preprocess_page_signals.py`
- Test: `/Users/yangqi/investing/tests/test_ingest_aggregate_phase1_claims.py`
- Test: `/Users/yangqi/investing/tests/test_ingest_qa_phase1.py`
- Test: `/Users/yangqi/investing/tests/test_ingest_merge_phase1.py`

- [ ] **Step 1: Run the focused suite**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest \
  tests/test_preprocess_page_signals.py \
  tests/test_ingest_aggregate_phase1_claims.py \
  tests/test_ingest_qa_phase1.py \
  tests/test_ingest_merge_phase1.py -v
```

Expected: PASS with all tests green.

- [ ] **Step 2: If any test fails, fix the minimal implementation**

Use the failing traceback to patch only the affected function in:

```text
scripts/preprocess_report.py
scripts/ingest_aggregate.py
scripts/ingest_qa.py
```

Keep the patch local to the failing assertion; do not refactor unrelated code.

- [ ] **Step 3: Re-run the focused suite**

Run:
```bash
cd /Users/yangqi/investing && .venv/bin/pytest \
  tests/test_preprocess_page_signals.py \
  tests/test_ingest_aggregate_phase1_claims.py \
  tests/test_ingest_qa_phase1.py \
  tests/test_ingest_merge_phase1.py -v
```

Expected: PASS with all tests green.

- [ ] **Step 4: Commit**

```bash
git add tests/test_preprocess_page_signals.py \
  tests/test_ingest_aggregate_phase1_claims.py \
  tests/test_ingest_qa_phase1.py \
  tests/test_ingest_merge_phase1.py \
  scripts/preprocess_report.py scripts/ingest_aggregate.py scripts/ingest_qa.py
git commit -m "test(ingest): cover phase1 v2 skeleton"
```

---

## Spec coverage check

- **Preprocess minimal metadata** → Task 1, Task 2
- **Extract layer remains insight-block based** → preserved by plan scope; no rewrite task
- **Independent claim + validity** → Task 3
- **Minimal QA guards** → Task 5
- **Compare / delta for repeated ingest** → Task 4
- **Human-approved merge** → Task 6, Task 7
- **Minimal time validity model** → Task 3

No spec gap remains for the phase-1 skeleton. This plan intentionally excludes phase-2 items: full visual artifact system, investment views, heavy canonicalization, review burden tooling, and dashboard metrics.

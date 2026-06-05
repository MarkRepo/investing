# Comprehensive Audit: All `user_todos` Modification Calls

**Search Scope**: `/Users/yangqi/investing/prism/workflows/` (all `.md` files) and `/Users/yangqi/investing/prism/scripts/` (all `.py` files)

**Last Updated**: 2026-06-05

---

## 1. Python Script: `topic.py` (Core Library Functions)

### Function 1.1: `set_user_todos(slug, todos, variant, *, _skip_resolve=False)`
**File**: `/Users/yangqi/investing/prism/scripts/topic.py`
**Lines**: 885-915
**Signature**: Full-replacement function for `user_todos`

#### What It Does:
- Replaces entire `user_todos` list with new content
- Accepts `list[str | dict]` and normalizes each item to unified schema
- **Protection (H2 modification)**: Raises `ValueError` if existing yaml has structured todos with non-empty `addresses` but new todos have all-empty addresses → forces caller to use `append_user_todos` instead
- Auto-resolves new todos against existing materials (marks `done` if match found)

#### Data Written:
```python
Writes normalized dict structure per todo:
{
  "task": str,
  "priority": "P0|P1|P2",
  "info_tier": "public|half_public|hard",
  "addresses": list[str]  # K# or Q# format, optionally with @event anchor
  "source_hint": str,
  "status": "pending|in_progress|done",
  # Optional fields:
  "covered_by": list[mat_id],
  "coverage_note": str,
  "archive_candidate": str,
}
```

#### Usage Context (Callers):
- **test_web_prescan_batch.py:138** - Test: initial todos setup
- **workflow 01-build-roadmap.md:499** - Step 5.6: Append new structured todos after manual material review
- **workflow 00-research-topic.md:464** - Step 5.3: Initial user_todos creation with full dict structure

---

### Function 1.2: `append_user_todos(slug, todos, variant)`
**File**: `/Users/yangqi/investing/prism/scripts/topic.py`
**Lines**: 918-940
**Signature**: Incremental append to `user_todos`

#### What It Does:
- Appends new todos to existing list (no replacement)
- Accepts `list[str | dict]`, normalizes to schema
- Deduplicates by `task` field (skips if same task already exists)
- Auto-resolves new todos against existing materials
- **Purpose**: Used in workflow stages 03/04/05 where previous todos have structured fields that must be preserved

#### Data Written:
- Same normalized dict structure as `set_user_todos`
- Preserves all existing todos with their addresses/priority/info_tier intact
- New items default to `status='pending'` unless explicitly passed

#### Usage Context (Callers):
- **workflow 03-extract-findings.md:566** - Step 4: Milestone reporting "资料提取完成" (done status)
- **workflow 03-extract-findings.md:573** - Step 4: Progress reporting "资料提取中" (in_progress status)
- **workflow 03-extract-findings.md:610, 618, 625** - Step 2.3c/2.4b/2.5c: Inline progress notes
- **workflow 04-synthesize/_shared.md:252** - Step 4: Completion milestone
- **workflow 05-critic-review.md:394** - Step 7: Request-more verdict → append resource needs

---

### Function 1.3: `update_user_todo_status(slug, variant, task_substring, status, covered_by=None, coverage_note=None)`
**File**: `/Users/yangqi/investing/prism/scripts/topic.py`
**Lines**: 975-1005
**Signature**: Update status of todos by task substring match

#### What It Does:
- Matches todo by **substring** within `task` field
- Updates `status` field to: `pending | in_progress | done`
- Optional: append `covered_by` mat_ids (deduplicated merge)
- Optional: overwrite `coverage_note` with coverage explanation
- **Important**: Substring must be unique; raises `ValueError` if no match found

#### Data Written:
- Updates `status` field only, preserves all other fields
- Appends to `covered_by` set (sorted deduplication)
- Overwrites `coverage_note` if provided

#### Usage Context (Callers):
- **workflow 01-build-roadmap.md:481** - Step 5.6: Update after materials reviewed
  - Example: `'宁德时代凝聚态' → 'in_progress'` (annual report received, transcript pending)
  - Example: `'QuantumScape/Solid Power' → 'done'` (10-K + 10-Q complete)

---

### Function 1.4: `auto_resolve_todos(slug, variant, new_mat_ids)` in web_prescan.py
**File**: `/Users/yangqi/investing/prism/scripts/web_prescan.py`
**Lines**: 1002-1076
**Signature**: Auto-resolve todos against newly added materials

#### What It Does:
- Scans `user_todos` for address matches against new materials
- Appends material IDs to `covered_by` field
- **Tier-aware closure**:
  - `public` info_tier: Any K# match → `status='done'`
  - `hard | half_public`: Only event-anchored match (`K#@event` → `K#@event`) → `done`
  - Bare K# web match on deep-tier → `status='in_progress'` (partial, not closure)
- Writes via `set_user_todos(slug, todos, variant, _skip_resolve=True)`

#### Data Written:
```python
todo["covered_by"] = sorted(set(existing) | set(new_mat_ids))
todo["status"] = "done" | "in_progress"  # Based on tier logic
todo["coverage_note"] = "已由 web-search {mat_ids} 覆盖" | "需事件锚…（未 done）"
```

#### Trigger Context:
- Called from `register_web_search_batch()` during prescan/synthesis
- Returns: `list[dict]` of `{"task": str, "mat_ids": [...]}`

---

## 2. Workflow Markdown Calls

### Workflow 00-research-topic.md
**Line 464-480**: Initial `set_user_todos()` call in Step 5.3
- **Function**: `set_user_todos(slug, [...dict list...], variant)`
- **Data**: K#-addressing research todo structure (P0 resources)
- **Context**: After thesis_v0 written, creates structured todo list for 01-roadmap guidance

### Workflow 01-build-roadmap.md
**Line 481**: `update_user_todo_status()` call in Step 5.6
- **Function**: `update_user_todo_status(slug, variant, task_substring, status)`
- **Data**: Status updates based on LLM material completeness assessment
- **Context**: Material hunt completed, assess what's in hand vs needed

**Line 499**: `set_user_todos()` call in Step 5.6
- **Function**: `set_user_todos(slug, updated_todos_list, variant)`
- **Data**: Full list with status updates + new roadmap-discovered todos
- **Context**: Final material stage before advancing to 02-gather-materials
- **Constraint**: Must pass dict (not list[str]) to preserve addresses/priority/info_tier

### Workflow 02-gather-materials.md
**Lines 267-294**: Documentation + guardrails
- **Constraint**: No `set_user_todos(list[str])` - raises if replacing structured todos
- **Recommendation**: Use `append_user_todos` for progress or `update_user_todo_status` for status changes

### Workflow 03-extract-findings.md
**Line 566, 573, 610, 618, 625**: Multiple `append_user_todos()` calls
- **Step 4 (lines 566, 573)**: Progress milestones after material processing
  - Line 566: `{'task': '资料提取完成：N份全部处理完毕', 'status': 'done'}`
  - Line 573: `{'task': '资料提取中：M/N份已处理', 'status': 'in_progress'}`
- **Steps 2.3c, 2.4b, 2.5c (lines 610, 618, 625)**: Conflict detection diagnostics

**Critical Rule (lines 549-551)**: 
- Must use `append_user_todos` NOT `set_user_todos` (preserves K# addresses)
- Must pass explicit `status` (pending only for real user work, not progress notes)

### Workflow 04-synthesize/_shared.md
**Line 252**: `append_user_todos()` completion milestone
- **Function**: `append_user_todos(slug, [...], variant)`
- **Data**: `{'task': 'synthesis output generation complete', 'status': 'done'}`

### Workflow 04-synthesize/_company_case.md, _industry_funnel.md, _arena_funnel.md
**Lines 272, 243, 236**: Case-specific `append_user_todos()` finalization
- **Pattern**: Completion milestone after case synthesis
- **Status**: 'done'

### Workflow 05-critic-review.md
**Line 394-397**: `append_user_todos()` for request-more verdict
- **Function**: `append_user_todos(slug, resource_todos, variant)`
- **Data**: `{'task': '补充：{具体资料}', 'priority': 'P0', 'info_tier': 'half_public', 'addresses': ['K?']}`
- **Context**: Critic verdict triggers stage back to 02-gather-materials with resource needs
- **Critical**: Must include `addresses` for auto_resolve_todos to match when materials added

---

## 3. Tests: test_web_prescan_batch.py

### Test 133-149: test_batch_resolves_matching_todos
- **Setup**: `set_user_todos(slug, [{'task': 'find K1 evidence', 'addresses': ['K1'], ...}], variant)`
- **Trigger**: `register_web_search_batch()` with matching address
- **Result**: `summary['resolved_todos']` contains completed todo

### Test 151-170: test_auto_resolve_hard_todo_bare_k_not_closed
- **Setup**: Hard-tier todo with bare K# address
- **Trigger**: Web-search match with same K# (no event anchor)
- **Result**: `status='in_progress'`, not `done` (F9 fix)
- **Data**: `coverage_note` explains "需事件锚"

### Test 172-188: test_auto_resolve_hard_todo_event_anchored_closes
- **Setup**: Hard-tier todo with `K#@event` address
- **Trigger**: Material with same `K#@event` address
- **Result**: `status='done'` (strong match)

---

## Key Guardrails

### H2: set_user_todos Safeguard
- **Location**: topic.py lines 900-909
- **Rule**: Raises if passing list[str] when yaml has structured todos
- **Intent**: Prevent accidental overwrite of K# coverage

### F9: Deep-Tier Closure
- **Location**: web_prescan.py lines 1054-1072, topic.py lines 868-880
- **Rule**: Hard/half_public info_tier requires event-anchored match for closure
- **Intent**: Don't false-close expert interview / geopolitical / mirror todos on bare web hit

### S4: set_critic_verdict Encapsulation
- **Location**: workflow 05 line 409, topic.py lines 599-667
- **Rule**: verdict handler manages stage/next_actions/output_status; only append for request-more
- **Intent**: Simplify caller logic, centralize verdict routing

---

## Summary Count

- **Python functions**: 4 main + 2 auto-called (set/append/update/auto-resolve + reverse-check + archive)
- **Workflow markdown calls**: 14+ explicit locations across 00-05 workflows
- **Test coverage**: 4+ test cases validating tier-aware closure and deduplication
- **Total locations**: 20+ distinct call sites


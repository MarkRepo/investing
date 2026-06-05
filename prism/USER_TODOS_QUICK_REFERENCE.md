# Quick Reference: user_todos Modification Functions

## Core Functions (topic.py)

### 1. `set_user_todos(slug, todos, variant)`
**Lines**: 885-915  
**Purpose**: Replace entire user_todos list  
**When to use**: Workflows 00, 01 only (initial creation + final update after material review)  
**Data structure**: `list[dict]` with normalized fields  
**Key constraint (H2)**: Raises if replacing structured todos with bare list[str]

**Example**:
```python
set_user_todos(slug, [
    {'task': 'Download X', 'priority': 'P0', 'info_tier': 'public', 
     'addresses': ['K1'], 'status': 'pending'},
], variant)
```

---

### 2. `append_user_todos(slug, todos, variant)`
**Lines**: 918-940  
**Purpose**: Append todos without replacing existing ones  
**When to use**: Workflows 03, 04, 05 (progress milestones, completion notes)  
**Data structure**: `list[dict]` (same as set, or just `{'task': str, 'status': str}` for progress)  
**Deduplication**: By task field (skips if task already exists)  
**Key rule**: Must pass explicit `status` field (pending/in_progress/done)

**Example**:
```python
append_user_todos(slug, [
    {'task': 'Materials processed: 15/20', 'status': 'in_progress'},
], variant)
```

---

### 3. `update_user_todo_status(slug, variant, task_substring, status)`
**Lines**: 975-1005  
**Purpose**: Update status of single/multiple todos by substring match  
**When to use**: Workflow 01 Step 5.6 (after material review)  
**Matching**: Substring of `task` field (must be unique!)  
**Status values**: pending | in_progress | done  
**Optional**: `covered_by` (list of mat_ids), `coverage_note` (string)

**Example**:
```python
update_user_todo_status(slug, variant, '宁德时代凝聚态', 'in_progress')
```

---

### 4. `auto_resolve_todos(slug, variant, new_mat_ids)` (web_prescan.py)
**Lines**: 1002-1076 (web_prescan.py)  
**Purpose**: Auto-update todos when new materials added  
**Called by**: `register_web_search_batch()` after web-search  
**Tier-aware closure**:
- `public`: Any K# match → done
- `hard|half_public`: Only event-anchored match (K#@event) → done; bare K# → in_progress
- **Note (F9)**: Deep-tier todos don't auto-close on bare K# web hit (must be event-anchored)

---

## Workflow Call Locations

| Workflow | Line | Step | Function | Purpose |
|----------|------|------|----------|---------|
| 00 | 464 | 5.3 | `set_user_todos()` | Create K#-addressing todos for roadmap guidance |
| 01 | 481 | 5.6 | `update_user_todo_status()` | Update after LLM assesses material completeness |
| 01 | 499 | 5.6 | `set_user_todos()` | Write updated list with new roadmap-discovered todos |
| 02 | 267-294 | 6 | (Documentation) | Warns: NO `set_user_todos(list[str])` overwrite (H2 guard) |
| 03 | 566 | 4 | `append_user_todos()` | Milestone: "资料提取完成" (status='done') |
| 03 | 573 | 4 | `append_user_todos()` | Progress: "资料提取中" (status='in_progress') |
| 03 | 610, 618, 625 | 2.3c, 2.4b, 2.5c | `append_user_todos()` | Conflict detection diagnostics |
| 04/_shared | 252 | 4 | `append_user_todos()` | Completion: "Synthesis outputs ready" (status='done') |
| 04/_company | 272 | 4.6 | `append_user_todos()` | Company case finalization |
| 04/_industry | 243 | 4.6 | `append_user_todos()` | Industry case finalization |
| 04/_arena | 236 | 4.6 | `append_user_todos()` | Arena case finalization |
| 05 | 394 | 7 | `append_user_todos()` | Request-more verdict: append resource needs |

---

## Critical Rules (Guardrails)

### H2: set_user_todos Safeguard
- **Rule**: Raises ValueError if trying to replace structured todos (with addresses) using list[str]
- **Fix**: Use `append_user_todos` for progress, or pass complete dict list to `set_user_todos`
- **File**: topic.py lines 900-909

### F9: Deep-Tier Closure
- **Rule**: Hard/half_public info_tier todos won't auto-close on bare K# web match
- **Rationale**: Expert interviews, geopolitical analysis, mirrors need event-specific evidence
- **Behavior**: Bare K# match → status='in_progress' (not done); Event-anchored → done
- **Files**: web_prescan.py 1054-1072, topic.py 868-880, tests 151-188

### Status Field Requirements
- **pending**: User action required (real research task, not progress note)
- **in_progress**: Workflow in progress
- **done**: Completed milestone/task
- **Critical**: Progress notes MUST NOT be pending (confuses UI into thinking user action needed)

---

## Normalized Todo Schema

```python
{
  "task": str,                    # Required
  "priority": "P0"|"P1"|"P2",     # Required (default P1 if not provided)
  "info_tier": "public"|"half_public"|"hard",  # Required
  "addresses": list[str],         # K#/Q# format; can include @event anchor
  "source_hint": str,             # Where to find (optional)
  "status": "pending"|"in_progress"|"done",  # Required (default pending)
  "covered_by": list[str],        # Material IDs that address this (optional)
  "coverage_note": str,           # Explanation of coverage (optional)
  "archive_candidate": str,       # Marked if K# dropped from thesis (optional)
}
```

---

## When to Use Each Function

### `set_user_todos()` (Full Replace)
✓ Workflow 00 Step 5.3 - Create initial K#-addressing todos  
✓ Workflow 01 Step 5.6 - Final update after material review  
✓ Tests - Setup phase  
✗ Workflow 03-05 - Use `append_user_todos` instead (preserves addresses)

### `append_user_todos()` (Non-Destructive Append)
✓ Workflow 03 - Progress milestones (with explicit status)  
✓ Workflow 04 - Completion notes  
✓ Workflow 05 - Resource needs (with addresses for auto_resolve)  
✗ Initial creation - Use `set_user_todos` instead

### `update_user_todo_status()` (Single Update)
✓ Workflow 01 Step 5.6 - Update status after LLM assessment  
✓ Tests - Verify status changes  
✗ Multiple todos - Use `set_user_todos` or `append_user_todos`

### `auto_resolve_todos()` (Auto-Triggered)
✓ Called automatically by `register_web_search_batch()` after web search  
✓ No explicit call needed - happens during prescan/synthesis  
✗ Manual invocation (it's for internal use)

---

## Test Coverage

| Test File | Lines | What | Key Findings |
|-----------|-------|------|--------------|
| test_web_prescan_batch.py | 138-149 | Basic todo resolution | `set_user_todos` + web match → done |
| test_web_prescan_batch.py | 151-170 | F9: bare K# on hard tier | Bare K# → in_progress (NOT done) |
| test_web_prescan_batch.py | 172-188 | F9: event-anchored hard tier | K#@event match → done |

---

## Auto-Called Functions (Internal)

### `reverse_check_roadmap_coverage(slug, variant, version)`
- **Called by**: `set_thesis(version >= 1)` automatically
- **Does**: Compares thesis K# against roadmap, creates reverse-check todos for missing K#
- **Data**: Auto-generates todos with `source_hint="auto-generated by set_thesis reverse-check"`
- **Stage flip**: May change stage to "01-roadmap-reopen" if post-roadmap

### `mark_outdated_ks(slug, variant, version)`
- **Called by**: `set_thesis(version >= 1)` automatically  
- **Does**: Marks todos whose K# was dropped from new thesis version
- **Data**: Adds `archive_candidate` field (doesn't change status)

---

## Common Patterns

### Pattern 1: Initial Creation (Workflow 00)
```python
set_user_todos(slug, [
    {'task': '...', 'priority': 'P0', 'info_tier': 'public', 'addresses': ['K1']},
], variant)
```

### Pattern 2: Status Update (Workflow 01)
```python
update_user_todo_status(slug, variant, 'substring of task', 'done')
set_user_todos(slug, [full updated list], variant)  # Write changes
```

### Pattern 3: Progress Milestone (Workflow 03-05)
```python
append_user_todos(slug, [
    {'task': 'Milestone: X complete', 'status': 'done'},
], variant)
```

### Pattern 4: Resource Gaps (Workflow 05)
```python
append_user_todos(slug, [
    {'task': '补充：X资料', 'priority': 'P0', 'addresses': ['K?']},
], variant)
```

---

## Files to Reference

- **Main implementation**: `/Users/yangqi/investing/prism/scripts/topic.py` (lines 885-1005)
- **Web-search auto**: `/Users/yangqi/investing/prism/scripts/web_prescan.py` (lines 1002-1076)
- **Workflows**: `/Users/yangqi/investing/prism/workflows/` (all .md)
- **Tests**: `/Users/yangqi/investing/prism/scripts/test_web_prescan_batch.py`

---

**Last Updated**: 2026-06-05

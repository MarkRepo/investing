# user_todos Modification Audit - Complete Documentation

## Overview

This audit documents **ALL places** where `user_todos` is modified in the prism system, including workflow markdown files, Python scripts, and tests.

**Total call sites found**: 25+  
**Functions identified**: 6 (4 public + 2 auto-called)  
**Workflow locations**: 14+ call sites  
**Test coverage**: 4 comprehensive tests

---

## Files in This Audit Package

### 1. `USER_TODOS_QUICK_REFERENCE.md` ⭐ START HERE
- **Purpose**: Quick lookup guide for day-to-day reference
- **Contains**: 
  - Each function's signature, purpose, and examples
  - Workflow call locations table
  - Critical rules and guardrails
  - When to use each function
  - Common patterns
- **Best for**: Quick answers, debugging, copy-paste examples

### 2. `USER_TODOS_AUDIT.md`
- **Purpose**: Detailed technical documentation
- **Contains**:
  - In-depth explanation of each function (H2 modification, F9 fix, S4 encapsulation)
  - Complete data structures written
  - Usage context and trigger conditions
  - Auto-called functions (reverse_check, mark_outdated)
  - Guardrails and constraints
  - Change history
- **Best for**: Understanding design decisions, refactoring, testing

### 3. `USER_TODOS_LOCATIONS_TABLE.txt`
- **Purpose**: Comprehensive reference table of all call sites
- **Contains**:
  - Organized table showing file → line → function → data → context
  - Separated by Python scripts, workflows, tests
  - Visual formatting for easy scanning
  - Summary statistics at end
- **Best for**: Finding all locations, cross-reference checks

---

## Key Functions at a Glance

| Function | Purpose | Workflow | Key Rule |
|----------|---------|----------|----------|
| `set_user_todos()` | Full replacement | 00, 01 | H2: Raises if replacing structured with strings |
| `append_user_todos()` | Non-destructive append | 03, 04, 05 | Must pass explicit status field |
| `update_user_todo_status()` | Update by substring | 01 | Substring must be unique |
| `auto_resolve_todos()` | Auto on web-search | (internal) | F9: Deep-tier needs event anchor |
| `reverse_check_roadmap_coverage()` | Auto on thesis upgrade | (internal) | Auto-generates if K# uncovered |
| `mark_outdated_ks()` | Auto on thesis upgrade | (internal) | Marks archive_candidate field |

---

## Workflow Stages and Their user_todos Patterns

```
Workflow 00 (Create Research Topic)
  └─ Step 5.3: set_user_todos() → Create K#-addressing todos

Workflow 01 (Build Roadmap)
  ├─ Step 5.6a: update_user_todo_status() → Update based on material review
  └─ Step 5.6b: set_user_todos() → Write updated list with new appends

Workflow 02 (Gather Materials)
  └─ Step 6: (Constraint documentation) No set_user_todos(list[str]) overwrite!

Workflow 03 (Extract Findings)
  ├─ Step 2: append_user_todos() → Conflict detection diagnostics
  └─ Step 4: append_user_todos() → Progress milestones (done/in_progress)

Workflow 04 (Synthesize)
  ├─ _shared.md Step 4: append_user_todos() → Synthesis completion
  ├─ _company.md Step 4.6: append_user_todos() → Case finalization
  ├─ _industry.md Step 4.6: append_user_todos() → Case finalization
  └─ _arena.md Step 4.6: append_user_todos() → Case finalization

Workflow 05 (Critic Review)
  └─ Step 7: append_user_todos() → Request-more verdict resource needs
```

---

## Critical Guardrails

### H2 (topic.py 900-909): set_user_todos Safeguard
```
RULE: Raises ValueError if trying to overwrite structured todos with bare list[str]
INTENT: Prevent accidental K# coverage loss
WORKAROUND: Use append_user_todos or pass complete dict list
```

### F9 (web_prescan.py 1054-1072): Deep-Tier Closure Restriction
```
RULE: Hard/half_public info_tier requires event-anchored match for closure
- Bare K# web hit → status='in_progress' (NOT done)
- Event-anchored match (K#@event) → status='done'
INTENT: Prevent false closure of expert interview/geopolitical/mirror todos
RATIONALE: These deep materials require specific evidence, not generic web hits
```

### S4 (topic.py 599-667): set_critic_verdict Encapsulation
```
RULE: Verdict handler manages stage/next_actions/output_status automatically
INTENT: Simplify caller logic, centralize routing
CALLER RESPONSIBILITY: Only append todos for request-more verdict
```

---

## Normalized Todo Schema

Every todo (when stored) follows this structure:

```python
{
  "task": str,                              # Required: human-readable task
  "priority": "P0" | "P1" | "P2",          # Required: urgency
  "info_tier": "public" | "half_public" | "hard",  # Required: retrieval difficulty
  "addresses": list[str],                   # K# or Q# references (with optional @event)
  "source_hint": str,                       # Where to find (optional)
  "status": "pending" | "in_progress" | "done",  # Required: workflow state
  "covered_by": list[str],                  # Material IDs addressing this (optional)
  "coverage_note": str,                     # Explanation of coverage (optional)
  "archive_candidate": str,                 # Marked if K# dropped from thesis (optional)
}
```

---

## Common Patterns by Workflow Stage

### Pattern 1: Initial Creation (Workflow 00)
Use `set_user_todos()` with full dict structure:
```python
set_user_todos(slug, [
    {'task': 'Research objective X', 
     'priority': 'P0', 
     'info_tier': 'public', 
     'addresses': ['K1', 'Q1'],
     'status': 'pending'},
], variant)
```

### Pattern 2: Status Update (Workflow 01)
First update individual statuses, then write full list:
```python
update_user_todo_status(slug, variant, 'task substring', 'done')
set_user_todos(slug, [complete updated list], variant)
```

### Pattern 3: Progress Milestone (Workflow 03-05)
Use `append_user_todos()` with minimal structure + explicit status:
```python
append_user_todos(slug, [
    {'task': 'Materials processed: 15/20', 'status': 'in_progress'},
], variant)
```

### Pattern 4: Resource Gap (Workflow 05)
Append with addresses for auto-resolution:
```python
append_user_todos(slug, [
    {'task': 'Supplement: specific material X',
     'priority': 'P0',
     'addresses': ['K3'],
     'info_tier': 'half_public'},
], variant)
```

---

## Testing & Validation

### Test File: `test_web_prescan_batch.py`

| Test Name | Purpose | Key Finding |
|-----------|---------|-------------|
| `test_batch_resolves_matching_todos` | Basic resolution | Public todos auto-close on K# match |
| `test_auto_resolve_hard_todo_bare_k_not_closed` | F9 validation | Bare K# → in_progress (NOT done) |
| `test_auto_resolve_hard_todo_event_anchored_closes` | F9 validation | Event-anchored match → done |

---

## Quick Lookup by Use Case

**"I need to create initial todos"** → See `Pattern 1` + `set_user_todos()` in Quick Reference

**"I need to update a todo status"** → See `update_user_todo_status()` + `Pattern 2`

**"I need to add a progress note"** → See `append_user_todos()` + `Pattern 3` (with status!)

**"I need to report a resource gap from critic"** → See `Pattern 4` + workflow 05 line 394

**"I don't understand a constraint"** → See "Critical Guardrails" section above

**"I'm debugging a todo issue"** → Use `USER_TODOS_LOCATIONS_TABLE.txt` to find all references

---

## Files Changed Across Audit

All modifications follow the function signatures in `/Users/yangqi/investing/prism/scripts/topic.py`:
- Lines 885-915: `set_user_todos()`
- Lines 918-940: `append_user_todos()`
- Lines 975-1005: `update_user_todo_status()`

Supported by auto-calls in:
- Lines 1320-1348: `mark_outdated_ks()`
- Lines 1351-1436: `reverse_check_roadmap_coverage()`

Web integration in:
- `/Users/yangqi/investing/prism/scripts/web_prescan.py` lines 1002-1076: `auto_resolve_todos()`

---

## Document Navigation

1. **For quick lookup**: `USER_TODOS_QUICK_REFERENCE.md`
2. **For technical deep-dive**: `USER_TODOS_AUDIT.md`
3. **For all locations**: `USER_TODOS_LOCATIONS_TABLE.txt`
4. **For this overview**: This file (README_USER_TODOS_AUDIT.md)

---

**Audit Date**: 2026-06-05  
**Scope**: All `.md` in `/workflows/`, all `.py` in `/scripts/`  
**Search Breadth**: Very thorough (25+ locations found)

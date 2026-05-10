# Prism Research System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `prism/` — an LLM-driven investment research system where Claude (in the chat window) follows markdown workflows to research industries/arenas/companies, producing 8 structured outputs viewable at `/prism` in the existing FastAPI web app.

**Architecture:** Three-layer separation: (1) `prism/scripts/` — deterministic Python, zero LLM calls, reads/writes YAML+markdown files; (2) `prism/workflows/` — markdown files Claude reads and follows step-by-step in the chat; (3) `app/routes/prism.py` + `app/templates/prism/` — read-only web views of topic state. All LLM work happens in the Claude dialog window, never in Python. Pattern mirrors the existing `.claude/skills/ingest/` skill.

**Tech Stack:** Python 3, pytest, FastAPI (existing app), Jinja2, PyYAML, `markdown` lib (all already in `requirements.txt`). No new dependencies.

---

## Constraints

- **Zero LLM calls in Python** — scripts only do file I/O, YAML parsing, path resolution
- **All paths absolute or resolved from `prism/scripts/` using `Path(__file__).resolve().parent.parent`**
- **Topic data lives at `prism/topics/{slug}/`** — not inside `app/` or existing dirs
- **Workflows are markdown instructions for Claude** — not code, not agents
- **Web is strictly read-only** — no forms, no writes via HTTP

---

## Directory Layout (final state)

```
prism/
├── __init__.py
├── scripts/
│   ├── __init__.py
│   ├── topic.py          # create/read/update topic.yaml
│   ├── manifest.py       # create/read/update manifest.yaml
│   └── outputs.py        # list outputs, staleness check
├── workflows/
│   ├── 00-research-topic.md
│   ├── 01-build-roadmap.md
│   ├── 02-gather-materials.md
│   ├── 03-extract-findings.md
│   ├── 04-synthesize/
│   │   ├── _shared.md
│   │   ├── 01-panorama.md
│   │   ├── 02-cycle.md
│   │   ├── 03-narrative.md
│   │   ├── 04-expectations.md
│   │   ├── 05-mirrors.md
│   │   ├── 06-risks.md
│   │   ├── 07-decision-kit.md
│   │   └── 08-feed.md
│   ├── 05-critic-review.md
│   ├── 06-daily-monitor.md
│   ├── 07-drilldown.md
│   └── 99-decision-record.md
├── templates/
│   ├── topic.yaml.tmpl
│   ├── roadmap.yaml.tmpl
│   └── manifest.yaml.tmpl
├── prompts/
│   ├── analyst_voice.md
│   └── output_quality_rubric.md
├── topics/               # user data, gitignored or committed per preference
│   └── {slug}/
│       ├── topic.yaml
│       ├── roadmap.yaml
│       ├── manifest.yaml
│       └── outputs/
│           ├── 01_business_panorama.md
│           ├── 02_cycle_positioning.md
│           ├── 03_narrative_ecology.md
│           ├── 04_implied_expectations.md
│           ├── 05_historical_mirrors.md
│           ├── 06_risk_blindspots.md
│           ├── 07_decision_kit.md
│           └── 08_living_feed.md
└── inbox/
    ├── auto/
    └── manual/
app/
├── config.py             # add PRISM_DIR
├── routes/prism.py       # new — /prism routes
└── templates/prism/
    ├── index.html        # new
    ├── detail.html       # new
    └── output.html       # new
.claude/skills/prism/
└── SKILL.md              # new
main.py                   # add prism router + nav entry
tests/
├── test_prism_scripts.py # new — topic.py / manifest.py / outputs.py
└── test_prism_routes.py  # new — /prism HTTP smoke tests
```

---

## topic.yaml Schema

Every topic lives at `prism/topics/{slug}/topic.yaml`:

```yaml
slug: cn-commercial-space
display_name: 中国商业航天
type: arena          # industry | arena | company
created: 2026-05-07T20:00:00+08:00
status: active       # active | paused | archived
stage: 00-init       # current workflow stage name
scope:
  geo: CN
  question: "中国商业航天有哪些投资机会"
  depth: deep        # quick | standard | deep
outputs_state:
  "01_business_panorama":
    version: 0
    last_updated: null
    status: pending   # pending | fresh | stale
  "02_cycle_positioning":
    version: 0
    last_updated: null
    status: pending
  "03_narrative_ecology":
    version: 0
    last_updated: null
    status: pending
  "04_implied_expectations":
    version: 0
    last_updated: null
    status: pending
  "05_historical_mirrors":
    version: 0
    last_updated: null
    status: pending
  "06_risk_blindspots":
    version: 0
    last_updated: null
    status: pending
  "07_decision_kit":
    version: 0
    last_updated: null
    status: pending
  "08_living_feed":
    version: 0
    last_updated: null
    status: pending
next_actions:
  - "运行 workflow 01-build-roadmap"
user_todos: []
monitoring:
  enabled: false
  cadence: daily
```

---

## Phase 0 — Python Scripts + Tests (Tasks 1–4)

### Task 1: Directory scaffold + `prism/__init__.py`

**Files:**
- Create: `prism/__init__.py`
- Create: `prism/scripts/__init__.py`
- Create: `prism/topics/.gitkeep`
- Create: `prism/inbox/auto/.gitkeep`
- Create: `prism/inbox/manual/.gitkeep`
- Create: `prism/workflows/.gitkeep` (placeholder — workflows come in Phase 3)
- Create: `tests/test_prism_scripts.py` (empty initially)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p /Users/yangqi/investing/prism/scripts
mkdir -p /Users/yangqi/investing/prism/workflows/04-synthesize
mkdir -p /Users/yangqi/investing/prism/templates
mkdir -p /Users/yangqi/investing/prism/prompts
mkdir -p /Users/yangqi/investing/prism/topics
mkdir -p /Users/yangqi/investing/prism/inbox/auto
mkdir -p /Users/yangqi/investing/prism/inbox/manual
```

- [ ] **Step 2: Create `prism/__init__.py`**

```python
```
(empty file)

- [ ] **Step 3: Create `prism/scripts/__init__.py`**

```python
```
(empty file)

- [ ] **Step 4: Create placeholder test file**

Create `tests/test_prism_scripts.py`:

```python
"""Tests for prism/scripts/ — topic, manifest, outputs helpers."""
```

- [ ] **Step 5: Create gitkeep files**

```bash
touch /Users/yangqi/investing/prism/topics/.gitkeep
touch /Users/yangqi/investing/prism/inbox/auto/.gitkeep
touch /Users/yangqi/investing/prism/inbox/manual/.gitkeep
```

- [ ] **Step 6: Verify structure**

```bash
find /Users/yangqi/investing/prism -type d | sort
```

Expected output:
```
/Users/yangqi/investing/prism
/Users/yangqi/investing/prism/inbox
/Users/yangqi/investing/prism/inbox/auto
/Users/yangqi/investing/prism/inbox/manual
/Users/yangqi/investing/prism/prompts
/Users/yangqi/investing/prism/scripts
/Users/yangqi/investing/prism/templates
/Users/yangqi/investing/prism/topics
/Users/yangqi/investing/prism/workflows
/Users/yangqi/investing/prism/workflows/04-synthesize
```

- [ ] **Step 7: Commit**

```bash
cd /Users/yangqi/investing
git add prism/ tests/test_prism_scripts.py
git commit -m "feat(prism): scaffold directory structure"
```

---

### Task 2: `prism/scripts/topic.py`

Handles creating, reading, and updating `topic.yaml` files. No LLM calls.

**Files:**
- Create: `prism/scripts/topic.py`
- Modify: `tests/test_prism_scripts.py`

**Key functions:**
- `topics_dir() -> Path` — returns `prism/topics/` resolved relative to script
- `create_topic(slug, display_name, topic_type, question, geo, depth) -> Path` — creates `prism/topics/{slug}/topic.yaml`, raises `FileExistsError` if already exists
- `read_topic(slug) -> dict` — reads and parses `topic.yaml`, raises `FileNotFoundError` if missing
- `update_topic(slug, **fields) -> None` — merges top-level fields into topic.yaml; for nested `outputs_state`, `next_actions`, `user_todos` use the dedicated helpers below
- `set_stage(slug, stage: str) -> None` — updates `stage` field
- `set_output_status(slug, output_key: str, status: str, version: int | None = None) -> None` — updates `outputs_state[output_key]` with status + last_updated timestamp + optional version bump
- `set_next_actions(slug, actions: list[str]) -> None`
- `set_user_todos(slug, todos: list[str]) -> None`
- `list_topics() -> list[dict]` — returns list of all topic dicts, sorted by `created` desc

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_prism_scripts.py` with:

```python
"""Tests for prism/scripts/ — topic, manifest, outputs helpers."""
from __future__ import annotations

import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# topic.py tests
# ---------------------------------------------------------------------------

@pytest.fixture
def topics_root(tmp_path, monkeypatch):
    """Redirect prism/scripts/topic.py to use tmp_path as the prism root."""
    import prism.scripts.topic as t
    monkeypatch.setattr(t, "_PRISM_ROOT", tmp_path)
    (tmp_path / "topics").mkdir()
    return tmp_path


def test_create_topic_writes_yaml(topics_root):
    from prism.scripts import topic as t

    path = t.create_topic(
        slug="cn-pet",
        display_name="中国宠物行业",
        topic_type="industry",
        question="中国宠物行业的投资机会在哪里",
        geo="CN",
        depth="deep",
    )

    assert path.exists()
    data = t.read_topic("cn-pet")
    assert data["slug"] == "cn-pet"
    assert data["display_name"] == "中国宠物行业"
    assert data["type"] == "industry"
    assert data["scope"]["geo"] == "CN"
    assert data["scope"]["depth"] == "deep"
    assert data["status"] == "active"
    assert data["stage"] == "00-init"
    # All 8 outputs present and pending
    assert len(data["outputs_state"]) == 8
    for v in data["outputs_state"].values():
        assert v["status"] == "pending"
        assert v["version"] == 0
        assert v["last_updated"] is None


def test_create_topic_raises_if_exists(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    with pytest.raises(FileExistsError):
        t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")


def test_read_topic_raises_if_missing(topics_root):
    from prism.scripts import topic as t

    with pytest.raises(FileNotFoundError):
        t.read_topic("nonexistent")


def test_set_stage(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    t.set_stage("cn-pet", "02-gather-materials")
    assert t.read_topic("cn-pet")["stage"] == "02-gather-materials"


def test_set_output_status(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    t.set_output_status("cn-pet", "01_business_panorama", "fresh", version=1)
    data = t.read_topic("cn-pet")
    out = data["outputs_state"]["01_business_panorama"]
    assert out["status"] == "fresh"
    assert out["version"] == 1
    assert out["last_updated"] is not None


def test_set_next_actions(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    t.set_next_actions("cn-pet", ["运行 workflow 02", "上传资料"])
    assert t.read_topic("cn-pet")["next_actions"] == ["运行 workflow 02", "上传资料"]


def test_set_user_todos(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    t.set_user_todos("cn-pet", ["下载年报"])
    assert t.read_topic("cn-pet")["user_todos"] == ["下载年报"]


def test_list_topics_returns_all(topics_root):
    from prism.scripts import topic as t

    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    t.create_topic("cn-space", "中国商业航天", "arena", "q2", "CN", "standard")
    topics = t.list_topics()
    slugs = [tp["slug"] for tp in topics]
    assert "cn-pet" in slugs
    assert "cn-space" in slugs
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/yangqi/investing && python -m pytest tests/test_prism_scripts.py -v 2>&1 | head -30
```

Expected: ImportError or ModuleNotFoundError for `prism.scripts.topic`

- [ ] **Step 3: Implement `prism/scripts/topic.py`**

```python
"""Create, read, and update topic.yaml files. Zero LLM calls."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

_PRISM_ROOT = Path(__file__).resolve().parent.parent

_OUTPUT_KEYS = [
    "01_business_panorama",
    "02_cycle_positioning",
    "03_narrative_ecology",
    "04_implied_expectations",
    "05_historical_mirrors",
    "06_risk_blindspots",
    "07_decision_kit",
    "08_living_feed",
]


def _topics_dir() -> Path:
    return _PRISM_ROOT / "topics"


def _topic_path(slug: str) -> Path:
    return _topics_dir() / slug / "topic.yaml"


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_topic(
    slug: str,
    display_name: str,
    topic_type: str,
    question: str,
    geo: str,
    depth: str,
) -> Path:
    path = _topic_path(slug)
    if path.exists():
        raise FileExistsError(f"Topic already exists: {slug}")
    data = {
        "slug": slug,
        "display_name": display_name,
        "type": topic_type,
        "created": _now_iso(),
        "status": "active",
        "stage": "00-init",
        "scope": {
            "geo": geo,
            "question": question,
            "depth": depth,
        },
        "outputs_state": {
            key: {"version": 0, "last_updated": None, "status": "pending"}
            for key in _OUTPUT_KEYS
        },
        "next_actions": ["运行 workflow 01-build-roadmap"],
        "user_todos": [],
        "monitoring": {"enabled": False, "cadence": "daily"},
    }
    _write_yaml(path, data)
    # Create outputs/ directory
    (path.parent / "outputs").mkdir(exist_ok=True)
    return path


def read_topic(slug: str) -> dict:
    path = _topic_path(slug)
    if not path.exists():
        raise FileNotFoundError(f"Topic not found: {slug}")
    return _read_yaml(path)


def update_topic(slug: str, **fields) -> None:
    data = read_topic(slug)
    data.update(fields)
    _write_yaml(_topic_path(slug), data)


def set_stage(slug: str, stage: str) -> None:
    update_topic(slug, stage=stage)


def set_output_status(slug: str, output_key: str, status: str, version: int | None = None) -> None:
    data = read_topic(slug)
    entry = data["outputs_state"].setdefault(output_key, {"version": 0, "last_updated": None, "status": "pending"})
    entry["status"] = status
    entry["last_updated"] = _now_iso()
    if version is not None:
        entry["version"] = version
    _write_yaml(_topic_path(slug), data)


def set_next_actions(slug: str, actions: list[str]) -> None:
    update_topic(slug, next_actions=actions)


def set_user_todos(slug: str, todos: list[str]) -> None:
    update_topic(slug, user_todos=todos)


def list_topics() -> list[dict]:
    root = _topics_dir()
    if not root.exists():
        return []
    results = []
    for d in root.iterdir():
        path = d / "topic.yaml"
        if path.is_file():
            try:
                results.append(_read_yaml(path))
            except Exception:
                pass
    results.sort(key=lambda t: t.get("created", ""), reverse=True)
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/yangqi/investing && python -m pytest tests/test_prism_scripts.py -v -k "topic"
```

Expected: all 8 topic tests PASS

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/topic.py tests/test_prism_scripts.py
git commit -m "feat(prism): topic.py — create/read/update topic.yaml"
```

---

### Task 3: `prism/scripts/manifest.py`

Handles `prism/topics/{slug}/manifest.yaml` — the material inventory for a topic.

**manifest.yaml schema:**
```yaml
slug: cn-pet
updated: 2026-05-07T20:00:00Z
materials:
  - id: "mat-001"
    filename: "广发_宠物行业深度_2024.md"
    source_type: "sell-side-note"   # sell-side-note | annual-report | web-article | manual-note
    added: "2026-05-07T20:00:00Z"
    processed: false   # true after extract-findings runs on it
    notes: ""
```

**Key functions:**
- `create_manifest(slug) -> Path` — creates empty manifest for existing topic
- `read_manifest(slug) -> dict` — reads manifest.yaml
- `add_material(slug, filename, source_type, notes="") -> str` — adds entry, returns generated `id`
- `mark_processed(slug, mat_id: str) -> None`
- `list_unprocessed(slug) -> list[dict]`
- `material_count(slug) -> dict` — returns `{"total": N, "processed": N, "unprocessed": N}`

**Files:**
- Create: `prism/scripts/manifest.py`
- Modify: `tests/test_prism_scripts.py` (append)

- [ ] **Step 1: Append manifest tests to `tests/test_prism_scripts.py`**

```python
# ---------------------------------------------------------------------------
# manifest.py tests
# ---------------------------------------------------------------------------

@pytest.fixture
def manifest_root(tmp_path, monkeypatch):
    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    monkeypatch.setattr(t, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(m, "_PRISM_ROOT", tmp_path)
    (tmp_path / "topics").mkdir()
    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    return tmp_path


def test_create_manifest(manifest_root):
    from prism.scripts import manifest as m

    path = m.create_manifest("cn-pet")
    assert path.exists()
    data = m.read_manifest("cn-pet")
    assert data["slug"] == "cn-pet"
    assert data["materials"] == []


def test_add_material_returns_id(manifest_root):
    from prism.scripts import manifest as m

    m.create_manifest("cn-pet")
    mat_id = m.add_material("cn-pet", "report.md", "sell-side-note")
    assert mat_id.startswith("mat-")
    data = m.read_manifest("cn-pet")
    assert len(data["materials"]) == 1
    assert data["materials"][0]["filename"] == "report.md"
    assert data["materials"][0]["processed"] is False


def test_mark_processed(manifest_root):
    from prism.scripts import manifest as m

    m.create_manifest("cn-pet")
    mat_id = m.add_material("cn-pet", "report.md", "sell-side-note")
    m.mark_processed("cn-pet", mat_id)
    assert m.read_manifest("cn-pet")["materials"][0]["processed"] is True


def test_list_unprocessed(manifest_root):
    from prism.scripts import manifest as m

    m.create_manifest("cn-pet")
    m.add_material("cn-pet", "a.md", "sell-side-note")
    id2 = m.add_material("cn-pet", "b.md", "annual-report")
    m.mark_processed("cn-pet", id2)
    unprocessed = m.list_unprocessed("cn-pet")
    assert len(unprocessed) == 1
    assert unprocessed[0]["filename"] == "a.md"


def test_material_count(manifest_root):
    from prism.scripts import manifest as m

    m.create_manifest("cn-pet")
    id1 = m.add_material("cn-pet", "a.md", "sell-side-note")
    m.add_material("cn-pet", "b.md", "sell-side-note")
    m.mark_processed("cn-pet", id1)
    counts = m.material_count("cn-pet")
    assert counts == {"total": 2, "processed": 1, "unprocessed": 1}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/yangqi/investing && python -m pytest tests/test_prism_scripts.py -v -k "manifest" 2>&1 | head -20
```

Expected: ImportError for `prism.scripts.manifest`

- [ ] **Step 3: Implement `prism/scripts/manifest.py`**

```python
"""Material manifest for a research topic. Zero LLM calls."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

_PRISM_ROOT = Path(__file__).resolve().parent.parent


def _topics_dir() -> Path:
    return _PRISM_ROOT / "topics"


def _manifest_path(slug: str) -> Path:
    return _topics_dir() / slug / "manifest.yaml"


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_manifest(slug: str) -> Path:
    path = _manifest_path(slug)
    data = {"slug": slug, "updated": _now_iso(), "materials": []}
    _write_yaml(path, data)
    return path


def read_manifest(slug: str) -> dict:
    path = _manifest_path(slug)
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found for topic: {slug}")
    return _read_yaml(path)


def add_material(slug: str, filename: str, source_type: str, notes: str = "") -> str:
    data = read_manifest(slug)
    mat_id = f"mat-{uuid.uuid4().hex[:6]}"
    data["materials"].append({
        "id": mat_id,
        "filename": filename,
        "source_type": source_type,
        "added": _now_iso(),
        "processed": False,
        "notes": notes,
    })
    data["updated"] = _now_iso()
    _write_yaml(_manifest_path(slug), data)
    return mat_id


def mark_processed(slug: str, mat_id: str) -> None:
    data = read_manifest(slug)
    for mat in data["materials"]:
        if mat["id"] == mat_id:
            mat["processed"] = True
            break
    data["updated"] = _now_iso()
    _write_yaml(_manifest_path(slug), data)


def list_unprocessed(slug: str) -> list[dict]:
    return [m for m in read_manifest(slug)["materials"] if not m["processed"]]


def material_count(slug: str) -> dict:
    materials = read_manifest(slug)["materials"]
    processed = sum(1 for m in materials if m["processed"])
    return {"total": len(materials), "processed": processed, "unprocessed": len(materials) - processed}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/yangqi/investing && python -m pytest tests/test_prism_scripts.py -v -k "manifest"
```

Expected: all 5 manifest tests PASS

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/manifest.py tests/test_prism_scripts.py
git commit -m "feat(prism): manifest.py — material inventory for topics"
```

---

### Task 4: `prism/scripts/outputs.py`

Queries the state of the 8 outputs for a topic, for use by the web layer.

**Key functions:**
- `list_outputs(slug) -> list[dict]` — returns list of 8 output dicts, each with keys: `key`, `label`, `status`, `version`, `last_updated`, `file_exists`
- `read_output_html(slug, output_key) -> str` — reads the markdown output file and converts to HTML; raises `FileNotFoundError` if not yet generated

**Files:**
- Create: `prism/scripts/outputs.py`
- Modify: `tests/test_prism_scripts.py` (append)

- [ ] **Step 1: Append outputs tests**

```python
# ---------------------------------------------------------------------------
# outputs.py tests
# ---------------------------------------------------------------------------

_OUTPUT_LABELS = {
    "01_business_panorama": "商业全景",
    "02_cycle_positioning": "周期定位",
    "03_narrative_ecology": "叙事谱系",
    "04_implied_expectations": "隐含预期与观点光谱",
    "05_historical_mirrors": "历史镜像",
    "06_risk_blindspots": "风险盲点",
    "07_decision_kit": "决策辅助",
    "08_living_feed": "信息流时间线",
}


@pytest.fixture
def outputs_root(tmp_path, monkeypatch):
    import prism.scripts.topic as t
    import prism.scripts.outputs as o
    monkeypatch.setattr(t, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(o, "_PRISM_ROOT", tmp_path)
    (tmp_path / "topics").mkdir()
    t.create_topic("cn-pet", "中国宠物", "industry", "q", "CN", "deep")
    return tmp_path


def test_list_outputs_returns_8(outputs_root):
    from prism.scripts import outputs as o

    result = o.list_outputs("cn-pet")
    assert len(result) == 8
    keys = [r["key"] for r in result]
    assert keys == list(_OUTPUT_LABELS.keys())


def test_list_outputs_file_exists_false_initially(outputs_root):
    from prism.scripts import outputs as o

    result = o.list_outputs("cn-pet")
    for r in result:
        assert r["file_exists"] is False
        assert r["status"] == "pending"


def test_list_outputs_file_exists_true_after_write(outputs_root, tmp_path):
    from prism.scripts import outputs as o
    import prism.scripts.topic as t

    # Simulate Claude writing the output file
    out_path = tmp_path / "topics" / "cn-pet" / "outputs" / "01_business_panorama.md"
    out_path.write_text("# 商业全景\n\n内容。", encoding="utf-8")
    t.set_output_status("cn-pet", "01_business_panorama", "fresh", version=1)

    result = o.list_outputs("cn-pet")
    panorama = next(r for r in result if r["key"] == "01_business_panorama")
    assert panorama["file_exists"] is True
    assert panorama["status"] == "fresh"


def test_read_output_html_converts_markdown(outputs_root, tmp_path):
    from prism.scripts import outputs as o

    out_path = tmp_path / "topics" / "cn-pet" / "outputs" / "01_business_panorama.md"
    out_path.write_text("# 标题\n\n**加粗**文本。", encoding="utf-8")

    html = o.read_output_html("cn-pet", "01_business_panorama")
    assert "<h1>" in html
    assert "<strong>" in html


def test_read_output_html_raises_if_missing(outputs_root):
    from prism.scripts import outputs as o

    with pytest.raises(FileNotFoundError):
        o.read_output_html("cn-pet", "01_business_panorama")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/yangqi/investing && python -m pytest tests/test_prism_scripts.py -v -k "outputs" 2>&1 | head -20
```

- [ ] **Step 3: Implement `prism/scripts/outputs.py`**

```python
"""Query output state for topics. Zero LLM calls."""
from __future__ import annotations

from pathlib import Path

import markdown as _md
import yaml

_PRISM_ROOT = Path(__file__).resolve().parent.parent

_OUTPUT_KEYS_LABELS = [
    ("01_business_panorama", "商业全景"),
    ("02_cycle_positioning", "周期定位"),
    ("03_narrative_ecology", "叙事谱系"),
    ("04_implied_expectations", "隐含预期与观点光谱"),
    ("05_historical_mirrors", "历史镜像"),
    ("06_risk_blindspots", "风险盲点"),
    ("07_decision_kit", "决策辅助"),
    ("08_living_feed", "信息流时间线"),
]


def _topic_dir(slug: str) -> Path:
    return _PRISM_ROOT / "topics" / slug


def _read_topic_yaml(slug: str) -> dict:
    path = _topic_dir(slug) / "topic.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Topic not found: {slug}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def list_outputs(slug: str) -> list[dict]:
    data = _read_topic_yaml(slug)
    outputs_state = data.get("outputs_state", {})
    result = []
    for key, label in _OUTPUT_KEYS_LABELS:
        state = outputs_state.get(key, {"version": 0, "last_updated": None, "status": "pending"})
        out_path = _topic_dir(slug) / "outputs" / f"{key}.md"
        result.append({
            "key": key,
            "label": label,
            "status": state.get("status", "pending"),
            "version": state.get("version", 0),
            "last_updated": state.get("last_updated"),
            "file_exists": out_path.is_file(),
        })
    return result


def read_output_html(slug: str, output_key: str) -> str:
    out_path = _topic_dir(slug) / "outputs" / f"{output_key}.md"
    if not out_path.is_file():
        raise FileNotFoundError(f"Output not yet generated: {output_key}")
    raw = out_path.read_text(encoding="utf-8")
    return _md.markdown(raw, extensions=["tables", "fenced_code", "toc"])
```

- [ ] **Step 4: Run all prism script tests**

```bash
cd /Users/yangqi/investing && python -m pytest tests/test_prism_scripts.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/outputs.py tests/test_prism_scripts.py
git commit -m "feat(prism): outputs.py — list/read topic outputs"
```

---

## Phase 1 — Web Dashboard (Tasks 5–10)

### Task 5: Add `PRISM_DIR` to `app/config.py`

**Files:**
- Modify: `app/config.py`

- [ ] **Step 1: Read current config**

Read `/Users/yangqi/investing/app/config.py` — verify last line before adding.

- [ ] **Step 2: Add `PRISM_DIR`**

In `app/config.py`, after the existing path constants (after `STATIC_DIR = ...`), add:

```python
PRISM_DIR = BASE_PATH / "prism"
```

- [ ] **Step 3: Verify import works**

```bash
cd /Users/yangqi/investing && python -c "from app.config import PRISM_DIR; print(PRISM_DIR)"
```

Expected: prints the absolute path ending in `/prism`

- [ ] **Step 4: Commit**

```bash
git add app/config.py
git commit -m "feat(prism): add PRISM_DIR to app/config"
```

---

### Task 6: `app/routes/prism.py`

Three routes:
- `GET /prism` → index (list all topics)
- `GET /prism/{slug}` → topic dashboard
- `GET /prism/{slug}/output/{output_key}` → rendered markdown output

**Files:**
- Create: `app/routes/prism.py`
- Create: `tests/test_prism_routes.py`

- [ ] **Step 1: Write the failing route tests**

Create `tests/test_prism_routes.py`:

```python
"""Smoke tests for /prism routes."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def prism_client(tmp_path, monkeypatch):
    """App client with isolated prism dir and minimal topic fixture."""
    repo = Path(__file__).resolve().parent.parent

    # Copy templates so Jinja2 can render
    shutil.copytree(repo / "app" / "templates", tmp_path / "app_templates")

    from app import config as cfg
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "APP_TEMPLATES_DIR", tmp_path / "app_templates")
    monkeypatch.setattr(cfg, "STATIC_DIR", tmp_path / "static")
    monkeypatch.setattr(cfg, "PRISM_DIR", tmp_path / "prism")

    # Patch other dirs so home route doesn't crash
    for attr in ("COMPANIES_DIR", "INDUSTRIES_DIR", "ARENAS_DIR",
                 "WATCHLIST_DIR", "PORTFOLIO_DIR", "MACRO_DIR",
                 "JOURNAL_DIR", "DATA_DIR"):
        d = tmp_path / attr.lower()
        d.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(cfg, attr, d)
    monkeypatch.setattr(cfg, "FINANCIALS_DB", tmp_path / "data" / "financials.db")
    (tmp_path / "portfolio" / "rules.md").write_text("# r\n")
    (tmp_path / "journal" / "decisions").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cfg, "CONTROLLED_VOCAB_DIR", repo / "controlled-vocab")

    # Patch prism scripts to use tmp_path
    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    import prism.scripts.outputs as o
    monkeypatch.setattr(t, "_PRISM_ROOT", tmp_path / "prism")
    monkeypatch.setattr(m, "_PRISM_ROOT", tmp_path / "prism")
    monkeypatch.setattr(o, "_PRISM_ROOT", tmp_path / "prism")

    # Create a fixture topic
    prism_topics = tmp_path / "prism" / "topics"
    prism_topics.mkdir(parents=True)
    t.create_topic("cn-pet", "中国宠物行业", "industry", "宠物投资机会", "CN", "deep")
    m.create_manifest("cn-pet")

    from main import app
    return TestClient(app)


def test_prism_index_200(prism_client):
    r = prism_client.get("/prism")
    assert r.status_code == 200
    assert "中国宠物行业" in r.text


def test_prism_detail_200(prism_client):
    r = prism_client.get("/prism/cn-pet")
    assert r.status_code == 200
    assert "cn-pet" in r.text


def test_prism_detail_404_for_unknown(prism_client):
    r = prism_client.get("/prism/does-not-exist")
    assert r.status_code == 404


def test_prism_output_404_before_generated(prism_client):
    r = prism_client.get("/prism/cn-pet/output/01_business_panorama")
    assert r.status_code == 404


def test_prism_output_200_after_file_written(prism_client, tmp_path):
    out_path = tmp_path / "prism" / "topics" / "cn-pet" / "outputs" / "01_business_panorama.md"
    out_path.write_text("# 商业全景\n\n内容。", encoding="utf-8")
    r = prism_client.get("/prism/cn-pet/output/01_business_panorama")
    assert r.status_code == 200
    assert "商业全景" in r.text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/yangqi/investing && python -m pytest tests/test_prism_routes.py -v 2>&1 | head -20
```

Expected: ImportError or 404 from missing router

- [ ] **Step 3: Implement `app/routes/prism.py`**

```python
"""Prism research system views — /prism."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR, PRISM_DIR
from prism.scripts import outputs as outputs_io
from prism.scripts import topic as topic_io
from prism.scripts import manifest as manifest_io

router = APIRouter(prefix="/prism", tags=["prism"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def prism_index(request: Request):
    topics = topic_io.list_topics()
    return templates.TemplateResponse(
        request,
        "prism/index.html",
        {"topics": topics},
    )


@router.get("/{slug}")
def prism_detail(request: Request, slug: str):
    try:
        topic = topic_io.read_topic(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r} not found")

    outputs = outputs_io.list_outputs(slug)

    try:
        manifest = manifest_io.read_manifest(slug)
        mat_counts = manifest_io.material_count(slug)
    except FileNotFoundError:
        manifest = {"materials": []}
        mat_counts = {"total": 0, "processed": 0, "unprocessed": 0}

    return templates.TemplateResponse(
        request,
        "prism/detail.html",
        {
            "topic": topic,
            "outputs": outputs,
            "manifest": manifest,
            "mat_counts": mat_counts,
        },
    )


@router.get("/{slug}/output/{output_key}")
def prism_output(request: Request, slug: str, output_key: str):
    try:
        topic = topic_io.read_topic(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r} not found")

    try:
        html_body = outputs_io.read_output_html(slug, output_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Output {output_key!r} not yet generated")

    outputs = outputs_io.list_outputs(slug)
    current_output = next((o for o in outputs if o["key"] == output_key), None)

    return templates.TemplateResponse(
        request,
        "prism/output.html",
        {
            "topic": topic,
            "output_key": output_key,
            "current_output": current_output,
            "html_body": html_body,
            "outputs": outputs,
        },
    )
```

- [ ] **Step 4: Run tests — expect template errors (templates don't exist yet)**

```bash
cd /Users/yangqi/investing && python -m pytest tests/test_prism_routes.py -v 2>&1 | head -30
```

Expected: TemplateNotFound errors — that's fine, templates come next

- [ ] **Step 5: Commit route**

```bash
git add app/routes/prism.py tests/test_prism_routes.py
git commit -m "feat(prism): prism router — /prism index/detail/output routes"
```

---

### Task 7: `app/templates/prism/index.html`

- [ ] **Step 1: Create `app/templates/prism/` directory**

```bash
mkdir -p /Users/yangqi/investing/app/templates/prism
```

- [ ] **Step 2: Create `app/templates/prism/index.html`**

```html
{% extends "base.html" %}
{% block title %}研究主题{% endblock %}
{% block content %}
<h1>研究主题</h1>
<p class="hint">所有 Prism 研究主题。在对话窗口说「研究 X」开启新主题。</p>

{% if topics %}
<table class="data-table">
  <thead>
    <tr>
      <th>主题</th>
      <th>类型</th>
      <th>阶段</th>
      <th>产出进度</th>
      <th>状态</th>
      <th>创建</th>
    </tr>
  </thead>
  <tbody>
  {% for t in topics %}
    {% set fresh_count = t.outputs_state.values() | selectattr('status', 'equalto', 'fresh') | list | length %}
    {% set total_count = t.outputs_state | length %}
    <tr>
      <td><a href="/prism/{{ t.slug }}">{{ t.display_name or t.slug }}</a></td>
      <td class="hint">{{ t.type }}</td>
      <td class="hint">{{ t.stage }}</td>
      <td>
        <span class="progress-label">{{ fresh_count }}/{{ total_count }}</span>
      </td>
      <td>
        <span class="badge badge-{{ t.status }}">{{ t.status }}</span>
      </td>
      <td class="hint">{{ (t.created or '')[:10] }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
<p class="hint">暂无研究主题。在对话窗口说「研究中国宠物行业」开启第一个主题。</p>
{% endif %}

<style>
  .data-table { border-collapse: collapse; width: 100%; margin: 1em 0; }
  .data-table th, .data-table td { padding: 0.5em 0.8em; text-align: left; border-bottom: 1px solid #eee; }
  .data-table th { font-weight: 600; color: #555; }
  .badge { font-size: 0.75em; padding: 0.2em 0.5em; border-radius: 3px; }
  .badge-active { background: #e6f4ea; color: #2d7a3a; }
  .badge-paused { background: #fff3e0; color: #b45309; }
  .badge-archived { background: #f1f5f9; color: #888; }
  .hint { color: #888; font-size: 0.85em; }
  .progress-label { font-size: 0.85em; color: #555; }
</style>
{% endblock %}
```

- [ ] **Step 3: Verify route test passes**

```bash
cd /Users/yangqi/investing && python -m pytest tests/test_prism_routes.py::test_prism_index_200 -v
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add app/templates/prism/index.html
git commit -m "feat(prism): index template — topic list"
```

---

### Task 8: `app/templates/prism/detail.html`

- [ ] **Step 1: Create `app/templates/prism/detail.html`**

```html
{% extends "base.html" %}
{% block title %}{{ topic.display_name or topic.slug }} · 研究主题{% endblock %}
{% block content %}
<div class="prism-header">
  <h1>{{ topic.display_name or topic.slug }}</h1>
  <span class="badge badge-{{ topic.status }}">{{ topic.status }}</span>
  <span class="hint"> · {{ topic.type }} · {{ topic.scope.geo }}</span>
</div>

<p class="scope-question">研究问题：<em>{{ topic.scope.question }}</em></p>

<div class="prism-columns">

  <!-- Left: 8 outputs -->
  <section class="outputs-panel">
    <h2>8 份产出</h2>
    <table class="data-table">
      <thead>
        <tr><th>产出</th><th>版本</th><th>状态</th><th>更新时间</th></tr>
      </thead>
      <tbody>
      {% for out in outputs %}
        <tr>
          <td>
            {% if out.file_exists %}
              <a href="/prism/{{ topic.slug }}/output/{{ out.key }}">{{ out.label }}</a>
            {% else %}
              <span class="hint">{{ out.label }}</span>
            {% endif %}
          </td>
          <td class="hint">v{{ out.version }}</td>
          <td>
            <span class="badge-small badge-{{ out.status }}">{{ out.status }}</span>
          </td>
          <td class="hint">{{ (out.last_updated or '')[:10] or '—' }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </section>

  <!-- Right: next actions + todos -->
  <aside class="actions-panel">
    <section>
      <h3>下一步（系统建议）</h3>
      {% if topic.next_actions %}
      <ul>
        {% for action in topic.next_actions %}
        <li>{{ action }}</li>
        {% endfor %}
      </ul>
      {% else %}
      <p class="hint">暂无建议</p>
      {% endif %}
    </section>

    <section>
      <h3>你需要做的事</h3>
      {% if topic.user_todos %}
      <ul>
        {% for todo in topic.user_todos %}
        <li>{{ todo }}</li>
        {% endfor %}
      </ul>
      {% else %}
      <p class="hint">暂无待办</p>
      {% endif %}
    </section>

    <section>
      <h3>资料库</h3>
      <p>共 {{ mat_counts.total }} 份 · 已处理 {{ mat_counts.processed }} · 未处理 {{ mat_counts.unprocessed }}</p>
      {% if manifest.materials %}
      <ul class="material-list">
        {% for mat in manifest.materials %}
        <li>
          <span class="{% if mat.processed %}processed{% else %}unprocessed{% endif %}">
            {{ mat.filename }}
          </span>
          <span class="hint"> · {{ mat.source_type }}</span>
        </li>
        {% endfor %}
      </ul>
      {% else %}
      <p class="hint">暂无资料。运行 workflow 02-gather-materials 后自动更新。</p>
      {% endif %}
    </section>

    <section>
      <h3>当前阶段</h3>
      <p class="hint stage-badge">{{ topic.stage }}</p>
    </section>
  </aside>

</div>

<a href="/prism" class="back-link">← 所有主题</a>

<style>
  .prism-header { display: flex; align-items: center; gap: 0.7em; margin-bottom: 0.3em; }
  .scope-question { color: #444; margin: 0.5em 0 1.5em; }
  .prism-columns { display: grid; grid-template-columns: 1fr 320px; gap: 2em; align-items: start; }
  @media (max-width: 900px) { .prism-columns { grid-template-columns: 1fr; } }
  .outputs-panel h2, .actions-panel h3 { margin: 0 0 0.5em; font-size: 1em; color: #333; }
  .actions-panel { border-left: 2px solid #eee; padding-left: 1.5em; }
  .actions-panel section { margin-bottom: 1.5em; }
  .actions-panel ul { padding-left: 1.2em; margin: 0.3em 0; }
  .actions-panel li { margin: 0.3em 0; font-size: 0.9em; }
  .material-list { padding-left: 1em; }
  .material-list li { margin: 0.25em 0; font-size: 0.85em; }
  .processed { color: #888; }
  .unprocessed { color: #222; font-weight: 500; }
  .stage-badge { font-family: monospace; background: #f4f4f4; padding: 0.2em 0.5em; border-radius: 3px; display: inline-block; }
  .badge { font-size: 0.75em; padding: 0.2em 0.5em; border-radius: 3px; }
  .badge-small { font-size: 0.72em; padding: 0.15em 0.4em; border-radius: 3px; }
  .badge-active, .badge-fresh { background: #e6f4ea; color: #2d7a3a; }
  .badge-paused, .badge-stale { background: #fff3e0; color: #b45309; }
  .badge-archived, .badge-pending { background: #f1f5f9; color: #888; }
  .data-table { border-collapse: collapse; width: 100%; }
  .data-table th, .data-table td { padding: 0.45em 0.7em; border-bottom: 1px solid #eee; font-size: 0.9em; }
  .data-table th { font-weight: 600; color: #555; }
  .hint { color: #888; font-size: 0.85em; }
  .back-link { display: inline-block; margin-top: 2em; color: #666; font-size: 0.9em; }
</style>
{% endblock %}
```

- [ ] **Step 2: Run detail route tests**

```bash
cd /Users/yangqi/investing && python -m pytest tests/test_prism_routes.py::test_prism_detail_200 tests/test_prism_routes.py::test_prism_detail_404_for_unknown -v
```

Expected: both PASS

- [ ] **Step 3: Commit**

```bash
git add app/templates/prism/detail.html
git commit -m "feat(prism): detail template — topic dashboard"
```

---

### Task 9: `app/templates/prism/output.html`

- [ ] **Step 1: Create `app/templates/prism/output.html`**

```html
{% extends "base.html" %}
{% block title %}{{ current_output.label if current_output else output_key }} · {{ topic.display_name }}{% endblock %}
{% block content %}
<nav class="breadcrumb">
  <a href="/prism">研究主题</a> /
  <a href="/prism/{{ topic.slug }}">{{ topic.display_name or topic.slug }}</a> /
  <span>{{ current_output.label if current_output else output_key }}</span>
</nav>

<div class="output-layout">
  <!-- Sidebar: output nav -->
  <aside class="output-nav">
    <h3>8 份产出</h3>
    <ul>
    {% for out in outputs %}
      <li class="{% if out.key == output_key %}active{% endif %}">
        {% if out.file_exists %}
          <a href="/prism/{{ topic.slug }}/output/{{ out.key }}">
            {{ out.label }}
            {% if out.status == 'stale' %}<span class="stale-dot" title="需要更新">⚠</span>{% endif %}
          </a>
        {% else %}
          <span class="hint">{{ out.label }}</span>
        {% endif %}
      </li>
    {% endfor %}
    </ul>
    <p class="hint nav-back"><a href="/prism/{{ topic.slug }}">← 返回仪表盘</a></p>
  </aside>

  <!-- Main content -->
  <article class="output-body">
    {% if current_output %}
    <div class="output-meta hint">
      版本 v{{ current_output.version }} ·
      {% if current_output.last_updated %}更新于 {{ current_output.last_updated[:10] }}{% endif %}
      {% if current_output.status == 'stale' %}<span class="stale-label"> · 已过期，建议重新生成</span>{% endif %}
    </div>
    {% endif %}

    <div class="markdown-body">
      {{ html_body | safe }}
    </div>
  </article>
</div>

<style>
  .breadcrumb { font-size: 0.85em; color: #888; margin-bottom: 1.5em; }
  .breadcrumb a { color: #555; }
  .output-layout { display: grid; grid-template-columns: 200px 1fr; gap: 2em; align-items: start; }
  @media (max-width: 800px) { .output-layout { grid-template-columns: 1fr; } }
  .output-nav h3 { font-size: 0.85em; color: #888; margin: 0 0 0.5em; text-transform: uppercase; letter-spacing: 0.05em; }
  .output-nav ul { list-style: none; padding: 0; margin: 0; }
  .output-nav li { margin: 0.3em 0; font-size: 0.9em; padding: 0.25em 0.4em; border-radius: 3px; }
  .output-nav li.active { background: #f0f0f0; font-weight: 600; }
  .output-nav li.active a { color: #111; }
  .nav-back { margin-top: 1em; }
  .output-meta { margin-bottom: 1em; }
  .stale-dot { color: #b45309; }
  .stale-label { color: #b45309; }
  .markdown-body h1 { font-size: 1.4em; margin-top: 0; }
  .markdown-body h2 { font-size: 1.1em; margin-top: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 0.2em; }
  .markdown-body table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.9em; }
  .markdown-body th, .markdown-body td { border: 1px solid #ddd; padding: 0.4em 0.7em; }
  .markdown-body th { background: #f8f8f8; font-weight: 600; }
  .markdown-body code { background: #f4f4f4; padding: 0.1em 0.3em; border-radius: 3px; font-size: 0.9em; }
  .markdown-body pre { background: #f4f4f4; padding: 1em; border-radius: 4px; overflow-x: auto; }
  .markdown-body blockquote { border-left: 3px solid #ddd; margin: 0; padding-left: 1em; color: #666; }
  .hint { color: #888; font-size: 0.85em; }
</style>
{% endblock %}
```

- [ ] **Step 2: Run remaining route tests**

```bash
cd /Users/yangqi/investing && python -m pytest tests/test_prism_routes.py -v
```

Expected: all 5 route tests PASS

- [ ] **Step 3: Commit**

```bash
git add app/templates/prism/output.html
git commit -m "feat(prism): output template — rendered markdown output"
```

---

### Task 10: Wire prism router into `main.py` + add nav link in `base.html`

**Files:**
- Modify: `main.py`
- Modify: `app/templates/base.html`

- [ ] **Step 1: Read `main.py` imports block**

Read `/Users/yangqi/investing/main.py` lines 1-40 to see exact import block.

- [ ] **Step 2: Add prism router import to `main.py`**

After the line `from app.routes.mineru import router as mineru_router`, add:

```python
from app.routes.prism import router as prism_router
```

- [ ] **Step 3: Register router in `main.py`**

After the line `app.include_router(mineru_router)`, add:

```python
app.include_router(prism_router)
```

- [ ] **Step 4: Add nav link to `base.html`**

In `app/templates/base.html`, after the line `{{ _navlink('/insights', '备忘录') }}`, add:

```html
    {{ _navlink('/prism', '研究') }}
```

- [ ] **Step 5: Run smoke test**

```bash
cd /Users/yangqi/investing && python -m pytest tests/test_prism_routes.py -v
```

Expected: all PASS

- [ ] **Step 6: Run full test suite to catch regressions**

```bash
cd /Users/yangqi/investing && python -m pytest --tb=short -q 2>&1 | tail -20
```

Expected: same pass/fail as before (no new failures)

- [ ] **Step 7: Commit**

```bash
git add main.py app/templates/base.html
git commit -m "feat(prism): wire /prism router + nav link"
```

---

## Phase 2 — Skill + Entry Workflow (Tasks 11–12)

### Task 11: `.claude/skills/prism/SKILL.md`

This skill file tells Claude how to handle "研究 X" requests. When the user says something like "研究中国宠物行业" or "研究商业航天", Claude invokes this skill.

**Files:**
- Create: `.claude/skills/prism/SKILL.md`

- [ ] **Step 1: Create directory**

```bash
mkdir -p /Users/yangqi/investing/.claude/skills/prism
```

- [ ] **Step 2: Create `.claude/skills/prism/SKILL.md`**

```markdown
---
name: prism
description: LLM 驱动的投资研究系统。触发词：研究 X / prism / 开始研究 / 研究主题 / 推进研究 / 更新产出 / 查看研究进度。用于对行业、竞技场、公司开展结构化投资研究，产出 8 份标准产出，可在 /prism 查看。
allowed-tools: Bash Read Write
---

# Prism — 投资研究系统

## 触发场景与路由

| 用户说 | 执行 |
|--------|------|
| 「研究 X」/ 「开始研究 X」 | 读 `prism/workflows/00-research-topic.md` |
| 「prism 推进 {slug}」/ 「继续研究 {slug}」 | 读 `topic.yaml` 判断当前 stage，跳转对应 workflow |
| 「生成产出 {output}」/ 「更新 {slug} 的 {output}」 | 读对应 `prism/workflows/04-synthesize/{N}-{name}.md` |
| 「评审 {slug}」 | 读 `prism/workflows/05-critic-review.md` |
| 「监控 {slug}」 | 读 `prism/workflows/06-daily-monitor.md` |
| 「深挖 {slug} 的 {问题}」 | 读 `prism/workflows/07-drilldown.md` |
| 「记录决策 {slug}」 | 读 `prism/workflows/99-decision-record.md` |
| 「查看 {slug} 进度」 | 直接读 `topic.yaml` 输出当前状态表格 |

## Prism Root

所有 topic 数据在 `prism/topics/{slug}/`：
- `topic.yaml` — 主状态文件
- `manifest.yaml` — 资料清单
- `outputs/` — 8 份产出 markdown

## Python Scripts（仅用于 CRUD，零 LLM 调用）

```bash
# 创建 topic
python -c "from prism.scripts.topic import create_topic; create_topic('slug', '显示名', 'industry', '研究问题', 'CN', 'deep')"

# 读 topic
python -c "from prism.scripts.topic import read_topic; import json; print(json.dumps(read_topic('slug'), ensure_ascii=False, indent=2))"

# 更新阶段
python -c "from prism.scripts.topic import set_stage; set_stage('slug', '02-gather-materials')"

# 更新产出状态
python -c "from prism.scripts.topic import set_output_status; set_output_status('slug', '01_business_panorama', 'fresh', version=1)"

# 更新 next_actions
python -c "from prism.scripts.topic import set_next_actions; set_next_actions('slug', ['下一步内容'])"

# 更新 user_todos
python -c "from prism.scripts.topic import set_user_todos; set_user_todos('slug', ['用户待办'])"

# 创建 manifest
python -c "from prism.scripts.manifest import create_manifest; create_manifest('slug')"

# 添加资料
python -c "from prism.scripts.manifest import add_material; add_material('slug', 'filename.md', 'sell-side-note')"

# 标记已处理
python -c "from prism.scripts.manifest import mark_processed; mark_processed('slug', 'mat-abc123')"
```

## 关键规则

1. **所有 LLM 推断在对话里做** — Python 脚本只做文件读写
2. **每步结束后更新 topic.yaml** — 用脚本写 stage / next_actions / user_todos
3. **产出写入 `prism/topics/{slug}/outputs/{key}.md`**，然后调脚本更新状态
4. **Web 自动反映最新状态** — 无需手动刷新配置
5. **资料放 `prism/inbox/manual/`**（用户手动）或 `prism/inbox/auto/`（脚本下载）
```

- [ ] **Step 3: Verify file created**

```bash
cat /Users/yangqi/investing/.claude/skills/prism/SKILL.md | head -5
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/prism/SKILL.md
git commit -m "feat(prism): SKILL.md — skill routing for research triggers"
```

---

### Task 12: `prism/workflows/00-research-topic.md`

This is the entry workflow. Claude reads it when the user says "研究 X".

**Files:**
- Create: `prism/workflows/00-research-topic.md`

- [ ] **Step 1: Create `prism/workflows/00-research-topic.md`**

```markdown
# Workflow 00 — 开启新研究主题

**触发**：用户说「研究 X」或「开始研究 X」  
**产出**：创建 `prism/topics/{slug}/topic.yaml` + `manifest.yaml`，Web 页面 /prism/{slug} 可访问

---

## Step 1：确认研究对象

向用户确认以下信息（如果用户没说清楚则 AskUserQuestion）：

1. **研究对象名称**（中文，例如「中国宠物行业」「中国商业航天」「宁德时代」）
2. **研究类型**（industry / arena / company）
   - industry：整个行业（宠物、储能、机器人）
   - arena：细分竞技场（宠物食品、人形机器人执行器）
   - company：单家公司
3. **核心研究问题**（例如「中国宠物行业哪些细分赛道值得投资」）
4. **研究深度**（quick = 1-2 天 / standard = 1 周 / deep = 持续跟踪）
5. **地理范围**（CN / US / GLOBAL）

如果用户直接说「研究中国宠物行业」，可以推断：type=industry, geo=CN，然后只确认研究问题和深度。

---

## Step 2：生成 slug

slug 规则：
- 全小写，连字符分隔
- 格式：`{geo}-{keywords}`
- 示例：`cn-pet-industry`、`cn-commercial-space`、`cn-catl`
- 不超过 30 字符

在对话里显示 slug，等用户确认或修改。

---

## Step 3：检查是否已存在

```bash
ls prism/topics/ 2>/dev/null
```

如果已有同名 slug，告知用户并询问：
- 继续已有研究（运行 workflow 推进）
- 还是创建新研究（slug 加后缀，如 `cn-pet-industry-2`）

---

## Step 4：创建 topic

```bash
python -c "
from prism.scripts.topic import create_topic
create_topic(
    slug='{slug}',
    display_name='{display_name}',
    topic_type='{type}',
    question='{question}',
    geo='{geo}',
    depth='{depth}',
)
print('创建成功')
"
```

```bash
python -c "
from prism.scripts.manifest import create_manifest
create_manifest('{slug}')
print('manifest 创建成功')
"
```

---

## Step 5：基于训练知识做初步定向

**注意**：这一步 100% 使用 LLM 训练知识，不需要外部资料。目的是帮用户快速建立研究框架。

产出以下三部分（直接在对话里输出，不写文件）：

### 5.1 领域概览（3-5 句话）
- 这个行业/赛道/公司是什么
- 当前处于什么发展阶段
- 市场规模量级

### 5.2 关键研究维度（5-8 个问题）
列出要深度研究这个主题，最关键的 5-8 个问题。例如：
- 谁是核心受益者，谁是受损方？
- 增长的核心驱动力是什么，是结构性还是周期性？
- 当前市场共识是什么，哪里可能有分歧？
- 风险清单里最容易被低估的是什么？
- 有哪些历史类比案例？

### 5.3 资料获取建议（用户需要收集什么）
按优先级列出 5-10 份关键资料，包括：
- 哪些卖方研报（机构、标题方向）
- 哪些公司年报/季报
- 哪些行业协会数据
- 哪些政策文件
- 是否有关键的英文资料

---

## Step 6：更新 topic 状态

```bash
python -c "
from prism.scripts.topic import set_stage, set_next_actions, set_user_todos
set_stage('{slug}', '01-roadmap-pending')
set_next_actions('{slug}', [
    '运行 workflow 01-build-roadmap：制定详细研究路线图',
    '收集初始资料后运行 workflow 02-gather-materials',
])
set_user_todos('{slug}', {user_todos_from_step_5_3})
"
```

---

## Step 7：告知用户

输出：
```
✅ 研究主题「{display_name}」已创建

Slug: {slug}
Web 地址: http://localhost:8000/prism/{slug}

下一步：
1. 在对话里说「prism 推进 {slug}」继续制定研究路线图
2. 或者先收集资料放入 prism/inbox/manual/ 后说「prism 推进 {slug}」

你需要做的事：
{user_todos_list}
```
```

- [ ] **Step 2: Commit**

```bash
git add prism/workflows/00-research-topic.md
git commit -m "feat(prism): workflow 00 — open new research topic"
```

---

## Phase 3 — Research Workflows (Tasks 13–22)

> **Note for implementer:** Workflows are markdown instruction files for Claude — not Python code. Each file follows the same pattern: numbered steps Claude must follow in sequence, with bash commands for file I/O and explicit instruction blocks for LLM reasoning.

### Task 13: `prism/workflows/01-build-roadmap.md`

**Files:**
- Create: `prism/workflows/01-build-roadmap.md`
- Create: `prism/templates/roadmap.yaml.tmpl`

- [ ] **Step 1: Create `prism/templates/roadmap.yaml.tmpl`**

```yaml
# roadmap.yaml — 研究路线图 (由 workflow 01 生成)
slug: {slug}
created: {created}
learning_track:
  l1_orientation:     # 概览层：是什么，多大，谁玩
    - question: ""
      source_hint: ""
  l2_history:         # 历史层：怎么来的，周期节奏
    - question: ""
      source_hint: ""
  l3_debates:         # 争议层：分歧在哪，各方逻辑
    - question: ""
      source_hint: ""
  l4_hunting:         # 狩猎层：哪里有错误定价
    - question: ""
      source_hint: ""
material_priority:
  tier1:              # 必读，研究不可缺
    - title: ""
      type: ""        # sell-side / annual-report / policy / data
      source: ""
      why: ""
  tier2:              # 补充，有最好
    - title: ""
      type: ""
      source: ""
      why: ""
  tier3:              # 可选
    - title: ""
      type: ""
key_risks_to_monitor: []
analogies_to_study: []
```

- [ ] **Step 2: Create `prism/workflows/01-build-roadmap.md`**

```markdown
# Workflow 01 — 制定研究路线图

**触发**：stage=01-roadmap-pending 或用户说「制定路线图」  
**前置**：topic.yaml 已存在  
**产出**：`prism/topics/{slug}/roadmap.yaml`

---

## Step 1：读取 topic

```bash
python -c "
import json
from prism.scripts.topic import read_topic
print(json.dumps(read_topic('{slug}'), ensure_ascii=False, indent=2))
"
```

确认研究问题、类型、地理范围、深度。

---

## Step 2：制定学习轨道（L1→L4 问题树）

基于训练知识，为这个研究主题制定四层问题：

**L1 定向层**（3-4 个问题）：搞清楚「是什么」
- 这个行业的边界在哪里？怎么定义市场？
- 主要参与者有哪些（上游/中游/下游）？
- 市场规模多大？主要增长驱动是什么？

**L2 历史层**（3-4 个问题）：搞清楚「怎么来的」
- 过去 5-10 年经历了哪几个发展阶段？
- 有没有明显的周期性规律？
- 关键拐点（政策/技术/需求）是什么时候？

**L3 争议层**（4-5 个问题）：搞清楚「分歧在哪」
- 多空双方的核心分歧是什么？
- 市场共识是什么，哪里可能是错的？
- 最容易被忽视的风险是什么？

**L4 狩猎层**（3-5 个问题）：找错误定价
- 如果市场错了，错在哪里？
- 哪个时间节点能验证或证伪？
- 什么样的新信息会改变当前判断？

---

## Step 3：制定资料优先级

根据研究深度，列出三档资料：

**Tier 1（必读）**：对研究结论影响最大、最难被替代的 3-5 份
**Tier 2（补充）**：有助于验证但非必须的 3-5 份  
**Tier 3（可选）**：深度研究时可参考的

每份资料说明：标题方向、类型（研报/年报/政策/数据）、从哪里找、为什么重要。

---

## Step 4：识别历史类比

列出 2-3 个值得研究的历史类比案例，格式：
- 案例名称（国家+行业+时间段）
- 类比逻辑（哪里像）
- 类比局限（哪里不像）

---

## Step 5：写入 roadmap.yaml

复制 `prism/templates/roadmap.yaml.tmpl`，填入上面分析内容，写入：
`prism/topics/{slug}/roadmap.yaml`

---

## Step 6：更新 topic 状态

```bash
python -c "
from prism.scripts.topic import set_stage, set_next_actions, set_user_todos
set_stage('{slug}', '02-gathering')
set_next_actions('{slug}', [
    '收集 Tier 1 资料后运行 workflow 02-gather-materials 登记资料',
    '有资料可以处理时运行 workflow 03-extract-findings',
])
set_user_todos('{slug}', [
    '按 roadmap.yaml 的 tier1 清单收集资料，放入 prism/inbox/manual/',
    '如需自动下载可在对话里说「下载 {slug} 的 cninfo 年报」',
])
"
```

---

## Step 7：汇报

在对话输出：

```
✅ 研究路线图已生成 → prism/topics/{slug}/roadmap.yaml

L4 狩猎问题（最重要）：
{list L4 questions}

Tier 1 必读资料：
{list tier 1 items}

你现在需要做的事：
1. 收集上述资料放入 prism/inbox/manual/
2. 完成后说「prism 推进 {slug}」继续

Web 地址：http://localhost:8000/prism/{slug}
```
```

- [ ] **Step 3: Commit**

```bash
git add prism/workflows/01-build-roadmap.md prism/templates/roadmap.yaml.tmpl
git commit -m "feat(prism): workflow 01 — build research roadmap"
```

---

### Task 14: `prism/workflows/02-gather-materials.md`

**Files:**
- Create: `prism/workflows/02-gather-materials.md`
- Create: `prism/templates/manifest.yaml.tmpl`

- [ ] **Step 1: Create `prism/templates/manifest.yaml.tmpl`**

```yaml
# manifest.yaml — 资料清单 (由 workflow 02 维护)
slug: {slug}
updated: {updated}
materials: []
# 每条记录格式：
# - id: "mat-xxxxxx"
#   filename: "xxx.md"
#   source_type: "sell-side-note"  # sell-side-note|annual-report|web-article|manual-note|policy
#   added: "2026-05-07T..."
#   processed: false
#   notes: ""
```

- [ ] **Step 2: Create `prism/workflows/02-gather-materials.md`**

```markdown
# Workflow 02 — 登记资料到 Manifest

**触发**：用户上传了新资料，或说「登记资料」  
**前置**：topic.yaml 和 manifest.yaml 已存在  
**产出**：更新 `prism/topics/{slug}/manifest.yaml`

---

## Step 1：检查 inbox 有什么新资料

```bash
ls prism/inbox/manual/
ls prism/inbox/auto/
```

列出所有文件，记录文件名。

---

## Step 2：对每份新资料，判断 source_type

按文件名和内容（如有）判断类型：
- `sell-side-note`：卖方研报（某机构某日期某标题）
- `annual-report`：年报 / 半年报 / 10-K / 20-F
- `web-article`：网页抓取的新闻/文章
- `manual-note`：用户自己写的笔记
- `policy`：政策文件/监管文件

---

## Step 3：读当前 manifest

```bash
python -c "
import json
from prism.scripts.manifest import read_manifest
print(json.dumps(read_manifest('{slug}'), ensure_ascii=False, indent=2))
"
```

检查哪些文件已经在 manifest 里，避免重复登记。

---

## Step 4：逐一登记新资料

对每份新文件执行：

```bash
python -c "
from prism.scripts.manifest import add_material
mat_id = add_material(
    slug='{slug}',
    filename='{filename}',
    source_type='{source_type}',
    notes='{notes}',
)
print(f'已登记：{filename} → {mat_id}')
"
```

---

## Step 5：移动文件到 topic 目录（可选）

如果资料需要长期关联到这个 topic，可以移动：

```bash
mkdir -p prism/topics/{slug}/materials/
cp prism/inbox/manual/{filename} prism/topics/{slug}/materials/
```

> 注意：移动后原 inbox 文件可删除，manifest 记录 filename 用相对于 materials/ 的路径。

---

## Step 6：更新 topic 状态

```bash
python -c "
from prism.scripts.topic import set_stage, set_next_actions
from prism.scripts.manifest import material_count
counts = material_count('{slug}')
set_stage('{slug}', '03-extracting' if counts['unprocessed'] > 0 else '02-gathering')
set_next_actions('{slug}', [
    f'已有 {counts[\"unprocessed\"]} 份资料未处理，运行 workflow 03-extract-findings',
])
"
```

---

## Step 7：汇报

```
✅ manifest 已更新

新登记资料：{list}
当前资料库：共 N 份（已处理 X，未处理 Y）

下一步：
说「prism 推进 {slug}」或「提取发现 {slug}」继续
```
```

- [ ] **Step 3: Commit**

```bash
git add prism/workflows/02-gather-materials.md prism/templates/manifest.yaml.tmpl
git commit -m "feat(prism): workflow 02 — gather materials into manifest"
```

---

### Task 15: `prism/workflows/03-extract-findings.md`

This workflow is where Claude reads unprocessed materials and extracts key findings — the most LLM-intensive step.

**Files:**
- Create: `prism/workflows/03-extract-findings.md`

- [ ] **Step 1: Create `prism/workflows/03-extract-findings.md`**

```markdown
# Workflow 03 — 从资料中提取发现

**触发**：有未处理资料，或说「提取发现」  
**前置**：manifest.yaml 有 processed=false 的条目  
**产出**：在 `prism/topics/{slug}/outputs/` 中积累发现笔记（按资料 ID）

---

## Step 1：读取未处理资料清单

```bash
python -c "
import json
from prism.scripts.manifest import list_unprocessed
items = list_unprocessed('{slug}')
for i in items:
    print(f'{i[\"id\"]} | {i[\"filename\"]} | {i[\"source_type\"]}')
"
```

---

## Step 2：对每份资料，执行以下提取

每次处理一份资料：

### 2.1 读取资料内容

```bash
cat prism/topics/{slug}/materials/{filename}
# 或者
cat prism/inbox/manual/{filename}
```

如果文件是 PDF，要求用户先通过 MinerU 转换为 markdown。

### 2.2 提取结构化发现（LLM 推断，在对话里完成）

按以下框架提取：

**A. 数据点与事实**（有明确数字/时间/主体的陈述）
- 格式：「[来源] [时间] [主体] [指标] = [数值]，原文：xxx」
- 最多提取 10 条最重要的

**B. 叙事与观点**（分析师/管理层的判断、预测、逻辑）
- 格式：「[来源] [多空方向] 核心逻辑：xxx，依据：xxx」
- 最多 5 条

**C. 反常识/意外信息**（与市场共识相悖的内容）
- 格式：「市场预期：xxx，本文表明：xxx，差异原因可能：xxx」

**D. 资料质量评估**
- 数据新鲜度（最新数据截至几时）
- 分析师倾向（偏多/偏空/中性）
- 可信度（高/中/低，原因）
- 与已有发现是否矛盾

### 2.3 写入发现笔记

写入 `prism/topics/{slug}/outputs/findings_{mat_id}.md`：

```markdown
---
mat_id: {mat_id}
filename: {filename}
source_type: {source_type}
extracted: {timestamp}
quality: high|medium|low
bias: bull|bear|neutral
---

## 数据点与事实

{bullet list}

## 叙事与观点

{bullet list}

## 反常信息

{bullet list or "无"}

## 质量备注

{notes}
```

---

## Step 3：标记资料已处理

```bash
python -c "
from prism.scripts.manifest import mark_processed
mark_processed('{slug}', '{mat_id}')
print('已标记处理完成')
"
```

对每份处理完的资料执行一次。

---

## Step 4：完成所有资料后更新状态

```bash
python -c "
from prism.scripts.topic import set_stage, set_next_actions
from prism.scripts.manifest import material_count
counts = material_count('{slug}')
if counts['unprocessed'] == 0:
    set_stage('{slug}', '04-synthesizing')
    set_next_actions('{slug}', [
        '所有资料已处理完毕，可以生成产出',
        '说「生成产出 {slug} 商业全景」开始生成第一份产出',
        '或说「prism 推进 {slug}」按顺序生成所有 8 份产出',
    ])
else:
    set_next_actions('{slug}', [
        f'还有 {counts[\"unprocessed\"]} 份资料未处理',
    ])
"
```

---

## Step 5：汇报

```
✅ 资料提取完成

已处理：{N} 份
关键发现（跨所有资料）：
- 最重要的 3-5 条数据点
- 主要叙事方向
- 最值得注意的反常信息

下一步：
说「生成产出 {slug} 商业全景」或「prism 推进 {slug}」
```
```

- [ ] **Step 2: Commit**

```bash
git add prism/workflows/03-extract-findings.md
git commit -m "feat(prism): workflow 03 — extract findings from materials"
```

---

### Task 16: `prism/workflows/04-synthesize/_shared.md`

Shared preamble all 8 synthesize workflows import by reference.

**Files:**
- Create: `prism/workflows/04-synthesize/_shared.md`

- [ ] **Step 1: Create `prism/workflows/04-synthesize/_shared.md`**

```markdown
# 产出合成 — 共享前置规范

每份产出工作流开始前必须完成以下检查，违反则停止并告知用户。

## 前置检查

```bash
python -c "
import json
from prism.scripts.topic import read_topic
from prism.scripts.manifest import material_count
t = read_topic('{slug}')
counts = material_count('{slug}')
print('stage:', t['stage'])
print('materials:', json.dumps(counts))
print('question:', t['scope']['question'])
"
```

- **资料量**：至少 3 份已处理资料，否则提示「资料不足，建议先收集更多资料」
- **训练知识依赖**：每份产出明确标注哪些来自训练知识，哪些来自资料

## 写入规范

输出文件路径：`prism/topics/{slug}/outputs/{output_key}.md`

每份产出 markdown 必须包含：
1. YAML frontmatter（slug, output_key, version, generated）
2. 正文内容（按各 workflow 规定）
3. 末尾：`## 信息来源` — 列出使用的资料（mat_id + 文件名）和训练知识比例估计

## 更新状态（每份产出完成后必须执行）

```bash
python -c "
from prism.scripts.topic import set_output_status
set_output_status(
    slug='{slug}',
    output_key='{output_key}',
    status='fresh',
    version={new_version},
)
print('状态已更新')
"
```

## 质量检验

产出完成后自问：
- [ ] 有具体数据/时间/主体，不只是泛泛之词
- [ ] 多空观点都有呈现，不只说一边
- [ ] 有明确的「哪里可能是错的」
- [ ] 训练知识和资料来源有区分标注
- [ ] 字数适当（800-2000字为宜，过长反而难用）
```

- [ ] **Step 2: Commit**

```bash
git add prism/workflows/04-synthesize/_shared.md
git commit -m "feat(prism): synthesize shared pre-check rules"
```

---

### Task 17: `prism/workflows/04-synthesize/01-panorama.md`

Output 01 — 商业全景 (Business Panorama). ~60% training knowledge.

**Files:**
- Create: `prism/workflows/04-synthesize/01-panorama.md`

- [ ] **Step 1: Create `prism/workflows/04-synthesize/01-panorama.md`**

```markdown
# 产出 01 — 商业全景 (Business Panorama)

**定位**：给完全不了解这个行业的人，用 1 份文档解释「这个生意是怎么运转的」  
**训练知识比例**：约 60%（结合资料补充最新数据）  
**产出文件**：`prism/topics/{slug}/outputs/01_business_panorama.md`

---

## Step 0：前置检查

参见 `_shared.md` 前置检查，执行完再继续。

---

## Step 1：读取 findings

```bash
ls prism/topics/{slug}/outputs/findings_*.md
```

读取所有 findings 文件，提炼与「商业模式」相关的数据点。

---

## Step 2：撰写商业全景

按以下结构写 markdown（每节 3-8 句话或要点）：

### 2.1 行业定义与边界
- 这个行业做什么，提供什么产品/服务
- 边界在哪里（哪些算这个行业，哪些不算）
- 关键词/标准分类（SIC/GICS/SW）

### 2.2 市场规模与结构
- 当前市场规模（总量 + 增速），数据年份
- 国内/海外分布（如相关）
- CR3/CR5 集中度（如有数据）

### 2.3 价值链解析
用简图（文本版）展示上中下游：
```
原材料供应商 → [核心环节：XXX] → 品牌商/系统集成商 → 终端用户
```
每个环节说明：谁在做、毛利率水平、竞争格局

### 2.4 商业模式类型
- 主要商业模式（To B / To C / 平台 / 订阅等）
- 收入结构（产品 vs 服务，一次性 vs 经常性）
- 盈利驱动因子（量 × 价 × 成本）

### 2.5 需求端分析
- 核心客户群体
- 购买决策驱动因素
- 需求增长的核心驱动（人口/政策/技术/消费升级）

### 2.6 供给端分析
- 主要参与者类型（国央企/民企/外资）
- 进入壁垒（技术/资本/资质/品牌/规模）
- 产能/供给增速

### 2.7 竞争格局
- 格局类型（高度集中 / 分散 / 两极化）
- 核心竞争要素（不超过 3 个）
- 行业龙头与其优势来源

### 2.8 行业发展阶段
- 当前所处阶段（导入期/成长期/成熟期/衰退期）
- 判断依据（增速/格局/技术成熟度）

---

## Step 3：写入文件

写入 `prism/topics/{slug}/outputs/01_business_panorama.md`：

```markdown
---
slug: {slug}
output_key: 01_business_panorama
version: {N}
generated: {timestamp}
---

# 商业全景：{display_name}

> 生成于 {date}，训练知识占比约 60%，资料更新截至 {latest_data_date}

## 行业定义与边界
{content}

## 市场规模与结构
{content}

## 价值链解析
{content}

## 商业模式
{content}

## 需求端分析
{content}

## 供给端分析
{content}

## 竞争格局
{content}

## 发展阶段
{content}

## 信息来源
- 训练知识（约 60%）
- {mat_id}: {filename}（数据更新）
```

---

## Step 4：更新状态

```bash
python -c "
from prism.scripts.topic import set_output_status, read_topic
t = read_topic('{slug}')
current_v = t['outputs_state']['01_business_panorama']['version']
set_output_status('{slug}', '01_business_panorama', 'fresh', version=current_v+1)
print('状态已更新')
"
```

---

## Step 5：汇报

```
✅ 商业全景已生成 → v{N}

Web 查看：http://localhost:8000/prism/{slug}/output/01_business_panorama

关键数据点：
- 市场规模：{X}
- 增速：{Y}
- 集中度：CR3={Z}

下一步：说「生成产出 {slug} 周期定位」继续
```
```

- [ ] **Step 2: Commit**

```bash
git add prism/workflows/04-synthesize/01-panorama.md
git commit -m "feat(prism): synthesize workflow 01 — business panorama"
```

---

### Task 18: `prism/workflows/04-synthesize/02-cycle.md`

Output 02 — 周期定位 (Cycle Positioning). ~70% training knowledge.

**Files:**
- Create: `prism/workflows/04-synthesize/02-cycle.md`

- [ ] **Step 1: Create `prism/workflows/04-synthesize/02-cycle.md`**

```markdown
# 产出 02 — 周期定位 (Cycle Positioning)

**定位**：判断「这个行业现在在周期的哪个位置」，以及「接下来 12-24 个月的方向」  
**训练知识比例**：约 70%（历史类比靠训练，当前定位靠资料）  
**产出文件**：`prism/topics/{slug}/outputs/02_cycle_positioning.md`

---

## Step 0：前置检查（见 _shared.md）

---

## Step 1：读取 findings 中的周期相关信息

重点找：库存数据、价格数据、产能利用率、订单/出货比、ROE 趋势。

---

## Step 2：撰写周期定位

### 2.1 行业周期类型
判断这个行业的主要周期驱动：
- **需求周期**：跟随终端需求（消费/资本开支/政策）
- **产能周期**：扩产→供给过剩→出清→再扩产
- **库存周期**：主动补库/被动补库/主动去库/被动去库
- **技术周期**：新技术替代旧技术的 S 曲线节奏
- 通常是多重周期叠加，说明各周期的主次

### 2.2 历史周期复盘（训练知识为主）
过去 10 年经历了哪几轮完整周期？
- 时间范围
- 触发因素
- 持续时长
- 峰谷幅度（价格/量/ROE 变化）
- 每轮周期的结束信号是什么

### 2.3 当前周期定位
基于资料中的数据，当前处于：
- [ ] 底部（库存低 / 价格见底 / 产能出清）
- [ ] 复苏早期（订单回升 / 价格企稳 / 盈利改善）
- [ ] 上行中期（量价齐升 / 产能扩张开始）
- [ ] 顶部迹象（库存积累 / 价格见顶 / 新产能涌入）
- [ ] 下行（供给过剩 / 价格下行 / 盈利收缩）

关键数据支撑（来自资料）：
| 指标 | 当前值 | 历史均值 | 信号 |
|------|--------|----------|------|
| 库存天数 | | | |
| 价格同比 | | | |
| 产能利用率 | | | |
| ROE | | | |

### 2.4 未来 12-24 个月展望
- 最可能的情景（60% 概率）：方向 + 主要驱动
- 上行情景（20%）：什么条件触发，幅度
- 下行情景（20%）：什么条件触发，幅度
- 关键验证节点（什么数据/时间点会确认哪个情景）

### 2.5 对投资的含义
- 从周期角度看，当前是适合建仓/持仓/减仓/观望的哪个阶段
- 周期定位最大的不确定性是什么

---

## Step 3：写入文件

写入 `prism/topics/{slug}/outputs/02_cycle_positioning.md`（格式同产出 01，含 frontmatter + 信息来源）

---

## Step 4：更新状态（见 _shared.md）

output_key = `02_cycle_positioning`

---

## Step 5：汇报

```
✅ 周期定位已生成 → v{N}
当前判断：{一句话定位}
关键验证节点：{时间/数据}
Web 查看：http://localhost:8000/prism/{slug}/output/02_cycle_positioning
```
```

- [ ] **Step 2: Commit**

```bash
git add prism/workflows/04-synthesize/02-cycle.md
git commit -m "feat(prism): synthesize workflow 02 — cycle positioning"
```

---

### Task 19: `prism/workflows/04-synthesize/03-narrative.md`

Output 03 — 叙事谱系 (Narrative Ecology). ~40% training knowledge.

**Files:**
- Create: `prism/workflows/04-synthesize/03-narrative.md`

- [ ] **Step 1: Create `prism/workflows/04-synthesize/03-narrative.md`**

```markdown
# 产出 03 — 叙事谱系 (Narrative Ecology)

**定位**：市场上有哪些不同的叙事框架在竞争，各自的逻辑和证据是什么  
**训练知识比例**：约 40%（叙事需要从资料中提取，训练知识提供框架）  
**产出文件**：`prism/topics/{slug}/outputs/03_narrative_ecology.md`

---

## Step 0：前置检查（见 _shared.md）

---

## Step 1：从 findings 中提取叙事材料

重点提取：分析师的核心逻辑、管理层的战略叙事、产业链反馈、政策方向。

---

## Step 2：撰写叙事谱系

### 2.1 主流叙事（当前市场最常见的 2-3 个框架）

对每个叙事：
- **叙事标题**（一句话概括）
- **核心逻辑**（3-5 句话）
- **主要支持者**（哪类机构/分析师在讲这个故事）
- **关键证据**（什么数据在支撑）
- **脆弱点**（什么情况会打破这个叙事）

### 2.2 边缘叙事（少数派/反共识的框架）

对每个边缘叙事：
- **叙事标题**
- **核心逻辑**
- **为什么市场不接受**（认知偏差？信息缺失？还是确实错了？）
- **如果它是对的，意味着什么**

### 2.3 叙事演化轨迹

过去 1-2 年，主流叙事是怎么演变的？
- 时间轴上的关键叙事转折点
- 什么事件/数据触发了叙事切换
- 当前叙事是否稳固，还是正在转变中

### 2.4 叙事与估值的关系

当前主流叙事暗示了什么样的估值逻辑？
- 市场用什么框架在给这个行业/公司定价
- 估值框架本身有什么假设，这些假设是否合理

### 2.5 叙事风险

哪些信息/事件会造成叙事突然切换？
- 最危险的叙事风险（小概率大影响）
- 最可能的叙事迭代方向

---

## Step 3：写入文件 + 更新状态（同 01/02 格式）

output_key = `03_narrative_ecology`

---

## Step 4：汇报

```
✅ 叙事谱系已生成 → v{N}
当前主流叙事：{一句话}
最值得关注的边缘叙事：{一句话}
```
```

- [ ] **Step 2: Commit**

```bash
git add prism/workflows/04-synthesize/03-narrative.md
git commit -m "feat(prism): synthesize workflow 03 — narrative ecology"
```

---

### Task 20: `prism/workflows/04-synthesize/04-expectations.md`

Output 04 — 隐含预期与观点光谱. ~50% training knowledge. **Most actionable output.**

**Files:**
- Create: `prism/workflows/04-synthesize/04-expectations.md`

- [ ] **Step 1: Create `prism/workflows/04-synthesize/04-expectations.md`**

```markdown
# 产出 04 — 隐含预期与观点光谱 (Implied Expectations & View Spectrum)

**定位**：反推市场当前价格隐含了什么预期，然后构建从极度乐观到极度悲观的完整观点谱系  
**训练知识比例**：约 50%（估值框架来自训练，当前数据来自资料）  
**产出文件**：`prism/topics/{slug}/outputs/04_implied_expectations.md`  
**重要性**：这是 8 份产出中对投资决策最直接有用的一份

---

## Step 0：前置检查（见 _shared.md）

至少需要：当前股价/估值数据、行业/公司盈利预测数据（来自资料）

---

## Step 1：提取估值相关数据

从 findings 中提取：
- 当前 PE/PB/EV/EBITDA/PS
- 卖方一致预期（营收增速、净利润增速、毛利率）
- 历史估值区间（均值 ± 1σ）

---

## Step 2：反推隐含预期

**核心问题：「当前价格假设了什么必须为真？」**

步骤：
1. 以当前价格和市盈率，反推市场隐含的 3 年 CAGR
2. 对比历史增速区间，判断这个隐含增速是偏高/中性/偏低
3. 反推隐含的利润率假设
4. 反推隐含的终值估值假设

输出格式：
```
当前价格 = {P}，当前 PE = {X}x
隐含 3 年净利润 CAGR = {Y}%（历史均值 {Z}%，历史最高 {H}%）
隐含净利率 = {M}%（当前 {N}%）
市场似乎在假设：{一句话描述隐含假设}
这个假设属于：悲观 / 中性 / 乐观 / 极度乐观
```

---

## Step 3：构建观点光谱（5级）

**Super-bull（超级乐观）**
- 核心逻辑：
- 关键假设（3个）：
- 支持证据：
- 概率估计：X%
- 如果正确，潜在回报：+Y%

**Bull（乐观）**
- 核心逻辑：
- 关键假设：
- 支持证据：
- 概率估计：
- 如果正确，潜在回报：

**Base（中性/基准）**
- 核心逻辑：
- 关键假设：
- 支持证据：
- 概率估计：
- 潜在回报：

**Bear（悲观）**
- 核心逻辑：
- 关键假设：
- 支持证据（或：为什么这个情景可能发生）：
- 概率估计：
- 如果发生，潜在下跌：

**Super-bear（超级悲观）**
- 核心逻辑：
- 关键假设：
- 为什么市场低估这个风险：
- 概率估计：
- 尾部风险幅度：

---

## Step 4：识别关键分歧点

**「多空双方最核心的一个分歧是什么？」**

- 分歧焦点（一句话）：
- 多方认为：...，因为...
- 空方认为：...，因为...
- 解决这个分歧需要什么信息/等待什么时间节点？
- 我自己当前的判断（如果资料足够支撑）：

---

## Step 5：写入文件 + 更新状态

output_key = `04_implied_expectations`

---

## Step 6：汇报

```
✅ 隐含预期与观点光谱已生成 → v{N}

当前市场隐含假设：{一句话}
这个假设属于：{悲观/中性/乐观}
核心多空分歧：{一句话}
我的初步判断（供参考）：{一句话，标明信心度}
```
```

- [ ] **Step 2: Commit**

```bash
git add prism/workflows/04-synthesize/04-expectations.md
git commit -m "feat(prism): synthesize workflow 04 — implied expectations"
```

---

### Task 21: Remaining 4 synthesize workflows (05-08)

**Files:**
- Create: `prism/workflows/04-synthesize/05-mirrors.md`
- Create: `prism/workflows/04-synthesize/06-risks.md`
- Create: `prism/workflows/04-synthesize/07-decision-kit.md`
- Create: `prism/workflows/04-synthesize/08-feed.md`

- [ ] **Step 1: Create `prism/workflows/04-synthesize/05-mirrors.md`**

```markdown
# 产出 05 — 历史镜像 (Historical Mirrors)

**定位**：找出与当前情景最相似的历史案例，从中提炼类比与警示  
**训练知识比例**：约 90%（LLM 超能力所在，几乎不依赖资料）  
**产出文件**：`prism/topics/{slug}/outputs/05_historical_mirrors.md`

---

## Step 0：前置检查（见 _shared.md）

---

## Step 1：识别 3-5 个历史类比

类比维度：产业结构（供需格局）、技术替代曲线、政策驱动周期、估值叙事泡沫、地理市场复制。

对每个类比案例：

### 案例名称：{国家} {行业/公司} {年代}

**类比逻辑**（哪里最像）：
- 供需结构
- 政策环境
- 估值叙事
- 参与者行为

**类比局限**（哪里不像，为什么不能完全照搬）：
- 结构差异
- 时代背景差异

**历史结果**：
- 发生了什么
- 峰值/谷值时间与幅度
- 触发拐点的事件

**对当前的启示**：
- 如果历史重演，当前应该…
- 历史中哪个信号最早出现，现在是否已经出现

---

## Step 2：类比综合与当前定位

综合所有类比案例，现在最像哪个历史时刻？
- 最相似的时刻：{描述}
- 相似度：高/中/低，原因：
- 最大的差异点（不能类比的地方）：

---

## Step 3：写入文件 + 更新状态

output_key = `05_historical_mirrors`

---

## Step 4：汇报

```
✅ 历史镜像已生成 → v{N}
最佳类比：{案例名称} ({相似度})
最重要的历史教训：{一句话}
```
```

- [ ] **Step 2: Create `prism/workflows/04-synthesize/06-risks.md`**

```markdown
# 产出 06 — 风险盲点 (Risk & Blind Spots)

**定位**：系统梳理已知风险，并刻意寻找市场可能低估/忽视的风险  
**训练知识比例**：约 60%  
**产出文件**：`prism/topics/{slug}/outputs/06_risk_blindspots.md`

---

## Step 0：前置检查（见 _shared.md）

---

## Step 1：从 findings 提取已知风险

从资料中找出分析师/管理层明确提及的风险。

---

## Step 2：撰写风险盲点

### 2.1 市场已知风险（共识）

列出 3-5 个市场普遍知道并已在定价中的风险：
- 风险名称
- 市场的定价方式（折价多少 / 用什么情景概率）
- 是否被充分定价（过度/适当/不足）

### 2.2 潜在盲点风险（刻意寻找）

**用以下视角主动寻找被低估的风险：**

A. **二阶效应**：显而易见的风险引发的不那么显而易见的连锁反应
B. **叙事掩盖**：当前乐观叙事是否让人忽略了某些负面信号
C. **结构性脆弱**：商业模式或竞争格局中固有的但被习以为常的弱点
D. **政策尾部风险**：小概率但大影响的政策变化
E. **技术颠覆风险**：可能使当前护城河失效的技术变化
F. **全球宏观传导**：外部冲击如何影响这个行业

对每个盲点风险（3-5 个）：
- 风险描述
- 为什么市场可能低估
- 触发条件
- 影响量级（轻微/中等/严重/致命）

### 2.3 Kill Criteria（致命信号）

如果以下任何一个出现，说明这个投资逻辑已经根本性破坏，应考虑退出：
1. {具体、可观测的信号}
2. {具体、可观测的信号}
3. {具体、可观测的信号}

### 2.4 监控清单（下次复盘时重点看）

| 风险 | 监控指标 | 阈值 | 频率 |
|------|----------|------|------|
| | | | |

---

## Step 3：写入文件 + 更新状态

output_key = `06_risk_blindspots`

---

## Step 4：汇报

```
✅ 风险盲点已生成 → v{N}
最重要的盲点风险：{一句话}
Kill criteria 数量：{N} 个
```
```

- [ ] **Step 3: Create `prism/workflows/04-synthesize/07-decision-kit.md`**

```markdown
# 产出 07 — 决策辅助 (Decision Kit)

**定位**：把前 6 份产出的核心结论压缩成投资决策直接需要的形式  
**训练知识比例**：约 30%（主要是整合前 6 份产出的结论）  
**产出文件**：`prism/topics/{slug}/outputs/07_decision_kit.md`

**前置条件**：产出 01-06 必须至少有 4 份已生成（status=fresh）

---

## Step 0：前置检查

```bash
python -c "
from prism.scripts.topic import read_topic
t = read_topic('{slug}')
fresh = [k for k, v in t['outputs_state'].items() if v['status'] == 'fresh']
print('已生成产出：', fresh)
"
```

如果不足 4 份 fresh，停止并提示先完成更多产出。

---

## Step 1：读取已有产出

```bash
cat prism/topics/{slug}/outputs/01_business_panorama.md
cat prism/topics/{slug}/outputs/02_cycle_positioning.md
cat prism/topics/{slug}/outputs/03_narrative_ecology.md
cat prism/topics/{slug}/outputs/04_implied_expectations.md
cat prism/topics/{slug}/outputs/05_historical_mirrors.md
cat prism/topics/{slug}/outputs/06_risk_blindspots.md
```

---

## Step 2：撰写决策辅助

### 2.1 一页纸摘要

```
主题：{display_name}
研究问题：{question}
生成日期：{date}

【商业理解】
{3 句话：这是什么生意，护城河在哪里，增长驱动是什么}

【周期定位】
当前处于：{位置}
方向：{向上/横盘/向下}，置信度：{高/中/低}

【叙事】
主流叙事：{一句话}
是否认同：是/部分/否，原因：{一句话}

【隐含预期】
市场假设：{一句话}
我的判断：{偏乐观/中性/偏悲观}

【类比】
最像：{案例}，教训：{一句话}

【核心风险】
最大已知风险：{一句话}
最大盲点风险：{一句话}
```

### 2.2 核心假设清单（What Would Have To Be True）

投资成立需要以下假设为真：
1. {具体、可验证的假设}
2. {具体、可验证的假设}
3. {具体、可验证的假设}

如果以上假设有任何一个被证伪，投资逻辑需要重新评估。

### 2.3 Signposts（路标事件）

接下来 3-12 个月，以下事件/数据将帮助验证或证伪上述假设：

| 时间 | 事件/数据 | 多方信号 | 空方信号 |
|------|----------|----------|----------|
| | | | |

### 2.4 研究成熟度评估

- **信息完整性**：{高/中/低}（已覆盖多少关键维度）
- **观点确信度**：{高/中/低}（证据有多支持）
- **建议下一步**：{继续深挖哪个方向 / 等待哪个催化剂 / 还缺什么资料}

---

## Step 3：写入文件 + 更新状态

output_key = `07_decision_kit`

---

## Step 4：汇报

```
✅ 决策辅助已生成 → v{N}
核心假设数量：{N} 个
关键 Signpost 数量：{N} 个
研究成熟度：{评级}
```
```

- [ ] **Step 4: Create `prism/workflows/04-synthesize/08-feed.md`**

```markdown
# 产出 08 — 信息流时间线 (Living Feed)

**定位**：记录发生时序，以便日后复盘「当时知道什么，当时怎么判断」  
**训练知识比例**：约 20%（主要记录具体事实和日期）  
**产出文件**：`prism/topics/{slug}/outputs/08_living_feed.md`

**特点**：这份产出是追加式的，不是一次性生成，每次有新信息都在末尾追加。

---

## Step 0：检查文件是否存在

```bash
cat prism/topics/{slug}/outputs/08_living_feed.md 2>/dev/null || echo "FILE_NOT_EXISTS"
```

如果不存在，创建初始文件。如果存在，在末尾追加。

---

## Step 1：初次创建（文件不存在时）

写入文件头部：

```markdown
---
slug: {slug}
output_key: 08_living_feed
version: 1
generated: {timestamp}
---

# 信息流时间线：{display_name}

> 按时间顺序记录重要信息和判断变化。每次更新在末尾追加，不修改历史记录。

## {YYYY-MM-DD} 研究开始

**来源**：用户发起研究  
**主要事项**：
- 研究问题：{question}
- 初步了解：{3-5 句话的初步认知}

**当时的主要不确定性**：
- {一句话}
- {一句话}
```

---

## Step 2：追加更新（文件已存在时）

在文件末尾追加：

```markdown

---

## {YYYY-MM-DD} {触发更新的事件简述}

**来源**：{资料名称 / 市场事件 / 数据发布}  
**关键信息**：
- {具体事实，有数据就有数据}

**对已有判断的影响**：
- 支持了：{哪个假设}
- 否定了：{哪个假设，或"无"}
- 新增了：{哪个不确定性，或"无"}

**当前判断更新**（如有变化）：
{如没变化写"维持原判断"}
```

---

## Step 3：更新状态

output_key = `08_living_feed`，每次追加后 version+1。

---

## Step 4：汇报

```
✅ 信息流时间线已更新 → v{N}
本次追加事项：{一句话}
```
```

- [ ] **Step 5: Commit all 4 synthesize workflows**

```bash
git add prism/workflows/04-synthesize/
git commit -m "feat(prism): synthesize workflows 05-08 — mirrors/risks/decision-kit/feed"
```

---

### Task 22: Remaining workflows (05-critic, 06-monitor, 07-drilldown, 99-decision-record)

**Files:**
- Create: `prism/workflows/05-critic-review.md`
- Create: `prism/workflows/06-daily-monitor.md`
- Create: `prism/workflows/07-drilldown.md`
- Create: `prism/workflows/99-decision-record.md`

- [ ] **Step 1: Create `prism/workflows/05-critic-review.md`**

```markdown
# Workflow 05 — 批评者评审 (Critic Review)

**触发**：用户说「评审 {slug}」或「steelman 反方」  
**定位**：强制用反方逻辑质疑自己的研究结论  
**前置**：产出 04（隐含预期）和 06（风险盲点）必须已生成

---

## Step 1：读取核心产出

```bash
cat prism/topics/{slug}/outputs/04_implied_expectations.md
cat prism/topics/{slug}/outputs/06_risk_blindspots.md
cat prism/topics/{slug}/outputs/07_decision_kit.md 2>/dev/null
```

---

## Step 2：扮演反方（Steelman）

**指令：现在切换为持有相反观点的分析师。**

如果当前研究结论偏多，现在用空方最强逻辑反驳。
如果当前结论偏空，用多方最强逻辑反驳。

反驳格式：

### 对「核心假设 1」的质疑

多方假设：{原假设}  
反驳：{空方为什么认为这个假设不成立}  
支撑证据：{有什么数据或逻辑}  
强度评估：{强/中/弱} — 如果弱，说明为什么仍然值得考虑

### 对「核心假设 2」的质疑

{同格式}

### 对「核心假设 3」的质疑

{同格式}

---

## Step 3：给原研究评分

| 维度 | 评分(1-5) | 评语 |
|------|-----------|------|
| 逻辑严密性 | | |
| 证据充分性 | | |
| 考虑反面观点 | | |
| 隐含假设透明度 | | |
| 整体 | | |

---

## Step 4：给出修改建议

「如果我要加强这个研究，最重要的 3 件事是：」
1. {具体建议}
2. {具体建议}
3. {具体建议}

---

## Step 5：更新 next_actions

```bash
python -c "
from prism.scripts.topic import set_next_actions
set_next_actions('{slug}', [
    '批评者评审完成，根据建议补充：{重要建议}',
    '下次复盘时重点关注：{关键验证点}',
])
"
```
```

- [ ] **Step 2: Create `prism/workflows/06-daily-monitor.md`**

```markdown
# Workflow 06 — 日常监控 (Daily Monitor)

**触发**：用户说「监控 {slug}」或每日/每周定期运行  
**定位**：快速扫描新信息，判断是否影响现有判断  
**耗时**：目标 5-10 分钟

---

## Step 1：读取 Kill Criteria 和 Signposts

```bash
cat prism/topics/{slug}/outputs/06_risk_blindspots.md | grep -A 20 "Kill Criteria"
cat prism/topics/{slug}/outputs/07_decision_kit.md | grep -A 30 "Signposts"
```

---

## Step 2：用户提供新信息

询问用户：「今天有什么新信息需要评估？」

如果没有新信息，检查：
- 是否有定期数据发布（月度销量/PMI/价格指数）
- 公司是否有公告
- 行业是否有政策动态

---

## Step 3：逐条评估新信息

对每条新信息：

```
信息：{一句话描述}
来源：{来源}
日期：{日期}

影响评估：
□ 触发了 Kill Criteria？ 是/否
□ 验证了哪个 Signpost？ {或"无"}
□ 否定了哪个核心假设？ {或"无"}
□ 需要更新哪份产出？ {或"无需"}

结论：维持判断 / 小幅调整 / 需要重新评估
```

---

## Step 4：追加到信息流

将本次监控结果追加到产出 08（living feed），参见 workflow 04-synthesize/08-feed.md Step 2。

---

## Step 5：更新 next_actions

```bash
python -c "
from prism.scripts.topic import set_next_actions, set_user_todos
set_next_actions('{slug}', ['下次监控建议关注：{重点}'])
"
```
```

- [ ] **Step 3: Create `prism/workflows/07-drilldown.md`**

```markdown
# Workflow 07 — 深度钻探 (Drill-down)

**触发**：用户说「深挖 {slug} 的 {具体问题}」  
**定位**：对某个具体问题进行专项深度研究，产出专题笔记  
**产出文件**：`prism/topics/{slug}/outputs/drilldown_{timestamp}_{topic_keyword}.md`

---

## Step 1：明确钻探问题

用户的问题可能是：
- 「深挖 {slug} 的竞争格局」
- 「分析 {slug} 里 {公司名} 的护城河」
- 「中国 vs 海外 {slug} 的格局差异」
- 「{slug} 在利率上行环境的历史表现」

如果问题不够具体，AskUserQuestion 细化。

---

## Step 2：评估信息来源

```bash
python -c "
from prism.scripts.manifest import read_manifest
import json
data = read_manifest('{slug}')
for m in data['materials']:
    print(m['id'], '|', m['filename'], '|', 'processed' if m['processed'] else 'UNPROCESSED')
"
```

判断：现有资料是否足够回答这个问题，还是需要补充资料。

---

## Step 3：深度分析

使用训练知识 + 已有 findings，对问题进行深度分析：

- 结构：问题分解 → 每个子问题的分析 → 综合结论
- 要求：比产出 01-08 更深、更具体
- 字数：不限，以回答清楚问题为准

---

## Step 4：写入专题笔记

```bash
# 文件名格式：drilldown_YYYYMMDD_keyword.md
```

格式：
```markdown
---
slug: {slug}
type: drilldown
question: {具体问题}
generated: {timestamp}
---

# 深度钻探：{问题}

{分析内容}

## 结论
{一段话}

## 后续行动
{需要验证的 1-3 件事}
```

---

## Step 5：更新 living feed（追加本次钻探摘要）
```

- [ ] **Step 4: Create `prism/workflows/99-decision-record.md`**

```markdown
# Workflow 99 — 决策记录 (Decision Record)

**触发**：用户要做出实际投资决策（买入/卖出/持有/放弃）  
**定位**：在采取行动前记录决策依据，供事后复盘  
**产出文件**：`prism/topics/{slug}/outputs/decision_{YYYYMMDD}.md`

---

## Step 1：了解决策意图

AskUserQuestion：
1. 打算做什么操作（买入/加仓/减仓/卖出/放弃研究）
2. 考虑的仓位或规模
3. 为什么现在（什么触发了这个决策）

---

## Step 2：决策前检查

```bash
cat prism/topics/{slug}/outputs/07_decision_kit.md
```

核对：
- [ ] 核心假设是否还成立
- [ ] 是否有 Kill Criteria 被触发
- [ ] 当前信息是否足以支撑决策

如果信息明显不足，提醒用户并给出建议。

---

## Step 3：记录决策

写入 `prism/topics/{slug}/outputs/decision_{YYYYMMDD}.md`：

```markdown
---
slug: {slug}
type: decision
date: {YYYYMMDD}
action: buy|add|reduce|sell|pass
---

# 决策记录：{YYYYMMDD}

## 决策
操作：{buy/add/reduce/sell/pass}  
理由（一句话）：{一句话}

## 支撑这个决策的核心假设

1. {假设}（来自产出04）
2. {假设}
3. {假设}

## 我知道自己不知道的事情

1. {不确定性}
2. {不确定性}

## 如果我错了，最可能错在哪里

{一段话}

## Kill Criteria（触发后重新评估）

{来自产出06的 kill criteria}

## Signposts 下一个要看的

{来自产出07的 signpost}

## 研究成熟度

{high/medium/low} — {理由}

## 心理状态自检

□ 是否受近期涨跌影响而情绪化
□ 是否对这个行业/公司有特别的偏好
□ 是否充分考虑了反方观点
```

---

## Step 4：追加到 living feed

将决策摘要追加到 `08_living_feed.md`。

---

## Step 5：汇报

```
✅ 决策记录已保存 → prism/topics/{slug}/outputs/decision_{YYYYMMDD}.md

操作：{action}
核心假设数量：{N}
主要不确定性：{一句话}

建议：决策后 {30 天} 回来做一次复盘对照。
```
```

- [ ] **Step 5: Commit all**

```bash
git add prism/workflows/05-critic-review.md prism/workflows/06-daily-monitor.md
git add prism/workflows/07-drilldown.md prism/workflows/99-decision-record.md
git commit -m "feat(prism): workflows 05-07 + 99 — critic/monitor/drilldown/decision"
```

---

## Phase 4 — Templates + Prompts (Tasks 23–24)

### Task 23: `prism/templates/topic.yaml.tmpl`

- [ ] **Step 1: Create `prism/templates/topic.yaml.tmpl`**

Content: the `topic.yaml` schema from the top of this document, with `{slug}`, `{display_name}`, `{type}`, `{question}`, `{geo}`, `{depth}`, `{created}` as placeholders.

```yaml
# topic.yaml — Prism research topic state file
# Generated by workflow 00-research-topic, managed by prism/scripts/topic.py
slug: {slug}
display_name: {display_name}
type: {type}
created: {created}
status: active
stage: "00-init"
scope:
  geo: {geo}
  question: "{question}"
  depth: {depth}
outputs_state:
  "01_business_panorama":
    version: 0
    last_updated: null
    status: pending
  "02_cycle_positioning":
    version: 0
    last_updated: null
    status: pending
  "03_narrative_ecology":
    version: 0
    last_updated: null
    status: pending
  "04_implied_expectations":
    version: 0
    last_updated: null
    status: pending
  "05_historical_mirrors":
    version: 0
    last_updated: null
    status: pending
  "06_risk_blindspots":
    version: 0
    last_updated: null
    status: pending
  "07_decision_kit":
    version: 0
    last_updated: null
    status: pending
  "08_living_feed":
    version: 0
    last_updated: null
    status: pending
next_actions:
  - "运行 workflow 01-build-roadmap：制定详细研究路线图"
user_todos: []
monitoring:
  enabled: false
  cadence: daily
```

- [ ] **Step 2: Commit**

```bash
git add prism/templates/topic.yaml.tmpl
git commit -m "feat(prism): topic.yaml template"
```

---

### Task 24: Prompts — `analyst_voice.md` + `output_quality_rubric.md`

These are shared prompting guidelines Claude reads when generating outputs.

**Files:**
- Create: `prism/prompts/analyst_voice.md`
- Create: `prism/prompts/output_quality_rubric.md`

- [ ] **Step 1: Create `prism/prompts/analyst_voice.md`**

```markdown
# Analyst Voice Guidelines

产出时遵守以下声音规范：

## 风格
- 简洁直接，不用「我们认为」之类的空话，直接说观点
- 有数字就用数字，避免「较高」「较快」等模糊描述
- 区分事实（有来源）和判断（作者推断），用「[数据]」和「[判断]」标注
- 用主动语态，避免被动句
- 中文写作时避免翻译腔

## 结构
- 先结论后论据（不要把结论藏在末尾）
- 每节开头一句话总结本节核心观点
- 用表格组织对比类信息，比段落更清晰

## 禁止
- 禁止用「复杂」「错综复杂」「千丝万缕」之类无信息量的描述
- 禁止没有来源的宏观数据（「据报道中国经济增速为X%」）
- 禁止把不确定性掩盖掉，不知道就说不知道
- 禁止对所有情景都持中性立场，要给出自己的判断（哪怕信心度低）

## 信息来源标注
- 来自训练知识：无需标注，但在信息来源节说明
- 来自资料：引用 mat_id 和文件名
- 来自数据（有时间点）：`[{来源} {日期}] {数值}`
```

- [ ] **Step 2: Create `prism/prompts/output_quality_rubric.md`**

```markdown
# Output Quality Rubric

每份产出完成后对照此 rubric 自评。

## 必须通过（任何一项不通过则重写相关部分）

| 检查项 | 通过标准 |
|--------|----------|
| 有具体数字 | 至少 3 处有具体数据（不是「较高」「约几倍」） |
| 多空兼顾 | 有乐观视角也有悲观视角，不是单一方向 |
| 有「哪里可能是错的」 | 每份产出都明确指出当前判断最可能错在哪里 |
| 来源透明 | 训练知识 vs 资料来源有区分 |
| 结论在前 | 核心判断不埋在末尾 |

## 加分项（有则更好）

- 有量化的置信度估计（「60% 概率」比「可能」更有用）
- 有具体的可验证节点（「下个季报/2026Q1 如果 X 则...」）
- 有反直觉的洞见（不只是重复卖方共识）
- 类比案例有具体时间和幅度数据

## 减分项（有则在汇报时说明）

- 字数超过 3000 字（过长难以消化）
- 结论过于中性（「需要继续观察」不是结论）
- 数据老于 2 年（除历史类比外）
```

- [ ] **Step 3: Commit**

```bash
git add prism/prompts/analyst_voice.md prism/prompts/output_quality_rubric.md
git commit -m "feat(prism): prompts — analyst voice + quality rubric"
```

---

## End-to-End Verification

After all tasks complete, run this verification:

- [ ] **All tests pass**

```bash
cd /Users/yangqi/investing && python -m pytest tests/test_prism_scripts.py tests/test_prism_routes.py -v
```

Expected: 15+ tests PASS, 0 FAIL

- [ ] **Full test suite has no regressions**

```bash
cd /Users/yangqi/investing && python -m pytest --tb=short -q 2>&1 | tail -10
```

- [ ] **Web app starts and /prism loads**

```bash
cd /Users/yangqi/investing && uvicorn main:app --reload --port 8000 &
sleep 2
curl -s http://localhost:8000/prism | grep -c "研究主题"
```

Expected: output includes `研究主题`

- [ ] **End-to-end: create topic and view it**

```bash
python -c "
from prism.scripts.topic import create_topic
from prism.scripts.manifest import create_manifest
create_topic('cn-pet-e2e', '中国宠物（验证）', 'industry', '宠物行业机会', 'CN', 'quick')
create_manifest('cn-pet-e2e')
print('OK')
"
curl -s http://localhost:8000/prism/cn-pet-e2e | grep -c "中国宠物"
```

Expected: `1`

- [ ] **Final commit**

```bash
git add -A
git commit -m "feat(prism): complete phase 0-4 implementation"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] `prism/` isolated from existing `app/`, `arenas/`, `companies/`
- [x] Zero LLM calls in Python scripts
- [x] 8 standard outputs defined with full workflow detail
- [x] Web dashboard at `/prism` (index + detail + output)
- [x] SKILL.md for chat trigger routing
- [x] `topic.yaml` as single source of truth for state
- [x] `manifest.yaml` for material tracking
- [x] All workflows numbered and complete
- [x] TDD: tests before implementation for all Python code
- [x] Frequent commits after each task

**No placeholders detected.**

**Type consistency:** All scripts use `_PRISM_ROOT` consistently, monkeypatched in tests. Output keys match `_OUTPUT_KEYS_LABELS` in `outputs.py` and topic.yaml schema.

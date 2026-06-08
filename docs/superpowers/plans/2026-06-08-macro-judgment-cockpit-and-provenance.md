# 宏观层「判断驾驶舱 + 评估溯源」Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给宏观层加一个零-LLM 的「评估快照」脊梁，并在输入源表/新「评估溯源」tab 上做到可控、可溯、可验证（结论←输入←因果句、相对上次评估的变化、监控开关、一键组装重估简报）。

**Architecture:** 新产物 `outputs/regime_eval_log.yaml` 是脊梁：LLM 每次（重）写 regime_read 时经 `append_evaluation` 落一条 evaluation（`input_snapshot` 列全所有输入 + `conclusions` 按结论挂输入）。diff、重估简报、参与/溯源标记全由 `eval_snapshot.py` 零-LLM 从快照派生。web 全部零-LLM；真正的重判永远在对话里由人触发，落地后写回新快照、清「待重判」戳。

**Tech Stack:** Python 3.14（`.venv/bin/python`）、pytest、PyYAML、FastAPI + Jinja2、httpx（fetcher，测试 mock）。所有 pytest 跑 `.venv/bin/python -m pytest -p no:cacheprovider -q`。

**实现期纪律（CLAUDE.md / GitNexus）：** 改既有 symbol（`macro_registry.*`、`prism.py` 路由）前先 `gitnexus_impact({target, direction:"upstream"})` 报爆炸半径，HIGH/CRITICAL 先警告；每次提交前 `gitnexus_detect_changes()`；改名走 `gitnexus_rename`；不用 `git add -A`（逐文件 add）。提交信息以 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` 结尾。

---

## 阶段 1 — 快照骨架（eval_snapshot.py）

### Task 1: eval_snapshot 读写 + append + 不变量校验

**Files:**
- Create: `prism/scripts/eval_snapshot.py`
- Test: `prism/scripts/test_eval_snapshot.py`

- [ ] **Step 1: Write the failing test**

`prism/scripts/test_eval_snapshot.py`:

```python
"""评估快照（regime_eval_log.yaml）零-LLM CRUD + diff + 重估简报 的测试。"""
import pytest

from prism.scripts import eval_snapshot as es
from prism.scripts import macro_registry as reg


@pytest.fixture
def tmp_topic(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(es, "_PRISM_ROOT", tmp_path)
    slug, variant = "m", "v"
    reg.create_registry(slug, variant)
    reg.upsert_input(slug, variant, {
        "name": "A", "tier": "A", "cadence_type": "event", "mechanism": "CD",
        "causal_sentence": "x", "importance": "load_bearing"})
    reg.upsert_input(slug, variant, {"name": "B", "cadence_type": "series", "importance": "background"})
    return slug, variant


def _ev_all(extra_conclusions=None):
    """列全 A、B 两条输入的最小 evaluation（满足"必须列全"不变量）。"""
    return {
        "input_snapshot": [
            {"name": "A", "value": 3.0, "as_of": "2026-05-01", "used": True},
            {"name": "B", "value": None, "as_of": None, "used": False},
        ],
        "conclusions": extra_conclusions if extra_conclusions is not None else [
            {"id": "rates", "label": "利率", "state": "紧",
             "based_on": [{"input": "A", "role": "load_bearing"}], "causal": "A→紧"}],
    }


def test_read_eval_log_missing_returns_skeleton(tmp_topic):
    slug, variant = tmp_topic
    log = es.read_eval_log(slug, variant)
    assert log["evaluations"] == []
    assert log["reeval_pending"] is None


def test_append_evaluation_writes_and_increments(tmp_topic):
    slug, variant = tmp_topic
    assert es.append_evaluation(slug, variant, _ev_all()) == 1
    assert es.append_evaluation(slug, variant, _ev_all()) == 2
    latest = es.latest_evaluation(slug, variant)
    assert latest["version"] == 2
    assert latest["conclusions"][0]["id"] == "rates"


def test_append_rejects_missing_input(tmp_topic):
    slug, variant = tmp_topic
    ev = {"input_snapshot": [{"name": "A", "value": 1, "used": True}], "conclusions": []}
    with pytest.raises(ValueError, match="漏列"):
        es.append_evaluation(slug, variant, ev)


def test_append_rejects_dangling_based_on(tmp_topic):
    slug, variant = tmp_topic
    ev = _ev_all([{"id": "x", "based_on": [{"input": "ZZZ", "role": "load_bearing"}]}])
    with pytest.raises(ValueError, match="悬空"):
        es.append_evaluation(slug, variant, ev)


def test_append_rejects_bad_role(tmp_topic):
    slug, variant = tmp_topic
    ev = _ev_all([{"id": "x", "based_on": [{"input": "A", "role": "bogus"}]}])
    with pytest.raises(ValueError, match="role"):
        es.append_evaluation(slug, variant, ev)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_snapshot.py -p no:cacheprovider -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'prism.scripts.eval_snapshot'`.

- [ ] **Step 3: Write minimal implementation**

`prism/scripts/eval_snapshot.py`:

```python
"""宏观层评估快照（regime_eval_log.yaml）的零-LLM CRUD + diff + 重估简报组装。

评估快照是「输入→判断」可溯源的脊梁：每次（重）写 regime_read 时，LLM 经 append_evaluation
落一条 evaluation（input_snapshot 列全所有输入 + conclusions 按结论挂输入）。之后 diff/简报
全由本模块零-LLM 派生。判断永远人在对话里触发，本模块不含任何 LLM 调用。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from prism.scripts import macro_registry as reg

_PRISM_ROOT = Path(__file__).resolve().parent.parent

VALID_ROLE = ("load_bearing", "confirming", "background")


def _log_path(slug: str, variant: str) -> Path:
    if not variant:
        raise ValueError("必须显式指定 variant")
    return _PRISM_ROOT / "topics" / slug / variant / "outputs" / "regime_eval_log.yaml"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def read_eval_log(slug: str, variant: str) -> dict:
    """读评估日志；缺文件返回空骨架（不抛，让 web 优雅显示"未生成首份快照"）。"""
    path = _log_path(slug, variant)
    if not path.exists():
        return {"slug": slug, "variant": variant, "evaluations": [], "reeval_pending": None}
    data = _read_yaml(path)
    data.setdefault("evaluations", [])
    data.setdefault("reeval_pending", None)
    return data


def latest_evaluation(slug: str, variant: str) -> dict | None:
    evals = read_eval_log(slug, variant).get("evaluations") or []
    return evals[-1] if evals else None


def _validate_evaluation(evaluation: dict, input_names: set) -> list:
    """校验一条 evaluation 的不变量。返回错误列表（空=通过）。"""
    errors = []
    snap = evaluation.get("input_snapshot") or []
    snap_names = {s.get("name") for s in snap}
    missing = input_names - snap_names
    if missing:
        errors.append(f"input_snapshot 漏列输入: {sorted(missing)}")
    for c in evaluation.get("conclusions") or []:
        cid = c.get("id", "<无 id>")
        for b in c.get("based_on") or []:
            if b.get("input") not in snap_names:
                errors.append(f"[{cid}] based_on 悬空引用: {b.get('input')!r} 不在 input_snapshot")
            if b.get("role") not in VALID_ROLE:
                errors.append(f"[{cid}] role 非法: {b.get('role')!r}")
    return errors


def append_evaluation(slug: str, variant: str, evaluation: dict) -> int:
    """追加一条 evaluation（校验不变量后落盘，version 自增，清 reeval_pending）。零 LLM。

    evaluation: {evaluated_at?, note?, input_snapshot:[{name,value,as_of,used}], conclusions:[...]}
    校验失败抛 ValueError，不落盘（保持快照可信）。
    """
    registry = reg.read_registry(slug, variant)
    input_names = {e["name"] for e in registry.get("inputs") or []}
    errors = _validate_evaluation(evaluation, input_names)
    if errors:
        raise ValueError("评估快照不变量校验失败:\n" + "\n".join(errors))
    log = read_eval_log(slug, variant)
    version = len(log["evaluations"]) + 1
    entry = {"version": version, "evaluated_at": evaluation.get("evaluated_at") or _now_iso()}
    if evaluation.get("note"):
        entry["note"] = evaluation["note"]
    entry["input_snapshot"] = evaluation.get("input_snapshot") or []
    entry["conclusions"] = evaluation.get("conclusions") or []
    log["evaluations"].append(entry)
    log["reeval_pending"] = None
    log["slug"], log["variant"], log["updated"] = slug, variant, _now_iso()
    _write_yaml(_log_path(slug, variant), log)
    return version
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_snapshot.py -p no:cacheprovider -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/eval_snapshot.py prism/scripts/test_eval_snapshot.py
git commit -m "feat(macro): 评估快照 regime_eval_log 的 CRUD + 不变量校验

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: diff_since_last + conclusions_for_input

**Files:**
- Modify: `prism/scripts/eval_snapshot.py`
- Test: `prism/scripts/test_eval_snapshot.py`

- [ ] **Step 1: Write the failing test** (append to test file)

```python
def test_conclusions_for_input_reverse_index(tmp_topic):
    slug, variant = tmp_topic
    es.append_evaluation(slug, variant, _ev_all())
    latest = es.latest_evaluation(slug, variant)
    assert es.conclusions_for_input(latest, "A") == ["rates"]
    assert es.conclusions_for_input(latest, "B") == []


def test_diff_no_snapshot_is_first(tmp_topic):
    slug, variant = tmp_topic
    diff = es.diff_since_last(slug, variant)
    assert {d["name"] for d in diff} == {"A", "B"}
    assert all(d["changed"] is None for d in diff)


def test_diff_detects_numeric_change_and_conclusions(tmp_topic):
    slug, variant = tmp_topic
    es.append_evaluation(slug, variant, _ev_all())
    reg.record_observation(slug, variant, "A", value=3.5)
    diff = {d["name"]: d for d in es.diff_since_last(slug, variant)}
    assert diff["A"]["changed"] is True
    assert diff["A"]["delta"] == pytest.approx(0.5)
    assert diff["A"]["snapshot_value"] == 3.0
    assert diff["A"]["live_value"] == 3.5
    assert diff["A"]["conclusions"] == ["rates"]
    assert diff["A"]["used"] is True
    assert diff["B"]["changed"] is False        # 两端都 None → 未变
    assert diff["B"]["used"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_snapshot.py -p no:cacheprovider -q`
Expected: FAIL — `AttributeError: module 'prism.scripts.eval_snapshot' has no attribute 'conclusions_for_input'`.

- [ ] **Step 3: Write minimal implementation** (append to `eval_snapshot.py`)

```python
def conclusions_for_input(evaluation: dict, name: str) -> list:
    """based_on 反查：该输入支撑哪些 conclusion id。"""
    out = []
    for c in evaluation.get("conclusions") or []:
        if any(b.get("input") == name for b in c.get("based_on") or []):
            out.append(c.get("id"))
    return out


def diff_since_last(slug: str, variant: str) -> list:
    """对登记表每条输入，比对现 observed.value 与 latest 快照值。零 LLM。

    返回每条 {name, snapshot_value, live_value, delta, changed, breached, used, conclusions}。
    无快照 → changed=None（"首次评估，无基准"）。非数值按字符串比 changed。
    """
    registry = reg.read_registry(slug, variant)
    latest = latest_evaluation(slug, variant)
    snap_by_name = {}
    if latest:
        snap_by_name = {s["name"]: s for s in latest.get("input_snapshot") or []}
    out = []
    for e in registry.get("inputs") or []:
        name = e["name"]
        live = (e.get("observed") or {}).get("value")
        snap = snap_by_name.get(name) or {}
        snap_val = snap.get("value")
        row = {
            "name": name, "snapshot_value": snap_val, "live_value": live,
            "delta": None, "changed": None if latest is None else False,
            "breached": False, "used": bool(snap.get("used")),
            "conclusions": conclusions_for_input(latest, name) if latest else [],
        }
        if latest is not None:
            if isinstance(live, (int, float)) and isinstance(snap_val, (int, float)):
                row["delta"] = live - snap_val
                row["changed"] = row["delta"] != 0
                row["breached"] = reg._reading_breaches(
                    {**e, "observed": {"value": live, "prev_value": snap_val}})
            else:
                row["changed"] = live != snap_val
        out.append(row)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_snapshot.py -p no:cacheprovider -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/eval_snapshot.py prism/scripts/test_eval_snapshot.py
git commit -m "feat(macro): 评估快照 diff（现值 vs 上次评估）+ based_on 反查

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: assemble_reeval_brief + stamp_reeval_pending

**Files:**
- Modify: `prism/scripts/eval_snapshot.py`
- Test: `prism/scripts/test_eval_snapshot.py`

- [ ] **Step 1: Write the failing test** (append to test file)

```python
def test_assemble_brief_lists_changed_unfetched_affected(tmp_topic):
    slug, variant = tmp_topic
    es.append_evaluation(slug, variant, _ev_all())
    reg.record_observation(slug, variant, "A", value=4.0)   # A 变了，支撑 rates
    brief = es.assemble_reeval_brief(slug, variant)
    assert "A" in [c["name"] for c in brief["changed"]]
    assert "B" in brief["unfetched"]                        # B 从未抓到值
    assert "rates" in brief["affected_conclusions"]
    assert set(brief) == {"changed", "breached", "due", "alert", "unfetched", "affected_conclusions"}


def test_stamp_and_clear_reeval_pending(tmp_topic):
    slug, variant = tmp_topic
    es.append_evaluation(slug, variant, _ev_all())
    es.stamp_reeval_pending(slug, variant, {"changed": [], "affected_conclusions": []})
    assert es.read_eval_log(slug, variant)["reeval_pending"] is not None
    es.append_evaluation(slug, variant, _ev_all())          # 新评估落地清戳
    assert es.read_eval_log(slug, variant)["reeval_pending"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_snapshot.py -p no:cacheprovider -q`
Expected: FAIL — `AttributeError: ... has no attribute 'assemble_reeval_brief'`.

- [ ] **Step 3: Write minimal implementation** (append to `eval_snapshot.py`)

```python
def assemble_reeval_brief(slug: str, variant: str) -> dict:
    """零-LLM 组装重估简报：变化项 + 到期/越带 + 受影响结论 + 未抓盲区清单。

    未抓清单是诚实盲区提示（这些输入无法判断是否变化）。供 S5 展示与对话重判消费。
    """
    diff = diff_since_last(slug, variant)
    changed = [d for d in diff if d["changed"]]
    breached = [d for d in diff if d["breached"]]
    unfetched = [d["name"] for d in diff if d["live_value"] is None]
    registry = reg.read_registry(slug, variant)
    scan = reg.scan_macro_inputs(registry)
    due = [e["name"] for e in scan["due_event"] + scan["due_policy"]]
    alert = [e["name"] for e in scan["alert_series"]]
    affected = sorted({c for d in (changed + breached) for c in d["conclusions"]})
    return {"changed": changed, "breached": breached, "due": due,
            "alert": alert, "unfetched": unfetched, "affected_conclusions": affected}


def stamp_reeval_pending(slug: str, variant: str, brief: dict) -> None:
    """盖「待重判」戳（写 reeval_pending）。append_evaluation 时自动清空。零 LLM。"""
    log = read_eval_log(slug, variant)
    log["reeval_pending"] = {"stamped_at": _now_iso(), "brief": brief}
    log["slug"], log["variant"], log["updated"] = slug, variant, _now_iso()
    _write_yaml(_log_path(slug, variant), log)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_snapshot.py -p no:cacheprovider -q`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/eval_snapshot.py prism/scripts/test_eval_snapshot.py
git commit -m "feat(macro): 重估简报组装 + 待重判戳（reeval_pending）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 阶段 2 — 展示面（eval-trace tab + 输入表 S1/S3/S4）

### Task 4: eval-trace 路由（GET）

**Files:**
- Modify: `app/routes/prism.py`（在 `@router.get("/{slug}/{variant}/transmission-map")` 之后、任何 `/{output_key}` 通配之前插入）
- Test: `tests/test_macro_inputs_web.py`

**先决：** 改 `prism.py` 路由前运行 `gitnexus_impact({target: "prism_macro_inputs", direction: "upstream"})` 报告爆炸半径；HIGH/CRITICAL 先警告。

- [ ] **Step 1: Write the failing test** (append to `tests/test_macro_inputs_web.py`)

```python
def test_eval_trace_renders_conclusions(macro_web_client):
    import prism.scripts.eval_snapshot as es
    es.append_evaluation(SLUG, VARIANT, {
        "input_snapshot": [{"name": "HY OAS", "value": 3.1, "as_of": "2026-06-01", "used": True}],
        "conclusions": [{"id": "liquidity", "label": "流动性体制", "state": "偏紧",
                         "based_on": [{"input": "HY OAS", "role": "confirming"}],
                         "causal": "HY OAS 走阔 → 风险偏好降 → 流动性偏紧"}]})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/eval-trace")
    assert r.status_code == 200
    assert "流动性体制" in r.text
    assert "HY OAS 走阔" in r.text                  # causal 句


def test_eval_trace_404_for_non_macro(macro_web_client):
    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    t.create_topic("cn-ind-z", "某行业", "industry", "Q", "CN", "deep", VARIANT)
    m.create_manifest("cn-ind-z", VARIANT)
    assert macro_web_client.get(f"/prism/cn-ind-z/{VARIANT}/eval-trace").status_code == 404
```

**注意：** `macro_web_client` fixture 需同时给 `eval_snapshot` 打 `_PRISM_ROOT`。本任务 Step 3 同时改 fixture。

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_eval_trace_renders_conclusions -p no:cacheprovider -q`
Expected: FAIL — 404（路由不存在）。

- [ ] **Step 3a: Patch fixture to bind eval_snapshot root**

在 `tests/test_macro_inputs_web.py` 的 `macro_web_client` fixture 里，紧挨 `monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path / "prism")` 之后加：

```python
    import prism.scripts.eval_snapshot as es
    monkeypatch.setattr(es, "_PRISM_ROOT", tmp_path / "prism")
```

- [ ] **Step 3b: Add the route** to `app/routes/prism.py`（紧跟 transmission-map 路由之后）

```python
@router.get("/{slug}/{variant}/eval-trace")
def prism_eval_trace(request: Request, slug: str, variant: str):
    """评估溯源（结论←输入←因果句 + diff，仅 macro topic）。
    必须声明在 /{output_key} 通配之前（同 macro-inputs / transmission-map）。"""
    from prism.scripts import eval_snapshot as es
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")
    if topic.get("type") != "macro":
        raise HTTPException(status_code=404, detail="非宏观主题")
    return templates.TemplateResponse(request, "prism/eval_trace.html", {
        "topic": topic, "variant": variant,
        "evaluation": es.latest_evaluation(slug, variant),
        "diff": {d["name"]: d for d in es.diff_since_last(slug, variant)},
    })
```

- [ ] **Step 3c: Create `app/templates/prism/eval_trace.html`** (S6)

```jinja
{% extends "base.html" %}
{% from "prism/_view_tabs.html" import view_tabs %}
{% block title %}评估溯源 · {{ topic.display_name }}{% endblock %}
{% block content %}
<nav class="breadcrumb">
  <a href="/prism">研究主题</a> /
  <a href="/prism/{{ topic.slug }}">{{ topic.display_name or topic.slug }}</a> /
  <a href="/prism/{{ topic.slug }}/{{ variant }}">{{ variant }}</a> /
  <span>评估溯源</span>
</nav>
<div class="prism-header">
  <h1>{{ topic.display_name or topic.slug }}</h1>
  <span class="model-tag">{{ variant }}</span>
  <span class="hint"> · 评估溯源（结论←输入←因果句）</span>
</div>
{{ view_tabs(topic, variant, 'eval') }}

{% if not evaluation %}
  <p class="hint">未生成首份评估快照。下次在对话里重判 regime_read 时会写入。</p>
{% else %}
  <p class="hint">评估 v{{ evaluation.version }} · {{ (evaluation.evaluated_at or '')[:19] }}
    {% if evaluation.note %} · {{ evaluation.note }}{% endif %}</p>
  {% for c in evaluation.conclusions %}
  <section class="concl">
    <h2>{{ c.label or c.id }} <span class="concl-state">{{ c.state or '' }}</span></h2>
    {% if c.causal %}<p class="concl-causal">{{ c.causal }}</p>{% endif %}
    <table class="data-table">
      <thead><tr><th>依赖输入</th><th>角色</th><th>上次评估值</th><th>现值 / Δ</th></tr></thead>
      <tbody>
      {% for b in c.based_on %}
        {% set d = diff.get(b.input) %}
        <tr>
          <td><code>{{ b.input }}</code></td>
          <td>{{ b.role }}</td>
          <td>{% if d and d.snapshot_value is not none %}{{ d.snapshot_value }}{% else %}<span class="hint">—</span>{% endif %}</td>
          <td>
            {% if d and d.live_value is not none %}{{ d.live_value }}
              {% if d.delta is not none and d.delta != 0 %}<span class="badge-delta">{{ '%+.4g' | format(d.delta) }}</span>{% endif %}
              {% if d.breached %}<span class="badge-breach">越带</span>{% endif %}
            {% else %}<span class="hint">未抓</span>{% endif %}
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </section>
  {% endfor %}
{% endif %}
<style>
  .breadcrumb { font-size: 0.85em; color: #888; margin-bottom: 0.5em; }
  .breadcrumb a { color: #555; }
  .prism-header { margin: 0.5em 0; }
  .prism-header h1 { display: inline; font-size: 1.5em; margin-right: 0.5em; }
  .model-tag { font-size: 0.82em; color: #2a5db0; background: #f0f4ff; padding: 0.1em 0.4em; border-radius: 3px; font-family: monospace; }
  .diag-tabs { display: flex; align-items: center; gap: 0.1em; margin: 0.8em 0; border-bottom: 2px solid #e5e5e5; }
  .diag-tabs-label { font-size: 0.78em; color: #aaa; margin-right: 0.5em; }
  .diag-tab { padding: 0.4em 1em; font-size: 0.88em; text-decoration: none; color: #666; border-bottom: 2px solid transparent; margin-bottom: -2px; border-radius: 4px 4px 0 0; }
  .diag-tab.active { color: #333; font-weight: 600; background: #f1f3f5; border-bottom-color: #333; }
  .concl { margin: 1.2em 0; }
  .concl h2 { font-size: 1.05em; border-bottom: 1px solid #eee; padding-bottom: 0.2em; }
  .concl-state { font-size: 0.8em; color: #2a5db0; background: #f0f4ff; padding: 0.1em 0.4em; border-radius: 3px; }
  .concl-causal { color: #444; font-size: 0.9em; }
  .data-table { border-collapse: collapse; width: 100%; }
  .data-table th, .data-table td { padding: 0.4em 0.6em; border-bottom: 1px solid #eee; font-size: 0.85em; text-align: left; }
  .hint { color: #888; font-size: 0.85em; }
  .badge-delta { font-size: 0.72em; padding: 0.1em 0.35em; border-radius: 3px; background: #eef2f7; color: #44566b; }
  .badge-breach { font-size: 0.72em; padding: 0.1em 0.35em; border-radius: 3px; background: #fde8e8; color: #b42318; }
</style>
{% endblock %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_eval_trace_renders_conclusions tests/test_macro_inputs_web.py::test_eval_trace_404_for_non_macro -p no:cacheprovider -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add app/routes/prism.py app/templates/prism/eval_trace.html tests/test_macro_inputs_web.py
git commit -m "feat(web): 评估溯源页（结论←输入←因果句 + diff）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: 把「评估溯源」加进视图 tab 条

**Files:**
- Modify: `app/templates/prism/_view_tabs.html:13`（macro 分支，transmission 之后）
- Test: `tests/test_macro_inputs_web.py`

- [ ] **Step 1: Write the failing test** (append)

```python
def test_macro_detail_has_eval_trace_tab(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}")
    assert r.status_code == 200
    assert "评估溯源" in r.text
    assert f"/prism/{SLUG}/{VARIANT}/eval-trace" in r.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_macro_detail_has_eval_trace_tab -p no:cacheprovider -q`
Expected: FAIL — `assert "评估溯源" in r.text`.

- [ ] **Step 3: Edit `_view_tabs.html`** — 在 macro 分支的 transmission 行（第 13 行）之后插入一行：

```jinja
    {% if active == 'eval' %}<span class="diag-tab active">评估溯源</span>{% else %}<a class="diag-tab" href="/prism/{{ topic.slug }}/{{ variant }}/eval-trace">评估溯源</a>{% endif %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_macro_detail_has_eval_trace_tab -p no:cacheprovider -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/templates/prism/_view_tabs.html tests/test_macro_inputs_web.py
git commit -m "feat(web): 视图 tab 条加「评估溯源」(macro)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: 输入表传入 diff + reeval_pending

**Files:**
- Modify: `app/routes/prism.py`（`prism_macro_inputs`，约 690-707）
- Test: `tests/test_macro_inputs_web.py`

**先决：** 运行 `gitnexus_impact({target: "prism_macro_inputs", direction: "upstream"})`。

- [ ] **Step 1: Write the failing test** (append)

```python
def test_macro_inputs_passes_diff(macro_web_client):
    """有快照时输入表能拿到 diff（用于 S3/S4 列）：现值与上次评估值都出现。"""
    import prism.scripts.macro_registry as reg
    import prism.scripts.eval_snapshot as es
    reg.record_observation(SLUG, VARIANT, "HY OAS", value=3.5, as_of="2026-06-07")
    es.append_evaluation(SLUG, VARIANT, {
        "input_snapshot": [{"name": "HY OAS", "value": 3.0, "as_of": "2026-06-01", "used": True}],
        "conclusions": [{"id": "liquidity", "based_on": [{"input": "HY OAS", "role": "confirming"}]}]})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert r.status_code == 200
    assert "3.0" in r.text and "3.5" in r.text     # 上次评估值 + 现值
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_macro_inputs_passes_diff -p no:cacheprovider -q`
Expected: FAIL — 模板还没渲染 `3.0`（旧模板只显示 observed.value=3.5）。

- [ ] **Step 3: Edit `prism_macro_inputs`** — 替换函数体为：

```python
@router.get("/{slug}/{variant}/macro-inputs")
def prism_macro_inputs(request: Request, slug: str, variant: str):
    """宏观输入源信息表（仅 macro topic）。必须声明在 /{output_key} 通配之前。"""
    from prism.scripts import macro_registry as macro_reg
    from prism.scripts import eval_snapshot as es
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")
    if topic.get("type") != "macro":
        raise HTTPException(status_code=404, detail="非宏观主题")
    try:
        registry = macro_reg.read_registry(slug, variant)
        inputs = registry.get("inputs", [])
    except FileNotFoundError:
        inputs = []
    log = es.read_eval_log(slug, variant)
    diff = {d["name"]: d for d in es.diff_since_last(slug, variant)} if inputs else {}
    return templates.TemplateResponse(request, "prism/macro_inputs.html", {
        "topic": topic, "variant": variant, "inputs": inputs,
        "diff": diff, "reeval_pending": log.get("reeval_pending"),
    })
```

（模板此时还没用 `diff`，测试仍红——下一任务的模板改动让它变绿。本任务只先把数据喂进去。）

- [ ] **Step 4: Run test (still red until Task 7), confirm route imports OK**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_macro_inputs_table_renders -p no:cacheprovider -q`
Expected: PASS（既有渲染测试不被破坏，证明路由改动无回归）。`test_macro_inputs_passes_diff` 仍 FAIL，由 Task 7 转绿。

- [ ] **Step 5: Commit**

```bash
git add app/routes/prism.py
git commit -m "feat(web): macro-inputs 路由传入 diff + reeval_pending

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: 输入表 S1 报警看板 + S3 变化列 + S4 参与/支撑

**Files:**
- Modify: `app/templates/prism/macro_inputs.html`
- Test: `tests/test_macro_inputs_web.py`

- [ ] **Step 1: Write the failing test** (append)

```python
def test_alert_board_shows_alert_series(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "承重报警序列" in r.text
    assert "HY OAS" in r.text          # 报警卡片里出现


def test_inputs_table_shows_participation(macro_web_client):
    import prism.scripts.macro_registry as reg
    import prism.scripts.eval_snapshot as es
    reg.record_observation(SLUG, VARIANT, "HY OAS", value=3.5, as_of="2026-06-07")
    es.append_evaluation(SLUG, VARIANT, {
        "input_snapshot": [{"name": "HY OAS", "value": 3.0, "as_of": "2026-06-01", "used": True}],
        "conclusions": [{"id": "liquidity", "based_on": [{"input": "HY OAS", "role": "confirming"}]}]})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "参与" in r.text             # S4 参与徽章
    assert "liquidity" in r.text        # 支撑的结论 id
    assert "3.0" in r.text and "3.5" in r.text   # S3 上次评估值 + 现值
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_alert_board_shows_alert_series tests/test_macro_inputs_web.py::test_inputs_table_shows_participation -p no:cacheprovider -q`
Expected: FAIL — `承重报警序列` / `参与` 不在文本。

- [ ] **Step 3a: 在 `macro_inputs.html` 的 `{{ view_tabs(...) }}` 行之后、`<p class="hint">共 ...` 之前插入 S1 报警看板：**

```jinja
{% set alerts = inputs | selectattr('alert_series') | list %}
{% if alerts %}
<section class="alert-board">
  <h2>承重报警序列（{{ alerts | length }}）</h2>
  <div class="alert-cards">
  {% for a in alerts %}
    {% set d = diff.get(a.name) %}
    <div class="alert-card{% if d and d.breached %} breached{% endif %}">
      <div class="ac-name"><code>{{ a.name }}</code></div>
      <div class="ac-band hint">报警带 {{ a.alert_band }}</div>
      <div class="ac-val">
        {% if a.observed and a.observed.value is not none %}现 {{ a.observed.value }}{% else %}<span class="hint">未抓</span>{% endif %}
        {% if a.observed and a.observed.streak %}<span class="hint"> · 连越 {{ a.observed.streak }}</span>{% endif %}
      </div>
      <div class="ac-status">{% if d and d.breached %}<span class="badge-breach">越带</span>{% else %}<span class="badge-ok">带内</span>{% endif %}</div>
      {% if d and d.conclusions %}<div class="ac-feeds hint">支撑：{{ d.conclusions | join(', ') }}</div>{% endif %}
    </div>
  {% endfor %}
  </div>
</section>
{% endif %}
```

- [ ] **Step 3b: 替换 `<thead>` 行**为带新列的表头：

```jinja
  <thead><tr>
    <th>输入名</th><th>等级</th><th>频率</th><th>目标</th><th>重要性</th>
    <th>来源</th><th>抓取</th><th>上次评估值</th><th>现值 / Δ</th><th>参与·支撑</th><th>监控</th><th>报警带</th>
  </tr></thead>
```

- [ ] **Step 3c: 把行内「最近观测」那个 `<td>`（含 `inp.observed.value` 的整块）替换为三个 td：**

```jinja
      {% set d = diff.get(inp.name) %}
      <td>{% if d and d.snapshot_value is not none %}{{ d.snapshot_value }}{% else %}<span class="hint">—</span>{% endif %}</td>
      <td>
        {% if d and d.live_value is not none %}{{ d.live_value }}
          {% if d.delta is not none and d.delta != 0 %}<span class="badge-delta">{{ '%+.4g' | format(d.delta) }}</span>{% endif %}
          {% if d.breached %}<span class="badge-breach">越带</span>{% endif %}
        {% elif inp.observed and inp.observed.value is not none %}{{ inp.observed.value }}
        {% else %}<span class="hint">未抓</span>{% endif %}
      </td>
      <td>
        {% if d and d.used %}<span class="badge-used">参与</span>{% elif d %}<span class="badge-unused">未参与</span>{% endif %}
        {% if d and d.conclusions %}<span class="hint">{{ d.conclusions | join(', ') }}</span>{% endif %}
      </td>
```

- [ ] **Step 3d: 在 `<style>` 块末尾（`</style>` 之前）追加 CSS：**

```css
  .alert-board { margin: 0.8em 0 1.2em; }
  .alert-board h2 { font-size: 1em; margin: 0 0 0.5em; }
  .alert-cards { display: flex; flex-wrap: wrap; gap: 0.6em; }
  .alert-card { border: 1px solid #e5e5e5; border-radius: 6px; padding: 0.5em 0.7em; min-width: 11em; font-size: 0.85em; }
  .alert-card.breached { border-color: #f0a7a0; background: #fff6f5; }
  .ac-name code { font-size: 0.95em; }
  .ac-val { margin: 0.2em 0; }
  .badge-breach { font-size: 0.72em; padding: 0.1em 0.35em; border-radius: 3px; background: #fde8e8; color: #b42318; }
  .badge-ok { font-size: 0.72em; padding: 0.1em 0.35em; border-radius: 3px; background: #e6f4ea; color: #2d7a3a; }
  .badge-delta { font-size: 0.72em; padding: 0.1em 0.35em; border-radius: 3px; background: #eef2f7; color: #44566b; }
  .badge-used { font-size: 0.72em; padding: 0.1em 0.35em; border-radius: 3px; background: #e6f4ea; color: #2d7a3a; }
  .badge-unused { font-size: 0.72em; padding: 0.1em 0.35em; border-radius: 3px; background: #f1f1f1; color: #999; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_alert_board_shows_alert_series tests/test_macro_inputs_web.py::test_inputs_table_shows_participation tests/test_macro_inputs_web.py::test_macro_inputs_passes_diff -p no:cacheprovider -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add app/templates/prism/macro_inputs.html tests/test_macro_inputs_web.py
git commit -m "feat(web): 输入表 S1 报警看板 + S3 变化列 + S4 参与/支撑

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 阶段 3 — 控制面（监控开关 + 发起重估）

### Task 8: 监控开关（POST）+ S2 toggle UI

**Files:**
- Modify: `app/routes/prism.py`（新增 POST 路由）、`app/templates/prism/macro_inputs.html`（监控 td）
- Test: `tests/test_macro_inputs_web.py`

**先决：** 运行 `gitnexus_impact({target: "upsert_input", direction: "upstream"})`（POST 会调它）；HIGH/CRITICAL 先警告。

- [ ] **Step 1: Write the failing test** (append)

```python
def test_monitoring_toggle_post_sets_enabled(macro_web_client):
    # fixture 里 HY OAS monitoring.enabled=True；POST enabled=false 关掉
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/monitoring",
                              data={"name": "HY OAS", "enabled": "false"}, follow_redirects=False)
    assert r.status_code == 303
    import prism.scripts.macro_registry as reg
    hy = next(e for e in reg.read_registry(SLUG, VARIANT)["inputs"] if e["name"] == "HY OAS")
    assert hy["monitoring"]["enabled"] is False


def test_monitoring_toggle_404_unknown_input(macro_web_client):
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/monitoring",
                              data={"name": "不存在的输入", "enabled": "true"}, follow_redirects=False)
    assert r.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_monitoring_toggle_post_sets_enabled -p no:cacheprovider -q`
Expected: FAIL — 405/404（POST 路由不存在）。

- [ ] **Step 3a: 确认 `app/routes/prism.py` 顶部导入** 含 `Form` 与 `RedirectResponse`；缺则加：

```python
from fastapi import Form
from fastapi.responses import RedirectResponse
```

（若文件已从 `fastapi` 导入其它名，把 `Form` 并进现有 import 行即可。）

- [ ] **Step 3b: 新增 POST 路由**（紧跟 `prism_macro_inputs` 之后）：

```python
@router.post("/{slug}/{variant}/macro-inputs/monitoring")
def prism_macro_monitoring(slug: str, variant: str,
                           name: str = Form(...), enabled: str = Form(...)):
    """切换某输入的 monitoring.enabled（零 LLM）。输入不存在 → 404。"""
    from prism.scripts import macro_registry as macro_reg
    try:
        registry = macro_reg.read_registry(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="登记表不存在")
    if not any(e["name"] == name for e in registry.get("inputs") or []):
        raise HTTPException(status_code=404, detail=f"输入 {name!r} 不存在")
    macro_reg.upsert_input(slug, variant, {"name": name, "monitoring": {"enabled": enabled == "true"}})
    return RedirectResponse(f"/prism/{slug}/{variant}/macro-inputs", status_code=303)
```

- [ ] **Step 3c: 替换 `macro_inputs.html` 行内监控 td**（原 `<td>{% if inp.monitoring ... %}✓{% else %}○{% endif %}</td>`）为 toggle 表单：

```jinja
      <td>
        {% set on = (inp.monitoring or {}).get('enabled', True) %}
        <form method="post" action="/prism/{{ topic.slug }}/{{ variant }}/macro-inputs/monitoring" style="margin:0">
          <input type="hidden" name="name" value="{{ inp.name }}">
          <input type="hidden" name="enabled" value="{{ 'false' if on else 'true' }}">
          <button type="submit" class="mon-toggle {{ 'on' if on else 'off' }}">{{ '✓ 监控' if on else '○ 停' }}</button>
        </form>
      </td>
```

- [ ] **Step 3d: 在 `macro_inputs.html` 的 `<style>` 末尾追加：**

```css
  .mon-toggle { font-size: 0.78em; padding: 0.15em 0.5em; border-radius: 3px; border: 1px solid #ddd; cursor: pointer; }
  .mon-toggle.on { background: #e6f4ea; color: #2d7a3a; border-color: #bfe3c8; }
  .mon-toggle.off { background: #f1f1f1; color: #999; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_monitoring_toggle_post_sets_enabled tests/test_macro_inputs_web.py::test_monitoring_toggle_404_unknown_input -p no:cacheprovider -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add app/routes/prism.py app/templates/prism/macro_inputs.html tests/test_macro_inputs_web.py
git commit -m "feat(web): 输入表 S2 监控开关（POST 切 monitoring.enabled）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: 发起重估（POST）+ S5 简报区

**Files:**
- Modify: `app/routes/prism.py`（新增 POST `/reeval`）、`app/templates/prism/macro_inputs.html`（按钮 + 简报区）
- Test: `tests/test_macro_inputs_web.py`

- [ ] **Step 1: Write the failing test** (append)

```python
def test_reeval_post_stamps_and_brief_shows(macro_web_client):
    import prism.scripts.eval_snapshot as es
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/reeval", follow_redirects=False)
    assert r.status_code == 303
    assert es.read_eval_log(SLUG, VARIANT)["reeval_pending"] is not None
    r2 = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "重估简报" in r2.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_reeval_post_stamps_and_brief_shows -p no:cacheprovider -q`
Expected: FAIL — 405/404（路由不存在）。

- [ ] **Step 3a: 新增 POST 路由**（紧跟 `prism_macro_monitoring` 之后）：

```python
@router.post("/{slug}/{variant}/reeval")
def prism_reeval(slug: str, variant: str):
    """组装重估简报 + 盖「待重判」戳（零 LLM）。真正重判在对话里做。"""
    from prism.scripts import eval_snapshot as es
    brief = es.assemble_reeval_brief(slug, variant)
    es.stamp_reeval_pending(slug, variant, brief)
    return RedirectResponse(f"/prism/{slug}/{variant}/macro-inputs#reeval-brief", status_code=303)
```

- [ ] **Step 3b: 在 `macro_inputs.html` 的 S1 报警看板之后、`<p class="hint">共 ...` 之前插入按钮 + 简报区：**

```jinja
<form method="post" action="/prism/{{ topic.slug }}/{{ variant }}/reeval" style="margin:0.6em 0">
  <button type="submit" class="reeval-btn">发起重估（组装简报）</button>
</form>
{% if reeval_pending %}
{% set b = reeval_pending.brief %}
<section id="reeval-brief" class="reeval-brief">
  <h2>重估简报 <span class="hint">· 盖戳 {{ (reeval_pending.stamped_at or '')[:19] }}</span></h2>
  <p>变化输入 {{ b.changed | length }} · 越带 {{ b.breached | length }} · 到期 {{ b.due | length }}
     · 受影响结论：{{ b.affected_conclusions | join(', ') or '—' }}</p>
  {% if b.unfetched %}<p class="hint">盲区（未抓、无法判断变化）：{{ b.unfetched | length }} 条</p>{% endif %}
  <p class="hint">拿此简报到对话发起重判；重判落地（写新评估）后此戳自动清除。</p>
</section>
{% endif %}
```

- [ ] **Step 3c: 在 `<style>` 末尾追加：**

```css
  .reeval-btn { font-size: 0.9em; padding: 0.4em 1em; border-radius: 5px; border: 1px solid #b8cfe8; background: #f0f4ff; color: #2a5db0; cursor: pointer; }
  .reeval-btn:hover { background: #dce6fb; }
  .reeval-brief { border: 1px solid #e5e5e5; border-left: 3px solid #2a5db0; border-radius: 4px; padding: 0.6em 0.9em; margin: 0.6em 0 1em; background: #fbfcff; }
  .reeval-brief h2 { font-size: 1em; margin: 0 0 0.4em; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_reeval_post_stamps_and_brief_shows -p no:cacheprovider -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routes/prism.py app/templates/prism/macro_inputs.html tests/test_macro_inputs_web.py
git commit -m "feat(web): 输入表 S5 发起重估（组装简报 + 待重判戳）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 阶段 4 — β 数据落地（源权威/可用性 + llm-web fetcher）

### Task 10: macro_registry 新字段校验（authority / availability）

**Files:**
- Modify: `prism/scripts/macro_registry.py`（顶部常量 + `validate_registry`）
- Test: `prism/scripts/test_macro_registry_fields.py`（新）

**先决：** 运行 `gitnexus_impact({target: "validate_registry", direction: "upstream"})`；HIGH/CRITICAL 先警告。

- [ ] **Step 1: Write the failing test**

`prism/scripts/test_macro_registry_fields.py`:

```python
"""β：登记表新字段 authority / availability 的枚举校验（可空，给值则须合法）。"""
import pytest
from prism.scripts import macro_registry as reg


@pytest.fixture
def tmp_reg(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path)
    reg.create_registry("m", "v")
    return "m", "v"


def _base(extra):
    return {"name": "X", "tier": "B", "cadence_type": "series",
            "mechanism": "CO", "importance": "confirming", **extra}


def test_valid_authority_availability_pass(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"authority": "official", "availability": "scripted"}))
    assert reg.validate_registry(slug, variant) == []


def test_bad_authority_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"authority": "bogus"}))
    assert any("authority" in e for e in reg.validate_registry(slug, variant))


def test_bad_availability_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"availability": "maybe"}))
    assert any("availability" in e for e in reg.validate_registry(slug, variant))


def test_absent_fields_ok(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({}))
    assert reg.validate_registry(slug, variant) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_registry_fields.py -p no:cacheprovider -q`
Expected: FAIL — `test_bad_authority_flagged` / `test_bad_availability_flagged`（当前无校验，不报错）。

- [ ] **Step 3a: 在 `macro_registry.py` 的枚举常量区（`VALID_TARGET = ...` 之后）新增：**

```python
VALID_AUTHORITY = ("official", "primary", "secondary", "aggregator")
VALID_AVAILABILITY = ("scripted", "scriptable_todo", "no_stable_source")
```

- [ ] **Step 3b: 在 `validate_registry` 的 for 循环里（`alert_series` 那条校验之后、循环末尾）新增：**

```python
        if e.get("authority") is not None and e.get("authority") not in VALID_AUTHORITY:
            errors.append(f"[{name}] authority 非法: {e.get('authority')!r}")
        if e.get("availability") is not None and e.get("availability") not in VALID_AVAILABILITY:
            errors.append(f"[{name}] availability 非法: {e.get('availability')!r}")
```

- [ ] **Step 3c: 更新 `macro_registry.py` 顶部 docstring 的 schema 段**，在 `fetch_method` 行附近补充字段说明：

```
  source_url     具体源链接（可空）
  authority      "official"|"primary"|"secondary"|"aggregator"（可空，权威性）
  availability   "scripted"|"scriptable_todo"|"no_stable_source"（可空，可脚本化判定）
  fetch_recipe   {url, parse:{json_path, date_path}}（可空，llm-web fetcher 用）
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_registry_fields.py -p no:cacheprovider -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/macro_registry.py prism/scripts/test_macro_registry_fields.py
git commit -m "feat(macro): 登记表新增 source_url/authority/availability/fetch_recipe 字段 + 校验

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: 输入表 S7 源/权威/可用性列

**Files:**
- Modify: `app/templates/prism/macro_inputs.html`（「来源」「抓取」两 td）
- Test: `tests/test_macro_inputs_web.py`

- [ ] **Step 1: Write the failing test** (append)

```python
def test_inputs_table_shows_source_and_grades(macro_web_client):
    import prism.scripts.macro_registry as reg
    reg.upsert_input(SLUG, VARIANT, {
        "name": "MOVE 债市波动率", "fetch_method": "llm-web",
        "source": "ICE", "source_url": "https://example.com/move",
        "authority": "primary", "availability": "scriptable_todo"})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "https://example.com/move" in r.text     # 具体源链接
    assert "primary" in r.text                       # 权威性
    assert "待脚本" in r.text                          # availability=scriptable_todo 的人话标签
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_inputs_table_shows_source_and_grades -p no:cacheprovider -q`
Expected: FAIL — 链接/`primary`/`待脚本` 不在文本。

- [ ] **Step 3a: 替换「来源」td**（原 `<td>{{ inp.source or '—' }}</td>`）为带链接 + 权威性：

```jinja
      <td>
        {% if inp.source_url %}<a href="{{ inp.source_url }}" target="_blank" rel="noopener">{{ inp.source or '源' }}</a>
        {% else %}{{ inp.source or '—' }}{% endif %}
        {% if inp.authority %}<span class="badge-auth">{{ inp.authority }}</span>{% endif %}
      </td>
```

- [ ] **Step 3b: 在「抓取」td 末尾（`{% endif %}</td>` 之前）追加 availability 徽章：**

```jinja
        {% if inp.availability %}
          {% set avail_label = {'scripted': '已脚本', 'scriptable_todo': '待脚本', 'no_stable_source': '无稳定源'} %}
          <span class="badge-avail avail-{{ inp.availability }}">{{ avail_label[inp.availability] }}</span>
        {% endif %}
```

- [ ] **Step 3c: 在 `<style>` 末尾追加：**

```css
  .badge-auth { font-size: 0.7em; padding: 0.1em 0.35em; border-radius: 3px; background: #eef2f7; color: #44566b; margin-left: 0.3em; }
  .badge-avail { font-size: 0.7em; padding: 0.1em 0.35em; border-radius: 3px; margin-left: 0.3em; }
  .avail-scripted { background: #e6f4ea; color: #2d7a3a; }
  .avail-scriptable_todo { background: #fff7ed; color: #b45309; }
  .avail-no_stable_source { background: #f1f1f1; color: #888; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_inputs_table_shows_source_and_grades -p no:cacheprovider -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/templates/prism/macro_inputs.html tests/test_macro_inputs_web.py
git commit -m "feat(web): 输入表 S7 具体源链接 + 权威性/可用性徽章

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: llmweb_fetch.py 通用抓取脚本

**Files:**
- Create: `prism/scripts/llmweb_fetch.py`
- Test: `prism/scripts/test_llmweb_fetch.py`

- [ ] **Step 1: Write the failing test**

`prism/scripts/test_llmweb_fetch.py`:

```python
"""llm-web 通用 fetcher：仅抓 availability=='scripted' 且有 recipe 的输入；其余诚实跳过。"""
from prism.scripts import llmweb_fetch


def _fake_client(payload):
    class _Resp:
        def __init__(self, p): self._p = p
        def raise_for_status(self): pass
        def json(self): return self._p
    class _Client:
        def __init__(self, p): self._p = p
        def get(self, url, timeout=None): return _Resp(self._p)
    return _Client(payload)


def test_fetch_by_recipe_digs_json():
    client = _fake_client({"data": {"latest": "12.3", "date": "2026-06-05"}})
    recipe = {"url": "https://x", "parse": {"json_path": ["data", "latest"], "date_path": ["data", "date"]}}
    val, as_of = llmweb_fetch.fetch_by_recipe(recipe, client=client)
    assert val == 12.3 and as_of == "2026-06-05"


def test_fetch_by_recipe_missing_path_returns_none():
    client = _fake_client({"data": {}})
    recipe = {"url": "https://x", "parse": {"json_path": ["data", "nope"]}}
    val, as_of = llmweb_fetch.fetch_by_recipe(recipe, client=client)
    assert val is None


def test_run_only_fetches_scripted(monkeypatch):
    from prism.scripts import macro_registry as reg
    fake = {"inputs": [
        {"name": "已配", "fetch_method": "llm-web", "availability": "scripted",
         "fetch_recipe": {"url": "https://x", "parse": {"json_path": ["v"]}}},
        {"name": "待脚本", "fetch_method": "llm-web", "availability": "scriptable_todo"},
        {"name": "无源", "fetch_method": "llm-web", "availability": "no_stable_source"},
        {"name": "FRED 的", "fetch_method": "fred-api"},
    ]}
    monkeypatch.setattr(reg, "read_registry", lambda s, v: fake)
    monkeypatch.setattr(llmweb_fetch, "fetch_by_recipe", lambda recipe, client=None: (9.0, "2026-06-05"))
    recorded = []
    monkeypatch.setattr(reg, "record_observation",
                        lambda s, v, name, **kw: recorded.append((name, kw.get("value"))))
    summary = llmweb_fetch.run_llmweb_fetch("m", "v", client=object())
    assert recorded == [("已配", 9.0)]
    assert summary == {"fetched": 1, "skipped_todo": 1, "skipped_no_source": 1, "failed": 0}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest prism/scripts/test_llmweb_fetch.py -p no:cacheprovider -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'prism.scripts.llmweb_fetch'`.

- [ ] **Step 3: Write implementation**

`prism/scripts/llmweb_fetch.py`:

```python
"""llm-web 输入的通用抓取（β）。零 LLM：读登记表里 fetch_method=='llm-web' 且
availability=='scripted' 且有 fetch_recipe 的输入，按 recipe 抓取 → record_observation。

availability 为 scriptable_todo / no_stable_source 的跳过并计数，绝不假装抓到。判源 +
写 recipe + 评 authority/availability 是逐条增量的 LLM 工作（对话里做），本脚本只跑已配好的。
单测 mock httpx（同 fred_fetch）。"""
from __future__ import annotations

import sys

import httpx

from prism.scripts import macro_registry as reg


def _dig(obj, path):
    for key in path:
        if obj is None:
            return None
        try:
            obj = obj[key]
        except (KeyError, IndexError, TypeError):
            return None
    return obj


def fetch_by_recipe(recipe: dict, *, client=None) -> tuple[float | None, str | None]:
    """按 fetch_recipe 抓一个数值。recipe: {url, parse:{json_path:[...], date_path:[...]}}。
    仅支持 JSON 取值（json_path/date_path 是键/索引序列）。client 可注入（测试 mock）。"""
    url = recipe.get("url")
    if not url:
        return None, None
    parse = recipe.get("parse") or {}
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        resp = client.get(url, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
    finally:
        if owns:
            client.close()
    val = _dig(payload, parse.get("json_path") or [])
    as_of = _dig(payload, parse.get("date_path") or [])
    as_of = str(as_of) if as_of is not None else None
    try:
        return (float(val) if val is not None else None), as_of
    except (ValueError, TypeError):
        return None, as_of


def run_llmweb_fetch(slug: str, variant: str, *, client=None) -> dict:
    """抓所有 fetch_method=='llm-web' 且 availability=='scripted' 且有 recipe 的输入。
    待脚本 / 无稳定源 的诚实跳过并计数。返回 summary。"""
    data = reg.read_registry(slug, variant)
    fetched = skipped_todo = skipped_no_source = failed = 0
    for e in data["inputs"]:
        if e.get("fetch_method") != "llm-web":
            continue
        avail = e.get("availability")
        if avail == "no_stable_source":
            skipped_no_source += 1
            continue
        if avail != "scripted" or not e.get("fetch_recipe"):
            skipped_todo += 1
            continue
        val, as_of = fetch_by_recipe(e["fetch_recipe"], client=client)
        if val is None:
            failed += 1
            continue
        reg.record_observation(slug, variant, e["name"], value=val, as_of=as_of)
        fetched += 1
    return {"fetched": fetched, "skipped_todo": skipped_todo,
            "skipped_no_source": skipped_no_source, "failed": failed}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    print(f"llm-web 抓取: {run_llmweb_fetch(slug, variant)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest prism/scripts/test_llmweb_fetch.py -p no:cacheprovider -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/llmweb_fetch.py prism/scripts/test_llmweb_fetch.py
git commit -m "feat(macro): llm-web 通用 fetcher（仅跑 scripted，待脚本/无源诚实跳过）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 阶段 1 收尾 — 补写真实主题的首份评估快照

> 放在最后，因为它依赖阶段 2/4 的产物（eval-trace 页、新字段）已就位，便于补写后立即在 web 上肉眼核对。**本任务是 LLM 内容创作**：conclusions 的 based_on/causal 必须来自真实 `m_regime_read.md` 的结论行，不能编。

### Task 13: 补写 regime_eval_log.yaml 首份快照

**Files:**
- Create: `prism/scripts/backfill_macro_snapshot.py`（一次性脚本）
- Read（人/LLM 必读，用于填 conclusions）: `prism/topics/global-macro-rates-liquidity/opus4.8/outputs/m_regime_read.md`
- Produce（脚本运行后）: `prism/topics/global-macro-rates-liquidity/opus4.8/outputs/regime_eval_log.yaml`

- [ ] **Step 1: 读真实 regime_read，抄出结论行**

Run: `.venv/bin/python -c "print(open('prism/topics/global-macro-rates-liquidity/opus4.8/outputs/m_regime_read.md',encoding='utf-8').read())"`
从中抄出每个体制结论（利率/流动性/汇率 × 美中、象限、脆弱度）的 state，以及叙述里点名的「承重/确认」输入名（这些就是 `based_on`）。**输入名必须与 `macro_inputs.yaml` 里的 `name` 逐字一致**（否则 append_evaluation 会因悬空报错）。

- [ ] **Step 2: 写补写脚本**

`prism/scripts/backfill_macro_snapshot.py`：

```python
"""一次性：把当前 m_regime_read 的判断逆向落成首份评估快照。
input_snapshot 自动列全登记表所有输入（值取自现有 observed，未抓记 null）；
CONCLUSIONS 手填——内容来自真实 m_regime_read.md 的结论行（输入名须与登记表逐字一致）。"""
from prism.scripts import eval_snapshot as es
from prism.scripts import macro_registry as reg

SLUG, VARIANT = "global-macro-rates-liquidity", "opus4.8"

# ⚠️ 手填：每条结论的 based_on/causal 抄自真实 m_regime_read.md。input 须与登记表 name 逐字一致。
# role ∈ {load_bearing, confirming, background}。下面是结构示例，落地时按真实文档替换。
CONCLUSIONS = [
    {"id": "rates_us", "label": "美国利率体制", "state": "<抄 regime_read>",
     "based_on": [{"input": "美国政策利率", "role": "load_bearing"}],
     "causal": "<抄 regime_read 的因果句>"},
    {"id": "rates_cn", "label": "中国利率体制", "state": "<抄>", "based_on": [], "causal": "<抄>"},
    {"id": "liquidity_us", "label": "美国流动性体制", "state": "<抄>", "based_on": [], "causal": "<抄>"},
    {"id": "liquidity_cn", "label": "中国流动性体制", "state": "<抄>", "based_on": [], "causal": "<抄>"},
    {"id": "fx_cny", "label": "人民币汇率体制", "state": "<抄>", "based_on": [], "causal": "<抄>"},
    {"id": "quadrant", "label": "象限", "state": "<抄>", "based_on": [], "causal": "<抄>"},
    {"id": "fragility", "label": "脆弱度", "state": "<抄>", "based_on": [], "causal": "<抄>"},
]


def build():
    registry = reg.read_registry(SLUG, VARIANT)
    snapshot = []
    used_names = {b["input"] for c in CONCLUSIONS for b in c["based_on"]}
    for e in registry["inputs"]:
        obs = e.get("observed") or {}
        snapshot.append({
            "name": e["name"],
            "value": obs.get("value"),                 # 未抓 → None（诚实）
            "as_of": (obs.get("as_of") or None),
            "used": e["name"] in used_names,
        })
    return {"note": "首份快照（由 backfill_macro_snapshot 从现有 m_regime_read 逆向补写）",
            "input_snapshot": snapshot, "conclusions": CONCLUSIONS}


def main():
    version = es.append_evaluation(SLUG, VARIANT, build())
    print(f"写入评估快照 v{version}，输入 {len(build()['input_snapshot'])} 条")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 用真实结论替换 `CONCLUSIONS` 占位**，把所有 `<抄...>` 换成 m_regime_read 的真实 state/因果句，并把每条结论真正依赖的输入填进 `based_on`（输入名逐字对齐登记表）。

- [ ] **Step 4: 运行补写脚本（会触发不变量校验）**

Run: `.venv/bin/python -m prism.scripts.backfill_macro_snapshot`
Expected: 打印 `写入评估快照 v1，输入 N 条`。若报 `悬空引用` → 说明某 based_on 输入名与登记表对不上，修名后重跑（脚本可重复运行，会累加 version；首次成功即可，多余版本可手动删 yaml 中多余条目）。

- [ ] **Step 5: 肉眼核对 + 提交**

启动 web（用户自行 `! .venv/bin/uvicorn main:app` 或既有方式），打开
`/prism/global-macro-rates-liquidity/opus4.8/eval-trace`，确认每条结论的依赖输入/因果句/现 vs 快照值都对。

```bash
git add prism/scripts/backfill_macro_snapshot.py prism/topics/global-macro-rates-liquidity/opus4.8/outputs/regime_eval_log.yaml
git commit -m "feat(macro): 补写当前 regime_read 的首份评估快照（结论←输入链）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 全量回归 & 收尾

### Task 14: 全量测试 + detect_changes

- [ ] **Step 1: 跑宏观相关测试全绿**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_snapshot.py prism/scripts/test_llmweb_fetch.py prism/scripts/test_macro_registry_fields.py tests/test_macro_inputs_web.py -p no:cacheprovider -q`
Expected: 全部 PASS。

- [ ] **Step 2: 全量回归（确认无新增失败）**

Run: `.venv/bin/python -m pytest -p no:cacheprovider -q`
Expected: 新增测试全绿；既有的 9 个预存失败（test_config_dimensions::test_arena_dimensions_is_6_tuple、test_eod_script ×3、test_fetch_financials_cn ×1、test_prism_scripts ×4）维持原样，**不得新增任何失败**。若出现新失败，定位并修复后再继续。

- [ ] **Step 3: GitNexus 变更校验**

运行 `gitnexus_detect_changes()`，确认受影响 symbol/执行流只落在本计划预期范围（eval_snapshot、llmweb_fetch、macro_registry.validate_registry、prism.py 三个新路由 + prism_macro_inputs）。HIGH/CRITICAL 先报告。

- [ ] **Step 4: 文档指针**（DRY：让后人找得到）

在 `docs/superpowers/specs/2026-06-08-macro-judgment-cockpit-and-provenance-design.md` 顶部「目标」段后加一行：
`> 实现计划：docs/superpowers/plans/2026-06-08-macro-judgment-cockpit-and-provenance.md`

```bash
git add docs/superpowers/specs/2026-06-08-macro-judgment-cockpit-and-provenance-design.md
git commit -m "docs(macro): spec 指向实现计划

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 附：阶段 → 任务 → spec 表面对照

| spec 表面 | 任务 |
|---|---|
| 脊梁 regime_eval_log + CRUD/校验 | Task 1 |
| diff_since_last + 反查 | Task 2 |
| 重估简报 + 待重判戳 | Task 3 |
| S6 评估溯源页 + tab | Task 4, 5 |
| S3 变化列 + S4 参与/支撑（含路由喂 diff） | Task 6, 7 |
| S1 报警序列专版看板 | Task 7 |
| S2 监控开关 | Task 8 |
| S5 发起重估 | Task 9 |
| β schema 字段（authority/availability/source_url/fetch_recipe） | Task 10 |
| S7 源/权威/可用性列 | Task 11 |
| llm-web 通用 fetcher | Task 12 |
| 补写首份快照 | Task 13 |
| 回归 + detect_changes + 文档指针 | Task 14 |

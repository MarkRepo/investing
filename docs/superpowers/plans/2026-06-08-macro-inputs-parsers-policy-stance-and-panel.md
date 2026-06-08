# 宏观输入层 — 解析器演进 + policy 立场 + 面板打磨 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让宏观输入→判断回路的数据层能吃 csv（不只 json）、policy 输入有可溯源的有序立场读数、面板用中文/表格/变更汇总把"变了啥"一眼讲清。

**Architecture:** 三层零-LLM 改动。引擎层：`llmweb_fetch` 加按 `kind` 派发的解析器注册表（json/csv）；`macro_registry` 加 recipe 校验 + policy 立场轴常量与校验；`eval_snapshot.diff_since_last` 对 policy 输入走立场比对（出方向词）。展示层：两个 Jinja 模板做报警表格化、变更汇总表、中文映射、悬停释义、「评估逻辑」标签。所有派生仍零-LLM；判断永远人在对话里触发。

**Tech Stack:** Python 3.14（`.venv/bin/python`）、pytest、PyYAML、httpx（mock）、FastAPI + Jinja2。

**对应 spec：** `docs/superpowers/specs/2026-06-08-macro-inputs-parsers-policy-stance-and-panel-design.md`

---

## Pre-flight（执行前必读）

- **解释器**：`.venv/bin/python`（3.14）。
- **跑测试**：`.venv/bin/python -m pytest <path> -p no:cacheprovider -q`。
- **GitNexus 纪律（CLAUDE.md 硬规则）**：修改既有函数前必须先 `gitnexus_impact({target, direction:"upstream"})`，HIGH/CRITICAL 先告警。本计划改动的既有符号有三个：`fetch_by_recipe`、`validate_registry`、`diff_since_last`——相关任务首步已列出 impact 命令。若任何 GitNexus 工具报索引陈旧，先在终端跑 `npx gitnexus analyze`。
- **提交纪律**：逐文件 `git add`（不用 `git add -A`）；commit message 结尾加
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。
- **不碰**：`prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml`（会话前就有的未提交 WIP，本计划不涉及内容填料 C）。

## 文件结构（改动地图）

| 文件 | 责任 | 本计划改动 |
|---|---|---|
| `prism/scripts/llmweb_fetch.py` | llm-web 通用抓取 | 解析器注册表 `_PARSERS`、`_parse_json`/`_parse_csv`、`fetch_by_recipe` 按 kind 派发 |
| `prism/scripts/test_llmweb_fetch.py` | 上者测试 | csv 解析、kind 派发、未知 kind 报错 |
| `prism/scripts/macro_registry.py` | 登记表 CRUD + 校验 + 立场轴常量 | recipe kind/parse 键校验；`STANCE_SCALES`/`STANCE_DIRECTION` 常量 + stance 校验 |
| `prism/scripts/test_macro_registry_fields.py` | 上者校验测试 | recipe 校验、stance 校验 |
| `prism/scripts/eval_snapshot.py` | 评估快照 diff/简报 | `diff_since_last` 对 policy 走立场比对 + 方向；`_stance_direction` 助手 |
| `prism/scripts/test_eval_snapshot.py` | 上者测试 | policy 立场 diff 方向 |
| `app/templates/prism/macro_inputs.html` | 输入源页 | 报警表格化、变更汇总表、中文映射、cadence/mechanism 悬停 |
| `app/templates/prism/eval_trace.html` | 评估溯源页 | 「评估逻辑」标签 |
| `tests/test_macro_inputs_web.py` | web 渲染测试 | 报警表、变更汇总三态、中文映射、评估逻辑标签 |

---

## Task 1: fetcher 解析器注册表（json/csv + kind 派发）

把 `fetch_by_recipe` 从 JSON-only 升级为按 `kind` 派发的声明式解析器注册表。json 逻辑原样搬进 `_parse_json`（向后兼容：kind 缺省 json）；新增 `_parse_csv`。

**Files:**
- Modify: `prism/scripts/llmweb_fetch.py`
- Test: `prism/scripts/test_llmweb_fetch.py`

- [ ] **Step 0: 改既有符号前先跑 impact（CLAUDE.md 硬规则）**

运行：`gitnexus_impact({target: "fetch_by_recipe", direction: "upstream"})`
向用户报告爆炸半径（直接调用方 / 受影响流程 / 风险级别）。HIGH/CRITICAL 先告警再继续。
（已知调用方：`run_llmweb_fetch` 同文件内；签名不变，风险应为 LOW。）

- [ ] **Step 1: 写失败测试（csv 解析 + kind 派发 + 未知 kind 报错）**

在 `prism/scripts/test_llmweb_fetch.py` 顶部，把 `from prism.scripts import llmweb_fetch` 改为加 `import pytest`：

```python
import pytest

from prism.scripts import llmweb_fetch
```

在文件末尾追加：

```python
def _fake_text_client(text):
    class _Resp:
        def __init__(self, t): self.text = t
        def raise_for_status(self): pass
    class _Client:
        def __init__(self, t): self._t = t
        def get(self, url, timeout=None): return _Resp(self._t)
    return _Client(text)


def test_fetch_csv_latest_row():
    csv_text = "DATE,Value\n2026-06-01,10.5\n2026-06-05,12.3\n"
    recipe = {"kind": "csv", "url": "https://x",
              "parse": {"value_column": "Value", "date_column": "DATE", "row": "latest"}}
    val, as_of = llmweb_fetch.fetch_by_recipe(recipe, client=_fake_text_client(csv_text))
    assert val == 12.3 and as_of == "2026-06-05"


def test_fetch_csv_first_row():
    csv_text = "DATE,Value\n2026-06-01,10.5\n2026-06-05,12.3\n"
    recipe = {"kind": "csv", "url": "https://x",
              "parse": {"value_column": "Value", "date_column": "DATE", "row": "first"}}
    val, as_of = llmweb_fetch.fetch_by_recipe(recipe, client=_fake_text_client(csv_text))
    assert val == 10.5 and as_of == "2026-06-01"


def test_fetch_csv_missing_column_returns_none():
    csv_text = "DATE,Value\n2026-06-05,12.3\n"
    recipe = {"kind": "csv", "url": "https://x", "parse": {"value_column": "Nope"}}
    val, as_of = llmweb_fetch.fetch_by_recipe(recipe, client=_fake_text_client(csv_text))
    assert val is None


def test_unknown_kind_raises():
    recipe = {"kind": "xml", "url": "https://x", "parse": {}}
    with pytest.raises(ValueError, match="未知"):
        llmweb_fetch.fetch_by_recipe(recipe, client=_fake_text_client("x"))
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest prism/scripts/test_llmweb_fetch.py -p no:cacheprovider -q`
Expected: FAIL（csv 走 json 解析返回 None / 未知 kind 不报错）。

- [ ] **Step 3: 实现解析器注册表 + kind 派发**

在 `prism/scripts/llmweb_fetch.py`，把顶部 imports 补上 `csv` 和 `io`：

```python
from __future__ import annotations

import csv
import io
import sys

import httpx

from prism.scripts import macro_registry as reg
```

保留现有 `_dig` 不动。把现有 `fetch_by_recipe`（整段，从 `def fetch_by_recipe` 到其 `return ... as_of` 结束）替换为：

```python
def _parse_json(payload, cfg) -> tuple[float | None, str | None]:
    """JSON 取值：json_path/date_path 是键/索引序列（原 fetch_by_recipe 逻辑）。"""
    val = _dig(payload, cfg.get("json_path") or [])
    as_of = _dig(payload, cfg.get("date_path") or [])
    as_of = str(as_of) if as_of is not None else None
    try:
        return (float(val) if val is not None else None), as_of
    except (ValueError, TypeError):
        return None, as_of


def _parse_csv(text, cfg) -> tuple[float | None, str | None]:
    """CSV 取值：value_column 取列、row 选行（latest=末行/first=首行/整数=索引）、
    date_column 取日期。值转 float 失败 → (None, as_of)。诚实降级，不抛。"""
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        return None, None
    sel = cfg.get("row", "latest")
    if sel == "latest":
        r = rows[-1]
    elif sel == "first":
        r = rows[0]
    else:
        try:
            r = rows[int(sel)]
        except (ValueError, IndexError, TypeError):
            return None, None
    raw = r.get(cfg.get("value_column"))
    date_col = cfg.get("date_column")
    as_of = str(r.get(date_col)) if date_col and r.get(date_col) is not None else None
    try:
        return (float(raw) if raw not in (None, "") else None), as_of
    except (ValueError, TypeError):
        return None, as_of


_PARSERS = {"json": _parse_json, "csv": _parse_csv}


def fetch_by_recipe(recipe: dict, *, client=None) -> tuple[float | None, str | None]:
    """按 fetch_recipe 抓一个数值。recipe: {kind?, url, parse:{...}}。
    kind 缺省 'json'（向后兼容现有写法）；按 kind 派发解析器。未知 kind 抛 ValueError
    （不静默）。client 可注入（测试 mock）。"""
    url = recipe.get("url")
    if not url:
        return None, None
    kind = recipe.get("kind", "json")
    parser = _PARSERS.get(kind)
    if parser is None:
        raise ValueError(f"未知 fetch_recipe.kind: {kind!r}（支持 {sorted(_PARSERS)}）")
    parse = recipe.get("parse") or {}
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        resp = client.get(url, timeout=30)
        resp.raise_for_status()
        payload = resp.json() if kind == "json" else resp.text
    finally:
        if owns:
            client.close()
    return parser(payload, parse)
```

- [ ] **Step 4: 跑测试确认通过（含旧 json 测试回归）**

Run: `.venv/bin/python -m pytest prism/scripts/test_llmweb_fetch.py -p no:cacheprovider -q`
Expected: PASS（旧 `test_fetch_by_recipe_digs_json` / `test_run_only_fetches_scripted` 仍绿，新增 4 条绿）。

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/llmweb_fetch.py prism/scripts/test_llmweb_fetch.py
git commit -m "feat(prism): llm-web fetcher 解析器注册表（json/csv + kind 派发）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: recipe kind/parse 键校验（macro_registry）

`validate_registry` 增加 recipe 校验：`fetch_recipe.kind` 必须在已知集；按 kind 检查必填 parse 键（json 需 `json_path`，csv 需 `value_column`）。无 `fetch_recipe` 不触发（字段可空）。

**Files:**
- Modify: `prism/scripts/macro_registry.py`
- Test: `prism/scripts/test_macro_registry_fields.py`

- [ ] **Step 0: 改既有符号前先跑 impact**

运行：`gitnexus_impact({target: "validate_registry", direction: "upstream"})`
报告爆炸半径并按 HIGH/CRITICAL 规则告警。（仅新增校验分支、不改签名，风险应为 LOW。）

- [ ] **Step 1: 写失败测试**

在 `prism/scripts/test_macro_registry_fields.py` 末尾追加：

```python
def test_recipe_json_default_requires_json_path(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"fetch_recipe": {"url": "https://x", "parse": {}}}))
    assert any("json_path" in e for e in reg.validate_registry(slug, variant))


def test_recipe_csv_requires_value_column(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base(
        {"fetch_recipe": {"kind": "csv", "url": "https://x", "parse": {"date_column": "DATE"}}}))
    assert any("value_column" in e for e in reg.validate_registry(slug, variant))


def test_recipe_unknown_kind_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base(
        {"fetch_recipe": {"kind": "xml", "url": "https://x", "parse": {}}}))
    assert any("kind" in e for e in reg.validate_registry(slug, variant))


def test_recipe_valid_csv_passes(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base(
        {"fetch_recipe": {"kind": "csv", "url": "https://x", "parse": {"value_column": "Value"}}}))
    assert reg.validate_registry(slug, variant) == []
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_registry_fields.py -p no:cacheprovider -q`
Expected: FAIL（尚无 recipe 校验）。

- [ ] **Step 3: 加常量 + 校验分支**

在 `prism/scripts/macro_registry.py` 的枚举常量区（`VALID_AVAILABILITY = (...)` 行之后）加：

```python
VALID_RECIPE_KIND = ("json", "csv")   # 须与 llmweb_fetch._PARSERS 键一致
_RECIPE_REQUIRED_PARSE = {"json": "json_path", "csv": "value_column"}  # 每 kind 的必填 parse 键
```

在 `validate_registry` 的 for 循环内，把现有 `availability` 校验块（结尾两行）：

```python
        if e.get("availability") is not None and e.get("availability") not in VALID_AVAILABILITY:
            errors.append(f"[{name}] availability 非法: {e.get('availability')!r}")
```

替换为（在其后追加 recipe 校验）：

```python
        if e.get("availability") is not None and e.get("availability") not in VALID_AVAILABILITY:
            errors.append(f"[{name}] availability 非法: {e.get('availability')!r}")
        recipe = e.get("fetch_recipe")
        if recipe:
            kind = recipe.get("kind", "json")
            if kind not in VALID_RECIPE_KIND:
                errors.append(f"[{name}] fetch_recipe.kind 非法: {kind!r}")
            else:
                req = _RECIPE_REQUIRED_PARSE[kind]
                if not (recipe.get("parse") or {}).get(req):
                    errors.append(f"[{name}] fetch_recipe kind={kind} 缺 parse.{req}")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_registry_fields.py -p no:cacheprovider -q`
Expected: PASS（旧 4 条 + 新 4 条全绿）。

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/macro_registry.py prism/scripts/test_macro_registry_fields.py
git commit -m "feat(prism): 登记表 fetch_recipe kind/parse 键校验

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: policy 立场轴常量 + stance 校验（macro_registry）

加 4 根有序立场轴常量（轴名→档位元组）与方向取词常量，供校验与 diff 共用。`validate_registry` 校验：`stance_scale` 须合法轴；设了 `observed.stance` 则须声明轴、档位合法、附非空 `evidence`。

**Files:**
- Modify: `prism/scripts/macro_registry.py`
- Test: `prism/scripts/test_macro_registry_fields.py`

- [ ] **Step 1: 写失败测试**

在 `prism/scripts/test_macro_registry_fields.py` 末尾追加：

```python
def _policy(extra_obs):
    return {"name": "货政报告", "tier": "B", "cadence_type": "policy",
            "mechanism": "CO", "importance": "confirming",
            "stance_scale": "hawk_dove", "observed": extra_obs}


def test_valid_stance_passes(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _policy({"stance": "偏鹰", "evidence": "删去'保持耐心'"}))
    assert reg.validate_registry(slug, variant) == []


def test_bad_stance_scale_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"stance_scale": "bogus"}))
    assert any("stance_scale" in e for e in reg.validate_registry(slug, variant))


def test_stance_off_scale_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _policy({"stance": "扩张", "evidence": "x"}))
    assert any("不在轴" in e for e in reg.validate_registry(slug, variant))


def test_stance_without_scale_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"observed": {"stance": "偏鹰", "evidence": "x"}}))
    assert any("未声明 stance_scale" in m for m in reg.validate_registry(slug, variant))


def test_stance_without_evidence_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _policy({"stance": "偏鹰"}))   # 无 evidence
    assert any("evidence" in m for m in reg.validate_registry(slug, variant))
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_registry_fields.py -p no:cacheprovider -q`
Expected: FAIL（尚无 stance 校验）。

- [ ] **Step 3: 加立场轴常量 + 校验分支**

在 `prism/scripts/macro_registry.py` 的常量区（Task 2 加的 `_RECIPE_REQUIRED_PARSE` 行之后）加：

```python
# policy 立场有序轴：轴名 → 档位元组（有序，索引升=趋势的"高"端）。diff 按索引差算方向。
STANCE_SCALES = {
    "hawk_dove": ("鸽", "偏鸽", "中性", "偏鹰", "鹰"),
    "ease_tighten": ("宽松", "偏松", "中性", "偏紧", "收紧"),
    "expand_contract": ("扩张", "中性", "收缩"),
    "path_shift": ("上移", "不变", "下移"),
}
# 每轴方向取词：(索引上升时词, 索引下降时词)
STANCE_DIRECTION = {
    "hawk_dove": ("更鹰", "更鸽"),
    "ease_tighten": ("更紧", "更松"),
    "expand_contract": ("更收缩", "更扩张"),
    "path_shift": ("更下移", "更上移"),
}
```

在 `validate_registry` 的 for 循环内，把 Task 2 加的 recipe 校验块末尾（紧接 `errors.append(f"[{name}] fetch_recipe kind={kind} 缺 parse.{req}")` 之后）追加 stance 校验：

```python
        scale = e.get("stance_scale")
        if scale is not None and scale not in STANCE_SCALES:
            errors.append(f"[{name}] stance_scale 非法: {scale!r}")
        stance = (e.get("observed") or {}).get("stance")
        if stance is not None:
            if scale is None:
                errors.append(f"[{name}] 设了 observed.stance 但未声明 stance_scale")
            elif scale in STANCE_SCALES and stance not in STANCE_SCALES[scale]:
                errors.append(f"[{name}] stance {stance!r} 不在轴 {scale} 档位内")
            if not str((e.get("observed") or {}).get("evidence") or "").strip():
                errors.append(f"[{name}] 设了 observed.stance 必须附 evidence")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_registry_fields.py -p no:cacheprovider -q`
Expected: PASS（全绿）。

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/macro_registry.py prism/scripts/test_macro_registry_fields.py
git commit -m "feat(prism): policy 立场有序轴常量 + stance/evidence 校验

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: policy 立场 diff + 方向（eval_snapshot）

`diff_since_last` 对声明了 `stance_scale` 的输入走立场比对：新增 `stance`/`snapshot_stance`/`direction` 字段，按档位索引差出方向词；不算数值 delta、不显示越带。数值输入这三个字段为 None。

**Files:**
- Modify: `prism/scripts/eval_snapshot.py`
- Test: `prism/scripts/test_eval_snapshot.py`

- [ ] **Step 0: 改既有符号前先跑 impact**

运行：`gitnexus_impact({target: "diff_since_last", direction: "upstream"})`
报告爆炸半径并按 HIGH/CRITICAL 规则告警。（已知消费方：`assemble_reeval_brief` 同文件、web 路由 `prism_macro_inputs`/`prism_eval_trace`、两个模板。只新增字段、不删旧字段，风险应为 LOW/MEDIUM。）

- [ ] **Step 1: 写失败测试**

在 `prism/scripts/test_eval_snapshot.py` 末尾追加：

```python
def test_diff_policy_stance_direction(tmp_topic):
    slug, variant = tmp_topic
    reg.upsert_input(slug, variant, {
        "name": "C", "tier": "B", "cadence_type": "policy", "mechanism": "CO",
        "importance": "confirming", "stance_scale": "hawk_dove",
        "observed": {"stance": "偏鹰", "evidence": "x"}})
    ev = _ev_all()
    ev["input_snapshot"].append(                       # 上次 C 为 中性
        {"name": "C", "stance": "中性", "as_of": "2026-05-01", "used": True})
    es.append_evaluation(slug, variant, ev)
    diff = {d["name"]: d for d in es.diff_since_last(slug, variant)}
    assert diff["C"]["changed"] is True
    assert diff["C"]["snapshot_stance"] == "中性"
    assert diff["C"]["stance"] == "偏鹰"
    assert diff["C"]["direction"] == "更鹰"
    assert diff["C"]["delta"] is None                  # policy 不算数值 delta
    assert diff["C"]["breached"] is False              # policy 无报警带
    assert diff["A"]["stance"] is None                 # 数值输入立场字段为 None
    assert diff["A"]["direction"] is None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_snapshot.py::test_diff_policy_stance_direction -p no:cacheprovider -q`
Expected: FAIL（diff 行无 stance/direction 键 → KeyError）。

- [ ] **Step 3: 加 `_stance_direction` 助手 + diff policy 分支**

在 `prism/scripts/eval_snapshot.py`，在 `diff_since_last` 函数定义之前加助手：

```python
def _stance_direction(scale, prev, cur):
    """policy 立场方向：按档位索引差取轴方向词。无变化 / 缺档 / 未知轴 → None。"""
    levels = reg.STANCE_SCALES.get(scale)
    if not levels or prev is None or cur is None or prev == cur:
        return None
    try:
        delta = levels.index(cur) - levels.index(prev)
    except ValueError:
        return None
    up, down = reg.STANCE_DIRECTION[scale]
    return up if delta > 0 else down
```

把 `diff_since_last` 的 for 循环体（从 `name = e["name"]` 到 `out.append(row)`）整体替换为：

```python
        name = e["name"]
        live = (e.get("observed") or {}).get("value")
        snap = snap_by_name.get(name) or {}
        snap_val = snap.get("value")
        row = {
            "name": name, "snapshot_value": snap_val, "live_value": live,
            "delta": None, "changed": None if latest is None else False,
            "breached": False, "used": bool(snap.get("used")),
            "conclusions": conclusions_for_input(latest, name) if latest else [],
            "stance": None, "snapshot_stance": None, "direction": None,
        }
        scale = e.get("stance_scale")
        if scale:                                  # policy 输入：走立场比对，不碰数值
            live_stance = (e.get("observed") or {}).get("stance")
            snap_stance = snap.get("stance")
            row["snapshot_value"] = None
            row["live_value"] = None
            row["stance"] = live_stance
            row["snapshot_stance"] = snap_stance
            if latest is not None:
                row["changed"] = live_stance != snap_stance
                row["direction"] = _stance_direction(scale, snap_stance, live_stance)
            out.append(row)
            continue
        if latest is not None:
            if isinstance(live, (int, float)) and isinstance(snap_val, (int, float)):
                row["delta"] = live - snap_val
                row["changed"] = row["delta"] != 0
                row["breached"] = reg._reading_breaches(
                    {**e, "observed": {"value": live, "prev_value": snap_val}})
            else:
                row["changed"] = live != snap_val
        out.append(row)
```

- [ ] **Step 4: 跑测试确认通过（含 diff 旧测试回归）**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_snapshot.py -p no:cacheprovider -q`
Expected: PASS（旧 12 条 + 新 1 条全绿；数值 diff 行新增的 stance/direction=None 不影响旧断言）。

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/eval_snapshot.py prism/scripts/test_eval_snapshot.py
git commit -m "feat(prism): diff 对 policy 输入走立场比对 + 方向词

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: 承重报警序列 卡片 → 表格（macro_inputs.html）

把 `.alert-board` 的卡片堆改为表格，列：输入 / 报警带 / 上次值 / 现值 / Δ / 越带 / 支撑结论。数据源不变。删掉无用的卡片 CSS（否则 `.alert-cards` 字符串残留在 `<style>` 里会让"已改表格"的测试误判）。

**Files:**
- Modify: `app/templates/prism/macro_inputs.html`
- Test: `tests/test_macro_inputs_web.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_macro_inputs_web.py` 末尾追加：

```python
def test_alert_board_is_table(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "承重报警序列" in r.text
    assert "支撑结论" in r.text          # 表格化后新表头列
    assert "alert-cards" not in r.text   # 卡片容器类（含 CSS）已移除
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_alert_board_is_table -p no:cacheprovider -q`
Expected: FAIL（仍是卡片，`alert-cards` 出现在 CSS 里）。

- [ ] **Step 3: 报警区改表格**

把 `app/templates/prism/macro_inputs.html` 的报警区（从 `<section class="alert-board">` 到对应 `</section>`，即现有的 `<div class="alert-cards">...</div>` 整块）替换为：

```html
<section class="alert-board">
  <h2>承重报警序列（{{ alerts | length }}）</h2>
  <table class="data-table">
    <thead><tr>
      <th>输入</th><th>报警带</th><th>上次值</th><th>现值</th><th>Δ</th><th>越带</th><th>支撑结论</th>
    </tr></thead>
    <tbody>
    {% for a in alerts %}
      {% set d = diff.get(a.name) %}
      <tr{% if d and d.breached %} class="breached-row"{% endif %}>
        <td><code>{{ a.name }}</code></td>
        <td><code class="hint">{{ a.alert_band }}</code></td>
        <td>{% if d and d.snapshot_value is not none %}{{ d.snapshot_value }}{% else %}<span class="hint">—</span>{% endif %}</td>
        <td>{% if a.observed and a.observed.value is not none %}{{ a.observed.value }}{% else %}<span class="hint">未抓</span>{% endif %}</td>
        <td>{% if d and d.delta is not none and d.delta != 0 %}<span class="badge-delta">{{ '%+.4g' | format(d.delta) }}</span>{% else %}—{% endif %}</td>
        <td>{% if d and d.breached %}<span class="badge-breach">越带</span>{% else %}<span class="badge-ok">带内</span>{% endif %}</td>
        <td>{% if d and d.conclusions %}{{ d.conclusions | join(', ') }}{% else %}<span class="hint">—</span>{% endif %}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</section>
```

- [ ] **Step 4: 删卡片 CSS、加行高亮**

在同文件 `<style>` 块内，把这 5 行：

```css
  .alert-cards { display: flex; flex-wrap: wrap; gap: 0.6em; }
  .alert-card { border: 1px solid #e5e5e5; border-radius: 6px; padding: 0.5em 0.7em; min-width: 11em; font-size: 0.85em; }
  .alert-card.breached { border-color: #f0a7a0; background: #fff6f5; }
  .ac-name code { font-size: 0.95em; }
  .ac-val { margin: 0.2em 0; }
```

替换为：

```css
  .breached-row { background: #fff6f5; }
```

（保留 `.alert-board` 与 `.alert-board h2` 两行。）

- [ ] **Step 5: 跑测试确认通过（含报警旧测试回归）**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py -p no:cacheprovider -q`
Expected: PASS（`test_alert_board_is_table` 绿；`test_alert_board_shows_alert_series` 仍绿）。

- [ ] **Step 6: 提交**

```bash
git add app/templates/prism/macro_inputs.html tests/test_macro_inputs_web.py
git commit -m "feat(web): 承重报警序列 卡片改表格

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: 变更汇总表（输入页顶，三态）

页顶加变更汇总区：有快照才显示；有变化项列表（输入 / 上次→现值 / Δ 或方向 / 越带 / 影响结论），无变化项显示"自上次评估无变化"。用 Task 4 的 diff 字段（含 policy 立场）。

**Files:**
- Modify: `app/templates/prism/macro_inputs.html`
- Test: `tests/test_macro_inputs_web.py`

- [ ] **Step 1: 写失败测试（三态）**

在 `tests/test_macro_inputs_web.py` 末尾追加：

```python
def test_change_summary_no_snapshot_hidden(macro_web_client):
    # fixture 未 append_evaluation → 无快照 → 不显示变更汇总
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "变更汇总" not in r.text


def test_change_summary_lists_changed(macro_web_client):
    import prism.scripts.macro_registry as reg
    import prism.scripts.eval_snapshot as es
    reg.record_observation(SLUG, VARIANT, "HY OAS", value=3.5, as_of="2026-06-07")
    es.append_evaluation(SLUG, VARIANT, {
        "input_snapshot": [{"name": "HY OAS", "value": 3.0, "as_of": "2026-06-01", "used": True}],
        "conclusions": [{"id": "liquidity",
                         "based_on": [{"input": "HY OAS", "role": "confirming"}]}]})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "变更汇总" in r.text
    assert "3.0" in r.text and "3.5" in r.text


def test_change_summary_no_change_message(macro_web_client):
    import prism.scripts.eval_snapshot as es
    # 有快照、但 HY OAS 现值仍未抓（None）→ 有快照无变化
    es.append_evaluation(SLUG, VARIANT, {
        "input_snapshot": [{"name": "HY OAS", "value": None, "as_of": "2026-06-01", "used": False}],
        "conclusions": []})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "变更汇总" in r.text
    assert "自上次评估无变化" in r.text
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py -k change_summary -p no:cacheprovider -q`
Expected: FAIL（无变更汇总区）。

- [ ] **Step 3: 加变更汇总区**

在 `app/templates/prism/macro_inputs.html` 中，紧接 `{{ view_tabs(topic, variant, 'inputs') }}` 行之后、`{% set alerts = ... %}` 行之前插入：

```html
{% set graded = diff.values() | rejectattr('changed', 'none') | list %}
{% if graded %}
{% set changed_rows = graded | selectattr('changed') | list %}
<section class="change-summary">
  <h2>变更汇总 <span class="hint">· 自上次评估</span></h2>
  {% if changed_rows %}
  <table class="data-table">
    <thead><tr>
      <th>输入</th><th>上次 → 现值</th><th>Δ / 方向</th><th>越带</th><th>影响结论</th>
    </tr></thead>
    <tbody>
    {% for d in changed_rows %}
      <tr>
        <td><code>{{ d.name }}</code></td>
        <td>
          {% if d.stance is not none or d.snapshot_stance is not none %}
            {{ d.snapshot_stance or '—' }} → {{ d.stance or '—' }}
          {% else %}
            {{ d.snapshot_value if d.snapshot_value is not none else '—' }} → {{ d.live_value if d.live_value is not none else '—' }}
          {% endif %}
        </td>
        <td>
          {% if d.direction %}<span class="badge-delta">{{ d.direction }}</span>
          {% elif d.delta is not none and d.delta != 0 %}<span class="badge-delta">{{ '%+.4g' | format(d.delta) }}</span>
          {% else %}—{% endif %}
        </td>
        <td>{% if d.breached %}<span class="badge-breach">越带</span>{% else %}—{% endif %}</td>
        <td>{% if d.conclusions %}{{ d.conclusions | join(', ') }}{% else %}<span class="hint">—</span>{% endif %}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
  <p class="hint">自上次评估无变化。</p>
  {% endif %}
</section>
{% endif %}
```

- [ ] **Step 4: 加变更汇总 CSS**

在同文件 `<style>` 块内，`.alert-board { ... }` 行之前加：

```css
  .change-summary { margin: 0.8em 0 1.2em; }
  .change-summary h2 { font-size: 1em; margin: 0 0 0.5em; }
```

- [ ] **Step 5: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py -p no:cacheprovider -q`
Expected: PASS（三态测试全绿，其余 web 测试不回归）。

- [ ] **Step 6: 提交**

```bash
git add app/templates/prism/macro_inputs.html tests/test_macro_inputs_web.py
git commit -m "feat(web): 输入页顶变更汇总表（有变化/无变化/无快照三态）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: 中文显示映射 + cadence/mechanism 悬停（macro_inputs.html）

模板内建映射字典，把 频率/目标/重要性 渲染成中文；cadence、mechanism 加 `title` 悬停释义。mechanism 现未在表中显示——新增「机制」列（值不变、加 tooltip）。

**Files:**
- Modify: `app/templates/prism/macro_inputs.html`
- Test: `tests/test_macro_inputs_web.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_macro_inputs_web.py` 末尾追加：

```python
def test_inputs_table_chinese_labels(macro_web_client):
    # fixture HY OAS：cadence series / targets liquidity / importance confirming
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "序列" in r.text       # cadence series → 序列
    assert "流动性" in r.text      # target liquidity → 流动性
    assert "确认" in r.text        # importance confirming → 确认


def test_inputs_table_cadence_tooltip(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "可连续抓取的常规时间序列" in r.text   # series 悬停释义


def test_inputs_table_mechanism_tooltip(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "同步读数" in r.text     # HY OAS mechanism CO → 悬停释义
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py -k "chinese_labels or cadence_tooltip or mechanism_tooltip" -p no:cacheprovider -q`
Expected: FAIL（仍渲染英文枚举、无 tooltip、无机制列）。

- [ ] **Step 3: 定义映射字典**

在 `app/templates/prism/macro_inputs.html` 中，紧接 `{% block content %}` 之后插入映射定义：

```html
{% set cadence_label = {'event': '事件', 'policy': '政策', 'series': '序列'} %}
{% set cadence_tip = {'event': '不定期事件（如 FOMC 会议、数据发布日）', 'policy': '政策发布（如 LPR、货政报告）', 'series': '可连续抓取的常规时间序列'} %}
{% set target_label = {'rates': '利率', 'liquidity': '流动性', 'fx': '汇率'} %}
{% set importance_label = {'load_bearing': '承重', 'confirming': '确认', 'background': '背景'} %}
{% set mechanism_tip = {'CD': '因果驱动', 'CF': '资金流渠道（因果子类）', 'CO': '同步读数', 'CR': '仅相关'} %}
```

- [ ] **Step 4: 表头加「机制」列**

把主表表头：

```html
  <thead><tr>
    <th>输入名</th><th>等级</th><th>频率</th><th>目标</th><th>重要性</th>
    <th>来源</th><th>抓取</th><th>上次评估值</th><th>现值 / Δ</th><th>参与·支撑</th><th>监控</th><th>报警带</th>
  </tr></thead>
```

替换为（在 频率 后插入 机制）：

```html
  <thead><tr>
    <th>输入名</th><th>等级</th><th>频率</th><th>机制</th><th>目标</th><th>重要性</th>
    <th>来源</th><th>抓取</th><th>上次评估值</th><th>现值 / Δ</th><th>参与·支撑</th><th>监控</th><th>报警带</th>
  </tr></thead>
```

- [ ] **Step 5: 行内三格中文化 + 机制格**

把主表行里频率/目标/重要性这三格：

```html
      <td>{{ inp.cadence_type or '—' }}</td>
      <td>{{ (inp.targets or []) | join(', ') }}</td>
      <td>{{ inp.importance or '—' }}</td>
```

替换为（频率中文化 + 新增机制格 + 目标/重要性中文化）：

```html
      <td>{% if inp.cadence_type %}<span title="{{ cadence_tip.get(inp.cadence_type, '') }}">{{ cadence_label.get(inp.cadence_type, inp.cadence_type) }}</span>{% else %}—{% endif %}</td>
      <td>{% if inp.mechanism %}<span title="{{ mechanism_tip.get(inp.mechanism, '') }}">{{ inp.mechanism }}</span>{% else %}—{% endif %}</td>
      <td>{% for t in inp.targets or [] %}{{ target_label.get(t, t) }}{% if not loop.last %}, {% endif %}{% endfor %}</td>
      <td>{{ importance_label.get(inp.importance, inp.importance or '—') }}</td>
```

- [ ] **Step 6: 跑测试确认通过（含旧 web 测试回归）**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py -p no:cacheprovider -q`
Expected: PASS（中文/tooltip 三测绿；`test_macro_inputs_table_renders` 等旧测试不回归）。

- [ ] **Step 7: 提交**

```bash
git add app/templates/prism/macro_inputs.html tests/test_macro_inputs_web.py
git commit -m "feat(web): 输入表中文映射 + cadence/mechanism 悬停释义（含机制列）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: eval-trace 加「评估逻辑」标签（eval_trace.html）

每条结论 `causal` 段前加浅色小标签「评估逻辑」，明确这段是判断逻辑、下表是它依赖的输入。

**Files:**
- Modify: `app/templates/prism/eval_trace.html`
- Test: `tests/test_macro_inputs_web.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_macro_inputs_web.py` 末尾追加：

```python
def test_eval_trace_has_logic_label(macro_web_client):
    import prism.scripts.eval_snapshot as es
    es.append_evaluation(SLUG, VARIANT, {
        "input_snapshot": [{"name": "HY OAS", "value": 3.1, "as_of": "2026-06-01", "used": True}],
        "conclusions": [{"id": "liquidity", "label": "流动性体制", "state": "偏紧",
                         "based_on": [{"input": "HY OAS", "role": "confirming"}],
                         "causal": "HY OAS 走阔 → 流动性偏紧"}]})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/eval-trace")
    assert "评估逻辑" in r.text
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py::test_eval_trace_has_logic_label -p no:cacheprovider -q`
Expected: FAIL（无「评估逻辑」标签）。

- [ ] **Step 3: 加标签 + CSS**

在 `app/templates/prism/eval_trace.html`，把：

```html
    {% if c.causal %}<p class="concl-causal">{{ c.causal }}</p>{% endif %}
```

替换为：

```html
    {% if c.causal %}<p class="concl-causal"><span class="logic-label">评估逻辑</span> {{ c.causal }}</p>{% endif %}
```

在同文件 `<style>` 块内，`.concl-causal { ... }` 行之后加：

```css
  .logic-label { font-size: 0.72em; color: #999; background: #f5f5f5; padding: 0.1em 0.4em; border-radius: 3px; margin-right: 0.4em; }
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py -k eval_trace -p no:cacheprovider -q`
Expected: PASS（`test_eval_trace_has_logic_label` 绿；`test_eval_trace_renders_conclusions` 不回归）。

- [ ] **Step 5: 提交**

```bash
git add app/templates/prism/eval_trace.html tests/test_macro_inputs_web.py
git commit -m "feat(web): eval-trace 结论加「评估逻辑」标签

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 收尾：全量回归 + detect_changes

- [ ] **Step 1: 跑三个脚本测试 + web 测试全绿**

```bash
.venv/bin/python -m pytest prism/scripts/test_llmweb_fetch.py prism/scripts/test_macro_registry_fields.py prism/scripts/test_eval_snapshot.py tests/test_macro_inputs_web.py -p no:cacheprovider -q
```
Expected: 全 PASS。

- [ ] **Step 2: 提交前查影响范围（CLAUDE.md 硬规则）**

运行 `gitnexus_detect_changes()`，确认改动只触及预期符号/流程（`fetch_by_recipe`、`validate_registry`、`diff_since_last` 及两个模板）。若索引陈旧先 `npx gitnexus analyze`。

---

## 测试策略表（spec ↔ 任务）

| spec 测试项 | 任务 | 文件 |
|---|---|---|
| csv 解析按列/行取值与日期 | T1 | test_llmweb_fetch.py |
| kind 派发 json/csv；未知 kind 报错 | T1 | test_llmweb_fetch.py |
| recipe 缺必填 parse 键报错 | T2 | test_macro_registry_fields.py |
| stance_scale 非法 / stance 越档 / 缺 evidence 报错 | T3 | test_macro_registry_fields.py |
| policy diff 立场方向（更鹰）正确 | T4 | test_eval_snapshot.py |
| 报警表格渲染 | T5 | test_macro_inputs_web.py |
| 变更汇总表三态 | T6 | test_macro_inputs_web.py |
| 中文映射（targets/importance/cadence）+ mechanism 悬停 | T7 | test_macro_inputs_web.py |
| eval-trace「评估逻辑」标签 | T8 | test_macro_inputs_web.py |

## 不做（YAGNI，承自 spec）

- html 解析器（留 `kind` 扩展点，注册表加一个 parser 即可）。
- 逐条填 recipe / 判源评权威 / 填 policy 立场 / 补术语表（内容填料 C，另走一轮）。
- policy 立场数值化打分（有序档位足够）。
- 报警带应用到 policy（policy 无带，只报方向）。
- `record_observation` 扩展写 stance（C 期内容填料用 `upsert_input` 直接写 observed 即可）。

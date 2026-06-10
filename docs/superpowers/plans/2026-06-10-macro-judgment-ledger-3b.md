# 宏观层判断台账（阶段 3b）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给每条 regime 结论的承重输入写下可证伪的方向预测（`expected`），事后由零-LLM 脚本拿实际序列机械裁决「判得对不对」，并把战绩在 eval-trace web 面摊开、老错的机制边浮成降级候选。

**Architecture:** 在既有 `regime_eval_log.yaml` 脊梁上**只追加**两件事——`based_on` 边加 `expected` 方向词（写时校验，承重数值/立场边强制）+ 评估条目可带 `prior_verdict`（append-only 落新条目、不改旧）。新增零-LLM 派生模块 `eval_score.py`（`score_edge`/`score_evaluation`/`edge_ledger`，全派生不存盘，镜像 `diff_since_last` 的「连续可算」哲学）。web eval-trace tab 加战绩卡；workflow `_macro_regime.md` Step 5 教 LLM 写 expected/prior_verdict。判断永远人在对话触发，脚本零 LLM。

**Tech Stack:** Python 3.14（`.venv/bin/python`）、pytest（`-p no:cacheprovider -q`）、PyYAML、FastAPI + Jinja2。沿用 prism 既有 yaml-sidecar / 零-LLM CRUD 模式。

**前置事实（已核实，写代码前不必再查）：**
- `prism/scripts/eval_snapshot.py`：`_validate_evaluation(evaluation, input_names)` 现校验「input_snapshot 列全 + based_on 不悬空 + role 合法」；`append_evaluation` 写 `entry={version, evaluated_at, note?, input_snapshot, conclusions}`；`record_evaluation(slug, variant, conclusions, *, note=None)` 自动列全快照 + 标 used + append；`_stance_direction(scale, prev, cur)` 已存在；`VALID_ROLE=("load_bearing","confirming","background")`；模块级 `_PRISM_ROOT`。
- `prism/scripts/macro_registry.py`：`STANCE_DIRECTION`（轴→(升词,降词)，如 `{"hawk_dove":("更鹰","更鸽"),...}`）、`STANCE_SCALES`、`read_registry`、`_reading_breaches`、`alert_band.delta`、`stance_scale`、`observed.{value,stance}`。
- eval-trace web：路由 `app/routes/prism.py` 的 `prism_eval_trace`（~line 1053，**必须在 `/{output_key}` 通配前**），模板 `app/templates/prism/eval_trace.html`，目前传 `{topic, variant, evaluation, diff}`。
- workflow：`prism/workflows/04-synthesize/_macro_regime.md` Step 5（~line 309 起）已含 `record_evaluation` 示例 + `apply_holding_staleness`/`coverage_gaps` 调用（3a 落的）。
- **回归面（仅此）**：加「承重数值/立场边强制 expected」后，唯一会破的既有写路径是 `prism/scripts/test_eval_snapshot.py` 的 `_ev_all`（输入 A 有数值 3.0）与 `test_record_evaluation_builds_snapshot_and_clears_pending`（A load_bearing）。其余测试要么用 `confirming`（web 测试），要么 `USDCNY` 在 record_evaluation 时无 observed 值（快照值 None → 非数值 → 不强制），故不破。Task 1 显式修这两处。

---

## 设计要点（实现期不要偏离）

**方向词表（`expected` 合法取值）**：数值型 `up / down / flat / up_or_flat / down_or_flat`；立场型复用 `reg.STANCE_DIRECTION` 各轴方向词（`更鹰/更鸽/更紧/更松/更收缩/更扩张/更下移/更上移`）。

**强制规则（`_validate_evaluation`）**：
- 任意 `expected`（无论 role）若给出，必须 ∈ 方向词表，否则报错。
- `load_bearing` 边：当该输入的 **input_snapshot 行有数值 `value`（int/float）或有 `stance`** 时，**缺 `expected` 报错**；行无数值无立场（未抓/纯定性）→ `expected` 可空（呼应 spec「非数值输入 expected 可空」+「未抓→neutral」）。
- confirming/background 边：`expected` 永远可选（本期不强制）。

**`prior_verdict`**：`record_evaluation`/`append_evaluation` 可选参数，写在**新评估条目**上（append-only，不改旧条目）。格式 `[{conclusion_id, verdict, note?}]`，`verdict ∈ {held, partial, wrong}`；给出时校验 verdict 合法。

**评分三态（`score_edge`）**：`hit | miss | neutral`。缺 expected / 缺基准（snapshot 或 live 为 None）→ `neutral`（不计入命中/失手）。数值按方向 + 容差（仅 `flat` 及 `_or_flat` 边界用容差 `tol`，默认 0.0，由 `alert_band.delta` 供）。立场走 `_stance_direction`：无移动/不可比 → `neutral`（保守，不冤判）。

**全派生不存盘**：`score_*`/`edge_ledger` 每次现算，唯一存盘的人工动作是 `prior_verdict`。

**GitNexus 纪律**：Task 1/2 改既有 symbol `_validate_evaluation`/`append_evaluation`/`record_evaluation`、Task 6 改 `prism_eval_trace` 前，按 CLAUDE.md 先 `gitnexus_impact({target, direction:"upstream"})` 报爆炸半径，HIGH/CRITICAL 先警告；每个 commit 前 `gitnexus_detect_changes()` 核范围。

---

## File Structure

| 文件 | 职责 | 动作 |
|------|------|------|
| `prism/scripts/eval_snapshot.py` | 评估快照 CRUD + 校验 | 改：加 `expected` 校验 + `prior_verdict` 落条目 |
| `prism/scripts/eval_score.py` | 零-LLM 战绩派生（score_edge/score_evaluation/edge_ledger） | **新建** |
| `prism/scripts/test_eval_snapshot.py` | 快照校验回归 | 改：修 2 处 fixture + 加 expected/prior_verdict 测试 |
| `prism/scripts/test_eval_score.py` | 战绩派生测试 | **新建** |
| `app/routes/prism.py` | eval-trace 路由 | 改：`prism_eval_trace` 传 score + ledger |
| `app/templates/prism/eval_trace.html` | 评估溯源页 | 改：加战绩卡区 + 边预测/战绩列 |
| `tests/test_macro_inputs_web.py` | web 回归 | 改：加战绩卡渲染测试 |
| `prism/workflows/04-synthesize/_macro_regime.md` | macro 合成 Step 5 | 改：示例加 expected + 战绩卡/prior_verdict 流程 |

---

## Task 1: `expected` 方向预测校验

**Files:**
- Modify: `prism/scripts/eval_snapshot.py`（加方向词常量 + `_validate_evaluation` 校验）
- Test: `prism/scripts/test_eval_snapshot.py`（修 2 处既有 fixture + 加新测试）

- [ ] **Step 0: GitNexus 影响分析**

Run: `gitnexus_impact({target: "_validate_evaluation", direction: "upstream"})`，报直接调用方（`append_evaluation`）+ 风险级别给用户。LOW/MEDIUM 直接进；HIGH/CRITICAL 先警告。

- [ ] **Step 1: 修既有 fixture，先让回归测试在新规则下仍绿（写校验前先备好兼容）**

在 `prism/scripts/test_eval_snapshot.py` 中，把 `_ev_all` 默认结论的承重边补 `expected`（A 有数值 3.0 → 受强制）：

```python
def _ev_all(extra_conclusions=None):
    """列全 A、B 两条输入的最小 evaluation（满足"必须列全"不变量）。"""
    return {
        "input_snapshot": [
            {"name": "A", "value": 3.0, "as_of": "2026-05-01", "used": True},
            {"name": "B", "value": None, "as_of": None, "used": False},
        ],
        "conclusions": extra_conclusions if extra_conclusions is not None else [
            {"id": "rates", "label": "利率", "state": "紧",
             "based_on": [{"input": "A", "role": "load_bearing", "expected": "up_or_flat"}],
             "causal": "A→紧"}],
    }
```

并把 `test_record_evaluation_builds_snapshot_and_clears_pending` 里的 conclusions（约 line 165-166）补 `expected`：

```python
    conclusions = [{"id": "rates", "label": "利率体制", "state": "紧",
                    "based_on": [{"input": "A", "role": "load_bearing", "expected": "up_or_flat"}],
                    "causal": "A→紧"}]
```

- [ ] **Step 2: 写失败测试（新校验行为）**

在 `prism/scripts/test_eval_snapshot.py` 末尾追加：

```python
def test_load_bearing_numeric_edge_requires_expected(tmp_topic):
    """承重边且该输入有数值 → 缺 expected 报错。"""
    slug, variant = tmp_topic
    ev = _ev_all([{"id": "rates", "label": "利率", "state": "紧", "causal": "c",
                   "based_on": [{"input": "A", "role": "load_bearing"}]}])  # A 有数值、缺 expected
    with pytest.raises(ValueError, match="expected"):
        es.append_evaluation(slug, variant, ev)


def test_expected_illegal_direction_word_rejected(tmp_topic):
    slug, variant = tmp_topic
    ev = _ev_all([{"id": "rates", "label": "利率", "state": "紧", "causal": "c",
                   "based_on": [{"input": "A", "role": "load_bearing", "expected": "sideways"}]}])
    with pytest.raises(ValueError, match="方向词"):
        es.append_evaluation(slug, variant, ev)


def test_load_bearing_nonnumeric_edge_expected_optional(tmp_topic):
    """承重边但该输入无数值无立场（B 是 None）→ expected 可空，不报错。"""
    slug, variant = tmp_topic
    ev = _ev_all([{"id": "x", "label": "x", "state": "s", "causal": "c",
                   "based_on": [{"input": "B", "role": "load_bearing"}]}])  # B value=None
    assert es.append_evaluation(slug, variant, ev) == 1


def test_confirming_edge_expected_optional(tmp_topic):
    """confirming 边永不强制 expected。"""
    slug, variant = tmp_topic
    ev = _ev_all([{"id": "x", "label": "x", "state": "s", "causal": "c",
                   "based_on": [{"input": "A", "role": "confirming"}]}])
    assert es.append_evaluation(slug, variant, ev) == 1


def test_stance_load_bearing_edge_requires_expected(tmp_topic):
    """承重边且该输入有 stance → 缺 expected 报错。"""
    slug, variant = tmp_topic
    ev = {
        "input_snapshot": [
            {"name": "A", "value": 3.0, "as_of": "2026-05-01", "used": False},
            {"name": "B", "value": None, "used": False},
            {"name": "C", "stance": "偏鹰", "as_of": "2026-05-01", "used": True},
        ],
        "conclusions": [{"id": "p", "label": "政策", "state": "鹰", "causal": "c",
                         "based_on": [{"input": "C", "role": "load_bearing"}]}],  # 缺 expected
    }
    reg.upsert_input(slug, variant, {
        "name": "C", "tier": "B", "cadence_type": "policy", "mechanism": "CO",
        "importance": "load_bearing", "stance_scale": "hawk_dove",
        "observed": {"stance": "偏鹰", "evidence": "x"}})
    with pytest.raises(ValueError, match="expected"):
        es.append_evaluation(slug, variant, ev)
```

- [ ] **Step 3: 跑测试看失败**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_snapshot.py -p no:cacheprovider -q`
Expected: 新 4 个 require/illegal 测试 FAIL（当前无 expected 校验，append 不报错）；2 个 optional 测试 PASS；既有测试 PASS（Step 1 已兼容）。

- [ ] **Step 4: 实现校验**

在 `prism/scripts/eval_snapshot.py` 顶部、`VALID_ROLE` 之后加方向词常量：

```python
NUMERIC_DIRECTIONS = ("up", "down", "flat", "up_or_flat", "down_or_flat")


def _valid_expected_words() -> set:
    """合法 expected 方向词：数值型 + 全部立场轴方向词（复用 registry 单一真相）。"""
    words = set(NUMERIC_DIRECTIONS)
    for pair in reg.STANCE_DIRECTION.values():
        words.update(pair)
    return words
```

在 `_validate_evaluation` 里，给 based_on 循环加 expected 校验。把现有循环体改为（保留原 input/role 检查，新增 expected 段）：

```python
    valid_dirs = _valid_expected_words()
    snap_by_name = {s.get("name"): s for s in snap if s.get("name") is not None}
    for c in evaluation.get("conclusions") or []:
        cid = c.get("id", "<无 id>")
        for b in c.get("based_on") or []:
            inp = b.get("input")
            if inp is None:               # 漏 input 键 → 显式拒，不靠 None 是否在名册里碰运气
                errors.append(f"[{cid}] based_on 缺 input 键")
            elif inp not in snap_names:
                errors.append(f"[{cid}] based_on 悬空引用: {inp!r} 不在 input_snapshot")
            if b.get("role") not in VALID_ROLE:
                errors.append(f"[{cid}] role 非法: {b.get('role')!r}")
            exp = b.get("expected")
            if exp is not None and exp not in valid_dirs:
                errors.append(f"[{cid}] expected 非法方向词: {exp!r}")
            if b.get("role") == "load_bearing" and exp is None and inp is not None:
                row = snap_by_name.get(inp) or {}
                has_numeric = isinstance(row.get("value"), (int, float))
                has_stance = row.get("stance") is not None
                if has_numeric or has_stance:
                    errors.append(f"[{cid}] load_bearing 边 {inp!r} 缺 expected 方向预测")
```

> 注：原 `_validate_evaluation` 已先建 `snap`/`snap_names`（input_snapshot 校验段），本步只在 conclusions 循环里复用并新增 `snap_by_name`。

- [ ] **Step 5: 跑测试看通过**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_snapshot.py -p no:cacheprovider -q`
Expected: 全 PASS（含新 6 个 + 既有回归）。

- [ ] **Step 6: 提交**

```bash
gitnexus_detect_changes()   # 核对仅动 eval_snapshot.py + 其测试
git add prism/scripts/eval_snapshot.py prism/scripts/test_eval_snapshot.py
git commit -m "feat(prism): regime based_on 加可证伪 expected 方向预测(承重数值/立场边强制·零-LLM 校验)"
```

---

## Task 2: 评估条目落 `prior_verdict`

**Files:**
- Modify: `prism/scripts/eval_snapshot.py`（`record_evaluation` + `append_evaluation` + `_validate_evaluation`）
- Test: `prism/scripts/test_eval_snapshot.py`

- [ ] **Step 0: GitNexus 影响分析**

Run: `gitnexus_impact({target: "record_evaluation", direction: "upstream"})`，报调用方（workflow + xcut 间接）+ 风险级别。

- [ ] **Step 1: 写失败测试**

追加到 `prism/scripts/test_eval_snapshot.py`：

```python
def test_prior_verdict_written_on_new_entry_not_old(tmp_topic):
    """prior_verdict 落新条目，不改旧条目（append-only 不可变）。"""
    slug, variant = tmp_topic
    es.append_evaluation(slug, variant, _ev_all())                       # v1：无 verdict
    conclusions = [{"id": "rates", "label": "利率", "state": "紧", "causal": "c",
                    "based_on": [{"input": "A", "role": "load_bearing", "expected": "up_or_flat"}]}]
    v2 = es.record_evaluation(slug, variant, conclusions,
                              prior_verdict=[{"conclusion_id": "rates", "verdict": "held",
                                              "note": "利率确按预测维持"}])
    assert v2 == 2
    evals = es.read_eval_log(slug, variant)["evaluations"]
    assert "prior_verdict" not in evals[0]                               # 旧条目没动
    assert evals[1]["prior_verdict"][0]["verdict"] == "held"             # 新条目带裁定


def test_prior_verdict_illegal_value_rejected(tmp_topic):
    slug, variant = tmp_topic
    conclusions = [{"id": "rates", "label": "利率", "state": "紧", "causal": "c",
                    "based_on": [{"input": "A", "role": "load_bearing", "expected": "up_or_flat"}]}]
    with pytest.raises(ValueError, match="verdict"):
        es.record_evaluation(slug, variant, conclusions,
                             prior_verdict=[{"conclusion_id": "rates", "verdict": "bogus"}])
```

- [ ] **Step 2: 跑测试看失败**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_snapshot.py -k prior_verdict -p no:cacheprovider -q`
Expected: FAIL（`record_evaluation` 还没 `prior_verdict` 参数 → TypeError）。

- [ ] **Step 3: 实现**

在 `prism/scripts/eval_snapshot.py` 的 `VALID_ROLE` 附近加：

```python
VALID_VERDICT = ("held", "partial", "wrong")
```

在 `_validate_evaluation` 末尾（`return errors` 前）加 prior_verdict 校验：

```python
    for i, pv in enumerate(evaluation.get("prior_verdict") or []):
        if pv.get("verdict") not in VALID_VERDICT:
            errors.append(f"prior_verdict[{i}] verdict 非法: {pv.get('verdict')!r}")
```

在 `append_evaluation` 组 `entry` 时（`entry["conclusions"] = ...` 之后）加：

```python
    if evaluation.get("prior_verdict"):
        entry["prior_verdict"] = evaluation["prior_verdict"]
```

把 `record_evaluation` 签名与组装改为带 `prior_verdict`：

```python
def record_evaluation(slug: str, variant: str, conclusions: list, *,
                      note: str | None = None, prior_verdict: list | None = None) -> int:
    """便利写回：用 snapshot_inputs 自动列全输入 + 据 based_on 标 used，再走 append_evaluation。

    prior_verdict（可选）= [{conclusion_id, verdict: held|partial|wrong, note?}]，对上一版判断的
    人工裁定，落在本（新）条目上、append-only 不改旧条目。降低 headless 闭环手工拼 input_snapshot 的
    漏列/悬空风险；不变量校验仍由 append_evaluation 全程把关。
    """
    used_names = {b.get("input")
                  for c in (conclusions or [])
                  for b in (c.get("based_on") or []) if b.get("input")}
    snapshot = snapshot_inputs(slug, variant)
    for s in snapshot:
        if s["name"] in used_names:
            s["used"] = True
    evaluation = {"input_snapshot": snapshot, "conclusions": conclusions or []}
    if note:
        evaluation["note"] = note
    if prior_verdict:
        evaluation["prior_verdict"] = prior_verdict
    return append_evaluation(slug, variant, evaluation)
```

- [ ] **Step 4: 跑测试看通过**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_snapshot.py -p no:cacheprovider -q`
Expected: 全 PASS。

- [ ] **Step 5: 提交**

```bash
gitnexus_detect_changes()
git add prism/scripts/eval_snapshot.py prism/scripts/test_eval_snapshot.py
git commit -m "feat(prism): record_evaluation 加 prior_verdict(人工裁定落新条目·append-only)"
```

---

## Task 3: `eval_score.score_edge`（单边三态裁决）

**Files:**
- Create: `prism/scripts/eval_score.py`
- Test: `prism/scripts/test_eval_score.py`（新建）

- [ ] **Step 1: 写失败测试**

新建 `prism/scripts/test_eval_score.py`：

```python
"""战绩派生（eval_score）零-LLM 测试：score_edge 三态 + score_evaluation + edge_ledger。"""
import pytest

from prism.scripts import eval_score as sc
from prism.scripts import eval_snapshot as es
from prism.scripts import macro_registry as reg


def test_score_edge_numeric_up_hit_and_miss():
    assert sc.score_edge("up", 3.0, 3.5) == "hit"
    assert sc.score_edge("up", 3.0, 2.5) == "miss"
    assert sc.score_edge("down", 3.0, 2.5) == "hit"


def test_score_edge_flat_uses_tolerance():
    assert sc.score_edge("flat", 3.0, 3.05, tol=0.1) == "hit"     # 容差内
    assert sc.score_edge("flat", 3.0, 3.5, tol=0.1) == "miss"     # 越界


def test_score_edge_up_or_flat():
    assert sc.score_edge("up_or_flat", 3.0, 3.0) == "hit"
    assert sc.score_edge("up_or_flat", 3.0, 3.5) == "hit"
    assert sc.score_edge("up_or_flat", 3.0, 2.5) == "miss"


def test_score_edge_missing_baseline_is_neutral():
    assert sc.score_edge("up", None, 3.5) == "neutral"
    assert sc.score_edge("up", 3.0, None) == "neutral"
    assert sc.score_edge(None, 3.0, 3.5) == "neutral"


def test_score_edge_stance_axis():
    # hawk_dove: 中性 → 偏鹰 = "更鹰"
    assert sc.score_edge("更鹰", "中性", "偏鹰", scale="hawk_dove") == "hit"
    assert sc.score_edge("更鹰", "中性", "偏鸽", scale="hawk_dove") == "miss"
    assert sc.score_edge("更鹰", "中性", "中性", scale="hawk_dove") == "neutral"  # 无移动→保守
```

- [ ] **Step 2: 跑测试看失败**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_score.py -p no:cacheprovider -q`
Expected: FAIL（`eval_score` 模块不存在 / `score_edge` 未定义）。

- [ ] **Step 3: 实现**

新建 `prism/scripts/eval_score.py`：

```python
"""宏观判断台账战绩（零-LLM·全派生不存盘）：单边裁决 + 整版战绩卡 + 跨版边台账。

每条 regime 结论写时对承重输入许 expected 方向预测（见 eval_snapshot）；本模块拿实际序列
机械裁决 hit/miss/neutral，连续可算、按需重算（镜像 diff_since_last 哲学）。判断永远人在
对话触发，本模块零 LLM。

依赖方向（无环）：eval_score → {eval_snapshot, macro_registry}。
"""
from __future__ import annotations

from datetime import datetime, timezone

from prism.scripts import eval_snapshot as es
from prism.scripts import macro_registry as reg


def score_edge(expected, snapshot_value, live_value, scale=None, tol=0.0):
    """单条承重边裁决：hit / miss / neutral。零 LLM。

    缺 expected / 缺基准（snapshot 或 live 为 None）→ neutral（不计命中/失手）。
    立场型（scale 给定）走 _stance_direction：无移动/不可比 → neutral（保守不冤判）。
    数值型按方向；flat 与 _or_flat 边界用容差 tol（默认 0.0，由 alert_band.delta 供）。
    """
    if not expected or live_value is None or snapshot_value is None:
        return "neutral"
    if scale:                                  # 立场/政策轴
        observed = es._stance_direction(scale, snapshot_value, live_value)
        if observed is None:
            return "neutral"
        return "hit" if observed == expected else "miss"
    if not (isinstance(snapshot_value, (int, float)) and isinstance(live_value, (int, float))):
        return "neutral"
    delta = live_value - snapshot_value
    if expected == "up":
        return "hit" if delta > 0 else "miss"
    if expected == "down":
        return "hit" if delta < 0 else "miss"
    if expected == "flat":
        return "hit" if abs(delta) <= tol else "miss"
    if expected == "up_or_flat":
        return "hit" if delta >= -tol else "miss"
    if expected == "down_or_flat":
        return "hit" if delta <= tol else "miss"
    return "neutral"
```

- [ ] **Step 4: 跑测试看通过**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_score.py -p no:cacheprovider -q`
Expected: 全 PASS。

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/eval_score.py prism/scripts/test_eval_score.py
git commit -m "feat(prism): eval_score.score_edge 单边三态裁决(数值方向+容差/立场轴·零-LLM)"
```

---

## Task 4: `eval_score.score_evaluation`（整版战绩卡）

**Files:**
- Modify: `prism/scripts/eval_score.py`
- Test: `prism/scripts/test_eval_score.py`

- [ ] **Step 1: 写失败测试**

追加到 `prism/scripts/test_eval_score.py`：

```python
@pytest.fixture
def tmp_macro(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(es, "_PRISM_ROOT", tmp_path)
    slug, variant = "m", "v"
    reg.create_registry(slug, variant)
    reg.upsert_input(slug, variant, {
        "name": "A", "tier": "A", "cadence_type": "series", "mechanism": "CD",
        "causal_sentence": "x", "importance": "load_bearing"})
    return slug, variant


def test_score_evaluation_counts_hits(tmp_macro):
    slug, variant = tmp_macro
    reg.record_observation(slug, variant, "A", value=3.0, as_of="2026-01-01")
    es.record_evaluation(slug, variant, [
        {"id": "rates", "label": "利率", "state": "升", "causal": "c",
         "based_on": [{"input": "A", "role": "load_bearing", "expected": "up"}]}],
        note="v1")
    reg.record_observation(slug, variant, "A", value=3.6)        # 实际走高 → 命中 up
    out = sc.score_evaluation(slug, variant)
    assert out["scored"] is True
    assert out["version"] == 1
    assert out["hits"] == 1 and out["misses"] == 0
    assert out["conclusions"][0]["hit_rate"] == 1.0
    assert out["conclusions"][0]["edges"][0]["verdict"] == "hit"
    assert isinstance(out["days"], int) and out["days"] >= 0


def test_score_evaluation_no_eval_returns_unscored(tmp_macro):
    slug, variant = tmp_macro
    out = sc.score_evaluation(slug, variant)
    assert out["scored"] is False and out["conclusions"] == []


def test_score_evaluation_unfetched_edge_is_neutral(tmp_macro):
    slug, variant = tmp_macro
    es.record_evaluation(slug, variant, [
        {"id": "rates", "label": "利率", "state": "升", "causal": "c",
         "based_on": [{"input": "A", "role": "load_bearing"}]}],  # A 无 observed 值→快照/现值 None
        note="v1")
    out = sc.score_evaluation(slug, variant)
    assert out["conclusions"][0]["edges"][0]["verdict"] == "neutral"
    assert out["hit_rate"] is None                                # 无命中也无失手
```

- [ ] **Step 2: 跑测试看失败**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_score.py -k score_evaluation -p no:cacheprovider -q`
Expected: FAIL（`score_evaluation` 未定义）。

- [ ] **Step 3: 实现**

在 `prism/scripts/eval_score.py` 追加：

```python
def _days_since(iso) -> int | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


def _edge_baseline(entry, snap_row, scale):
    """取 (snapshot 值, 现 live 值)：立场取 stance，数值取 value。"""
    if scale:
        return snap_row.get("stance"), (entry.get("observed") or {}).get("stance")
    return snap_row.get("value"), (entry.get("observed") or {}).get("value")


def score_evaluation(slug: str, variant: str, version: int | None = None) -> dict:
    """对某版评估（默认最新版）的承重边逐条裁决 → 每结论占对率 + 整版战绩卡 + 天数。零 LLM。

    拿「该版 expected」vs「现 observed 序列」，连续可算、按需重算（不存盘）。
    只给 load_bearing 边记战绩（本期范围）；neutral 不计入占对率分母。
    """
    log = es.read_eval_log(slug, variant)
    evals = log.get("evaluations") or []
    if not evals:
        return {"version": None, "scored": False, "reason": "no_evaluation", "conclusions": []}
    if version is None:
        ev = evals[-1]
    else:
        ev = next((e for e in evals if e.get("version") == version), None)
        if ev is None:
            return {"version": version, "scored": False, "reason": "version_not_found",
                    "conclusions": []}
    registry = reg.read_registry(slug, variant)
    entry_by_name = {e["name"]: e for e in registry.get("inputs") or []}
    snap_by_name = {s.get("name"): s for s in ev.get("input_snapshot") or []}
    conclusions_out, tot_hit, tot_miss, tot_neu = [], 0, 0, 0
    for c in ev.get("conclusions") or []:
        edges, c_hit, c_miss, c_neu = [], 0, 0, 0
        for b in c.get("based_on") or []:
            if b.get("role") != "load_bearing":
                continue
            name = b.get("input")
            entry = entry_by_name.get(name) or {}
            scale = entry.get("stance_scale")
            tol = (entry.get("alert_band") or {}).get("delta", 0.0) or 0.0
            snap_v, live_v = _edge_baseline(entry, snap_by_name.get(name) or {}, scale)
            verdict = score_edge(b.get("expected"), snap_v, live_v, scale=scale, tol=tol)
            edges.append({"input": name, "expected": b.get("expected"), "verdict": verdict,
                          "snapshot_value": snap_v, "live_value": live_v})
            c_hit += verdict == "hit"
            c_miss += verdict == "miss"
            c_neu += verdict == "neutral"
        denom = c_hit + c_miss
        conclusions_out.append({
            "id": c.get("id"), "label": c.get("label"), "state": c.get("state"),
            "hits": c_hit, "misses": c_miss, "neutrals": c_neu,
            "hit_rate": (c_hit / denom) if denom else None, "edges": edges})
        tot_hit += c_hit
        tot_miss += c_miss
        tot_neu += c_neu
    tot_denom = tot_hit + tot_miss
    return {"version": ev.get("version"), "scored": True,
            "evaluated_at": ev.get("evaluated_at"), "days": _days_since(ev.get("evaluated_at")),
            "hits": tot_hit, "misses": tot_miss, "neutrals": tot_neu,
            "hit_rate": (tot_hit / tot_denom) if tot_denom else None,
            "conclusions": conclusions_out}
```

> `c_hit += verdict == "hit"` 用 bool→int 累加，等价于条件自增，惯用法。

- [ ] **Step 4: 跑测试看通过**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_score.py -p no:cacheprovider -q`
Expected: 全 PASS。

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/eval_score.py prism/scripts/test_eval_score.py
git commit -m "feat(prism): eval_score.score_evaluation 整版战绩卡(逐结论占对率+天数·连续可算)"
```

---

## Task 5: `eval_score.edge_ledger`（跨版边台账 + 降级候选）

**Files:**
- Modify: `prism/scripts/eval_score.py`
- Test: `prism/scripts/test_eval_score.py`

- [ ] **Step 1: 写失败测试**

追加到 `prism/scripts/test_eval_score.py`：

```python
def test_edge_ledger_accumulates_across_versions(tmp_macro):
    """v1 预测 up：实现值取 v2 快照；v2 预测 up：实现值取当前 live。"""
    slug, variant = tmp_macro
    reg.record_observation(slug, variant, "A", value=3.0, as_of="2026-01-01")
    es.record_evaluation(slug, variant, [                        # v1：快照 A=3.0
        {"id": "rates", "label": "利率", "state": "升", "causal": "c",
         "based_on": [{"input": "A", "role": "load_bearing", "expected": "up"}]}], note="v1")
    reg.record_observation(slug, variant, "A", value=3.5)        # v1 的实现值（v2 快照）= 3.5 ↑ hit
    es.record_evaluation(slug, variant, [                        # v2：快照 A=3.5
        {"id": "rates", "label": "利率", "state": "升", "causal": "c",
         "based_on": [{"input": "A", "role": "load_bearing", "expected": "up"}]}], note="v2")
    reg.record_observation(slug, variant, "A", value=3.2)        # v2 的实现值（当前 live）= 3.2 ↓ miss
    led = sc.edge_ledger(slug, variant)
    row = next(r for r in led if r["conclusion_id"] == "rates" and r["input"] == "A")
    assert row["hits"] == 1 and row["misses"] == 1
    assert row["hit_rate"] == 0.5


def test_edge_ledger_flags_downgrade_candidate(tmp_macro):
    """命中率差（≥2 裁定且 <0.5）→ track='降级候选'，且排在前。"""
    slug, variant = tmp_macro
    reg.record_observation(slug, variant, "A", value=3.0, as_of="2026-01-01")
    es.record_evaluation(slug, variant, [
        {"id": "rates", "label": "利率", "state": "升", "causal": "c",
         "based_on": [{"input": "A", "role": "load_bearing", "expected": "up"}]}], note="v1")
    reg.record_observation(slug, variant, "A", value=2.5)        # v1 miss（预测 up 却跌）
    es.record_evaluation(slug, variant, [
        {"id": "rates", "label": "利率", "state": "升", "causal": "c",
         "based_on": [{"input": "A", "role": "load_bearing", "expected": "up"}]}], note="v2")
    reg.record_observation(slug, variant, "A", value=2.0)        # v2 miss
    led = sc.edge_ledger(slug, variant)
    assert led[0]["track"] == "降级候选"                          # 差的排最前
    assert led[0]["misses"] == 2 and led[0]["hits"] == 0
```

- [ ] **Step 2: 跑测试看失败**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_score.py -k edge_ledger -p no:cacheprovider -q`
Expected: FAIL（`edge_ledger` 未定义）。

- [ ] **Step 3: 实现**

在 `prism/scripts/eval_score.py` 追加：

```python
def _track_label(hits: int, misses: int) -> str:
    denom = hits + misses
    if denom == 0:
        return "无裁定"
    rate = hits / denom
    if denom >= 2 and rate < 0.5:
        return "降级候选"
    if rate >= 0.7:
        return "可靠"
    return "观察"


def edge_ledger(slug: str, variant: str) -> list:
    """跨所有评估版本按 (conclusion_id, input) 累计 hit/miss/neutral → 降级候选浮出。零 LLM。

    每版 expected 的「实现值」取下一版快照；末版用当前 live observed。只算 load_bearing 边。
    返回按 hit_rate 升序（差的在前；None 垫底），每行 {conclusion_id, input, hits, misses,
    neutrals, hit_rate, track}。
    """
    log = es.read_eval_log(slug, variant)
    evals = log.get("evaluations") or []
    registry = reg.read_registry(slug, variant)
    entry_by_name = {e["name"]: e for e in registry.get("inputs") or []}
    acc: dict = {}
    for i, ev in enumerate(evals):
        snap_by_name = {s.get("name"): s for s in ev.get("input_snapshot") or []}
        nxt_by_name = ({s.get("name"): s for s in evals[i + 1].get("input_snapshot") or []}
                       if i + 1 < len(evals) else None)
        for c in ev.get("conclusions") or []:
            cid = c.get("id")
            for b in c.get("based_on") or []:
                if b.get("role") != "load_bearing" or not b.get("expected"):
                    continue
                name = b.get("input")
                entry = entry_by_name.get(name) or {}
                scale = entry.get("stance_scale")
                tol = (entry.get("alert_band") or {}).get("delta", 0.0) or 0.0
                snap_row = snap_by_name.get(name) or {}
                snap_v = snap_row.get("stance") if scale else snap_row.get("value")
                if nxt_by_name is not None:                       # 实现值=下一版快照
                    nrow = nxt_by_name.get(name) or {}
                    live_v = nrow.get("stance") if scale else nrow.get("value")
                else:                                             # 末版=当前 live
                    obs = entry.get("observed") or {}
                    live_v = obs.get("stance") if scale else obs.get("value")
                verdict = score_edge(b.get("expected"), snap_v, live_v, scale=scale, tol=tol)
                a = acc.setdefault((cid, name), {"hits": 0, "misses": 0, "neutrals": 0})
                a[{"hit": "hits", "miss": "misses", "neutral": "neutrals"}[verdict]] += 1
    out = []
    for (cid, name), a in acc.items():
        denom = a["hits"] + a["misses"]
        out.append({"conclusion_id": cid, "input": name,
                    "hits": a["hits"], "misses": a["misses"], "neutrals": a["neutrals"],
                    "hit_rate": (a["hits"] / denom) if denom else None,
                    "track": _track_label(a["hits"], a["misses"])})
    out.sort(key=lambda r: (r["hit_rate"] is None, r["hit_rate"] if r["hit_rate"] is not None else 1.0))
    return out
```

- [ ] **Step 4: 跑测试看通过**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_score.py -p no:cacheprovider -q`
Expected: 全 PASS。

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/eval_score.py prism/scripts/test_eval_score.py
git commit -m "feat(prism): eval_score.edge_ledger 跨版边台账+降级候选(命中率差排前·零-LLM)"
```

---

## Task 6: eval-trace web 战绩卡 + 边预测/战绩列

**Files:**
- Modify: `app/routes/prism.py`（`prism_eval_trace`，~line 1053）
- Modify: `app/templates/prism/eval_trace.html`
- Test: `tests/test_macro_inputs_web.py`

- [ ] **Step 0: GitNexus 影响分析**

Run: `gitnexus_impact({target: "prism_eval_trace", direction: "upstream"})`，报风险级别（路由叶子，预期 LOW）。

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_macro_inputs_web.py`（沿用既有 `macro_web_client` / `SLUG` / `VARIANT`）：

```python
def test_eval_trace_shows_track_record_card(macro_web_client):
    """承重边带 expected + 现值走对 → eval-trace 渲战绩卡（占对率 + 预测词 + 命中）。"""
    import prism.scripts.macro_registry as reg
    import prism.scripts.eval_snapshot as es
    reg.record_observation(SLUG, VARIANT, "HY OAS", value=3.6, as_of="2026-06-07")  # 现值走高
    es.append_evaluation(SLUG, VARIANT, {
        "input_snapshot": [{"name": "HY OAS", "value": 3.0, "as_of": "2026-06-01", "used": True}],
        "conclusions": [{"id": "liquidity_us", "label": "美国流动性体制", "state": "偏紧",
                         "based_on": [{"input": "HY OAS", "role": "load_bearing", "expected": "up"}],
                         "causal": "HY OAS 走阔 → 流动性偏紧"}]})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/eval-trace")
    assert r.status_code == 200
    assert "战绩" in r.text                       # 战绩卡标题词
    assert "占对" in r.text                       # 占对率措辞
    assert "up" in r.text                         # 该边的 expected 方向词
```

> 前置：`macro_web_client` fixture 的 registry 里已有 `HY OAS`（既有 eval-trace 测试在用）。若该 fixture 未把 `HY OAS` 设为可记录观测的输入，测试中的 `record_observation` 仍会写入 observed，`score_evaluation` 即可取到 live=3.6。

- [ ] **Step 2: 跑测试看失败**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py -k track_record -p no:cacheprovider -q`
Expected: FAIL（模板无「战绩」「占对」字样）。

- [ ] **Step 3: 路由传 score + ledger**

在 `app/routes/prism.py` 的 `prism_eval_trace` 里，把 import 与 TemplateResponse 改为（新增 `eval_score` + 两个上下文键）：

```python
    from prism.scripts import eval_snapshot as es
    from prism.scripts import eval_score as sc
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
        "score": sc.score_evaluation(slug, variant),
        "ledger": {(r["conclusion_id"], r["input"]): r for r in sc.edge_ledger(slug, variant)},
    })
```

- [ ] **Step 4: 模板渲战绩卡 + 边列**

在 `app/templates/prism/eval_trace.html` 的 `{% if not evaluation %}…{% else %}` 分支内，**紧接** `<p class="hint">评估 v…</p>`（line 22 后）插入战绩卡区：

```html
  {% if score and score.scored and score.hit_rate is not none %}
  <section class="track-card">
    <h2>📊 上版战绩 <span class="hint">（v{{ score.version }} 预测 vs 现序列 · {{ score.days }} 天）</span></h2>
    <p>承重输入占对：<strong>{{ score.hits }}/{{ score.hits + score.misses }}</strong>
      （{{ (score.hit_rate * 100) | round(0) | int }}% 占对）
      {% if score.neutrals %}· {{ score.neutrals }} 边无基准/未抓{% endif %}</p>
  </section>
  {% endif %}
```

在每条结论的 based_on 表格里加「预测 / 战绩」列。把 `<thead>` 与行模板改为：

```html
    <table class="data-table">
      <thead><tr><th>依赖输入</th><th>角色</th><th>上次评估值</th><th>现值 / Δ</th><th>预测 / 战绩</th></tr></thead>
      <tbody>
      {% for b in c.based_on %}
        {% set d = diff.get(b.input) %}
        {% set lg = ledger.get((c.id, b.input)) %}
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
          <td>
            {% if b.expected %}<code class="exp">{{ b.expected }}</code>{% else %}<span class="hint">—</span>{% endif %}
            {% if lg %}<span class="track-{{ lg.track }}">{{ lg.track }}</span>
              <span class="hint">{{ lg.hits }}/{{ lg.hits + lg.misses }}</span>{% endif %}
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
```

在 `<style>` 块末尾（`}` 收口前最后一行 `.badge-breach{…}` 之后）加样式：

```css
  .track-card { margin: 1em 0; padding: 0.6em 0.9em; background: #f6f9f4; border-left: 3px solid #5a8f3c; border-radius: 4px; }
  .track-card h2 { font-size: 1em; margin: 0 0 0.3em; border: none; }
  .exp { font-size: 0.78em; background: #eef4ff; color: #2a5db0; padding: 0.1em 0.35em; border-radius: 3px; }
  .track-降级候选 { font-size: 0.72em; padding: 0.1em 0.35em; border-radius: 3px; background: #fde8e8; color: #b42318; margin-left: 0.3em; }
  .track-可靠 { font-size: 0.72em; padding: 0.1em 0.35em; border-radius: 3px; background: #e7f5e7; color: #2f7d2f; margin-left: 0.3em; }
  .track-观察, .track-无裁定 { font-size: 0.72em; padding: 0.1em 0.35em; border-radius: 3px; background: #f0f0f0; color: #666; margin-left: 0.3em; }
```

- [ ] **Step 5: 跑测试看通过 + 全 web 回归**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py -p no:cacheprovider -q`
Expected: 全 PASS（新战绩卡测试 + 既有 eval-trace/inputs 测试）。

- [ ] **Step 6: 提交**

```bash
gitnexus_detect_changes()
git add app/routes/prism.py app/templates/prism/eval_trace.html tests/test_macro_inputs_web.py
git commit -m "feat(prism): eval-trace 加上版战绩卡+边预测/命中率列(零-LLM 派生)"
```

---

## Task 7: workflow `_macro_regime.md` Step 5 教写 expected / prior_verdict

**Files:**
- Modify: `prism/workflows/04-synthesize/_macro_regime.md`（Step 5，~line 309-343）

> 纯文档；无测试。但**关键**：Task 1 上线后，真实 macro 合成若 record_evaluation 的承重数值/立场边不带 `expected` 会校验报错——本任务确保 workflow 示例与说明同步，否则下次重判失败。

- [ ] **Step 1: 给 record_evaluation 示例的承重边加 expected**

把 `_macro_regime.md` 中 `record_evaluation` 的 conclusions 示例（约 line 316-324）改为带 `expected`（承重边示范方向词，confirming/background 可留空）：

```bash
python3 -c "
from prism.scripts.eval_snapshot import record_evaluation
v = record_evaluation('{slug}', '{variant}', [
    {'id': 'overall',      'label': '综合判断',     'state': '偏防御·压久期', 'causal': '...', 'based_on': [{'input': '<名>', 'role': 'load_bearing', 'expected': 'up_or_flat'}]},
    {'id': 'rates_us',     'label': '美国利率体制', 'state': '高位企稳',     'causal': '...', 'based_on': [{'input': '<名>', 'role': 'load_bearing', 'expected': 'up_or_flat'}]},
    {'id': 'rates_cn',     'label': '中国利率体制', 'state': '...',          'causal': '...', 'based_on': [{'input': '<名>', 'role': 'confirming'}]},
    {'id': 'liquidity_us', 'label': '美国流动性体制','state': '...',          'causal': '...', 'based_on': [{'input': '<名>', 'role': 'load_bearing', 'expected': 'down_or_flat'}]},
    {'id': 'fx_cny',       'label': '人民币汇率体制','state': '...',          'causal': '...', 'based_on': [{'input': '<名>', 'role': 'confirming'}]},
    {'id': 'quadrant',     'label': '增长/通胀象限','state': '滞胀',          'causal': '...', 'based_on': [{'input': '<名>', 'role': 'background'}]},
    {'id': 'fragility',    'label': '脆弱度',       'state': 'high',          'causal': '...', 'based_on': [{'input': '<名>', 'role': 'background'}]},
], note='S5 合成/重估')
print(f'评估快照已写 v{v}，reeval_pending 已自动清')
"
```

- [ ] **Step 2: 在 record_evaluation 说明段后插入「可证伪 expected」要求**

在 `_macro_regime.md` 中「不确定某结论挂哪些输入时…」那条 `>` 引用（约 line 329）**之后**插入：

```markdown
> **可证伪预测（硬要求 · 仅承重边）**：每条结论的 `load_bearing` 边、且该输入有数值或立场基准时，**必须**带 `expected` 方向预测（缺则 `record_evaluation` 校验报错）。方向词表：数值型 `up / down / flat / up_or_flat / down_or_flat`；立场型用对应轴方向词（`更鹰/更鸽`、`更紧/更松`、`更收缩/更扩张`、`更下移/更上移`）。这是日后机器拿 FRED 序列机械裁决「判得对不对」的钉子——预测提前钉死、数据说话。confirming/background 边可不带。
```

- [ ] **Step 3: 在「复核 provisional + 体制变扫失鲜」块后插入「上版战绩 → prior_verdict」流程**

在 `_macro_regime.md` 中 provisional 复核那条 `>` 引用（约 line 343）**之后**插入：

````markdown
**带上版战绩裁定（重估时 · 软要求）**：本轮若是**重估**（已有上一版评估），重判前先看上版机械战绩，据此对每条结论落 `prior_verdict`（held/partial/wrong），写在本（新）评估条目上（append-only、不改旧）：

```bash
python3 -c "
from prism.scripts import eval_score as sc
s = sc.score_evaluation('{slug}', '{variant}')   # 上版整版战绩卡
print('上版占对：', s.get('hits'), '/', (s.get('hits') or 0)+(s.get('misses') or 0), '·', s.get('days'), '天')
for c in s.get('conclusions') or []:
    print(' -', c['label'], c['hits'], 'hit /', c['misses'], 'miss', '· 占对', c['hit_rate'])
led = sc.edge_ledger('{slug}', '{variant}')        # 跨版边台账 → 降级候选
for r in led[:5]:
    print('   边', r['conclusion_id'], r['input'], r['track'], r['hits'], '/', r['hits']+r['misses'])
"
```

据此在 `record_evaluation(...)` 调用补 `prior_verdict=[{'conclusion_id': '<id>', 'verdict': 'held|partial|wrong', 'note': '...'}]`。**机制边降级**＝一次普通 registry 编辑：对 `edge_ledger` 报「降级候选」的边，按需调 `macro_registry.upsert_input` 改该输入 `tier`（A→B）或调它在 based_on 的 `role`（load_bearing→confirming）。不发明新台账文件。
````

- [ ] **Step 4: 跑全套确认无回归（文档改不影响测试，但跑一遍兜底）**

Run: `.venv/bin/python -m pytest prism/scripts/test_eval_snapshot.py prism/scripts/test_eval_score.py prism/scripts/test_macro_xcut.py prism/scripts/test_dashboard_macro.py tests/test_macro_inputs_web.py -p no:cacheprovider -q`
Expected: 全 PASS。

- [ ] **Step 5: 提交**

```bash
git add prism/workflows/04-synthesize/_macro_regime.md
git commit -m "docs(prism): _macro_regime Step5 教写可证伪 expected + 上版战绩→prior_verdict/降级"
```

---

## 完成后

全 7 任务过后跑收尾（superpowers:finishing-a-development-branch）：先全量 `.venv/bin/python -m pytest prism/scripts/test_eval_snapshot.py prism/scripts/test_eval_score.py prism/scripts/test_macro_xcut.py prism/scripts/test_monitor_macro.py prism/scripts/test_dashboard_macro.py tests/test_macro_inputs_web.py -p no:cacheprovider -q` 绿，再向用户给出合并/PR/保留/丢弃四选项。

> 注：分支 `feat/macro-xcut-and-judgment-ledger` 已含 3a + 用户 WIP（取文登记表/取数去重/headless 缓冲）三个 commit，收尾合并会一并进 main——届时向用户点明。

## Self-Review（写计划者自检 · 已过）

- **Spec 覆盖**：§3.2 expected→Task1；§3.4 prior_verdict→Task2；§3.3 score_edge→Task3 / score_evaluation→Task4 / edge_ledger→Task5；§3.5 web→Task6；§8「Step5 落 expected/prior_verdict」+ 降级→Task7。§3.4「机制边降级=普通 registry 编辑，不发明新文件」已在 Task7 Step3 言明，无需改 `macro_registry.py`（故无 test_macro_registry 扩展）。
- **占位符**：无 TBD/TODO/"类似 TaskN"；每步含完整代码或精确编辑锚点。
- **类型一致**：`score_edge(expected, snapshot_value, live_value, scale=None, tol=0.0)` 在 Task4/5 调用签名一致；`edge_ledger` 行键 `(conclusion_id, input)` 与 Task6 路由 `ledger` 字典键一致；`score_evaluation` 返回键（`scored/version/hits/misses/neutrals/hit_rate/days/conclusions[].{id,label,hit_rate,edges}`）与 Task6 模板消费键一致；`VALID_VERDICT`/`NUMERIC_DIRECTIONS`/`_valid_expected_words` 命名前后统一。
- **回归**：Task1 Step1 先修 `test_eval_snapshot` 两处 numeric fixture；已核实 web 测试用 confirming、xcut/dashboard 的 USDCNY 在 record_evaluation 时无 observed 值（非数值→不强制），故不破。

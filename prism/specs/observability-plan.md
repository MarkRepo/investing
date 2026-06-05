# Prism 可观测性 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建一个纯被动、零 LLM 的观测层，从已有产物残留重建 prism 流程质量诊断，呈现在一张平行诊断页上给人看。

**Architecture:** 新增 `prism/scripts/observability.py`，`run_probes(slug, variant)` 跑全部探针（读 topic.yaml / manifest / findings / sidecar / web_search_log / gap_detector，机械判 pass/fail/flag/na），返回结构化 Trace。少数缺残留的探针靠 B 建设补字段（B1 stage.history 承重墙、B2-B4 sidecar 字段）。渲染器仿 `dashboard.py` 出 per-topic 诊断页。

**Tech Stack:** Python 3（dataclasses + PyYAML），pytest（仿 `prism/scripts/test_gap_detector.py` 的 monkeypatch PRISM_ROOT 模式），零 LLM 调用。

**Spec:** `prism/specs/observability.md`（探针全表 §3、B 建设 §4、约束 §5、诊断页 §6）。

**约定（CLAUDE.md 硬规则）：** 每个代码符号编辑前跑 `gitnexus_impact({target, direction:"upstream"})`；提交前跑 `gitnexus_detect_changes()`。本计划只在用户明示时才 commit。

---

## 文件结构（先锁分解）

| 文件 | 职责 | 动作 |
|---|---|---|
| `prism/scripts/observability.py` | Probe dataclass + 各探针族函数 + `run_probes` 汇总 | 新建 |
| `prism/scripts/test_observability.py` | 全部探针单测 | 新建 |
| `prism/scripts/observability_render.py` | Trace → 诊断页 markdown（仿 dashboard.py） | 新建 |
| `prism/scripts/test_observability_render.py` | 渲染单测 | 新建 |
| `prism/scripts/topic.py` | B1：`set_stage` 写 `stage.history` + gap 快照 | 改 `set_stage`（436-437） |
| `prism/scripts/test_topic_stage_history.py` | B1 单测 | 新建 |
| `prism/scripts/gap_detector.py` | B1：精简快照导出 `snapshot_gaps` | 加新函数 |
| sidecar 模板 + `04-synthesize/*.md` | B2/B3/B4：`chain_links` / `honest_gaps` / `market_implied` / `my_vs_market_delta` 字段 | 改 markdown |
| `prism/scripts/outputs.py`（sidecar 校验处） | B2/B3/B4：放行新字段 | 改 schema 白名单 |

**依赖序**：Task 1（骨架+无建设探针）→ Task 2（更多无建设探针）→ Task 3（B5′ 卷积）→ Task 4（B1 承重墙 + 02 diff 探针）→ Task 5（B2-B4 + 04 探针）→ Task 6（B6 可选）→ Task 7（渲染器）。

**测试运行**：`cd /Users/yangqi/investing && python3 -m pytest prism/scripts/test_observability.py -v`

---

## Task 1: observability 骨架 + Probe schema + 贯穿探针 CC1/CC3/CC4/CC6

**Files:**
- Create: `prism/scripts/observability.py`
- Test: `prism/scripts/test_observability.py`

- [ ] **Step 1: 写失败测试（fixture + CC1/CC3/CC4/CC6）**

仿 `test_gap_detector.py` 的 monkeypatch 模式。写入 `prism/scripts/test_observability.py`：

```python
"""Tests for observability probe layer."""
import tempfile
from pathlib import Path

import pytest

from prism.scripts import topic as topic_io
from prism.scripts import observability as obs


@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.gap_detector.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    slug, variant = "obs-test", "test"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(
        slug=slug, display_name="T", topic_type="company",
        question="Q?", geo="US", depth="quick", variant=variant,
    )
    return slug, variant


def _probe(probes, pid):
    return next((p for p in probes if p["probe_id"] == pid), None)


def test_run_probes_returns_trace_shape(tmp_topic):
    slug, variant = tmp_topic
    trace = obs.run_probes(slug, variant)
    assert trace["slug"] == slug and trace["variant"] == variant
    assert isinstance(trace["probes"], list)
    assert "summary" in trace


def test_cc1_addresses_missing_fails(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "有 addr", "priority": "P0", "addresses": ["K1"]},
        {"task": "缺 addr", "priority": "P1"},  # 无 addresses
    ], variant=variant)
    p = _probe(obs.run_probes(slug, variant)["probes"], "CC1")
    assert p["status"] == "fail"
    assert "缺 addr" in p["detail"]


def test_cc3_autofetch_debt_flags_unattempted(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "没抓过", "priority": "P0", "addresses": ["K1"], "info_tier": "public"},
    ], variant=variant)
    p = _probe(obs.run_probes(slug, variant)["probes"], "CC3")
    assert p["status"] == "fail"


def test_cc4_empty_undecided_flags(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "公开无源", "priority": "P0", "addresses": ["K1"]},
    ], variant=variant)
    topic_io.mark_todo_fetch(slug, variant, "公开无源", "empty", note="搜空")
    p = _probe(obs.run_probes(slug, variant)["probes"], "CC4")
    assert p["status"] == "fail"


def test_cc6_p0_pending_at_stage04_flags(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "P0 没收敛", "priority": "P0", "addresses": ["K1"]},
    ], variant=variant)
    topic_io.set_stage(slug, "04-synthesizing", variant)
    p = _probe(obs.run_probes(slug, variant)["probes"], "CC6")
    assert p["status"] == "fail"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest prism/scripts/test_observability.py -v`
Expected: FAIL（`ModuleNotFoundError: prism.scripts.observability`）

- [ ] **Step 3: 写最小实现**

写入 `prism/scripts/observability.py`：

```python
"""Prism 可观测性观测层（纯被动 · 零 LLM）。

run_probes(slug, variant) 从已有产物残留重建流程质量诊断。
探针族：produce(产出) / quality(质量) / pitfall(坑)。
quality.tier: 1=机械重建 / 2=机械代理 / 3=纯判断挂复核旗。
status: pass / fail / flag / na。

spec: prism/specs/observability.md
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from prism.scripts import topic as topic_io
from prism.scripts.gap_detector import detect_gaps


@dataclass
class Probe:
    probe_id: str
    label: str
    stage: str
    family: str            # produce | quality | pitfall
    status: str            # pass | fail | flag | na
    signal: str
    tier: int | None = None
    detail: str = ""
    action: str = ""


def _active_todos(topic: dict) -> list[dict]:
    return [t for t in (topic.get("user_todos") or [])
            if isinstance(t, dict) and t.get("status") in ("pending", "in_progress")]


def _cross_cutting(slug: str, variant: str, topic: dict, gaps: dict) -> list[Probe]:
    out: list[Probe] = []
    active = _active_todos(topic)

    # CC1: active todo 都带 addresses（H2）
    missing = [t.get("task", "?") for t in active if not t.get("addresses")]
    out.append(Probe(
        "CC1", "active todo 都带 addresses", "cross-cutting", "pitfall",
        "fail" if missing else "pass", "todo.addresses 字段", tier=1,
        detail=("丢字段: " + "; ".join(missing)) if missing else "全带",
        action="补 addresses" if missing else "",
    ))

    # CC3: autofetch 欠账（unattempted/error）
    debt = gaps.get("autofetch_debt") or []
    out.append(Probe(
        "CC3", "autofetch 欠账", "cross-cutting", "pitfall",
        "fail" if debt else "pass", "gap_detector.autofetch_debt", tier=1,
        detail=f"{len(debt)} 条欠尝试" if debt else "无欠账",
        action="error→重试 / unattempted→去抓" if debt else "",
    ))

    # CC4: empty 待用户决（硬闸门）
    empty = gaps.get("empty_pending_decision") or []
    out.append(Probe(
        "CC4", "empty 待用户决", "cross-cutting", "pitfall",
        "fail" if empty else "pass", "empty_undecided_todos", tier=1,
        detail=f"{len(empty)} 条待决" if empty else "无待决",
        action="走 empty 硬闸门" if empty else "",
    ))

    # CC6: P0 pending 进 04/05 前已收敛
    stage = topic.get("stage", "")
    late = stage.startswith(("04", "05", "done"))
    p0_pending = [t.get("task", "?") for t in active
                  if t.get("priority") == "P0" and t.get("status") == "pending"]
    cc6_fail = late and bool(p0_pending)
    out.append(Probe(
        "CC6", "P0 pending 进 04/05 前已收敛", "cross-cutting", "pitfall",
        "fail" if cc6_fail else "pass", "P0 todo.status + stage", tier=1,
        detail=("未收敛: " + "; ".join(p0_pending)) if cc6_fail else "已收敛或未到 04",
        action="收敛 P0（done/重试/waived）" if cc6_fail else "",
    ))
    return out


def run_probes(slug: str, variant: str) -> dict:
    topic = topic_io.read_topic(slug, variant)
    try:
        gaps = detect_gaps(slug, variant)
    except Exception as e:  # 诊断层绝不因底层异常炸掉
        gaps = {"error": str(e)}

    probes: list[Probe] = []
    probes += _cross_cutting(slug, variant, topic, gaps)

    rows = [asdict(p) for p in probes]
    summary = {
        "fail": sum(1 for p in rows if p["status"] == "fail"),
        "flag": sum(1 for p in rows if p["status"] == "flag"),
        "pass": sum(1 for p in rows if p["status"] == "pass"),
        "na":   sum(1 for p in rows if p["status"] == "na"),
    }
    return {"slug": slug, "variant": variant, "probes": rows, "summary": summary}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest prism/scripts/test_observability.py -v`
Expected: PASS（5 passed）

- [ ] **Step 5: Commit**（仅用户明示时执行；先在分支上）

```bash
git add prism/scripts/observability.py prism/scripts/test_observability.py
git commit -m "feat(prism): 可观测层骨架 + 贯穿探针 CC1/3/4/6"
```

---

## Task 2: 无建设探针批次（00/01/03/05 产出+质量+坑 + CC2/CC5）

读现成残留，不依赖 B 建设。

**Files:**
- Modify: `prism/scripts/observability.py`
- Modify: `prism/scripts/test_observability.py`

- [ ] **Step 1: 写失败测试**

追加到 `test_observability.py`：

```python
def test_05x1_failed_prescan_approve_flags(tmp_topic):
    slug, variant = tmp_topic
    # 写一个 failed prescan 的 thesis，再给 approve verdict
    topic_io.set_thesis(slug, variant, version=1, prescan_status="failed")
    topic_io.set_critic_verdict(slug, variant, verdict="approve", score=4)
    p = _probe(obs.run_probes(slug, variant)["probes"], "05.X1")
    assert p["status"] == "fail"


def test_05q2_low_score_approve_flags(tmp_topic):
    slug, variant = tmp_topic
    topic_io.set_critic_verdict(slug, variant, verdict="approve", score=2)
    p = _probe(obs.run_probes(slug, variant)["probes"], "05.Q2")
    assert p["status"] == "fail"


def test_cc2_fake_pending_flags(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "已覆盖却 pending", "priority": "P1", "addresses": ["K1"],
         "covered_by": ["mat-x"]},
    ], variant=variant)
    p = _probe(obs.run_probes(slug, variant)["probes"], "CC2")
    assert p["status"] == "fail"


def test_01q1_public_unattempted_flags(tmp_topic):
    slug, variant = tmp_topic
    topic_io.append_user_todos(slug, [
        {"task": "public 没抓", "priority": "P1", "addresses": ["K1"],
         "info_tier": "public"},
    ], variant=variant)
    p = _probe(obs.run_probes(slug, variant)["probes"], "01.Q1")
    assert p["status"] == "fail"


def test_05q1_steelman_always_flag(tmp_topic):
    slug, variant = tmp_topic
    p = _probe(obs.run_probes(slug, variant)["probes"], "05.Q1")
    assert p["status"] == "flag"  # 纯判断，永远挂复核旗
```

注：`set_thesis` / `set_critic_verdict` 的确切签名先 `grep -n "def set_thesis\|def set_critic_verdict" prism/scripts/topic.py` 核对（B5/H5 修订过参数名）；若签名不符按实际调整测试入参。

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest prism/scripts/test_observability.py -v`
Expected: FAIL（新增 5 个 test 因探针未实现而 `p is None` → AttributeError）

- [ ] **Step 3: 写实现**

在 `observability.py` 加探针族函数，并在 `run_probes` 里挂上。先加 helper 读 verdict/prescan：

```python
from prism.scripts.topic import get_current_prescan_status


def _stage_05(slug, variant, topic, gaps) -> list[Probe]:
    out: list[Probe] = []
    critic = topic.get("critic") or {}
    verdict = critic.get("verdict")
    score = critic.get("score")

    # 05.X1: failed prescan 却 approve（纯机械可逮）
    ps = get_current_prescan_status(slug, variant)  # 返回 dict 或带 status 键
    prescan_failed = (isinstance(ps, dict) and ps.get("status") == "failed")
    x1_fail = prescan_failed and verdict == "approve"
    out.append(Probe(
        "05.X1", "failed prescan 却 approve", "05-critic-review", "pitfall",
        "fail" if x1_fail else ("na" if verdict is None else "pass"),
        "prescan_status + verdict", tier=1,
        detail="时敏论断未校准就 approve" if x1_fail else "",
        action="按脆弱处理，最高 request-more" if x1_fail else "",
    ))

    # 05.Q2: verdict 与评分一致（评分低却 approve = 放水）
    q2_fail = verdict == "approve" and isinstance(score, (int, float)) and score < 4
    out.append(Probe(
        "05.Q2", "verdict 与评分一致", "05-critic-review", "quality",
        "fail" if q2_fail else ("na" if verdict is None else "pass"),
        "score vs verdict", tier=1,
        detail=f"score={score} 却 approve" if q2_fail else "",
        action="复核是否放水" if q2_fail else "",
    ))

    # 05.Q1: 反方真 steelman —— 纯判断，永远挂旗
    out.append(Probe(
        "05.Q1", "反方真 steelman 还是走过场", "05-critic-review", "quality",
        "na" if verdict is None else "flag", "—", tier=3,
        detail="被动层判不了，需人复核 critic 是否攻最强论证",
        action="人复核" if verdict else "",
    ))
    return out


def _cross_cutting_extra(slug, variant, topic) -> list[Probe]:
    out: list[Probe] = []
    active = _active_todos(topic)

    # CC2: 假 pending（pending 但 covered_by≠∅ 或 fetch_status=fetched）
    fake = [t.get("task", "?") for t in active if t.get("status") == "pending"
            and (t.get("covered_by") or t.get("fetch_status") == "fetched")]
    out.append(Probe(
        "CC2", "无待补料假 pending", "cross-cutting", "pitfall",
        "fail" if fake else "pass", "pending + covered_by/fetch_status", tier=1,
        detail=("应翻 done: " + "; ".join(fake)) if fake else "无假 pending",
        action="update_user_todo_status → done" if fake else "",
    ))

    # 01.Q1 / 01.X1: public/half 是否真过自动获取（fetch_status≠unattempted）
    unatt = [t.get("task", "?") for t in active
             if t.get("info_tier", "public") in ("public", "half_public")
             and t.get("fetch_status", "unattempted") == "unattempted"]
    out.append(Probe(
        "01.Q1", "5.6 跑了（public/half 真过自动获取）", "01-roadmap", "quality",
        "fail" if unatt else "pass", "fetch_status≠unattempted", tier=1,
        detail=("未尝试: " + "; ".join(unatt)) if unatt else "都尝试过",
        action="去抓（CC3）" if unatt else "",
    ))
    return out
```

在 `run_probes` 的 `probes +=` 区追加：

```python
    probes += _cross_cutting_extra(slug, variant, topic)
    probes += _stage_05(slug, variant, topic, gaps)
```

> 注：`get_current_prescan_status` 的返回结构按 topic.py 实际为准（H5 改为从 history 取）；若返回 `(status, reason)` 元组或纯 str，相应调整 `prescan_failed` 取值。`critic` 字段路径同样先 `grep -n "critic" prism/scripts/topic.py` 核对实际存储位置（可能在 `outputs_state` 或顶层 `critic`）。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest prism/scripts/test_observability.py -v`
Expected: PASS（全部）

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/observability.py prism/scripts/test_observability.py
git commit -m "feat(prism): 无建设探针批次 05.X1/Q1/Q2 + CC2 + 01.Q1"
```

---

## Task 3: B5′ 被动 provenance 卷积探针

读 `web_search_log` + `manifest` + `fetch_status 全家`，卷成一块面板。零建设。

**Files:**
- Modify: `prism/scripts/observability.py`
- Modify: `prism/scripts/test_observability.py`

- [ ] **Step 1: 写失败测试**

```python
def test_b5prime_rollup(tmp_topic):
    slug, variant = tmp_topic
    from prism.scripts.web_prescan import append_search_log
    append_search_log(slug, variant, triggered_by="01-deepfetch",
                      queries=["q1", "q2"], n_high=1, n_mid=0)
    topic_io.append_user_todos(slug, [
        {"task": "降级了", "priority": "P1", "addresses": ["K1"]},
    ], variant=variant)
    topic_io.mark_todo_fetch(slug, variant, "降级了", "empty", note="搜空")
    p = _probe(obs.run_probes(slug, variant)["probes"], "B5prime")
    assert p["status"] == "pass"          # 卷积探针始终 pass（信息面板）
    assert "搜" in p["detail"] and "降级" in p["detail"]
```

注：`append_search_log` 入参以 `grep -nA10 "def append_search_log" prism/scripts/web_prescan.py` 实际签名为准（queries/n_high/n_mid 命名可能不同），按实调整。

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest prism/scripts/test_observability.py::test_b5prime_rollup -v`
Expected: FAIL（探针不存在 → AttributeError）

- [ ] **Step 3: 写实现**

```python
from prism.scripts.web_prescan import list_search_log
from prism.scripts.manifest import read_manifest


def _b5prime(slug, variant, topic) -> list[Probe]:
    # 搜索轮次
    log = list_search_log(slug, variant)
    rounds = len(log)
    registered = sum(1 for e in log if e.get("disposition", "registered") == "registered")
    skipped = rounds - registered
    # 入库料
    try:
        mats = (read_manifest(slug, variant).get("materials") or [])
    except Exception:
        mats = []
    # 降级决定
    todos = topic.get("user_todos") or []
    downgraded = [t for t in todos if isinstance(t, dict)
                  and t.get("fetch_status") in ("empty", "error")
                  or (isinstance(t, dict) and t.get("disposition") in ("waived", "will_collect"))]
    detail = (f"搜 {rounds} 轮（入库 {registered} / 跳过 {skipped}）"
              f" → 入库 {len(mats)} 份料 → 降级 {len(downgraded)} 条")
    return [Probe(
        "B5prime", "本轮收料卷积（执行轨迹被动版）", "cross-cutting", "produce",
        "pass", "web_search_log + manifest + fetch_status", tier=1,
        detail=detail,
    )]
```

在 `run_probes` 追加 `probes += _b5prime(slug, variant, topic)`。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest prism/scripts/test_observability.py::test_b5prime_rollup -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/observability.py prism/scripts/test_observability.py
git commit -m "feat(prism): B5' 被动 provenance 卷积探针"
```

---

## Task 4: B1 承重墙 —— stage.history + 进入时 gap 快照（+ 02.Q2/Q3 探针）

**先跑 impact**：`gitnexus_impact({target:"set_stage", direction:"upstream"})` 和 `gitnexus_impact({target:"detect_gaps", direction:"upstream"})`，把 blast radius 报给用户；HIGH/CRITICAL 必先告警。

**Files:**
- Modify: `prism/scripts/gap_detector.py`（加 `snapshot_gaps`）
- Modify: `prism/scripts/topic.py:436-437`（`set_stage` 写 history）
- Create: `prism/scripts/test_topic_stage_history.py`
- Modify: `prism/scripts/observability.py`（02.Q2/Q3）
- Modify: `prism/scripts/test_observability.py`

- [ ] **Step 1: 写 B1 失败测试**

`prism/scripts/test_topic_stage_history.py`：

```python
import tempfile
from pathlib import Path

import pytest

from prism.scripts import topic as topic_io


@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.gap_detector.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    slug, variant = "sh-test", "test"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(slug=slug, display_name="T", topic_type="company",
                          question="Q?", geo="US", depth="quick", variant=variant)
    return slug, variant


def test_set_stage_appends_history(tmp_topic):
    slug, variant = tmp_topic
    topic_io.set_stage(slug, "02-gather-materials", variant)
    topic_io.set_stage(slug, "03-extracting", variant)
    data = topic_io.read_topic(slug, variant)
    hist = data["stage"]["history"]
    assert [h["stage"] for h in hist][-2:] == ["02-gather-materials", "03-extracting"]
    assert hist[-2]["exited_at"] is not None     # 上一条已回填
    assert hist[-1]["exited_at"] is None         # 当前未退出
    assert "gap_snapshot" in hist[-1]


def test_set_stage_idempotent_same_stage(tmp_topic):
    slug, variant = tmp_topic
    topic_io.set_stage(slug, "02-gather-materials", variant)
    n1 = len(topic_io.read_topic(slug, variant)["stage"]["history"])
    topic_io.set_stage(slug, "02-gather-materials", variant)  # 同 stage 不重复 append
    n2 = len(topic_io.read_topic(slug, variant)["stage"]["history"])
    assert n1 == n2


def test_legacy_topic_no_history_is_safe(tmp_topic):
    slug, variant = tmp_topic
    data = topic_io.read_topic(slug, variant)
    # 旧 topic 可能无 stage.history；read 不应炸
    assert isinstance(data.get("stage", {}), (dict, str)) or data.get("stage") is None
```

注：`create_topic` 可能已把 `stage` 写成顶层 str（如现状 `data["stage"]`）。B1 把它升级为 `{"current":..., "history":[...]}` 结构时**必须向后兼容**：read 时若 `stage` 是 str 则视为无 history。测试 `test_legacy_topic_no_history_is_safe` 守这点。**实现前先 `grep -n '"stage"\|stage=' prism/scripts/topic.py` 确认 stage 当前存储形态**，决定是新增 `stage.history` 子结构还是平行 `stage_history` 顶层键（**推荐后者：平行 `stage_history` 顶层键，不动现有 `stage` str，零破坏现消费方**）。下面实现按**平行 `stage_history` 顶层键**写。

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest prism/scripts/test_topic_stage_history.py -v`
Expected: FAIL（无 `stage.history` / `stage_history`）

- [ ] **Step 3a: gap_detector 加精简快照导出**

在 `prism/scripts/gap_detector.py` 末尾加：

```python
def snapshot_gaps(slug: str, variant: str) -> dict:
    """进入 stage 时的精简 gap 快照（B1 承重墙用）。失败返回空，绝不抛。"""
    try:
        g = detect_gaps(slug, variant)
    except Exception:
        return {}
    if "error" in g:
        return {}
    return {
        "uncovered_ks": list(g.get("uncovered_ks") or []),
        "uncovered_ring_inputs": [i.get("code") for i in (g.get("uncovered_ring_inputs") or [])],
        "autofetch_debt": len(g.get("autofetch_debt") or []),
        "empty_pending_decision": len(g.get("empty_pending_decision") or []),
    }
```

- [ ] **Step 3b: set_stage 写 history（平行 stage_history 顶层键）**

把 `prism/scripts/topic.py:436-437` 的 `set_stage` 改为：

```python
def set_stage(slug: str, stage: str, variant: str) -> None:
    from datetime import datetime, timezone
    data = _read_yaml(_topic_path(slug, variant))
    prev = data.get("stage")
    if prev == stage:
        update_topic(slug, variant, stage=stage)  # 同 stage：不动 history
        return
    hist = data.get("stage_history")
    if not isinstance(hist, list):
        hist = []
    now = datetime.now(timezone.utc).isoformat()
    if hist and hist[-1].get("exited_at") is None:
        hist[-1]["exited_at"] = now          # 回填上一条退出
    # 延迟 import 防循环（gap_detector imports topic）
    from prism.scripts.gap_detector import snapshot_gaps
    hist.append({
        "stage": stage,
        "entered_at": now,
        "exited_at": None,
        "gap_snapshot": snapshot_gaps(slug, variant),
    })
    update_topic(slug, variant, stage=stage, stage_history=hist)
```

测试里 history 访问改为 `data["stage_history"]`（不是 `data["stage"]["history"]`）；同步修正 Step 1 三个测试的取值路径为 `data["stage_history"]`。

- [ ] **Step 4: 跑 B1 测试确认通过**

Run: `python3 -m pytest prism/scripts/test_topic_stage_history.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 加 02.Q2/Q3 探针（吃 stage_history diff）**

`test_observability.py` 追加：

```python
def test_02q2_red_gap_carried_forward_fails(tmp_topic):
    slug, variant = tmp_topic
    # 伪造 stage_history：02 进入红 K3，03 进入仍红 K3 → 硬升
    topic_io.update_topic(slug, variant, stage_history=[
        {"stage": "02-gather-materials", "entered_at": "t0", "exited_at": "t1",
         "gap_snapshot": {"uncovered_ks": ["K3"]}},
        {"stage": "03-extracting", "entered_at": "t1", "exited_at": None,
         "gap_snapshot": {"uncovered_ks": ["K3"]}},
    ])
    p = _probe(obs.run_probes(slug, variant)["probes"], "02.Q2")
    assert p["status"] == "fail"
    assert "K3" in p["detail"]


def test_02q2_red_gap_resolved_passes(tmp_topic):
    slug, variant = tmp_topic
    topic_io.update_topic(slug, variant, stage_history=[
        {"stage": "02-gather-materials", "entered_at": "t0", "exited_at": "t1",
         "gap_snapshot": {"uncovered_ks": ["K3"]}},
        {"stage": "03-extracting", "entered_at": "t1", "exited_at": None,
         "gap_snapshot": {"uncovered_ks": []}},
    ])
    p = _probe(obs.run_probes(slug, variant)["probes"], "02.Q2")
    assert p["status"] == "pass"
```

在 `observability.py` 加：

```python
def _stage_02(slug, variant, topic) -> list[Probe]:
    hist = topic.get("stage_history") or []
    def snap(stage_prefix):
        return next((h.get("gap_snapshot", {}) for h in hist
                     if h.get("stage", "").startswith(stage_prefix)), None)
    s02, s03 = snap("02"), snap("03")
    if s02 is None or s03 is None:
        return [Probe("02.Q2", "gap 红项被处理 vs 无视硬升", "02-gather-materials",
                      "quality", "na", "stage_history diff", tier=1,
                      detail="无 02/03 快照（旧 topic 或未到）")]
    carried = sorted(set(s02.get("uncovered_ks") or []) & set(s03.get("uncovered_ks") or []))
    fail = bool(carried)
    return [Probe(
        "02.Q2", "gap 红项被处理 vs 无视硬升", "02-gather-materials", "quality",
        "fail" if fail else "pass", "stage_history diff", tier=1,
        detail=("红着硬升: " + ", ".join(carried)) if fail else "红项进 03 前已清",
        action="补料或诚实标缺" if fail else "",
    )]
```

`run_probes` 追加 `probes += _stage_02(slug, variant, topic)`。

- [ ] **Step 6: 跑全部测试 + detect_changes**

Run: `python3 -m pytest prism/scripts/test_observability.py prism/scripts/test_topic_stage_history.py prism/scripts/test_gap_detector.py -v`
Expected: PASS（含回归 gap_detector）

提交前跑 `gitnexus_detect_changes()`，确认只动 set_stage/detect_gaps/observability 预期范围。

- [ ] **Step 7: Commit**

```bash
git add prism/scripts/topic.py prism/scripts/gap_detector.py prism/scripts/observability.py \
        prism/scripts/test_topic_stage_history.py prism/scripts/test_observability.py
git commit -m "feat(prism): B1 stage_history+gap快照承重墙 + 02.Q2 红项硬升探针"
```

---

## Task 5: B2/B3/B4 sidecar 字段 + 04 探针（04.Q1/Q3/S1）

**Files:**
- Modify: `prism/scripts/observability.py`（04.S1/Q1/Q3）
- Modify: `prism/scripts/test_observability.py`
- Modify: sidecar 模板 + `prism/workflows/04-synthesize/_company_case.md` 等（加字段写入指引）
- Modify: `prism/scripts/outputs.py`（sidecar 校验白名单放行 `chain_links`/`honest_gaps`/`market_implied`/`my_vs_market_delta`）

> 先 `grep -n "def .*sidecar\|allowed\|schema\|_VALID" prism/scripts/outputs.py` 定位 sidecar 字段校验处；把 4 个新键加入白名单。impact 跑 `gitnexus_impact` 于该校验函数。

- [ ] **Step 1: 写失败测试**

```python
def _write_sidecar(slug, variant, tmproot, payload):
    import yaml
    d = tmproot / "topics" / slug / variant / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    (d / "07_decision_kit.yaml").write_text(
        yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")


def test_04q1_broken_chain_fails(tmp_topic, monkeypatch):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_sidecar(slug, variant, t.PRISM_ROOT, {
        "slug": slug, "variant": variant, "topic_type": "company",
        "chain_links": {"rings_present": [1, 2, 3, 4, 6],   # 缺 5
                        "r4_anchors_r2": True, "r6_takes_r4_ev": True,
                        "r5_has_kill_signpost": False},
    })
    p = _probe(obs.run_probes(slug, variant)["probes"], "04.Q1")
    assert p["status"] == "fail"
    assert "5" in p["detail"]


def test_04q1_intact_chain_passes(tmp_topic):
    slug, variant = tmp_topic
    import prism.scripts.topic as t
    _write_sidecar(slug, variant, t.PRISM_ROOT, {
        "chain_links": {"rings_present": [1, 2, 3, 4, 5, 6],
                        "r4_anchors_r2": True, "r6_takes_r4_ev": True,
                        "r5_has_kill_signpost": True},
    })
    p = _probe(obs.run_probes(slug, variant)["probes"], "04.Q1")
    assert p["status"] == "pass"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest prism/scripts/test_observability.py -k 04q1 -v`
Expected: FAIL

- [ ] **Step 3: 写实现**

```python
import yaml as _yaml


def _read_sidecar(slug, variant) -> dict:
    d = topic_io.PRISM_ROOT / "topics" / slug / variant / "outputs"
    for name in ("07_decision_kit.yaml", "09_industry_to_arenas.yaml", "10_peer_matrix.yaml"):
        p = d / name
        if p.is_file():
            try:
                return _yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except Exception:
                return {}
    return {}


def _stage_04(slug, variant, topic) -> list[Probe]:
    sc = _read_sidecar(slug, variant)
    cl = sc.get("chain_links")
    if not cl:
        q1 = Probe("04.Q1", "断链（6环结构+交叉引用）", "04-synthesizing", "quality",
                   "na", "sidecar chain_links", tier=1, detail="无 chain_links（未合成或旧产出）")
    else:
        missing = [r for r in (1, 2, 3, 4, 5, 6) if r not in (cl.get("rings_present") or [])]
        broken = [k for k in ("r4_anchors_r2", "r6_takes_r4_ev", "r5_has_kill_signpost")
                  if cl.get(k) is False]
        fail = bool(missing or broken)
        q1 = Probe("04.Q1", "断链（6环结构+交叉引用）", "04-synthesizing", "quality",
                   "fail" if fail else "pass", "sidecar chain_links", tier=1,
                   detail=(f"缺环 {missing}; 断 {broken}".strip("; ")) if fail else "链完整",
                   action="补环/补交叉引用" if fail else "")

    # 04.Q3: 诚实缺口标记（检测侧）—— 有 honest_gaps 字段即视为诚实标了
    hg = sc.get("honest_gaps")
    q3 = Probe("04.Q3", "缺口诚实标 vs 冒充实证", "04-synthesizing", "quality",
               "na" if not sc else ("pass" if hg is not None else "flag"),
               "sidecar honest_gaps", tier=2,
               detail="有诚实缺口列表" if hg else "无 honest_gaps，冒充侧需人复核",
               action="" if hg else "人复核是否冒充实证")
    return [q1, q3]
```

`run_probes` 追加 `probes += _stage_04(slug, variant, topic)`。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest prism/scripts/test_observability.py -k 04q1 -v`
Expected: PASS

- [ ] **Step 5: sidecar 白名单 + workflow 写入指引**

- `outputs.py` sidecar 字段校验白名单加 `chain_links` / `honest_gaps` / `market_implied` / `my_vs_market_delta`（按 Step 0 grep 到的实际机制）。
- `04-synthesize/_company_case.md` / `_industry_funnel.md` / `_arena_funnel.md` 各加一段：合成收尾时按 spec §4.2-4.4 落 `chain_links`（rings_present + 三布尔）、`honest_gaps`（[{ring,kind,note}]）、`market_implied` + `my_vs_market_delta`。引 `prism/specs/observability.md` §4。

- [ ] **Step 6: 回归 + detect_changes + commit**

Run: `python3 -m pytest prism/scripts/test_observability.py prism/scripts/test_sidecar_edit.py prism/scripts/test_outputs.py -v`
Expected: PASS（sidecar 现消费回归不破）

```bash
git add prism/scripts/observability.py prism/scripts/test_observability.py \
        prism/scripts/outputs.py prism/workflows/04-synthesize/
git commit -m "feat(prism): B2/B3/B4 sidecar 字段 + 04.Q1/Q3 断链与诚实缺口探针"
```

---

## Task 6（可选 · 低优先）: B6 findings 冲突标记 + 03.Q3

仅当需要 03.Q3 识别侧落地时做；否则 03.Q3 退化为纯 ② 挂旗（默认 flag）。

**Files:**
- Modify: `prism/scripts/observability.py`（03.Q3）
- Modify: `prism/scripts/test_observability.py`
- Modify: `prism/workflows/03-extract-findings.md`（findings frontmatter 加可选 `conflicts_with`/`conflict_note`）

- [ ] **Step 1: 写测试**

```python
def test_03q3_no_findings_is_na(tmp_topic):
    slug, variant = tmp_topic
    p = _probe(obs.run_probes(slug, variant)["probes"], "03.Q3")
    assert p["status"] in ("na", "flag")
```

- [ ] **Step 2: 跑确认失败** — Run: `python3 -m pytest prism/scripts/test_observability.py -k 03q3 -v` → FAIL

- [ ] **Step 3: 实现**（扫 findings frontmatter 有无 conflict 标记；无 findings → na，有但无标记 → flag）

```python
def _stage_03(slug, variant) -> list[Probe]:
    fdir = topic_io.PRISM_ROOT / "topics" / slug / variant / "findings"
    files = list(fdir.glob("*.md")) if fdir.is_dir() else []
    if not files:
        return [Probe("03.Q3", "冲突证据被识别", "03-extracting", "quality",
                      "na", "findings conflict 标记", tier=2, detail="无 findings")]
    has_conflict_marker = any("conflicts_with" in f.read_text(encoding="utf-8")
                              for f in files)
    return [Probe("03.Q3", "冲突证据被识别", "03-extracting", "quality",
                  "pass" if has_conflict_marker else "flag",
                  "findings conflict 标记", tier=2,
                  detail="有冲突标记" if has_conflict_marker else "无标记，需人复核是否和稀泥",
                  action="" if has_conflict_marker else "人复核冲突处理")]
```

`run_probes` 追加 `probes += _stage_03(slug, variant)`。

- [ ] **Step 4: 跑确认通过** — Run: `python3 -m pytest prism/scripts/test_observability.py -k 03q3 -v` → PASS

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/observability.py prism/scripts/test_observability.py prism/workflows/03-extract-findings.md
git commit -m "feat(prism): B6 findings 冲突标记 + 03.Q3 探针"
```

---

## Task 7: 平行诊断页渲染器

**Files:**
- Create: `prism/scripts/observability_render.py`
- Create: `prism/scripts/test_observability_render.py`

- [ ] **Step 1: 写失败测试**

```python
import tempfile
from pathlib import Path

import pytest

from prism.scripts import topic as topic_io
from prism.scripts import observability_render as render


@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.gap_detector.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    slug, variant = "rnd-test", "test"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(slug=slug, display_name="T", topic_type="company",
                          question="Q?", geo="US", depth="quick", variant=variant)
    return slug, variant


def test_render_contains_sections(tmp_topic):
    slug, variant = tmp_topic
    md = render.render_diagnostic_page(slug, variant)
    assert "# 诊断" in md
    assert "体检条" in md or "体检" in md
    assert "贯穿" in md
    assert "复核旗" in md


def test_render_flag_summary_lists_flags(tmp_topic):
    slug, variant = tmp_topic
    topic_io.set_critic_verdict(slug, variant, verdict="approve", score=4)
    md = render.render_diagnostic_page(slug, variant)
    assert "05.Q1" in md   # steelman flag 进复核旗汇总
```

- [ ] **Step 2: 跑确认失败** — Run: `python3 -m pytest prism/scripts/test_observability_render.py -v` → FAIL

- [ ] **Step 3: 实现渲染器**

```python
"""Trace → per-topic 诊断页 markdown（仿 dashboard.py）。纯被动。"""
from prism.scripts.observability import run_probes

_BADGE = {"pass": "🟢", "fail": "🔴", "flag": "🟠", "na": "⚪"}


def render_diagnostic_page(slug: str, variant: str) -> str:
    trace = run_probes(slug, variant)
    probes = trace["probes"]
    s = trace["summary"]
    L = [f"# 诊断 · {slug} / {variant}", ""]
    # 体检条
    L.append(f"**体检条**：🔴 {s['fail']} 　🟠 {s['flag']} 　🟢 {s['pass']} 　⚪ {s['na']}")
    L.append("")

    def section(title, rows):
        L.append(f"## {title}")
        L.append("| | 探针 | 检查 | detail | 动作 |")
        L.append("|--|--|--|--|--|")
        for p in rows:
            L.append(f"| {_BADGE[p['status']]} | {p['probe_id']} | {p['label']} "
                     f"| {p['detail']} | {p['action']} |")
        L.append("")

    cc = [p for p in probes if p["stage"] == "cross-cutting"]
    section("贯穿（cross-cutting）", cc)

    stages = ["00", "01", "02", "03", "04", "05", "06"]
    for st in stages:
        rows = [p for p in probes if p["stage"].startswith(st)]
        if rows:
            section(f"Stage {st}", rows)

    flags = [p for p in probes if p["status"] == "flag"]
    L.append("## 复核旗汇总（待人复核）")
    if flags:
        for p in flags:
            L.append(f"- 🟠 **{p['probe_id']}** {p['label']} — {p['detail']}")
    else:
        L.append("- 无")
    return "\n".join(L) + "\n"
```

- [ ] **Step 4: 跑确认通过** — Run: `python3 -m pytest prism/scripts/test_observability_render.py -v` → PASS

- [ ] **Step 5: 全量回归 + Commit**

Run: `python3 -m pytest prism/scripts/test_observability.py prism/scripts/test_observability_render.py prism/scripts/test_topic_stage_history.py prism/scripts/test_gap_detector.py -v`
Expected: PASS

```bash
git add prism/scripts/observability_render.py prism/scripts/test_observability_render.py
git commit -m "feat(prism): 平行诊断页渲染器"
```

> 接线到 web `/prism/{slug}/{variant}/trace` 路由属 web-server 集成，超出本计划脚本层范围；渲染器函数 `render_diagnostic_page` 已就绪可被 web 层直接调用。

---

## Self-Review（写完计划后自查）

**Spec coverage：**
- §3.1 贯穿 CC1-6 → Task 1（CC1/3/4/6）+ Task 2（CC2）✓；CC5 假覆盖（addresses_match_event_anchored）**未单列任务** → 见下补。
- §3.1 B5′ → Task 3 ✓
- §3.2 00 → 00.S/Q/X 探针**仅部分**（计划聚焦高价值；00.Q3=CC1、其余 00 探针为同模式机械字段检查）→ 见下补。
- §3.2 01 → 01.Q1/X1 ✓（Task 2）；01.Q2/Q3/X3/S 同模式可后补。
- §3.2 02 → 02.Q2 ✓（Task 4）；02.Q3 同 diff 模式（Task 4 已建 stage_history，02.Q3 复用）。
- §3.2 03 → 03.Q3 ✓（Task 6）；03.Q1（frontmatter 字段）同 Task 6 扫描模式。
- §3.2 04 → 04.Q1/Q3/S1 ✓（Task 5）；04.Q4 已存在 sidecar schema、04.Q5 已存在 F17、04.Q2/X1/X2 后补。
- §3.2 05 → 05.X1/Q1/Q2 ✓（Task 2）；05.Q3 同模式。
- §4 B1 ✓Task4 / B2-B4 ✓Task5 / B6 ✓Task6 / B5′ ✓Task3。
- §6 诊断页 ✓Task7。

**补充说明（避免遗漏被当成完成）**：本计划把**探针引擎 + 承重墙 B1 + 加固 04 的 B2-B4 + 诊断页**做成可跑闭环；其余**同模式的机械字段探针**（00.Q1/Q2/Q4/X1、01.Q2/Q3/X3、02.Q3、03.Q1、04.Q2/X1/X2、05.Q3、06.Q1、CC5）是**纯增量、零新机制**——每条 = 在 `observability.py` 加一个读字段的 `Probe(...)` + 一个断言测试，照 Task 2 的体例补。执行 Task 1-7 后，追加一个 **Task 8（探针补全）** 把这批按 §3 全表逐条加齐即可，无新风险。

**Placeholder scan：** 各 Step 含真实代码/命令/预期；签名不确定处（set_thesis/set_critic_verdict/append_search_log/get_current_prescan_status/critic 存储位/sidecar 校验位/stage 存储形态）均显式标注"先 grep 核对"并给了默认实现路径，非 TODO。

**Type consistency：** `Probe` 字段一致（probe_id/label/stage/family/status/signal/tier/detail/action）；`run_probes` 返回 `{slug,variant,probes,summary}` 全程一致；B1 采用顶层 `stage_history`（非 `stage.history`），测试与实现已对齐。

---

## 风险与顺序回顾

- **MEDIUM 接缝 1**：B1 改 `set_stage`（Task 4）。缓解：用平行 `stage_history` 顶层键，不动现有 `stage` str，零破坏现消费方；同 stage 幂等；快照失败返回空不抛；延迟 import 防循环。impact + detect_changes 双跑。
- **MEDIUM 接缝 2**：B2-B4 给 sidecar 加字段（Task 5）。缓解：只加白名单放行，不改现有字段；回归 `test_sidecar_edit.py`/`test_outputs.py`。
- 其余皆新文件 + 纯读，LOW。
- **不破原理 1/3**：观测层零 LLM；纯展示不设闸；trace 落现有 yaml 体系。

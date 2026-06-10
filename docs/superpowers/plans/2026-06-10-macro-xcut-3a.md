# 宏观层第三期 · 阶段 3a 横切接入 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 company case 合成时显式消费 regime（定性四渠道 + DCF 贴现率锚）并落反查印章；新持仓自注册进 transmission_map、漏覆盖被看门狗暴露；regime 重合成时依赖变化的持仓被零-LLM 扫出、盖 stale 旗 + 提 `macro_regime` proposal（stage 不动）。

**Architecture:** 新增零-LLM 脚本 `macro_xcut.py`（印章 CRUD + staleness 扫 + coverage 看门狗 + self-register），镜像既有 `eval_snapshot.py`/`diff_since_last` 派生模式。transmission_map 行追加三个可空字段不破 dashboard 契约。company 侧新 sidecar `macro_stamp.yaml` 作反查锚。proposal 走既有 `monitor.propose_flips`（新 `kind='macro_regime'`，confirm_flip 对未知 kind 已天然走信息型回路，无需改）。工作流 .md 与 web 模板增量改。

**Tech Stack:** Python 3.14（`.venv/bin/python`）、pytest（`-p no:cacheprovider -q`）、PyYAML、FastAPI + Jinja2 模板。判断永远人在对话触发——本期脚本全零-LLM。

设计依据：`docs/superpowers/specs/2026-06-10-macro-cross-cutting-and-judgment-ledger-design.md` §2（阶段 3a）。

---

## 文件结构

| 文件 | 责任 | 动作 |
|---|---|---|
| `prism/scripts/macro_xcut.py` | 印章 CRUD + staleness 扫 + coverage 看门狗 + self-register（零-LLM） | 新建 |
| `prism/scripts/test_macro_xcut.py` | 上述全覆盖 | 新建 |
| `prism/scripts/monitor.py` | 复用 `propose_flips`；无需改 confirm_flip（已天然处理未知 kind） | 只读 + 回归测试 |
| `prism/scripts/test_monitor_macro.py` | `macro_regime` proposal confirm 走信息型回路回归 | 扩展 |
| `prism/scripts/dashboard.py` | `_collect_macro_banner` 加过期持仓 + 覆盖率 | 改 |
| `prism/scripts/test_dashboard_macro.py` | banner 新字段 | 扩展 |
| `prism/workflows/04-synthesize/_company_case.md` | Step 1 强制 macro hook | 改（文档） |
| `prism/workflows/04-synthesize/_arena_funnel.md` / `_industry_funnel.md` | 软提示 | 改（文档） |
| `prism/workflows/04-synthesize/_macro_regime.md` | 复核 provisional + 体制变扫失鲜调用 | 改（文档） |
| `app/routes/prism.py` | company 详情页读 macro_stamp 显示宏观背景 | 改 |
| `app/templates/prism/*.html` | dashboard banner 过期/覆盖率 + company 页宏观背景 | 改 |
| `tests/test_macro_inputs_web.py` | company 页宏观背景 + dashboard banner 渲染 | 扩展 |

> **GitNexus 纪律**：动 `dashboard._collect_macro_banner` / `monitor` / `app/routes/prism.py` 既有 symbol 前，先跑 `npx gitnexus analyze`（索引现 stale），再 `gitnexus_impact(target, upstream)` 报爆炸半径，HIGH/CRITICAL 先警告；提交前 `gitnexus_detect_changes`。

---

## 数据契约（本计划全程引用）

**`outputs/macro_stamp.yaml`（company 侧）**
```yaml
slug: pinduoduo
variant: opus4.8
stamped_at: "2026-06-10T...Z"
as_of_regime_version: 3
regime_composite: "美紧中松分化..."
depends_on_states:
  - {conclusion: fx_cny,   state: "人民币企稳", role: load_bearing}
  - {conclusion: rates_us, state: "高位筑顶",   role: confirming}
discount_rate:            # 仅 DCF case；否则 null
  risk_free: 0.0211
  applied_wacc: 0.115
  rate_sensitivity: "贴现率 ±50bp → 估值 ∓12%"
  source_input: "10Y 实际利率 TIPS"
stale: false
stale_reason: null
```
不变量：`depends_on_states[].conclusion` 非空；`role ∈ {load_bearing, confirming, background}`。

**transmission_map.yaml holdings 行追加字段**：`source: macro_synth|self_registered`、`provisional: bool`、`as_of_regime: vN`（均可空；缺省视作 `macro_synth/false/null`）。

---

## Task 1: `macro_xcut.py` 印章 CRUD + 不变量

**Files:**
- Create: `prism/scripts/macro_xcut.py`
- Test: `prism/scripts/test_macro_xcut.py`

- [ ] **Step 1: Write the failing test**

```python
# prism/scripts/test_macro_xcut.py
"""宏观横切（macro_stamp CRUD + staleness 扫 + coverage + self-register）零-LLM 测试。"""
import pytest
import yaml

from prism.scripts import macro_xcut as mx
from prism.scripts import macro_registry as reg
from prism.scripts import eval_snapshot as es
from prism.scripts import topic as topic_mod
from prism.scripts import monitor


@pytest.fixture
def tmp_world(tmp_path, monkeypatch):
    """一个 macro topic（registry+eval_log+transmission_map）+ 若干 company topic。"""
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(es, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(mx, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(topic_mod, "PRISM_ROOT", tmp_path)
    monkeypatch.setattr(monitor, "PRISM_ROOT", tmp_path)
    monkeypatch.setattr(monitor, "QUEUE_PATH", tmp_path / "monitor_queue.yaml")
    return tmp_path


def _write_topic_yaml(root, slug, variant, ttype, display=None):
    d = root / "topics" / slug / variant
    d.mkdir(parents=True, exist_ok=True)
    (d / "topic.yaml").write_text(
        yaml.dump({"slug": slug, "type": ttype, "display_name": display or slug,
                   "scope": {"ticker": "X"}}, allow_unicode=True),
        encoding="utf-8")


def test_read_macro_stamp_missing_returns_empty(tmp_world):
    assert mx.read_macro_stamp("pdd", "v") == {}


def test_write_then_read_macro_stamp_roundtrip(tmp_world):
    _write_topic_yaml(tmp_world, "pdd", "v", "company")
    mx.write_macro_stamp("pdd", "v", {
        "as_of_regime_version": 1, "regime_composite": "x",
        "depends_on_states": [{"conclusion": "fx_cny", "state": "稳", "role": "load_bearing"}],
        "discount_rate": None})
    got = mx.read_macro_stamp("pdd", "v")
    assert got["slug"] == "pdd" and got["variant"] == "v"
    assert got["stale"] is False and got["stale_reason"] is None
    assert got["depends_on_states"][0]["conclusion"] == "fx_cny"


def test_write_macro_stamp_rejects_bad_role(tmp_world):
    _write_topic_yaml(tmp_world, "pdd", "v", "company")
    with pytest.raises(ValueError, match="role 非法"):
        mx.write_macro_stamp("pdd", "v", {
            "depends_on_states": [{"conclusion": "fx_cny", "state": "稳", "role": "WRONG"}]})


def test_write_macro_stamp_rejects_missing_conclusion(tmp_world):
    _write_topic_yaml(tmp_world, "pdd", "v", "company")
    with pytest.raises(ValueError, match="缺 conclusion"):
        mx.write_macro_stamp("pdd", "v", {
            "depends_on_states": [{"state": "稳", "role": "load_bearing"}]})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_xcut.py -p no:cacheprovider -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'prism.scripts.macro_xcut'`

- [ ] **Step 3: Write minimal implementation**

```python
# prism/scripts/macro_xcut.py
"""宏观层横切接入（零-LLM）：company 侧 macro_stamp 反查锚 CRUD + 体制变扫失鲜
+ 覆盖看门狗 + 新持仓自注册。判断永远人在对话触发；本模块只做文件读写与派生。

依赖方向（无环）：macro_xcut → {macro_registry, eval_snapshot, topic, monitor}；
monitor 不 import macro_xcut。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from prism.scripts import macro_registry as reg
from prism.scripts import eval_snapshot as es
from prism.scripts import topic as topic_mod
from prism.scripts import monitor

_PRISM_ROOT = Path(__file__).resolve().parent.parent

VALID_ROLE = ("load_bearing", "confirming", "background")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp_path(slug: str, variant: str) -> Path:
    return _PRISM_ROOT / "topics" / slug / variant / "outputs" / "macro_stamp.yaml"


def read_macro_stamp(slug: str, variant: str) -> dict:
    """读 company 侧宏观印章；缺文件返回 {}（让调用方优雅显示"未接入"而非抛）。"""
    p = _stamp_path(slug, variant)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _validate_stamp(stamp: dict) -> list:
    errors = []
    for i, d in enumerate(stamp.get("depends_on_states") or []):
        if not d.get("conclusion"):
            errors.append(f"depends_on_states[{i}] 缺 conclusion")
        if d.get("role") not in VALID_ROLE:
            errors.append(f"depends_on_states[{i}] role 非法: {d.get('role')!r}")
    return errors


def write_macro_stamp(slug: str, variant: str, stamp: dict) -> Path:
    """校验不变量后落盘 macro_stamp.yaml；补默认 stale/stale_reason/stamped_at。"""
    errors = _validate_stamp(stamp)
    if errors:
        raise ValueError("macro_stamp 校验失败:\n" + "\n".join(errors))
    out = dict(stamp)
    out["slug"], out["variant"] = slug, variant
    out.setdefault("stamped_at", _now_iso())
    out.setdefault("stale", False)
    out.setdefault("stale_reason", None)
    p = _stamp_path(slug, variant)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.dump(out, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_xcut.py -p no:cacheprovider -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/macro_xcut.py prism/scripts/test_macro_xcut.py
git commit -m "feat(prism): macro_xcut macro_stamp CRUD + 不变量校验(零-LLM)"
```

---

## Task 2: `scan_holding_staleness` — 体制变扫失鲜

**Files:**
- Modify: `prism/scripts/macro_xcut.py`
- Test: `prism/scripts/test_macro_xcut.py`

- [ ] **Step 1: Write the failing test**

```python
# 追加到 test_macro_xcut.py

def _seed_macro(root, slug="gm", variant="v"):
    """macro topic：registry 两输入 + 一版 eval（结论 fx_cny=稳）。"""
    reg.create_registry(slug, variant)
    reg.upsert_input(slug, variant, {"name": "USDCNY", "tier": "A",
        "cadence_type": "series", "mechanism": "CO", "importance": "load_bearing"})
    es.record_evaluation(slug, variant, [
        {"id": "fx_cny", "label": "人民币汇率体制", "state": "人民币企稳", "causal": "x",
         "based_on": [{"input": "USDCNY", "role": "load_bearing"}]}], note="v1")
    return slug, variant


def test_staleness_no_stamp_is_skipped(tmp_world):
    gm, v = _seed_macro(tmp_world)
    _write_topic_yaml(tmp_world, "pdd", v, "company")  # 没盖印章
    out = mx.scan_holding_staleness(gm, v)
    assert out == []  # 没接入 → 不在 staleness 范畴（归 coverage）


def test_staleness_state_unchanged_not_stale(tmp_world):
    gm, v = _seed_macro(tmp_world)
    _write_topic_yaml(tmp_world, "pdd", v, "company")
    mx.write_macro_stamp("pdd", v, {"as_of_regime_version": 1,
        "depends_on_states": [{"conclusion": "fx_cny", "state": "人民币企稳", "role": "load_bearing"}]})
    out = mx.scan_holding_staleness(gm, v)
    assert len(out) == 1 and out[0]["stale"] is False


def test_staleness_state_changed_is_stale(tmp_world):
    gm, v = _seed_macro(tmp_world)
    _write_topic_yaml(tmp_world, "pdd", v, "company")
    mx.write_macro_stamp("pdd", v, {"as_of_regime_version": 1,
        "depends_on_states": [{"conclusion": "fx_cny", "state": "人民币企稳", "role": "load_bearing"}]})
    # 新一版 regime：fx_cny 翻成贬压
    es.record_evaluation(gm, v, [
        {"id": "fx_cny", "label": "人民币汇率体制", "state": "贬压重来", "causal": "y",
         "based_on": [{"input": "USDCNY", "role": "load_bearing"}]}], note="v2")
    out = mx.scan_holding_staleness(gm, v)
    assert out[0]["stale"] is True
    assert out[0]["changed_states"][0] == {
        "conclusion": "fx_cny", "from": "人民币企稳", "to": "贬压重来", "role": "load_bearing"}
    assert "人民币企稳" in out[0]["reason"] and "贬压重来" in out[0]["reason"]


def test_staleness_no_regime_eval_marks_no_basis(tmp_world):
    reg.create_registry("gm", "v")  # 无 eval
    _write_topic_yaml(tmp_world, "pdd", "v", "company")
    mx.write_macro_stamp("pdd", "v", {"as_of_regime_version": 1,
        "depends_on_states": [{"conclusion": "fx_cny", "state": "稳", "role": "load_bearing"}]})
    out = mx.scan_holding_staleness("gm", "v")
    assert out[0]["stale"] is False and out[0]["basis"] == "no_regime_eval"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_xcut.py -k staleness -p no:cacheprovider -q`
Expected: FAIL with `AttributeError: module 'prism.scripts.macro_xcut' has no attribute 'scan_holding_staleness'`

- [ ] **Step 3: Write minimal implementation**

```python
# 追加到 macro_xcut.py

def _latest_regime_states(macro_slug: str, macro_variant: str):
    """最新 regime eval 的 (version, {conclusion_id: state})；无 eval → (None, {})。"""
    latest = es.latest_evaluation(macro_slug, macro_variant)
    if not latest:
        return None, {}
    states = {c.get("id"): c.get("state") for c in (latest.get("conclusions") or [])}
    return latest.get("version"), states


def scan_holding_staleness(macro_slug: str, macro_variant: str) -> list:
    """枚举带 macro_stamp 的 company topic，比依赖体制状态 vs 最新 regime。零 LLM。

    返回 [{slug, variant, stale, reason, changed_states:[{conclusion,from,to,role}],
           as_of_regime_version, latest_regime_version}]。
    无 regime eval → stale=False + basis='no_regime_eval'（无基准，不报错）。
    没盖印章的 company 不收（归 coverage_gaps）。
    """
    version, states = _latest_regime_states(macro_slug, macro_variant)
    out = []
    for t in topic_mod.list_topics(macro_variant):
        if t.get("type") != "company":
            continue
        cslug, cvar = t.get("slug"), t.get("variant")
        stamp = read_macro_stamp(cslug, cvar)
        if not stamp:
            continue
        if version is None:
            out.append({"slug": cslug, "variant": cvar, "stale": False, "reason": None,
                        "changed_states": [], "basis": "no_regime_eval"})
            continue
        changed = []
        for d in stamp.get("depends_on_states") or []:
            cid = d.get("conclusion")
            now_state = states.get(cid)
            if now_state is not None and now_state != d.get("state"):
                changed.append({"conclusion": cid, "from": d.get("state"),
                                "to": now_state, "role": d.get("role")})
        stale = bool(changed)
        reason = None
        if stale:
            f = changed[0]
            reason = (f"依赖的『{f['from']}』已变『{f['to']}』"
                      f"(regime v{stamp.get('as_of_regime_version')}→v{version})")
        out.append({"slug": cslug, "variant": cvar, "stale": stale, "reason": reason,
                    "changed_states": changed,
                    "as_of_regime_version": stamp.get("as_of_regime_version"),
                    "latest_regime_version": version})
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_xcut.py -k staleness -p no:cacheprovider -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/macro_xcut.py prism/scripts/test_macro_xcut.py
git commit -m "feat(prism): macro_xcut.scan_holding_staleness 体制变扫失鲜(零-LLM)"
```

---

## Task 3: `coverage_gaps` — 覆盖看门狗

**Files:**
- Modify: `prism/scripts/macro_xcut.py`
- Test: `prism/scripts/test_macro_xcut.py`

- [ ] **Step 1: Write the failing test**

```python
# 追加到 test_macro_xcut.py

def _write_transmission_map(root, slug, variant, holdings):
    d = root / "topics" / slug / variant / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    (d / "transmission_map.yaml").write_text(
        yaml.dump({"slug": slug, "variant": variant, "holdings": holdings},
                  allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_coverage_gaps_reports_missing_and_provisional(tmp_world):
    gm, v = "gm", "v"
    _write_topic_yaml(tmp_world, "pdd", v, "company")
    _write_topic_yaml(tmp_world, "futu", v, "company")
    _write_topic_yaml(tmp_world, "baijiu", v, "arena")  # 非 company 不计
    _write_transmission_map(tmp_world, gm, v, [
        {"slug": "pdd", "provisional": True},   # 已覆盖但临时
    ])
    cov = mx.coverage_gaps(gm, v)
    assert cov["missing"] == ["futu"]
    assert cov["provisional"] == ["pdd"]
    assert cov["covered_count"] == 1 and cov["total_company"] == 2


def test_coverage_gaps_no_transmission_map(tmp_world):
    _write_topic_yaml(tmp_world, "pdd", "v", "company")
    cov = mx.coverage_gaps("gm", "v")
    assert cov["missing"] == ["pdd"] and cov["covered_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_xcut.py -k coverage -p no:cacheprovider -q`
Expected: FAIL with `AttributeError: ... has no attribute 'coverage_gaps'`

- [ ] **Step 3: Write minimal implementation**

```python
# 追加到 macro_xcut.py

def coverage_gaps(macro_slug: str, macro_variant: str) -> dict:
    """company-type topic vs transmission_map holdings → 漏注册 + provisional。零 LLM。

    呼应"输入不能有遗漏、沉默≠确认"：漏覆盖被显式暴露。slug 匹配（holdings 行无 variant）。
    """
    tm = reg.read_transmission_map(macro_slug, macro_variant)
    holdings = tm.get("holdings") or []
    covered = {h.get("slug") for h in holdings if h.get("slug")}
    provisional = sorted(h.get("slug") for h in holdings
                         if h.get("provisional") and h.get("slug"))
    company_slugs = {t.get("slug") for t in topic_mod.list_topics(macro_variant)
                     if t.get("type") == "company"}
    return {"missing": sorted(company_slugs - covered),
            "provisional": provisional,
            "covered_count": len(company_slugs & covered),
            "total_company": len(company_slugs)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_xcut.py -k coverage -p no:cacheprovider -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/macro_xcut.py prism/scripts/test_macro_xcut.py
git commit -m "feat(prism): macro_xcut.coverage_gaps 覆盖看门狗(零-LLM)"
```

---

## Task 4: `register_holding_row` — 新持仓自注册

**Files:**
- Modify: `prism/scripts/macro_xcut.py`
- Test: `prism/scripts/test_macro_xcut.py`

- [ ] **Step 1: Write the failing test**

```python
# 追加到 test_macro_xcut.py

def test_register_holding_row_appends_with_provisional(tmp_world):
    gm, v = "gm", "v"
    _write_transmission_map(tmp_world, gm, v, [{"slug": "pdd"}])
    res = mx.register_holding_row(gm, v, {
        "slug": "futu", "display_name": "富途控股", "duration": "long",
        "rate_beta": "high", "as_of_regime": "v3"})
    assert res["registered"] is True
    tm = reg.read_transmission_map(gm, v)
    futu = next(h for h in tm["holdings"] if h["slug"] == "futu")
    assert futu["source"] == "self_registered" and futu["provisional"] is True
    assert futu["as_of_regime"] == "v3"


def test_register_holding_row_existing_is_skipped(tmp_world):
    gm, v = "gm", "v"
    _write_transmission_map(tmp_world, gm, v, [{"slug": "pdd", "source": "macro_synth"}])
    res = mx.register_holding_row(gm, v, {"slug": "pdd", "duration": "mid"})
    assert res["registered"] is False and res["reason"] == "exists"
    tm = reg.read_transmission_map(gm, v)
    assert len(tm["holdings"]) == 1  # 未覆盖既有行


def test_register_holding_row_no_map(tmp_world):
    res = mx.register_holding_row("gm", "v", {"slug": "pdd"})
    assert res["registered"] is False and res["reason"] == "no_transmission_map"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_xcut.py -k register -p no:cacheprovider -q`
Expected: FAIL with `AttributeError: ... has no attribute 'register_holding_row'`

- [ ] **Step 3: Write minimal implementation**

```python
# 追加到 macro_xcut.py

def _transmission_path(slug: str, variant: str) -> Path:
    return _PRISM_ROOT / "topics" / slug / variant / "outputs" / "transmission_map.yaml"


def register_holding_row(macro_slug: str, macro_variant: str, row: dict) -> dict:
    """新持仓自注册进 transmission_map。撞已存在 slug → 跳过+不覆盖。零 LLM。

    补默认 source=self_registered / provisional=True。注：yaml 回写丢顶部注释，
    由下次 _macro_regime 全量合成复核 provisional 时重生成，可接受。
    """
    tm = reg.read_transmission_map(macro_slug, macro_variant)
    if not tm:
        return {"registered": False, "reason": "no_transmission_map"}
    holdings = tm.setdefault("holdings", [])
    if any(h.get("slug") == row.get("slug") for h in holdings):
        return {"registered": False, "reason": "exists", "slug": row.get("slug")}
    new_row = dict(row)
    new_row.setdefault("source", "self_registered")
    new_row.setdefault("provisional", True)
    holdings.append(new_row)
    p = _transmission_path(macro_slug, macro_variant)
    p.write_text(yaml.dump(tm, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return {"registered": True, "slug": row.get("slug")}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_xcut.py -k register -p no:cacheprovider -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/macro_xcut.py prism/scripts/test_macro_xcut.py
git commit -m "feat(prism): macro_xcut.register_holding_row 新持仓自注册(零-LLM)"
```

---

## Task 5: `apply_holding_staleness` — 盖 stale 旗 + 写 macro_regime proposal

**Files:**
- Modify: `prism/scripts/macro_xcut.py`
- Test: `prism/scripts/test_macro_xcut.py`

- [ ] **Step 1: Write the failing test**

```python
# 追加到 test_macro_xcut.py

def test_apply_staleness_flags_stamp_and_writes_proposal(tmp_world):
    gm, v = _seed_macro(tmp_world)
    _write_topic_yaml(tmp_world, "pdd", v, "company")
    mx.write_macro_stamp("pdd", v, {"as_of_regime_version": 1,
        "depends_on_states": [{"conclusion": "fx_cny", "state": "人民币企稳", "role": "load_bearing"}]})
    es.record_evaluation(gm, v, [
        {"id": "fx_cny", "label": "人民币汇率体制", "state": "贬压重来", "causal": "y",
         "based_on": [{"input": "USDCNY", "role": "load_bearing"}]}], note="v2")

    res = mx.apply_holding_staleness(gm, v)
    assert res["applied"] == 1
    # 印章被盖 stale
    stamp = mx.read_macro_stamp("pdd", v)
    assert stamp["stale"] is True and "贬压重来" in stamp["stale_reason"]
    # queue 里有一条 macro_regime proposal 指向 pdd
    pending = monitor.load_queue()
    macro_regime = [p for p in pending if p["kind"] == "macro_regime"]
    assert len(macro_regime) == 1
    assert macro_regime[0]["slug"] == "pdd" and macro_regime[0]["status"] == "awaiting_confirm"
    assert macro_regime[0]["requires_thesis_review"] is True


def test_apply_staleness_noop_when_nothing_stale(tmp_world):
    gm, v = _seed_macro(tmp_world)
    _write_topic_yaml(tmp_world, "pdd", v, "company")
    mx.write_macro_stamp("pdd", v, {"as_of_regime_version": 1,
        "depends_on_states": [{"conclusion": "fx_cny", "state": "人民币企稳", "role": "load_bearing"}]})
    res = mx.apply_holding_staleness(gm, v)
    assert res["applied"] == 0
    assert monitor.load_queue() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_xcut.py -k apply -p no:cacheprovider -q`
Expected: FAIL with `AttributeError: ... has no attribute 'apply_holding_staleness'`

- [ ] **Step 3: Write minimal implementation**

```python
# 追加到 macro_xcut.py

def apply_holding_staleness(macro_slug: str, macro_variant: str) -> dict:
    """落地 staleness：给 stale 持仓盖 stamp.stale 旗 + 写 kind='macro_regime' proposal。

    stage 不动（沿 monitor 信息型回路；confirm 走 confirm_flip 的未知-kind 通道）。
    返回 {applied, scanned}。零 LLM。
    """
    results = scan_holding_staleness(macro_slug, macro_variant)
    labels = es.conclusion_labels(macro_slug, macro_variant)
    today = datetime.now(timezone.utc).date().isoformat()
    proposals = []
    applied = 0
    for r in results:
        if not r.get("stale"):
            continue
        stamp = read_macro_stamp(r["slug"], r["variant"])
        stamp["stale"] = True
        stamp["stale_reason"] = r["reason"]
        write_macro_stamp(r["slug"], r["variant"], stamp)
        applied += 1
        f = r["changed_states"][0]
        clabel = labels.get(f["conclusion"], f["conclusion"])
        entry = (
            f"## {today} 宏观体制变化：{clabel}\n"
            f"**来源**：宏观层 regime 重合成（v{r['as_of_regime_version']}→v{r['latest_regime_version']}）\n"
            f"**关键信息**：你依赖的『{f['from']}』已变『{f['to']}』\n"
            f"**对已有判断的影响**：该 case 的宏观背景已过期，建议重判\n"
            f"**当前判断更新**：维持，等用户在 web 端决定是否重跑合成")
        proposals.append({
            "slug": r["slug"], "variant": r["variant"], "kind": "macro_regime",
            "locator": f["conclusion"], "proposed_value": "regime_shift",
            "living_feed_entry": entry,
            "rationale": r["reason"], "requires_thesis_review": True})
    if proposals:
        monitor.propose_flips(proposals)
    return {"applied": applied, "scanned": len(results)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_xcut.py -k apply -p no:cacheprovider -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Run full macro_xcut suite + commit**

Run: `.venv/bin/python -m pytest prism/scripts/test_macro_xcut.py -p no:cacheprovider -q`
Expected: PASS (15 passed)

```bash
git add prism/scripts/macro_xcut.py prism/scripts/test_macro_xcut.py
git commit -m "feat(prism): macro_xcut.apply_holding_staleness 盖旗+macro_regime proposal(零-LLM)"
```

---

## Task 6: `macro_regime` proposal confirm 走信息型回路（回归测试）

**Files:**
- Modify: `prism/scripts/test_monitor_macro.py`

> confirm_flip 对未知 kind 已天然跳过 sidecar 写回、只追加 living_feed + 标 confirmed（与 `macro_input` 同）。本任务**不改 monitor.py**，只加回归测试锁住该行为，防后续重构破坏。

- [ ] **Step 1: Write the failing test**

```python
# 追加到 prism/scripts/test_monitor_macro.py（沿用该文件既有 fixture 风格；
# 若该文件无 tmp 世界 fixture，则照下方自带 monkeypatch）
import yaml
from prism.scripts import monitor
from prism.scripts import topic as topic_mod


def test_confirm_macro_regime_is_informational(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor, "PRISM_ROOT", tmp_path)
    monkeypatch.setattr(monitor, "QUEUE_PATH", tmp_path / "monitor_queue.yaml")
    monkeypatch.setattr(topic_mod, "PRISM_ROOT", tmp_path)
    d = tmp_path / "topics" / "pdd" / "v" / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    monitor.propose_flips([{
        "slug": "pdd", "variant": "v", "kind": "macro_regime", "locator": "fx_cny",
        "proposed_value": "regime_shift", "living_feed_entry": "## t 宏观体制变化\nx",
        "rationale": "r", "requires_thesis_review": True}])
    pid = monitor.load_queue()[0]["proposal_id"]
    res = monitor.confirm_flip(pid)
    assert res["status"] == "confirmed"
    # 信息型：living_feed 被追加，无 sidecar 翻牌报错
    feed = (d / "08_living_feed.md")
    assert feed.exists() and "宏观体制变化" in feed.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it passes (behavior already correct)**

Run: `.venv/bin/python -m pytest prism/scripts/test_monitor_macro.py -k macro_regime -p no:cacheprovider -q`
Expected: PASS（若 FAIL 报 `_append_living_feed` 触达的 output-status bump 缺 topic.yaml，则在 fixture 里补写最小 `topics/pdd/v/topic.yaml`：`{"slug":"pdd","type":"company"}`，再跑）

- [ ] **Step 3: Commit**

```bash
git add prism/scripts/test_monitor_macro.py
git commit -m "test(prism): 锁定 macro_regime proposal confirm 走信息型回路"
```

---

## Task 7: transmission_map schema + `_macro_regime.md` 复核 provisional + 扫失鲜调用（文档）

**Files:**
- Modify: `prism/workflows/04-synthesize/_macro_regime.md`

> 纯文档/工作流编排改动（LLM 合成时遵循），无单元测试；验证靠 grep 确认插入。

- [ ] **Step 1: transmission_map schema 块加三字段说明**

在 `_macro_regime.md` §4 的 `transmission_map.yaml` schema 代码块里，`holdings` 行注释后追加：

```yaml
holdings:
  - {slug: ..., display_name: ..., duration: long|short, rate_beta: high|mid|low,
     usd_exposure: high|mid|low, liquidity_beta: high|mid|low, exposure_score: high|mid|low,
     regime_favor: [...], regime_hurt: [...], plain: "一句大白话传导链",
     source: macro_synth, provisional: false, as_of_regime: vN}   # 新增三字段(3a)
```

并在该 schema 下方"新增字段语义"段补一行：
> `source`=`macro_synth`(macro 合成判) / `self_registered`(company 自注册待复核)；`provisional`=self_registered 未复核；`as_of_regime`=依据哪版 regime eval。**macro 合成时必复核 provisional 行：确认/改写标签 → 清 provisional → 更新 as_of_regime**。

- [ ] **Step 2: Step 5 收尾加体制变扫失鲜调用块**

在 `_macro_regime.md` Step 5「写评估快照」的 `record_evaluation` 代码块**之后**，新增一段：

````markdown
**复核 provisional + 体制变扫失鲜（硬要求 · 写完评估快照后跑）**：record_evaluation 落新版后，跑横切回路——给依赖体制状态已变的持仓盖 stale 旗 + 写 `macro_regime` proposal（stage 不动）：

```bash
python3 -c "
from prism.scripts import macro_xcut as mx
res = mx.apply_holding_staleness('{slug}', '{variant}')
cov = mx.coverage_gaps('{slug}', '{variant}')
print(f'体制变扫失鲜：{res[\"applied\"]}/{res[\"scanned\"]} 持仓标 stale')
print(f'覆盖率：{cov[\"covered_count\"]}/{cov[\"total_company\"]} company 已入表；漏注册={cov[\"missing\"]}；待复核 provisional={cov[\"provisional\"]}')
"
```

> provisional 行的复核是 LLM 动作（在本合成对话里做）：对 `coverage_gaps` 报出的 provisional 持仓，逐行确认/改写四渠道标签、清 `provisional`、更新 `as_of_regime`，写回 transmission_map（照 §4 落盘惯例）。
````

- [ ] **Step 3: 验证插入**

Run: `grep -n "self_registered\|apply_holding_staleness\|provisional" prism/workflows/04-synthesize/_macro_regime.md`
Expected: 命中 schema 字段说明 + Step 5 调用块

- [ ] **Step 4: Commit**

```bash
git add prism/workflows/04-synthesize/_macro_regime.md
git commit -m "docs(prism): _macro_regime 加 transmission provisional 复核 + 体制变扫失鲜"
```

---

## Task 8: `_company_case.md` 强制 macro hook + arena/industry 软提示（文档）

**Files:**
- Modify: `prism/workflows/04-synthesize/_company_case.md`
- Modify: `prism/workflows/04-synthesize/_arena_funnel.md`
- Modify: `prism/workflows/04-synthesize/_industry_funnel.md`

- [ ] **Step 1: `_company_case.md` Step 1 末尾加 macro hook 块**

在 `_company_case.md` Step 1「加载 findings + thesis_v0 + 财务数据」的"亲属复用 hook"说明之后，新增子段：

````markdown
> **宏观横切 hook（company 强制 · 紧随亲属 hook）**：company case 必接入 macro 体制。
>
> 1. **读 macro 产出**：`python3 -c "from prism.scripts import macro_registry as r; import json; tm=r.read_transmission_map('global-macro-rates-liquidity','{variant}'); print(json.dumps([h for h in tm.get('holdings',[]) if h.get('slug')=='{slug}'], ensure_ascii=False))"` 取本持仓行；并 Read `topics/global-macro-rates-liquidity/{variant}/outputs/m_regime_read.md` 的相关体制节。
> 2. **织进决策链**：把四渠道敏感度（贴现率/风险偏好/carry-久期/汇率）+ `regime_favor/hurt` 织进 ⑤风险 与 ②估值——**定性为主**。
> 3. **DCF 锚（仅当 case 跑 DCF）**：取 macro 的 10Y 实际利率（regime_read / 登记表「10Y 实际利率 TIPS」），作无风险腿 → 跑**贴现率 ±50bp 估值弹性**；落进 `macro_stamp.discount_rate`。
> 4. **落 `macro_stamp.yaml`**（反查锚 · 硬要求）：记站在哪版 regime + 依赖哪些体制状态 + 贴现率：
>
> ```bash
> python3 -c "
> from prism.scripts import macro_xcut as mx, eval_snapshot as es
> latest = es.latest_evaluation('global-macro-rates-liquidity', '{variant}')
> mx.write_macro_stamp('{slug}', '{variant}', {
>     'as_of_regime_version': (latest or {}).get('version'),
>     'regime_composite': '<合成时综合判断一句话>',
>     'depends_on_states': [  # 本 case 倚赖的体制状态；conclusion 须是 regime eval 里的真实 id
>         {'conclusion': 'fx_cny',   'state': '<现读数>', 'role': 'load_bearing'},
>         {'conclusion': 'rates_us', 'state': '<现读数>', 'role': 'confirming'},
>     ],
>     'discount_rate': None,  # 跑 DCF 则填 {risk_free, applied_wacc, rate_sensitivity, source_input}
> })
> print('macro_stamp 已落')
> "
> ```
> 5. **不在表则自注册**：若 step 1 取回空（本持仓不在 transmission_map）→ 就着当下 regime **自判一行四渠道标签**，写回（标 provisional 待 macro 复核）：
>
> ```bash
> python3 -c "
> from prism.scripts import macro_xcut as mx, eval_snapshot as es
> latest = es.latest_evaluation('global-macro-rates-liquidity', '{variant}')
> ver = f\"v{(latest or {}).get('version')}\" if latest else None
> print(mx.register_holding_row('global-macro-rates-liquidity', '{variant}', {
>     'slug': '{slug}', 'display_name': '<名>', 'duration': 'long|short',
>     'rate_beta': 'high|mid|low', 'liquidity_beta': 'high|mid|low',
>     'usd_exposure': 'high|mid|low', 'exposure_score': 'high|mid|low',
>     'regime_favor': [...], 'regime_hurt': [...], 'plain': '一句传导链', 'as_of_regime': ver}))
> "
> ```
> **软降级**：无 macro topic / 无 regime eval（`latest is None`）→ 标"无宏观基准"，仍落 stamp（`as_of_regime_version: null`、`depends_on_states: []`），**不阻塞 case 合成**。
````

- [ ] **Step 2: arena/industry 软提示**

在 `_arena_funnel.md` 与 `_industry_funnel.md` 各自合成收尾段（critic 之后、汇报之前）各加一行：

```markdown
> **宏观横切（软提示 · 不强制）**：赛道/行业层多跨标的，宏观敏感度偏糊；如该赛道有显著利率/流动性/汇率暴露，**建议**（非强制）跑一遍 macro hook（见 `_company_case.md` Step 1 宏观横切 hook）补一段体制敏感度。不落 macro_stamp、不参与 staleness/coverage。
```

- [ ] **Step 3: 验证插入**

Run: `grep -n "宏观横切 hook\|macro_stamp\|register_holding_row" prism/workflows/04-synthesize/_company_case.md && grep -ln "宏观横切（软提示" prism/workflows/04-synthesize/_arena_funnel.md prism/workflows/04-synthesize/_industry_funnel.md`
Expected: company 命中 hook 块；arena + industry 各命中软提示

- [ ] **Step 4: Commit**

```bash
git add prism/workflows/04-synthesize/_company_case.md prism/workflows/04-synthesize/_arena_funnel.md prism/workflows/04-synthesize/_industry_funnel.md
git commit -m "docs(prism): company 强制 macro hook + arena/industry 软提示"
```

---

## Task 9: dashboard `_collect_macro_banner` 加过期持仓 + 覆盖率

**Files:**
- Modify: `prism/scripts/dashboard.py:395-421`（`_collect_macro_banner`）
- Test: `prism/scripts/test_dashboard_macro.py`

> 先 `npx gitnexus analyze` 刷新索引，再 `gitnexus_impact(target="_collect_macro_banner", direction="upstream")` 报爆炸半径（HIGH/CRITICAL 先警告）。

- [ ] **Step 1: Write the failing test**

```python
# 追加到 prism/scripts/test_dashboard_macro.py（沿用该文件既有 fixture；
# 下方自带 monkeypatch 以自包含）
import yaml
from prism.scripts import dashboard as dash
from prism.scripts import macro_registry as reg
from prism.scripts import eval_snapshot as es
from prism.scripts import topic as topic_mod
from prism.scripts import macro_xcut as mx


def _mk(root, slug, variant, ttype):
    d = root / "topics" / slug / variant
    d.mkdir(parents=True, exist_ok=True)
    (d / "topic.yaml").write_text(yaml.dump(
        {"slug": slug, "type": ttype, "display_name": slug}, allow_unicode=True), encoding="utf-8")


def test_macro_banner_includes_stale_and_coverage(tmp_path, monkeypatch):
    for m in (dash, reg, es, mx):
        monkeypatch.setattr(m, "PRISM_ROOT" if hasattr(m, "PRISM_ROOT") else "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(topic_mod, "PRISM_ROOT", tmp_path)
    gm, v = "global-macro-rates-liquidity", "opus4.8"
    # transmission_map：含 regime + 一持仓
    od = tmp_path / "topics" / gm / v / "outputs"
    od.mkdir(parents=True, exist_ok=True)
    (od / "transmission_map.yaml").write_text(yaml.dump({
        "slug": gm, "variant": v,
        "regime": {"composite": "x", "conviction": 6},
        "holdings": [{"slug": "pdd", "display_name": "拼多多", "exposure_score": "high"}],
    }, allow_unicode=True, sort_keys=False), encoding="utf-8")
    # macro registry + eval（fx_cny=贬压重来）
    reg.create_registry(gm, v)
    reg.upsert_input(gm, v, {"name": "USDCNY", "cadence_type": "series", "importance": "load_bearing"})
    es.record_evaluation(gm, v, [{"id": "fx_cny", "label": "汇率", "state": "贬压重来",
        "causal": "y", "based_on": [{"input": "USDCNY", "role": "load_bearing"}]}])
    # company pdd 盖了旧印章（依赖 fx_cny=人民币企稳）+ futu 没入表
    _mk(tmp_path, "pdd", v, "company")
    _mk(tmp_path, "futu", v, "company")
    mx.write_macro_stamp("pdd", v, {"as_of_regime_version": 1,
        "depends_on_states": [{"conclusion": "fx_cny", "state": "人民币企稳", "role": "load_bearing"}]})

    banner = dash._collect_macro_banner()
    assert banner is not None
    stale_slugs = [h["slug"] for h in banner["stale_holdings"]]
    assert "pdd" in stale_slugs
    assert banner["coverage"]["missing"] == ["futu"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest prism/scripts/test_dashboard_macro.py -k stale_and_coverage -p no:cacheprovider -q`
Expected: FAIL with `KeyError: 'stale_holdings'`

- [ ] **Step 3: Modify `_collect_macro_banner`**

在 `dashboard.py` `_collect_macro_banner` 内，组装返回 dict 处（现 `return {... "regime":..., ...}`）加两键。先在文件顶部确认/补 import：`from prism.scripts import macro_xcut`（置于既有 prism.scripts import 群）。然后：

```python
    # —— 横切（3a）：过期持仓 + 覆盖率。零-LLM 派生，失败不拖垮 banner ——
    macro_slug = "global-macro-rates-liquidity"
    try:
        stale = [r for r in macro_xcut.scan_holding_staleness(macro_slug, variant) if r.get("stale")]
    except Exception:
        stale = []
    try:
        coverage = macro_xcut.coverage_gaps(macro_slug, variant)
    except Exception:
        coverage = {"missing": [], "provisional": [], "covered_count": 0, "total_company": 0}
```

并在 `return {...}` 里追加：
```python
        "stale_holdings": stale,
        "coverage": coverage,
```

> `variant` 取该函数已有的 macro topic variant 变量（若函数签名无 variant，用 banner 所属 sidecar 的 `variant` 字段，或硬取 `"opus4.8"` 与既有 banner 一致——按现有代码就近变量为准）。

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest prism/scripts/test_dashboard_macro.py -k stale_and_coverage -p no:cacheprovider -q`
Expected: PASS

- [ ] **Step 5: Full dashboard macro suite + commit**

Run: `.venv/bin/python -m pytest prism/scripts/test_dashboard_macro.py -p no:cacheprovider -q`
Expected: PASS（既有用例不回归）

```bash
git add prism/scripts/dashboard.py prism/scripts/test_dashboard_macro.py
git commit -m "feat(prism): dashboard macro banner 加过期持仓+覆盖率(零-LLM)"
```

---

## Task 10: web — dashboard banner 渲染 + company 页宏观背景

**Files:**
- Modify: `app/routes/prism.py`（`@router.get("/{slug}/{variant}")` 详情页，line ~367）
- Modify: `app/templates/prism/dashboard.html`（macro banner 区）
- Modify: `app/templates/prism/detail.html`（或 company 详情对应模板）
- Test: `tests/test_macro_inputs_web.py`

> 先 `gitnexus_impact` 详情页路由函数（upstream），HIGH/CRITICAL 先警告。模板文件名以仓库实际为准（用 `grep -rl "macro" app/templates/prism/` 定位 banner 与详情模板）。

- [ ] **Step 1: Write the failing test（company 页显示宏观背景）**

```python
# 追加到 tests/test_macro_inputs_web.py（沿用该文件 TestClient fixture）

def test_company_page_shows_macro_stamp(client, tmp_prism):  # fixture 名以该文件为准
    # 准备：一个 company topic + 一份 stale 的 macro_stamp
    from prism.scripts import macro_xcut as mx
    # （按该测试文件既有的 topic 建立惯例创建 company topic 'pdd'/'opus4.8'）
    mx.write_macro_stamp("pdd", "opus4.8", {
        "as_of_regime_version": 1, "regime_composite": "美紧中松分化",
        "depends_on_states": [{"conclusion": "fx_cny", "state": "人民币企稳", "role": "load_bearing"}],
        "stale": True, "stale_reason": "依赖的『人民币企稳』已变『贬压重来』(regime v1→v2)"})
    resp = client.get("/prism/pdd/opus4.8")
    assert resp.status_code == 200
    assert "美紧中松分化" in resp.text
    assert "已过期" in resp.text and "贬压重来" in resp.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py -k macro_stamp -p no:cacheprovider -q`
Expected: FAIL（页面无 stamp 文案）

- [ ] **Step 3: 路由读 macro_stamp 传模板**

在 `app/routes/prism.py` 的 `@router.get("/{slug}/{variant}")` 详情处理函数里，组装 `TemplateResponse` context 前加：

```python
    macro_stamp = None
    if topic.get("type") == "company":
        from prism.scripts import macro_xcut
        macro_stamp = macro_xcut.read_macro_stamp(slug, variant) or None
```

并在该 `TemplateResponse(...)` 的 context dict 里加 `"macro_stamp": macro_stamp,`。

- [ ] **Step 4: 模板渲染宏观背景**

在 company 详情模板（Step 0 `grep` 定位，常为 `app/templates/prism/detail.html`）正文合适处加：

```html
{% if macro_stamp %}
<section class="macro-context">
  <h3>🌐 宏观背景 <small>as_of regime v{{ macro_stamp.as_of_regime_version or '—' }}</small></h3>
  <p>{{ macro_stamp.regime_composite or '（未记录综合判断）' }}</p>
  {% if macro_stamp.stale %}
    <p class="stale-flag">⚠️ 已过期：{{ macro_stamp.stale_reason }}（说「重判 {{ macro_stamp.slug }}」重跑合成以刷新）</p>
  {% endif %}
  {% if macro_stamp.discount_rate %}
    <p>贴现率锚：无风险 {{ macro_stamp.discount_rate.risk_free }} · {{ macro_stamp.discount_rate.rate_sensitivity }}</p>
  {% endif %}
</section>
{% endif %}
```

- [ ] **Step 5: dashboard banner 模板加过期持仓 + 覆盖率**

在 dashboard 模板的 macro banner 区（`grep -n "exposure\|最受影响\|regime\|macro" app/templates/prism/dashboard.html` 定位），在「最受影响持仓」列表后加：

```html
{% if macro.stale_holdings %}
<div class="macro-stale">
  <strong>⚠️ 过期持仓（体制已变，建议重判）</strong>
  <ul>{% for h in macro.stale_holdings %}
    <li>{{ h.slug }}：{{ h.reason }}</li>
  {% endfor %}</ul>
</div>
{% endif %}
<div class="macro-coverage">
  覆盖率：{{ macro.coverage.covered_count }}/{{ macro.coverage.total_company }} company 已入表
  {% if macro.coverage.missing %}· 漏注册：{{ macro.coverage.missing | join('、') }}{% endif %}
  {% if macro.coverage.provisional %}· 待复核：{{ macro.coverage.provisional | join('、') }}{% endif %}
</div>
```

> 模板里 banner 上下文键名以 `_render_macro_banner` / dashboard 路由传入的实际变量名为准（grep `_collect_macro_banner` 的消费处确认是 `macro` 还是别名）。

- [ ] **Step 6: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py -k macro_stamp -p no:cacheprovider -q`
Expected: PASS

- [ ] **Step 7: 全量 web + dashboard 回归 + commit**

Run: `.venv/bin/python -m pytest tests/test_macro_inputs_web.py prism/scripts/test_dashboard_macro.py -p no:cacheprovider -q`
Expected: PASS（无回归）

```bash
git add app/routes/prism.py app/templates/prism/
git commit -m "feat(prism): web 显示 company 宏观背景 + dashboard 过期持仓/覆盖率"
```

---

## Task 11: 收尾 — 全量回归 + GitNexus detect_changes

**Files:** 无（验证）

- [ ] **Step 1: 跑全部受影响测试**

Run:
```bash
.venv/bin/python -m pytest prism/scripts/test_macro_xcut.py prism/scripts/test_monitor_macro.py \
  prism/scripts/test_dashboard_macro.py prism/scripts/test_eval_snapshot.py \
  tests/test_macro_inputs_web.py -p no:cacheprovider -q
```
Expected: 全 PASS（新增 ~22 用例 + 既有不回归）

- [ ] **Step 2: GitNexus 改动核对**

Run: `npx gitnexus analyze`（刷新索引）后在对话调 `gitnexus_detect_changes()`，确认改动只触达：`macro_xcut`(新)、`dashboard._collect_macro_banner`、`app/routes/prism.py` 详情路由、对应模板与测试；无意外执行流被牵动。HIGH/CRITICAL 风险向用户报告。

- [ ] **Step 3: 提交计划完成标记（可选）**

```bash
git add -A && git commit -m "chore(prism): 阶段 3a 横切接入完成（macro_xcut + hook + web）" || echo "无残留改动"
```

---

## Self-Review（写计划后对照 spec §2）

- **spec §2.2 transmission 三字段** → Task 4（self-register 写入）+ Task 7（schema 文档）✓
- **spec §2.2 macro_stamp** → Task 1（CRUD+不变量）✓
- **spec §2.3 macro_xcut（staleness/coverage/self-register）** → Task 2/3/4/5 ✓
- **spec §2.3 company 强制 hook + arena/industry 软提示** → Task 8 ✓
- **spec §2.3 _macro_regime 复核 provisional + 扫失鲜** → Task 7 ✓
- **spec §2.3 monitor `kind='macro_regime'`** → Task 5（写）+ Task 6（confirm 回路回归）✓
- **spec §2.3 dashboard 过期持仓+覆盖率 / company 页宏观背景** → Task 9 + Task 10 ✓
- **spec §2.4 stage 不动、stale 走 stamp 旗（不碰 c_investment_case status）** → Task 5 仅写 stamp.stale + proposal，全程不调 set_output_status / set_stage ✓
- **占位扫描**：无 TBD/TODO；模板文件名/banner 上下文键名以 grep 实证（已标注定位命令），非占位。
- **类型一致性**：`scan_holding_staleness` 返回的 `changed_states[].{conclusion,from,to,role}` 与 `apply_holding_staleness` 消费一致；`coverage_gaps` 的 `{missing,provisional,covered_count,total_company}` 与 Task 9/10 消费一致；`write_macro_stamp` 字段与 Task 8 写入、Task 10 渲染一致 ✓
- **DCF 锚** 在 spec §2.2/§2.3 属 company hook 内 LLM 动作（Task 8 文档化 `discount_rate` 字段与 ±50bp 弹性），脚本侧 `macro_stamp` 已留 `discount_rate` 字段承载 ✓

> 阶段 3b（判断台账：`expected`/`eval_score`/`prior_verdict`/战绩卡）见后续独立计划，不在本计划内。

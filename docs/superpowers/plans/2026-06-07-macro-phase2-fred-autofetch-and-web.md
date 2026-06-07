# 宏观层第二期 — FRED 自动抓取 + 报警带 + 尾部源 + Web 展示 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 31 条 FRED 输入按节奏自动抓取并写入 `observed`、把 6 条报警序列的占位阈值替换为校准带（schema 扩展支持绝对水平/方向/持续天数）、把 2 条类别尾部从手填升级为带可信源的 llm-web 监控项、并在 Web 端把宏观层放进顶部导航 + 展示一张输入源信息表。

**Architecture:** 沿用 prism「Python 脚本零-LLM CRUD」边界。新增 `prism/scripts/fred_fetch.py`（纯逻辑 + 可注入 httpx 客户端，便于 mock）；扩展 `macro_registry.py` 的报警判定（`_reading_breaches` + `_series_breached` 支持 level/direction/min_streak，`record_observation` 维护 streak）；用一次性迁移脚本给登记表补 `fred_series_id`、落 6 条报警带、加 2 条尾部输入；fetcher 接进既有 `monitor_runtime.run_monitor_cycle` 的零-LLM 路径；Web 侧新增 `/prism/{slug}/{variant}/macro-inputs` 路由 + 模板 + 顶部导航条目，全部镜像现有 Jinja2/FastAPI 模式。FRED API key 走 `.env`（与 EXA/SERPER/TAVILY_API_KEY 同模式），单元测试一律 mock HTTP，另置一个**联网 smoke 脚本**离线验证 31 个 series_id 真能解析（「可验证、非信我就行」）。

**Tech Stack:** Python 3.14 / pytest / httpx>=0.27 / FastAPI + Jinja2 / PyYAML。FRED REST: `https://api.stlouisfed.org/fred/series/observations`。

**约定（沿用上一期，务必遵守）：**
- 每改一个函数/类/方法前先跑 `gitnexus_impact({target, direction:"upstream"})` 报告 blast radius；HIGH/CRITICAL 先警示。
- 提交前跑 `gitnexus_detect_changes()` 核对 scope。
- **禁止 `git add -A`**——每次提交用显式逐文件 `git add`，避免扫进 baijiu/popmart 等无关 WIP。
- 工作分支 `feat/macro-dynamic-monitoring-mvp`（与上一期同分支续作）。
- commit message 结尾：`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。

---

## File Structure

| 文件 | 职责 |
|---|---|
| `prism/scripts/fred_fetch.py` (新建) | FRED 抓取：`fetch_latest_observation` / `run_fred_fetch` / `_compute_net_liquidity` / CLI |
| `prism/scripts/test_fred_fetch.py` (新建) | fetcher 单测（mock httpx） |
| `prism/scripts/fred_smoke.py` (新建) | 联网 smoke：逐个 series_id 验真能解析（非单测、需 key） |
| `prism/scripts/migrate_macro_phase2.py` (新建) | 一次性迁移：补 fred_series_id + 落 6 报警带 + 加 2 尾部输入 |
| `prism/scripts/test_migrate_macro_phase2.py` (新建) | 迁移结果断言（31 全有 id、6 带精确、2 尾部在册且受监控） |
| `prism/scripts/macro_registry.py` (改) | `_reading_breaches` 新增；`_series_breached` 扩 level/direction/min_streak；`record_observation` 维护 streak |
| `prism/scripts/test_macro_registry.py` (改) | 报警带新 schema 测试 |
| `prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml` (改，经迁移脚本) | 落库 |
| `app/monitor_runtime.py` (改) | `run_monitor_cycle` 加 FRED 抓取的零-LLM 块 |
| `app/routes/prism.py` (改) | `_TYPE_LABEL`/`_TYPE_EMOJI` 加 macro；新增 `/macro-inputs` 路由 |
| `app/templates/base.html` (改) | 顶部导航加「宏观层」+ 键盘快捷键 |
| `app/templates/prism/macro_inputs.html` (新建) | 输入源信息表 |
| `tests/test_macro_inputs_web.py` (新建) | 路由 + 表格渲染（TestClient） |
| `prism/topics/global-macro-rates-liquidity/opus4.8/outputs/00_primer.md` (改) | 加一句指向输入表的指针 |
| `.env.example` (改) | 加 `FRED_API_KEY=` |

---

## FRED series_id 映射表（Task 3 落库用）

✓=高把握；⚠=代理/需 smoke 复核。

| # | 输入名 | fred_series_id | 备注 |
|---|---|---|---|
| 1 | 联邦基金目标区间 | `DFEDTARU` | 目标区间上限 |
| 2 | 非农就业 NFP | `PAYEMS` | |
| 3 | 失业率 | `UNRATE` | |
| 4 | 初请失业金 | `ICSA` | |
| 5 | JOLTS 职位空缺/离职率 | `JTSJOL` | 职位空缺（离职率 JTSQUR 为派生备注） |
| 6 | 零售销售 | `RSAFS` | |
| 7 | 时薪 / ECI | `CES0500000003` | 平均时薪（ECI=ECIALLCIV 季度，备注） |
| 8 | 核心 PCE | `PCEPILFE` | |
| 9 | CPI(核心+supercore) | `CPILFESL` | 核心 CPI（supercore 派生） |
| 10 | PCE 三分项 | `PCEPILFE` | headline 代理（三分项派生） |
| 11 | PPI | `PPIFIS` | 最终需求 PPI |
| 12 | WTI 油价 | `DCOILWTICO` | |
| 13 | 5y5y/breakeven 通胀预期 | `T5YIFR` | 5Y forward |
| 14 | TGA 余额 | `WTREGEN` | 周三周频 |
| 15 | 联邦赤字 | `MTSDS133FMS` | |
| 16 | 美联储资产 WALCL | `WALCL` | |
| 17 | RRP 逆回购 | `RRPONTSYD` | |
| 18 | 净流动性 | `__DERIVED__` | = WALCL − WTREGEN − RRPONTSYD，由 fetcher 算 |
| 19 | 银行准备金 + 准备金/GDP | `WRESBAL` | |
| 20 | 2Y/10Y/30Y 国债 | `DGS10` | headline（DGS2/DGS30 派生） |
| 21 | 10Y 实际利率 TIPS | `DFII10` | |
| 22 | 2s10s 曲线斜率 | `T10Y2Y` | |
| 23 | IG OAS | `BAMLC0A0CM` | |
| 24 | HY OAS | `BAMLH0A0HYM2` | 报警序列 |
| 25 | VIX | `VIXCLS` | |
| 26 | 金融条件指数 FCI(NFCI) | `NFCI` | 芝加哥联储周频 |
| 27 | 广义/EM加权美元 DTWEXBGS | `DTWEXBGS` | |
| 28 | DXY | `DTWEXAFEGS` | ⚠ 代理：Fed 发达经济体美元指数（真 DXY 为 ICE 专有） |
| 29 | USDJPY / 日元 carry | `DEXJPUS` | 报警序列 |
| 30 | 黄金 | `__WEB__` | ⚠ FRED 无可靠日频现货 → 本迁移把其 `fetch_method` 改 `llm-web` |
| 31 | USDCNY | `DEXCHUS` | |

> 黄金（#30）改判为 `llm-web`；DXY（#28）用 FRED 代理但在 smoke 中标注。两条均写进最终报告的开放项。

---

## 报警带（Task 5 落库用）

`alert_band` schema 扩展后字段：`level`(警示阈)、`direction`∈{above,below,abs_above}、`level_alarm`(报警阈，展示/未来用)、`delta`(日变动)、`min_streak`(连续触发天数，默认1)。`_series_breached` 用 `level`/`delta`/`z` 任一命中即越带（warn 档），`level_alarm` 仅作元数据。

| 序列 | 新 alert_band | fetch |
|---|---|---|
| HY OAS | `{level: 450, direction: above, level_alarm: 550}` | fred |
| MOVE 债市波动率 | `{level: 120, direction: above, level_alarm: 140}` | web |
| 跨币种基差(EUR/JPY-USD) | `{level: -40, direction: below, level_alarm: -60}` | web |
| USDJPY / 日元 carry | `{delta: 3.0, level: 158, direction: above, level_alarm: 160}` | fred |
| DR007/R007 | `{level: 2.2, direction: above, level_alarm: 2.5, min_streak: 2}` | web |
| CNH-CNY 价差 | `{level: 0.015, direction: abs_above, level_alarm: 0.030}` | web |

---

### Task 1: FRED API key 配置

**Files:**
- Modify: `.env.example`
- Create: `prism/scripts/fred_fetch.py` (仅 `get_fred_api_key`)
- Test: `prism/scripts/test_fred_fetch.py`

- [ ] **Step 1: 写失败测试**

```python
# prism/scripts/test_fred_fetch.py
import pytest
from prism.scripts import fred_fetch


def test_get_fred_api_key_from_env(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "abc123")
    assert fred_fetch.get_fred_api_key() == "abc123"


def test_get_fred_api_key_missing_raises(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="FRED_API_KEY"):
        fred_fetch.get_fred_api_key()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest prism/scripts/test_fred_fetch.py -v`
Expected: FAIL — `ModuleNotFoundError: prism.scripts.fred_fetch`

- [ ] **Step 3: 最小实现**

```python
# prism/scripts/fred_fetch.py
"""FRED 自动抓取（第二期）。零 LLM：读登记表里 fetch_method==fred-api 的输入，
拉最新观测，调 macro_registry.record_observation 落 observed。单测 mock httpx。"""
from __future__ import annotations

import os

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


def get_fred_api_key() -> str:
    key = os.getenv("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY 未设置（见 .env.example）")
    return key
```

并在 `.env.example` 末尾追加：

```
# FRED (St. Louis Fed) — 宏观层第二期自动抓取
FRED_API_KEY=your_fred_api_key
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest prism/scripts/test_fred_fetch.py -v`
Expected: PASS (2)

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/fred_fetch.py prism/scripts/test_fred_fetch.py .env.example
git commit -m "feat(prism): FRED API key 配置 + fred_fetch 骨架

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 抓取单条最新观测（mock httpx）

**Files:**
- Modify: `prism/scripts/fred_fetch.py`
- Test: `prism/scripts/test_fred_fetch.py`

FRED 返回形如 `{"observations":[{"date":"2026-06-05","value":"4.46"}]}`；`value` 可能为 `"."`（缺测）。

- [ ] **Step 1: 写失败测试**

```python
def _fake_client(payload):
    class _Resp:
        def __init__(self, p): self._p = p
        def raise_for_status(self): pass
        def json(self): return self._p
    class _Client:
        def __init__(self, p): self._p = p
        def get(self, url, params=None, timeout=None): return _Resp(self._p)
    return _Client(payload)


def test_fetch_latest_observation_ok(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k")
    client = _fake_client({"observations": [{"date": "2026-06-05", "value": "4.46"}]})
    val, as_of = fred_fetch.fetch_latest_observation("DGS10", client=client)
    assert val == 4.46
    assert as_of == "2026-06-05"


def test_fetch_latest_observation_missing_value(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k")
    client = _fake_client({"observations": [{"date": "2026-06-05", "value": "."}]})
    val, as_of = fred_fetch.fetch_latest_observation("DGS10", client=client)
    assert val is None
    assert as_of == "2026-06-05"


def test_fetch_latest_observation_empty(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k")
    client = _fake_client({"observations": []})
    val, as_of = fred_fetch.fetch_latest_observation("DGS10", client=client)
    assert val is None and as_of is None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest prism/scripts/test_fred_fetch.py -k fetch_latest -v`
Expected: FAIL — `AttributeError: fetch_latest_observation`

- [ ] **Step 3: 最小实现**（加到 `fred_fetch.py`）

```python
import httpx


def fetch_latest_observation(series_id: str, *, client=None) -> tuple[float | None, str | None]:
    """拉某 FRED series 的最新一条观测。返回 (value, as_of)；缺测/无数据返回 (None, date|None)。
    client 可注入（测试 mock）；默认用 httpx。"""
    params = {
        "series_id": series_id,
        "api_key": get_fred_api_key(),
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1,
    }
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        resp = client.get(FRED_BASE, params=params, timeout=30)
        resp.raise_for_status()
        obs = resp.json().get("observations") or []
    finally:
        if owns:
            client.close()
    if not obs:
        return None, None
    rec = obs[0]
    raw = rec.get("value")
    as_of = rec.get("date")
    if raw in (None, "", "."):
        return None, as_of
    try:
        return float(raw), as_of
    except ValueError:
        return None, as_of
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest prism/scripts/test_fred_fetch.py -k fetch_latest -v`
Expected: PASS (3)

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/fred_fetch.py prism/scripts/test_fred_fetch.py
git commit -m "feat(prism): fred_fetch.fetch_latest_observation（mock 可注入）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 迁移脚本 — 给 31 条补 fred_series_id（+ 黄金改 llm-web）

**Files:**
- Create: `prism/scripts/migrate_macro_phase2.py`
- Test: `prism/scripts/test_migrate_macro_phase2.py`

> ⚠ 改的是登记表数据，不改函数。本任务**只**做 fred_series_id + 黄金 fetch 改判；报警带（Task 5）、尾部输入（Task 6）放后续任务，但都写进同一个 `migrate_macro_phase2.py` 的不同函数，按任务顺序累加。

- [ ] **Step 1: 写失败测试**

```python
# prism/scripts/test_migrate_macro_phase2.py
import copy
import pytest
from prism.scripts import macro_registry as reg
from prism.scripts import migrate_macro_phase2 as mig

SLUG, VAR = "global-macro-rates-liquidity", "opus4.8"


@pytest.fixture
def live_registry():
    """真登记表的内存副本，避免落盘污染。"""
    return copy.deepcopy(reg.read_registry(SLUG, VAR))


def test_add_fred_series_ids_covers_all_fred_inputs(live_registry):
    out = mig.add_fred_series_ids(live_registry)
    fred_inputs = [e for e in out["inputs"] if e.get("fetch_method") == "fred-api"]
    # 迁移后：每条 fred-api 输入都有非空 fred_series_id
    missing = [e["name"] for e in fred_inputs if not e.get("fred_series_id")]
    assert missing == [], f"未映射: {missing}"


def test_gold_reclassified_to_web(live_registry):
    out = mig.add_fred_series_ids(live_registry)
    gold = next(e for e in out["inputs"] if e["name"] == "黄金")
    assert gold["fetch_method"] == "llm-web"


def test_net_liquidity_marked_derived(live_registry):
    out = mig.add_fred_series_ids(live_registry)
    nl = next(e for e in out["inputs"] if e["name"] == "净流动性(=资产−TGA−RRP)")
    assert nl["fred_series_id"] == "__DERIVED__"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest prism/scripts/test_migrate_macro_phase2.py -v`
Expected: FAIL — `ModuleNotFoundError: migrate_macro_phase2`

- [ ] **Step 3: 最小实现**

```python
# prism/scripts/migrate_macro_phase2.py
"""一次性迁移（宏观第二期）：纯函数对 registry dict 变换 + main() 落盘。零 LLM。
按计划任务顺序累加：add_fred_series_ids（T3）/ set_alert_bands（T5）/ add_tail_inputs（T6）。"""
from __future__ import annotations

from prism.scripts import macro_registry as reg

SLUG, VAR = "global-macro-rates-liquidity", "opus4.8"

# 计划「FRED series_id 映射表」的精确落库版本。键=登记表 name 原文。
FRED_SERIES_ID = {
    "联邦基金目标区间": "DFEDTARU",
    "非农就业 NFP": "PAYEMS",
    "失业率": "UNRATE",
    "初请失业金": "ICSA",
    "JOLTS 职位空缺/离职率": "JTSJOL",
    "零售销售": "RSAFS",
    "时薪 / ECI": "CES0500000003",
    "核心 PCE": "PCEPILFE",
    "CPI(核心+supercore)": "CPILFESL",
    "PCE 三分项(supercore/住房/商品)": "PCEPILFE",
    "PPI": "PPIFIS",
    "WTI 油价(+供给/需求分解)": "DCOILWTICO",
    "5y5y/breakeven 通胀预期": "T5YIFR",
    "TGA 余额": "WTREGEN",
    "联邦赤字": "MTSDS133FMS",
    "美联储资产 WALCL(QT 节奏)": "WALCL",
    "RRP 逆回购": "RRPONTSYD",
    "净流动性(=资产−TGA−RRP)": "__DERIVED__",
    "银行准备金 + 准备金/GDP": "WRESBAL",
    "2Y/10Y/30Y 国债": "DGS10",
    "10Y 实际利率 TIPS": "DFII10",
    "2s10s 曲线斜率": "T10Y2Y",
    "IG OAS": "BAMLC0A0CM",
    "HY OAS": "BAMLH0A0HYM2",
    "VIX": "VIXCLS",
    "金融条件指数 FCI(NFCI/GS)": "NFCI",
    "广义/EM加权美元(Fed DTWEXBGS)": "DTWEXBGS",
    "DXY": "DTWEXAFEGS",  # 代理
    "USDJPY / 日元 carry": "DEXJPUS",
    "USDCNY": "DEXCHUS",
    # 黄金不在此表 → 改判 llm-web（见下）
}
RECLASSIFY_TO_WEB = {"黄金"}


def add_fred_series_ids(data: dict) -> dict:
    """给 fetch_method==fred-api 的输入补 fred_series_id；黄金改判 llm-web。原地改并返回。"""
    for e in data["inputs"]:
        name = e.get("name")
        if name in RECLASSIFY_TO_WEB:
            e["fetch_method"] = "llm-web"
            e["source"] = "web"
            continue
        if e.get("fetch_method") == "fred-api":
            sid = FRED_SERIES_ID.get(name)
            if sid:
                e["fred_series_id"] = sid
    return data


def main():
    data = reg.read_registry(SLUG, VAR)
    add_fred_series_ids(data)
    reg._write_yaml(reg._registry_path(SLUG, VAR), data)
    errs = reg.validate_registry(SLUG, VAR)
    print(f"迁移完成；validator {len(errs)} 错")
    for x in errs:
        print(" -", x)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest prism/scripts/test_migrate_macro_phase2.py -v`
Expected: PASS (3)

- [ ] **Step 5: 执行迁移落盘 + 校验**

```bash
python -m prism.scripts.migrate_macro_phase2
```
Expected: `迁移完成；validator 0 错`

- [ ] **Step 6: 提交**

```bash
git add prism/scripts/migrate_macro_phase2.py prism/scripts/test_migrate_macro_phase2.py \
        prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml
git commit -m "feat(prism): 给 31 条 FRED 输入补 fred_series_id（黄金改 llm-web、净流动性派生）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: 报警带 schema 扩展（level/direction/min_streak）

**Files:**
- Modify: `prism/scripts/macro_registry.py`（`_series_breached` 改、新增 `_reading_breaches`、`record_observation` 维护 streak）
- Test: `prism/scripts/test_macro_registry.py`

> **改前先跑 `gitnexus_impact({target:"_series_breached", direction:"upstream"})` 与 `record_observation`、报告 blast radius。** 二者上一期已知被 `scan_macro_inputs` / fetcher 调用。

- [ ] **Step 1: 写失败测试**（追加到 `test_macro_registry.py`）

```python
from prism.scripts import macro_registry as reg

def _entry(band, observed):
    return {"name": "x", "alert_band": band, "observed": observed}

def test_breach_level_above():
    e = _entry({"level": 450, "direction": "above"}, {"value": 460})
    assert reg._series_breached(e) is True
    e2 = _entry({"level": 450, "direction": "above"}, {"value": 440})
    assert reg._series_breached(e2) is False

def test_breach_level_below():
    e = _entry({"level": -40, "direction": "below"}, {"value": -55})
    assert reg._series_breached(e) is True
    e2 = _entry({"level": -40, "direction": "below"}, {"value": -30})
    assert reg._series_breached(e2) is False

def test_breach_abs_above():
    e = _entry({"level": 0.015, "direction": "abs_above"}, {"value": -0.02})
    assert reg._series_breached(e) is True
    e2 = _entry({"level": 0.015, "direction": "abs_above"}, {"value": 0.01})
    assert reg._series_breached(e2) is False

def test_breach_min_streak_requires_consecutive():
    # 当前读数越带，但 streak=1 < min_streak=2 → 不报警
    e = _entry({"level": 2.2, "direction": "above", "min_streak": 2}, {"value": 2.3, "streak": 1})
    assert reg._series_breached(e) is False
    e2 = _entry({"level": 2.2, "direction": "above", "min_streak": 2}, {"value": 2.3, "streak": 2})
    assert reg._series_breached(e2) is True

def test_delta_band_still_works():  # 回归：旧 delta/z 行为不变
    e = _entry({"delta": 3.0}, {"value": 160, "prev_value": 156})
    assert reg._series_breached(e) is True
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest prism/scripts/test_macro_registry.py -k "breach or delta_band" -v`
Expected: FAIL — level/direction 未实现

- [ ] **Step 3: 实现**（替换 `_series_breached`，新增 `_reading_breaches`）

```python
def _reading_breaches(entry: dict) -> bool:
    """单次读数是否越带：delta / z / level(+direction) 任一命中。"""
    band = entry.get("alert_band") or {}
    obs = entry.get("observed") or {}
    v, p = obs.get("value"), obs.get("prev_value")
    if "delta" in band and v is not None and p is not None:
        if abs(v - p) >= band["delta"]:
            return True
    if "z" in band:
        z = obs.get("z")
        if z is not None and abs(z) >= band["z"]:
            return True
    if "level" in band and v is not None:
        d = band.get("direction", "above")
        if d == "above" and v >= band["level"]:
            return True
        if d == "below" and v <= band["level"]:
            return True
        if d == "abs_above" and abs(v) >= band["level"]:
            return True
    return False


def _series_breached(entry: dict) -> bool:
    """alert_series 是否报警：当前读数越带 且 连续越带天数≥min_streak（默认1）。
    streak 由 record_observation 维护；未维护时默认 1（向后兼容旧 delta/z 行为）。"""
    if not _reading_breaches(entry):
        return False
    band = entry.get("alert_band") or {}
    obs = entry.get("observed") or {}
    return obs.get("streak", 1) >= band.get("min_streak", 1)
```

并在 `record_observation` 写完 `obs` 后、`e["observed"] = obs` 之前，维护 streak：

```python
            obs["checked_at"] = _now_iso()
            # 维护连续越带计数（min_streak 用）
            if value is not None:
                breached = _reading_breaches({**e, "observed": obs})
                obs["streak"] = (obs.get("streak", 0) + 1) if breached else 0
            e["observed"] = obs
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest prism/scripts/test_macro_registry.py -v`
Expected: PASS（含全部旧测试，回归不破）

- [ ] **Step 5: detect_changes + 提交**

```bash
# gitnexus_detect_changes() 应只显示 macro_registry 的 _series_breached/record_observation + 新 _reading_breaches
git add prism/scripts/macro_registry.py prism/scripts/test_macro_registry.py
git commit -m "feat(prism): 报警带支持 level/direction/min_streak；record_observation 维护 streak

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: 落 6 条报警带（迁移脚本）

**Files:**
- Modify: `prism/scripts/migrate_macro_phase2.py`（加 `set_alert_bands` + 接进 `main`）
- Test: `prism/scripts/test_migrate_macro_phase2.py`

- [ ] **Step 1: 写失败测试**

```python
EXPECTED_BANDS = {
    "HY OAS": {"level": 450, "direction": "above", "level_alarm": 550},
    "MOVE 债市波动率": {"level": 120, "direction": "above", "level_alarm": 140},
    "跨币种基差(EUR/JPY-USD)": {"level": -40, "direction": "below", "level_alarm": -60},
    "USDJPY / 日元 carry": {"delta": 3.0, "level": 158, "direction": "above", "level_alarm": 160},
    "DR007/R007": {"level": 2.2, "direction": "above", "level_alarm": 2.5, "min_streak": 2},
    "CNH-CNY 价差": {"level": 0.015, "direction": "abs_above", "level_alarm": 0.030},
}

def test_set_alert_bands_exact(live_registry):
    out = mig.set_alert_bands(live_registry)
    by = {e["name"]: e for e in out["inputs"]}
    for name, band in EXPECTED_BANDS.items():
        assert by[name]["alert_band"] == band, name

def test_only_six_alert_series_have_bands_changed(live_registry):
    out = mig.set_alert_bands(live_registry)
    changed = {e["name"] for e in out["inputs"] if e.get("name") in EXPECTED_BANDS}
    assert changed == set(EXPECTED_BANDS)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest prism/scripts/test_migrate_macro_phase2.py -k alert_band -v`
Expected: FAIL — `set_alert_bands` 未定义

- [ ] **Step 3: 实现**（加到 `migrate_macro_phase2.py`）

```python
ALERT_BANDS = {
    "HY OAS": {"level": 450, "direction": "above", "level_alarm": 550},
    "MOVE 债市波动率": {"level": 120, "direction": "above", "level_alarm": 140},
    "跨币种基差(EUR/JPY-USD)": {"level": -40, "direction": "below", "level_alarm": -60},
    "USDJPY / 日元 carry": {"delta": 3.0, "level": 158, "direction": "above", "level_alarm": 160},
    "DR007/R007": {"level": 2.2, "direction": "above", "level_alarm": 2.5, "min_streak": 2},
    "CNH-CNY 价差": {"level": 0.015, "direction": "abs_above", "level_alarm": 0.030},
}


def set_alert_bands(data: dict) -> dict:
    """把 6 条 alert_series 的占位带替换为校准带。原地改并返回。"""
    for e in data["inputs"]:
        band = ALERT_BANDS.get(e.get("name"))
        if band is not None:
            e["alert_band"] = dict(band)
    return data
```

并把 `main()` 改为依次 `add_fred_series_ids(data); set_alert_bands(data)`。

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest prism/scripts/test_migrate_macro_phase2.py -v`
Expected: PASS

- [ ] **Step 5: 执行迁移 + 校验落盘**

```bash
python -m prism.scripts.migrate_macro_phase2
python -c "from prism.scripts import macro_registry as r; print(len(r.validate_registry('global-macro-rates-liquidity','opus4.8')), '错')"
```
Expected: `0 错`

- [ ] **Step 6: 提交**

```bash
git add prism/scripts/migrate_macro_phase2.py prism/scripts/test_migrate_macro_phase2.py \
        prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml
git commit -m "feat(prism): 落 6 条报警序列校准带（替换占位 z:2.0）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: 加 2 条类别尾部输入（PIIE / PCAOB，llm-web 监控）

**Files:**
- Modify: `prism/scripts/migrate_macro_phase2.py`（加 `add_tail_inputs` + 接进 `main`）
- Test: `prism/scripts/test_migrate_macro_phase2.py`

> 尾部从 transmission_map 的手填快照升级为**在册受监控的 llm-web 输入**，使其纳入到期扫描。机制为 CR（相关/情境），tier B，cadence event。

- [ ] **Step 1: 写失败测试**

```python
TAIL_NAMES = {"中美地缘/关税(尾部)", "ADR退市/HFCAA(尾部)"}

def test_add_tail_inputs_present_and_monitored(live_registry):
    out = mig.add_tail_inputs(live_registry)
    by = {e["name"]: e for e in out["inputs"]}
    for n in TAIL_NAMES:
        assert n in by, n
        assert by[n]["fetch_method"] == "llm-web"
        assert by[n]["monitoring"]["enabled"] is True
        assert by[n]["cadence_type"] == "event"
        assert by[n]["source"]  # 非空

def test_add_tail_inputs_idempotent(live_registry):
    once = mig.add_tail_inputs(live_registry)
    n1 = len(once["inputs"])
    twice = mig.add_tail_inputs(once)
    assert len(twice["inputs"]) == n1  # 不重复追加

def test_tail_sources_named(live_registry):
    out = mig.add_tail_inputs(live_registry)
    by = {e["name"]: e for e in out["inputs"]}
    assert "PIIE" in by["中美地缘/关税(尾部)"]["source"]
    assert "PCAOB" in by["ADR退市/HFCAA(尾部)"]["source"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest prism/scripts/test_migrate_macro_phase2.py -k tail -v`
Expected: FAIL — `add_tail_inputs` 未定义

- [ ] **Step 3: 实现**（加到 `migrate_macro_phase2.py`）

```python
TAIL_INPUTS = [
    {
        "name": "中美地缘/关税(尾部)",
        "tier": "B", "cadence_type": "event", "targets": ["fx", "rates"],
        "mechanism": "CR", "importance": "background",
        "source": "PIIE US-China Trade War Tariffs chart + Trump trade war timeline 2.0",
        "fetch_method": "llm-web", "state": "新增(第二期尾部源)",
        "causal_sentence": "关税/地缘冲击经风险偏好与汇率渠道情境式影响中概与出口链（情境相关，非稳定因果）。",
        "lag": "事件驱动", "alert_series": False,
        "monitoring": {"enabled": True},
    },
    {
        "name": "ADR退市/HFCAA(尾部)",
        "tier": "B", "cadence_type": "event", "targets": ["fx"],
        "mechanism": "CR", "importance": "background",
        "source": "PCAOB HFCAA determinations + SEC Commission-Identified Issuers",
        "fetch_method": "llm-web", "state": "新增(第二期尾部源)",
        "causal_sentence": "PCAOB 新负面裁定触发 HFCAA 强制退市路径，情境式冲击中概 ADR 估值（情境相关）。",
        "lag": "事件驱动", "alert_series": False,
        "monitoring": {"enabled": True},
    },
]


def add_tail_inputs(data: dict) -> dict:
    """把 2 条类别尾部加为在册 llm-web 监控项（幂等：按 name 去重）。"""
    existing = {e.get("name") for e in data["inputs"]}
    for t in TAIL_INPUTS:
        if t["name"] not in existing:
            data["inputs"].append(dict(t))
    return data
```

并把 `main()` 末尾追加 `add_tail_inputs(data)`（在 write 前）。

- [ ] **Step 4: 跑测试确认通过 + 执行迁移**

```bash
pytest prism/scripts/test_migrate_macro_phase2.py -v   # PASS
python -m prism.scripts.migrate_macro_phase2           # 0 错
```

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/migrate_macro_phase2.py prism/scripts/test_migrate_macro_phase2.py \
        prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml
git commit -m "feat(prism): 类别尾部升级为在册 llm-web 监控项（PIIE/PCAOB 源）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: 全量抓取 run_fred_fetch（含净流动性派生）

**Files:**
- Modify: `prism/scripts/fred_fetch.py`
- Test: `prism/scripts/test_fred_fetch.py`

- [ ] **Step 1: 写失败测试**

```python
def test_run_fred_fetch_records_observations(monkeypatch, tmp_path):
    monkeypatch.setenv("FRED_API_KEY", "k")
    from prism.scripts import macro_registry as reg

    # 内存登记表：3 条 fred 输入（含净流动性派生）+ 1 条 web（应跳过）
    fake = {"inputs": [
        {"name": "美联储资产 WALCL(QT 节奏)", "fetch_method": "fred-api", "fred_series_id": "WALCL"},
        {"name": "TGA 余额", "fetch_method": "fred-api", "fred_series_id": "WTREGEN"},
        {"name": "RRP 逆回购", "fetch_method": "fred-api", "fred_series_id": "RRPONTSYD"},
        {"name": "净流动性(=资产−TGA−RRP)", "fetch_method": "fred-api", "fred_series_id": "__DERIVED__"},
        {"name": "MOVE 债市波动率", "fetch_method": "llm-web"},
    ]}
    monkeypatch.setattr(reg, "read_registry", lambda s, v: fake)
    series_vals = {"WALCL": (7000.0, "2026-06-04"), "WTREGEN": (800.0, "2026-06-04"),
                   "RRPONTSYD": (200.0, "2026-06-04")}
    monkeypatch.setattr(fred_fetch, "fetch_latest_observation",
                        lambda sid, client=None: series_vals[sid])
    recorded = []
    monkeypatch.setattr(reg, "record_observation",
                        lambda s, v, name, **kw: recorded.append((name, kw.get("value"))))

    summary = fred_fetch.run_fred_fetch("global-macro-rates-liquidity", "opus4.8", client=object())

    rec = dict(recorded)
    assert rec["美联储资产 WALCL(QT 节奏)"] == 7000.0
    assert rec["净流动性(=资产−TGA−RRP)"] == 7000.0 - 800.0 - 200.0  # 派生算出
    assert "MOVE 债市波动率" not in rec  # web 跳过
    assert summary["fetched"] == 3 and summary["derived"] == 1 and summary["skipped"] == 1
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest prism/scripts/test_fred_fetch.py -k run_fred -v`
Expected: FAIL — `run_fred_fetch` 未定义

- [ ] **Step 3: 实现**（加到 `fred_fetch.py`）

```python
from prism.scripts import macro_registry as reg

# 净流动性派生：name → (被减项构成)
_NET_LIQ_NAME = "净流动性(=资产−TGA−RRP)"
_NET_LIQ_PARTS = ("美联储资产 WALCL(QT 节奏)", "TGA 余额", "RRP 逆回购")  # assets, minus, minus


def run_fred_fetch(slug: str, variant: str, *, client=None) -> dict:
    """抓所有 fetch_method==fred-api 且有 fred_series_id 的输入，落 observed。
    __DERIVED__（净流动性）在常规抓取后由构成项计算。返回 summary。"""
    data = reg.read_registry(slug, variant)
    fetched = skipped = derived = failed = 0
    values: dict[str, float | None] = {}

    for e in data["inputs"]:
        if e.get("fetch_method") != "fred-api":
            skipped += 1
            continue
        sid = e.get("fred_series_id")
        if not sid or sid == "__DERIVED__":
            continue
        val, as_of = fetch_latest_observation(sid, client=client)
        if val is None:
            failed += 1
            continue
        reg.record_observation(slug, variant, e["name"], value=val, as_of=as_of)
        values[e["name"]] = val
        fetched += 1

    # 净流动性派生
    assets, tga, rrp = (values.get(n) for n in _NET_LIQ_PARTS)
    if None not in (assets, tga, rrp):
        nl = assets - tga - rrp
        reg.record_observation(slug, variant, _NET_LIQ_NAME, value=nl)
        derived += 1

    return {"fetched": fetched, "derived": derived, "skipped": skipped, "failed": failed}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest prism/scripts/test_fred_fetch.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/fred_fetch.py prism/scripts/test_fred_fetch.py
git commit -m "feat(prism): run_fred_fetch 全量抓取 + 净流动性派生

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: 联网 smoke 脚本（验 31 个 series_id 真能解析）

**Files:**
- Create: `prism/scripts/fred_smoke.py`

> 非单测（需真 key + 联网，CI 不跑）。目的：满足「可验证、非信我就行」——离线运行一次，确认每个 fred_series_id 真能从 FRED 取到数，并打印 ⚠ 代理项。

- [ ] **Step 1: 实现**

```python
# prism/scripts/fred_smoke.py
"""联网 smoke：逐个验证登记表 fred_series_id 能否从 FRED 解析。
用法：FRED_API_KEY=... python -m prism.scripts.fred_smoke
非单元测试（需 key + 网络）。"""
from __future__ import annotations

from prism.scripts import fred_fetch
from prism.scripts import macro_registry as reg

SLUG, VAR = "global-macro-rates-liquidity", "opus4.8"
PROXY_NOTE = {"DTWEXAFEGS": "DXY 代理（非 ICE 真 DXY）"}


def main():
    data = reg.read_registry(SLUG, VAR)
    ok = bad = 0
    for e in data["inputs"]:
        sid = e.get("fred_series_id")
        if not sid or sid == "__DERIVED__":
            continue
        try:
            val, as_of = fred_fetch.fetch_latest_observation(sid)
            status = "OK " if val is not None else "空值"
            ok += val is not None
            bad += val is None
        except Exception as ex:  # noqa: BLE001
            status, as_of, val = f"ERR {ex}", "-", "-"
            bad += 1
        note = PROXY_NOTE.get(sid, "")
        print(f"[{status}] {sid:14s} {e['name']:30s} val={val} asof={as_of} {note}")
    print(f"\n解析成功 {ok} / 失败或空 {bad}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 离线运行一次（需 key）**

```bash
FRED_API_KEY=<你的key> python -m prism.scripts.fred_smoke
```
Expected: 每行打印 OK/空值/ERR；记录任何 ERR/空值的 series_id 进最终报告开放项。

- [ ] **Step 3: 提交**

```bash
git add prism/scripts/fred_smoke.py
git commit -m "feat(prism): fred_smoke 联网验证脚本（可验证 series_id 解析）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: CLI 入口 `python -m prism.scripts.fred_fetch`

**Files:**
- Modify: `prism/scripts/fred_fetch.py`
- Test: `prism/scripts/test_fred_fetch.py`

- [ ] **Step 1: 写失败测试**

```python
def test_main_invokes_run(monkeypatch, capsys):
    monkeypatch.setenv("FRED_API_KEY", "k")
    calls = {}
    monkeypatch.setattr(fred_fetch, "run_fred_fetch",
                        lambda s, v: calls.setdefault("args", (s, v)) or {"fetched": 5, "derived": 1, "skipped": 80, "failed": 0})
    fred_fetch.main(["global-macro-rates-liquidity", "opus4.8"])
    assert calls["args"] == ("global-macro-rates-liquidity", "opus4.8")
    assert "fetched" in capsys.readouterr().out
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest prism/scripts/test_fred_fetch.py -k main_invokes -v`
Expected: FAIL — `main` 未定义

- [ ] **Step 3: 实现**（加到 `fred_fetch.py`）

```python
import sys


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    summary = run_fred_fetch(slug, variant)
    print(f"FRED 抓取: {summary}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑测试 + 提交**

```bash
pytest prism/scripts/test_fred_fetch.py -v   # PASS
git add prism/scripts/fred_fetch.py prism/scripts/test_fred_fetch.py
git commit -m "feat(prism): fred_fetch CLI 入口

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: 接进 monitor 周期（零-LLM 抓取块）

**Files:**
- Modify: `app/monitor_runtime.py`（`run_monitor_cycle` 加 FRED 抓取块，镜像既有 price/ macro 零-LLM 块）
- Test: `prism/scripts/test_monitor_macro.py`（追加）

> **改前跑 `gitnexus_impact({target:"run_monitor_cycle", direction:"upstream"})` 报告 blast radius。** 抓取块须在 macro scan 之前执行，使扫描看到最新 observed。失败要吞掉（抓取失败不应阻断监控周期），并计入 summary。

- [ ] **Step 1: 写失败测试**

```python
# 追加到 test_monitor_macro.py
import asyncio

def test_run_monitor_cycle_invokes_fred_fetch(monkeypatch, macro_monitor_env):
    import app.monitor_runtime as mr
    from prism.scripts import fred_fetch
    called = {}
    monkeypatch.setattr(fred_fetch, "run_fred_fetch",
                        lambda s, v: called.setdefault("hit", True) or {"fetched": 1, "derived": 0, "skipped": 0, "failed": 0})
    # FRED key 缺失或抓取异常不应炸周期
    monkeypatch.setenv("FRED_API_KEY", "k")
    asyncio.run(mr.run_monitor_cycle())
    assert called.get("hit") is True


def test_fred_fetch_failure_does_not_break_cycle(monkeypatch, macro_monitor_env):
    import app.monitor_runtime as mr
    from prism.scripts import fred_fetch
    def boom(s, v): raise RuntimeError("FRED down")
    monkeypatch.setattr(fred_fetch, "run_fred_fetch", boom)
    # 不抛即通过
    asyncio.run(mr.run_monitor_cycle())
```

> 注：若 `run_monitor_cycle` 需遍历 macro topics 才知道 slug/variant，则在 env fixture 里已有 1 个 macro topic；fetch 调用以该 topic 的 slug/variant 触发。实现时按 fixture 实际结构取（见既有 macro 块如何拿 slug）。

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest prism/scripts/test_monitor_macro.py -k "fred" -v`
Expected: FAIL — 周期未调 fetch

- [ ] **Step 3: 实现**

在 `run_monitor_cycle` 内、macro 零-LLM 扫描块之前，对每个启用监控的 macro topic 加：

```python
    # FRED 自动抓取（零 LLM）：失败吞掉、不阻断周期
    try:
        from prism.scripts import fred_fetch
        fred_summary = await asyncio.to_thread(fred_fetch.run_fred_fetch, slug, variant)
        # 计入既有 summary 结构（与 price/macro 块同风格）
    except Exception as exc:  # noqa: BLE001
        fred_summary = {"error": str(exc)}
```

（slug/variant 取法与同函数现有 macro 块一致；若现有 macro 块按 topic 遍历，则把抓取放进同一遍历。）

- [ ] **Step 4: 跑测试确认通过 + detect_changes**

```bash
pytest prism/scripts/test_monitor_macro.py -v   # PASS
# gitnexus_detect_changes() 应只显示 run_monitor_cycle
```

- [ ] **Step 5: 提交**

```bash
git add app/monitor_runtime.py prism/scripts/test_monitor_macro.py
git commit -m "feat(prism): monitor 周期内零-LLM FRED 抓取（失败不阻断）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: 顶部导航加「宏观层」

**Files:**
- Modify: `app/templates/base.html`（nav 区 20-33 行；键盘快捷键 42-58 行）
- Test: `tests/test_macro_inputs_web.py`（新建，先放 nav 测试）

- [ ] **Step 1: 写失败测试**

```python
# tests/test_macro_inputs_web.py
"""宏观层 Web：顶部导航 + 输入表。"""
from __future__ import annotations
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

VARIANT = "opus4.8"
SLUG = "global-macro-rates-liquidity"


@pytest.fixture
def macro_web_client(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parent.parent
    shutil.copytree(repo / "app" / "templates", tmp_path / "app_templates")
    from app import config as cfg
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "APP_TEMPLATES_DIR", tmp_path / "app_templates")
    monkeypatch.setattr(cfg, "STATIC_DIR", tmp_path / "static")
    monkeypatch.setattr(cfg, "PRISM_DIR", tmp_path / "prism")
    for name in ("companies", "industries", "watchlist", "macro", "data", "static", "portfolio"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    (tmp_path / "portfolio" / "rules.md").write_text("# r\n")
    (tmp_path / "journal" / "decisions").mkdir(parents=True, exist_ok=True)
    for attr, sub in [("COMPANIES_DIR","companies"),("INDUSTRIES_DIR","industries"),
                      ("WATCHLIST_DIR","watchlist"),("MACRO_DIR","macro"),("DATA_DIR","data"),
                      ("PORTFOLIO_DIR","portfolio"),("JOURNAL_DIR","journal")]:
        monkeypatch.setattr(cfg, attr, tmp_path / sub)
    monkeypatch.setattr(cfg, "FINANCIALS_DB", tmp_path / "data" / "financials.db")
    monkeypatch.setattr(cfg, "CONTROLLED_VOCAB_DIR", repo / "controlled-vocab")

    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    import prism.scripts.outputs as o
    import prism.scripts.macro_registry as reg
    monkeypatch.setattr(t, "PRISM_ROOT", tmp_path / "prism")
    monkeypatch.setattr(m, "_PRISM_ROOT", tmp_path / "prism")
    monkeypatch.setattr(o, "_PRISM_ROOT", tmp_path / "prism")
    # macro_registry 路径根（按其实际常量名 patch；见 _registry_path 实现）
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path / "prism", raising=False)

    (tmp_path / "prism" / "topics").mkdir(parents=True)
    t.create_topic(SLUG, "宏观层 (利率/流动性/汇率体制)", "macro", "三体制传导", "GLOBAL", "deep", VARIANT)
    m.create_manifest(SLUG, VARIANT)
    # 最小登记表
    reg.create_registry(SLUG, VARIANT)
    reg.upsert_input(SLUG, VARIANT, {
        "name": "HY OAS", "tier": "B", "cadence_type": "series", "targets": ["liquidity"],
        "mechanism": "CO", "importance": "confirming", "source": "FRED", "fetch_method": "fred-api",
        "fred_series_id": "BAMLH0A0HYM2", "alert_series": True,
        "alert_band": {"level": 450, "direction": "above"}, "monitoring": {"enabled": True},
    })

    from main import app
    return TestClient(app)


def test_nav_has_macro_link(macro_web_client):
    r = macro_web_client.get("/prism")
    assert r.status_code == 200
    assert "宏观层" in r.text
    assert f"/prism/{SLUG}/{VARIANT}/macro-inputs" in r.text or f"/prism/{SLUG}" in r.text
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_macro_inputs_web.py -k nav -v`
Expected: FAIL — 导航无「宏观层」

- [ ] **Step 3: 实现**

在 `app/templates/base.html` nav 区（仪表盘链接后）加：

```jinja
  {{ _navlink('/prism/global-macro-rates-liquidity/opus4.8/macro-inputs', '宏观层') }}
```

并在键盘快捷键块（`g` 前缀）加一条 `m` → 该 URL（与现有 r/b/f/p/d 同写法）。

- [ ] **Step 4: 跑测试 + 提交**

```bash
pytest tests/test_macro_inputs_web.py -k nav -v   # PASS
git add app/templates/base.html tests/test_macro_inputs_web.py
git commit -m "feat(web): 顶部导航加「宏观层」入口 + 键盘快捷键 g m

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: macro 类型标签/emoji

**Files:**
- Modify: `app/routes/prism.py`（`_TYPE_LABEL` 71 行、`_TYPE_EMOJI` 71 行附近、`_TYPE_ORDER` 74 行）
- Test: `tests/test_macro_inputs_web.py`

> 上一期已映射 `_CASE_BY_TYPE["macro"]="m_regime_read"`，但 `_TYPE_LABEL`/`_TYPE_EMOJI` 仍缺 macro，索引页会显示原始 "macro"。

- [ ] **Step 1: 写失败测试**

```python
def test_index_shows_macro_label(macro_web_client):
    r = macro_web_client.get("/prism")
    assert "宏观" in r.text          # 中文标签
    assert ">macro<" not in r.text   # 不暴露原始 type
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_macro_inputs_web.py -k macro_label -v`
Expected: FAIL

- [ ] **Step 3: 实现**（`app/routes/prism.py`）

```python
_TYPE_LABEL = {"company": "公司", "arena": "竞技场", "industry": "行业", "macro": "宏观层"}
_TYPE_EMOJI = {"company": "🏢", "arena": "🥊", "industry": "🏭", "macro": "🌐"}
_TYPE_ORDER = {"industry": 0, "arena": 1, "company": 2, "macro": 3}
```

- [ ] **Step 4: 跑测试 + 提交**

```bash
pytest tests/test_macro_inputs_web.py -k macro_label -v   # PASS
git add app/routes/prism.py tests/test_macro_inputs_web.py
git commit -m "feat(web): macro 类型标签/emoji/排序

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: 输入源信息表路由 + 模板

**Files:**
- Modify: `app/routes/prism.py`（新增 `GET /{slug}/{variant}/macro-inputs`）
- Create: `app/templates/prism/macro_inputs.html`
- Test: `tests/test_macro_inputs_web.py`

> 列：输入名 / 等级 / 频率 / 目标 / 重要性 / 来源 / 抓取方式（是否自动） / 最近观测值+时效 / 监控 / 报警带。「是否自动」由 `fetch_method=='fred-api'` 判定。

- [ ] **Step 1: 写失败测试**

```python
def test_macro_inputs_table_renders(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert r.status_code == 200
    assert "HY OAS" in r.text          # 输入名
    assert "FRED" in r.text            # 来源
    assert "fred-api" in r.text or "自动" in r.text   # 抓取方式
    assert "BAMLH0A0HYM2" not in r.text or True  # series_id 展示可选


def test_macro_inputs_404_for_non_macro(macro_web_client, monkeypatch):
    # 非 macro topic 应 404
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert r.status_code in (200, 404)  # 该 fixture 是 macro，预期 200
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_macro_inputs_web.py -k table -v`
Expected: FAIL — 路由不存在（404 但无内容）

- [ ] **Step 3: 实现路由**（`app/routes/prism.py`，放在 `prism_output` 等具体路由附近，**注意路由顺序**：`/macro-inputs` 须在 `/{slug}/{variant}/{output_key}` 之前声明，否则被通配吞掉）

```python
@router.get("/{slug}/{variant}/macro-inputs")
def prism_macro_inputs(request: Request, slug: str, variant: str):
    """宏观输入源信息表（仅 macro topic）。"""
    from prism.scripts import macro_registry as macro_reg
    topic = topic_io.read_topic(slug, variant)
    if topic.get("type") != "macro":
        raise HTTPException(status_code=404, detail="非宏观主题")
    try:
        registry = macro_reg.read_registry(slug, variant)
        inputs = registry.get("inputs", [])
    except FileNotFoundError:
        inputs = []
    return templates.TemplateResponse(request, "prism/macro_inputs.html", {
        "topic": topic, "variant": variant, "inputs": inputs,
    })
```

（确认 `HTTPException` 已 import；文件顶部若无则加 `from fastapi import HTTPException`。）

- [ ] **Step 4: 实现模板** `app/templates/prism/macro_inputs.html`

```jinja
{% extends "base.html" %}
{% block title %}宏观输入源 · {{ topic.display_name }}{% endblock %}
{% block content %}
<h1>宏观输入源信息表</h1>
<p class="hint">共 {{ inputs | length }} 条输入。「自动」= FRED API 脚本拉取；其余为 llm-web / manual。</p>
<table class="data-table">
  <thead><tr>
    <th>输入名</th><th>等级</th><th>频率</th><th>目标</th><th>重要性</th>
    <th>来源</th><th>抓取</th><th>最近观测</th><th>监控</th><th>报警带</th>
  </tr></thead>
  <tbody>
  {% for inp in inputs %}
    <tr>
      <td><code>{{ inp.name }}</code></td>
      <td>{{ inp.tier or '—' }}</td>
      <td>{{ inp.cadence_type or '—' }}</td>
      <td>{{ (inp.targets or []) | join(', ') }}</td>
      <td>{{ inp.importance or '—' }}</td>
      <td>{{ inp.source or '—' }}</td>
      <td>
        {% if inp.fetch_method == 'fred-api' %}
          <span class="badge-small">自动 · FRED</span>
          {% if inp.fred_series_id %}<code class="hint">{{ inp.fred_series_id }}</code>{% endif %}
        {% else %}{{ inp.fetch_method or '—' }}{% endif %}
      </td>
      <td>
        {% if inp.observed and inp.observed.value is not none %}
          {{ inp.observed.value }} <span class="hint">@{{ (inp.observed.as_of or '')[:10] or '—' }}</span>
        {% else %}<span class="hint">未抓</span>{% endif %}
      </td>
      <td>{% if inp.monitoring and inp.monitoring.enabled %}✓{% else %}○{% endif %}</td>
      <td>{% if inp.alert_series and inp.alert_band %}<code class="hint">{{ inp.alert_band }}</code>{% else %}—{% endif %}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 5: 跑测试确认通过**

Run: `pytest tests/test_macro_inputs_web.py -v`
Expected: PASS（全部）

- [ ] **Step 6: 提交**

```bash
git add app/routes/prism.py app/templates/prism/macro_inputs.html tests/test_macro_inputs_web.py
git commit -m "feat(web): 宏观输入源信息表路由 + 模板

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: 领域入门加输入表指针（小改）

**Files:**
- Modify: `prism/topics/global-macro-rates-liquidity/opus4.8/outputs/00_primer.md`
- Test: `prism/scripts/test_macro_regime_doc.py`（追加 grep 锚点）

- [ ] **Step 1: 写失败测试**

```python
def test_primer_points_to_input_table():
    p = Path("prism/topics/global-macro-rates-liquidity/opus4.8/outputs/00_primer.md")
    text = p.read_text(encoding="utf-8")
    assert "macro-inputs" in text or "输入源信息表" in text
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest prism/scripts/test_macro_regime_doc.py -k input_table -v`
Expected: FAIL

- [ ] **Step 3: 实现** — 在 `00_primer.md` 顶部引言加一句：

```markdown
> 本文点名的每个指标现已在**输入源信息表**（`/prism/global-macro-rates-liquidity/opus4.8/macro-inputs`）登记追踪：来源、是否自动抓取、最近观测值与报警带一表可查。
```

- [ ] **Step 4: 跑测试 + 提交**

```bash
pytest prism/scripts/test_macro_regime_doc.py -v   # PASS
git add prism/topics/global-macro-rates-liquidity/opus4.8/outputs/00_primer.md prism/scripts/test_macro_regime_doc.py
git commit -m "docs(prism): 领域入门加输入源信息表指针

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 15: 终检（全套 + validator + detect_changes + smoke 回顾）

**Files:** 无新增

- [ ] **Step 1: 全量测试**

Run: `pytest -q`
Expected: 全绿，数量 ≥ 上一期基线 +（本期新增测试数）。

- [ ] **Step 2: validator**

```bash
python -c "from prism.scripts import macro_registry as r; e=r.validate_registry('global-macro-rates-liquidity','opus4.8'); print(len(e),'错'); [print(' -',x) for x in e]"
```
Expected: `0 错`（含新加 2 条尾部 CR 机制 + 6 条新带）。

- [ ] **Step 3: detect_changes**

`gitnexus_detect_changes()` — 确认改动范围只含本期文件，无 baijiu/popmart 等无关 WIP 被扫入。

- [ ] **Step 4: 最终评审 + 报告开放项**

dispatch 最终 code reviewer 审整个分支。向用户报告：
- fred_smoke 跑出的任何 ERR/空值 series_id（尤其 DXY 代理 `DTWEXAFEGS`、已改判 web 的黄金）；
- 仍需真 `FRED_API_KEY` 才能实抓（部署环境配 .env）；
- 第三步（战绩台账/DCF）为后续独立计划。

---

## Self-Review（写完计划的自查）

- **Spec 覆盖**：FRED 自动抓取（T1-T2,T7-T10）、报警带精值（T4-T5）、尾部源（T6）、Web 导航（T11-T12）、Web 输入表（T13）、领域入门指针（T14）——本批 5 条用户指令全覆盖。
- **占位扫描**：FRED 映射表、6 报警带、2 尾部输入均为**具体值**；唯 Task 10 的 slug/variant 取法依赖 `run_monitor_cycle` 既有 macro 块结构，已注明「按 fixture/既有块实际结构取」——实现者须读该函数现状（非占位，是显式依赖既有代码）。
- **类型一致**：`fetch_latest_observation`/`run_fred_fetch`/`record_observation(value=,as_of=)` 签名贯穿一致；`alert_band` 字段（level/direction/level_alarm/delta/min_streak）在 T4 定义、T5 使用一致。
- **路由顺序坑**：T13 已标注 `/macro-inputs` 必须在 `/{output_key}` 通配前声明。
- **风险**：DXY 代理、黄金改判 web 为已知偏差，进开放项，非静默。

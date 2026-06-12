# FOMC 点阵图(SEP) 数值通道 + 美联储主席讲话 取文通道 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 `FOMC 点阵图(SEP)` 加零-LLM 数值脚本通道（`fetch_method: fomc_sep`），给 `美联储官员讲话(主席)` 加零-LLM 取文脚本通道（`text_fetch: fed_speech`，立场判读仍 LLM）。

**Architecture:** A 部分仿 `fedwatch_fetch.py`（数值通道，纯函数与 IO 分离），从 Fed `fomccalendars.htm` 发现最新 `fomcprojtabl{YYYYMMDD}.htm` 投影表、解析「Federal funds rate」行首数 = 近年中位。B 部分仿 `fomc_fetch.py`/`pbc_mpr_fetch.py`（取文通道），从 Fed 静态 JSON feed `ne-speeches.json` 过滤最新主席讲话、下原文存 `local_cache_path`。两者各仿一个已落地同类 fetcher，自动继承定时巡检、去重门、Web 批量刷新。

**Tech Stack:** Python 3.14, httpx, pyyaml, pytest；既有 `prism.scripts.macro_registry` CRUD。

**Spec:** `docs/superpowers/specs/2026-06-12-fomc-sep-and-chair-speech-fetchers-design.md`

---

## 文件结构

新建：
- `prism/scripts/fomc_sep_fetch.py` — SEP 数值 fetcher（纯函数 + IO + run + main）
- `prism/scripts/test_fomc_sep_fetch.py` — SEP 纯函数单测
- `prism/scripts/fed_speech_fetch.py` — 主席讲话取文 fetcher
- `prism/scripts/test_fed_speech_fetch.py` — 取文纯函数单测

修改：
- `prism/scripts/macro_registry.py` — `VALID_FETCH_METHOD` / `VALID_TEXT_FETCH` 各追加一项
- `prism/scripts/textfetch.py` — 注册 `fed_speech` fetcher
- `app/monitor_runtime.py` — `run_monitor_cycle` 加 `fomc_sep` 派发块
- `app/routes/prism.py` — 单条手动路由 + `fetch-script-all` 批量路由各加 `fomc_sep`
- `prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml` — 两条目字段

---

## Task 0: gitnexus 影响预检（CLAUDE.md 强制）

**Files:** 无改动（只读分析）

- [ ] **Step 1: 对将被修改的共享符号跑 upstream 影响分析**

Run（逐个）:
```
gitnexus_impact({target: "run_textfetch", direction: "upstream"})
gitnexus_impact({target: "run_monitor_cycle", direction: "upstream"})
gitnexus_impact({target: "validate_registry", direction: "upstream"})
```
Expected: 全部为增量改动（枚举元组追加 / 新派发块 / 新 `_FETCHERS` 条目），无签名变更。若任一返回 HIGH/CRITICAL，停下并向用户报告后再继续。新建文件无 upstream，无需分析。

---

## Task 1: macro_registry 放行 `fomc_sep` 数值通道枚举

**Files:**
- Modify: `prism/scripts/macro_registry.py:61`
- Test: `prism/scripts/test_macro_registry_fields.py`（追加用例）

- [ ] **Step 1: 写失败测试**

在 `prism/scripts/test_macro_registry_fields.py` 末尾追加（沿用该文件的 `tmp_reg` fixture 与 `_base(extra)` helper，与现有 cftc 用例同款）：

```python
def test_fomc_sep_method_validates_without_config_block(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"availability": "scripted", "fetch_method": "fomc_sep"}))
    assert reg.validate_registry(slug, variant) == []
```

> 注：`fomc_sep` 无参，validator **不**强制 config 块（类比 fred-api/recipe 无专属块校验）。本测试断言「scripted + fomc_sep」校验全清。

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest prism/scripts/test_macro_registry_fields.py::test_fomc_sep_method_validates_without_config_block -v`
Expected: FAIL — `fetch_method 非法: 'fomc_sep'`

- [ ] **Step 3: 最小实现**

`prism/scripts/macro_registry.py:61`，把 `"fedwatch"` 后追加 `"fomc_sep"`：

```python
VALID_FETCH_METHOD = ("fred-api", "recipe", "akshare", "yfinance", "macromicro", "barchart", "ecb", "safe", "cftc", "mofcom", "fedwatch", "fomc_sep")   # 脚本「数值」通道，仅 scripted 项可设
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest prism/scripts/test_macro_registry_fields.py::test_fomc_sep_method_validates_without_config_block -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/macro_registry.py prism/scripts/test_macro_registry_fields.py
git commit -m "feat(prism/macro): fomc_sep 数值通道入 VALID_FETCH_METHOD 枚举"
```

---

## Task 2: SEP 纯函数（发现最新表 + 解析中位）

**Files:**
- Create: `prism/scripts/fomc_sep_fetch.py`
- Test: `prism/scripts/test_fomc_sep_fetch.py`

- [ ] **Step 1: 写失败测试**

新建 `prism/scripts/test_fomc_sep_fetch.py`：

```python
"""fomc_sep 数值 fetcher 单测：纯函数解析（发现最新投影表 + 取中位联邦基金利率）。零网络。"""
from prism.scripts import fomc_sep_fetch as sep


# 日历页样本：多个 projtabl 日期、故意乱序，断言取最大日期
_CALENDAR = """
<a href="/monetarypolicy/fomcprojtabl20251210.htm">December 2025 Projections</a>
<a href="/monetarypolicy/fomcprojtabl20260318.htm">March 2026 Projections</a>
<a href="/monetarypolicy/fomcprojtabl20250618.htm">June 2025 Projections</a>
"""

# 投影表样本：Table 1「Federal funds rate」行（中位在前，后随中心趋势/区间），
# 另含一条以 Median 开头的备忘行（应被 startswith 过滤掉）。
_PROJTABL = """
<table>
<tr><th>Variable</th><th>2026</th><th>2027</th><th>2028</th><th>Longer run</th></tr>
<tr><td>Federal funds rate</td><td>3.4</td><td>3.1</td><td>3.1</td><td>3.1</td>
    <td>3.1&#8211;3.6</td></tr>
<tr><td>Median</td><td>-</td><td>-</td><td>3.4</td><td>3.1</td></tr>
</table>
"""


def test_find_latest_projtabl_picks_newest():
    url, as_of = sep.find_latest_projtabl(_CALENDAR)
    assert url == "https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260318.htm"
    assert as_of == "2026-03-18"


def test_find_latest_projtabl_no_match():
    assert sep.find_latest_projtabl("<a href='/foo.htm'>x</a>") == (None, None)


def test_parse_median_funds_rate_takes_first_number_of_ffr_row():
    assert sep.parse_median_funds_rate(_PROJTABL) == 3.4


def test_parse_median_funds_rate_none_when_no_ffr_row():
    assert sep.parse_median_funds_rate("<table><tr><td>GDP</td><td>2.0</td></tr></table>") is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest prism/scripts/test_fomc_sep_fetch.py -v`
Expected: FAIL — `ModuleNotFoundError: fomc_sep_fetch`

- [ ] **Step 3: 最小实现（纯函数部分）**

新建 `prism/scripts/fomc_sep_fetch.py`：

```python
"""FOMC 点阵图(SEP) 中位联邦基金利率取数通道（零 LLM）。读登记表里 fetch_method=='fomc_sep' 且
availability=='scripted' 的输入，从 Fed FOMC 日历页发现最新季度投影表（fomcprojtabl{YYYYMMDD}.htm），
解析 Table 1「Federal funds rate」行的近年中位 → record_observation。

与 fedwatch_fetch 平行（脚本「数值」通道）且互补：FedWatch 给市场**隐含**政策路径，本通道给
FOMC **自己昭示**的中位路径——二者之差即「市场 vs Fed」预期差。

口径：SEP 每季度（3/6/9/12 月会议）一次，故 cadence_type=event。Table 1「Federal funds rate」行
剥标签后文本以 "Federal funds rate" 开头，其后第一个数字 = 最近完整日历年年底中位（现 = 3.4）。
"""
from __future__ import annotations

import re
import sys

import httpx

from prism.scripts import macro_registry as reg

_FED_BASE = "https://www.federalreserve.gov"
_CALENDAR_URL = _FED_BASE + "/monetarypolicy/fomccalendars.htm"
_INPUT_NAME = "FOMC 点阵图(SEP)"

_PROJTABL_RE = re.compile(r"fomcprojtabl(\d{8})\.htm")
_TR_RE = re.compile(r"<tr[^>]*>.*?</tr>", re.IGNORECASE | re.DOTALL)
_ANY_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_FFR_LABEL = "Federal funds rate"


def find_latest_projtabl(calendar_html: str) -> tuple[str, str] | tuple[None, None]:
    """从日历页提取最新（日期最大）投影表 URL。返回 (绝对url, as_of='YYYY-MM-DD')；无命中 → (None, None)。"""
    dates = _PROJTABL_RE.findall(calendar_html)
    if not dates:
        return None, None
    d = max(dates)
    url = f"{_FED_BASE}/monetarypolicy/fomcprojtabl{d}.htm"
    as_of = f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return url, as_of


def parse_median_funds_rate(projtabl_html: str) -> float | None:
    """从投影表取「Federal funds rate」行的第一个数字（近年中位）。无该行/无数字 → None（诚实）。"""
    for row in _TR_RE.findall(projtabl_html):
        txt = _WS.sub(" ", _ANY_TAG.sub(" ", row)).strip()
        if txt.startswith(_FFR_LABEL):
            m = _NUM_RE.search(txt[len(_FFR_LABEL):])
            if m:
                return float(m.group(0))
    return None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest prism/scripts/test_fomc_sep_fetch.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/fomc_sep_fetch.py prism/scripts/test_fomc_sep_fetch.py
git commit -m "feat(prism/macro): fomc_sep 纯函数（发现最新投影表+解析中位 FFR）"
```

---

## Task 3: SEP IO 入口 + run + main

**Files:**
- Modify: `prism/scripts/fomc_sep_fetch.py`
- Test: `prism/scripts/test_fomc_sep_fetch.py`（追加注入 fake client 的用例）

- [ ] **Step 1: 写失败测试**

在 `prism/scripts/test_fomc_sep_fetch.py` 末尾追加：

```python
import pytest
from prism.scripts import macro_registry as reg


class _FakeResp:
    def __init__(self, text):
        self.text = text
    def raise_for_status(self):
        pass


class _FakeClient:
    """按 URL 返回日历页或投影表样本。"""
    def __init__(self, calendar, projtabl):
        self._cal, self._proj = calendar, projtabl
    def get(self, url, **kw):
        return _FakeResp(self._cal if "fomccalendars" in url else self._proj)
    def close(self):
        pass


@pytest.fixture
def sep_topic(tmp_path, monkeypatch):
    # 把 _PRISM_ROOT 指向临时目录，建一个登记表 + 一条 fomc_sep 输入
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(sep, "_PRISM_ROOT", tmp_path, raising=False)
    slug, variant = "t-macro", "opus4.8"
    reg.create_registry(slug, variant)
    reg.upsert_input(slug, variant, {
        "name": sep._INPUT_NAME, "tier": "A", "cadence_type": "event",
        "targets": ["rates"], "mechanism": "CD", "importance": "load_bearing",
        "causal_sentence": "x→y→z。", "availability": "scripted", "fetch_method": "fomc_sep",
    })
    return slug, variant


def test_fetch_fomc_sep_records_median(sep_topic):
    slug, variant = sep_topic
    client = _FakeClient(_CALENDAR, _PROJTABL)
    res = sep.fetch_fomc_sep(slug, variant, client=client)
    assert res["ok"] and res["value"] == 3.4 and res["as_of"] == "2026-03-18"
    obs = next(e for e in reg.read_registry(slug, variant)["inputs"]
               if e["name"] == sep._INPUT_NAME)["observed"]
    assert obs["value"] == 3.4 and obs["as_of"] == "2026-03-18"


def test_run_fomc_sep_fetch_counts(sep_topic):
    slug, variant = sep_topic
    summary = sep.run_fomc_sep_fetch(slug, variant, client=_FakeClient(_CALENDAR, _PROJTABL))
    assert summary["fetched"] == 1 and summary["failed"] == 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest prism/scripts/test_fomc_sep_fetch.py::test_fetch_fomc_sep_records_median -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'fetch_fomc_sep'`

- [ ] **Step 3: 最小实现（追加 IO 部分）**

在 `prism/scripts/fomc_sep_fetch.py` 末尾追加：

```python
def fetch_fomc_sep(slug: str, variant: str, *, client: httpx.Client | None = None,
                   input_name: str | None = None) -> dict:
    """发现最新投影表→解析近年中位→record_observation。返回 {value, as_of, url, ok}；
    任一步取不到 → {"error": ...}（真失败，调度器据此记 fetch_error）。"""
    target = input_name or _INPUT_NAME
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        try:
            cal = client.get(_CALENDAR_URL, timeout=30, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0"})
            cal.raise_for_status()
        except httpx.HTTPError as exc:
            return {"error": f"FOMC 日历页抓取失败：{exc}"}
        url, as_of = find_latest_projtabl(cal.text)
        if url is None:
            return {"error": "日历页未找到投影表链接（站点结构可能变更）"}
        try:
            tbl = client.get(url, timeout=30, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0"})
            tbl.raise_for_status()
        except httpx.HTTPError as exc:
            return {"error": f"投影表抓取失败（{url}）：{exc}"}
        median = parse_median_funds_rate(tbl.text)
        if median is None:
            return {"error": f"投影表未解析到 Federal funds rate 中位行（{url}）"}
        reg.record_observation(slug, variant, target, value=median, as_of=as_of)
        return {"value": median, "as_of": as_of, "url": url, "ok": True}
    finally:
        if owns:
            client.close()


def run_fomc_sep_fetch(slug: str, variant: str, *, only: set[str] | None = None,
                       client: httpx.Client | None = None) -> dict:
    """抓所有 fetch_method=='fomc_sep' 且 availability=='scripted' 的输入（一般仅 1 条）。
    失败记 record_fetch_error 计数、不连累其余。返回 {fetched, skipped_todo, failed}。"""
    data = reg.read_registry(slug, variant)
    fetched = skipped_todo = failed = 0
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        for e in data["inputs"]:
            if e.get("fetch_method") != "fomc_sep":
                continue
            if only is not None and e["name"] not in only:
                continue
            if e.get("availability") != "scripted":
                skipped_todo += 1
                continue
            res = fetch_fomc_sep(slug, variant, client=client, input_name=e["name"])
            if res.get("error"):
                reg.record_fetch_error(slug, variant, e["name"], msg=res["error"])
                failed += 1
            else:
                fetched += 1
        return {"fetched": fetched, "skipped_todo": skipped_todo, "failed": failed}
    finally:
        if owns:
            client.close()


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:  # 活体冒烟：拉真表打印中位
        url, as_of = find_latest_projtabl(
            httpx.get(_CALENDAR_URL, timeout=30, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"}).text)
        if url is None:
            print("未找到投影表链接")
            return
        tbl = httpx.get(url, timeout=30, follow_redirects=True,
                        headers={"User-Agent": "Mozilla/5.0"})
        print(f"最新投影表 {url}（as_of {as_of}）")
        print(f"  近年中位联邦基金利率 = {parse_median_funds_rate(tbl.text)}")
        return
    slug = argv[0]
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    print(f"fomc_sep 抓取: {run_fomc_sep_fetch(slug, variant)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest prism/scripts/test_fomc_sep_fetch.py -v`
Expected: PASS（6 passed）

- [ ] **Step 5: 活体冒烟（真网络，确认线上结构未变）**

Run: `python3 -m prism.scripts.fomc_sep_fetch`
Expected: 打印最新投影表 URL + `近年中位联邦基金利率 = 3.4`（或当季最新值）

- [ ] **Step 6: 提交**

```bash
git add prism/scripts/fomc_sep_fetch.py prism/scripts/test_fomc_sep_fetch.py
git commit -m "feat(prism/macro): fomc_sep IO 入口 fetch/run + CLI 冒烟"
```

---

## Task 4: fomc_sep 接入定时循环

**Files:**
- Modify: `app/monitor_runtime.py:185`（cftc 块之后、mofcom 块之前插入）

- [ ] **Step 1: 加派发块**

在 `app/monitor_runtime.py` 的 cftc 块（结束于约 184 行 `_log(f"cftc fetch failed: {e}")`）之后、mofcom 块之前插入：

```python
        # macro FOMC SEP 自动抓取（零 LLM）：点阵图近年中位联邦基金利率（Fed 季度投影表），
        # fetch_method=='fomc_sep' 的 scripted 项。与 fred/recipe 同为脚本通道，在 macro scan 之前刷新。失败吞掉、不阻断周期。
        try:
            from prism.scripts import fomc_sep_fetch
            from prism.scripts import topic as topic_io
            for t in topic_io.list_topics():
                if t.get("type") != "macro":
                    continue
                sep_summary = await asyncio.to_thread(
                    fomc_sep_fetch.run_fomc_sep_fetch, t["slug"], t["variant"])
                _log(f"fomc_sep fetch [{t['slug']}/{t['variant']}]: {sep_summary}")
        except Exception as e:
            _log(f"fomc_sep fetch failed: {e}")
```

- [ ] **Step 2: 导入冒烟（语法/导入无误）**

Run: `python3 -c "import app.monitor_runtime"`
Expected: 无输出、退出码 0

- [ ] **Step 3: 提交**

```bash
git add app/monitor_runtime.py
git commit -m "feat(prism/macro): fomc_sep 接入定时巡检循环"
```

---

## Task 5: fomc_sep 接入手动/批量路由

**Files:**
- Modify: `app/routes/prism.py:967`（单条路由）、`app/routes/prism.py:988-1061`（批量路由）

- [ ] **Step 1: 单条手动路由加分支**

在 `app/routes/prism.py` 的 `elif method == "fedwatch":` 块（约 967–969 行）之后、`else:` 之前插入：

```python
    elif method == "fomc_sep":
        from prism.scripts import fomc_sep_fetch
        summary = fomc_sep_fetch.run_fomc_sep_fetch(slug, variant, only={name})
```

- [ ] **Step 2: 批量路由 import 追加**

`app/routes/prism.py` 约 988–990 行的 import 元组末尾加 `fomc_sep_fetch`：

```python
    from prism.scripts import (fred_fetch, recipe_fetch, textfetch, akshare_fetch,
                               yfinance_fetch, macromicro_fetch, barchart_fetch, ecb_fetch,
                               cftc_fetch, fedwatch_fetch, fomc_sep_fetch)
```

- [ ] **Step 3: 批量路由加 run 块**

在 fedwatch run 块（约 1030–1034 行，结束于 `fedwatch_sum = {...}`）之后、`# recipe：` 注释之前插入：

```python
    # fomc_sep（点阵图近年中位联邦基金利率：Fed 自己昭示的政策路径）：脚本数值通道；失败吞掉不毁整批
    try:
        fomc_sep_sum = fomc_sep_fetch.run_fomc_sep_fetch(slug, variant)
    except Exception as _exc:
        fomc_sep_sum = {"_error": str(_exc), "fetched": 0}
```

- [ ] **Step 4: 批量路由计数 + JSON summary 并入**

在 `fedwatch_n = fedwatch_sum.get("fetched", 0) or 0`（约 1050 行）之后加：

```python
    fomc_sep_n = fomc_sep_sum.get("fetched", 0) or 0
```

并把 JSON 返回体（约 1053–1061 行）改为含 `fomc_sep`：在 `"fedwatch": fedwatch_n,` 之后加 `"fomc_sep": fomc_sep_n,`；把 `fetched` 合计加上 `+ fomc_sep_n`；在 `"fedwatch_summary": fedwatch_sum,` 之后加 `"fomc_sep_summary": fomc_sep_sum,`。改后片段：

```python
    if "application/json" in (request.headers.get("accept") or ""):
        return JSONResponse({"fred": fred_n, "recipe": recipe_n, "akshare": akshare_n,
                             "yfinance": yfin_n, "macromicro": mm_n, "barchart": bc_n,
                             "ecb": ecb_n, "cftc": cftc_n, "fedwatch": fedwatch_n,
                             "fomc_sep": fomc_sep_n, "text": text_n,
                             "fetched": fred_n + recipe_n + akshare_n + yfin_n + mm_n + bc_n + ecb_n + cftc_n + fedwatch_n + fomc_sep_n + text_n,
                             "fred_summary": fred_sum, "recipe_summary": recipe_sum,
                             "akshare_summary": akshare_sum, "yfinance_summary": yfin_sum,
                             "macromicro_summary": mm_sum, "barchart_summary": bc_sum,
                             "ecb_summary": ecb_sum, "cftc_summary": cftc_sum,
                             "fedwatch_summary": fedwatch_sum, "fomc_sep_summary": fomc_sep_sum,
                             "text_summary": text_sum})
```

- [ ] **Step 5: 导入冒烟**

Run: `python3 -c "import app.routes.prism"`
Expected: 无输出、退出码 0

- [ ] **Step 6: 提交**

```bash
git add app/routes/prism.py
git commit -m "feat(prism/macro): fomc_sep run 派发（单条手动 + 批量刷新路由）"
```

---

## Task 6: 登记表 `FOMC 点阵图(SEP)` 改 scripted

**Files:**
- Modify: `prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml`（`FOMC 点阵图(SEP)` 条目，约 37–65 行）

- [ ] **Step 1: 改字段（脚本驱动，零手改 YAML 易错）**

Run:
```bash
python3 -c "
from prism.scripts import macro_registry as reg
slug, variant = 'global-macro-rates-liquidity', 'opus4.8'
reg.upsert_input(slug, variant, {'name': 'FOMC 点阵图(SEP)', 'availability': 'scripted', 'fetch_method': 'fomc_sep'})
print('updated')
"
```
Expected: `updated`（`upsert_input` 按 name 合并，只改这两字段，其余保留）

- [ ] **Step 2: 校验登记表机制纪律全清**

Run:
```bash
python3 -c "
from prism.scripts import macro_registry as reg
errs = reg.validate_registry('global-macro-rates-liquidity', 'opus4.8')
print('errors:', errs)
assert not errs, errs
"
```
Expected: `errors: []`

- [ ] **Step 3: 真抓一次确认落值**

Run: `python3 -m prism.scripts.fomc_sep_fetch global-macro-rates-liquidity opus4.8`
Expected: `fomc_sep 抓取: {'fetched': 1, 'skipped_todo': 0, 'failed': 0}`

- [ ] **Step 4: 提交**

```bash
git add prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml
git commit -m "content(prism/macro): 点阵图(SEP) 转 scripted（fomc_sep 通道首落观测）"
```

---

## Task 7: macro_registry 放行 `fed_speech` 取文通道枚举

**Files:**
- Modify: `prism/scripts/macro_registry.py:63`
- Test: `prism/scripts/test_macro_registry_fields.py`（追加用例）

- [ ] **Step 1: 写失败测试**

在 `prism/scripts/test_macro_registry_fields.py` 末尾追加：

```python
def test_fed_speech_text_fetch_validates_on_llm(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"availability": "llm", "text_fetch": "fed_speech"}))
    assert reg.validate_registry(slug, variant) == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest prism/scripts/test_macro_registry_fields.py::test_fed_speech_text_fetch_validates_on_llm -v`
Expected: FAIL — `text_fetch 非法: 'fed_speech'`

- [ ] **Step 3: 最小实现**

`prism/scripts/macro_registry.py:63`，`"pbc_mpr"` 后追加 `"fed_speech"`：

```python
VALID_TEXT_FETCH = ("fomc", "qra", "china_us", "hfcaa", "politburo", "pbc_mpr", "fed_speech")   # 脚本「取文」通道（下载原文存本地缓存），须与 textfetch._FETCHERS 键一致；
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest prism/scripts/test_macro_registry_fields.py::test_fed_speech_text_fetch_validates_on_llm -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/macro_registry.py prism/scripts/test_macro_registry_fields.py
git commit -m "feat(prism/macro): fed_speech 取文通道入 VALID_TEXT_FETCH 枚举"
```

---

## Task 8: 主席讲话取文 纯函数（过滤最新主席条 + 正文剥离）

**Files:**
- Create: `prism/scripts/fed_speech_fetch.py`
- Test: `prism/scripts/test_fed_speech_fetch.py`

- [ ] **Step 1: 写失败测试**

新建 `prism/scripts/test_fed_speech_fetch.py`：

```python
"""fed_speech 取文 fetcher 单测：纯函数（JSON feed 过滤最新主席条 + 正文剥离）。零网络。"""
from prism.scripts import fed_speech_fetch as fs


# feed 样本：含主席/副主席/理事，故意乱序，断言取最新主席条（排除 Vice Chair）
_ENTRIES = [
    {"d": "6/6/2026 12:00:00 PM", "t": "Dereg", "s": "Governor Michael S. Barr",
     "l": "/newsevents/speech/barr20260606a.htm"},
    {"d": "3/21/2026 1:30:00 PM", "t": "Acceptance Remarks", "s": "Chair Jerome H. Powell",
     "l": "/newsevents/speech/powell20260321a.htm"},
    {"d": "5/31/2026 9:00:00 AM", "t": "Outlook", "s": "Vice Chair Philip N. Jefferson",
     "l": "/newsevents/speech/jefferson20260531a.htm"},
    {"d": "1/11/2026 7:30:00 PM", "t": "Statement", "s": "Chair Jerome H. Powell",
     "l": "/newsevents/speech/powell20260111a.htm"},
]


def test_pick_latest_chair_excludes_vice_and_takes_newest():
    e = fs.pick_latest_chair(_ENTRIES)
    assert e is not None
    assert e["s"] == "Chair Jerome H. Powell"
    assert e["l"] == "/newsevents/speech/powell20260321a.htm"   # 3/21 > 1/11，且排除 5/31 Vice Chair


def test_pick_latest_chair_none_when_no_chair():
    only_others = [e for e in _ENTRIES if "Chair" not in e["s"] or "Vice" in e["s"]]
    assert fs.pick_latest_chair(only_others) is None


def test_extract_body_strips_tags_and_footer():
    html = ("<html><body><p>The economy remains resilient and inflation eased.</p>"
            "<div>Last Update: June 01, 2026</div></body></html>")
    body = fs._extract_body(html)
    assert "economy remains resilient" in body
    assert "Last Update" not in body
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest prism/scripts/test_fed_speech_fetch.py -v`
Expected: FAIL — `ModuleNotFoundError: fed_speech_fetch`

- [ ] **Step 3: 最小实现（纯函数部分）**

新建 `prism/scripts/fed_speech_fetch.py`：

```python
"""美联储主席讲话文本下载（零 LLM）——与 fomc_fetch / pbc_mpr_fetch 平行的取文 fetcher。

主席讲话是**定性前瞻指引**输入（stance_scale=hawk_dove）：脚本零-LLM 从 Fed 静态 JSON feed
（ne-speeches.json）过滤最新一篇主席（Chair，非 Vice Chair）讲话、下原文到 inbox/ 本地缓存、写
local_cache_path，之后 headless LLM 用 Read 判鹰鸽立场 → 降本，且新讲话自动发现。立场判读仍归 LLM，
本脚本只取文（故该输入 availability 仍是 llm，非 scripted）。

为何脚本可达：主页 speeches-testimony.htm 为 JS 渲染（脚本取不到），但 Fed 暴露静态 JSON feed
ne-speeches.json（utf-8-sig），每条 {d:日期, t:标题, s:讲话人, l:相对链接}。speaker 字段无歧义，
过滤 'Chair' in s 且 'Vice Chair' not in s 即得主席讲话。讲话正文页为静态 HTML。

「无新讲话」非常态失败：feed 始终含历史主席讲话，故每轮都能定位「最新主席讲话」并幂等重写缓存（同 fomc）。
指纹 = 讲话相对链接（内嵌日期，发布即定型）→ 新讲话 → 指纹变 → 去重门触发 LLM 重判。

用法：
  python -m prism.scripts.fed_speech_fetch [slug] [variant]
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from html import unescape
from pathlib import Path

import httpx

from prism.scripts import macro_registry as reg

_PRISM_ROOT = Path(__file__).resolve().parent.parent
_INPUT_NAME = "美联储官员讲话(主席)"
_FED_BASE = "https://www.federalreserve.gov"
_FEED_URL = _FED_BASE + "/json/ne-speeches.json"
_CHROME_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# ── HTML helper（按本仓约定各 fetcher 自带一份，不交叉 import） ──
_SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_PARA_TAG = re.compile(r"</?(?:p|h[1-6]|blockquote|section|article)\b[^>]*/?>", re.IGNORECASE)
_BLOCK_TAG = re.compile(r"</?(?:div|li|tr|header|footer)\b[^>]*/?>|<br\b[^>]*/?>", re.IGNORECASE)
_ANY_TAG = re.compile(r"<[^>]+>")
_INLINE_WS = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{3,}")
_BODY_ENDS = ["Last Update:", "Board of Governors of the Federal Reserve System",
              "Accessibility | Contact Us | Disclaimer"]


def _strip_html(raw: str) -> str:
    raw = _SCRIPT_STYLE.sub(" ", raw)
    raw = _PARA_TAG.sub("\n\n", raw)
    raw = _BLOCK_TAG.sub("\n", raw)
    raw = _ANY_TAG.sub(" ", raw)
    raw = unescape(raw)
    lines = [_INLINE_WS.sub(" ", ln).strip() for ln in raw.splitlines()]
    text = "\n".join(ln for ln in lines if ln).strip()
    return _MULTI_NL.sub("\n\n", text)


def _extract_body(report_html: str) -> str:
    """剥标签 → 截 footer 线索。返回正文（诚实兜底：无 footer 标记则全文）。"""
    text = _strip_html(report_html)
    cut = len(text)
    for end in _BODY_ENDS:
        j = text.find(end)
        if j != -1:
            cut = min(cut, j)
    return text[:cut].strip()


def _is_chair(speaker: str | None) -> bool:
    s = speaker or ""
    return "Chair" in s and "Vice Chair" not in s


def _parse_feed_date(s: str | None) -> _dt.datetime | None:
    """feed 日期 'M/D/YYYY h:mm:ss AM/PM' → datetime；解析失败 → None。"""
    try:
        return _dt.datetime.strptime((s or "").strip(), "%m/%d/%Y %I:%M:%S %p")
    except (ValueError, AttributeError):
        return None


def pick_latest_chair(entries: list[dict]) -> dict | None:
    """从 feed 取最新一篇主席（非副主席）讲话条目。解析 d 日期取最大，防 feed 排序异常。无主席条 → None。"""
    best, best_dt = None, None
    for e in entries:
        if not _is_chair(e.get("s")):
            continue
        dt = _parse_feed_date(e.get("d"))
        if dt is None:
            continue
        if best_dt is None or dt > best_dt:
            best, best_dt = e, dt
    return best
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest prism/scripts/test_fed_speech_fetch.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/fed_speech_fetch.py prism/scripts/test_fed_speech_fetch.py
git commit -m "feat(prism/macro): fed_speech 纯函数（feed 过滤最新主席条+正文剥离）"
```

---

## Task 9: 主席讲话取文 IO 入口 + fetch_one + main

**Files:**
- Modify: `prism/scripts/fed_speech_fetch.py`
- Test: `prism/scripts/test_fed_speech_fetch.py`（追加注入 fake client 的用例）

- [ ] **Step 1: 写失败测试**

在 `prism/scripts/test_fed_speech_fetch.py` 末尾追加：

```python
import json
import pytest
from prism.scripts import macro_registry as reg


class _FakeResp:
    def __init__(self, *, text=None, content=None):
        self.text = text or ""
        self.content = content if content is not None else (text or "").encode()
    def raise_for_status(self):
        pass


class _FakeClient:
    """feed URL 返回 JSON（带 BOM），讲话页返回 HTML。"""
    def __init__(self, entries, speech_html):
        self._feed = ("﻿" + json.dumps(entries)).encode("utf-8")
        self._html = speech_html
    def get(self, url, **kw):
        if url.endswith(".json"):
            return _FakeResp(content=self._feed, text=self._feed.decode("utf-8-sig"))
        return _FakeResp(text=self._html)
    def close(self):
        pass


@pytest.fixture
def speech_topic(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(fs, "_PRISM_ROOT", tmp_path)
    slug, variant = "t-macro", "opus4.8"
    reg.create_registry(slug, variant)
    reg.upsert_input(slug, variant, {
        "name": fs._INPUT_NAME, "tier": "A", "cadence_type": "policy",
        "targets": ["rates"], "mechanism": "CD", "importance": "confirming",
        "causal_sentence": "x→y→z。", "availability": "llm",
        "stance_scale": "hawk_dove", "text_fetch": "fed_speech",
    })
    return slug, variant


def test_fetch_fed_speech_writes_cache_and_sets_path(speech_topic, tmp_path):
    slug, variant = speech_topic
    html = "<html><body><p>Policy is well positioned; inflation eased.</p></body></html>"
    res = fs.fetch_fed_speech(slug, variant, client=_FakeClient(_ENTRIES, html))
    assert res["ok"]
    assert res["fingerprint"] == "/newsevents/speech/powell20260321a.htm"
    cache = tmp_path / "topics" / slug / "inbox" / "fed_speech_latest.md"
    assert cache.exists() and "inflation eased" in cache.read_text(encoding="utf-8")
    entry = next(e for e in reg.read_registry(slug, variant)["inputs"]
                 if e["name"] == fs._INPUT_NAME)
    assert entry["local_cache_path"].endswith("fed_speech_latest.md")


def test_fetch_one_routes_with_entry_name(speech_topic):
    slug, variant = speech_topic
    entry = {"name": fs._INPUT_NAME, "text_fetch": "fed_speech"}
    res = fs.fetch_one(slug, variant, entry,
                       client=_FakeClient(_ENTRIES, "<p>hawkish tone</p>"))
    assert res["ok"] and res["speaker"] == "Chair Jerome H. Powell"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest prism/scripts/test_fed_speech_fetch.py::test_fetch_fed_speech_writes_cache_and_sets_path -v`
Expected: FAIL — `AttributeError: ... 'fetch_fed_speech'`

- [ ] **Step 3: 最小实现（追加 IO 部分）**

在 `prism/scripts/fed_speech_fetch.py` 末尾追加：

```python
def _get(client: httpx.Client, url: str) -> httpx.Response:
    resp = client.get(url, timeout=30, follow_redirects=True,
                      headers={"User-Agent": _CHROME_UA})
    resp.raise_for_status()
    return resp


def fetch_fed_speech(slug: str, variant: str, *, client: httpx.Client | None = None,
                     input_name: str | None = None) -> dict:
    """下载最新主席讲话全文，存 inbox/fed_speech_latest.md，写 local_cache_path。

    返回 {title, speaker, date, url, cache_path, ok, fingerprint}。
    feed 抓取失败 / 无主席条 / 讲话页抓取失败 → {"error": ...}（真失败，调度器记 fetch_error 回落 llm）。
    fingerprint = 讲话相对链接（内嵌日期，发布即定型）→ 新讲话 → 指纹变 → 去重门触发 LLM 重判立场。
    """
    target = input_name or _INPUT_NAME
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        try:
            feed_resp = _get(client, _FEED_URL)
        except httpx.HTTPError as exc:
            return {"error": f"讲话 feed 抓取失败：{exc}"}
        try:
            entries = json.loads(feed_resp.content.decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError) as exc:
            return {"error": f"讲话 feed 解析失败：{exc}"}

        latest = pick_latest_chair(entries)
        if latest is None:
            return {"error": "feed 未找到主席讲话（站点结构可能变更）"}
        rel_link = latest.get("l", "")
        url = rel_link if rel_link.startswith("http") else _FED_BASE + rel_link
        title = latest.get("t", "")
        speaker = latest.get("s", "")
        date = latest.get("d", "")

        try:
            speech_html = _get(client, url).text
        except httpx.HTTPError as exc:
            return {"error": f"讲话页抓取失败（{title}）：{exc}"}
        body = _extract_body(speech_html)

        inbox_dir = _PRISM_ROOT / "topics" / slug / "inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        out_path = inbox_dir / "fed_speech_latest.md"
        lines = [
            f"# {title}",
            f"讲话人：{speaker}",
            f"日期：{date}",
            f"来源：{url}",
            "",
            body or "（正文抓取失败，仅留标题/链接——LLM 可据来源 URL 回落现场检索）",
            "",
            "---",
            "> 注：脚本零-LLM 自 Fed 讲话 feed 定位最新主席讲话并下原文存本地缓存；"
            "鹰鸽立场判读仍由 LLM 读本文件给出（observed.stance）。",
        ]
        out_path.write_text("\n".join(lines), encoding="utf-8")

        rel = str(out_path.relative_to(_PRISM_ROOT))
        reg.set_local_cache_path(slug, variant, target, rel)

        return {
            "title": title, "speaker": speaker, "date": date, "url": url,
            "cache_path": str(out_path), "ok": bool(body), "fingerprint": rel_link,
        }
    finally:
        if owns:
            client.close()


def fetch_one(slug: str, variant: str, entry: dict, *, client: httpx.Client | None = None) -> dict:
    """取文调度器入口（text_fetch=='fed_speech' 路由到此）。用 entry['name'] 作目标输入名。"""
    return fetch_fed_speech(slug, variant, client=client, input_name=entry.get("name"))


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    result = fetch_fed_speech(slug, variant)
    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)
    print(f"最新主席讲话: {result['title']}（{result['speaker']}，{result['date']}）"
          f"{'✓' if result['ok'] else '✗'}")
    print(f"来源: {result['url']}")
    print(f"缓存: {result['cache_path']}")
    print(f"指纹: {result['fingerprint']}")
    print("local_cache_path 已更新 → LLM 下次拉取将读本地文件判鹰鸽立场")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest prism/scripts/test_fed_speech_fetch.py -v`
Expected: PASS（5 passed）

- [ ] **Step 5: 活体冒烟（真网络）**

Run: `python3 -m prism.scripts.fed_speech_fetch global-macro-rates-liquidity opus4.8`
Expected: 打印最新主席讲话标题/讲话人/日期 + 缓存路径 + 指纹

- [ ] **Step 6: 提交**

```bash
git add prism/scripts/fed_speech_fetch.py prism/scripts/test_fed_speech_fetch.py
git commit -m "feat(prism/macro): fed_speech IO 入口 fetch/fetch_one + CLI 冒烟"
```

---

## Task 10: fed_speech 注册进取文调度器

**Files:**
- Modify: `prism/scripts/textfetch.py:23-39`

- [ ] **Step 1: import + 注册**

`prism/scripts/textfetch.py`：在 import 区（约 23–29 行）按字母序加 `from prism.scripts import fed_speech_fetch`；在 `_FETCHERS` 字典（约 32–39 行）`"fomc": fomc_fetch.fetch_one,` 之后加一行：

```python
    "fed_speech": fed_speech_fetch.fetch_one,
```

- [ ] **Step 2: 导入冒烟 + 键一致性**

Run:
```bash
python3 -c "
from prism.scripts import textfetch
from prism.scripts import macro_registry as reg
assert set(textfetch._FETCHERS) <= set(reg.VALID_TEXT_FETCH), '键须 ⊆ VALID_TEXT_FETCH'
assert 'fed_speech' in textfetch._FETCHERS
print('ok')
"
```
Expected: `ok`

- [ ] **Step 3: 提交**

```bash
git add prism/scripts/textfetch.py
git commit -m "feat(prism/macro): fed_speech 注册进取文调度器 _FETCHERS"
```

---

## Task 11: 登记表 `美联储官员讲话(主席)` 挂 text_fetch

**Files:**
- Modify: `prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml`（`美联储官员讲话(主席)` 条目，约 140–171 行）

- [ ] **Step 1: 挂 text_fetch（脚本驱动）**

Run:
```bash
python3 -c "
from prism.scripts import macro_registry as reg
reg.upsert_input('global-macro-rates-liquidity', 'opus4.8',
                 {'name': '美联储官员讲话(主席)', 'text_fetch': 'fed_speech'})
print('updated')
"
```
Expected: `updated`（availability 保持 llm 不动）

- [ ] **Step 2: 校验登记表全清**

Run:
```bash
python3 -c "
from prism.scripts import macro_registry as reg
errs = reg.validate_registry('global-macro-rates-liquidity', 'opus4.8')
print('errors:', errs); assert not errs, errs
"
```
Expected: `errors: []`

- [ ] **Step 3: 真取文一次确认落缓存**

Run: `python3 -m prism.scripts.textfetch global-macro-rates-liquidity opus4.8`
Expected: 输出含 `✓ 美联储官员讲话(主席): fp=/newsevents/speech/... cache=.../fed_speech_latest.md`

- [ ] **Step 4: 提交**

```bash
git add prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml prism/topics/global-macro-rates-liquidity/inbox/fed_speech_latest.md
git commit -m "content(prism/macro): 主席讲话挂 fed_speech 取文通道（首落原文缓存）"
```

---

## Task 12: 全量回归 + 变更核验 + 收尾

**Files:** 无新增

- [ ] **Step 1: 跑两 fetcher 单测 + 登记表字段测试**

Run: `python3 -m pytest prism/scripts/test_fomc_sep_fetch.py prism/scripts/test_fed_speech_fetch.py prism/scripts/test_macro_registry_fields.py -v`
Expected: 全 PASS

- [ ] **Step 2: 批量刷新路由冒烟（确认两通道并入 summary）**

Run:
```bash
python3 -c "
from prism.scripts import fomc_sep_fetch, textfetch
print('sep:', fomc_sep_fetch.run_fomc_sep_fetch('global-macro-rates-liquidity', 'opus4.8'))
res = textfetch.run_textfetch('global-macro-rates-liquidity', 'opus4.8', only={'美联储官员讲话(主席)'})
print('speech ok:', res['美联储官员讲话(主席)'].get('ok'))
"
```
Expected: `sep: {'fetched': 1, ...}` 且 `speech ok: True`

- [ ] **Step 3: gitnexus 变更核验（CLAUDE.md 强制）**

Run: `gitnexus_detect_changes()`
Expected: 受影响符号限于本计划新增/修改项（两 fetcher、macro_registry 枚举、textfetch、monitor_runtime、prism 路由），无意外波及。

- [ ] **Step 4: 索引刷新（让新文件进 GitNexus 图）**

Run: `npx gitnexus analyze`
Expected: 索引更新成功（新增 2 fetcher + 2 测试纳入图）

- [ ] **Step 5: 终验**

确认：`git status` 干净（除预期外无残留）；`git log --oneline -12` 见本计划各 commit。

---

## 自检（writing-plans 要求，已核）

- **Spec 覆盖**：A 部分（纯函数 T2 / IO T3 / 循环 T4 / 路由 T5 / 登记表 T6 / 枚举 T1）；B 部分（枚举 T7 / 纯函数 T8 / IO T9 / 调度器 T10 / 登记表 T11）；测试随各 Task；影响预检 T0 + 核验 T12。无遗漏。
- **占位符扫描**：无 TBD/TODO；每个改码步骤含完整代码。
- **类型/命名一致**：`find_latest_projtabl`/`parse_median_funds_rate`/`fetch_fomc_sep`/`run_fomc_sep_fetch`（A）与 `pick_latest_chair`/`_extract_body`/`fetch_fed_speech`/`fetch_one`（B）全程一致；`_INPUT_NAME` 两模块各自定义；`fomc_sep`/`fed_speech` 键贯穿枚举↔注册↔登记表一致。
- **风险**：线上 HTML/feed 结构变更会使解析返回 None/error → 走 record_fetch_error 留痕、不污染旧值（诚实降级）。Task 3/9 的活体冒烟即早期探针。

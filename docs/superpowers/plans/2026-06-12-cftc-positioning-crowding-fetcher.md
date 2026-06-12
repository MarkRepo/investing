# CFTC 持仓拥挤接入脚本 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增零-LLM 的 `cftc` 取数通道，从 CFTC 官方 Socrata API 拉杠杆基金 Treasury 净头寸 + 回看窗 z-score 拥挤度，落进登记表并开启 |z|≥2 报警，把 `持仓拥挤(...)` 这条 load-bearing 输入从 `scriptable_todo` 升为 `scripted`。

**Architecture:** 复用既有「脚本数值通道」范式（与 barchart/ecb/safe 同构）：新 fetcher 读登记表筛 `fetch_method=='cftc'` 的 scripted 项 → SoQL 单请求拉一窗周报 → 算 `net = long − short` 与 z → `record_observation`。中央派发挂到 `monitor_runtime`（定时）与 `routes/prism.py`（手动单条 + 批量）。

**Tech Stack:** Python · httpx（惰性导入，测试注入 mock）· statistics（z-score）· pytest · CFTC Socrata 开放数据 API（dataset `gpe5-46if`，TFF Futures-Only）

**前置参考：** spec `docs/superpowers/specs/2026-06-12-cftc-positioning-crowding-fetcher-design.md`；范本 `prism/scripts/barchart_fetch.py`、`tests/test_barchart_fetch.py`、`prism/scripts/test_macro_registry_fields.py`。

---

## File Structure

- **Create** `prism/scripts/cftc_fetch.py` — 通道实现：`fetch_by_cftc`（解析+算法）/`run_cftc_fetch`（派发）/`main`（冒烟+CLI）。
- **Create** `tests/test_cftc_fetch.py` — 单元测试（mock httpx，零网络）。
- **Modify** `prism/scripts/macro_registry.py` — `VALID_FETCH_METHOD` 加 `cftc`；`validate_registry` 加 cftc 块校验。
- **Modify** `prism/scripts/test_macro_registry_fields.py` — cftc 块校验测试。
- **Modify** `app/monitor_runtime.py` — 定时循环加 cftc 通道 try 块。
- **Modify** `app/routes/prism.py` — 单条手动抓分支 + 批量「刷新脚本项」try 块与汇总。
- **Modify** `prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml` — 经 `upsert_input` 改 entry（availability/fetch_method/cftc 块/alert_series/alert_band/note）。

---

## Task 1: 登记表加 `cftc` 通道枚举与块校验

**Files:**
- Modify: `prism/scripts/macro_registry.py:61`（`VALID_FETCH_METHOD`）、`prism/scripts/macro_registry.py:300-307`（validator，紧接 `safe` 块之后）
- Test: `prism/scripts/test_macro_registry_fields.py`（文件末尾追加）

- [ ] **Step 0: 改前影响分析（CLAUDE.md 强制）**

Run: `gitnexus_impact({target: "validate_registry", direction: "upstream"})`
Expected: 报告 blast radius（validate_registry 的调用方/受影响流程/风险级）。本改动仅「加一个并列分支」，预期 LOW；若返回 HIGH/CRITICAL 先告知用户再继续。

- [ ] **Step 1: 写失败测试**

在 `prism/scripts/test_macro_registry_fields.py` 末尾追加（复用文件内既有 `tmp_reg` fixture 与 `_base` helper）：

```python
# --- cftc 通道块校验：scripted + fetch_method=cftc 须配 cftc 块（dataset/contract 必填）---

def test_cftc_valid_block_passes(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({
        "availability": "scripted", "fetch_method": "cftc",
        "cftc": {"dataset": "gpe5-46if", "contract": "UST 10Y NOTE"}}))
    assert reg.validate_registry(slug, variant) == []


def test_cftc_missing_block_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"availability": "scripted", "fetch_method": "cftc"}))
    assert any("cftc 须配 cftc 块" in e for e in reg.validate_registry(slug, variant))


def test_cftc_missing_contract_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({
        "availability": "scripted", "fetch_method": "cftc",
        "cftc": {"dataset": "gpe5-46if"}}))   # 缺 contract
    assert any("cftc 块缺 contract" in e for e in reg.validate_registry(slug, variant))
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest prism/scripts/test_macro_registry_fields.py -k cftc -v`
Expected: FAIL —`test_cftc_valid_block_passes` 因 `fetch_method 非法: 'cftc'` 而 validate 非空；缺块/缺 contract 两条因尚无 cftc 校验分支而无对应错误串。

- [ ] **Step 3: 实现——加枚举 + 校验分支**

`prism/scripts/macro_registry.py:61` 行末把 `cftc` 加进元组：

```python
VALID_FETCH_METHOD = ("fred-api", "recipe", "akshare", "yfinance", "macromicro", "barchart", "ecb", "safe", "cftc")   # 脚本「数值」通道，仅 scripted 项可设
```

在 `validate_registry` 里 `if fm == "safe":` 块（`prism/scripts/macro_registry.py:300-307`）之后，紧接插入：

```python
        if fm == "cftc":
            cc = e.get("cftc")
            if not cc:
                errors.append(f"[{name}] fetch_method=cftc 须配 cftc 块")
            else:
                for k in ("dataset", "contract"):
                    if not cc.get(k):
                        errors.append(f"[{name}] cftc 块缺 {k}")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest prism/scripts/test_macro_registry_fields.py -k cftc -v`
Expected: PASS（3 条）

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/macro_registry.py prism/scripts/test_macro_registry_fields.py
git commit -m "feat(prism/macro): cftc 通道登记表枚举 + 块校验"
```

---

## Task 2: `fetch_by_cftc`——SoQL 取数 + 净头寸 + z 算法

**Files:**
- Create: `prism/scripts/cftc_fetch.py`
- Test: `tests/test_cftc_fetch.py`

- [ ] **Step 1: 写失败测试**

新建 `tests/test_cftc_fetch.py`：

```python
"""cftc 取数通道：fetch_by_cftc 解析 + run_cftc_fetch 派发（mock httpx，零网络）。

覆盖：净头寸+z 正算、最新行选取、样本不足 z=None、std=0 z=None、cohort 切换、
空数据软降级、缺 contract/dataset 抛、未知 cohort 抛、缺腿行跳过；run 级成功/失败/only/跳过。
"""
from __future__ import annotations

import statistics

import pytest

from prism.scripts import cftc_fetch as cf


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeClient:
    """mock httpx.Client：.get(url, params=) → FakeResp(payload)。记录 calls 供断言。"""

    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def get(self, url, params=None):
        self.calls.append((url, params))
        return FakeResp(self._payload)


def _row(date, lng, sht, oi=1000000):
    return {"report_date_as_yyyy_mm_dd": f"{date}T00:00:00.000",
            "lev_money_positions_long": str(lng),
            "lev_money_positions_short": str(sht),
            "open_interest_all": str(oi)}


def test_net_and_z_computed():
    # 4 行降序；净头寸 net = long - short = [-100, -80, -60, -40]
    rows = [_row("2026-06-02", 400, 500), _row("2026-05-26", 420, 500),
            _row("2026-05-19", 440, 500), _row("2026-05-12", 460, 500)]
    cli = FakeClient(rows)
    v, z, d = cf.fetch_by_cftc(
        {"dataset": "gpe5-46if", "contract": "UST 10Y NOTE", "min_obs": 4}, client=cli)
    nets = [-100, -80, -60, -40]
    expected_z = (nets[0] - statistics.fmean(nets)) / statistics.pstdev(nets)
    assert v == -100 and d == "2026-06-02"
    assert abs(z - expected_z) < 1e-9
    _, params = cli.calls[0]
    assert params["$where"] == "contract_market_name='UST 10Y NOTE'"
    assert "DESC" in params["$order"] and params["$limit"] == "156"


def test_latest_row_is_first():
    rows = [_row("2026-06-02", 100, 900), _row("2026-05-26", 500, 500)]
    v, _, d = cf.fetch_by_cftc(
        {"dataset": "d", "contract": "c", "min_obs": 99}, client=FakeClient(rows))
    assert v == -800 and d == "2026-06-02"


def test_insufficient_obs_z_none():
    rows = [_row("2026-06-02", 400, 500), _row("2026-05-26", 420, 500)]
    v, z, _ = cf.fetch_by_cftc(
        {"dataset": "d", "contract": "c", "min_obs": 30}, client=FakeClient(rows))
    assert v == -100 and z is None


def test_zero_std_z_none():
    rows = [_row("2026-06-02", 400, 500), _row("2026-05-26", 400, 500),
            _row("2026-05-19", 400, 500)]
    v, z, _ = cf.fetch_by_cftc(
        {"dataset": "d", "contract": "c", "min_obs": 3}, client=FakeClient(rows))
    assert v == -100 and z is None


def test_cohort_switch_reads_asset_mgr():
    rows = [{"report_date_as_yyyy_mm_dd": "2026-06-02T00:00:00.000",
             "asset_mgr_positions_long": "900", "asset_mgr_positions_short": "100"}]
    cli = FakeClient(rows)
    v, _, _ = cf.fetch_by_cftc(
        {"dataset": "d", "contract": "c", "cohort": "asset_mgr", "min_obs": 99}, client=cli)
    assert v == 800
    assert "asset_mgr_positions_long" in cli.calls[0][1]["$select"]


def test_empty_data_returns_none():
    v, z, d = cf.fetch_by_cftc({"dataset": "d", "contract": "c"}, client=FakeClient([]))
    assert v is None and z is None and d is None


def test_rows_missing_legs_skipped():
    rows = [{"report_date_as_yyyy_mm_dd": "2026-06-02T00:00:00.000",
             "lev_money_positions_long": "400"},   # 缺 short
            _row("2026-05-26", 420, 500)]
    v, _, d = cf.fetch_by_cftc(
        {"dataset": "d", "contract": "c", "min_obs": 99}, client=FakeClient(rows))
    assert v == -80 and d == "2026-05-26"   # 首行缺腿被跳过，value/as_of 对齐次行


def test_missing_dataset_raises():
    with pytest.raises(ValueError, match="dataset"):
        cf.fetch_by_cftc({"contract": "c"}, client=FakeClient([]))


def test_missing_contract_raises():
    with pytest.raises(ValueError, match="contract"):
        cf.fetch_by_cftc({"dataset": "d"}, client=FakeClient([]))


def test_unknown_cohort_raises():
    with pytest.raises(ValueError, match="cohort"):
        cf.fetch_by_cftc({"dataset": "d", "contract": "c", "cohort": "retail"},
                         client=FakeClient([]))
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_cftc_fetch.py -v`
Expected: FAIL —`ModuleNotFoundError: No module named 'prism.scripts.cftc_fetch'`

- [ ] **Step 3: 实现 `cftc_fetch.py`（本任务只到 `fetch_by_cftc`）**

新建 `prism/scripts/cftc_fetch.py`：

```python
"""CFTC 持仓拥挤取数通道（杠杆基金净头寸 + 回看窗 z-score）。零 LLM：读登记表里
fetch_method=='cftc' 且 availability=='scripted' 且有 cftc 配置块的输入，
从 CFTC 官方 Socrata 开放数据 API 拉一窗周度持仓 → 算净头寸 + z → record_observation。

与 fred_fetch / recipe_fetch / barchart_fetch / ecb_fetch / safe_fetch 平行（脚本「数值」通道）。
典型用途：**杠杆基金(leveraged funds)在 UST 10Y NOTE 期货上的净头寸**——carry/套息拥挤度的
直接探头，且杠杆基金 Treasury 净空头是 basis-trade(现券-期货基差交易)规模的公开代理。

取数机制（单请求 SoQL）：
  GET {base}/{dataset}.json
      ?$where=contract_market_name='{contract}'
      &$order=report_date_as_yyyy_mm_dd DESC
      &$limit={lookback}
      &$select=report_date...,{cohort}_positions_long,{cohort}_positions_short,open_interest_all
  逐行 net = long − short（按报告日降序，第 0 行=最新）。

口径：
  value = 最新一期净头寸（合约数，带符号；负=净空）。
  z     = 整个 lookback 窗净头寸序列的 z-score（教科书 COT 拥挤极端度）；样本不足/方差 0 → None。
  as_of = 最新一期报告日 YYYY-MM-DD。
注意：CFTC TFF 周报（周二为准、约 3 天发布延迟）；官方免鉴权、无反爬，匿名有速率限制——周频单请求不触发。
"""
from __future__ import annotations

import math
import statistics
import sys

from prism.scripts import macro_registry as reg

_DEFAULT_BASE = "https://publicreporting.cftc.gov/resource"
_VALID_COHORTS = ("lev_money", "asset_mgr", "dealer", "other_rept")
_DATE_COL = "report_date_as_yyyy_mm_dd"


def _to_float(v) -> float | None:
    """单元转 float；空/非数/NaN → None。值含千分位逗号则去掉。"""
    if v is None:
        return None
    if isinstance(v, str):
        v = v.replace(",", "").strip()
        if not v:
            return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _import_httpx():
    import httpx  # 惰性导入
    return httpx


def fetch_by_cftc(cfg: dict, *, client=None) -> tuple[float | None, float | None, str | None]:
    """按 cftc 配置抓一期净头寸 + 回看窗 z-score。
    cfg: {dataset, contract, cohort?='lev_money', lookback?=156, min_obs?=30, base_url?}。
    返回 (value=最新净头寸合约数, z=净头寸序列 z-score 或 None, as_of=最新报告日 或 None)。
    缺 dataset/contract 或 cohort 非法 → 抛 ValueError；空数据/字段缺失 → 诚实 (None, None, None)。
    client 可注入（测试 mock：支持 .get(url, params=...) → .raise_for_status()/.json()）。"""
    dataset = (cfg.get("dataset") or "").strip()
    contract = (cfg.get("contract") or "").strip()
    if not dataset:
        raise ValueError("cftc 配置缺 dataset")
    if not contract:
        raise ValueError("cftc 配置缺 contract")
    cohort = cfg.get("cohort", "lev_money")
    if cohort not in _VALID_COHORTS:
        raise ValueError(f"cftc cohort 非法: {cohort!r}（仅 {list(_VALID_COHORTS)}）")
    lookback = int(cfg.get("lookback", 156))
    min_obs = int(cfg.get("min_obs", 30))
    base_url = cfg.get("base_url", _DEFAULT_BASE)
    long_col = f"{cohort}_positions_long"
    short_col = f"{cohort}_positions_short"
    url = f"{base_url}/{dataset}.json"
    params = {
        "$where": f"contract_market_name='{contract}'",
        "$order": f"{_DATE_COL} DESC",
        "$limit": str(lookback),
        "$select": f"{_DATE_COL},{long_col},{short_col},open_interest_all",
    }
    owns = client is None
    if owns:
        client = _import_httpx().Client(timeout=30)
    try:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        rows = resp.json()
    finally:
        if owns:
            client.close()
    if not rows:
        return None, None, None
    # (日期, 净头寸) 序列，按返回的报告日降序；跳过缺腿/非数行
    # （value 取首个可用行、as_of 对齐之，避免最新行缺腿时日期错配）
    series: list[tuple[str | None, float]] = []
    for r in rows:
        lo = _to_float(r.get(long_col))
        sh = _to_float(r.get(short_col))
        if lo is None or sh is None:
            continue
        d = r.get(_DATE_COL)
        series.append((str(d)[:10] if d else None, lo - sh))
    if not series:
        return None, None, None
    as_of, value = series[0]
    nets = [n for _, n in series]
    z = None
    if len(nets) >= min_obs:
        sd = statistics.pstdev(nets)
        if sd > 0:
            z = (value - statistics.fmean(nets)) / sd
    return value, z, as_of
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_cftc_fetch.py -v`
Expected: PASS（11 条 fetch_by_cftc 用例；run 级用例下一任务加）

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/cftc_fetch.py tests/test_cftc_fetch.py
git commit -m "feat(prism/macro): cftc_fetch.fetch_by_cftc 净头寸+z 解析"
```

---

## Task 3: `run_cftc_fetch` + `main`——派发与 CLI/冒烟

**Files:**
- Modify: `prism/scripts/cftc_fetch.py`（追加两函数）
- Test: `tests/test_cftc_fetch.py`（追加 run 级用例）

- [ ] **Step 1: 写失败测试**

在 `tests/test_cftc_fetch.py` 末尾追加：

```python
# --- run_cftc_fetch 派发 ---

def _patch_reg(monkeypatch, inputs):
    from prism.scripts import macro_registry as reg
    monkeypatch.setattr(reg, "read_registry", lambda s, v: {"inputs": inputs})
    obs, errs = [], []
    monkeypatch.setattr(reg, "record_observation",
                        lambda s, v, name, **kw: obs.append((name, kw.get("value"), kw.get("z"))))
    monkeypatch.setattr(reg, "record_fetch_error",
                        lambda s, v, name, **kw: errs.append((name, kw.get("msg"))))
    return obs, errs


def test_run_records_observation(monkeypatch):
    rows = [_row("2026-06-02", 400, 500), _row("2026-05-26", 420, 500)]
    obs, errs = _patch_reg(monkeypatch, [
        {"name": "持仓拥挤", "fetch_method": "cftc", "availability": "scripted",
         "cftc": {"dataset": "d", "contract": "c", "min_obs": 2}},
        {"name": "别的", "fetch_method": "fred-api"},   # 非 cftc → 跳过
    ])
    summary = cf.run_cftc_fetch("m", "v", client=FakeClient(rows))
    assert obs and obs[0][0] == "持仓拥挤" and obs[0][1] == -100
    assert summary["fetched"] == 1 and not errs


def test_run_records_error_on_empty(monkeypatch):
    obs, errs = _patch_reg(monkeypatch, [
        {"name": "持仓拥挤", "fetch_method": "cftc", "availability": "scripted",
         "cftc": {"dataset": "d", "contract": "c"}}])
    summary = cf.run_cftc_fetch("m", "v", client=FakeClient([]))
    assert not obs and errs and summary["failed"] == 1


def test_run_only_filters(monkeypatch):
    rows = [_row("2026-06-02", 400, 500)]
    obs, _ = _patch_reg(monkeypatch, [
        {"name": "A", "fetch_method": "cftc", "availability": "scripted",
         "cftc": {"dataset": "d", "contract": "c", "min_obs": 99}},
        {"name": "B", "fetch_method": "cftc", "availability": "scripted",
         "cftc": {"dataset": "d", "contract": "c", "min_obs": 99}}])
    summary = cf.run_cftc_fetch("m", "v", only={"A"}, client=FakeClient(rows))
    assert [o[0] for o in obs] == ["A"] and summary["fetched"] == 1


def test_run_skips_non_scripted(monkeypatch):
    obs, _ = _patch_reg(monkeypatch, [
        {"name": "待办", "fetch_method": "cftc", "availability": "scriptable_todo",
         "cftc": {"dataset": "d", "contract": "c"}}])
    summary = cf.run_cftc_fetch("m", "v", client=FakeClient([]))
    assert not obs and summary["skipped_todo"] == 1
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_cftc_fetch.py -k run -v`
Expected: FAIL —`AttributeError: module 'prism.scripts.cftc_fetch' has no attribute 'run_cftc_fetch'`

- [ ] **Step 3: 实现——追加 `run_cftc_fetch` 与 `main`**

在 `prism/scripts/cftc_fetch.py` 末尾（`fetch_by_cftc` 之后）追加：

```python
def run_cftc_fetch(slug: str, variant: str, *, only: set[str] | None = None,
                   client=None) -> dict:
    """抓所有 fetch_method=='cftc' 且 availability=='scripted' 且有 cftc 配置的输入。
    llm 项诚实跳过计数（走 headless LLM）。only 给定时只抓名字在其中的项（web 单条手动抓）。
    失败（抛异常/取不到值）记 record_fetch_error 并计数，不连累其余。返回 summary。"""
    data = reg.read_registry(slug, variant)
    fetched = skipped_todo = skipped_llm = failed = 0
    for e in data["inputs"]:
        if e.get("fetch_method") != "cftc":
            continue
        if only is not None and e["name"] not in only:
            continue
        avail = e.get("availability")
        if avail == "llm":
            skipped_llm += 1
            continue
        if avail != "scripted" or not e.get("cftc"):
            skipped_todo += 1
            continue
        try:
            val, z, as_of = fetch_by_cftc(e["cftc"], client=client)
        except Exception as exc:               # 配置/网络/结构等：记错、跳过，不连累其余
            reg.record_fetch_error(slug, variant, e["name"], msg=str(exc))
            failed += 1
            continue
        if val is None:
            reg.record_fetch_error(slug, variant, e["name"],
                                   msg=f"cftc 未取到值（限流或源变更）: {e['cftc'].get('contract')}")
            failed += 1
            continue
        reg.record_observation(slug, variant, e["name"], value=val, z=z, as_of=as_of)
        fetched += 1
    return {"fetched": fetched, "skipped_todo": skipped_todo,
            "skipped_llm": skipped_llm, "failed": failed}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    # 自带活体冒烟：无参时直接拉 UST 10Y NOTE 杠杆基金净头寸 + z
    if not argv:
        v, z, d = fetch_by_cftc({"dataset": "gpe5-46if", "contract": "UST 10Y NOTE"})
        zs = f"{z:.2f}" if z is not None else "None"
        print(f"UST 10Y NOTE lev_money net: {v} (z={zs}) @ {d}")
        return
    slug = argv[0]
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    print(f"cftc 抓取: {run_cftc_fetch(slug, variant)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_cftc_fetch.py -v`
Expected: PASS（全部 15 条）

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/cftc_fetch.py tests/test_cftc_fetch.py
git commit -m "feat(prism/macro): cftc_fetch run 派发 + CLI 冒烟"
```

---

## Task 4: 中央派发接线（monitor_runtime + routes/prism）

**Files:**
- Modify: `app/monitor_runtime.py:156`（ecb try 块之后插入 cftc 块）
- Modify: `app/routes/prism.py:963`（单条分支）、`app/routes/prism.py:982-983`（批量 import）、`app/routes/prism.py:1017`（批量 try 块）、`app/routes/prism.py:1029-1041`（汇总与返回）

- [ ] **Step 0: 改前影响分析（CLAUDE.md 强制）**

Run: `gitnexus_impact({target: "prism_macro_fetch_script_all", direction: "upstream"})`
Expected: blast radius 报告；预期 LOW（仅新增并列通道，不改既有分支）。HIGH/CRITICAL 则先告知用户。

- [ ] **Step 1: monitor_runtime 加 cftc 通道块**

在 `app/monitor_runtime.py` 的 ecb try 块结束处（`app/monitor_runtime.py:156`，`_log(f"ecb fetch failed: {e}")` 行之后）插入：

```python
        # macro CFTC 自动抓取（零 LLM）：杠杆基金净头寸 + z 拥挤度（持仓拥挤探头/basis-trade 代理），
        # fetch_method=='cftc' 的 scripted 项，CFTC Socrata 周报。失败吞掉、不阻断周期。
        try:
            from prism.scripts import cftc_fetch
            from prism.scripts import topic as topic_io
            for t in topic_io.list_topics():
                if t.get("type") != "macro":
                    continue
                cftc_summary = await asyncio.to_thread(
                    cftc_fetch.run_cftc_fetch, t["slug"], t["variant"])
                _log(f"cftc fetch [{t['slug']}/{t['variant']}]: {cftc_summary}")
        except Exception as e:
            _log(f"cftc fetch failed: {e}")
```

- [ ] **Step 2: routes/prism 单条手动抓分支**

在 `app/routes/prism.py` 的 `elif method == "ecb":` 块（`app/routes/prism.py:961-963`）之后、`else:`（line 964）之前插入：

```python
    elif method == "cftc":
        from prism.scripts import cftc_fetch
        summary = cftc_fetch.run_cftc_fetch(slug, variant, only={name})
```

- [ ] **Step 3: routes/prism 批量——import + try 块 + 汇总**

(a) 批量函数 import（`app/routes/prism.py:982-983`）加 `cftc_fetch`：

```python
    from prism.scripts import (fred_fetch, recipe_fetch, textfetch, akshare_fetch,
                               yfinance_fetch, macromicro_fetch, barchart_fetch, ecb_fetch,
                               cftc_fetch)
```

(b) 在 ecb_sum try 块（`app/routes/prism.py:1013-1017`）之后、recipe 注释行（line 1018）之前插入：

```python
    # cftc（杠杆基金净头寸+z 拥挤度，basis-trade 代理）：脚本数值通道；失败吞掉不毁整批
    try:
        cftc_sum = cftc_fetch.run_cftc_fetch(slug, variant)
    except Exception as _exc:
        cftc_sum = {"_error": str(_exc), "fetched": 0}
```

(c) 在 `ecb_n = ecb_sum.get("fetched", 0) or 0`（`app/routes/prism.py:1031`）之后插入：

```python
    cftc_n = cftc_sum.get("fetched", 0) or 0
```

(d) 把返回 JSON（`app/routes/prism.py:1033-1041`）整段替换为（加入 cftc）：

```python
    if "application/json" in (request.headers.get("accept") or ""):
        return JSONResponse({"fred": fred_n, "recipe": recipe_n, "akshare": akshare_n,
                             "yfinance": yfin_n, "macromicro": mm_n, "barchart": bc_n,
                             "ecb": ecb_n, "cftc": cftc_n, "text": text_n,
                             "fetched": fred_n + recipe_n + akshare_n + yfin_n + mm_n + bc_n + ecb_n + cftc_n + text_n,
                             "fred_summary": fred_sum, "recipe_summary": recipe_sum,
                             "akshare_summary": akshare_sum, "yfinance_summary": yfin_sum,
                             "macromicro_summary": mm_sum, "barchart_summary": bc_sum,
                             "ecb_summary": ecb_sum, "cftc_summary": cftc_sum, "text_summary": text_sum})
```

- [ ] **Step 4: 冒烟——import 不破 + 路由可加载**

Run: `python -c "import app.monitor_runtime, app.routes.prism; from prism.scripts import cftc_fetch; print('import ok')"`
Expected: 打印 `import ok`，无 ImportError/SyntaxError。

- [ ] **Step 5: 提交**

```bash
git add app/monitor_runtime.py app/routes/prism.py
git commit -m "feat(prism/macro): cftc 通道接入定时循环 + 手动/批量路由"
```

---

## Task 5: 升级登记表 entry 并校验

**Files:**
- Modify: `prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml`（经 `upsert_input` 改 entry，**不手改 yaml**）

- [ ] **Step 1: 经 upsert_input 升级 entry + 校验**

Run（一段脚本，merge 既有字段、改 6 处、即时校验）：

```bash
python -c "
from prism.scripts import macro_registry as reg
slug, variant = 'global-macro-rates-liquidity', 'opus4.8'
name = '持仓拥挤(CFTC + CTA/vol-target + basis-trade规模)'
reg.upsert_input(slug, variant, {
    'name': name,
    'availability': 'scripted',
    'fetch_method': 'cftc',
    'cftc': {'dataset': 'gpe5-46if', 'contract': 'UST 10Y NOTE',
             'cohort': 'lev_money', 'lookback': 156, 'min_obs': 30},
    'alert_series': True,
    'alert_band': {'z': 2.0},
    'note': ('杠杆基金 Treasury 净头寸做 basis-trade + CFTC 主腿'
             '(源 gpe5-46if / lev_money / UST 10Y NOTE, 周频)。'
             'CTA/vol-target 无免费单值源, 仍属 LLM 判读/待办。'),
})
errs = reg.validate_registry(slug, variant)
print('validate errors:', errs)
assert not errs, errs
e = next(i for i in reg.read_registry(slug, variant)['inputs'] if i['name'] == name)
assert e['availability'] == 'scripted' and e['fetch_method'] == 'cftc'
assert e['alert_series'] is True and e['alert_band'] == {'z': 2.0}
assert e['cftc']['contract'] == 'UST 10Y NOTE'
# gloss/causal_sentence/family/tier 等既有字段未丢
assert e.get('gloss') and e.get('causal_sentence') and e.get('family') == '跨资产代理'
print('entry OK')
"
```

Expected: `validate errors: []`、`entry OK`。

- [ ] **Step 2: 确认 diff 只动这一条 entry**

Run: `git diff --stat prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml`
Expected: 仅该文件变更；`git diff` 内容应集中在目标 entry 的 6 处字段 + 顶部 `updated` 时间戳（`upsert_input` 会刷新）。若出现无关 entry 的大面积重排，停下检查（yaml.dump 一致性问题）。

- [ ] **Step 3: 提交**

```bash
git add prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml
git commit -m "content(prism/macro): 持仓拥挤升 scripted（cftc 通道 + z≥2 报警）"
```

---

## Task 6: 活体验证 + 影响面复核

**Files:** 无（验证步骤）

- [ ] **Step 1: 离线全测试绿**

Run: `python -m pytest tests/test_cftc_fetch.py prism/scripts/test_macro_registry_fields.py -q`
Expected: PASS，无 fail。

- [ ] **Step 2: 活体冒烟（只读，不写盘）**

Run: `python -m prism.scripts.cftc_fetch`
Expected: 形如 `UST 10Y NOTE lev_money net: -1963094.0 (z=-X.XX) @ 2026-06-02`（具体数字随当周变；net 为大额负数=净空、z 为有限浮点）。若打印 `None`，说明源结构/合约名变更——停下排查再继续。

- [ ] **Step 3: 真实落盘一次（实际接入抓取）**

Run: `python -m prism.scripts.cftc_fetch global-macro-rates-liquidity opus4.8`
Expected: 形如 `cftc 抓取: {'fetched': 1, 'skipped_todo': 0, 'skipped_llm': 0, 'failed': 0}`。

随后确认 observed 已落（value/z/as_of、且无 fetch_error）：

```bash
python -c "
from prism.scripts import macro_registry as reg
e = next(i for i in reg.read_registry('global-macro-rates-liquidity','opus4.8')['inputs']
         if i['name'].startswith('持仓拥挤'))
print(e['observed'])
assert e['observed'].get('value') is not None and 'fetch_error' not in e['observed']
print('observed OK')
"
```

Expected: 打印含 `value`/`z`/`as_of`/`checked_at` 的 observed dict + `observed OK`。

- [ ] **Step 4: 影响面复核（CLAUDE.md 强制，提交前）**

Run: `gitnexus_detect_changes()`
Expected: 受影响符号仅限本期新增/改动（cftc_fetch 新模块、validate_registry、批量/单条路由、monitor 循环）；无意外波及。出现意外范围则停下核对。

- [ ] **Step 5: 提交落盘观测**

```bash
git add prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml
git commit -m "content(prism/macro): 持仓拥挤 cftc 首次落盘观测（lev_money 10Y 净头寸+z）"
```

---

## Self-Review（plan vs spec）

- **Spec §2.1 新通道** → Task 2/3（`fetch_by_cftc`/`run_cftc_fetch`/`main`）。✅
- **Spec §2.2 取数与算法**（SoQL 单请求、net=long−short、value/z/as_of、min_obs/std=0 降级、cohort 白名单、config 默认值）→ Task 2 代码 + Task 2 测试逐条覆盖。✅
- **Spec §2.3 登记表改动**（VALID_FETCH_METHOD、validator、entry 6 处字段、alert_series 翻 true）→ Task 1（枚举+校验）+ Task 5（entry）。✅
- **Spec §2.4 中央派发两处** → Task 4（monitor_runtime + routes 单条 + 批量）。✅
- **Spec §2.5 Web 展示**（无新模板工作，复用既有 observed 渲染）→ 无任务，符合 spec。✅
- **Spec §3 测试**（净头寸+z、最新行、<min_obs、std=0、cohort 切换、空数据、配置非法、缺腿、run 级成功/失败/only/跳过、validator）→ Task 1/2/3 测试逐条对应。✅
- **Spec §4 影响面/风险**（impact 复核、alert 行为变更、诚实降级）→ Task 1/4 Step 0 impact、Task 6 detect_changes。✅
- **占位符扫描**：无 TBD/TODO；每个代码步均含完整代码。✅
- **类型/签名一致性**：`fetch_by_cftc` 全程返 `(value, z, as_of)` 三元组；`run_cftc_fetch(slug, variant, *, only, client)` 在测试与路由调用处签名一致；`cftc` 配置键（dataset/contract/cohort/lookback/min_obs/base_url）在代码、测试、entry、validator 间一致。✅

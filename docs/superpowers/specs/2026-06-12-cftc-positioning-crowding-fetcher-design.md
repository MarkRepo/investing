# 宏观层 · 持仓拥挤（CFTC 杠杆基金净头寸）接入脚本设计

> 状态：已与用户逐项确认架构方向，待用户复审本文档后转实现计划
> 日期：2026-06-12 · slug `global-macro-rates-liquidity` · variant `opus4.8` · type=macro
> 前置（均已实现）：
> - `2026-06-07-macro-dynamic-monitoring-and-maturation-design.md`（第二期，FRED 自动抓 + 报警带 + Web 输入表）
> - `2026-06-10-macro-cross-cutting-and-judgment-ledger-design.md`（第三期，横切接入 + 判断台账）
> - CIP 合成层（barchart/ecb 新通道 + 按名派生）——本期新增的 `cftc` 通道与之同构

---

## 0. 一句话目标

把登记表里 `持仓拥挤(CFTC + CTA/vol-target + basis-trade规模)` 这条复合 load-bearing 输入，从 `scriptable_todo` 落成 `scripted`：新增一个零-LLM 的 **`cftc` 取数通道**，从 CFTC 官方 Socrata 开放数据 API 拉 **杠杆基金（leveraged funds）在 Treasury 期货上的净头寸**，算出**净头寸（合约数）+ 回看窗 z-score 拥挤度**，落进 `observed`，并开启 `|z|≥2` 的「carry 去杠杆」报警探头。

---

## 1. 背景与现状（已核实）

### 1.1 这条输入今天长什么样

`macro_inputs.yaml`（`global-macro-rates-liquidity/opus4.8`）现有 entry（节选）：

```yaml
- name: 持仓拥挤(CFTC + CTA/vol-target + basis-trade规模)
  tier: B
  cadence_type: series
  targets: [rates, fx, liquidity]
  mechanism: CD
  importance: load_bearing
  causal_sentence: 拥挤定位是 carry 渠道传感器：拥挤越极端，去杠杆平仓的非线性冲击越大 → 经强制平仓资金流 → 驱动利率/汇率/流动性。
  alert_series: false
  authority: official
  availability: scriptable_todo
  source_url: https://publicreporting.cftc.gov/
  note: 复合指标(CFTC 持仓+CTA/vol-target+basis-trade 规模)难单值化——CFTC 有 Socrata JSON API 可抓持仓腿,但
    CTA/basis 无公开单值源。保留 scriptable_todo:待定一个主腿(如 CFTC 杠杆基金净头寸)后可写部分 recipe。
  family: 跨资产代理
  gloss:
    define: 期货持仓+CTA/波动率目标+基差交易规模的复合拥挤度
    read: carry/杠杆交易有多拥挤，去杠杆冲击的传感器
    use: 极端拥挤=强平踩踏风险大、尾部脆弱；分散=缓冲厚
```

note 已把本期要解决的开放问题写明：**「待定一个主腿后可写部分 recipe」**。

### 1.2 现有取数框架（本期复用，不重造）

脚本「数值」通道是一组同构的 fetcher，每个：读登记表 → 筛 `fetch_method==<自己>` 且 `availability=='scripted'` 且有自己的配置块 → 抓值 → `record_observation`；失败记 `record_fetch_error`、跳过不连累其余。

- `prism/scripts/macro_registry.py`：登记表 CRUD + 校验 + `record_observation(value, z, as_of, ...)` / `record_fetch_error`。`VALID_FETCH_METHOD` 枚举所有通道，validator 按 `fetch_method` 校验对应配置块。
- 现有通道：`fred-api / recipe / akshare / yfinance / macromicro / barchart / ecb / safe`。`barchart_fetch.py` / `ecb_fetch.py` / `safe_fetch.py` 是「专有源 + 自带配置块」的范本。
- **中央派发两处**：
  - `app/monitor_runtime.py`：定时循环里每通道一个 `try` 块，`run_*_fetch` 刷新 observed（macro scan 之前）。
  - `app/routes/prism.py`：单条手动抓（`/macro-inputs/fetch-script`，按 `fetch_method` 分支）+ 批量「刷新脚本项」（`/macro-inputs/fetch-script-all`）。
- 测试范式：`tests/test_barchart_fetch.py`——mock httpx，零网络，逐路径覆盖解析与降级。

### 1.3 实地探测结论（feasibility，已实拉验证）

- 端点 `https://publicreporting.cftc.gov/resource/gpe5-46if.json` 活、免鉴权、无反爬；`gpe5-46if` = *Traders in Financial Futures*（TFF）周报 Futures-Only。
- SoQL 参数 `$where / $order / $select / $limit` 均可用。
- 字段齐备：`contract_market_name`、`report_date_as_yyyy_mm_dd`、`open_interest_all`，以及分交易者类型的多空腿：`lev_money_positions_long/short`（杠杆基金）、`asset_mgr_positions_long/short`（资管）、`dealer_positions_long/short`（做市商）、`other_rept_positions_long/short`。
- 最新一期 2026-06-02（周频，周二为准、约 3 天发布延迟）。
- 关键合约名均在：`UST 2Y NOTE / UST 5Y NOTE / UST 10Y NOTE / UST BOND / ULTRA UST 10Y / ULTRA US T BOND`、`E-MINI S&P 500`、`JAPANESE YEN`、`EURO FX`、`SOFR-3M` 等。
- 实测：UST 10Y NOTE 杠杆基金净头寸 = 398,043 − 2,361,137 = **−1,963,094 张（净空）**——即当前 basis trade 的体量。

### 1.4 三维数据源可得性（定了本设计取舍）

| 维度 | 数据源 | 状态 | 说明 |
|------|--------|------|------|
| CFTC 持仓 | CFTC Socrata API（官方一手、免费） | ✅ 脚本化 = 主值 | 杠杆基金净头寸 = carry/套息拥挤度直接探头 |
| basis-trade 规模 | 同上，杠杆基金 Treasury 净空头**代理** | ✅ 同一腿覆盖 | basis trade 机制=对冲基金做空 Treasury 期货+做多现券；其净空头是 OFR/Fed/BIS 量化 basis trade 用的同款公开代理 |
| CTA/vol-target | 投行模型估算（付费指数/卖方研报） | 🔴 留 note、LLM 待办 | 模型估算量，无免费单值端点，硬抓不稳定不权威 |

取舍原则：**能拿官方一手免费数据的维度脚本化（CFTC，且一鱼两吃代理 basis-trade）；拿不到免费权威数据的维度（CTA/vol-target）诚实留白**，绝不为「复合指标看起来完整」拼一个不可信的数。与既有 CIP 基差「免费算不准就别假装算得准」同一原则。

---

## 2. 设计

### 2.1 新通道 `cftc`（与 barchart/ecb/safe 同构）

新建 `prism/scripts/cftc_fetch.py`，两个公开函数：

```python
def fetch_by_cftc(cfg: dict, *, client=None) -> tuple[float | None, float | None, str | None]:
    """按 cftc 配置抓一期净头寸 + 回看窗 z-score。
    返回 (value=最新净头寸合约数, z=净头寸序列 z-score, as_of=最新报告日 YYYY-MM-DD)。
    任何对不上 → 诚实 (None, None, None)，不抛（除配置非法）。client 可注入（测试 mock）。"""

def run_cftc_fetch(slug: str, variant: str, *, only=None, client=None) -> dict:
    """抓所有 fetch_method=='cftc' 且 availability=='scripted' 且有 cftc 配置的输入。
    成功 record_observation(value, z, as_of)；失败 record_fetch_error。返回 summary。"""
```

注意 `fetch_by_cftc` 比同类多返一个 `z`（同类只返 `(value, as_of)`）——因为拥挤度的核心信息在极端度而非绝对水平，`record_observation` 本就支持 `z=` 形参，直接落盘。

### 2.2 取数与算法（全部 config-driven）

一次请求（GET）：

```
GET https://publicreporting.cftc.gov/resource/{dataset}.json
    ?$where=contract_market_name='{contract}'
    &$order=report_date_as_yyyy_mm_dd DESC
    &$limit={lookback}
    &$select=report_date_as_yyyy_mm_dd,{cohort}_positions_long,{cohort}_positions_short,open_interest_all
```

逐行：`net = {cohort}_positions_long − {cohort}_positions_short`（按报告日降序，第 0 行=最新）。

- **value** = 最新一期 `net`（合约数，带符号；负=净空）。教科书 COT 净头寸口径，与下方 z 同序列、可解释。
- **z** = 整个 lookback 窗 `net` 序列的 z-score：`(net_latest − mean(net_series)) / std(net_series)`。这是交易员实际在用的「COT z-score」拥挤极端度指标。
  - 样本不足（usable 行数 `< min_obs`，默认 30）→ `z=None`（诚实降级，不编造 z），但 `value` 仍落。
  - `std==0`（罕见，全窗持平）→ `z=None`。
- **as_of** = 最新行 `report_date_as_yyyy_mm_dd` 的日期段（`[:10]`）。
- 任一字段缺失/非数/空数据 → 该项 `(None, None, None)`；`run_cftc_fetch` 据此 `record_fetch_error`。

**配置块默认值**：

```yaml
cftc:
  dataset: gpe5-46if          # TFF Futures-Only
  contract: "UST 10Y NOTE"    # basis-trade + 利率 carry 主腿
  cohort: lev_money           # 杠杆基金；可选 asset_mgr/dealer/other_rept
  lookback: 156               # 回看周数（3 年），算 z 用
  min_obs: 30                 # 算 z 的最小样本（不足则 z=None）
```

`cohort` 白名单 `{lev_money, asset_mgr, dealer, other_rept}`，非法 → raise（拼字段名前校验，杜绝拼错字段静默取空）。`base_url` 可选覆盖（默认 `https://publicreporting.cftc.gov/resource`），便于测试/换源。

### 2.3 登记表改动（macro_registry.py + entry）

`macro_registry.py`：
- `VALID_FETCH_METHOD` 追加 `"cftc"`。
- validator 追加：`fm == "cftc"` ⟹ 须有 `cftc` 块且块内 `dataset`、`contract` 非空（与 barchart/ecb/safe 的块校验同款）。

entry `持仓拥挤(CFTC + CTA/vol-target + basis-trade规模)` 改动（经 `upsert_input` 或直接改 yaml）：
- `availability: scriptable_todo → scripted`
- 新增 `fetch_method: cftc` + 上述 `cftc` 配置块
- **`alert_series: false → true`** + `alert_band: {z: 2.0}`（唯一行为变更，已确认开）：杠杆基金拥挤度 |z|≥2 触发「carry 去杠杆」探头报警。
- `note` 更新为诚实记录：*杠杆基金 Treasury 净头寸做 basis-trade + CFTC 主腿（源 gpe5-46if/lev_money/UST 10Y NOTE）；CTA/vol-target 无免费单值源，仍属 LLM 判读/待办。*
- `name`/`gloss`/`causal_sentence` 不变（不拆分）。

校验：改完跑 `validate_registry` 须零错误（alert_series=true 要求 cadence_type=series——本条已是 series，通过）。

### 2.4 中央派发接线（两处）

- `app/monitor_runtime.py`：仿 barchart/ecb 块新增一个 `try` 块，遍历 macro 主题调 `cftc_fetch.run_cftc_fetch`，失败吞掉不阻断周期。位置：与其余各腿通道并列，**在 recipe（按名派生）之前**即可（本通道不被任何派生项依赖，位置不敏感）。
- `app/routes/prism.py`：
  - 单条手动抓 `prism_macro_fetch_script`：`method == "cftc"` 分支 → `cftc_fetch.run_cftc_fetch(slug, variant, only={name})`。
  - 批量 `prism_macro_fetch_script_all`：import 加 `cftc_fetch`，仿 barchart 加一个 `try` 块；其 summary 计入返回（`cftc_n`）。

### 2.5 Web 展示

无需新模板工作：`observed` 的 `value/z/as_of/alert_band` 既有「输入源信息表」已渲染；`alert_series=true` + `alert_band.z` 自动进现有报警显示。z 由本通道落盘，与 FRED 项的 z 同样消费。

---

## 3. 测试

新建 `tests/test_cftc_fetch.py`，mock httpx（零网络），仿 `test_barchart_fetch.py`：

1. **净头寸 + z 正算**：给一窗已知 long/short 行 → value=最新 net、z 等于手算 z-score、as_of=最新日期。
2. **最新行选取**：乱序/降序输入下取 `$order DESC` 第 0 行为 value。
3. **样本不足**：行数 `< min_obs` → value 有值、z=None。
4. **std==0**：全窗 net 持平 → z=None、value 有值。
5. **cohort 切换**：`cohort=asset_mgr` 取 `asset_mgr_positions_*` 字段。
6. **空数据**：`[]` → `(None, None, None)`。
7. **配置非法**：缺 `contract`/`dataset` → raise；未知 `cohort` → raise。
8. **字段缺失/非数**：行缺腿或非数 → 诚实降级。
9. **run 级**：mock registry，验证成功走 `record_observation(value, z, as_of)`、失败走 `record_fetch_error`、`only=` 过滤、非 scripted/无配置块跳过计数。

另加 `macro_registry` 校验测试：cftc 项缺块/缺 dataset/缺 contract 报错（仿现有 `test_macro_registry_fields.py` 风格）。

`cftc_fetch.main()` 自带活体冒烟（无参 → 实拉 UST 10Y NOTE 打印 value/z/as_of），与 barchart `main()` 一致，便于手验源未变。

---

## 4. 影响面与风险

- **新增为主**：新文件 `cftc_fetch.py` + 测试；改动点是 `macro_registry.py`（加枚举+校验分支）、`monitor_runtime.py`（加 try 块）、`routes/prism.py`（加分支+try 块）、entry yaml。均为「加一个并列通道」，不动既有通道逻辑。实现前对 `VALID_FETCH_METHOD`、`run_*_fetch` 派发点跑 gitnexus impact 复核 blast radius。
- **唯一行为变更**：该 entry `alert_series` 翻 true——会新增一个可能报警的 series（|z|≥2 时）。已确认。
- **数据陈旧/源变更**：周频源；若 CFTC 改 dataset id/字段名 → `fetch_by_cftc` 取空 → `record_fetch_error` 留痕、旧值保留不污染（与既有通道同款诚实降级），Web 顶部告警板提示去修。
- **匿名限流**：Socrata 匿名有速率限制；周频单请求远不触发。需要时配置块可扩 `app_token`（留扩展位，首版不做）。
- **z 的趋势污染**：原始净头寸的 z 在 3 年窗内含轻微市场扩张趋势（已与用户讨论，确认用原始净头寸以匹配「净头寸」口径与教科书 COT z）。未来若需更平稳口径，可在配置块加 `normalize: net_oi`（净头寸/未平仓量）开关——首版不做。

---

## 5. 交付清单

1. `prism/scripts/cftc_fetch.py`（`fetch_by_cftc` + `run_cftc_fetch` + `main`）
2. `tests/test_cftc_fetch.py`
3. `prism/scripts/macro_registry.py`：`VALID_FETCH_METHOD` += `cftc`、validator cftc 块校验
4. `app/monitor_runtime.py`：cftc 通道 try 块
5. `app/routes/prism.py`：单条分支 + 批量 try 块
6. entry yaml 改动（availability/fetch_method/cftc 块/alert_series/alert_band/note）
7. 校验：`validate_registry` 零错误；`pytest tests/test_cftc_fetch.py` 绿；`gitnexus_detect_changes` 确认影响面

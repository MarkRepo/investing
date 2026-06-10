# 宏观层 · 横切接入与判断台账设计（第三期）

> 状态：已与用户逐块确认架构方向，待用户复审本文档后转实现计划
> 日期：2026-06-10 · slug `global-macro-rates-liquidity` · variant `opus4.8` · type=macro
> 前置：
> - `2026-06-07-macro-rates-liquidity-layer-design.md`（第一期 MVP，已实现）
> - `2026-06-07-macro-dynamic-monitoring-and-maturation-design.md`（第二期，已实现；本期落其 §7「第三步」）
> - `2026-06-08-macro-judgment-cockpit-and-provenance-design.md`（第二期判断驾驶舱/溯源，已实现；本期复用其 `regime_eval_log` 脊梁）

---

## 0. 一句话目标

把宏观层从一个**只对自己说话**的独立 topic，升级成：① **横切接入其他 topic 的研究**——regime 读数显式喂进 company/arena 的合成，并在体制变化时反向标记受影响持仓；② **判断可证伪台账**——每条结论写时许下可证伪的方向预测，事后由数据机械裁决"判得对不对"，老错的机制边降级。

落第二期 spec §7「第三步」的两项（item 8 决策/结果台账 + 自评分；item 9 贴现率注入各 case），并按用户"可独立核验、不是 trust-me"的元诉求重新定型。

---

## 1. 背景与现状（已核实）

第二期建好了**宏观自己**的活框架：116 条输入登记表、FRED 自动抓、报警带、`regime_eval_log.yaml`（输入→判断溯源脊梁，含 `input_snapshot` 全列 + `conclusions[].based_on` 反查）、web 输入表 + eval-trace 溯源 tab + 发起重估盖戳。但有两处缺口，是本期要补：

1. **横切几乎不存在**：`transmission_map.yaml` 是单向产物（regime → 每持仓敏感度标签），且只被 dashboard banner 读。company/arena 的合成工作流**不拉** macro；其他 topic 只在 findings/primer 里偶尔提"宏观"，无结构化消费。体制变化也无法反向触达受影响持仓。
2. **判断对错无人验**：`eval_snapshot.py` 记下了"判了什么、靠哪些输入"，但**零**评分——没有任何机制拿后续事实核对 regime 判断（§6.8 决策/结果台账 + 自评分在第二期被显式推迟到第三期）。

### 1.1 驱动本设计的两个用户洞察（brainstorm 中确认）

- **利率/流动性不是只通过 DCF 起作用**。primer 的四条传导渠道里，只有**贴现率渠道**是 DCF；**风险偏好渠道**走估值倍数/风险溢价、**carry-久期渠道**走资金流、**汇率渠道**走计价+资金流。且对部分持仓 macro 打的是**基本面**而非估值（富途/Robinhood 的交投量=流动性函数=营收；利率→地产→白酒销量；汇率→出口商利润）。故"只做贴现率注入"会接错地方——组合里最受 macro 影响的几只（富途/Robinhood/拼多多）主渠道恰恰不是 DCF。
- **transmission_map 应保持定性，不该硬掰成数字**。宏观 beta 不稳定、随体制漂移，逐持仓硬定量=假精确，违背第二期 §9「不做方向预测/择时、不做 EV 加总」。唯一诚实可量化的是**贴现率本身**（机械：供 10Y 实际利率，由 case 自己跑贴现率弹性）。

### 1.2 本期定型（逐项为用户拍板结论）

| 维度 | 决定 |
|------|------|
| 范围与排序 | 两条都做、**横切先行**、一份 spec |
| 接入形态 | **定性为主 + DCF case 加贴现率锚**（覆盖四渠道，唯一数字是贴现率） |
| 闭环范围 | **拉取 + 体制变扫失鲜（双向闭环）**；反向对账留第四期 |
| 强制度 | **company 强制 hook，arena/industry 软提示** |
| 新 topic 不在表 | **自注册 + provisional + 覆盖看门狗** |
| 验证真相 | **结果台账（机械打分）** |
| 可证伪机制 | 写时每条结论对 load_bearing 输入许 `expected` 方向预测 |
| 打分时机 | **连续可算（零-LLM）+ 重评时落档裁定 + 机制边降级** |

---

## 2. 阶段 3a — 横切接入

### 2.1 核心数据流（双向闭环）

```
macro 合成 ──写──▶ transmission_map.yaml (每持仓四渠道标签 + favor/hurt)
                         │
   company 合成 ──读──▶ macro hook (_company_case.md Step 1, 紧随亲属 hook)
        │                ├─ 读 regime_read + 本持仓行 → 织进 ⑤风险 / ②估值
        │                ├─ DCF case: 取 10Y 实际利率 → 贴现率锚 + ±50bp 弹性
        │                └─ 落 macro_stamp.yaml (站在哪版 regime / 依赖哪些体制状态 / 用了什么贴现率)
        │                      │
        ▼                      ▼ (新持仓不在表里)
   source=macro_synth 行       自判四渠道标签写回 transmission_map (source=self_registered, provisional=true)
        │
 regime 重合成 ──▶ 复核 provisional 行(晋升/改写) + 体制变扫失鲜
                         │ macro_xcut.scan_holding_staleness(): 零-LLM
                         │ 各 company 的 macro_stamp.depends_on_states vs 最新 regime eval
                         │ → 依赖的体制状态变了 → 给该持仓盖 stale 旗 + 写 macro_regime proposal
                         ▼
              dashboard banner: 「N 持仓 vs 当前体制已过期」+ 覆盖率(漏注册/provisional)
```

判断永远人在对话触发；staleness 与 coverage 全是零-LLM 派生（镜像现有 `diff_since_last`）。

### 2.2 数据模型

#### transmission_map.yaml — 每持仓行新增字段

| 字段 | 取值 | 含义 |
|---|---|---|
| `source` | `macro_synth` / `self_registered` | 这行是 macro 合成判的，还是 company 自注册的 |
| `provisional` | bool（默认 false） | self_registered 且未经 macro 层复核；macro 合成时晋升清除 |
| `as_of_regime` | `vN` | 这行依据哪一版 regime eval 判的 |

> 既有字段（`duration / rate_beta / liquidity_beta / usd_exposure / exposure_score / regime_favor / regime_hurt / plain`）原样不动；本期只**追加**三个可空字段，旧行缺这三个字段视为 `source=macro_synth, provisional=false, as_of_regime=null`，不破坏 dashboard banner 契约。

#### outputs/macro_stamp.yaml（company 侧新 sidecar · 反查锚）

`regime_eval_log` 的镜像反向件——"我写这份 case 时站在哪套 macro 上"：

```yaml
slug: pinduoduo
variant: opus4.8
stamped_at: "2026-06-10T..."
as_of_regime_version: 3              # 站在 regime_eval_log 的哪一版
regime_composite: "美紧中松分化..."   # 合成时综合判断快照(人读)
depends_on_states:                   # 这份 case 倚赖的体制状态(机械反查锚)
  - {conclusion: fx_cny,   state: "人民币企稳", role: load_bearing}
  - {conclusion: rates_us, state: "高位筑顶",   role: confirming}
discount_rate:                       # 仅 DCF case 有；否则整块 null
  risk_free: 0.0211                  # 由 macro 供的 10Y 实际利率
  applied_wacc: 0.115
  rate_sensitivity: "贴现率 ±50bp → 估值 ∓12%"
  source_input: "10Y 实际利率 TIPS"
stale: false                         # 宏观来源失鲜旗(下游 scan 写)
stale_reason: null                   # 如 "依赖的『人民币企稳』已变『贬压』(regime v3→v4)"
```

**不变量**：`depends_on_states[].conclusion` 必须能在对应版本 regime eval 的 conclusions 里找到；`role ∈ {load_bearing, confirming, background}`。

> **取舍**：`macro_stamp` 独立 sidecar，**不折进 `07_decision_kit.yaml`**——后者是 dashboard 硬契约"只认这套字段名"，不能污染。

### 2.3 组件

#### `prism/scripts/macro_xcut.py`（新 · 零-LLM）

- `read_macro_stamp(slug, variant) -> dict`（缺文件返空骨架，不抛）。
- `write_macro_stamp(slug, variant, stamp) -> Path`（校验不变量后落盘）。
- `scan_holding_staleness(macro_slug, macro_variant) -> list`：枚举所有带 `macro_stamp` 的 company topic，对每个比 `as_of_regime_version` + `depends_on_states` vs 最新 regime eval 的 conclusions；某依赖结论的 `state` 自 stamp 版本以来变了 → `[{slug, variant, stale, changed_states:[{conclusion, from, to}]}]`。无基准（无 regime eval / 无 stamp）→ 标"无基准"不报错。
- `apply_holding_staleness(...)`：把 scan 结果落地——给 stamp 盖 `stale: true` + `stale_reason`，并经 `monitor.propose_flips` 写 `kind='macro_regime'` proposal。
- `coverage_gaps(macro_variant) -> dict`：枚举所有 company-type topic（`topic.list_topics`）vs transmission_map 的 holdings slug → `{missing:[...], provisional:[...], covered_count, total_company}`。漏覆盖被显式暴露（呼应"沉默≠确认"）。
- `register_holding_row(...)`：self-register 写回辅助——撞已存在行**不覆盖、跳过+计数**。

#### 工作流改动

- **`_company_case.md` Step 1（强制 hook，紧随亲属 hook）**：① 读 macro `transmission_map` 本持仓行 + `m_regime_read` 相关体制；② 织进决策链 ⑤风险/②估值——定性四渠道敏感度 + favor/hurt；DCF case 另取 10Y 实际利率落贴现率锚 + 跑 ±50bp 弹性；③ 落 `macro_stamp.yaml`（含 `depends_on_states` + `discount_rate`）；④ 不在表则就着当下 regime 自判四渠道标签、写回 transmission_map（`source=self_registered, provisional=true, as_of_regime=vN`）。**缺 macro topic / 缺 regime eval → 软降级**：标"无宏观基准"，仍落空 stamp，不阻塞 case。
- **`_arena_funnel.md` / `_industry_funnel.md`（软提示）**：合成收尾加一句"建议跑 macro hook 评估赛道/行业的体制敏感度"，不强制、不阻塞、不落 stamp。
- **`_macro_regime.md`（macro 合成）**：Step 4 transmission_map 落盘后，**复核 provisional 行**（确认/改写标签、清 `provisional`、更新 `as_of_regime`）；Step 5 record_evaluation 后调 `macro_xcut.scan_holding_staleness` + `apply_holding_staleness`（体制变扫失鲜）。

#### monitor 回路

- 新 proposal `kind='macro_regime'`，指向**下游 company topic**，`status='awaiting_confirm'`，文案"宏观体制变化：你依赖的 X 已由『A』变『B』，建议重判"。与既有 `kind='macro_input'` 同构（信息型）。
- **stage 不动**（关键决策，见 §2.4）。confirm 一条 macro_regime proposal = 追加该 topic living_feed + 维持 stale 旗（真正清旗靠用户重跑 company 合成）。

#### web 面

- **dashboard banner**：加「过期持仓」列（`scan_holding_staleness` 的 stale 项 + 一句 reason）+「覆盖率」指示（`coverage_gaps`：已覆盖/漏注册/provisional）。
- **company topic 页**：显示"宏观背景 as_of regime vN"+ 若 stale 显"已过期 X 天：reason"。
- 路由守卫沿既有 macro 路由惯例。

### 2.4 关键决策：持仓被标 stale 后 stage 不变

沿用现有 monitor 回路形态——**stage 保持原样**（通常 `06-daily-monitor`）。证据：现有 monitor（含宏观自己的 `macro_input` proposal）从不改 stage，只写 `awaiting_confirm` proposal + 盖戳（`monitor.py` 明注"macro proposal 是信息型"）。理由：topic 的 stage 代表"人驱动研究流程走到哪"，宏观挪一格不否定那份研究、只让它**可能**需刷新——正是"加 stale 旗 + 提 proposal"该干的，不是把 stage 倒回 04 重做。

信号三处落点：① `macro_stamp` 的 `stale`/`stale_reason` 字段（**不碰 `c_investment_case` 的 output status**——那是"本 topic 自己资料变了"的增量重写信号，宏观来源 stale 走 stamp 自己的字段，避免两种 stale 混锅）；② monitor 队列 `macro_regime` proposal；③ dashboard「过期持仓」列。用户消化：看旗 → 说「重判 拼多多」→ 重跑 company 合成 → macro hook 重盖 `as_of_regime=最新版`、清 stale 旗、写新 case；stage 自然仍停监控、无需倒带。

---

## 3. 阶段 3b — 判断台账

### 3.1 核心思想

每条结论写时对它的承重输入许下**可证伪的方向预测**；事后机器拿实际序列裁决，不靠 LLM 回头给自己打分。预测提前钉死、数据说话——这是门外汉能独立核验的"战绩"。

### 3.2 数据模型：`based_on` 边加 `expected`

```yaml
conclusions:
  - id: rates_us
    label: 美国利率体制
    state: "高位筑顶"
    based_on:
      - {input: 联邦基金目标区间, role: load_bearing, expected: up_or_flat}   # 可证伪：维持/升
      - {input: 2Y/10Y/30Y 国债,  role: load_bearing, expected: up_or_flat}
      - {input: HY OAS,           role: confirming,    expected: widen}      # 可选
    causal: "..."
```

- **方向词表**：数值型 `up / down / flat / up_or_flat / down_or_flat`；policy/stance 型复用既有 stance 轴方向（`reg.STANCE_DIRECTION`，鹰/鸽等）；非数值输入 `expected` 可空。
- **`load_bearing` 边强制带 `expected`**；confirming/background 可选（本期不强制 confirming）。
- 校验落 `eval_snapshot._validate_evaluation`：load_bearing 缺 `expected` 报错；`expected` 非法方向词报错。`expected` 不破坏既有 `input_snapshot 列全 + based_on 不悬空 + role 合法` 三不变量。

### 3.3 组件：`prism/scripts/eval_score.py`（新 · 零-LLM · 全派生不存盘）

- `score_edge(expected, snapshot_value, live_value, scale=None) -> "hit"|"miss"|"neutral"`：数值型按方向 + 容差判（复用 `reg._reading_breaches` 思路）；stance 型走 `eval_snapshot._stance_direction`；`flat` 预测在容差内=hit、越界=miss；缺基准序列（未抓）→ `neutral`（不算命中也不算失手，呼应"未抓=诚实盲区"）。
- `score_evaluation(slug, variant, version=None) -> dict`：对指定版本（默认上一版）的每条结论逐边算 hit/miss/neutral → 每结论"占对率"+ 整版战绩卡 + 天数。拿"该版 expected" vs "现 observed 序列"，**连续可算、按需重算**（同 `diff_since_last`，不存盘）。
- `edge_ledger(slug, variant) -> list`：跨所有评估版本按 `(conclusion_id, input_name)` 累计 hit/miss → `[{conclusion_id, input, hits, misses, neutrals, track}]`，挑出命中率差的**降级候选**。

### 3.4 两个时机

- **连续可算（零-LLM，web 随时显示）**：`score_evaluation` 实时算"上一版判断现在走对几个承重输入"，web 显示如「3 个月前那版利率判断：4 个承重输入 3 个走对、1 个走反 → 75% 占对，已 95 天」。
- **重评时落档裁定（LLM/人，折进现有流程）**：`record_evaluation` 增可选参数 `prior_verdict: [{conclusion_id, verdict: held|partial|wrong, note}]`，写在**新评估条目**上（不改旧条目，保 `regime_eval_log` append-only 不可变）。`_macro_regime.md` Step 5 流程：简报多带"上一版机械战绩卡"→ LLM/用户据此落 `prior_verdict`。**机制边降级** = 一次正常 registry 编辑（`macro_registry.upsert_input` 改 tier A→B / 调 based_on role），由 `edge_ledger` 浮出降级候选驱动；不发明新台账文件。

### 3.5 web 面

- `eval-trace` tab 加"上版战绩卡"区（`score_evaluation` 结果：逐结论占对率 + 天数 + 走对/走反明细）。
- 输入表/结论旁显示边的历史命中率（`edge_ledger`）；降级候选高亮。

---

## 4. 测试策略（TDD，零-LLM 脚本全覆盖）

解释器 `.venv/bin/python`（3.14.4），`-p no:cacheprovider -q`。

- `prism/scripts/test_macro_xcut.py`（新）：staleness 扫（依赖状态变/没变/无 stamp/无 regime eval 优雅降级）、`coverage_gaps`（漏注册/provisional 计数）、self-register 写回幂等（撞行不覆盖+计数）、stamp CRUD + 不变量（悬空 conclusion 报错）。
- `prism/scripts/test_eval_score.py`（新）：`score_edge` 三态（数值 up/down/flat、stance 轴、缺基准 neutral、容差边界）、`score_evaluation` 占对率与天数、`edge_ledger` 跨版累计与降级候选、无 expected/无上一版的优雅降级。
- `prism/scripts/test_eval_snapshot.py`（扩展）：`expected` 字段校验（load_bearing 缺 expected 报错、方向词枚举非法报错）、`prior_verdict` 落新条目不改旧、既有不变量回归。
- `prism/scripts/test_macro_registry.py`（扩展，如需）：降级编辑（tier/role 改）回归。
- `tests/test_macro_inputs_web.py`（扩展）+ dashboard 测试：过期持仓列、覆盖率指示、战绩卡渲染、`macro_regime` proposal 出现、company 页宏观背景/stale 显示。

---

## 5. 错误处理 / 边界

- 无 `regime_eval_log` / 无 `transmission_map`：staleness 全标"无基准"、coverage 照常枚举、score 标"首次/无基准"，均不 500。
- company 无 DCF：`macro_stamp.discount_rate` 整块 null，只落定性 `depends_on_states`。
- self-register 撞已存在行：跳过 + 计数，不覆盖（macro 合成才是权威改写处）。
- `expected` 缺基准序列（输入未抓）：该边记 `neutral`，不计入命中/失手。
- company hook 缺 macro topic / 缺 regime eval：软降级标"无宏观基准"，落空 stamp，不阻塞 case 合成。
- `record_evaluation` 校验失败（load_bearing 缺 expected / 悬空 based_on / 未列全输入）：抛错不落盘（保快照可信）。
- arena/industry：软提示，永不阻塞、不落 stamp、不参与 staleness/coverage。

---

## 6. 受 GitNexus 纪律约束的实现期动作

改 `record_evaluation` / `monitor` proposal 路径 / `set_output_status` / `dashboard` / 各合成 workflow 引用的既有 symbol 前，按 CLAUDE.md：先 `gitnexus_impact(target, upstream)` 报爆炸半径，HIGH/CRITICAL 先警告再动；提交前 `gitnexus_detect_changes` 核改动范围；重命名走 `gitnexus_rename`。

---

## 7. 非目标（YAGNI）

- 不做宏观方向预测/择时（延续第一/二期）。
- 不硬定量 transmission_map（除 DCF case 的贴现率锚）——定性是诚实上限。
- 不强制 confirming/background 边带 `expected`（只压 load_bearing）。
- 不做 company→macro 反向对账（实证与标签冲突的回流）——留第四期；provisional 复核已埋种子。
- 不自动发起任何重判/重合成——永远人在对话触发（延续既定边界）。
- 不把战绩/ledger 存盘——全零-LLM 派生、按需重算（唯一存盘的人工动作是 `prior_verdict`）。
- 不改 dashboard banner 既有字段名/契约——transmission_map 只追加可空字段。

---

## 8. prism 容器映射

| 件 | 变化 | 阶段 |
|------|------|------|
| `transmission_map.yaml` schema | 改：每行加 `source`/`provisional`/`as_of_regime`（可空，不破契约） | 3a |
| `outputs/macro_stamp.yaml`（company 侧） | **新 sidecar**：反查锚 + 贴现率锚 + stale 旗 | 3a |
| `prism/scripts/macro_xcut.py` | **新（零-LLM）**：staleness 扫 + coverage 看门狗 + self-register | 3a |
| `prism/workflows/04-synthesize/_company_case.md` | 改：Step 1 强制 macro hook | 3a |
| `prism/workflows/04-synthesize/_arena_funnel.md` / `_industry_funnel.md` | 改：软提示 | 3a |
| `prism/workflows/04-synthesize/_macro_regime.md` | 改：复核 provisional + 体制变扫失鲜 + Step 5 落 expected/prior_verdict | 3a+3b |
| `prism/scripts/monitor.py` | 改：新 `kind='macro_regime'` proposal | 3a |
| `prism/scripts/eval_snapshot.py` | 改：`based_on` 加 `expected` 校验 + `record_evaluation` 加 `prior_verdict` | 3b |
| `prism/scripts/eval_score.py` | **新（零-LLM）**：score_edge / score_evaluation / edge_ledger | 3b |
| `app/routes/prism.py` + 模板（dashboard / macro_inputs / eval_trace / company 页） | 改：过期持仓列 + 覆盖率 + 战绩卡 + 宏观背景显示 | 3a+3b |

---

## 9. 成功标准

- 每个 company case 合成时显式消费 regime（定性四渠道 + DCF 贴现率锚），并落 `macro_stamp` 反查锚；新建持仓自注册进 transmission_map、漏覆盖被看门狗显式暴露。
- regime 重合成时，依赖变化的持仓被零-LLM 扫出、盖 stale 旗 + 提 `macro_regime` proposal；stage 不被倒带；用户重跑 company 合成即清旗。
- 每条 regime 结论的承重输入带可证伪 `expected`；任一时点可零-LLM 算出历史判断的"占对率战绩"；重评时落 `prior_verdict`、老错机制边被 `edge_ledger` 浮出并可降级。
- 全程判断人触发、信号不静默；战绩可由门外汉对照 FRED 序列独立核验（不是 trust-me）。
- 与 prism 现有 topic/dashboard/monitor/eval-log 机器同构，web 自动反映。

---

## 10. 留待第四期

- company→macro 反向对账（自下而上实证与 transmission 标签冲突的结构化回流；provisional 复核已埋种子）。
- confirming/background 边的 `expected` 与更细战绩。
- （可选）跨 topic 的组合级体制压力测试 / doom-loop 查找表联动（第二期 §6.5）。

# 三层知识系统 ingest 设计

**Status**: 设计已定，待 writing-plans 出实施计划
**Date**: 2026-04-26（v2.2，含财务 line items 扩展 + 研报图 caption 强化）
**Supersedes**: `docs/PLAN-INDUSTRY-INGEST.md`（v0，已废弃）
**v1 → v2 变化**: arena 从"聚合视图"升为"博弈叙事独立数据层（6 维度）"；company 增加"画像 narrative 层（8 维度）"；ingest 四套 workflow（行业研报 / 年报 / 季报 / 公司研报）全部升级为 digest + 主 agent 分拣架构；sector 概念及其所有派生物完全删除
**v2.1 → v2.2 变化**: §4.7 财务 line items 从 8 列扩到 ~45 列（支持 DuPont / FCF / OCF quality / CCC 等二次分析）+ A 股/US GAAP alias map；§4.8 preprocess 新增 `figure_contexts[]` 抽取（caption + 周围文本）以强化研报图表数据捕获；vision 裁图方案推 v2

---

## 1. 背景与动机

### 1.1 问题诊断（三层都碎）

当前"一套投资决策工作流"的知识呈现是**事实碎片 + 无维度叙事**，不符合"先学懂公司/战场/行业，再决策"的人脑认知规律。每层都有自己的碎片问题：

**industry 层（当前 sector 白名单 5 桶）**：
- `VALID_SECTORS = (consumer, saas, cyclical, bank, biotech)` 粒度太粗，与 arena 不对齐
- 新建行业要改代码（白名单硬 coded）
- `industries/{sector}/landscape.md` 走 5 章节固定模板，与行业研报真正的 11 维度（CFA/Porter/Damodaran）不对应
- 每份研报 append 段到 landscape，无法做跨报告字段级聚合（TAM 谁对谁错看不出）

**arena 层（当前 checklist-first）**：
- arena 作为"窄战场"本意是竞争叙事单位，但实现上偏成"按问题 id 组织的答卷"（competence-notes）
- 行业事实被错位挂到单 ticker 名下（`q_power_grid_tam`、`q_policy_subsidies_barriers` 的答案都挂在"太湖远大"公司名下，下次导万马股份需重抄）
- 没有"博弈维度"的叙事入口，用户看 arena 页读到的是一堆独立 q_id 答案

**company 层（当前 claims + profile）**：
- `claims.jsonl` 是原子事实库，交叉验证/检索不可替代，但**唯一的用户阅读入口是"按 subject_tag 分组的 50 条 claim 列表"**
- `profile-YYYY.md` 章节随报告来（稳定事实 / 年度事实 / 业务条线），不是按公司维度组织
- 用户读完 50 条 claim 拼不出公司全貌
- 行业事实被错位塞进公司 claims（BSE_920118 前 5 条 claim 中 4 条是"电网投资 3 万亿"这类行业 TAM，跟太湖远大无关）

### 1.2 核心原则

**ingest 流程和存储设计服务于用户学习体验**，反向驱动。先定三层知识框架（用户阅读入口），数据 schema 和 ingest pipeline 都是这个框架的附属。

三层设计对称：每层有自己固定的维度清单（11 / 6 / 8）、自己的 narrative 文件按维度拆、自己的结构化事实层（observations / claims）、自己的入口页按维度呈现。跨层关联走 backlinks + `arena_refs` 索引字段。

## 2. 三层知识框架

### 2.1 industry（产业全景，11 维度）

产业的客观事实库。理论来源：CFA L1 Industry Analysis + Porter Scope + Damodaran 估值框架。

| # | 维度 | 核心内容 | 数据形态 |
|---|---|---|---|
| 1 | 定义与边界 | 行业做什么、子行业/品类划分、与相邻行业的边界 | narrative |
| 2 | 市场规模与增长 | 全球/分地域 TAM、历史/未来 CAGR、分品类拆解 | structured observations |
| 3 | 生命周期阶段 | Embryonic/Growth/Shakeout/Mature/Decline + 判据 | enum observation + narrative |
| 4 | 产业链分析 | 上/中/下游 + 各环节成本占比 + 议价权分布 | narrative + segment observations |
| 5 | 竞争结构 | Porter 五力 + 集中度 HHI/CR5 + 头部公司市占 | structured observations |
| 6 | 增长驱动与催化 | 技术/需求/政策/宏观；短期 catalysts | narrative |
| 7 | 技术与产品 | 工艺原理、产品品类、技术演进路径、关键指标 | narrative |
| 8 | 监管与政策 | 监管框架、行业标准、补贴/税收、贸易政策、环保合规 | narrative |
| 9 | 关键经营指标基准值 | 行业特有指标 + 优秀/平均/差基线 | structured observations |
| 10 | 主要风险 | 周期/政策/技术替代/客户集中/上游依赖/合规/汇率 | narrative |
| 11 | 投资视角与估值锚 | Damodaran 三元 + 历史 PE/PB/EV 中枢 + 选股逻辑 | narrative + structured observations |

### 2.2 arena（博弈叙事，6 维度）

**arena = 一组参与者围绕某个博弈焦点的竞争叙事单位**，不是行业的细分市场（那是 industry 的 segment）。理论来源：Porter 竞争战略 + Christensen 颠覆理论 + Crossing the Chasm。

**建立前提**：必须有明确的博弈焦点（国产替代 / 技术路线之争 / incumbent 守擂 / 升级破局 / 平台迁移 等）。没有博弈焦点的子市场不建 arena，直接用 industry segment 表达。

| # | 维度 | 核心内容 | 与 industry/company 的区分 |
|---|---|---|---|
| 1 | 战场定义与博弈焦点 | 四维（产品/客户/地理/价位）+ 博弈主题 + 边界条件 | industry 不讲博弈；company 只讲自家 |
| 2 | 参与者与相对位置 | 角色（incumbent/challenger/disruptor）+ 份额（引 industry observation）+ 当前攻守状态 | industry.concentration 是全行业数字；arena 讲相对位置 |
| 3 | 博弈规则与胜负手 | 靠什么取胜（认证/技术/规模/品牌/渠道）+ 当前最关键不确定性 | industry 不做胜负判断，company 讲自家策略 |
| 4 | 演进轨迹与触发事件 | 过去 3-5 年格局如何变 + 未来演进路径 + 触发转向事件 | industry 讲产业生命周期；arena 讲**这场博弈**的弧线 |
| 5 | 多空叙事 | bull（挑战者赢）/ bear（格局不变）/ disruption（第三方颠覆）三元情景 + 证据反证 | 只有 arena 做叙事三分 |
| 6 | 决策启示 | 这场博弈下哪类参与者值得下注 + 什么触发点会改变结论 | industry §11 是产业整体估值锚；arena 讲**这个具体博弈里怎么选边** |

### 2.3 company（单公司画像，8 维度）

单家公司的画像叙事。8 维度。"市场位置/份额"不做独立维度，通过 cross-ref 连 industry.observations (share_by_player) 和 arena.participants 反向呈现。

| # | 维度 | 核心内容 |
|---|---|---|
| 1 | 业务模式 | 做什么生意、收入结构、业务条线、单位经济 / 盈利模型 |
| 2 | 护城河与竞争策略 | 差异化/成本/聚焦来源、可持续性、与对手相对位置 |
| 3 | 增长引擎与未来规划 | 量 / 价 / 新品 / 地理 / M&A 的增长结构分解；3-5 年规划 |
| 4 | 管理层与治理 | 实控人结构、CEO 履历、激励机制、董事会、过往资本配置决策质量 |
| 5 | 财务分析 | 核心指标演进、利润结构、现金流、资本开支与回报 |
| 6 | 关键事件与催化剂 | 短期触发点、里程碑、事件日历（与维度 3 的结构性增长分开） |
| 7 | 风险 | 公司层面风险（业务/财务/治理/特殊） |
| 8 | 估值 | 估值锚、历史 P/E P/B 区间、当前位置 |

### 2.4 三层视角对照

| 层 | 视角 | 维度数 | 核心问题 | 事实库 | 叙事库 |
|---|---|---|---|---|---|
| industry | 产业全景（客观） | 11 | 这个产业有多大、格局如何、往哪走 | observations.jsonl | 11 份 narrative .md |
| arena | 博弈叙事（相对） | 6 | 这个战场谁会赢、为什么 | （无独立事实库，引 industry + company） | 6 份 narrative .md |
| company | 单公司画像 | 8 | 这家公司做什么、护城河在哪、估值几何 | claims.jsonl | 8 份 narrative .md |

三层视角**正交、不重叠**。重叠区的归属原则：
- **纯数字事实** → industry.observations（带 segment / arena_refs 字段精准过滤）
- **公司 × 战场交互事实** → company.claims（带 arena_refs 字段标注关联 arena）
- **跨 ticker 的窄战场规律** → industry.observations（带 arena_refs，视为 arena 相关的产业级 fact）
- **博弈判断/相对位置/多空叙事** → arena narrative（独有）
- **公司内在属性** → company narrative / claims

## 3. 核心设计决策（19 条）

| # | 决策 | 取舍 |
|---|---|---|
| D1 | 三层（industry/arena/company）都作为一等公民，各有固定维度、自己的 narrative 层 | 服务于"用户按维度学习" |
| D2 | **sector 概念完全删除**：`VALID_SECTORS` 白名单 / `app/io/competence.py` / `competence-sector/` 词表 / `competence-check.md.tmpl` / 所有 `companies/*/competence-check.md` 全废 | 用户明确指令。能力圈概念迁出：不再挂 sector，改为基于三层知识框架的"维度覆盖度"（v2 checklist spec 一并做） |
| D3 | industry slug 中粒度，跟随报告主题，**无白名单** | 卖方切分即默认 industry 单位 |
| D4 | **arena = 博弈叙事单位**（非细分市场）。"有博弈焦点才建 arena"，某些 industry 下 0 个 arena | 不与 industry segment 重复；arena 数 ≤ industry 数 |
| D5 | 所有事实库**双模式**：结构化 `observations.jsonl`/`claims.jsonl` + 按维度拆的 `*.md` narrative | 单 jsonl 不可读；单 md 无法做字段级聚合 |
| D6 | 交叉验证 **lazy**：写入不检测冲突，页面层按 field 聚合渲染 spread/outlier | ingest 简单；用户一定会打开页面 |
| D7 | 旧错位数据不迁移，新规则只对新导入生效 | 迁移脚本难写得可靠；历史数据有溯源价值 |
| D8 | ingest 架构统一：**digest-extract subagent（读全文一次，产结构化摘要）+ 主 agent 分拣**。所有 workflow 共用这套 | 关注点分离；subagent 单职责提质；主 agent 可互动审改 |
| D9 | digest 产 `key_facts[]`，每条带 `target_layer` / `dimension_hint` / `arena_refs` 等路由提示；主 agent 分拣 | 主 agent 做业务语义判断，subagent 只做机械抽取 |
| D10 | **v1 去 checklist 设计**：industry + arena checklist 都不在 v1 ingest 流程里抽。arena 现有 checklist.yaml + competence-notes 保留作历史资产，新 ingest 不动 | v2 独立 spec：基于三层知识库反向生成 checklist |
| D11 | `arena_refs: [slug]` 是新增跨层引用字段，出现在 industry.observation 和 company.claim 的 schema 中 | 解决 arena 作为叙事层但"需要的底层事实散在 industry/company"的引证问题 |
| D12 | company meta frontmatter `industry_primary: {5桶}` 字段改名为 `industry_slugs: [list]`，freeform 不卡白名单 | 一家公司可属多 industry；迁移零成本 |
| D13 | 分流识别：文件名关键词 + 预处理扫 ≥2 独立 ticker → AskUser 确认 | 半自动 |
| D14 | ingest 产出时**所有维度都会产 narrative**，但允许**空维度**（报告不覆盖就空段） | 不强行填充；下次 ingest 逐步补齐 |
| D15 | narrative 写入方式：**按 source 分块 append**（每次 ingest 在对应维度 .md 末尾加 `### 来源 {institution} {date}` 段），永不修改/覆盖历史段 | 跨报告比对只能靠按 source 分块；合并精简靠用户手动 |
| D16 | 现有 `profile-YYYY.md` v1 保留过渡：新 ingest 产 8 维度 narrative（主产出），profile-YYYY.md 仍按年度生成（副产出，作为"公司的某年快照"） | 不破坏现有年度快照概念；未来 v3 可能弃 profile 改 narrative 打快照 |
| D17 | arena 现有 definition.md / checklist.yaml / competence-notes.md 保留位置，frontmatter 加 `industry: {slug}` 字段 + 加 `battleground_focus: str` 字段（博弈焦点文本） | 向后兼容；不破坏 cn-power-cable-polymer-material 现有数据 |
| D18 | arena 新增 6 份维度 narrative（§1 definition 不新建，复用现有 definition.md；§2-§6 新建 5 份） | definition.md 扩展为 arena §1 内容 |
| D19 | 阅读视图 v1：数据 backlink + 页面 cross-ref + 按维度渲染 narrative/observation。`/brief/{slug}` 按决策问题聚合视图推 v2 独立 spec | 本次 scope 已经很大；brief 单独评估 |

## 4. 数据模型

### 4.1 三层目录布局

```
industries/{slug}/                  # 产业全景层（新）
├── meta.yaml                       # slug / name / scope / linked_arenas / linked_tickers / created / last_updated
├── observations.jsonl              # 结构化事实（见 §4.2）
├── definition.md                   # §1
├── market-size.md                  # §2
├── lifecycle.md                    # §3
├── value-chain.md                  # §4
├── competition.md                  # §5
├── drivers.md                      # §6
├── technology.md                   # §7
├── regulation.md                   # §8
├── benchmark.md                    # §9
├── risks.md                        # §10
├── valuation.md                    # §11
└── sources/                        # 原研报 PDF 存档

arenas/{slug}/                      # 博弈叙事层（升级）
├── definition.md                   # §1 战场定义与博弈焦点（现有文件扩展；frontmatter 加 industry/battleground_focus 字段）
├── participants.md                 # §2 参与者与相对位置（新）
├── decisive-factors.md             # §3 博弈规则与胜负手（新）
├── trajectory.md                   # §4 演进轨迹与触发事件（新）
├── narratives.md                   # §5 多空叙事（bull/bear/disruption）（新）
├── investment-view.md              # §6 决策启示（新）
├── checklist.yaml                  # 保留（v1 不抽取，v2 重做）
└── competence-notes.md             # 保留（v1 不抽取，v2 重做）

companies/{key}/                    # 单公司画像层（升级）
├── meta.md                         # frontmatter 字段改：industry_primary → industry_slugs: [list]
├── claims.jsonl                    # 原子事实库（schema 加 arena_refs 字段）
├── profile-YYYY.md                 # 保留过渡（v3 可能弃）
├── narratives/                     # 新：按 8 维度
│   ├── business-model.md           # §1 业务模式
│   ├── moat.md                     # §2 护城河与竞争策略
│   ├── growth-engine.md            # §3 增长引擎与未来规划
│   ├── management.md               # §4 管理层与治理
│   ├── financial-profile.md        # §5 财务分析
│   ├── catalysts.md                # §6 关键事件与催化剂
│   ├── risks.md                    # §7 风险
│   └── valuation.md                # §8 估值
└── sources/                        # 原文 PDF
```

**删除**：现有 `industries/{sector}/` 子目录结构（仅 .gitkeep，无用户数据）；`companies/*/competence-check.md`（3 份均为空骨架，已验证）；`controlled-vocab/competence-sector/*.yaml`（5 个）；`templates/competence-check.md.tmpl`。

### 4.2 industry.observations 行 schema

```json
{
  "id": "cmp-material-0001",
  "dimension": "market_size",           // ∈ INDUSTRY_DIMENSIONS（11 闭集）
  "field": "tam_global",                // 开放词表（INDUSTRY_FIELDS 给建议清单）
  "value": 33.8,
  "unit": "usd_bn",
  "timeframe": "2025",
  "time_type": "actual",                // actual | forecast
  "metric_type": "atomic",              // atomic | enum | segment
  "segment": null,                      // 若 segment 型：品类 slurry/pad，或 ticker（表 share_by_player）
  "arena_refs": [],                     // 若与某 arena 博弈直接相关：[arena_slug, ...]
  "source_id": "行研-国金证券-2026-03-10-abc12345",
  "source_file": "...",
  "source_note": "引用 Market Growth Reports",   // 研报引用的更原始数据源
  "confidence": "high",                 // high | medium | low
  "claim_text": "2025 年全球 CMP 抛光液和抛光垫市场规模约 33.8 亿美元",
  "evidence": "...",                    // 原文 quote
  "extracted_by": "claude-opus-4-7",
  "extracted_at": "2026-04-26T..."
}
```

### 4.3 company.claims 行 schema（增量字段）

现有 schema 保持不变（ticker / subject_tag / polarity / claim_type / timeframe / evidence / confidence / source_id / source_file / extracted_by / id / extracted_at / claim_text），**新增**：

```json
{
  // ... 现有字段 ...
  "arena_refs": ["cn-cmp-slurry-domestic-substitution"],  // 新：该 claim 属于哪些博弈战场（可选，默认 []）
  "company_dimension_hint": "moat"     // 新：建议归到哪个 company 维度（∈ COMPANY_DIMENSIONS，用于聚合页渲染）
}
```

`arena_refs` 和 `company_dimension_hint` 都是可选字段，旧 claim 无此字段时视为空列表 / null。

### 4.4 narrative .md 写入格式（所有层通用）

每次 ingest 在对应维度文件末尾**追加段**，格式：

```markdown
### 来源 {institution} {date} (sha8={sha8})
source_id: {source_id}

{要点内容，≤300 字浓缩，必要时 quote 原文}

> {原文 quote 1}
> {原文 quote 2}
```

永不修改/覆盖历史段。多报告 append 后文件变"日志流"是已知代价；用户手动合并精简不在 ingest 流程内。

### 4.5 维度固定清单（config.py）

```python
# app/config.py 新增
INDUSTRY_DIMENSIONS = (
    "definition", "market_size", "lifecycle", "value_chain",
    "competition", "drivers", "technology", "regulation",
    "benchmark", "risks", "valuation",
)

INDUSTRY_FIELDS = {                     # 开放词表，仅建议
    "market_size":  ["tam_global", "tam_china", "tam_by_segment", "cagr_global", "cagr_china"],
    "lifecycle":    ["stage", "stage_evidence"],            # stage enum
    "competition":  ["hhi", "cr5", "cr10", "share_by_player",
                     "porter_entry_barrier", "porter_substitute_threat",
                     "porter_supplier_power", "porter_buyer_power", "porter_rivalry"],
    "benchmark":    ["gross_margin_leader", "gross_margin_avg",
                     "capex_intensity_avg", "rd_ratio_leader"],
    "valuation":    ["pe_ttm_median", "pb_median", "ev_ebitda_median"],
}

ARENA_DIMENSIONS = (                    # snake_case key ↔ kebab-case .md filename
    "definition", "participants", "decisive_factors",
    "trajectory", "narratives", "investment_view",
)

COMPANY_DIMENSIONS = (                  # snake_case key ↔ kebab-case .md filename; 8 dims
    "business_model", "moat", "growth_engine", "management",
    "financial_profile", "catalysts", "risks", "valuation",
)

# 文件路径规则：{layer_dir}/{slug_or_key}/{dim.replace('_','-')}.md
# e.g. company_dim="growth_engine" → companies/{key}/narratives/growth-engine.md
```

### 4.6 跨层引用机制

**backlinks 字段**：
- `industries/{slug}/meta.yaml`: `linked_arenas: [slug, ...]` + `linked_tickers: [{market, ticker, name}, ...]`
- `arenas/{slug}/definition.md` frontmatter: `industry: {slug}` + `battleground_focus: str`（博弈焦点短句）
- `companies/{key}/meta.md` frontmatter: `industry_slugs: [slug, ...]` + `arenas: [slug, ...]`（现有 arenas 字段保留）

**arena_refs 索引字段**：industry.observation 和 company.claim 都携带。让 arena 页能精准过滤出与自己博弈相关的底层事实。

**反查 helpers**：
- `industry_io.find_by_company(ticker, market) -> list[slug]`（扫所有 industry meta.yaml 的 linked_tickers）
- `industry_io.find_by_arena(arena_slug) -> slug`（读 arena.definition.md frontmatter.industry）
- `arena_io.find_by_company(ticker, market)`（现有）
- `arena_io.find_by_industry(industry_slug) -> list[slug]`（新）
- `industry_io.filter_observations_by_arena(slug, arena_slug) -> list[row]`（按 arena_refs 过滤）
- `claims_io.filter_by_arena(arena_slug) -> list[claim]`（扫所有 companies，按 arena_refs 过滤）

### 4.7 财务 line items 扩展（8 → ~40 列）

当前 `app/io/financials.py:21-30` 的 `FINANCIAL_COLUMNS` 只有 8 列（revenue / gross_profit / operating_income / net_income / total_assets / total_equity / operating_cashflow / shares_outstanding），无法支持 DuPont 分解、FCF 计算、营运资本变动、OCF quality 等常见二次分析。本次扩到三表标准 line items，约 40 项。

**新 schema 清单**（`app/config.py` 新增）：

```python
INCOME_STATEMENT_LINES = (
    "revenue", "cost_of_revenue", "gross_profit",
    "selling_expense", "admin_expense", "rd_expense", "other_opex",
    "operating_income",
    "interest_income", "interest_expense", "other_non_operating",
    "pretax_income", "income_tax", "net_income",
    "minority_interest", "net_income_to_parent",
    "eps_basic", "eps_diluted",
)  # 18 项

BALANCE_SHEET_LINES = (
    "cash_and_equivalents", "short_term_investments",
    "accounts_receivable", "inventory", "other_current_assets",
    "total_current_assets",
    "ppe_net", "goodwill", "intangibles", "other_non_current_assets",
    "total_assets",
    "accounts_payable", "short_term_debt", "other_current_liab",
    "total_current_liab",
    "long_term_debt", "other_non_current_liab",
    "total_liab",
    "minority_equity", "total_equity",
)  # 20 项

CASHFLOW_LINES = (
    "net_income_cf", "depreciation_amortization",
    "working_capital_change", "other_operating",
    "operating_cashflow",
    "capex", "other_investing", "investing_cashflow",
    "debt_issued", "debt_repaid", "equity_issued", "dividends",
    "other_financing", "financing_cashflow",
    "fx_effect", "net_change_in_cash",
)  # 16 项

# Total ≈ 54 列（含重复的 net_income / operating_cashflow 锚点），
# 实际 SQLite 列数 ~45（去重 + 去锚）。
```

**命名规则**：snake_case 英文；A 股科目 / US GAAP 的原名通过 `FINANCIAL_ALIAS_MAP` 映射到标准 key。alias map 作为独立 yaml（`controlled-vocab/financial-aliases.yaml`）方便迭代：

```yaml
# controlled-vocab/financial-aliases.yaml (片段)
revenue:
  a_share: [营业收入, 营业总收入]
  us_gaap: [Revenue, Revenues, Net sales, Total revenue]
cost_of_revenue:
  a_share: [营业成本, 营业总成本]  # 注意：A 股"营业总成本"含期间费用，需拆分
  us_gaap: [Cost of revenue, Cost of goods sold, Cost of sales]
# ... 约 40 项 alias
```

**派生指标扩展**（`financials.py` view `ratios`）：
- 现有：gross_margin / net_margin / operating_margin / roe / roa / debt_to_equity
- 新增：asset_turnover / equity_multiplier（DuPont 三因子）、fcf（= OCF − capex）、fcf_margin、ocf_quality（= OCF / net_income）、interest_coverage（= op_income / interest_expense）、current_ratio、quick_ratio、days_inventory、days_receivable、days_payable、cash_conversion_cycle

**缺失处理**：任何 line 缺失 → NULL；ratios view 用 `NULLIF` 守护除零；页面层缺字段显示 `—`。

**迁移策略**：
- 不迁移旧数据。现有 `financials` 表结构 `ALTER TABLE ADD COLUMN` 扩容（SQLite 支持），保留旧 8 列数据；新 ingest 填新列
- 老数据的派生指标只能基于 8 列算（保持现状）；新 ingest 后有完整 40 列的期间才能算 DuPont / FCF 等新指标
- SQL 查询层 `financials` 表统一读（旧期间新列为 NULL，应用层兼容）

### 4.8 研报 figure_contexts（preprocess 产出）

研报图表数据现状全丢（`preprocess_report.py:85-106` 用 PyMuPDF `get_text("text")` 纯文本提取）。本次 v1 做零成本强化：preprocess 识别图表 caption 模式，把 caption + 前后 2 段文本标为 `figure_context`，在 digest prompt 里显式要求关注这类段。

**preprocess JSON 新增字段**：

```json
{
  // ... 现有 meta + sections ...
  "figure_contexts": [
    {
      "id": "fig-001",
      "page": 3,
      "caption": "图表1: 2020-2030 全球 CMP 抛光材料市场规模（亿美元）",
      "surrounding_text": "...如图表1所示，2025 年市场规模 33.8 亿美元，CAGR 9.0%...",
      "section_name": "market_size"
    },
    ...
  ]
}
```

**caption 模式**（正则）：
- 中文：`图表?\s*\d+[:：]`、`表\s*\d+[:：]`、`图\s*\d+[:：]`
- 英文：`(Exhibit|Figure|Chart|Table)\s+\d+[:\.]`

**digest prompt 注入**：加段 "`figure_contexts` 中的 surrounding_text 是作者对图表的文字描述，关键数据常出现在这里（如市场规模、份额占比、时间序列）。优先从 figure_contexts 抽 observations。"

**不做**（v2）：裁图、vision subagent、evidence_figure schema（见 §9）。

## 5. ingest pipelines

### 5.1 统一架构：digest-extract subagent + 主 agent 分拣

所有 4 类报告（行业研报 / 公司年报 / 公司季报 / 公司卖方研报）都走这套架构：

```
[preprocess]  scripts.preprocess_report --type {industry|annual|quarterly|sell-side}
              产出: sections[] + detected_tickers + meta{institution/date/sha8/form}
              + report_abstract_200w（从封面+首页抽）
              + figure_contexts[]（§4.8，图表 caption + 周围 2 段文本）

[1 个 digest subagent]  prompts/digest/{type}-digest.md
              注入: 全文 + figure_contexts[] + 三层维度清单 + 已知 arena 列表（{slug, definition_four_dims, battleground_focus}）
                    + 现有 observations/claims schema + per-type 侧重说明
                    + 财务 line items 字典（年报/季报 type）
              职责: 读全文产结构化摘要，单职责只吐事实，不做写入决策
              输出 JSON: {
                key_facts: [
                  {
                    idx, fact_text, evidence_quote,
                    target_layer: "industry"|"arena"|"company"|"cross",
                    target_refs: {industry_slug?, arena_slug?, ticker?},
                    dimension_hint: str,      // 对应层的维度
                    field_hint?: str,         // 若是结构化数值
                    value_numeric?, unit?, timeframe?, time_type?, segment?,
                    arena_refs: [slug, ...],
                    subject_tag_hint?: str,   // claim 用
                    confidence: "high"|"medium"|"low"
                  }, ...
                ],
                narratives: {
                  industry: { dim → md_block },
                  arena: { arena_slug: { dim → md_block } },
                  company: { ticker: { dim → md_block } }
                },
                proposed_arenas: [             // 若发现报告明确讨论了未在 known_arenas 里的博弈，建议新 arena
                  { tentative_slug, battleground_focus, tentative_participants, parent_industry_slug }
                ]
              }

[主 agent 在对话内]  读 digest，做：
              1. dedup observations（同 field+timeframe+source_id 保留 confidence 最高）
              2. 按 target_layer/dimension_hint 归类到三层的 observation/claim/narrative
              3. 对 proposed_arenas 走 AskUser 确认是否 bootstrap 新 arena
              4. 与用户互动审改 (见 §5.2-5.5 各 workflow 的审阅环节)
              5. 用户批准后写入所有落盘目标
              6. QA checkpoint（现有 ingest_qa warn/gap）
```

**读文次数**：digest subagent 读全文 1 次；主 agent 不读原文（只读 digest）。

**token 估算（Opus 4.7，以 12 页行业研报为基数）**：
- digest subagent：input ~8k（全文 6k + prompt schema 2k），output ~10k（丰富结构化）
- 主 agent：input ~15k（digest 10k + 三层维度清单 + 已有 observations 参考；prompt cache 命中重复段）, output ~5k（写入 draft + 审阅 UI 文本）
- 单份 ingest 总计约 **$0.9-$1.3**（Opus），Sonnet 约 $0.2-$0.3

### 5.2 行业研报 workflow（`workflows/industry-report.md`，新）

```
1. /ingest <pdf>
2. SKILL 分流识别：文件名命中 "行业/深度/industry/sector/strategy"
   或预处理扫出 ≥2 独立 ticker → AskUser: [行业研报 / 公司深度研报 / 取消]
3. preprocess --type industry, 产 sections[] + detected_tickers + report_abstract
4. industry slug 确认:
   - 主 agent 基于报告标题/目录/首段推候选 slug
   - AskUser: [新建候选 / 选择已有 / 改名]
   - 新建 → auto-create industries/{slug}/meta.yaml + 11 份空 narrative .md 骨架
5. 预加载已知 arena 列表 (industry 反查: arena_io.find_by_industry(industry_slug))
6. 派 1 个 digest subagent (prompts/digest/industry-digest.md)，
   注入: 全文 + 三层维度 + 已知 arena 列表 + 要求输出三层分类提示
7. 主 agent 分拣:
   - key_facts[].target_layer == "industry" → 候选 industry observation (+ arena_refs 透传)
                                                或 industry narrative (按 dim)
   - target_layer == "arena" → 分拣到对应 arena narrative (按 arena 6 维度)
   - target_layer == "company" → 候选 per-ticker claim (+ arena_refs)
   - proposed_arenas → AskUser 是否 bootstrap 新 arena (若批准，auto-create arena 6 份骨架 md + definition.md 填入 battleground_focus)
8. 用户审 4 处 (按顺序):
   - industry observations (表格 diff: 新增 N 条)
   - industry narratives (11 维度每维度 md block 预览)
   - arena narratives (每 arena 6 维度预览; 每 arena 独立分页审)
   - per-ticker claims (按 ticker 分段预览)
9. 写入:
   - industries/{slug}/observations.jsonl append
   - industries/{slug}/{dim}.md 末尾 append 块
   - arenas/{slug}/{dim}.md 末尾 append 块 (per linked_arena)
   - industries/{slug}/meta.yaml 更新 linked_arenas/linked_tickers/last_updated
   - arenas/{slug}/definition.md frontmatter 字段更新 (若 new)
   - companies/{ticker}/claims.jsonl append (带 arena_refs)
   - sources/ 归档 PDF
10. QA checkpoint: scripts.ingest_qa warn --write + gap --write
```

source_id 规则：
- industry 写入: `行研-{institution}-{date}-{sha8}`
- arena 写入: 同 id（一份报告的 arena narrative 与 industry narrative 共享 id）
- per-ticker claims: `行研-{institution}-{date}-{sha8}-{ticker}`

### 5.3 公司年报 / 10-K / 半年报 workflow（`workflows/annual-report.md` 改造）

现有 workflow 升级，数据产出增加 **8 维度 company narrative**：

```
1-4. 同现有（识别类型/company key/预处理）
5. 派 1 个 digest subagent (prompts/digest/annual-digest.md)，
   注入: 全文 + company 8 维度 + arena 已关联（若 company.arenas 非空）+ industry 已关联（若 industry_slugs 非空）
6. 主 agent 分拣:
   - key_facts[].target_layer == "company" (主力) → claim + narrative
   - target_layer == "industry" → 候选 "来自公司视角的行业补充" (confidence 标 medium，append 到 industry narrative 对应 dim)
   - target_layer == "arena" → 若公司参与某 arena，append 到该 arena narrative 对应 dim
   - financial_rows → financials.db (现有)
7. 用户审 3 处 + 现有 profile-YYYY.md 审:
   - claims (按 subject_tag 分段)
   - company narratives (8 维度 md block 预览)
   - 可选：industry 补充段 / arena 补充段
   - profile-YYYY.md 年度快照 (现有流程保留)
8. 写入 + QA
```

source_id: `年报-{fiscal_year}-{sha8}`（不变）

### 5.4 公司季报 / 10-Q workflow（`workflows/quarterly-report.md` 改造）

与年报对称但轻量：季报主要补 `financial-profile.md` / `catalysts.md` 两个维度；其他 narrative 维度若无新事实则空。

### 5.5 公司卖方研报 workflow（`workflows/sell-side-note.md` 改造）

原有 workflow 除产 per-ticker claims 外：

- 研报中行业段（前几页"行业简介"）→ 轻量 industry narrative append（标 source_type=sell_side, confidence 偏 medium）
- 研报中博弈段（"竞争格局"/"行业地位"章节）→ 轻量 arena narrative append（若 arena 已存在）
- 研报主体（推荐公司）→ company narrative + claims
- 取消现有 "问 sector" 步骤（D2），改为 "问 industry_slugs"（freeform 多值）

### 5.6 arena bootstrap 机制（任一 workflow 触发）

任一 workflow 的 digest 产出 `proposed_arenas` 非空 → 走 AskUser 机制：

```
检测到报告明确讨论以下博弈焦点，建议新建 arena：
  [ ] tentative_slug: cn-cmp-slurry-domestic-substitution
      battleground_focus: 国产 CMP 抛光液厂商挑战 Dupont/Cabot/Versum 等海外龙头
      tentative_participants: 安集(challenger), Dupont(incumbent), Cabot(incumbent)
      parent_industry_slug: cn-cmp-material
  [ ] ...
```

用户勾选后 auto-create arena 骨架（definition.md frontmatter 填 industry + battleground_focus；participants 表填候选；5 份新 narrative .md 空骨架），后续由本次 ingest 或后续 ingest 逐步填充。

## 6. 阅读视图（v1 cross-ref + 按维度渲染）

### 6.1 页面层布局

| 页面 | 顶部面包屑 | 主体 | 侧边/底部 |
|---|---|---|---|
| `/industries/{slug}` | industry 名 | 11 维度 narrative（按 §顺序展开） + 每维度尾部结构化 observation 表格（若有） | linked_arenas 列表 + linked_tickers 参与者卡片 + 原文 sources |
| `/industries/{slug}/observations` | industry 名 · observations | 所有结构化事实的跨源聚合表格 | 按 dimension 分 tab，spread/outlier 标注 |
| `/arenas/{slug}` | 所属 industry（→）→ arena 名 | 6 维度 narrative（含 §1 definition.md） + 参与者 × 关键指标聚合表（从 industry.observations 按 arena_refs 过滤） | 参与者卡片（→ company 页）+ 相关 claims（按 arena_refs 过滤） |
| `/companies/{key}` | industry_slugs tag（→） + arenas tag（→） | 8 维度 narrative 卡片 + 每卡片底部"支撑证据（N claims）"可展开 | meta + profile-YYYY 快照 + competence-check 链接（v1 仍在，v2 拆） |
| `/companies/{key}/claims` | company 名 · claims | 按 subject_tag 分组的 claim 列表（现状保留） | 过滤器：timeframe / confidence / source_id |

### 6.2 跨源分歧渲染规则（industry 层）

- atomic 数值字段：`table {source | timeframe | value | unit}` + 顶部 `median / range / spread` + `spread > 30%` 显示红色 🚨
- enum 字段：各 source 判断并列；一致 → 🟢；分歧 → 🟡 展开对比
- segment 字段（如 share_by_player）：按 segment 分组，各 segment 内跨源聚合
- narrative .md：默认展开最新段 + 折叠其他；勾选多源做侧边栏对照

### 6.3 arena 页的聚合逻辑

arena narrative 主要靠自己的 6 份 .md。但 §2 participants、§3 decisive-factors 经常需要引证底层事实，通过：

- `industry_io.filter_observations_by_arena(arena.slug)` 拉出 arena_refs 包含本 slug 的 industry observations
- `claims_io.filter_by_arena(arena.slug)` 拉出 arena_refs 包含本 slug 的 company claims（按 participants.tickers 过滤）
- 侧边栏"参与者 × 关键指标"表由这两类数据组装

### 6.4 不在本次 scope（v2 独立 spec）

- `/brief/{slug}` 按决策问题聚合视图（三层事实融合一页摘要）
- 首页决策仪表盘（按公司聚合 arena/industry 未答 checklist + 分歧 + 最新事实）
- industry + arena checklist 基于知识库反向生成

## 7. 代码改动清单

### 7.1 删除

| 路径 | 删除原因 |
|---|---|
| `app/config.VALID_SECTORS` | sector 概念完全废 |
| `app/io/industry.py`（旧） | 重写（slug-based） |
| `app/io/competence.py` | sector 能力圈废 |
| `app/routes/competence.py` | 同上 |
| `controlled-vocab/competence-sector/*.yaml`（5 个） | 同上 |
| `templates/competence-check.md.tmpl` | 同上 |
| `companies/*/competence-check.md`（3 份，均空骨架） | 同上 |
| 所有 `import VALID_SECTORS` 点 | 级联 |

### 7.2 迁移（本次 PR 一次性）

- 3 份 `companies/*/meta.md` frontmatter：`industry_primary: {cyclical|consumer|...}` → `industry_slugs: []`（置空待回填；保留 `arenas: [...]`）
- `app/io/company.py` 移除 sector 白名单分支
- `docs/USER-GUIDE.md` / `docs/DEVELOPER-GUIDE.md` 对应章节改写
- `.claude/skills/ingest/SKILL.md` 支持范围 + 关键资源索引更新
- `.claude/skills/ingest/workflows/sell-side-note.md` Step "问 sector" 改为 "问 industry_slugs"
- 旧 `docs/PLAN-INDUSTRY-INGEST.md` 文件头加 `Status: superseded by specs/2026-04-26-industry-ingest-design.md` 注记

**不做的迁移**（D7）：
- `BSE_920118/claims.jsonl` 前 5 条行业错位 claim 留原地
- `arenas/cn-power-cable-polymer-material/competence-notes.md` 里行业错位答案留原地
- 3 家 `companies/*/profile-YYYY.md` 内容不拆到 narratives/（profile 保留过渡，narratives 由下次 ingest 新填）

### 7.3 新增

**核心 IO 层**：

```
app/io/industry.py            # 重写 slug-based
  list_industries / read_meta / write_meta / bump_meta_linked_*
  read_observations / append_observations / dedup_observations
  filter_observations_by_arena / filter_observations_by_segment
  read_narrative(slug, dim) / append_narrative_block(slug, dim, block, source_meta)
  find_by_company(ticker, market) / find_by_arena(arena_slug)

app/io/arenas.py              # 升级
  read/write definition.md frontmatter 含 industry + battleground_focus
  read_narrative(slug, dim) / append_narrative_block(slug, dim, block, source_meta)  # 6 维度
  (现有 checklist / competence-notes / participants / consolidate_answers 全保留不改)
  find_by_industry(industry_slug) -> list[slug]

app/io/company.py             # 升级
  create_company 不再校验 sector 白名单
  read/write meta.md frontmatter 加 industry_slugs: [list]
  read_narrative(key, dim) / append_narrative_block(key, dim, block, source_meta)  # 8 维度

app/io/claims.py              # 升级
  validate_batch 接受 arena_refs / company_dimension_hint 可选字段
  filter_by_arena(arena_slug) / filter_by_company_dimension(key, dim)

app/io/financials.py          # 升级（§4.7）
  FINANCIAL_COLUMNS: 8 → ~45 列（三表 line items）
  _SCHEMA: financials 表 ALTER ADD COLUMN 扩容；ratios view 扩派生指标
  import_financials_csv: 接受宽表 CSV；未知列警告而非报错
  load_alias_map() -> dict: 读 controlled-vocab/financial-aliases.yaml
  ratios view 增: asset_turnover / equity_multiplier / fcf / fcf_margin /
                  ocf_quality / interest_coverage / current_ratio /
                  quick_ratio / days_{inventory,receivable,payable} / ccc
```

**config**：
- `app/config.INDUSTRY_DIMENSIONS`（闭集 11）
- `app/config.INDUSTRY_FIELDS`（建议词表）
- `app/config.ARENA_DIMENSIONS`（闭集 6）
- `app/config.COMPANY_DIMENSIONS`（闭集 8）
- `app/config.INCOME_STATEMENT_LINES` / `BALANCE_SHEET_LINES` / `CASHFLOW_LINES`（§4.7）
- 删 `VALID_SECTORS`

**受控词表新增**：
- `controlled-vocab/financial-aliases.yaml`（§4.7，A 股 / US GAAP 科目名 → 标准 key）

**routes + templates**：

```
app/routes/industries.py      # 重写 slug 路由
  /industries/ 列表
  /industries/{slug}  主页（11 维度 narrative + observation 表格）
  /industries/{slug}/observations  结构化事实跨源聚合表

app/routes/arenas.py          # 升级
  /arenas/{slug}  主页（6 维度 narrative + 参与者聚合表）
  现有路由（checklist/notes）保留

app/routes/companies.py       # 升级
  /companies/{key}  主页加"8 维度 narrative 卡片"（可展开证据 claims）
  /companies/{key}/claims  现有按 subject_tag 列表保留
  删 sector 相关

app/routes/competence.py      # 整体删

app/templates/industries/*.html  # slug 模板 + observation diff + 维度渲染
app/templates/arenas/*.html      # 6 维度模板 + 参与者聚合
app/templates/companies/*.html   # 8 维度 narrative 卡片 + claims 分组
```

**预处理 + 聚合**：

```
scripts/preprocess_report.py    # 加 --type industry 分支 + detected_tickers
                                # + report_abstract + figure_contexts[]（§4.8）
scripts/ingest_aggregate.py     # 新增
  write_industry_observations(slug, rows)
  write_industry_narrative(slug, dim, block, source_meta)
  write_arena_narrative(arena_slug, dim, block, source_meta)
  write_company_narrative(key, dim, block, source_meta)
  dedup_observations(rows) + validate_schema(row)
```

**ingest skill**：

```
.claude/skills/ingest/
├── SKILL.md                             # 支持范围放开到行业研报 + 三层产出说明
├── workflows/
│   ├── industry-report.md               # 新：§5.2
│   ├── annual-report.md                 # 改造：§5.3 加 narrative 产出
│   ├── quarterly-report.md              # 改造：§5.4
│   └── sell-side-note.md                # 改造：§5.5 删 sector + 加 narrative
├── templates/
│   ├── a-share-industry.yaml            # 新：行业研报剔除规则
│   ├── us-industry.yaml                 # 新
│   ├── a-share-annual.yaml              # 保留
│   └── ... 其他保留
├── prompts/
│   ├── digest/                          # 新目录
│   │   ├── industry-digest.md           # 新
│   │   ├── annual-digest.md             # 新
│   │   ├── quarterly-digest.md          # 新
│   │   └── sell-side-digest.md          # 新
│   ├── arena/                           # 现有保留
│   └── sections/                        # 现有 section 抽取 prompt 保留（兼容 fallback，不是主路径）
├── section-routing.yaml                 # 加 industry-generic 通道
├── source-id-rules.yaml                 # 加 行研- 格式
└── cross-checks.yaml                    # 保留
```

**tests**：

```
tests/test_industry_io.py                # slug CRUD / observations dedup / narrative append / find_by_company / filter_by_arena
tests/test_arenas_narrative.py           # 6 维度 narrative append
tests/test_company_narrative.py          # 8 维度 narrative append
tests/test_digest_schema.py              # digest JSON schema 校验
tests/test_ingest_aggregate_triple.py    # 三层分拣逻辑
tests/test_preprocess_industry.py        # ticker 扫描 + abstract 提取
tests/test_industry_routes.py            # /industries/{slug} 页面渲染 + spread badge
tests/test_arena_aggregation.py          # arena 聚合 view（filter by arena_refs）
```

## 8. 破坏性变更与兼容策略

**破坏性（一次性完成，CI 暴露级联）**：
- `VALID_SECTORS` 从代码完全移除
- `company.meta.industry_primary` 字段迁移（3 份 meta 改写）
- 旧 `app/io/industry.py` API 签名完全变
- `app/routes/competence.py` 删除，URL `/competence/*` 消失
- `industries/{sector}/` 子目录删除（空）

**不破坏**：
- `claims.jsonl` schema 只新增可选字段（arena_refs / company_dimension_hint），旧 claim 可读
- `arenas/{slug}/` 现有文件保留位置（definition.md 扩展 frontmatter 字段不破坏读取）
- `financials.db` / `profile-YYYY.md` / `meta.md`（除 industry_primary 外）不变

**已知遗留**（D7 的代价）：
- `BSE_920118/claims.jsonl` 4 条行业错位 claim、`cn-power-cable-polymer-material/competence-notes.md` 行业错位答案 —— 保留
- 3 家 company 的 `profile-YYYY.md` 内容暂不拆到 narratives/；后续新 ingest 会为这些公司补 narrative，profile 与 narrative 并存

## 9. 不做 / 推后

- ❌ 自动冲突检测（D6：lazy view）
- ❌ industry observation → company claim 自动联动（两个独立事实层）
- ❌ 迁移旧错位数据（D7）
- ❌ industry + arena checklist 基于知识库反向生成（v2 独立 spec）
- ❌ `/brief/{slug}` 聚合视图（v2 独立 spec）
- ❌ 首页决策仪表盘（推后）
- ❌ `profile-YYYY.md` 完全退休（v3 评估）
- ❌ 多份报告间 narrative 自动合并（只按 source 并列；合并靠用户手动）
- ❌ 预测数据进 `actual` 观察序列（用 `time_type=forecast` 区分）
- ❌ 长报告（> 30 页）digest 按 section 二次拆分（首批不需要，遇到再加）
- ❌ Vision-enabled digest（研报图表裁图 + subagent 看图）：推 v2，先用 §4.8 figure_context caption 强化方案跑 v1 样本，看缺口多大
- ❌ observations/claims evidence 支持图片引用（`evidence_figure: {page, bbox, caption}`）：随 vision 一起推 v2
- ❌ 财务附注 / 分部数据 / 季度环比微观数据（现在只抽合并三表 line items，附注表级数据未来再议）

## 10. 测试策略

**Unit**：
- 三层 narrative append 写入格式正确（frontmatter / 来源段头 / quote 块）
- observations dedup（同 field+timeframe+source_id 保留 confidence 最高）
- filter_by_arena 按 arena_refs 精准过滤
- 反查 helpers 正确性
- **财务扩展**（§4.7）：financials ALTER ADD COLUMN 迁移不丢旧数据；新 40 列 CSV 导入；alias map 从 A 股"营业收入"、US "Net sales" 正确映射到 `revenue`；派生指标 view 计算正确（DuPont 三因子 / FCF / OCF quality / CCC 等）
- **figure_contexts 抽取**（§4.8）：preprocess 对 `图表\d+:` / `Figure \d+` 等 caption 正则命中；surrounding_text 取 caption 前后 2 段文本；CMP 样本至少抽出 10+ figure_contexts

**Integration**（端到端 fixture）：
- 用 `~/Downloads/化学机械抛光行业.pdf` 走 industry-report workflow，断言：
  - `industries/cn-cmp-material/` 11 维度 .md + observations.jsonl 生成
  - observations 含 `market_size.tam_global=33.8 @ 2025`、`market_size.tam_china` 同 source 29.6 与 23.0 两条（source_note 分别为"华经"、"弗若斯特沙利文"）
  - `market_size.md` narrative 段含"33.8 亿美元"等要点
  - `proposed_arenas` 至少推出 `cn-cmp-slurry-*` / `cn-cmp-pad-*` 两个候选
  - 若用户 bootstrap 了 `cn-cmp-slurry-domestic-substitution` arena，6 份 .md 生成，definition.md frontmatter 含 battleground_focus
  - 被提及 ≥3 句话的 ticker（安集 / 鼎龙）生成 per-ticker claims 和 narrative，且 claims 不含 `market_size.tam_global` 这类行业级事实
- 用 茅台 2025 年报走 annual-report workflow，断言 `companies/SSE_600519/narratives/*.md` 生成且 8 维度覆盖，claims.jsonl 新增

**Regression**：
- 现有 annual-report / quarterly-report / sell-side-note 的基础行为（claims 产出 + financials 导入）不退化

**UI**：
- `/industries/{slug}` 跨源 spread>30% badge 渲染
- `/arenas/{slug}` 参与者聚合表正确拉出 industry.observations with matching arena_refs

## 11. 未决与 v2 演进

- `/brief/{slug}` 三层融合决策视图（v2 独立 spec）
- industry + arena checklist 基于知识库反向生成机制（v2 独立 spec；现有 arena.checklist.yaml 作 seed）
- field inventory 初版够不够：跑完 3-5 份行业研报后回头复盘，看哪些 dim 需补 structured field
- `profile-YYYY.md` 退休评估（v3 spec）
- 跨 industry 的上下游关系表达（currently 不表达；若需要加 `upstream_industries / downstream_industries` 字段）
- arena 数量增多后的浏览 UX（arena 列表页分类、按 industry 分组）
- digest subagent 对长报告（> 30 页）的分批策略
- **Vision-enabled digest 的 ROI 评估**：v1 跑完 3-5 份行业研报后，统计 figure_contexts 方案抓到多少"图中数据"，剩余多少关键数据仍只在图里。若缺口显著（> 20%），v2 启动 vision 方案（裁图 + multi-modal subagent + `evidence_figure` schema）
- 财务附注级数据（分部数据、分产品收入、存货构成等）的抽取设计（v1 只抽合并三表，附注留给 v2）

## 附录 A · 三层维度速查

| 层 | 维度 | 对应文件 |
|---|---|---|
| industry | 11 | definition / market-size / lifecycle / value-chain / competition / drivers / technology / regulation / benchmark / risks / valuation |
| arena | 6 | definition（现有）/ participants / decisive-factors / trajectory / narratives / investment-view |
| company | 8 | business-model / moat / growth-engine / management / financial-profile / catalysts / risks / valuation |

## 附录 B · CMP 用例端到端跟踪

ingest `~/Downloads/化学机械抛光行业.pdf`（国金证券 2026-03-10，12 页）预期产物：

1. **industry 新建** `industries/cn-cmp-material/`：
   - meta.yaml：linked_tickers 含 `[SSE/688019 安集, SZ/300054 鼎龙, SH/603659 上海新阳, SZ/002088 时代新材]` 等报告明确提及的；linked_arenas 由 Step 7 用户选择决定
   - observations.jsonl：约 20-30 条（tam/cagr 市场规模、Dupont 75% / 头部 6 家 85% 等 concentration、磨料 54.6% 成本占比、CMP 步骤数 vs 制程节点等 benchmark、钴抛光液演进等 technology）
   - 11 份 narrative .md 按维度 append `### 来源 国金证券 2026-03-10`
2. **arena 候选提出**（用户审后决定 bootstrap 哪些）：
   - `cn-cmp-slurry-domestic-substitution`（安集 challenger vs Dupont/Cabot/Versum incumbent）
   - `cn-cmp-pad-dupont-disruption`（Dupont 75% 被 Fujibo/鼎龙挑战）
3. **若 arena 被 bootstrap**：各 6 份 narrative .md 初始化，§2 §3 §4 由本次 digest 填；definition.md frontmatter 含 battleground_focus
4. **公司 narrative + claims**：
   - `companies/SSE_688019/narratives/` 8 维度 md 部分维度有内容（business-model / moat / financial-profile / growth-engine 约 4 维）
   - `companies/SZ_300054/narratives/` 同上
   - 其他被提及 ticker 若证据 <2 句话则不建 narrative，但可入 linked_tickers 列表
   - claims.jsonl per ticker append，带 `arena_refs` 指向相关 arena（若已 bootstrap）

## 附录 C · 废除 sector 级联 grep 清单

```
app/config.py:23                      VALID_SECTORS 定义 (删)
app/io/company.py:11,51,52,162,164    import + sector 校验 (改/删)
app/io/industry.py:all                重写
app/io/competence.py:all              删
app/routes/companies.py:6,51,151      form 下拉去除
app/routes/industries.py:all          slug 路由重写
app/routes/competence.py:all          删
.claude/skills/ingest/SKILL.md:47             关键资源索引更新
.claude/skills/ingest/workflows/sell-side-note.md:38   Step 问 sector 改写
docs/USER-GUIDE.md:63,102,297         章节改写
docs/DEVELOPER-GUIDE.md:123,251,299   同上
docs/PLAN-INDUSTRY-INGEST.md          标 superseded
```

---

**Next step**：用户终审本 spec → 切 `superpowers:writing-plans` 出实施计划。建议 plan 切分：
- Plan 1: 三层数据模型 + IO 层（`app/io/{industry,arenas,company,claims,financials}.py`）+ config + 财务 line items 扩展（§4.7 含 alias map 和 ratios view）+ 迁移 + tests
- Plan 2: preprocess（加 figure_contexts §4.8 + --type industry + detected_tickers + report_abstract）+ digest subagent prompts（四类）+ ingest_aggregate helpers
- Plan 3: 四个 workflow（industry-report / annual-report / quarterly-report / sell-side-note）+ SKILL.md 升级
- Plan 4: routes + templates（三层页面 + cross-ref + 聚合 view + 新派生指标渲染）
- Plan 5: 端到端集成测试 + 清理旧 sector 代码

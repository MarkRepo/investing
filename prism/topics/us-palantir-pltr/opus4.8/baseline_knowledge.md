---
slug: us-palantir-pltr
variant: opus4.8
written_at: 2026-07-17
training_cutoff_estimate: 2025-10
---

# 训练知识 Baseline — Palantir Technologies (PLTR, NASDAQ)

> 本文记录 LLM 在**训练截止时**对该 topic 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。
> ⚠️ 训练截止约 2025-10，当前 2026-07；期间 Q3'25(Nov'25)、Q4'25/FY2025(Feb'26)、Q1'26(May'26) 财报均已发布，所有"快变"财务/估值 fact 大概率已过时，必须 prescan 校准。

## 〇、基本信息

- **主代码**：`US_PLTR`（NASDAQ；2022-11 由 NYSE 转板至 NASDAQ）
- **多市场上市**：单市场（仅美股）
- **市场属性**：美股常规交易 9:30-16:00 ET，无涨跌停；散户持仓比例高、期权活跃、波动大；被纳入 S&P 500 与 NASDAQ-100 后有被动资金托底

## 一、关键事实记忆（26 条）

### 公司与治理（静态/慢变）
- `[fact-01]` Palantir 2003 年由 Peter Thiel、Alex Karp、Stephen Cohen、Joe Lonsdale、Nathan Gettings 创立；CEO 为 Alex Karp（哲学博士，风格特立独行）→ 置信度：高 | time_sensitivity：静态
- `[fact-02]` 2020-09 通过**直接上市(direct listing)** 登陆 NYSE（非传统 IPO）→ 置信度：高 | time_sensitivity：静态
- `[fact-03]` 采用双层/多层股权结构，Thiel/Karp/Cohen 通过 Class F 等超级投票权保持控制 → 置信度：中 | time_sensitivity：慢变
- `[fact-04]` 核心高管：Alex Karp(CEO)、Shyam Sankar(CTO)、David Glazer(CFO)、Ryan Taylor(CRO/首席法务) → 置信度：中 | time_sensitivity：慢变
- `[fact-05]` Peter Thiel(董事长/联创)、Alex Karp 长期通过 10b5-1 计划**持续减持** → 置信度：中 | time_sensitivity：快变 ⚠️

### 产品与业务结构（慢变）
- `[fact-06]` 两大板块：**Government(政府)** + **Commercial(商业)**；各自再分 US / International → 置信度：高 | time_sensitivity：慢变
- `[fact-07]` 四大产品：Gotham(政府/情报/国防)、Foundry(商业数据操作系统)、Apollo(持续部署层)、**AIP(Artificial Intelligence Platform)** → 置信度：高 | time_sensitivity：慢变
- `[fact-08]` **AIP 于 2023-04 发布**，是 LLM 编排/落地层，通过"AIP Bootcamp"快速转化客户，是美国商业增长的核心引擎 → 置信度：高 | time_sensitivity：慢变
- `[fact-09]` 政府板块护城河深（IC/国防长周期合同、认证壁垒、深度嵌入），代表合同含陆军 TITAN、Maven Smart System → 置信度：中 | time_sensitivity：慢变

### 指数纳入（静态里程碑）
- `[fact-10]` 2024-09 纳入 **S&P 500** → 置信度：高 | time_sensitivity：静态
- `[fact-11]` 2024-12 纳入 **NASDAQ-100** → 置信度：高 | time_sensitivity：静态

### 财务（多为快变 ⚠️）
- `[fact-12]` FY2023 营收 ≈ $2.23B → 置信度：高 | time_sensitivity：慢变（历史已定）
- `[fact-13]` FY2024 营收 ≈ $2.87B，同比 ≈ +29% → 置信度：高 | time_sensitivity：慢变（历史已定）
- `[fact-14]` 2024 起 **GAAP 持续盈利**（自 2023 全年首次 GAAP 盈利后转正维持）→ 置信度：高 | time_sensitivity：慢变
- `[fact-15]` **美国商业营收 2024-2025 高速增长**，某些季度同比 >50%~70%；是估值溢价核心叙事 → 置信度：中 | time_sensitivity：快变 ⚠️
- `[fact-16]` FY2025 营收指引被多次上调，全年预计 ≈ $3.9-4.1B 量级（同比 ~35%+）→ 置信度：低 | time_sensitivity：快变 ⚠️
- `[fact-17]` Rule of 40（增速+利润率）远超 40，常被管理层强调达 80+ → 置信度：中 | time_sensitivity：快变 ⚠️
- `[fact-18]` **股价 2024-2025 暴涨**：2024 初约 $16-20 → 2025 年内数倍上涨，成为散户与被动资金追捧标的 → 置信度：中 | time_sensitivity：快变 ⚠️
- `[fact-19]` **估值极端**：2025 年 P/S 常在 ~50-90x、forward P/E ~150-250x，为大盘软件股最贵之一（空头核心）→ 置信度：低 | time_sensitivity：快变 ⚠️
- `[fact-20]` **SBC(股权激励)** 占营收比历史偏高（曾 >20%），稀释与"调整后利润 vs GAAP"差异是空头论据；近年占比下降但仍显著 → 置信度：中 | time_sensitivity：快变 ⚠️
- `[fact-21]` 净收入留存率(NRR)/客户数/美国商业客户数持续改善（Bootcamp 驱动新客）→ 置信度：中 | time_sensitivity：快变 ⚠️
- `[fact-22]` 现金充裕、基本无有息负债，自由现金流为正且利润率高 → 置信度：中 | time_sensitivity：慢变

### 政策/宏观关联（快变）
- `[fact-23]` 2025 Trump 政府"政府效率(DOGE)"叙事：软件整合/去冗余，Palantir 被视为**潜在受益者**（也存在政府预算削减的两面性）→ 置信度：低 | time_sensitivity：快变 ⚠️
- `[fact-24]` 国防"软件定义战争"、Golden Dome 导弹防御等 2025 主题，Palantir 深度参与国防现代化 → 置信度：低 | time_sensitivity：快变 ⚠️
- `[fact-25]` 商业竞争层：Databricks、Snowflake、超大规模云(AWS/Azure/GCP)、C3.ai，以及企业 AI 应用/编排层新进入者 → 置信度：中 | time_sensitivity：慢变
- `[fact-26]` 国际商业（尤其欧洲）增长慢于美国商业，是相对拖累/待观察点 → 置信度：低 | time_sensitivity：快变 ⚠️

**第一节统计**：静态 4 条 / 慢变 10 条 / 快变 12 条。
**快变 + 高/中置信度子集**（最易蒙蔽 thesis，第五节必须逐条 query）：fact-05、15、17、20、21、26（快变+中）；fact-16、18、19、23、24（快变+低，也需校准以定锚）。

## 二、关键人物 / 公司 / 产品

- **Alex Karp（CEO）**：哲学博士，公开发言激进，强调西方价值观/国防/反共识叙事；是散户信仰核心，也是治理争议点。
- **Peter Thiel（董事长/联创）**：硅谷保守派资本，长期减持，政治网络深（与 Trump 政府关联）。
- **Shyam Sankar（CTO）**：技术与政府业务关键推手，公开倡导"软件定义国防"。
- **AIP**：把 Palantir 从"数据集成平台"重定位为"企业 AI 落地/编排层"的产品，Bootcamp 销售模式是增长叙事核心。
- **Gotham / Foundry**：政府与商业两大存量基座，前者护城河深、后者是商业放量载体。

## 三、产业链 / 竞争格局认知

1. **政府/国防**：Palantir 在美国情报界(IC)与国防有深嵌入、认证壁垒和长周期合同护城河，竞争者是 Booz Allen 等集成商、国防主承包商以及"自建"。政府板块稳、可见度高，但增长受预算周期/政治影响，DOGE 是 2025 两面性变量。
2. **商业**：AIP 把 Palantir 推入企业 AI 应用/编排层，与 Databricks/Snowflake（数据平台）、超大规模云（AI 基础设施+应用）、C3.ai（企业 AI 应用）竞争。差异化在"从数据到决策的端到端落地 + Bootcamp 快速验证"。
3. **估值范式**：市场把 PLTR 当"AI 落地纯正标的 + 政府稳态基座"双轮叙事定价，给出软件股极端估值。多空分歧几乎全在"增长可持续性 vs 估值消化速度"。
4. **叙事驱动/散户结构**：高散户+期权+被动资金占比，使股价对叙事与指数事件敏感，基本面兑现节奏与股价常阶段性背离。

## 四、训练知识盲点（自我承认）

- **最新财报**：FY2025 全年实际数、Q4'25、Q1'26 的营收/增速/利润/指引全在训练截止后，训练里的 FY2025 数字是"指引外推"而非实际。
- **当前估值锚**：当前股价、市值、P/S、forward P/E、EV/S 完全不知（fact-18/19 是训练时区间记忆，已大概率过时）。
- **美国商业增速最新读数**：2025H2→2026H1 是否维持高增速、是否见顶回落不知。
- **政府板块 post-DOGE 实况**：DOGE 到底是净利好还是预算削减拖累，2025-2026 政府营收轨迹不知。
- **SBC 与稀释最新占比**：近几个季度 SBC/营收、稀释股数趋势不知。
- **NRR / 客户数 / RPO/TCV bookings 最新值**：留存与在手订单最新读数不知。
- **重大新合同**：2025H2-2026 的国防/商业大单、Warp Speed、国际拓展进展不知。
- **一致预期(consensus)**：卖方对 FY2026/2027 营收/EPS 的一致预期与目标价分布不知。

## 五、需要 web-search 校准的优先项

> 强制：第一节"快变 + 高/中置信"fact 每条至少对应一个 query。

1. `Palantir Q1 2026 earnings revenue growth guidance` — 校准 fact-16/15/17（最新季度实况）
2. `Palantir FY2025 full year revenue US commercial growth results` — 校准 fact-13/15/16（全年实际 vs 指引）
3. `Palantir stock price market cap valuation P/S forward P/E 2026` — 校准 fact-18/19（当前估值锚，thesis 目标价基础）
4. `Palantir US commercial revenue growth rate latest quarter 2026` — 校准 fact-15/21（增长引擎是否维持）
5. `Palantir stock based compensation dilution shares outstanding 2025 2026` — 校准 fact-20（稀释空头论据）
6. `Palantir net dollar retention customer count Q1 2026` — 校准 fact-21（留存/获客）
7. `Palantir government revenue DOGE defense budget 2025 2026 impact` — 校准 fact-23/24（政府板块两面性）
8. `Palantir remaining performance obligations RPO TCV bookings 2026` — 校准在手订单可见度（新增，训练无最新值）
9. `Palantir analyst consensus price target FY2026 FY2027 estimate` — 校准一致预期（A 合同 consensus 必收）
10. `Palantir Peter Thiel Alex Karp insider selling 2025 2026` — 校准 fact-05（内部人减持）
11. `Palantir international commercial revenue Europe growth 2026` — 校准 fact-26（国际拖累）
12. `Palantir new contracts 2025 2026 Army defense commercial Warp Speed` — 校准 fact-24（催化剂/大单）

**质检自检**：第一节快变 12 条，第五节 12 条 query 全覆盖；一致预期/RPO 为训练盲点新增 query。满足"query 数 ≥ 快变+高/中 fact 数"。

## 六、prescan 校准结果（2026-07-17 回写）

> Step 4.5 prescan 入库 29 份 web-search material（14 high + 15 mid，0 丢弃）后，对照第一节 fact-NN 的更新。
> **核心结论：训练 baseline 系统性低估了增长速度——AIP 商业化放量比训练知识强得多，牛市叙事已被强力证实；但股价自 2025 末高点已回调约 31%，估值在压缩。**

### 被推翻（高优先级——thesis_v0 不要再引用原 fact，改 cite 新 mat）

- `[fact-15]` 训练"美国商业增速 >50-70%" → **实际 Q1'26 美国营收 +104% YoY 至 $1.28B，美国商业首破 100% 增长**（TIKR/IR Q1'26 104%）。增速远超训练认知。
- `[fact-16]` 训练"FY2025 ≈ $3.9-4.1B / 同比 ~35%" → **实际 FY2025 ≈ $4.40B；且 Q4'25 增速 +70% YoY、Q3'25 +63%——增速在全年加速而非放缓**（investing.com/IR Q4'25 70%）。FY2026 指引已上调至 **$7.65-7.66B**（2 月初始指引 $7.18-7.20B），隐含 ~+74% 增长。
- `[fact-17]` 训练"Rule of 40 达 80+" → **Q1'26 增速 85% + 调整后运营利润率 ~低 50% → Rule of 40 ≈ 135**，远超训练值（saastr/investing.com）。
- `[fact-18]` 训练"2025 年内数倍上涨" → 确认（$75→$194，+158%），但**2026 已回调**：当前股价 **$133.76**（chartmill，较 2025 末 ~$194 峰值 -31%）。
- `[fact-19]` 训练"P/S ~50-90x / fwd P/E ~150-250x" → **当前市值 $309.97B / TTM 营收 $5.22B → P/S ~59x（TTM）、fwd P/S ~40x（FY26 $7.65B）**。估值仍极端但已从峰值压缩（stockanalysis，S&P Global 数据源，2026-07-06）。
- `[fact-20]` 训练"SBC 稀释显著、股数快速增长" → **稀释大幅放缓：Q1'26 在外股数 2.571B，仅同比 +0.71%**（macrotrends）。净稀释担忧明显缓解——空头核心论据之一被削弱。

### 被验证（可继续引用，置信度提升）

- `[fact-13]` FY2024 ≈ $2.87B → 一致，置信度 高 → 高+
- `[fact-14]` GAAP 持续盈利 → **强验证：Q1'26 净利 $870.5M（$0.34/摊薄股，同比 ~4 倍）；Q3'25 GAAP 净利 $476M（+231%）**（yahoo/investing.com）。
- `[fact-05]` Thiel/Karp 持续减持 → 验证（bloomberg："insiders keep selling after $4B windfall"）。
- `[fact-21]` NRR/客户数改善 → **强验证：Q1'26 NDR 150%**（社媒转述 IR，待正式财报确认口径）。
- `[fact-23/24]` 政府/国防两面性 → **双向验证**：利好侧 **Army $10B 企业协议（2025-07-31，"one of many ELAs"）** + Trump $1.5T 国防预算 + Warp Speed 首批 cohort；风险侧 Forbes "Pentagon prepares for budget cuts" 致股价承压。

### 仍未校准（thesis_v0 引用时标注）

- `[fact-26]` 国际商业（欧洲）增速——本轮 hit 多聚焦美国，国际拆分未拿到硬数字，thesis 标 uncertain，留 02/03 收料。
- RPO/在手订单具体值——hit 提示"RPO exploded"但未拿到精确 $ 与同比，留正式财报/transcript。

### 关键新增事实（训练盲点补上）

- `[new-01]` **Q1'26（2026-05 报）：营收 $1.63B（+85% YoY，2020 直接上市以来最强）；美国营收 +104% 至 $1.28B；净利 $870.5M（$0.34）；FY26 指引上调至 $7.65-7.66B；Q2 指引 ~$1.8B（超 $1.68B 一致预期）；FY26 调整后 FCF 目标上调至 $4.2-4.4B。**
- `[new-02]` **一致预期：39 位分析师均值目标价 $189.65（当前 $133.76，隐含 ~+42% 上行），近 3 月下修 2.08%；评级 Moderate Buy（35 位：19 买/11 持/3 卖/2 强买）；UBS 于 2026-06-16 上调至 Buy。** ← 注意：分析师目标价高于现价，与"估值过高"叙事存在张力。
- `[new-03]` **估值锚（2026-07）：股价 $133.76、市值 $309.97B、在外股数 2.571B、TTM 营收 $5.22B、员工 4,429 人。**

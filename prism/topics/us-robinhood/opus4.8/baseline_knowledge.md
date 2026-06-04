---
slug: us-robinhood
variant: opus4.8
written_at: 2026-06-04T04:15:00+00:00
training_cutoff_estimate: 2026-01
---

# 训练知识 Baseline — Robinhood (HOOD, NASDAQ)

> 本文记录 LLM 在**训练截止时**（自评约 2026-01）对 HOOD 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。
> ⚠️ 训练截止 ~2026-01 → 我大概率知道到 **Q3 2025 业绩（2025-11 披露）**；**Q4 2025/全年（2026-02 披露）与 Q1 2026（2026-04 披露）我不可靠**，是校准重点。

## 〇、基本信息

- **主代码**：`US_HOOD`（NASDAQ，Robinhood Markets, Inc.）
- **多市场上市**：单市场（仅美股 NASDAQ）
- **市场属性**：美东时间 9:30-16:00 常规盘 + 盘前盘后；HOOD 本身主打 24/5 股票交易与 24/7 加密。

## 一、关键事实记忆（28 条）

**业务模式 / 收入结构**
- `[fact-01]` HOOD 三大收入：① transaction-based（PFOF：期权/股票/加密订单流返佣）② net interest revenue（保证金贷款/现金 sweep/证券出借）③ other（Gold 订阅等）。 → 置信度：高 | time_sensitivity：慢变
- `[fact-02]` 交易收入里**期权 > 加密 > 股票**是常态结构，但加密在牛市季度可暴涨成第一。 → 置信度：中 | time_sensitivity：快变 ⚠️
- `[fact-03]` 净利息收入对**联储利率高度敏感**：高利率利好 sweep/保证金利差，但 2024-2025 联储进入降息周期 → NII 单位利差承压，靠余额（AUC/margin book）增长对冲。 → 置信度：中 | time_sensitivity：快变 ⚠️
- `[fact-04]` Gold 订阅 $5/月，权益含更高现金 APY、3% IRA match（Gold）/1%（非 Gold）、更大即时入金、Level II 数据等；Gold 订户数持续增长是 ARPU/other 收入引擎。 → 置信度：中 | time_sensitivity：快变 ⚠️
- `[fact-05]` HOOD **2024 年首次实现全年 GAAP 盈利**；2024 营收约 $2.95B（同比约 +58%），净利约 $1.4B（含递延税资产释放等一次性项）。 → 置信度：中 | time_sensitivity：慢变
- `[fact-06]` ARPU（每用户平均收入）2024-2025 持续回升，靠多产品交叉销售。 → 置信度：中 | time_sensitivity：快变 ⚠️

**产品扩张（2024-2025 大量上新）**
- `[fact-07]` Robinhood Legend：面向活跃交易者的桌面端平台，2024 下半年发布。 → 置信度：中 | time_sensitivity：慢变
- `[fact-08]` 期货交易（Futures）2024-2025 上线，扩 active trader 钱包份额。 → 置信度：中 | time_sensitivity：慢变
- `[fact-09]` 退休金/IRA 业务带 match 激励，AUC（受托资产）快速增长。 → 置信度：中 | time_sensitivity：快变 ⚠️
- `[fact-10]` 2025-03 发布会推出 Robinhood Strategies（管理型组合/类 robo）、Robinhood Banking、Robinhood Cortex（AI 投资助手）。 → 置信度：中 | time_sensitivity：慢变
- `[fact-11]` **预测市场（event contracts）**：2025 年初通过与 Kalshi 合作上线（含赛事/大事件合约），是新兴交易增量。 → 置信度：中 | time_sensitivity：快变 ⚠️

**加密**
- `[fact-12]` 加密是核心波动引擎：自营撮合 + Robinhood Crypto。 → 置信度：高 | time_sensitivity：快变 ⚠️
- `[fact-13]` **收购 Bitstamp**（全球加密交易所，含机构/欧洲牌照），2024 年宣布、2025 年完成交割，是国际化 + 机构化关键拼图。 → 置信度：中 | time_sensitivity：慢变
- `[fact-14]` 收购 WonderFi（加拿大持牌加密平台，2025）扩北美加密版图；另有 X1 信用卡（2023）、Pluto 等小并购。 → 置信度：低 | time_sensitivity：慢变
- `[fact-15]` SEC 2024-05 对 HOOD Crypto 发 Wells notice；我记忆中 **2025 年初 SEC 撤回/关闭了该加密调查（无执法行动）**，与新政府亲加密转向一致。 → 置信度：低 | time_sensitivity：快变 ⚠️（结局不确定，必须校准）

**监管 / PFOF**
- `[fact-16]` PFOF 是 HOOD 核心商业模式命门；Gensler 任内 SEC 推 Order Competition Rule + Reg Best Execution 威胁 PFOF 经济性。 → 置信度：高 | time_sensitivity：慢变
- `[fact-17]` 2025 年新政府（Trump）下 SEC 主席换为 Paul Atkins，监管转向友好；**我判断 Gensler 时代的 PFOF/Order Competition 规则大概率被搁置或撤回**，但具体状态不确定。 → 置信度：低 | time_sensitivity：快变 ⚠️
- `[fact-18]` 加密监管环境 2025 整体大幅转暖（亲加密行政基调、稳定币/市场结构立法推进）。 → 置信度：中 | time_sensitivity：快变 ⚠️

**估值 / 股价**
- `[fact-19]` HOOD 2021-07 IPO 价 $38；2022 熊市最低跌至约 $7；2023-2025 强劲修复。 → 置信度：高 | time_sensitivity：静态
- `[fact-20]` 2025 年 HOOD 股价大涨（加密牛 + 多元化兑现 + 纳入标普500预期/事件），我记忆中年内一度站上 $100+，但**确切区间与年末点位不可靠**。 → 置信度：低 | time_sensitivity：快变 ⚠️
- `[fact-21]` 估值偏贵：PE 处于高位（交易型券商给成长股估值），具体倍数训练时记不准。 → 置信度：低 | time_sensitivity：快变 ⚠️
- `[fact-22]` 市值量级我记忆中 2025 年到 $80-100B+ 区间，uncertain。 → 置信度：uncertain | time_sensitivity：快变 ⚠️
- `[fact-23]` HOOD 持续**回购**股票（管理层资本返还信号）。 → 置信度：低 | time_sensitivity：快变 ⚠️

**竞争格局**
- `[fact-24]` 直接竞品：Charles Schwab（SCHW，全能券商+银行）、Interactive Brokers（IBKR，专业/全球/低成本）、Webull、SoFi、Fidelity；加密侧 Coinbase（COIN）。 → 置信度：高 | time_sensitivity：慢变
- `[fact-25]` HOOD 差异化 = 移动优先 UX + 年轻散户基本盘 + 加密/期权高交易频次 + 多产品捆绑提 ARPU。 → 置信度：高 | time_sensitivity：慢变
- `[fact-26]` IBKR 客户更专业、利息收入占比高、ROE 高；SCHW 体量巨大但有客户现金"sorting"流失隐患（2023 区域行危机时暴露）。 → 置信度：中 | time_sensitivity：慢变
- `[fact-27]` COIN 是加密纯标的，HOOD 加密业务与之正面竞争（Bitstamp flips Robinhood crypto volumes 之类标题暗示量级博弈）。 → 置信度：低 | time_sensitivity：快变 ⚠️
- `[fact-28]` HOOD 用户/AUC 基本盘 2024-2025 持续净流入（funded customers 增长、净存入正向）。 → 置信度：中 | time_sensitivity：快变 ⚠️

**第一节统计**：静态 2 条 / 慢变 11 条 / 快变 15 条。
→ 快变且置信度高/中的子集（fact-02/03/04/06/09/12/18/28 + 部分低置信快变 fact-15/17/20/21/23）是第五节 query 的强制来源——这些最容易蒙蔽 thesis_v0。

## 二、关键人物 / 公司 / 产品

- **Vlad Tenev**（联合创始人 & CEO）：训练时主导多元化叙事（从"meme 散户券商"转"全栈金融超app + 加密 + AI + 预测市场"）。
- **Jason Warnick**（CFO）：训练时在任，主导盈利转正与资本返还。
- **Robinhood Gold**：订阅产品，ARPU/留存核心抓手。
- **Bitstamp**：收购的全球加密交易所，国际+机构跳板。
- **Kalshi**：预测市场合作方（事件合约）。
- **Robinhood Legend / Cortex / Strategies / Banking**：2024-2025 新产品矩阵，目标提客单价、抢高净值与活跃交易者。

## 三、产业链 / 竞争格局认知

主线：HOOD 从"零佣金移动券商（靠 PFOF + meme/加密交易量）"演化为"多收入引擎的零售金融平台"。三条腿——交易（期权/加密/股票/期货/预测市场）、净息（margin/sweep/证券出借）、订阅与服务（Gold/银行/管理组合）。投资判断核心张力 = **交易收入的高 beta 波动性**（随加密/市况起落）vs **净息 + 订阅的"准经常性"基本盘**能否做厚、平滑周期。

竞争位：HOOD 在"年轻散户 + 高频交易品类（期权/加密）"占优；向上撞 SCHW/Fidelity（资产规模、全能服务、信任度）、IBKR（专业/全球/利息效率）；加密侧撞 COIN。HOOD 的护城河是 UX + 网络效应 + 捆绑交叉销售，弱点是收入对市况/加密/利率三重敏感、监管（PFOF）尾部风险、品牌仍带"赌场"标签。

利率维度：2024-2025 降息周期对 NII 单位利差是逆风，但 HOOD 靠 AUC/margin/sweep 余额增长对冲——这是个"价跌量补"的赛跑，是 thesis 关键变量。

## 四、训练知识盲点（自我承认）

- **Q4 2025 / 全年 2025 业绩**（2026-02 披露）我不可靠——营收/净利/ARPU/funded customers/AUC 全要校准。
- **Q1 2026 业绩**（2026-04 披露）完全在训练截止之后，必须靠资料。
- **当前股价 / 市值 / PE / 估值倍数**——我只有模糊量级，确切数字不可用。
- **SEC 加密调查最终结局**（撤回与否、时间）——记忆为"2025 初撤回"但低置信。
- **PFOF / Order Competition Rule 在 Atkins SEC 下的确切状态**（搁置/撤回/仍在）。
- **Bitstamp 交割后整合进度与加密量级**、**预测市场实际交易量与监管（CFTC）状态**。
- **回购规模 / 资本返还政策细节**、**标普500纳入是否落地**。
- **降息路径**对 NII 的实际季度冲击数。

## 五、需要 web-search 校准的优先项

> 强制规则：第一节"快变 + 高/中"fact 必须有对应 query。

1. `Robinhood HOOD Q1 2026 earnings revenue net income ARPU funded customers`（校准 fact-05/06/28，Q1 在截止后）
2. `Robinhood HOOD Q4 2025 full year 2025 results transaction net interest revenue`（校准 fact-05/06，全年）
3. `Robinhood HOOD crypto revenue percentage Q1 2026 trading volume`（fact-02/12/27 加密占比）
4. `Robinhood net interest revenue 2026 rate cut sensitivity NII guidance`（fact-03 利率敏感）
5. `Robinhood Gold subscribers count ARPU 2026`（fact-04 Gold 引擎）
6. `Robinhood stock price HOOD current 2026 market cap PE ratio valuation`（fact-20/21/22 估值）
7. `Robinhood SEC crypto investigation closed Wells notice outcome 2025`（fact-15 调查结局）
8. `PFOF payment for order flow SEC Order Competition Rule status 2025 2026 Atkins`（fact-16/17 监管现状）
9. `Robinhood prediction markets event contracts volume CFTC 2026`（fact-11 预测市场）
10. `Robinhood Bitstamp integration crypto international 2026`（fact-13 整合进度）
11. `Robinhood share buyback repurchase authorization 2025 2026`（fact-23 资本返还）

## 六、prescan 校准结果（2026-06-04 回写）

> Step 4.5 入库 10 份新 web-search（00-prescan-baseline）+ 复用 13 份（2026-05-25, 00-prescan-reuse）后，对照第一节 fact-NN 校准。**权威 Q1/Q4 数字以已注册的 HOOD 10-Q/10-K（materials/sec/）为准，本节 web 数仅作 thesis_v0 定向校准。**

### 被推翻 / 大幅更新（thesis_v0 不要再引用原 fact 的模糊版）
- `[fact-02]` 训练时"加密在牛市季可成第一大交易收入"→ **Q1 2026 加密收入同比 -47%**（qz.com），当前加密是**逆风**不是顺风；交易收入靠期权/期货/预测市场撑。
- `[fact-20/21/22]` 训练时估值"模糊量级、PE 高位、市值 $80-100B+"→ **校准**：股价 ~$76.3（5/21）、市值 ~$68.9B、**PE TTM ~34.6**（已从 2025 末 53.6 压缩 35%，4年均值 50.6）、EPS TTM $2.14、ROE 21.5%、ROIC 8.4%、beta 2.29、52周 +57.5%、FCF $3.0B/年、净现金 $5.66B。市值低于我记忆区间下限。
- `[fact-05/06]` 训练时"2024 营收 $2.95B、净利 $1.4B（含一次性）"→ 补 **Q1 2026 实数**：营收 $1.07B(+15%)、净利 $346M(+3%)、EPS $0.38、净存入 $17.7B(22% 年化)、平台资产 $307B(+39%)、Gold 4.3M(+36%)、opex +18% 至 $656M。
- **CFO 修正**：第二节写的 **Jason Warnick 已卸任，现任 CFO 为 Shiv Verma**（Q1 2026 财报口径）。

### 被验证（可继续引用，置信度提升）
- `[fact-15]` SEC 加密调查 → **确认 2025-02-24 关闭、无执法行动**（law.com / courthousenews）；置信度 低 → **高**。这是 thesis 的重大利好解除。
- `[fact-03]` NII 利率敏感 → **Q1 NII +24% 至 $359M**，验证"降息周期里靠余额增长对冲单位利差"的赛跑逻辑当前仍胜；置信度 中 → 高。
- `[fact-04]` Gold 引擎 → **4.3M 订户 +36%**，验证 ARPU/订阅引擎强劲；中 → 高。
- `[fact-11]` 预测市场 → **Q1 创纪录 88 亿张事件合约**、WSJ 称其推升利润，但"业务波动大"；中 → 高（但波动属性要进 thesis 反方）。
- `[fact-23]` 回购 → **Q1 $250M、董事会授权刷新至 $1.5B**；低 → 高。

### 新增事实（baseline 未记，进 thesis_v0）
- `[new-A]` **Q1 2026 是一次"miss"**：营收与 EPS 双线低于一致预期，财报次日（4/29）股价 **-13.24%**。当前 $76 价位是 post-correction。
- `[new-B]` HOOD **已纳入标普500**；分析师 2026 目标价区间 **$79.79–$164.06**（当前价低于区间下沿）。
- `[new-C]` 管理层称已运营 **11 条业务线、每条年化 ≥$100M**——多元化叙事的量化锚。
- `[new-D]` Guidance：2026 调整后 opex+SBC **$2.7B**；EPS **Q2 $0.45 / Q3 $0.50**；CFO 称 Q2 开局强（4 月股票/期权量为年内最高、月内净存入 ~$5B）。

### 仍未校准（thesis_v0 引用时标 uncertain）
- `[fact-16/17]` PFOF / Order Competition Rule 在 Atkins SEC 下的**确切现状**——prescan 仅拿到规则提案背景（sec.gov/congress），未拿到"已撤回/搁置"的定论。thesis 标 uncertain，列入 todo 深挖。
- funded customers 精确数、ARPU 绝对值、NII 对每 25bp 降息的敏感度 $——留 03 从 10-Q 抽。
- `[fact-13]` Bitstamp 交割后整合进度与加密国际化量级——留 02/03 收料。

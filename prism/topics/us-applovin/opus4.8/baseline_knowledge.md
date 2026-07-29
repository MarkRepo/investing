---
slug: us-applovin
variant: opus4.8
written_at: 2026-07-27
training_cutoff_estimate: 2025-06
---

# 训练知识 Baseline — AppLovin (APP, NASDAQ)

> 本文记录 LLM 在**训练截止时**对该 topic 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。
> ⚠️ APP 是 2024-2025 极端高波动、多空剧烈分歧标的（暴涨 + 空头报告），几乎所有财务/股价/业务节奏 fact 都是**快变**，训练知识极易过时——第五节 query 必须密集校准。

## 〇、基本信息

- **主代码**：`US_APP`（NASDAQ，与 topic.yaml `scope.ticker` 一致）
- **多市场上市**：单市场（仅 NASDAQ）
- **市场属性**：美股常规交易 9:30-16:00 ET；纳入 S&P 500（2024-09）、Nasdaq-100；可融券做空

## 一、关键事实记忆（26 条）

### 公司与业务结构
- `[fact-01]` AppLovin 成立于 2012 年，创始人兼 CEO Adam Foroughi；总部 Palo Alto, CA → 置信度：高 | time_sensitivity：静态
- `[fact-02]` 2021-04 IPO，发行价约 $80/股；上市后一度跌至个位数~$10（2022 熊市）→ 置信度：高 | time_sensitivity：静态
- `[fact-03]` 历史上分两大板块：**Software Platform（软件平台）** 与 **Apps（自有手游组合）**；软件平台是高毛利核心，Apps 是历史遗留的自研/收购游戏工作室 → 置信度：高 | time_sensitivity：慢变
- `[fact-04]` 软件平台核心资产：**AXON**（AI 广告推荐引擎）、**MAX**（广告聚合/中介 mediation）、**Adjust**（归因/measurement，2021 收购）、AppDiscovery（用户获取）→ 置信度：高 | time_sensitivity：慢变

### AXON 与增长引擎
- `[fact-05]` **AXON 2.0** 约 2023 年中推出，是基于机器学习的自学习广告引擎；它是 2023H2 起软件平台收入爆发式增长的主因 → 置信度：高 | time_sensitivity：慢变
- `[fact-06]` AXON 的护城河叙事：自学习模型 + 历史自有 App 海量数据训练，广告 ROAS/eCPM 持续优化，形成数据飞轮 → 置信度：中 | time_sensitivity：慢变
- `[fact-07]` **电商广告（e-commerce）** 试点约 2024Q4 启动，是 TAM 外延的核心增长叙事——从手游广告主扩展到电商/非游戏广告主；2025 年持续 ramp，被视为下一个数量级增长来源 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-08]` CTV（联网电视）广告是另一条外延路径（收购/自建 CTV 库存）→ 置信度：低 | time_sensitivity：**快变** ⚠️

### 财务（训练时记忆，全部快变）
- `[fact-09]` 2024 全年营收约 $4.7B，其中软件平台约 $3.2B、Apps 约 $1.5B → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-10]` 软件平台毛利率极高（~75%+），整体调整后 EBITDA margin 高且快速扩张 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-11]` 2024Q4（2025-02 发布）业绩强劲，软件平台增速仍在高位（同比 >50%）→ 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-12]` 公司持续大额回购股票，自由现金流转化率高 → 置信度：中 | time_sensitivity：**快变** ⚠️

### 股价与估值（快变，极易过时）
- `[fact-13]` 股价从 2023 初~$10 涨到 2024 底~$300+，2025 初一度冲到 $400-500 区间，是标普表现最好的股票之一 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-14]` 市值峰值约 $150-200B 量级（2025 上半年）→ 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-15]` 估值高企：forward P/E 约 40-60x、P/S 极高（软件收入口径）→ 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-16]` 2024-09 纳入 S&P 500 → 置信度：高 | time_sensitivity：静态

### 空头质疑（2025 关键事件）
- `[fact-17]` 2025-02 前后 **Fuzzy Panda Research** 与 **Culper Research** 发布做空报告，指控：违反 Apple/Google 应用商店政策、用误导手段强制下载、"归因造假"（把本会发生的电商销售算作自己功劳）、涉嫌利用/去匿名化 Meta 等平台数据 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-18]` 空头报告后股价大跌但随后反弹；公司发文反驳 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-19]` 存在潜在监管/合规尾部风险（应用商店政策、隐私数据使用、SEC 关注可能）→ 置信度：低 | time_sensitivity：**快变** ⚠️

### 战略动作
- `[fact-20]` 2025 年 AppLovin 计划**剥离/出售 Apps（自有手游）业务**，转型为纯广告平台公司；买家/对价我记忆为 Tripledot Studios，约 $900M 现金 + 股权（细节不确定）→ 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-21]` 剥离 Apps 后，公司叙事变为"纯软件/广告平台"，估值口径与毛利结构会显著改善（去掉低毛利游戏）→ 置信度：中 | time_sensitivity：**快变** ⚠️

### 人物与治理
- `[fact-22]` Adam Foroughi 任 CEO，是核心人物与叙事驱动者；持股比例可观、创始人主导 → 置信度：中 | time_sensitivity：慢变
- `[fact-23]` Herald Chen 曾任 President/CFO（是否仍在任不确定）→ 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-24]` KKR 曾是早期重要投资方（2018 投资）→ 置信度：中 | time_sensitivity：静态

### 竞争格局
- `[fact-25]` 竞争对手：手游广告中介 MAX vs Google AdMob、Unity LevelPlay（ironSource 已并入 Unity）；广义数字广告 vs Meta、Google、The Trade Desk（尤其 CTV/程序化）、Digital Turbine → 置信度：中 | time_sensitivity：慢变
- `[fact-26]` iOS ATT（App Tracking Transparency，2021）曾重创移动广告归因，但 AXON 的建模能力被认为部分对冲了信号损失 → 置信度：中 | time_sensitivity：慢变

**第一节统计**：静态 5 条 / 慢变 7 条 / 快变 14 条。⚠️ 快变占比过半——这是本 topic 的核心风险，第五节 query 必须逐条校准快变 fact。

## 二、关键人物 / 公司 / 产品

- **Adam Foroughi** — 联合创始人兼 CEO，叙事驱动者，主导 AXON+电商+剥离游戏三步棋。
- **Herald Chen** — 曾任 President/CFO（在任状态待校准）。
- **AXON** — AI 广告引擎，公司增长与估值的核心，理解本 topic 必须理解 AXON 的自学习机制。
- **MAX / Adjust / AppDiscovery** — 广告技术栈（聚合/归因/获客）。
- **Fuzzy Panda / Culper Research** — 2025 做空方。
- **Tripledot Studios** — 记忆中的手游业务买家（待校准）。

## 三、产业链 / 竞争格局认知

移动广告技术栈：广告主（游戏/电商）→ DSP/推荐引擎（AXON、AppDiscovery）→ 聚合中介（MAX）→ 供给侧库存（App 内广告位、CTV）→ 归因/measurement（Adjust）。AppLovin 独特之处是**全栈自持 + AI 引擎自动化投放**，让中小广告主也能获得类 Meta/Google 的算法投放效果。

竞争分两层：(1) 手游广告中介层——MAX 与 Google AdMob、Unity LevelPlay 三足鼎立；(2) 广义 performance 广告——若电商外延成功，直接对标 Meta/Google 的效果广告与 The Trade Desk 的程序化/CTV。AXON 的效果（ROAS）是广告主迁移的唯一理由，因此"效果可持续性"是命门。

护城河争议：多头认为是 AI 模型 + 数据飞轮的复合优势；空头认为增长部分来自激进/违规的投放手段和归因夸大，可持续性存疑。iOS ATT 后信号缺失环境下，建模能力谁强谁赢。

## 四、训练知识盲点（自我承认）

- **2025H2 以后的一切**：训练截止约 2025 年中，剥离游戏业务的最终成交与否/对价、电商 ramp 的真实规模、空头事件的后续（监管是否介入、诉讼）我基本不知道。
- **精确财务数字**：季度收入/EBITDA/EPS/指引的准确数值、软件平台增速的最新读数，我只有模糊量级，必须校准。
- **当前估值**：现价、市值、forward P/E、P/S、一致预期——训练记忆几乎不可用，必须实时拉。
- **电商广告的单位经济**：广告主留存、ROAS 兑现、是否从试点转为规模收入——我不清楚。
- **空头指控的实证进展**：应用商店政策处罚、SEC 是否问询、公司自查结果——不知道。
- **剥离游戏交易的会计影响**：口径重述、continuing operations 的收入/利润基数——不知道。
- **CFO/高管变动**、最新股权结构、Foroughi 持股与减持——不确定。

## 五、需要 web-search 校准的优先项

> 强制规则：第一节所有 `快变 + 高/中` fact 必须有对应 query。快变 14 条，下列 query 覆盖之。

1. `AppLovin APP stock price market cap July 2026 current valuation`（fact-13/14 现价市值）
2. `AppLovin forward P/E P/S valuation 2026 analyst consensus`（fact-15 估值锚 + 一致预期）
3. `AppLovin Q1 2026 earnings revenue software platform growth`（fact-09/11 最新季报）
4. `AppLovin 2025 full year revenue software platform advertising results`（fact-09/10/11 年度）
5. `AppLovin e-commerce advertising revenue ramp 2025 2026 update`（fact-07 电商外延实况）
6. `AppLovin sell mobile gaming apps business Tripledot deal closed 2025`（fact-20/21 剥离交易结局）
7. `AppLovin short seller Fuzzy Panda Culper aftermath SEC investigation 2025 2026`（fact-17/18/19 空头后续/监管）
8. `AppLovin AXON 2.0 advertising engine e-commerce performance 2026`（fact-05/06 引擎效果最新）
9. `AppLovin CTV connected TV advertising strategy acquisition 2025 2026`（fact-08 CTV 路径）
10. `AppLovin CFO Herald Chen executive changes 2025 2026`（fact-23 高管在任）
11. `AppLovin analyst price target buy sell rating 2026`（一致目标价 / 评级分布）
12. `AppLovin S&P 500 index inclusion buyback capital allocation 2025`（fact-12/16 回购/资本配置）

## 六、prescan 校准结果（2026-07-27 回写）

> Step 4.5 prescan 入库多份 web-search material + 直取 stockanalysis/marketbeat 后，对照第一节 fact-NN 更新。数据口径日期：股价/估值截至 2026-07-24 收盘（$391.98，盘前 $401）。

### 被推翻（高优先级——thesis_v0 不要再引用原 fact）
- `[fact-15]` 训练时"forward P/E 40-60x、估值透支" → **实际 forward P/E 22.6x、PEG 0.61、forward P/S 15x、EV/EBITDA 27x、P/FCF 30x**（stockanalysis 2026-07-24）。**估值透支的先验被证伪**——对 70%+ 增速 + 80%+ 营业利润率的生意，22.6x forward PE / PEG 0.61 不算贵。估值认知必须重置。
- `[fact-20]` 训练时"Tripledot ~$900M 现金+股权" → **实际 $400M 现金 + ~20% Tripledot 股权，2025Q2 已完成交割**（AppLovin IR + Wall St Engine）。对价数字错，但剥离方向正确且已落地。
- `[fact-14]` 训练时"市值峰值 $150-200B" → 峰值确实更高，但**当前市值已回落至 $131.7B**（股价从 200-DMA $525 / 50-DMA $498 回撤至 ~$392，RSI 31 超卖）。

### 被验证（可继续引用，置信度提升）
- `[fact-09/10/11]` 高增长 + 超高毛利 → **2025A 营收 $5.48B、净利 $3.33B、毛利率 87.86%、FCF $3.94B（vs 2024 $2.07B / 2023 $1.0B）；LTM 营收 $6.16B、净利 $3.96B、EPS $11.64、营业利润率 77%**。Q1'25 广告收入 $1.16B(+71%)、Q2'25 +77%、Q1 2026 总营收 $1.84B。增长与利润兑现被强力验证，置信度 中→高。
- `[fact-21]` 剥离后纯广告平台 → **验证**：毛利率 88%、仅 898 名员工、人均营收 $6.86M，已是纯软件/广告平台结构；S&P 上调评级至 BBB（投资级）。
- `[fact-07]` 电商外延 → **验证并加速**：AXON 2026-06 转自助服务(self-serve)，广告引擎交出 59% 收入增长。电商 ramp 从试点走向规模化，置信度 中→中高。
- `[fact-17/18/19]` 空头质疑 + 监管尾部 → **验证并升级**：出现**已报道的 SEC 调查 + 数据隐私调查**（nypost/Forbes：消息使高管与早期投资人账面损失 $8.65B）；空头曾游说将 APP 剔出 S&P 500（未果，已在指数内）。监管/合规尾部是**真实、活跃**的下行风险，不是稻草人。

### 新增关键事实（baseline 未记录）
- `[new-01]` **2026 年出现广泛的软件/AI 股抛售**（Bloomberg/Reuters/CNBC），拖累 APP 从 ~$525 回撤约 25% 至 ~$392——当前回调部分是 beta（板块）而非纯 alpha（公司）。beta 2.48 极高。
- `[new-02]` 分析师一致预期：**24 家 Moderate Buy（2 强买/17 买/5 持有/0 卖），平均目标价 $668（区间 $340-860），较现价约 +50-70% 空间**（marketbeat 2026-07）。卖方仍显著看多。
- `[new-03]` 下次财报 **2026-08-05 盘后**——thesis 兑现的近端催化。
- `[new-04]` 净现金 -$1.09B（略净负债，$2.76B 现金 vs $3.85B 债务）；账面权益仅 $2.36B（回购致 P/B 55.8）；短仓 3.6% 流通股。

### 仍未校准（thesis_v0 引用时标 uncertain）
- `[fact-08]` CTV 路径的最新进展（未专门搜到实质更新）
- `[fact-23]` CFO/高管在任状态（Herald Chen 是否仍任职未确认）
- 电商广告的单位经济（广告主留存/ROAS 兑现/复投率）——需 03 深挖

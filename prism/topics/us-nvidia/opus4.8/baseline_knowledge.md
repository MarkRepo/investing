---
slug: us-nvidia
variant: opus4.8
written_at: 2026-07-24
training_cutoff_estimate: 2025-01
---

# 训练知识 Baseline — 英伟达 (NVIDIA, US NVDA)

> 本文记录 LLM 在**训练截止时**对该 topic 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。
> ⚠️ 训练截止约 2025-01，今天 2026-07-24，gap ≈ 18 个月——本 topic **快变 fact（业绩/股价/出口管制/新品爬坡/份额）几乎全部需要校准**，训练记忆只作框架与逻辑锚。

## 〇、基本信息

- **主代码**：`US_NVDA`（NASDAQ 上市，与 topic.yaml `scope.ticker` 一致）
- **多市场上市**：单市场（美股 NASDAQ）。无 A/H/ADR 多重上市。
- **财年特殊**：NVIDIA 财年**非自然年**——FY 于**每年 1 月末**结束。故 "FY2025" 指截至 2025-01 的财年，"FY2026" 指截至 2026-01 的财年（约等于自然年 2025 的经营）。所有季度/年度数字必须先分清 FY 口径，避免与自然年混淆（历史最大踩坑点）。
- 交易属性：美股 9:30-16:00 ET，纳指成分/权重股，无涨跌停，期权流动性极高，散户+机构+被动指数集中持有。

## 一、关键事实记忆（约 30 条）

### A. 财务与业绩（多为快变）
- `[fact-01]` FY2025（截至 2025-01）全年营收约 **$130.5B**，同比 FY2024 的 $60.9B 翻倍以上 → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-02]` FY2025 数据中心分部营收约 **$115B**，占总营收约 88% → 置信度：高 | **快变** ⚠️
- `[fact-03]` Q3 FY2025（截至 2024-10）营收约 $35.1B，数据中心约 $30.8B → 置信度：高 | **快变** ⚠️
- `[fact-04]` 整体毛利率约 **73-75%**（Blackwell 初期爬坡阶段毛利率短期承压至 70-72% 区间指引） → 置信度：中 | **快变** ⚠️
- `[fact-05]` FY2026（自然年 2025）营收市场普遍预期 **$180-200B+** 量级，我训练时对全年确切数字 uncertain → 置信度：低 | **快变** ⚠️
- `[fact-06]` 净利率极高（约 50-55%），自由现金流巨大，账上现金充裕，持续大额回购 → 置信度：中 | **慢变**

### B. 产品与技术路线（架构节奏偏慢变，具体爬苗快变）
- `[fact-07]` GPU 架构代际：Ampere(A100)→Hopper(H100/H200)→**Blackwell(B200/B300/GB200/GB300)**→**Rubin**(下一代)。→ 置信度：高 | **慢变**
- `[fact-08]` Blackwell（B200/GB200 NVL72 机柜）于 2024 下半年量产爬坡，2025 全年为放量主力 → 置信度：高 | **快变** ⚠️
- `[fact-09]` Blackwell 早期曾传出机柜级散热/良率/设计 respin 问题致小幅延迟，但已量产出货 → 置信度：中 | **快变** ⚠️
- `[fact-10]` Rubin 架构（+Vera CPU）规划 **2026 年**推出，节奏转为"一年一代"（annual cadence）→ 置信度：中 | **慢变**
- `[fact-11]` CUDA 软件生态是核心护城河——十余年积累的库/框架/开发者锁定，是对手最难复制的部分 → 置信度：高 | **静态**
- `[fact-12]` 网络是第二增长极：收购 Mellanox 后有 InfiniBand + Spectrum-X 以太网 + NVLink/NVSwitch，机柜级互联是 GB200 卖点 → 置信度：高 | **慢变**
- `[fact-13]` 数据中心之外分部：游戏(GeForce RTX 50系 Blackwell)、专业可视化、汽车(DRIVE/Thor)、机器人(Jetson/Isaac)——合计占比 <12% → 置信度：中 | **慢变**

### C. 估值与市值（全快变）
- `[fact-14]` 市值曾突破 **$3T+**，与 Apple/Microsoft 争夺全球市值第一，训练截止前一度接近/超越 $3.3-3.6T → 置信度：中 | **快变** ⚠️
- `[fact-15]` 前瞻 P/E 训练时约 **30-45x** 区间波动，PEG 因高增速而看似不贵 → 置信度：低 | **快变** ⚠️
- `[fact-16]` 2025-01-27 "DeepSeek 时刻"：DeepSeek R1 低成本模型引发算力需求担忧，NVDA 单日暴跌约 **17%**（史上最大单日市值蒸发之一）→ 置信度：高 | **静态**（已发生事件）但对 thesis 有持续含义

### D. 竞争格局（慢变为主）
- `[fact-17]` 直接 GPU 竞争：**AMD** Instinct MI300X→MI325X→MI350/MI400 系列，是唯一具规模的独立挑战者但份额远小 → 置信度：中 | **慢变**
- `[fact-18]` 定制 ASIC 是更大的结构性威胁：Google TPU(v6 Trillium)、Amazon Trainium2/Inferentia、Microsoft Maia、Meta MTIA——超大厂自研以降低对 NVDA 依赖 → 置信度：高 | **慢变**
- `[fact-19]` Broadcom(AVGO)、Marvell 是超大厂定制 ASIC 的主要设计代工方，Broadcom AI 定制芯片收入高速增长 → 置信度：中 | **快变** ⚠️
- `[fact-20]` Intel Gaudi 系列基本掉队，非主要威胁 → 置信度：中 | **慢变**
- `[fact-21]` 台积电(TSMC)是唯一先进制程代工方，CoWoS 先进封装产能是全行业供给瓶颈 → 置信度：高 | **慢变**

### E. 客户与需求侧（快变）
- `[fact-22]` 核心客户高度集中于超大厂：Microsoft、Meta、Amazon、Google、Oracle，加 xAI、CoreWeave 等 neocloud → 置信度：高 | **慢变**
- `[fact-23]` 前几大客户合计占营收比例很高（曾披露少数客户各占 >10%），客户集中度是风险点 → 置信度：中 | **慢变**
- `[fact-24]` 2025 年超大厂 AI capex 指引持续上修（MSFT/META/GOOGL/AMZN 合计年 capex 迈向 $2500-3000亿+），是 NVDA 需求的直接驱动 → 置信度：中 | **快变** ⚠️
- `[fact-25]` 需求可见度：管理层多次称 Blackwell 需求"远超供给"、订单能见度到数个季度后 → 置信度：中 | **快变** ⚠️

### F. 地缘与监管（全快变）
- `[fact-26]` 对华出口管制：H100/A100 早被禁，为中国市场特制降规版 **H20**；训练截止前 H20 仍可售但持续收紧 → 置信度：中 | **快变** ⚠️
- `[fact-27]` 我训练时对 2025 年 H20 是否被进一步限制/是否需许可证/是否计提库存减值 **uncertain**——这是重大待校准项 → 置信度：uncertain | **快变** ⚠️
- `[fact-28]` 中国市场曾占 NVDA 数据中心营收的相当比例（管制前约 20-25%，管制后大幅下降至个位数~低双位数）→ 置信度：低 | **快变** ⚠️

### G. 人物治理
- `[fact-29]` 创始人兼 CEO **黄仁勋(Jensen Huang)** 仍在任，是公司灵魂与技术愿景核心，持股比例可观 → 置信度：高 | **慢变**
- `[fact-30]` CFO Colette Kress；公司无重大治理丑闻，10:1 股票拆分已于 2024-06 完成 → 置信度：中 | **静态**

**第一节时效统计**：静态 3 条（fact-11/16/30）| 慢变 12 条 | **快变 15 条** ⚠️ ——其中"快变+高/中置信"子集（fact-01/02/03/04/08/09/14/19/24/25/26）是第五节优先 query 的强制来源。

## 二、关键人物 / 公司 / 产品

- **黄仁勋 (Jensen Huang)** — 创始人/CEO/技术布道者，皮衣，GTC keynote 定调全行业 AI 叙事。
- **Colette Kress** — CFO，业绩电话会指引口径的权威来源。
- **Blackwell (GB200 NVL72)** — 当前放量主力，机柜级 rack-scale 系统是卖点（把 GPU+CPU+网络整柜卖）。
- **Rubin** — 下一代架构，2026 节奏，决定"一年一代"能否持续。
- **CUDA** — 软件护城河本体。
- **NVLink / Spectrum-X / InfiniBand** — 互联生态。
- **对手阵营**：AMD(Lisa Su, MI 系列)、Broadcom(定制 ASIC 代设计)、Google TPU、Amazon Trainium、台积电(供给命脉)。

## 三、产业链 / 竞争格局认知

1. **上游供给瓶颈**：先进制程只有台积电，**CoWoS 先进封装 + HBM(SK海力士/三星/美光) 是全行业供给天花板**。NVDA 出货节奏受台积电 CoWoS 扩产与 HBM 供给约束，这也是护城河的一部分（对手同样受限，但 NVDA 优先锁产能）。

2. **NVDA 的护城河三层**：①CUDA 软件+开发者生态（最深、最难攻）②机柜级系统整合（GPU+CPU+NVLink+网络，卖整柜而非单卡，抬高单机价值与切换成本）③供应链话语权（优先锁 CoWoS/HBM 产能）。

3. **威胁的两条线**：**(a) 通用 GPU 正面竞争**——AMD 是唯一规模玩家，但软件生态(ROCm)落后、份额个位数，短期难撼动；**(b) 定制 ASIC 迂回**——超大厂为降本+降依赖自研专用芯片（TPU/Trainium/Maia/MTIA），Broadcom/Marvell 代设计。ASIC 在特定推理/训练负载上性价比可胜出，是对 NVDA 份额与毛利的**结构性长期侵蚀**，而非正面替代。关键问题是"通用 GPU vs 专用 ASIC"在推理放量时代的负载占比迁移。

4. **需求侧的脆弱性**：需求高度依赖少数超大厂的 AI capex，而 capex 本身取决于 AI 应用变现能否兑现。若变现证明不了 ROI → capex 拐点 → NVDA 断崖。这是最大的周期性/泡沫风险（DeepSeek 时刻是一次预演）。

5. **利润池位置**：当前 AI 算力价值链的利润几乎全归 NVDA（毛利 75%），这种超额利润天然吸引对手与客户自研分流，长期均值回归压力大——问题是这个"长期"有多长、护城河能撑几代。

## 四、训练知识盲点（自我承认）

- **FY2026 的实际业绩轨迹**（Q1-Q4 FY2026，即自然年 2025 各季）——训练时只有预期，无确切实绩，全部需校准。
- **2025 年对华出口管制的确切演变**：H20 是否被禁/需许可证/库存减值金额/是否有"营收分成换出口"安排——完全 uncertain，重大盲点。
- **当前股价、市值、估值倍数**（快变，训练记忆必过时）。
- **Blackwell 全年放量的实际兑现 vs 早期延迟担忧**的最终结果。
- **超大厂 2025-2026 capex 指引的最新数字**与是否出现任何减速信号。
- **定制 ASIC 2025 年的实际渗透进度**（Broadcom AI 收入、TPU/Trainium 出货占比）——份额侵蚀的真实速度。
- **Rubin 的确切规格/时间表/是否如期**。
- **CoWoS/HBM 供给 2025-2026 的松紧变化**（供给是否仍是瓶颈，还是已缓解）。
- 任何 2025 下半年至今的重大并购/诉讼/反垄断调查（如各国对 NVDA 的反垄断审查进展）。

## 五、需要 web-search 校准的优先项

> 强制规则：第一节所有 `time_sensitivity: 快变 + 高/中置信` 的 fact 必须有对应 query。快变+高/中 = 11 条，以下 query ≥11 条。

1. `NVIDIA FY2026 Q1 Q2 Q3 revenue data center results 2025`（校准 fact-01/02/03/05）
2. `NVIDIA latest quarterly earnings 2025 2026 revenue gross margin guidance`（校准 fact-04/05）
3. `NVIDIA Blackwell GB200 ramp production shipments 2025 status`（校准 fact-08/09）
4. `NVIDIA Rubin architecture launch timeline 2026 Vera CPU specs`（校准 fact-10）
5. `NVIDIA stock price market cap valuation forward PE July 2026`（校准 fact-14/15）
6. `NVIDIA H20 China export restrictions license 2025 charge writedown`（校准 fact-26/27/28）
7. `NVIDIA China data center revenue percentage 2025 export controls impact`（校准 fact-28）
8. `hyperscaler AI capex guidance 2025 2026 Microsoft Meta Amazon Google total`（校准 fact-24）
9. `AMD MI350 MI400 vs NVIDIA market share AI GPU 2025 2026`（校准 fact-17）
10. `Broadcom custom ASIC AI revenue 2025 growth TPU Trainium hyperscaler`（校准 fact-18/19）
11. `NVIDIA Blackwell demand exceeds supply order visibility 2026 backlog`（校准 fact-25）
12. `TSMC CoWoS HBM supply capacity 2025 2026 AI chip bottleneck ease`（校准供给瓶颈盲点）
13. `NVIDIA antitrust investigation regulatory 2025 EU China US probe`（校准治理盲点）

**质检自检**：第一节快变 15 条（其中高/中置信 11 条），第五节 13 条 query 覆盖全部快变+高/中 fact ✓。static/慢变类不再列（框架逻辑用训练知识即可，或走 4.5b 默认模板）。

## 六、prescan 校准结果（2026-07-24 回写）

> Step 4.5a 跑 12 条优先 query，入库 37 份 web-search material（10 high + 28 mid，0 drop）。对照第一节 fact-NN 的更新：

### 被推翻 / 大幅更新（高优先级——thesis_v0 不要再引用原 fact）
- `[fact-01]` 训练"FY2025 全年 $130.5B" → 已进入 **FY2026**：Q4 FY2026(截至 2026-01)单季营收 **$68.1B**（+20% QoQ），FY2026 全年约 **$240B 量级**（Q1~Q4 递增：Q3 数据中心 $51.2B、Q4 数据中心 $62.3B）→ 收入规模比训练记忆翻倍。cite mat-32a09a / mat-f69d2f
- `[fact-02]` 训练"数据中心占 88%" → 现 Q4 FY2026 数据中心 **$62.3B 占 91.5%**（+75% YoY），集中度更高。cite mat-f69d2f
- `[fact-05]` 训练对 FY2026 全年 uncertain → 已实现，远超训练时"$180-200B"预期，约 $240B。cite mat-82c4ed
- `[fact-14]` 训练"市值 $3T+ 争第一" → 仍是全球市值最大公司之一，但**估值倍数大反转**。
- `[fact-15]` 训练"前瞻 PE 30-45x" → **前瞻 PE 已跌到 22-23x（2026-07-23 gurufocus 23.33x / yahoo 22.22x），multiyear low**——即"收入创纪录但估值创多年新低"，市场已把增长兑现打进价格、开始担忧见顶。这是本 thesis 最重要的校准：**NVDA 现在不是"贵估值"叙事，而是"便宜估值 + 见顶担忧"叙事**。cite mat（gurufocus/yahoo valuation）
- `[fact-24]` 训练"超大厂 capex 迈向 $2500-3000亿" → **2026 年 MSFT+AMZN+GOOGL+META 合计 capex $725B，同比 2025 的 $410B 增 77%**——capex 仍在加速而非见顶。cite mat（valueaddvc/statista/cnbc）
- `[fact-26/27/28]` H20 出口管制已明朗：**2025-04 计提 $5.5B H20 库存/采购 charge**（Reuters/CNBC/WSJ 三源确认）；后续 **2025-08 达成"付美政府 15% 中国 AI 芯片销售分成"换取出口许可**的安排。FY2025 中国占营收 **13.1%（$17.1B）**。cite mat（reuters/fool/aicerts）

### 被验证（可继续引用，置信度提升）
- `[fact-08]` Blackwell 放量兑现：GB200/GB300 已大规模出货，Blackwell 月产接近百万 GPU 级别。置信度 高 → 高+
- `[fact-10]` Rubin 节奏验证并**超预期**：**Vera Rubin 已于 2026-05-31 进入"full production"**（比训练时"2026 推出"更快落地量产），"一年一代"cadence 成立。cite mat-fe818a31 相关
- `[fact-17]` AMD 份额验证：**NVDA GPU 份额约 85%，AMD 约 7% 且在增长**——AMD 仍是小挑战者，格局未变。cite mat（fool 85%）
- `[fact-18/19]` 定制 ASIC 威胁验证并加速：**Broadcom AI 收入 Q1 FY2026 $8.4B（+106% YoY），指引 $10.7B**；Broadcom 预计 2027 保持 AI ASIC 设计 ~60% 份额；ASIC 出货量预计 2027 翻三倍。这是**最实质的结构性侵蚀信号**，需在 thesis 重点押注。cite mat（tech-insider/counterpoint/tomshardware）
- `[fact-25]` 需求能见度验证：**订单 backlog $600B~$1T（到 2027），黄仁勋上调订单展望至 $1T 级**——多年周期能见度极强。cite mat（investing/fool backlog）

### 仍未校准 / thesis_v0 引用时标 uncertain
- 供给瓶颈松紧：CoWoS/HBM 仍被称瓶颈但有"不再是瓶颈"的对立说法，未定论 → 标 uncertain
- 毛利率具体最新值：训练"73-75%"，Quartz 称"hovers near 75%"，大方向验证但确切季度值待 03 从财报确认

### 新增（训练盲点补上）
- **中国反垄断**：2025-09 中国监管认定 NVDA 违反反垄断法并继续调查（CNBC/WSJ 确认）——叠加出口管制，中国市场对 NVDA 是"双向夹击"（既被美管制出口、又被中反垄断施压）。cite mat（cnbc/wsj antitrust）

**结论对 thesis 的净影响**：估值叙事发生根本反转（贵→便宜 + 见顶担忧），capex 仍加速（利多），ASIC 侵蚀加速（利空结构），backlog 极强（利多能见度）。多空张力从"估值太贵"转移到"周期见顶 vs 便宜估值"的对决。

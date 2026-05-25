# Thesis v1 — 全球量子计算与量子模拟产业

> 写于：2026-05-23 资料消化后
> 模型：claude-opus-4-7
> 数据基础：13 份 findings（5 份行业研报 + 8 份财报，覆盖 IonQ/Rigetti/D-Wave/QUBT 各 10-K+10-Q、Oxford Instruments 年报+半年报、国盾量子 2024 年报）
> 关键缺口：未覆盖 IBM/Google/Quantinuum/Atom Computing/PsiQuantum 一手材料，仅依赖行业研报转述

---

## 1. 核心 thesis（v1）

> **看空美股纯硬件 SPAC 量子四傻（IONQ/RGTI/QBTS/QUBT）2026 H1-H2 估值；看空"Bluefors/Oxford 量子制冷机 +40% 订单"假设；中性偏看多国产替代（国盾量子+本源）作为 2027-2028 国家资本套利窗口；通用量子优势叙事 2027 前不会落地，量子模拟商业化 2028 后才有第一批可证伪样本。**

**信念强度：7/10**（高于 v0 的 6/10，主要来自 K5 反向证据密度）。内部分化：
- 看空美股四傻 **9/10**（v0 3/10 → 大幅升级，K5 财务证据极硬）
- 看空 Oxford 量子叙事 **7/10**（v0 8/10 看多卖铲人 → 反转，NanoScience 已剥离）
- 看多中国国产替代 **6/10**（v0 未单列，新增结论）
- 量子模拟商业化 **4/10**（v0 6/10 → 下调，BASF/Pfizer/ArcelorMittal 全是客户名单无经济价值案例）
- 通用量子优势 2027 前 **2/10**（v0 隐含 5/10 → 大幅下调，所有标的 Risk Factors 律师层自承 "may never occur"）

---

## 2. 五大 Killer Question 裁决

### K1：2027 前是否出现首例"经济价值量子优势"
**裁决：大概率不命中（命中概率 15-25%）**

**关键证据**：
- **D-Wave**（findings_mat-55d3c2）是 K1 唯一有"已发生"主张的标的：2025-03 Science 论文称在 1200-qubit Advantage2 上做 spin-glass 量子动力学模拟，分钟级完成，Oak Ridge Frontier 需 100 万年。但 10-K **未把这篇论文与任何客户合同/经济价值挂钩**；Jülich $16M 系统销售是否因该突破而买单未披露。
- **D-Wave Q1 2026 收入塌方 -81%**（findings_mat-2e82b4）：若 supremacy 真带来商业拐点，QCaaS 应起飞，但 QCaaS 实际只 +15% 且全年 -18%，反向证据。
- **IonQ 10-K**（findings_mat-032370）Risk Factors 原文：*"No current quantum computers, including our quantum hardware, have reached a broad quantum advantage, and they may never reach such advantage."*
- **Rigetti 10-K**（findings_mat-aa9195）Risk Factors 原文：*"LFTQC may never occur"*；自定义 QA 门槛 1,000+ qubits + 99.9% 双比特，**当前 108Q 仅 99.0%**（差 0.9pp + 10× 比特数）。
- **国盾 2024 年报**（findings_mat-140f68）：量子计算业务仅 ¥5,659 万（+26%），整机在手订单 ¥1.06 亿——规模与"经济价值优势"不在一个量级。

**结论**：spin-glass 模拟是否被业界承认为"useful, real-world problem"是 K1 唯一辩论点。Scott Aaronson 学派与 D-Wave 之间的争论 2026 内不会有共识，**2027 前难以出现"企业付费 $1M+/year"的硬证据**。

### K2：2028 前 ≥1 个 FTQC 系统达 ≥100 逻辑比特、错误率 ≤10⁻⁹
**裁决：大概率不命中（命中概率 10-20%）**

**关键证据**：
- 本批材料覆盖的四家美股纯硬件公司**均无 logical qubit 数披露**：
  - Rigetti 自承 "large-scale fault tolerant phase roughly a decade away"，108Q 99.0% 物理保真度离 100 逻辑比特 + 10⁻⁹ 错误率还有 **5-7 个数量级**
  - IonQ 99.99% 物理两比特门保真度是亮点，但 10-K/10-Q 均不披露 #AQ 或 logical qubit，Oxford Ionics 收购 6 个月后路线图仍沉默
  - D-Wave 是 annealing 路线不参赛；2026-01 收购 Quantum Circuits 后才有 gate-model 入场券，无 logical qubit 数据
  - QUBT 是光量子/熵子路线，完全不在 FTQC 主流赛道
- **未在本批材料覆盖的真正候选**：Google Willow（2024 末跨过 break-even）、IBM Heron/Quantum System Two、Quantinuum H 系列、Atom Computing、PsiQuantum——必须在 thesis_v2 周期补充一手 roadmap 材料。
- 行业研报（信通院、金元证券、华泰、东兴）转述 IBM 2029 ~200 logical qubits 目标——但 IBM 自己的口径**没有承诺逻辑错误率 ≤10⁻⁹**，仅 ≤10⁻³。

**结论**：K2 的两个 AND 条件（≥100 logical qubit **且** ≤10⁻⁹）几乎不可能同时在 2028 前命中。"≥100 logical qubit" 单条件命中概率 30-40%（IBM/Quantinuum 最可能），"≤10⁻⁹" 单条件 2028 前几乎为零。

### K3：Bluefors/Oxford Instruments 量子相关订单 2027 前同比 >40%
**裁决：大概率不命中，且强反向证据已出现（命中概率 20-30%）**

**关键证据**：
- **Oxford Instruments FY2024/25 年报**（findings_mat-9f34e2）：AT segment 整体 +21.3% OCC（含量子+其它），但已签约 **以 £60m 出售 NanoScience（量子稀释制冷机业务）给 Quantum Design International**。
- **Oxford Instruments H1 FY2025/26 半年报**（findings_mat-71e318）：NanoScience H1 收入 **-11.6%、亏损翻倍至 £2.2m**，已重分类为 discontinued operation；UK NSI Act 安全审查已拖 5+ 个月——意味着 Oxford 自家管理层认定量子稀释制冷机**不是核心增长业务**。
- **国盾量子 ez-Q Fridge**（findings_mat-140f68）：突破禁运，2024 量产，意味着 Bluefors/Oxford 在中国市场被分流；Rigetti Quanta 合作（findings_mat-aa9195）把稀释制冷机列为国产替代优先类别——**双向去龙头化**。
- **绝对量仍在增长**（IonQ/Rigetti capex +60-70% YoY），但同比 +40% 的高基数已被 2024 透支，2026-2027 年率难继续。
- **IonQ 离子阱 + QUBT 光子 + D-Wave annealing**：四家美股标的中只有 Rigetti 真正强依赖制冷机；离子阱/中性原子/光量子路线扩张反而压制制冷机长期需求。

**结论**：K3 假设已被反向证据击穿。**Oxford Instruments LSE:OXIG 作为"量子卖铲人"的叙事 2026 内基本破产**。

### K4：≥3 家制药/化工/材料公司公开披露经济价值案例
**裁决：大概率不命中（命中概率 15-20%）**

**关键证据**：
- **D-Wave 10-K**（findings_mat-55d3c2）客户名单包括 BASF、Pfizer、ArcelorMittal、DENSO、Siemens Healthineers、Ford Otosan、Mastercard、Deloitte——但 **10-K 全部以 "have included" 模糊措辞列出，未披露任何一家的合同金额、ROI 或经济价值数字**。
- D-Wave 唯一具体的"经济价值案例"实际是 **国防（Davidson Technologies + Anduril 导弹防御 POC）**，不在 K4 范围内。
- IonQ、Rigetti、QUBT 完全无制药/化工/材料客户案例披露。
- 行业研报（信通院 2025）列出的 PoC 全部停留在"探索性合作"层级，未见任一份"为我们节省了 $X / 缩短了 Y 月"的量化披露。

**结论**：K4 的关键瓶颈不是"是否有客户"，而是**"客户是否愿意公开量化经济价值"**。药企/化工巨头出于竞争原因极少公开量化算法收益，2027 前满足"≥3 家+具体经济价值数字"门槛极难。

### K5：2026 H1 末 IonQ/Rigetti/D-Wave 估值是否崩塌 >50% from peak
**裁决：部分兑现且持续加压（命中概率 60-75%）**

**关键证据矩阵**：

| 标的 | YE2025 关键数据 | Q1 2026 关键边际 | K5 信号强度 |
|---|---|---|---|
| **QUBT** | 营收 $682K、市值 $2.55B、PSR 3,700x；单年增发 86.3M 股（+62%）；3 起证券集体诉讼 | 营收 +9,367% 但 **95% 来自 LSI 并购**；原 QCi 主业仅 $204K；单季现金流出 $480M；AFS 浮亏 $3.8M；AZ Chips 产能闲置 | **9/10**（最弱叙事+最厚现金垫子，崩塌路径是市值多档下调而非破产） |
| **D-Wave** | 营收 $24.6M（+179% 全靠 Jülich 一次性 $16M）；现金 $635M；Customer A 67%；QCaaS -18% | 营收 **-81%**；烧钱率翻倍 $45M/季；$256M 现金 + $282M 股票收购 QCI；商誉 $342M；RPO 仅 $42.4M | **9/10**（收入塌方 + 大额减值风险 + 教科书级催化剂组合） |
| **IonQ** | 营收 $130M（+202%）但 **39% 来自当年并购**；净亏 -$510M；现金 $3.34B；79M private warrant + 25M 激励池新增；2 家客户曾占 77% | GAAP 净利润 +$804.6M **99% 来自 warrant 公允价值**（股价跌的会计幻觉）；真实经营亏损 -$271M（+3.6x）；现金垫子季度 -$245M；SkyWater 收购将再消耗 $1B 现金；Q1 完全无 ATM | **8/10**（最大现金垫 + 最复杂会计噪音；Q2 大概率出现镜像 -$1B 账面亏损） |
| **Rigetti** | 营收 $7.1M（-34%）；毛利率 53%→29%；净亏 -$216M；Customer D 42%；政府 90.2%；现金 $590M（其中 $440M 是 2025 当年融来的）；108Q 实际 99.0%（vs 36Q 99.6%——比特数翻 3 倍保真度退回） | 营收 +199%（C-DAC 印度 $8.4M 订单）但 Customer A 占 54%；**股价 YE25 $22.15 → 3/31/26 $14.04（-36.6%）**；Q1 完全无 ATM；warrant gain $53.7M；roadmap 重做 | **8/10**（股价已部分兑现 K5，剩 60 天若再 -30% 完整命中） |

**K5 综合判断**：
1. **Rigetti 股价已 -36.6%** 在 Q1 阶段——离 -50% 仅一步之遥；H1 剩余 60 天（4-6 月）若任一财报/技术里程碑令市场失望即触发。
2. **IonQ Q2 财报（2026-08 前后）**是最关键观察窗口：若股价回升，warrant 反向 mark-to-market 将产生 ~$1B 账面亏损，对应 headline "IonQ Q2 net loss $1B"，可能触发散户抛售；若股价继续跌，真实经营恶化将被基本面派识破。
3. **D-Wave Q2 财报**：若 RPO 没有显著扩张、Customer A 替换没有顶上，"FY2025 +179%" 的故事彻底破产。
4. **QUBT**：现金垫子最厚但叙事最弱；若 H1 末重启 ATM 或 AFS 浮亏继续扩大，触发估值重估，可能从 PSR 100x 下调至 12-20x（对标传统光子半导体公司），对应市值从 $2.5B 跌至 $300-500M。
5. **四家共振机制**：若任一家先崩，市场会重估其它三家——QUBT 是最可能先崩的标的（基本面最差 + 散户依赖最重）。

**结论**：K5 是本批材料命中度最高的 question。**未来 4-8 周（2026 H1 末）大概率至少有一家完成 -50% 崩塌**。

---

## 3. 支持理由（更新）

1. **四傻基本面 vs 估值的撕裂已被 Q1 数据点实证**：D-Wave 收入塌方、QUBT 原主业归零、Rigetti 收入靠政府且 36Q→108Q 保真度退化、IonQ 39% 营收来自并购且经营烧钱 +3.6x。任何一份 Q2 财报都可能触发市场重估。

2. **Oxford Instruments 主动剥离 NanoScience** 是产业最重要的"内部反向票"：制冷机龙头自己认为这块业务不值得继续持有，远比空头报告有说服力。

3. **国产替代窗口实质性打开**：国盾 ez-Q Fridge 突破禁运 + 中电信 ¥17.75 亿定增成为控股股东，2026-2028 中国国家资本对量子整机的采购具备明确预算（科技部十四五专项 + 中电信集采）；这是为数不多的"政策红利明确 + 估值未透支"组合。

4. **会计噪音失效**：warrant 公允价值变动以前是"亏损放大器"，2025 年开始变成"利润放大器"，市场对这类一次性收益的容忍度正在下降；IonQ Q1 的 +$804M 是测试。

5. **行业研报集体口径**：信通院 2025、金元证券、华泰、东兴四份均指出"2027-2030 才是 NISQ→FTQC 拐点"，把 K1/K2 的合理时间窗口推后至 2030+，与本批财报的"诚实律师叙事"吻合。

---

## 4. 最大反方观点（更新）

1. **散户叙事的非线性**：四傻股价的散户成分（QUBT 尤甚）让"基本面 vs 估值"的均值回归路径可能再延迟 6-12 个月。Reddit/Robinhood 资金不读 10-Q footnotes。如果 2026 H2 出现新的"量子突破"PR（Google Willow 2 / IBM Heron 2），股价可能再次集体翻倍而非崩塌。

2. **D-Wave spin-glass 论文的杠杆**：如果 2026 内有任何 follow-up 论文证明该结果**对应一个真实工业问题**（材料相变、超导体优化、组合优化的工业版本），K1 可能在 2027 前部分命中，D-Wave 估值会率先反弹拉动板块。

3. **IBM / Google 未在本批材料覆盖**：本 thesis 完全依赖 4 家纯量子 SPAC + Oxford + 国盾，缺乏"主流候选"（IBM/Google/Quantinuum/Atom Computing/PsiQuantum）一手数据。若 IBM 2026 年中给出 200 logical qubit demo（如已传闻的 Quantum System Three），K2 命中概率可能从 10% 跳到 30-40%。

4. **国产替代被高估的风险**：国盾 2024 量子计算业务仅 ¥5,659 万、整机在手订单仅 ¥1.06 亿——绝对规模太小，即便订单 +100% 也只是 ¥2 亿级别，对市值（已含十四五预期）的边际影响有限。中电信入主可能带来政策订单，但也可能把公司变成"运营商内部供应商"而非独立成长股。

5. **量子模拟商业化的窗口可能比预期更远**：BASF/Pfizer/ArcelorMittal/DENSO 等大客户在 D-Wave 名单 5+ 年仍无量化案例披露——说明经济价值案例不仅难产，**药企/化工本身的算法收益也可能远低于 NISQ 时代营销话术**。这是 K4 的深层风险。

---

## 5. Position implications（v1 新增）

### 5.1 看空候选（优先级排序）

1. **QUBT（Quantum Computing Inc）**——叙事最弱、PSR 最高、基本面最差、散户依赖最重。崩塌路径：H1 末重启 ATM + AZ Chips 仍无首单 + LSI 整合费超预期 → PSR 重估至 12-20x → 市值 $300-500M（-80% 至 -88%）。但**散户挤压风险高**，应使用 put spread 而非裸卖空。
2. **QBTS（D-Wave）**——Q2 财报是关键催化剂，若 Customer A 继续 contributor < 10% 且 RPO 不增长，"FY2025 高增长" 故事破产。崩塌目标：市值从当前 ~$3-4B 下调至 $1-1.5B（-60%）。
3. **IONQ（IonQ）**——Q2 warrant 反向 mark-to-market 是关键触发；SkyWater $1B 现金支付是另一压力点。崩塌目标：从当前 ~$10B 下调至 $4-5B（-50%）。
4. **RGTI（Rigetti）**——已经 -36.6%，可能剩余空间 -20% 至 -40% 至 -55% 总跌幅。性价比已不如前三者；可作配置但不是首选。
5. **LSE:OXIG（Oxford Instruments）**——量子叙事破产 + NanoScience 剥离不确定性 + AT 整体减速。但公司有传感、半导体、医疗影像等非量子业务支撑，崩塌空间 -15% 至 -25%，作配对交易（vs 国盾）。

### 5.2 看多候选（保守度更高）

1. **国盾量子（SSE:688027）**——中国国产替代 + 中电信入主 + ez-Q Fridge 突破禁运。**仅适合中国 A 股账户**；估值含十四五预期，不便宜，应等 2026-2027 任何系统性回调 -20% 后建仓。
2. **量子模拟 PoC 进展**——非投资标的，但作为信号观察 IBM Quantum Network 客户名单、Quantinuum partnership、各药企 R&D 年报量子章节披露密度。

### 5.3 等待信号（暂不交易）

- **PsiQuantum**（光量子 FTQC 路线，未上市）——若 2026-2027 IPO 是重大事件
- **IBM**——Quantum 业务嵌在大集团内，不是纯标的；观察 2026 Q4 financial briefing 是否给量子板块 segment disclosure
- **Bluefors 母公司**（私有 PE 资产）——无法直接投资，但订单数据是 K3 verdict 的关键

---

## 6. 关键观察窗口（2026 H1-H2）

| 时间 | 事件 | 关键观察 | 对应 K |
|---|---|---|---|
| 2026-06 月底 | H1 收盘股价 | IonQ/Rigetti/QUBT/QBTS 是否 -50% from peak | K5 |
| 2026-07 中 | IonQ Q2 财报 | warrant FV 反向 mark-to-market 是否产生 -$1B 账面亏损；SkyWater 进展 | K5 |
| 2026-08 上 | D-Wave Q2 财报 | RPO 是否扩大；是否有第二台 Advantage2 system delivery | K5、K1 |
| 2026-08 中 | Rigetti Q2 财报 | 108Q GA 后实际 QCaaS ARR；C-DAC 印度 $8.4M 是否入账 | K5、K2 |
| 2026-08 下 | QUBT Q2 财报 | LSI 整合是否稳定；AFS 浮亏；ATM 是否重启 | K5 |
| 2026-09 | IBM Quantum Summit | 是否给出 200 logical qubit demo 或 Quantum System Three 时间表 | K2 |
| 2026 Q4 | 药企/化工年报 R&D 章节 | BASF/Pfizer/ArcelorMittal 是否首次给出量子项目量化收益 | K4 |
| 2026 Q4 | Oxford Instruments 半年报（修正） | NanoScience 处置完成情况；UK NSI Act 审查结果 | K3 |
| 2026 Q4 | 国盾 2026 三季报 | 量子计算业务增速、中电信集采落地、ez-Q Fridge 出货量 | K3 反向（国产替代）、K1 边缘 |

---

## 7. Coverage 闭环（v1）

| Killer Question | 本批材料覆盖度 | v1 verdict | 缺口 |
|---|---|---|---|
| K1（经济价值量子优势 2027 前） | 中（D-Wave 部分主张）| 大概率不命中（15-25%）| 缺 IBM Quantum Network 客户付费数据、Quantinuum 商业案例 |
| K2（FTQC ≥100 逻辑比特 ≤10⁻⁹ 2028 前）| 弱（仅四家纯硬件 SPAC）| 大概率不命中（10-20%）| 缺 IBM/Google/Quantinuum/Atom Computing/PsiQuantum 一手 roadmap |
| K3（制冷机龙头订单 +40%）| 强（Oxford 年报+半年报）| 大概率不命中且反向（20-30%）| 缺 Bluefors 母公司订单数据（私有 PE） |
| K4（≥3 家药企/化工/材料经济价值案例）| 弱（仅 D-Wave 客户名单）| 大概率不命中（15-20%）| 缺各药企/化工年报 R&D 章节 |
| K5（2026 H1 末四傻估值崩塌）| **强（4 家 10-K + 10-Q 全覆盖）** | **部分兑现且持续加压（60-75%）** | 仅缺最新两周股价数据 |

**Coverage 评分：K5 充分（90%），K3 充分（70%），K1/K2/K4 不充分（30-50%）**。

---

## 8. Thesis v2 触发条件

以下任一发生时需要起 thesis_v2：
1. 任一美股纯硬件标的（IONQ/RGTI/QBTS/QUBT）-50% 完成 → K5 兑现，需重新评估"是否还有下行空间"
2. IBM 或 Google 公开发布 ≥100 logical qubit + ≤10⁻⁶ 错误率 demo → K2 重大边际变化
3. D-Wave 或 IBM 公布"客户付费 ≥$1M/year 解决经典做不到的问题"的具名案例 → K1 重大边际变化
4. 任一药企/化工/材料公司年报披露量化经济价值案例 → K4 重大边际变化
5. Oxford Instruments NanoScience 出售失败（UK NSI Act 否决）→ K3 局部反转
6. 国盾量子或本源量子完成重大订单/IPO 事件 → 国产替代 thesis 升级

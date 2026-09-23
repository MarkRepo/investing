---
slug: us-moderna-mrna
variant: opus4.8
written_at: 2026-08-25T14:03:26Z
training_cutoff_estimate: 2025-01
---

# 训练知识 Baseline — Moderna (MRNA, NASDAQ)

> 本文记录 LLM 在**训练截止时**（约 2025-01）对 Moderna 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。训练 vs 今天(2026-08)差 ≥18 月，"快变"类 fact 大概率已过时。

## 〇、基本信息（company）

- **主代码**：`US_MRNA`（NASDAQ，单市场上市）
- **多市场上市**：单市场（无 ADR / 双重上市）
- **总部**：Cambridge, MA｜**CEO**：Stéphane Bancel｜**President**：Stephen Hoge｜**CFO**：Jamey Mock（训练时）
- 市场属性：美股常规时段，无陆股通/南向；生物科技波动极高、事件驱动（临床读出/FDA/指南）

## 一、关键事实记忆（26 条）

**COVID 断崖 & 财务**
- `[fact-01]` Spikevax(mRNA-1273) COVID 疫苗峰值营收 2021≈$17.7B、2022≈$18.4B → 置信度：高 | time_sensitivity：静态（历史）
- `[fact-02]` COVID 营收断崖：2023≈$6.7B、2024 指引一路下修到≈$3.0-3.5B → 置信度：中 | **快变** ⚠️
- `[fact-03]` 2025 营收指引（2024-09 R&D Day 给出）≈$1.5-2.5B，大幅低于市场预期、当日重挫 → 置信度：中 | **快变** ⚠️
- `[fact-04]` 现金+投资 2023 年末≈$13B、2024 一路消耗（训练时约 $9B 量级，不确定）→ 置信度：低 | **快变** ⚠️
- `[fact-05]` 公司宣布成本削减：目标 2027 前削 opex ~$1.1B；盈亏平衡从 2026 推迟到 2028 → 置信度：中 | **快变** ⚠️
- `[fact-06]` 2024 全年营收≈$3.2B、录得净亏损 → 置信度：低 | **快变** ⚠️
- `[fact-07]` 年 R&D 支出量级≈$4.0-4.8B（高研发烧钱是现金消耗主因）→ 置信度：中 | 慢变

**呼吸道特许经营（近端收入基）**
- `[fact-08]` mRESVIA(mRNA-1345) RSV 疫苗（60+ 成人）FDA 2024-05 获批，第三个 RSV 疫苗（落后 GSK Arexvy / Pfizer Abrysvo）→ 置信度：高 | 慢变（批准）
- `[fact-09]` 2024-06 ACIP 收窄 RSV 推荐（75+ 全体、60-74 仅高危），压制整个 RSV 品类需求 → 置信度：中 | **快变** ⚠️
- `[fact-10]` mRNA-1010 季节性流感疫苗 P3：早期一次读出 A 型达标/B 型不足，2024 更新 P3 转阳 → 置信度：中 | **快变** ⚠️
- `[fact-11]` mRNA-1083（流感+COVID 组合）P3 2024-06 公布阳性结果 → 置信度：中 | **快变** ⚠️
- `[fact-12]` BARDA 授予 H5N1 禽流感 mRNA-1018 约 $176M（2024）→ 置信度：中 | **快变** ⚠️

**肿瘤期权（皇冠上的明珠）**
- `[fact-13]` INT 个体化新抗原疗法 mRNA-4157/V940 与 Merck 合作；Merck 2022-10 行权、成本 50/50 分摊 → 置信度：高 | 静态
- `[fact-14]` INT+Keytruda 黑色素瘤（辅助）Phase 2b(KEYNOTE-942)：相较单药 Keytruda 复发/死亡风险降低约 44-49% → 置信度：高 | 静态（已读出）
- `[fact-15]` INT Phase 3：黑色素瘤(V940-001)、NSCLC(V940-002)进行中，读出在训练之后 → 置信度：中 | **快变** ⚠️

**其他管线**
- `[fact-16]` CMV 疫苗 mRNA-1647 P3(CMVictory)进行中，读出待公布 → 置信度：中 | **快变** ⚠️
- `[fact-17]` 诺如病毒 mRNA-1403：疑似 2024 末/2025 因 Guillain-Barré 个案被 FDA clinical hold（训练末期，记忆模糊）→ 置信度：uncertain | **快变** ⚠️
- `[fact-18]` 罕见病：丙酸血症 mRNA-3927、甲基丙二酸血症 mRNA-3705（早期）→ 置信度：中 | 慢变
- `[fact-19]` 平台在研管线曾宣称"到 2025 有多达 10 个产品获批"的目标（后收缩）→ 置信度：低 | **快变** ⚠️

**估值 / 股价 / 竞争**
- `[fact-20]` 股价 2021-08 峰值≈$484，2023-2024 跌至 $40-100 区间，训练末期约 $40 附近 → 置信度：低 | **快变** ⚠️
- `[fact-21]` 竞争：Pfizer/BioNTech（COVID+流感组合竞速）、GSK Arexvy / Pfizer Abrysvo（RSV 在位领先）、Novavax → 置信度：高 | 慢变
- `[fact-22]` mRNA 平台估值逻辑：COVID 现金牛递减 + 呼吸道近端基 + 肿瘤/罕见病远期期权 → 置信度：中 | 慢变
- `[fact-23]` 商业模式：疫苗为主（季节性、政府/私付混合），肿瘤为潜在放量拐点 → 置信度：高 | 静态
- `[fact-24]` mRNA 技术机制：脂质纳米颗粒(LNP)递送编码抗原的 mRNA，诱导免疫应答 → 置信度：高 | 静态
- `[fact-25]` 个体化新抗原(INT)机制：测序肿瘤突变→定制编码新抗原 mRNA→联合 PD-1 放大 T 细胞应答 → 置信度：高 | 静态
- `[fact-26]` 公司持有大量现金但无债务负担为主；靠现金垫过 COVID 断崖到管线放量是核心生存赌注 → 置信度：中 | 慢变

**统计**：静态 8 条 / 慢变 6 条 / 快变 12 条。**"快变+高/中置信"子集**（fact-02/03/05/06/09/10/11/12/15/16）= 第五节强制 query 来源。

## 二、关键人物 / 公司 / 产品

- **Stéphane Bancel**（CEO，长期掌舵，激进押注 mRNA 平台）
- **Stephen Hoge**（President，研发/平台负责人）｜**Jamey Mock**（CFO，训练时）
- **Merck**：INT 肿瘤合作方，50/50 分摊，决定肿瘤期权能否兑现的关键伙伴
- **产品线**：Spikevax（COVID，现金牛递减）、mRESVIA（RSV，已上市）、mRNA-1010（流感，P3）、mRNA-1083（流感+COVID 组合）、mRNA-1647（CMV）、mRNA-4157/V940（INT 肿瘤，与 Merck）

## 三、产业链 / 竞争格局认知

Moderna 是纯 mRNA 平台公司，商业模式由三层构成：① COVID 现金牛（Spikevax）——正快速递减，是"融化的冰块"；② 呼吸道特许经营（RSV mRESVIA + 流感 mRNA-1010 + 流感/COVID 组合 mRNA-1083）——近端收入基，但 RSV 品类受 2024 ACIP 收窄推荐重挫、流感/组合尚待获批放量；③ 远期期权（INT 肿瘤 + CMV + 罕见病）——INT 是最大价值兑现点，成败取决于 Phase 3 读出与 Merck 协同。

竞争格局：COVID+流感组合与 Pfizer/BioNTech 直接竞速；RSV 市场 GSK(Arexvy)、Pfizer(Abrysvo) 在位领先且已抢占先发；肿瘤 INT 领域 Moderna+Merck 在个体化新抗原方向领先但面临 BioNTech 等 mRNA 肿瘤玩家。核心生存命题：高研发烧钱 + COVID 断崖下，现金跑道能否撑到呼吸道放量 + 肿瘤兑现。

## 四、训练知识盲点（自我承认）

- **2025-2026 实际业绩**：真实营收 vs 指引、真实现金余额与消耗速度、最新现金跑道测算——训练时只有 2024 指引，全不知实际兑现
- **关键临床读出（训练后）**：INT Phase 3 黑色素瘤/NSCLC 结果、流感 mRNA-1010 是否获批、流感+COVID 组合 mRNA-1083 审批进展、CMV mRNA-1647 P3 读出
- **管线重排/停摆**：诺如 clinical hold 是否解除、是否有新的管线砍单/优先级重排、进一步成本削减
- **最新股价/估值**：训练末期约 $40，2025-2026 走势与当前市值/估值倍数完全不知
- **指引修订史**：2025/2026 指引是否再度下修、盈亏平衡时点是否再推迟
- **RSV 标签/推荐**：mRESVIA 是否扩龄（50-59）、ACIP 推荐是否变化影响放量

## 五、需要 web-search 校准的优先项

**强制规则**：第一节所有"快变+高/中置信"fact 必须有对应 query。以下 10 条精准可执行 query（4.5a 逐条跑入库）：

1. `Moderna 2025 full year revenue actual vs guidance product sales` （校准 fact-02/03/06）
2. `Moderna cash and investments balance late 2025 2026 cash runway breakeven` （校准 fact-04/05）
3. `Moderna INT mRNA-4157 V940 Phase 3 melanoma NSCLC readout 2025 2026 results` （校准 fact-15）
4. `Moderna mRNA-1010 seasonal flu vaccine FDA approval status 2025 2026` （校准 fact-10）
5. `Moderna mRNA-1083 flu COVID combination vaccine FDA decision 2025 2026` （校准 fact-11）
6. `Moderna mRESVIA RSV vaccine 2025 sales uptake ACIP recommendation age expansion` （校准 fact-08/09）
7. `Moderna CMV vaccine mRNA-1647 Phase 3 CMVictory readout results 2025` （校准 fact-16）
8. `Moderna 2026 revenue guidance cost cuts R&D reprioritization pipeline` （校准 fact-05/19）
9. `Moderna stock price 2026 market cap valuation analyst rating` （校准 fact-20）
10. `Moderna norovirus mRNA-1403 clinical hold Guillain-Barre FDA 2025 status` （校准 fact-17）

**质检自检**：第一节快变+高/中 = 10 条；第五节 query = 10 条，逐一对应 ✓。

## 六、prescan 校准结果回写（4.5c · prescan_status=partial 5/10）

> 2026-08-25 跑 5 条宽 query（adapter 今日耗尽 → native WebSearch fallback），入库 11 份 mid。以下按 fact-NN 逐条对齐最新现实。**标"被推翻"的 fact 在 thesis_v0 里禁止继续 cite 原记忆，须 cite 新入库 web mat。**

### 被推翻 / 重大更新（训练知识已过时，必用新 mat）
- `[fact-15]` INT P3 **待读出** → **已成功**：2026-08-19 INTerpath-001（辅助黑色素瘤 1137 例）RFS+DMFS 双达标，全球首个个体化新抗原/mRNA 肿瘤疗法 P3 首胜，最早 2027 获批。**这是 thesis 级事件**——训练知识里的"期权待验证"已兑现。
- `[fact-20]` 股价 **~$40** → **~$139-151**：8/19 +177% 至 $174.38，8/20 -24%，8/24 $138.89（cap~$55.5B），YTD +300%+。COVID 断崖后的"融化冰块"叙事已被肿瘤期权兑现彻底重定价。
- `[fact-16]` CMV mRNA-1647 P3 进行中 → **已停研**（P3 失败，仅留骨髓移植 P2），无 2026 催化剂。
- `[fact-17]` 诺如 clinical hold → 2024 末 GBS 个案 hold 属实，但 **2026 Q2 中期未达早期成功标准**，增招队列、读出延后。
- `[fact-10]` 流感 mRNA-1010 P3 转阳 → 实际遭 **FDA Refusal-to-File**，已再申，**美国 PDUFA 2026-08-05**（或成第 5 产品）；EU/加/澳审评中。
- `[fact-19]` "2025 前 10 个产品获批" → 已大幅收缩/重排优先级。

### 被验证 / 精修（方向对，数字更新）
- `[fact-02][fact-03]` COVID 断崖 + 2025 指引 $1.5-2.5B → **FY2025 实际 $1.94B(-40%)**，净产品销售 $1.818B，净亏 $2.8B。✓
- `[fact-04]` 现金 ~$9B → **2025 末 $8.1B，2026-06 末 $6.9B**，年末 2026 指引 $4.7-5.2B。✓
- `[fact-05]` 成本削减 + 盈亏平衡推迟 → **opex 削减 $2.2B(~30%)超目标，重申 2028 现金盈亏平衡**；2026 现金成本~$4.2B、2027 $3.5-3.9B。✓
- `[fact-08][fact-09]` mRESVIA 获批 + ACIP 收窄 → 属实，且 2025 扩龄至 18-59 高危(6/12)、50-59 高危(6/25 RFK 采纳)；但 **Q1 2025 销售大幅低于预期**，RSV 品类第 2 年接种下滑。
- `[fact-13][fact-14]` INT+Merck 50/50 + KEYNOTE-942 → 属实（5 年随访复发死亡风险降 49% HR0.51）。✓

### 新增（原盲点已补）
- **mNEXSPIKE**（次代 COVID，2025 美国获批，取~24% 零售份额/65+ 达 34%）——原 baseline 完全不知。
- 流感+COVID 组合 **mRNA-1083(mCOMBRIAX)** EU 获批，日/加/澳审评中，待 FDA 美国再申指引。
- 分析师 P3 后目标价 $60-170 极度分化，**共识~$85-95.67 低于现价 → ~$17B 估值缺口（共识隐含下行）**；Wolfe 估 4 适应症峰值 $9.2B。ESMO 2026(10月)披露完整 HR。

### 仍未校准（partial 缺口 → 05-critic 须列清单 / thesis 标不确定）
- INT P3 的 **HR/p 值/绝对获益**（ESMO 2026-10 才披露）——目前只知达标，力度未知。
- **冷肿瘤外推**（NSCLC/胰腺）——无读出，是平台价值最大不确定。
- mRESVIA / 呼吸道 **2025-2026 具体销售 $ 数字**（仅知"低于预期"）。
- 流感 mRNA-1010 **8/5 PDUFA 结果**（今日 8/25，决定或已出，未校准）。

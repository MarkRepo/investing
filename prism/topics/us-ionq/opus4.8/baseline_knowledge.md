---
slug: us-ionq
variant: opus4.8
written_at: 2026-07-27T00:00:00Z
training_cutoff_estimate: 2025-10
---

# 训练知识 Baseline — IonQ (IONQ, NYSE)

> 本文记录 LLM 在**训练截止时**对该 topic 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。

## 〇、基本信息（company）

- **主代码**：`US_IONQ`（NYSE，与 topic.yaml `scope.ticker` 一致）
- **多市场上市**：单市场（仅 NYSE）
- **市场属性**：美股常规交易时段 9:30-16:00 ET；可做空、期权活跃；散户/期权驱动波动极大，属"主题股/meme 化"量子板块。

## 一、关键事实记忆

**公司与身份**
- `[fact-01]` IonQ 是离子阱（trapped-ion）路线的量子计算公司，2015 年由 Chris Monroe（UMD/Duke）与 Jungsang Kim（Duke）创立，总部 College Park, Maryland → 置信度：高 | time_sensitivity：**静态**
- `[fact-02]` 2021-10 通过 SPAC（dMY Technology Group III）上市，是首家在 NYSE 上市的纯量子计算公司 → 置信度：高 | time_sensitivity：**静态**
- `[fact-03]` 技术采用镱离子（ytterbium）离子阱，室温运行、无需稀释制冷机（相对超导路线的差异化卖点）；全连接门、门保真度高 → 置信度：高 | time_sensitivity：**静态**

**技术指标与产品**
- `[fact-04]` IonQ 自定义"Algorithmic Qubits (#AQ)"作为性能指标；系统迭代 Harmony → Aria → Forte → Forte Enterprise → Tempo；Forte #AQ 约 36 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-05]` 路线图目标：Tempo #AQ 64（2025 目标），后续向逻辑比特/容错跃迁，长期宣称 2028-2030 达到实用容错系统 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-06]` 系统通过 AWS Braket、Azure Quantum、Google Cloud 三大云平台可访问 → 置信度：中 | time_sensitivity：**慢变**

**财务**
- `[fact-07]` 2023 年营收约 $22M；2024 年营收约 $43M（超此前 $37-41M 指引上沿）→ 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-08]` 持续大额净亏损（研发/股权激励为主）；账上现金因多轮股权融资较充裕（2024-2025 期间估计数亿到 $10 亿级）→ 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-09]` 收入结构高度依赖美国政府/科研合同（AFRL 空军研究实验室 ~$54M 合同、DARPA、国家实验室），商业化收入占比低 → 置信度：中 | time_sensitivity：**慢变**

**估值与股价**
- `[fact-10]` 市值波动极大，历史区间从约 $2B 到 $10B+ 以上；P/S 达数百倍级（远高于任何盈利锚），是核心看空理由 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-11]` 2025-01 前后量子板块暴涨后，因 NVIDIA CEO 黄仁勋"实用量子计算还需 15-20 年"言论引发量子股集体大跌（IONQ/RGTI/QBTS 单日重挫），随后有反复 → 置信度：中 | time_sensitivity：**快变** ⚠️

**M&A / 战略**
- `[fact-12]` 2025 年宣布以约 $1.075B 收购英国离子阱公司 Oxford Ionics（芯片级离子阱、CMOS 兼容，主打可扩展性）→ 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-13]` 收购 Qubitekk、Entangled Networks 等，布局量子网络/量子互联网（quantum networking）第二增长曲线 → 置信度：低 | time_sensitivity：**慢变**
- `[fact-14]` 曾宣布拟收购 Capella Space（卫星，指向天基量子密钥分发/QKD）→ 置信度：低 | time_sensitivity：**快变** ⚠️

**管理层**
- `[fact-15]` Niccolo de Masi（原 dMY 主席，资本市场/并购背景）于 2025 年出任 CEO，Peter Chapman（原 CEO，前 Amazon Prime 工程总监）转任执行主席 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-16]` Jungsang Kim 任 CTO；Chris Monroe 联合创始人/首席科学家（其参与度可能下降，unclear）→ 置信度：低 | time_sensitivity：**慢变**

**行业竞争基线**
- `[fact-17]` 离子阱同路线主要对手 Quantinuum（Honeywell + Cambridge Quantum，未上市，H 系列高保真，普遍被视为离子阱技术领先者）→ 置信度：中 | time_sensitivity：**慢变**
- `[fact-18]` 超导路线：IBM（最激进路线图，Condor 1121 比特，Starling 目标 2029 容错）、Google（2024-12 Willow 芯片实现"低于阈值"纠错里程碑）、Rigetti（RGTI 上市）→ 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-19]` 其他路线：中性原子（QuEra、Pasqal、Atom Computing、Infleqtion）、光子（PsiQuantum 未上市 $6B+、Xanadu）、退火（D-Wave/QBTS）、硅自旋（Intel、Diraq）→ 置信度：中 | time_sensitivity：**慢变**
- `[fact-20]` 美股量子纯玩标的可比：IONQ、RGTI（Rigetti）、QBTS（D-Wave）、QUBT（Quantum Computing Inc）、ARQQ（Arqit）→ 置信度：中 | time_sensitivity：**慢变**

**行业范式**
- `[fact-21]` 当前处于 NISQ（含噪中等规模量子）向容错（FTQC）过渡期；纠错、物理比特→逻辑比特、量子优势/商业实用性的兑现时点是全行业最大不确定性 → 置信度：高 | time_sensitivity：**静态**

> **快变统计**：第一节共约 21 条，其中 time_sensitivity=快变 约 10 条（fact-04/05/07/08/10/11/12/14/15/18），这些是第五节优先 query 的强制来源。

## 二、关键人物 / 公司 / 产品

- **Niccolo de Masi** — CEO（2025 起），资本运作/并购风格激进，主导 Oxford Ionics 等收购
- **Peter Chapman** — 执行主席（原 CEO），前 Amazon Prime 工程总监
- **Jungsang Kim** — 联合创始人/CTO；**Chris Monroe** — 联合创始人/首席科学家
- **Quantinuum** — 未上市离子阱最强对手（Honeywell 系）
- **产品线**：Aria / Forte / Forte Enterprise / Tempo（计算）；Qubitekk 系（量子网络）

## 三、产业链 / 竞争格局认知

量子计算产业目前仍在"科研合同 + 云访问试用"阶段，尚无规模化商业营收；估值由技术里程碑叙事与主题资金驱动，与基本面严重脱钩。技术路线未收敛：超导（IBM/Google/Rigetti）比特数领先但需极低温、纠错开销大；离子阱（IonQ/Quantinuum/Oxford Ionics）保真度与全连接占优、但门速慢、扩展性是瓶颈；中性原子与光子是后起黑马。

IonQ 的定位：离子阱阵营的上市纯玩龙头，用 #AQ 指标叙事 + 三大云平台可得性 + 政府合同 + 激进并购（Oxford Ionics 补扩展性、Qubitekk 补量子网络、Capella 补天基 QKD）讲"全栈量子 + 量子网络"故事。真实技术领先度相对 Quantinuum 存疑。

真正的胜负手在纠错与逻辑比特扩展：谁先以可接受开销做出稳定逻辑比特、跑出有商业价值的量子优势。Google Willow（2024-12 低于阈值纠错）被视为超导阵营标志性进展，对离子阱叙事构成压力。

营收端，IonQ 收入小且以政府/科研为主，商业化跃迁（企业付费用量子算力解决真实问题）是否发生、何时发生，是估值能否证成的命门。

## 四、训练知识盲点（自我承认）

- **最新财务**：2024 全年确切数、2025 各季度营收/bookings/亏损/现金/融资 —— 快变，训练知识大概率过时
- **最新股价与估值**：当前市值、P/S、股本稀释情况（含 ATM 增发）—— 快变
- **M&A 落地状态**：Oxford Ionics 是否已交割、Capella Space 交易是否完成/告吹、对价与股份稀释 —— 快变
- **最新技术里程碑**：最新 #AQ、逻辑比特数量、2 逻辑比特/纠错 demo 进展、路线图是否更新或延期 —— 快变
- **管理层现状**：de Masi/Chapman 分工是否稳定、有无新变动 —— 快变
- **竞争对手最新进展**：IBM/Google/Quantinuum 2025-2026 里程碑、是否有新的"quantum advantage"声明 —— 快变
- **一致预期/卖方覆盖**：分析师目标价、评级分布、营收预测曲线 —— 训练时基本无结构化记忆
- **政府政策**：美国国家量子倡议（NQI）再授权、出口管制、国防采购对 IonQ 的资金含义 —— 慢变但可能有近期变化

## 五、需要 web-search 校准的优先项

1. `IonQ Q2 2026 earnings revenue bookings guidance` （fact-07/08 快变+中/低 → 必校准）
2. `IonQ 2025 full year revenue net loss cash position` （fact-07/08）
3. `IonQ stock market cap price to sales valuation 2026` （fact-10/11 快变 → 估值锚必须重置）
4. `IonQ Oxford Ionics acquisition close status completed` （fact-12 快变 → M&A 落地）
5. `IonQ Capella Space acquisition status 2025 2026` （fact-14 快变）
6. `IonQ logical qubits milestone AQ roadmap latest 2026` （fact-04/05 快变 → 技术里程碑）
7. `IonQ CEO Niccolo de Masi Peter Chapman management 2026` （fact-15 快变 → 管理层现状）
8. `Quantinuum IonQ competitive trapped ion 2026 fidelity` （fact-17 → 竞争位）
9. `Google IBM quantum error correction milestone 2025 2026` （fact-18 快变 → 竞品压制叙事）
10. `IonQ analyst price target rating consensus 2026` （第四节盲点：一致预期无记忆）
11. `IonQ equity raise dilution share count ATM 2025 2026` （fact-08 稀释）
12. `quantum computing stocks Nvidia Jensen Huang comment quantum advantage timeline` （fact-11 情绪催化剂）

## 六、prescan 校准结果（2026-07-27 回写）

> Step 4.5 prescan 入库 32 份 web-search material（9 high / 23 mid）后，对照第一节 fact-NN 的更新。**本轮 prescan 大幅改写了 baseline——IonQ 已从"零营收纯故事"变为"营收 100%+ 高速增长 + 巨额并购滚雪球 + 净亏损扩大"的形态。**

### 被推翻（高优先级——thesis_v0 不要再引用原 fact）

- `[fact-07]` 训练时"2024 营收 ~$43M"严重低估当前体量：**Q1 2026 单季营收 $64.7M**（超指引中点 30%），FY2026 指引上调至 **$270M**（100%+ YoY 有机增长），backlog/bookings $470M；FY2025 营收指引 $106-110M；Q3 2025 营收 $39.9M(+221.5% YoY) → 引用 `[mat-acf2c0]`（Q1 2026）`[mat-feab7f]``[mat-a0a4fd]``[mat-60d66e]`
- `[fact-08]` 训练时"现金数亿到十亿级、大额净亏损"需精确重置：**现金 $1.485B（Q3 2025 记录高位）**；FY2025 净亏损 **$512M**（vs FY2024 $331.6M）；Q3 2025 单季净亏损 $1,055.6M（含大额认股权证/衍生品公允价值损失，非经营）；ATM 融资 $360-372M（授权上限 $500M，达标后终止）+ 更大规模股权融资 → `[mat-a0a4fd]``[mat-383412]``[mat-b5259a]``[mat-6e18e7]`
- `[fact-09]` 训练时"收入高度依赖政府/科研"已部分翻转：**Q1 2026 约 60% 营收来自商业客户、约 35% 国际客户**——商业化跃迁正在发生（但需辨明是否含并购并表贡献）→ `[mat-acf2c0]`
- `[fact-10]` 训练时"P/S 数百倍"需按增长重估：**市值 ~$11-13B（2026-07）**（capital.com $11.26B / companiesmarketcap $13B；近 7 日 -12%；2024-11 低点 $4.99B），forward P/S ≈ 40-48x（$270M 指引）、trailing ≈ 110-130x。仍极高但非"数百倍"，市场按"量子成为大产业的可能性"定价而非当期业绩 → `[mat-781c37]``[mat-c93eba]``[mat-feab7f]`
- `[fact-11]` 训练时"黄仁勋看空言论压制量子股"已**反转**：Jensen Huang 公开承认此前时间线判断"错了"，NVIDIA 转而投资三家量子公司——从逆风变顺风催化剂 → `[mat-9eaf2a]``[mat-9326d8]`
- `[fact-04]/[fact-05]` #AQ 叙事让位于逻辑比特/保真度：IonQ 推"加速路线图"，主打 Oxford Ionics 带来的芯片级电子量子比特控制(EQC) + **99.99% 双比特门保真度（半导体标准工艺可量产）** → `[mat-a9845e]``[mat-dd60c9]``[mat-452ef4]`
- `[fact-12]` Oxford Ionics 收购已**完成**（2025-09，$1.075B），核心资产 on-chip EQC，是"用可量产芯片弥合与 Quantinuum 保真度差距"的关键 → `[mat-a0360d]``[mat-a7b34a]``[mat-2f5ec0]`

### 被验证（可继续引用，置信度提升）

- `[fact-15]` de Masi 任 Chairman & CEO 确认（资本运作/激进并购风格），Peter Chapman 转执行主席 → 中→高 `[mat-975a55]``[mat-84c1e9]`
- `[fact-17]` Quantinuum 仍是离子阱最强对手且技术领先（逻辑比特/纠错），但 IonQ 借 Oxford 缩小保真度差距 → 置信度维持 `[mat-fdf44c]``[mat-9cf962]`

### 新增事实（baseline 未记，本轮补入 — 直接影响 thesis）

- **2025 并购滚雪球（de Masi "acquisition empire"）**：除 Oxford Ionics 外，还收购 ID Quantique（QKD 龙头控股权）、Vector Atomic（~$250M，原子钟/传感）、Skyloom & Lightsynq（量子互联网/光子互连）、Capella Space（卫星/天基 QKD）→ 战略从"造一台好机器"转向"垂直整合全栈 + 量子网络" `[mat-3a1051]``[mat-fdf44c]`
- **竞争格局重大变化**：Quantinuum（Honeywell）2026-01-14 递交保密 IPO 文件，估值 >$20B；拥有 TKET 行业标准编译器 + Microsoft 背书 → 离子阱阵营即将有第二个上市对标 `[mat-fdf44c]``[mat-9cf962]`
- **一致预期/分析师覆盖存在**（MarketBeat/Benzinga/WSJ 有目标价与评级），具体数字待 01/02 深挖 `[mat-127027]``[mat-8929d8]``[mat-b5505e]`

### 仍未校准（thesis_v0 引用时标 uncertain / 留 01-02 深挖）

- `[fact-16]` Chris Monroe/Jungsang Kim 现参与度、核心技术团队稳定性 — 未校准
- 分析师目标价具体区间、评级分布、营收预测曲线 — 有覆盖但未取数（`[mat-127027]` 等待深读）
- 并购的商誉/无形资产减值风险、并表对"商业营收占比"的真实贡献拆分 — 未校准
- IonQ 自身逻辑比特数量/纠错 demo 的独立可验证进展（vs Quantinuum/Google）— 未校准
- FY2025 实际营收落地数（Q4 已披露，`[mat-60d66e]` 未取全文）— 待精确

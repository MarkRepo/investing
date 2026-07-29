---
slug: global-glp1-highend-efficacy
variant: opus4.8
written_at: 2026-07-24
training_cutoff_estimate: 2025-01
---

# 训练知识 Baseline — GLP-1 三激动/amylin 高端疗效 arena

> 本文记录 LLM 在**训练截止时**对本 arena 的认知现状。后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。
> **arena 定位**：减重疗效天花板竞赛（22-30% 档）——三激动（retatrutide 类）+ amylin combo（CagriSema/amycretin 类）+ 差异化 antibody-peptide（MariTide）。终局 = 在候选标的里选 shortlist（谁是赢家 + 介入纪律）。
> 本 arena 派生自父行业 `global-glp1-obesity`（已复用 23 份父级耐久 findings），baseline 聚焦**疗效阶梯精确数字 + GCG 机理双面性 + 挑战者读出时点**三个 arena 专属轴。

## 一、关键事实记忆（疗效阶梯 + 机制 + 竞争）

### 疗效数据阶梯（本 arena 的核心标尺）

- `[fact-01]` retatrutide（LY-3437943，LLY 三靶 GLP-1+GIP+GCGR）Phase 2（48wk，12mg）减重约 24.2%（安慰剂调整），当时被视为疗效天花板 → 置信度：高 | time_sensitivity：**慢变**（Phase 2 已定，但 Phase 3 TRIUMPH 读数会刷新）
- `[fact-02]` 继承 thesis 称 retatrutide TRIUMPH-1 80wk 28.3% / 104wk 30.3% → 置信度：**uncertain**（训练时 Phase 3 顶线未读出，此数字来自父级 thesis 引用，必须 web 校准）| time_sensitivity：**快变** ⚠️
- `[fact-03]` tirzepatide（Zepbound/Mounjaro，GLP-1/GIP 双靶）SURMOUNT-1 72wk：5mg −15.0% / 10mg −19.5% / 15mg −20.9%（安慰剂 −3.1%）——注射双激动疗效金标准基准 → 置信度：高 | time_sensitivity：**静态**（已发表）
- `[fact-04]` semaglutide（Wegovy，纯 GLP-1）STEP-1 68wk 约 14.9%（安慰剂调整约 12.4%）→ 置信度：高 | time_sensitivity：**静态**
- `[fact-05]` CagriSema（cagrilintide amylin + semaglutide combo）REDEFINE-1 68wk 20.4%（vs 目标市场预期的 25%，被视为"令市场失望"）→ 置信度：中 | time_sensitivity：**慢变**
- `[fact-06]` Roche CT-388（GLP-1/GIP 双激动，收购自 Carmot）早期数据约 18-19%（24wk 级），有报道称 Phase 达 22-22.5% → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-07]` VKTX VK2735（GLP-1/GIP 双激动）VENTURE Phase 2 皮下 13wk 约 14.7% → 置信度：中 | time_sensitivity：**慢变**（Phase 3 VANQUISH 读出会刷新）
- `[fact-08]` AMGN MariTide（maridebart cafraglutide，antibody-peptide conjugate，GLP-1 激动 + GIPR 拮抗——注意与替尔泊肽 GIP 激动方向相反）Phase 2 约 20% 级但耐受性差（高呕吐/停药）→ 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-09]` NVO sema 高剂量 7.2mg（STEP-UP）减重约 20.7% → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-10]` NVO amycretin（amylin+GLP-1 单分子，皮下+口服双剂型）早期数据激进（皮下 36wk 约 22%），是 NVO 的下一代反击核心 → 置信度：中 | time_sensitivity：**快变** ⚠️

### 机制与安全性（arena 胜负手）

- `[fact-11]` GCGR（胰高血糖素受体）激动是 retatrutide 三靶的"疗效放大器"——通过增加能量消耗（而非仅抑制食欲）带来额外减重，这是它疗效领先的机理来源 → 置信度：高 | time_sensitivity：**静态**
- `[fact-12]` GCGR 激动的双面性：可能升高心率、影响肝糖输出、潜在肌肉流失/瘦体重保护问题——GCG 靶点安全窗是"30% 疗效能否全剂量落地"的核心命门 → 置信度：中 | time_sensitivity：**静态**（机理）但兑现快变
- `[fact-13]` amylin（胰淀素）通路通过增强饱腹感 + 保护瘦体重，被认为是"下一代提升减重质量（fat-selective）"的方向，CagriSema/amycretin/petrelintide 都走此路 → 置信度：中 | time_sensitivity：**静态**
- `[fact-14]` 疗效阶梯可能接近生理上限，30% 级减重逼近减重手术（袖状胃/胃旁路约 25-35%）——边际疗效递减是 arena TAM 与差异化的隐含约束 → 置信度：中 | time_sensitivity：**静态**

### 竞争格局与标的

- `[fact-15]` LLY（Eli Lilly）当前疗效领跑者，手握 tirzepatide（已上市金标准）+ retatrutide（下一代天花板），估值最贵（forward PE 训练时约 35-42x）→ 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-16]` NVO（Novo Nordisk）疗效第二梯队，CagriSema 失望 + Wegovy 面临 IRA 谈判 + 2026 指引下调，估值大幅回落 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-17]` 挑战者中 VKTX（Viking）是唯一皮下+口服双剂型双靶挑战者、纯 pipeline 无收入、被视为头号并购标的（现金撑到约 2027-2028）→ 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-18]` GPCR（Structure Therapeutics）aleniglipron（GSBR-1290）口服 biased GLP-1R 激动剂，属口服 arena 而非高端疗效 arena（疗效约 16%），高端 arena 关联度低 → 置信度：中 | time_sensitivity：**慢变**

## 二、关键人物 / 公司 / 产品

- **LLY**：retatrutide（三激动，TRIUMPH Phase 3 项目群）+ tirzepatide + orforglipron（口服）。疗效领跑者，本 arena 默认赢家候选。
- **NVO**：CagriSema（amylin combo，REDEFINE 失望）+ amycretin（下一代单分子 amylin+GLP-1，双剂型）+ sema 7.2mg 高剂量。反击靠 amycretin。
- **AMGN**：MariTide（月频给药 antibody-peptide，GIPR 拮抗差异化），III 期推迟约 2027，耐受性是命门。
- **Roche/罗氏**：CT-388（注射双靶，收购 Carmot）+ CT-996（口服）+ petrelintide（amylin，收购 Zealand 部分权益）。后进入的整合玩家。
- **VKTX（Viking）**：VK2735（双靶皮下+口服），头号并购期权。
- **Zealand Pharma**：petrelintide（amylin 单药 + 与罗氏合作），amylin 纯玩家。
- **Structure（GPCR）**：aleniglipron 口服，本 arena 关联度低。

## 三、产业链 / 竞争格局认知

减重药疗效竞赛已从"GLP-1 单靶（12-15%）"进入"双靶（tirzepatide 20%）"，高端 arena 是第三阶——三激动（加 GCGR，retatrutide 目标 25-30%）与 amylin combo（提升减重质量）两条技术路线争夺 22-30% 的天花板池。

利润池结构：注射 incretin 存量池（tirzepatide/sema）目前是绝对利润主体，但高端疗效 arena 是"下一代溢价"的来源——谁拿下最高疗效 + 可耐受，谁就锁定高净价与医生优先处方权。LLY 凭 retatrutide 疗效独占天花板，是本 arena 默认赢家；NVO 靠 amycretin 追赶；AMGN/罗氏/VKTX 差异化或并购期权。

关键张力：（1）疗效领先 ≠ 商业领先——最高剂量能否全剂量落地（GCG 安全窗）决定纸面疗效是否缩水；（2）疗效可能已近生理上限，边际差异化收窄，"减重质量（瘦体重保护）/给药频率/口服"可能成为新竞争维度；（3）高端定价在 IRA/TrumpRx 净价压制下能否守住。

## 四、训练知识盲点（自我承认）

- **retatrutide TRIUMPH Phase 3 完整顶线**——训练时 Phase 3 数据基本未读出，父级 thesis 引用的 28.3%/30.3% 需 web 校准（是否已读出、最高剂量安全性）。
- **各挑战者 2025H2-2026 最新读出时点**：VANQUISH-1/2（VKTX）、MariTide Phase 3 剂量方案、罗氏 CT-388 Phase 2b 完整数据、amycretin 皮下/口服 Phase 2 全数据——训练时多为倒计时状态。
- **retatrutide FDA 提交/上市时点**——训练时未知具体监管节奏。
- **GCG 靶点长期安全性信号**（心血管/肌肉）的实际读出——训练时仅机理层面。
- **高端标的最新估值**（LLY/NVO forward PE、VKTX 市值/现金跑道）——快变，训练数字已过时。
- **amylin 单药疗效的独立价值**（petrelintide 是否能作为独立高端资产而非组合成分）。

## 五、需要 web-search 校准的优先项

> 强制规则：第一节所有 `time_sensitivity: 快变 + 高/中` 的 fact（fact-02/06/08/09/10/15/16/17）必须有对应 query。

1. `retatrutide TRIUMPH-1 TRIUMPH-2 Phase 3 topline weight loss results 2026`（校准 fact-02，最关键——决定天花板是否兑现）
2. `retatrutide highest dose 12mg tolerability heart rate discontinuation TRIUMPH`（校准 fact-11/12 GCG 安全窗）
3. `retatrutide FDA submission BLA timeline Lilly obesity 2026`（校准监管节奏）
4. `Novo Nordisk amycretin subcutaneous oral Phase 2 weight loss results 2026`（校准 fact-10，NVO 反击核心）
5. `Amgen MariTide Phase 3 MARITIME dosing weight loss discontinuation 2026`（校准 fact-08）
6. `Viking VK2735 VANQUISH Phase 3 topline results 2026 takeover`（校准 fact-07/17）
7. `Roche CT-388 petrelintide Phase 2 obesity weight loss data 2026`（校准 fact-06）
8. `CagriSema REDEFINE Novo Nordisk 2026 update amylin`（校准 fact-05）
9. `Eli Lilly Novo Nordisk forward PE valuation obesity 2026`（校准 fact-15/16 估值锚）
10. `obesity drug efficacy ceiling amylin GCGR muscle preservation 2026`（校准 fact-13/14 减重质量新维度）

## 六、prescan 校准结果（2026-07-24 回写）

> Step 4.5 prescan 入库 26 份 web-search material（10/10 query 命中，hit_rate 100%）后，对照第一节 fact-NN 的更新：

### 被验证 / 兑现（重大——本 arena 核心赌注锁定）
- `[fact-02]`（原 uncertain）retatrutide TRIUMPH-1 **已于 2026-05-21 读出并被多源确认**：80wk 28.3% / 104wk 30.3%，**45.3% 患者达 ≥30% 减重**，匹配减重手术级别（investor.lilly.com / ajmc / pharmaceutical-journal 一致）→ 置信度 uncertain → **高**。**继承 thesis 的天花板赌注已从"押注"变为"实证"**——LLY 疗效独占从预期兑现为事实。
- `[fact-03]` tirzepatide SURMOUNT 20.9% 金标准 → 一致，仍为基准。
- `[fact-08]` MariTide 疗效 Phase 2 52wk **~20%（"fell short"）+ 高停药/呕吐** → 验证掉队 + 耐受性差；III 期改滴定给药压副作用（biospace/fierce 一致）→ 置信度 中 → 高。

### 被更新 / 补充（细化，非推翻）
- `[fact-11/12]` GCG 靶点安全窗**实锤化**：TRIUMPH-1 最高剂量停药率 **11.3%** + 出现 **dysesthesia（感觉异常）新型不良反应**（pharmacytimes）→ K1 "副作用是否封顶最高剂量"从机理担忧变为可量化风险，但 30% 疗效仍在最高剂量落地（未因副作用缩水到纸面）。
- `[fact-10]` amycretin Phase 2 已读出（T2D 显著减重 + HbA1c），NVO 已推进 Phase III → NVO 反击核心兑现进度确认。
- `[fact-06]` Roche：petrelintide（amylin）Phase 2 阳性（2026-03）+ CT-388，罗氏 ADA2026 展示"双靶+amylin 双策略"——从"落后"升级为"整合期权 + amylin 独立资产"。
- `[fact-05]` CagriSema：2026 补充数据（HbA1c 1.91% / 皮下 2.4mg 显著减重），但头对头仍败于 Zepbound（clinicaltrialsarena 2026-02）→ 验证掉队。

### 仍需 02/03 深挖校准（thesis 引用时标注）
- `[fact-15/16]` LLY/NVO 精确 forward PE：prescan 拿到定性"分化"+ 定价压力，精确倍数需 02 财务料。
- retatrutide **FDA 提交节奏**：prescan 显示 LLY 曾指引 2025H2 提交 NDA，实际 BLA/审评状态需 02 补（gethealthspan 二手源，标 mid）。
- `[fact-07]` VKTX VANQUISH-2 顶线**尚未读出**（2026-03 完成入组，倒计时中）——这是仍开放的挑战者催化剂。

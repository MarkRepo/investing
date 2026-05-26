---
slug: global-glp1-obesity
output_key: 01_business_panorama
version: 1
generated: 2026-05-26
data_freshness: 2026 Q1（LLY 10-Q / NVO 6-K / HIMS 10-Q）+ 2025 全年（信达 / 恒瑞 / 华东 / NVO 20-F / LLY 10-K）
data_freshness_basis: mat-20e63b (LLY 10-Q) + mat-606af8 (NVO 6-K Wegovy 7.2mg) + mat-69b291 (HIMS 10-Q) + mat-11a269 (信达年报) + mat-3c1ced (恒瑞年报)
training_knowledge_pct: 50
---

# 商业全景：GLP-1 减肥药全球赛道

> 生成于 2026-05-26，训练知识占比约 50%（机制 / 历史 / 监管框架），资料更新截至 2026 Q1（LLY/NVO/HIMS 季报）+ 2025 全年（A/H 股年报 + SEC 10-K）

## 行业定义与边界

GLP-1 受体激动剂（Glucagon-like Peptide-1 Receptor Agonists）是一类肠促胰素（incretin）类药物，**主营业务**是糖尿病（T2D）+ 肥胖（obesity）+ 衍生适应症（心衰 HFpEF / 阻塞性睡眠呼吸暂停 OSA / 慢性肾病 CKD / MASH 代谢相关脂肪肝）的处方药开发与销售。本研究 scope 锁定**减肥药细分市场**（obesity / overweight 适应症），但因 GLP-1 类药物本身在糖尿病和减重双适应症共用同一分子（如 semaglutide = Ozempic 糖尿病 / Wegovy 减重；tirzepatide = Mounjaro 糖尿病 / Zepbound 减重），所以财务/产能维度需要看糖尿病+减重合计。

边界排除：传统减肥药（西布曲明 / 奥利司他 / Qsymia / Contrave 类）— 减重效率仅 3-12% 显著低于 GLP-1（12-22%），已是被挤压的旧赛道。也排除手术类减肥（Inspire / ResMed 是间接受影响而非赛道内）。

GICS 分类：35 Health Care → 3520 Pharmaceuticals, Biotechnology & Life Sciences。

## 市场规模与结构

**全球肥胖/超重 TAM**：成人肥胖 >10 亿（16% 全球成人）+ 超重 >30 亿（mat-524100）。WHO 已宣布全球肥胖流行病；糖尿病人口 5.89 亿（2025）→ 7.8 亿（2045 预期，mat-5b9ef4）。**全球 GLP-1 总 TAM ~$100B+/年**（GPCR 10-K mat-0ed0b9）。

**美国市场**：
- LLY 2025 营收 $65.18B，**Mounjaro+Zepbound 占 56% ≈ $36.5B**（mat-3a4b6e）
- NVO 2025 Ozempic 全球 DKK 127B（≈$18B）+ Wegovy DKK 79B（≈$11B / +36% YoY）（mat-653869）
- 2026 Q1 LLY 业务集中度上升至 **65%**（mat-20e63b）

**中国市场**：减肥药市场 ¥87 亿（2025）→ ¥149 亿（2030），中信证券预测 GLP-1 减重 2030 中国 ¥383 亿（mat-6672e4）—— GLP-1 不是切蛋糕，而是结构性放大市场（人群覆盖率提升驱动）。

**集中度**：CR2 (LLY+NVO) 美国市场 ~95%，全球 ~85%。中国市场仍处于"利拉鲁肽 + sema 仿制 + mazdutide / HRS9531 创新药"四国混战阶段。

## 价值链解析

```
[药学发现] → [临床试验/CRO] → [API 制造 + fill-finish] → [品牌商] → [流通渠道] → [终端用户]
   ↑              ↑                ↑                    ↑              ↑
  顶尖科研所   一线 CRO         CordenPharma 等    LLY/NVO/恒瑞/信达    PBM/Medicare/医保 + DTC
```

- **API 制造**：肽类 GLP-1 长期被 fill-finish 产能瓶颈卡住（NVO 2024 Wegovy 短缺、tirz 2024 短缺），**LLY 8 年期 manufacturing commitments up to $10B**（mat-3a4b6e），VKTX 与 CordenPharma 签 100M 注射器 + 1B+ oral tablets（mat-20420a），这是临床期 biotech 罕见的商业化级产能预付，毛利率最高（~80%+）
- **品牌商**：LLY/NVO 双寡头美国 ~95% 份额；中国信达/恒瑞/华东切分国产空间。营业毛利率 LLY 80%+
- **流通渠道**：美国走 PBM（CVS Caremark / Express Scripts / OptumRx）+ Medicare Part D + Medicaid + DTC（LillyDirect 自营 / NovoCare 自营 / HIMS 合作）；中国走医院 + 药店（华东铺货 3 万家终端，mat-6672e4）+ 京东健康（信达分销）
- **终端**：美国 net price ~$1000/月 list → DTC $299-449（mat-e84be3）→ Medicare BALANCE $245+50（mat-a29026, mat-3a4b6e）→ IRA $274（mat-92bc1e）四轨定价

## 商业模式

- **B2B2C 处方模式 + 直营 DTC 双轨**：传统模式 = 处方医生开方 → 流通到 PBM → 商保/Medicare 报销 → 终端患者
- **DTC self-pay 路径**（2024-2025 起爆发）：LillyDirect / NovoCare / HIMS 平台直送，绕过 PBM，挤压"中间商套利"
- **收入结构**：
  - 大型药企（LLY/NVO）：单产品依赖型增长（GLP-1 类占 NVO >90% / LLY 65%）
  - 中型创新药（信达/恒瑞）：BD 出海现金流 + 国内商业化双轨（恒瑞 5 笔 BD ¥33.92 亿 = 营收 11%）
- **盈利驱动**：
  - 量驱：处方覆盖人群扩大（仅美国 ~1 亿肥胖成人 + 3000 万 T2D，目前渗透率 <10%）
  - 价驱：原研保护期 unit net price 在四轨压制下持续下行（NVO 2025 已 declined）
  - 量价剪刀差：LLY 2025 量 +50%+ 抵消价 -10-15% → 营收 +45%（mat-3a4b6e）

## 需求端分析

- **核心客户**：成年 BMI≥30（肥胖）+ BMI≥27（超重 + 1 项 comorbid）+ T2D 患者 + 心衰/CKD/MASH 衍生适应症患者
- **购买决策驱动**：
  - 临床医生（处方权）+ 患者（DTC 自费）+ 商保（报销决定可负担性）
  - 美国 self-insured 雇主必须 opt-in 才覆盖减重药（mat-a070ec）— 雇主对 GLP-1 报销仍是"选择性覆盖"
  - 商保看 cost-effectiveness：CV outcome / OSA / 长期医疗费节约支撑覆盖逻辑
- **需求增长驱动**：
  - 全球肥胖/超重人口结构性增长（10 亿 → 长期增长，mat-524100）
  - 适应症扩展：糖尿病 → 减重 → 心衰 → OSA（2024-12）→ MASH（2025-08）→ CV（2025-10）→ T2D + obesity → CKD → 阿尔茨海默（2025-11 evoke 失败）
  - DTC 渠道降低就医门槛（LillyDirect / NovoCare / HIMS 50M+ 累计 telehealth）

## 供给端分析

- **主要参与者类型**（按梯队）：
  - 第一梯队（注射 GLP-1 类双寡头）：LLY (tirzepatide / Mounjaro+Zepbound) + NVO (semaglutide / Ozempic+Wegovy)
  - 第二梯队（注射 + 口服 mid-cap biotech）：Roche (CT-388 22.5%) / Viking (VK2735 注射+口服) / Structure (aleniglipron 口服) / Amgen (MariTide 月度) — Phase 3 阶段，mat-d16d2f / mat-1f9505 / mat-0ed0b9 / mat-6c585f
  - 第三梯队（中国创新药 + 仿制）：Innovent (mazdutide GCG/GLP-1 dual + 自研口服 IBI3042/IBI3032，mat-11a269) / 恒瑞 (HRS9531 GLP-1/GIP + HRS7535 oral，授权 Kailera，mat-3c1ced) / 华东 (利鲁平 + sema 仿制，mat-d48cc8) / 九源/丽珠/齐鲁/正大天晴/石药 (sema 仿制，mat-cc70d1, mat-60e1ab)
  - 渠道型：HIMS (telehealth + 自营 pharmacy + peptide 工厂，mat-f38030)
- **进入壁垒**：
  - 临床试验成本：单 Phase 3 ~$200-500M，CV outcome 试验 +$200M
  - 制造产能：肽类 fill-finish 是 industry-wide 瓶颈；oral 小分子（GPCR 6000 吨/年 = 1.2 亿患者）是规模化最大的差异化
  - IP：tirz 美国 2036 / sema 美国 2031 / cagri 2037 — LLY 5 年护城河领先 NVO
  - 渠道关系：LLY/NVO 与 PBM、医院、雇主长期关系；DTC 平台需自建（LillyDirect/HIMS）

## 竞争格局

- **格局类型**：双寡头 + 第二梯队成熟 + 中国国产化
- **核心竞争要素（3 个）**：
  1. **临床效果（减重 %）**：tirz 22.5% / CT-388 22.5% / Wegovy 7.2mg 20.7% 已三家追平 best-in-class（mat-606af8 / mat-6c585f）；reta 24% 待 Phase 3 验证
  2. **渠道与定价能力**：LLY 自营 LillyDirect + 自有产能；NVO 与 HIMS 合作 + 自营 NovoCare；信达靠京东健康
  3. **专利护城河 + 适应症广度**：LLY tirz 2036 美国专利 + 6 项 Phase 3 衍生适应症（CV/OSA/MASH/sleep apnea/HFpEF/T1D），是结构性最厚

- **行业龙头与优势**：
  - LLY：单一业务段聚焦 + 临床代际领先 + 自有产能 + DTC 自营 → 综合最强
  - NVO：sema 全球商业化最广 + Akero $4.7B MASH 多元化 + Wegovy 7.2mg 临床已追平
  - 信达：业绩拐点（2025 首次盈利 +420% Non-IFRS 净利）+ BD 出海三轨

## 发展阶段

**当前所处阶段**：**成长期早中段 + 第一波代际护城河被追平**
- 增速：全球 GLP-1 类 2024-2025 营收年增 +30-50%，2026-2027 预期 +20-30%（NVO/LLY 一致 outlook）
- 格局：CR2 仍 ~85% 全球，但 Phase 3 数据 2026-2027 集中读出后**第二梯队成熟、双寡头护城河收窄**
- 技术成熟度：注射 GLP-1 类已 best-in-class 2025 → 2026-2027 看 oral GLP-1 + 三靶 + 维持治疗剂量 + amylin 组合
- 政策成熟度：美国 BALANCE Bridge / IRA 第二批 / MFN / Medicare 长期机制 = 多轨定价压制路径正在搭建（2026-07 起 7 月 - 2027-12 是 Bridge 窗口）

**判断依据**：渗透率 <10% + TAM $100B+ → 还有 5-10 年量增空间；但单价压制周期已开启，**未来 thesis 由"量增大于价跌"主导，而非"持续高定价"**。

## 信息来源

- 训练知识（约 50%）：GLP-1 类机制 / 历史代际跃迁 / 监管框架 / 历史并购参考
- mat-3a4b6e (LLY 10-K MD&A 2025)：营收+利润 / 产能 commitments / IRA 选药史 / 量价剪刀差实证
- mat-20e63b (LLY 10-Q 2026 Q1)：业务集中度 56→65% / BALANCE Bridge / MFN 协议
- mat-653869 + mat-5b9ef4 (NVO 20-F)：sema 净价下行自承 / Akero 收购 / 340B $4.2B / IRA 第二批
- mat-606af8 (NVO 6-K)：Wegovy 7.2mg 20.7% 追平 tirz
- mat-11a269 (信达年报)：营收 +38% / 首次盈利 / IBI3042 + IBI3032 自研口服双管线
- mat-3c1ced (恒瑞年报)：创新药 +50%+ / BD 5 笔 ¥33.92 亿
- mat-d48cc8 (华东年报)：仿制 + 创新药综合体
- mat-20420a + mat-1f9505 (VKTX)：VK2735 双形式 + CordenPharma 100M+1B 产能
- mat-0ed0b9 (GPCR)：aleniglipron + 6000 吨 oral 产能
- mat-6c585f + mat-dfd8f0 (Roche CT-388)：22.5% 减重 + Carmot $2.7B 收购先例
- mat-d16d2f + mat-55c05b (Amgen MariTide)：月度 ~20% 但安全性弱
- mat-d45d79 + mat-f38030 + mat-69b291 (HIMS)：DTC 平台规模 / 战略转向 / 2026 Q1 美国营收 -8%
- mat-cc70d1 + mat-60e1ab (中国 sema 仿制)
- mat-92bc1e + mat-36eaeb (IRA 第二批 sema $274)
- mat-a29026 (KFF BALANCE)
- mat-524100 + mat-6672e4 (Wikipedia + 摩熵 — 行业 TAM)

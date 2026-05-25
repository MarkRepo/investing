---
slug: global-ai-drug-gene-edit
output_key: 01_business_panorama
version: 1
generated: 2026-05-22
data_freshness: 2026 Q1
data_freshness_basis: mat-1fe402 (VRTX 10-Q 2026-05-05), mat-3a51f9 (NTLA 10-Q 2026-05-11), mat-2b431a (BEAM 10-Q 2026-05-07), mat-a66935 (CRSP 10-Q 2026-05-04)
---

# 商业全景：AI 辅助药物研发与基因编辑

> 生成于 2026-05-22，训练知识占比约 60%，资料更新截至 2026 Q1

## 行业定义与边界

本主题覆盖两个相互交叉、但商业模式与监管路径差异显著的细分领域：

1. **基因编辑疗法（Gene Editing Therapeutics）**——以 CRISPR-Cas9、base editing、prime editing 等技术为核心，通过修改人类基因 DNA/RNA 序列治疗遗传病、心血管病、肿瘤等。可分为 **ex vivo**（体外编辑造血干细胞后回输，如 Casgevy）和 **in vivo**（用 LNP 载体或病毒载体直接递送到靶器官，如 NTLA-2002、BEAM-302）。
2. **AI 辅助药物研发（AI-aided Drug Discovery）**——使用机器学习、蛋白结构预测（AlphaFold）、生成式分子设计加速 hit-to-lead、靶点发现、结构优化的工具/平台型公司，以及自研管线公司。

边界：**不含**通用医药 CRO（药明康德）、传统抗体药物（Adagene 类）、细胞免疫疗法非编辑路径（CAR-T 一代产品）。**GICS 分类**：3520 Pharmaceuticals, Biotechnology & Life Sciences；NAICS 3254 Pharmaceutical and Medicine Manufacturing。

## 市场规模与结构

**基因编辑全球市场**：2025 年约 $50-70 亿美元（管线 + 销售合计），其中销售端仅 Casgevy 一家——VRTX 披露 2025 全年 Casgevy 收入 $115.8M（全球累计仅约 150 例输注）[mat-49861e]。即便加上 in vivo 项目研发期的合作收入、Pfizer/Lilly 大型 license deals（NTLA-Regeneron $320M/target、BEAM-Pfizer 单候选 opt-in），整个基因编辑赛道当前销售收入仍处早期。

**AI 制药全球市场**：2025 年约 $20-30 亿美元（含软件订阅 + co-discovery 服务），头部如 Schrödinger 年收入 ~$2-3 亿、Recursion ~$0.8-1 亿；增速从 2021-2023 的 25-30% 放缓到 2024-2026 的 10-15%（行业进入"去泡沫"阶段）。

**地理分布**：美国占基因编辑研发投入 65-70%、欧洲 15-20%、中国 5-10%；AI 制药美国占 60%、欧洲 20%、中国 15%、其他 5%。**集中度**：基因编辑头部三家（CRISPR/Intellia/Beam）+ Verve（已被 LLY 收购）+ Editas 占研发管线约 70%；AI 制药 CR5（Schrödinger、Recursion、Relay、Insilico、晶泰）+ 大药企内化合计 ~50%。

## 价值链解析

```
[上游] 序列设计 / 蛋白结构预测（AlphaFold 3, Chai-1, RFDiffusion 开源工具）
     ↓
[中游] 编辑工具 / 平台（CRISPR-Cas9, base editing, prime editing, LNP 递送）
     ↓
[研发/临床] 自研管线（CRSP / NTLA / BEAM / VRTX）+ 合作管线（Pfizer / Lilly / Regeneron / BMS / Biogen）
     ↓
[制造] CDMO + 自有 GMP 工厂（细胞收集 ATC 网络是 ex vivo 关键瓶颈）
     ↓
[商业化] 医院 ATC 网络 + 支付方（CMS/商保 + 海外医保）→ 患者
```

各环节经济学：
- **上游工具**：毛利率 60-70%（软件授权类如 Schrödinger）；前沿开源工具（AlphaFold 3）压缩商业模型上限
- **中游平台**：研发期纯烧钱（无收入），毛利率不可测
- **临床/合作**：里程碑收入 + royalty 5-15%（如 BEAM-Pfizer 35/65 co-com 期权）
- **制造**：Casgevy 单例毛利率约 50-60%（含 CRSP 40% 利润分成），但被 myeloablative conditioning 物流摩擦严重压制 [mat-49861e]
- **商业化**：售价 $220 万/患者（Casgevy）→ 单 patient gross profit ~$130-150 万；但 VRTX 自述 "manufacturing CASGEVY as a percentage of revenue is significantly higher than for our CF medicines" [mat-49861e]

## 商业模式

主流模式有四类：
1. **自研管线 To B/支付方**：CRSP/NTLA/BEAM/VRTX，长周期重资本（单产品 8-15 年 / $2-5B 累计研发）；收入来自里程碑 + 销售分成。CRSP 2025 仅 $3.5M 收入但烧 $664M [mat-ae69f9]；NTLA 2025 净亏 $412.7M [mat-8d4e6d]；BEAM 2025 收入 $139.7M（多为里程碑） vs 烧 $383.7M 运营 [mat-797ff7]
2. **平台 + 合作收入**：BEAM 与 Pfizer/Apellis/Lilly 多 deals；NTLA 与 Regeneron Co/Co
3. **软件授权（卖铲子）**：Schrödinger 物理化学计算（未在 findings 覆盖）
4. **支付方协议**：Casgevy 美国与覆盖 275M+ lives 的国家/支付方达成 access 协议 [mat-49861e]

**盈利驱动**：（输注数 × 售价 - 制造成本）× 利润分成比例 - R&D。当前所有基因编辑公司均未盈利，靠现金 + 融资 + 里程碑续命。

## 需求端分析

**核心患者群体**：
- SCD/TDT（Casgevy）：全球可寻址 ~60,000 人严重患者 [mat-ae69f9]
- HAE（lonvo-z）：美国 ~7,000 人在治 [mat-8d4e6d]；99% 患者愿意尝试一次性疗法（NTLA 调研）
- ATTR（nex-z）：百万级（CM）+ 数千（PN）
- AATD（BEAM-302）：美国 PiZZ ~100,000 人 [mat-797ff7]
- 心血管 dyslipidemia（CTX310/Verve）：千万级（最大潜在市场）

**驱动因素**：
- 患者端：一次性根治意愿强烈，但 myeloablative 化疗预处理是巨大心理/生理门槛
- 医生端：92% 愿意处方 HAE 一次性疗法 [mat-8d4e6d]
- 支付方端：$220 万/例对支付方是巨大冲击，需 outcome-based reimbursement 模式
- 监管端：FDA 在 2025-10 后对 in vivo 项目趋严但 5 个月内可解禁 [mat-3a51f9]

## 供给端分析

**主要参与者类型**：
- 美股头部基因编辑：CRSP、NTLA、BEAM、Editas、Prime Medicine
- 大药企内化/收购：LLY（收 Verve）、BMS（收 Orbital）、Biogen（收 Apellis）、VRTX（收 Alpine $5B）、Roche、Novartis
- AI 制药纯标的：Schrödinger、Recursion、Relay、Isomorphic Labs（Alphabet 子公司）、Insilico
- 中国选手：博雅辑因、邦耀生物、XtalPi、Argo Bio、Gritgen、YolTech（in vivo ATTR）[mat-8d4e6d]

**进入壁垒**：
- IP（CRISPR/Cas9 Broad vs UC 干涉案 2025-05 发回重审，ToolGen 诉讼对全行业悬剑） [mat-8d4e6d, mat-ae69f9]
- 制造（LNP 包封、HSC 处理、GMP 工厂建设资本投入 $1-3B/家）
- 临床能力（gene therapy 通常需要 15 年长期随访 LTFU）
- 监管能力（与 FDA 的 RMAT/Priority Voucher 协商）

## 竞争格局

**类型**：基因编辑 = 三足鼎立（CRSP-Cas9 / Beam-base editing / Prime Medicine prime editing），叠加 LLY-Verve 一极；AI 制药 = 高度分散，软件商 vs 自研管线两条赛道。

**核心竞争要素**：
1. **临床数据兑现速度**——HAELO 87% 减发作 [mat-3a51f9] vs BEACON 12 月 72.8% 编辑效率 [mat-797ff7] vs CTX310 ANGPTL3 -73% [mat-ae69f9]
2. **递送技术**——LNP（in vivo 肝靶） vs ex vivo 电穿孔 + busulfan 预处理
3. **BD/合作变现能力**——BEAM 与 Pfizer/Lilly/Apellis 多 deal 体系 vs NTLA 与 Regeneron 单一深度合作

**龙头与优势来源**：
- Casgevy（VRTX/CRSP）= 商业先发，但 K2 兑现远低预期（2025 仅 64 例输注）[mat-49861e]
- NTLA = in vivo 临床进度第一（HAE BLA H2 2026 已 rolling）[mat-3a51f9]
- BEAM = 平台广度第一（base editing + ex vivo SCD + in vivo AATD/PKU/GSDIa）[mat-797ff7]

## 发展阶段

**所处阶段**：**导入期晚期到成长期早期**。判断依据：
- 商业销售刚起步（Casgevy 全球累计仅 ~150 例 [mat-49861e]）
- 第一波 in vivo BLA 即将到来（NTLA HAE H2 2026 [mat-3a51f9]、BEAM risto-cel 2026 年底 [mat-797ff7]）
- 监管框架成型但仍有不确定性（CNPV Priority Voucher、RMAT designation 流程化）
- 资本市场对赛道有"去泡沫"阶段：CRSP/NTLA/BEAM 从 2021 高点跌幅 60-90%；但 Q1 2026 集体融资（CRSP $600M 可转债、NTLA $195M 二级、BEAM Sixth Street $500M）显示头部公司跑道延至 2028+

**核心矛盾**：技术成熟度上升 vs 商业化爬坡远低预期。**未来 18-24 个月将是从导入期向成长期切换的关键窗口期**。

## 信息来源

- 训练知识（约 60%）
- mat-ae69f9: 2025_CRSP_10-K（财务结构、CTX310、Casgevy 不披露架构）
- mat-a66935: 2026_CRSP_10-Q（$600M 可转债、Q1 collab expense -20%）
- mat-8d4e6d: 2025_NTLA_10-K（HAE 患者池、ATTR clinical hold）
- mat-3a51f9: 2026_NTLA_10-Q（HAELO topline、MAGNITUDE 解禁、$195M 增发）
- mat-797ff7: 2025_BEAM_10-K（risto-cel BLA、BEAM-302 加速审批、Sixth Street 5 亿信贷）
- mat-2b431a: 2026_BEAM_10-Q（BEAM-302 60mg pivotal、NEJM 发表）
- mat-49861e: 2025_VRTX_10-K（**Casgevy 64 例输注铁证**、CRSP 60/40 利润分成）
- mat-1fe402: 2026_VRTX_10-Q（Casgevy Q1 $42.9M、TRIKAFTA -7% 首次下滑）

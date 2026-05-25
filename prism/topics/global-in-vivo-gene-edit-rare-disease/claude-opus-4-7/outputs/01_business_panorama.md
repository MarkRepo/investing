---
slug: global-in-vivo-gene-edit-rare-disease
output_key: 01_business_panorama
version: 1
generated: 2026-05-23
data_freshness: 2026-Q1
data_freshness_basis: NTLA/BEAM/ALNY/BBIO/BCRX/KALV/VRTX 全部 10-Q（2026-05-07 前后）+ 4 月 NTLA HAELO topline
---

# 商业全景：In vivo CRISPR/base editing 罕见病 (HAE/AATD/HSD)

> 生成于 2026-05-23，训练知识占比约 50%，资料更新截至 2026 Q1（NTLA HAELO topline 截至 2026-04-29）

## 行业定义与边界

In vivo 基因编辑 = **将编辑工具（Cas 蛋白 mRNA + guide RNA 或 base editor mRNA + guide RNA）通过脂质纳米颗粒（LNP）静脉一次输注，使其在体内（绝大多数为肝细胞）完成靶基因永久性编辑**。

边界：
- **属于本范畴**：NTLA-2002（HAE，CRISPR/Cas9 KLKB1 敲除）、NTLA-2001/nex-z（ATTR，CRISPR/Cas9 TTR 敲除）、BEAM-302（AATD，base editor E342K 修复）、BEAM-301（GSDIa）、BEAM-304（PKU）、Verve-101/102（PCSK9，base editor，2025 被 Lilly 收购）、YolTech ART-001（中国 ATTR in vivo CRISPR）。
- **不属于**：ex vivo 编辑回输（Casgevy/risto-cel SCD/TDT，需 myeloablation）；mRNA 替代（不修改基因组）；ASO/siRNA（不切 DNA，需重复给药）；AAV 基因增补（替换而非编辑）。
- 关键词/分类：GICS 35201010 Biotechnology；FDA 监管路径走 BLA + RMAT/Orphan Drug + 部分用 Accelerated Approval（生物标志物）。

研究问题对应的"竞技场"是 **HAE / AATD / HSD（hereditary swelling/storage disorders）三个罕见病适应症**——首批商业化集中于此，因为：(1) 肝靶向 LNP 已成熟，(2) 罕见病可走 RMAT/ODD 加速通道，(3) 单基因疾病编辑靶点清晰，(4) 患者池足够小（数千到数万）使得首年商业化建模可行。

## 市场规模与结构

**HAE（遗传性血管性水肿）**：
- 全球流行率约 1/50,000，美国约 7,000 在治患者，全球 30,000-50,000（NTLA 10-K [mat-8d4e6d]）。
- 2025 年现存 LTP（长期预防）+ on-demand 市场全球约 $5-7B：BCRX ORLADEYO FY2025 全球净销售 $601.8M [mat-a9e722]、Takeda Takhzyro 估计 $2.5B+（[训练知识]）、CSL Berinert/Haegarda 合计 $1.5B+（[训练知识]）、KalVista EKTERLY 上市首季 Q1 2026 $39.2M [mat-961a86]。
- 增长来自诊断率提升 + LTP/on-demand 渗透 + ORLADEYO 仍在 +37% YoY 加速（5 年 launch curve 不减速）。

**AATD（α-1 抗胰蛋白酶缺乏症）**：
- 美国约 100,000 PiZZ 双 Z 等位患者（BEAM 10-K [mat-797ff7]），全球 200,000+。
- 现行治疗（增强治疗 IV 周注 Aralast/Prolastin/Zemaira）市场约 $1.5B；BEAM-302 目标用 AAT 生物标志物 12 月加速审批。
- 适应症横跨"肺病 + 肝病"——BEAM-302 设计 Part A 仅肺病、Part B 肝病±肺病。

**HSD（hereditary storage disorders，含 GSDIa/PKU/Canavan 等）**：
- BEAM-301（GSDIa，2026 报告初步 Phase 1 数据）、BEAM-304（PKU，2026 提交 IND）、BBIO BBP-812（Canavan，Phase 1/2，[mat-6bd364]）。
- 单适应症患者池更小（PKU 美国 ~16,500，GSDIa <2,500），但 lifetime cost 高，是 in vivo 编辑下一步扩张方向。

**赛道整体规模**：现行 HAE+AATD+HSD 治疗市场约 $10B；若 in vivo 编辑实现"一次治疗终生缓解"，可货币化潜力（按一次性 $1-2M 定价 × 渗透 30-50%） = $20-40B 累计 5 年 NPV，但单年峰值受首年渗透率制约。

## 价值链解析

```
靶点发现/优化 → CRISPR/编辑器开发 → LNP 递送平台 → 临床试验/CMC → 监管 (BLA/EMA) → ATC/IDN 输液中心 → 患者
   (Broad/Doudna)   (NTLA/BEAM/Verve)  (Acuitas/Genevant) (CRO/AAALAC)  (FDA/CBER)    (输液网络)
```

- **靶点+编辑器开发**：NTLA（CRISPR/Cas9）、BEAM（base editor）、Verve→Lilly（base editor，PCSK9）、Prime Medicine（prime editor）。毛利率 N/A（亏损期），R&D burn $300-500M/年/家。
- **LNP 递送**：Acuitas/Genevant/Arbutus（IP 持有）+ NTLA/BEAM 自研。LNP IP 仍是潜在卡点。
- **CMC + Conditioning**：in vivo 编辑因不需 myeloablation，相比 ex vivo（Casgevy）COGS 显著低（无 cell collection / busulfan / 长期住院），单例成本预计 $200-400k vs Casgevy $500k+ (训练知识)。
- **ATC 网络**：HAE/AATD 不需要专门细胞输注中心，普通输液中心即可——这是 in vivo 编辑相比 Casgevy "ATC 物流瓶颈"的根本优势[mat-49861e VRTX FY2025 漏斗 300/147/64 显示 myeloablation 是 ex vivo 致命瓶颈]。
- **支付方**：罕见病 + 一次性高价路径（Casgevy $2.2M、Hemgenix $3.5M）已建立先例，CMS/欧洲商保已开 outcomes-based agreement 通道。

## 商业模式

- **一次性输注 + 终生疗效**（vs 现行 LTP/on-demand 终身订阅）。
- 收入结构：单点高单价（预计 $1-2M/患者）× 渗透曲线，3-5 年达峰，无续费收入。
- 与现有订阅式产品对照：BCRX ORLADEYO WAC 年化约 $830k/患者（[mat-a9e722]）、Takhzyro ~$600k、AMVUTTRA ATTR-CM 年化 ~$500k（[训练知识]）—— in vivo 编辑一次性 $1-2M 在 NPV 维度对患者/支付方有吸引力。
- 盈利驱动 = 渗透率（K3-RD）× 单价 × (1 − 制造成本率) × (1 − Regeneron/Pfizer 利润分成 25-35%)。

## 需求端分析

- **核心客户**：HAE 专科诊所（约 200 个 HCEC 美国）、AATD 肺病 / 肝病专科、罕见病儿童中心。
- **决策驱动**：(1) 当前订阅式产品依从性差/费用高（HAE 患者每月皮下/IV 自注，60% 急性发作 1h 内未及时处理 [mat-0e71c4]）；(2) 一次治疗便利性 + 心理负担减轻；(3) 安全性（NTLA HAELO 0 SAE、62% attack-free [mat-3a51f9]）；(4) 长期成本（一次 $1.5M vs 终生订阅 $15M+ NPV）。
- 需求增长驱动：诊断率提升（BBIO ATTR-CM 美国诊断池 5K→50K 6 年 10× [mat-6bd364]，类比 HAE/AATD 仍有诊断红利）+ 患者协会 advocacy（HAEA、Alpha-1 Foundation）。

## 供给端分析

- **主要参与者**：NTLA、BEAM、Verve（Lilly 子）、CRSP（已切回 ex vivo + in vivo 二线）、Editas（早期）、Prime Medicine、YolTech（中国 ATTR）、AccurEdit（中国，BPR-30221616）、Tessera、Caribou。
- **进入壁垒**：(1) CRISPR/base editor 平台 IP（Broad、UC Berkeley、Beam Foundation 多重纠纷）；(2) LNP 递送平台 IP（Acuitas/Genevant 仍是关键合作方）；(3) FDA RMAT/Orphan 审批先发优势；(4) 单家研发烧钱年 $400M+ 资本壁垒；(5) 制造（GMP CRISPR mRNA）规模门槛。
- **产能/供给**：当前在研管线 >20 个 in vivo 编辑项目进入临床；2026-2028 真正能拿到 BLA 的 ≤3-5 个（NTLA-2002 HAE、BEAM-302 AATD、Verve-102 PCSK9 心血管不在本研究范围）。

## 竞争格局

- **赛道格局**：高度集中——NTLA + BEAM + Verve（Lilly）三家把持西方 in vivo 编辑罕见病管线 80%+ 市值；中国玩家（YolTech、AccurEdit）在 ATTR 跟跑但西方监管尚未落地。
- **核心竞争要素**（不超过 3 个）：
  1. **临床数据兑现速度**：NTLA-2002 HAELO 已读出 + rolling BLA [mat-3a51f9]；BEAM-302 60mg 锁定 + 2026 H2 启动 pivotal [mat-2b431a]——节点先行者锁定品类心智。
  2. **安全性记录**：单例死亡（NTLA Phase 1 Grade 4 → 2025-11-05 患者死亡，[mat-8d4e6d]）+ BEAM 双剂 Grade 4 ALT [mat-2b431a] 是赛道悬剑；HAELO 0 SAE 是当下最强反证 [mat-3a51f9]。
  3. **商业化基础设施 + 支付方接入**：NTLA 4 月增发 $195M 现金跑道延至 2028 [mat-3a51f9]，BEAM $1.2B + Sixth Street $500M 信贷 [mat-797ff7]——准备 BLA + 上市资金充足。

- **行业龙头与优势**：
  - NTLA："the only company with in vivo genome editing product candidates in Phase 3 clinical development"（自述，FY2025 10-K [mat-8d4e6d]）+ HAELO 已读出 + ATTR 二线管线（即使有 hold 历史）。
  - BEAM：base editor 专利组合 + risto-cel BLA 2026 年底 + BEAM-302 加速审批通路确认。
  - 两者各自在不同适应症形成"first-in-class+first-mover"组合，短期非直接对抗。

- **替代竞争**（不在 in vivo 编辑赛道但替代 HAE/AATD 治疗）：
  - HAE：BCRX ORLADEYO（口服日服）+ Takeda Takhzyro（皮下季度）+ KalVista EKTERLY（口服 on-demand，2025 上市）+ CSL Andembry（月针）+ ADARx Onvuzosiran（siRNA）。BCRX 10-K 直接把 NTLA-2002 列 Phase III "One-time Prophylaxis"对手 [mat-a9e722]。
  - AATD：Grifols/Takeda/CSL 周输 IV 增强治疗（在售但便利性差）+ Wave/Inhibrx ASO 在研。

## 发展阶段

**当前阶段：导入期向成长期过渡**——技术可行性已验证（NTLA-2002 Phase 3 -87%、BEAM-302 60mg AAT 16.1µM），监管路径已清晰（RMAT/Orphan/Accelerated），但**商业化兑现尚未发生**。

判断依据：
- **导入期信号尚存**：尚无产品获批；FDA 对 in vivo 编辑长期安全监测要求（15 年 LTFU）+ 监管对脱靶/肝毒性敏感 [mat-8d4e6d 的 NTLA-2001 hold]。
- **成长期信号已现**：Phase 3 阳性数据兑现（HAELO 2026-04，[mat-3a51f9]）；BLA 启动（NTLA rolling BLA 2026-04）；BEAM-302 pivotal 锁定（2026 H2 启动，[mat-2b431a]）；BP 整合潮（Lilly→Verve 2025-07 [mat-797ff7]、BMS→Orbital 2025-12、Biogen→Apellis 2026-Q2 [mat-2b431a]）。
- 预计 **2027-2029 进入完整成长期**：第一批 BLA 获批 + 商业放量 + 适应症扩张。

赛道整体仍处"事件驱动型估值"阶段——NTLA HAELO topline 后 4-30 日股价反弹（市场 reprice），但首年商业化 ramp 尚未发生，距 ALNY/BBIO/BCRX 那种"第一年净销售 $300M-700M"的成熟期 base rate 至少差 18-24 个月。

## 信息来源

- **训练知识（约 50%）**：行业定义、AATD/HAE 流行病学、价值链、订阅式产品现行格局、ex vivo vs in vivo 监管差异、LNP/CRISPR IP 历史。
- **资料**：
  - mat-3a51f9 (NTLA Q1 2026 10-Q): HAELO Phase 3 -87% / 0 SAE / rolling BLA 2026-04 / 现金跑道至 2028
  - mat-8d4e6d (NTLA 2025 10-K): HAE 全管线 + 99% 调研 + Phase 1 死亡 + ATTR hold 历史 + Regeneron Co/Co
  - mat-2b431a (BEAM Q1 2026 10-Q): BEAM-302 60mg AAT 16.1µM / pivotal 2026 H2 / Grade 4 ALT 双剂 / Apellis→Biogen
  - mat-797ff7 (BEAM 2025 10-K): risto-cel BLA 2026 年底 + AATD 加速审批通路 + Sixth Street $500M
  - mat-49861e (VRTX 2025 10-K): Casgevy 全年 64 例输注 / 漏斗 300/147/64（ex vivo 反向参考）
  - mat-1fe402 (VRTX Q1 2026 10-Q): Casgevy Q1 19 例 / 透明度倒退（ex vivo 慢爬坡）
  - mat-a9e722 (BCRX 2025 10-K): ORLADEYO $602M FY2025 +37.5% / NTLA-2002 列竞争表 / Astria $874M
  - mat-a50200 (BCRX Q1 2026 10-Q): ORLADEYO Q1 $148M / Astria 关账
  - mat-961a86 (KALV Q1 2026 10-Q): EKTERLY Q1 $39.2M / Chiesi $27/股 tender
  - mat-0e71c4 (KALV 2025 10-K): KONFIDENT Phase 3 1.79h vs 6.72h / 60% attacks 治疗 >1h 晚
  - mat-b1ab1b (ALNY 2025 10-K): AMVUTTRA $2.31B FY2025 +138% / nucresiran 6 月 -90% / Alnylam 2030
  - mat-5fe00b (ALNY Q1 2026 10-Q): AMVUTTRA US Q1 $702.6M +255% / ONPATTRO -59%
  - mat-6bd364 (BBIO 2025 10-K): Acoramidis FY2025 $362.4M / 7,804 患者 / 1,856 处方医生 / NBRx >25%
  - mat-696075 (BBIO Q1 2026 10-Q): Acoramidis Q1 $180.6M +391% / SG&A +54% / $500M 回购

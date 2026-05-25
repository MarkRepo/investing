# Thesis v2 — 全球量子计算与量子模拟产业

> 写于：2026-05-23 4 份 web 补充 findings 入库后
> 模型：claude-opus-4-7
> 数据基础：17 份 findings = v1 的 13 份 + 4 份 web 一手补充（IBM / Google Quantum AI / Quantinuum+Atom Computing / PsiQuantum+Microsoft Majorana）
> 与 v1 的主要差异：K1 微幅上调、K2 进一步下调、新增主流候选评分、新增 Quantinuum IPO 与 Microsoft Majorana 两个反向标的、保留 K5 主结论

---

## 0. 与 thesis_v1 相比的关键边际变化

| 维度 | v1 verdict | v2 verdict | 主要变化原因 |
|---|---|---|---|
| K1（2027 经济价值量子优势）| 15-25% | **20-30%** | Q-CTRL × IBM 2026-05-06 Fermi-Hubbard 3,000× 加速 demo + Cleveland Clinic/RIKEN/IBM 12,635 原子蛋白模拟是迄今最接近"经济价值"的证据；IBM CEO Krishna 公开承诺 2026 内出现首次 real-world advantage（强承诺，未兑现将引发反噬）|
| K2（2028 前 ≥100 LQ + ≤10⁻⁹）| 10-20% | **5-15%** | 主流候选全员 roadmap 显示"≥100 LQ"在 2028 仅 IBM Starling 前体节点（前一年磁态注入演示，非完整 100 LQ）+ Quantinuum Sol（~96 LQ）；"≤10⁻⁹" 在所有公司官方时间表上都指向 **2029-2030**，无一例外。两项 AND 命中概率被压缩 |
| K3（制冷机 +40%）| 20-30%（反向证据已出现）| 20-30% 维持 | 无新边际证据，K3 反向叙事已定 |
| K4（≥3 家药企/化工/材料经济价值案例）| 15-20% | **20-25%** | Cleveland Clinic 12,635 原子蛋白 + Q-CTRL 1D Fermi-Hubbard + IBM 与 Boeing 防腐材料合作 = 三起 *研究层级* 案例已出现；但仍未达到"客户付费 + 量化 ROI"标准；2026-2027 内若任一案例升级为商业合同，K4 可能命中 |
| K5（2026 H1 末四傻 -50%）| 60-75% | **70-85%** | RGTI 已 -54.6%、QUBT -52.5%（已部分兑现 K5 阈值）；剩 IONQ/QBTS 尚需进一步下行 |
| **新增主线 1**| — | **Quantinuum IPO $20B 是新的 K5 候选** | 2025 营收 $30.9M / 客户集中度 90% RIKEN / 2026-Q1 仅 $5.2M，P/S ~650× 高于 IONQ 当年 SPAC 上市估值 |
| **新增主线 2**| — | **Microsoft Majorana 1 是空头叙事支柱**| Nature 审稿人明确否认 MZM 存在；2026 内无任何独立 follow-up 证据 |
| **新增主线 3**| — | **Nvidia VC 跨入 PsiQuantum**| 黄仁勋 2024-01 看空 → 2025 转向 + NVentures 入股是顶部信号还是 catalyst，二者之一 |
| **总信念强度** | 7/10 | **7.5/10** | K5 验证概率上调 + 新增 Quantinuum/Majorana 标的；主线维持 |

---

## 1. 核心 thesis（v2）

> **看空美股纯硬件 SPAC 量子四傻（IONQ/RGTI/QBTS/QUBT）2026 H1-H2 估值；新增看空 Quantinuum 2026 IPO 估值（$20B 目标，P/S 650×）；继续看空 Bluefors/Oxford 制冷机叙事；中性看待 IBM/Google/Atom Computing 主流候选——其 K1/K2 路线技术更扎实但商业兑现仍指向 2029-2030，与 K1/K2 时间窗错位；中性偏看多国产替代（国盾+本源）；通用量子优势 2027 前小幅利多于 v1（IBM Q-CTRL demo + Krishna 承诺），但"付费 $1M+/年企业客户"硬证据仍缺；量子模拟商业化在 2026 内研究层级案例渐多，但量化 ROI 披露仍不会 2028 前到位。**

**信念强度：7.5/10**（v1 7/10 → 小幅上调）。内部分化：
- 看空美股四傻 **9.5/10**（v1 9/10 → 上调；K5 已部分兑现）
- 看空 Quantinuum IPO 估值 **7/10**（v2 新增；P/S 650× 不可持续）
- 看空 Microsoft "拓扑路线已 work" 叙事 **8/10**（v2 新增；Nature 审稿人明确否定是最硬证据）
- 看空 Oxford 量子叙事 **7/10**（v1 维持）
- 看多中国国产替代 **6/10**（v1 维持）
- 量子模拟商业化 **5/10**（v1 4/10 → 微调，Q-CTRL/Cleveland 提供研究级证据）
- 通用量子优势 2027 前 **3/10**（v1 2/10 → 微调，IBM Q-CTRL demo + Krishna 承诺增加 catalyst 风险）

---

## 2. 五大 Killer Question 裁决（v2）

### K1：2027 前是否出现首例"经济价值量子优势"
**裁决：大概率不命中（命中概率 20-30%）**

**v2 新增证据**：
- **Q-CTRL × IBM（2026-05-06）**：120-qubit Nighthawk 跑 1D Fermi-Hubbard 材料模拟，2 分钟 vs 经典 100+ 小时（3,000× 加速）。Q-CTRL 主动框定为"first practical quantum advantage"。**但 Q-CTRL 是合作伙伴而非付费客户，且材料模拟问题选取本身受质疑**。
- **Cleveland Clinic + RIKEN + IBM（2026-05-05）**：12,635 原子蛋白量子模拟，史上最大。Cleveland Clinic 与 IBM 是 multi-year onsite Q-System 合作，但未披露付费机制是否到 $1M/年。
- **IBM CEO Krishna 2026-04**：公开承诺 2026 年内出现首次 real-world quantum advantage——**这是首次有量子领头羊 CEO 把硬节点放进当年**，未兑现将引发叙事反噬。
- **Q-CTRL/IBM 类工程演示尚未跨越"客户付费 $1M+/年 + 解决经典做不到的商业问题"门槛**。
- **Quantinuum 2026-Q1 营收 $5.2M / 客户集中度 90% 单一客户（RIKEN）**——所谓"commercial tipping point"在硬数据上未出现。
- **Google 2025-11 自己承认 Stage 3（real-task advantage）未达成**。

**关键证据矩阵**（v2 含 v1）：

| 来源 | K1 信号 | 强度 | 时间窗 |
|---|---|---|---|
| D-Wave Science 论文（spin-glass）| 物理 benchmark, 不构成经济价值 | 弱 | 2025-03 |
| D-Wave Q1 2026 收入塌方 | 反向证据（QCaaS 没起飞）| 强 | 2026 |
| IonQ Risk Factors | 律师层自承 "may never occur" | 中 | 2025-FY |
| Rigetti Risk Factors | 自承 LFTQC may never occur | 中 | 2025-FY |
| 国盾 2024 业务量级 | ¥5,659 万 / 在手 ¥1.06 亿 | 弱 | 2024 |
| **Q-CTRL/IBM 3000× demo** | **最接近"经济价值"但仍 POC** | **中** | 2026-05 |
| **Cleveland Clinic 12,635-atom 蛋白** | **研究合作，未量化 ROI** | **中** | 2026-05 |
| **IBM Krishna 2026 内承诺** | **强 catalyst（双向 catalyst）** | **强** | 2026 内 |
| Quantinuum 2026-Q1 营收 $5.2M | 反向证据 | 强 | 2026-Q1 |
| Google Stage 3 自认未达 | 反向证据 | 强 | 2025-11 |

**结论**：K1 命中概率从 v1 的 15-25% 上调至 **20-30%**——主要因为 IBM/Q-CTRL/Cleveland Clinic 提供了更接近 K1 门槛的研究级 demo。但"付费客户 + 量化 ROI"硬门槛仍未跨越，且 K1 真正的危险来自 IBM Krishna 2026 内承诺——**若 2026 H2 IBM 真给出企业付费案例，K1 命中概率会跳到 50%+**；若 2026 末仍仅 POC 而无具名付费客户，K1 命中概率回落到 15%。

### K2：2028 前 ≥1 个 FTQC 系统达 ≥100 逻辑比特、错误率 ≤10⁻⁹
**裁决：大概率不命中（命中概率 5-15%）**

**v2 新增证据**（覆盖全部主流候选）：

| 公司 | 当前最大 logical qubit demo | 当前 logical error rate | 官方 2028 内承诺 ≥100 LQ 路径 | 官方 ≤10⁻⁹ 目标年份 |
|---|---|---|---|---|
| **IBM** | 未公开实测 logical 数 | ~10⁻³ 仿真上 qLDPC 估算 | **2028 Starling 前体磁态注入演示（非完整 100 LQ）**，2029 Starling 200 LQ | **未承诺 10⁻⁹，仅 "orders of magnitude vs surface code"** ≈ 10⁻⁶~10⁻⁸ |
| **Google** | **1 个 logical qubit**（Willow d=7 memory）| **1.4×10⁻³ / cycle** | 没有公开 2028 内 ≥100 LQ 路径 | 路线图 useful FTQC 2029-2030 |
| **Quantinuum** | **94 LQ GHZ 态 / 48 standard LQ**（Helios）| ~10⁻³ 到 10⁻⁴ | **Sol (2027) ~96 LQ**；Apollo (2029) 数百 LQ | **官方 FT 目标 2029-2030** |
| **Atom Computing** | 28 LQ 跑 Bernstein-Vazirani（2024-11）| 阈值下 2.14× | **Magne (2027 Q1) 50 LQ**；次代 2027-2028 目标 100+ LQ | 配合 QuEra 新型码理论 10⁻¹³ 可行，但实证未到 |
| **PsiQuantum** | 0（无 logical qubit demo）| — | Brisbane 延期 12 月，~2029-2030 才"点亮"；100+ LQ 应 2031+ | — |
| **Microsoft Majorana**| 0（8 物理点位非完整 qubit）| — | 物理基础未独立验证 | — |

**v2 关键观察**：
1. **"≥100 LQ" 单条件命中概率**：35-45%（IBM Starling 前体 + Quantinuum Sol + Atom Computing 次代任一兑现即触发）
2. **"≤10⁻⁹" 单条件命中概率**：**~5%**（无一家在 2028 前给出 ≤10⁻⁹ 时间表；qLDPC 仿真最乐观估计为 10⁻⁶~10⁻⁸；surface code 当前实测 10⁻³）
3. **两项 AND 命中**：5-15%。从 v1 的 10-20% 下调，主要因为 web 一手数据进一步证实"≤10⁻⁹" 在所有路线上都是 2029-2030 目标
4. **最可能押对的路径**：Atom Computing 中性原子（最高 scale 上限 + 高效 QEC 码）但需 IPO 或被并购才能交易

**结论**：K2 在 2028 前命中**几乎可断言不会全条件命中**。**比 v1 更悲观**。但"≥100 LQ" 单条件大概率会在 2028-2029 之交命中（IBM Starling 全量交付或 Quantinuum Apollo 早 demo），届时市场可能解读为"K2 部分兑现"并推动板块阶段性上涨——**这是空头时间窗管理的关键风险点**。

### K3：Bluefors/Oxford Instruments 量子相关订单 2027 前同比 >40%
**裁决：大概率不命中且反向证据持续（命中概率 20-30%）**

**v1 已充分覆盖，v2 无重大边际变化**。

### K4：≥3 家制药/化工/材料公司公开披露经济价值案例
**裁决：大概率不命中（命中概率 20-25%）**

**v2 微幅上调（v1 15-20% → v2 20-25%）**：
- **Cleveland Clinic 12,635 原子蛋白**（医疗，2026-05）：虽是研究而非付费产品，但 Cleveland Clinic 是大型医疗机构，已多年与 IBM 签约，**形式上接近 K4 门槛**。
- **Q-CTRL 1D Fermi-Hubbard 材料模拟**（材料/能源，2026-05）：算 K4 范围内的"材料"案例，但消费方是 Q-CTRL 而非材料公司。
- **Boeing 防腐材料合作**（IBM Think 2026 公开）：材料/化工范围，未披露金额。
- 仍**没有**任何制药/化工/材料公司在自家年报 R&D 章节量化披露"用量子节省了 $X / 缩短了 Y 月"。

**结论**：研究层级案例数量正在增加（2026 H1 已出现 3-4 起），但**"客户公司自己披露量化经济价值"的硬门槛仍未跨越**。2027 前 ≥3 家命中概率仍偏低。

### K5：2026 H1 末 IonQ/Rigetti/D-Wave 估值是否崩塌 >50% from peak
**裁决：部分兑现（RGTI/QUBT 已命中），剩 IONQ/QBTS 持续加压（命中概率 70-85%）**

**v2 验证（截至 2026-05-23）**：
- **RGTI**：已 **-54.6%** from 52w 高点 → **K5 已命中**
- **QUBT**：已 **-52.5%** from 52w 高点 → **K5 已命中**
- **IONQ**：**-30.4%**，未到 -50% 阈值
- **QBTS**：**-37.2%**，未到 -50% 阈值

**v2 新增 K5 候选**：
- **Quantinuum IPO（2026 目标 $20B 估值）**：营收 $30.9M（2025）/ $5.2M（2026-Q1），P/S ~650×（v1 时未列入）。若 2026 上市后 6 个月内出现 -50% 回调，**Quantinuum 也将进入 K5 命中名单**。但 IPO 时点和锁仓期未定，时间窗 may 跨入 2027。

**v2 新增观察**：**美股政府量子政策催化剂的反弹风险**——
- 2026 春美国 $2B 量子计划公布后，RGTI 周内 +42.2%
- 2026 春 $100M 量子拨款后，QBTS 单日 +14.23%
- 这类政策 catalyst 在 H2 仍可能反复发生，**空头需用 put spread 而非裸卖空**

**结论**：K5 命中概率从 v1 的 60-75% 上调至 **70-85%**。RGTI/QUBT 已兑现；IONQ/QBTS 在 Q2 财报（2026-07/08）将是关键观察窗口。**K5 主线已基本确认**，未来 12 月维度上还可叠加 Quantinuum IPO 后跌幅。

---

## 3. 支持理由（v2 更新）

1. **K5 主线已部分兑现**（RGTI/QUBT 双双 -50%+），且未触发"量子板块整体崩塌"——说明市场对四傻是个股性偏多于行业性的认知，反向证明 IonQ/QBTS 仍有进一步下行空间。

2. **IBM Q-CTRL 3000× demo 是双刃剑**：短期对 K1 利多（板块情绪修复），但中期更利空四傻——若 IBM 真正确立"主流候选+主流客户" 地位，IonQ/RGTI/QBTS/QUBT 作为"纯量子小公司" 的稀缺溢价进一步消失。

3. **主流候选官方 roadmap 全员把 "≥100 LQ + ≤10⁻⁹" 推到 2029-2030**：IBM、Google、Quantinuum、Atom Computing 路线图惊人一致——**K2 的 ≤10⁻⁹ 在 2028 前几乎不可能命中**。这是 v2 最硬的发现。

4. **Microsoft Majorana 1 论文 Nature 审稿人附 editorial note 明确否定**：业界顶刊罕见地公开否定厂商主张——是空头叙事最硬的科学证据。Microsoft 至今未补交满足异议的额外数据。

5. **PsiQuantum Brisbane 延期 12 个月**：澳洲参议院听证会确认地基公众咨询尚未启动 → "million-qubit by 2027" 自我证伪。

6. **Quantinuum IPO 估值 $20B + 营收脆弱**：90% 来自单一客户 RIKEN，2026-Q1 营收环比萎缩。若以传统 SaaS P/S 30-50× 估值，公允估值仅 $1-1.5B（vs $20B 目标），**回归空间 -90%+**。但 IPO 时点不确定。

7. **Nvidia VC 入股 PsiQuantum + 黄仁勋表态反转**：是 SPAC 量子板块顶部信号还是 Catalyst，二者皆然——short-term catalyst（推升 RGTI/QBTS 等通用代理）+ long-term top（VC 入股通常意味着私募已进入退出窗口）。

8. **国产替代叙事仍成立但需要等回调**：国盾量子估值含十四五预期不便宜，应等 2026-2027 系统性回调 -20%+ 后建仓。

---

## 4. 最大反方观点（v2 更新）

1. **IBM Krishna "2026 内 real-world advantage" 承诺若兑现**：K1 命中概率会从 20-30% 跳到 50-60%。整个空头逻辑会被推翻——量子板块将集体重估。**这是 v2 最大的反方风险**。
2. **Quantinuum IPO 若成功定价 $20B 且开盘上涨**：会拉抬整个 SPAC 量子板块情绪，IONQ/RGTI/QBTS/QUBT 阶段性反弹 50-100% 不奇怪。**对空头是时间杀手**。
3. **散户叙事的非线性**（v1 已列）。
4. **Atom Computing 中性原子 2027-2028 突破**：若官方 ≥100 LQ 提前到 2027 末实现，K2 部分兑现，板块再起。但不影响 ≤10⁻⁹ 部分。
5. **美国国家量子法案 2026 H2 续展或加码**：政府订单 catalyst 会反复推升 RGTI/IONQ（政府收入占比最高）。
6. **国产替代被高估的风险**（v1 已列）。
7. **量子模拟商业化的窗口仍可能比预期更远**（v1 已列）。

---

## 5. Position implications（v2 更新）

### 5.1 看空候选（优先级排序）

1. **QUBT（Quantum Computing Inc）**——已 -52.5%，K5 已命中。剩余下行空间 -30% 至 -60% 仍存在，但性价比已不如前。可获利了结部分，保留 long-dated put 等 PSR 重估。
2. **QBTS（D-Wave）**——尚未 -50%，Q2 财报（2026-08 前后）是关键 catalyst。崩塌目标 ~$1-1.5B 市值（-60%）。
3. **IONQ（IonQ）**——尚未 -50%，Q2 warrant 反向 mark-to-market 是关键触发 + SkyWater $1B 现金支付。崩塌目标 ~$4-5B（-50%）。
4. **RGTI（Rigetti）**——已 -54.6%，K5 已命中。剩余下行空间有限，性价比下降。
5. **LSE:OXIG（Oxford Instruments）**——v1 维持。
6. **(v2 新增) Quantinuum IPO post-IPO**——若 IPO 完成且开盘后 30 天有完整流动性，是 K5 的延续候选。IPO 前不可交易；IPO 后看 lock-up 期与价格走势。**P/S 650× 是看空的核心理由**。

### 5.2 看多候选（v2 维持 + 新增）

1. **国盾量子（SSE:688027）**——v1 维持。
2. **(v2 新增) Atom Computing proxy 押注**（如 IonQ 的 trapped ion 部分通过收购 Oxford Ionics 接入中性原子思想；Microsoft Azure Quantum 接入 Magne）——非首选，等明确 catalyst。
3. **(v2 新增) IBM Watson + Quantum bundle 反向看多**：若 K1 在 2026 内被 IBM 兑现，IBM 公司股票（IBM）是受益方且估值便宜（P/E ~25），可作 K1 命中场景的对冲多头。

### 5.3 等待信号

- **PsiQuantum**（光量子 FTQC，未上市）——若 2026-2027 IPO 是重大事件
- **Bluefors 母公司**（PE 资产）
- **Microsoft Majorana 路线**——等待 follow-up 论文是否补足证据；若 2026-2027 仍无新证据，Microsoft 拓扑路线可视为"已死"

---

## 6. 关键观察窗口（2026 H1-H2，v2 更新）

| 时间 | 事件 | 关键观察 | 对应 K |
|---|---|---|---|
| 2026-06 月底 | H1 收盘股价 | IONQ/QBTS 是否完成 -50% | K5 |
| **2026-07** | **Q-CTRL/IBM 3000× demo 工业界 follow-up 案例** | 是否有材料/化工公司公开引用、估算 ROI | **K1, K4** |
| 2026-07 中 | IonQ Q2 财报 | warrant FV 反向 mark-to-market；SkyWater 进展 | K5 |
| 2026-08 上 | D-Wave Q2 财报 | RPO 扩张；Customer A 替换 | K5、K1 |
| 2026-08 中 | Rigetti Q2 财报 | 108Q 后 QCaaS ARR；C-DAC $8.4M | K5、K2 |
| 2026-08 下 | QUBT Q2 财报 | LSI 整合；ATM 重启 | K5 |
| **2026-Q3-Q4** | **Quantinuum IPO 定价 + 上市** | 估值水平、首日表现、3 个月走势 | **K5 新增** |
| 2026-09 | IBM Quantum Summit | 200 LQ demo / Kookaburra 首跑 | K2 |
| **2026-Q4** | **IBM 是否兑现 Krishna 2026 real-world advantage 承诺** | 是否有具名企业客户 + 量化 ROI 披露 | **K1（critical）** |
| 2026 Q4 | 药企/化工 R&D 年报章节 | BASF/Pfizer/ArcelorMittal/Boeing 量子项目 ROI | K4 |
| 2026 Q4 | Oxford Instruments 半年报 | NanoScience 处置 / NSI Act 结果 | K3 |
| 2026 Q4 | 国盾三季报 | 中电信集采、ez-Q Fridge 出货 | K3 反向、K1 边缘 |
| **2027 Q1** | **Atom Computing Magne 是否如期投运 Denmark QuNorth** | 50 LQ 实物交付（K2 阶段性兑现）| **K2 部分** |
| **2027 H1** | **Microsoft Majorana 是否有 follow-up 论文** | 若仍无 → 拓扑路线死亡 | K2 |

---

## 7. Coverage 闭环（v2）

| Killer Question | 本批材料覆盖度 | v2 verdict | 缺口 |
|---|---|---|---|
| K1（经济价值量子优势 2027 前）| **强**（含 IBM 一手 + Q-CTRL + Cleveland Clinic）| 大概率不命中（20-30%）| 缺各药企/化工自家年报披露 |
| K2（FTQC ≥100 逻辑比特 ≤10⁻⁹ 2028 前）| **强**（含 IBM/Google/Quantinuum/Atom Computing/PsiQuantum/Microsoft 全主流候选）| 大概率不命中（5-15%）| 缺各家未公开的内部 logical error rate 测试数据 |
| K3（制冷机龙头订单 +40%）| 充分 | 大概率不命中且反向（20-30%）| 缺 Bluefors 母公司订单数据（私有 PE） |
| K4（≥3 家药企/化工/材料经济价值案例）| 中（v2 添加 Cleveland Clinic / Boeing / Q-CTRL）| 大概率不命中（20-25%）| 缺各药企/化工年报 R&D 章节量化披露 |
| K5（2026 H1 末四傻估值崩塌）| **充分**（4 家 10-K + 10-Q + 实时股价）| **部分兑现（RGTI/QUBT 已 -50%+）**| 持续追踪 IONQ/QBTS Q2 财报 |

**Coverage 评分（v2）：K1/K2 从 30-50% 升至 70-80%，K3/K5 维持充分，K4 微升**。

---

## 8. Thesis v3 触发条件

以下任一发生时需要起 thesis_v3：
1. **IBM 在 2026 内给出具名企业客户付费 $1M+/年 + 量化 ROI 案例** → K1 重大兑现，看空逻辑被推翻
2. **IONQ/QBTS 任一完成 -50% 崩塌** → K5 全部命中，需重估"是否还有下行空间"
3. **Quantinuum IPO 定价低于 $10B 或开盘破发 -30%+** → K5 候选 1 命中，可扩为新的空头主题
4. **Microsoft 2026 H2 补交 Majorana follow-up 论文且独立验证 MZM 存在**（极小概率）→ M-cluster K2 复活
5. **Atom Computing Magne 2027 Q1 如期投运并附 ≥50 LQ benchmark** → K2 部分兑现，需重估时间窗
6. **任一药企/化工/材料公司年报披露量化经济价值案例** → K4 重大边际变化
7. **国盾或本源完成重大订单/IPO 事件** → 国产替代 thesis 升级

---

## 9. v2 核心一句话总结

> **K5 主线已部分兑现（RGTI/QUBT），剩 IONQ/QBTS 待 Q2 财报触发；K2 在 2028 前命中概率被全主流候选 roadmap 进一步压低至 5-15%；K1 因 IBM Q-CTRL demo + Krishna 承诺微幅上调至 20-30% 但仍未跨越付费门槛；新增 Quantinuum IPO 与 Microsoft Majorana 两个反向标的；2026 H2 IBM 是否兑现 Krishna 承诺是空头逻辑的最大单一风险点。**

---
slug: global-quantum-computing
output_key: 03_narrative_ecology
version: 1
generated: 2026-05-23T00:00:00+08:00
data_freshness: 2026-Q1
data_freshness_basis: findings_external_ibm (2026-05-06 Q-CTRL demo) + findings_external_quantinuum_atom (Quantinuum 2026 IPO 路演) + findings_external_psiquantum_microsoft (Nature editorial note 2024-2025 + Brisbane 延期)
---

# 叙事谱系：全球量子计算

> 生成于 2026-05-23，训练知识占比约 35%（叙事框架来自训练，具体证据来自资料）

## 主流叙事（市场最常见的 3 个框架）

### 叙事 A：「通用量子优势 2027 来临，硬件赢家通吃」

**核心逻辑**（3-5 句）：
1. Google Willow（2024-12 Nature）跨过 sub-threshold（Lambda=2.14），证明 QEC 物理可行；
2. IBM 路线图 Heron→Loon→Kookaburra(2026)→Cockatoo(2027)→Starling(2029 200 LQ) 节点清晰，CEO Krishna 2026 公开承诺"量子 advantage by 2026 end"；
3. Q-CTRL + IBM 2026-05-06 在 Fermi-Hubbard 模拟跑出 3000× speedup（findings_external_ibm），首次出现 "real-world workload" 上的 advantage 迹象；
4. 一旦通用 advantage 兑现，全球数百亿美元化学/材料/金融/物流市场将向量子迁移，硬件龙头（IBM/IonQ/Quantinuum）赢家通吃；
5. 因此 2026-2027 是"上车前夜"，估值再贵也合理。

**主要支持者**：Goldman Sachs Quantum Compute report (2024-2025)、Morgan Stanley、CB Insights、华尔街 SPAC 多头、IBM/IonQ IR 团队、部分中国卖方（中信/中金）

**关键证据**：
- Willow Lambda=2.14（findings_external_google）
- Q-CTRL/IBM Fermi-Hubbard 3000× (findings_external_ibm 2026-05-06)
- Quantinuum Helios 48-94 LQ（findings_external_quantinuum_atom）
- IBM 累计量子营收 $1B (2017-2024)
- Quantinuum IPO 路演中目标 $20B

**脆弱点**：
- Google 自己 2025-11 五阶段成熟度路线图明文承认 **"no quantum computation has yet demonstrated a clear advantage on a real-world problem"**（Stage 3 未达成）
- IBM Krishna "by 2026 end" 承诺与 Hartmut Neven (Google) 的 "commercial within 5 years"（即 2029-2030）存在 3 年错位，至少一方在"管理预期"
- Q-CTRL 3000× demo 仍是 benchmark 而非 ROI 案例，没有客户为这个结果付钱

### 叙事 B：「卖铲人模式 +40% 订单，避免路线赌注」

**核心逻辑**：与其赌哪家硬件路线赢，不如做"加州淘金潮卖铲人"——稀释制冷机（Bluefors/Oxford Instruments NanoScience/Janis）、低温线缆（Maybell）、控制电子（Quantum Machines）、光子集成代工（PsiQuantum/GlobalFoundries）在任意路线胜出时都受益。**核心假设：2026-2028 量子硬件年订单增长 +40%。**

**主要支持者**：英国 LSE 投资圈（OXIG 涨势的拥护者）、PE/VC（Bluefors 母公司 Bregal 持有）、欧洲机构投资者、部分 K3 假设的 prism 多头

**关键证据**：
- Bluefors 估稀释制冷机市占 60%+（训练知识）
- 稀释制冷机交付周期延长至 18-24 个月（市场传闻 + 部分访谈）
- PsiQuantum + GlobalFoundries 合作（findings_external_psiquantum_microsoft）

**脆弱点**：
- **Oxford Instruments 2024 已剥离 NanoScience 业务**，"OXIG 量子卖铲人"叙事 fundamentally 错配
- Bluefors 是私营，**没有公开订单数据**支持"+40%"假设
- 即便订单 +40%，单价不一定 +40%——客户压价能力增强
- IBM/Google 自研稀释制冷机能力提升，可能内部化部分需求

### 叙事 C：「量子模拟先行，化学/材料 2027-2028 PoC 商业化」

**核心逻辑**：通用 FTQC 离我们 5+ 年，但**专用量子模拟（化学/材料/药物发现）**门槛低，2027-2028 应有 ≥3 家化学/制药/材料企业的经济价值案例。

**主要支持者**：McKinsey Quantum Tech Monitor、BCG、Quantinuum/Roche/Boehringer Ingelheim 合作通稿写作者

**关键证据**：
- D-Wave 2025-03 Science 论文 spin-glass 量子动力学模拟（mat-55d3c2）
- Quantinuum InQuanto 化学软件栈 + Roche/BMS 合作
- BASF/Pfizer/ArcelorMittal 名单常见于通稿

**脆弱点**：
- BASF/Pfizer/Roche 全部为 **PoC 阶段，0 个公开 ROI 数字**
- D-Wave 的 Science 论文未与任何客户合同挂钩（10-K 未披露 Jülich $16M 系统购买与该论文的因果）
- Roche 2024 年报量子项目预算未在 R&D 主表中单列（说明体量极小）

---

## 边缘叙事（少数派/反共识）

### 边缘叙事 1：「中国国产替代 + 国家资本套利窗口」

**核心逻辑**：合肥/济南/北京三大量子科学中心 2026-2028 集中放量；国盾量子（SSE:688027）+ 本源量子 + 国仪量子构成"硬件-控制-工程化"三角；十四五最后一年 + 十五五开局 = 2026-2027 国家资本最密集窗口；国产替代率从当前 30% 上升至 60%+，国盾量子作为 A 股唯一标的有套利空间。

**为什么市场不接受**：信息透明度低（年报披露不充分）、A 股流动性有限、外资难以触达、中美关系敏感度高（ITAR 限制反向适用）。

**如果对，意味着**：国盾量子 2027-2028 营收翻 3×，估值套利 +50-100%；但**对美股标的中性偏负**（中国封闭循环，与美股估值无直接传导）。

### 边缘叙事 2：「Microsoft Majorana 是科学欺诈」

**核心逻辑**：Microsoft 2024 Nature 发表 Majorana 1 拓扑量子比特"读出"论文，但 Nature **2025 editorial note 明确声明** "the data presented do not represent evidence of Majorana zero modes (MZMs)"（findings_external_psiquantum_microsoft）。这相当于 Nature 公开否定了 Microsoft 自己最重要的拓扑路线宣传，但市场至今未充分定价此事。

**为什么市场不接受**：editorial note 在 Nature.com 上不显眼；MSFT 体量大（量子部分占总市值 <0.1%），整体股价不受影响；普通投资者无法理解技术细节。

**如果对，意味着**：拓扑路线整体跌价，与拓扑路线挂钩的 PsiQuantum/Xanadu/Pasqal 等光量子标的的"差异化"溢价消失；MSFT 不受影响，但 K2 milestone 集合中拓扑路线节点应直接划掉。

### 边缘叙事 3：「量子永远是 10 年后」（Gil Kalai 派）

**核心逻辑**：Gil Kalai 长期论证量子噪声本质上不可控，QEC 看似 sub-threshold 实则统计学外推（Willow d=7 直接经典验证需 10^25 年）；FTQC 永远在 10 年之后，类似可控核聚变。

**为什么市场不接受**：被视为悲观/反技术；学界主流（Aaronson/Preskill）不认同 Kalai 强结论；但 Aaronson 自己也只敢赌 "2027 年底前 500 qubit + 99.9% fidelity"，远低于商业化门槛。

**如果对，意味着**：所有硬件标的都应按"研发服务公司"估值（PS 5-10×，而非 200-650×），意味着 IONQ/Quantinuum 应跌 80-95%。

---

## 叙事演化轨迹

```
2022-2024 Q3：低谷／怀疑   →   2024-12 Willow Nature       →   叙事 A 起势
2025 Q4 Google OTOC          →   叙事 A 强化（"verifiable advantage"）
2025-11 Google 五阶段路线图  →   叙事 A 内部出现裂缝（"Stage 3 未达"）
2026-05-06 Q-CTRL 3000×      →   叙事 A 再次强化（"real-world workload"）
2026 Q1 D-Wave -81%          →   叙事 C 受质疑（商业化收入证伪）
2026 Q1 Quantinuum 路演       →   叙事 A 估值再创新高（IPO target $20B）
2026 H2（预测）              →   lock-up 解禁 + IBM Cockatoo 跳票概率 → 叙事 A 第一次硬测试
```

**当前叙事状态**：A 是顶部，B 是裂痕显现但未崩塌，C 在 D-Wave Q1 后已开始动摇。整体处于"主流叙事强势但内部矛盾积累"的转折前期。

## 叙事与估值的关系

当前主流叙事 A 暗示的估值逻辑：**"赢家通吃 + 5 年内通用 advantage 商业化 + 全球数百亿市场迁移"**——这隐含 IONQ/Quantinuum 应按 2028E 收入 ~$1-2B、PE ~30× 估值，对应市值 $30-60B；但**前提是叙事 A 完全正确**。

估值框架的关键假设：
1. 5 年内通用 advantage 商业化（≥50% 概率）
2. 赢家通吃格局（≥40% 概率）
3. IBM/Google 不会用云模式压死硬件标的（≥60% 概率）

**三者联合概率（乐观）= 0.5 × 0.4 × 0.6 = 12%**。市场用"完全正确"概率定价了 12% 概率事件——典型的叙事溢价。

## 叙事风险（最危险 → 最可能）

**最危险（小概率大影响）**：
- **Nature 撤回 Microsoft Majorana 论文** → 拓扑路线完全崩塌（概率 5%，影响极大）
- **Aaronson 或 Preskill 公开质疑 IBM advantage demo** → 叙事 A 信用瓦解（概率 10%，影响极大）

**最可能（高概率中影响）**：
- IBM Nighthawk advantage demo 2026 Q4 跳票或被独立验证不成立 → 叙事 A 第一次硬测试（概率 40-50%，影响 -30~-50% sector）
- Quantinuum IPO 定价低于 $15B → 叙事 A 估值溢价被纠正（概率 30%，影响 -20~-40%）
- IonQ/Rigetti lock-up 解禁后内部人减持 ≥30% → 叙事 A 信用受损（概率 25%，影响 -20~-30%）

## 信息来源

- 训练知识（约 35%）—— Gil Kalai 长期争论、Aaronson 博客、Preskill NISQ 框架、半导体/互联网叙事演化类比
- findings_external_google：Willow Lambda=2.14、Quantum Echoes、Google 自承 Stage 3 未达
- findings_external_ibm：Q-CTRL/IBM 3000× demo、Krishna 2026 承诺、IBM 路线图
- findings_external_quantinuum_atom：Quantinuum IPO $20B target + Helios 48-94 LQ
- findings_external_psiquantum_microsoft：**Nature editorial note 否认 MZM 证据**、Brisbane 延期 12 月
- findings_mat-55d3c2：D-Wave Science 论文与 Jülich 合同未挂钩
- findings_mat-2e82b4：D-Wave Q1 -81% 反向证据
- findings_mat-bde95b：国盾量子 2024 年报支撑国产替代叙事

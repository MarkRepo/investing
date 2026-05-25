---
mat_id: external-quantinuum-atom
filename: web-research-2026-05-23
source_type: web-research
quality: high
bias: neutral
addresses: [K1, K2]
---

# Quantinuum + Atom Computing — K1/K2 supplement

> Date cutoff: 2026-05-23. 焦点：K1 (经济价值量子优势 by 2027) & K2 (≥100 逻辑比特 + 逻辑错误率 ≤10⁻⁹ by 2028)。
> 资料来源：公司公告/Nature/Microsoft 博客/IPO S-1/McKinsey/HPCwire 等 web 一手或权威转述（见末尾 URL 清单）。

## Quantinuum

### 当前 logical qubit 数 & 逻辑错误率
- **2024-04 (H2-32q)**：与 Microsoft 联合演示 4 逻辑比特，逻辑错误率比物理低 **800×**（active syndrome extraction，首次商用级 logical qubit demo）。
- **2024-09 (H2-56q)**：升级到 **12 逻辑比特**，circuit error rate 较物理低 22×；用 2 个 logical qubit + AI + HPC 算化学反应中间体基态能量。
- **2025-11 (Helios)**：98 物理 qubit → **48 逻辑 qubit**（标准编码）；论文配套实验做出 **94 logical qubit 的 GHZ 态**（near-2:1 physical-to-logical 比例，行业最高）。逻辑层 SPAM fidelity 99.99%，better-than-break-even。
- **当前逻辑错误率**：~10⁻³ 到 10⁻⁴ 量级（per logical operation / per cycle），距 K2 要求的 10⁻⁹ 仍有 **5-6 个数量级**差距。

### H 系列 / Helios 性能 KPI（2025-11 Helios commercial launch）
| KPI | Helios | 同代对比 |
|---|---|---|
| 物理 qubit | 98 (全连通) | H2 = 56 |
| 2-qubit gate fidelity | **99.921%** | 商用最高 |
| 1-qubit gate fidelity | 99.9975% | 商用最高 |
| Logical SPAM | 99.99% | better-than-break-even |
| Quantum Volume | 2,000,000+ (prototype) | 行业纪录 |
| 新增 | Real-time control engine + Guppy (Python-based) | 让 hybrid quantum-classical 可编程 |

### Microsoft 合作的 logical qubit 突破时间线
- 2024-04：4 logical qubits, 800× error suppression（H2-32q）。
- 2024-09：12 logical qubits, 22× error suppression + chemistry simulation（H2-56q）。
- 2025-11：Helios 上 48-94 logical qubits, GHZ 态纪录。
- 2025-07：Microsoft + Atom Computing 公布 **Magne**（50 logical qubit 中性原子）落地 Denmark QuNorth，2027 初投运 — 与 Quantinuum 在 Level 2 赛道上**正面对垒**。

### Roadmap → K2
- **Sol (2027)**：~192 物理 / ~96 logical (2D-grid)。
- **Apollo (2029)**：千级物理 + 数百 logical，full FT，目标 millions of gates。
- Quantinuum 自己写明 "2027 cross 100 logical qubit threshold"（Sol → Apollo 过渡期），但 **10⁻⁹ logical error rate 官方 target 是 2029-2030**，2028 前命中 K2 全部条件概率不高（逻辑 qubit 数量可能勉强达标，error rate 远不够）。

### 商业客户披露（来自 IPO S-1）
- 2025 全年营收：$30.9M（亏损 $192.6M）。
- 2026-Q1 营收：$5.2M（亏损 $136.6M） — **环比明显萎缩**。
- 客户集中度极高：**RIKEN 占 2025 全年营收 90%**；2026-Q1 RIKEN 7%、US Gov 24%、其余分散。
- 商业客户名单：Honeywell、Airbus、BMW、HSBC、JPMorgan Chase（但多为 POC/订阅，未披露大单）。
- **IPO**：2026 已递交 S-1，目标估值 **$20B+**（vs 2025-09 私募 $10B pre-money）。

### K1/K2 评分（Quantinuum）
- **K1 (2027 前经济价值量子优势)**：**中性偏负**。Helios 已可演示 "scientific advantage"，但客户营收数据（90% 集中 RIKEN，2026-Q1 $5M）显示**没有付费市场把 quantum compute 当生产工具买**。McKinsey 称 2026 是 "commercial tipping point"，但实际付费证据微弱。2027 前出现真正"经济价值量子优势"概率 ~25%。
- **K2 (2028 前 ≥100 logical qubit + 10⁻⁹ error rate)**：**逻辑 qubit 数量可达，但 error rate 几乎不可能**。Sol (2027) 给到 ~96 logical，Apollo (2029) 给到数百，但官方自承 FT 目标线在 2029-2030。2028 前同时命中两项概率 ~10%。

---

## Atom Computing

### 1180-qubit demo 实际成绩
- **2023-10**：1225-site 阵列装入 **1180 个物理 qubit**，首家突破 1000-qubit。
- **关键 caveat**：这是 "qubit count" 而非可用算力——单 qubit 相干时间和 2-qubit gate fidelity 当时未达 Helios/H2 级别。
- **2024-11 (与 Microsoft)**：在中性原子上做出 **24 个 logical qubit 纠缠**（截至当时业界最多），并用 28 logical qubit 跑 Bernstein-Vazirani 算法，logical 结果优于 physical。
- **2025-2026**：Nature 论文报告 448-atom 阵列在 fault-tolerance threshold 之下 **2.14×**，atom loss detection + ML decoder。

### 中性原子 vs 超导/离子阱 logical qubit 效率
| 维度 | 中性原子 (Atom Computing) | 离子阱 (Quantinuum Helios) | 超导 (IBM/Google) |
|---|---|---|---|
| Physical qubit scale | 1000-10000+ (路标) | 98 (Helios), ~1000 (Apollo) | 1000+ (Condor 类) |
| Physical-to-logical 比 | ~24:1 (24L from ~1200P, Magne) | **~2:1 (Helios)** | ~10:1+ (Google distance-7) |
| 2-qubit gate fidelity | 99.5%+ (尚未到 99.9%) | **99.921%** | 99.5-99.9% |
| 可扩展性物理上限 | **最高**（光镊可阵列扩展） | 中（trap engineering 限） | 中（cryo + 互连） |
| QEC code 灵活度 | 高（运动 atom + Rydberg） | 高（trapped ion all-to-all） | 中 |
- 中性原子优势：**scale**（可扩到 10k+ physical）+ **encoding efficiency**（QuEra 等团队近期 demo 编码率 >1/2，逻辑错误率理论可到 10⁻¹³/cycle）。
- 中性原子劣势：物理 gate fidelity 暂落后离子阱，**logical qubit 数量需要大物理 qubit 池才能换出来**。

### Roadmap → K2
- **Magne (2027 Q1, with Microsoft, Denmark QuNorth)**：50 logical / 1200 physical。是 **K2 路径上最具体可验证的里程碑**。
- **次代系统 (2027-2028)**：目标 >10,000 物理 → **>100 logical qubit**（公司公开预期）。
- 配合 QuEra/Harvard 系学界 demo 的 10⁻¹³ 量级 logical error rate 可行性，**Atom Computing 在 K2 上技术叙事最契合**。

### K1/K2 评分（Atom Computing）
- **K1 (2027 前经济价值量子优势)**：**偏负**。Magne 2027 Q1 投运但定位科研（Novo Nordisk Foundation + EIFO 80M EUR 资助），**不是付费商业算力**；Atom Computing 商业客户披露远少于 Quantinuum。2027 前命中 K1 概率 ~15%。
- **K2 (2028 前 ≥100 logical qubit + 10⁻⁹ error rate)**：**两项中各有 50%+ 概率，但同时命中需要错误率从 ~10⁻³ 急降到 10⁻⁹**。次代系统若按公司预期 2027-2028 出货 100+ logical qubit 是合理的；error rate 10⁻⁹ 需要 QuEra 系新型 high-rate code 落地。综合 ~20-25%。

---

## 综合判断

### 哪家最有可能 2028 前命中 K2
- **Atom Computing 概率略高于 Quantinuum**（~22% vs ~10%）。
- 原因：中性原子是**唯一能在 2027-2028 时间窗内同时扩到 >10k 物理 qubit + 跑高效 LDPC 码**的硬件路线；Quantinuum 离子阱受 trap 工程限制，Apollo (2029) 才到 hundreds of logical qubit。
- 风险：10⁻⁹ 是**极高门槛**。两家官方 roadmap 都把 "fully FT" 放到 2029-2030 而非 2028。**K2 的 error rate 部分大概率会落空**，更可能是 2029-2030 实现，而不是 2028 前。

### 哪家最有可能 2027 前命中 K1
- **Quantinuum 概率略高于 Atom Computing**（~25% vs ~15%）。
- 原因：Quantinuum Helios 已商用、有客户名单、IPO 在即，**变现机制存在**；Atom Computing 主路径仍偏科研合作。
- 但 Quantinuum 2026-Q1 营收 $5M / 客户集中度 90% 在单一客户，说明**"经济价值量子优势"还停留在 POC 阶段**——付费方在为"未来的优势"买单而非现在的优势。
- **更现实判断**：2027 前两家都难以严格满足 "经济价值量子优势"（即 quantum 解某问题比 classical 便宜或快得多到产生付费需求），更可能是 2028-2029 出现首个明确案例。

### 一句话结论
- **K1（2027 前）**：保守视角下两家都不命中（合计 P ≈ 30-35%）；Quantinuum 路径更近商业但客户结构脆弱，Atom Computing 路径技术潜力更大但商业化更慢。
- **K2（2028 前）**：两家都不会在 2028 前同时满足 ≥100 logical qubit **且** ≤10⁻⁹ error rate（合计 P ≈ 25%）；中性原子是最可能首先命中 logical qubit 数量条件的路径，但 error rate 10⁻⁹ 是 2029 之后的目标线。
- **对投资框架的含义**：K1/K2 在 2027/2028 时点**大概率不命中**，应把硬节点放到 2029-2030；如果只能选一家押 K2，押 Atom Computing 路径（尽管未上市，只能通过 Microsoft Azure Quantum / QuEra / IonQ 等 proxy 表达）。

---

## 引用 URLs

**Quantinuum / Helios / Microsoft 合作**
- https://www.quantinuum.com/press-releases/quantinuum-announces-commercial-launch-of-new-helios-quantum-computer-that-offers-unprecedented-accuracy-to-enable-generative-quantum-ai-genqai
- https://www.quantinuum.com/blog/introducing-helios-the-most-accurate-quantum-computer-in-the-world
- https://www.quantinuum.com/blog/helios-delivers-quantum-advantage-with-real-world-impact
- https://www.hpcwire.com/2025/11/05/quantinuum-introduces-helios-quantum-system-as-roadmap-advances-toward-apollo/
- https://thequantuminsider.com/2025/11/06/illuminating-helios-quantinuums-shiny-new-quantum-computer-gets-sunny-reception/
- https://www.nextplatform.com/2025/11/10/quantinuum-makes-another-milestone-on-commercial-quantum-roadmap/
- https://blogs.microsoft.com/blog/2024/04/03/advancing-science-microsoft-and-quantinuum-demonstrate-the-most-reliable-logical-qubits-on-record-with-an-error-rate-800x-better-than-physical-qubits/
- https://azure.microsoft.com/en-us/blog/quantum/2024/09/10/microsoft-and-quantinuum-create-12-logical-qubits-and-demonstrate-a-hybrid-end-to-end-chemistry-simulation/
- https://www.quantinuum.com/press-releases/quantinuum-unveils-accelerated-roadmap-to-achieve-universal-fault-tolerant-quantum-computing-by-2030
- https://www.quantinuum.com/blog/quantinuum-overcomes-last-major-hurdle-to-deliver-scalable-universal-fault-tolerant-quantum-computers-by-2029

**Quantinuum IPO / 财务**
- https://www.constellationr.com/insights/news/quantinuums-ipo-what-you-need-know
- https://thenextweb.com/news/quantinuum-ipo-quantum-computing-honeywell
- https://techfundingnews.com/honeywell-backed-quantinuum-files-for-us-ipo-at-up-to-20b-valuation/
- https://startupfortune.com/quantinuums-ipo-filing-tests-investor-patience-with-quantum-computing/
- https://www.quantinuum.com/press-releases/honeywell-announces-600-million-capital-raise-for-quantinuum-at-10b-pre-money-equity-valuation-to-advance-quantum-computing-at-scale

**Atom Computing / Magne / 中性原子 QEC**
- https://quantumcomputingreport.com/atom-computing-previews-an-1180-qubit-neutral-atom-processor/
- https://atom-computing.com/wp-content/uploads/2025/01/Atom-Computing-Whitepaper-2025.pdf
- https://arxiv.org/html/2411.11822v1
- https://www.nature.com/articles/s41586-025-09848-5
- https://www.nature.com/articles/s41534-025-01095-w
- https://thequantuminsider.com/2025/06/26/neutral-atom-quantum-processor-demonstrates-repeatable-error-correction/
- https://thequantuminsider.com/2026/04/21/quera-led-study-points-to-ultra-high-rate-quantum-error-correction-moving-closer-to-practical-hardware/
- https://thequantuminsider.com/2025/07/17/microsoft-and-atom-computing-partner-on-level-2-quantum-system-for-nordic-users/
- https://quantumcomputingreport.com/denmarks-qunorth-to-acquire-50-logical-qubit-magne-quantum-computer-from-atom-computing-and-microsoft/
- https://www.datacenterdynamics.com/en/news/microsoft-and-atom-computing-to-build-worlds-most-powerful-quantum-computer-in-denmark/
- https://novonordiskfonden.dk/en/news/eifo-and-the-novo-nordisk-foundation-acquire-the-worlds-most-powerful-quantum-computer/
- https://spectrum.ieee.org/neutral-atom-quantum-computing

**Industry context**
- https://www.mckinsey.com/capabilities/mckinsey-technology/our-insights/mckinsey-quantum-technology-monitor-2026-a-commercial-tipping-point
- https://postquantum.com/industry-news/mckinsey-quantum-monitor-2026/
- https://postquantum.com/quantum-computing-companies/quantinuum/
- https://postquantum.com/quantum-computing-companies/atom-computing/

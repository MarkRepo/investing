---
mat_id: external-psiquantum-microsoft
filename: web-research-2026-05-23
source_type: web-research
quality: high
bias: neutral
addresses: [K1, K2]
---

# PsiQuantum + Microsoft Majorana — K1/K2 supplement

> 评估时点：2026-05；评估对象：两条"非主流但常被吹爆"的 FTQC 路线（光子 / 拓扑）能否在 2027 前命中 K1（经济价值量子优势），2028 前命中 K2（≥100 逻辑比特、逻辑错误率 ≤1e-9）。

---

## PsiQuantum（光子 FTQC）

### 制造合作 & 实际进度

- **代工伙伴：GlobalFoundries（不是 SkyWater）**。Omega 芯片设计在 GF 纽约 Fab 的 300 mm 硅光平台、45 nm 工艺上流片。公开报道里没有任何 SkyWater 参与 Omega 量产的实证——SkyWater 更多是 DARPA US2QC 项目里给其它光子初创做 MPW，**用户问题里的"SkyWater 合作"应视为传闻或误传**。
- **Omega 芯片 (2025-02 公布)**：包含单光子源、超导单光子探测器、基于 BaTiO₃（钛酸钡）的下一代光开关；论文式 benchmark：
  - single-qubit SPAM fidelity **99.98%**
  - chip-to-chip 互连 fidelity **99.72%**
  - 两比特 fusion gate fidelity **99.22%**
  - 量子干涉可见度 **99.5%**
  - 注意：这些都是**单元器件 / 单 fusion 级别**的指标，不是"已经搭出一台 N 逻辑比特机器"的指标。
- **资本层（2025-09 Series E）**：$1B 新融资，BlackRock / Temasek / Baillie Gifford 领投，NVentures（英伟达 VC 臂）、QIA、Macquarie、Ribbit 等跟投；估值 **$7B**，累计融资接近 $2B，是全球融资最多的量子公司。
- **Nvidia / 黄仁勋表态**：2025 年明显转向——Huang 公开承认量子"到达拐点，比预期更快进入实用"，Nvidia 与 PsiQuantum 在 GPU-QPU 集成、算法、光子层协同研发；这是 2024 年 1 月 Huang "实用量子要 15-30 年"言论的明确反转。**意义**：来自最有动机看空（避免 AI 叙事被分流）的玩家的认知调整，对 K1 是适度利好；但仍是"押注"而非"验证"。
- **Brisbane 站点**：原本激进计划 2025 开工、2027 末通电运行第一个 utility-scale 子系统、2029 全面 fault-tolerant。**最新事实**：截至 2025-12 澳洲参议院 Estimates 听证会，Brisbane Airport 站点的开发草案公众咨询尚未启动（至少要 2 个月）；项目可能比原计划晚 12 个月；政府拨款也未提取。Startup Daily 报道两台机器"时间表都更接近 2030"。
- **Chicago 站点**：2025 在 Illinois Quantum and Microelectronics Park 破土，进度比 Brisbane 更快，但官方表态仍是 2027 出第一台"useful"版本，2029 才完整 fault-tolerant。

### 当前已 demo 的 photonic qubit 数 / fidelity

- **没有任何公开数据**显示 PsiQuantum 已构建出哪怕几十个 fusion-network 集成、可用的 photonic logical qubit。Omega 是"manufacturable building block"的可生产性证明，**不是逻辑比特演示**。
- 对比：Quantinuum + Microsoft 在 H2 离子阱上已经做出 **12 个 entangled logical qubits，22× 逻辑/物理改善比**（2024-09），Google Willow 在 surface code 上证明了逻辑错误随码距下降。**PsiQuantum 在 logical qubit 的实证轴上落后这些玩家一个台阶。**

### K1/K2 评分

- **K1（2027 经济价值量子优势）**：PsiQuantum 自身不构成关键路径——它的目标就是 2027 末"先点亮"，2029 才 useful。即使按官方剧本，PsiQuantum 也不会成为 2027 经济价值的来源。Brisbane 已显著延期，更进一步弱化。**对 K1 评分：弱负面（confirms K1 多半要靠超导/离子阱）**。
- **K2（2028 前 ≥100 逻辑比特、LER ≤1e-9）**："million qubit by end-of-2027" 主张在物理上不等于 "≥100 logical qubits by 2028"——百万物理光子比特组装成 ~100 个逻辑比特技术上是合理的目标，但当下没有任何 photonic logical qubit 工程数据，K2 要求的 1e-9 LER 在光子架构上未被实验证实过。**结论：PsiQuantum 命中 K2 概率 <15%**；million-qubit 2027 主张本身在工程现实层面（Brisbane 延期、Chicago 也指向 2029）**不再 credible**，应折算为"~2029-2030 才有第一台 utility-scale 系统、~2031 才可能 ≥100 logical qubits"。

---

## Microsoft Majorana 1（拓扑路线）

### 实际 demo qubit 数（8 是否真实）

- 官方宣传：芯片"为 100 万比特设计"，**当前实际 8 个拓扑比特**。
- 真实状态：**8 这个数字是"该器件有 8 个能容纳拓扑模式的纳米线位点"**——**不是"已经独立、可寻址、可纠错的 8 个 qubit"**。Nature 同期论文做的是**单个**器件的"interferometric readout of fermion parity"（奇偶读出），并未演示双比特门、纠缠、或多比特电路。
- Microsoft 用 InAs/Al 异质结构，在毫开尔文 + 磁场调谐下尝试形成拓扑超导纳米线、在两端产生 Majorana Zero Modes (MZMs)；"qubit"由两根纳米线 = 4 个 MZMs 组成。

### 学界质疑现状

这是 2025 年量子物理界最大的公开争议事件：

- **Nature 编辑部异常声明**（这是关键）：Nature 在论文发表时罕见地附带 editorial note，明确写"the results in this manuscript do not represent evidence for the presence of Majorana zero modes in the reported devices"。即 **Nature 自己的两位审稿人结论是：本论文不构成 MZM 存在的证据**。Microsoft 把这篇"只是奇偶读出"的论文当作"我们有拓扑 qubit"的发布会基础，**这是核心争议点**。
- **Henry Legg (圣安德鲁斯大学) 等**：Microsoft 的 Topological Gap Protocol (TGP) 测试存在 false positive，可以被"doppelgangers"（电子学特征像 Majorana 但没有拓扑保护的态）骗过。
- **UNSW 团队 (2025-06 preprint)**：即使 MZM 真实存在，**退相干时间 (decoherence time) 太短**，不足以支撑 qubit 工作；需要重大的材料突破才能达到可用 decoherence。
- **Scott Aaronson、Science、Science News、Physics World、APS Physics** 多家专业刊物 2025 年 2-7 月持续登载怀疑文章；2025-07 HPCwire 又有"another challenge"报道。
- **Microsoft 回应（Chetan Nayak）**："我们只展示了所做工作的一小部分"——典型的"trust me bro"姿态，**至今未补交满足审稿人异议的额外数据**。

### Microsoft 路线图 (M2 / M3)

- Microsoft 官方 quantum roadmap 用 Foundational / Resilient / Scale 三级表述，**不公开 "M2/M3" 这样的代号**——这是社区/媒体的非正式说法，没有具体规格或日期。
- 官方表述：Majorana 1 → "fault-tolerant prototype in years, not decades"（DARPA US2QC Phase III）。Microsoft 自己 vague 地说 "2027-2029 practical quantum"，但**到 2026/05 没有发布过 M2 的物理芯片**。
- 与 Quantinuum 的合作 (2024-09)：12 logical qubits、22× 改善——**注意：这是离子阱（H2）+ Microsoft 软件 qubit-virtualization，不是 Majorana 硬件**；这部分是 Microsoft 的"plan B"——用别人家硬件刷 logical qubit 数。Quantinuum Helios (2025) 计划支持"≥10 highly reliable logical qubits"。

### K2 评分

- **Majorana 自身命中 K2（2028 前 ≥100 拓扑 logical qubits + LER ≤1e-9）：概率极低（<5%）**。
  - 物理基础（MZM 存在性）未被独立验证，Nature 审稿人明确说"非证据"。
  - 当前演示是单器件奇偶读出，距离哪怕 1 个完整 working topological qubit 都还有距离，更不用说 100 个 logical qubits（每个 logical qubit 还要 surface-code-like 编码层）。
  - 即使物理上 MZM 真实，UNSW 指出 decoherence 时间不足，需要新材料突破。
  - 从 8 物理点 → 100 logical qubits 需要 2-3 个数量级的硬件 + 1 个完整 QEC 层，**在 2.5 年内完成不现实**。
- **Microsoft "通过 Quantinuum 路径"间接命中 K2**：可能，但那本质上是 ion-trap 路线的成果，不是拓扑路线的胜利；且 Quantinuum Helios 2025 目标只是 ≥10 logical qubits，到 2028 达到 100 + LER 1e-9 仍极具挑战。

---

## 综合判断：两条非主流路线 2028 前命中 K2 的可能性

| 路线 | 当前最大 logical qubit demo | 物理基础是否被独立验证 | 工程交付是否按计划 | 2028 前 ≥100 LQ + LER 1e-9 概率 |
|------|---------------------------|--------------------|----------------|------------------------------|
| PsiQuantum 光子 | 0（无 logical qubit 演示） | 是（photon、fusion gate 标准物理） | **否**（Brisbane 延期 ~12 个月，时间表滑向 2029-2030） | **<15%** |
| Microsoft Majorana | 0（8 是物理点位、非可用 qubit） | **否**（Nature 审稿人明确否定） | 路线图缺乏具体节点 | **<5%** |

**总体结论**：

1. **K1（2027 经济价值量子优势）**：这两条路线**都不是 K1 的关键贡献者**。若 K1 在 2027 前命中，最可能来自 IBM Heron/Kookaburra + 量子-经典混合（IBM 自承诺 2026 demonstrate quantum advantage、2027 fault-tolerant modules），或 Google Willow 后续 + 离子阱（Quantinuum/IonQ）。PsiQuantum 自己的官方目标也只是 2027 末"点亮"。
2. **K2（2028 前 ≥100 LQ + LER ≤1e-9）**：
   - PsiQuantum：million-qubit-2027 主张**已被自身的 Brisbane 延期实质性证伪**；纵使 Chicago 进度更好，也只指向 2029，与 K2 时间窗错位。
   - Microsoft Majorana：拓扑路线在 **物理可行性尚未被独立验证**的阶段，2028 命中 K2 不构成现实可能。
   - **K2 在 2028 前命中要看 IBM Starling-路径压缩（2029→2028？）或 Quantinuum/Atom Computing/Google 的中性原子/超导/离子阱叠加 demo**，**不太可能押在光子或拓扑上**。
3. **投资 implication**：把 PsiQuantum / Majorana 当 K1/K2 的"surprise upside"是不理性的。它们的真实价值在更长时间窗（2029-2032）。围绕 K1/K2 的近场叙事应以 IBM / Quantinuum / Google / 中性原子（QuEra、Atom Computing）为锚。

---

## 引用 URLs

PsiQuantum / Omega / Brisbane / 融资 / Nvidia：
- https://www.psiquantum.com/omega
- https://www.businesswire.com/news/home/20250226714082/en/PsiQuantum-Announces-Omega-a-Manufacturable-Chipset-for-Photonic-Quantum-Computing
- https://thequantuminsider.com/2025/02/26/psiquantum-announces-omega-a-manufacturable-photonic-quantum-computing-chipset/
- https://www.psiquantum.com/news-import/psiquantum-1b-fundraise
- https://thequantuminsider.com/2025/09/10/psiquantum-raises-1-billion-to-build-million-qubit-scale-fault-tolerant-quantum-computers/
- https://www.sourcery.vc/p/breaking-psiquantums-1b-series-e
- https://www.datacenterdynamics.com/en/news/psiquantum-raises-1bn-in-funding-including-from-nvidias-venture-capital-arm/
- https://www.psiquantum.com/news-import/psiquantum-to-build-worlds-first-utility-scale-fault-tolerant-quantum-computer-in-australia
- https://www.startupdaily.net/topic/global-tech/psiquantums-brisbane-build-is-already-running-very-late/
- https://thequantuminsider.com/2025/05/19/nvidia-eyes-stake-in-psiquantum-signaling-a-strategic-shift-toward-quantum/
- https://time.com/7319603/nvidia-ai-quantum-computing/
- https://en.wikipedia.org/wiki/PsiQuantum

Microsoft Majorana 1 + 学界质疑：
- https://azure.microsoft.com/en-us/blog/quantum/2025/02/19/microsoft-unveils-majorana-1-the-worlds-first-quantum-processor-powered-by-topological-qubits/
- https://news.microsoft.com/source/features/innovation/microsofts-majorana-1-chip-carves-new-path-for-quantum-computing/
- https://en.wikipedia.org/wiki/Majorana_1
- https://www.science.org/content/article/debate-erupts-around-microsoft-s-blockbuster-quantum-computing-claims
- https://www.nature.com/articles/d41586-025-00683-2
- https://www.nature.com/articles/d41586-025-00829-2
- https://www.sciencenews.org/article/microsoft-topological-quantum-majorana
- https://physicsworld.com/a/experts-weigh-in-on-microsofts-topological-qubit-claim/
- https://link.aps.org/doi/10.1103/Physics.18.68
- https://scottaaronson.blog/?p=8669
- https://thequantuminsider.com/2025/03/10/major-debate-continues-to-swirl-around-majorana-findings/
- https://www.hpcwire.com/2025/07/02/another-challenge-to-microsofts-majorana-quantum-roadmap/
- https://postquantum.com/industry-news/microsofts-majorana-1-hype/

Microsoft + Quantinuum logical qubit / 路线图 / FTQC 行业对照：
- https://azure.microsoft.com/en-us/blog/quantum/2024/09/10/microsoft-and-quantinuum-create-12-logical-qubits-and-demonstrate-a-hybrid-end-to-end-chemistry-simulation/
- https://www.quantinuum.com/press-releases/quantinuum-and-microsoft-announce-new-era-in-quantum-computing-with-breakthrough-demonstration-of-reliable-qubits
- https://quantum.microsoft.com/en-us/vision/quantum-roadmap
- https://www.ibm.com/quantum/blog/large-scale-ftqc
- https://www.ibm.com/roadmaps/quantum/2026/
- https://www.riverlane.com/blog/quantum-error-correction-our-2025-trends-and-2026-predictions

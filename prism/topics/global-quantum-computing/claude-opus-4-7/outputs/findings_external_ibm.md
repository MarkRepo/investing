---
mat_id: external-ibm
filename: web-research-2026-05-23
source_type: web-research
quality: high
bias: neutral
addresses: [K1, K2]
---

# IBM Quantum — K1/K2 supplement

## 1. 当前公开 roadmap 节点

IBM 在 2025-06 大幅刷新 roadmap，并在 2025-11-12 Quantum Developer Conference 公布 Nighthawk/Loon；目标终点：2029 年 Starling 系统（200 logical qubits / 100M operations），2033 年 Blue Jay（2000+ logical qubits / 1B operations）。

| 年份 | 处理器 / 系统 | 关键里程碑 | 状态 |
|---|---|---|---|
| 2023 | Heron r1 | 133 physical qubits | 已交付 |
| 2024 | **Flamingo** | 462 qubits，引入芯片间 quantum link | 已交付 |
| 2024-2025 | Heron r2 | 156 qubits；2-qubit gate fidelity >99.9%（>50% pairs）| 已交付，云上运行 |
| **2025** | **Nighthawk** | **120 qubits，square lattice + 218 tunable couplers，可跑 5,000 two-qubit gates 电路**（年底上云）| 2025-11 公布，年底交付 |
| **2025** | **Loon** | qLDPC 架构验证机（~112 qubits）；多层布线、C-couplers、快速 reset；FPGA decoder <480 ns | 2025 末完成封装；研究用，非商用 |
| 2026 | Nighthawk + | 同款芯片扩到 7,500 two-qubit gates；目标演示"量子优势" | 计划 |
| **2026** | **Kookaburra** | **首个 modular FT 处理器，logic+memory 整合，1,386 qubits/模块；可串 3 片→4,158 qubits**；首次在 qLDPC memory 中存编码态 | 计划 |
| 2027 | Cockatoo | 用 L-couplers 串接两个 Kookaburra → 分布式量子计算 | 计划 |
| 2027 | Nighthawk + | 10,000 two-qubit gates | 计划 |
| 2028 | Starling 前体 | 跨模块 magic state injection 演示 | 计划 |
| **2029** | **Starling** | **200 logical qubits，100M+ quantum operations** | 部署于 Poughkeepsie 新数据中心 |
| 2033+ | Blue Jay | 2,000+ logical qubits，1B+ operations | 远景 |

**逻辑比特路径与错误率目标**：
- IBM 已从 surface code 切到 **qLDPC code**，宣称物理 qubit overhead 降低 ~90%
- 官方 roadmap **未公开具体 logical error rate 数字目标**（如 10⁻⁶ / 10⁻⁹），只承诺"orders-of-magnitude improvement vs surface code"
- 目标 logical clock rate 在 Starling 一代下"100M operations / 200 logical qubits" → 单 qubit-operation 必须低于 10⁻⁸ 才不被错误吞掉，IBM 内部隐含目标可推断在此量级

## 2. K1 命中度证据（经济价值量子优势 / 付费 $1M+/年）

**业绩与商业证据**：
- IBM 累计签约 quantum 业务 **~$1B（2017Q1-2024Q4）**，平均 ~$31M/季度；CNBC 2025-02 首次披露
- 2020-2025/6 IBM 拿下全球量子 QPU 披露 deal value 的 **47%**，按金额第一
- IBM Quantum Network 准入门槛：**Flex / Premium / On-Prem 合同 ≥ $250,000** 即加入，远低于 $1M
- 已部署 ~80 套量子系统，其中 **13 套 utility-scale (100+ qubits)** 分布于 Poughkeepsie、德国数据中心和客户现场（含 RIKEN、Cleveland Clinic）
- 2026-Q1 IBM 总营收 $15.9B，+9.5% YoY，公司层面正向，但 quantum 单独披露收入仍未列项

**$1M+/year 付费且"经典做不到"的具名披露**：
- **Q-CTRL × IBM（2026-05-06）**：在 IBM Quantum 平台上的 120-qubit Nighthawk 跑 1D Fermi-Hubbard 材料模拟，2 分钟 vs 经典 100+ 小时，宣称 **3,000× 加速**，自称首次"practical quantum advantage"。被 Q-CTRL 框定为商业里程碑，但 Q-CTRL 是合作伙伴，非典型最终客户
- **Cleveland Clinic + RIKEN + IBM（2026-05-05）**：12,635 原子蛋白量子模拟，史上最大；属于研究合作（Cleveland Clinic 与 IBM 是 multi-year onsite Q-System 合作伙伴），未公开是否到 $1M/年体量
- **Boeing**（IBM Think 2026 演讲）：用 IBM Quantum 做防腐材料/涂层研发（背景：航空业每年 $20B 防腐成本）；具体合同金额未披露
- IBM CEO Krishna 在 IBM Think 2026 **明确预测 2026 年内出现首次 real-world quantum advantage**

**结论（K1）**：
- 截至 2026-05，"付费 $1M+/年 + 经典做不到"的具名案例**尚无硬证据**；最接近的是 Q-CTRL 的 3,000× 演示，但消费方是研究/工具合作，不是终端企业按年付 $1M+ 使用
- IBM 累计 $1B 签约说明客户付费意愿存在，但年化 ~$125M / 全行业份额，多以预购机时和 Premium Plan 为主，非"问题驱动"价值定价
- **K1 在 2027 前命中可能性：中性偏负面**——需在 2026-2027 看到至少 1 个非 IBM 系且非研究合作的企业客户公开承认"用 IBM 量子机解掉了无法用经典解的商业问题、且付费 $1M+/年"

## 3. K2 命中度证据（2028 前 ≥100 logical qubits + 错误率 ≤10⁻⁹）

**已公布的最大 logical qubit demo**：
- IBM 至 2026-05 **尚未公开宣布"X logical qubits 同时运行"的实测**
- 路线图上首次 logic+memory 集成模块是 2026 Kookaburra，但单模块 logical qubit 数量未公开承诺；首次跨模块 logical 操作要等 2027 Cockatoo
- 业内 logical qubit 领先者目前是 Quantinuum / Google / Atom Computing 在 2024-2025 公布的"几十个 logical qubits"演示，IBM 在 logical 计数公开比拼中**反而相对低调**

**已公布的最佳 logical 错误率**：
- IBM 公开的硬指标主要是 **physical 2-qubit gate fidelity 99.9%+**（Heron r2）
- 2025-11 公布 FPGA decoder 在 <480 ns 完成解码，比同行快 ~10×（这是吞吐量，不是 logical error rate 本身）
- **官方未给出 logical error rate 实测**；仿真层面声称 qLDPC 比 surface code "好几个数量级"

**距 K2 阈值（100 logical / 10⁻⁹）的差距**：
- 数量上：IBM 路线图 200 logical qubits 是 **2029 年 Starling 系统**目标 → 2028 年达到 ≥100 logical qubits 是 IBM 自己 roadmap 上的**前一年**（Starling 前体的 magic-state-injection 演示节点），存在但极为激进
- 质量上：10⁻⁹ logical error rate 在 IBM 公开材料中**从未承诺时间表**，业界普遍认为 qLDPC + Starling 一代能达到的 logical error rate 大概在 10⁻⁶ - 10⁻⁸ 区间，要打到 10⁻⁹ 需要更大 code distance 或叠加 magic state distillation
- **K2 在 2028 前命中可能性：低**——IBM 自己 roadmap 上 100 logical qubit 在 2028（前置态），10⁻⁹ 错误率几乎一定要到 2029-2030 Starling 全量交付才有可能

## 4. 反常识 / 限制

**IBM 营销叙事 vs 学术界质疑**：
- IBM 2024 年的 "quantum utility" 论文（Nature, Eagle 127-qubit）被 **多个团队用经典张量网络 / belief propagation 在数小时内复现**，含 Caltech、EPFL 等。学术界默认 IBM "utility" ≠ "advantage"
- 2025 Quantinuum 和 Google 的 advantage 主张在数月内被经典模拟反超；arXiv 2511.09124 "Grand Challenge" 综述明确把这种竞赛叫做"持续被经典反超的 cat-and-mouse game"
- IBM 与 Pasqal 2025-07 联合发布"Quantum Advantage 框架"：要求**可证伪、可验证、可重复**——这是 IBM 在被打脸多次后主动收紧的科学语言，但也意味着 IBM 自己承认尚未达到这一标准

**IBM 是否回避披露 logical qubit 数**：
- **是**。在与 Quantinuum/Atom/Google 的 logical qubit 数公开竞争中，IBM 几乎不参战；2025-11 大会重点都在"physical fidelity + qLDPC 架构 + decoder 速度"，没有把"logical qubit count"放进 PR 头条
- 这与 IBM qLDPC 路线本身的工程难度有关：qLDPC 在硬件上需要长程连接 (C/L-couplers)，目前还在 Loon 验证阶段，单模块 logical demo 要 2026 Kookaburra 才有
- 一种解读是 IBM 的策略是"晚发但全栈" —— 等到 2026 Kookaburra 才直接拿出"工程上可扩"的 logical qubit；另一种解读是 IBM 在 logical qubit 实测进度上**落后 Quantinuum 半年到一年**

**其他限制**：
- $1B 累计签约里多大比例是"硬件预购 + 服务费"vs "解掉了经典做不到的问题"，IBM 不披露
- "Quantum advantage by end of 2026" 已成为 Krishna / 全公司挂在嘴边的口号；如未兑现将面临巨大叙事反噬
- Nighthawk 5,000→10,000 two-qubit gates 路径是 IBM 押注 advantage 的核心，但 5,000 gate 的电路在经典张量网络/MPS 仿真下仍可能可解，advantage 边界并非铁板

## 5. 引用 URLs

- https://www.ibm.com/quantum/blog/large-scale-ftqc
- https://www.ibm.com/roadmaps/quantum/2025/
- https://www.ibm.com/roadmaps/quantum/2026/
- https://newsroom.ibm.com/2025-06-10-IBM-Sets-the-Course-to-Build-Worlds-First-Large-Scale,-Fault-Tolerant-Quantum-Computer-at-New-IBM-Quantum-Data-Center
- https://www.ibm.com/quantum/blog/qdc-2025
- https://newsroom.ibm.com/2025-11-12-ibm-delivers-new-quantum-processors,-software,-and-algorithm-breakthroughs-on-path-to-advantage-and-fault-tolerance
- https://postquantum.com/industry-news/ibm-loon-nighthawk/
- https://www.tomshardware.com/tech-industry/semiconductors/ibm-unveils-new-120-qubit-processor-and-software-stack
- https://www.datacenterdynamics.com/en/news/ibm-unveils-nighthawk-quantum-processor-claims-it-will-deliver-large-scale-fault-tolerant-quantum-computer-by-2029/
- https://thequantuminsider.com/2025/06/12/engineering-fault-tolerance-ibms-modular-scalable-full-stack-quantum-roadmap/
- https://moorinsightsstrategy.com/ibms-vision-for-a-large-scale-fault-tolerant-quantum-computer-by-2029/
- https://www.datacenterdynamics.com/en/news/ibm-claims-to-have-booked-1bn-of-cumulative-quantum-business/
- https://thequantuminsider.com/2025/02/05/ibm-has-earned-1-billion-from-quantum-cnbc-reports/
- https://thequantuminsider.com/2025/08/19/in-initial-stages-of-quantum-computing-commercialization-sales-stats-show-ibm-leads-in-quantum-deal-value-iqm-in-units-sold/
- https://www.ibm.com/quantum/ibm-quantum-network
- https://www.ibm.com/quantum/products
- https://newsroom.ibm.com/2026-05-05-cleveland-clinic,-riken,-and-ibm-model-a-12,635-atom-protein-the-largest-known-to-be-simulated-with-quantum-computers
- https://www.ibm.com/quantum/blog/cleveland-clinic-riken-chemistry
- https://thequantuminsider.com/2026/04/30/ibms-krishna-predicts-first-real-world-quantum-advantage-in-2026/
- https://www.techtarget.com/searchdatacenter/news/366642895/Quantum-moves-from-promise-to-practice-at-IBM-Think-2026
- https://q-ctrl.com/blog/q-ctrl-delivers-3-000x-speedup-in-materials-discovery-for-the-energy-sector-with-quantum-computing-and-demonstrates-evidence-of-practical-quantum-advantage
- https://www.hpcwire.com/off-the-wire/q-ctrl-claims-3000x-quantum-speedup-for-materials-science-simulations-on-ibm-quantum-platform/
- https://thequantuminsider.com/2026/05/06/qctrl-practical-quantum-advantage-materials-discovery/
- https://www.ibm.com/quantum/blog/quantum-advantage-era
- https://www.hpcwire.com/2025/07/07/ibm-offers-a-prescription-for-identifying-quantum-advantage/
- https://www.nextplatform.com/2025/08/05/ibm-outlines-steps-to-verify-claims-of-quantum-advantage/
- https://arxiv.org/html/2511.09124v3
- https://quantumcomputingreport.com/ibm-reveals-more-details-about-its-quantum-error-correction-roadmap/
- https://spectrum.ieee.org/ibm-quantum-error-correction-starling
- https://jackkrupansky.medium.com/thoughts-on-the-2025-ibm-quantum-roadmap-update-6f45a6009ce8

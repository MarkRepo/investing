---
mat_id: external-google
filename: web-research-2026-05-23
source_type: web-research
quality: high
bias: neutral
addresses: [K1, K2]
---

# Google Quantum AI — K1/K2 supplement

## 1. Willow 论文实际成绩（2024-12，Nature）

**论文**: "Quantum error correction below the surface code threshold", Nature, 2024-12（arXiv:2408.13687）

| 指标 | 数值 |
|---|---|
| 物理 qubit 总数 | 105（transmon 超导） |
| 单比特门保真度 | 99.97% |
| 两比特纠缠门保真度 | 99.88% |
| 读出保真度 | 99.5% |
| Surface code 距离 | d=3, d=5, d=7（同芯片演示） |
| d=7 编码占用物理 qubit | 101 |
| **d=7 逻辑错误率/cycle** | **0.143% ± 0.003%（约 1.4×10⁻³）** |
| **距离每+2 错误率抑制系数 Λ** | **2.14 ± 0.02**（"sub-threshold"首次确证） |
| Cycle 时间 | 1.1 µs |
| 实时 decoder 平均延迟 | 63 µs (d=5) |
| **Break-even**（vs. 最佳物理 qubit 寿命） | **2.4 × ± 0.3 ×** |

**真实的"逻辑 qubit"数量** = **1 个**（一块 d=7 patch，纯量子存储 memory，没做逻辑门、没做多逻辑比特纠缠）。

**是否"超越 break-even"** = **是**，但只是"一个 memory 比一个物理 qubit 活得更久"，不是 fault-tolerant 计算意义上的 break-even（后者需 ~10⁻⁶ 两比特门错误率 + multi-logical-qubit 操作）。Scott Aaronson 评："tickling the tail of the dragon of quantum fault-tolerance"——刚刚摸到龙尾巴。

---

## 2. 2025-2026 后续 demo

### 2025-10-22：Quantum Echoes (OTOC) — "verifiable quantum advantage"
- **平台**：同款 Willow（论文里说 65-qubit subset，blog 强调 105-qubit 全芯片可用）
- **算法**：Out-of-Time-Order Correlator（OTOC²），forward-evolve → 蝴蝶扰动 → backward-evolve
- **速度**：vs. Frontier 超算，**13,000 ×**（2.1 小时 vs. 3.2 年）
- **"verifiable"** 的含义：另一台同档量子机可重复得到同样答案 → 比 2019 RCS 进了一步，但**不是经典验证**，仍是"quantum-on-quantum"
- **应用 hook**：与 UC Berkeley 合作做了 15-atom 与 28-atom 分子的 NMR-like "molecular ruler" 测距（Hamiltonian learning 概念演示）
- **商业客户**：**无公布的付费/产业客户**，仍是学术合作 (Berkeley)
- **Nature 发表**：是

### 2025-11：Google 发布"五阶段应用成熟度路线图"
Stage 1 算法发现 → 2 找到 hard 实例 → 3 在真实任务上做 demo → 4 工程优化 → 5 生产部署。
Google 自己承认 **"no quantum computation has yet demonstrated a clear advantage on a real-world problem"**（明确否定到 Stage 3 的兑现）。

### 2026：neutral atom 路线披露
有报道（tech-insider.org）指 Google 在 2026 同时下注 superconducting + neutral atom 两条 hardware 路线（hedge bet）。无新一代 superconducting 芯片正式发布的公开记录截至 2026-05。

---

## 3. K1 命中度（2027 前"经济价值量子优势"）

**结论：负面（基本不会命中）**

证据：
- **Google 自己 2025-11 承认 Stage 3（真实任务上的 advantage）未达成**——这是经济价值的前置条件
- Quantum Echoes 的 "advantage" 是物理 benchmark（OTOC），不是商业问题；其 NMR 类比仅是 proof-of-principle
- 公开**没有任何付费客户案例**（Ford / HSBC / AstraZeneca 等出现在通稿里，主要走 IBM / D-Wave / IonQ，且都未公开 ROI 数字）
- Hartmut Neven 多次公开口径："commercial within 5 years" → **目标年份 2029-2030**，明确晚于 2027
- Google 2026 计划"开 quantum data center + commercial system **by 2029**"——再次把窗口定在 2027 之后

K1 在 Google 路径上**几乎确定不会在 2027 前兑现**。

---

## 4. K2 命中度（2028 前 ≥100 逻辑比特 + 逻辑错误率 ≤10⁻⁹）

**结论：极度负面（差几个数量级）**

| 项目 | 当前 (Willow 2024) | K2 门槛 | 差距 |
|---|---|---|---|
| 逻辑 qubit 数 | **1** (memory only) | ≥100 | **× 100** |
| 逻辑错误率 / cycle | **1.4 × 10⁻³** | **≤10⁻⁹** | **× 10⁶**（6 个量级） |
| 支持逻辑门 | 无（只是 quantum memory） | 通用门集 | 整条 milestone 4 都没做 |

**Google 自己的 6 个 milestone 进度**：
1. Beyond classical（2019 Sycamore）✓
2. QEC 原型（2023）✓
3. **Long-lived logical qubit**（**进行中**，Willow 是迈向 M3 的一步但未达成）
4. Universal gate logical qubit ✗
5. 工程化 scale-up ✗
6. Large-scale FTQC ✗

Google 给的"useful FTQC by **2029-2030**"已被业内（Aaronson 等）视为乐观估计。**2028 前** logical qubit 数到 100 + 10⁻⁹ 错误率，需要：
- 物理 qubit 数从 105 → ~10⁵（×1000）
- 单/双比特门保真度再提一个数量级
- 实现 multi-logical-qubit 通用门集（Milestone 4 整步还没动）

K2 在 Google 路径上**基本不可能在 2028 前兑现**。Aaronson 仅愿赌 "2027 年底前 500 qubit + 99.9% fidelity"，连这个都远低于 K2 标准。

---

## 5. 反常识 / 学界质疑

1. **RCS / OTOC supremacy 没有商业意义**
   - IBM 立场（Dario Gil）："quantum computers are not 'supreme' against classical computers because of a laboratory experiment...with no practical applications"
   - RCS 是 **stress test，不是算法**，不解任何实际问题
   - Quantum Echoes 比 RCS 进了一步（可被另一台量子机复现），但仍然**经典不可验证**——所谓 13,000× 是用 small-case 外推得到的

2. **Gil Kalai 长期质疑（2024-12 重申）**
   - Willow 结果统计学上仍依赖间接外推（直接经典验证需 ~10²⁵ 年）
   - 噪声模型可能掩盖系统性 bias
   - "supremacy"声明在他看来仍未被独立证伪/证实

3. **IBM 路线分歧**
   - IBM 公开**不用** "quantum supremacy" 术语，主张 "quantum utility"（先在 100+ noisy qubit 上做有用的近似计算，再走 FTQC）
   - IBM 自己 2025 路线图押 Heron/Condor 系超导 + LDPC code，而非 surface code；声称 2026-2029 可达数百逻辑比特（但同样未公开经济价值案例）

4. **中国 USTC 潘建伟 Zuchongzhi 3.2（2025）**
   - 在 RCS 上声称比 Google 同类更稳定
   - 加剧"RCS 是不是个有意义指标"的争论

5. **共识级别的"真问题"**
   - 行业内（Aaronson、Preskill 等）普遍认为：**2027 前不会有 useful FTQC；2030 前能做到 single-purpose advantage 已属乐观**
   - "Useful quantum advantage" 的杀手应用——化学/材料模拟——所需 logical qubit 数估计 **数百到数千 + 错误率 10⁻⁹ ~ 10⁻¹²**，与 K2 量级一致但时间表普遍指向 2030s 后期

---

## 6. 引用 URLs

- https://www.nature.com/articles/s41586-024-08449-y
- https://arxiv.org/abs/2408.13687
- https://quantumai.google/roadmap
- https://quantumai.google/qecmilestone
- https://blog.google/innovation-and-ai/technology/research/google-willow-quantum-chip/
- https://blog.google/innovation-and-ai/technology/research/quantum-echoes-willow-verifiable-quantum-advantage/
- https://research.google/blog/a-verifiable-quantum-advantage/
- https://research.google/blog/making-quantum-error-correction-work/
- https://thequantuminsider.com/2025/10/22/google-quantum-ai-shows-13000x-speedup-over-worlds-fastest-supercomputer-in-physics-simulation/
- https://thequantuminsider.com/2025/11/14/google-ai-outlines-five-stage-roadmap-to-make-quantum-computing-useful/
- https://thequantuminsider.com/2025/05/16/quantum-computing-roadmaps-a-look-at-the-maps-and-predictions-of-major-quantum-players/
- https://www.hpcwire.com/2024/12/09/google-debuts-new-quantum-chip-error-correction-breakthrough-and-roadmap-details/
- https://www.datacenterdynamics.com/en/news/google-opens-quantum-computer-data-center-and-rd-lab-plans-commercial-system-by-2029/
- https://scottaaronson.blog/?p=8525
- https://gilkalai.wordpress.com/2024/12/09/the-case-against-googles-claims-of-quantum-supremacy-a-very-short-introduction/
- https://www.ibm.com/quantum/blog/on-quantum-supremacy
- https://www.science.org/content/article/ibm-casts-doubt-googles-claims-quantum-supremacy
- https://postquantum.com/engineering-news/google-surface-code-threshold/
- https://physicsworld.com/a/quantum-processor-enters-unprecedented-territory-for-error-correction/
- https://www.scmp.com/news/china/science/article/3337742/chinas-new-quantum-computer-hits-stability-milestone-beating-google-efficiency
- https://www.uscc.gov/sites/default/files/2025-11/Vying%20for%20Quantum%20Supremacy%20U.S.-China%20Competition%20in%20Quantum%20Technologies.pdf
- https://www.forrester.com/blogs/googles-willow-chip-quantum-leap-or-quantum-hype/

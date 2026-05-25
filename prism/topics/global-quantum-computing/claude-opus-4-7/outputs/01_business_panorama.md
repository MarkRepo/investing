---
slug: global-quantum-computing
output_key: 01_business_panorama
version: 1
generated: 2026-05-23T00:00:00+08:00
data_freshness: 2026-Q1
data_freshness_basis: findings_mat-2e82b4 (D-Wave Q1 2026 10-Q) + findings_external_ibm (IBM 2026 Q-CTRL demo) + findings_external_quantinuum_atom (Quantinuum Helios 2025-Q4 + IPO 2026 路演披露)
---

# 商业全景：全球量子计算与量子模拟产业

> 生成于 2026-05-23，训练知识占比约 55%，资料更新截至 2026 Q1（部分硬件路线进展更新至 2026-05）

## 行业定义与边界

量子计算（Quantum Computing, QC）以"量子比特（qubit）的叠加+纠缠+干涉"为基本计算单元，对特定问题类（搜索、整数分解、量子化学模拟、组合优化、机器学习子模块）提供经典计算无法多项式时间解决的加速。**与"量子通信（QKD）"、"量子传感"是不同产业**——本研究**只覆盖通用量子计算（QC）+ 专用量子模拟（Quantum Simulation/Annealing）**两个子领域。

边界判定：
- **包括**：硬件平台（超导/离子阱/中性原子/光子/拓扑/退火机）、低温与控制硬件（稀释制冷机/低温线缆/CMOS 控制芯片/激光器/光子集成）、软件栈（编译/纠错/算法库）、云量子服务、终端应用合作（化学/材料/金融/物流）。
- **不包括**：量子密钥分发（QKD）、量子雷达、量子陀螺仪、量子重力计——这些归"量子精密测量"子产业。
- **行业代码**：尚无独立 GICS 二级代码；硬件标的多归在 IT Hardware 9020；中国 A 股归在"通信设备/计算机设备"。

## 市场规模与结构

| 维度 | 当前数值（2025） | 来源 |
|---|---|---|
| 全球 QC 硬件 + 服务总营收 | ~$1.2-1.5B | findings_mat-fa4949 (IonQ 10-K) / mat-d83292 (Rigetti 10-K) / mat-55d3c2 (D-Wave 10-K) / mat-71e318 (QUBT 10-K) + 训练知识（IBM/Google quantum 部分不分拆披露） |
| 其中：美股纯硬件四傻合计营收 | ~$110M（IonQ $43M + RGTI $11M + QBTS $9M + QUBT $0.5M + Quantinuum 估 ~$50M 私营） | findings_mat-2e82b4 + mat-902c40 + mat-d83292 等 |
| IBM 累计量子营收 2017-2024 | $1B | findings_external_ibm |
| 政府/科研采购占比 | 60-80%（不同标的差异大） | 多份 10-K Risk Factors |
| 2030 市场规模预测（McKinsey） | $10-15B | 训练知识（McKinsey Quantum Tech Monitor 2024） |
| 2030 市场规模预测（保守派 BCG/Forrester） | $5-7B | 训练知识 |

**结构特征**：
- 极度分散——硬件 5 大路线无统一赢家；CR3（IBM + IonQ + D-Wave）按公开营收口径 ~50%，但 Quantinuum 私营 + Google 不披露，真实集中度未知。
- **政府/学术为主，商业化收入占比极低**：D-Wave 2025 商业 QCaaS 仅 $5.5M，远低于 Jülich $16M 单笔系统销售。

## 价值链解析

```
原材料/卖铲人 ─→ 硬件平台 ─→ 中间件/软件栈 ─→ 云量子服务 ─→ 终端应用商
（稀释制冷机/    （超导/离子阱/     （Qiskit/    （AWS Braket/   （化学/材料/
低温线缆/激光/    中性原子/光子/     Cirq/Q#/    Azure Quantum/  金融/物流/
光子集成芯片）    拓扑/退火）        OpenQASM）   IBM Quantum/    药物发现）
                                                Google Engine）
```

| 环节 | 关键玩家 | 毛利率水平 | 竞争格局 |
|---|---|---|---|
| 稀释制冷机 | Bluefors（FI，60%+ 份额）/Oxford Instruments LSE:OXIG NanoScience（已剥离 2024）/Quantum Machines/Janis | 估 40-50%（PE 持有，无公开） | 寡头（Bluefors 独大） |
| 低温线缆/控制 | Maybell Quantum/Cryogenic/Coax Quantum | 估 30-40% | 分散 |
| 硬件平台 | IBM/Google/IonQ/Quantinuum/Rigetti/D-Wave/Atom Computing/PsiQuantum/Xanadu/Pasqal/国盾量子/本源 | 负毛利至 20%（findings_mat-fa4949 IonQ FY2024 GM ~20%） | 路线分化 |
| 软件栈/编译器 | IBM Qiskit/Google Cirq/Microsoft Q#/Quantinuum InQuanto/Q-CTRL Boulder Opal | 软件不单独计费 | IBM Qiskit 是事实标准 |
| 云量子服务 | AWS Braket/Azure Quantum/IBM Quantum Network/Google Quantum Engine | 不披露 | 4 大云超大厂 + IBM Network |
| 终端应用 | Mercedes/JPMorgan/Roche/BASF/Boeing/ExxonMobil（合作而非采购） | 无 ROI 披露 | 全部 PoC 阶段 |

## 商业模式

四种主要变现路径，**几乎所有标的都是"叙事-资本-政府订单"三角，商业 ARR 极薄**：

1. **硬件系统销售**（D-Wave Advantage2 $16M/套 给 Jülich；IBM Quantum System Two 不公开报价）——大单不可重复，属"项目制收入"。
2. **云量子服务 QCaaS**（IonQ on AWS Braket / D-Wave Leap / IBM Quantum Network）——D-Wave 全年 QCaaS 营收仅 $5.5M。
3. **政府/军方合同**（IonQ 60%+ 营收来自 USAF/DoE/DARPA；Rigetti 类似）——属"研发服务"性质，毛利低、续费不确定。
4. **企业战略合作**（IBM Quantum Network 250+ 成员，按订阅费 + 联合研发分成）——合作多，付费 ROI 案例 0 个。

**盈利驱动因子**：当前所有标的都未跨越盈亏平衡，**驱动公式 = "技术里程碑 → 叙事溢价 → 融资续命 → 烧钱研发"**，不是"量×价×成本"的产业逻辑。

## 需求端分析

- **核心客户群体**：
  - 政府/学术（70%）：DoE/NSF/DARPA/NIH（美国）、欧盟 Quantum Flagship（€10亿）、中国十四五量子专项、英国 NQCC、日本 Moonshot、加拿大 QSI
  - 大企业 R&D（25%）：IBM Quantum Network 250+ 成员，多数为试点项目预算
  - 算法/软件开发者（5%）：通过云访问做实验
- **购买驱动因素**：政府是"国家战略+技术储备"动机（不看 ROI），企业是"科研选项费"（小预算+长视野）
- **需求增长核心驱动**：
  - 美国 NQI 2.0 法案 2024 重新授权 + 2025 H.R.6213 增 $2.7B 联邦量子预算
  - 中国十四五 + 合肥/济南/北京三大量子科学中心配套（findings_mat-bde95b 国盾量子 2024 年报）
  - 欧盟 Quantum Flagship 2024-2028 续期 €10亿

## 供给端分析

**主要参与者类型**：
- 上市公司（4 家美股 + IBM/Google 子业务 + 国盾量子 SSE:688027）
- 独角兽（PsiQuantum $7B 估值/Quantinuum 即将 IPO $20B target/Atom Computing $300M 融资）
- 巨头子业务（Google Quantum AI/Microsoft Azure Quantum 拓扑）
- 中国国家队（本源量子+国仪量子+中电科 38 所，非上市）

**进入壁垒**：
- 技术：稀释制冷机、千 qubit 集成、量子纠错（QEC）三大硬骨头，10 年以上积累 + $1B 以上烧钱才有入场券
- 资本：单家年烧 $0.3-1B（IonQ FY2024 净亏 $331M）
- 资质：政府合同需 ITAR/出口管制许可（美国 DoC 2024 加严）
- 人才：全球深量子硬件工程师 < 5,000 人

## 竞争格局

**格局类型**：**路线分化的多寡头**——5 大硬件路线（超导/离子阱/中性原子/光子/拓扑）+ 1 个退火专用（D-Wave），各路线内 2-3 家头部，无路线间统一赢家。

**核心竞争要素（3 个）**：
1. **物理 qubit 数 × 保真度**（Lambda 抑制因子）：Google Willow Lambda=2.14 是当前里程碑
2. **逻辑 qubit 数量与门集**：Quantinuum Helios 48-94 LQ，Atom Computing 50 LQ 路线图 2027
3. **商业化客户案例**：除 D-Wave Jülich 外，无成熟商业 ROI 案例

**行业龙头与优势**：
- **IBM**：超导路线（Heron/Loon/Kookaburra），Qiskit 生态 + IBM Quantum Network 250+ 客户，$1B 累计营收（findings_external_ibm）
- **Google Quantum AI**：Willow 105 qubits + Lambda=2.14（findings_external_google），但 Stage 3（真实任务 advantage）未达成
- **Quantinuum**：48-94 LQ（行业最强），Honeywell+Cambridge Quantum 合资，IPO 路演中 $20B target
- **D-Wave**：唯一规模化退火机商，1,200-qubit Advantage2 + 2025-03 Science 论文 spin-glass supremacy 主张

## 发展阶段

**当前阶段：导入期晚段 → 成长期早段过渡**

判断依据：
- **技术**：QEC 跨越 sub-threshold（Willow 2024-12 Lambda=2.14）首次确证，开始进入"工程化 scale-up"阶段，但 Milestone 4（multi-logical-qubit 通用门）整步未启动
- **商业**：唯一可统计的 ROI 案例 = D-Wave Jülich $16M（属"科研基础设施"采购），无任何企业 ROI 案例
- **资本**：SPAC 量子四傻已经历 2021 IPO 顶 → 2022-2023 -70%~-90% 崩盘 → 2024 Q4 Willow 触发的第二波叙事（2025 H2 估值再创新高），周期上属于"叙事第二波顶部"

**关键不对称**：技术上"导入晚→成长早"是真实的（QEC 突破不可逆），但估值上"叙事顶部+基本面背离"是新泡沫信号——技术拐点与商业化拐点至少有 3-5 年错位（参考半导体 1965 集成电路发明 vs 1970 商业放量）。

## 信息来源

- 训练知识（约 55%）—— McKinsey/BCG/Forrester 行业报告、半导体/AI 历史类比、5 大量子硬件路线物理原理
- findings_mat-fa4949 (IonQ 10-K FY2024)：营收结构、烧钱速度、Risk Factors
- findings_mat-2e82b4 (D-Wave Q1 2026 10-Q)：QCaaS -81% 收入断崖
- findings_mat-d83292 (Rigetti 10-K)：政府订单依赖度
- findings_mat-71e318 (QUBT 10-K)：边缘标的财务
- findings_mat-55d3c2 (D-Wave 10-K FY2024)：Advantage2 + Jülich $16M 单笔
- findings_mat-bde95b (国盾量子 2024 年报)：中国国家队基本面
- findings_external_ibm：IBM 路线图 Heron/Loon/Kookaburra + Q-CTRL 3000× demo + $1B 累计营收
- findings_external_google：Willow 105 qubits + Lambda=2.14
- findings_external_quantinuum_atom：Helios 48-94 LQ + Quantinuum IPO + Atom Magne 路线
- findings_external_psiquantum_microsoft：PsiQuantum Omega 99.22% + Brisbane 延期 + Microsoft Majorana 学术争议

# Thesis v0 — 全球量子计算与量子模拟产业

> 写于：2026-05-22 资料阅读前
> 模型：claude-opus-4-7
> 数据基础：仅 LLM 训练知识，未阅外部资料

---

## 1. 核心 thesis

**分化看法看多卖铲人 + 量子模拟先行应用，看空当下纯量子硬件标的估值；通用量子优势 2030+，量子模拟商业 PoC 2027-2028 起。**

**强度：6/10**（中等偏看多，但内部强烈分化——卖铲人 8/10、量子模拟 6/10、通用量子硬件标的 3/10）

---

## 2. 支持理由

1. **卖铲人订单已经起来**——Bluefors、Oxford Instruments 稀释制冷机交付周期仍 24-36 个月排产，2024-2025 全球扩产；低温线缆、CMOS 控制芯片、低温放大器 (Quantum Machines/Zurich Instruments) 处于供不应求状态，这是量子产业最早开始放量的环节
2. **量子纠错取得真实工程进展**——Google Willow (2024 末) 实现"码距 d 增加，逻辑错误率指数级下降"，是 surface code 首次跨过 break-even point；IBM Quantum System Two 平台架构升级 + Heron 处理器迭代；这条曲线如果继续，2030 年前出 100+ 逻辑 qubit 系统并非天方夜谭
3. **量子模拟可能不需要等 FTQC**——VQE / QAOA 等 hybrid 算法在 NISQ 已能跑 ~30-50 量子比特的化学分子；制药/材料/催化剂领域中等规模分子 (50-200 atoms) 商业价值高，2027-2028 可能出现首批"用量子模拟节省 R&D 美元"的真实案例
4. **路线多元化降低系统性风险**——超导（Google/IBM）、离子阱（IonQ/Quantinuum）、中性原子（Atom Computing/QuEra）、光量子（PsiQuantum/Xanadu）、拓扑（Microsoft Majorana）五条路线并行，单一路线失败不会拖死整个产业
5. **国家资本持续输血**——美 NQI 2.0、中国十四五量子科技专项、欧盟 Quantum Flagship、英国 NQCC、日本 Moonshot 都在加码，2030 年前行业不会出现"断粮"风险，给硬件公司争取了至少 5 年时间窗口

---

## 3. 最大反方观点

1. **"经济价值量子优势"可能 10 年内不出现**——所有公开的"量子优势"宣称（Google 2019 RCS、Willow 2024 RCS、中国九章玻色采样）都在人造任务上，没有任何任务做到"经典算力做不到 + 企业愿意付费"。如果这条线 2028 年前还不出现，整个产业叙事崩塌
2. **FTQC 量子规模差 4 个数量级**——surface code 估算 1 逻辑 qubit ≈ 1000 物理 qubit，Shor 破 RSA-2048 需 ~2000 万物理 qubit。当下最大系统才 1000+ 物理 qubit，且错误率仍在 10^-3 量级。从 1000 到 2000 万需要 10-20 年工程化，这期间一级估值要靠"故事"撑
3. **纯量子标的估值已经透支 10 年预期**——IonQ/Rigetti/D-Wave 2025 年市销率 >50x，营收 70-90% 来自政府订单 + 学术合作，自由现金流持续为负。任何一次延期或纠错论文翻车都会触发 -50% 级别回撤，类比 2000 年互联网泡沫破裂前夕

---

## 4. Killer Question（可观测、可证伪）

- **K1**：**2027 年前**是否出现"用量子计算解决一个经典算力无法解决、且企业愿意付费 $1M+/year 的真实商业问题"？（验证经济价值量子优势是否真存在）
- **K2**：**2028 年前** Google / IBM / PsiQuantum / Quantinuum / Atom Computing 是否有任一家实现"逻辑量子比特数 ≥100、逻辑错误率 <10⁻⁹"的容错里程碑？（验证 FTQC 工程化曲线是否在轨）
- **K3**：稀释制冷机龙头（Bluefors、Oxford Instruments）年订单同比是否持续 >40%？若 2027 年降到 <20%，说明硬件资本支出退潮，整个卖铲人链条转弱
- **K4**：**2027 年底前**是否有 ≥3 家制药 / 材料 / 化工公司公开披露"量子模拟为我们节省了 X 美元 / 缩短了 Y 月开发周期"的具体案例？（验证量子模拟先商业化路径）
- **K5**：IonQ / Rigetti / D-Wave 是否在 **2026-2028 年**发生估值崩塌（股价 -70%+）、被并购或退市？（验证当下纯硬件标的估值过高的反方观点）

---

## 5. 研究中重点验证项

1. **卖铲人订单与产能数据**——Bluefors、Oxford Instruments、Janis、Quantum Machines、Zurich Instruments、IQM；附 → K3、Q1
2. **各量子硬件玩家季度里程碑**——Google、IBM、Quantinuum、IonQ、Atom Computing、QuEra、PsiQuantum、Rigetti、Microsoft；附 → K1、K2、K5
3. **量子模拟商业 PoC 案例**——Mercedes-Benz、ExxonMobil、JPMorgan、Roche、Boehringer Ingelheim、BASF、Pfizer 的公开量子项目进展；附 → K4
4. **中国量子产业链玩家与政策**——本源量子（合肥）、国盾量子（合肥）、中科大、济南量子技术研究院、中电科 38 所；十四五专项资金落地情况
5. **量子纠错学术与工程突破**——Surface code、qLDPC、bosonic code、Magic state distillation、Logical qubit benchmark 论文追踪；附 → K2

---

## Coverage 闭环

| Killer Question | 对应 user_todos | 状态 |
|---|---|---|
| K1（经济价值量子优势） | T1（玩家里程碑追踪）、T4（量子模拟 PoC） | ✓ |
| K2（FTQC 工程化曲线） | T1、T5（纠错论文追踪） | ✓ |
| K3（卖铲人景气度） | T2（稀释制冷机订单） | ✓ |
| K4（量子模拟商业化） | T4（药企 / 化工 PoC） | ✓ |
| K5（纯硬件标的估值） | T3（IonQ/Rigetti/D-Wave 财报 + 股价追踪） | ✓ |

5 条 Killer Question 全部至少一个 todo 攻打，coverage 闭环 OK。

---
mat_id: mat-efcb7e
filename: 2025-06_McKinsey_Quantum_Technology_Monitor.pdf
source_type: industry-research
quality: high
bias: bull
addresses: [K1, K2, K4]
---

## 核心数据点与事实
- [Key messages / Market sizing] [2024 实际] [QC 公司总收入] $650M–$750M（2023 为 $200–250M，2025 预测 >$1B，+40% p.a.）[K1]
- [Market size scenarios] [2035/2040] [QC TAM] 保守 $28B/$45B，乐观 $72B/$131B；2024 基数 $4B（含融资+收入+大厂内部投入），2030 区间 $16B–$37B，CAGR 11–14%[K1]
- [Value at stake] [2035] [QC 经济价值] $0.9T–$2.0T，金融 $400–600B、化工 $200–500B、制药 $200–500B、先进电子/航空 $70–400B、电信 $50–100B（McKinsey 自身测算，"approximative, not definitive"）[K1, K4]
- [Investment landscape] [2024] [QT 初创总投资] $2.0B（2023 $1.3B，YoY +50%），其中公有占 34%（+19pp YoY），美国占 ~78%；2024 头部两笔（PsiQuantum + Quantinuum）合计 ~$925M ≈ 全年一半 [K3, K5]
- [Public announcements] [2025 Jan–Apr] [政府宣布] >$10B，其中日本 $7.4B（含下一代芯片+QC）占 ~75%；西班牙 $900M、美国伊州 $500M、马里兰 $1B 目标 [K3]
- [Government cumulative] [截至 2025-04] [累计政府承诺] 中国 ~$15.3B（领跑）、日本 $9.2B、美国 $6.0B、德国 $5.2B、英国 $4.6B、韩国 $2.4B、印度 $1.7B [K3]
- [Innovations / Google Willow] [2024-12] [逻辑 qubit 里程碑] Google 用 105 物理 qubit 跑 distance-7 surface code，1 个 logical qubit fidelity ~99.86%（错误率 0.143%），首次显示物理 qubit 增加 → 错误率指数级压制 [K2]
- [Innovations / AWS] [2024] [逻辑 qubit] 用 5 cat data + 4 ancilla = 9 物理 qubit 实现 distance-5 logical qubit fidelity 98.35%，比 distance-3（98.25%）略好 [K2]
- [Innovations / QuEra] [2024] [中性原子] 280 物理 qubit 上 2 个 high-fidelity 逻辑 qubit，distance-3 升至 distance-7 [K2]
- [Innovations / Atom Computing] [2024] [中性原子] 256-Yb 处理器跑 28-logical-qubit Bernstein-Vazirani，错误率优于 28 物理 qubit（distance-2，仍为 proof-of-concept）[K2]
- [Innovations / Microsoft] [2025-02] [拓扑 qubit] Majorana 1 chip 宣称 "in years, not decades"，但发表的是 InAs-Al 干涉单次 parity 测量，未公布 fidelity/qubit 数 [K2]
- [Innovations / Quantinuum] [2024] [trapped-ion] 30-离子设备上 7 data + 3 ancilla 实现 fault-tolerant teleportation，逻辑过程 fidelity 97.5%，但未执行逻辑门 [K2]
- [Roadmap] [2024→2029] [IBM] 1.121 → 2,000 物理 qubit；error-corrected 路标 2026 起逐年 10×（2026: 10²、2029: 10⁶ 物理 qubit / 1000 逻辑）[K2]
- [Roadmap] [IonQ algorithmic qubit] 2024 36 → 2025 64 → 2026 256 → 2027 384 → 2028 1024（注：algorithmic 非 1:1 等于 logical qubit）[K2, K5]
- [Roadmap] [QuEra] 2023 10 → 2024 >256 → 2025 >3000 → 2026 >10,000 物理 qubit；2027 100 逻辑 [K2]
- [Resource req] [Gidney-Ekerå 2021] [破 RSA-2048] 需要 2000 万噪声 qubit / ~1000 逻辑 qubit；图示交点约在 2029–2030 附近 [K2]
- [Revenue funding split] [2023–24] [按 modality] superconducting $1.033B、photonic $886M 拔得头筹，trapped-ion $386M、neutral atom $339M、spin $312M [K5]
- [Value chain] [2024 新创] 19 家新 QT 初创中，hardware-agnostic 设备/组件 + 应用软件占 11/13；funding 70% 流向 emerging + mature 阶段，scaling 期被冷落（30%）[K5]
- [QComm] [2023→2035] [QComm 市场] $1.0B → $11B–$15B，CAGR 22–25%；政府客户份额 62–66% (2023) → 27–31% (2035)，电信从 2–6% → 16–26%
- [Top 10 deals 2024] PsiQuantum、Quantinuum、Zapata、Q-CTRL、Riverlane、Quantum Circuits、Planqc、Quantum Source、Maybell、SEEQC（注：报告未披露具体 deal 金额）[K5]
- [Cluster] [2024 底] 全球 QC 初创 274 家，美国 77 家居首但 2024 新增仅 2 家（→ 市场走向"consolidation/production"，新创枯竭信号）[K5]
- [Patent / Publication] [2024] QT 专利授权 YoY +13%；中国占 QC 申请 32%（领先），美国占 QComm/QS 43%/45%；中国占物理科学发文 41.8%（同比 +7pp），美 EU 各降至 17.8%/17.2%

## 叙事主线
因为 2024 多家大厂同时跨过 "exponential error suppression" 与首个 logical qubit fidelity > 99% 的工程门槛（Google Willow、QuEra、AWS、Atom Computing 多模态共振）+ 政府投入指数级放大（2025 Q1 公开承诺已 $10B、日本一国 $7.4B）→ 所以 McKinsey 判断 QC 进入"收入化"拐点，2024–2025 收入翻倍至 $1B 量级、2035 TAM $28–72B、价值池 $0.9–2.0T → 对投资意味着 hardware/设备+组件（superconducting + photonic 吸走 70% modality 融资）以及 PsiQuantum/Quantinuum 等"两笔吃半个市场"的赢家通吃格局是 2024–2028 主要套利窗口；纯软件/应用层估值需等 logical qubit 工业可用（McKinsey 路线图指向 2027–2030）后再起。

## 反常识/分歧点
- 市场预期：QC 收入主要来自客户付费；本文表明：2024 $650–750M 收入中"政府+国防"是主要驱动，且 30–40% 的 estimate 是 McKinsey 对 <$1M 营收私企的分配假设 — 实际可验证的"商业客户付费"远低于头条数字（对 K1 判断偏负）。
- 市场预期：scaling 期初创（4–8 岁）应该最受追捧；本文表明：2024 funding 反而从 scaling（48%→30%）撤离，流向 emerging（30%→37%）和 mature（22%→34%），中间层被双向夹击 — 利好巨头 + 早期 deep tech，利空 IonQ/Rigetti/D-Wave 这类"已上市但未盈利"的中段玩家（对 K5 略偏正：估值压力实在）。
- 市场预期：中国在 QC 上落后；本文表明：中国 QC 专利申请份额 32%（>美 22%）、累计政府投入 $15B+ 居全球首位、科研论文份额 41.8%（>美 + EU 之和） — 但商业披露被"limited transparency"刻意打折，西方分析师可能系统性低估。
- 市场预期：Microsoft Majorana 是颠覆性突破；本文表明：McKinsey 把它和 Google/AWS/IBM 并列为"selected announcements"，且备注"in years, not decades" — 这是用相对模糊的承诺，对照 Google 的可量化 99.86% fidelity，McKinsey 实际更偏 Google 路线（K2 信号：押 Google/IBM/Atom Computing/QuEra > 押 Microsoft）。

## 未回答问题
- K3 关键缺失：稀释制冷机 OEM（Bluefors、Oxford Instruments）订单 / 收入 / 产能数据全无；McKinsey 只在 value chain 提了 "cryogenic" 是 enabler。
- K4 关键缺失：没有任何一家制药/材料/化工公司公开披露 "量子模拟节省了 $X 或缩短了 Y 月"的具体 ROI；Pasqal 的 conical intersections 算法、QuEra 的 280 qubit 都仍是论文级 demo，未见商业客户付费证据。
- K5 关键缺失：完全没有 IonQ/Rigetti/D-Wave 的股价、市值、收入对比；这份报告把"上市纯量子公司"和未上市初创（PsiQuantum、Quantinuum）混在一起处理，无估值崩塌信号。
- 2024 Top 10 deals 表的 deal size 列在 OCR 中是空的（原 PDF 有数字），下游 ingest 时若需精确金额需回查原图。

## 质量备注
- 数据新鲜度：截至 2025-04（公开投资统计），技术 announcement 截至 2025-02（Microsoft Majorana 1），市场预测面向 2030/2035/2040。新鲜度高。
- 分析师倾向：明显 bull / industry-builder 立场（McKinsey 自身有 QT 咨询业务，会从"教育市场+背书"角度撰写）；revenue 数字含 30–40% 的 estimate 加成；TAM 用 conservative + optimistic 双轨但都给到 $28B+ 起跳。
- 可信度：高 — 数据来源 PitchBook、Patsnap、Nature Index、ArXiv 论文均可验证；Gidney-Ekerå 的 RSA-2048 资源估算是行业基准引用；技术里程碑均附 ArXiv 论文标题可回溯。
- 与已知 quantum 共识矛盾点：(1) 报告对 NV-center/diamond 量子传感（如 Quantum Diamonds 半导体故障分析）给了较高 commercial 评价，但传感主线在共识中常被边缘化；(2) 把 PQC 与 QKD 并列且默认 QKD 会大规模商业化，与"NIST 已标准化 PQC、QKD 在企业侧需求疲软"的另一阵营观点冲突 — 投资人需警惕 QKD 商业化叙事的过度乐观。

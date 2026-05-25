---
mat_id: mat-55d3c2
filename: 2025_QBTS_10-K_2026-02-26.htm
source_type: annual-report
quality: high
bias: neutral
addresses: [K1, K3, K4, K5]
---

# QBTS FY2025 10-K — 资料消化

## 1. 核心数据点与事实

**损益表（FY2025 vs FY2024，美元）：**
- 总收入 **$24.6M vs $8.8M**，YoY **+179%**（GAAP 史上最快增速，但绝对值仍极小）
- 收入构成：**System sales $16.18M（0 → 16.18M，全新增项）** | QCaaS $5.52M（vs $6.74M，**YoY -18%**） | Professional services $2.72M（+40%） | Other $0.17M
- 毛利率 82.6%（gross profit $20.3M / cost $4.3M）
- 运营支出 $120.7M（R&D $50.7M +44%；G&A $41.2M +27%；S&M $28.8M +91%）
- 运营亏损 **-$100.4M**（vs -$77.2M）；净亏损 **-$355.1M**（vs -$143.9M），差额主要来自 **$270.5M 的 warrant fair-value mark-to-market non-cash charge**
- 经营现金流 **-$72.0M**（vs -$42.6M，烧钱 +69%）；累计赤字 $982.0M

**地域 & 客户集中度（炸裂级数据）：**
- Germany **$16.77M（占 68.2%）** vs 2024 仅 $1.89M
- US $2.65M | Japan $1.32M | Switzerland $0.96M | Canada $0.88M | Other $2.01M
- **Customer A = 67% of total revenue**（vs 2024 的 17%）——几乎肯定是 Jülich Supercomputing Centre 的 Advantage2 系统升级/采购
- 全年 system upgrade 收入 $3.5M（计入 system sales）
- China/Russia/Ukraine 销售记录为零（政策性披露）

**资本结构与现金（K5 关键）：**
- 期末现金 $635.3M（vs $178.0M，+$457M）+ 可变现证券 $249.1M = **总流动性 ~$884M**
- 融资活动现金流入 **$779.1M**：ATM $536.7M（净）+ 行权 $202.9M + Lincoln Park $37.8M + ESPP/期权 $12.2M
- 2025 年 ATM 工具：$100M、$75M、$150M、**$400M**（H2 用尽，单季 Q2 净进 $390.6M）
- 股本爆炸式增长：**266.6M → 358.7M 股**（+34.6%），另有 3.18M 可交换股；Public Warrants 已于 2025-11-19 全部赎回退市
- 2026 年发行 S-3ASR 又登记 1043 万股可转售（来自 Quantum Circuits 收购对价）
- 2026-01-20 完成对 **Quantum Circuits（gate-model 公司）收购**，对价 cash+股票，subsequent event

**产品/科学（K1 拐点叙事）：**
- 2025-05 发布 **Advantage2 量产机**：4400+ qubits、20-way connectivity（vs Advantage 的 15-way）、更高 coherence、更高 energy scale
- 2025-03 **Science 论文**：在 1200-qubit Advantage2 原型机上做 programmable spin glass 量子动力学模拟，分钟级完成、Oak Ridge Frontier supercomputer 需 ~100 万年（也将"超过全球年用电量"）
- 2026-01 announced 可扩展片上 cryogenic 控制 fluxonium gate-model qubits，宣称为"行业首例"
- 截至 2026-02，Leap service 累计 280M+ 问题提交；Advantage2 上累计 62M+ jobs
- 三台 Advantage2 已部署：Canada、US（Davidson, Huntsville AL；2025-11 上线）、Germany（Jülich）

**已披露重大合同/客户（K4 相关）：**
- **FAU**（Florida Atlantic University, 2026-01）：签约采购+部署 Advantage2，2026 年内安装，附 MOU 设立 D-Wave Quantum Applications Academy
- **Q-Alliance/SQT**（2025-10）：Swiss Quantum Technology 与 D-Wave 签约在欧洲部署 Advantage2 服务意大利政府 Q-Alliance 战略框架，含 SQT 后续购买权
- **Davidson Technologies**（Huntsville, AL，2025-11 上线）+ 与 Anduril 合作做导弹防御 proof-of-concept
- Customer roster：Mastercard、Deloitte、BASF、Pfizer、Unisys、Siemens Healthineers、NTT DOCOMO、Ford Otosan、Interpublic、ArcelorMittal、Pattison Food Group、DENSO、BBVA、NEC
- 注意：FAU/Q-Alliance 是签约/announcement，10-K **未具体披露三大订单的合同金额**（用户提到的 FAU $20M / Fortune 100 $10M QCaaS / Q-Alliance €10M 都来自 press release，非 10-K 数字）

## 2. 叙事主线

D-Wave 在 2025 年完成了从"科学故事公司"到"系统销售公司"的关键性转身——FY2025 收入 179% 的暴增**100% 由系统销售驱动**（$0 → $16.2M），而 QCaaS（理论上的高复购、SaaS 式生意）反而 -18%。这是一次 backlog 释放型的 lumpy revenue（一台机器在 Jülich 那侧确认了 ~$16M），不是订阅业务起飞。但管理层把 2025-03 的 Science 论文（在 spin-glass 模拟上对 Frontier 超算实现"100 万年 vs 几分钟"的速度差）作为商业化叙事的核心锚点反复提及，且把"world-first quantum supremacy on a useful, real-world problem"写入 Item 1 业务概述、Risk Factors、MD&A 三个位置，定位为"工业级量子优势已经发生"。配合 Advantage2 量产、Quantum Circuits 收购（拿 gate-model 入场券，从"annealing-only"切到"only dual-platform"叙事）、$884M 总流动性（远超 IonQ 同期），D-Wave 把自己塑造成 K1 唯一已经"打卡完成"的公司，并用 2025 年发行 ~$780M 股权融资把估值泡沫现金化。

## 3. 反常识

- **核心 KPI（QCaaS）在 supremacy 论文发布的同一年下滑 18%**——如果"工业级量子优势"已实现，云订阅理应起飞，但事实上 QCaaS 从 $6.7M 缩到 $5.5M，比 supremacy 之前还差。管理层在 MD&A 中只用一句轻描淡写带过。
- **收入的 67% 来自单一客户（Customer A，几乎肯定是 Jülich/Forschungszentrum FZJ 的德国政府机构）**，且这是 system upgrade 一次性确认收入，不是 ARR。如果剔除该客户，"调整后收入"约 $8.1M，YoY 实际几乎无增长。
- **管理层在 Risk Factors 里仍然写"broad quantum advantage 可能数十年才能实现，甚至可能永远不会实现"**，与 MD&A 的"已实现 quantum supremacy"叙事直接冲突——典型的"营销叙事 vs 律师叙事"分裂。
- **net loss 急剧恶化（-$143.9M → -$355.1M）的 76% 不是经营恶化，而是 warrant fair-value 上调 $270.5M 的非现金会计 noise**——股价上涨反而吃掉账面利润，2025-11 已全部赎回 Public Warrant 以消除该噪音。
- Stock-based compensation $22.7M（占收入 92%）；员工股票稀释结构持续侵蚀股东价值。
- D-Wave 自称是"the only company with all three key technologies for scaled, error-corrected superconducting gate-model"——这是收购 Quantum Circuits 两周后的措辞，**尚未在 D-Wave 体系内验证过**。
- 在 spin-glass 论文里宣称"经典需要超过全球年用电量"——这是 worst-case 经典算法的能耗外推，并非业界普遍接受的 fair comparison，类似 Google 2019 量子霸权之争的同款话术。

## 4. K1–K5 命中度评分

- **K1（2027 前首例经济价值量子优势）：9/10 — 决定性证据级别**。D-Wave 自我宣称在 2025-03 已经在"useful, real-world problem"上实现 quantum supremacy（spin-glass dynamics 比 Frontier 超算快 100 万倍），论文发表在 Science。这是 K1 唯一一个有"已发生"主张的标的，问题不是"会不会发生"，而是"该 spin-glass 模拟是否构成 economically valuable use case"——10-K 没有披露 Jülich 的 $16M 是不是因这一突破而买单。
- **K2（≥100 逻辑比特、≤10⁻⁹ 错误率 FTQC 系统）：1/10**。D-Wave 是 annealing 路线，根本不参赛；2026-01 通过收购 Quantum Circuits 才拿到 gate-model 入场券，且尚无任何 logical qubit / 逻辑错误率披露。
- **K3（稀释制冷机龙头订单同比）：2/10**。10-K 提及"竞争对手在用增大的 dilution refrigerators 路线，越来越费电"作为对自家 superconducting+片上控制路线的对比；没有具体披露 Bluefors/Oxford 等稀释制冷机供应商的订单或采购金额。
- **K4（≥3 家制药/化工/材料经济价值案例）：4/10**。客户名单包括 BASF（化工）、Pfizer（制药）、ArcelorMittal（材料）、DENSO（汽车）、Siemens Healthineers（医疗）、Ford Otosan（汽车），但 10-K 全部以"have included"模糊措辞列出，**未披露任何一家的合同金额、ROI 或"经济价值案例"细节**，与 K4 所要求的"披露经济价值"门槛差距明显。最具体的经济价值案例反而是国防（Davidson Technologies + Anduril 导弹防御 POC），不在制药/化工/材料范围内。
- **K5（2026 H1 末 IonQ/Rigetti/D-Wave 估值是否崩塌）：8/10 — 高信息量**。FY2025 末现金 $635M + 证券 $249M = $884M 流动性，账面健康；但是：(1) 2025 全年净增发 9200 万股（+34%），含 $400M ATM 在 Q2 一次性吃完（净进 $390.6M）；(2) 67% 单客户集中度；(3) QCaaS 萎缩；(4) -$72M 经营烧钱率，纯靠融资活下去；(5) 1.27 亿 USD warrant non-cash 噪音已清理但 SBC 仍占收入 92%。给估值崩塌假说提供大量基本面 ammo。

## 5. 未回答问题

1. Customer A（67% 集中度）到底是谁？是 Jülich/FZJ 一次性升级，还是新订单管道？2026 年还有没有第二个 system sale？
2. 那台 $16.2M 的 Advantage2 system sale 的真实 ASP 是多少？管理层从未披露 list price 或 unit count，无法外推 system pipeline 的金额能见度。
3. Science 论文的 spin-glass 模拟是否对应任何商业客户的真实工作流？10-K 没有把论文和任何客户 use case 直接挂钩。
4. FAU $20M、Fortune 100 $10M QCaaS、Q-Alliance €10M 三个 press release 订单中，有几个已计入 deferred revenue 或 RPO？10-K 数字（deferred revenue $3.3M total）显示**几乎没有**——说明这些"订单"要么未签约、要么金额被大幅夸张。
5. Quantum Circuits 的 $538M acquisition 估值（其中 $342M goodwill + $217M intangibles）依据是什么？是否会在 2026/2027 产生 impairment？

## 6. 质量备注

- 来源：SEC EDGAR 10-K 官方文件，FY ended 2025-12-31，filed 2026-02-26
- 审计师签字、KPMG/Deloitte 级别审计（具体名称需查 Exhibit 23），财务数字可信度高
- bias: neutral（SEC 文件，但管理层 MD&A 部分明显有 supremacy 叙事偏好）
- 文件结构：完整披露 Risk Factors / MD&A / 三大报表 + 详细 footnotes，地域 & 客户集中度披露透明
- 关键限制：(1) 三大 PR 订单（FAU、Fortune 100 QCaaS、Q-Alliance）**未在 10-K 中以金额披露**；(2) Quantum Circuits 收购的 PPA 仍为 preliminary（measurement period 内可调整）；(3) D-Wave 不披露 ARR、Net Revenue Retention、客户数等 SaaS 标准指标

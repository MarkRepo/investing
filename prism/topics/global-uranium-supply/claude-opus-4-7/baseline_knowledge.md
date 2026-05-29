---
slug: global-uranium-supply
variant: claude-opus-4-7
written_at: 2026-05-28T00:00:00+00:00
training_cutoff_estimate: 2026-01
---

# 训练知识 Baseline — 全球铀供给端（铀矿/转化/浓缩）

> 本文记录 LLM 在训练截止时对该 topic 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。

## 一、关键事实记忆（30 条）

### 供需平衡
- `[fact-01]` 2024 全球一次铀矿产量 ~60,000 tU，反应堆需求 ~67,000 tU，结构性赤字 ~7-10kt/yr → 置信度：高 | time_sensitivity：慢变
- `[fact-02]` 二次供应（DOE 库存、稀释 HEU、再处理）历史填补缺口，2025 起逐步耗尽 → 置信度：中 | time_sensitivity：慢变
- `[fact-03]` WNA 2024 Nuclear Fuel Report 基准情景 2030 需求 ~83kt vs 当前 ~67kt → 置信度：高 | time_sensitivity：慢变
- `[fact-04]` Sprott Physical Uranium Trust (SPUT) 2021 起累计囤铀 ~6,500 万磅 U3O8，是 2021-2023 价格爆发主因 → 置信度：高 | time_sensitivity：慢变

### 价格
- `[fact-05]` 现货 U3O8 价格 2024-01 触及 $107/lb 历史第二高，2024Q4 回落 $77-85/lb 区间 → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-06]` 长期合约价 2025 中期 ~$80-82/lb，与现货价差收窄 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-07]` 新矿激励价格阈值 $80-100/lb（marginal supply 需 $100+） → 置信度：中 | time_sensitivity：慢变
- `[fact-08]` Kazatomprom ISR 全成本 ~$25-30/lb，Cigar Lake $30-40/lb，Tier 3 矿 $50-60/lb → 置信度：中 | time_sensitivity：慢变

### 头部生产商
- `[fact-09]` Kazatomprom 2024 产量 ~22.5kt，2025 指引 25kt（受硫酸短缺影响下调过） → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-10]` Cameco 2024 产量 ~10kt，McArthur River 2022 重启爬坡 → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-11]` Cameco 2023 收购 Westinghouse 49%（Brookfield 51%），向核燃料下游延伸 → 置信度：高 | time_sensitivity：静态
- `[fact-12]` Orano（法国国企）+ CNNC + Rosatom 构成另外三极，合计 ~30% 产量 → 置信度：中 | time_sensitivity：慢变

### 转化（UF6）瓶颈
- `[fact-13]` 全球转化产能 ~70kt UF6/yr，需求 ~75kt，Cameco Port Hope + ConverDyn + Orano + Rosatom 四家 → 置信度：中 | time_sensitivity：慢变
- `[fact-14]` Rosatom 占全球转化产能 ~38%，欧美依赖度高 → 置信度：中 | time_sensitivity：慢变
- `[fact-15]` 转化服务价格 2020 $7/kgU → 2024 峰值 $70+/kgU，10 倍涨幅 → 置信度：高 | time_sensitivity：**快变** ⚠️

### 浓缩（SWU）瓶颈
- `[fact-16]` 全球浓缩产能 ~63 MSWU/yr，Rosatom 占 ~44%，Urenco ~33%，Orano ~12%，Centrus 美国仅 ~3% → 置信度：中 | time_sensitivity：慢变
- `[fact-17]` SWU 价格 2020 $50 → 2024 $170+ → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-18]` HALEU（5-20% U-235，先进反应堆/SMR 必需）西方产能极有限，Centrus 是美国唯一商业生产商 → 置信度：高 | time_sensitivity：慢变
- `[fact-19]` Centrus 2023-10 首批 HALEU 交付 DOE（~20kg），2024 年小规模商业产能爬坡 → 置信度：高 | time_sensitivity：**快变** ⚠️

### 监管 / 地缘
- `[fact-20]` 2024-05 拜登签 Prohibiting Russian Uranium Imports Act，2028 前 DOE 可发豁免 → 置信度：高 | time_sensitivity：静态
- `[fact-21]` 美国 Civil Nuclear Credit 法案给 $2.7B 支持国内铀产业 → 置信度：高 | time_sensitivity：慢变
- `[fact-22]` 2023-07 Niger 政变后 Orano 在 Niger 三座矿（Arlit/Imouraren/Akouta）运营受阻 → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-23]` Kazakhstan 是 NSG 成员，KAP 既向中俄也向西方出货，政治风险中等 → 置信度：中 | time_sensitivity：慢变

### 在建/重启项目
- `[fact-24]` Paladin Energy Langer Heinrich（Namibia）2024-03 重启首批装船 → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-25]` Boss Energy Honeymoon（澳）2024 重启 → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-26]` NexGen Energy Arrow（Saskatchewan）全球最大未开发铀矿，预计 2027-2028 投产 → 置信度：中 | time_sensitivity：慢变
- `[fact-27]` Denison Wheeler River、F3 Patterson Lake、Goviex Madaouela 等 pre-production → 置信度：中 | time_sensitivity：慢变

### 需求侧锚点
- `[fact-28]` 全球在运 437 反应堆 ~370 GWe，在建 60+，IAEA 高情景 2050 达 950 GWe → 置信度：高 | time_sensitivity：慢变
- `[fact-29]` 2024-09 Microsoft + Constellation 签 20 年 PPA 重启 Three Mile Island Unit 1 → 置信度：高 | time_sensitivity：静态
- `[fact-30]` 2024-10 Amazon AWS + X-energy 协议建 SMR；Google + Kairos Power 协议；hyperscaler 集中下单 → 置信度：高 | time_sensitivity：静态

**第一节统计**：静态 4 / 慢变 14 / 快变 12 → 第五节优先 query 必须覆盖 12 条快变 fact

## 二、关键人物 / 公司 / 产品

### 矿端
- **Kazatomprom (KAP LSE/AIX)** — 全球最大 ISR 生产商，~30% 市占，CEO Meirzhan Yussupov
- **Cameco (CCJ NYSE / TSX)** — 加拿大 Cigar Lake + McArthur River，CEO Tim Gitzel
- **NexGen Energy (NXE NYSE/TSX)** — Arrow 项目，Saskatchewan 高品位
- **Denison Mines (DNN NYSE/TSX)** — Wheeler River + 持 SPUT 股权
- **Paladin Energy (PDN ASX)** — Langer Heinrich 重启 + 2024-06 收购 Fission Uranium
- **Boss Energy (BOE ASX)** — Honeymoon 重启 + Alta Mesa 美国
- **Energy Fuels (UUUU NYSE)** — 美国 White Mesa Mill + 稀土副产品
- **Uranium Energy Corp (UEC NYSE)** — 美国 ISR + 物理 U3O8 持有
- **Ur-Energy (URG NYSE)** — Wyoming ISR
- **中广核矿业 (1164.HK)** — 中广核海外铀矿运营平台
- **Yellow Cake (YCA LSE)** — 物理铀持有信托（与 SPUT 性质类似）

### 转化/浓缩
- **Cameco Port Hope** — 北美主要转化设施
- **ConverDyn** (Honeywell + General Atomics JV) — 美国转化
- **Orano (法国国企)** — 转化 + 浓缩 + 燃料下游全产业链
- **Urenco** (英德荷联营 + 美国新墨西哥) — 西方最大浓缩
- **Centrus Energy (LEU NYSE)** — 美国唯一 HALEU 商业生产，Piketon Ohio 厂
- **Rosatom (俄国企)** — 转化 ~38% + 浓缩 ~44% 全球份额

### 金融化标的
- **Sprott Physical Uranium Trust (U.UN / U.U TSX)** — 物理铀持有，2021 起重塑铀市定价
- **Yellow Cake (YCA LSE)** — 同上欧洲版
- **URA / URNM ETF** — 美国铀 ETF，URA AUM ~$4B（2024）

## 三、产业链 / 竞争格局认知

**产业链结构**：铀矿（U3O8 yellowcake）→ 转化（UF6）→ 浓缩（SWU 富集至 3-5% U-235，HALEU 5-20%）→ 燃料组件 fabrication → 反应堆。每一段都有独立的产能、定价、地缘特征。

**矿端格局**：Kazatomprom + Cameco + Orano + CNNC + Rosatom 五家寡头占 ~70% 全球产量。ISR（地浸）方法（KAP 主力 + 部分美国/澳洲）成本最低 $25-30/lb，传统井下/露天 $35-60/lb。新矿项目从勘探到投产通常 8-12 年，监管 + 资金双重壁垒。供给端弹性极差。

**转化瓶颈**：四家供应商，Rosatom 占 ~38%。Cameco Port Hope 2024 年扩产至 12,000 tU/yr；ConverDyn 重启；Orano 法国 + 美国厂在扩。但西方扩产 lead time 5-7 年，2026-2028 仍紧。转化服务费已从 $7 涨到 $70+/kgU，10 倍。

**浓缩瓶颈**：Rosatom + Urenco + Orano 三家 + Centrus 小份额。HALEU（先进反应堆 + SMR 必需）西方实际产能近零，Centrus Piketon 是美国唯一商业线，2024 年级别仅几百 kg。X-energy / TerraPower / Oklo 商业化都卡在 HALEU 供应。DOE 拨款数十亿建 HALEU 联盟（Orano + Urenco + BWXT + Centrus）。

**地缘主线**：俄罗斯铀燃料链（转化 + 浓缩）占欧美进口 ~30-40%，2024 美国 Prohibiting Russian Uranium Imports Act 启动脱钩，但 2028 前给豁免。脱俄过程中，西方转化/浓缩 + Kazatomprom（中间路线国）受益。Niger 政变后 Orano 在西非受阻，全球铀矿地缘集中度反升。

**金融化主线**：SPUT 把"现货市场买盘"金融化了，囤铀 6500 万磅 U3O8（相当于 1 年全球 ~50% 产量）改变了铀价定价机制——从过去 ~20 年 utility 长协主导，转为现货 + 物理信托主导。这点是 2020 年后铀市最大结构变化。

## 四、训练知识盲点（自我承认）

- 2026 年内现货铀价的实际走势 / 当前价位（训练截止 2026-01 后约 4 个月）
- Kazatomprom 2026 年指引（FY2025 年报 2026-03 公布后的更新）
- Cameco McArthur River 2026 实际产量爬坡情况
- 2025-2026 是否有新矿真正进入商业生产（特别是 NexGen Arrow 是否提前/推迟）
- Trump 政府 2025-2026 对俄铀豁免政策的具体调整
- Centrus HALEU 2025-2026 年度产量与新订单
- TerraPower Natrium、X-energy Xe-100、Oklo Aurora 等 SMR 项目实际进度（vs 原定 2030）
- 中国 2025-2026 新批准核电机组数量与海外铀矿股权收购动态
- 2025-2026 hyperscaler 与核电厂新签 PPA 情况（继 MSFT-TMI、AMZN-X-energy 之后）
- SPUT 2026 实际物理购买活跃度（2024-2025 一度沉寂）
- Niger 矿产权处置最新进展（Orano vs Niger 军政府博弈）
- 澳大利亚自由党 2025 大选后核电政策（自由党承诺解禁核电）
- 主要 utility（Constellation/Vistra/Duke 等）2025-2026 新签长期采购合同情况
- 重大并购：Cameco/KAP/Paladin 是否被大矿企（BHP/RioTinto）盯上

## 五、需要 web-search 校准的优先项

**强制规则覆盖**：第一节 12 条快变 fact 必须全覆盖。

### P0 — 价格与供给现状
1. `2026 年 5 月 铀现货价格 U3O8 最新行情`（覆 fact-05）
2. `2026 年长期合约价格 uranium term price`（覆 fact-06）
3. `Kazatomprom 2026 年生产指引 production guidance`（覆 fact-09）
4. `Cameco 2026 Q1 财报 McArthur River 产量`（覆 fact-10）
5. `2026 年 UF6 转化价格 conversion price`（覆 fact-15）
6. `2026 年 SWU 浓缩价格 enrichment price`（覆 fact-17）

### P0 — 关键项目进度
7. `Paladin Energy Langer Heinrich 2026 产量爬坡`（覆 fact-24）
8. `Boss Energy Honeymoon 2026 production update`（覆 fact-25）
9. `Centrus Energy HALEU 2026 production shipment`（覆 fact-19）
10. `NexGen Energy Arrow 2026 进展 投产时间`（覆 fact-26）

### P1 — 地缘与政策
11. `Niger Orano 2026 最新进展 矿权 SOMAIR`（覆 fact-22）
12. `Trump 政府 2026 俄罗斯铀豁免 政策变化`（覆 fact-20 延伸）
13. `2026 中国新批准核电机组 核电规划`（覆 fact-28 延伸）

### P1 — 需求侧锚点
14. `2026 hyperscaler 新签核电 PPA Microsoft Amazon Google`（覆 fact-29/30 延伸）
15. `SMR 项目 2026 进展 NuScale TerraPower X-energy Oklo`（覆 fact-30 延伸）

### P2 — 资金面
16. `Sprott Physical Uranium Trust SPUT 2026 购买 NAV`（覆 fact-04 延伸）

**质检自检**：第一节快变 fact 12 条 → 第五节 query 16 条（含延伸） → 覆盖完整 ✓

## 六、prescan 校准结果（2026-05-28 回写）

> Step 4.5 prescan 入库 49 份 web-search material 后，对照第一节 fact-NN 的更新。
> prescan_status='partial' (hit_rate 67%)，所有 16 条快变 fact 优先 query 均有 hit 入库。

### 被推翻（高优先级 — thesis_v0 不要再引用原 fact）

- `[fact-05]` 训练时"现货 2024-01 触及 $107，2024Q4 $77-85" → `[mat-784991]` (TradingEconomics 2026-05-27) 实际 **$85.30/lb，过去一月跌 1.95%**；`[mat-ded408]` (TradeTech) 2026-01 $65.50/lb 上涨段 → **价格区间需重置为 $65-85/lb，2024 峰值后已回落 20%**
- `[fact-09]` 训练时"KAP 2025 指引 25kt"忽略 sulphuric acid 持续制约 → `[mat-826df0]` (KAP 4Q25 update) 显示 **2026 产量仍受 sulphuric acid availability 制约**；Mining.com 显示 **KAP 主动下调 2026 产量 5%**（市场条件考量） → 不是单纯爬坡，是 active production curtailment
- `[fact-10]` 训练时"Cameco McArthur 2022 重启爬坡" → Cameco IR landing 显示 **2026-05-27 McArthur River/Key Lake Resumes Production 公告**——说明此前**又一次停产**（baseline 完全错位）；`[mat-06d17b]` Q1 2026 MD&A 待深读
- `[fact-15]` 训练时"UF6 转化价 2024 峰值 $70+/kgU，10 倍涨幅" → `[mat-c516d1]` (DOE) 明确写"conversion prices were **$38/kgU as UF6 as of Sept. 30**" → **从峰值 $70+ 已大幅回落到 $38（-46%）**，这是 thesis 最重要的反转之一
- `[fact-22]` 训练时"Niger 政变后 Orano 受阻" → `[mat-c63c6b]` Bloomberg + `[mat-5ed2c5]` Mana Magazine 揭示：**2025-06 Niger 军政府宣布国有化 SOMAÏR**；Niger 现在准备退还 Orano 已产铀。**不是"受阻"，是已被夺走资产** → Orano 法语区铀矿地位重塑
- `[fact-25]` 训练时"Boss Honeymoon 2024 重启" → `[mat-a0245c]` discoveryalert：**2026-03 暴雨导致季度产量 -47-48% 下调**；CapitalBrief：**Boss 撤回 feasibility study (faulty production assumptions)** → 重大产能瑕疵，不只是"爬坡"
- `[fact-26]` 训练时"NexGen Arrow 预计 2027-2028 投产" → `[mat-ea2088]` + `[mat-5a0d79]` Canada.ca：**2026-03-05 CNSC 批准 EA + 颁发 Licence to Prepare Site**——这是历史性里程碑，意味着 Arrow 正式进入施工准备期；具体投产时点待 build phase 推进
- `[fact-19]` 训练时"Centrus HALEU 2024 几百 kg 小规模" → `[mat-50d57b]` + `[mat-3f4b8d]` (DOE)：**累计达 900 kg HALEU 交付里程碑**；`[mat-023bf6]` $110M 合同延期 + `[mat-2e6be9]` **$900M Ohio 扩产 grant** → 比 baseline 进度量级跃迁

### 被验证（可继续引用，置信度提升）

- `[fact-04]` SPUT 累计 ~6500 万磅 → `[mat-bfedfe]` 显示"World's Largest Physical Uranium Fund" + `[mat-423820]` **2026 announced $100M bought deal financing**（新增持） + SRUUF NAV $19.76 (2026-05-27) → SPUT 在 2026 重启活跃，置信度 高+
- `[fact-06]` 长期合约 ~$80/lb → `[mat-b606bf]` Oregon Group 2024 中长期 $79/lb；`[mat-4841bc]` 长期合约活跃度 picking up，与 baseline 一致
- `[fact-20]` Russian Uranium Imports Act → `[mat-ed9889]` Wikipedia + `[mat-f78a8b]` Congress.gov + `[mat-f69b45]` DOE waiver guidance 全部一致，置信度 高+
- `[fact-28]` 全球 437 reactor / 60+ 在建 → `[mat-347989]` WNA "440 reactor / 400 GWe / 2024 2667 TWh"，与 baseline 基本一致
- `[fact-24]` Paladin Langer Heinrich 重启 → `[mat-24cb6a]` + `[mat-7c8a49]` + `[mat-e69c7e]` 多源证实：**FY2026 产量指引上调 4.5-4.8M lb（vs 原 4.0-4.4M）**，朝 nameplate 6M lb (FY2027) 爬坡。trajectory 比 baseline 更乐观

### 新增重要事实（baseline 未捕捉）

- **`[new-01]` Solstice Advanced Materials 从 Honeywell 分拆，承接 ConverDyn 业务** (`[mat-9c0291]`) → 美国转化业务的纯 pure-play 出现
- **`[new-02]` Urenco USA 完成第 4 cascade gas centrifuge 安装** (`[mat-fd3099]`) → 西方浓缩端复苏在加速
- **`[new-03]` Centrus 获 DOE $900M grant + $110M 合同延期** (`[mat-2e6be9]` `[mat-023bf6]`) → 美国浓缩重建力度远超 baseline 想象
- **`[new-04]` 中国新五年计划信号继续核电建设** (`[mat-e80039]`) → 中国需求侧锚点强化

### 仍未校准（thesis_v0 引用时标 uncertain）

- `[fact-13]` 全球转化总产能 ~70kt 数据点缺更新源
- `[fact-16]` 浓缩 SWU 全球产能 ~63 MSWU 数据点缺更新源
- `[fact-17]` SWU 价格 2024 峰值 $170+ 与当前价位差，未拿到具体当前 SWU 价格数据
- `[fact-23]` Kazakhstan 政治风险 — 缺最新 NSG / 出口管制动作信息
- `[fact-27]` Denison Wheeler River 等 pre-production 项目最新进展未校准

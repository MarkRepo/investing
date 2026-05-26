---
slug: us-robinhood
output_key: 01_business_panorama
version: 1
generated: 2026-05-26
data_freshness: 2026-Q1（HOOD 10-Q）+ 2025-FY（HOOD/SCHW/IBKR/COIN 10-K）
data_freshness_basis: mat-8ed60a / mat-706061 / mat-32e412 / mat-c70cf2 / mat-eb3ef4 / mat-687a1d / mat-9730ab
---

# 商业全景：Robinhood Markets (HOOD)

> 生成于 2026-05-26，训练知识占比约 50%，资料数据更新至 2026-Q1

## 行业定义与边界

HOOD 落在三个高度交叉的赛道上：
- **零售在线券商**（核心）：股票/期权交易、保证金贷款、IPO 通道；主要竞品 IBKR / SCHW / FUTU
- **加密资产经纪**：自营现货 + Bitstamp 交易所；竞品 COIN / Kraken / Gemini
- **泛金融超级 App**：Gold 订阅、Banking（与 Coastal Bank BaaS）、Strategies 管理账户、Cortex AI 投研、Robinhood Ventures Fund (RVI)；竞品 SQ / SoFi / Cash App

边界外：传统财富管理（信托/保险/养老金管理整体生态）、银行存贷主营、加密原生 L1/DEX 协议层。SIC 6211 / GICS 4020 / SW 银行+多元金融。

## 市场规模与结构

- **美国零售券商市场**：客户资产规模 ~$30T（2025），SCHW $11.9T 居首约 40%，Fidelity ~$15T 综合（含 401k 托管），HOOD $307B 约 1%（按账户口径，按用户数则 27M vs SCHW 36M ≈ 75%）。年化交易佣金池估算 ~$15-20B（含 PFOF rebate）
- **美国加密交易市场**：日均现货交易量 cycle 高峰 $50-80B / 低谷 $15-25B（2026-Q1 处低谷），COIN 占美国零售 ~50%，HOOD App + Bitstamp 合计 ~10-15%
- **CFTC Prediction Markets**：年化合约交易量在 2024 大选驱动下首次破百亿合约，2025-2026 转入"事件 + 利率/经济指标"长青形态；Kalshi 估值 $11B（2025-11，K7 mat-e9d55a），HOOD 通过 Kalshi 合作 + MIAXdx 收购走"分销 → 自建"路径
- 集中度：传统券商 CR3（Fidelity + SCHW + Morgan Stanley E*Trade）≈ 75%；HOOD 是 CR3 之外最大独立玩家；加密 CR3（COIN + Binance.US + Kraken）≈ 60%

## 价值链解析

```
[零售用户] ↓
[订单流量] →（HOOD App / Bitstamp / Robinhood Derivatives 入口）
       ↓
[订单路由 / PFOF rebate] →（Citadel Securities / Virtu / Susquehanna 等做市商）
       ↓                          ↑（PFOF 回款占 HOOD 季度收入 65-80%，mat-599824）
[清算/托管] →（DTCC 股票 / OCC 期权 / Bitstamp 自营加密 / MIAXdx 衍生品）
       ↓
[现金 sweep] →（Coastal Bank BaaS）
       ↓
[财富产品] →（Strategies 0.25% 管理费 / Gold 订阅 $50/mo / Gold Card / Banking）
```

价值链中各环节毛利率：
- **PFOF 收入**：边际利润 ~95%（无变动成本）— HOOD 最高毛利来源
- **净息收入**：margin lending 利差 ~3%，segregated cash + securities lending 利差 ~1%
- **Gold 订阅 / Strategies**：边际利润 ~85%（订阅 SaaS 模型）
- **Event Contracts**：take rate 极低（$147M / 8.8B 合约 ≈ $0.017/合约），但成本极低，毛利率高
- **Bitstamp**：现货 spread + maker/taker fee（institutional 占比高，take rate 较 COIN Consumer 139 bps 显著低）

## 商业模式

HOOD 是 **混合三引擎**：
1. **交易引擎（59% FY25 收入）**：股票/期权/加密 PFOF + 鉴权 fee（Event Contracts），Q1'26 占比降至 56%
2. **净息引擎（34% FY25 收入）**：客户现金 sweep + margin lending + segregated cash + securities lending；2026 降息周期对 corporate cash 利率敏感（FY25 corporate cash 收入 -35%）
3. **订阅 + 财富引擎（7% FY25 收入，但增速 +70%）**：Gold $50/mo + Strategies 0.25% + Gold Card + Banking BaaS spread + RVI 募资费

收入结构变化方向：交易→订阅+财富（thesis K5 主轴）；但 Q1'26 显示 Net Income +3% << Revenue +15%（mat-a6e176），OpEx 失控（2026 guidance $2.7-2.825B 含 $100M Trump Accounts）

## 需求端分析

**核心用户群体**：
- **年轻零售投资者**（核心）：18-40 岁，单户资产 $11k（mat-8ed60a），低于 IBKR 单户 $166k（mat-687a1d）15× 和 SCHW $326k 30×
- **加密原生用户**：通过 HOOD App / Bitstamp 入场，2026 cycle 下行已显著影响活跃度（Crypto rev -47% Q1'26）
- **Gold 订阅用户**（4.34M Q1'26，占 funded 16%）：更高 ARPU 群体，是 thesis K3/K5 核心
- **RIA 托管客户**（TradePMR 收购后 $42.5B AUM）：B2B 渠道首次进入 HOOD 报表

**购买决策驱动**：
- 零佣金（vs SCHW 已跟进零佣，差异化收窄）
- 移动端 UX（Gen Z 黏性）
- 加密 + 预测市场 + Banking 一站式（差异化护城河，但 SCHW 2026-04 已宣布加密上线 → K6 触发）
- Gold 高收益 sweep + 3% IRA match

**需求增长驱动**：
- 美国零售投资人口扩张（27M HOOD funded vs SCHW 36M 总户）
- 利率周期：降息周期对券商资产规模有利但净息收入承压
- 加密渗透率：长期向上但 2026 处 cycle 下行
- Prediction Markets 新品类（2024 大选 → 2027 大选周期 + 利率/经济指标长青）

## 供给端分析

**主要参与者**：
- **传统巨头**：SCHW（$11.9T，含 TD Ameritrade 整合）、Fidelity（私营，~$15T 含 401k）、Morgan Stanley E*Trade
- **专业自动化**：IBKR（4.75M 账户，国际化龙头，pretax margin 77%）
- **互联网原生**：HOOD、SQ Cash App（投资功能）、SoFi、Webull
- **加密原生**：COIN（FY25 营收 $7.18B）、Kraken（IPO 推进中）

**进入壁垒**：
- **监管牌照**：FINRA broker-dealer + 各州/海外加密 license（MiCA / VASP / 新加坡 MAS）+ CFTC DCM/DCO（Prediction Markets）
- **资本要求**：净资本 + 客户保护规则要求 $10亿+ 注册资本
- **技术**：自营订单路由 + 实时风控 + 24/7 加密清算的全栈（IBKR 50 年技术积累壁垒最高）
- **品牌**：年轻用户黏性（HOOD 强项）vs 高净值信任（SCHW/Fidelity 强项）
- **规模效应**：PFOF 议价权 + Banking sweep 利差需要规模 → 头部双寡头化

**产能 / 供给增速**：用户数增长全行业放缓（HOOD Funded Customers +6% Q1'26 vs FY25 +7%），但 ARPU 和产品深度仍在扩张；新进入者主要靠加密原生 / 预测市场切入

## 竞争格局

**格局类型**：**两极化** — 传统巨头（SCHW/Fidelity）垄断高净值 + 401k，HOOD 占据零售年轻端，中间梯队（IBKR 国际化、COIN 加密专业、Webull 中文背景）形成"垂直深耕 + 跨界进入"双向夹击

**核心竞争要素**（不超过 3 个）：
1. **客户单户资产/ARPU**：决定净息和管理费的天花板（HOOD $11k vs IBKR $166k vs SCHW $326k）
2. **产品广度**：股票/期权/加密/futures/forex/bonds/预测市场全栈程度（IBKR 最全 / HOOD 最年轻化创新 / COIN 加密专精）
3. **执行质量 + 监管承接**：PFOF 阶段后 Rule 605 公开（2026-08），将首次公开可比

**行业龙头优势来源**：
- **SCHW**：客户资产规模 + RIA 渠道 + 全产品（2026-04 启动加密填补最后短板）+ 银行牌照
- **HOOD**：年轻用户 + 加密 + Banking + Event Contracts + Bitstamp 国际化（多元化最快但深度浅）
- **IBKR**：自动化效率（pretax margin 77%）+ 200+ 国家 / 39 国子公司国际化护城河 + ForecastEx 全栈预测市场
- **COIN**：加密 IPO 第一股 + Deribit 机构衍生品 + USDC 利息分成

## 发展阶段

**阶段判断**：**成长期中后段**

- HOOD 自身仍处快速扩张：FY2025 收入 +52%，Q1'26 +15% 进入"高位减速"
- 行业整体（零售券商）已进入成熟期，CR3 集中度 75%；HOOD 是成熟行业里的成长股
- 加密赛道处 cycle 下行 + 监管成熟期（CLARITY Act / GENIUS Act 已落地）
- Prediction Markets 处导入期到成长期切换（Kalshi $11B 估值锚）

**判断依据**：
- HOOD 客户数 +6% YoY 已显著放缓（成熟期信号）
- ARPU +8% 仍正增长（深耕变现，未饱和）
- 多元化第二曲线（Gold/Banking/Strategies/Event Contracts）兑现速度差异大，Gold 兑现 / Event Contracts 兑现 / Banking/Strategies AUM 化仍需 12-24 个月
- Net Income 增速 +3% << 收入 +15%（Q1'26）显示 OpEx 阶段领先收入，未进入运营杠杆释放期
- 对比 IBKR 已进入"零边际成本扩张"（FY25 非利息成本 -4% 同时收入 +20%），HOOD 至少落后 5 年

## 信息来源

- mat-706061 (2025_HOOD_10-K)：业务结构、收入拆解、用户数、监管时间线
- mat-8ed60a (2026_HOOD_Q1_10-Q)：Q1'26 实时数据、Margin Book、Gold 订阅、Event Contracts
- mat-a6e176 (Yahoo Q1'26 摘要)：Q1 各品类收入分解、April MTD 反弹
- mat-4c5f6e / mat-a99410 (HOOD IR press releases)：FY2025/Q1'26 官方口径
- mat-eb3ef4 / mat-687a1d (IBKR 10-K/10-Q)：自动化券商盈利上限 + 国际化护城河锚
- mat-32e412 / mat-c70cf2 (SCHW 10-K/10-Q)：传统巨头规模锚 + **2026-04 加密上线**
- mat-9730ab / mat-0f5222 (COIN 10-K/10-Q)：加密专业户对标 + cycle 同步性 + take rate 量级
- mat-599824 / mat-6abade (CRS / SEC.gov)：PFOF 监管时间表
- mat-188ea6 / mat-24d0dd / mat-ad0673 (HOOD newsroom)：Strategies/Banking/Prediction Markets 产品
- mat-409ba8 / mat-7475c0 (Bitstamp blog / CoinMarketCap)：K4 take rate 反证
- mat-115c1e / mat-e9d55a / mat-1daa0f / mat-abea64 (第三方综合)：SpaceX IPO / 收购清单 / 估值数据
- 训练知识：行业历史结构、SCHW/Fidelity/COIN 历史 PE 分位、加密 cycle 一般框架

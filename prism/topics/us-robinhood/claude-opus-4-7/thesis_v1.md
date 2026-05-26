---
slug: us-robinhood
variant: claude-opus-4-7
version: 1
parent_version: 0
generated: 2026-05-26
writing_convention: 方案 C 全快照 + 顶部 changelog
data_freshness: 2026-Q1（HOOD/IBKR/SCHW/COIN 完整 10-K + Q1 10-Q + 14 份 web-search 校准）
data_freshness_basis: 22 份 findings + market_data 2026-05-22
---

# Robinhood Markets (HOOD) thesis_v1

## § 0. v0 → v1 changelog

- **强度评分调整**：v0 7/10 → v1 6/10（中性偏多收窄至中性，主因 K1 时间窗收窄 + K4 take rate 假设证伪 + K6 SCHW 加密反扑触发）
- **新增关键发现 1**：**SCHW Q1'26 10-Q 披露 2026-04 启动现货加密交易**（CSPB 自托管 + Paxos 子托管） — K6 边缘叙事从远端变近端
- **新增关键发现 2**：HOOD Q1'26 **Net Income 仅 +3%**（vs 收入 +15%），OpEx 失控明显（2026 guidance 上调至 $2.7-2.825B 含 $100M Trump Accounts）
- **新增关键发现 3**：HOOD Q1'26 **Crypto volumes -48% / revenue -47%** 同步 → Bitstamp 整合后 take rate 假设证伪（K4 partly_refuted）
- **新增关键发现 4**：PFOF 监管时间表确定 — 2026-05-01 SIPs odd-lot / 2026-08-01 Rule 605 / 2026-11 tick size 三连发（不是 2028 后远端事件）
- **新增关键发现 5**：IBKR 是真正的"自动化券商终局"参照系（pretax margin 77% / PE 22-27 / 客户单户 $166k vs HOOD $11k 15× 差距）— 估值上限锚
- **新增反方观点**：现价 $73.64 vs 模型 B 公允 $52 + 模型 C 公允 $45 + 模型 A base $64 加权 → **合理中枢 $55-65，现价隐含 15-30% 下行**
- **新增 K7（保留 v0）**：Event Contracts $147M (+320% YoY) 验证爆发，但 $0.017/合约 take rate 极低；2027 大选后可持续性是 K7 真正考验
- **未变章节**：核心 thesis 长期方向"中性偏多"未变，仍认为 HOOD 5-15 年具有 SCHW 历史路径潜力；但短期 12 个月 entry 时机推迟

## § 1. 核心 thesis（当前完整版）

**中性，强度 6/10**：HOOD 5-15 年长期持有逻辑仍成立（多元化第二曲线兑现 + Gen Z 客群结构性 tailwind + 国际化 + 预测市场 + Banking + RVI），路径类似 SCHW 1998-2024 的 25 年 250× 长牛。但当前价 $73.64 已较饱满（PE 35.75 / PS 14.38 / Forward PE 38.21），隐含 5 年 CAGR 18-22% 显著高于 Q1'26 +3% Net Income 实际值；同时 12 个月内 4 大近端催化剂（2026-05 SIPs odd-lot / 2026-08 Rule 605 / 2026-11 tick size / SCHW 加密 ramp）均偏空。**合理中枢 $55-65（模型 A/B/C 加权 base）；强力买入区间 $45-55**。

- 估值带：**$45-55 强力买入 / $55-65 可建仓 / $65-80 观望 / >$80 减仓**
- 时间维度：**3-5 年持有期**，覆盖完整加密 cycle + 监管落地 + 2028 大选监管再起观察
- 当前操作：**不追高建仓**；若已持仓，保留 50% 底仓 + 等回调至 $60 区间分批补仓

## § 2. 支持理由（当前完整清单）

### 2.1 业务面（已被 22 份 findings 验证）

1. **多元化第二曲线兑现进度领先同业**（K3 + K5 supported）
   - Gold Subs Q1'26 4.34M (+36% YoY)，Q4'25 4.18M (+58%)；Gold 渗透率 15.5% 稳态（mat-8ed60a / mat-4c5f6e）
   - Total Platform Assets Q1'26 $307B (+39% YoY)，含 TradePMR $42.5B RIA AUM 首次并表（mat-706061）
   - Margin Book $17.0B (+93% YoY) — 净息收入主驱动（mat-a6e176）
   - Strategies / Banking / Cortex 三件套 2025 已发布；RVI Q3 2025 招股；MIAXdx 2026-01 并购完成自建预测市场

2. **Bitstamp 国际化 + Event Contracts 是差异化护城河（K4 部分 + K7 + 国际化）**
   - Bitstamp 加密交易量已超 HOOD App（$48B vs $34B Q4'25），机构占比上升（mat-7475c0）
   - 2026-02 BVI VASP 牌照 + MiCA + MiFID + 全球合规护城河（mat-409ba8）
   - Event Contracts Q1'26 $147M (+320% YoY) + 8.8B record 合约，CFTC 全栈（Kalshi 合作 + MIAXdx 自建）
   - Tracxn 显示 13 起收购加速（mat-e9d55a），含 WonderFi（加拿大）+ 印尼加密 + MIAXdx

3. **资本回报支持估值 + 管理层信号**
   - Q3'24 至今累计回购 $1.2B（22M 股 @ avg $40.64）；Q1'26 单季 $250M @ avg $81 — 高位回购信号
   - CFO Verma 提到 April 单月 "highest month of the year" + MTD $5B 净存款（mat-a6e176）

4. **PFOF 短期暂安全**（K1 短期利好）
   - Trump SEC 不撤规则只是不执法；2025-2029 任期内监管执法风险低（mat-6abade）
   - OCR Rule 在册但 stalled；EU 已禁但 HOOD 美国本土主战场（mat-599824）

### 2.2 财务面（一手 SEC 数据支撑）

5. **FY25 财务历史最佳**：收入 $4.473B (+52%) / Net Income $1.883B (+33%) / Adj. EBITDA $2.522B (+76%) / Net Margin 42%（mat-706061）
6. **Net Interest 收入扩张**：FY25 $1.514B (+37%)，Margin Interest +80% / Securities Lending +102% / Credit Card +167%（mat-706061）
7. **客户深度高净值化**：FY25 ARPU $171 (+40%) / Total Platform Assets $322B (+67%) 含 TradePMR 整合 + Net Deposits $68.1B
8. **回购规模可观**：$1.2B 总回购 vs 市值 $66.3B = 1.8%

### 2.3 战略面

9. **SpaceX IPO 散户分销**（2026 H1 重大业务催化，mat-115c1e）
10. **Robinhood Banking + Trump Accounts**（与 Coastal Bank + BNY 合作）— 银行 BaaS + 政府账户对接

## § 3. 反方观点（当前完整清单）

### 3.1 业务面（被 Q1'26 数据强化）

1. **Funded Customers 增速骤降至 +6%**（Q1'26 vs FY25 +7% / FY24 +9%）— 用户基数增长基本停滞，所有 KPI 增长靠 ARPU + 多元化变现 + 收购（mat-a6e176）
2. **Net Income +3% << Revenue +15%**（Q1'26）— OpEx 失控；2026 guidance 上调至 $2.7-2.825B（含 $100M Trump Accounts）；运营杠杆故事难以维持（mat-a6e176）
3. **Bitstamp take rate 假设证伪**（K4 refuted）：Crypto volume -48% / revenue -47% 几乎完全同步，institutional 占比上升通常拉低 take rate；COIN Consumer take rate 139 bps vs Institutional 4.9 bps 量级差异 28×，验证 take rate 不可比（mat-7475c0 / mat-9730ab）
4. **Crypto cycle 下行已触发**（K2 confirmed）：Q1'26 Crypto rev -47% / volumes -48%；COIN Consumer -54% 验证全行业 cycle（mat-0f5222）
5. **Churn 翻倍**：Churned Customers 从 FY24 0.9M → FY25 1.7M（+89%），真实 organic 净增仅 0.8M；留存承压（mat-706061）
6. **平台资产中加密占比从 18%→12%**：加密资产被股票牛市稀释；HOOD 已不再是纯加密 high-beta proxy

### 3.2 监管面（K1 时间窗收窄）

7. **PFOF 监管时间表已确定**（K1 partly_refuted）：2026-05-01 SIPs odd-lot 公开 / 2026-08-01 Rule 605 执行质量披露 / 2026-11 tick size + access fee cap 合规；管理层明示"expect could lead to a decrease in PFOF"（mat-706061）
8. **HOOD PFOF 占季度收入 65-80%**（mat-599824，远高于市场认知 ~50%）— 监管落锤的杠杆比想象更大
9. **EU 已全面禁 PFOF**（mat-599824） — 美国跟进路径风险存在但概率不高（短期）；2028 大选后民主党回归可能立法

### 3.3 竞品面（K6 已触发）

10. **SCHW 2026-04 启动现货加密交易**（K6 已触发，最关键的新发现）：通过 CSPB 自托管 + Paxos 子托管，BTC/ETH 优先；SCHW $11.77T 客户资产潜在加密渗透空间巨大，可吸收 $50-100B 加密迁移（mat-32e412）
11. **IBKR 全栈 ForecastEx vs HOOD-Kalshi 合作劣势**：IBKR 100% 持有 ForecastEx CFTC DCM/DCO；HOOD 通过 Kalshi 分销 + MIAXdx 收购自建初期；监管承接、清算费收入、产品迭代 IBKR 全拿（mat-eb3ef4）
12. **IBKR 国际化护城河领先 5-10 年**：IBKR 200+ 国家 / 39 国子公司 / 29 种货币 / 170+ 交易所；HOOD 仅 US+UK+EU 初步落地；客户单户 $166k vs HOOD $11k = 15×差距（mat-687a1d）
13. **COIN Deribit 机构衍生品**：COIN 已通过 Deribit $4.3B 收购占住机构期权 + 永续；HOOD Bitstamp 仍以现货为主；机构客户 spread 大头在衍生品（mat-9730ab / mat-0f5222）

### 3.4 估值面（critic 强反驳）

14. **当前价 $73.64 vs 合理中枢 $55-65 隐含 15-30% 下行**：模型 A base $64 / 模型 B $52 / 模型 C $45 — 三模型独立运算均低于现价
15. **同业横截面 HOOD 溢价 +38%**：同业平均 PE 26x vs HOOD 35.75x；调整后公允 PE 应为 20-22x（IBKR 区间）
16. **Forward PE 38.21 > Trailing PE 35.75**：EPS 共识小幅下修信号（mat-1daa0f）
17. **基本盘 + 期权拆解显示市场对期权估值 2.1× 高估**：基本盘 $29B + 我估算期权 $17.5B vs 市场给期权 $37B

### 3.5 治理面

18. **Dual-class B 股 10× 投票权 + Vlad Tenev 历史套现 >$1B**
19. **2025 Steadview Capital Q2 大额减持** — 机构信心警讯（thesis_v0 已提）
20. **Rothera JV 治理结构**：HOOD 90% LP + 多数董事 → MIAXdx 全并表（含 SIG 10%），治理风险与财务风险不匹配（mat-706061）

## § 4. Killer Question 现状表（K1-K7 完整）

| K# | 主题 | 当前状态 | 触发条件 | 关键 mat |
|----|------|---------|---------|---------|
| K1 | PFOF 监管 | **partly_refuted（时间窗收窄）** | 2026-08 Rule 605 数据负面 / 2026-11 tick size 后 PFOF -10%+ QoQ | mat-706061 / mat-599824 / mat-6abade |
| K2 | 加密 cycle 下行 | **confirmed（已触发 -47%）** | BTC 跌破 $60k + Crypto rev 跌破 $100M/Q | mat-8ed60a / mat-0f5222 / mat-7475c0 |
| K3 | Gold 飞轮 | **supported（仍强但减速）** | Gold subs YoY <+25% 连续 2 季度 | mat-8ed60a / mat-4c5f6e |
| K4 | Bitstamp take rate | **refuted（take rate 假设证伪）** | Bitstamp take rate 实际下行 + 收入贡献仍 1-2% | mat-7475c0 / mat-8ed60a / mat-9730ab |
| K5 | 财富管理 AUM | **supported（兑现加速）** | Strategies/Banking AUM 2026 底突破 $30B | mat-8ed60a / mat-706061 / mat-188ea6 |
| K6 | 竞品反扑 | **confirmed（SCHW 加密已触发）** | SCHW 加密 AUM > $20B 12 个月内 | mat-32e412 / mat-c70cf2 |
| K7 | Event Contracts 可持续 | **unverified（爆发已发生）** | Q1'27（2026 大选后）YoY > +50% | mat-8ed60a / mat-ad0673 / mat-24d0dd / mat-e9d55a |

## § 5. 应对策略矩阵

| 价格区间 | 动作 | 理由 |
|---------|------|------|
| **>$95**（PE 45+） | 减仓至 0-1%（仅留底仓 / 全清） | 估值超 super-bull 概率 10% 区间 |
| **$80-95**（PE 38-45） | 观望，新增仓位为 0 | 估值已超合理中枢 30%+ |
| **$65-80**（PE 30-38）当前 | 持有现有底仓，不新增 | 现价 $73.64 在此区间，等回调 |
| **$55-65**（PE 26-30） | 分批建仓首仓 1-3% | 模型 A base 公允区间 |
| **$45-55**（PE 21-26） | 强力买入 / 加仓至 5-6% | 模型 B/C 公允 + 15-20% 安全边际 |
| **$35-45**（PE 16-21） | 极强买入 / 加仓至满仓 8% | 模型 C bear + 极限折价 |
| **<$35**（PE <16） | Kill criteria 触发自检；若基本面未坏则继续加仓 | 需先判断是估值杀还是基本面杀 |

## § 6. catalyst 时点表

| 时间 | 事件 | 重要性 | 多 / 空判读 |
|------|------|------|-----------|
| 2026-05-01 | SIPs odd-lot 数据开始公开 | M | 媒体反应 |
| 2026-07-31 | HOOD Q2'26 财报 | H | Net Income 是否回升 +15% |
| 2026-08-01 | SEC Rule 605 执行质量披露生效 | **CRITICAL** | HOOD 执行质量排名 |
| 2026-08-01 | SCHW Q2'26 财报（加密上线 4 个月） | **CRITICAL** | SCHW 加密 AUM 规模 |
| 2026-10-31 | HOOD Q3'26 财报 | H | Bitstamp 整合 + Net Income 趋势 |
| 2026-11-01 | SEC tick size + access fee cap 合规 | **CRITICAL** | PFOF 收入 Q4 QoQ |
| 2026-11-04 | 美国中期选举 | H | 民主党参议院结果 |
| 2027-02-28 | HOOD FY2026 财报 | H | 全年定盘 |
| **2027-04-30** | **HOOD Q1'27 财报（大选后第一季度）** | **CRITICAL** | **K7 Event Contracts 可持续性** |
| 2027-H1 | SpaceX IPO 兑现（如发生） | M | HOOD 散户分销规模 |
| 2028-11 | 美国大选 | H | 监管环境再起 |

## § 7. 数据缺口

### P0（必须填补，影响核心判断）
1. **PFOF 收入对各品类敏感性弹性**：tick size 后 small-tick equity PFOF 收入弹性？管理层仅给方向，未给数字
2. **SCHW 加密上线后 6-12 月真实 AUM 数据**：决定 K6 实质性程度
3. **Bitstamp 独立财务数据**：take rate / 利润率 / 整合协同时间表（10-K 仅说 1% FY25 收入 ≈ $45M）

### P1（重要，影响中期判断）
4. **Gold→Banking→Strategies 转化漏斗**：单户 LTV / 转化率
5. **HOOD 用户结构 demo**：18-30 / 30-50 / 50+ 占比；与 SCHW Starter Kit 用户重叠度
6. **Event Contracts 品类细分**：利率合约 vs 大选合约 vs 体育合约 占比
7. **加密 OAuth 内幕**：Bitstamp 收入是否包含 staking yield / institutional vs retail 比例

### P2（次要，可后续深挖）
8. **Bitstamp 各国监管合规进度时间表**
9. **MIAXdx 整合 12-18 月计划**（Rothera JV 与 SIG 分工）
10. **SpaceX IPO 散户分销具体条款**

**期望解决路径**：
- P0：等 2026-Q2-Q3 财报（7-10 月）+ SCHW 季度披露 + Bitstamp 第一个完整年度（FY26）
- P1：dispatch drilldown subagent 跨数据库挖单户 LTV / demo
- P2：等公开材料 / 行业大会 / 卖方深度

## § 8. 思维过程留痕

### 8.1 已知
- HOOD 商业模式已经从"PFOF 单引擎"完成转型，5 引擎多元化是事实（FY25 数据支撑）
- 加密 cycle 当前在下行段，已部分反映在 Q1'26 数据
- 美国零售券商行业是寡头格局，HOOD 作为 #4 玩家被淘汰概率低
- IBKR 是自动化券商的真正终局参照系，pretax margin 77% 是 HOOD 估值天花板
- SCHW 2026-04 启动加密是 K6 实质性触发

### 8.2 刻意避开的偏见
- **"超级 App = 估值溢价"叙事偏差**：刻意用 IBKR/SCHW PE 22-25 区间作为基准而非 SaaS PE 30+
- **"多元化 = 抗周期"叙事偏差**：在 06 中刻意找出"5 个引擎同时 cycle-sensitive"的反证
- **"Trump SEC 不执法 = PFOF 安全"叙事偏差**：用监管时间表（2026-05/08/11）反驳"远端事件"假设
- **"卖方 27 analyst Buy 共识 +29%"权威偏差**：模型 A/B/C 三独立估值均低于现价 → 反映共识可能过乐观
- **"高位回购 = 管理层信心"叙事偏差**：管理层信号是 1 个数据点，与 Steadview Q2 大额减持机构信号矛盾
- **"加密 + Event Contracts 差异化护城河"叙事偏差**：SCHW 加密上线 + IBKR ForecastEx 同时攻入

### 8.3 关键差异（vs 主流卖方共识）
| 维度 | 卖方共识 | 我的判断 |
|------|---------|---------|
| 12M 目标价 | $98 (+29%) | $55-65 (-15% 到 -25%) |
| 强度评分 | Buy（隐含 7-8/10） | 6/10 中性 |
| Net Income 2026 增速 | 隐含 +20-25% | +5-10%（OpEx 失控为结构性） |
| K1 PFOF 风险 | 2028 后远端 | 12 个月内三连发 |
| K4 Bitstamp take rate | 提升 50%+ | 持平或下行 |
| K6 SCHW 加密风险 | 默认未发生 | 2026-04 已触发 |

## § 9. 信息来源

### 训练知识占比：约 30%
- 主要用于：估值框架（DCF/相对估值/SaaS vs 券商）、历史镜像（SCHW/ETFC/SQ/FUTU 完整路径）、行业周期框架、Cash App 历史对比

### 关键 mat_id（22 份完整）
- **HOOD 一手 SEC**：mat-706061（FY25 10-K）/ mat-8ed60a（Q1'26 10-Q）
- **同业 10-K/10-Q**：mat-eb3ef4 / mat-687a1d（IBKR）/ mat-c70cf2 / mat-32e412（SCHW）/ mat-9730ab / mat-0f5222（COIN）
- **HOOD IR / Yahoo**：mat-a99410（Q1'26 PR）/ mat-4c5f6e（FY25 PR）/ mat-a6e176（Yahoo Q1'26 深度）
- **HOOD newsroom**：mat-188ea6（Strategies/Banking/Cortex）/ mat-24d0dd（Prediction Markets Hub）/ mat-ad0673（JV 扩展）
- **监管政策**：mat-6abade（SEC.gov OCR）/ mat-599824（Congress CRS）
- **Bitstamp / 加密对标**：mat-409ba8（Bitstamp blog）/ mat-7475c0（CoinMarketCap K4 反证）
- **第三方综合**：mat-115c1e（SpaceX IPO）/ mat-e9d55a（Tracxn 收购 + Kalshi $11B）/ mat-1daa0f（PE 历史）/ mat-abea64（卖方共识）
- **市场数据**：market_data 自动获取（yfinance）2026-05-22

### 综合产出参考
- 本 thesis 引用了 _synthesis_brief 的 K1-K7 v0→v1 校准结论
- 估值模型详见 04_implied_expectations
- 仓位框架详见 07_decision_kit + 07_decision_kit.yaml
- 监控清单详见 06_risk_blindspots

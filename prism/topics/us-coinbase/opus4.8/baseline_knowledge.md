---
slug: us-coinbase
variant: opus4.8
written_at: 2026-07-14
training_cutoff_estimate: 2025-10
---

# 训练知识 Baseline — Coinbase (COIN, NASDAQ)

> 本文记录 LLM 在**训练截止时**对该 topic 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。

## 〇、基本信息（company）

- **主代码**：`US_COIN`（NASDAQ 上市，2021-04 直接上市 direct listing）
- **多市场上市**：单市场（仅 NASDAQ）
- **市场属性**：美股常规交易时段 9:30-16:00 ET；含盘前盘后；被动指数纳入是重要资金事件（见 fact-05）
- **公司定位**：美国最大的合规加密货币交易所 + 加密基础设施（托管/稳定币/L2）平台。创始人兼 CEO Brian Armstrong（2012 与 Fred Ehrsam 共同创立）

## 一、关键事实记忆（20 条）

**收入与业务结构**
- `[fact-01]` Coinbase 收入高度顺周期，随加密牛熊剧烈波动：FY2021(牛市)净收入约 $7.8B，FY2022 约 $3.2B，FY2023 约 $3.1B，FY2024 约 $6.6B → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-02]` 交易收入（consumer + institutional 佣金）是最大且最顺周期的收入源；订阅与服务收入(Subscription & Services)是公司主推的"抗周期"第二增长曲线 → 置信度：高 | time_sensitivity：慢变
- `[fact-03]` 订阅与服务收入包含：稳定币(USDC)利息分成、Blockchain rewards(staking 质押)、托管费(custody)、Coinbase One 订阅、利息收入 → 置信度：高 | time_sensitivity：慢变
- `[fact-04]` 零售交易 take rate 较高(约 1.5-2%+)，机构交易 take rate 极低——收入结构里零售贡献利润远高于其交易量占比 → 置信度：中 | time_sensitivity：慢变
- `[fact-05]` Coinbase 于 2025-05 被纳入 S&P 500 指数（首个纳入标普500的纯加密公司），带来被动资金买入 → 置信度：中 | time_sensitivity：**快变** ⚠️

**稳定币 / USDC**
- `[fact-06]` USDC 是 Circle 发行的稳定币，Coinbase 与 Circle 有收入分成协议：Coinbase 获得其平台上持有 USDC 的 100% 储备利息 + 平台外部分约 50% 分成 → 置信度：中 | time_sensitivity：慢变
- `[fact-07]` Circle 于 2025-06 完成 IPO(CRCL)；上市后 Coinbase-Circle 的分成条款/竞合关系是关注点 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-08]` 稳定币利息收入高度依赖美联储利率——降息周期会直接压缩这部分收入 → 置信度：高 | time_sensitivity：慢变
- `[fact-09]` GENIUS Act(联邦稳定币立法)于 2025-07 签署成法，建立美国稳定币联邦监管框架 → 置信度：中 | time_sensitivity：**快变** ⚠️

**监管**
- `[fact-10]` SEC 于 2023-06 起诉 Coinbase 涉未注册证券交易所；Gensler 卸任、Paul Atkins 任 SEC 主席后，SEC 于 2025 年初(约 2025-02)撤诉 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-11]` Trump 政府(2025 上任)整体亲加密；Coinbase 是加密行业 PAC(Fairshake)的主要出资方，政治游说是其护城河策略之一 → 置信度：中 | time_sensitivity：慢变
- `[fact-12]` 市场结构立法(CLARITY Act / market structure bill)将界定 SEC vs CFTC 对加密资产的管辖权，是行业级监管确定性来源，训练时状态为"众议院推进中/未最终成法" → 置信度：低 | time_sensitivity：**快变** ⚠️

**托管 / ETF**
- `[fact-13]` 美国现货比特币 ETF 于 2024-01 获批；Coinbase 是绝大多数现货 BTC ETF(含 BlackRock IBIT)的托管方，这是重要的机构托管收入与关系锚 → 置信度：高 | time_sensitivity：慢变
- `[fact-14]` 现货以太坊 ETF 于 2024 年年中获批，Coinbase 同样为主要托管方 → 置信度：中 | time_sensitivity：慢变

**衍生品 / 扩张**
- `[fact-15]` Coinbase 2025 年宣布收购 Deribit(全球最大加密期权/衍生品交易所)，对价约 $2.9B，大幅扩张衍生品业务 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-16]` Coinbase 运营 Base(基于 OP Stack 的以太坊 L2，2023 上线)，是其链上生态与潜在长期变现入口 → 置信度：中 | time_sensitivity：慢变

**竞争 / 市场**
- `[fact-17]` Binance 是全球交易量最大的交易所，但 2023 年 CZ 认罪辞职、缴 $4.3B 和解金，监管受限；Kraken(筹划 IPO)、Robinhood(收购 Bitstamp 扩张加密)、Gemini 是主要竞争者 → 置信度：中 | time_sensitivity：慢变
- `[fact-18]` 比特币价格在 2024 年底突破 $100K，2025 年持续在高位(训练记忆约 $90K-$120K 区间波动)——直接驱动 Coinbase 交易量与收入 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-19]` Coinbase 市值训练记忆在约 $50B-$90B 区间大幅波动，估值随加密周期起伏、P/E 极不稳定 → 置信度：低 | time_sensitivity：**快变** ⚠️

**资产负债 / 其他**
- `[fact-20]` Coinbase 自持一定量加密资产(含比特币)在资产负债表上，采用公允价值计量后其净利润受币价 mark-to-market 影响 → 置信度：中 | time_sensitivity：慢变

**第一节 time_sensitivity 统计**：静态 0 / 慢变 11 / 快变 9（其中"快变+高/中置信度"= fact-01/05/07/09/10/15 共 6 条 → 第五节强制对应 query；fact-12/18/19 为快变+低置信度，也纳入校准）

## 二、关键人物 / 公司 / 产品

- **Brian Armstrong** — 联合创始人兼 CEO，加密行业头面人物，长期主义、亲监管博弈立场
- **Emilie Choi** — President/COO，负责业务运营与并购
- **Alesia Haas** — CFO
- **Paul Grewal** — Chief Legal Officer，对外监管沟通/诉讼的核心发言人（活跃于公开表态）
- **Fred Ehrsam** — 联合创始人，Paradigm(加密风投)合伙人，董事
- **USDC / Circle** — Coinbase 稳定币收入的合作方与关键第三方依赖
- **Base** — Coinbase 自研以太坊 L2
- **Deribit** — 2025 拟收购的衍生品标的
- **Coinbase One** — 零售订阅产品(免佣金/权益)

## 三、产业链 / 竞争格局认知

1. **加密交易所层**：全球 Binance 量最大但受监管压制；美国合规市场 Coinbase 是龙头，享受"合规溢价"与机构信任；Kraken、Gemini、Robinhood(crypto)、以及传统券商/Fintech 入场者竞争零售份额。价格战与 take rate 压缩是长期风险。

2. **稳定币层**：USDC(Circle) vs USDT(Tether) 双寡头；Coinbase 通过与 Circle 的分成深度绑定 USDC 生态。GENIUS Act 后，银行/Fintech(如 PayPal PYUSD、Stripe/Bridge)可能加速入场，稳定币竞争格局重塑。

3. **机构基础设施层**：ETF 托管(Coinbase 为多数现货 BTC/ETH ETF 托管方)、Coinbase Prime(机构经纪/托管)、Coinbase International(离岸衍生品)。这是"卖铲子"逻辑——无论谁赢，机构加密资金流经 Coinbase。

4. **链上 / L2 层**：Base 承接 Coinbase 用户上链，长期是费用/排序器(sequencer)收入与生态变现的潜在期权，但当前变现规模小、竞争(Arbitrum/OP/其他 L2)激烈。

5. **监管层**：从 Gensler 时代的执法打压转向 Trump/Atkins 时代的立法确定性(GENIUS 成法、市场结构法推进、SEC 撤诉)。监管从"最大尾部风险"转为"潜在护城河"——但也降低了合规壁垒，可能引入更多传统金融竞争者(双刃剑)。

## 四、训练知识盲点（自我承认）

- **最新季度业绩**：Q4 2025 / Q1 2026 收入、交易量、订阅收入占比、净利润——训练时不掌握
- **当前币价与加密总市值**：BTC/ETH 现价、市场情绪(牛熊位置)——快变，训练记忆不可靠
- **Deribit 收购**：是否已交割、监管审批状态、并表影响
- **Circle IPO 后的 USDC 分成关系**：CRCL 上市后条款是否调整、USDC 流通市值、Coinbase 稳定币收入实际占比
- **当前股价与估值**：COIN 现价、市值、P/E、P/S、市场对 2026 盈利的一致预期
- **订阅与服务收入的最新拆分**：稳定币/staking/托管/Coinbase One 各自占比与增速
- **市场结构立法(CLARITY Act)最新进展**：是否成法、对 Coinbase 业务定性的影响
- **降息路径对稳定币收入的实际冲击**：2025-2026 美联储利率路径
- **新竞争威胁**：Robinhood/PayPal/Stripe(Bridge)/传统银行在稳定币与加密交易的最新动作
- **管理层资本配置史**：回购/并购/现金使用记录（未系统掌握）
- **一致预期与目标价**：卖方对 COIN 的评级分布、目标价区间

## 五、需要 web-search 校准的优先项

> 强制：第一节所有"快变 + 高/中置信度"fact 都有对应 query。

1. `Coinbase Q1 2026 earnings revenue transaction subscription breakdown`（校准 fact-01/02/03 最新季度实际）
2. `Coinbase stock price market cap valuation P/E 2026`（校准 fact-19 当前估值）
3. `Bitcoin price July 2026 crypto market cap total`（校准 fact-18 当前币价/周期位置）
4. `Coinbase subscription services revenue mix stablecoin USDC 2025 2026 percentage`（校准 fact-03/06 非交易收入占比——核心命门）
5. `Coinbase Circle USDC revenue sharing agreement after Circle IPO 2025`（校准 fact-06/07 分成关系）
6. `GENIUS Act stablecoin law implementation 2026 Coinbase impact`（校准 fact-09 立法落地影响）
7. `Coinbase SEC lawsuit dismissed 2025 CLARITY Act market structure bill status 2026`（校准 fact-10/12 监管确定性）
8. `Coinbase Deribit acquisition closed derivatives revenue 2026`（校准 fact-15 衍生品扩张兑现）
9. `Coinbase S&P 500 inclusion 2025 index passive flows`（校准 fact-05）
10. `Coinbase analyst rating price target consensus 2026`（校准盲点：一致预期/目标价锚）
11. `USDC market cap stablecoin market share 2026 Tether competition`（校准稳定币格局）
12. `Fed interest rate cuts 2025 2026 impact Coinbase stablecoin interest income`（校准 fact-08 降息冲击）

## 六、prescan 校准结果（2026-07-14 回写）

> Step 4.5a 12 条优先 query 全命中、入库 24 份（4 high + 20 mid）。以下对照第一节 fact-NN 的更新。
> **核心颠覆：我训练时的"加密牛市"先验完全错误——当前(2026-07)是加密熊市/寒冬，COIN 已从高位崩塌且转亏。thesis_v0 的"看多"必须重构为逆周期/周期底部押注，不能建立在过时的牛市假设上。**

### 被推翻（高优先级——thesis_v0 不要再引用原 fact，改 cite 新 mat）
- `[fact-18]` 训练"BTC $90K-$120K高位" → **推翻**：2026-07-06 BTC ≈ **$61,934**，较一年前 $109,231 **跌 43%**（fortune）；2026-03 底约 $66-68K（coinmarketcap）。**现在是熊市，不是牛市。**
- `[fact-19]` 训练"市值 $50B-$90B" → **推翻**：当前市值 **$41.46B**、EV $38.99B，股价 ~**$160**，过去 52 周 **-59.34%**；TTM PE 54.96 / forward PE 59.66 / EV-EBITDA 38.89 / beta 3.35 / 净现金 $2.47B（$9.39/股）（stockanalysis/tikr）。
- `[fact-01]` 训练 FY 收入序列 → **更新为季度轨迹**：Q1'24 $1.6B(牛市) → Q1'25 $2.0B(EPS $0.24,miss) → Q2'25 $1.5B(-26%QoQ,EPS $0.12) → **Q1'26 $1.4B(-31%YoY，营业利润率从 Q4'25 的 +12% 转负至 -7%，即已亏损)**，交易量 QoQ -20%+（theblock/tikr/coinotag）。**收入随周期剧烈收缩，当前处于亏损。**

### 被验证（可继续引用，置信度提升）
- `[fact-05]` S&P500 纳入 → **验证**：2025-05 确认纳入，纳入当日股价 +24%（spglobal/cnbc）→ 置信度 高
- `[fact-15]` Deribit 收购 → **验证+进展**：$2.9B，**已于 2025-08-14 交割并表**（"Deribit joins Coinbase"官方）→ 衍生品扩张已落地，置信度 高
- `[fact-09]` GENIUS Act → **验证**：2025-07 成法，当前进入实施细则阶段（OCC 发布 NPRM）→ 但见下"新增威胁"
- `[fact-06/07]` USDC/Circle 分成 → **验证+量化**：Q3'25 平台平均 USDC ~$15B，稳定币收入 Q2'25 $332M→Q3'25 $355M(+7%QoQ)，平台总资产 ATH ~$516B（Bill Hughes 引 Q3'25 股东信）

### 新增（baseline 未覆盖，thesis 必须纳入）
- **[新-A] 稳定币收益禁令是命门级威胁**：GENIUS/CLARITY 立法含"禁止对稳定币余额付收益/奖励"条款，直接威胁 Coinbase 的 USDC 激励(rewards)模式——而该模式正是驱动 USDC 余额→稳定币收入的引擎（whitehouse.gov/coindesk 2026-03）。**"收入多元化护城河"与"监管天花板"在稳定币这条线上正面对撞。**
- **[新-B] 市场结构法(CLARITY Act)仍未通过、在参议院拉锯**：Coinbase 2026-01-14 撤回支持(Armstrong 称"不能支持现有文本")，后于 2026-04-10 在财长 Bessent 呼吁 markup 后重新背书；三大未决点=稳定币收益语言/DeFi 条款/共和党全票。Digital Commodity Intermediaries Act(CFTC 管辖)于 2026-01-29 出委（galaxy/forbes）。→ fact-12 从"众议院推进"更新为"参议院激烈博弈，监管确定性尚未兑现"。
- **[新-C] 分析师与股价严重背离**：共识 Buy（约 30 位分析师，22 买/3 卖/9 持），2026 目标价 ~$292(public)–$316(tikr 中性情景) vs 现价 ~$160 → **隐含 ~80-97% 上行**。逆周期机会 or 价值陷阱是核心分歧。
- **[新-D] 稳定币市场在收缩**：USDT+USDC 合计市值降至 ~$257.9B(2026-01)，USDC 领跌；USDT ~$184B（coindesk/binance）→ 熊市中稳定币"抗周期"属性存疑。
- **催化剂**：下次财报 Q2 2026 = **2026-07-30**（盘后）。

### 仍未校准（thesis 引用时标 uncertain，留待 02/03 厚料）
- `[fact-04]` 零售 vs 机构 take rate 精确值、当前混合费率
- `[fact-08]` 降息路径对稳定币利息收入的定量冲击（2025-26 Fed 已在降息，但稳定币收入 YoY 仍增——需拆息差 vs 余额驱动）
- 订阅与服务收入四项(稳定币/staking/托管/One)最新占比与增速拆分
- 管理层资本配置史（回购/现金使用）

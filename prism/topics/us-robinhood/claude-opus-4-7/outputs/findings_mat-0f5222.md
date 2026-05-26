---
mat_id: mat-0f5222
filename: 2026_COIN_10-Q_2026-05-07.htm
source_type: quarterly-report
extracted: 2026-05-26
quality: high
bias: neutral
addresses: [K2, K4]
---

# COIN 10-Q Q1 2026 摘要

## 核心数据点与事实

### 收入结构（Q1 2026 vs Q1 2025，YoY）
- **Consumer transaction revenue**: -$591.6M（约 -54% YoY），明确口径"due to a 54% decrease in Consumer trading volume"
- **Institutional transaction revenue（现货）**: -$37.5M（约 -48% YoY），机构现货交易量同步下滑
- **Institutional derivatives revenue**: +$68.5M YoY，全部来自 Deribit（2025 年 8 月完成收购，期权清算 + 永续合约）
- **Stablecoin revenue**: $305M（+11% YoY），USDC 平均流通量增长 + 利息分成
- **Blockchain rewards (staking)**: $101M（-49% YoY），ETH/SOL 价格 + 链上 reward rate 同时下行
- **Subscription & services 合计**: $584M（-14% YoY）
- **订阅 & 服务收入占净收入比**: 44%（去年同期 35%）—— 结构性占比上升的原因是 transaction 端跌得更狠，而不是 sub 端绝对值增长

### 资产/币种集中度
- **BTC 占现货交易收入比**: 40%（去年同期 26%）—— altcoin 长尾交易量塌方，BTC 成为唯一活跃品种
- 未单独披露 ETH/SOL 占比变化，但 staking 收入 -49% 暗示 ETH/SOL 价格与质押需求双杀

### 业务节点
- **Deribit acquisition closed Aug 2025**: 当季首次完整体现机构衍生品贡献（+$68.5M）
- **Prediction markets trading launched**: 本季新业务线，10-Q 中作为"new product"披露，未单独披露收入金额（量级太小未拆分）

## 叙事主线

1. **交易侧 cycle 同步下行，订阅托住净收入**：Consumer -54% 与 Institutional 现货 -48% 是同一根曲线 —— Q1 2026 加密现货市场活跃度急剧回落（与 HOOD crypto notional 跌幅可直接对照）。COIN 把"收入韧性"故事押在订阅 & 服务（stablecoin + Coinbase One + custody）上，使其占比从 35% 跃升至 44%。
2. **从 retail broker 向 institutional infra 转型加速**：Deribit 收购在 Q1 首次贡献完整季度，机构衍生品 +$68.5M 部分对冲了现货 -$37.5M，机构口径净跌幅显著小于消费者口径。这与 HOOD 收购 Bitstamp 走的是相反方向 —— COIN 已经先一步占住机构衍生品。
3. **预测市场上线**：在 Kalshi/Polymarket/HOOD Event Contracts 之外开辟第四极，且 COIN 走的是"加密原生交易者横向扩品"路径，与 HOOD 的"零售券商 + event contracts 反向打加密"形成对称竞争。

## 反常识 / 分歧点

- **市场叙事 vs 实际数据**：外界普遍认为"COIN 已经 de-risk 到订阅"，但订阅绝对值 -14% YoY（$584M），所谓"订阅占比上升"本质是分母（transaction）跌得更快 —— 不是订阅业务本身在增长，stablecoin +11% 是唯一真正的有机增长来源。
- **BTC 集中度 40% 的含义**：现货收入越来越像"BTC 单品 take rate"游戏，意味着 COIN 的现货费率定价权在 altcoin 长尾上正在丢失（用户转向链上 DEX / Solana memecoin 平台），这与 take rate 反推 Bitstamp（K4）直接相关 —— 若 HOOD 接管 Bitstamp 现货也会面临同样的"BTC 集中化"压力。
- **机构现货 -48% vs 消费者 -54%**：通常认为机构是"smart money"先撤，但本季消费者跌幅更大，反向暗示散户在 Q1 大幅 deleverage（与 HOOD 同期 crypto notional 跌幅吻合度需要验证）。
- **Staking -49% 与现货 -54% 几乎同步**：意味着加密 cycle 已经从"价格 + 链上活动两条腿"双杀，不是单纯交易量回调；这对所有依赖 staking 分成的 retail broker（HOOD ETH staking）都是 K2 cycle 信号。

## 未回答问题

1. **Consumer take rate 是否同步压缩**：交易量 -54% 与收入 -54% 数字一致是"take rate 持平"还是巧合？需要拿 Consumer trading volume 美元值与 revenue 直接除算 take rate（10-Q 表格层应该有，但本次抽取未拿到 trading volume 绝对值）。
2. **Institutional take rate 真实水平**：Institutional 现货 take rate 通常远低于 Consumer（10x 以下），需要从 Institutional transaction volume 表反推，这是 K4 反推 Bitstamp 公允价值的核心输入。
3. **Deribit 单季 $68.5M 的隐含 take rate**：Deribit 期权 + 永续合约的 ADV 是多少？$68.5M / 季度对应的名义交易量决定了 HOOD-Bitstamp 衍生品估值上限。
4. **Prediction markets 收入量级**：本季未拆分披露，但作为"新产品"披露意味着 management 认为它会成为 line item —— Q2 是否会单独披露？
5. **Coinbase One 订阅用户数 / ARPU**：未在 10-Q 中拆分披露，无法对照 HOOD Gold 订阅。
6. **Stablecoin $305M 收入中 USDC 利息分成占比**：随着美联储降息周期，这部分对利率敏感，HOOD 现金 sweep 收入面临同样风险。

## 质量备注

- **来源**：Coinbase Global, Inc. Form 10-Q for Q1 2026, filed 2026-05-07，一手 SEC 申报文件，权威性最高。
- **抽取方式**：本次基于 HTML 文本提取（/tmp/coin_10q_text.txt），叙述类 MD&A 段落覆盖完整；**数字表格（Consumer trading volume USD 绝对值、Institutional ADV、Deribit notional volume）未在本次抽取中拿到具体数值**，后续若做 take rate 精确计算需要回到 HTM 原文或附表（建议用 mineru-vlm 重抽 trading volume tables）。
- **偏差**：管理层口径中性，10-Q 比 earnings call 更克制，未做未来 guidance。本次摘要忠实于披露口径，未做外推。
- **覆盖 claim**：K2（加密 cycle 同步性，COIN trading volume 与 HOOD 可直接对照）、K4（consumer/institutional take rate 结构 + Deribit 给 Bitstamp 估值锚），另对 HOOD 直接竞争点（Coinbase One / Deribit / 预测市场）提供对照素材。
- **未覆盖**：HOOD 自身数据需 cross-ref Robinhood Q1 2026 10-Q，本份只提供 COIN 端 mirror。

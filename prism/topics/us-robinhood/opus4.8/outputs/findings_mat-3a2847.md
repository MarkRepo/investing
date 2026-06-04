---
mat_id: mat-3a2847
filename: sec/2025_IBKR_10-K_2026-02-27/item_7a_quant_risk.md
source_type: sec-section
extracted: 2026-06-04
quality: high
bias: neutral
addresses: [K3, risk]
rings: [financial-arc]
---

## 核心数据点与事实
- **利率敏感性（K3 核心）**：基于 2025-12-31 余额，美元利率 +0.25% → NII 年化 +$77M；-0.25% → NII 年化 -$77M；非美元 +0.25%→+$30M，-0.25%→-$31M。即每 25bp 约 ±$77M（美元）／±$107M（含非美元）。
- 投资组合短久期：所有 U.S. government securities 到期均在 3 个月内（主动缩短久期以匹配资产负债期限，规避 MTM 风险）——与 HOOD 同样把客户现金投短端规避久期风险。
- 保证金贷款敞口：2025-12-31 客户保证金贷款 $90.5B；最低收费 0.75%（美元及多数外币）；风险"unlimited and not quantifiable"（取决于股价剧烈波动）。
- 货币多元化（GLOBAL 篮子，10 币种）：2025 年 GLOBAL 兑美元 +2.05%；约 25% 权益为非美元计价；总权益 $20,472M（GLOBAL 口径）——这是 HOOD 没有的汇率敞口/对冲维度。
- VaR（市场风险）：Trading（做市）VaR 仅 $10M，Non-Trading（投资+汇率）VaR $35M——做市残余风险极小，印证盈利质量纯净。
- 无变动利率债务。

## 叙事主线
因为 IBKR 每 25bp 利率变动仅影响 NII 约 $77M（相对 $3,563M NII 占比小，且靠短久期+余额增长缓冲）→ 所以其 NII 模式对利率冲击有韧性 → 对 HOOD 判断意味着：可用"每 25bp/NII"敏感度做同口径横比，评估 HOOD 在降息路径下 NII 受损弹性是否更脆弱（HOOD 缺 IBKR 的全球货币与保证金规模分散）。

## 反常识/分歧点
- IBKR 做市 VaR 仅 $10M——市场常以为 IBKR 有大量自营做市风险，实际残余做市敞口极小，盈利几乎全来自低风险经纪+利息。

## 质量备注
定量敏感度为 2025-12-31 时点快照，假设短端再投资。GLOBAL 汇率策略是 IBKR 独有项，横比 HOOD 时应剔除其汇率收益/损失噪音。

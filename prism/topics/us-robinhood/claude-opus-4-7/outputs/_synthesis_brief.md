---
slug: us-robinhood
output_key: _synthesis_brief
version: 1
generated: 2026-05-26
purpose: K1-K7 v0→v1 校准结论（供 06/07/08/thesis_v1 cross-mat 引用）
---

# HOOD K1-K7 v0→v1 校准

> 基于 22 份 findings（14 份 web-search + 8 份 SEC htm）的交叉验证结论。强度评分 0-10，正向为看多。

| K# | 主题 | v0 强度 | v1 强度 | 变化方向 | 关键 mat | 校准要点 |
|----|------|--------|--------|--------|---------|---------|
| K1 | PFOF 监管 | 6/10（短期利好） | 4/10（时间窗收窄） | ↓ partly_refuted | mat-706061 / mat-599824 / mat-6abade | 10-K 明确给出 **12 个月内三个落锤日期**：2026-05-01 SIPs odd-lot 公开 / 2026-08-01 Rule 605 执行质量披露 / 2026-11 tick size + access fee cap 合规。"Trump SEC 不执法"不等于"规则失效"——规则在册且日期已定，管理层明示"expect could lead to a decrease in PFOF" |
| K2 | 加密 cycle 下行 | 5/10（部分触发） | 4/10（确认下行但影响有限） | ↓ confirmed | mat-8ed60a / mat-0f5222 / mat-7475c0 | Q1'26 Crypto rev -47% / volumes -48% = take rate 持平；但 crypto 占总收入仅 12.5%；COIN Consumer -54% 同步验证全行业 cycle |
| K3 | Gold 订阅飞轮 | 8/10（远超预期） | 7/10（仍强但减速） | ↓ 小幅 supported | mat-8ed60a / mat-4c5f6e / mat-a6e176 | Gold subs 4.34M Q1'26 (+36% YoY) vs Q4'25 +58% — 增速从 +58% 降至 +36%；Gold 渗透率 15.5% 稳态；订阅收入 $50M/Q（年化 $200M）仅占总收入 4.7%，价值在交叉销售杠杆 |
| K4 | Bitstamp take rate | 6/10（institutional ×2 验证） | 3/10（take rate 假设证伪） | ↓ refuted | mat-7475c0 / mat-8ed60a / mat-0f5222 / mat-9730ab | 关键证据：Crypto volume -48% / Crypto revenue -47% → take rate 几乎持平，且 institutional 占比上升通常拉低 take rate；COIN Consumer take rate 139bps vs Institutional 4.9bps 量级差异巨大；Bitstamp 估值锚应从 "+50% take rate" 改为 "合规护城河 + 国际渠道" |
| K5 | 财富管理 AUM | 6/10（部分支持） | 7/10（兑现加速） | ↑ supported | mat-8ed60a / mat-706061 / mat-188ea6 | Total Platform $307B (+39% Q1'26 YoY)，Margin Book $17B (+93%)，TradePMR RIA $42.5B 已并表；Strategies/Banking/Cortex 三件套已发布；但 Strategies $100k+ 零费率，AUM 增长重点是交叉销售而非管理费 |
| K6 | 竞品反扑 | 5/10（待观察） | 3/10（已触发） | ↓↓ confirmed | **mat-32e412 (CRITICAL)** / mat-c70cf2 / mat-eb3ef4 / mat-687a1d | **SCHW Q1'26 10-Q 明确披露 2026-04 启动现货加密交易**（CSPB 自托管 + Paxos 子托管），分阶段 rollout BTC/ETH；IBKR 全栈 ForecastEx CFTC DCM/DCO 持续领先 HOOD Kalshi 合作模式；HOOD 差异化护城河（加密 + 预测市场）正在被同步攻破 |
| K7 | Event Contracts 可持续 | 6/10（爆发已发生） | 6/10（保持，待 2027 验证） | → unchanged | mat-8ed60a / mat-ad0673 / mat-24d0dd / mat-e9d55a | Q1'26 收入 $147M (+320% YoY) + 8.8B 合约 record；但单合约平均收入仅 ~$0.017，take rate 极低；管理层定性"fastest-growing by revenue"；MIAXdx 收购 + RHD 法律实体 + CFTC 全牌完成自建路径；K7 暴露真实风险在 2027 大选后能否维持 +50%+ YoY |

## 加权汇总：thesis v0→v1 强度变化

- **v0 强度**：7/10（中性偏看多）
- **v1 强度**：6/10（中性，仍偏多但收窄）
- **变化主因**：K1 时间窗收窄（-2）+ K4 take rate 假设证伪（-3）+ K6 SCHW 加密反扑触发（-2）；被 K5 兑现加速（+1）+ K3 仍强（+0）+ K7 保持（+0）部分对冲
- **核心 v1 结论**：**长期持有逻辑仍成立**（多元化第二曲线、Gold 飞轮、自营 RIA 平台、SP500 候选），但 **2026 H2 三大监管+竞争催化剂集中爆发**（PFOF 监管落锤 / SCHW 加密上线 / IBKR 国际化压制），当前 PE 35 / PS 14 已较饱满，**等回调到 $60-65（PE 30，IRR 15%+）再分批建仓**

## 估值锚定（cross-mat）

| 锚 | 数值 | mat |
|----|------|-----|
| HOOD 当前价 | $73.64（2026-05-22） | market_data |
| HOOD PE TTM | 35.75 | market_data + mat-1daa0f |
| HOOD PS TTM | 14.38 | market_data |
| HOOD Forward PE | 38.21 (隐含 EPS 略下修) | mat-1daa0f |
| HOOD 52w 区间 | $62.92 - $153.86 | market_data |
| HOOD 12M 卖方目标价 | $98.4（27 analysts，Buy 共识，+29% upside） | mat-abea64 |
| IBKR pretax margin（自动化券商边界） | 77% (FY25) | mat-eb3ef4 |
| IBKR PE | 22-27x（已纳入 SP500） | mat-eb3ef4 |
| IBKR/HOOD 客户质量比 | 单户 $166k vs $11k = 15× | mat-687a1d / mat-8ed60a |
| SCHW PE | ~22x | mat-c70cf2 |
| SCHW 客户资产 | $11.77T（HOOD = SCHW 2.6%） | mat-32e412 / mat-abea64 |
| COIN 加密 Consumer take rate | 139 bps（去年 153 bps） | mat-9730ab |
| Kalshi 估值 | $11B（2025-11 融资） | mat-e9d55a |

## 关键反共识结论（用于 06/07）

1. **K4 是 thesis 最脆弱假设**：Bitstamp 整合后 take rate 不升反平，"institutional 占比上升 = take rate 下降"是结构性而非周期；Bitstamp 价值锚应改为合规护城河
2. **K6 已从远端变近端**：SCHW 加密 4 月已上线，HOOD 加密差异化护城河收窄；ETF + 自托管模式可能比 HOOD PFOF 模式更被零售接受
3. **K1 时间窗收窄至 12 个月**：不是 2028 大选后的尾部风险，而是 2026-05/08/11 三连发的近端事件
4. **Funded Customers 增速骤降至 +6%**：所有增长靠 ARPU 和多元化变现，留存承压（Churn 翻倍）
5. **Net Income +3% << Revenue +15%**：Q1'26 OpEx 失控，2026 guidance 上调至 $2.7-2.825B（含 $100M Trump Accounts），盈利能力受压
6. **管理层 $81 高位回购 + April MTD $5B 净存款**：信号偏多，但需与 H2 监管事件交叉

## 信息来源

- 本 brief 综合 22 份 findings 的 cross-mat 校准结论
- 22 份 mat 完整列表见 manifest.yaml
- 估值数据来自 market_data 自动获取 + mat-1daa0f / mat-abea64
- IBKR / SCHW / COIN 对标来自 mat-eb3ef4 / mat-687a1d / mat-c70cf2 / mat-32e412 / mat-9730ab / mat-0f5222

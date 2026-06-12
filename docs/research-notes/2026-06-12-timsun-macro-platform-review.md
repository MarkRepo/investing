# timsun.net（US Macro 美国宏观研究平台）探站结论

> 日期：2026-06-12 · 探站对象：https://timsun.net （og:site_name "US Macro Research"，免费）
> 目的：评估其利率预期数据可否用作输入源、可补充哪些输入、平台设计有何可借鉴。
> 关联：prism 主题 `global-macro-rates-liquidity/opus4.8`；本仓 macro 取数通道（`prism/scripts/*_fetch.py`）。

平台定位（其 JSON-LD self-description）：**面向交易员与宏观研究者的美元流动性传导链监控**——
SOFR-IORB 利差、跨资产确认矩阵、VIX 期限结构、信用利差与每日宏观研究报告。数据源清一色免费
（Yahoo Finance / FRED / U.S. Treasury / Cboe / NY Fed / ICE BofA via FRED），与本仓"免费源优先 +
显式 fallback"哲学同源。和我们的 prism 宏观主题几乎是同物种。

---

## 1. CME FedWatch 隐含路径 / 利率预期，能用吗？

**结论：信号值得纳入，但不抓他的页面当源——用同一批 ZQ 期货自己复算。**

他的口径（页面明示）：
- 源 = **CME 30-Day Fed Funds Futures（ZQ 合约），经 Yahoo Finance 取数**
- 方法 = "CME FedWatch 标准方法**近似**"，结算价反推隐含利率，概率按 25bp 区间分布
- 更新 = 交易日收盘（UTC 22:00）；Yahoo 有 **10–15 分钟延迟**
- 页面示例（2026-05 截图）：目标区间 3.50–3.75%、有效利率 FEDFUNDS 3.63%、下次 FOMC 隐含降息概率 11.1%

不直接依赖他的三点理由：
1. 是**二手派生值**且自称"近似"——无 provenance 保证、方法可能漂移（同 memory `omo-7d-anchor` /
   网关成本虚高教训：别把别人算好的数当锚）。
2. 只有**收盘级**更新，拿不到盘中。
3. 依赖第三方站 = 脆弱（akshare 下线那类风险）。

**更优做法（= 本次实现 A）**：FedWatch 二项插值法是公开可复现算法。直接拉 ZQ 合约
（Yahoo `ZQ=F` 或逐月 `ZQM26/ZQN26/…/ZQZ26`），自算隐含路径 / 降息计价。契合本仓既有模式
（已自算 CIP basis、自抓 FRED）。增量价值：FRED `FEDFUNDS` 只给**已实现**有效利率，隐含路径给的是
**前瞻政策预期**——目前输入源缺的一类前瞻信号。落地通道见 `prism/scripts/fedwatch_fetch.py`。

---

## 2. 哪些数据可补充输入源

对照现有输入（FRED 自动抓取含 DXY、CIP basis EUR/JPY、7d OMO 锚、CFTC 持仓 z），**真正新增**的高价值项：

| 板块 | 可补充指标 | 为什么有用 / 免费源 |
|---|---|---|
| 流动性·暗流 | **SOFR-IORB 利差** | 回购市场压力最灵敏探针，主题目前没有；NY Fed 直发 |
| 流动性·暗流 | **SRF 常备回购便利用量、央行美元互换额度** | 美元荒早警；平时≈0、一动即事件；NY Fed |
| 流动性·暗流 | SOFR 尾部 / 成交量异常 | 准备金稀缺的微观裂缝 |
| 利率 | **国债拍卖 tail / bid-to-cover** | 久期需求强弱，期限溢价领先量；Treasury 拍卖结果 |
| 利率 | 实际利率 10Y TIPS / breakeven / 5y5y | FRED `DFII10` `T10YIE`；若未单列可补 |
| 波动率 | **VIX 期限结构倒挂（VIX vs VIX1D/VIX3M 前端）** | 他当 regime 信号（"前端倒挂→压力未消除"）；Cboe CSV |
| 美联储 | **鹰鸽光谱量化**（讲话/声明 diff 打分） | 把官员措辞转成可比标量 |
| 大类资产 | CFTC 持仓（已落地 ✓）、options/GEX 伽马敞口 | GEX 新；做市商对冲流方向 |
| 信用 | HY OAS（FRED `BAMLH0A0HYM2`）、CDS、信用压力面板 | 他用 OAS 做触发阈值 |

**最该先补的三个**：SOFR-IORB、SRF/央行互换额度、国债拍卖 tail——流动性/利率主题核心管道信号，
全部免费源，且现在缺。（本次范围只做 A=FedWatch；这三个留作后续候选，对应当初讨论的 B/C。）

---

## 3. 平台值得借鉴的设计

1. **"数据口径与可信度"面板** — 每指标内联展示 `数值 · 数据截至 · 来源 · 状态(正常)`。即本仓
   `00b_input_glossary` + "看真模型才知 provenance"教训的公开版。借鉴点：**把 source 归属 + 健康
   flag 直接挂在每个数旁边**，而非埋在文档里。

2. **证据 / 证伪 / 触发 三段式日度判断** — 先列证据（WTI、10Y），再列**证伪**（带具体阈值，如
   "5Y5Y 守住 2.1% 且 HY OAS 未降至 2.7 以下→此反弹仅事件驱动，不可追高"），再给 **24–72h
   触发/行动清单**。本质就是 thesis 的 **Killer Question（可证伪赌注）**，但下沉到**日度节奏** +
   **近端可证伪触发器**。我们 thesis 偏中期，借这个补一层短周期触发监控。

3. **跨资产确认矩阵** — 股/债/油/BTC/VIX 同向 → 判"流动性驱动 vs 基本面驱动"（"股债同涨=流动性
   驱动，60/40 对冲失效"）。紧凑 regime 分类器，可喂进 `m_regime_read`。

4. **传导链总分（标量化，如 "3.6 中性"）** — 把一堆管道指标压成单一压力分。regime read 可加这种
   composite scalar 做快读。

底层架构哲学一致：**免费源优先 + 显式 fallback 链**（如 VIX "Cboe CSV / FRED VIXCLS fallback"）——
"声明 fallback"本身值得抄进取数脚本。

---

## 附：观察到的数据源映射（其每日总览面板，2026-06-12 截图）

| 指标 | 源 |
|---|---|
| 标普500 / DXY / 比特币 / WTI | Yahoo Finance |
| 10Y 国债收益率 | U.S. Treasury Daily Treasury Yield Curve |
| VIX | Cboe VIX History CSV / FRED VIXCLS fallback |
| 高收益债 OAS | ICE BofA（FRED `BAMLH0A0HYM2`） |
| RRP 余额 | Fed H.4.1 |
| TGA 余额 | Treasury DTS / Fed balance sheet table |
| 净流动性 | Fed H.4.1 + Treasury/RRP（总资产 − RRP − TGA） |

站点板块全景：大类资产（股/ETF/期权·GEX/CFTC/债/商品/FX/加密/衍生品）、利率（联邦基金/收益率曲线/
国债拍卖/实际利率/利率预期）、美联储（FOMC/讲话/公告/鹰鸽追踪）、流动性（传导链/资产负债表/公开市场
操作/RRP·TGA/准备金/全球美元/暗流）、经济数据（GDP/就业/通胀/消费）、波动率（面板/VIX）、信用（概览/
CDS/压力面板）。

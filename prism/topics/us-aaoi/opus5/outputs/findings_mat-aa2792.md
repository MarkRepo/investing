---
mat_id: mat-aa2792
filename: 2026-08-26_applied-optoelectronics-future-growth.md
source_type: web-search
extracted: 2026-09-01
quality: medium
bias: bull
addresses: [K1, K3]
rings: [consensus, valuation-anchor]
conflicts_with: [findings_mat-7d8079.md]
conflict_note: 本页 analyst-estimates 表给 FY2027 收入 $2,574M / 净利 $381M（4 家）；mat-7d8079 由 ChartMill 季度路径相加得 $2,502.5M / EPS $4.18。两者收入接近，但本页直接给净利、**不需要股数假设**，因此是反推「街上模型隐含股数」的唯一干净口径。
warning: 同页「Narrative Update」板块为 Simply Wall St 社区叙事，其目标价 $27.20-$35.00 与本股 $113.76 现价及街上 $140-151 目标价严重不符（疑为陈旧或错口径）→ **该板块不可用，本 finding 只取 analyst estimates 表**。
---

## 核心数据点与事实

**analyst future estimates 表（原文，USD Millions）**

| Date | Revenue | Earnings | Free Cash Flow | Avg. No. Analysts |
|---|---|---|---|---|
| 12/31/2027 | **2,574** | **381** | **+168** | **4** |
| 12/31/2026 | **1,030** | **73** | −148 | 5 |
| 12/31/2025（实际） | 456 | −38 | −385 | — |

- [★ 推导，本份最重要的 K3 发现] **街上模型隐含股数 = 净利 $381M ÷ 一致 EPS**：÷$4.60（Yahoo，mat-1b5964）= **82.8M**；÷$4.87（Fintel/ChartMill 年表，mat-4d20e6）= **78.2M**；÷$4.18（mat-7d8079 季度和）= 91.1M。→ **街上模型用的股数约 78-83M**，介于券商 75.2M（mat-e575c5 反推）与公司 Q3'26 指引 92.8M 之间。
- [★ 推导] **街上隐含 FY2027 净利率 = $381M / $2,574M = 14.80%**——此为**不依赖股数假设**的干净口径。对照 `c_investment_case` 环④ 用 $4.18×92.8M÷$2.50B 算出的 15.52%：**两者接近（→ 分歧 1 的方向被独立佐证），但 case 的算法把股数分歧混进了净利率分歧**；按本口径 delta 应为 14.80% → 12%（自判）= **−2.8pp**，而非 case 写的 −3.5pp。
- [★ 反向证据，K3/风险 5] **街上预期 FY2027 自由现金流转正至 +$168M**（FY2026 仍 −$148M）。→ 若成立，则 `c_investment_case` 风险 5「融资通道关闭」与假设 3「ATM 必须继续」的前提在 2027 年消失；这也是 kill 条件 `share_count_held_below_95m` 的街上版本。**case 未记录这条街上口径。**
- [原文] FY2026 指引上调至 >$1.1B；**超大厂在手订单 >$324M**；与 Mediacom 的多年期 DOCSIS 4.0 协议。→ 与 case 引的「1.6T 首单 >$200M + 800G >$124M」合计 $324M+ **数值互证**（mat-0e6628）。
- [原文] 管理层计划资本开支「more than double」。

## 对投资的意味
街上的 FY2027 是「收入 $2.57-2.66B、净利 $381M（14.8% 净利率）、FCF 转正 +$168M、股数约 78-83M」这一组。case 的 Base（收入 $2.5B、净利率 12%、股数 96M）与之相比，**分歧集中在净利率 −2.8pp 与股数 +16-23%，而非收入**——这与 case 自述「分歧不在能不能卖出货」一致，但幅度需按本口径重算。

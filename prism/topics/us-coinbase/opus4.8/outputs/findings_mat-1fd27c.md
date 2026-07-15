---
mat_id: mat-1fd27c
filename: 2026-07-14_market-data-derivatives.md
source_type: web-search
extracted: 2026-07-14
quality: low-medium
bias: issuer-official（Coinbase market-data 页面，抓取片段字段错位）
addresses: [K1]
rings: [biz-moat-unit-econ]
---

# Finding: 衍生品市场数据 — Deribit vs Coinbase Derivatives 交易量对比

## A. 核心数据点与事实
- 快照 2026 口径给出三家/多口径交易量对照（原文字段拼接，单位/时间窗未明确标注，谨慎引用）：
  - **International Exchange: $2.66B；Deribit: $686.13M；Coinbase Derivatives: $254.5M**
  - **Deribit: $28.24B；Coinbase Derivatives: $707.37M**
  - **Deribit: $1.73B；Coinbase Derivatives: …**（片段截断）
- 关键相对关系：**Deribit 交易量量级显著大于 Coinbase 自有 Derivatives 平台**（如 $28.24B vs $707.37M，约 40x；$686.13M vs $254.5M，约 2.7x），印证 Deribit 是 Coinbase 衍生品版图的主力承载体。

## B. 叙事主线
在多个口径下 Deribit 的衍生品交易量都数量级领先 Coinbase 原生 Derivatives 平台，说明 $2.9B 收购买入的正是 Coinbase 此前缺失的规模化衍生品流动性入口（第二曲线核心资产）。

## C. 反常识/分歧点
- 抓取片段字段错位（日成交/未平仓/月量混排），无法确认各数字的时间窗与口径（daily volume vs open interest），量级对比方向可用，绝对值不可直接入模。

## D. 未回答问题
- 各数字是日量、月量还是未平仓（OI）？基准日？
- Coinbase 并表后合并衍生品交易量总规模与市占率未给出。

## E. 质量备注
- 来自 coinbase.com/market-data，抓取为动态页片段、字段拼接严重，quality 定 low-medium；仅取"Deribit >> Coinbase 自有衍生品"这一相对结论，绝对数字待结构化数据源复核。

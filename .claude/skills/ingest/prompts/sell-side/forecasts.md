# subagent: forecasts

**负责 section**：盈利预测 / 业绩预测 / 财务预测 / Forecasts / Earnings Model

**targets**：`claims`（**仅**）

---

## 你要产出的东西

**⚠️ 关键**：本 subagent **不产出 `financial_rows`**。研报预测是**作者对未来期的观点**，不是已披露的历史数字。预测数字必须以 claim 形式落地，而不是写入 financials 表。

### `claims`

研报预测表典型形式：

```
       | 2023A | 2024A | 2025E | 2026E | 2027E
营收   | 1000  | 1200  | 1450  | 1750  | 2100
净利   | 200   | 260   | 320   | 400   | 500
EPS    | 0.8   | 1.04  | 1.28  | 1.60  | 2.00
```

**抽取规则**：

1. **`A` 列（actual 已披露）不抽**。那些数字由年报/季报的 financials-tables subagent 已经录入，研报抽会重复。只抽 `E` / `F` / 预测列。
2. **每个(期, 指标) → 1 条 claim**。例：2025E 营收、2025E 净利、2025E EPS 各一条。
3. **timeframe**：严格对应预测期，`FY2025` / `FY2026` / `FY2027`。
4. **claim_type**：`quantitative`（预测都是数字型）。
5. **subject_tag**：
   - 营收预测 → `revenue_growth` 或 `guidance_reliability`（如果和公司指引差距大）
   - 利润 / EPS 预测 → `guidance_reliability` 为主
   - 毛利率 / 净利率预测 → `margin_trend`
   - 市占率 / ASP 预测 → `market_share` / `pricing_power`
6. **polarity**：
   - 预测值 > 上期实际且作者表达看多 → `bull`
   - 预测值 < 上期实际 → `bear`
   - 预测值平稳 / 单纯中性陈述 → `neutral`
7. **evidence**：直引预测表格里该数据点的完整行/列上下文（≤200 字）。光贴数字不够，要带指标名 + 期次。

**一条 claim 的完整模板**：

```json
{
  "claim_text": "[中信证券 2025-10-28] 预测茅台 FY2026 营收 1,930 亿元（YoY +14%）",
  "subject_tag": "revenue_growth",
  "polarity": "bull",
  "claim_type": "quantitative",
  "timeframe": "FY2026",
  "evidence": [{"text": "我们预计 2026 年公司营业收入 1,930 亿元，同比增长 14.2%，主要来自飞天茅台量价齐升", "type": "primary"}],
  "confidence": "medium"
}
```

## 抽多少条合适

典型盈利预测表覆盖 3 年 × 5 个指标 = 15 个预测单元格。**不要全抽**：

- **必抽**：每年的 revenue + net_income / EPS（3 年 × 2-3 指标 = 6-9 条）
- **选抽**（视作者重点）：毛利率、费用率、ROE、market share、ASP
- **不抽**：资产负债 / 现金流量表的预测项（除非作者特别强调）——那些层级太低

总量控制在 10-15 条；超过说明你在抽噪音。

## 和公司指引的对比（重要）

研报预测的价值在于**"和公司指引的差异"**。如果研报作者在本 section 里做了这种对比，对比本身是一条高价值 claim：

```
"[中信证券 2025-10-28] 研报预测 FY2026 净利润 420 亿，比公司指引区间上限（400 亿）高 5%，反映作者对提价节奏更乐观"
→ subject_tag: guidance_reliability
→ polarity: bull
→ confidence: high
```

**没有对比时不要硬造**。

## 特有注意事项

1. **单位务必保留原文** —— 中资研报常用"亿元"、外资研报常用"million"。claim_text 里保留原单位（"1,930 亿元" / "$13B"），别擅自换算。
2. **如果研报同时给出多情景预测**（"乐观 / 基准 / 悲观"），**只抽基准场景**。乐观 / 悲观场景作为 flags 里提一句。
3. **CAGR / YoY 等比率** 单独成 claim 还是合进数字 claim：
   - 如果作者明确给出 CAGR 数字 → 独立 claim（subject_tag=revenue_growth，claim_text="FY2024-FY2027 营收 CAGR 15%"）
   - 如果只是隐含 → 不抽
4. **不产出** `financial_rows` / `profile_fragments` / `meta_updates`。**即便**你觉得这些预测数字适合进 financials 表 —— **绝对不要**。研报数字和公司披露数字混在一个表会污染审计链。
5. **confidence 给"medium"为主**。研报预测本质是预测，即便作者给了详细调研也不配 `high`（那是对已披露数字的）。

## 反例

- ❌ 抽 `2024A` 列数据 —— 历史数字走年报通道
- ❌ 产出 `financial_rows: [{"period":"2025E","revenue":1450000000}]` —— 预测不进表
- ❌ 单位换算错：把"1,930 亿元"写成"193B 美元"
- ❌ 一整张表全抽（15+ 条）—— 必抽项之外要克制
- ❌ `polarity: "positive"` —— 必须 `bull`
- ❌ 对"同比 +14%"单独再抽一条 —— 已经在营收 claim 里了

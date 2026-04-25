# subagent: thesis

**负责 section**：投资要点 / 核心观点 / Investment Thesis / Key Points / 风险提示 / Key Risks

**targets**：`claims`（**仅**）

---

## 你要产出的东西

### `claims`

每条投资要点 / 风险点 → 1 条 atomic claim。保留研报作者立场的 polarity。

**抽取规则**：

1. **每个 bullet 点独立成 claim**。研报的投资要点通常列为"论点 1 / 论点 2 / ..."——**别合并**，一条一条来。
2. **claim_text 保留作者原话的核心数字和对比**。
   - 作者写："我们预计公司市占率从 2024 年的 12% 提升至 2027 年的 20%" → claim_text 完整保留这段
   - 作者写："看好公司的长期成长性" → **不抽**（空话）
3. **polarity 跟作者立场走**：
   - 投资要点里的看多论点 → `bull`
   - 风险提示里的担忧 → `bear`
   - 中性陈述（"行业增速 10%"这类市场事实）→ `neutral`
4. **timeframe**：
   - 研报作者明确说"FY2027" / "2025-2027"：`FY2027` / 多年取最后一年
   - 研报泛指长期观点："未来 3 年" / "中长期"：`long-term`
   - 无时间提示：`long-term`（研报观点默认是投资周期层面的）
5. **每条 claim 必须带 evidence**（直引研报原文 ≤200 字）。原文里的那条 bullet 本身就是最好的 evidence。

**抽几条合适**：
- 单独的"投资要点"section：一般 3-7 条 thesis claim + 1-3 条关键假设 claim
- 单独的"风险提示"section：2-5 条 bear claim；**别把模板化风险（"行业政策变化"）抽进来**
- 合起来不超过 15 条；研报信息密度低，与其多不如精

## subject_tag 使用指南（研报场景）

研报观点的 subject_tag 通常落在下面几类：

- `competitive_position` — 公司的护城河 / 差异化 / 行业地位陈述
- `market_share` — 市占率变化的具体预期
- `pricing_power` — 提价能力、ASP 趋势
- `revenue_growth` — 收入增长节奏的观点
- `margin_trend` — 毛利率 / 净利率走向
- `catalyst` — 即将发生的推动事件（新品发布、政策、并购）
- `regulatory_risk` — 监管或政策风险
- `concentration_risk` — 大客户 / 大供应商依赖
- `cyclical_risk` — 周期下行敞口
- `consensus_direction` — 作者自己对市场共识的判断（比市场更看多/看空）
- `guidance_reliability` — 作者对公司指引可信度的评价

**不在白名单的 tag 不要发明**。模糊时优先选"具体度更高"的，避开用 `revenue_growth` 兜底所有。

## claim_text 格式建议

开头加上 `[机构名 发布日期]` 前缀便于下游区分研报观点 vs 公司自述：

```
"[中信证券 2025-10-28] 预计茅台 FY2026 出厂价提升 5-8%，支撑营收双位数增长"
```

前缀不是必须，但加了便于以后做 "研报 vs 一手" 的分歧检索。

## 特有注意事项

1. **对"关键假设"section** 的抽取：研报关键假设常常是"我们假设 FY2026 茅台出厂价上涨 5%"——这是 claim 的精髓，一条假设一条 claim，`subject_tag=pricing_power` + `claim_type=quantitative`。
2. **对"风险提示"section**：多数机构的风险提示是**模板化**（"行业政策变化" / "宏观经济波动"）—— **不抽**。只抽作者定制过的、具体可证伪的风险。
3. **评级 / 目标价不在本 section 抽**。那是 valuation subagent 的职责。即便 thesis section 里顺带提了一句"维持买入评级"，不抽——让 valuation 统一出。
4. **不产出** `financial_rows` / `profile_fragments` / `meta_updates`。顶层返回空 `[]` / `{}`。

## polarity 和 confidence

- polarity：严格跟作者立场。作者说"行业下行"即便原文用中性措辞，也归 `bear`
- confidence：
  - `high`：作者给了具体数字 + 来源（"根据我们调研，40 家经销商提价幅度 5-8%"）
  - `medium`：作者给了数字但无明确来源（"预计提价 5%"）
  - `low`：纯观点无数字 —— **通常这类不该抽**

## 反例

- ❌ claim_text: "公司未来增长空间广阔" —— 空话
- ❌ claim_text: "行业景气度有望提升" —— 空话
- ❌ `polarity: positive` —— 必须是 `bull`
- ❌ 把"评级：买入，目标价 ¥2000"在 thesis 里又抽一次 —— 让 valuation 抽
- ❌ 把模板化风险（"行业政策变化"/"宏观波动"）抽成 bear claim —— 不可证伪

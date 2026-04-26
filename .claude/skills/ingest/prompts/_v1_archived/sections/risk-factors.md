# subagent: risk-factors

**负责 section**：风险因素 / Item 1A Risk Factors / Item 1C Cybersecurity / Item 3 Legal Proceedings / 第十节 风险因素 / 公司面临的风险

**targets**：`profile.§9` / `claims`

---

## 你要产出的东西

### 1. `profile_fragments.§9_risk_factors`

按年报**原文的风险条目标题**列出 **Top 5**。格式：

```markdown
1. **{原文标题}**：{一句话复述原文主旨，≤80 字}
2. **{原文标题}**：{...}
3. ...
```

**Top 5 的取法**：
- 10-K Risk Factors 往往有 20-50 条。选**公司业务核心的、可观察的、且原文用较大篇幅展开**的 Top 5。
- 先读所有标题，再从标题本身的具体度挑：
  - 选："Export controls restricting sales of advanced chips to China could materially impact revenue"
  - 不选（太泛）："We face risks related to global economic conditions"
- 标题直引，不改写。**不要**自己起一个更好的标题。

### 2. `claims`（每条风险衍生 0-2 条可证伪的 claim）

**只抽真正可证伪的**。风险因素段落大量是"可能/如果/不能保证"式的免责话，绝大多数**不可证伪 → 不抽**。

**可抽的三类**：

1. **具体的已披露依赖事实**：
   - "公司 80% 的芯片产能依赖于 TSMC" → 有数字、可证伪
2. **已发生的法律诉讼/监管措施**：
   - "公司于 2024 Q3 收到 FTC 关于 X 的问询" → 已发生、可查证
3. **具体披露的单一来源/集中度**：
   - "前五大客户贡献 60% 收入" → 可和财务附注对账

**不可抽的（大多数）**：
- "如果我们无法持续创新，我们的业务可能受到不利影响" —— 不可证伪
- "市场竞争加剧可能压缩我们的利润率" —— 不可证伪
- "网络安全事件可能导致数据泄露" —— 不可证伪（未发生、无可观察信号）

## subject_tag 使用指南

- `regulatory_risk` — 监管/合规/法律
- `concentration_risk` — 客户/供应商/地理集中度
- `cyclical_risk` — 周期敞口
- `competitive_position` — 具体竞争格局陈述
- `related_party` — 关联方风险
- `management_credibility` — 管理层信用问题（已发生的争议）

## 特有注意事项

1. **控制 claim 数量**：风险因素章节庞大，但真正有价值的 claim 通常 < 10 条。**少而精**。
2. **Item 3 Legal Proceedings**（如果是这份文档）：已立案的诉讼一定要抽，标 timeframe 为立案/进展的具体季度
3. **Item 1C Cybersecurity**（10-K 新增必选）：
   - 如果披露"本公司过去 12 个月发生 N 起重大安全事件" → 抽
   - 如果只是"我们有安全团队和流程" → 不抽（规则披露，非风险事实）
4. **原文含具体数字的 Risk Factor 要优先抽**：数字是"可证伪"的最强信号

## polarity 和 confidence

- risk-factors 的 claim 几乎全部 `polarity: bear`（描述的是负面风险）
- confidence：
  - `high`：原文明写数字（"占 60% 收入"）
  - `medium`：原文定性但具体（"主要依赖 TSMC"）
  - 不要 `low` —— 标 low 的"风险"多半就是你不该抽的空话

## 反例

- ❌ `§9_risk_factors` 给出 20 条每条都一样重要 —— 选 5 条，不要图多
- ❌ claim: "FDA 可能撤回某豁免" —— 未发生，不可证伪（监管层面的**已发生动作**才抽）
- ❌ claim: "我们面临产品责任诉讼风险" —— 空话
- ❌ `§9_risk_factors`: 自己归纳 5 个大类 —— 必须直引原文风险标题

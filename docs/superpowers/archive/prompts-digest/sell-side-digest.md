# sell-side-digest prompt（卖方公司研报 专用 digest subagent）

读 `_common.md` 的通用规则先；本文档只写卖方研报专属指令。

## 你面对的输入

卖方研报（10-30 页 / 单公司为主，偶尔含 1-2 家可比公司）。核心期望产出：

- **company.claims 候选**（大量：评级/目标价/财务预测/赛道判断）
- **company narratives**（5-8 维度浓缩，尤其 valuation / growth_engine / moat / catalysts）
- **少量 industry narrative**（研报前几页"行业简介"章节的事实，confidence=medium）
- **少量 arena narrative**（竞争格局/行业地位章节，confidence=medium，仅当 arena 已存在）
- **proposed_arenas 极少**（研报少主动开战场；除非研报主题就是"国产替代"等明确博弈 → 可提 1 个）

## 产出分层侧重

| target_layer | 典型占比 |
|---|---|
| company | 70-80% |
| industry | 10-20% |
| arena    | 5-15% |
| cross    | 0-5% |

## 不产 financial_rows

研报给的"预测"是前瞻（forecast），不是已发生财务；走 **company.claims** 通道，带 `time_type: "forecast"` 而非填 `financial_rows`。财务口径的真值来自年报/季报。

## valuation narrative 必填

研报核心产出：目标价、估值锚、WACC 假设、相对估值（PE / PB / EV/EBITDA 区间）。**必填 `narratives.company.{key}.valuation`**。

## subject_tag 集中

典型 subject_tag_hint：
- `target_price` / `rating` / `revenue_forecast` / `eps_forecast`
- `moat` / `catalyst` / `risk_highlight`
- `industry_outlook`（target_layer=industry 才用）

## 输出自查

- [ ] narratives.company.{key}.valuation 非空
- [ ] 若研报给了目标价 / 评级 → 必有至少 1 条 subject_tag_hint=target_price 的 company claim
- [ ] 研报里的行业数据标 confidence=medium（非一手）
- [ ] proposed_arenas ≤1（研报少开新战场）

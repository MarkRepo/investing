# annual-digest prompt（年报 / 10-K / 半年报 专用 digest subagent）

读 `_common.md` 的通用规则先；本文档只写年报专属指令。

## 你面对的输入

A 股年报（100+页）/ 10-K / 半年报。核心期望产出：

- 大量 **company.claims 候选**（key_facts[].target_layer=company，带 subject_tag_hint / company_dimension_hint）
- 8 份 **company.narratives**（按 COMPANY_DIMENSIONS 维度浓缩）
- **financial_rows**（从预处理 `financial_line_rows[]` 里主 agent 已做了初筛；你读这些 rows + 原文 context 做最终填表）
- **meta_updates**（website / listed_date / 行业补充 / 实控人变更）
- 若有"行业 / 市场"章节 → 少量 **industry 补充 narrative**（confidence=medium，作为"公司视角的行业段"）
- 若公司属于某 arena（prompt 里 company_context.arenas 非空）→ arena narrative 补充段

## 产出分层侧重

| target_layer | 典型占比 | 说明 |
|---|---|---|
| company | 70-85% | 主力 |
| industry | 10-20% | "行业竞争格局"/"市场概况"章节的客观事实（confidence 偏 medium） |
| arena    | 5-15% | 仅当公司参与的 arena 在 narratives 里有自然段落 |

## Financial rows 细则

- prompt 里有 `financial_line_rows: [{raw_label, standard_key, numeric_candidates, line}, ...]`（preprocess 抽的）
- 你的任务：对每个 fiscal period（通常是 2 期：本期 + 比较期），选出哪个 numeric_candidate 填哪个 `standard_key`
- 典型 A 股"单位: 万元" 陷阱：**硬转到基础单位（元）**；看到"万元"表头 → 所有数字 × 10000
- 输出到 JSON 里走 **单独字段** `financial_rows`（不是 key_facts）：

```json
{
  "financial_rows": [
    {
      "period": "2025A",
      "period_type": "annual",
      "revenue": 168838102500,
      "cost_of_revenue": 59831212100,
      "net_income_to_parent": 85219487300,
      ...
    }
  ]
}
```

- `period` 用 `{YYYY}A` (年报) / `{YYYY}Q{1-4}` (季报) / `HY{YYYY}H1` (半年报)
- 缺行就省略 key（不要填 null）；主 agent 会走 NULL 保护

## Company narratives 8 维度

逐维度写浓缩段：

| dim | 典型素材 |
|---|---|
| business_model | 业务线/收入结构/单位经济 → `§业务概要`/`MD&A` |
| moat | 差异化/成本/聚焦来源 → `§核心竞争力` |
| growth_engine | 量/价/新品/地理/M&A → `§主要业务` 和 `§未来展望` |
| management | 实控人/CEO/激励 → `§公司治理`/`§股东情况`/`§董监高` |
| financial_profile | 核心指标演进 / 利润结构 / 现金流质量 → `§财务报告` |
| catalysts | 短期触发点 / 在手订单 / 产能爬坡里程碑 → `§重要事项`/`§未来展望` |
| risks | 公司层面风险（业务/财务/治理/特殊）→ `§风险` |
| valuation | 年报鲜少给，管理层"可比公司 PE"偶尔有 → 通常留空 |

**空维度**：年报不覆盖某维度（如 valuation）→ `narratives.company.{key}` 里不要列该 dim key。

## Subject tag hint + company_dimension_hint

- `subject_tag_hint`：必须在 `subjects_whitelist` 里（主 agent 注入了）；违反整条被主 agent 降级
- `company_dimension_hint`：必须在 COMPANY_DIMENSIONS 闭集；violating 整条被 validate_batch 拒

一条典型 company key_fact：

```json
{
  "fact_text": "FY2025 营业收入 1,688 亿元，同比 +14.3%",
  "evidence_quote": "报告期内，公司实现营业收入 168,883,810.25 万元 ...",
  "target_layer": "company",
  "target_refs": {"ticker": "600519", "market": "SSE"},
  "dimension_hint": "financial_profile",
  "value_numeric": 1688.38,
  "unit": "cny_bn",
  "timeframe": "FY2025",
  "subject_tag_hint": "revenue_growth",
  "company_dimension_hint": "financial_profile",
  "confidence": "high"
}
```

## Industry / Arena 补充

- 公司的"行业地位"章节里谈到行业格局（"全球 CMP pad 市场 Dupont 市占 75%"）→ target_layer=industry，confidence=medium
- 公司在某 arena 里 → 该 arena 的 narrative 某维度可以自然 append（"我司在低端国产替代战场处于挑战者位置"）

## 输出自查（补充通用自查之外）

- [ ] 每个 financial_row 至少有 revenue + net_income 两列
- [ ] company narratives 覆盖至少 3 维（通常 5-7 维）
- [ ] 没有抽 company_dimension_hint=catalysts 的空泛项（"公司将继续发展"不是 catalyst）
- [ ] A 股"万元"换算已硬乘 10000（回头自查：营收在 100-10,000 亿量级才合理）

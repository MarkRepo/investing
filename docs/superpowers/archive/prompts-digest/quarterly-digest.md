# quarterly-digest prompt（季报 / 10-Q 专用 digest subagent）

> **⚠️ 迁移中（2026-04）**：**不要再产 `financial_rows`** 字段——财务数字统一由 `scripts/fetch_financials_{cn,us}` 从 akshare / yfinance API 入库。`financial_profile` narrative 来源改为 `§管理层讨论与分析` / `§Item_7_MDA`。以下文档中提到 `financial_rows` 的地方请**跳过**，输出 JSON 顶层 keys 不含 `financial_rows`。

读 `_common.md` + `annual-digest.md` 的通用规则先；本文档只写季报专属差异。

## 与年报的差异

季报比年报薄很多（10-30 页），核心期望产出：

- **financial_rows**（最主产物；季报主业）
- 少量 **company.claims** 候选（催化剂进展、重大合同、业绩前瞻）
- 极少 **narrative 更新**（一般只在 financial_profile / catalysts 两维追一段）

**不产出**：
- 完整 8 维 company narrative（季报素材不支持）
- meta_updates（季报罕见有 website/listed_date 变化）
- industry / arena narrative（季报不讲行业）

## financial_rows 特别

- `period_type: "quarterly"` / `period: "{YYYY}Q{N}"`
- A 股季报常有"本报告期"和"本年初至报告期末"两套数据；取 **本报告期** 那一列（即单 Q）
- 10-Q 有"three months ended"和"nine months ended"两套；取 three months ended 作为 Q2/Q3 单季

## narratives 段只写两维度

- `financial_profile`：本 Q 核心指标 vs QoQ / YoY；毛利率变动原因
- `catalysts`：本 Q 有无新催化（如新品发布、重大合同、产能落地）

其它 6 维度 narrative dict 不列 key（空）。

## 输出自查

- [ ] financial_rows 非空且至少 1 期
- [ ] narrative 仅限 financial_profile / catalysts 两维
- [ ] company.claims 候选集中在 subject_tag=revenue_growth / margin_trend / catalyst / guidance

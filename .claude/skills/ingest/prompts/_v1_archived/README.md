# v1 section-per-subagent prompts（归档，Plan 3 已废弃）

此目录是 ingest skill v1 架构的历史产物。

**v1 架构**（2026-04-26 Plan 3 之前）：主 agent 按 `section-routing.yaml` 对每份报告的每个 `action: extract` section 派 1 个 Explore subagent（并发 ≤ 5），每个 subagent 只看自己的 section 文本，返回 `{section, claims, profile_fragments, financial_rows, meta_updates, competence_findings, flags}`。

**v2 架构**（Plan 3 起）：每份报告只派 **1 个 digest subagent**（见 `prompts/digest/{source-type}-digest.md`），读整份报告 + figure_contexts + detected_tickers + known_arenas，返回 `{key_facts, narratives, proposed_arenas, financial_rows, competence_findings, flags}`，主 agent 用 `agg.route_key_facts` 分拣到 industry / arena / company 三层。

**本目录的文件**：
- `sections/` — 年报 / 季报的 section-level prompt：`business-overview.md` / `mdna.md` / `financials-tables.md` / `governance.md` / `risk-factors.md` / `contracts.md` / `related-party.md`
- `sell-side/` — 研报的 section-level prompt：`thesis.md` / `forecasts.md` / `valuation.md`
- `dispatch-merge-rules.md` — v1 同名 section 合并决策树（digest 架构下不存在此问题）

**保留归档的理由**：
1. v2 digest prompt 设计借鉴了部分 v1 经验（如 MD&A "不要把指引当事实"、risk-factors "逐条独立"）——归档让 debug / prompt 迭代能回看原始出处
2. 如果未来发现 digest 在某一领域表现不足，可参考 v1 的 section prompt 作为回滚参考

**不要** 在新 workflow 里引用本目录下的文件。section-routing.yaml 也不再消费 `subagent` 字段。

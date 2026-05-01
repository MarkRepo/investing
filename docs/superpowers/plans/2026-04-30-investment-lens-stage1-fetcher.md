---
name: Investment Lens — Stage 1 fetcher
description: Data access plan — FIELD_SOURCES mapping, bundle/claim/narrative aggregation, LensMaterial output
type: plan
status: done
---

## 目标

为 `/lens/{industry|arena|company}/{ref}` 端点的只读投资决策视图提供数据层，不涉及 HTML 渲染和用户交互。

## 数据模型

- **LensMaterial**: 顶层聚合结果，包含 `scope_type + scope_ref + field + bundle_excerpts + claims + narrative_excerpts`
- **BundleExcerpt**: 从 bundle JSON 按 path_spec 抽取的原文片段，带 `source_id / publish_date / path_in_bundle / text / confidence / bundle_sha8`
- **ClaimCard**: 从 ClaimRegistry 按 claim_type + dimension_hint 过滤的 active claims，带 `claim_id / claim_text / claim_type / confidence / evidence_count / as_of`
- **NarrativeExcerpt**: 从 archive narrative 文件读取的摘要，带 `scope_type / scope_ref / dimension / path / headline_count`

## FIELD_SOURCES 设计

24 组映射 `(scope_type, field) → {bundle_paths, claim_filter, archive_narrative_dim}`：

| Scope | Dims |
|-------|------|
| industry | thesis, demand, supply_competition, profit_pool, unit_economics, stage_gates, catalysts_timeline, risks_disconfirming_evidence (8) |
| arena | battlefield_definition, players_positions, winning_variables, evidence_scoreboard, stage_gates, inflection_points, company_implications (7) |
| company | business_exposure, thesis_fit, moat_execution, financial_quality, growth_drivers, stage_gate_status, valuation_expectations, catalysts_risks, open_questions (9) |

## Bundle path dispatch

`_dispatch_bundle_path()` 支持 6 种 spec 形式：
- `synthesis.X` — 直接取字段（str/list）
- `stage_gates[]` — 遍历 stage_gates 数组
- `insight_blocks[dimension_hint=X|Y]` — 按 dimension_hint 过滤 insight_blocks
- `atomic_facts[block_dim=X|Y]` — 先找 insight_blocks → block_id 映射，再过滤 atomic_facts
- `arena_candidates[slug=?]` — 按 tentative_slug 匹配
- `company_candidates[ticker=?]` / `company_candidates[]` — 按 key 或全量

## Claim 过滤逻辑

`_filter_claims()`: status=active 硬条件 + claim_type/dimension_hint 并集匹配（两过滤器都设时满足其一即可）。

## Archive narrative 读取

投射到已有 narrative md 文件，提供 `headline_count` 作为写作上下文参考。

## 对外接口

`fetch_lens_material(scope_type, scope_ref, field, registry, base) → LensMaterial`

## CLI 调试

`python -m scripts.lens_inspect <scope_type> <scope_ref>` 打印每字段 material counts。

## 已验证

35 个单元测试覆盖所有 24 字段、bundle path 6 种 dispatch、claim filter、空/缺失数据路径。

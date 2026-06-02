# prism — 设计概览

> 本文是高层概览。权威细节见 [`docs/architecture/prism-design.md`](./docs/architecture/prism-design.md)、
> [`docs/PLAN-PRISM-FUNNEL.md`](./docs/PLAN-PRISM-FUNNEL.md) 与 prism skill（`.claude/skills/prism/`）。

## 它解决什么

把一个投资研究主题（行业 / 竞技场 / 公司）从「起手论点」推进到「可决策的结构化产出」。
研究过程中的所有 LLM 推断由 Claude 在对话里完成，Python 脚本只做文件读写、校验与查询。

## 核心对象

- **topic** — 一个研究主题，存于 `prism/topics/{slug}/`，主状态文件 `topic.yaml`。
- **variant** — 同一 slug 下的研究变体（如换模型重研），用全 model-id 式命名，经 model_registry 归一。
- **materials / manifest** — 资料清单 `manifest.yaml`，原始资料放 `inbox/` 或 `materials/`（gitignore）。
- **outputs** — 决策链产出：`00_primer` 领域入门 + 按 type 的单份 case（company `c_investment_case` /
  industry `i_industry_case` / arena `a_arena_case`）+ sidecar（`07_decision_kit` / `09_industry_to_arenas` /
  `10_peer_matrix`）+ `thesis_v{N}` / `decomposition_v{N}`。

## 流程（workflow）

`prism/workflows/` 下的编号步骤：00 起题 → 01 路线图 → 02 资料 → 03 抽取 findings →
04 合成（primer-first + 6 环决策链，按 type 走 `_company_case` / `_industry_funnel` / `_arena_funnel`）→
05 critic 评审 → 06 监控 → 07 深挖。每步结束用脚本回写 `topic.yaml` 的 stage / next_actions / user_todos。

## 数据管道

- **抓取**：`scripts/fetch_report_prism.py` 路由多市场（HK/JP/KR/UK 等）下载，写入 `prism/inbox/auto/` 或主题 materials。
- **解析**：卖方/行业研报走 MinerU（`scripts/mineru_api.py` + clean/validate/rebuild 后处理）；
  年报/季报走 `scripts/annual_report_extractor.py`（pymupdf）。
- **行情/财务**：`prism/scripts/{market_data,financial_data}.py` 经 `app/io/{quotes,financials,adapters}`
  与 `scripts/fetch_{quotes_eod,financials_cn,financials_us}.py` 读写 `data/financials.db`（A 股行情主力源 Sina）。

## Web 看板

`app/routes/prism.py` + `app/templates/prism/`，挂在 `/prism`，只读消费 `topic.yaml` / outputs / sidecar / dashboard。
sidecar 是机器文件，字段严格按 workflow 模板。

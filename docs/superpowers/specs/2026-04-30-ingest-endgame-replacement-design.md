# Ingest Endgame Replacement Design

**Status**: design approved for implementation planning
**Date**: 2026-04-30
**Supersedes**: digest-era ingest path (`bd466a1` SKILL.md rewrite + 4 workflow files)
**Builds on**:
- `docs/superpowers/specs/2026-04-28-ingest-v2-research-os-design.md`
- `docs/superpowers/specs/2026-04-28-insight-block-ingest-design.md`
- `docs/superpowers/specs/2026-04-29-ingest-v2-phase1-review-bundle-design.md`
- `docs/superpowers/specs/2026-04-30-phase1-finalize-eval-bridge.md`
- `docs/superpowers/specs/2026-04-30-phase2-claim-layer-design.md`
- `docs/superpowers/specs/2026-04-30-phase3a-arena-investment-narrative-layer-design.md`

---

## 1. 目标

把四个 ingest workflow（`industry-research / annual-report / quarterly-report / sell-side-note`）从 digest 路径全面替换为 review-bundle / endgame 路径。删除 digest 专属的脚本、prompt、workflow md、per-company `claims.jsonl`、`observations.jsonl`，统一走：

```
preprocess → review-bundle → ingest_match → ingest_apply → ClaimRegistry
                                                                 ↓
                                               narrative_propose → user approve → narrative_apply
                                                                 ↓
                                                         narrative_flags
```

## 2. 非目标

- 不在本 spec 内实现 `investment_lens` 层（8/7/9 维投资视图）——另开 Phase
- 不迁移现存 18 家公司的 `companies/*/claims.jsonl`（接受旧数据丢失）
- 不重跑现存 3 个 industry + 5 个 arena + 18 家 company 的 archive（existing archive 保留，新 ingest 追加 narrative frontmatter）
- 不做全局 `/claims` 视图（跨 scope 浏览推迟到 investment_lens phase）
- 不自动生成最终买入/卖出决策
- 不让 Python 脚本直调 LLM API（LLM 判断发生在 Claude 对话或 Agent 子任务里）

## 3. 问题背景

本 spec 不是 Phase 3 的引入错误。时间线：

```
2026-04-26  bd466a1  SKILL.md 重写为"digest + 三层写入"架构  ← 分岔点
2026-04-29  3ee72dd  Phase 1 review-bundle design
2026-04-29  bce1ac0  Phase 1 review-bundle QA 落地
2026-04-30  11cc8a8  Phase 1 finalize + Phase 1.5 bridge
2026-04-30  f769972…9e532ec  Phase 2：ingest_match + ingest_apply + ClaimRegistry
2026-04-30  bd9132d…57b0241  Phase 3A/B/C：narrative_propose/apply/flags
```

SKILL.md 的 digest 架构落地早于 review-bundle。Phase 1/1.5/2/3 搭出的完整 endgame 链路**从未被 SKILL.md 引用**，四个 workflow 全部走 digest 路径。两条路径并存、互不相通，Phase 3 narrative 工具看不到 digest 产生的 per-company claims。

本 spec 拆掉 digest 路径，让四个 workflow 全部走 endgame 链路，单一路径。

## 4. 新管线端到端架构

```
source file
   ↓
[Step 1]  preprocess (scripts/preprocess_report.py, 不变)
   ↓  preprocess.json + figure_contexts + detected_tickers
[Step 2]  Review-bundle Dispatch (Agent subagent, Explore)
          输入：preprocess.json + 受控词表 + 已知 arenas/industries/companies
          输出：bundle.json (v2-phase1)
   ↓
[Step 3]  QA (scripts/ingest_qa.py review-bundle) — error 阻塞, warn 提示但继续
   ↓
[Step 4]  Arena candidates review (AskUserQuestion 批量 approve) → bootstrap_arena()
   ↓
[Step 5]  Industry autobuild (若 claim_candidates/arena_candidates 引用了未存 industry slug)
   ↓
[Step 6]  Company autobuild (bundle.company_candidates → ensure_company_exists, 沉默建骨架)
   ↓
[Step 7]  ingest_match (bundle.claim_candidates vs ClaimRegistry)
          输出两份 decisions：auto_apply.jsonl (confidence=high) + pending_review.jsonl (medium/low)
   ↓
[Step 8]  Match decisions review (pending_review 走 AskUserQuestion 批量过)
   ↓
[Step 9]  ingest_apply → ClaimRegistry，emit applied.jsonl
   ↓
[Step 10] narrative_propose 对每个 touched (scope, ref) 跑一次
   ↓
[Step 11] narrative proposals 批量 review (AskUserQuestion, multiSelect)
   ↓  approved proposals → narrative_apply
   ↓
[Step 12] figure_contexts 写入 (按源所在层：industries/{slug}/ 或 companies/{key}/)
   ↓
[Step 13] narrative_flags 对每个 touched (scope, ref) 跑一次
   ↓
[Step 14] bundle 持久化 + 写 bundle_registry
   ↓
[Step 15] 收尾报告
```

## 5. Review-bundle schema 扩展

在 `docs/prompts/ingest-review-bundle.md` 的 JSON 输出里，在 `company_candidates` 之后加一个 `arena_candidates[]` 块（与 company_candidates 对称）：

```jsonc
"arena_candidates": [
  {
    "candidate_id": "ac-001",
    "tentative_slug": "cn-fusion-hts-magnet-supply",
    "name": "中国高温超导磁体供应竞争",
    "parent_industry_slug": "cn-nuclear-fusion",
    "battleground_focus": "≤120字，说明这个 arena 在争什么",
    "participant_tickers": ["SSE_603011", "SSE_688122"],
    "linked_block_ids": ["ib-003", "ib-007"],
    "confidence": "high | medium | low",
    "verification_questions": ["进入 arena archive 前必须验证的问题"]
  }
]
```

### 5.1 新增硬约束

- `arena_candidates[*].linked_block_ids` 必须全部指向本 bundle 的 `insight_blocks[].id`
- `arena_candidates[*].participant_tickers` 必须全部出现在 `company_candidates[*].ticker`（MARKET_TICKER 格式）
- `arena_candidates[*].parent_industry_slug` 必填，非空
- `tentative_slug` 和 `name` 不允许包含具体公司名（arena 是战场，不是公司）
- `confidence=high` 要求至少 2 条 `linked_block_ids`

### 5.2 新增 QA 规则（`scripts/ingest_qa.py check_ingest_review_bundle`）

- `arena_candidate_missing_parent_industry`
- `arena_candidate_unknown_linked_block`
- `arena_candidate_participant_not_in_company_candidates`
- `arena_candidate_overconfident`
- `claim_refs_nonexistent_arena`（`claim_candidates[*].scope_type=arena` 且 `scope_ref` 是未存在 slug 时，要求该 slug 必须在 `arena_candidates[*].tentative_slug` 里出现）

### 5.3 Source-type 要求扩展

- `industry_report`：若原文提到 ≥2 家公司在某子赛道争夺，**应**产出至少 1 条 `arena_candidate`
- `company_report / sell_side_report`：`arena_candidates` 可以为空（除非原文明确对比了多家竞争者）
- `annual_report / quarterly_report`：`arena_candidates` 通常为空

## 6. 新 workflow 骨架

### 6.1 `_ingest-common.md`（新文件，四 workflow 共用骨架）

按 Section 4 的 15 步骨架铺开。四个 workflow 都 include 这份 common，只写自己的差异点。

### 6.2 四个 workflow 的差异点

| workflow | source_type | 原文落位 | 特殊处理 |
|---|---|---|---|
| `industry-research.md` | `industry_report` | `industries/{primary_slug}/sources/` | Step 5 前推 industry_slug（可能新建） |
| `annual-report.md` | `annual_report` | `companies/{key}/sources/` | Step 2 补 `period=FYxxxx`；`detected_tickers[0]` 是 primary company |
| `quarterly-report.md` | `quarterly_report` | `companies/{key}/sources/` | Step 2 补 `period=FYxxxxQx` |
| `sell-side-note.md` | `sell_side_report` | 见下 | Step 0 判 `focus_type=company \| industry`，落位分岔 |

### 6.3 sell-side-note.md 的 focus_type 分岔

- `focus_type=company`（研报单公司焦点）：
  - 原文落 `companies/{primary_key}/sources/`
  - Step 5 可跳过 industry slug 推导（仅当公司 meta 的 industry_slugs 已填时）
- `focus_type=industry`（研报行业面焦点）：
  - 原文落 `industries/{primary_slug}/sources/`
  - Step 5 走 industry slug 推导 / autobuild（同 industry-research）
- 判定：preprocess 的 `report_abstract` + `sections[0:3]` 的 text 前 2K 字，主 agent 推理：
  - 单公司名出现密度 > 行业术语密度 → company focus
  - 多公司对比 + 行业术语主导 → industry focus
  - 无法判定 → AskUserQuestion

### 6.4 SKILL.md 重写

删 digest dispatch / key_facts / route_key_facts / proposed_arenas 所有字样。新 routing：

```
source_type 判定 → 选 workflow →
  industry_report → workflows/industry-research.md
  annual_report → workflows/annual-report.md
  quarterly_report → workflows/quarterly-report.md
  sell_side_report → workflows/sell-side-note.md
每个 workflow 都 include workflows/_ingest-common.md 的 15 步骨架
```

## 7. ingest_aggregate.py 改动

### 7.1 删

`route_key_facts / derive_arena_facts / group_company_facts / facts_to_claims / propose_arena_bootstrap / load_json_tolerant / write_industry_observations / write_claims / write_industry_narrative / write_arena_narrative / write_company_narrative`

### 7.2 留

`ensure_industry_exists / ensure_company_exists / bootstrap_arena / write_figure_contexts`

### 7.3 新增

| 函数 | 做什么 |
|---|---|
| `write_figure_contexts_for_company(market_ticker, contexts, source_meta)` | 写 `companies/{key}/figure_contexts.jsonl` |
| `bootstrap_arena_from_candidate(arena_candidate)` | 把 `bundle.arena_candidates[*]` 的 shape 转到 `bootstrap_arena` 期望的 shape |

### 7.4 `scripts/ingest_match.py` 调整

- 决策输出 schema 加 `confidence: high | medium | low`（LLM 自己填）
- 输出拆两个文件：`<bundle>.auto_apply.jsonl` + `<bundle>.pending_review.jsonl`

### 7.5 `scripts/ingest_apply.py` 调整

- `--decisions <file>` 支持接收多个决策文件
- emit `applied.jsonl`，列本次写进 ClaimRegistry 的每条 claim 的 `(scope_type, scope_ref, claim_id)`

## 8. Narrative propose 内嵌（Step 10-11）

### 8.1 收集 touched (scope, ref)

读 `applied.jsonl` 去重得到：

```python
touched = {
    "industry": {"cn-nuclear-fusion", ...},
    "arena":    {"cn-fusion-hts-magnet-supply", ...},
    "company":  {"SSE_603011", ...},
}
```

### 8.2 跑 propose

对每个 `(scope, ref)`：

```bash
.venv/bin/python -m scripts.narrative_propose --scope {scope} --ref {ref} --out /tmp/np-{scope}-{ref}.jsonl
```

主 agent 把所有 jsonl 收拢成扁平列表：`[{scope, ref, dim, proposal_id, proposed_text, supported_by_claims, change_reason}, ...]`

### 8.3 批量 review（AskUserQuestion）

- 按 scope 分三大屏：industry → arena → company
- 多 ref 合并一屏（按 `(ref, dim)` 排）
- 单屏上限 25 条；超过按 scope 拆多屏
- 每条显示：`{scope}/{ref}/{dim}: {proposed_text 前 80 字}`
- multiSelect=true，**只**有 approve / skip 两种操作（不做 edit）

### 8.4 apply

```bash
.venv/bin/python -m scripts.narrative_apply --proposals /tmp/to_apply.jsonl
```

写到 `industries/{slug}/{dim}.md` / `arenas/{slug}/{dim}.md` / `companies/{key}/narratives/{dim}.md`，frontmatter 里写 `supported_by_claims / proposal_id / last_written`。

### 8.5 终止与回滚

- 全 reject → Step 11 结束，claims 已落盘但 archive *.md 不动
- 中途 apply 失败 → 报告成功/失败 dim，不自动回滚已写
- ingest_apply 成功但 narrative_apply 全失败 → claims 仍在 ClaimRegistry，下次 ingest 或手动 propose 可补

## 9. Web 影响

### 9.1 `/companies/{key}` claims 面板

读源从 `companies/{key}/claims.jsonl` 切到 `claims/companies.jsonl`（按 `scope_ref == "{market}_{ticker}"` filter）。schema 基本一致，新增 `direction_on_source / confidence` 两列。

### 9.2 观测面板删除

删两处：
- 公司财务页下方的"行业观测"小卡片
- 行业页 `/industries/{slug}` 顶部的"数值观测"表格

行业页其他面板（11 dim narrative / linked_arenas / linked_tickers / figure_contexts 预览 / narrative-flags 徽章）**全部保留**。

### 9.3 新路由 · Bundle / Source 浏览

**Bundle 存储**：`{source_dir}/bundles/{sha8}.json`（与 sources/ 对称）+ 全局 `data/bundle_registry.jsonl`（append-only）：

```jsonc
{
  "source_id": "行研-中银证券-2025-04-10-ad983472",
  "sha8": "ad983472",
  "source_type": "industry_report",
  "institution": "中银证券",
  "publish_date": "2025-04-10",
  "bundle_path": "industries/cn-nuclear-fusion/bundles/ad983472.json",
  "source_file_path": "industries/cn-nuclear-fusion/sources/xxx.pdf",
  "ingested_at": "2026-04-30T08:15:00Z",
  "touched": {
    "industries": ["cn-nuclear-fusion"],
    "arenas": ["cn-fusion-hts-magnet-supply", ...],
    "companies": ["SSE_603011", ...]
  }
}
```

**路由**：

| 路由 | 渲染 |
|---|---|
| `/bundles` | 全局列表，按 ingested_at 倒序；支持 type / institution / industry filter |
| `/bundles/{source_id}` | 单 bundle 详情：source_digest 卡 + insight_blocks（含 reasoning_chain）+ atomic_facts（按 block 分组）+ synthesis + stage_gates + claim_candidates（链到 ClaimRegistry 对应 claim）+ arena_candidates / company_candidates（标已 approve/reject）+ schema_fit_review。右上角"查看源文件"按钮。**所有字段默认展开** |
| `/sources/{source_id}/file` | 源文件渲染：PDF 用 `<embed>` inline viewer。右上角"查看 review bundle"按钮回到 `/bundles/{source_id}` |

**跨跳**：
- bundle → 源文件：按钮链 `/sources/{source_id}/file`，后端用 registry 查 `source_file_path`
- 源文件 → bundle：按钮链 `/bundles/{source_id}`
- claim → bundle：claim 列表每条的 `supporting_source_ids` 渲成小徽章链到对应 bundle

### 9.4 web 改动总清单

| 文件 | 改动 |
|---|---|
| `app/routes/companies.py` | 读源切换；删观测面板 |
| `app/routes/industries.py` | 删数值观测面板；add bundle 徽章链 |
| `app/routes/arenas.py` | add bundle 徽章链 |
| `app/templates/companies/*.html` | 删观测面板；claim 列表加 bundle 链 |
| `app/templates/industries/*.html` | 删数值观测面板；claim 列表加 bundle 链 |
| `app/templates/arenas/*.html` | claim 列表加 bundle 链 |
| `app/routes/bundles.py`（新） | `/bundles` + `/bundles/{source_id}` |
| `app/routes/sources.py`（新） | `/sources/{source_id}/file` |
| `app/templates/bundles/index.html`（新） | 列表模板 |
| `app/templates/bundles/detail.html`（新） | 详情模板 |
| `app/templates/sources/file.html`（新） | PDF/MD viewer 模板 |
| `app/io/claim_registry.py` | 加 `list_claims(scope_type, scope_ref)` helper（如无） |
| `app/io/bundle_registry.py`（新） | `append_registry(entry)` / `list_bundles(filters)` / `get_bundle(source_id)` |

## 10. 迁移清单

### 10.1 删

| 路径 | 说明 |
|---|---|
| `companies/*/claims.jsonl` | 18 家公司 per-company claims 全删 |
| `industries/*/observations.jsonl` | 3 个 industry 的 observations |
| `scripts/ingest_aggregate.py` 内 digest 专属函数 | Section 7.1 列表 |
| `tests/` 下针对已删函数的 case + digest mock fixture | Section 11.1 列表 |

### 10.2 归档（`git mv` 到 `docs/superpowers/archive/`，保留历史）

| 源路径 | 归档路径 |
|---|---|
| `.claude/skills/ingest/prompts/digest/*.md`（5 个） | `docs/superpowers/archive/prompts-digest/` |
| `.claude/skills/ingest/workflows/*.md`（旧版） | `docs/superpowers/archive/workflows-digest-era/` |
| `.claude/skills/ingest/SKILL.md`（旧版） | `docs/superpowers/archive/SKILL-digest-era.md` |

### 10.3 保留

- Phase 1/2/3 所有脚本
- ClaimRegistry 存储层
- `controlled-vocab/subjects.yaml`
- 所有 archive *.md（11/6/8 narrative）
- `industries/*/figure_contexts.jsonl`
- 所有 meta / narrative-flags jsonl
- `claims/arenas.jsonl`（本次 Phase 3A 测试时手塞的 5 条，是有效数据）
- `arenas/cn-fusion-*`（Phase 3A 测试写的，已是新格式）

### 10.4 新建

见 Section 6-9 散列的新文件；data/bundle_registry.jsonl 起步为空。

### 10.5 existing archive 的行为

- 11/6/8 dim *.md：保留。新 ingest 用 narrative_apply 追加 frontmatter
- **首次跑新流程后 narrative_flags 会把旧 dim（`supported_by_claims=[]`）全标 orphaned**，web 上全部打红点。这是预期，提醒用户旧 narrative 缺证据链，需重 ingest 才能补

### 10.6 git 策略

全合一批 merge。内部 commit 维持 TDD 风格（test → impl → commit）。

## 11. 测试策略

### 11.1 删

- `tests/test_ingest_aggregate*.py` 内针对已删函数的 case
- 所有 mock digest JSON 的 fixture（`test_digest_prompt_contracts.py` + 任何 `digest.json` mock）
- `tests/test_industry_research_workflow*.py` 内测 digest dispatch 的 case

### 11.2 保留

- `tests/test_preprocess*.py`
- `tests/test_ingest_review_bundle_qa.py`
- Phase 2：`test_claim_registry / test_ingest_match / test_ingest_apply`
- Phase 3：`test_narrative_propose_{arena,company,industry} / test_narrative_apply / test_narrative_flags`
- `tests/test_ingest_eval_cli.py`

### 11.3 改

- `test_ingest_review_bundle_qa.py`：加 `arena_candidates` 的 QA 规则 case（5 条新规则）
- `test_ingest_match.py`：decisions 加 `confidence` + 拆 `auto_apply.jsonl` + `pending_review.jsonl`
- `test_ingest_apply.py`：apply 后 emit `applied.jsonl`

### 11.4 新增

| 测试文件 | 覆盖 |
|---|---|
| `tests/test_bundle_registry.py` | `append_registry / list_bundles / get_bundle` |
| `tests/test_bundle_routes.py` | `/bundles` 列表 + `/bundles/{source_id}` 详情 + 404 |
| `tests/test_source_routes.py` | `/sources/{source_id}/file` |
| `tests/test_ingest_aggregate_new.py` | `write_figure_contexts_for_company` + `bootstrap_arena_from_candidate` |
| `tests/test_workflow_integration.py` | e2e：mock preprocess.json + mock bundle.json → 跑 15 步骨架 → 断言 ClaimRegistry / archive narrative / bundle registry 都落位 |
| `tests/test_web_claims_source_switch.py` | `/companies/{key}` claims 面板切到读 ClaimRegistry 后仍然正常渲染 |
| `tests/test_web_observations_panel_removed.py` | 观测面板 DOM 节点消失 |

### 11.5 端到端验收（用户手动跑）

新流程写完后，用户**手动**复用核聚变报告重跑整条管线（不进 plan 的 task）。验收清单：

1. preprocess → bundle → QA pass（0 error）
2. `arena_candidates` 里能看到 4 个聚变 arena
3. `ingest_match` 给每条 candidate 打 confidence；auto_apply 自动写，pending_review 走 AskUserQuestion
4. `ingest_apply` 后 `claims/{arenas,industries,companies}.jsonl` 条目数合理（industry ≥10 / 4 arena 各 ≥3 / 4 company 各 ≥1）
5. narrative_propose + 全 approve + apply → archive 11/6/8 dim 全部带 frontmatter
6. narrative_flags 对新 ingest 范围应 0 条（本次写的 frontmatter 都有 supported_by_claims）；范围外的旧 dim 仍为 orphaned
7. web：`/bundles` 列表有这份；详情页正常；源文件 inline viewer 正常；claim 的 source 徽章回跳 bundle
8. `/industries/cn-nuclear-fusion` 页面 11 dim 正常渲染，观测面板消失
9. `/companies/SSE_603011` 页面 claims 面板正常（读 ClaimRegistry），`companies/SSE_603011/claims.jsonl` 不存在

### 11.6 测试不覆盖

- LLM 抽取质量（依赖 `ingest_qa.py review-bundle` + 人工 review）
- PDF 渲染兼容性（只做"能加载"基础断言）
- 大 bundle 性能（不压测）

## 12. Rollout 实施顺序

### 12.1 Phase 结构

```
Phase A：底层脚手架
  A1  review-bundle prompt 扩展 arena_candidates + QA 规则
  A2  ingest_match confidence + 拆 auto/pending
  A3  ingest_apply emit applied.jsonl
  A4  ingest_aggregate 瘦身 + 新增两个函数
  A5  app/io/bundle_registry.py

Phase B：Workflow 改写
  B1  写 _ingest-common.md 骨架
  B2  重写 industry-research.md
  B3  重写 annual-report.md
  B4  重写 quarterly-report.md
  B5  重写 sell-side-note.md（完整支持 focus_type 分岔）
  B6  SKILL.md 重写
  B7  归档旧 digest prompts / workflows / SKILL.md

Phase C：Web 路由
  C1  app/io/claim_registry.list_claims helper
  C2  /companies/{key} claims 面板改读 ClaimRegistry
  C3  删观测面板
  C4  /bundles 路由 + 列表模板
  C5  /bundles/{source_id} 详情路由 + 模板
  C6  /sources/{source_id}/file 路由 + 模板
  C7  claim 面板加 bundle 徽章链

Phase D：旧数据清理
  D1  删 companies/*/claims.jsonl（18 家）
  D2  删 industries/*/observations.jsonl（3 个）

Phase E：文档
  E1  更新 USER-GUIDE.md
  E2  update-memory 记架构决定
```

**Phase D 之后核聚变重跑由用户手动完成，不进 plan。**

### 12.2 关键依赖

- A1 → Phase B
- A2, A3 → B1
- A5 → C4, C5
- Phase B 完成 → 用户可手动重跑
- Phase C → 重跑后能从 web 看到结果

### 12.3 commit 节奏

TDD 风格，每个小 task 一个 commit（test → impl）。参考 Phase 2 commit 模板（`test(claims): define...` → `feat(claims): add...`）。

### 12.4 规模预估

- Phase A: ~15 task
- Phase B: ~10 task
- Phase C: ~20 task
- Phase D: ~2 task
- Phase E: ~3 task

**合计 ~50 个 bite-sized task**，Sonnet 执行估 2-3 session 完成。

## 13. 未来工作（本 spec 外）

- **investment_lens 层**（industry 8 / arena 7 / company 9 维）：spec §10 of research-os-design 定义。
  **未实现**，需单独 Phase 规划。⚠ 区别于 Phase 3A/B/C——那是 archive 11/6/8 的 claim-proposal 写入管线，不是 decision-view projection。
- **全局 /claims 路由**（跨 scope 浏览 ClaimRegistry）：随 investment_lens phase 一起做
- **migration**（把旧 per-company claims 迁到 ClaimRegistry）：目前放弃，接受旧数据丢失。若将来改主意，单独写迁移脚本
- **bundle 的 knowledge_delta 层**（对比新旧 bundle 产出增量）：research-os-design §8 定义，未实现。需要跨报告比对时再做
- **Phase 3D**（memo 反向引用 + auto_review_flags）：用户已 memo 延期到 Phase 4 之后

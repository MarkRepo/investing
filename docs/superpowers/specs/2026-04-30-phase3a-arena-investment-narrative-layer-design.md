# Phase 3A Arena Investment Narrative Layer 设计

> **Errata 2026-05-01**：本文标题和部分正文沿用 endgame-design.md 误称 "投资视图叙事层"。
> Phase 3A/B/C 实际实现的是 archive 叙事层的 claim-proposal 写入管线，目标是 archive 11/6/8 的同一批 .md 文件
> (`app/config.py:30-62`)，而非 research-os §10 的 investment_lens (8/7/9 decision view)。文件名保留不变（避免破坏引用）。

**Status**: 设计草案，待用户 review 后再进入实施计划  
**Date**: 2026-04-30  
**Builds on**:
- [2026-04-29-ingest-endgame-design.md](./2026-04-29-ingest-endgame-design.md)（Phase 3 archive 叙事层）
- [2026-04-30-phase2-claim-layer-design.md](./2026-04-30-phase2-claim-layer-design.md)（Phase 2 claim registry）

---

## 1. 定位

Phase 3A 是 endgame Phase 3 的 arena 子集：先把 claim-proposal 管线落到 **arena archive 叙事层**（ARENA_DIMENSIONS 去掉 definition = 5 实际产出），不同时铺到 industry / company。

Phase 2 完成后，系统已经具备 claim registry、claim matching、pending apply 和 archive/arena 写入门。Phase 3A 在此基础上回答：

> 这个 arena 当前的连贯投资叙事是什么，它由哪些 active claim 支撑，哪些段落需要因为 claim 变化而复审？

Phase 3A 不重做 ingest、不替代 archive、不自动产出投资结论。它是 claim 驱动的阅读层和复审提醒层。

## 2. 目标

Phase 3A 完成后，系统应具备：

1. 从 Phase 2 arena claims 生成按 arena dimension 分组的 pending narrative proposals；
2. 用户/Claude 在对话中填写或编辑 narrative body，并给出 approve / edit / reject / defer 决策；
3. apply 脚本只把 approved/edit proposals 写入对应 arena narrative Markdown；
4. 每段正式叙事显式包含 `supported_by_claims[]`；
5. 当支撑 claim 被 retired、missing，或出现反向 evidence 时，系统可标记 review flags；
6. arena detail 页面显示叙事内容和 needs-review flags。

## 3. 非目标

Phase 3A 明确不做：

- 不做 industry / company 的 claim-proposal 管线（留给 Phase 3B/3C）；
- 不做 event adapter；
- 不做 review queue；
- 不做 cron / periodic scan；
- 不做自动 narrative rewrite；
- 不做 claim status 自动升级/降级；
- 不做 memo 反向引用 frontmatter；
- 不做 UI 中的 proposal 编辑/审批；
- 不做独立 narrative segment registry；
- 不做复杂段落 diff、去重重排或摘要重写；
- 不让 Python 调用 `anthropic`、`openai` 或任何 LLM API；
- 不动 V0 `companies/*/claims.jsonl`。

## 4. 总体架构

```text
active arena claims
  + source/evidence metadata
  + existing arena narrative files
  -> generate pending narrative proposals
  -> user/Claude fills approve/reject/edit/defer decisions
  -> apply approved proposals into arena narrative files
  -> manual claim lifecycle scan marks affected narrative as review-needed
```

Phase 3A 只处理 `app.config.ARENA_DIMENSIONS`：

- `definition`
- `participants`
- `decisive_factors`
- `trajectory`
- `narratives`
- `investment_view`

首期自动 proposal 只写入除 `definition` 外的 5 个 narrative Markdown 文件。`definition.md` 继续作为 arena 基础定义，不由 narrative proposal 覆盖。

## 5. 数据对象

### 5.1 Pending proposal 文件

路径：

```text
data/pending/narrative-proposals-<source_id>.json
```

结构：

```json
{
  "source_id": "2024-report-bci",
  "generated_at": "2026-04-30T12:00:00+00:00",
  "proposal_version": "phase3a-v1",
  "scope_type": "arena",
  "proposals": [
    {
      "proposal_id": "np-001",
      "arena_slug": "cn-bci-industrialization",
      "dimension": "participants",
      "title": "核心参与者从科研机构扩展到医疗器械与康复场景公司",
      "body": null,
      "supported_by_claims": ["clm-arena-0007", "clm-arena-0012"],
      "source_ids": ["2024-report-bci"],
      "evidence_summary": [
        {
          "claim_id": "clm-arena-0007",
          "claim_text": "侵入式脑机接口的商业化路径仍主要依赖医疗场景验证",
          "confidence": "medium_high",
          "as_of": "2024-12-31",
          "evidence_source_ids": ["2024-report-bci"]
        }
      ],
      "existing_narrative_excerpt": "可选：当前目标维度已有内容摘录，用于 Claude 对话避免重复。",
      "decision": null,
      "decision_reason": null,
      "edited_title": null,
      "edited_body": null
    }
  ],
  "unmapped_claims": [],
  "summary_stats": {
    "total_proposals": 1,
    "arena_count": 1,
    "dimension_count": 1,
    "unsupported_candidates_skipped": 0
  }
}
```

### 5.2 Decision 值

`decision` 只允许：

| decision | 行为 |
|---|---|
| `approve` | 使用 `title` / `body` 写入目标 arena narrative 文件 |
| `edit` | 使用 `edited_title` / `edited_body` 写入目标 arena narrative 文件 |
| `reject` | 不写入 narrative，记录 audit |
| `defer` | 暂不写入，记录 audit；pending 文件归档为 deferred 状态 |

规则：

- generator 产出的 `body` 默认为 `null`；叙事正文必须由用户主动在 Claude 对话里填写，或由用户确认后填入 `edited_body`；
- 所有 decision 都必须有非空 `decision_reason`；
- `approve` 必须有非空 `body`，且不能是占位文本；
- `edit` 必须有非空 `edited_body`，且不能是占位文本；`edited_title` 可选，缺省沿用 `title`；
- `approve` / `edit` 的 `supported_by_claims[]` 必须非空；
- `approve` / `edit` 引用的 claim 必须存在且当前 `status=active`；
- `dimension` 必须属于 `ARENA_DIMENSIONS` 且不能是 `definition`。

### 5.3 正式写入 Markdown 格式

写入目标：

```text
arenas/<slug>/<dimension-kebab>.md
```

例如：

```text
arenas/cn-bci-industrialization/participants.md
```

追加格式：

```markdown
### <title>

status: active
last_written: 2026-04-30
supported_by_claims: [clm-arena-0007, clm-arena-0012]
source_ids: [2024-report-bci]
proposal_id: np-001

<body>
```

首期不引入每段 frontmatter。一个 Markdown 文件里会有多个段落，用轻量 metadata block 与现有 `append_narrative_block()` 风格更一致。

### 5.4 Review flag 文件

路径：

```text
arenas/<slug>/narrative-flags.jsonl
```

每行一个 flag：

```json
{
  "flag_id": "nf-0001",
  "created_at": "2026-04-30T12:00:00+00:00",
  "dimension": "participants",
  "segment_ref": "participants.md#np-001",
  "supported_by_claim": "clm-arena-0007",
  "flag_level": "critical",
  "reason": "supporting claim retired",
  "dismissed": false,
  "superseded_by": null
}
```

首期只生成 flags，不做 dismiss CLI 或复杂 UI。重复运行 flag scan 不得产生重复 active flag；去重 key 为：

```text
(dimension, segment_ref, supported_by_claim, reason)
```

## 6. Dimension 映射

Phase 2 claim 的 `dimension_hint` 不一定等于 arena 的 6 个 narrative 维度。Phase 3A 使用小型硬编码映射：

```python
CLAIM_DIMENSION_TO_ARENA_NARRATIVE = {
    "participants": "participants",
    "competition": "participants",
    "competitive_position": "participants",

    "moat": "decisive_factors",
    "technology": "decisive_factors",
    "supply_chain": "decisive_factors",
    "winning_variables": "decisive_factors",

    "catalysts": "trajectory",
    "stage_gate": "trajectory",
    "regulation": "trajectory",

    "thesis": "narratives",
    "judgment": "narratives",
    "risk": "narratives",
    "scenario": "narratives",

    "valuation": "investment_view",
    "investment_view": "investment_view",
}
```

未命中的 `dimension_hint` 不硬塞进叙事层，进入 `unmapped_claims[]`。这避免把语义不清的 claim 写成误导性叙事。

## 7. 新增模块

新增：

```text
app/io/narrative_proposals.py
```

职责：

- 从 claim registry 读取 `scope_type=arena` 且 `status=active` 的 claims；
- 按 `arena_slug + dimension_hint` 聚合 claims；
- 映射 `dimension_hint` 到 arena narrative dimension；
- 生成 pending proposal skeleton；
- 校验 proposal decision；
- 将 approved/edit proposal append 到 arena narrative Markdown；
- 生成或追加 `narrative-flags.jsonl`；
- 提供读取 flags 的 helper，供 arena detail 页面展示。

它不负责：

- 写 LLM 生成正文；
- 判断 claim 是否真的支持叙事；
- 自动重写旧段落；
- 处理 industry/company narrative。

## 8. CLI

### 8.1 `scripts/narrative_propose.py`

示例：

```bash
.venv/bin/python scripts/narrative_propose.py \
  --registry-base data \
  --source-id 2024-report-bci \
  --arena cn-bci-industrialization \
  --out data/pending/narrative-proposals-2024-report-bci.json
```

行为：

1. 读取 `data/claims/arenas.jsonl`；
2. 过滤：
   - `scope_type == "arena"`；
   - `scope_ref == <arena>`；
   - `status == "active"`；
   - `supporting_evidence[].source_id` 包含 `--source-id`；
3. 按 mapped dimension 分组；
4. 为每个维度生成一个 proposal skeleton；
5. 写入 pending JSON。

首期默认只使用当前 `source_id` 支撑的 active claims，避免一次 proposal 重写历史所有 claim。

### 8.2 `scripts/narrative_apply.py`

示例：

```bash
.venv/bin/python scripts/narrative_apply.py \
  --proposals data/pending/narrative-proposals-2024-report-bci.json
```

行为：

1. 读取 pending proposal；
2. 校验所有 proposal 的 decision；
3. 对 `approve` / `edit` append 到 `arenas/<slug>/<dimension-kebab>.md`；
4. 对 `reject` / `defer` 不写 narrative，只写 audit；
5. 成功后把 pending 文件归档到：

```text
data/pending/archive/narrative-proposals-<source_id>.json
```

### 8.3 `scripts/narrative_flags.py`

示例：

```bash
.venv/bin/python scripts/narrative_flags.py \
  --registry-base data \
  --arena cn-bci-industrialization
```

行为：

1. 扫描该 arena narrative Markdown 里的 `supported_by_claims` metadata；
2. 对每个 claim 查询 registry 当前状态；
3. 若 claim 不存在、非 active、或 supporting evidence 出现 `refutes`，追加 flag；
4. 不修改正文，不自动改段落 status；
5. 重复运行不得产生重复 active flag。

Flag level：

| 条件 | flag_level | reason |
|---|---|---|
| claim missing | `critical` | `supporting claim missing` |
| claim retired / non-active | `critical` | `supporting claim retired` 或 `supporting claim not active` |
| claim 有 refutes evidence | `significant` | `supporting claim has refuting evidence` |

## 9. UI

修改：

```text
app/routes/arenas.py
app/templates/arenas/detail.html
```

Arena detail 页面读取并展示：

- 每个 narrative dimension 的 Markdown 内容；
- 该 arena 未 dismiss 的 `narrative-flags.jsonl`；
- 每个 flag 的：
  - dimension；
  - segment_ref；
  - supported_by_claim；
  - flag_level；
  - reason；
  - created_at。

页面行为：

- 如果某个维度有 flag，在该维度标题旁显示 `needs review`；
- 不做 dismiss 按钮；
- 不做 proposal 编辑/审批；
- pending proposal 的 approve/edit/reject/defer 仍通过 JSON + CLI 完成。

## 10. 测试范围

新增测试：

```text
tests/test_narrative_proposals.py
tests/test_narrative_apply_cli.py
tests/test_narrative_flags.py
tests/test_arenas_narrative_flags.py
```

覆盖：

### 10.1 Proposal 生成

- active arena claim 生成 grouped proposal；
- retired claim 不进入 proposal；
- company/industry claim 不进入 arena proposal；
- unmapped `dimension_hint` 进入 `unmapped_claims[]`，不生成正文 proposal；
- proposal 包含 `supported_by_claims[]` 和 evidence summary。

### 10.2 Proposal apply

- `approve` 写入正确 `arenas/<slug>/<dimension>.md`；
- `edit` 使用 edited title/body；
- `reject` / `defer` 不写 narrative，但写 audit；
- missing body / missing decision_reason / empty supported_by_claims 导致非零退出；
- supported claim 已 retired 导致非零退出；
- `dimension=definition` 导致非零退出。

### 10.3 Flag 生成

- narrative 引用 active claim 不生成 flag；
- referenced claim retired 生成 critical flag；
- referenced claim missing 生成 critical flag；
- claim 有 `direction=refutes` evidence 生成 significant flag；
- 重复运行不重复写同一个 active flag。

### 10.4 UI helper

- arena detail route 能读取 flags；
- template 能按 dimension 显示 needs review；
- 没有 flags 时页面正常渲染。

## 11. 成功判据

Phase 3A 完成后必须满足：

- 能从真实 `data/claims/arenas.jsonl` 为某个 arena 生成 `narrative-proposals-<source_id>.json`；
- Claude/用户可在 pending JSON 中填入 `body` 和 `decision`；
- apply 后内容只追加到对应 arena narrative Markdown，不改 `definition.md`；
- 每个正式写入段落都显式包含 `supported_by_claims[]`；
- 如果支撑 claim 被 retired 或出现反向 evidence，手动运行 flags 命令能产生 review flag；
- Arena detail 页面能看到 narrative 内容和 needs-review flags；
- Python 不调用任何 LLM API；
- 不动 industry/company narrative；
- 不动 V0 `companies/*/claims.jsonl`；
- 新增测试全部通过。

## 12. 反延展护栏

| 念头 | 实际应做 |
|---|---|
| “既然是 archive 叙事，顺便做 industry/company” | 不做；Phase 3A 只做 arena |
| “直接让脚本调用 Claude 写 body” | 不做；body 由用户主动在 Claude 对话里生成/编辑 |
| “claim refutes 了就自动改段落文字” | 不改；只生成 flag |
| “做一个完整 review queue” | 不做；Phase 4 范围 |
| “加 cron 定期扫描” | 不做；只提供手动命令 |
| “把 proposal 审批做进 UI” | 不做；首期继续 JSON + CLI |
| “建 narrative segment registry” | 不做；首期 Markdown 为正式阅读面，pending JSON 为工作流对象 |
| “修改 memo frontmatter” | 不做；memo 反向引用是后续 Phase 3B/3C |
| “处理 definition.md 自动更新” | 不做；definition 只由 arena 创建/手工维护 |

## 13. 与后续 Phase 的关系

Phase 3A 建成后，后续可自然扩展：

1. Phase 3B：company archive narrative claim 管线（COMPANY_DIMENSIONS 8 维）+ memo shallow references；
2. Phase 3C：industry archive narrative claim 管线（INDUSTRY_DIMENSIONS 11 维，减 definition = 10 产出）；
3. Phase 4：event adapters + review queue + periodic scan；
4. Phase 5+：UI 审批、flag dismiss、narrative registry 或更强内容治理。

Phase 3A 不预先实现这些能力，只保留足够 metadata：`proposal_id`、`supported_by_claims[]`、`source_ids[]`、`narrative-flags.jsonl`。

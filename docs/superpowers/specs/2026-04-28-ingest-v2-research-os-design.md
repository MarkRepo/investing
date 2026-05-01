# 研报 ingest v2 总方案（research OS）

**Status**: 设计草案，待用户 review 后再进入实施计划  
**Date**: 2026-04-28  
**Extends**: `docs/superpowers/specs/2026-04-28-insight-block-ingest-design.md`

---

## 1. 目标

现有 `2026-04-28-insight-block-ingest-design.md` 已经定义了单份研报的核心抽取中间层：`source_roles`、`insight_blocks`、`atomic_facts`、`theme_basket`、`scenario_map`、`stage_gate`、`company_candidates`、`synthesis`。

这份 v2 总方案不推翻它，而是补齐它尚未覆盖的五个问题：

1. 多次 ingest 同一行业或同一主题时，知识如何合并；
2. 旧 `11/6/8` archive schema 与更适合投资分析的阅读视图如何共存；
3. ingest 如何产出“当前 schema 是否适配”的评价与改进建议；
4. 预处理、后处理、QA、Web 需要如何联动；
5. 研报中的图片、图表、产业链图、技术路线图如何作为一等对象处理。

核心结论：

> insight-block 方案继续作为 **Extract 层**；ingest v2 增加 **Preprocess / Compare / Merge / Investment View / Schema Evolution / Web Review Workflow**，把单次抽取升级为可持续演化的研究操作系统。

## 2. 非目标

- 不在本设计中重写现有 `industry 11 / arena 6 / company 8` 全部 archive 文件。
- 不自动生成最终买入/卖出决策。
- 不允许 ingest 自动改 schema；所有 schema 变更必须用户确认。
- 不把 vision 抽取结果无审核地提升为强事实。
- 不在本设计中实现具体脚本；实现留给后续实施计划。

## 3. 总体架构

```text
source document
  -> preprocess
  -> extract (reuse insight-block design)
  -> validate / QA
  -> compare against existing knowledge base
  -> knowledge_delta
  -> user review
  -> approved merge into archive
  -> generate investment views
  -> schema feedback queue
```

系统分为七层：

1. `Preprocess`：把 PDF / OCR / 图片 / 表格 / 页面角色整理成可抽取输入。
2. `Extract`：复用现有 insight-block 设计产出 digest。
3. `Validate`：检查 block、fact、stage gate、candidate、visual artifact 的一致性。
4. `Compare`：与现有知识库比较，生成增量变化。
5. `Merge`：只合并用户确认过的 delta。
6. `Views`：保留旧 archive view，同时生成 investment view。
7. `Schema evolution`：输出 schema 适配度与改进建议，进入待确认队列。

## 4. Preprocess 预处理层

现有方案默认 source document 已可直接抽取，但从实际样本看，研报里大量关键信息存在于图表、产业链图、技术路线图和扫描页中。预处理必须显式输出结构化元数据。

### 4.1 预处理输出

```yaml
preprocess_output:
  source_file: /path/to/report.pdf
  page_count: 42
  extracted_pages:
    - page: 1
      page_role: cover
      text_quality: high
      image_heavy: true
      table_heavy: false
      chart_heavy: false
    - page: 10
      page_role: body
      text_quality: medium
      image_heavy: true
      chart_heavy: true
  tables:
    - table_id: tbl-001
      page: 9
      extraction_method: text_layer
      confidence: medium_high
  visual_artifacts:
    - artifact_id: va-001
      page: 10
      type: value_chain_diagram
      extraction_method: text_layer
      text_extract_quality: medium
      structure_extract_quality: low
      needs_review: true
  extraction_warnings:
    - "第 10 页为产业链图，结构关系需视觉复核"
    - "第 18 页表格跨页，可能存在漏列"
```

### 4.2 页面角色

建议受控词表：

- `cover`
- `toc`
- `executive_summary`
- `body`
- `appendix`
- `risk_disclosure`
- `valuation_table`
- `company_table`
- `unknown`

页面角色不是展示用途，而是为了后续 prompt 和 QA：

- `cover` / `toc` 可用于 source metadata；
- `executive_summary` 优先用于 `report_thesis`；
- `valuation_table` 不能直接覆盖 company valuation narrative；
- `company_table` 必须降级到 `company_candidates`。

## 5. Visual artifacts 图片与图表策略

样本验证显示：纯 PDF 文本层足以恢复很多标题、标签和部分表格，但不能稳定恢复产业链图、技术分类树、多曲线趋势图、热力表和 logo 与分类框关系。视觉内容必须成为一等对象。

### 5.1 `visual_artifacts`

```yaml
visual_artifacts:
  - id: va-bci-010
    page: 10
    type: value_chain_diagram
    title: "脑机接口产业链"
    extraction_method: text_layer | vision | manual
    text_extract_quality: medium
    structure_extract_quality: low
    extracted_summary: "产业链分为上游核心器件、中游系统集成、下游应用。"
    linked_blocks:
      - ib-value-chain-001
    extracted_facts: []
    needs_review: true
```

### 5.2 图片处理三档

**第一档：文本可恢复图表**

- 图标题、图注、普通表格、可复制标签；
- 允许直接进入 `atomic_facts`，但置信度不高于文本本身。

**第二档：需要视觉结构识别的图表**

- 产业链图、分类树、技术路线图、timeline、stage gate 路线图、热力表；
- 先生成 `visual_artifact`，只有结构置信度足够才进入 `insight_block` 的强结构化内容。

**第三档：无法可靠恢复的视觉内容**

- 低清扫描、复杂多轴图、logo 矩阵、颜色编码强依赖图；
- 保留 artifact 和 `needs_review`，不自动生成强事实。

### 5.3 图片 QA 约束

- `structure_extract_quality = low` 的 artifact 不能直接生成强事实；
- 如果一个 `synthesis` 依赖视觉证据，必须记录其 artifact 来源；
- 如果图片中出现公司 logo/公司名与分类框映射，默认 `needs_review = true`；
- 正文未重复说明的图中关键数值，默认置信度不高于 `medium`。

## 6. Extract 抽取层

本层直接复用 `2026-04-28-insight-block-ingest-design.md`。

每次 ingest 至少产出：

- `source_digest`
- `insight_blocks[]`
- `atomic_facts[]`
- `theme_basket`
- `scenario_map`
- `stage_gates[]`
- `company_candidates[]`
- `synthesis`
- `schema_fit_review`

v2 对 Extract 层只新增两个要求：

1. Extract 必须引用 `preprocess_output`，尤其是 page role 和 visual artifacts；
2. Extract 必须显式输出 schema 适配评价，而不是只输出内容。

## 7. Validate / QA 层

在本地写入知识库前，必须做机器校验。

### 7.1 基础校验

- 每个 `atomic_fact` 必须有 `linked_block_id`；
- 每个 `insight_block` 必须有 `block_type`、`summary`、`source_page_range`；
- 每个 `company_candidate` 必须有 `exposure_type` 和 `verification_questions`；
- 主题篮子来源的公司候选必须有 `theme_refs`；
- `stage_gate` 未跨过时，`synthesis.cannot_conclude` 不能为空。

### 7.2 医药/医疗器械/硬科技加严校验

- 有 `pipeline` 时，必须带 `clinical_phase` 或 `approval_status`；
- 有 `regulatory_pathway` 时，必须有对应的 gate 或 verification question；
- 供应商类公司必须追问收入占比和客户性质；
- 科研/示范项目订单不得直接写成长期商业化收入。

### 7.3 视觉校验

- 每个 `chart_heavy` 或 `image_heavy` 页面，若被抽为关键 block，应存在 `visual_artifact`；
- `visual_artifact.needs_review = true` 的内容不得直接生成高置信 company mapping；
- 如果图表结论被写进 `what_we_know`，必须有足够 `evidence_strength`。

## 8. Compare / Delta 层

当前 insight-block 设计以单份报告为中心，但 ingest v2 必须支持多次 ingest 同一行业、同一 arena、同一公司。

原则：

> 新的 ingest run 先生成独立 digest，再与现有知识库比较，输出 `knowledge_delta`；不直接覆盖 archive。

### 8.1 `knowledge_delta`

```yaml
knowledge_delta:
  new_facts: []
  duplicate_facts: []
  updated_facts: []
  conflicting_facts: []
  strengthened_claims: []
  weakened_claims: []
  new_stage_gates: []
  stage_gate_updates: []
  new_company_candidates: []
  exposure_updates: []
  user_review_required: []
```

### 8.2 delta 分类规则

- `new_facts`：知识库中不存在的新事实；
- `duplicate_facts`：事实已存在，但可作为交叉验证来源；
- `updated_facts`：同类事实因时间维度或数值刷新发生变化；
- `conflicting_facts`：新旧资料对同一命题给出相互冲突的信息；
- `strengthened_claims`：新报告用独立证据支持已有 claim；
- `weakened_claims`：新报告提出反证、削弱已有判断；
- `stage_gate_updates`：门槛状态推进或退化；
- `exposure_updates`：公司暴露类型从 `thematic_related` 升级或降级。

### 8.3 用户应看到的增量变化

Web 和 CLI 都应直接显示：

- 本次新增了什么；
- 强化了什么；
- 削弱或冲突了什么；
- 哪些变化会改写 `synthesis`；
- 哪些变化需要用户确认后才 merge。

## 9. Merge 层

### 9.1 merge 原则

- 只有用户确认过的 delta 才能写入 archive；
- 未解决冲突必须保留 pending，不得强行覆盖；
- 被削弱的 claim 不必删除，但应下调信心和阅读位置；
- `duplicate_facts` 不应重复写 narrative，只增加 provenance。

### 9.2 merge 输出

```yaml
merge_result:
  applied_deltas: []
  pending_conflicts: []
  updated_archive_refs: []
  regenerated_views:
    - industry: medical-biotech
    - arena: cn-bci-industrialization
    - company: innovent-biologics
```

## 10. Archive view 与 Investment view

现有设计里已经明确：`11/6/8` 继续作为 archive schema。这一点不改。

但旧 `11/6/8` 偏归档，不够贴近投资分析阅读。因此 ingest v2 新增 `investment_lens` 投影。

### 10.1 关系

```text
insight_blocks / facts
  -> archive routing: industry 11 / arena 6 / company 8
  -> investment_lens routing:
       industry_investment_view
       arena_battlefield_view
       company_memo_view
```

### 10.2 `industry_investment_view`

```yaml
industry_investment_view:
  thesis:
  demand:
  supply_competition:
  profit_pool:
  unit_economics:
  stage_gates:
  catalysts_timeline:
  risks_disconfirming_evidence:
```

### 10.3 `arena_battlefield_view`

```yaml
arena_battlefield_view:
  battlefield_definition:
  players_positions:
  winning_variables:
  evidence_scoreboard:
  stage_gates:
  inflection_points:
  company_implications:
```

### 10.4 `company_memo_view`

```yaml
company_memo_view:
  business_exposure:
  thesis_fit:
  moat_execution:
  financial_quality:
  growth_drivers:
  stage_gate_status:
  valuation_expectations:
  catalysts_risks:
  open_questions:
```

### 10.5 为什么不直接替换 11/6/8

- 旧 archive 已经和当前页面、文件结构、脚本有耦合；
- 直接替换会增加迁移成本和错误面；
- investment view 可以先作为新 tab 验证是否更适合阅读和投资分析。

结论：`11/6/8` 做 archive，`investment_lens` 做 decision view。

> **实现状态（2026-05-01）**：
> - archive 11/6/8：已实现（`app/config.py` + `industries|arenas|companies/*.md`）。Phase 3A/B/C（2026-04-30）把写入路径从 digest 改为 claim-driven proposal。
> - investment_lens 8/7/9（本节定义）：**未实现**。字段名 (`thesis` / `battlefield_definition` / `memo_view` 等) 与 archive 维度语义不重叠——archive 是分析面，investment_lens 是决策面。未来独立 Phase 实施。

## 11. Schema evolution 自进化层

每次 ingest 不只是输出内容，还要输出“现有 schema 对本次资料适不适配”。

### 11.1 `schema_fit_review`

```yaml
schema_fit_review:
  fit_score: high | medium_high | medium | low
  fit_reason: []
  awkward_mappings: []
  uncovered_content: []
  proposed_schema_changes: []
  user_decision_required: []
```

### 11.2 作用

- 告诉用户本次资料是否被当前 schema 自然覆盖；
- 暴露哪些内容被生硬塞进现有字段；
- 把“这次 ingest 暴露出的 schema 缺口”标准化沉淀下来；
- 允许方案随着实践进化，但必须保持人工确认。

### 11.3 `proposed_schema_changes`

```yaml
proposed_schema_changes:
  - change_type: add_optional_field
    target: company_candidates
    field: pipeline[]
    reason: "医药报告需要区分临床阶段和商业化产品"
    generality: "applies_to_biomed_and_medtech"
    priority: medium
    status: proposed
```

### 11.4 用户确认原则

- ingest 不得自动修改 schema；
- schema 变更必须进入待确认队列；
- 只有用户确认后，才更新 design doc、prompt、QA 和写入器。

## 12. Web 展示与 review workflow

ingest v2 的 Web 不是只显示最终 narrative，而是支持 review 流程。

### 12.1 新页面 / 新区块

1. `ingest run detail`
   - source metadata
   - preprocess warnings
   - synthesis
   - insight blocks
   - visual artifacts
   - schema fit review

2. `knowledge delta review`
   - 新增 / 重复 / 更新 / 冲突 / 强化 / 削弱
   - stage gate 更新
   - exposure 更新
   - 待确认 merge 项

3. `schema feedback review`
   - 本次 ingest 的 schema 改进建议
   - 已批准变更
   - 已拒绝/延后变更

4. `industry / arena / company detail`
   - `Archive view`
   - `Investment view`
   - `Evidence / Sources`
   - `Open questions`

### 12.2 交互原则

- 用户先看 `synthesis` 和 `delta`，再决定是否深入 facts；
- 对冲突和 schema 变更，Web 必须给出明确 pending 状态；
- investment view 和 archive view 要能相互跳转，避免信息割裂。

## 13. CLI / 后处理 / 聚合脚本要求

### 13.1 preprocess

需要输出 page-level metadata、tables、visual artifacts 和 extraction warnings。

### 13.2 aggregate / compare

聚合脚本需要新增 compare mode：

```text
new digest + existing archive -> knowledge_delta
```

### 13.3 QA

QA 脚本新增以下检查：

- facts 是否都 linked；
- stage gate guard 是否触发；
- 视觉 artifact 是否缺失；
- `schema_fit_review` 是否存在；
- company candidate 是否满足行业特定问题约束。

## 14. 样本验证结论

基于当前样本报告：

- `脑机接口.pdf`
- `储能.pdf`
- `生物医药2025.pdf`

得到以下结论：

1. PDF text layer 能恢复大量图标题、图例、标签、部分表格；
2. 产业链图、技术分类树、多曲线趋势图、热力表不能只靠文本层稳定恢复；
3. 图片策略必须进入 v2 方案，且要显式区分 text extract quality 和 structure extract quality；
4. 当前研报适合作为 v2 的先行验证样本。

## 15. 关键约束

- 不允许新的 ingest run 直接覆盖知识库。
- 不允许未确认冲突被强行 merge。
- 不允许自动替换旧 `11/6/8` archive schema。
- 不允许 schema 在未获用户确认时自动演化。
- 不允许视觉抽取结果无置信度和无复核状态就进入强事实。
- 不允许把 company screening 直接当成 company thesis。
- 不允许在 stage gate 未跨过时生成强投资结论。
- 不允许把临床前、临床中、NDA、医保准入前的 pipeline 写成确定商业化收入。
- 不允许把国家科研项目、示范项目或主题订单直接外推为公司长期商业收入。

## 16. 与现有 insight-block 设计的关系

本方案与 `2026-04-28-insight-block-ingest-design.md` 的关系是：

- 旧文档负责 **单份资料如何抽取**；
- 新文档负责 **多次 ingest 如何比较、合并、展示、演化**；
- 旧文档是新文档的 Extract 子系统，而不是被替换对象。

换句话说：

```text
2026-04-28-insight-block-ingest-design.md
  = 单次 digest / extract 设计

2026-04-28-ingest-v2-research-os-design.md
  = ingest 全链路与研究系统总设计
```

## 17. 明显缺陷与补充设计

本轮 review 发现，当前 v2 总方案虽然已覆盖主流程，但如果不补以下骨架，系统会在长期使用中出现结构性缺陷。

### 17.1 `claim` 必须成为独立对象

当前方案已经有 `atomic_facts`、`insight_blocks`、`synthesis` 和 `knowledge_delta`，但 compare / merge 真正需要比较的，经常不是单条 fact，而是更高一层的命题。

例如：

- “钠离子储能的成本优势尚未兑现”；
- “脑机接口已进入临床迈向商业化关键节点”；
- “创新药 2025 年具备更高配置性价比”。

这些内容不是 atomic fact，也不应只存在于 `synthesis` 文本中。它们需要成为可被加强、削弱、修正、冲突化的独立对象。

```yaml
claims:
  - claim_id: clm-storage-sodium-econ-001
    scope_type: industry | arena | company | theme
    scope_ref: cn-energy-storage
    claim_type: thesis | judgment | scenario | risk | gate_assessment
    claim_text: "钠离子储能的成本优势尚未转化为现实竞争力"
    supported_by_blocks: [ib-001, ib-007]
    supported_by_facts: [fact-003, fact-019]
    confidence: medium
    status: active | weakened | superseded | conflicted
```

没有独立 `claim`，`strengthened_claims` / `weakened_claims` / `updated synthesis` 会退化为文本 diff，难以长期维护。

### 17.2 必须引入时间有效性与衰减

投资研究不是静态百科。行业景气、估值判断、stage gate 状态、公司暴露和催化剂都会过期。v2 方案必须显式处理“旧知识何时降权”。

```yaml
validity:
  as_of: 2026-04-28
  review_by: 2026-07-31
  decay_policy: fast | normal | slow
  stale_after_days: 90
```

建议：

- `valuation`、`market_sentiment`、短期景气判断：快衰减；
- `technology_landscape`、`value_chain_mapping`：中慢衰减；
- `stage_gate_status`：事件驱动更新；
- `synthesis` 默认继承其所依赖对象里最短的有效期。

没有时间机制，知识库会变成 append-only 日志，用户难以分辨当前判断和历史判断。

### 17.3 必须有 canonicalization / 实体归一化层

v2 方案默认了各对象可以自然比较，但真实研报里同一实体常有多个写法：

- 公司简称 / 全称 / ticker；
- 药品名 / 项目代号；
- 技术路线中英文别名；
- gate 名称、场景名、主题名别名。

如果没有归一化层，compare / merge 很容易把同一对象误当成多个对象。

```yaml
canonical_refs:
  - entity_type: company | product | technology | gate | scenario | theme
    canonical_id: bci-invasive-route
    aliases:
      - 侵入式脑机接口
      - invasive BCI
      - 植入式脑机接口
```

不要求一开始完全自动化，但 schema 必须预留 canonical id 与 alias 映射，否则知识库会高度碎片化。

### 17.4 必须定义用户确认粒度

v2 方案要求用户确认 delta 和 schema 变更，但未定义确认粒度。太粗会误合并，太细会把用户拖入 review 地狱。

建议默认粒度为：

```text
scope + delta type
```

即用户默认审批：

- 某个 industry 的 facts 更新；
- 某个 arena 的 stage gate 更新；
- 某个 company 的 exposure 更新；
- 某次 ingest 的 schema proposal。

必要时再 drill down 到单条 delta。这样既能控制风险，也能控制 review 成本。

### 17.5 必须控制 review burden

v2 会天然产生多种待确认对象：

- conflict review
- visual review
- schema review
- merge review
- candidate demotion / upgrade review

如果没有负载控制，系统在实践中会因为 pending backlog 过大而不可用。

建议增加以下控制：

- 默认只把高影响 review 项推给用户；
- 低影响项记录但不阻塞 merge；
- 单次 ingest 的 review 总量设预算；
- 超载时自动降级为“只产 digest，不生成 merge proposal”。

### 17.6 必须有失败降级策略

不是每份资料都应该完整进入 compare / merge / investment view。

建议分三级降级：

1. **完整模式**：可 compare、可 delta、可 merge；
2. **digest-only 模式**：抽取结果可读，但不建议 merge；
3. **archive-only 模式**：只归档 source 与 preprocess 结果，不生成 investment view。

典型触发条件：

- preprocess 质量差；
- visual loss 过高；
- schema fit 太低；
- conflict 过多；
- 核心 stage gate 页无法可靠抽取。

### 17.7 必须定义 success metrics

如果没有指标，系统会越来越复杂，但无法判断复杂度是否换来了质量收益。

至少应跟踪三类指标：

- 质量：claim / fact / candidate / visual artifact 误判率；
- 效率：单次 ingest review 时间、merge latency、pending backlog；
- 价值：有多少 ingest 真正更新了 archive，有多少 investment view 被继续使用。

这些指标不一定在第一期就完全自动化，但设计阶段必须明确它们存在。

## 18. Phase 1 / Phase 2 收缩原则

本方案在完整形态下覆盖 preprocess、extract、validate、compare、merge、views、schema evolution、web review workflow 等多个层次，但首期实现不应追求“设计上全覆盖”。

本轮收缩 review 采用的原则是：

> **Phase 1 只保留“不做就会导致明显系统缺陷”的最小骨架；其他提升体验、提升可读性、降低运营成本但不影响系统正确性的能力，进入 Phase 2。**

### 18.1 Phase 1 必须具备的最小骨架

#### A. 最小 preprocess metadata

Phase 1 不要求完整的页面 taxonomy 和复杂 artifact catalog，但至少必须输出：

- page number
- `text_quality`
- `image_heavy`
- `chart_heavy`
- `table_heavy`
- `extraction_warnings`

原因：如果系统连“哪些关键内容来自低质量页、图表页、图片页”都不知道，后续 QA 与 merge 根本无法控制风险。

#### B. 继续使用 insight-block 作为 extract 中间层

Phase 1 必须保留：

- `source_digest`
- `insight_blocks[]`
- `atomic_facts[]`
- `stage_gates[]`
- `company_candidates[]`
- `synthesis`
- `schema_fit_review`

原因：如果没有 extract 中间层，系统会退回“直接把原文碎片塞进 11/6/8 archive”的状态，原文论证链会丢失。

#### C. `claim` 独立对象

Phase 1 必须引入独立 `claim` 对象，并允许 compare / delta 直接表达：

- `strengthened_claims`
- `weakened_claims`
- `conflicted_claims`

原因：如果没有独立 claim，系统只能比较 facts，无法表达“新研报是在强化还是削弱一个既有投资判断”。这会让多次 ingest 退化成笔记堆积，而不是知识演进。

#### D. 最小 Validate / QA

Phase 1 只保留最关键的机器校验：

- 每个 `atomic_fact` 必须有 `linked_block_id`
- 每个 `insight_block` 基本字段必须完整
- `stage_gate` 未跨过时不得产出强结论
- 来自 `image_heavy` / `chart_heavy` 页的关键结论必须保留 artifact 或 warning 痕迹
- `company_candidates` 不得直接提升为高置信 company thesis

原因：如果没有这些校验，错误内容会被正常 merge 进知识库，形成结构性污染。

#### E. 最小 Compare / Delta

Phase 1 必须至少支持：

- `new_facts`
- `updated_facts`
- `conflicting_facts`
- `strengthened_claims`
- `weakened_claims`
- `stage_gate_updates`
- `new_company_candidates`

原因：没有 delta，系统就无法正确处理“同一行业 / arena / company 被多次 ingest”的场景。

#### F. Human-approved merge

Phase 1 必须保证：

- ingest run 先生成独立 digest
- compare 产出独立 delta
- 只有用户确认过的 delta 才能写入 archive

原因：这是整个系统的总闸门。如果抽取结果直接落库，错误会逐次累积，且很难追溯污染来自哪次 ingest。

#### G. 最小时效性模型

Phase 1 不要求完整 decay engine，但至少要给 facts / claims 提供：

- `as_of`
- `review_by` 或 `stale_after_days`

原因：投资研究天然受时效约束。没有时间属性，旧判断和新判断无法共存，也无法判断哪些结论已经陈旧。

### 18.2 Phase 2 再做的增强项

以下能力有价值，但不属于“缺了就会让系统明显失真”的首期骨架，可进入 Phase 2。

#### A. 完整 `visual_artifacts` 体系

包括：

- 更细的 artifact 类型
- `text_extract_quality` / `structure_extract_quality` 的完整分层
- artifact 与 block / fact / claim 的丰富映射
- 更强的视觉结构恢复

Phase 1 只需要做到“视觉高风险内容有痕迹、不能直接升格为强事实”。

#### B. 完整 Investment views

包括：

- `industry_investment_view`
- `arena_battlefield_view`
- `company_memo_view`

这些是高价值的消费层与阅读层，但不是 ingest 正确性的最小前提。

#### C. Archive view 与 Investment view 的完整双轨联动

包括新 tab、双向跳转、Evidence / Sources 联动等。这些都可以在 ingest 主流程稳定后再做。

#### D. Schema evolution 产品化工作台

`schema_fit_review` 本身在 Phase 1 应保留输出，但：

- 不必一期就做 schema feedback dashboard
- 不必一期就做复杂的 proposal triage / approval queue

Phase 1 把它作为 ingest run 结果中的一个 review section 即可。

#### E. 重型 canonicalization 体系

Phase 2 再考虑：

- 更完整的 entity graph
- 跨 domain alias 归并
- 更复杂的 technology / scenario / theme normalization

Phase 1 只建议保留最小 canonicalization（如 company name/ticker alias、常见主题/技术别名）以防实体重复爆炸。

#### F. 复杂 review burden control

包括：

- 批量审批
- 风险分层 review queue
- 自动排序与优先级系统
- review 噪音压缩

这些是流程效率优化，不是首期正确性前提。

#### G. 成熟 success metrics 仪表盘

Phase 2 再做：

- merge acceptance rate
- conflict rate
- review burden trend
- schema change adoption rate

Phase 1 只需记录基础统计，供人工观察即可。

### 18.3 最小首期的一句话定义

如果必须再压缩成一句话，Phase 1 的核心就是：

> **extract 中间层 + claim 对象 + 最小 QA + delta 比较 + 用户确认 merge + 最小时效性。**

只要这六件事成立，系统就具备“可持续 ingest 而不明显污染知识库”的最小可用骨架；其余能力都可以在此基础上迭代。

## 19. 后续实施建议

后续实施建议按以下顺序拆解：

1. 定义 preprocess artifact schema；
2. 扩展 digest schema，加入 `schema_fit_review`、`visual_artifacts` 和独立 `claims`；
3. 引入 canonical refs 与 validity 规则；
4. 实现 compare / delta / merge 流程；
5. 增加 QA 规则与失败降级策略；
6. 新增 ingest run / delta / schema feedback 页面；
7. 在 industry / arena / company 页面增加 investment view。

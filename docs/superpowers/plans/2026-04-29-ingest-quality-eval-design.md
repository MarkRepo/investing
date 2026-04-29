# Phase 1 Bundle 质量评估系统设计方案

**日期**：2026-04-29
**适用范围**：Phase 1 ingest review bundle 的质量评估
**关系说明**：本文档是 [2026-04-29-ingest-endgame-design.md](../specs/2026-04-29-ingest-endgame-design.md) 终局评测规划的**第一阶段**。后续 Phase 会扩展评测面（claim 层、叙事层、matching 层），评测系统随主系统同构增长。

---

## 1. 目标与范围

### 1.1 当前目标（Phase 1）

每次 ingest 完成后，对产出的 `ingest_review_bundle` 做系统性质量评估，积累数据驱动 ingest prompt / QA 的持续改进。

### 1.2 非目标

- 不修改单次 bundle 内容（修复走"改 bundle → 重跑 QA"）
- Python 不调 LLM API（所有语义判断在 Claude 对话里）
- 不自动写入 archive

### 1.3 核心假设

评测产出是**缺陷目录 + 演进就绪度信号**，不是分数。高频缺陷类型驱动改进目标；演进就绪度信号驱动 phase 迁移决策。

---

## 2. 评测系统随 Phase 演进的规划

本文档定义的是 Phase 1 所需的评测能力。每进入新 phase，新增对应评测面，结构如下：

| 系统 Phase | 新评测对象 | 新增评测内容 |
|---|---|---|
| **Phase 1（本文档）** | review bundle | 覆盖、忠实、推断、校准、投资实用、一致、压缩、叙事、系统适配 |
| P1.5（桥梁） | + claim_candidates（bundle 新字段） | claim 粒度、dimension_hint 准确度、phase2 就绪度 |
| P2（claim 层） | + claim registry + archive 写入决策 | claim dedup 质量、arena 审批判断、archive 路由准确度 |
| P3（叙事层） | + 投资视图叙事段 | 叙事可读性、叙事与 backing claims 一致度、divergent 复写质量 |
| P4（event 监视） | + matching 结果 + 优先级 | 事件匹配 precision/recall、优先级与用户实际处理偏好的一致度 |

每 phase 的评测用同一套 `quality_review.json` 骨架，通过 `review_version` 字段和新增可选对象向后兼容。

**关键原则**：Phase 1 评测 schema **保留扩展位**（`claim_evaluation`, `narrative_evaluation`, `matching_evaluation` 等可选对象）。未来 phase 只追加字段，不破坏既有 review 数据。

---

## 3. 架构总览

```
单次 ingest
    │
    ├─ [L1] 结构 QA            ingest_qa.py review-bundle         ← 已有
    ├─ [L2] 量化指标            ingest_qa.py score-bundle          ← 新增
    ├─ [L2.5] schema 一致性检查  ingest_qa.py schema-conformance    ← 新增
    └─ [L3] LLM 语义评审        Claude 对话（bundle-quality-review prompt） ← 新增
                    │ quality_review.json
                    ▼
             [L4] 聚合分析      ingest_qa.py defect-report         ← 新增
                    │
                    ▼
             系统改动（prompt / QA 规则 / design 文档）
                    │
                    ▼
             回归对比（对旧文档重新 ingest，对比前后 quality_review）
```

各层独立，输出通过文件系统传递。

---

## 4. 数据模型：quality_review.json

### 4.1 顶层结构

```json
{
  "review_version": "v1",
  "bundle_id": "nuclear-fusion-2024-haitong",
  "source_title": "核聚变行业深度报告",
  "source_type": "sellside_industry_report",
  "bundle_date": "2026-04-29",
  "review_date": "2026-04-29",
  "prompt_version": "2026-04-29",
  "reviewer": "claude",

  "metrics": { ... },                    // L2 自动填
  "schema_conformance": { ... },         // L2.5 自动填
  "dimension_ratings": { ... },          // L3 LLM 填
  "system_fit": { ... },                 // L3 LLM 填
  "phase2_readiness": { ... },           // L3 LLM 填 (新增)
  "defects": [ ... ],                    // L3 LLM 填

  "overall_rating": "medium_high",
  "reviewer_notes": "..."

  // 后续 phase 扩展位（Phase 1 为空）:
  // "claim_evaluation": { ... },
  // "narrative_evaluation": { ... },
  // "matching_evaluation": { ... }
}
```

### 4.2 `metrics`（L2 自动）

```json
{
  "sections_total": 45,
  "sections_reviewed": 42,
  "coverage_rate": 0.93,
  "high_confidence_rate": 0.38,
  "risky_high_rate": 0.0,
  "reasoning_shallow_rate": 0.08,
  "fact_per_block": 2.8,
  "unknown_dimension_rate": 0.12,
  "auto_qa_errors": 0,
  "auto_qa_warnings": 1
}
```

**Phase 1 只保留可可靠计算的指标**。`entity_capture_rate` 需要 NER，误差大于信号，移出 Phase 1。

### 4.3 `schema_conformance`（L2.5 自动，新增）

检查 design 文档 / prompt / QA 三者的字段集一致性，避免再次分叉。

```json
{
  "design_prompt_drift": {
    "design_fields_not_in_prompt": ["insight_blocks.assumptions", "insight_blocks.counterpoints"],
    "prompt_fields_not_in_design": [],
    "severity": "warning"
  },
  "prompt_bundle_drift": {
    "prompt_required_fields_missing_in_bundle": [],
    "severity": "error"
  },
  "qa_coverage": {
    "prompt_fields_not_checked_by_qa": ["insight_blocks.routing"],
    "severity": "note"
  }
}
```

自动比对：
- design 里声明字段 vs prompt 里要求字段 vs bundle 实际产出字段 vs QA 实际校验字段

这个信号触发**系统自我维护**——当三者分叉时明确告诉你"文档和实施已经不同步了"。

### 4.4 `dimension_ratings`（L3 LLM）

```json
{
  "coverage":           { "score": "medium", "notes": "section 18 后半段漏提炼" },
  "fidelity":           { "score": "high",   "notes": "" },
  "reasoning_depth":    { "score": "medium", "notes": "" },
  "calibration":        { "score": "high",   "notes": "" },
  "investment_utility": { "score": "medium", "notes": "stage_gates 过抽象" },
  "coherence":          { "score": "high",   "notes": "" },
  "compression":        { "score": "high",   "notes": "" },
  "narrative":          { "score": "medium", "notes": "blocks 缺主线" }
}
```

共 8 个维度，都用五档评分（`high / medium_high / medium / medium_low / low`）。

**`system_fit` 不在 dimension_ratings 里**，作为独立顶层对象（见 4.5）。

### 4.5 `system_fit`（L3 LLM，独立顶层）

```json
{
  "source_type_match": "good",
  "source_type_notes": "分节研报结构与 prompt 设计吻合",
  "prompt_friction_points": [],
  "schema_adequacy": "partial",
  "schema_adequacy_notes": "fusion-fission 混合路线无对应维度",
  "block_type_naturalness": "good",
  "block_type_naturalness_notes": "",
  "adaptation_suggestions": [],
  "overall_fit": "partial"
}
```

三态判断（`good | partial | poor`），回答"工具和这类文档合不合拍"——和 dimension_ratings 的"这次提炼做得怎么样"正交。

### 4.6 `phase2_readiness`（L3 LLM，新增）

评估 bundle 是否为 P2（claim 层 + archive 写入）做好了准备。P1.5 补丁实施后此字段才真正有内容。

```json
{
  "claim_candidate_quality": "good",
  "claim_candidate_notes": "10 条候选命题，粒度合理，dimension_hint 分布均衡",
  "as_of_completeness": "good",
  "source_type_branch_applicable": true,
  "source_type_branch_fields_complete": "partial",
  "source_type_branch_notes": "核聚变报告缺少 stage_gate 的 current_state 字段",
  "overall_p2_readiness": "partial"
}
```

**Phase 1 当前不填** (bundle 还没有 claim_candidates)。P1.5 prompt 加字段后开始填。

### 4.7 `defects`

结构不变：

```json
[
  {
    "defect_id": "def-001",
    "dimension": "coverage",
    "severity": "error",
    "defect_type": "missed_subtopic",
    "description": "...",
    "linked_section": "section-18",
    "linked_block_ids": [],
    "root_cause_hint": "prompt"
  }
]
```

`root_cause_hint` 可选值扩展：`prompt | qa_rule | both | design_gap | source_type_branch | unclear`。

`design_gap` 表示"设计本身没考虑到这种情况"，`source_type_branch` 表示"需要 per-source_type 分支处理"。

### 4.8 字段约束

| 字段 | 约束 |
|---|---|
| `review_version` | 固定 `"v1"` |
| `source_type` | 与 bundle source_digest.source_type 一致 |
| `prompt_version` | 记录 ingest prompt 版本日期 |
| `dimension_ratings[*].score` | `high \| medium_high \| medium \| medium_low \| low` |
| `system_fit.*` 三值字段 | `good \| partial \| poor` |
| `phase2_readiness.*` 三值字段 | `good \| partial \| poor` |
| `defects[*].severity` | `error \| warning \| note` |
| `defects[*].root_cause_hint` | `prompt \| qa_rule \| both \| design_gap \| source_type_branch \| unclear` |
| `overall_rating` | 五档 |

---

## 5. 缺陷类型完整分类

### 5.1 覆盖度（coverage）

| defect_type | 说明 |
|---|---|
| `missed_subtopic` | 原文 section 内子话题未被提炼 |
| `missed_company` | 原文明确点名的公司未进入 candidates |
| `missed_key_figure` | 重要数值/指标未被 fact 捕获 |

### 5.2 忠实度（fidelity）

| defect_type | 说明 |
|---|---|
| `hallucinated_fact` | fact 无原文支撑 |
| `entity_mismatch` | fact_text 实体未出现在 evidence_quote（已有 QA） |
| `evidence_quote_fabricated` | quote 在 preprocess 中找不到（已有 QA） |

### 5.3 推断质量（reasoning_depth）

| defect_type | 说明 |
|---|---|
| `facts_only_reasoning` | reasoning_chain 全是事实陈述，无投资含义 |
| `shallow_reasoning` | reasoning_chain < 2 条（已有 QA） |
| `block_fact_undifferentiated` | block summary = facts 合并，无额外合成 |
| `circular_reasoning` | 结论复述前提 |

### 5.4 校准度（calibration）

| defect_type | 说明 |
|---|---|
| `inflated_confidence` | high confidence 无充分支撑 |
| `uniform_high_evidence` | 所有 blocks/facts 均为 high（可疑） |
| `overclaimed_synthesis` | synthesis 措辞超出 evidence strength 允许（已有 QA） |
| `exposure_type_overclaimed` | direct_supplier 无合同证据 |

### 5.5 投资实用性（investment_utility）

| defect_type | 说明 |
|---|---|
| `vague_stage_gates` | stage gate 条件过抽象 |
| `missing_stage_gates` | 有重要门槛未标 |
| `non_actionable_questions` | investment_questions 过宽泛 |
| `candidate_overclaimed` | candidates 被写成确定受益者 |

### 5.6 内部一致性（coherence）

| defect_type | 说明 |
|---|---|
| `synthesis_block_mismatch` | synthesis 结论无 block 支撑 |
| `candidate_not_in_blocks` | candidate source_block_ids 对应 block 未提该公司 |
| `relation_direction_wrong` | block_relations 方向有误 |

### 5.7 压缩效率（compression）

| defect_type | 说明 |
|---|---|
| `redundant_blocks` | 两个 block 覆盖同一子话题 |
| `block_too_broad` | 单 block 混多个无关子话题 |
| `over_granular_facts` | facts 粒度过细 |

### 5.8 叙事逻辑与可理解性（narrative）

| defect_type | 说明 |
|---|---|
| `disconnected_blocks` | blocks 之间缺联系（块间关系问题） |
| `missing_narrative_arc` | 整体无"是什么 → 为什么 → 投资含义"递进（结构问题） |
| `synthesis_not_grounded` | synthesis 引入 blocks 中未建立的框架 |
| `block_summary_opaque` | block summary 需对照原文才能理解 |
| `inconsistent_entity_reference` | 同一实体不同 blocks 称呼不一 |
| `synthesis_sections_incoherent` | what_we_know / plausible / cannot_conclude 矛盾 |

### 5.9 系统适配性（system_fit）

| defect_type | 说明 |
|---|---|
| `source_type_mismatch` | 文档结构 vs prompt 设计假设 |
| `reasoning_chain_forced` | 文档本身无投资视角但被强制要求推断 |
| `block_type_unnatural` | block_type 大量 unknown 或套用 |
| `schema_dimension_gap` | 文档核心内容无法映射到现有 archive 维度 |
| `stage_gate_framework_mismatch` | gate 框架不适用于该文档类型 |
| `coverage_review_mismatch` | full_report_pass 与文档结构不匹配 |
| `wrong_dimension_hint` | 具体 block 的 dimension_hint 错误 |
| `wrong_target_layer` | 具体 block 的 target_layer 错误 |

### 5.10 Phase 2 就绪度（P1.5 后启用）

| defect_type | 说明 |
|---|---|
| `claim_candidate_granularity_off` | 命题过细（单个事实）或过粗（含多个独立命题） |
| `claim_dimension_hint_wrong` | claim 的 dimension_hint 分错层 |
| `claim_supporting_blocks_weak` | claim 挂的 supporting_block_ids 不足以支撑命题 |
| `as_of_missing_or_wrong` | validity 字段缺失或填错 |
| `source_type_specific_fields_missing` | 医药/核聚变等应有的专属字段未填 |

---

## 6. 各层组件规格

### 6.1 L2：`ingest_qa.py score-bundle`

```bash
ingest_qa.py score-bundle --bundle bundle.json --preprocess preprocess.json [--out quality_review.json]
```

行为：合并 metrics 到 quality_review.json（不存在则创建骨架）。

Phase 1 只计算以下可可靠指标：

```
coverage_rate          = sections_reviewed / sections_total
high_confidence_rate   = high_conf_facts / total_facts
risky_high_rate        = high_conf_facts_on_risky_pages / high_conf_facts
reasoning_shallow_rate = shallow_blocks / total_blocks
fact_per_block         = total_facts / total_blocks
unknown_dimension_rate = unknown_dim_blocks / total_blocks
auto_qa_errors         = 从 review-bundle 读
auto_qa_warnings       = 从 review-bundle 读
```

### 6.2 L2.5：`ingest_qa.py schema-conformance`（新）

```bash
ingest_qa.py schema-conformance --design docs/superpowers/specs/2026-04-29-ingest-v2-phase1-review-bundle-design.md --prompt docs/prompts/ingest-review-bundle.md --out quality_review.json
```

行为：
- 解析 design 文档提取声明字段集
- 解析 prompt 提取要求字段集
- 读 `scripts/ingest_qa.py` 提取 QA 校验字段集
- 三者交叉比对，输出到 `quality_review.json.schema_conformance`

触发：每次 ingest 后跑一次；也可独立跑。

**注意**：解析 markdown / python 提取字段集是工程任务，可以用简单的 grep + pattern，不需要完整 AST。字段集定义清单手动维护（一份 JSON）比自动解析更可靠，初期推荐手动维护。

### 6.3 L3：`docs/prompts/bundle-quality-review.md`

Claude 对话里贴此 prompt + bundle.json + preprocess.json + 已填的 metrics，Claude 返回 quality_review.json（严格 JSON）。

**评审步骤结构**：

```
【L3.1 内容质量】
- 对照 preprocess sections 核查漏提炼子话题 → missed_subtopic
- 核查 reasoning_chain 最后一条是推断还是事实复述 → facts_only_reasoning
- 核查 stage_gates 可验证性 → vague_stage_gates
- 核查 synthesis 与 blocks 一致性 → synthesis_block_mismatch

【L3.2 叙事与可理解性】
- 判断 block summary 是否自包含 → block_summary_opaque
- 判断 blocks 块间联系 → disconnected_blocks
- 判断整体递进结构 → missing_narrative_arc
- 核查 synthesis 各小节一致性 → synthesis_sections_incoherent
- 核查实体引用一致 → inconsistent_entity_reference

【L3.3 系统适配性】
- 判断文档结构 vs prompt 设计假设 → source_type_mismatch
- 判断 reasoning_chain 要求对该文档是否自然 → reasoning_chain_forced
- 判断 block_type 分配质量 → block_type_unnatural
- 核查 schema_fit_review 是否遗漏真实 gap → schema_dimension_gap
- 核查 dimension_hint / target_layer 准确度 → wrong_dimension_hint / wrong_target_layer
- 填写 system_fit 结构化字段

【L3.4 Phase 2 就绪度】（P1.5 后启用）
- 核查 claim_candidates 粒度 → claim_candidate_granularity_off
- 核查 claim 的 dimension_hint 准确度 → claim_dimension_hint_wrong
- 核查 supporting_blocks 充足度 → claim_supporting_blocks_weak
- 核查 as_of 完整度 → as_of_missing_or_wrong
- 核查 source_type 专属字段 → source_type_specific_fields_missing
- 填写 phase2_readiness 结构化字段

输出严格 JSON 到 quality_review.json
```

### 6.4 L4：`ingest_qa.py defect-report`

```bash
ingest_qa.py defect-report --reviews-dir ingests/ [--min-count 2] [--top 15]
```

聚合跨文档的 defect 频率，按 root_cause_hint 分组：

```
=== By root_cause ===
prompt                   28 defects / 6 bundles
qa_rule                   3 defects / 2 bundles
design_gap                4 defects / 3 bundles  ← 设计层问题
source_type_branch        8 defects / 4 bundles  ← 需要专属分支

=== By defect_type ===
defect_type                   count  error  warning  bundles
missed_subtopic                  12      8        4     6/8
facts_only_reasoning              9      0        9     5/8
...
```

---

## 7. `review-quality` 校验规则

| rule_id | severity | 说明 |
|---|---|---|
| `missing_required_field` | error | review_version/bundle_id/defects/overall_rating 缺失 |
| `invalid_score_value` | error | dimension_ratings score 不在五档内 |
| `invalid_fit_value` | error | system_fit / phase2_readiness 三值字段不在 good/partial/poor 内 |
| `invalid_defect_type` | warning | defect_type 不在已知分类中 |
| `invalid_severity` | error | severity 不是 error/warning/note |
| `invalid_root_cause_hint` | warning | root_cause_hint 不在允许值内 |
| `invalid_overall_rating` | error | overall_rating 不在五档内 |
| `defect_id_duplicate` | error | defect_id 重复 |
| `linked_block_unknown` | warning | defect 引用 block_id 不存在 |
| `linked_section_unknown` | warning | defect 引用 section 不存在 |

---

## 8. 工作流

### 8.1 单文档 ingest 后（每次）

```
preprocess_report.py
  → Claude 对话（ingest prompt）→ bundle.json
  → ingest_qa.py review-bundle           # 结构 QA
  → ingest_qa.py score-bundle            # metrics
  → ingest_qa.py schema-conformance      # 三者一致性
  → Claude 对话（quality-review prompt） → quality_review.json
  → ingest_qa.py review-quality          # quality_review 结构校验
```

### 8.2 批量分析（每积累 5+ 份）

```
ingest_qa.py defect-report --reviews-dir ingests/
  → 读取高频 defect_type + root_cause 分布
  → 决定本轮改 prompt / QA / design 文档
```

### 8.3 回归验证（改动后）

```
对代表性文档重新 ingest → 新 quality_review.json
ingest_qa.py compare-reviews --before v1 --after v2
  → dimension_ratings delta + defect diff
  → 确认目标 defect 减少，无新增 defect
```

---

## 9. 实施计划

### Phase 1 评测（本文档即时可做）

**优先级 A**（先做）：
1. `docs/prompts/bundle-quality-review.md` 完整 prompt（含 L3.1-L3.3，暂不含 L3.4）
2. `ingest_qa.py review-quality` 子命令（结构校验）
3. 对现有核聚变 / 储能 bundle 各跑一次评审，验证 prompt 可用

**优先级 B**：
4. `ingest_qa.py score-bundle` 子命令（metrics 自动化）
5. `ingest_qa.py schema-conformance` 子命令（需要先手动维护 design/prompt/QA 字段集 JSON）

**优先级 C**（积累 5+ 份 review 后）：
6. `ingest_qa.py defect-report` 子命令
7. `ingest_qa.py compare-reviews` 子命令

### P1.5 评测扩展（与 ingest P1.5 同步）

- L3 prompt 补 L3.4 phase2_readiness 评审
- 缺陷类型 §5.10 启用

### P2+ 评测扩展（随主系统 phase 演进）

按 §2 规划，新增 `claim_evaluation` / `narrative_evaluation` / `matching_evaluation` 顶层对象和对应 prompt 段落。

---

## 10. 设计约束与局限性

### 10.1 设计约束

- **Python 不调 LLM API**：所有 L3 判断在 Claude 对话里
- **quality_review.json 与 bundle.json 分离**：bundle 是 artifact，review 是 meta-artifact
- **defect_type 开放扩展**：未知 defect_type 只警告不阻断
- **prompt_version 必填**：确保回归对比有锚点
- **schema 向后兼容**：新 phase 只追加字段，不破坏既有 review

### 10.2 LLM 自评局限性（重要）

**已知**：Claude 评审另一个 Claude 产出的 bundle 存在系统性盲点——两者共享训练数据，同源失误会被同源放过。尤其以下维度受影响：

- `coverage.missed_subtopic`：ingest Claude 认为"不重要"跳过的子话题，评审 Claude 可能同样认为不重要
- `reasoning_depth.facts_only_reasoning`：同模型对"投资含义推断"的标准相近
- `narrative.missing_narrative_arc`：同模型对"叙事连贯"的标准相近

**缓解**：
1. **跨 LLM 评审**（用户规划中）：用 GPT / Gemini 等其他 LLM 作为第二评审器，对比两者评审差异
2. **spot-check 机制**：用户偶尔人工评审一份，对比 LLM 评审偏差
3. **不把 overall_rating 当 ground truth**：只用于趋势观察，不做决策依据

### 10.3 评测本身驱动改进的前提条件

评测系统要真正驱动 ingest 改进，需要：

1. **信号稳定性**：同一 bundle 评审两次结果应该大体一致。噪音太大则评测无用
2. **归因清晰**：改动后质量变化应能归因到具体 prompt 或 QA 改动
3. **防止 gaming**：prompt 改动不该只是"让 LLM 评审不抱怨"，而要实质改善提炼质量
4. **跨 source_type 基线**：不同报告类型有不同基线，评分/缺陷率需按 source_type 分组看

这些是评测系统成熟的标志，Phase 1 只能做到**第 1 条的初步验证**；第 2-4 条在积累 10+ 份评审后才能观察。

### 10.4 评测不能做什么

- **不能评估投资价值**：能告诉你 bundle 结构好坏，不能告诉你这份研报观点是否正确
- **不能替代实际使用验证**：最终检验是"这份 bundle 在 Phase 2 合成 claim 时好不好用"。评测只是代理信号
- **不能保证改进无副作用**：某维度提升可能以另一维度为代价，需要 compare-reviews 持续监测

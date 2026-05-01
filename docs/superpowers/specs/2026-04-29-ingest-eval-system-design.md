# Ingest 评测系统分阶段设计

**Status**: 概念设计，用于指导各 phase 实施计划
**Date**: 2026-04-29
**Builds on**: [2026-04-29-ingest-endgame-design.md](./2026-04-29-ingest-endgame-design.md)
**Supersedes**: `plans/2026-04-29-ingest-quality-eval-design.md`（旧版按 Phase 1 单一形态写，未覆盖后续 phase）

---

## 1. 目标与原则

### 1.1 目标

评测系统驱动 ingest 系统迭代：
- 每次 ingest 后可在 Claude 对话里触发评测
- 产出结构化缺陷记录，支持按 root_cause 聚类
- 跨 ingest 跟踪趋势，为 phase 升级提供门槛信号

### 1.2 核心原则

- **评测与主系统同阶段演进**：每 phase 评测只覆盖该 phase 产出的对象；不提前设计未来对象的评测规则
- **LLM 判断在对话里**：评测系统 Python 端不调 LLM API，与主系统一致
- **分数弱化，缺陷强化**：LLM 自评绝对分数不可靠；主产物是**结构化缺陷清单**，分数仅做趋势相对观察
- **评测不阻断 ingest**：发现缺陷是信号，不是验收门；是否修在下次 ingest 由用户判断
- **评测本身可审计**：评测 prompt / 规则集 git 版本化，每次评测输出关联 prompt 版本

### 1.3 非目标

- 不出总分作"合格/不合格"结论
- 不自动化定时跑（token 成本由用户决定）
- 不替代 git 作为内容变更审计

---

## 2. 方法分层（贯穿所有 phase）

| 层   | 方法                        | 典型用例                                             | 触发                     |
| --- | ------------------------- | ------------------------------------------------ | ---------------------- |
| L1  | Python schema/rule 检查     | 硬性结构错（缺字段、引用错位、preprocess risk 与 confidence 不匹配） | 每次 ingest 必跑           |
| L2  | Claude 对话里跑 review prompt | 语义判断（覆盖度、推理完整、校准、叙事）                             | 用户按需                   |
| L3  | 跨 ingest 轨迹观察             | claim 状态演进合理性、重复 claim 检测、review_by 处理及时性        | 定期（建议每 N 次 ingest 或每周） |
| L4  | Cross-LLM 交叉验证            | 用其他模型独立跑 L2 对齐 Claude 自评盲区                       | Phase 5+ 启用            |

L1 必跑、零成本；L2 是主力语义评测；L3 需样本量（Phase 2+ 有意义）；L4 规模化后引入。

---

## 3. Phase 1 评测（当前阶段）

### 3.1 范围

Review bundle 的全部组件：`source_digest / insight_blocks / atomic_facts / stage_gates / company_candidates / synthesis / schema_fit_review / qa_warnings`。

### 3.2 L1 检查

直接复用 [Phase 1 spec §11](./2026-04-29-ingest-v2-phase1-review-bundle-design.md) 已定义的 QA 规则集（bundle shape / fact-block link / evidence fidelity / preprocess risk discipline / stage-gate discipline / company candidate discipline / synthesis discipline）。评测系统**不重复实现**，只聚合 `qa_warnings` 进 evaluation 记录。

### 3.3 L2 维度

4 维评测 + 2 项独立判断。

| 维度 | 评测内容 |
|---|---|
| `coverage_fidelity` | 报告关键论点是否被提炼；提炼是否扭曲原文（合并两者因为漏和扭曲往往同源） |
| `reasoning_quality` | insight_block 的 reasoning_chain 完整性；assumptions / counterpoints 是否被识别；facts 是否支撑 block 结论 |
| `calibration` | 证据强度 vs. confidence 匹配度；低质量来源（chart_heavy、image_heavy 页）是否被误升为 high |
| `narrative` | synthesis 可读性；blocks 之间的逻辑连接；`what_we_know / what_is_plausible / cannot_conclude` 分层纪律 |

独立判断（不进维度分，单独输出）：
- `system_fit`：bundle 字段集是否适配该 source_type（此 phase 常见答案：通用 prompt 对某些 source_type 不够——是 Phase 1.5 的主要信号源）
- `phase2_readiness`：当前 bundle 能否为未来 claim layer 提供足够基础

### 3.4 Defect 结构

```yaml
defect:
  id
  category            # 对应 L1 规则名或 L2 维度名
  severity            # blocker | major | minor
  target_ref          # block_id / fact_id / candidate_id / synthesis
  description
  root_cause_hint     # prompt_gap | schema_gap | source_hard_case | preprocess_loss
  suggested_fix
```

`root_cause_hint` 是聚类 key，驱动后续 prompt / schema / preprocess 三条迭代线。

### 3.5 Evaluation 输出

```yaml
evaluation:
  bundle_ref
  evaluated_at
  evaluator               # e.g. claude-opus-4-7
  eval_prompt_version
  method_layers_run       # [L1, L2]
  dimension_ratings:
    coverage_fidelity:    {trend, notes}
    reasoning_quality:    {trend, notes}
    calibration:          {trend, notes}
    narrative:            {trend, notes}
  system_fit:             {notes}
  phase2_readiness:       {notes}
  defects: []
  overall_notes
```

`trend` 不是绝对分数（1-5），而是**相对上次同 source_type ingest** 的定性判断：`stronger | comparable | weaker | insufficient_samples`。首次评测或缺乏对比样本时选 `insufficient_samples`。

### 3.5.1 存储约定

- evaluation 与 bundle、preprocess 同目录存放
- 文件名固定 `evaluation.json`；多次评测时后续记为 `evaluation-{ISO-date}.json`（不覆盖旧版）
- `bundle_ref` 统一存 `source_digest.source_id`，便于跨目录跨 session 引用
- `dimension_ratings.*.trend` 允许值：`stronger | comparable | weaker | insufficient_samples`；首次评测或缺乏对比样本时选 `insufficient_samples`
- `evaluator` 字段由人工填（如 `claude-opus-4-7`、`gpt-5` 等），evaluation init 留空
- `eval_prompt_version` 与 prompt 文件头 `<!-- prompt_version: ... -->` 对齐

### 3.6 迭代闭环

- `prompt_gap` 缺陷聚类 → Phase 1 prompt 模版补丁
- `schema_gap` 缺陷聚类 → 推动 Phase 1.5 桥梁字段集
- `source_hard_case` 聚类 → 推动 Phase 1.5 的 source_type 分型
- `preprocess_loss` 聚类 → preprocess 阶段正则/模版正向修

---

## 4. Phase 1.5 评测（桥梁补丁）

Phase 1.5 的主系统变更：bundle 新增 `claim_candidates[]`、`as_of`、source_type 分型字段、schema_fit_review 结构化。

### 4.1 新增 L1 检查

- `claim_candidate.claim_text` 单句启发检查（长度 + 标点；语义层面单句交给 L2）
- `claim_candidate.scope_type ∈ {industry, arena, company, cross_cutting}`，`scope_ref` 格式合法
- `claim_candidate.supporting_block_ids` 均存在于 `insight_blocks[].id`
- `claim_candidate.direction_on_source` 必填（supports / refutes / neutral）
- `claim_candidate.as_of` 存在且等于 source_date
- source_type 分型必填字段按类型检查（医药 → pipeline、核聚变 → stage_gate 等）

### 4.2 新增 L2 维度

| 维度 | 评测内容 |
|---|---|
| `claim_extraction_quality` | 粒度是否合适（不过粗、不过碎）；text 是否单句命题；scope/dimension_hint 归属是否准确；是否可作为跨报告比对单元 |

此维度独立立项（不并入 reasoning_quality），因为 Phase 2 起它是 matching 质量的先决因素，需单独追溯。

### 4.3 Phase2_readiness 升格

Phase 1.5 起 `phase2_readiness` 从独立备注升为**必评项**，evaluation 需明确回答：此 bundle 进入 Phase 2 claim layer 是否会产生脏数据。

### 4.4 迁移观察

Phase 1.5 是过渡 phase，需对比观察：
- 同 source_type 在补丁前后的缺陷分布变化
- claim_candidate 引入是否改变 LLM 对 synthesis 的写法（应无负面影响）
- source_type 分型后 `source_hard_case` 缺陷是否下降

---

## 5. Phase 2 评测（Claim 层 + Archive 写入门）

Phase 2 主系统变更：引入 claim registry、claim matching 决策（新建 vs 挂载）、archive 11/6/8 写入、arena_candidate 审批。

### 5.1 评测范围扩展

评测从"单 bundle"扩展到"ingest 决策 + 跨 ingest 状态"：
- **per-ingest**：bundle（Phase 1 评测不变）+ matching 决策 + archive 写入
- **registry-level**：claim 状态演进（L3 轨迹观察首次真正有意义）

### 5.2 新增 L1 检查

- 每个 `claim_candidate` 必有 match decision：`new | attach_to:<claim_id>`
- `claim.supporting_evidence` 追加不改写（与上一版本 diff 检查）
- `claim.user_override` 非空时，自动计算结果不应覆盖其 status
- `claim.state_log` 完整（每次状态变化有记录）
- `conflicted` 状态存在时间不超过 90 天（forcing function 硬检查）
- archive 写入：fact 的 `dimension_hint` 与 archive 维度对应；没有孤儿 fact（未归档）

### 5.3 新增 L2 维度（per-ingest）

| 维度 | 评测内容 |
|---|---|
| `matching_accuracy` | candidate 挂到了正确的已有 claim？有无漏挂（应挂但新建，形成重复）或过挂（不该挂却挂了，污染 claim）？ |
| `claim_lifecycle_discipline` | confidence 升降与证据强度匹配？conflict resolution（strengthens/weakens/split/uncertain）选择合理？split 时原 claim 的 evidence 是否正确分配？ |

### 5.4 新增 L3 轨迹观察

定期跑（建议每 10 次 ingest 或每 2 周），覆盖：
- 重复 claim 检测：`claim_text` 高相似但未合并的候选对
- 证据方向分布：某 claim 证据方向混杂但仍 active 未进 conflicted（漏标 conflict）
- `review_by` 到期 claim 处理时效（>30 天未 review 的比例）
- Archive 覆盖缺口：某实体某维度长期无更新
- Arena candidate 通过率 / 合并率 / 拒绝率：过高过低都是信号（提名策略或审批策略需调）

### 5.5 Archive 写入评测

除 L1 硬检查，L2 补充一个维度：
- `archive_placement_quality`：fact 落到 archive 的维度是否最贴切？同一事实是否该同时写多维？

此维度可以合并进 `matching_accuracy`（都是"放对位置"的判断），实施时再定。

---

## 6. Phase 3 评测（叙事层 + Memo Flags）

Phase 3 主系统变更：archive 11/6/8 叙事段（claim-proposal 管线）、`supported_by_claims` 链接、segment status 流转、memo `auto_review_flags`。

### 6.1 新增 L1 检查

- 每个 `narrative_segment` 至少有一条 `supported_by_claims`
- 当 `supported_by_claims` 中有 claim 状态变化（active → weakened/retired/conflicted）时，segment.status 应自动进 `divergent`
- segment.trigger_log 完整（每次状态变化有记录 + commit_ref）
- memo `auto_review_flags[].superseded_by` 链不成环
- memo forcing function 规则执行：`last_reviewed > 180d + pending critical/significant` → status = `dormant`

### 6.2 新增 L2 维度

| 维度 | 评测内容 |
|---|---|
| `narrative_claim_consistency` | 叙事段内容与其引用 claims 是否一致？有无"引用了 claim 但段落结论与其相反"的飘移？ |
| `divergent_flagging_precision` | 该标 divergent 的段是否及时标了；不该标的段是否被误标 |
| `memo_flag_quality` | flag_level 分级是否合理；`superseded_by` dedup 是否准确；forcing function 触发是否过严/过松 |

### 6.3 新增 L3 轨迹观察

- 叙事段 `last_reviewed` 分布（长期未 review 的段落占比）
- claim 变化 → segment divergent → 重写完成的端到端时间分布
- memo dormant 转换率：如过高说明 flag 噪声大，用户 dismissal 跟不上；如过低说明 forcing function 过松
- 同一 dimension（如 moat）在多个 arena / company 之间的叙事一致性（跨实体系统性偏差）

---

## 7. Phase 4 评测（Events + Review Queue）

Phase 4 主系统变更：event adapter、matching engine、review queue + 优先级、Web UX。

### 7.1 新增 L1 检查

- event 必有 `occurred_at / source / linked_entities`（至少一个有效匹配）
- review_queue_item.prompt_package.affected_claims 必展开 claim 全文（不只是 id）
- resolution_ref 最终指向有效的 claim 状态变更或显式 `dismissed`
- queue item `status = pending` 超过 14 天 → 系统发 stale 提示（L1 层用规则判断）

### 7.2 新增 L2 维度

| 维度 | 评测内容 |
|---|---|
| `event_matching_precision` | event 匹配到的 claim 真相关？有无漏匹配（该触发 review 却没触发）？有无过匹配（不相关的 claim 被拉进来）？ |
| `queue_prioritization_quality` | 高优先级 item 是否真的高影响？低优先级是否系统性被延误？四个优先级维度权重是否需调？ |
| `prompt_package_actionability` | Claude 对话拿到 prompt_package 能直接上手，不用补足上下文？缺的上下文是哪类？ |

### 7.3 新增 L3 轨迹观察

- event → queue → resolution 端到端时延分布
- queue 堆积率：pending > 14 天的比例
- dismissed event 的后验：dismiss 一段时间后该实体是否出现重大变化（只观察，不判对错——dismissal 本就是用户决定）
- Adapter 健康度：每个 adapter 拉到的 event → 被匹配上的比例；长期低匹配率意味匹配规则或 adapter schema 需调

---

## 8. Phase 5+ 评测（Cross-LLM + 精炼）

### 8.1 Cross-LLM 交叉验证（L4）

用 GPT / Gemini 等独立跑 L2 维度评分，与 Claude 自评对比：
- 显著偏离维度 → 可能是 Claude 自评系统性盲区
- 持续一致维度 → 评测可信度提升

实施仍保持"用户对话里跑"原则：用户把同一 bundle + 评测 prompt 粘到不同模型的 CLI/Web，回写结果到 evaluation 记录。

### 8.2 评测 Drift 检测

- 同 bundle 不同时间用同模型跑 L2，结果应大致稳定；若漂移说明评测不可复现
- 评测 prompt 每次改动记 rationale 与 diff，对相同历史 bundle 重跑对比影响

### 8.3 规模化采样策略

当 ingest 速率上升，不再每次全 L2：
- L1 每次必跑
- L2 按 source_type 轮转采样（每 source_type 每 N 次必 L2）
- L3 按既定周期全量
- L4 每月 + 显著事件后

### 8.4 其他精炼项

adapter 扩充后的健康度基线、UX A/B 反馈、eval prompt 多版本比对、历史 evaluation 的 retrospective 重评等，属常规运维。

---

## 9. 评测驱动系统进步

### 9.1 缺陷聚类闭环

```
每次 evaluation → defects[]
  ↓
按 root_cause_hint 聚类
  ↓  prompt_gap / schema_gap / source_hard_case / matching_error
  ↓  narrative_drift / flag_noise / queue_prioritization_bias
  ↓
高频 → 当前 phase 补丁 或 触发下个 phase
  ↓
补丁后 → 新 ingest 的同类缺陷是否下降（retrospective 验证）
```

### 9.2 Phase 升级门槛

下个 phase 开始前，当前 phase 评测指标需稳定：
- L1 blocker 缺陷率 → 0
- L2 维度 `trend` 不呈持续 `weaker`
- L3 无结构性问题（系统性重复 claim / 系统性漏挂 / 系统性叙事飘移）

具体阈值各 phase 实施计划里定，不在概念设计锁死。

### 9.3 User override 作为 ground truth

用户在 Claude 对话里覆盖系统自动计算（`claim.user_override` / 手动改 segment.status / 手动 dismiss flag）是强信号：
- 某类 override 高频 → 对应自动计算逻辑或 prompt 需调
- override 方向一致 → 可参数化拟合用户偏好
- 此信号 Phase 2 起才有意义（Phase 1/1.5 没 override 对象）

---

## 10. 评测系统自身的可靠性

### 10.1 已知盲区

- **同模型自评偏好放大**：Claude 自评倾向于认可 Claude 产出的结构；对 reasoning_chain / counterpoints 这类维度偏宽松
- **Prompt 引导性**：问"coverage 如何"会让模型默认往 coverage 方向答；评测 prompt 需用开放式问法（"发现哪些缺陷"而非"打几分"）
- **样本量不足**：L3 轨迹在 Phase 1/1.5 无意义；Phase 2 前 10-20 次 ingest 的趋势噪声大于信号
- **评测成本非零**：完整 L2 对大 bundle 耗 token 显著，用户可能跳过；要接受"评测本身也要节流"

### 10.2 缓解策略

- Cross-LLM 从 Phase 5+ 正式引入（Phase 2-4 可临时手工跑一两次作为偏差校准）
- 评测 prompt 开放式、不暗示方向
- 早期 phase 以 L1 + 缺陷清单为主，`trend` 弱相对判断
- 评测 prompt + 规则集 git 版本化，每次改动记 rationale

### 10.3 评测不是自证清白

若评测结果长期无缺陷、无趋势变化，不是"系统完美"，更可能是"评测方法不够锋利"。定期反思评测 prompt 是否变得钝化是 cross-LLM 引入前的必要自检。

---

## 11. 文档关系

- 终局概念：[2026-04-29-ingest-endgame-design.md](./2026-04-29-ingest-endgame-design.md)
- Phase 1 bundle + 内建 QA：[2026-04-29-ingest-v2-phase1-review-bundle-design.md](./2026-04-29-ingest-v2-phase1-review-bundle-design.md)
- Insight-block 核心结构：[2026-04-28-insight-block-ingest-design.md](./2026-04-28-insight-block-ingest-design.md)
- 旧版评测 plan（单 phase 形态）：`plans/2026-04-29-ingest-quality-eval-design.md`——被本文件取代

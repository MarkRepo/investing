# Ingest 系统终局设计

> **Errata 2026-05-01**：本文原稿把 Phase 3 叙事层数字写成 "投资视图 8/6/9"。
> 这是草稿错误——从未列出过字段、也无代码实现。Phase 3A/B/C 实际写入的是 archive **11/6/8** (`app/config.py:30-62`)，
> 以 claim 驱动的 proposal 管线替换原 digest 写入路径。真正 decision-view 的 investment_lens (8/7/9) 见
> `research-os-design.md §10`，尚未实现。

**Status**: 终局概念设计，用于指导 Phase 演进规划，不直接实施
**Date**: 2026-04-29
**Supersedes for endgame vision**: 本文档取代
[2026-04-28-ingest-v2-research-os-design.md](./2026-04-28-ingest-v2-research-os-design.md) 中关于终局的讨论
**Phase 1 specification**: 不变，继续遵循
[2026-04-29-ingest-v2-phase1-review-bundle-design.md](./2026-04-29-ingest-v2-phase1-review-bundle-design.md)

---

## 1. 目标与非目标

### 1.1 目标

Ingest 系统的终局是一个**个人投资研究操作系统**：

- 每次 ingest 不只是存入知识，还触发对已有判断的强化 / 削弱
- 在时间轴上维护一组活的投资论点（claims），旧结论会随时间衰减或被新证据更新
- 主动监视外部事件（财报日、监管公告、关键行业数据点、新研报/新闻），推动研究议程
- 与用户协作演化——系统负责收集、匹配、调度、提示；用户（在 Claude 对话里）负责所有语义判断

### 1.2 非目标

- 不生成交易信号（买/卖/仓位建议）
- 不监视价格数据，不做估值触发式提醒
- 不自动写入 archive；所有写入经过用户确认
- 不让系统 Python 端调用 LLM API；所有语义判断发生在用户主动发起的 Claude 对话中
- 不替代投资论点 memo（用户私产），只做浅层反向追踪

---

## 2. 六个定调决策

终局设计建立在以下六个维度的明确选择上：

| 维度 | 决策 |
|---|---|
| 系统本质 | 个人投资研究操作系统（非笔记库、非交易助手） |
| 活性模型 | 主动监视 + 定期重评估 |
| 监视范围 | 事件驱动（财报、监管、行业数据点、新研报、新闻）；不监视价格 |
| 主观性 | 呈现变化 + 研究议程推荐；不涉交易建议 |
| 判断分工 | 系统做匹配 / 调度 / 打包；所有语义判断在 Claude 对话里 |
| 规模 | 5-10 个行业，50-100 个 arena，200-500 个公司；数十事件/天 |

---

## 3. 四层数据架构

```
┌──────────────────────────────────────────────────────────┐
│  决策层  投资论点 memo（原 V0，重命名）                    │
│         │ 用户私产；引用 narrative_refs + claim_refs       │
│         │ 浅层反向追踪：claim/叙事变化时系统只做标记         │
├──────────────────────────────────────────────────────────┤
│  叙事层  archive 11/6/8 (claim 驱动的 narrative proposal) │
│         │ 每段有 supported_by_claims + status + trigger_log │
│         │ claim 变化时段落自动标 divergent                 │
│         │ 内容永远由人写（含 Claude 对话里写），git 是内容史 │
├──────────────────────────────────────────────────────────┤
│  判断层  claims                                           │
│         │ 跨报告持久的原子命题，有显式生命周期              │
│         │ supporting_evidence 追加不改写                  │
│         │ related_claims 关系形成 DAG                     │
├──────────────────────────────────────────────────────────┤
│  证据层  insight_blocks / atomic_facts / synthesis /       │
│         per-report stage_gates                           │
│         │ per-report 不可变，append-only                  │
│         │ 按 (entity, dimension) 索引到 archive 11/6/8     │
└──────────────────────────────────────────────────────────┘
```

### 3.1 四层的角色分工

- **证据层**：回答"某份报告在某时间点说了什么"。历史事实，冻结不变
- **判断层**：回答"截至现在，我的观点状态如何"。可变，有生命周期
- **叙事层**：回答"这个行业/arena/公司现在的连贯叙述是什么"。用户主要阅读面
- **决策层**：回答"我对这家公司实际持什么立场"。用户私产

### 3.2 层间关系

- 证据层 **support** 判断层（blocks / facts → claims）
- 判断层 **back** 叙事层（claims → narrative segments）
- 叙事层 + 判断层 **被引用于** 决策层（thesis memo referenced）
- 反向：claim 状态变化 → 叙事段标 divergent → 若 thesis memo 引用了该 claim → memo 标 review

### 3.3 archive 11/6/8 的定位

Archive 是**证据层按 (entity, dimension) 的结构化索引**，不是阅读面。用户读的是 archive 叙事层（11/6/8，每维一个 .md），由 Phase 3 的 claim-proposal 管线写入。Archive 只在下钻具体证据时才被访问。

---

## 4. 第一等对象

### 4.1 claim（新，判断层核心）

```yaml
claim:
  claim_id
  claim_text                        # 单句命题，不是主题名
  scope_type                        # industry | arena | company | cross_cutting
  scope_ref
  claim_type                        # thesis | judgment | risk | scenario | gate_assessment
  dimension_hint                    # 对应叙事层的某维度（如 demand、moat、risks）
  
  # 当前状态
  status                            # active | review_due | weakened | strengthened | conflicted | retired
  confidence                        # high | medium_high | medium | medium_low | low
  as_of
  review_by                         # 时间衰减触发复审的截止
  
  # 证据台账（追加，不改写）
  supporting_evidence[]             # {source_id, block_ids, fact_ids, direction, weight, added_at, added_by}
  
  # 关系
  related_claims[]                  # {claim_id, relation}  relation: premise_for | corroborates | risk_to | contradicts
  
  # 变更 trail（审计用）
  state_log[]                       # {timestamp, from_status, to_status, trigger, trigger_ref}
  
  # 用户手动覆写（至高优先级）
  user_override                     # {status, note, overridden_at}
```

**规则**：

- `claim_text` 必须是单句命题
- `dimension_hint` 是叙事层对接的关键
- `supporting_evidence` 永远追加，矛盾证据也追加（方向不同）
- `user_override.status` 非空时覆盖所有自动计算

**Conflict resolution（conflicted 不是终态）**：

当 claim 进入 `conflicted`（证据方向矛盾且权重接近），用户在 Claude 对话里 review 后**必须**产出一种 resolution：

| resolution_type | 状态流转 | 说明 |
|---|---|---|
| `judge_strengthens` | conflicted → active（可能升 confidence） | 判定新证据方向主导，反向证据降权但保留在台账 |
| `judge_weakens` | conflicted → weakened | 判定反向证据主导 |
| `split_claim` | 原 claim → retired；新建两条独立 claim | 发现原 claim 实际混合了两个命题 |
| `keep_uncertain` | 保持 conflicted，追加 user_note | 无法判定，明确悬置 |

`split_claim` 时原 claim 的 `state_log` 记录 split 到的新 claim_ids；新 claim 继承原 claim 的 related_claims 和 supporting_evidence（按方向分配到对应新 claim）。

`keep_uncertain` 不是默认选项——系统不允许 conflict 无限期挂起，每 90 天 forcing 用户重新 review。

### 4.2 event（新，外部信号）

```yaml
event:
  event_id
  event_type                        # earnings_date | regulatory_filing | industry_data_point | new_report | news
  source                            # adapter 名
  occurred_at
  ingested_at
  
  # 轻量内容（不存 raw_payload）
  title
  summary_snippet                   # ≤ 500 字
  url                               # 用户要查原始自己去点
  
  # 匹配结果
  linked_entities[]                 # {entity_type, entity_ref, match_method, confidence}
  matched_claims[]                  # {claim_id, match_reason, suggested_direction: unknown}
  
  status                            # pending | queued | resolved | dismissed
  # 默认 90 天后自动归档/删除
```

### 4.3 review_queue_item（新，系统 backbone）

```yaml
review_queue_item:
  item_id
  created_at
  
  # 来源
  trigger_type                      # event_arrival | periodic_scan | ingest_completion
  trigger_refs                      # {event_ids, claim_ids, source_ids}
  
  # 优先级（系统计算）
  priority                          # high | medium | low
  priority_reasons[]                # 可读理由
  
  # Claude 对话准备
  prompt_package:
    task_type                       # event_evaluation | ingest_review | claim_audit
    affected_claims[]               # 展开 claim 全文
    supporting_context              # recent_events, linked_blocks, current_narrative
    suggested_prompt_template
  
  status                            # pending | in_progress | resolved | dismissed
  assigned_at
  resolved_at
  resolution_ref                    # 指向 Claude 对话回写的 JSON
```

### 4.4 arena_candidate（新，实体审批对象）

```yaml
arena_candidate:
  candidate_id
  proposed_slug
  proposed_name
  battleground_focus                # arena 的核心博弈焦点，必填
  core_participants[]
  proposed_related_industries[]
  source_block_ids[]
  first_seen_at
  seen_in_sources[]
  merge_suggestions[]               # 系统自动匹配到的已有 arena
  
  status                            # pending | approved | merged | rejected
  user_decision                     # {decision, merge_target, decided_at}
```

### 4.5 archive 叙事段 (frontmatter 延伸)

```yaml
narrative_segment:
  dimension                         # 对应 archive 11/6/8 的某一维（definition 不经 proposal 写）
  text                              # markdown / plain text
  supported_by_claims[]
  status                            # active | divergent | under_review
  last_written
  last_reviewed
  trigger_log[]                     # {timestamp, event, triggered_by_claims, claim_state_change, commit_ref}
  # 内容历史归 git，系统只记 trigger
```

### 4.6 投资论点 memo 反向引用（延伸 frontmatter）

```yaml
---
memo_id
company_ref
written_at
last_reviewed
status                              # active | dormant | archived
referenced_claims[]                 # 用户手动声明
referenced_narratives[]
auto_review_flags[]                 # {flag_level, ref_type, ref_id, reason, flagged_at, dismissed, superseded_by}
---
# 正文用户手写，系统不解析
```

**Flag 分级（由系统计算）**：

| flag_level | 触发条件 |
|---|---|
| `critical` | 引用的 claim 从 active → weakened/retired，或叙事段 status → divergent |
| `significant` | 引用的 claim confidence 跨 2 档变化（如 high → medium_low），或 claim 进入 conflicted |
| `informational` | 引用的 claim 追加证据但状态不变 |

**Flag 合并与批量操作**：

- 同一 claim 在 30 天内多次变化 → 新 flag 标记 `superseded_by` 指向更新的 flag，UI 只展示最新那条
- 批量 dismiss：用户可一次性 dismiss 某 memo 下所有 `informational` flag
- 展开视图：critical/significant 默认展开，informational 默认折叠

**Forcing function（防止堆积）**：

- memo.last_reviewed 超过 180 天且有 pending critical/significant flag → status 自动降为 `dormant`
- dormant memo 不再产生新 flag，UI 默认不展示，但保留 frontmatter 可用户显式 restore 回 active
- flag 创建超过 365 天未 dismiss 或处理 → 自动 archived（不在默认视图，可查询历史）

**关键**：系统只读 frontmatter，正文完全不解析（差异化观点 / 买入价 / kill conditions 保持用户私产）。

### 4.7 既有对象不变

insight_blocks / atomic_facts / synthesis / stage_gates（per-report 层）保持现有
[insight-block design](./2026-04-28-insight-block-ingest-design.md) 定义的结构。Archive 11/6/8 维度保持现有归档角色。

---

## 5. 三触发路径 + Review Queue

```
┌────────────┐   ┌─────────────┐   ┌──────────────────────┐
│  用户 ingest │   │  外部事件    │   │  定期扫描（cron）     │
└──────┬──────┘   └──────┬──────┘   └──────────┬───────────┘
       │                 │                      │
       ▼                 ▼                      ▼
     Matching Engine（纯 Python，不调 LLM API）
       │
       ▼
     Review Queue（系统核心 backbone）
       │
       ▼
     Claude 对话（语义判断全部在此发生）
       │
       ▼
     回写：claim 状态 / 叙事 divergent 标记 / memo flags
       │
       ▼
     级联：related_claims 进 review_due、下游叙事标 divergent
```

### 5.1 三种触发路径

- **ingest**：用户 ingest 新报告，系统从 synthesis 中提炼候选 claim 更新（新建或挂到已有 claim）
- **event**：外部 adapter 拉到事件，matching engine 按 entity / keyword / type 兼容性匹配到 claims
- **periodic scan**：每日扫描 review_by 到期 / 长期无证据 / 证据矛盾的 claims

### 5.2 Matching Engine 职责边界

- 只做规则匹配（entity 重合 + keyword 相关 + type 兼容）
- 只输出候选匹配和原因，**不判断方向**（方向由 Claude 对话决定）
- 有最低置信度阈值，低于阈值不入队（避免噪音）

### 5.3 优先级组成

Queue item 的优先级由四个维度综合：影响面（涉及多少 claim）+ 是否触及投资论点引用的实体 + 是否有高 confidence claim 被削弱 + 事件本身权重（监管 > 财报 > 新闻）。具体权重交付实施时调整。

### 5.4 Web 入口

- **Claim 看板**：按实体 / dimension / status 切片的 claim 状态视图
- **Review Queue**：按优先级排列的待处理项
- **实体页**：两者的投影（显示实体的叙事 + 相关 active claims + 实体相关 pending reviews）

三个入口互相跳转，不强制单一主入口。

---

## 6. 关键约束与原则

| 约束 | 落地方式 |
|---|---|
| LLM 判断在 Claude 对话里 | Python 只做 matching / scheduling / packaging / writeback |
| 证据不可变 | per-report 对象 append-only，ingest 后冻结 |
| 判断可追溯 | claim.supporting_evidence 追加式积累，不删历史证据 |
| 用户主权至上 | 所有级联只触发 review，不自动改状态；`user_override` 覆盖所有自动计算 |
| 叙事由人维护 | 系统只标 divergent，不自动重写；内容史归 git，系统只记 trigger_log |
| 隐私边界 | 投资论点 memo 浅层纳入（只读 frontmatter），正文不解析 |
| Arena 创建过审 | Claude 提候选 → 系统三层去重 → 用户审批 → 正式建立 |
| claim 粒度由 LLM 提炼 | ingest 时 Claude 从 synthesis 提炼，scope + dimension_hint 决定归属 |

---

## 7. 对当前 Phase 1 实现的影响

当前 Phase 1 review bundle 实现与终局的关键 gap：

1. **claim 对象未收集**：终局里 claim 是判断层核心，Phase 1 没有。compare / merge 没有命题层级比较的基础
2. **validity / as_of 未收集**：终局有时间衰减机制，Phase 1 bundle 里所有数据都是静态的，没有"何时生效、何时过期"
3. **source_type 分型未落地**：终局对医药 / 量子科技 / 低空经济等有专属字段需求，Phase 1 是通用 prompt
4. **schema_fit_review 是空壳**：终局需要 schema evolution 信号，但 Phase 1 既没结构也没 QA
5. **设计 / 实现字段集长期分叉**：insight_blocks / atomic_facts / stage_gates 若干设计字段 prompt 里没收集
6. **投资论点 memo 引用关系未打桩**：终局有浅层反向追踪；此 gap 可延到 Phase 3，因为 Phase 2 才有 claim registry 可引用

gap 1、2 是**演进断桥问题**——不现在埋下，Phase 2 启动时会有显著回炉成本；gap 3、4、5 是**质量债务**，不补也能运转但会长期累积；gap 6 是**自然延后**，Phase 3 前不需要。

---

## 8. 演进路径

分四 phase 走，每个 phase 独立可用；停在任意 phase 都是一个可用的系统，只是能力越来越弱。

### Phase 1.5：桥梁补丁（小改动，避免未来回炉）

**目标**：让 Phase 1 bundle 收集 Phase 2+ 需要的字段，不改语义。

- prompt 要求 Claude 从 synthesis 提炼 `claim_candidates[]`（每条含 claim_text、scope_type/scope_ref、claim_type、dimension_hint、supporting_block_ids、direction_on_source）
- bundle 每个 claim_candidate 带 as_of（等于 source_date）
- source_type 分型：prompt 里按 source_type 增加字段要求（医药 pipeline / 核聚变 stage_gate 等）
- schema_fit_review：要么结构化 + QA，要么删除
- 同步 design 和 prompt 字段集（消除文档债）

Phase 1.5 不建 claim 对象、不建 archive、不做 merge。只是让 bundle 里**多带一些字段备用**。

### Phase 2：Claim 层 + archive 写入门

- 引入 claim 对象 + claim registry
- Ingest 时从 bundle 的 `claim_candidates` 走匹配逻辑：新建 claim 或挂到已有 claim 作为新证据
- archive 11/6/8 接受 blocks / facts 写入（用户审批后）
- Arena candidate 审批流程
- 无叙事层、无事件监视

完成后系统具备：跨报告 claim 状态、evidence 台账、archive 档案库。用户能查"这条命题现在怎么样"，但没有连贯叙事阅读面。

### Phase 3：archive 叙事层的 claim 驱动写入管线 / 用 claim 驱动替换 digest 直写，产出 archive 11/6/8 的 Markdown (definition 维度除外)

- archive 叙事层初版叙事（手写或 Claude 对话辅助写）
- 每段标 supported_by_claims
- Claim 变化 → 叙事段自动标 divergent
- 叙事复写工作流（Claude 对话 + 用户确认）
- 投资论点 memo 浅层反向引用（frontmatter + auto_review_flags）

完成后系统具备：连贯叙事阅读面、叙事 divergent 提醒、memo 反向追踪。但仍需用户主动来用，没有外部事件驱动。

### Phase 4：Event 监视 + Review Queue

- 首批 event adapter（earnings calendar + 主要交易所披露 + 关键行业数据点）
- Matching engine + 优先级计算 + review queue
- Web UX 双入口
- 定期扫描 cron
- 扩充 adapter（新研报、新闻等）

完成后即终局系统：主动触发、被动阅读、用户判断。

### Phase 5+：精炼

adapter 扩充、UX 迭代、规模扩大时的性能调优、多 LLM 交叉评审（用户计划的 quality review 层）等，进入常规运维迭代，不再是结构性新建。

---

## 9. 不在本文档范围的事项

以下决策留给各 Phase 的实施计划，不在终局概念设计里钉死：

- 各 adapter 的具体实现（schema、认证、轮询频率）
- Matching engine 的具体评分算法和阈值
- 定期扫描的具体 cron 时间
- Review queue 的 UI 布局和交互细节
- claim 去重 / 合并的具体相似度算法
- 叙事 divergent 的级联传播深度限制
- Claude 对话 prompt 模板的具体措辞

这些属于"等实施阶段根据实际数据调"的问题，现在定死反而束缚。

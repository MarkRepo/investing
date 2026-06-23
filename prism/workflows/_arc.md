# 推荐弧线 + 不变量模型

> Prism B 模式的核心哲学：**系统由产物契约 + 不变量 + 领域知识定义，流程涌现而非规定。**
> `prism doctor` 报告哪些不变量未满足，LLM 自行决定顺序——可乱序、可批处理、可跳过已满足项。
> stage 标签保留在 topic.yaml 作 dashboard 兼容，但不再是必须顺序执行的状态机。

---

## 推荐弧线（LLM 自由可行任意顺序）

```
立题(I1) ──► 定向(I2) ──► 路线(I3) ──► 收料(I4) ◄──► 抽料(I5)
                                                              │
                                                              ▼
                                              合成(I6) ──► 评审(I7)
                                                              │
                                                     ┌────────┘
                                                     ▼
                                           监控/深挖循环(I8)
                                           (每次 daily-monitor 重入 I4→I6)
```

**收料⟺抽料互锁**：新料到手即可抽，不必等全部资料到齐。prescan 校准和 todo 收料并行。

---

## 弧线不变量（I1-I8）

| ID | 名称 | 必须成立（doctor 如何判定） | 强制方 |
|----|------|--------------------------|--------|
| I1 | 立题 | topic.yaml 存在；type∈{company,industry,arena,macro}；scope.question 非空；question>25字→search_terms 非空；company→ticker+short_name | **已强制** `create_topic` |
| I2 | 定向 | thesis_v0.md 存在且含 ≥1 个可证伪 K#；frontmatter 含 revised_after_prescan + data_freshness；decomposition_v0.md 存在 | 部分（`set_thesis` 校验 prescan_status；K# 可证伪性靠散文） |
| I3 | 路线 | roadmap.yaml 存在；每个 K# 被 ≥1 条 L4 狩猎 addresses 覆盖；search_keywords 非空 | `reverse_check_roadmap_coverage`（不 raise，写 todo） |
| I4 | 收料 | 每份 actionable inbox 资料已登记 manifest（addresses 非空 + rings）；`pending_unfetched_todos` 为空（无 unattempted/error）；`empty_undecided_todos` 为空 | 部分（`add_material` 校验；`set_stage` 阻断，见阶段 2） |
| I5 | 抽料 | 每份 actionable 资料 processed；对应 findings 笔记存在、frontmatter 合法、addresses 非空；findings 索引已重建 | 部分（processed 检查靠 `set_stage` gate） |
| I6 | 合成 | primer 存在且过门外人真懂门；case 覆盖 6 环全部硬落地；sidecar 存在；thesis_v1 为 Scheme C 全快照；缺口诚实标注 | 存在性/coverage 脚本 + 质量散文（`primer_quality_gate` / F17） |
| I7 | 评审 | critic_verdict 已定（approve/request-rewrite/request-more）；承重充分性横幅在 case 头 | **已强制** `set_critic_verdict` |
| I8 | 监控 | monitoring tier 已设（deep/watch/dormant）；所有 proposal 为 awaiting_confirm（绝不自动 confirm） | **已强制** `set_monitoring_tier` / `monitor.propose_flips` |

**横切不变量（FLOOR，恒成立）**：详见 `_floor.md`——
F1 web URL 真实命中 · F2 subagent 不写文件 · F3 研报必 vlm · F4 _extracted/_vlm 是 slug 级
· F5 todo 身份=文档非 K# · F6 gap 仅诊断 · F7 跨层借料必标来源 · F8 prescan 与 todo 无交集
· F9 H2 tier 救回 · F10 三态盖戳+R1/R2/R3 · F11 time_sensitivity+多市场口径

---

## `prism doctor` 用法

```bash
python3 -c "
from prism.scripts.doctor import doctor
import json
print(json.dumps(doctor('{slug}', '{variant}'), ensure_ascii=False, indent=2))
"
```

返回结构：
- `arc`：最高连续满足的不变量的**下一个**（当前瓶颈）
- `satisfied`：已满足的 I# 列表
- `unmet`：未满足的 I# + 具体 detail（哪几条 mat 未处理、哪个 K# 无覆盖等）
- `blockers`：unattempted/error todos + empty_undecided（来自 `pending_unfetched_todos` / `empty_undecided_todos`）
- `diagnostics`：`detect_gaps` 的精简（uncovered_ks / uncovered_ring_inputs / single_source / autofetch_debt）
- `prescan_status`：`get_current_prescan_status` 的值
- `suggested_next`：规则模板句（零 LLM），形如"抽 mat-a1/b2/c3 → 满足 I5 → 进合成 I6"
- `floor`：正在违反的 FLOOR 条目（若有）

**读报告后**：LLM 看 `unmet`/`blockers`/`diagnostics` 自行决定是补料、是抽料还是合成。doctor 不强制路径。

---

## 各能力说明

### I1 · 立题

**目标**：让系统知道"在研究什么"——type/scope/question 精确到可以生成覆盖槽。

LLM 特有判断：
- question 含糊（"研究 A 公司"）→ 追问用户聚焦命门（"从哪个维度切入？估值重估/业务转型/竞争格局？"）
- question >25 字时必须手动提炼 search_terms（≤15 字/条），否则后续 prescan 搜不准
- company type 必须确认 ticker（格式 `{EXCHANGE}_{CODE}`，如 `SZSE_001270`）

主动词：`create_topic` / `update_topic_scope`
Floor 关联：无直接关联，F11（多市场口径）在此初始化

---

### I2 · 定向

**目标**：thesis_v0 + prescan 定出"赌什么"，decomposition_v0 定出"命门拆解"。

LLM 特有判断：
- **训练知识 baseline（prescan 前先做，质量地基）**：写 thesis_v0 前，先把训练记忆里关于本 topic 的关键事实逐条列出，每条带**双标签**——置信度（高/中/低/uncertain）× time_sensitivity（静态/慢变/快变，见 `_floor.md` F11）——再自承认盲点。**硬规则：所有「快变 + 高/中置信」的 fact 必须在 prescan 有对应校准 query**（这是"自以为确定但极可能过时"、最易蒙蔽 thesis 的子集）；prescan 跑完回写「被推翻/验证/未校准」，被推翻的 fact 禁止再进 thesis_v0。落 `{variant}/baseline_knowledge.md`（后续 findings/case 用 `[fact-NN]` 引用，禁散文化重述）。company 额外标多市场口径（A/H/ADR，见 F11）。三类通用、company 最吃重（快变 fact 最多）。脚本：`has_baseline_knowledge` / `read_baseline_knowledge`
- **prescan 的目的是校准训练知识**，不是收料——prescan 完成前，thesis_v0 是训练知识初判（v0 强度仅凭训练记忆）；prescan 完成后，必须用校准事实修订 `revised_after_prescan` 字段
- K# 可证伪性检查：K# 不能是"未来不确定"（废话），必须有可观测触发条件。判断方法：能不能在 6 个月内验证？能=合格
- prescan_status=partial/failed 时，next_actions 首条提示需先完善 prescan；但 partial 情况下可继续（非硬 gate）
- decomposition_v0 的"命门"是本研究特有的核心不确定性（B 层），不是通用行业分析维度

主动词：`set_thesis`（v0）`set_decomposition`（v0）`run_prescan`
内嵌 prescan：`prism search`（见 F10 R1/R2/R3 + `_floor.md` F8）

---

### I3 · 路线

**目标**：roadmap.yaml 把每个 K# 展开成可执行狩猎清单（L1 假设→L2 证据类型→L3 资料来源→L4 具体 todo）。

LLM 特有判断：
- `reverse_check_roadmap_coverage`：每个 K# 必须有 ≥1 条 L4 todo addresses 它——无覆盖的 K# 直接告知用户"该 K# 还没有收料计划"
- L4 todo 的 `info_tier`（public/half_public/hard）决定收料努力强度，不决定是否跳过
- hard 的三类（管理层资本配置史/consensus/历史镜鉴）：告知用户需要显式排期，不默认能自动获取
- search_keywords 必须是 prescan 用得上的词（中文+英文各 ≥3 条，适用于你的 query 结构）

主动词：`create_roadmap` / `update_roadmap` / `reverse_check_roadmap_coverage`

---

### I4 · 收料

**目标**：inbox 里的资料全登记 manifest，所有 todo 都有 fetch_status（非 unattempted/error），empty 全决策。

LLM 特有判断：
- **合法 manifest 项**：addresses 非空（`add_material` 强制）；研报类需设 mineru_state=needs（F3）
- **todo 优先级判断**：P0 =不做无法进下一步；P1 = 严重影响 K# 强度；P2 = 锦上添花
- **fetch_status=empty → empty 硬闸门**（A1）：必须 AskUserQuestion 让用户逐条选 waived/will_collect，不得静默跳过
- **fetch_status=error**：必须重试（不算有效尝试，F10 R2），工具/网络故障不得降级为"公开没有"
- **H2 救回判断**（F9）：`register_web_search_batch` 返回 drop_ratio > 0.8 时，调 `extract_url_features` 对被丢弃 hits 做 tier 判定，高可信者带 `domain_tier='llm-judged-official'` 重新 register

主动词：`add_material`（强制 addresses+rings）`mark_todo_fetch`（三态盖戳）`prism search`（包装全流程）
Floor 关联：F1（URL 真实）F3（研报 vlm）F9（H2 救回）F10（三态+R1/R2/R3）

---

### I5 · 抽料

**目标**：每份 actionable 资料有对应 findings 笔记，frontmatter 合法，findings 索引已更新。

LLM 特有判断（精华）：
- **留具体数字，弃泛泛判断**：保留"毛利率从 42% 降到 37%"，删除"盈利能力有所下滑"
- **六维检查清单**（写完 findings 自查）：① 核心数字是否原文直引，② K# addresses 是否填了，③ 质量/偏差是否诚实（sell-side 报告≈bull 偏差），④ 冲突是否标 conflicts_with，⑤ rings 与 input_contract 对齐，⑥ 未回答问题是否列出（启动后续 deep_search）
- **冲突处理**：同一 K# 两份 findings 结论相悖 → 不合并、不删除任一方，而是在两份中都填 `conflicts_with`（见 `_contracts.md` §五），合成层再做仲裁
- **mineru 后 findings**：`full.md` 路径 `materials/{stem}_vlm/full.md`；只写一份 findings（slug 级），findings 笔记本身放 `{variant}/outputs/`（见 F4）
- **单料不足可 dispatch 深挖**：单份资料填不满关键 K#，可 dispatch subagent 深挖单份原文（≤1 层嵌套）；subagent 只产 markdown 到 final message，主 agent 落盘（F2 强制）
- **findings 索引**：所有 findings 落盘后调 `build_findings_index`（见附录 A）

主动词：`mark_processed` + Write findings + `build_findings_index`
Floor 关联：F2（subagent 不写文件）F3（研报 vlm）F4（路径隔离）F7（跨层借料标来源）

---

### I6 · 合成

**目标**：primer + case + sidecar 三件套齐全；6 环覆盖；thesis_v1 全快照；缺口诚实标注。

LLM 特有判断（精华）：
- **primer-first**：case 之前先写 primer（独立于投资判断的领域入门）；primer 过"门外人真懂门"（F17 软门：deep 研究 char_count≥6000 + has_controversy + has_selfcheck）后再写 case
- **来源三分层**（见 `_contracts.md` §九）：训练知识 / 本研究 findings / 本研究特色判断——case 里这三类必须可辨认，不混用
- **time_sensitivity**（F11）：快变 fact（价格/库存/汇率/利率）必须有实收料支撑；慢变 fact 标"训练知识估算"；静态 fact 不标
- **gap 诊断诚实标注**（F6）：`detect_gaps` 返回红灯缺口，在 case 第 0 节"数据缺口"写诚实注解；gap 存在不阻断合成，但不能不写
- **6 环全覆盖 checklist**（快速 self-check）：
  - ①理解：有生意模式/护城河/财务弧线 → ②定价锚：有估值反推/consensus 对比 → ③WWHTBT：有若干可观测必要条件 → ④下注：company=EV加总/industry=arena 6维/arena=peer横比 → ⑤证伪：有 K# 信号+历史镜鉴 → ⑥行动：有明确 buy_box/tier/shortlist
- **thesis_v1 全快照**：见 `_contracts.md` §七，11 段式，禁"见 v0"引用；写完调 `set_thesis(..., version=1)`
- **sidecar 写完后**：调 `set_output_status(output_key='07_decision_kit', status='fresh')`；dashboard 只读 sidecar，sidecar 字段名不得改（见 `_contracts.md` §六）
- **incremental rewrite 判定**：B 轴命门有重大修订（命门变化≥2个/置信度跳动≥2档）时触发 decomposition_v2 重拆，不在旧版上打补丁

主动词：Write primer/case/sidecar + `set_output_status` + `set_thesis`（v1）+ `set_decomposition`（v1）
Floor 关联：F6（gap 诊断）F7（跨层借料）F11（time_sensitivity）
参考：`_knowledge.md`（6环/估值模型/宏观/primer 规约）`_contracts.md`（sidecar schema）

---

### I7 · 评审

**目标**：独立 critic 对 case 给出 verdict，承重充分性横幅写进 case 头部。

LLM 特有判断：
- **独立 critic**：不能自己既写 case 又做 critic——必须 dispatch 干净上下文 subagent 以对抗视角重读。**喂成稿结论 + 硬数据，瞒 thesis 理由链/findings 叙事/primer**（独立性的关键）；押与作者相反方向（别只做空）。dispatch 模板见 `prism/prompts/critic_independent.md`
- **prescan 门禁**：`get_current_prescan_status`=`failed` → verdict **封顶 `request-more`（不许 `approve`）**，且把时敏论断按脆弱加重攻击；`partial` → 反方攻击起点须含 baseline"仍未校准"清单
- **承重充分性横幅**：case 头必须有"当前最重要的未回答问题/数据缺口 + 承重充分性（够/单线承重/不足）"横幅；**不足 不得配 approve，单线承重 最高 request-more**；critic 通过不删横幅，保留至下次 daily-monitor 覆盖
- **verdict 三选一**：`approve`（case 可用）/ `request-rewrite`（重大逻辑漏洞，case 须返工，调 `set_output_status` 标目标 output `stale`）/ `request-more`（有关键数据缺口，回 I4 补料后再评）
- **request-more 处理**：critic 指出缺口 → 回 I4（补料）→ 抽料 → 重写相关 case 段 → 再 critic；不是整份重写。缺口可 web-search 兜到的先兜一轮再定 verdict
- **对话历史 critic**：若合成在当前 session，critic 必须"假设自己刚读完 case，之前没看写作过程"（避免确认偏差）
- **suggested_drilldowns 回流**：写完 verdict 后扫 gap report——`thin_evidence`≥1 或承重判"单线承重" → 调 `set_suggested_drilldowns(mode='append')`（不覆盖合成阶段的）把薄弱 K# 翻成深挖建议

主动词：`set_critic_verdict`（自动 set_stage + 标 rewrite_keys stale）+ Write case（更新承重横幅）+（按需）`set_suggested_drilldowns`
Prompt ref：`prism/prompts/critic_independent.md` · `prism/prompts/output_quality_rubric.md`

---

### I8 · 监控

**目标**：monitoring tier 已设，所有催化剂事件进 living_feed，所有 flip 提案人工 confirm。

LLM 特有判断：
- **tier 选择判断**：deep = 持有/重点研究；watch = 跟踪但未建仓；dormant = 历史存档（无需定期更新）
- **living_feed 更新**：每次 daily-monitor 写入 `08_living_feed.md`——新事件 + sidecar signpost 命中情况；time_sensitivity 快变 fact 必须用实收料盖戳（F11）
- **flip 机制**：`monitor.propose_flips`产出"建议变更"（monitoring_tier 升降 / K# 状态更新），**绝对不自动 confirm**；必须 AskUserQuestion 让用户确认；`topic.yaml.pending_thesis_review` 非空时也触发 AskUserQuestion
- **深挖回路**：monitoring 发现 K# 信号命中 → 可触发 drilldown（回到 I4 补料 → I5 抽料 → 局部 I6 更新）；不是全盘重跑，只更新受影响章节和 sidecar signpost
- **daily-monitor 重入**：`prescan_status` 每次 monitor 刷新（校准快变 fact）；thesis_v1 在信号触发后升为 thesis_v2（Scheme C 全快照升版，不打补丁）

**daily-monitor CLI（零 LLM 提案，绝不 confirm）**：
```bash
python -m prism.scripts.monitor scan [14]    # scan_due_events → {due_signposts, due_kills, price_breach, macro_due, macro_alert, ...}
python -m prism.scripts.monitor price [14]   # propose_price_breaches（零 LLM）
python -m prism.scripts.monitor macro [14]   # propose_macro_updates（零 LLM，macro topic 的事件/行情指标到期）
```
- `macro_due`（事件/描述型到期）/ `macro_alert`（行情型 alert_series 越带）两桶走**零 LLM 路径**：`propose_macro_updates` 机械写 `kind=macro_input` proposal（信息型，预写 living_feed 文案）。
- `monitor.confirm_flip(id)` 仅在用户 web 端点头时调（零 LLM 机械回写 sidecar + append living_feed + 注册证据）；`discard_flip(id)` 丢弃。**proposal 一律 `awaiting_confirm`，确认永远是用户**。

**macro 闭环重估（macro topic 改版必做，非可选）**：每版 regime_read 走存快照→可证伪预测→战绩对账→体制变盖持仓戳的闭环（`eval_snapshot.record_evaluation` 含可证伪 `expected` 硬校验 / `eval_score.edge_ledger` 浮降级候选 / `macro_xcut.apply_holding_staleness` 联动持仓 / `coverage_gaps` 持仓全覆盖）。纪律与字段见 `_knowledge.md §三·闭环重估`。`reeval_pending` 戳由 monitor 盖、`record_evaluation` 落新版后清。

主动词：`set_monitoring_tier` + `monitor.propose_flips` / `propose_macro_updates` / `confirm_flip` + Write living_feed + （必要时）`set_thesis`（v2+）+ （macro 重估）`record_evaluation` / `apply_holding_staleness`
Floor 关联：F11（快变 fact 须实收料）

---

### 深挖（drilldown · I8 循环内的专项研究）

**目标**：对某个具体问题做专项深度研究，产出专题笔记 `outputs/drilldown_{timestamp}_{keyword}.md`。触发：用户说「深挖 {slug} 的 {问题}」或监控信号命中。

LLM 特有判断：
- **深度分级（quick vs load-bearing）**：
  - `quick`：用户好奇/纯背景探索，不承载 thesis 承重
  - `load-bearing`：深挖问题来自 `suggested_drilldowns`（`source=capped_decomposition` / `critic_weak_k`）/ 攻 capped 命门 / 补 thin_evidence K# / 结论可能动摇 thesis
  - 判定时机：来自 `suggested_drilldowns` 默认 load-bearing；用户自发默认 quick，但问一句"这个结论会影响 thesis 吗？"；写进笔记 frontmatter `weight: quick|load-bearing`
- **load-bearing 专属**：必须回答"命门解没解决"，并闭环 `resolve_suggested_drilldown`；结论动摇 thesis 时回 I6 局部更新（不全盘重跑，只改受影响章节 + sidecar signpost）+ 升 thesis_v{N+1}（Scheme C 全快照）
- 问题不够具体 → AskUserQuestion 细化；多子问题深挖可 dispatch sub-agent（≤1 层，见 `prism/prompts/deep_search.md`）

主动词：Write drilldown 笔记 + `set_suggested_drilldowns` / `resolve_suggested_drilldown` + （动摇 thesis 时）`set_thesis`
Floor 关联：F1（URL 真实）F2（subagent 不写文件）

---

## 能力地图（动词 → 不变量 → 数据流）

```
┌─────────────────────────────────────────────────────────────────────┐
│  create_topic / update_topic_scope          → I1 立题              │
│  set_thesis(v0) + set_decomposition(v0)     → I2 定向              │
│    └─ prism search（prescan）                  (F8: 不闭 todo)     │
│  create_roadmap + reverse_check_roadmap     → I3 路线              │
│  add_material + mark_todo_fetch + prism search → I4 收料           │
│    └─ H2 rescue (F9) + empty 硬闸门 (A1)                           │
│  mark_processed + Write findings + build_findings_index → I5 抽料  │
│    └─ subagent final_msg → 主 agent Write (F2)                      │
│  Write primer/case/sidecar + set_output_status → I6 合成           │
│    └─ set_thesis(v1) Scheme C (§七)                                 │
│  set_critic_verdict                         → I7 评审              │
│  set_monitoring_tier + propose_flips        → I8 监控              │
└─────────────────────────────────────────────────────────────────────┘
                    ↑ doctor 随时可调，报告当前弧线位置
```

---

## doctor 报告样例（可直接 paste 给 LLM）

```json
{
  "topic": {"slug": "荣昌生物-company", "variant": "opus4.8", "type": "company"},
  "arc": "I5",
  "satisfied": ["I1", "I2", "I3", "I4"],
  "unmet": [
    {"id": "I5", "detail": "6/9 已处理；3 未抽：mat-a1(2023AR), mat-b2(摩根研报), mat-c3(访谈纪要)"}
  ],
  "blockers": [],
  "diagnostics": {
    "uncovered_ks": [],
    "uncovered_ring_inputs": ["historical-mirror"],
    "single_source": ["consensus"],
    "autofetch_debt": 0
  },
  "prescan_status": "full",
  "suggested_next": "抽 mat-a1/b2/c3（3 份）→ 满足 I5 → 进合成 I6",
  "floor": []
}
```

LLM 读到 `arc: "I5"` → 知道当前瓶颈是抽料。`uncovered_ring_inputs: ["historical-mirror"]` → 知道合成前还缺历史镜鉴料，可以提前排 todo 或在合成里诚实标 gap。

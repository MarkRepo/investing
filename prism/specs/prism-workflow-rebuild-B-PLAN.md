# Prism Workflow 重构执行计划 · 方案 B（doctor 驱动 / 护栏内自由）

> **本计划是上下文无关、自满足的。** 执行者（可能是 Sonnet / GLM 等任意模型）只需读本文件
> + 文中点名的源文件，即可完成重构，无需任何对话历史。
> 北极星设计见 `prism/specs/prism-workflow-rebuild-B.md`；本文件是其可执行展开。
>
> **总原则**：能力不变（中间数据/状态/web/产出全保留）、质量不降、复杂度最低、LLM 自由最大。
> 落点 workflows/ 从 ~6655 行降到 ~1500-1800 行；真正的目标是把 LLM 要同时拿住的概念从
> 「8 套 stage 流程 × N 步」塌成「**动词 + doctor + 不变量**」。

---

## 第 0 部分：执行者必读的背景（自包含）

Prism 是一个 LLM 驱动的投资研究系统，对 company/industry/arena/macro 四类标的做结构化研究，
产出"决策链 case + sidecar + primer"。数据布局：

```
prism/topics/{slug}/
  topic.yaml          主状态文件（见附录 B 完整字段）
  manifest.yaml       资料清单（见附录 C）
  inbox/              用户放/脚本下载的原始资料
  materials/          slug 级共享：_extracted.md(年报) / {stem}_vlm/full.md(研报 mineru 产物)
  {variant}/          按模型变体隔离（如 opus4.8）
    thesis_v{N}.md / decomposition_v{N}.md
    outputs/          00_primer / c_investment_case 等 / sidecar yaml / 08_living_feed
prism/scripts/        Python，纯 CRUD/状态/校验，零 LLM（见附录 A 函数签名）
prism/workflows/      ← 本次重构对象
```

**现状问题**：`workflows/` 是 8 份 stage 程序文档（00..07）+ 一堆共享片段，共 ~6655 行。大量内容是
①手把手脚本演示 ②跨文件复制粘贴 ③教 LLM 通用技能。这些是 agent 理解成本的来源，但不是系统能力。

**重构哲学**：系统由"产物契约 + 不变量 + 领域知识"定义，**流程涌现而非规定**。
- 脚本管"对不对"（动词自带校验，非法状态 raise）。
- 文档只剩"为什么这么设计"（领域知识）+ 无法机械化的底线。
- "怎么做"全交给 LLM：路径、顺序、怎么搜、怎么读、何时开 subagent。
- stage 从"必须照走的状态机"变成"带强制退出不变量的推荐弧线"。LLM 看 `prism doctor` 的报告，
  自己决定下一步——可乱序、可批处理、可跳过已满足项。

**张力声明（重要）**：最大自由 ≠ 无约束。附录 D 的血教训（F1-F11）是当年放任自由踩坑换来的质量
脚手架，**该刚的用脚本 guard 刚到底**。B = 护栏内自由。执行本计划时，凡涉及删除约束，先确认它
是否在附录 D；在附录 D 的，只能"从散文搬进 guard/不变量"，**不能删除**。

---

## 第 1 部分：目标文件架构

重构后 `workflows/` 只有 4 份文档 + 退役一批：

| 新文件 | 目标行数 | 内容 | 主要来源 |
|--------|---------|------|---------|
| `_contracts.md` | ~250 | 产物契约单源：topic.yaml / manifest / findings frontmatter / 各 sidecar schema / 编号体系(K#/R#/F#/KILL) / input_contract 8·6·5 表 | 现 `_reading_guide_canonical.md` + `_input_contract.md` + 散落各处的 frontmatter/schema 定义 + 附录 B/C |
| `_knowledge.md` | ~700 | 不可压投资 IP：6 环决策链(参数化一份+三类差异) / 8 估值模型 / 宏观四层+机制纠错八条 / primer 规约 / 来源分层+depth 降级 | `04-synthesize/` 全部文件**逐字搬运+去重** |
| `_floor.md` | ~150 | 血教训不变量(F1-F11)。能进 guard 的标注"已下沉脚本"，无法机械化的留散文 | 附录 D |
| `_arc.md` | ~150 | 推荐弧线 + I1..I8 退出不变量 + 每个"能力"一段话(立题/路线/收料/抽料/合成/评审/监控/深挖) | 第 2 部分 + 各 stage 文档的"领域判断"精华 |

**退役（移动内容后删除或存档为 `.bak`）**：`00-research-topic.md` `01-build-roadmap.md`
`02-gather-materials.md` `03-extract-findings.md` `04-synthesize/*`（内容搬进 _knowledge）
`05-critic-review.md` `06-daily-monitor.md` `07-drilldown.md` `_autofetch_protocol.md`
`_web_prescan_shared.md`（流程进 `prism search` 动词）`_web_search_routing.md`
`_web_search_aggregation.md` `_baseline_knowledge.md` `_reading_guide_canonical.md`
`_subagent_deep_search.md` `_subagent_fetch_material.md` `_input_contract.md`。

> ⚠️ SKILL.md（`.claude/skills/prism/SKILL.md`）的路由表引用了这些文件路径，**最后一步必须同步更新**
> （见第 5 部分阶段 6）。

---

## 第 2 部分：不变量模型（新骨架，替代 stage 程序）

这是整个方案的核心。stage 不再是程序，而是"必须成立的不变量"。`prism doctor` 报告哪些未满足。

### 弧线不变量（推荐顺序；LLM 可任意可行顺序满足）

| ID | 名称 | 必须成立（doctor 如何判定） | 强制方 |
|----|------|--------------------------|--------|
| I1 | 立题 | topic.yaml 存在；type∈{company,industry,arena,macro}；scope.question 非空；question>25字→search_terms 非空；company→ticker+short_name | **已强制** `create_topic`（附录 A.guards） |
| I2 | 定向 | thesis_v0.md 存在且含 ≥1 个可证伪 K#；frontmatter 含 revised_after_prescan + data_freshness；decomposition_v0.md 存在 | 部分（`set_thesis` 校验 prescan_status；K# 可证伪性靠散文） |
| I3 | 路线 | roadmap.yaml 存在；每个 K# 被 ≥1 条 L4 狩猎 addresses 覆盖；search_keywords 非空 | `reverse_check_roadmap_coverage`（不 raise，写 todo） |
| I4 | 收料 | 每份 actionable inbox 资料已登记 manifest（addresses 非空 + rings）；`pending_unfetched_todos` 为空（无 unattempted/error）；`empty_undecided_todos` 为空 | 部分（`add_material` 校验 addresses 非空；set_stage 阻断需补，见阶段 2） |
| I5 | 抽料 | 每份 actionable 资料 processed；对应 findings 笔记存在、frontmatter 合法、addresses 非空；findings 索引已重建 | 部分（`add_material` frontmatter 约定；processed 检查靠 set_stage gate） |
| I6 | 合成 | primer 存在且过"门外人真懂"门(primer_quality_gate)；case 覆盖 6 环全部硬落地；对应 sidecar 存在；thesis_v1 为 Scheme C 全快照；来源分层已标；缺口诚实标注 | 存在性/coverage 脚本 + 质量散文（附录 A.primer_quality_gate / set_output_status F17） |
| I7 | 评审 | critic_verdict 已定(approve/request-rewrite/request-more)；承重充分性横幅在 case 头 | **已强制** `set_critic_verdict` |
| I8 | 监控 | monitoring tier 已设(deep/watch/dormant)；所有 proposal 为 awaiting_confirm（绝不自动 confirm） | **已强制** `set_monitoring_tier` / monitor.propose_flips |

### 横切不变量（FLOOR，恒成立，详见附录 D）

F1 web finding 必来自真实 hit · F2 subagent 不写文件 · F3 研报必 vlm · F4 _extracted/_vlm 是 slug 级
· F5 todo 身份=文档非 K# · F6 gap 是诊断非 gate · F7 跨层借料必标来源 · F8 prescan 与 todo 无交集
· F9 H2 tier 救回 · F10 三态盖戳+R1/R2/R3 · F11 time_sensitivity+多市场口径。

### 关键洞察：doctor 不需要新逻辑

`prism doctor` 是**现有只读函数的纯组合**（见附录 A）：
- I1 → `read_topic` 存在性 + type/question/ticker 字段
- I2 → thesis 文件存在 + frontmatter 字段 + `read_topic.thesis` 元数据
- I3 → roadmap.yaml 存在 + `reverse_check_roadmap_coverage`
- I4 → `manifest.read_manifest` 全登记 + `pending_unfetched_todos` + `empty_undecided_todos`
- I5 → `manifest.list_unprocessed`（空=全处理）+ findings 索引文件存在
- I6 → `read_topic.outputs_state[*].status` + `primer_quality_gate`
- I7 → `read_topic.critic_verdict`
- I8 → `read_topic.monitoring.tier`
- 非阻断诊断 → `gap_detector.detect_gaps`（附录 A.5 返回结构）
- prescan 门禁 → `get_current_prescan_status`

**这证明 B 可行**：把"8 套程序"换成"doctor 组合现有读函数 + 一张不变量表"，零新业务逻辑。

---

## 第 3 部分：源→目标内容映射（执行者照此搬运）

> **铁律：知识地板逐字搬运，不重写。** _knowledge.md 与 _contracts.md 的内容应从源文件**整段复制**，
> 仅做去重（多处重复的，留一处，其余改为"见 _knowledge.md §X"）。**禁止改写投资框架/估值模型/
> 机制纠错的实质表述**——弱模型重写会引入质量损失。

### → `_contracts.md`
| 目标章节 | 从哪搬 |
|---------|--------|
| 编号体系 K#/R#/F#/KILL/±10 刻度/WWHTBT | `_reading_guide_canonical.md` 全文相关段 |
| input_contract 8·6·5 表 | `_input_contract.md`（已是纯表，整体搬） |
| topic.yaml 字段 schema | 附录 B（本文件） |
| manifest.yaml 字段 schema | 附录 C（本文件） |
| findings frontmatter schema | `03-extract-findings.md` 第 422-434 行（mat_id/filename/source_type/extracted/quality/bias/addresses/rings/conflicts_with/conflict_note） |
| 各 sidecar schema（decision_kit/industry_to_arenas/peer_matrix/transmission_map） | `04-synthesize/_decision_kit_spec.md` / `_arena_select_spec.md` / `_peer_matrix_spec.md` / `_macro_regime.md` 的 schema 段 + `prism/templates/*.tmpl` |
| thesis_v1 Scheme C 十一段 + decomposition_v1 | `04-synthesize/_shared.md` 的 thesis_v1 段 |

### → `_knowledge.md`（最大去重杠杆）
| 目标章节 | 从哪搬 + 去重方式 |
|---------|------------------|
| 6 环决策链（参数化一份） | 对比 `_company_case.md` / `_industry_funnel.md` / `_arena_funnel.md` 三份的环①..⑥，**抽出公共骨架写一份**，三类只列差异。已知差异：环④ company=期望收益EV加总 / industry=arena 6维评分 / arena=peer 横比矩阵；环⑥ company=买入框+仓位档 / industry=三档 arena 分流 / arena=三档 peer shortlist。其余环大体同构。 |
| macro 四层因果链 + 机制纠错八条 + 四传导渠道 | `_macro_regime.md`，**逐字搬运**（macro 独有，不与三类共享） |
| 8 估值模型 | `_valuation_models.md`，**整体搬**（纯工具库，零删） |
| primer 规约（primer-first / 门外人真懂门 / 与 case 分工 / 来源分层三类 / depth 降级） | `00-primer.md` + 三路径 §2/§3.3 重复段**合并为一份** |
| arena 6维评分口径 / peer 财务脊柱选择 | `_arena_select_spec.md` / `_peer_matrix_spec.md` 的知识段（schema 归 _contracts，知识归这里） |

### → `_floor.md`
整表从附录 D 搬。每条标注：原文要点 + 出处 + 为什么(踩坑) + 当前强制方式 + 是否已下沉 guard。

### → `_arc.md`
- I1..I8 不变量表（从第 2 部分搬）。
- 每个"能力"一段话（目标 + LLM 特有判断 + 用哪个动词 + ref 哪条 floor）。"LLM 特有判断"的精华从对应
  旧 stage 文档的【C 领域知识】段提炼，例如抽料的"留具体数字弃泛泛判断 + 六维检查清单 + 冲突即搜单份≤3
  + 单料不足可 dispatch 深挖≤1"。
- 推荐弧线图：立题→定向→路线→收料↔抽料→合成→评审→(监控/深挖循环)。

---

## 第 4 部分：脚本改动（薄包装，纯增量，现有 ~70 函数不动）

> 最小必要改动只有 **2 个新动词 + 3 处 guard 增强**。其余动词 = 现有函数直接用，文档只 ref。

### 新动词 1：`prism doctor`（keystone，新建 `prism/scripts/doctor.py`）
```
python3 -c "from prism.scripts.doctor import doctor; import json; print(json.dumps(doctor('{slug}','{variant}'), ensure_ascii=False, indent=2))"
```
**实现**：纯组合附录 A 的只读函数，按第 2 部分映射逐一判定 I1..I8，返回：
```python
{
  "topic": {"slug","variant","type"},
  "arc": "I5",                      # 最高连续满足的不变量的下一个
  "satisfied": ["I1","I2","I3","I4"],
  "unmet": [{"id":"I5","detail":"6/9 processed; 3 未抽: mat-a1,mat-b2,mat-c3"}],
  "blockers": [],                   # unattempted/error todos, empty_undecided（来自 pending_unfetched_todos / empty_undecided_todos）
  "diagnostics": {...},             # detect_gaps 的精简（uncovered_ks / uncovered_ring_inputs / single_source / autofetch_debt）
  "prescan_status": "full",         # get_current_prescan_status
  "suggested_next": "抽 mat-a1/b2/c3 → 满足 I5 → 进合成 I6",
  "floor": ["研报必 vlm","subagent 不写文件","gap 仅诊断"]
}
```
零 LLM。`suggested_next` 用简单规则（第一个 unmet 的 ID → 模板句）。

### 新动词 2：`prism search`（新建 wrapper，替代 383 行 prescan SOP）
包装 `web_prescan.build_search_queries` + `register_web_search_batch` + `log_search_skipped` +
`check_prescan_health`（签名见附录 A.6）。一条命令完成"枚举覆盖槽→搜→落盘→去重→健康检查"，
主 agent 只需提供 query 措辞（领域判断）。H2 救回（F9）保留：返回 `drop_ratio`/`dropped_hits`，
主 agent 判 tier 后带 `domain_tier='llm-judged-official'` 二次 register。

### Guard 增强（在现有函数内嵌已有逻辑，不新建）
1. **`set_stage`**：内嵌 `pending_unfetched_todos` 非空（unattempted/error）则 raise（落地 I4 阻断）。
   现逻辑散在 02 Step6 / 03 Step0a 的脚本块里，搬进函数。
2. **`add_material`**：addresses 为空时 raise（已部分有"现有非空则不许清空"保护，扩为"actionable
   资料必带 addresses"）。
3. **`update_user_todo_status`**：拒绝无 `task` 子串的批量闭环（落地 F5：禁 K# 自动撮合）。

### 可选动词（非必需，现有 setter 已够；列此供后续）
`prism finding register`(=mark_processed+build_findings_index) / `prism material add`(=add_material) /
`prism output mark`(=set_output_status)。**阶段 3 试点不依赖这些**，主 agent 用 Write 落盘 + 直接调
现有 setter 即可。

### prompt 库
独立反方 / critic / deep-search 的 prompt 模板移到 `prism/prompts/`（已有 analyst_voice.md /
output_quality_rubric.md）。_arc.md 只 ref 文件名。从 `05-critic-review.md` Step2 / `_subagent_deep_search.md` 提取原文。

---

## 第 5 部分：分阶段执行（受控，逐阶段验收）

每阶段独立验收；任一阶段验收不过→该部分回退（见第 7 部分）。**全程旧文件先存 `.bak` 不删**，
该阶段双关验收通过后才删 `.bak`。

### 阶段 0：准备（零风险）
- 读本计划全部附录 + 第 3 部分点名的所有源文件，建立全局认识。
- 确认 git 干净；为本次重构开分支（如 `prism-workflow-rebuild-b`）。

### 阶段 1：落共享层（不碰旧 workflow，纯新增）
- 写 `_contracts.md`（按第 3 部分映射，schema 逐字搬）。
- 写 `_knowledge.md`（6 环参数化去重；macro/估值逐字搬）。
- 写 `_floor.md`（附录 D 全表）。
- 写 `_arc.md`（不变量表 + 能力段 + 弧线图）。
- **验收 1**：人读四份文件，确认 (a) 三类 6 环差异完整无丢 (b) 估值模型/机制纠错八条**逐字**在
  (c) 所有附录 B/C/D 的字段/条文有落点 (d) 无投资框架被改写。✅ 才进阶段 2。

### 阶段 2：最小动词 + guard（脚本，纯增量）
- 新建 `doctor.py`（第 4 部分动词 1）。
- 新建 `search` wrapper（第 4 部分动词 2）。
- 增强 set_stage / add_material / update_user_todo_status 三处 guard。
- **验收 2**：跑现有测试套件 `pytest prism/`（确认未破坏现有 ~70 函数）；对一个真实 slug 跑
  `prism doctor`，输出的 satisfied/unmet/diagnostics 与人工核对 topic.yaml 一致。

### 阶段 3：03（抽料 I5）试点 — 验证 doctor 驱动
- 把 `00..03` 旧文档存 `.bak`。
- 用 doctor + `_arc.md` 抽料段 + `_floor.md` 驱动，对一个**未完成抽料**的真实 slug 跑：
  `prism doctor` 看 unmet=I5 → LLM 自行抽料 → 调现有 setter 落盘 → 再 `doctor` 确认 I5 满足。
- **验收 3（双关，最关键）**：
  - **数据契约**：抽料前后 `read_topic` + `outputs/` 文件树 + manifest dump，与"用旧 03 文档跑"
    的结果结构 **diff 为空**（字段/路径/状态机一致）。
  - **端到端质量**：取一个已有完整 case 的 slug，重跑 I5→I6→I7，核对：6 环硬落地齐全、来源分层
    标注在、findings frontmatter 合法、critic verdict + 承重横幅照常、**无静默丢料、无编造 URL**
    （抽检 web findings 的 URL 真实性）、F1-F11 无违反。
  - 通过 → 删 `00..03.bak`，B 模式成立，进阶段 4。**不过 → 阶段 3 回退方案 A**（保留薄程序版 03）。

### 阶段 4：合成（I6）— 最大去重杠杆
- `04-synthesize/*` 存 `.bak`。验证：用 `_knowledge.md` 参数化 6 环驱动合成，三类各跑一个 slug，
  6 环硬落地与旧文档产出对齐。双关验收同阶段 3。通过删 `.bak`。

### 阶段 5：其余环（I1-I3 立题/定向/路线，I7/I8 评审/监控，深挖）
- 逐环：旧文档存 `.bak` → doctor 驱动 → 双关验收 → 删 `.bak`。

### 阶段 6：收口
- `prism search` 替代 prescan SOP 全流程验证（query 措辞由 LLM 给，H2 救回正常）。
- **更新 `SKILL.md` 路由表**：把指向 `00..07` / 各 `_*.md` 的路径，改为指向 `_arc.md` / `_contracts.md`
  / `_knowledge.md` / `_floor.md` + 动词用法。
- 删所有 `.bak`。跑全量测试 + dashboard（`/prism`）确认 web 端展示正常。

---

## 第 6 部分：每阶段验收命令（具体）

```bash
# 现有测试套件（每个脚本阶段后跑）
cd /Users/mark/investing && python -m pytest prism/ -q

# doctor 输出
python3 -c "from prism.scripts.doctor import doctor; import json; print(json.dumps(doctor('SLUG','VARIANT'),ensure_ascii=False,indent=2))"

# 数据契约 diff（抽料/合成前后对比）：dump 关键状态
python3 -c "from prism.scripts.topic import read_topic; import json; print(json.dumps(read_topic('SLUG','VARIANT'),ensure_ascii=False,indent=2))" > /tmp/before.json
# ...执行该阶段...
# 再 dump 一次，diff before/after 的 schema（字段集合、status 枚举、文件路径），结构应一致
find prism/topics/SLUG -type f | sort        # 文件树对比
python3 -c "from prism.scripts.gap_detector import detect_gaps; import json; print(json.dumps(detect_gaps('SLUG','VARIANT'),ensure_ascii=False))"
```

**端到端质量人工检查清单**（阶段 3/4 必过）：
- [ ] case 六环每环有"必带硬落地"（对 _knowledge.md 逐环核）
- [ ] 来源分层：训练知识/[mat-XXX]/特色判断三类标注在
- [ ] findings frontmatter 字段齐（mat_id/source_type/addresses/quality/bias）
- [ ] web findings 抽 3 条核 URL 真实存在（F1）
- [ ] 无 actionable 资料被静默跳过（list_unprocessed 为空 vs inbox 对账）
- [ ] critic verdict ∈ {approve,request-rewrite,request-more} + 承重横幅在
- [ ] thesis_v1 是全快照十一段（非增量补丁）

---

## 第 7 部分：回滚

- 每阶段旧文件存 `.bak`，未删前可 `mv X.md.bak X.md` 即时恢复。
- 脚本改动在 git 分支上；`git checkout -- prism/scripts/` 回退。
- **阶段 3 验收不过 = B 在抽料环不成立**：该环回退方案 A（保留一份薄程序 `03.md`，~90 行，
  内容=目标+工具一条入口+LLM 判断+底线+退出条件，但仍读 doctor）。其余环可继续试 B。
- doctor / search 动词是纯增量，失败不影响现有系统（旧 workflow 文档仍可用）。

---

## 第 8 部分：给执行者的硬规矩

1. **知识地板逐字搬，不重写**（第 3 部分铁律）。
2. **删约束前查附录 D**：在表里的只能"散文→guard"搬移，不能删。
3. **doctor 零 LLM、零新业务逻辑**：只组合附录 A 的现有读函数。发现需要新逻辑 = 设计有误，停下报告。
4. **不碰现有 ~70 个脚本函数的签名/语义**，只新增动词 + 在 3 个函数内嵌已有逻辑。
5. **一次一阶段，验收过才下一步**。
6. **AskUserQuestion 的 label/description 禁中文弯引号**（U+201C/U+201D 触发 InputValidationError，用「」）。
7. 任何"我觉得这条规则没用想删"的冲动，先在 `.bak` 保留 + 记录到本计划的"待确认"，交人类裁决。

---

# 附录 A：现有脚本函数签名与守卫（精确，可照抄）

### A.1 topic.py 关键函数（约 70 个，列 doctor/verbs 用到的）
- `read_topic(slug, variant) -> dict` — 读 topic.yaml（含 setdefault 兜底）
- `create_topic(slug, display_name, type, question, geo, depth, variant, ticker=None, short_name=None, extra_tickers=None, search_terms=None) -> ...`
- `set_stage(slug, stage, variant)` / `next_stage(type, current)` / `stage_progress(stage)->dict`
- `set_output_status(slug, output_key, status, variant, version=None)` — status∈pending/draft/fresh/stale
- `set_critic_verdict(slug, variant, verdict, ...)` — verdict∈approve/request-rewrite/request-more
- `get_critic_verdict(slug, variant)->dict|None`
- `set_thesis(...)` / `set_decomposition(...)` — frontmatter/convergence 校验
- `set_user_todos / append_user_todos / update_user_todo_status / mark_todo_fetch / set_todo_disposition`
- `pending_unfetched_todos(slug, variant) -> list[dict]` — 返回 unattempted+error 的 todo
- `empty_undecided_todos(slug, variant) -> list[dict]` — 返回 empty 且未处置的 todo
- `primer_quality_gate(slug, variant) -> dict` — 返回 {passed?, warnings, ...}
- `get_current_prescan_status(slug, variant) -> dict` — 三态
- `reverse_check_roadmap_coverage(slug, variant, version) -> dict`
- `set_monitoring_tier(slug, tier, variant)` — tier∈deep/watch/dormant
- `list_variants(slug) -> list[str]` / `list_topics(variant=None) -> list[dict]`
- `set_parent / suggest_relatives / set_parent_materials / list_missing_parent_findings`(在 findings.py)

### A.2 manifest.py
- `read_manifest(slug) -> dict` / `add_material(slug, filename, source_type, addresses=..., rings=...)` /
  `mark_processed(slug, mat_id)` / `list_unprocessed(slug, variant, exclude_triggered_by=...) -> list` /
  `list_pending_mineru / set_mineru_state(state∈needs/in_progress/done/failed/not_needed) / material_count`

### A.3 findings.py
- `build_findings_index(slug, variant)` / `list_all_findings(slug, variant)` /
  `list_missing_parent_findings(slug, variant) -> list`

### A.4 守卫现状（哪些已 raise — 见 _floor 的"已下沉"判定）
**已强制 raise**：create_topic(company 必 ticker+short_name≤12字；question>25字必 search_terms；
ticker 格式 {EXCHANGE}_{CODE}；extra_tickers 不含主 ticker 且不重复；文件已存在 FileExistsError)；
set_critic_verdict(verdict 枚举)；set_monitoring_tier(tier 枚举)；set_thesis(prescan_status 枚举；
failed 必 force_failed+reason)；set_decomposition(convergence 枚举)；set_prescan_log(status 枚举；
failed 必 reason)；set_user_todos/_normalize_todo(info_tier∈public/half_public/hard；priority∈P0/P1/P2；
status∈pending/in_progress/done；fetch_status∈unattempted/fetched/empty/error；disposition∈
undecided/waived/will_collect；addresses 须 K#/Q#/K#@event-slug 格式；现有有 address 但新传全空→raise)；
update_user_todo_status/mark_todo_fetch(枚举+无匹配 task raise)；set_parent(自指/不存在/tier 不递增 raise)；
manifest.set_mineru_state/make_search_meta(枚举)；web_prescan.register_web_search_result(URL 命中占位/
编造特征 raise)。
**未强制（仅 stderr/软门）**：变体名归一化、未登记模型、slug 已存在其他 variant、未知 type、
set_output_status F17(primer depth=deep 不过→降 draft 不 raise)、detect_gaps(topic 不存在返 error dict)、
reverse_check_roadmap_coverage(不 raise 直接写 todo+翻 stage)。

### A.5 gap_detector.detect_gaps(slug, variant) 返回结构
```python
{
 "topic": {"slug","variant","thesis_version"},
 "uncovered_ks": [K#...],            # evidence_count==0
 "thin_evidence": [K#...],           # 0<count<min
 "evidence_count": {K#: int},
 "ring_axis_status": "active"|"n/a",
 "ring_coverage": {code: int},
 "uncovered_ring_inputs": [{"code","ring","label","served_by":[..],"hard":bool,"reason"}],
 "thin_ring_inputs": [{"code","ring","label","served_by","hard":True,"count","min_evidence"}],
 "api_pending_inputs": [{"code","ring","label","served_by"}],
 "expired_web_materials": [{"id","filename","expire_at"}],   # web-search >90d
 "prescan_untagged": [{"id","filename","addresses"}],
 "single_source": [{"k","count","source_types","domains","reason"}],
 "autofetch_debt": [{"task","fetch_status","info_tier","addresses"}],
 "empty_pending_decision": [{"task","info_tier","addresses"}],
 "relative_updated": [...], "training_only_claims": []
}
# snapshot_gaps() 精简版: {uncovered_ks, uncovered_ring_inputs:[code], autofetch_debt:int, empty_pending_decision:int}
# detect_gaps 永不 raise（topic 不存在返 {"error":...}）—— 体现 F6 gap 非 gate
```

### A.6 web_prescan.py（供 `prism search` 包装）
```python
build_search_queries(slug, variant, recency_days=90) -> list[dict]   # [{addresses,kind,recency_days,hint}]
register_web_search_batch(slug, variant, query, addresses, triggered_by, hits:list[dict],
   full_texts=None, inline_finding=None, rings=None) -> dict
   # 返回 {n_high,n_mid,n_low,mat_ids,n_dropped_invalid,n_dropped_low,drop_ratio,
   #       dropped_hits, silent_failure, failure_mode('upstream_empty'|'all_low_band'|'none'), ...}
register_web_search_result(slug,variant,query,url,title,snippet,addresses,full_text=None,
   confidence=None,domain_tier=None,triggered_by=None,rings=None) -> dict
log_search_skipped(slug,variant,query,triggered_by,n_results,reason)
check_prescan_health(slug,variant,expected_queries,triggered_by_prefix="00-prescan") -> dict  # 三态
should_run_step0(slug,variant) -> dict   # {should_run,recency_days,reason,last_prescan}
extract_url_features(urls,slug=None,variant=None) -> dict   # H2 救回用
# 限流常量: BATCH_LIMIT=5, BATCH_INTERVAL_S=10, SERIAL_RETRY_INTERVAL_S=30, FAIL_THRESHOLD=0.5
```

### A.7 monitor.py（监控环 I8 用，CLI 直通）
```
python -m prism.scripts.monitor scan [14]    # scan_due_events -> JSON
python -m prism.scripts.monitor price [14]   # propose_price_breaches (零LLM)
python -m prism.scripts.monitor macro [14]   # propose_macro_updates (零LLM)
# scan_due_events -> {due_signposts,due_kills,price_breach,recurring_review,unparseable,macro_due,macro_alert,...}
# propose_flips(proposals) 每条必带 slug,variant,kind,locator,proposed_value; 可选 evidence,requires_thesis_review
# confirm_flip(id) 零LLM 机械回写 sidecar+append 08_living_feed+注册证据  | discard_flip(id) | add_watch(...)
```

---

# 附录 B：topic.yaml 完整运行时字段 schema

```yaml
slug: str
display_name: str
type: company|industry|arena|macro
created: iso8601
status: active|archived
stage: str                      # 历史保留；B 模式下 doctor 用不变量取代，但字段仍写（兼容 dashboard）
parent_topic: str|null
parent_materials: [...]         # 子 topic 复用父级资料
monitoring_tier: deep|watch|dormant
monitoring: {enabled:bool, cadence:str, tier:..., reviewed_at:iso}
concepts: [str]
scope: {geo:str, question:str, depth:str}
ticker: str                     # company 必填，格式 {EXCHANGE}_{CODE}
short_name: str                 # company 必填 ≤12 字
extra_tickers: [str]            # 多市场（A/H/ADR）
search_terms: [str]             # question>25字必填，每项≤15字
outputs_state:
  {output_key}:                 # 如 01_business_panorama / 07_decision_kit / 00_primer / c_investment_case ...
    version: int
    last_updated: iso|null
    status: pending|draft|fresh|stale
    data_freshness: str|null
    critic_passed: bool         # set_output_critic_passed
    referenced_mats: [mat_id]   # set_output_referenced_mats
    error: str|null             # set_output_error
    primer_gate: {...}          # 仅 primer，F17 软门记录
next_actions: [str]             # prescan_status=failed 时自动 prepend 警示
user_todos:
  - task: str                   # 文档身份（闭环键，非 K#）
    priority: P0|P1|P2
    info_tier: public|half_public|hard
    status: pending|in_progress|done
    fetch_status: unattempted|fetched|empty|error
    fetch_attempts: int>=0
    disposition: undecided|waived|will_collect
    addresses: [K#|Q#|K#@event-slug]
    covered_by: [str]
prescan_status: full|partial|failed|null   # 顶层当前态（H5 后绑 history）
prescan_log: [...]
pending_thesis_review: {...}|null          # daily-monitor 翻牌待重评 marker
critic_verdict: {verdict:approve|request-rewrite|request-more, ...}|null
```

---

# 附录 C：manifest.yaml 字段 schema

```yaml
materials:
  - mat_id: str
    filename: str
    source_type: sell-side-note|annual-report|industry-research|web-article|manual-note|policy|sec-section|drilldown
    addresses: [K#|Q#|...]      # 非空（actionable 资料）；prescan 校准料标 ['scope']
    rings: [code]               # input_contract 的 ring code
    processed: bool
    mineru_state: needs|in_progress|done|failed|not_needed
    parent_mat: str             # 可选，SEC section 指向原 htm
    sec_section: str            # 可选，source_type=sec-section 时
    search_meta:                # 可选，web 入库料
      domain_tier: whitelist|llm-judged-official|other
      confidence: float
      triggered_by: 00-prescan|00-prescan-baseline|01-prescan|02-step0|03-extract|04-synth|05-critic|06-daily-monitor|07-drilldown|unknown
      prev_queries: [str]
```

---

# 附录 D：血教训 / 横切不变量（F1-F11，精确，搬进 _floor.md）

> 格式：要点 | 出处 | 为什么(踩坑) | 当前强制 | 可否机械化(难度)

- **F1 web finding 必来自真实 hit，禁凭记忆补 URL** | `_web_prescan_shared.md`:68/350、`03`:495、`_subagent_deep_search.md`:48 | 训练记忆幻觉 URL 污染 manifest，下游产出不可靠 | 散文 + register_web_search_result 拒占位/编造特征 URL | 难（合法格式无法区分真假，需 hook）
- **F2 subagent 只产 markdown 到 final message，主 agent 落盘；禁 subagent 写文件/heredoc** | `_subagent_deep_search.md`:35、`03`:217-233 | 2026-05-22 4/4 测试：subagent Write 总幻觉"被拦截"错误，声称的 heredoc 绕过也是幻觉 | 散文（dispatch prompt 内嵌） | 中（主 agent 侧 watchdog）
- **F3 研报/行业报告必经 mineru vlm；失败必报+跳过，禁 pymupdf 偷工** | `02`:170、`03`:279-282/317-323 | pymupdf 丢表格/公式/多栏，研报关键数据在表格 | 散文 + test -f {stem}_vlm/full.md | 部分（入口检查 mineru_state；绕过直读需 hook）
- **F4 _extracted/_vlm 是 slug 级确定性产物，findings 按 variant 隔离** | `03`:250-264 | 跨 variant 重跑 mineru 浪费配额；写错路径 FileNotFoundError | 散文 + 幂等跳过 | 低（add_material 校验路径属 slug 级 materials/）
- **F5 todo 身份=文档非 K#，脚本零自动撮合，闭环须显式** | `_autofetch_protocol.md`:42-51 | 旧 K# 交集自动闭环：共享 K# ≠ 文档到齐，已删 auto_resolve_todos | 散文（旧代码已删） | 低（update_user_todo_status 拒无 task 子串的批量闭环）
- **F6 gap 是诊断不是 gate** | `02`:291、`03`:36/64、`_shared.md`:45 | 脚本不做"预设判断"，gap 由 LLM 判读 | 半（detect_gaps 不 raise，set_stage 不拒） | 不应完全机械化（设计选择）
- **F7 跨层借料必标来源、本维度自跑、冲突本 topic 赢；父级 finding 缺失须查** | `03`:42-64/430-435 | feedback_addresses_granularity：父级假覆盖，子 topic 相关 K# 静默跳过 | 03 Step0b list_missing_parent_findings(已机械化) + conflicts_with optional | 中
- **F8 prescan 与 todo 无交集** | `_autofetch_protocol.md`:14、`_web_prescan_shared.md`:297-300 | suggest_todo_coverage_candidates 造假覆盖，已删 | 散文 | 低（assert prescan triggered_by 不得调 todo 闭环）
- **F9 H2 tier 救回闭环** | `_web_prescan_shared.md`:135-143/226-265 | 2026-05 荣昌：P0 6 query 40 hit 仅 4 入库（80% 失血）；非白名单默认 0.4→low→丢 | 散文 + drop_ratio 警告 + extract_url_features + F4 域族晋升(自动) | 部分（drop_ratio>0.8 自动触发救回流）
- **F10 三态盖戳 fetched/empty/error + R1/R2/R3** | `_autofetch_protocol.md` 全 | 旧 info_tier=hard 当跳过门槛；error 当"没有"降级，可获取料静默缺失 | 散文 + pending_unfetched_todos 阻断升 stage | 低-中。R1 全覆盖(所有 tier/info_tier 都尝试，info_tier 只定努力强度非跳过门)；R2 有效尝试(搜真跑了+公开确无→才降级；故障必重试不降级)；R3 消费前兜底
- **F11 time_sensitivity 三分类 + 多市场口径** | `_baseline_knowledge.md`:34-48/68-80 | PRISM_VALIDATION F3：旧版对所有行业写死"产能变化" | 散文 + baseline 自检清单 | 低-中。静态(多年不变)/慢变(年级,训练vs今>=12月可能不准)/快变(季月级,>=3月大概率过时)；快变+高/中置信 fact 必在第五节有校准 query；多市场(A/H/ADR)估值/资金/公告 fact 必标市场口径，topic.yaml.extra_tickers 表达
- **附加铁律**：empty 硬闸门(empty_undecided_todos 空前不进决策链不写缺口，`_autofetch_protocol.md`:95)；
  AskUserQuestion 禁中文弯引号(U+201C/U+201D，用「」)；WebSearch 静默返空靠 failure_mode 字符串分流。

# 附录 E：MINERU 精确事实
- 环境变量：**`MINERU_TOKEN`**（在 `.env`），**不是** MINERU_API_KEY。错误：`MINERU_TOKEN not set — add it to .env`
- 调用：`.venv/bin/python -m scripts.mineru_api "{material_path}" --out "{stem}_vlm" --model vlm`（python API: `from scripts.mineru_api import convert; convert(src, out_dir, 'vlm')`）
- **禁止改第三参 vlm 为 pipeline/pymupdf**。产物：`prism/topics/{slug}/materials/{stem}_vlm/full.md`（slug 级）
- 适用 source_type：sell-side-note / industry-research / policy（add_material 自动标 mineru_state=needs）
- 年报 annual-report 走 `annual_report_extractor`→`_extracted.md`（pymupdf 零 LLM，确定性产物，不经 mineru）

# 附录 F：历史教训注记（原样）
- 2026-05 荣昌：80% 失血 / H2 救回（见 F9）
- 2026-05-22 4/4：subagent Write 幻觉（见 F2，参 [[subagent-write-hallucination]]）
- 2026-05-28：sidecar 模式只写 raw 不入库（inbox/_websearch_raw/）；runtime whitelist 已删(违反 H2，主观分类应 LLM 判)
- H5：thesis.prescan_status 顶层删除绑 history，避免 workflow01 Step8 prescan 失败覆盖 thesis_v0 的 full→failed 误 BLOCK 05
- PRISM_VALIDATION F3：旧版对所有行业写死"产能变化"（见 F11）
```

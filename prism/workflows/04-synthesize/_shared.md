# 产出合成 — 共享前置规范 + 通用工具

每份产出工作流开始前必须完成以下检查，违反则停止并告知用户。

> **本文件现为"共享工具库"**：三类 topic 的合成都改走决策链路径——company → `_company_case.md`、industry → `_industry_funnel.md`、arena → `_arena_funnel.md`。它们**引用**本文件的：前置检查 / gap 体检 / 增量重写判定 / 断点续跑 / 调度模式（主 agent 直做 + findings 加载/索引）/ thesis_v1 Scheme C / 即兴 web-search。
> **已退休（旧 8 份并列维度路径专属）**：01-08 分批 Write 清单、subagent dispatch 01-08 模板、自动触发 09/10、收尾 primer-last——均已下线，selection（09/10）折进 funnel 的环⑥、primer 改 primer-first 由各路径 Step 2 自管。磁盘上已有的旧 01-08 产出不受影响（静态文件，重合成走新路径）。

> **Web 搜索路径**：见 [[_web_search_routing]]（必读）。本步默认走 adapter；
> 仅事实校验类临时单查走 WebSearch tool。

## 前置检查

```bash
python -c "
import json
from prism.scripts.topic import read_topic
from prism.scripts.manifest import material_count
t = read_topic('{slug}', '{variant}')
counts = material_count('{slug}', '{variant}')
print('stage:', t['stage'])
print('materials:', json.dumps(counts))
print('question:', t['scope']['question'])
"
```

- **资料量**：至少 3 份已处理资料，否则提示「资料不足，建议先收集更多资料」
- **训练知识依赖**：每份产出明确标注哪些来自训练知识，哪些来自资料

## gap 体检（进 04 第一件事）

```bash
python3 -c "
from prism.scripts.gap_detector import detect_gaps, format_summary
print(format_summary(detect_gaps('{slug}', '{variant}')))
"
```

把 report 输出**完整贴到对话**。**双轴都看**（B 轴 = K# 脊柱，A 轴 = 决策链输入合同）：
- `uncovered_ks` 非空 → 该 K# 当前 0 条材料覆盖
- `thin_evidence` 非空 → 该 K# 证据 < 2 条
- `uncovered_ring_inputs` 非空 → 决策链某环必带输入无料（带 🔴 = 三项真·欠供）→ 该环写作会硬伤；`api_pending_inputs` 非红（合成期自动拉）
- `expired_web_materials` 非空 → web-search 材料 > 90 天

任一红项非空 → **不要硬合成**，否则 11 份产出全是"未充分论证"占位。先决定补救：即兴 web-search（_shared.md 末尾的"即兴 web-search"段）/ sub-agent 深挖 / 回 02 补资料。这是诊断不是 gate——脚本不会拒绝前进，但跳过等于让 05 critic 把雷踩回来。

> ring 轴 `uncovered_ring_inputs` 直接映射到"哪个决策环写作时缺输入硬落地"——比 K# 更早暴露断链风险。这也是下面**命门有界 delta 重拆**的输入之一。

## 增量重写判定（默认开启）

**目的**：避免 11 份产出每次都全重写——浪费 token 且让"未变章节"也升 version 引起噪声。

```bash
python3 -c "
from prism.scripts.outputs import list_affected_outputs
import json
r = list_affected_outputs('{slug}', '{variant}')
for k, v in r.items():
    print(f'{k}: {v[\"reason\"]} (+{len(v[\"new_mat_ids\"])} new mats)')
"
```

判定结果：
- `new`：从未合成 → 必须写
- `stale`：有新材料入库 → 必须重写
- `critic-stale`：critic verdict='request-rewrite' 显式标 stale（无新 mat 但 status='stale'） → 必须重写，**read critic-review 的反方论据作为补充输入**
- `fresh`：全部 mat 已纳入且未被 critic 标 stale → **跳过**

**写完每份产出后**，主 agent 必须调用以下一行注册引用：

```bash
python3 -c "
from prism.scripts.topic import set_output_referenced_mats
set_output_referenced_mats('{slug}', '{output_key}', {mat_ids_list}, '{variant}')
"
```

其中 `{mat_ids_list}` 是本份产出 frontmatter `## 信息来源` 段引用的所有 mat_id 列表。**未调用 → 下次仍判为 new/stale，浪费 token**。

### 触发全重写（绕过增量判定）

用户说「全重写所有 output」/「忽略增量」/「--full-rewrite」时，跳过 `list_affected_outputs`，对全部 9-11 份按 new 处理。常用于 thesis 大改、统一文风、修 schema 等场景。

## 命门有界 delta 重拆 + 收敛（B 层 · 写作期做，配合 thesis_v1）

> **为什么在写作期才做深度拆解**：00 的 `decomposition_v0` 是**薄知识**拆的（训练知识+prescan），其可靠性原理上无法认证（任何裁判也薄知识绑定）。真正的可靠性闸门是**厚料浮现后**的重拆——写 case 时读遍 findings，命门会自然浮现/移位/坍塌。这一步把它固化为 `decomposition_v1`。

### 1. delta 校验（读完 findings、动笔写 case 前）

对照 `decomposition_v0.md` 的命门 1-3，逐条问厚料：
- **新命门**：findings 揭示了 v0 没料到的、能翻盘 thesis 的特化问题？
- **掉队命门**：v0 某命门被证据证明是伪命题 / 不再决定成败？
- **重排**：命门间的杠杆顺序变了？
- **置信度更新**：v0 标"低/uncertain"的命门，厚料是否已能定调？

delta = 新增 ∪ 掉队 ∪ 重排。**delta 为空** → v0 已够好，直接 `set_decomposition(version=1, convergence_status='converged', changelog='厚料确认 v0 命门，无变化')` 后正常写作。

### 2. 第二收料趟（delta 非空时 · 双重收敛 + 硬顶）

delta 非空说明厚料改写了命门图景 → 需补这一轮的料，但**严格有界**（防 decompose↔gather 无限螺旋）：
- **只收新命门的料**（不重收已覆盖命门）——即兴 web-search / sub-agent 深挖，打对应 `rings`；
- **只重写受影响环**：用 `list_affected_outputs` + 命门→决策环映射，**仅重写命门变动直接波及的环**，未受影响的产出不动；
- **硬顶 2 轮**：第 1 轮收料+重拆若仍 delta 非空，再走第 2 轮；**第 2 轮后强制停**，残留命门进"诚实缺口清单"（见终态报告），不再开第 3 轮。

### 3. 防震荡（changelog 对全历史去重）

每次 `set_decomposition` 的 `changelog` 必须写清"**砍了什么 / 加了什么 + 为什么**"。重加一个曾被砍的命门，**必须附新证据**（changelog 注明"凭 mat-XXX 复活，区别于上次砍它的理由"）——否则视为震荡，不允许。动笔前对照 `decomposition` history 全历史，避免来回翻烙饼。

### 4. 收敛判定（写 thesis_v1 时一并定）

三条同时满足 → **收敛**：① delta 空；② gap 双轴绿（`uncovered_ks` + `uncovered_ring_inputs` 的红项都已补或诚实标缺）；③ 05 critic 无重大反转（critic 在 04 后跑，首轮可先标 `open`，critic 回来再定稿）。

```python
from prism.scripts.topic import set_decomposition
set_decomposition(
    slug='{slug}', variant='{variant}', version=1,
    summary='{更新后的命门一句话概览}',
    stage_set_at='04-synthesizing',
    convergence_status='converged',   # delta空+双轴绿+critic无重大；撞2轮顶用 'capped'；待critic用 'open'
    changelog='{砍了X(因mat-A证伪)/加了Y(凭mat-B)/命门2升信心；对照全历史无震荡}',
)
```

- **顽固命门**（撞 2 轮顶仍未解、但确实决定成败）→ 不在 04 死磕，`convergence_status='capped'` + 踢 `07-drilldown` 专项深挖（在终态报告里列出 + set_next_actions 提示）。

## 断点续跑（修 9：workflow resume）

**目的**：11 份产出循环，单份失败不能阻断后续 10 份；失败要可见且可重跑。

**模式**：每份产出包在 try/except 里：

```bash
python3 -c "
from prism.scripts.topic import set_output_referenced_mats, set_output_error
try:
    # 主 agent 已用 Write 工具落盘 outputs/{output_key}.md
    set_output_referenced_mats('{slug}', '{output_key}', {mat_ids}, '{variant}')
except Exception as e:
    set_output_error('{slug}', '{output_key}', str(e), '{variant}')
    raise  # 主 agent 看到后继续下一份，不中断 11 份循环
"
```

实践上主 agent 是用 Write 直接落盘，"失败"通常是 frontmatter 引用错 mat_id / addresses 不合 _ADDR_RE / 文件被外部锁。失败时调 `set_output_error` 标记，下一份继续。

### 重跑失败的 output

```bash
python3 -c "
from prism.scripts.topic import list_failed_outputs
for f in list_failed_outputs('{slug}', '{variant}'):
    print(f'  {f[\"output_key\"]}: {f[\"last_error\"][\"message\"]} @ {f[\"last_error\"][\"at\"]}')
"
```

主 agent 把 `list_failed_outputs` 返回的 output_key 加进重跑队列；成功一份调一次 `set_output_referenced_mats` 自动抹掉 last_error。

### 不要做的事

- ❌ **不要 try/except 吞异常**：失败必须 raise，让用户在汇报里看到"X 份成功 / Y 份失败"
- ❌ **不要在中途 commit 文件**：失败应只反映在 `outputs_state.last_error`，不留半成品 markdown
- ❌ **不要重跑全部 11 份"为了清错"**：只重跑 `list_failed_outputs` 列出的

## 写入规范

输出文件路径：`prism/topics/{slug}/{variant}/outputs/{output_key}.md`

每份产出 markdown 必须包含：
1. YAML frontmatter（slug, output_key, version, generated）
2. 正文内容（按各 workflow 规定）
3. 末尾：`## 信息来源` — 列出使用的资料（mat_id + 文件名）和训练知识比例估计

---

## 调度模式：主 agent 直做 + 并行 Write（**默认**）

**默认走主 agent 直做模式**——主 agent 读完 findings 后直接 Write case/决策链产出（`{c/i/a}_*_case` + sidecar yaml + thesis_v1，primer 已在 Step 2 先出），用 Write 工具并行批次（一次 message 发多个 Write 调用）。

### 为什么主 agent 直做（2026-05-22 改）

历史教训（feedback_subagent_bulk_synthesis）：用单 subagent 顺序模式 dispatch 11 份长产出，**两次测试都撞 60min subagent 硬上限被强杀，0 文件落盘**。原因：
1. **结构性超限**：11 份 × 400 行 markdown 的 token 输出本身就要 30-50min，加 findings 读取 + 推理 + cross-mat 校准必撞 60min 硬墙。
2. **Write 幻觉重试循环放大**（见 [[subagent-write-hallucination]]）。
3. **黑盒无可见性**：subagent stdout 不流式，前 30min 看不到进度，等发现已超时。

主 agent 直做的优势：
- **并行 Write**：一次 message 发 4-5 份产出的 Write 调用，比 subagent 串行快 3-5×
- **无 60min 硬墙**：主 agent 没有 wallclock 上限
- **无 Write 幻觉**：主 agent Write 工具可靠
- **可中途救**：每份 Write 实时落盘，断了可以接着写

### 执行步骤

主 agent 直做的标准流程：

1. **读 findings（一次性全文加载）**：调 `format_findings_for_prompt` helper 列出自有 + 父级 findings 路径，主 agent 用 Read 工具**并行**读完所有未读 findings（同一 message 多 Read 调用）。

2. **建轻索引（防 compact 防误读）**：

   ```bash
   python3 -c "
   from prism.scripts.findings import build_findings_index
   print(build_findings_index('{slug}', '{variant}'))
   "
   ```

   落盘 `outputs/_findings_index.md`：每份 finding 一行 = `mat_id | filename | addresses=[K#] | quality/bias | 80字摘要`。22 份 ≈ 3-5K tokens，远低于全文 ~40K。**索引是主 agent 的"地图"——下面所有"按需补读"决策都基于它。**

3. **读 thesis_v0**：作为强度 v0→v1 对照锚。

4. **写 _synthesis_brief.md**：先 dump K1-K5 v0→v1 强度调整结论到 `outputs/_synthesis_brief.md`，作为后续 06/07/08 的 cross-mat 校准锚。

5. **走本 type 的决策链写 case**：进入对应路径文档的决策链（company `_company_case.md` §3 / industry `_industry_funnel.md` §3 / arena `_arena_funnel.md` §3），按其逐环硬落地 Write。Write 节奏仍是"主 agent 直做 + 并行 Write"（一次 message 发多个 Write）。

   **每批次/每环开始前必做**（廉价且重要）：
   - **Read `outputs/_findings_index.md`**（已落盘，~3K token）—— 即使中间发生过 compact，看一眼索引也能立即定位本环需要哪些 mat_id
   - 从索引筛出与本环 addresses 维度相关的 mat_id
   - **自检**：还能清晰回忆这些 mat_id 对应 finding 的内容？能 → 直接写；不能/模糊 → 单独 Read 那几份补回（不是全部，只补本环需要的）

   **不要做的**：
   - ❌ 不要每环都 Read 全部 findings（重复重读浪费 token）
   - ❌ 不要假定 findings 一定还在 context（compact 可能切掉，索引让你能验证）

   > sidecar schema（`07_decision_kit.yaml` / `09_industry_to_arenas.yaml` / `10_peer_matrix.yaml`）**严格、dashboard 直接消费、禁自创字段**——字段清单见各路径文档的 sidecar 步骤（分别引 `07-decision-kit.md` Step 3.5 / `09-industry-to-arenas.md` Step 6.5 / `10-peer-matrix.md` Step 6.5）。
6. **状态注册**：用单个 Bash 脚本一次性注册各 output status + thesis v1（键名见各路径文档 §5）。
7. **收尾**：照各路径文档 §4 收尾——stage 推进 + 清空 user_todos + 更新 next_actions。

---

## 单份产出更新状态（每份产出完成后必须执行）

```bash
python -c "
from prism.scripts.topic import set_output_status
set_output_status(
    slug='{slug}',
    output_key='{output_key}',
    status='fresh',
    version={new_version},
)
print('状态已更新')
"
```

## 全部产出完成后（收尾）

先更新各产出完成状态：

```bash
python3 -c "
from prism.scripts.topic import read_topic, set_next_actions, append_user_todos
t = read_topic('{slug}', '{variant}')
# 仅 append 一条完成提示，不动 01/02 写的结构化 todos（修 H2）
append_user_todos('{slug}', [
    '全部产出完成（' + str(len(t['outputs_state'])) + ' 份），等待创建子 topic 或进入监控',
], '{variant}')
# 确认 next_actions 不再指向生成产出（next_actions 仍是 list[str]，OK）
actions = [x for x in t.get('next_actions', []) if '01-08' not in x and '产出' not in x]
set_next_actions('{slug}', actions, '{variant}')
print('收尾完成')
"
```

**写 thesis_v1（基于资料的修正版）**：

收尾时主 agent **必读** `outputs/_synthesis_brief.md`（如不存在 — 资料 <10 跳过，则直接读 06+07 合成 v1），把 K1-K5（或对应 thesis 钩子）的 v0→v1 强度调整结论 dump 到 `prism/topics/{slug}/{variant}/thesis_v1.md`。

#### Scheme C 写作约定（v1 起所有 thesis 强制）

任何 `thesis_v{N}.md`（N≥1）必须是**全快照**：包含当前完整的核心 thesis / 支持理由 / 反方观点 / K# 现状表 / 应对策略 / catalyst / 数据缺口 / 思维过程留痕，**不依赖 v{N-1} 章节即可独立阅读**。

强制结构：

1. **frontmatter** 加 `parent_version: {N-1}` + `writing_convention: 方案 C 全快照 + 顶部 changelog`
2. **§ 0. v{N-1} → v{N} changelog** — 5-10 行 release notes 帮 review 者快速定位增量（仅 review 用，正文不依赖）
3. **§ 1. 核心 thesis（当前完整版）** — 一句话观点 + 强度评分 + 估值带 + 时间维度
4. **§ 2. 支持理由（当前完整清单）** — 累积所有看空逻辑（含历代沉淀 + 本版新增），分类编号
5. **§ 3. 反方观点（当前完整清单）** — 累积所有看多逻辑（含历代沉淀 + 本版新增 + critic 强反驳），分类编号
6. **§ 4. Killer Question 现状表（K1-K{n} 完整）** — 表格列：K# / 主题 / 当前状态 / 触发条件
7. **§ 5. 应对策略矩阵** — 价格区间 × 动作
8. **§ 6. catalyst 时点表** — 当前完整 catalyst 序列
9. **§ 7. 数据缺口** — P0/P1/P2 分级 + 期望解决路径
10. **§ 8. 思维过程留痕** — 已知 / 刻意避开的偏见 / 关键差异
11. **§ 9. 信息来源** — 训练知识占比 + 关键 mat_id

**硬约束**：
- 禁止写「见 v{N-1} §X」「同 v{N-1} 不变」等需读老版本才能理解的引用
- 禁止只写"v{N-1} → v{N} 增量"而省略其他章节
- v0 是天然全快照（无 parent），五段式（见 00-research-topic 5.0）；v1 起改用本约定 11 段式

**为什么这样写**：用户阅读 thesis_vN 时只需打开一个文件即可看到当前完整画像；老版本（thesis_v0/v1/...）作为时点 archive 保留，仅供需要还原"当时怎么想的"时翻阅，不作为日常 review 的依赖。

写完调脚本登记：

```bash
python -c "
from prism.scripts.topic import set_thesis
set_thesis(
    slug='{slug}',
    variant='{variant}',
    version=1,
    summary='{修正后的核心 thesis，≤120字}',
    stage_set_at='04-post-synthesis',
)
print('thesis v1 已登记')
"
```

如果 brief 显示「v0 与 findings 完全契合，无需修正」，仍写 v1 但 summary 注明 `[与 v0 一致]`，便于后续 critic-review 锚定时点。

**写 thesis_v1 的同时写 decomposition_v1**（B 层与 thesis 配对升版）：把"命门有界 delta 重拆 + 收敛"那一节得到的命门图景落成 `decomposition_v1.md`（命门现状 + 置信度 + 每环 B 靶点 + §changelog），并调 `set_decomposition(version=1, convergence_status=..., changelog=...)`（见该节代码块）。

### 终态报告（收尾必出 · 三件套兜底）

收尾在对话里给用户一份终态报告，三块：

1. **双轴 gap 终态**：重跑 `detect_gaps` → B 轴（`uncovered_ks`/`thin_evidence`）+ A 轴（`uncovered_ring_inputs`，标出哪些已补、哪些仍缺）。
2. **收敛状态**：`decomposition` 的 `convergence_status`（converged / capped / open）+ 走了几轮第二收料趟。
3. **残留缺口清单（诚实）**：填不上的明写"**数据缺失**"或"**训练知识估算，非实证**"，**不冒充**；撞 2 轮顶的顽固命门列出 + 标记踢 `07-drilldown`。

> 三件套兜底 = 残留缺口清单（本步）+ 05 critic 复核 + 用户手检。薄拆解的不确定性靠这三层兜，不假装 04 一定收敛干净。

**stage 推进到 critic-review（修 7）**：04 完成后 stage 自动应为 `04-post-synthesis` → 由 next_stage 推到 `05-critic-review`。**company / default 类型必须跑 critic-review** 才能进 done；industry / arena 走 09/10 分支不强制（critic 是可选的）。

```bash
python3 -c "
from prism.scripts.topic import read_topic, set_stage, next_stage
t = read_topic('{slug}', '{variant}')
ns = next_stage(t['type'], t['stage'])
if ns == '05-critic-review':
    set_stage('{slug}', '05-critic-review', '{variant}')
    print('→ 05-critic-review 已就绪，告诉用户「评审 {slug}」启动 workflow 05')
"
```

**刷新仪表盘（修 S5：自动触发，无需手跑）**：

每份产出收尾调 `set_output_referenced_mats` 时已自动 fire-and-forget 重建 dashboard（异步 subprocess，~25s 在后台跑，主流程 <100ms）。**workflow 内不再需要显式 `python -m prism.scripts.dashboard`**。
后台失败仅写 `prism/logs/dashboard_auto.log`——若发现 dashboard 长期未刷新，手动跑一次 `python -m prism.scripts.dashboard` 排查。

**selection（09/10）已折进 funnel 环⑥**（不再自动触发独立 workflow）：
- **industry** → arena 选拔是 `_industry_funnel.md` 环⑥（落 `09_industry_to_arenas.yaml` + 建 arena stub），`09-industry-to-arenas.md` 降级为环④/⑥ 引用的"工具规范"（6 维评分 / sidecar schema / stub 创建）。
- **arena** → peer shortlist 是 `_arena_funnel.md` 环⑥（落 `10_peer_matrix.yaml` + 建 company stub），`10-peer-matrix.md` 同样降级为工具规范。
- **company** → 无 selection 环，c_investment_case 即完整决策。

> Tier 排序基于本 topic 的 thesis 最新版 + 决策链 ②④（funnel 文档 Step 1 已要求读 brief + thesis）。

### primer 由各路径 Step 2 自管（primer-first）

primer 不再是 04 的"最后一步"。三类路径都在**各自的 Step 2、case 之前**调用 `00-primer.md` 生成 `00_primer.md` + `_prism_reading_guide.md`（理解先行，case 站其上）。要点（主 agent 直做、critic 不可省、来源分层、depth 降级）见 `00-primer.md` 本身。本文件不再重复 primer 收尾逻辑。

## 质量检验

产出完成后自问：
- [ ] 有具体数据/时间/主体，不只是泛泛之词
- [ ] 多空观点都有呈现，不只说一边
- [ ] 有明确的「哪里可能是错的」
- [ ] 训练知识和资料来源有区分标注
- [ ] 字数适当（800-2000字为宜，过长反而难用）

---

## 即兴 web-search（新增）

合成某份产出过程中，如发现某段需要的关键事实数据**当前 manifest 缺失**（如"2025 Q3 全球 EV 销量"、"某公司最新季报营收"），主 agent 可以即兴调一次 WebSearch 而不必回退 02：

适用场景（**只在以下情况**才即兴）：
- 04 写产出时缺一个具体数字（销量/单价/市占率/估值倍数）
- 该数字训练知识无法准确给出（时效性过新）
- 已有 manifest 里搜了所有 findings 都没覆盖

执行（与 03-extract 用同一 helper）：

```python
from prism.scripts.web_prescan import register_web_search_batch
register_web_search_batch(
    slug='{slug}', variant='{variant}',
    query='缺失数据查询词，例如 "global EV sales 2025 Q3 IEA"',
    addresses=['{对应 K# 或 Q#}'],
    triggered_by='04-synth',
    hits=[...],  # WebSearch 返回的 hit
)
```

入库后在产出 frontmatter 的 `mat_ids_referenced` 列表中加入新 mat_id，确保 `set_output_referenced_mats` 调用时引用正确。

**自动产 inline finding（修 B2）**：`triggered_by='04-synth'` 时
`register_web_search_batch` 自动给每条 high/mid hit 写 `findings_{mat_id}.md`
+ `mark_processed`，返回值多 `inline_finding_paths`。**不再需要等下一轮 03 抽
finding**，05-critic 也能直接读到论据。

**纪律**：
- 单份产出合成过程即兴 web-search 不超过 5 条（避免膨胀）
- 引用 web-search 入库 material 时**仍需写 mat_id**（不准直接引 WebSearch URL，保溯源链）
- 如果即兴搜不到 → 在该段产出中标注"此处数据缺失，建议人工补充"，不要编造数字
- URL/snippet 必须来自 WebSearch 工具实际返回，不得用训练记忆补 URL
- 显式 `inline_finding=False` 关掉自动产 finding（罕见）

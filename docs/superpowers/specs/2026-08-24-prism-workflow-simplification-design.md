# Prism Workflow 简化设计（待批准）

> 日期：2026-08-24 · 状态：**方案待你拍板，未执行任何改动**
> 范围：`prism/workflows/**`（12 份 workflow + 共享 partial）、中间产物清单。
> 目标：① 降流程复杂度与维护成本；② **输出质量不降、争取提高**。
> 核实方式：读完 `DESIGN.md`(637 行) + 全部 workflow(7465 行) + 抽样 industry/arena/company 各 2-3 个 opus4.8 成稿与全部中间产物 + grep 脚本/web 确认每个产物的真实消费者。下文带"✅核实"的是查过的事实，不是推测。

---

## Part 1 · 复杂度从哪来（量化）

| 指标 | 现状 | ✅核实方式 |
|---|---|---|
| workflow 文档总量 | **7465 行** | `cat prism/workflows/*.md 04-synthesize/*.md \| wc -l` |
| 跑完一个 company 需读入的文档 | **5228 行 / 326 KB**（≈100K+ token，每次都付） | 主线 15 个文件相加 |
| Step 标题数（主线） | **113 个** | grep `^## Step` |
| LLM 需会调的脚本符号 | **74 个** | grep workflow 里的 `from prism.scripts.X import` |
| 硬约束提及（必跑/禁止/不得/硬闸门） | 00 有 **73 处**，全线 200+ | grep |
| 近 90 天改动次数 | 00×24、_shared×18、_company_case×17、_industry×14、_arena×14 | git log |

**三种复杂度，只有两种该打：**

1. **本质复杂度（不能动）**——6 环决策链、双轴覆盖（K#/ring）、primer-first、独立 critic。抽样 6 份成稿证明这就是质量来源（micron case 环②把"前瞻 PE 7.7x = 低 PE 陷阱"和 normalized $45 vs 市场隐含 $78 的 delta 咬死在同一组单位上——这种硬度正是链契约逼出来的）。
2. **补偿性复杂度（可大幅压）**——因为"脚本零 LLM，纪律不被代码强制"（DESIGN 原理 1 的代价），同一条规约在多处重复：产即收 13 处、闭环键 6 处、"诊断不是 gate" 3 处、auto-fetch 阶梯 3 处、primer↔case 分工 6 处。2026-06-16 自审已列为 B1-B5，**当时只问了没做**。
3. **同构复制（可大幅压）**——三条 case 路径（1037 行）标题级 100% 同构；两张选拔 spec（418 行）同构；01/02 两个 workflow（1018 行）功能高度重叠。**改一处链契约要改三遍**，这是近 90 天 45 次三倍工的来源。

---

## Part 2 · 全盘 I/O 拆解（含中间产物 · 按"谁消费"判定必要性）

存在率分母 = 58 个跑出过产出的 variant。

### A. 机器承重（**动不得**，dashboard/monitor/gate 直接吃）

| 产物 | 谁写 | 机器消费者（✅核实） | 判定 |
|---|---|---|---|
| `topic.yaml` | 脚本 | 全系统状态机 + web + monitor | 保留 |
| `manifest.yaml` | 脚本 | gap_detector 双轴 / list_unprocessed / list_affected_outputs / dashboard | 保留 |
| `thesis_v{N}.md` | LLM | `extract_killer_questions`→B 轴覆盖；`validate_roadmap_thesis_coverage` | 保留（K# 表是脊柱） |
| `findings_mat-*.md` | LLM | frontmatter `addresses`/`rings` 喂 gap 双轴；observability 03.Q1/Q3 | 保留 |
| sidecar `*.yaml`（07/09/10/transmission_map） | LLM | dashboard.py + monitor.py + observability 直接读，字段名硬契约 | 保留 |
| `web_search_log.yaml` | 脚本 | `verify_empty_todos_searched`（真闸门）+ `check_prescan_health` | 保留 |
| `macro_stamp.yaml` | LLM/脚本 | `scan_holding_staleness` / coverage_gaps | 保留 |
| `roadmap.yaml` | LLM | **仅 2 处**：`validate_roadmap_thesis_coverage`（01 闸门）+ `build_search_queries` 的 l4-hunting 槽 | 保留但可瘦身 |

### B. 交付物（读者价值 = 系统目的）

`00_primer.md`（23-39KB）、`{c/i/a}_case.md`（23-32KB）、`05-critic-review.md`、`drilldown_*.md` — **全部保留**。抽样质量很高，不动。

### C. LLM 工作记忆 / 人读（**零机器消费者**，是简化空间）

| 产物 | 存在率 | 机器消费者（✅核实） | 判定 |
|---|---|---|---|
| `baseline_knowledge.md`（13-17KB） | 55/58 | **0**（只有 `has_baseline_knowledge` 存在性；web 都不渲染） | **保留本体、瘦格式**。它的真价值是"快变 fact 台账 → 精准 prescan query"+"§6 校准回写让下游知道哪条 fact 已死"，这两件不可替代 |
| `decomposition_v{N}.md` | v0 55/58 · v1 49/58 | **仅存在性**（`gap_detector.has_decomp` 决定 ring 轴是否 active）+ 版本列举 | 保留本体（命门≠K#，是终局拆解轴），**取消双持久点**、v1 只写 changelog |
| `_synthesis_brief.md` | **40/58** | **0**（只有诊断页 `read_synthesis_brief_html` 渲染） | **退休**。抽样 micron：它的 K1-K5 强度表与 `thesis_v2 §4` + `decomposition_v1 一、命门现状` 是**同一时点第三次重述** |
| `_findings_index.md` | 55/58 | 脚本派生、防 compact 地图 | 保留（廉价高值） |
| `_prism_reading_guide.md` | 52/58，其中 **43 份与 canonical 字节相同** | 0 | **停止 per-topic 复制**，web 端统一渲染 |
| `08_living_feed.md` | 33/58 | **0 读**（8 处引用全是 append/write） | 降级纯人读日志 |

### D. 机械转换层（slug 级共享，已最优）

`materials/*.pdf` → `_extracted.md`（年报/pymupdf）/ `_vlm/full.md`（研报/mineru）/ `sec/item_*.md`、`inbox/_websearch_raw/*.json` — 跨 variant 复用、命中即跳过。**不动**。

---

## Part 3 · 按 workflow 粒度的简化方案（6 个独立闭环）

每个闭环自包含、可单独 review、可 `git revert` 单个 commit。

### W-A｜04 三条 case 路径去重 → 链骨架 + 3 张 type 卡 【首推】
- **现状**：`_company_case`(394) + `_industry_funnel`(325) + `_arena_funnel`(318) = **1037 行**，标题级 100% 同构（✅核实：§0/§1.2 分工表/§1.3 护栏/Step0/Step2/§3.1/§3.3/§3.4/Step5/收尾/汇报/附录 全部三份）。真正 type-specific 的只有：元目标 1 段、6 环各自【必带硬落地】、Step1 财务/行情取数口径、sidecar key、critic 特化项、Step0.5（company 独有）。
- **做法**：抽 `_case_chain.md`（链契约 + 通用 Step，~250 行）+ `_type_company.md` / `_type_industry.md` / `_type_arena.md`（各 ~110 行）。SKILL 路由改为 "读 `_case_chain.md` + 本 type 卡"。
- **收益**：1037 → ~580 行（-45%）；**改链契约从 3 处降到 1 处**（近 90 天这三份共改 45 次）。
- **质量影响**：0，甚至为正（消除三份已开始漂移的措辞，如 industry/arena 有"定价锚×证据强度张力"硬落地、company 没有）。

### W-B｜04 两张选拔 spec 去重
- **现状**：`_arena_select_spec`(181) + `_peer_matrix_spec`(237) = 418 行，同构：评分 → 强制三档 → data_freshness → sidecar schema → 建 stub + 继承父 thesis（Step6/6b vs Step7/7b，唯一差异是 child type）。
- **做法**：抽 `_child_stub.md`（建 stub + thesis_v0 继承 + 强度 -1，~60 行），两 spec 只留"评分维度 + sidecar schema"。
- **收益**：418 → ~280 行。质量影响 0。

### W-C｜01 + 02 合并为一个「收料」workflow
- **现状**：01(634) + 02(384) = 1018 行。**02 开头自己就写"如果你刚从 01 推进过来，Step 0-4 大概率全跳过"**；而 02 唯一独占价值（用户中途上传料的登记 + mineru）**已在 03 Step 0 的 "inline 02" 里完整实现**（✅核实：03 Step 0 含 add_material + `list_pending_mineru` 批转），且 `register_inbox_materials` 幂等、在 00/01/02 被调 3 次。
- **同源硬闸门写了三遍**：`pending_unfetched_todos`+`verify_empty_todos_searched` 在 00 Step 6.5e / 01 Step 5.8 / 02 Step 6（✅核实）。
- **做法**：`01-gather.md`（roadmap 计划 + 自动收料阶梯 + 登记 + 一处闸门 helper），02 退休。**stage 常量 `02-gather-materials` 保留不动**（web 进度条 + 5 处 gate 依赖，是承重墙）——只是不再对应独立 workflow 文件：01 跑完有可处理料就推 `03-extracting`，没有就停在 `02-gather-materials` 等用户上传，用户上传后"推进"直接进 03。
- **收益**：1018 → ~380 行；消掉一次"循环找不到事做"的空转。
- **质量影响**：0（脚本调用与闸门一个不少）。**风险**：stage 语义要写清，需回归验证 web 进度条 + `next_stage`。

### W-D｜硬规约反链化（跨全部 workflow）
- **现状**（= 2026-06-16 自审 B1-B5，未执行）：产即收 13 处、闭环键 6 处、"诊断不是 gate" 3 处、auto-fetch 三阶梯 3 处、primer↔case 分工 6 处、sidecar 写完自检 2 处。
- **做法**：每条规约**唯一权威处**（`_autofetch_protocol` / `DESIGN` / `_case_chain`），各调用点压成一行反链 + 本步特化参数（作用域、`triggered_by`、默认 `addresses`）。
- **安全前置（必须逐条做，这是本项唯一风险点）**：对照 `DESIGN.md §1.6` 真闸门表——
  - **有机械兜底 → 可压**（如"标 empty 前必须实搜"已被 `verify_empty_todos_searched` 拦；"thesis 必在 variant 根"已被 `validate_roadmap_thesis_coverage` 拦）；
  - **无兜底 → 原文保留**（如"dispatch prompt 里绝不提写权限/hook/失败兜底"——这条无脚本可拦，且踩过两次幻觉坑）。
- **收益**：~600-900 行；未来改规约只改一处。**质量影响**：0（前提是上面的逐条核对不偷懒）。

### W-E｜00 从"18 个 Step"改成"4 幕 + 验收断言" 【自由度落地点】
- **现状**：876 行 / 18 Step / 73 处硬约束，是最重入口，每开新研究全量读。真实产物只有 5 个：`topic.yaml+manifest` / `baseline_knowledge` / `thesis_v0` / `decomposition_v0` / `user_todos+抓料入库`。**文档自己开头已有"4 幕 / 3 思考产物"速览表**——心智模型早就想清了，只是被执行细节压住。
- **做法**：借用**系统自己最成功的设计模式**（primer 与 case 的"给元目标 + 自由发挥 + 独立 critic/机械闸门校验"，已在 6 份成稿验证）搬到入口：
  - 主线只留 **幕 → 产物 → 验收断言（一行脚本）**，≤280 行；
  - query 措辞规范、字段清单、盖戳判定表、inline 示例、历史教训全下沉 `_00_reference.md`，按需读；
  - **脚本闸门一个不删**：`create_topic` 的 ticker/short_name/search_terms raise、`check_prescan_health` 三态、`set_thesis(force_failed)`、6.5e 双闸门。
- **收益**：876 → ~280 行主线；入口理解成本从"背 18 步"变成"看懂 4 幕产物 + 5 个断言"。
- **质量影响**：**这是唯一需要实测的一项**。缓解：先只对一个新 topic 试跑，与既有同类 topic 的 v0 产物对比（thesis_v0 是否仍落在终局上、K# 是否可证伪、decomposition 是否仍带置信度 tag、prescan 命中率），不达标就回退。

### W-F｜中间产物瘦身（3 项，低风险，顺手做）
1. `_synthesis_brief` **退休** → 改为"对话内 dump v0→v1 强度校准，不落盘"；诊断页那一块随之去掉。（0 机器读者 + 69% 存在率 + 三重重述，✅核实）
2. `08_living_feed` 降级纯人读日志（0 读者，✅核实；DESIGN Part 10 也已确认）。
3. `_prism_reading_guide` 停止 per-topic `cp`，web 端统一渲染 canonical（43/52 字节相同）。
4. `decomposition` 取消双持久点（`_shared.md` 早写 + case Step5 收尾各一处），统一收尾；v1 只写「命门现状 + primer 目标现状 + changelog」，不重述 thesis 内容。

---

## Part 4 · 明确不动（承重墙 / 质量来源）

- 脚本零 LLM 调用（原理 1）
- 6 环链的**因果序**与每环【必带硬落地】
- 双轴 gap 解耦（B=`addresses` / A=`rings`）
- 闭环键 = task/文档身份（血泪删过 K# 撮合）
- sidecar 严格 schema（四处同步）
- file-first `outputs_state`
- primer-first + 独立 critic 不可省 + `primer_quality_gate`
- 三个思考产物**本体**（baseline / thesis / decomposition）——只允许瘦格式，不删不合并
- 所有真闸门（DESIGN §1.6 表 8 条）

---

## Part 5 · 交付顺序与验收

推荐顺序：**W-A → W-F → W-D → W-B → W-C → W-E**（先零风险高收益，最后动最激进的入口）。

每个闭环统一验收：
1. **行数前后对比**（写进 commit message）；
2. **硬规约逐条核对表**：改动涉及的每条"禁止 X / 必跑 Y"→ 标注"仍在主线 / 已压成反链且有闸门兜底（点名闸门）/ 原文保留（无兜底）"，任何一条落不进这三类就不改它；
3. `.venv/bin/python -m pytest prism/scripts/test_*.py`（W-C/W-F 动脚本时必跑）；
4. 按 CLAUDE.md：动脚本前 `impact({target, direction:"upstream"})`，提交前 `detect_changes()`；
5. **W-C / W-E 额外**：拿一个真 topic 跑一遍对应 stage，与既有同类产物对比质量断言（见 W-E）。

**总体预期**：workflow 7465 → ~4300 行（-42%）；单次 company 跑动读入 326KB → ~190KB；改一条链契约/一条规约从 3-13 处降到 1 处。

---

## Part 6 · 决策记录（2026-08-24 用户拍板）

- **打包方式**：渐进 6 闭环，一次一个 commit，可单独 review / revert。
- **第一批**：**W-A**（三条 case 路径去重）。
- **W-E 验收**：拿一个新 topic 用新 00 跑一遍，对 ① thesis_v0 是否落在 type 终局上 ② K# 是否可证伪 ③ decomposition 是否带置信度 tag ④ prescan 命中率 四项与既有同类 topic 逐条对比，不达标即 revert。
- 顺序：W-A → W-F → W-D → W-B → W-C → W-E。

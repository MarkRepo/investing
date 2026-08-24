# Prism 系统设计文档（内部细节 · 权威版）

> **这份文档讲清 prism 的全部内部设计**：数据结构逐字段、每条判定/闸门的机械逻辑、层与层之间的耦合点、以及"哪里能改、改了会牵动谁"的取舍清单。目标是**看文档就能理解系统所有设计思路与原理，并据此做迭代优化 / 简化设计的取舍**——不必再回头逐个读脚本与 workflow。
>
> **受众**：未来的你（时间久了会忘）+ 接手的 Claude 会话。
> **配套**：触发路由见 `.claude/skills/prism/SKILL.md`；逐步执行规约见 `prism/workflows/*.md`；逐字段/逐函数的单一事实源永远是**脚本 docstring + workflow 文件本身**——本文件是它们之上的**结构地图与取舍依据**，讲"为什么这么设计、动了会怎样"，不逐字复述操作。
>
> **维护约定**：改流程结构（stage 机、双轴、auto-fetch 规约、决策链环、sidecar schema、macro 层、可观测层）时同步更新对应 Part。新增 H-fix / drift 修复追加 Part 8。本文件写于 2026-08，覆盖到 macro 横切层 + 被动可观测层。
>
> **阅读顺序**：Part 1（心智模型，一场读完）→ Part 2（数据对象全表）→ Part 3-6（各子系统细节）→ Part 7（层间耦合图，改代码前必看）→ Part 8（踩坑归纳）→ Part 9（简化/迭代取舍清单，你最关心的）。

---

# Part 1 · 心智模型（一场读完）

## 1.1 一句话定位

Prism 是 **LLM 驱动的结构化投资研究系统**。它把"研究一个行业 / 竞技场 / 公司 / 宏观体制"拆成一条**固定阶段的流水线**，每阶段产出结构化中间物，最终按 topic 类型合成一份**理解先行 + 6 环决策链 case**（+ 机器可读 sidecar），可在 `/prism` web 端查看，并接入日常监控。

## 1.2 铁律：脚本零 LLM 调用

**所有判断、抽取、合成、评审都由 Claude 在对话里做；Python 脚本只做四类"不该靠 LLM"的事**：

1. **CRUD** — 读写 `topic.yaml` / `manifest.yaml` / `roadmap.yaml` / findings / outputs / sidecar / macro 登记表。
2. **机械校验** — gap 双轴计算、coverage 闭环、auto-fetch 全覆盖闸门、primer 深度门禁、sidecar schema 断言、macro 机制纪律。
3. **确定性取数** — web 搜索 adapter、财报下载、财务/行情 API、macro 数据源 fetcher。
4. **确定性派生** — dashboard 渲染、监控扫描、可观测探针、状态机推进。

这条线决定了整个系统的形态：**workflow 文件是写给 LLM 的"怎么想"，脚本是"怎么存 / 怎么算 / 怎么取"。**

**为什么这么分**：投资判断是 prism 的核心价值，高度依赖模型能力——锁进脚本就等于锁死在写代码那天的认知。把判断留在对话里，模型一升级整个系统的产出质量就抬升。脚本承担确定性部分，可单测、可审计、行为稳定。

**代价（贯穿全系统的核心张力）**：纪律不被代码强制。所以 workflow 文件里塞满"硬规约""禁止 X""必跑 Y"——这些是补偿"脚本不拦"的软约束。Part 8 收拢的 H-fix 多数是"软约束没守住 → 加机械门禁兜底"的演进。**理解这条张力，是理解为什么系统里既有'诊断不是 gate'的弹性、又有少数几处真闸门的关键。**

## 1.3 流水线（6 阶段 + 旁支）

```
00 立项          01 规划           02 收料              03 抽取          04 合成               05 评审          (06 监控)
research-topic → 01-build-roadmap → 02-gather-materials → 03-extract → 04-synthesize/ → 05-critic-review → done
   │               │                  │                     │             │                   │
 thesis_v0       roadmap            manifest              findings      primer + case        verdict
 K# + 拆解v0     三档资料计划        实收料登记            结构化抽取      + sidecar            approve/
 prescan校准     自动取数(产即收)    gap体检              gap体检         + thesis_v1          request-more/
 baseline知识                                                            + decomp_v1          request-rewrite
```

- **规范 stage 常量**：`00-init` / `01-roadmap`（+`-pending` / `-reopen` 子态）/ `02-gather-materials` / `03-extracting` / `00-quality-screen`（company 专属）/ `04-synthesizing` / `04-post-synthesis` / `05-critic-review` / `done`。特殊终态 `quarantined`（company 红线门控 FAIL）。
- **中文进度名**（web 三处共用，`topic.py:STAGE_PHASE_NAMES`）：`["立项","规划","收料","抽取","合成","评审","完成"]`——把细 stage 收敛成 7 个读者看得懂的大阶段。
- **`-pending` / `-reopen` 后缀**：同阶段的子态。`01-roadmap-pending`=待跑规划；`01-roadmap-reopen`=thesis 升版后 reverse-check 发现 roadmap 漏 K#，路由回 `02-gather-materials`。
- **旁支 workflow**（不在主线，按需触发）：`06-daily-monitor`（每日巡检）、`07-drilldown`（深挖单个命门）。
- **四类 type 的 stage 流**（`topic.py:next_stage`）：industry/arena/company/macro 第 6 阶段统一为 `05-critic-review`——company 必跑 critic 才能 done；industry/arena/macro critic 可选（对话跑评审或 web 点「完成」均可 done）。company 比其余多一个 `00-quality-screen`（红线门控）。

## 1.4 四种 topic 类型 + 类型 tier

| type | 终局（`_TYPE_TERMINALS`，type 独占、a priori 不可协商） | 决策链 case | sidecar | tier |
|------|------|------|------|------|
| `company` | 买/卖/持有 + 期望收益(EV) + 目标价/介入纪律 | `c_investment_case` | `07_decision_kit.yaml` | 0 |
| `arena` | 候选标的里选 shortlist——谁是赢家、介入纪律 | `a_arena_case` | `peer_matrix.yaml` | 1 |
| `industry` | 把资本/注意力分配给哪几个细分 arena（深挖/观察/淘汰三档分流） | `i_industry_case` | `industry_to_arenas.yaml` | 2 |
| `macro` | 体制定位 + 传导地图下的资产含义 | `m_regime_read` | `transmission_map.yaml` | —（横切层，不进 tier） |

- **type tier 严格递增**（`topic.py:_TYPE_TIER`，company<arena<industry）：约束父子关系——父 tier 必须 > 子 tier。industry 环⑥派生 arena 子 topic、arena 环⑥派生 company 子 topic，自顶向下建链。
- **终局由 type 独占**是全系统的锚：question / thesis K# / 命门 / 收料 / critic 全部围绕这个固定终局倒推。改 type 的终局定义（`topic.py:_TYPE_TERMINALS`）会牵动 00 Step 1a 声明、05 critic 终局证据强度核对、决策链环⑥。

## 1.5 核心数据对象（谁写、给谁读）

| 对象 | 路径 | 是什么 | 谁写 |
|------|------|------|------|
| `topic.yaml` | `topics/{slug}/{variant}/` | 主状态文件：stage / next_actions / user_todos / outputs_state / thesis 指针 / decomposition 指针 / stage_history / prescan_log / parent_materials / suggested_drilldowns / monitoring | 脚本（`topic.py`） |
| `manifest.yaml` | `topics/{slug}/{variant}/` | 资料清单：每份料的 id / source_type / rings / addresses / processed / search_meta / mineru_state | 脚本（`manifest.py`） |
| `roadmap.yaml` | `topics/{slug}/{variant}/` | 三档资料计划 + L3 争议 + L4 狩猎（逐条对齐 K#） | LLM Write（填模板） |
| `baseline_knowledge.md` | `topics/{slug}/{variant}/` | 训练知识先验（fact 账本 + 置信度 + 时效 + prescan 校准回写） | LLM Write |
| `thesis_v{N}.md` | `topics/{slug}/{variant}/` | 投资论点 + K#（Killer Questions，可证伪赌注），版本化 | LLM Write |
| `decomposition_v{N}.md` | `topics/{slug}/{variant}/` | 命门拆解（机理/兑现路径特化问题）+ primer 入门目标（B 轴），版本化 | LLM Write |
| findings | `topics/{slug}/{variant}/outputs/findings_*.md` | 从资料结构化抽取的证据条，带 frontmatter（rings/addresses/source/quality） | LLM Write |
| `outputs/` | `topics/{slug}/{variant}/outputs/` | `00_primer` + 按 type 的单份 case + sidecar yaml + `_prism_reading_guide` + `_findings_index` + `_synthesis_brief` + `08_living_feed` | LLM Write |
| sidecar | `outputs/*.yaml` | dashboard/monitor 直接消费的机器文件（严格 schema，禁自创字段） | LLM Write |
| `macro_stamp.yaml` | company `outputs/` | 该 company case 站在哪版 macro regime + 依赖哪些体制状态 | LLM/脚本 |
| `macro_inputs.yaml` | macro `topics/{slug}/{variant}/` | 宏观输入登记表（利率/流动性/汇率的机制边 + 观测值） | 脚本 CRUD + LLM 判读 |
| `regime_eval_log.yaml` | macro `outputs/` | 输入→判断可溯源的评估快照（版本化） | 脚本 append + LLM 提供 conclusions |

**变体（variant）**：同一 slug 下可有多个研究变体（换模型/换角度重研）。variant 名以 `model_registry` 规范名为准（如 `opus4.8`；旧别名 `claude-opus-4-8` 自动归一）。**所有 topic 数据都在 `{variant}/` 子目录下**——`topic.yaml` / `manifest.yaml` / `roadmap.yaml` / `thesis_v{N}` / `decomposition_v{N}` 在 variant 根，findings/outputs 在 `{variant}/outputs/`。**唯一的 slug 级共享是 `materials/`（原始文件 + mineru 转换产物）**，跨变体复用不重转 PDF。`inbox/` 也是 slug 级（用户手放料的落点）。

## 1.6 三条贯穿原理（设计理念精华 · 记住这三条就抓住了系统骨架）

**原理 1 — LLM 判断 / 脚本 CRUD 分离**（§1.2）。好处：判断质量不被脚本逻辑锁死，模型升级即受益；脚本可单测、确定性强。代价：纪律全靠 workflow 文档约束。

**原理 2 — 收料"先自动获取，抓不到才降级 user_todo"**（"产即收" auto-fetch 规约）。目标：todo 里**只剩用户才能搞到的东西**（付费墙/专家访谈/未公开数据）。实现：谁产 todo 谁当场收（下游只消费、不补抓）；财报走 `fetch_report_prism`、公开分析材料走 exa/adapter/WebFetch 三阶梯；每条尝试后必显式盖 `fetch_status`（fetched/empty/error）。**闭环键是 task/文档身份，不是 K#。** 详见 Part 4。

**原理 3 — 收敛靠"诊断不是 gate + 诚实降级"，不靠硬闸**。`gap_detector` 报红**不阻止你升 stage**——它是诊断，不是门禁。哲学是：**与其用硬闸卡死流程，不如让缺口显式可见 + 强制诚实标注**（"数据缺失"/"训练知识估算，非实证"）。**极少数地方才设真闸门**（下面这张表是全系统真闸门的完整清单——其余全是诊断/软约束）：

| 真闸门 | 位置 | 拦什么 | 脚本锚 |
|--------|------|--------|--------|
| auto-fetch 全覆盖 | 00 Step 6.5e / 01 Step 5.8 / 02 Step 6 | `unattempted` todo（从没试过抓就推进）+ 无痕 `empty` | `pending_unfetched_todos` + `verify_empty_todos_searched` → `SystemExit(1)` |
| empty 硬闸门 | 04 进决策链前 + 逐环 R3 | `empty` 且用户未处置（waived/will_collect） | `empty_undecided_todos` → `AskUserQuestion` 强制 |
| roadmap→thesis 闭环 | 01 Step 5.7 | thesis 缺失 / K# 未被 L4+material 覆盖 | `validate_roadmap_thesis_coverage` → `SystemExit(1)` |
| company 红线门控 | 04 Step 0.5 | 致命财务/治理红线 → `quarantined` | `get_quality_screen_data` + LLM 判 |
| primer 深度门禁 | 注册 00_primer 时 | depth=deep 但字数不足/缺争议节/未过 critic → 自动降 draft | `primer_quality_gate`（`set_output_status` 内调用） |
| 04 后强制 critic（仅 company） | `next_stage` | company 不过 critic 不能 done | `next_stage` 流里 04→05→done |
| prescan failed 封顶 | 05 Step 0.0 | failed prescan 时 verdict 最高 request-more，不许 approve | `get_current_prescan_status` + workflow 约束 |
| thesis failed 强制确认 | `set_thesis` | prescan_status='failed' 未传 force_failed → raise | `set_thesis` |

> 原理 3 是双刃剑：它给了流程弹性，但也是"todo 被静默忽略""薄弱论证蔓延到下游"的根因。**被动可观测层**（Part 6）就是为了把这些"静默"变"显式可见 + 可审计"，而不是把诊断改成硬闸。

## 1.7 两条正交的覆盖轴（理解 gap 的关键）

Prism 用**两条正交的覆盖轴**判断"料够不够、论证扎不扎实"，由 `gap_detector.py` 双轴计算：

- **B 轴 · K# 覆盖（thesis 脊柱）**：每个 K#（Killer Question）有没有 findings 证据撑着。资料用 `addresses: [K1, K3]` 字段挂到 K#。`uncovered_ks`=0 证据（🔴 硬伤）；`thin_evidence`=有料但 < min_evidence（🟡）；`single_source`=覆盖达标但来源塌缩到单一 source_type/域名（🟠 注意力路由器，非裁决）。
- **A 轴 · ring 覆盖（输入合同地板）**：6 环决策链每一环的"必带硬落地"有没有原始输入供给。资料用 `rings: [biz-moat-unit-econ]` 字段挂到环。`uncovered_ring_inputs`=某环必带输入无料（带 🔴 = 三项真·欠供）；`thin_ring_inputs`=hard 项有料但不足；`api_pending_inputs`=财务/估值类合成期自动拉（**非红**）。

**两轴解耦是刻意的**：
- B 轴的 K# 是"这个标的的特化赌注"（thesis 脊柱，**知识驱动、会变**）；查 `addresses` 字段。
- A 轴的 ring 合同是"任何 company/industry/arena 都必收的类目"（**type 常量、不依赖具体标的、无循环依赖**）；查 `rings` 字段。

**为什么必须两条**：只有 B 轴时，"任何 company/industry/arena 都必收的类目"（管理层资本配置、一致预期、历史镜鉴）如果不挂具体 K# 就没人管——但它们恰恰是决策链环①②⑤能落地的地板。A 轴把这个地板从 thesis 里独立出来，用 type 常量保证"研究任何标的之前就知道要收什么"，无循环依赖。

---

# Part 2 · 数据对象全表（逐字段 + 状态机）

> 本 Part 是数据层的"字典"。改任何字段前先在这里查它被谁读、被谁写。

## 2.1 topic.yaml — 主状态文件（`topic.py`）

```yaml
slug: cn-catl                       # 唯一标识，全小写连字符
display_name: 宁德时代 (CATL, SZSE 300750)   # UI 展示（可长，含 ticker/英文名）
type: company                       # company | arena | industry | macro
created: "2026-08-01T..."           # ISO 8601
status: active                      # active | paused | archived
stage: 04-synthesizing              # 见 §1.3 stage 机
canonical: true                     # 该 slug 下是否 canonical 变体（dashboard/monitor 展示它）
parent_topic: cn-battery-arena      # 父 slug（跨层复用）；null=无
monitoring_tier: dormant            # deep | watch | dormant
concepts: [...]                     # 概念标签（实测多空，relink 已不用）
scope:
  geo: CN                           # CN | US | GLOBAL
  question: "..."                   # 终局上的赌注（不是自由散文，见 00 Step 1b）
  depth: deep                       # quick | standard | deep
  terminal: "买/卖/持有 + EV + 目标价"  # 由 type 派生（terminal_for_type），核对锚
  ticker: SZSE_300750               # company 必填（{EXCHANGE}_{CODE}）
  market: SZSE                      # 由 ticker + geo 推断（_infer_market）
  extra_tickers: [HKEX_03750]       # AH 双重/ADR/多重上市
  extra_markets: [HKEX]             # 与 extra_tickers 并行
  short_name: 宁德时代               # company 必填（≤12 字，WebSearch 查询用）
  search_terms: [...]               # question >25 字必填（≤15字/项，prescan 覆盖槽 hint）
outputs_state:                      # file-first：只有落地文件才有条目（空 {} 起步）
  00_primer:
    version: 2
    status: fresh                   # pending | fresh | stale | draft
    last_updated: "..."
    referenced_mat_ids: [mat-x,...] # 上次合成引用的 mat（list_affected_outputs 判增量）
    data_freshness: "2026-Q1"
    last_error: null                # {at, message} 或 null（单份产出失败标记）
    critic_passed: true             # primer 门禁机械凭证
    primer_gate: {...}              # 被降级时记 downgraded_from + warnings
thesis:                             # 指针（正文在 thesis_v{N}.md）
  current_version: 1
  last_updated: "..."
  history: [{version, stage_set_at, set_at, summary, prescan_status?, prescan_failure_reason?}]
decomposition:                      # 指针（正文在 decomposition_v{N}.md）
  current_version: 1
  history: [{version, stage_set_at, set_at, summary, convergence_status?, changelog?}]
prescan_log: [...]                  # 后续轮次 prescan 健康度（独立于 thesis 写时状态，H5）
stage_history:                      # 每次 set_stage append（B1 承重墙）
  - {stage, entered_at, exited_at, gap_snapshot: {uncovered_ks, uncovered_ring_inputs, autofetch_debt, empty_pending_decision}}
critic: {verdict, summary, at, thesis_version, next_stage}   # set_critic_verdict 写
user_todos: [...]                   # 见 §2.2
parent_materials: [...]             # 跨层复用父级 findings 引用
suggested_drilldowns: [...]         # 07-drilldown 钩子（capped 命门 / critic 薄弱 K#）
pending_thesis_review: {...}        # daily-monitor 破位待重评戳（自动判消）
monitoring: {enabled, cadence, last_reviewed}
```

**产出状态（`outputs_state[key].status`）语义**：
- `pending`：outputs_state 有条目但未生成（file-first 后极少见，主要是遗留）。
- `fresh`：已生成、资料没更新、视为最新。
- `stale`：有新资料入库 或 critic verdict='request-rewrite' 显式标 → 需重写。
- `draft`：primer 门禁降级专用（depth=deep 但机械检查不过）。

> **file-first 设计**（`topic.py` 顶部注释）：`create_topic` **不再** seed 产出为 pending 死槽。产出只在文件落地时由 `set_output_status`/`set_output_referenced_mats` 的 `setdefault` 惰性注册。首次合成"该产哪些"的枚举由 `list_affected_outputs` 用 `_outputs_for_type(type)` 补出（`_DECISION_CHAIN_OUTPUTS` 表：company=`[00_primer, c_investment_case, 08_living_feed]` 等）。这消除了"未开工却显示 pending primer/case"的死 slot 污染。**遗留 topic 若带旧 8 维并列 key（01_business_panorama…）仍能 graceful 处理**（list_outputs skip-if-absent、list_affected_outputs union）。

## 2.2 user_todos — todo 生命周期（原理 2 的核心）

每条 todo 是 dict（`_normalize_todo` 规范化 + 校验，不合规 raise）：

```yaml
- task: "下载3份对比卖方深度报告"    # 文档身份 = 闭环键
  priority: P0 | P1 | P2
  info_tier: public | half_public | hard   # 信息差等级——只决定努力顺序，不是跳过门槛
  addresses: [K1, K3]                # 攻打哪些 K#（B 轴覆盖标签，可空、多对多）；格式 K# 或 K#@event-slug
  status: pending | in_progress | done
  fetch_status: unattempted | fetched | empty | error   # auto-fetch 规约机械层真实结果
  fetch_attempts: 0
  disposition: undecided | waived | will_collect        # 仅 fetch_status=empty 时有意义
  covered_by: [mat-abc123]           # 被哪些料覆盖
  coverage_note / last_fetch_note / disposition_note / source_hint / archive_candidate: 可选
```

**生命周期**：
```
生成 ──→ 有效尝试抓 ──→ 盖 fetch_status ──→ 状态流转
(00 5.3 /   (产即收:谁产      fetched → done(显式,按task子串)
 01 2/3 /    谁当场收)        empty → 用户决策(waived/will_collect)
 05 6.5)                     error → 必须重试,不降级
```

**三个 info_tier 决定命运**：`public`（一搜就有）应被 01 自动获取消化；`half_public`（需登录/付费/外文，alpha 主来源）深抓尽量消化；`hard`（专家访谈/产业链调研）留给用户。**理论上跑完 01 后 user_todos 里只剩 `hard` + 有效尝试确认 `empty` 的。**

**闭环键 = task/文档身份，不是 K#**（钉死，见 `_autofetch_protocol.md`）：一篇挂 K2 的二手新闻与一条挂 K2 的"年报全文"todo 共享 K2，不代表年报到手。多条不同 todo 常共享同一 K#。因此闭环只走 `mark_todo_fetch(task子串)` + `update_user_todo_status(task子串)`。**旧的 K# 自动撮合（`auto_resolve_todos` / `suggest_*coverage*`）已彻底删除**——它既造假 done 又造假 pending。

**关键脚本**（`topic.py`）：
- `set_user_todos` — 全量覆写；**含 addresses 的现有 todo 时若新传全空则 raise**（防覆写丢字段，H2）。
- `append_user_todos` — 追加（按 task 去重），不覆写。**进度播报用这个 + 传显式 `status='done'/'in_progress'`**（否则默认 pending 污染"待补料"计数）。
- `update_user_todo_status` / `mark_todo_fetch` / `set_todo_disposition` — 按 task 子串改单条。
- `pending_unfetched_todos`（R3 清单）/ `empty_undecided_todos`（empty 硬闸门清单）——auto-fetch 规约的两个查询谓词，被闸门脚本消费。

## 2.3 manifest.yaml — 资料清单（`manifest.py`）

```yaml
slug / variant / updated
materials:
  - id: mat-a1b2c3                   # "mat-{6hex}"，add_material 生成
    filename: citic-catl-2024.pdf
    source_type: sell-side-note      # 见下枚举
    added / processed: true/false
    notes: "..."
    mineru_state: needs | in_progress | done | failed | not_needed
    addresses: [K1, K3]              # B 轴标签（挂 K#）
    rings: [financial-arc, ...]      # A 轴标签（挂决策链输入合同 code）
    confidence: 0.8                  # 主要 web-search 料
    search_meta: {query,url,domain,domain_tier,searched_at,stale_at,expire_at,triggered_by,prev_queries?}
    parent_mat / sec_section: ...    # SEC 切片子 mat
```

- **source_type 开放词汇**：`sell-side-note` / `annual-report` / `industry-research` / `web-article` / `manual-note` / `policy` / `web-search` / `announcement` / `sec-section` / `data` / `finding` / `drilldown` 等。
- **mineru 路由**（`_default_mineru_state`）：sell-side/industry/policy 类 PDF → `needs`（走 mineru-vlm 保真表格）；年报 → `not_needed`（走 `annual_report_extractor`，pymupdf，mineru 有 200 页限）；非 PDF → `not_needed`。
- **web-search 时效**：`stale_at`=30 天、`expire_at`=90 天（`make_search_meta`）。`list_expired_web_search` 给 daily-monitor 重扫。
- **triggered_by 分层**（关键机制）：标记 mat 由哪一步入库。`_DEFAULT_EXCLUDED_TRIGGERED_BY`=(`00-prescan-baseline`,`00-prescan`,`01-prescan`)——这些 Role α prescan 料在 `list_unprocessed`（不进 03 抽取队列）+ `list_affected_outputs`（不触发 04 重写）两层被默认排除，因为它们在 baseline §6 + roadmap 阶段已消化进 thesis。Role β（`02-step0`）/ Role γ（`03/04/05` 即兴）正常计入。
- **rings 默认打标**（`input_contract.default_report_rings`）：财报 fetcher 按 report_type + topic.type 自动打 rings（年报→`financial-arc/mgmt-capital-alloc/biz-moat-unit-econ`，industry→`industry-financial-arc` 等）。03 抽取时按实际内容在 finding frontmatter 精修。

## 2.4 thesis / decomposition — 两条版本化脊柱

- **thesis_v{N}.md**（B 轴脊柱）：K#（Killer Question）住在这里。`extract_killer_questions` 靠正则 `\bK\d+\b` 抽编号；`extract_k_status` 按 thesis 的「命门/K# 现状表」第 3 列置信度判 supported/refuted/unverified。
  - v0：五段式（核心 thesis+强度 / 支持 / 反方 / K#），00 Step 5.0 写。
  - v1+：**Scheme C 全快照 11 段式**（`_shared.md`）——每版本自包含、不依赖 v{N-1}，顶部带 changelog。禁止"见 v{N-1} §X"引用。
  - `set_thesis` 副作用：v≥1 时跑 `mark_outdated_ks`（标上版有本版无的 K# 为 archive_candidate）+ `reverse_check_roadmap_coverage`（K# 未在 roadmap L4/material 闭环 → 写 todo + 翻 `01-roadmap-reopen`）+ 触发 dashboard 重建。prescan_status='failed' 未传 force_failed 时 raise。
- **decomposition_v{N}.md**（B 轴的另一半）：命门（机理/兑现路径特化问题）+ primer 入门目标，共住一份。**命门 ≠ K#**——K# 是"可证伪的会改变看法的事件"（覆盖轴，喂 gap_detector）；命门是"方向错了就翻盘的特化问题"（终局拆解轴，映射到决策环）。
  - v0：00 Step 5.4 用薄知识起草（命门置信度 tag + 每环 B 靶点 + primer 入门目标种子）。**不做 LLM critic**（薄拆解可靠性无法认证），只做置信度 tag + 机械自检。
  - v1：04 写作期做**有界 delta 重拆**（读完 findings 后逐条 diff v0，硬顶 2 轮防无限螺旋）。`convergence_status ∈ {open, converged, capped}`；capped→踢 07-drilldown。
  - `set_decomposition` 不做 prescan/reverse-check（它是合成活动前移物，闸门在 04 delta 重拆）。

## 2.5 outputs/ 目录 — 产出文件

| 文件 | 谁产 | 消费者 |
|------|------|--------|
| `00_primer.md` | 04 各路径 Step 2（primer-first） | 门外人 + case 站其上 |
| `_prism_reading_guide.md` | 从 `_reading_guide_canonical.md` 复制 | 读者（prism 系统约定，跨 topic 通用） |
| `{c/i/a}_investment/industry/arena_case.md` / `m_regime_read.md` | 04 主 agent 直做 | 决策者 + 05 critic + web output 页 |
| `07_decision_kit.yaml` / `industry_to_arenas.yaml` / `peer_matrix.yaml` / `transmission_map.yaml` | 04 Step 4/6.5 | **dashboard + monitor 直接消费**（严格 schema） |
| `findings_*.md` | 03 抽取 / 04 即兴 web-search inline | 04 合成、gap_detector、诊断页 |
| `_findings_index.md` | 03 Step 3.5 / 04 `build_findings_index` | 主 agent 防 compact 的"地图" |
| `_synthesis_brief.md` | 04 Step 4 | 04 后续环 + critic 的 v0→v1 校准锚 |
| `08_living_feed.md` | 05 / 06 追加 | 时间线 |
| `05-critic-review.md` | 05 Step 5 | 诊断页 |
| `macro_stamp.yaml` / `regime_eval_log.yaml` | company / macro | macro 横切层（Part 5） |

**渲染**（`outputs.render_markdown`）：统一入口，先剥 frontmatter、补表格/列表空行（python-markdown 要求），再交扩展。正文 `mat-XXX` 引用被 `linkify_mat_refs` 包成指向诊断页的链接（tag-safe，只在文本段替换）。

---

# Part 3 · 决策链合成（04 的核心 · case 的骨架）

## 3.1 理解先行 + 6 环决策链（契约本身）

04 合成的元目标（`_company_case.md` §1.1，逐字不改）：

> **一个门外人为了做出买/卖/不动的决策，正在研究这家公司。先让他读懂这门生意所在的领域与公司本身（primer）；再带他走完一条决策链：看懂生意 → 市场定了什么价 → 这价要什么为真 → 我信哪边 → 错了怎么知道 → 那就怎么做。**

**primer 与 case 分工（杀重复，硬规约）**：

| | 谁先生成 | 读者 | 干什么 |
|--|--|--|--|
| **00_primer** | 先（理解地基） | 完全门外人 | 看懂领域/公司本身，不被术语挡住 |
| **case** | 后（站在 primer 上） | 要做买卖决定的人 | 该不该买、什么价、会怎么错 |
| **thesis_v1** | 最后（提炼快照） | 持有期追踪者 | 把下好的注提炼成可追踪快照 |

生成顺序 = 阅读顺序。case 环① **已假定读者读过 primer**，只留决策导向速写，背景深度写"详见 primer"。

**6 环决策链**（紧的因果序，非并列箱，`_company_case.md` §1.3）：

```
① 能不能看懂这家公司？     —— 闸门（三梁：生意/护城河/单位经济 + 管理层资本配置 + 多年财务轨迹）
② 市场此刻替它定了什么价？ —— 锚（反推隐含预期，必须有数字；先拉实时同业倍数再谈估值）
③ 需要什么假设为真？       —— WMBT（把②翻译成 3-5 条可证伪假设）
④ 我信哪边，凭什么？       —— 下注（多空 + 核心分歧锚回②的隐含数 delta + 期望收益 EV 加总）
⑤ 错了会怎样、怎么第一时间知道？—— 证伪（风险 + ≥2 历史失败镜鉴 + kill 触发 + signpost）
⑥ 什么价/仓位/时点做什么？ —— 行动（买入框 + 仓位档位接④的 EV + 阶梯）
```

**为什么链是紧的**：③只因②产出定价才存在；④的 EV 加总把光谱压成一个数；⑥的仓位由④的 EV 决定；⑤只因④下注才需要。**断链**（有④无⑤、有⑥无②锚、⑥仓位不接④的 EV）是 chain-critic 必查项。

**industry/arena 的环⑥折入选拔**：industry 环⑥ = arena 三档分流（深挖/观察/淘汰，tier=吸引力×当前定价）+ 落 `industry_to_arenas.yaml` + 建 arena stub；arena 环⑥ = peer shortlist + 落 `peer_matrix.yaml` + 建 company stub。旧的独立 `09-arena-shortlist`/`10-peer-matrix` stage 已退休，选拔是 04 合成期 case 环⑥的产物。

## 3.2 每环的"必带硬落地"（决策机制保证）

每环给"必须落地什么"（不给固定子节模板，子问题/表格/详略在自由区）。关键硬落地（决定 chain-critic 判断）：

- **环①三梁缺一不可**：生意与护城河（含≥1 组单位经济数字）/ 管理层与资本配置（track record + 资本配置历史 + 激励治理，长期持有的一等公民）/ 多年财务轨迹（3-5Y ROIC/FCF 走势 + 拐点，来自 `get_financial_context`）。
- **环②数字最硬**：**强制先用 `.venv/bin/python` 调 `market_data.get_valuation_context_by_tickers` 现采实时同业倍数**（不靠 findings 手抽——findings 里的行情有保质期，pre-IPO/剧烈波动时数月漂 40%+，见 cn-momenta 教训 + memory `market-data-ps-currency`）。反推隐含 CAGR/终值 PE/IRR + 选 2-3 估值模型（`_valuation_models.md` 原型表 + 模型 A–H）。
- **环④核心分歧锚回②的 delta**：把分歧落成"我 vs 市场已定价的那个数"的 delta，咬同一条 driver 同一组单位。**只铺多空辩论不落 delta = 没回答命门**（共识已在价里，照着买不赚钱），chain-critic 必查。EV 加总 = Σ(各档概率×回报中点)，喂⑥的仓位档位。
- **环⑥仓位先定档位**（`position_tier` 试探/标准/重仓）：`initial_max_pct` 是档位的人工落点不是算出来的，给不出有据的数就填 null，禁用拍出来的精确 % 伪装严谨。

## 3.3 04 的执行骨架（`_shared.md` 是共享工具库）

三类 type 走各自路径文档（`_company_case.md` / `_industry_funnel.md` / `_arena_funnel.md` / `_macro_regime.md`），**都引用 `_shared.md`** 的：前置检查 / gap 双轴体检 / 增量重写判定 / 断点续跑 / 调度模式 / thesis_v1 Scheme C / B 轴 delta 重拆 / 即兴 web-search。

**执行顺序**（company 为例）：
0. **empty 硬闸门**（`empty_undecided_todos` 非空 → AskUserQuestion 逐条处置，全决策完前不进决策链）。
0.5. **质量红线门控**（company 专属，`get_quality_screen_data` → PASS/FAIL/NEEDS-REVIEW；FAIL→quarantine）。
1. 加载 findings（`format_findings_for_prompt` 列路径 → 主 agent 并行 Read）+ 财务数据（`ensure_financials` + `get_financial_context`）+ 亲属 hook（`get_relative_outputs` 取父/子成稿产出**路径**，脚本只返路径不读内容）+ macro 横切 hook（company 强制，读 transmission_map + 落 macro_stamp）。
2. **先出 00_primer**（primer-first，`00-primer.md` Step 1-5，critic 不可省）。
3. 走 6 环写 case（主 agent 直做 + 并行 Write）+ 写 sidecar。
4-6. 状态注册 + thesis_v1/decomposition_v1 + 内嵌 chain-critic + stage 推进到 05。

**调度模式：主 agent 直做 + 并行 Write（默认，不 dispatch subagent 写长产出）**。原因（`feedback_subagent_bulk_synthesis`）：subagent 批量合成撞 60min 硬墙 + Write 幻觉重试，实测两次 0 落盘。唯一 subagent 是 critic（只读不写）。防 compact：`build_findings_index` 落盘轻索引（每份 finding 一行，22 份≈3-5K token vs 全文 40K），每环开始前 Read 索引定位本环需要的 mat_id。

**增量重写判定**（`list_affected_outputs`）：比对 `outputs_state[key].referenced_mat_ids` vs manifest 当前 processed mat_ids，分 new/stale/critic-stale/fresh。fresh 跳过。**写完每份必调 `set_output_referenced_mats`** 注册引用（否则下次仍判 new/stale 浪费 token）。`ws-aggregate-*` 虚拟 ID 由 `_expand_aggregate_refs` 展开（读 finding frontmatter 的 `aggregated_from`），防止聚合 finding 导致 84 条真 mat 全判 new 的死循环（cn-commercial-space 教训）。

## 3.4 sidecar — dashboard/monitor 的硬契约

sidecar YAML **严格 schema、禁自创字段**（自创 `thesis_strength`/`killer_questions` 会破坏 dashboard 消费）。schema 单一事实源在各 spec 文件：`_decision_kit_spec.md` Step 3.5（company）/ `_arena_select_spec.md` Step 6.5（industry）/ `_peer_matrix_spec.md` Step 6.5（arena）。

**company `07_decision_kit.yaml` 关键字段**：`buy_box`（分档价格 + current_zone）/ `position_framework`（position_tier + sizing_rationale + initial_max_pct + add_ladder_prices）/ `valuation_models` / `kill_criteria`（id + status + check_at）/ `signposts`（date + bull/bear_signal + triggered）/ `cluster_tags`（英文 kebab，relink 交集用）。

**可观测字段是 sanctioned schema 的一部分**（不算自创，纯被动给诊断页/探针用）：`chain_links`（`rings_present` + `r4_anchors_r2`/`r6_takes_r4_ev`/`r5_has_kill_signpost` 三布尔，被动断链探针 04.Q1 读）/ `honest_gaps`（诚实缺口列表，04.Q3 读，无缺口写 `[]` 别省字段）/ `market_implied` + `my_vs_market_delta`（B4，环④ delta 锚回②的同指标校验，04.Q2 读）。

---

# Part 4 · auto-fetch 规约（"产即收" · 原理 2 的完整机制）

> 单一事实源：`_autofetch_protocol.md`。被 00 Step 6.5 / 01 Step 5.6 / 02 Step 5.7 / 03 Step 2.4 / 05 Step 6.5 共享引用。

## 4.1 总规约：产即收

**谁产 todo，谁当场收。** 任一阶段写下 todo，立刻在同一阶段跑 auto-fetch 盖 `fetch_status`。

- **下游只消费已入库的料，绝不替上游补抓**。00 产的 todo 在 00 Step 6.5 收；01 只补抓自己 Step 2/3 新增的 + 按 R3 重试上游遗留的 `error`。
- **prescan（事实校准）永不碰 todo 闭环**。prescan 只入库校准事实（标 `addresses=['scope']`）+ funnel + 写 log。
- **闭环只走文档身份**（task 子串），脚本侧无任何 K# 自动撮合。

## 4.2 三条规约

- **R1 全覆盖**：所有 tier（含 tier3）、所有 info_tier（含 hard）都要尝试。**info_tier 只决定努力顺序/强度，不是跳过门槛**（hard 先上 exa advanced + 权威 URL WebFetch；public 可单跑 adapter）。
- **R2 有效尝试**：一次有效尝试 = 搜索真跑了、公开确实没有 → 才可降级。工具/网络/限流故障**不算尝试**，必须重试。
- **R3 消费前兜底**：消费某 todo 的材料前确认它已被有效尝试（逐环/合成前钩子）。

## 4.3 fetch_status 三态 + 判定表

| 盖什么 | 何时 | 后续 |
|--------|------|------|
| `fetched` | 抓到这条 todo 要的文档并入库 | 按 task 子串显式 `update_user_todo_status(...,'done')` |
| `empty` | **有效尝试**确认公开无源 | 触发 empty 硬闸门 → 用户 waived/will_collect，不静默写缺口 |
| `error` | 工具/网络/限流失败 | **必须重试，永不降级**；R3 下轮再试 |

**关键判定**（web-search 阶梯）：`EXIT_NO_HITS=20`/`upstream_empty`（provider 有响应但 0 命中）= 有效空可降级；`EXIT_ALL_EXHAUSTED=40`/`RuntimeError('all providers exhausted')`（key 冷却/耗尽）= transient 必重试；`all_low_band`（有命中全被判低质）= 先走 H2 救回再判。**绝不能把 40/50 当"公开没有"。**

**报告抓取**（`fetch_report_prism`）：返回 Path/list=fetched；`ValueError`（"No report found"）=有效空 empty；重试耗尽的网络异常=error。

## 4.4 web 取数三件套 + 降级阶梯

| 工具 | 干什么 | 触发点 | 降级 |
|---|---|---|---|
| **prescan**（`web_prescan.py` + `_web_prescan_shared.md`） | 校准**事实**（数字/事件），近 90 天主动拉 | 00 Step 4.5 / 01 Step 8 / 02 Step 0 | 事件轴由主 agent 按领域自定（不套固定后缀，F3 病根）；`check_prescan_health` 检测 failed |
| **deep-fetch**（01 Step 5.6 / 00 Step 6.5b） | 获取**分析材料**（研报/裁决全文） | 收料期 | adapter sidecar → exa advanced → `web_fetch_exa`；只有 hard 或全搜无果才留 user_todo |
| **fetch_report_prism** | 自动下**结构化财报** | 01 Step 5.5 / 00 Step 6.5a | 按 ticker 路由：US→SEC EDGAR / CN→cninfo / HK→HKEXnews / UK→FCA NSM / KR→DART / JP→TDnet+EDINET |

**默认 sidecar-first（token 中性质量）**：搜索正文默认落盘、context 只承载 review-digest 投影——判 tier 靠 host/标题/flags（不需全文），关键数字在 highlights/snippet。exa `web_search_advanced` 的 `text` 字段全文直灌 context 是最大自造 token 成本（实测一轮 40-60K tok、利用率 <20%），**默认不取**；需通读的少数走 `web_fetch_exa` 精准抓选定 URL（落盘复用）。

**web_search adapter 架构**（`web_search.py` + `router.py` + `providers/`）：`classify_intent`（news/semantic/exact/vertical/general 启发）→ `rank_providers`（按 intent 给 provider 打分、过滤不 healthy）→ 逐 provider 尝试。domain_tier（`whitelist`/`llm-judged-official`/`other`）由主 agent 判（H2 教训：脚本只做 deterministic 测量 `extract_url_features`，不返回 tier/confidence）。`funnel_band`：confidence≥0.8=high、≥0.5=mid、<0.5=low（丢弃不入库）。白名单晋升（`_promote`）：同族同 host 被判 official ≥2 次 → 进 overlay。

**财报抽取工具分工**：卖方/行业研报**必须走 mineru-vlm**（表格/公式/多栏保真）；财报**走 `annual_report_extractor.py`**（pymupdf find_tables + TOC 切节；mineru 200 页限会撞墙）。SEC 10-K/10-Q 下载时自动 `sec_section_split` 切片 `item_*.md`。

## 4.5 财务两条管别混（reference）

- `market_data`：出倍数（PE/PS/市值，A 股可取）。`get_valuation_context` / `_by_tickers` / `get_quote`。A 股行情主力源 Sina（`stock_zh_a_daily/minute`），不走 eastmoney。**中概股 P/S 曾因不换汇算错**（memory `market-data-ps-currency`）。
- `financial_data`：出基本面（`ensure_financials` + `get_financial_context`：3Y ROIC/FCF/毛利率/资产负债率/商誉占比）。
- 二者合成期自动拉（gap ring 轴标 `api_pending` 非红），给 ticker 即可。

---

# Part 5 · macro 横切层（宏观体制 + 传导地图）

> macro 是**横切层**，不是第五种平行 topic：其余 company/arena/industry topic 的 case 通过 `macro_stamp` 挂到唯一的 macro topic（`global-macro-rates-liquidity`）上。相关脚本：`macro_registry.py`（输入登记表）/ `eval_snapshot.py`（评估快照）/ `macro_xcut.py`（company 侧接入 + staleness）/ 各 `*_fetch.py`（数据源）。workflow：`04-synthesize/_macro_regime.md`。

## 5.1 macro 因果链（四层，`_macro_regime.md` §1）

```
[L1 输入源] → [L2 驱动变量]   → [L3 目标·三体制读数]      → [L4 传导·决策]
   数据          增长/通胀        利率 / 流动性 / 汇率          每持仓敏感度
              政策反应/财政      (各自小框架 + 大白话)         → 仓位/久期倾斜
```

- **左半段 = 输入**（L1 数据源 + L2 驱动变量：增长/通胀/政策/财政，是利率/流动性的上游）。
- **中段 = L3 三体制**（利率/流动性/汇率，各自小框架把"输入怎么变成体制读数"讲透）→ `m_regime_read.md`。
- **右段 = L4 决策**（`transmission_map.yaml`：三体制 → 四条传导渠道（贴现率/风险偏好/carry-久期/汇率）→ 每持仓敏感度 → 组合倾斜）。
- **地理主线**：美国/全球为主线、中国第二块（全球利率/流动性总闸门在美国；汇率对以 A股/中概为主的组合不可省）。

产出：`00_primer.md`（全链入门）+ `m_regime_read.md`（L3 活读数）+ `transmission_map.yaml`（L4 sidecar）+ thesis + decomposition。

## 5.2 macro_inputs.yaml — 输入登记表（`macro_registry.py`）

与 manifest 刻意分离：manifest 存"资料/搜索 hit"，本表存"会影响利率/流动性/汇率判断的输入"及其机制边。每条 input entry 关键字段：

- `name`（唯一键）/ `tier`(A/B/C) / `cadence_type`(event/series/policy) / `targets`([rates/liquidity/fx]) / `mechanism`(CD/CF/CO/CR) / `importance`(load_bearing/confirming/background)。
- `causal_sentence`（CD/CF 必填的因果链）/ `family`（CANONICAL_FAMILIES 分组）/ `gloss`（门外汉三层词条 define/read/use）。
- **取数成本轴 `availability`**：`scripted`（脚本直拉零 LLM 便宜）/ `scriptable_todo`（能转脚本但 recipe 待写）/ `llm`（每轮 LLM 读或检索，贵）。
- `fetch_method`（scripted 项的数值通道：fred-api/recipe/akshare/yfinance/macromicro/barchart/ecb/safe/cftc/mofcom/fedwatch/fomc_sep）/ `text_fetch`（取文通道：fomc/qra/china_us/hfcaa/politburo/pbc_mpr/fed_speech，与 fetch_method 互斥）。
- `observed`（运行时位：value/prev_value/z/as_of/next_due/stance/fingerprint/checked_at/fetch_error）。

**机制纪律 validator**（`validate_registry`）：tier A ⟹ mechanism∈{CD,CF}；CD/CF ⟹ causal_sentence 非空；alert_series=True ⟹ cadence_type=series；stance 须在 stance_scale 轴内且附 evidence；gloss 三键齐全。

**policy 立场轴**（`STANCE_SCALES`）：把无市场序列可 diff 的事件叙事（鹰鸽/松紧/地缘）落成可 diff 的有序档位，使 LLM 判读进 `observed.stance` → 被 eval 战绩/翻牌消费。

## 5.3 评估快照 regime_eval_log.yaml（`eval_snapshot.py`）

"输入→判断"可溯源的脊梁：每次（重）写 regime_read 时经 `append_evaluation`/`record_evaluation` 落一条 evaluation（`input_snapshot` 列全所有输入 + `conclusions` 按结论挂输入的 `based_on`）。之后 diff/简报全由脚本零-LLM 派生：
- `_validate_evaluation`：input_snapshot 不能漏列输入；based_on 不能悬空引用；load_bearing 边须有 expected 方向预测；prior_verdict 须 held/partial/wrong。
- `diff_since_last`：比现 observed.value vs latest 快照值 → changed/breached/direction。
- `assemble_reeval_brief`：变化项 + 到期/越带 + 受影响结论 + 未抓盲区（诚实盲区提示）。

## 5.4 company 侧接入（`macro_xcut.py`）

- **macro_stamp.yaml**（company `outputs/`）：记该 case 站在哪版 regime + 依赖哪些体制状态（`depends_on_states`，role∈load_bearing/confirming/background）+ 贴现率。company case Step 1 macro hook 强制落。
- **staleness 扫描**（`scan_holding_staleness`）：比 company 依赖的体制状态 vs 最新 regime eval，变了则 stale。`apply_holding_staleness` 给 stale 持仓盖旗 + 写 `kind='macro_regime'` proposal（信息型，stage 不动）。
- **coverage_gaps**：company-type topic vs transmission_map holdings → 漏注册 + provisional，显式暴露"沉默≠确认"。
- **自注册**（`register_holding_row`）：company case 若不在 transmission_map，自判一行四渠道标签写回（标 provisional 待 macro 复核）。

**软降级**：无 macro topic / 无 regime eval → 标"无宏观基准"，仍落 stamp（`as_of_regime_version: null`），不阻塞 case 合成。

---

# Part 6 · 被动可观测层（把"静默"变"可审计"）

> 脚本：`observability.py`（`run_probes`）+ `observability_render.py`。spec：`prism/specs/observability.md`。**纯被动 · 零 LLM · 零建设**——从已有产物残留重建流程质量诊断，不新增写入义务。web `/checkup` 页展示。

## 6.1 探针族与状态

`run_probes(slug, variant)` 返回一组 Probe。三族：`produce`（产出）/ `quality`（质量）/ `pitfall`（坑）。四状态：`pass`/`fail`/`flag`/`na`。三 tier：1=机械重建可靠 / 2=机械代理（挂旗给人）/ 3=纯判断（只挂旗）。

**探针从哪读数据**（这是"零建设"的关键——全从既有残留重建）：
- gap_detector 报告（`autofetch_debt` / `empty_pending_decision` / `uncovered_ks` / `thin_evidence`）。
- topic.yaml（todo 字段 / stage / critic / stage_history 的 gap_snapshot）。
- sidecar 的可观测字段（`chain_links` / `honest_gaps` / `market_implied` / `my_vs_market_delta`）。
- findings frontmatter（source/quality/conflicts_with）、web_search_log、manifest。

## 6.2 探针清单（按 stage）

| 探针 | 查什么 | tier | 数据源 |
|------|--------|------|--------|
| CC1 | active todo 都带 addresses | 1 | todo.addresses |
| CC2 | 无假 pending（pending 但已 covered/fetched） | 1 | pending + covered_by/fetch_status |
| CC3 | autofetch 欠账（unattempted/error） | 1 | gap.autofetch_debt |
| CC4 | empty 待用户决 | 1 | empty_undecided_todos |
| CC5 | 无假覆盖（带 @event 锚的 covered todo 须事件锚匹配） | 2 | addresses_match_event_anchored |
| CC6 | P0 pending 进 04/05 前已收敛 | 1 | P0 todo.status + stage |
| 00.Q1/Q2/Q4 | prescan 未 failed / K# 可证伪 / 命门标置信度 | 1/3/2 | prescan_status / decomposition |
| 01.Q1/Q3/X3 | 5.6 跑了 / 剩 pending 只剩 hard+无果 / ticker 填了 | 1 | fetch_status / info_tier / scope.ticker |
| 02.Q2/Q3 | K# 红项 / ring 输入红项 02→03 是否带着硬升 | 1 | stage_history gap_snapshot diff |
| 03.Q1/Q3 | findings 标 source/quality / 冲突证据被识别 | 1/2 | findings frontmatter |
| 04.Q1/Q2/Q3/X1 | 断链 / ④锚回②delta / 诚实缺口 / 无硬合成占位 | 1/2 | sidecar chain_links + case 文本 |
| 05.X1/Q1/Q2/Q3 | failed prescan 却 approve / 反方真 steelman / verdict 与评分一致 / request-more todo 合规 | 1/3 | prescan_status + verdict + todo |
| 06.Q1 | 巡检对 signpost/kill 而非泛新闻 | 2 | monitor_queue vs sidecar |

**诚实 na 的探针**（盲点显式化，不伪造 fail）：`04.X2`（*-mirror 复用起手标红属预期，无法结构暴露）/ `00.X1`（Q#/V# 第三维已废，Q# 被合法复用机械扫必误报）/ `01.Q2`（"三项真欠供"无法机械枚举）——这些明写"被动层判不了"，避免假信号。

## 6.3 stage_history 与 gap_snapshot（B1 承重墙）

`set_stage` 每次切换：回填上一条 exited_at + append 新条目（含进入瞬间的 `snapshot_gaps` 精简快照：uncovered_ks / uncovered_ring_inputs / autofetch_debt 数 / empty_pending 数）。这让 02.Q2/Q3 能算"红项被处理 vs 红着硬升"——对比 02 进入快照 vs 03 进入快照的红项交集。这是**唯一为可观测层新增的写入**（其余全被动重建）。

---

# Part 7 · Web / dashboard / monitor（消费层）

## 7.1 Web 路由（`app/routes/prism.py`，只读为主）

| 路由 | 页面 |
|------|------|
| `GET /prism` | 主题森林（`build_topic_forest`，按父子/tier 组织） |
| `GET /prism/dashboard` | 决策仪表盘（读 `dashboard.md`，`?refresh` 重建） |
| `GET /prism/{slug}` | slug 下变体列表 |
| `GET /prism/{slug}/{variant}` | 主题详情（stage 进度条 + 产出状态 + thesis coverage strip + todo + 监控 + 建议深挖 + macro banner） |
| `GET /prism/{slug}/{variant}/diag` | 诊断页（findings / critic artifacts / roadmap / parent materials / mat 溯源） |
| `GET /prism/{slug}/{variant}/checkup` | 被动可观测探针页（`run_probes` 渲染） |
| `GET /prism/{slug}/{variant}/{output_key}` | 单份产出渲染 |
| `GET /prism/{slug}/{variant}/thesis/{version}` / `.../macro-inputs` / `.../transmission-map` / `.../eval-trace` | 版本化脊柱 / macro 登记表 / 传导地图 / 评估溯源 |
| `POST .../mark-done` / `set-canonical` / `reeval` / `macro-inputs/fetch-*` / `monitor/*` / `watchlist/*` | 少数写操作（标完成 / 切 canonical / macro 取数 / 监控确认） |

**单向数据流**：用户对话 → Claude 执行 workflow → 脚本写文件 → web 自动反映。web 的写操作限于状态标记 + 触发 headless 取数，不做 LLM 判断。

## 7.2 dashboard（`dashboard.py`）

`build()` 渲染 `prism/dashboard.md`：Section 0 macro banner（体制读数 + 高暴露持仓）+ company 决策行（现价 vs buy_box zone + kill 触发 + freshness）+ arena/industry 行（sidecar 分流/矩阵）。canonical variant 由 `canonical_variant` 解析（对齐 monitor）。**fire-and-forget 自动重建**：`set_output_referenced_mats` / `set_critic_verdict` / `set_thesis` / `set_decomposition` / `set_suggested_drilldowns` 后异步 subprocess 重建（~25s 后台跑，主流程 <100ms，失败仅写 `logs/dashboard_auto.log`）。

## 7.3 daily-monitor（`monitor.py`，旁支 06）

三件机械事（零 LLM）：
1. **watchlist**（`watchlist.yaml`）：用户 web 勾选的关注清单。**成本由它而非 topic 总数决定**——不在清单的 event 永不触发昂贵自动搜。scope=topic（跟全部 event）/ event（跟某条 signpost/kill/price）。
2. **scan**（`scan_due_events`，只读）：遍历 watchlist → 按 type 读 sidecar → 挑到期项分桶。signpost/kill 是"候选"（交 headless claude 判读）；price 零 LLM 直接成 proposal；macro 读 macro_inputs 登记表分桶；industry/arena 无 dated signpost 走周期重扫。
3. **queue**（`monitor_queue.yaml`）：staging。proposal 由 headless 判读或本模块（price/macro）写入；用户 web confirm 后 `confirm_flip` 机械回写 sidecar + 追加 living_feed + 注册证据进 web_search 库（addressed 到 signpost/kill 锚点、`triggered_by='06-daily-monitor'`，让 05 gap 体检数得到）。confirm 永远零 LLM。

**破位喂 05**：重大翻牌（kill 触发 / signpost 翻 bear，`requires_thesis_review=True`）→ `set_pending_thesis_review` 盖戳，详情页常驻横幅。跑过 04/05 后 `get_pending_thesis_review` 因 critic.at/thesis.last_updated 晚于破位 since 自动返回 None，横幅消失（无需手动清）。

**web-server 自动拉起**：每日 6:00 通过 `claude_runner`（headless `claude -p`）跑巡检。关键约束：显式继承 `os.environ`（headless 要读 `~/.claude/settings.json` 的 MCP env / web-search key，不继承 = 自动搜静默失效）。

---

# Part 8 · 设计理念 × 踩过的坑（H-fix 归纳）

> 把散落在 workflow 里的 H-fix / drift 修复 / PRISM_VALIDATION 病根，归纳成「理念 → 当初为何踩 → 现在怎么防」。这既是历史记忆，也是"改这块要小心什么"的清单。

| 理念 | 当初踩的坑 | 现在怎么防 |
|------|-----------|-----------|
| **事实先于赌注** | 纯训练知识写 thesis_v0，把过时事实当赌注 → K# 偏航 | 00 Step 4.5 必跑 prescan；`check_prescan_health` 机械检测 failed；`set_thesis(failed)` 强制 force_failed |
| **搜索用关键词不用问句** | question 长句问号喂 WebSearch 常返空（H4） | L4 用 `search_keywords` 短词组；create_topic 长 question 强制 search_terms |
| **事件轴按领域自定** | prescan 对所有行业写死后缀"产能变化"（F3 病根） | 事件轴由主 agent 按领域自定，不套固定后缀 |
| **先自动获取再降级** | tier1 资料默认全变 user_todos，甩锅用户 | auto-fetch 规约 R1/R2；01 Step 5.6 + 00 Step 6.5b 先深抓，只 hard/无果留 todo |
| **todo 结构不可覆写** | `set_user_todos(list[str])` 全量覆写丢 addresses（H2） | 含 addresses 时 raise；进度提示用 append + 显式 status |
| **pending 仅留真待办** | 进度播报落 pending → web 误计"待补 N 份" | 里程碑播报传 `status='done'`，绝不落 pending |
| **闭环键=文档身份非 K#** | K# 撮合既假 done 又假 pending（一个 K# 多条 todo 共享） | 删 `auto_resolve_todos`；闭环只走 task 子串显式盖 |
| **覆盖判定要够细** | `addresses=K#` 粒度过粗 → Q1 材料误覆盖 Q2 todo | 加事件锚 `K#@event`（`addresses_match_event_anchored`） |
| **二维足够，别加第三轴** | 旧版 Q#/V# 与 K# 双轨、与 todo 重复 | 收敛为 K#（thesis 脊柱）+ todo.addresses；Q#/V# 已废 |
| **主 agent 直做大合成** | bulk synthesis dispatch subagent 撞 60min 硬墙 | >30K token 或 >40min 主 agent 直做 + 并行 Write |
| **dispatch 嵌硬规约** | subagent 脑补"Write 被拦截"幻觉（本仓无 write hook，见 memory `subagent-write-hallucination`） | dispatch prompt 原文嵌硬规约 + retry；只信主 agent 的 ls |
| **抽取工具按料型选** | 卖方研报用 pymupdf 丢表格；财报用 mineru 撞 200 页限 | 研报走 mineru-vlm；财报走 annual_report_extractor |
| **来源主动分层** | prescan 非 whitelist hit 默认 confidence=0.4 被丢弃 | 行业垂直/海外/券商源主动标 `llm-judged-official`；脚本只测量不判 tier |
| **sidecar 严守 schema** | 自创 thesis_strength/killer_questions 破坏 dashboard | 写前 grep 模板；禁自创字段 |
| **镜鉴红是预期** | 复用起手 `*-mirror`（环⑤）必标红被误当可补缺口 | 从训练知识补镜鉴 + 明标"训练知识估算/depth 降级"，不回 02 搜料 |
| **primer 深度不许假冒** | depth=deep 用 outline 假冒、省 critic | `primer_quality_gate` 机械门禁：注册前必 `set_output_critic_passed` + 正文含争议节/自检节/过字数地板，否则自动降 draft |
| **thesis 文件不许错位** | 派生 stub 的 thesis 写进 outputs/ 致 5.7 空过（memory `prism-thesis-file-misplaced-outputs`） | thesis_v{N} 必在 variant 根（与 decomposition 同级）；`validate_roadmap_thesis_coverage` thesis_missing 强制 ok=False |
| **prescan 状态读写分离** | 后续轮次 prescan 回写 thesis 顶层污染写时状态（H5） | thesis 写时状态只在 history[version]；后续轮次走 `set_prescan_log`；读用 `get_current_prescan_status` |
| **公告不一把梭** | `with_announcements` 默认拉全年公告灌爆抽取队列 | 默认 False；改 list→LLM 标题分诊→按选下载（memory `prism-announcement-category-gap`） |
| **A 股一致预期查真源** | WebSearch 查 consensus 返幻觉散文（memory `prism-websearch-cn-consensus`） | 用 serper/tavily/exa 拿真实 URL（同花顺 F10/dfcfw） |
| **诊断不是 gate** | （双刃）gap 报红不阻止前进 → 薄弱论证蔓延到下游 | 弹性换跑偏风险，靠 04/05 兜底 + 被动可观测层（Part 6）把静默变可审计 |

---

# Part 9 · 迭代优化 / 简化设计 · 取舍清单

> 你的目标是**不重构、慢慢迭代优化、简化设计**。这一 Part 把系统按"可安全动的地方 / 动了会牵动谁 / 哪些是承重墙别碰"分类，给出改动时的判断依据。改任何东西前先在 Part 7 找它的耦合点。

## 9.1 五个承重墙（改动成本极高，建议不碰）

1. **原理 1（LLM 判断 / 脚本 CRUD 分离）**——整个系统的形态由它决定。任何"让脚本做判断"的改动都是逆流：会把质量锁死在写代码那天。要提升判断质量应改 workflow 提示，不是把逻辑写进脚本。
2. **两条覆盖轴解耦（B=addresses / A=rings）**——它们分别查不同字段、服务不同目的（特化赌注 vs type 地板）。合并会重新引入"必收类目没人管"的循环依赖问题。
3. **闭环键 = 文档身份**——已经血泪删过 K# 自动撮合。任何"按 K# 自动 done/pending"的想法都会复活假 done+假 pending。
4. **sidecar 严格 schema**——dashboard/monitor 直接消费，字段名是硬契约。改字段必须同步改 spec + dashboard.py + monitor.py + observability.py 四处。
5. **file-first outputs_state**——消除了死 slot 污染。回退到"create_topic 预置 pending 槽"会让未开工 topic 显示假 pending。

## 9.2 明确可简化 / 可优化的方向（低风险高收益）

| 方向 | 现状痛点 | 动它牵动谁 |
|------|---------|-----------|
| **workflow 文件瘦身** | 00-research 876 行 / 03 677 行 / 01 634 行，附录已分离主流程但主流程仍长 | 只动 `workflows/*.md` 文本，不碰脚本；风险低。已有先例（附录 A 移出执行动线）。**注意**：硬规约段（禁止 X/必跑 Y）是补偿"脚本不拦"的，删之前先确认对应机械门禁是否已兜底（查 Part 1.6 真闸门表） |
| **macro 层 fetch_method 家族** | `VALID_FETCH_METHOD` 已 11 种、每种一个 `*_fetch.py`（fred/akshare/yfinance/macromicro/barchart/ecb/safe/cftc/mofcom/fedwatch/fomc_sep），维护面大 | 加/删一个数据源 = 改 `macro_registry.VALID_FETCH_METHOD` + validator 块 + 对应 fetcher。彼此独立，可单独退役冷门源 |
| **web_search provider 冗余** | adapter + exa MCP + tavily MCP + serper 多路，router 打分逻辑分散 | 若某 provider 长期不用可从 `providers/` 摘掉；`rank_providers` 按 capabilities 自动降级，摘一个不崩 |
| **可观测探针的 tier-3 纯判断项** | 05.Q1/00.Q2 等只挂 flag、被动层判不了，价值有限 | 纯 `observability.py` 内部，删探针零外部影响。可保留最有信号的 tier-1 机械项、精简 tier-3 |
| **08_living_feed 与 monitor 的关系** | living_feed 是散文追加，证据现在已另注册进 web_search 库（05 能数到）——living_feed 的机器价值下降 | 若确认 05/dashboard 都不再读 living_feed 正文，可降级为纯人读日志。先 grep 消费者 |

## 9.3 已知薄弱点（改进候选，但需设计）

- **todo pending 语义歧义**：`pending` 无法区分"还没收" vs "已放弃"。`disposition`（waived/will_collect）部分缓解，但只对 empty 生效。若要彻底解决需给 pending 加子态——牵动 gap_detector 的 autofetch_debt 谓词 + 所有闸门。
- **decomposition 命门与 K# 的边界**：文档反复强调"命门 ≠ K# 换个说法"，说明实操中容易退化成 K# 的影子。这是提示词问题不是结构问题，改 00 Step 5.4 + 04 delta 重拆的提示即可，不动脚本。
- **prescan 三态（full/partial/failed）阈值**：`WEB_SEARCH_FAIL_THRESHOLD=0.5` 是拍的。若发现 partial 太宽/太严，只改这一个常量（`web_prescan.py`），影响 `check_prescan_health` + `set_thesis` 校验 + 05 封顶。
- **variant 复用的坑**（memory `project_variant_reuse_gotchas`）：换模型重研时 findings 必须本变体重抽、prescan 必自跑、`*-mirror` 起手标红属预期。这些是纪律不是代码，靠 workflow 约束。

## 9.4 改动时的自检流程（复用现有机械设施）

系统自带三套机械设施帮你验证改动安全（CLAUDE.md 已要求）：
1. **改脚本前**：`impact({target, direction:"upstream"})` 看 blast radius；HIGH/CRITICAL 风险先警示。
2. **改完提交前**：`detect_changes()` 验证只影响预期符号；`detect_changes({scope:"compare", base_ref:"main"})` 做回归对比。
3. **脚本层有单测**：`prism/scripts/test_*.py`（gap_detector / observability / macro / web_search / relatives / eval / primer_gate 等均有覆盖）。改脚本先跑对应 test（`.venv/bin/python -m pytest prism/scripts/test_X.py`）。

## 9.5 一句话记住每个子系统"能不能动"

- **状态机（stage/next_stage）**：能加子态，别改主流顺序（web 进度条 + 5 处 gate 依赖）。
- **双轴 gap**：算法稳定，别合并两轴；阈值（min_evidence=2）可调。
- **auto-fetch 规约**：三态 + 闭环键是承重墙；判定表可随新工具扩展。
- **决策链 6 环**：环的因果序是契约，别改；每环"必带硬落地"可细化提示。
- **sidecar schema**：硬契约四处同步，加字段容易删字段难。
- **macro 层**：横切、独立、可增量退役数据源。
- **可观测层**：纯被动、零外部依赖，随便精简探针。
- **web/dashboard/monitor**：消费层，跟着数据契约走，本身逻辑简单。

---

# Part 10 · 下一步迭代建议（按 收益/改动量 排序 · 2026-08）

> 基于本文档的一次自评。先核了三个数据点，直接修正了 Part 9.2 的部分判断——**排序里带 ✅ 的是已核实的事实，不是猜测**。原则：每条都能**最小闭环**（自包含、可验证、可回退），且都在 Part 7 的耦合图里找过落点。

## 10.0 核实到的事实（排序依据）

- ✅ workflow 总量 **7465 行**；`00`/`03`/`01` = 876/677/634 = **2187 行（占 29%）**，每次跑到对应 stage 都读进 context——这是当前**最大的可控复现 token 成本**（exa 全文灌 context 那个更大的坑已默认关掉，见 §4.4）。
- ✅ `08_living_feed`：py 里 8 处引用**全是 append/write，0 处读正文做机器逻辑** → Part 9.2 "机器价值下降"已证实，可安全降级为纯人读日志。
- ✅ 可观测探针实测 tier1=28 / tier2=8 / **tier3 仅 2 条** → Part 9.2 "精简 tier-3 低风险高收益"是**高估**，收益近零，**划掉这条**。

## 10.1 🥇 #1 — workflow「执行主线 / 按需附录」二分（token + 简化，最高 ROI）

**为什么最优**：唯一每次跑都在付的复现成本，同时正服务"简化"目标，且有先例（附录 A 已移出动线）。

**关键不是删字，是分层**。每段归三类：
1. **执行主线**（每次都走）→ 留主文件；
2. **参考/边角**（示例、罕见分支、历史说明）→ 移 `_00_reference.md`，按需 Read；
3. **硬规约**（禁止 X/必跑 Y）→ **危险区**。先对照 §1.6 真闸门表：**已有机械门禁兜底** → prose 冗余，压成一行指针；**无兜底 → 绝不能移**（移了就退回"靠 Claude 记"的老坑）。

**最小闭环**：只切 `00-research-topic.md`（876 行，最大）。产出 = 主线瘦身 + `_00_reference.md`。验证 = ①行数前后对比 ②逐条硬规约确认仍被真闸门或主线覆盖。纯文本、不碰脚本、可回退。做完一个再决定推不推广到 03/01。

## 10.2 🥈 #2 — tier-1 探针 fail 数顶到人眼处（质量最高 ROI）

现在 28 条 tier-1 机械探针藏在独立 `/checkup` 页，不主动点=等于没有，静默失败仍静默。**把 `run_probes` 的 fail 计数做成小徽标挂到 topic 详情页/dashboard 行**（红 N 项 → 点进 checkup 全表）。把"事后审计"变"在途告警"，是实打实的质量提升。

**改动量小**：纯消费层（`app/routes/prism.py` + 模板），§9.5 也说这层逻辑简单、跟数据契约走，不碰核心逻辑。

## 10.3 🥉 #3 — `08_living_feed` 降级为纯人读日志（已证实安全的顺手清理）

数据已确认没人读它正文。价值 = 消掉"living_feed 是机器产物"的心智负担。改动极小（去掉它在 `outputs_state` 里被当增量源的处理，consumer 全是 append）。housekeeping 级，顺手做，别单独立项。

## 10.4 明确别碰 / 别急

- **tier-3 探针精简**：仅 2 条，收益近零（修正 §9.2），划掉。
- **macro fetch_method 家族瘦身**（§9.2）：11 个 fetcher 彼此独立、只在增删源时才碰，不是复现成本；**仅在确认某源确实没在用**时退役，否则丢信号。
- **todo pending 子态 / 命门≠K# 退化 / prescan 阈值**（§9.3）：真痛点但**都不是最小闭环**——pending 子态牵动所有闸门谓词；命门问题是提示词工程、收益难验证。记着，先别动。

## 10.5 推荐起手

先做 **#1 的第一个闭环（只切 `00-research-topic.md`）**：逐段分类 → 列出「移附录 / 有闸门可压缩 / 必须留」三堆 → 审完再动手。或从 **#2（探针上墙）** 起手拿质量向的即时反馈。

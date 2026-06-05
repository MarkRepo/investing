# Prism 系统设计文档

> 这份文档讲 **prism 是怎么设计的、为什么这么设计、每一步怎么判断跑得好不好**。
> 受众：未来的你（时间久了会忘）+ 接手的 Claude 会话。
> 配套：触发路由见 `.claude/skills/prism/SKILL.md`；逐步执行规约见 `prism/workflows/*.md`；本文件是它们之上的**心智模型与设计理念**，不替代 workflow 的操作细节。
>
> **维护约定**：本文件描述设计意图与质量看点，会随系统演进。改流程结构时同步更新 Part 0/2；新增 H-fix/drift 修复时追加 Part 3。逐字段操作以 workflow 文件与脚本 docstring 为准（它们是单一事实源）。

---

# Part 0 · 心智模型（一场读完）

## 0.1 一句话定位

Prism 是 **LLM 驱动的结构化投资研究系统**。它把"研究一个行业/竞技场/公司"拆成一条**固定阶段的流水线**，每阶段产出结构化中间物，最终合成一份**6 环决策链 case**（+ 配套机器可读 sidecar），可在 `/prism` web 端查看。

**铁律：脚本零 LLM 调用。** 所有判断、抽取、合成、评审都由 Claude 在对话里做；Python 脚本只做 CRUD（读写 `topic.yaml` / `manifest.yaml` / findings / outputs）+ 机械校验 + 取数（web 搜索、财报下载、财务 API）。这条线决定了整个系统的形态：**workflow 文件是写给 LLM 的"怎么想"，脚本是"怎么存"。**

## 0.2 流水线（6 阶段 + 旁支）

```
00 立项        01 规划          02 收料             03 抽取          04 合成              05 评审         (06 监控)
research-topic → 01-roadmap → 02-gather-materials → 03-extracting → 04-synthesizing → 05-critic-review → done
   │              │              │                    │               │                  │
 thesis_v0      roadmap        manifest             findings        primer + case      verdict
 K# + 拆解v0    资料三档       实收料登记           结构化抽取       + sidecar          approve/
 prescan校准    自动取数       gap体检              gap体检          + thesis_v1        rewrite/more
```

- **阶段名（规范常量）**：`00-research-topic` / `01-roadmap` / `02-gather-materials` / `03-extracting` / `04-synthesizing` / `05-critic-review` / `done`。中文进度名 `STAGE_PHASE_NAMES = ["立项","规划","收料","抽取","合成","评审","完成"]`（见 `topic.py`）。
- **`-pending` / `-reopen` 后缀**：同阶段的子态（如 `01-roadmap-pending`=待跑规划；`01-roadmap-reopen`=评审打回重收料，会路由回 `02-gather-materials`）。
- **特殊终态**：`done`（完成）、`quarantined`（company 红线门控 FAIL，不再深研）。
- **旁支 workflow**（不在主线，按需触发）：`06-daily-monitor`（每日巡检）、`07-drilldown`（深挖单个问题）。
- **三类 type 第 6 阶段统一为 `05-critic-review`**：company 必跑 critic 才能 done；industry/arena critic 可选（对话跑评审或 web 点完成均可 done）。

## 0.3 核心数据对象

| 对象                      | 路径                                  | 是什么                                                                                                                | 谁写                     |
| ----------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ---------------------- |
| `topic.yaml`            | `topics/{slug}/topic.yaml`          | 主状态文件：stage / next_actions / user_todos / outputs_state / thesis 指针 / decomposition 指针                             | 脚本（`topic.py`）         |
| `manifest.yaml`         | `topics/{slug}/manifest.yaml`       | 资料清单：每份料的 id / type / rings / addresses / processed                                                                | 脚本（`manifest.py`）      |
| `thesis_v{N}.md`        | `topics/{slug}/{variant}/`          | 投资论点 + **K#（Killer Questions，可证伪赌注）**，版本化                                                                          | LLM Write              |
| `decomposition_v{N}.md` | `topics/{slug}/{variant}/`          | **命门拆解**（最该砸料验证的特化问题）+ **primer 入门目标**（B 轴）                                                                        | LLM Write              |
| findings                | `topics/{slug}/{variant}/findings/` | 从资料结构化抽取的证据条，带 frontmatter（rings/addresses/source/confidence）                                                      | LLM Write              |
| `outputs/`              | `topics/{slug}/{variant}/outputs/`  | `00_primer` + 单份 case（`c_investment_case`/`i_industry_case`/`a_arena_case`）+ sidecar yaml + `_prism_reading_guide` | LLM Write              |
| sidecar                 | `outputs/*.yaml`                    | dashboard 直接消费的机器文件：company `07_decision_kit` / industry `09_industry_to_arenas` / arena `10_peer_matrix`          | LLM Write（**严格按模板字段**） |

**变体（variant）**：同一 slug 下可有多个研究变体（如换模型重研）。variant 名以 `model_registry` 规范名为准（如 `opus4.8`）。`thesis_v{N}` / `decomposition_v{N}` 住在 `{variant}/` 根下；outputs 在 `{variant}/outputs/`。

## 0.4 两条质量轴（理解 gap 的关键）

Prism 用**两条正交的覆盖轴**判断"料够不够、论证扎不扎实"，由 `gap_detector.py` 双轴计算：

- **B 轴 · K# 覆盖（thesis 脊柱）**：每个 K#（Killer Question）有没有 findings 证据撑着。
  - `uncovered_ks` = 0 证据的 K#（🔴 硬伤）；`thin_evidence` = 有料但塌缩到单一来源/单域名（🟡）。
  - 资料用 `addresses: [K1, K3]` 字段挂到 K#。
- **A 轴 · ring 覆盖（输入合同地板）**：6 环决策链每一环的"必带硬落地"有没有原始输入供给。
  - `uncovered_ring_inputs` = 某环必带输入无料（带 🔴 = 三项真·欠供）；`thin_ring_inputs` = 有料但 < min_evidence（🟡）；`api_pending_inputs` = 财务/估值类合成期自动拉（**非红**）。
  - 资料用 `rings: [biz-moat-unit-econ]` 字段挂到环。

**两轴解耦是刻意的**：K# 是"这个标的的特化赌注"（thesis 脊柱，知识驱动、会变）；ring 合同是"任何 company/industry/arena 都必收的类目"（type 常量、不依赖具体标的，无循环依赖）。一个查 `addresses`，一个查 `rings`。

## 0.5 三条贯穿原理（设计理念精华）

1. **LLM 判断 / 脚本 CRUD 分离**（§0.1）。好处：判断质量不被脚本逻辑锁死，模型升级即受益；脚本可单测、确定性强。代价：纪律全靠 workflow 文档约束，跑偏不会被代码拦住（见原理 3）。
2. **收料"先自动获取，抓不到才降级 user_todo"**。目标：todo 里**只剩用户才能搞到的东西**（付费墙/专家访谈/未公开数据）。实现：财报走 `fetch_report_prism` 自动下，公开分析材料走 exa/semantic/WebFetch 深抓（01 Step 5.6），prescan 后 `auto_resolve_todos` 自动核销。详见 §1.5、§1.3。
3. **收敛靠"诊断不是 gate + 诚实降级"，不靠硬闸**。`gap_detector` 报红不阻止你升 stage——它是诊断，不是门禁。哲学是：**与其用硬闸卡死流程，不如让缺口显式可见 + 强制诚实标注**（"数据缺失"/"训练知识估算，非实证"）。极少数地方才设真闸门（如 company 红线 quarantine、primer depth=deep 的 critic 门禁、04 后强制 critic）。
   > 这条原理是双刃剑：它给了流程弹性，但也是"todo 被静默忽略""薄弱论证蔓延到下游"的根因——这正是下一轮**可观测性 spec**要解决的（见 Part 4）。

---

# Part 1 · 贯穿概念（深入一层）

## 1.1 LLM × 脚本 的分工边界

| LLM 在对话里做                                         | 脚本做                                       |
| ------------------------------------------------- | ----------------------------------------- |
| 立题、写 thesis/K#、拆命门、抽 findings、写 case、评审、判 verdict | 读写 topic.yaml / manifest / findings；状态机推进 |
| 判断资料质量、来源分层、domain_tier、降级决策                      | gap 双轴计算（数 evidence、查 ring served_by）     |
| 决定搜什么、抓哪个 URL、命门优先级                               | 执行 web 搜索 / 财报下载 / 财务 API 取数              |
| 关联谁是父/子（看候选判读）                                    | 出机械候选（geo/cluster_tags/ticker 加权打分）       |

**为什么这么分**：投资判断是 prism 的核心价值，且高度依赖模型能力——锁进脚本就等于锁死在写代码那天的认知。把判断留在对话里，模型一升级整个系统的产出质量就抬升。脚本只承担"不该靠 LLM 的"——状态持久化、机械校验、确定性取数。

**关键张力**：纪律不被代码强制（原理 3）。所以 workflow 文件里塞满了"硬规约""禁止 X""必跑 Y"——这些是补偿"脚本不拦"的软约束。Part 3 收拢的 H-fix 多数是"软约束没守住 → 加机械门禁兜底"的演进。

## 1.2 两条覆盖轴详解（gap_detector 怎么算）

`detect_gaps(slug, variant)` 返回双轴报告：

- **B 轴**：遍历 thesis 最新版 K#，数每个 K# 的 findings evidence 条数 → `uncovered_ks`（0 条）/ `thin_evidence`（有料但来源塌缩）。
- **A 轴（ring）**：读 `decomposition` 是否存在判 active；对本 type 的每个合同 code，按 `served_by` 查源：
  - 材料强制项（质性，`api_satisfiable=False`）无材料 → `uncovered_ring_inputs`（可靠红信号）。
  - `api_satisfiable` 项（financial_data/market_data）无材料 → `api_pending_inputs`（合成期自动拉，**非红**）。
  - 有料但 < min_evidence → `thin_ring_inputs`（🟡）。
- **legacy 守门**：旧 topic（无 decomposition 且无任一材料带 rings）→ ring 轴 `status='n/a'`，不刷红误报。

**红/黄/非红的意义**：🔴 = 写作会硬伤，必须补料或诚实标缺；🟡 = 单薄，补到阈值或降级；`api_pending` = 不用管，合成期给 ticker 就自动拉。

## 1.3 todo 生命周期（你最关心的一环）

todo 是 `topic.yaml` 里的 `user_todos`，每条是 dict：

```yaml
- task: "下载3份对比卖方深度报告"
  priority: P0 | P1 | P2
  info_tier: public | half_public | hard   # 信息差等级
  addresses: [K1, K3]                        # 攻打哪些 K#（参与 B 轴覆盖闭环）
  status: pending | in_progress | done
  covered_by: [mat-abc123]                   # 被哪些料覆盖（auto_resolve 写）
  coverage_note: "已由 web-search mat-xxx 覆盖"
```

**生命周期**：

```
生成 ──→ 自动获取尝试 ──→ auto_resolve ──→ 状态流转
(00 5.3 /  (01 5.5 财报 /   (prescan后        pending → in_progress → done
 01 / 02 /  01 5.6 深抓)     addresses 交集     ↑ 进度播报必须传显式 status
 03 / 05)                    自动标 done)         (否则污染"待补料"计数, 见 Part 3)
```

**关键脚本**（`topic.py`）：
- `set_user_todos(slug, todos, variant)` — 全量写（**含 addresses 时会 raise**，防覆写丢字段，H2 修）。
- `append_user_todos(...)` — 追加，不覆写已有结构化 todo。**进度播报用这个 + 传 `status='done'/'in_progress'`**。
- `update_user_todo_status(slug, variant, task_substring, status, covered_by=)` — 按 task 子串匹配改单条。
- `auto_resolve_todos(slug, variant, [mat_ids])`（`web_prescan.py`）— 新料入库后，对每条 todo 若 `todo.addresses ∩ mat.addresses ≠ ∅` 则标 done + 写 covered_by。
- `_resolve_todos_against_materials(...)` — `public` 类 K# 命中即 done（信息差低，搜到就算）。

**信息差等级（info_tier）决定命运**：`public`（一搜就有，价值低但作起点）→ 应被 01 自动获取消化；`half_public`（需登录/付费/外文/拼凑，alpha 主来源）→ 深抓尽量消化；`hard`（专家访谈/产业链调研，价值最高）→ 留给用户。**理论上跑完 01 后，user_todos 里只剩 `hard` + 搜索无果的。**

**已知薄弱点**（→ Part 4 观测 spec 解决）：todo 完成度**不是 gate**，gate 是 K#/ring 维度的。一条 P0 pending 若其 K# 碰巧有别的（更弱）证据，gap_detector 认为 K# 绿了，这条 todo 永远挂 pending 没人回头看。`pending` 状态也有歧义（"还没收" vs "已放弃"无法区分）。

## 1.4 变体 / model_registry / 亲属关系

- **variant**：同 slug 多变体（换模型/换角度重研）。`create_topic(..., variant='opus4.8')`。旧别名（`claude-opus-4-8`）由 `model_registry` 自动归一。
- **复用纪律**（换模型重研时）：材料机械层可复用，但 findings 必须本变体重抽（禁直接复制，避免 churn）；prescan URL 不能构造。`*-mirror`（环⑤镜鉴）复用起手标红属预期（坑④，见 Part 3）。
- **亲属关系**：`suggest_relatives(slug, variant)` 出机械候选（geo/cluster_tags/ticker 跨 sidecar/slug-token 加权）→ LLM 判读真父/子 → `set_parent(slug, variant, parent_slug)`。建链后合成路径 Step 1 亲属 hook 自动复用亲属成稿产出**作输入/参照**（不是继承结论；质量闸门一律本地，冲突时本维度赢）。
  - `cluster_tags` 必须英文 kebab 且与父对齐，否则交集为空 + dashboard 分组失效。

## 1.5 web 取数三件套 + 降级阶梯

| 工具 | 干什么 | 触发点 | 降级 |
|---|---|---|---|
| **prescan**（`web_prescan.py` + `_web_prescan_shared.md`） | 校准**事实**（数字/事件），近 90 天主动拉 | 00 Step 4.5（thesis_v0 前）/ 01 Step 8 | 事件轴由主 agent 按领域自定，**不套固定后缀**（F3 病根）；WebSearch 不可用时 B.2 降级，`check_prescan_health` 自动检测 failed |
| **deep-fetch**（01 Step 5.6） | 获取**分析材料**（研报/报告/裁决全文） | 01 规划期 | exa 高级搜索 → adapter semantic → WebFetch 三阶梯；只有 `hard` 或全搜无果才保留为 user_todo |
| **fetch_report_prism**（`scripts/fetch_report_prism.py`） | 自动下**结构化财报** | 01 Step 5.5（给 ticker） | 按 ticker 路由：US→SEC EDGAR / CN→cninfo / HK→HKEXnews / UK→FCA NSM / KR→DART / JP→TDnet+EDINET |

**财务两条管别混**（reference）：`market_data` 出倍数（PE/PS/市值，A 股可取）、`financial_data` 出基本面；二者合成期自动拉（`api_pending` 非红）。akshare A 股行情主力源是 Sina（`stock_zh_a_daily/minute`），不走 eastmoney。

**抽取工具分工**：卖方/行业研报**必须走 mineru-vlm**（表格/公式/多栏排版保真，不用 pymupdf 偷工）；财报**不走 mineru**（走 `annual_report_extractor.py`，pymupdf find_tables + TOC 切节；mineru 200 页限会撞墙）。

---

# Part 2 · 逐 stage 参考

> 每个 stage 五段：**① 目标 ② LLM 怎么执行 ③ 产出/状态变化 ④ 质量看点 ⑤ 常见跳坑**。
> 质量看点 = "这步跑得好不好看什么信号"；跳坑 = 已知失败模式（Part 3 有理念级归纳）。

## Stage 00 · 立项（`00-research-topic.md`）

- **① 目标**：把一个模糊研究意图，变成可下注的 `thesis_v0`（含 K#）+ `decomposition_v0`（命门 + primer 入门目标）+ 初版 user_todos，并用 prescan 校准事实。
- **② LLM 怎么执行**：查重（`list_variants` 非空走意图分叉）→ 写 thesis_v0（4 段，K1-K5）→ **必跑 web-prescan**（5-10 条优先 query，校准时敏事实）→ 5.3 列资料 todo（带 addresses）→ 5.4 产 decomposition_v0（命门置信度 tag + primer 入门目标）。
- **③ 产出/状态**：`thesis_v0.md` / `decomposition_v0.md`；`topic.yaml` stage→`01-roadmap-pending`，写 user_todos + next_actions（prescan failed 时 prepend ⚠️ 警示）。
- **④ 质量看点**：
  - thesis_v0 是否**基于 prescan 校准后的事实**，而非纯训练知识赌注？（看 `prescan_status`）
  - 每条 K# 是否可证伪、有数字赌注，而非空泛？
  - 每条 todo 是否都带 `addresses`（否则失去 thesis-driven 意义）？
  - decomposition 命门是否标了置信度（低置信度=提示 01 优先砸料）？
- **⑤ 跳坑**：跳过 prescan → thesis 基于过期事实 → K# 设错、todo 攻打错方向、整轮偏航（见 Part 3）。生成 Q#/V# 第三维（已废，K# + todo.addresses 二维足够）。

## Stage 01 · 规划（`01-build-roadmap.md`）

- **① 目标**：把 thesis 的 K# + 输入合同地板 + 命门靶点，组织成三档资料计划；**并尽最大努力自动获取**，让 todo 只剩用户才能搞的。
- **② LLM 怎么执行**：A 轴（输入合同必收类目，尤其三项真·欠供）+ B 轴（命门靶点）双轴排资料 → Step 4 把历史类比落成 `*-mirror` 收料 todo → **Step 5.5 自动下财报**（fetch_report_prism）→ **Step 5.6 深抓公开分析材料**（exa/semantic/WebFetch）→ Step 5.7 校验 roadmap→thesis 闭环 → Step 8 prescan + auto_resolve。
- **③ 产出/状态**：`roadmap.yaml`；自动下的料入 manifest；已获取 todo 标 done；stage→`02-gather-materials`。
- **④ 质量看点**：
  - **Step 5.6 跑了没**？`public`/`half_public` 的 todo 是否真的过了自动获取（而不是直接甩给用户）？
  - 三项真·欠供（mgmt-capital-alloc / consensus / historical-mirror）是否都显式排了 todo？
  - 自动下载/深抓后，剩余 user_todos 是否**只剩 hard + 搜索无果**？
  - 资料先深抓公开全文，抓不到才降级 user_todos（不应默认全变 todos）。
- **⑤ 跳坑**：跳过 5.6 直接把可自动获取的料写成 todo（甩锅用户）；`set_user_todos` 全量覆写丢 addresses（用 update/append）；ticker 没填导致财报下不了。

## Stage 02 · 收料（`02-gather-materials.md`）

- **① 目标**：登记实收资料（用户手放 + 脚本下载），打 rings/addresses，做 gap 体检决定够不够进抽取。
- **② LLM 怎么执行**：扫 inbox（topic-scope `topics/{slug}/inbox/` 优先于全局 `inbox/manual/`）→ `add_material` 登记打 rings → gap 体检（双轴）→ 任一红项非空则补救（web-search 增量 / sub-agent 深挖 / set_user_todos）。
- **③ 产出/状态**：manifest 更新；topic.yaml stage→`03-extracting`；`append_user_todos`（进度播报传显式 status）。
- **④ 质量看点**：
  - 每份料的 rings/addresses 标对了吗（决定它喂哪个环/哪个 K#）？
  - gap 红项是被真处理了（收料/降级），还是被无视硬升 stage？
  - `uncovered_ring_inputs` 的 hard 项升 stage 前是否显式处理（收料或诚实标缺）？
- **⑤ 跳坑**：脚本判"0 待办"还硬找事做（重跑 prescan/反复 read_manifest）；进度播报落进 pending 污染"待补料"计数；财报类自动料的 rings 没让 fetcher 默认打。

## Stage 03 · 抽取（`03-extract-findings.md`）

- **① 目标**：从原始资料结构化抽出 findings（带 rings/addresses/source/confidence），喂决策链各环。
- **② LLM 怎么执行**：gap 体检起步 → 逐料抽 findings，按**实际抽到的内容**精修 frontmatter rings（抽到才标）→ 冲突 >3 条则回退 02 走完整 prescan。SEC 10-K/10-Q 下载时已自动切片 `item_*.md`。
- **③ 产出/状态**：`findings/*.md`；stage→`04-synthesizing`；`append_user_todos`（显式 status）。
- **④ 质量看点**：
  - findings 是否标了 source/confidence，可溯源？
  - rings 是按真抽到的内容标，还是硬标（一份料可服务多环，但别硬塞）？
  - 冲突证据是否被识别并处理，而非和稀泥？
- **⑤ 跳坑**：bulk 抽取 dispatch subagent 撞 60min 硬墙（>30K token 或 >40min 主 agent 直做 + 并行 Write）；subagent 脑补"Write 被拦截"幻觉（不存在该 hook，dispatch prompt 必须原文嵌硬规约 + retry 闭环）。

## Stage 04 · 合成（`04-synthesize/`）

- **① 目标**：理解先行（primer）+ 写一份 6 环决策链 case + sidecar + thesis_v1。
- **② LLM 怎么执行**：按 type 走路径文档——company `_company_case.md` / industry `_industry_funnel.md` / arena `_arena_funnel.md`。Step 0 双轴 gap 体检 + 增量重写判定（`list_affected_outputs`，fresh 跳过）+ 命门 delta 重拆 → **Step 2 primer 先行**（primer-first，critic 不可省）→ 走 6 环写 case（主 agent 直做 + 并行 Write，不 dispatch subagent）。
- **6 环决策链**（case 的骨架，紧的因果序、非并列）：
  ```
  ① 能不能看懂这家公司？     —— 闸门（生意/护城河/单位经济 + 管理层资本配置 + 多年财务）
  ② 市场此刻替它定了什么价？ —— 锚（反推隐含预期，必须有数字）
  ③ 需要什么假设为真？       —— WMBT（把②翻译成 3-5 条可证伪假设）
  ④ 我信哪边，凭什么？       —— 下注（多空 + 核心分歧锚回②的隐含数 + 期望收益 EV 加总）
  ⑤ 错了会怎样、怎么第一时间知道？—— 证伪（风险 + 历史失败镜鉴 + kill 触发 + signpost）
  ⑥ 什么价/仓位/时点做什么？ —— 行动（买入框 + 仓位接④的 EV + 阶梯）
  ```
  industry/arena 的环⑥ 折入旧 09/10 选拔（落 `industry_to_arenas.yaml` / `peer_matrix.yaml` + 建下游 stub）。
- **③ 产出/状态**：`00_primer.md` + `_prism_reading_guide.md` + 单份 case + sidecar yaml + `thesis_v1.md`；stage→`05-critic-review`。
- **④ 质量看点**：
  - **断链没有**？（有④下注却无⑤证伪、有⑥行动却无②锚 = 断链，chain-critic 必查）
  - 环④核心分歧是否锚回环②的"我 vs 价里那个数"的 delta（只铺多空不落 delta = 没回答命门）？
  - 缺口是诚实标"数据缺失/训练知识估算"，还是冒充实证？
  - sidecar 是否严格按模板字段（禁自创 thesis_strength/killer_questions 等）？
  - primer depth=deep 是否过了 critic 门禁（否则自动降级 draft）？
- **⑤ 跳坑**：硬合成（双轴红项没补就写）→ 产出全是"未充分论证"占位，05 把雷踩回来；`*-mirror` 标红误当可补缺口（复用起手属预期，从训练知识补镜鉴并明标降级）；sidecar 自创字段破坏 dashboard 消费。

## Stage 05 · 评审（`05-critic-review.md`）

- **① 目标**：独立反方对抗式 steelman，定 verdict，决定 done / 重写 / 补料。
- **② LLM 怎么执行**：独立反方挑论证薄弱处 → Step 3 评分 → Step 7 三选一 verdict。failed prescan 续推时强制把时敏论断按脆弱处理、最高只能 request-more。
- **③ 产出/状态**：`set_critic_verdict` 自动推进——
  - `approve`（评分≥4/反驳弱/无重要遗漏）→ stage→`done`。
  - `request-rewrite`（部分 K# 薄/某 output 需重写）→ stage→`04-synthesizing`，rewrite_keys 标 stale。
  - `request-more`（关键证据 manifest 无覆盖）→ stage→`02-gather-materials`，append 待补 todo（**必带 addresses，否则后续 auto_resolve 算不进**）。
- **④ 质量看点**：
  - 反方是真 steelman（攻最强论证）还是走过场？
  - verdict 与评分一致吗（评分低却 approve = 放水）？
  - request-more 的 todo 是否只列 web-search 拿不到的部分（能搜的别甩用户）？
- **⑤ 跳坑**：failed prescan 仍给 approve（时敏论断未校准）；request-more 的 todo 漏 addresses → auto_resolve 永远核销不掉。

## Stage 06 · 监控（`06-daily-monitor.md`，旁支）

- **① 目标**：已 done 的 topic 持续监控信号（signpost/kill 触发）。
- **② 执行**：web-server 每日 6:00 自动拉起 / web 端「立即巡检」/ 对话「监控 {slug}」。提案进 `monitor_queue.yaml` 待确认（`awaiting_confirm`）。
- **④ 质量看点**：巡检是否对着 case 环⑤的 signpost/kill 条件，而非泛泛找新闻。

## 旁支 · 07 深挖

- **07-drilldown**：深挖单个顽固命门。笔记当 `source_type='drilldown'` material 入库（直接 mark_processed，不重抽），写 addresses 仍触发 auto_resolve。

---

# Part 3 · 设计理念 × 踩过的坑

> 这是文档的"记忆"：把散落在 workflow 里的 H-fix / drift 修复 / PRISM_VALIDATION 病根，归纳成「理念 → 当初为何踩 → 现在怎么防」。也是 Part 4 观测埋点的现成清单。

| 理念                    | 当初踩的坑                                                    | 现在怎么防                                                                     |
| --------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------- |
| **事实先于赌注**            | 纯训练知识写 thesis_v0，把过时事实当赌注 → K# 偏航                        | 00 Step 4.5 必跑 prescan；`check_prescan_health` 机械检测 failed                 |
| **搜索用关键词不用问句**        | question 长句问号喂 WebSearch 常返空（H4）                         | `search_keywords` 短促词组替代 question 当 query                                 |
| **事件轴按领域自定**          | prescan 对所有行业写死后缀"产能变化"、对 company 写死"最新公告"（F3 病根）        | 事件轴由主 agent 按领域自定，不套固定后缀                                                  |
| **先自动获取再降级**          | tier1 资料默认全变 user_todos，甩锅用户                             | 01 Step 5.5/5.6 先财报自动下 + 公开材料深抓，只有 hard/无果才保留 todo                        |
| **todo 结构不可覆写**       | `set_user_todos(list[str])` 全量覆写丢 priority/addresses（H2） | 含 addresses 时 raise；进度提示用 `append_user_todos` + 显式 status                 |
| **pending 仅留真待办**     | 进度播报落 pending → web 详情页误计"待你补 N 份"（待补料假 pending）         | 里程碑播报传 `status='done'`，进行中传 `in_progress`，绝不落 pending                     |
| **覆盖判定要够细**           | `addresses=K#` 粒度过粗 → Q1 材料误覆盖 Q2 todo（假覆盖）              | 加事件锚/时间窗校验（`addresses_match_event_anchored`）                              |
| **二维足够，别加第三轴**        | 旧版生成 Q#/V# 与 K# 双轨、与 todo 重复                             | 收敛为 K#（thesis 脊柱）+ todo.addresses；Q#/V# 已废                                |
| **主 agent 直做大合成**     | bulk synthesis dispatch subagent 撞 60min 硬墙              | >30K token 或 >40min 主 agent 直做 + 并行 Write                                 |
| **dispatch 嵌硬规约**     | subagent 脑补"Write 工具被拦截"幻觉（3/3 都是幻觉，无此 hook）             | dispatch prompt 原文嵌硬规约 + retry 闭环                                         |
| **抽取工具按料型选**          | 卖方研报用 pymupdf 丢表格；财报用 mineru 撞 200 页限                    | 研报走 mineru-vlm 保真；财报走 annual_report_extractor                             |
| **来源主动分层**            | prescan 非 whitelist hit 默认 confidence=0.4 被 funnel 丢弃    | 行业垂直/海外/券商研报源主动标 `llm-judged-official`                                    |
| **sidecar 严守 schema** | 自创 thesis_strength/killer_questions 字段破坏 dashboard 消费    | 写前 grep 模板 Step 3.5/6.5，禁自创字段                                             |
| **镜鉴红是预期**            | 复用起手 `*-mirror`（环⑤）必标红被误当可补缺口（坑④）                        | 从训练知识补镜鉴 + 明标"训练知识估算/depth 降级"，不回 02 搜料                                   |
| **primer 深度不许假冒**     | depth=deep 用 outline 假冒、省 critic                         | F17 机械门禁：注册前必 `set_output_critic_passed` + 正文须含争议节/自检节/过字数地板，否则自动降级 draft |
| **诊断不是 gate**         | （双刃）gap 报红不阻止前进 → 薄弱论证蔓延到下游                              | 弹性换来跑偏风险，靠 04/05 兜底；**根治留给 Part 4 观测层**                                   |

---

# Part 4 · 通往可观测性（占位，下一轮 spec 展开）

## 4.1 现状的缺口

当前 prism 已有诊断（`gap_detector` 双轴报告、dashboard staleness、prescan health），但**只给中间产出与静态状态**——你看得到"现在 K3 没覆盖""primer 是 draft"，但看不到：

- **每个 stage 的目标 vs 实际**：这步本该干什么、LLM 实际怎么执行的、结果如何。
- **执行轨迹**：一次推进里调了哪些工具、搜了什么、抓到什么、做了哪些降级决定。
- **todo 的完整命运**：为某目的生成 → 是否尝试自动获取 → 核销了没 → 卡在哪。
- **质量信号的聚合**：Part 2 每个 stage 的"质量看点"现在散在文档里，没有被系统采集成可回看的判据。

核心诉求：**让用户能看到流程怎么跑起来，并据此判断 LLM 执行过程的质量。**

## 4.2 已识别的埋点候选（来自 Part 2/3）

下一轮 spec 的输入清单（不在本轮设计）：
- **stage 级**：进入/退出、目标声明、耗时、产出文件、状态变化 diff。
- **质量看点**（Part 2 每 stage ④）：prescan_status、K# 可证伪性、todo addresses 完整性、5.6 是否跑、断链检查、sidecar schema 合规、primer gate 结果……
- **失败模式探针**（Part 3）：可自动获取却进了 todo、pending 被静默携带、覆盖粒度过粗假覆盖、镜鉴红误判、subagent 幻觉重试。
- **todo 维度收敛**（§1.3 薄弱点）：pending P0 在进 04/05 前是否显式收敛（done / 重试 / 诚实 waived）。

## 4.3 设计原则（给下一轮定调）

- **不破坏原理 1**：采集靠脚本（CRUD/校验），判断仍在对话——观测层记录"LLM 做了什么 + 机械信号如何"，不替 LLM 下质量结论。
- **顺着原理 3**：观测把"静默"变"显式可见 + 可审计"，而非把诊断改成硬闸（除终态 approve 等极少处）。
- **复用现有结构**：trace 落在 topic.yaml/sidecar 体系内，dashboard 增量呈现，不另起一套存储。

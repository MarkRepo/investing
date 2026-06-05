# Prism 可观测性 spec（观测层 · v1）

> 本文是 `DESIGN.md` Part 4 的展开。Part 4 留了占位（缺口 4.1 / 埋点候选 4.2 / 设计原则 4.3）；本 spec 把它收口成可落地的设计。
>
> **维护约定**：观测层是 `DESIGN.md` 三条贯穿原理之上的一层"看流程怎么跑"的镜子。改探针/字段时同步更新本文 §3/§4；新增失败模式探针时追加 §3.3。逐字段以脚本 docstring 为单一事实源。
>
> 配套：心智模型见 `DESIGN.md`；探针读的底层信号散落在 `topic.py` / `manifest.py` / `gap_detector.py` / `web_prescan.py`。

---

## §1 目标与非目标

### 1.1 一句话

观测层 = 一个**纯被动、零 LLM** 的脚本层，它在每次推进/合成后，从**已有产物的残留**重建一份"这个 topic 的流程跑得怎么样"的结构化诊断，呈现在一张**平行于详情页的诊断/debug 页**上，**给人看**，据此判断 LLM 执行过程的质量。

### 1.2 目标（in scope）

- **三族探针**全表落地（产出/状态、质量看点、跳坑），覆盖 00-06 每 stage + 贯穿维度（§3）。
- **被动重建为骨架**：探针靠脚本读 artifact（CRUD/校验）算出，不靠主动埋点（§5 约束）。
- **B 系列建设**（§4）：补齐少数"机械可重建、但当前缺残留"的字段——以 B1（stage 转换史 + 进入时 gap 快照）为承重墙。
- **复核旗**：纯判断类探针（③）老实挂"待人复核"旗，给人，不假装机械判得了（§3.4）。
- **平行诊断页**：per-topic 一张，按 stage + 贯穿分组，pass/fail/flag 徽章（§6）。

### 1.3 非目标（out of scope，本轮明确不做）

- **不驱动门禁**：观测信号**纯展示**。不把任何探针升级成升 stage 的软/硬闸（顺 `DESIGN.md` 原理3——把"静默"变"显式可见"，而非把诊断改成硬闸）。已有的极少数真闸门（company 红线 quarantine、primer F17、04 后强制 critic）不动。
- **不喂 05 critic**：复核旗给人，不自动作为 critic 输入（喂 critic = 从展示跨进驱动；且对 05 自身的旗会循环）。保留为未来可选扩展。
- **不建主动 per-push 工具调用 trace**（原 B5，已砍）：理由见 §4.5；替代为 B5′ 被动卷积。
- **不另起存储**：trace 落在现有 topic.yaml / sidecar / 既有 log 体系内，诊断页增量呈现（顺原理）。
- **机器消费 / 自检闭环**：现阶段主消费者是人。给下一个 Claude 会话自检留作未来。

### 1.4 成功判据

- 打开某 topic 的诊断页，能一眼回答 Part 4.1 的四问：每 stage 目标 vs 实际、收料执行轨迹、todo 完整命运、质量信号聚合。
- 凡 Part 2 ④ 质量看点中"可机械重建/机械代理"的项（§3 表 ①②类），都有对应探针给出 pass/fail/flag，且**不需要 LLM 在跑流程时额外报告**。
- 纯判断项（③类）只出现"待复核"旗，绝不出现脚本伪造的质量结论。

---

## §2 架构

```
                         ┌─────────────────────────────────────────┐
   已有产物（残留）        │   观测层（新增 · 纯被动 · 零 LLM）          │
   ─────────────         │                                           │
   topic.yaml      ─────▶│  observability.py                         │
   manifest.yaml   ─────▶│   · run_probes(slug, variant) -> Trace    │──▶ 平行诊断页
   findings/*.md   ─────▶│     逐 stage + 贯穿，跑全部探针             │   (per-topic)
   outputs/*(.yaml)─────▶│     读 artifact + 调 gap_detector /        │
   web_search_log  ─────▶│     list_search_log / read_manifest        │
   fetch_status 全家 ───▶│   · 每探针出 {status, signal, detail,...}  │
   gap_detector    ─────▶│                                           │
                         └─────────────────────────────────────────┘
                              ▲
                              │ B1-B4/B6 建设补齐缺失残留（§4）
```

- **新增脚本**：`prism/scripts/observability.py`。核心 `run_probes(slug, variant) -> dict`（Trace 对象），纯读 + 机械判，**零 LLM、零写**（除非把 Trace 缓存进 sidecar，见 §6.2）。
- **探针结果 schema**（每条）：
  ```yaml
  probe_id: "01.Q1"
  label: "5.6 跑了（public/half 真过自动获取）"
  stage: "01-roadmap"        # 或 "cross-cutting"
  family: produce | quality | pitfall
  tier: 1 | 2 | 3 | null      # 仅 quality 族有；① 机械重建 / ② 机械代理 / ③ 纯判断
  status: pass | fail | flag | na
  signal: "fetch_status 字段"  # 重建信号（源）
  detail: "3/5 public todo 仍 unattempted"
  action: "去抓（见 CC3）"      # 失败时建议动作（给人，非自动执行）
  ```
- **status 语义**：`pass`=探针通过；`fail`=机械确认有问题；`flag`=③类纯判断/②类代理存疑→待人复核；`na`=不适用（legacy topic / 该 stage 未到 / 守门跳过）。

---

## §3 探针全表

图例：族 `📦`产出 / `🎯`质量 / `🕳️`坑　·　质量类 `①`可机械重建 `②`机械代理 `③`纯判断挂复核旗
依赖标记：`[B1]` 等 = 需对应 §4 建设才能落地；无标记 = 读现成残留即可。

### 3.1 贯穿（cross-cutting · todo 生命周期 + 数据完整性，DESIGN §1.3 + Part 3）

| ID | 检查什么 | 重建信号（源） | 族/类 | 失败动作 |
|---|---|---|---|---|
| CC1 | active todo 都带 addresses（H2） | todo.addresses 字段 | 🕳️🎯① | flag 丢字段 |
| CC2 | 无"待补料假 pending" | pending 但 covered_by≠∅ 或 fetch_status=fetched | 🕳️① | 应翻 done |
| CC3 | autofetch 欠账 | `gap_detector.autofetch_debt` | 🕳️🎯① | error→重试 / unattempted→去抓 |
| CC4 | empty 待用户决 | `empty_undecided_todos` | 🕳️① | 硬闸门待决（已实施） |
| CC5 | 无假覆盖（addresses 粒度过粗） | `addresses_match_event_anchored` | 🕳️② | flag 复核 |
| CC6 | P0 pending 进 04/05 前已收敛 | P0 todo status=pending 且 stage≥04 | 🕳️🎯① | flag 未收敛 |
| **B5′** | **本轮收料卷积**（执行轨迹被动版） | `web_search_log` + `manifest` + `fetch_status 全家` | 📦🎯① | — （见 §4.5） |

> **B5′ 卷积面板**：「搜了 N 轮 query（入库 X / 跳过 Y + 原因）→ 入库 M 份料 → 降级 K 条（empty/error/waived + 一句理由）」。纯读现成残留，零埋点。这是人想要的"执行轨迹"，归探针层。

### 3.2 逐 stage · 产出 + 质量

#### 00 立项
| ID | 检查 | 信号源 | 族/类 | 失败动作 |
|---|---|---|---|---|
| 00.S1-3 | thesis_v0 / decomposition_v0 产出、stage→01-pending | 文件存在 + stage | 📦 | 缺件报红 |
| 00.Q1 | prescan 跑了且未 failed | `prescan_status` / `check_prescan_health` | 🎯① | 时敏论断脆弱化 |
| 00.Q2 | K# 可证伪 / 有数字赌注 | K# 文本含数字（代理） | 🎯② | 挂复核旗 |
| 00.Q3 | 每条 todo 带 addresses | 字段（=CC1） | 🎯① | — |
| 00.Q4 | 命门标了置信度 | decomposition confidence tag | 🎯① | — |
| 00.X1 | 无废弃 Q#/V# 第三维残留 | 文本扫 Q#/V# | 🕳️① | flag 清理 |

#### 01 规划
| ID | 检查 | 信号源 | 族/类 | 失败动作 |
|---|---|---|---|---|
| 01.S1-3 | roadmap.yaml、自动料入 manifest、stage→02 | 文件 + manifest + stage | 📦 | 缺件报红 |
| 01.Q1 | **5.6 跑了（public/half 真过自动获取）** | **`fetch_status`≠unattempted** | 🎯① | 见 01.X1 |
| 01.Q2 | 三项真·欠供都排了 todo | todo 命中那 3 个 ring code | 🎯① | flag 漏供 |
| 01.Q3 | 剩余 user_todos 只剩 hard+无果 | pending todo `fetch_status=empty` 或 `info_tier=hard` | 🎯① | flag 甩锅 |
| 01.X1 | 无"可自动获取却写成 todo" | pending `fetch_status=unattempted` 且 info_tier≠hard | 🕳️① | 去抓（CC3） |
| 01.X3 | ticker 填了 | ticker 空 + manifest 无财报 | 🕳️① | flag |

#### 02 收料
| ID | 检查 | 信号源 | 族/类 | 失败动作 |
|---|---|---|---|---|
| 02.S1-2 | manifest 实收登记、stage→03 | manifest + stage | 📦 | — |
| 02.Q1 | 每份料标了 rings/addresses | frontmatter 字段在/对 | 🎯①标没标 / ②标对没 | 挂旗 |
| 02.Q2 | **gap 红项被处理 vs 无视硬升** | **进/出 gap 快照 diff + stage diff** | 🎯① `[B1]` | flag 硬升 |
| 02.Q3 | uncovered_ring hard 项升前显式处理 | gap 快照 + state diff | 🎯① `[B1]` | flag |
| 02.X2 | 财报类自动料 rings 默认打了 | manifest 财报料 rings 空 | 🕳️① | flag |

#### 03 抽取
| ID | 检查 | 信号源 | 族/类 | 失败动作 |
|---|---|---|---|---|
| 03.S1-2 | findings/*.md 产出、stage→04 | 文件 + stage | 📦 | — |
| 03.Q1 | findings 标了 source/confidence | frontmatter | 🎯① | flag 不可溯源 |
| 03.Q2 | rings 按真抽到标（非硬标） | — | 🎯② | 挂旗 |
| 03.Q3 | 冲突证据被识别（>3 回退 02） | 冲突标记 `[B6]` + 回退记录 `[B1]` | 🎯② | 挂旗 |

#### 04 合成
| ID | 检查 | 信号源 | 族/类 | 失败动作 |
|---|---|---|---|---|
| 04.S1 | **5 件套全产出**（primer+case+sidecar+thesis_v1+reading_guide） | 文件存在 | 📦① | 缺件报红 |
| 04.Q1 | 断链（6 环结构 + 交叉引用） | sidecar chain-link 断言块 `[B2]` | 🎯①结构 / ②语义 | flag 断链 |
| 04.Q2 | 环④锚回②的 delta | ④分歧锚 + ②反推隐含数 字段 `[B4]` | 🎯② | 挂旗 |
| 04.Q3 | 缺口诚实标 vs 冒充实证 | 标准诚实缺口标记 `[B3]` | 🎯②（冒充侧③） | 挂旗 |
| 04.Q4 | sidecar 严格按模板字段 | schema 校验 | 🎯① | 报红（破坏 dashboard 消费） |
| 04.Q5 | primer deep 过 critic 门禁 | `set_output_critic_passed`+字数+section（F17） | 🎯① | 自动降 draft（已实施） |
| 04.X1 | 无硬合成（双轴红没补就写占位） | gap 红 + case 含"未充分论证"占位 | 🕳️① | flag |
| 04.X2 | `*-mirror` 标红抑制（复用起手属预期） | mirror todo 红 + variant 是复用 | 🕳️① | false-red 抑制 |

#### 05 评审
| ID | 检查 | 信号源 | 族/类 | 失败动作 |
|---|---|---|---|---|
| 05.S1 | verdict 落库 + stage 推对 | `set_critic_verdict` | 📦 | — |
| 05.Q1 | 反方真 steelman 还是走过场 | — | 🎯③ | **挂复核旗（被动给不了）** |
| 05.Q2 | verdict 与评分一致（评分低却 approve=放水） | score 字段 vs verdict | 🎯① | flag 放水 |
| 05.Q3 | request-more todo 只列搜不到的 + 必带 addresses | todo `fetch_status=empty` + addresses（CC1） | 🎯① | flag |
| 05.X1 | **failed prescan 却 approve** | `prescan_status=failed` + verdict=approve | 🕳️① | flag（纯机械可逮） |

#### 06 监控（旁支）
| ID | 检查 | 信号源 | 族/类 | 失败动作 |
|---|---|---|---|---|
| 06.Q1 | 巡检对着环⑤ signpost/kill 而非泛新闻 | monitor_queue 提案 vs signpost 条件 | 🎯② | 挂旗 |

### 3.3 三族关系（为何不冗余）

- **📦 产出/状态**：做了没/状态对没对（conformance）。与质量**正交**——可"全产出但质量差"或"半产出"。最便宜，纯被动。即 Part 4.1 第 1 条"目标 vs 实际"。
- **🎯 质量**：产得好不好。① 机械重建 / ② 机械代理 / ③ 纯判断挂旗。
- **🕳️ 坑**：有没有踩中已知 bug 签名。**多数独立**于质量看点（CC2 假 pending、05.X1 failed-prescan-approve、04.X2 mirror false-red 等 Part 2 ④ 全未覆盖）；少数是某质量看点的反面（00.X1↔prescan、CC1↔addresses），接缝处去重即可。

### 3.4 复核旗语义（③ 类 + ② 存疑）

- **给谁**：人（诊断页前的你）。**不自动喂 05 critic**（§1.3）。
- **说什么**：统一语义 = "被动层判不了，这里需要人看一眼"。绝不让脚本下质量结论。
- **谁挂**：纯判断 ③（05.Q1 steelman、04.Q3 冒充侧、00.Q2 可证伪真值）+ 机械代理 ② 命中存疑（02.Q1 标对没、04.Q2 delta、CC5 假覆盖、06.Q1）。
- **页面呈现**：`flag` 徽章 + 一句"为何机械判不了" + 指向要复核的具体 artifact 位置。

---

## §4 B 系列建设（补齐缺失残留）

> 原则：像 `fetch_status` 那样，把"判断的*输入*"机械化盖进产物，让被动层读出来——而不是用主动埋点去补判断。

### 4.1 B1 · stage 转换史 + 时间戳 + 进入时 gap 快照　⭐承重墙

**为什么**：`topic.yaml` 现仅存当前 stage，无 history/时间戳。没有进入时的 gap 快照，被动层只能看到"现在红没红"，**永远分不清红项是被处理了、还是红着被硬升 stage**（02.Q2/Q3）。`gap_detector.py:207` 已留 `# placeholder, requires baseline` 自证此缺口。

**解锁**：02.Q2/Q3、stage 耗时、Part 4.1#1、03.Q3 回退记录、gap_detector 的 `training_only_claims` baseline。

**结构**（镜像 thesis.history / decomposition.history 的版本化模式）：
```yaml
stage:
  current: "04-synthesizing"
  history:
    - stage: "02-gather-materials"
      entered_at: "2026-06-01T08:00:00+00:00"
      exited_at:  "2026-06-02T03:00:00+00:00"
      gap_snapshot:            # 进入该 stage 瞬间的 detect_gaps() 精简快照
        uncovered_ks: ["K3"]
        uncovered_ring_inputs: ["mgmt-capital-alloc"]
        autofetch_debt: {unattempted: 2, error: 0}
        empty_pending_decision: 1
    - stage: "03-extracting"
      entered_at: "2026-06-02T03:00:00+00:00"
      exited_at: null          # 当前 stage 退出时回填
      gap_snapshot: {...}
```
- **谁写**：`set_stage(slug, stage, variant)` 在切换时：① 给上一条 history 回填 `exited_at`；② append 新条目，盖 `entered_at` + 当下 `detect_gaps()` 精简快照。
- **diff 怎么算**：02.Q2 = 比较"02 进入快照"与"03 进入快照"（=02 退出态）的红项集合；红项消失=处理了 pass，红着不变却进了下游=硬升 fail。
- **耗时** = `exited_at - entered_at`。时间戳是机械 CRUD，不破铁律。
- **向后兼容**：旧 topic 无 `stage.history` → `setdefault` 补空；首条无快照的 stage 探针出 `na`（不误报）。
- **改动符号**：`set_stage`（impact 必跑）；`detect_gaps` 加一个"精简快照"导出（或观测层自取）。

### 4.2 B2 · case 6环结构锚 / chain-link 断言块（加固 04）

**为什么**：case 是自由 markdown，无保证 ring 边界/交叉引用的结构标记；被动逮断链需脆弱 parser。

**做法**：在对应 sidecar（`07_decision_kit` / `09_*` / `10_*`）加一个机器块，写 case 时顺手盖：
```yaml
chain_links:
  rings_present: [1,2,3,4,5,6]      # 6 环 section 是否齐
  r4_anchors_r2: true               # ④核心分歧引用了②的隐含数
  r6_takes_r4_ev: true              # ⑥仓位接④的 EV
  r5_has_kill_signpost: true        # ⑤有 kill 触发 + signpost
```
- **谁写**：04 合成路径文档（`_company_case.md` 等）Step 收尾，作为 sidecar 字段。schema 校验归 04.Q4 一并管。
- 结构侧 04.Q1 由 `rings_present` + 三个布尔机械判；语义侧（"是否真锚回命门"）仍 ② 挂旗。

### 4.3 B3 · 标准化诚实缺口标记（加固 04）

**为什么**：现在"数据缺失/训练知识估算"是自由散文，grep 脆弱。

**做法**：约定标准标记，二选一（spec 倾向后者，便于被动读）：
- 正文行内标签 `〔缺口:数据缺失〕` / `〔缺口:训练知识估算〕`；或
- sidecar `honest_gaps: [{ring: 5, kind: data-missing, note: "..."}]`。
- 解锁 04.Q3 检测侧（"有没有诚实标"）；"是否冒充实证"仍 ③ 挂旗。

### 4.4 B4 · ④分歧锚 + ②市场反推隐含数 显式字段（加固 04）

**为什么**：`decision_kit` 已结构化 `valuation_models`（bull/base/bear）+ `anchor_model`（②估值结构已在），但缺**②的"市场反推隐含数"**与**④的"我 vs 价 delta"**两个显式字段。

**做法**：decision_kit 加：
```yaml
market_implied:                 # ②：从现价反推市场隐含的关键变量
  metric: "implied_rev_cagr_3y"
  value: 0.18
my_vs_market_delta:             # ④：我的判断 vs 市场隐含 的差
  metric: "implied_rev_cagr_3y"
  my_value: 0.25
  delta: "+7pct"
  direction: long
```
- 解锁 04.Q2 代理（④ delta 是否锚回②同一指标）。

### 4.5 ~~B5~~ → B5′（已砍主动 trace，替为被动卷积）

- **B5 砍掉理由**：执行轨迹的有价值内容已是残留——`web_search_log.yaml`（搜了什么/registered/skipped+原因）+ `manifest`（抓到什么）+ `fetch_status 全家`（**降级决定+理由，上一轮已建**）。残留唯一缺的是死胡同探索调用的原始时序，对人做质量判断**高音量低信号**，且**是唯一需主动埋点**的部分——用会漏记的机制观测"流程有没有漏跑"自相矛盾，破坏原理3。
- **B5′** = 探针层的被动卷积（见 §3.1），零建设。

### 4.6 B6 · findings 冲突标记（可选 · 低优先）

findings frontmatter 加可选 `conflicts_with: [finding-id]` / `conflict_note`，解锁 03.Q3 识别侧。不建则 03.Q3 退化为纯 ② 挂旗。

### 4.7 建设优先级

`B1（承重）` > `B2/B3/B4（集中加固最高风险的 04 合成）` > `B6（可选）`。B5′ 无建设，随探针层一起出。

---

## §5 约束（不破坏 DESIGN 原理）

- **不破原理1（LLM 判断 / 脚本 CRUD 分离）**：观测层全部是脚本读 artifact + 机械判 + 机械盖字段（B1 时间戳/快照、B2-B4 由 LLM 写 case 时顺手落的结构化字段经 schema 校验）。**脚本绝不替 LLM 下质量结论**——③ 类一律挂旗给人。
- **顺原理3（诊断不是 gate）**：观测层**纯展示**，把"静默"变"显式可见 + 可审计"，不新增升 stage 闸门。
- **复用现有结构**：trace 落 topic.yaml（`stage.history`）/ sidecar（chain_links/honest_gaps/market_implied）/ 既有 log（web_search_log），诊断页增量呈现，不另起存储。
- **铁律不破**：时间戳、快照、provenance 卷积都是机械 CRUD，零 LLM 调用。

---

## §6 平行诊断页

### 6.1 形态

- per-topic 一张，路由平行于详情页（如 `/prism/{slug}/{variant}/trace`，或 web 详情页内的「诊断」标签）。
- **分区**：① 顶部体检条（各 stage 一颗灯：📦产出齐否 / 🎯质量 fail 数 / 🕳️坑 fail 数 / flag 数）→ ② 贯穿区（CC1-6 + B5′ 卷积面板）→ ③ 逐 stage 展开（产出/质量/坑三栏，pass/fail/flag 徽章 + detail + action）→ ④ 复核旗汇总（所有 flag 单列一处，指向要看的 artifact）。
- **时间线**（B1 落地后）：stage.history 渲染成泳道，每 stage 标耗时 + 进入时红项，红项在哪一 stage 被清/被带过去一目了然。

### 6.2 生成

- `observability.py` 出 Trace（结构化 dict）→ 渲染器产页（仿 `dashboard.py` 出 `dashboard.md` 的模式）。
- **缓存**：Trace 可选缓存进 sidecar `_observability.yaml`（便于 dashboard 列表页聚合"哪个 topic 一堆 flag"）；或每次实时跑（topic 规模小，实时即可）。v1 倾向**实时跑 + 不落盘**，避免又一份要维护的状态文件。

---

## §7 实施顺序与风险

按"先无建设探针、再 B 建设、最后页面"降爆炸半径；每个代码符号编辑前跑 `gitnexus_impact`，提交前跑 `gitnexus_detect_changes`（CLAUDE.md 硬规则）：

1. **`observability.py` + 无建设探针**（读现成残留：CC1-6、B5′、各 S/Q/X 中无 `[B]` 标记者）。新文件 + 纯读，**LOW**。
2. **B1 stage.history**（§4.1）—— impact `set_stage` / `detect_gaps`。动状态机写入路径，**MEDIUM**（向后兼容 + 快照精简度需验）。落地后接 02.Q2/Q3、耗时、时间线。
3. **B2/B3/B4 sidecar 字段**（§4.2-4.4）+ 04 路径文档写入 —— sidecar schema 加字段（impact sidecar 校验）+ markdown。**LOW-MEDIUM**。接 04.Q1/Q2/Q3。
4. **B6**（可选）—— findings frontmatter，**LOW**。
5. **诊断页渲染器**（§6）—— 仿 dashboard.py，**LOW**。

**两处 MEDIUM 接缝**：B1（set_stage 写 history + 快照向后兼容）与 B2-B4（sidecar schema round-trip 带新字段，勿破 dashboard 现消费）。

## §8 验证（在 throwaway variant，不碰生产 yaml）

1. **无建设探针**：对一个已 done 的 topic 跑 `run_probes` → 产出族全 pass、质量族 ①类有判、③类全 flag、坑族能逮已知签名（造一个 failed-prescan+approve 的假 topic 验 05.X1）。
2. **B1 快照**：连续 `set_stage` 三次 → `stage.history` 三条、`exited_at` 正确回填、每条带 gap_snapshot；旧 topic（无 history）→ 探针出 `na` 不报错。
3. **02.Q2 diff**：构造"02 进入红 K3、03 进入仍红 K3"→ fail（硬升）；"02 红、03 已清"→ pass。
4. **B2-B4 字段**：sidecar 加 chain_links/honest_gaps/market_implied 后 schema 校验通过、dashboard 现消费不破；04.Q1/Q2/Q3 能读出。
5. **B5′ 卷积**：读 web_search_log + manifest + fetch_status，卷出"搜 N / 入库 M / 降级 K"面板，数字与底层一致。
6. **复核旗**：③ 类探针只出 flag、绝无脚本伪造的 pass/fail 质量结论。
7. **页面**：渲染器吃 Trace 出诊断页，体检条/分区/复核旗汇总齐，时间线泳道正确。

## §9 关键文件

- 新建 `prism/scripts/observability.py`（`run_probes` + 各探针）
- 新建 诊断页渲染器（仿 `prism/scripts/dashboard.py`）
- `prism/scripts/topic.py`（B1：`set_stage` 写 `stage.history` + 快照）
- `prism/scripts/gap_detector.py`（B1：精简快照导出；既有 `autofetch_debt`/`empty_pending_decision` 已就位）
- sidecar 模板 + 04 路径文档（B2/B3/B4：chain_links / honest_gaps / market_implied 字段）
- 读但不改：`manifest.py`、`web_prescan.py`（`list_search_log`）、findings frontmatter

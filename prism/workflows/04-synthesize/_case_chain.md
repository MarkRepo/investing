# 决策链合成 · 共享链骨架（`_case_chain.md`）

> **调度提示**：本文件是 **company / industry / arena 三类 case 在 04-synthesize 阶段共用的链骨架**（定位/分工/护栏/6 环因果序/Step 0-6 通用流程/汇报骨架）。执行时：**先读本骨架，再读对应 type 卡**（`_type_company.md` / `_type_industry.md` / `_type_arena.md`），在骨架标「→ 见 type 卡 §X」处回到 type 卡取 type 专属内容（元目标 / 6 环【必带硬落地】 / 取数口径 / sidecar / critic 逐环 / 汇报填空）。整体替代 `_shared.md` + `01-08` 的 8 份分箱 spec。
>
> **复用上游、不重写**：00-research → 01-roadmap → 02-materials → 03-findings 产出的 findings、`gap_detector`、增量重写判定、`financial_data` 财务模块、dashboard sidecar、`00-primer.md`、`thesis` 全部沿用，本骨架只重做"合成"这一段。
>
> **sidecar schema 保留**：`_decision_kit_spec.md`（company 07）/ `_arena_select_spec.md`（industry 09）/ `_peer_matrix_spec.md`（arena 10）均不删——作为对应环的 sidecar schema + stub 创建机制被 type 卡 Step 4 引用（查 schema，不照搬结构）。

---

## 0. 定位与边界

> 📎 *各 type 的定位/边界、与旧路径的根本改动 → `_case_reference.md` 附录 A0（执行时可跳过）*

---

## 1. 核心方法

沿用 `00-primer.md` 已验证的"给目标 + 自由发挥 + 独立 critic 校验"闭环，但分两层落地：**primer 是上游理解地基（纯自由发挥），case 是下游决策（自由发挥锚定在决策链上）。**

### 1.1 不变的元目标（逐字不改）

→ 见 type 卡 §元目标（company/industry/arena 各一条，**逐字不改**）。

### 1.2 理解先行：primer 与 case 的依赖与分工（**核心规约**）

分工表（谁先生成 / 读者 / 干什么 / 谁依赖谁）的**读者与"干什么"单元格按 type**，见各 type 卡卡头。时间轴恒定：**学懂领域(primer) → 做决策(case) → 持续追踪(thesis)**。生成顺序 = 阅读顺序。

**primer↔case 分工（杀掉两者重复，硬规约）**：
- **primer** = 教科书级、可独立读懂的领域/公司/行业/赛道背景（深讲商业模式机理、术语、产业链、玩家）。
- **case 环①** = **已假定读者读过 primer** 的"决策导向速写"——只点决策相关的张力（钱怎么来 + 哪个张力直接影响估值/迁移/胜负），**不重教 primer 已讲透的背景**，需要深度就写"详见 primer"。
- 例外：若用户明示跳过 primer，则 case① 退回"自带压缩版理解"（自洽，可独立读）。原则不变：**理解永远在决策上游；primer 是这份上游理解的完整外化形态，存在时排最前。**
- 各 type 的 primer↔case 边界侧重（地图/路线"是什么"归 primer，动态方向/胜负判断归 case）→ 见 type 卡卡头。此边界 chain-critic 必查（funnel 类重叠面比 company 大，尤其要守）。

### 1.3 跨层复用质量护栏（**硬规约 · 与 Step 1 亲属 hook 配套**）

跨层复用是"站在肩膀上"，**不是"继承结论"**。亲属（父/子 topic，见各 type 卡亲属 hook）的蒸馏产出只作输入/参照，质量永远按本维度、本 topic 自身的 findings + 自身的 critic 来卡：
1. **本维度自己跑完整链**：照常跑 primer + 6 环 + critic，全程按本 type 级分辨率要求。亲属产出是脚手架不是正文。
2. **质量闸门一律本地**：`gap_detector`、chain-critic、05-critic、来源分层都对着**本 topic 自己的 K# 和 findings** 跑，不因"父/亲属已覆盖"放水。
3. **借来必标来源**：正文里 borrowed-from-relative 的内容可见地标出（对齐 mat-XXX 分层惯例），不许借来的框架冒充本 topic 自验证的结论。
4. **冲突时本维度赢**：亲属观点与本 topic 自己的 findings 打架 → 以本 topic 为准，允许背离；背离触发向上路径把亲属标 stale（`gap_detector` 的 `relative_updated` flag 会提示亲属产出比本 case 新）。

### 1.4 决策链（6 环 · 这就是契约本身）

**必须按序走完整条链，每一环必须落地（见各 type 卡 §6 环各自的【必带硬落地】）。不允许断链（如有 ④ 下注却无 ⑤ 证伪、有 ⑥ 行动却无 ② 锚）。** ASCII 因果序框架（三类结构相同，环名细节见 type 卡）：

```
① 能不能看懂？（理解闸门）
   └─ 看不懂/信不过就不投/不配/不选。→ 见 type 卡环①
        ↓ 看懂也信得过了，那市场现在怎么给它定价——
② 市场此刻替它定了什么价？（定价锚）
   └─ 反推当前价/估值隐含的预期（必须有数字）。这是后面一切判断的锚。→ 见 type 卡环②
        ↓ 这套定价，
③ 需要什么假设为真？（What-Must-Be-True）
   └─ 把②的定价翻译成 3-5 条可证伪的具体假设。→ 见 type 卡环③
        ↓ 这些假设，
④ 我信哪边/押谁，凭什么？（下注）
   └─ 多空/横比交锋 + 核心分歧一句话 + 我的判断。→ 见 type 卡环④（company 含 EV 加总；funnel 含 6 维/peer 横比）
        ↓ 我这个判断，
⑤ 如果错了会怎样、怎么第一时间知道？（证伪机制）
   └─ 风险/盲点 + 历史失败镜鉴 + kill 触发 + signpost。→ 见 type 卡环⑤
        ↓ 综合①-⑤，
⑥ 那就在什么价/仓位/时点做什么 / 怎么分流？（行动）
   └─ company: 买入框 + 仓位框架(接④EV) + 阶梯；funnel: 深挖/观察/淘汰三档(tier=吸引力×定价) + 建 stub。→ 见 type 卡环⑥
```

> 📎 *为什么链是紧的 / 与 company EV 的刻意差异 → `_case_reference.md` 附录 A1.3 / A1.4（执行时可跳过）*

---

## 2. 执行 — 上游准备与 primer 先行

### Step 0：前置检查 + gap 体检（双轴）+ 增量判定 + 命门 delta 重拆（**引用 `_shared.md`，不重抄**）

进 04 第一件事，照 `_shared.md` 跑三段，结果完整贴对话：

1. **前置检查**（资料 ≥3 份，否则停）。
2. **gap 体检**（`detect_gaps` 三项任一非空 → 不要硬合成，先补救）。
3. **增量重写判定**（`list_affected_outputs` 判 new/stale/fresh；`fresh` 跳过）。本 type 路径 output_key 见 type 卡 §sidecar / §产出形态。

> Web 搜索路径见 [[_web_search_routing]]；本阶段默认走 adapter。即兴 web-search 规约见 `_shared.md`。
> **company 专属**：进 case 正文前先过 **Step 0.5 质量红线门控** → 见 `_type_company.md`（industry/arena 无此闸门）。

### Step 1：加载 findings + thesis_v0 + 取数 + 亲属 hook

1. 照 `_shared.md` § 调度模式：`format_findings_for_prompt` 列 findings → 主 agent 并行 Read；`build_findings_index` 落盘 `_findings_index.md`（防 compact 地图）；读 `thesis_v0.md`（强度 v0→v1 锚）。
2. **拉取数**（财务轨迹 / 行情倍数 / 宏观 —— 口径按 type）→ 见 type 卡 §取数（含 `financial_data` / `market_data` 一手锚拉法、F13 硬 checkpoint、亲属复用 hook、company 的 macro 强制 hook）。财务/行情**不在 findings 里手抽**。
3. 写 `outputs/_synthesis_brief.md`：dump 核心 thesis / 关键假设 / v0→v1 强度调整，供 ④⑤⑥ 与 critic 复用。

> **调度模式**：case 默认**主 agent 直做 + 并行 Write**（同 `_shared.md` 默认；勿 dispatch subagent 写长产出，见 [[subagent-write-hallucination]] / feedback_subagent_bulk_synthesis）。唯一 subagent 是 critic（只读不写）。

### Step 2：**先出 `00_primer`（理解地基）**

按 `00-primer.md` Step 1-5 执行，产 `outputs/00_primer.md` + `_prism_reading_guide.md`。

**走 `00-primer.md` 的 primer-first 路径**（00-primer.md 已全类型统一 primer-first，见其头部调度提示）：
- 原材料 = **findings + `thesis_v0` + K# + type 卡 §取数拉到的财务/行情 + 亲属 primer（若有）**。
- 投资加权（"该讲什么"）来自元目标 + thesis_v0 + K#，**不需要等 case**。
- primer 其余流程（目标生成 / 起点诊断 / 自由发挥 / 来源分层 / depth 降级 / **独立 critic 校验**）照走，critic 不可省。
- primer 写完即 critic 收敛后，才进 Step 3 写 case——**case 站在已校验的 primer 上**。

---

## 3. 执行 — case 决策链（站在 primer 上）

### Step 3：走决策链写 case（case key 见 type 卡）

#### 3.1 起点诊断（写正文前必做 · 借 `00-primer.md` §2.1）

因 primer 已建好领域地基，case 的起点诊断**轻量化**：只需确认 (a) 本 topic 的**命门/特色点** 1-3 个（命门所在的环重点打、给足篇幅）；(b) case① 该把哪些背景"甩给 primer"、自己只留决策导向速写。

> 命门**不从零拍脑袋**：以 00 的 `decomposition_v0` 为种子，读完 findings 后按 `_shared.md` §"B 轴有界 delta 重拆 + 收敛"做 delta 校验（新增/掉队/重排/置信度更新）→ delta 非空则有界第二收料趟（封顶 2 轮）→ 落 `decomposition_v1`（changelog 防震荡）。

#### 3.2 逐环落地（链内无固定子节模板，每环给"必须落地什么"）

每环五样：**【元问题】/【为何由上一环逼出】/【必带硬落地】(决策机制保证，不可省)/【别漏的 lens】(01-08 当 checklist)/【自由区】**。子问题、子标题、表格、详略、类比全在自由区。

→ **6 环各自的【元问题】/【必带硬落地】/【别漏的 lens】见 type 卡 §6 环**（type 专属差异——company 三梁 / EV 加总；funnel 价值链-利润池 / 卡位-路线 / 6 维评分 / peer 横比 / 三档漏斗——一字不改地承载）。

#### 3.3 来源分层 + depth 降级

- **来源分层**（照搬 `00-primer.md` §2.3）：训练知识不标单条 / findings 凡引必标 `[mat-XXX]` / 亲属借用按 §1.3 标 / 特色判断文末点到指向 thesis_v1。文末 `## 信息来源` 给三者占比 + mat 列表。
- **depth 降级**（照搬 §2.4）：关键环数据缺口能训练知识粗估则标注"训练知识估算"，补不了明写"数据缺失"，**不编造**。瓶颈通常在 findings 覆盖度。
- **company 专属**：环②估值模型库（原型识别 + 模型 A–H）→ 见 `_type_company.md` §取数/环②与 `_valuation_models.md`。

#### 3.4 产出形态（份数交给 LLM）

- **默认一份连贯文档**（case key 见 type 卡）：决策链 ①→⑥ 作为主脉络，读者顺读即顺着决策走。
- 长度逼迫（自评 >8000 字且体验下降）可拆 2-3 份，**必须保持链序** + 每份开头交代"在链哪一环、承接上一份什么结论"。拆分键名见 type 卡 §sidecar。
- 无论几份：**起点诊断、6 环（各环硬落地齐）、sidecar、来源分层缺一不可** → 各 type 的"无论几份 checklist"见 type 卡 §产出形态。

### Step 4：写 sidecar（**硬契约 · schema 原样不动**）

⚠️ dashboard.py 只读对应 sidecar、只认那套字段名。**禁自创/改名/漏字段**，否则该 topic dashboard 整行为空。→ 见 type 卡 §sidecar（sidecar 文件名 + 字段来源环 + schema 引用处 + 建 stub / 继承父 thesis）。数字不加引号，缺失 null。写入用 `Path(...).write_text(...)`。

---

## 4. 执行 — 收尾

### Step 5：落盘 + 状态注册 + **thesis_v1（最后）**

每份落盘后注册引用（output keys 见 type 卡 §sidecar / §产出形态）：

```bash
python3 -c "
from prism.scripts.topic import set_output_status, set_output_referenced_mats, read_topic
t = read_topic('{slug}', '{variant}')
for key, mats in {'00_primer': [...], '<case_key>': [...], '<sidecar_key>': [...]}.items():
    cur = t['outputs_state'].get(key, {}).get('version', 0)
    set_output_status('{slug}', key, 'fresh', '{variant}', version=cur+1)
    set_output_referenced_mats('{slug}', key, mats, '{variant}')
print('primer + case 产出已注册')
"
```
> 新 case key 靠 `set_output_status` 的 `setdefault` 自动注册，**不用改 topic.py**。

**thesis_v1（决策链跑完后才写）**：照 `_shared.md` § thesis_v1 的 **Scheme C 全快照 11 段式**，不改。先读 `_synthesis_brief.md`，dump v0→v1 强度调整，写 `thesis_v1.md`，调 `set_thesis(version=1, ...)`。**同时写 `decomposition_v1.md` + `set_decomposition(version=1, summary, stage_set_at, convergence_status, changelog)`**（`summary`/`stage_set_at` 必填；`convergence_status ∈ {open, converged, capped}`；完整示例见 `_shared.md` §B 轴有界 delta 重拆）。收尾出**终态报告**（双轴 gap + 收敛状态 + 残留缺口诚实清单），见 `_shared.md` §终态报告。

**收尾**：照 `_shared.md` § 全部产出完成后（含 capped→suggested_drilldowns 回流）——`append_user_todos` + 清 `next_actions` + stage 推进。合成完 stage 置 `05-critic-review`（第 6 阶段「评审」，三类统一）——**company 必经 05 才能 `done`；industry/arena 的 05 critic 非强制**（可说「评审 {slug}」跑对抗式 steelman，或 web 详情页点「✓ 标记完成」直接 `done`）。industry/arena 的 stage 推进细节 + 旧 stage 名退休提示 + 宏观软提示见 type 卡 §收尾（company 必经 05，见本节）。

> **可选 primer 补丁**：若 case 暴露 primer 漏讲的命门（如某条命门假设需要的背景 primer 没铺），回头给 primer 打一个便宜补丁（局部 Edit + 升 version），不重写。primer 是上游，但允许一次下游反馈触碰。

### Step 6：critic 校验（**对着决策链** · 写完即跑一轮内嵌 chain-critic）

写完即跑一轮**内嵌 chain-critic**（合成期质控，模型同 `00-primer.md` Step 3，已验证 2 轮内收敛）。它与下游 05-critic 分工：chain-critic 查"链有没有走通、有没有断"，05 做对抗式 steelman 重审。

dispatch 独立 critic（`subagent_type: general-purpose`，不传 model，**只读不写**），逐环校验链是否走通（文里没讲清就标"断"，不用文外知识补）。**通用检查项（三类共有）**：
- **断链检查**：④下注↔⑤证伪、⑥行动↔②锚、⑥↔④ 是否一致（逐环问什么 + type 专属断链项见 type 卡 §critic）。
- **primer↔case 是否有重复**（case① 该甩 primer 的背景有没有甩）？
- **跨层复用护栏（§1.3）**：借来的判断标了来源吗、有没有冒充本维度自验证？
- **源分层**：findings 数字标 [mat-XXX]？

→ **逐环问什么 + type 专属核对（🎯目标达成核对 / 🔒终局证据强度核对 / 强制重修订门）见 type 卡 §critic**。薄弱维度翻成 `suggested_drilldowns`（`source=critic_weak_k`，`priority=P0`）挂 `set_suggested_drilldowns(mode='append')`；命门两轮未解则必要时 `set_decomposition(convergence_status='capped')`。

四段总评（链通不通 / 最严重 2-3 个断点 / **type 专属判定（见 type 卡）** / 只补一处补哪），苛刻直接，1800 字内。按反馈修订（主 agent 直接 Edit）；首轮涉断链（及 type 卡列明的其他触发）则跑第二轮。

**critic-review 阶段（05）**：按 type 规则进 `05-critic-review` 做对抗式重审。`05-critic-review.md` Step 1 已按 type 读对应 case 文件、rewrite_keys 用对应 case key——用户说「评审 {slug}」直接跑，无需手动替换。

### 汇报

→ 见 type 卡 §汇报（含各 type 的链体检模板与下一步提示）。

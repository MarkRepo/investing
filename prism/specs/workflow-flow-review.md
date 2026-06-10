# Prism 主线流程评审（00→05，排除宏观层）

> 评审日期：2026-06-08
> 范围：主线 workflow `00→01→02→03→04→05` + 共享规约文件（`_autofetch_protocol` / `_web_prescan_shared` / `_input_contract` / `04-synthesize/_shared` 等）。
> **排除**：宏观层（`04-synthesize/_macro_regime.md` 及宏观 stage 流程，仍在开发）。
> 关注点：① 流程明显缺陷（导致错误执行）；② 一次执行内的上下文流程简化（不改原语义与产出）。**不含**纯文档抽取复用、不含 industry/arena/company 三路径之间的重复（它们不属于同一次执行）。
> 核实方式：读 `DESIGN.md` + 全部 workflow 规约 + grep `prism/scripts/` 实现交叉验证。每条给 `file:line` 可直接定位。
>
> **处置状态（2026-06-08 更新）**：A1 ✅ · A3 ✅ · A4 ✅ · A5 ✅ · B1 ✅（精修方案）· B4 ✅ 已修 · A2 ⏸ 决定不修 · A6/B2/B3 仍为建议、未动。

---

## A 类 · 流程缺陷（建议修）

### A1 🔴 ✅ 已修 · `auto_resolve` 死引用 4 处——会重新制造系统已修过的"假 pending"病

> **2026-06-08 已修**：根因确认在 commit `6cda30d`（删 `auto_resolve_todos`/`suggest_*coverage*` 代码时漏改这几处流程文档）。4 处全部改成显式 `update_user_todo_status(...,'done',covered_by=)` 收口；`DESIGN.md:178` 同步（见 A5）。`grep auto_resolve` 现仅余正确的"已删除"说明。

脚本里 `auto_resolve_todos` / `suggest_*coverage*` 已**彻底删除**（确认：`prism/scripts/` 无任何 `def auto_resolve`，全部 `.py` 零出现；只剩 `addresses_match_event_anchored` 这个粒度校验 helper。`_autofetch_protocol.md:15/40` 与 `_web_prescan_shared.md:298` 也明确写"已删"）。但下列 4 处仍告诉 LLM 这些函数会自动核销 todo：

| 位置 | 文本 | 后果 |
|---|---|---|
| `_autofetch_protocol.md:91` | "will_collect…用户补的料一登记，auto_resolve 自动翻 `fetched`" | **最严重**。与本文件自己的 :15/:40/:51 直接矛盾；will_collect todo 被许诺自动翻转，实际永远挂 pending → 砸穿该文件标榜的"反静默核心" |
| `02-gather-materials.md:260` | "`fetched` 的会被 auto_resolve 自动标 done…无需手动降级" | 与同文件 Step 6 手动 `update_user_todo_status`(:337-339) 矛盾；LLM 以为不用手动收口 → fetched 仍计入"待补料" |
| `05-critic-review.md:411` | "含 addresses，否则后续 auto_resolve 算不进" | request-more 必带 addresses 的**理由是假的**（字段要求本身可能仍合理，但论据指向死函数） |
| `04-synthesize/_shared.md:205` | "补料登记后 auto_resolve 自动翻 fetched" | 同 A1 第一条 |

这正是 `DESIGN.md` §1.3「薄弱点」和 Part 3「pending 仅留真待办」想根治的洞，却被这 4 处文案重新打开。

**建议**：删掉"auto_resolve 自动…"的承诺，改成显式 `update_user_todo_status(...,'done',covered_by=)` 的指令（其它步骤已是这么写的）。这是评审里**唯一确定会导致错误执行**的项，建议优先修。全是 workflow 文案、不碰脚本符号，风险低。

### A2 🟡 ⏸ 决定不修 · `01 Step 8` 与 `00 Step 4.5b` prescan 槽位重叠

**代码核实**（`web_prescan.py:461 build_search_queries`）：该函数只枚举"槽位"、不拼 query 文本（query 由主 agent 在对话里写，:480）。槽位来源：
- `scope`(:495) 任何 topic 都有；`company-event`(:512) type==company 且有 ticker；`industry-event`(:526) type∈(industry,arena)；`concept-update`(:536) 逐 concept——这 4 类只依赖 `type/ticker/concepts/search_terms`（:483-490，00 时已定死）。
- `l4-hunting`(:551) **仅当 `roadmap.yaml` 存在**（:547）才出槽，逐 K# 对齐。

所以：`00 Step 4.5b` 时无 roadmap → 只出 scope/company/industry/concept 槽；`01 Step 8` 时 roadmap 已在 → 出**完全相同的那 4 类槽 + 新增 L4/K# 槽**。即 #1–4 槽两次结构相同、hint 相同、90 天窗口几分钟内重合 = **功能性重复拉取**；01 真正新增、00 给不了的只有 L4/K# 槽。

**为何不修**（精修结论）：① 重复的只有 #1–4（company/concept 各 ~2–4 条 query），省量有限；② query 文案是 agent 每次自写，01 已带 thesis 上下文、重写可能**比 00 的盲扫更准**，重拉不是纯浪费；③ 正确简化是**槽级**（"有近窗 00-prescan 料则跳 #1–4、永远跑 L4"）而非套用 02 的**步级** `should_run`（那会把 L4 一起跳掉、反而砍掉 01 prescan 的全部价值）。综合：幅度小 + 带 tradeoff + 易写错，**优先级最低，决定不动**。

### A3 🟡 ✅ 已修 · `05` verdict 口径自相冲突

> **2026-06-08 已修**：在 Step 7 表 `request-rewrite` 行的「何时选」补"（承重项为单线承重时降级为 request-more，见 Step 5.5/Step 0 横幅口径）"，与 5.5「单线承重 最高 request-more」对齐。


- `Step 5.5`(:259)："**单线承重** 最高 `request-more`"。
- `Step 7` 表(:366)：`request-rewrite` 选用条件 = "评分 ≥3 但部分 K# 论证薄弱"。

一个"单线承重"（某承重结论靠单源/二手）且评分 ≥3 的 case：Step 7 表判它该 `request-rewrite`，Step 5.5 却封顶 `request-more`。两条闸门对同一 case 给出不同 verdict。

**建议**：在 Step 7 表的 request-rewrite 行补一句"（承重为'单线承重'时降级为 request-more，见 5.5）"，让口径单一。

### A4 ⚪ ✅ 已修 · `05 Step 0.0`(:42)措辞错位

> **2026-06-08 已修**："BLOCK 04-synthesize"→"封顶 verdict（最高只能 request-more，不许 approve）"，并补一句点明"05 在 04 之后跑、不能回头拦 04，闸卡在 critic 自己头上"。


"`status=='failed'` → **BLOCK 04-synthesize**"。05 运行在 04 **之后**，无法 block 04；真实机制是紧随其后写的"verdict 最高只能 request-more"。措辞会误导（像是回去拦 04）。**建议**：改为"封顶 verdict / 要求用户二选一"。

### A5 ⚪ ✅ 已修 · 文档漂移（影响心智模型，非纯文档清理）

`DESIGN.md:178` 仍写 "Stage 01 …Step 8 prescan + **auto_resolve**"，但 01 Step 8 实际文本(:589-599)早已不含 auto_resolve。修 A1 时顺手对齐。

### A6 ⚪ `04` decomposition_v1 双持久点

`_shared.md:104` 允许在 Step 0 delta 判定时就 `set_decomposition(version=1)`，而 `_company_case.md:270` 把它放到 Step 5 收尾。两个落盘点，可达但易困惑；建议统一到收尾。

> **2026-06-09 备注**：曾按"删早写、统一收尾"修过一版（核实早写为真冗余：收料/分析靠对话内 delta 命门、B 轴 K# 取自 thesis、v0 已满足 has_decomp、无脚本读 convergence_status）；**用户决定回退**，保留双持久点现状。本条恢复为建议、未动。

---

## B 类 · 一次执行内可简化（不改语义/产出）

### B1 ⭐ ✅ 已修 · gap 报告"完整贴到对话"在一次执行内重复 4–5 次，其中两对是**同状态边界重复**

`detect_gaps` 是纯读、确定性，但每个体检点都要求"把 report 输出**完整贴到对话**"（`02:273` / `03:30` / `04 _shared:38` / `05:59`，外加 `04 终态 _shared:341` 的结构化总结）。问题有二：① report 本就已在 Bash 工具输出里出现一次，主 agent 再"完整贴/复述"一遍 = **同一份贴两遍**；② 用户实际看 web（覆盖徽章 + 待办），对话里的全文清单对用户是噪音。另有两对在状态未变的相邻边界上重复跑：
- `02 Step 5.8`（出口）↔ `03 Step 0a`（入口）：之间只 `set_stage`，**无新料、无 findings**。
- `04 终态`(_shared:341) ↔ `05 Step 0`：04 收尾刚跑过，直连进 05 无状态变更。
（`03→04` 不算：03 产出 findings，04 Step 0 是变后状态，合法。）

> **2026-06-08 已修（精修方案，用户拍板）**：体检脚本**照跑**（主 agent 要用结果决策）、双轴/四项**照看**、web **不动**；只把"完整贴到对话"改成"主 agent 直接读 Bash 输出做决策、对话只回**一句话摘要**、不再整份复述"（`02/03/04 _shared/05` 四处）。并在 `03 Step 0a`、`05 Step 0` 两个"紧跟上一阶段出口"的入口加一句"**若本会话直连推进、其后无状态变更则沿用、不必重跑**"。产出与判断不变。`04 终态报告`保留（它本就是结构化总结、非裸贴，且是合成完成的诚实缺口交付物）。

### B2 ⚪ `01→02` 直通时 auto-fetch 全覆盖逻辑重复

`01 Step 5.6`（深抓）+`Step 5.8`（unattempted=0 硬闸门，:447）已保证进 02 时无 unattempted；`02 Step 5.7`(:252 "对每条")再跑一遍 auto-fetch 阶梯，`02 Step 6`(:312-326)再断言一次 unattempted/error=0。直通且无新料时，02 这趟基本空转。

注：`02` 开头(:42)已显式声明 Step 5.7/5.8/6 不可跳（因 02 是用户上传料的收料点），所以这是**可接受的重入设计**，实际成本是"循环找不到事做"而非重复拉取。仅作记录，优先级低。

### B3 ⚪ `register_inbox_materials` 一次执行调 3 次

`00:120` / `01:499` / `02:93`，幂等但 01 那次在 00 已 ingest 且 00→01 间通常无新料时是空操作，可省。低。

### B4 ⚪ ✅ 已修 · Q# 残留在**活跃写路径模板**里

> **2026-06-08 已修**：写路径模板去 Q#——`03:478`、`_shared.md:403` 的 `addresses=['{...K# 或 Q#}']` → `['{...K#}']`；`00:293` 的 `addresses=[K#, Q#]` → `[K#]`；`_web_prescan_shared.md:168` 表头「K# / Q# 列表」→「K# 列表」。三态表（`_web_prescan_shared.md:359/362`）保留 Q#**向后兼容读**说明（"旧 topic 残留 Q# 仍可读，新 topic 不再产"），不再诱导写。`00:326/328` 为解释性散文（讲 fact-NN/覆盖来源、非可抄模板），不动。


`03:478` / `_shared.md:403` 的 `addresses=['{K# 或 Q#}']`，以及 `_web_prescan_shared.md:168/359/362` 三态表，而新 topic 永不产 Q#（`00:391-396` 已废）。这些是 LLM 会照抄的字符串，留着会诱导它复活废弃维度。建议从写路径模板里去掉 Q#（三态表保留"向后兼容旧 topic"的说明即可）。低。

---

## 处置小结（2026-06-08）

- ✅ **A1** 死引用 4 处 + **A5** DESIGN 同源漂移——已修（根因 commit `6cda30d`）。
- ✅ **B1** gap 报告重复贴——已修（精修方案：脚本照跑、对话只回一句话摘要、web 不动 + 两处入口直连沿用）。
- ⏸ **A2** prescan 槽位重叠——核实为槽级·幅度小·带 tradeoff，**决定不修**。
- ✅ **A3/A4**（05 verdict 口径冲突 / Step0.0 措辞）——已修（Step 7 表补降级口径；Step 0.0 改"封顶 verdict"并点明 05 不能回头拦 04）。
- ✅ **B4**（Q# 残留写路径模板）——写路径去 Q#，三态表保留向后兼容读。
- ↩️ **A6**（decomposition_v1 双持久点）——曾修后**用户回退**，保留双持久点现状，恢复为建议。
- ⬜ **B2/B3**——清理项，可顺带，**待定**。

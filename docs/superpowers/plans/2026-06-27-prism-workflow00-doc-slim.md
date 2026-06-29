# Prism Workflow 00 文档瘦身（relocation, not deletion）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `prism/workflows/00-research-topic.md` 的执行主路径从 740 行密集散文瘦到 ~1/3（≈230 行可执行正文），办法是把"为什么 / 反例 / 历史教训 / memory 链接 / inline worked example"**逐字搬到同文件末尾的 `## 附录 A`**（搬迁，不删除），主流程只留"做什么 + 命令块 + 规约 + 一行指针"。**不改任何执行语义、不改 Step 编号、不动 .py、不动其它 workflow 文件。**

**Architecture:** 这是**纯文本搬迁**——被移走的每一段散文都逐字重现在附录里，所以"等价性"机械可审。执行模型是 **per-step：先把要搬的块逐字复制进附录对应 key，再把主流程里那块替换成一行指针**（先 append 后 trim，保证文本在被删前已落附录）。最后跑一个硬验证 harness 校验 6 个不变量；任一不变量失败即停。

**Tech Stack:** Markdown；定位/搬迁用 Read + Edit 工具做 verbatim 字符串操作；验证用 `grep`/`rg`/`diff`/`wc`/`awk`（macOS bash）。

## Global Constraints

- **只改一个文件**：`prism/workflows/00-research-topic.md`。禁止编辑任何 `.py`、禁止改其它 `.md`（除非 T-VERIFY 的不变量 (e) 暴露下游引用断裂——那种情况停下报告用户，不擅自改下游）。
- **搬迁不删除**：被移出主流程的每一段，必须**逐字**（含标点/markdown 标记）出现在 `## 附录 A`。不允许改写、概括、合并被搬的散文。
- **Step 编号是锚点，逐字不动**：下游文件按 Step 号引用 00（`_baseline_knowledge.md`/`00-primer.md`/`01-build-roadmap.md`/`_arena_select_spec.md`/`_peer_matrix_spec.md`/`_web_search_routing.md`/`_web_prescan_shared.md`/`SKILL.md`）。这 19 个标题逐字保留：`## 00 速览` · `## Step 1` · `### Step 1a` · `### Step 1b` · `## Step 2` · `## Step 3` · `## Step 4` · `### Step 4.0` · `## Step 4.3` · `## Step 4.5` · `### Step 4.5a` · `### Step 4.5b` · `### Step 4.5c` · `## Step 5` · `## Step 5.4` · `## Step 6` · `## Step 6.5` · `## Step 6.5e` · `## Step 7`（注：`### 5.0/5.0a/5.1/5.2/5.3` 是 `## Step 5` 下的子节，也逐字保留）。
- **命令块逐字保留在主流程**：所有 ```python / ```bash 代码块（含块内注释，那是字段 spec）原样留主流程，**一行都不进附录**。
- **结构事实留主流程**：下游按"Step 5.0 四段式 / Step 4.3 五段 / Step 5.4 性质约束·终局豁免 / 三态语义 / 字段约束"直接引用——这些**清单/约束**留在对应步内可见，**不进附录**。具体见各 Task 的「保留」清单。
- **逐字匹配**：每个 Edit 的 `old_string` 必须先 Read 当前文件 verbatim 复制；前序 Task 改动会让行号漂移，**用唯一字符串定位，不要依赖行号**。
- **提交范围**：当前分支 `docs/wf00-fixes`，工作树有大量**无关**的研究产出改动（`prism/topics/...`、`prism/dashboard.md` 等）。本计划**只 stage 这一个文件**，绝不 `git add -A`。

### keep / move 判据（统一规则，逐段套用）
对主流程里每一段，问一句：**"下游文件或执行 agent 正确做这步，必须看到这段吗？"**
- 是 spec / 命令 / 硬约束 / 输出格式 / 决策分支骨架 / do-checklist → **留主流程**。
- 是 justification（`**为什么**`/`**为什么必须做**`段）/ 历史教训 / 纯论证型 `>` 引用 / `[[memory-slug]]` 解释 / 第 2 个起的反例正例 / inline worked example（如茅五泸 dict、荣昌生物长示例、百科式 question 改写示例）→ **搬附录**，主流程留 1 行最小骨架 + 指针。

### 指针格式（主流程里替换被搬块的位置）
统一写成单行斜体引用（`{key}` 用该步附录小节号，如 `A4.5b`）：
```
> 📎 *为什么 / 反例 / 历史教训 → [附录 A{key}](#附录-a{key})（执行时可跳过）*
```
（markdown 锚点不强求可点；文字指针足够导航。一个步若搬多块，合用一条指针即可。）

---

## File Structure

- `prism/workflows/00-research-topic.md` — 唯一受改文件。
  - 头部（触发/产出）+ `## 00 速览`：逐字保留，作精简后主索引。
  - `## Step 1 … ## Step 7`：精简执行路径。
  - 文件末新增 `## 附录 A — rationale / 反例 / 历史教训（执行时可跳过）`，按 Step 号收纳所有搬走的散文，小节顺序：`A1a · A1b · A3 · A4.0 · A4.3 · A4.5 · A4.5a · A4.5b · A5.0 · A5.0a · A5.2 · A5.3 · A5.4 · A6.5 · A6.5e`。
- `docs/superpowers/plans/_wf00slim_baseline/`（临时，T0 建，T-VERIFY 后删）— 存搬迁前的基线快照（代码块清单、锚点清单、行数）供不变量比对。

---

## Task 0: 基线快照（搬迁前先固化"真相"）

**Files:**
- Create: `docs/superpowers/plans/_wf00slim_baseline/codeblocks.txt`、`anchors.txt`、`metrics.txt`

- [ ] **Step 1: 确认当前分支 + 文件存在**

Run:
```bash
cd /Users/mark/investing && git branch --show-current && wc -l prism/workflows/00-research-topic.md
```
Expected: 分支 `docs/wf00-fixes`；行数 740（±数行，以实际为准，记下此数 `$ORIG`）。

- [ ] **Step 2: 落基线快照（代码块行集 / 锚点 / 行数）**

Run:
```bash
cd /Users/mark/investing
mkdir -p docs/superpowers/plans/_wf00slim_baseline
F=prism/workflows/00-research-topic.md
B=docs/superpowers/plans/_wf00slim_baseline
# (b) 代码块不变量基线：抽出所有 fenced code block 内容（去掉 ``` 围栏），排序去重存档
awk 'BEGIN{inb=0} /^```/{inb=!inb; next} inb{print}' "$F" | sort > "$B/codeblocks.txt"
# (a) 锚点不变量基线：所有 Step / 速览 标题
grep -nE "^#{2,4} (Step|00 速览)" "$F" > "$B/anchors.txt"
# 行数
wc -l "$F" > "$B/metrics.txt"
wc -l "$B/codeblocks.txt" "$B/anchors.txt"
```
Expected: `anchors.txt` 19 行（19 个标题）；`codeblocks.txt` 非空（记下行数，T-VERIFY 要逐字比对一致）。

- [ ] **Step 3: 不提交快照目录（仅本地比对用）** — 无需 commit；T-VERIFY 末尾会删。

---

## Task 1: 建附录骨架（先有容器，后续逐块填）

**Files:**
- Modify: `prism/workflows/00-research-topic.md`（文件末尾追加）

- [ ] **Step 1: 在文件最末追加附录骨架**

先 Read 文件最后 ~10 行，确认末尾内容（当前末行是 Step 7 的 `> 若 {M}=0...不伪造待办。`）。用 Edit 把**当前最后一行**替换成"它本身 + 附录骨架"。

old_string（当前文件最后一行，Read 后 verbatim 取）:
```
> 若 {M}=0（00 eager-fetch 全抓到），"你需要做的事"应为空——直接进 01，不伪造待办。
```
new_string:
```
> 若 {M}=0（00 eager-fetch 全抓到），"你需要做的事"应为空——直接进 01，不伪造待办。

---

## 附录 A — rationale / 反例 / 历史教训（执行时可跳过，调试 / 维护时查）

> 本附录收纳从各 Step 主流程搬出的"为什么 / 反例 / 历史教训 / memory 链接 / inline worked example"。**主流程逐字未删、只是移出执行动线**；要看某步的来龙去脉，按 Step 号查对应小节。

<!-- APPENDIX-ENTRIES -->
```

- [ ] **Step 2: 验证骨架就位**

Run:
```bash
grep -nF "## 附录 A — rationale / 反例 / 历史教训" prism/workflows/00-research-topic.md && grep -nF "<!-- APPENDIX-ENTRIES -->" prism/workflows/00-research-topic.md
```
Expected: 两条各命中 1 行。

> **后续每个搬迁 Task 的通用动作**（套用于 Task 2–14，不再重复写）：
> 1. **Read** 目标 Step 区块，verbatim 取出"要搬的块"。
> 2. **Edit#1（先 append）**：把 `<!-- APPENDIX-ENTRIES -->` 替换成 `### 附录 A{key} ...\n\n<搬来的块，逐字>\n\n<!-- APPENDIX-ENTRIES -->`（保留占位符在最下，供下一块续接）。
> 3. **Edit#2（后 trim）**：把主流程里那块 `old_string` 替换成指针行（或并入相邻保留内容）。
> 4. 块的边界：从"块起始 verbatim 短语"到"下一个保留标题 / 代码块 / `---` 之前"。多段连续散文可一次搬。

---

## Task 2（WORKED EXAMPLE / 模板）: Step 4.5b 搬迁 — 照此样式做后续所有步

> **这是给执行者的完整范例。** 后续 Task 3–14 只给「保留清单 + 搬迁清单 + 指针」，搬法照本任务。

**Files:** Modify `prism/workflows/00-research-topic.md`

**保留主流程：** `### Step 4.5b：跑覆盖槽 prescan` 标题；`调用 \`prism/workflows/_web_prescan_shared.md\`，参数 \`recency_days=90\`，\`triggered_by='00-prescan'\`。`；其后的 `跑完后输出汇报模板：` + 那个 ``` 汇报模板代码块（输出格式，留）。

**搬走 → 附录 A4.5b：** ① `> **4.5b 是兜底地板…**` 整个 `>` 引用块；② `注意：此时 thesis 还不存在…逐槽 query 措辞按 \`_web_prescan_shared.md\` Step A 由主 agent 写。` 整段。

- [ ] **Step 1: append 到附录（Edit#1）**

old_string:
```
<!-- APPENDIX-ENTRIES -->
```
new_string（把 `> **4.5b 是兜底地板...` 与 `注意：...` 两块逐字粘进来；下方 Read 后用真实 verbatim 文本替换示意省略号）:
```
### 附录 A4.5b — 4.5b 为什么是兜底地板而非第二轮普查

> **4.5b 是兜底地板，不是与 4.5a 并列的第二轮普查。** 若 4.5a 的 baseline §5 优先 query 已覆盖 `build_search_queries` 吐的槽（scope / industry-event 等），4.5b 只需确认覆盖、补未被覆盖的边角槽即可，**不必为已覆盖槽另写 query**。它的作用是兜住"§5 写薄"的情况（机械枚举不依赖 agent 想没想到）。

注意：此时 thesis 还不存在、roadmap 尚无 L4，`build_search_queries` 仅会枚举 **scope + company-event / industry-event / concept-update** 覆盖槽（无 l4-hunting 槽），这是预期的——本轮目的是为"写出靠谱的 thesis_v0"打地基，K# 类覆盖留给 workflow 01 prescan。逐槽 query 措辞按 `_web_prescan_shared.md` Step A 由主 agent 写。

<!-- APPENDIX-ENTRIES -->
```

- [ ] **Step 2: 从主流程删块 #1（Edit#2a）** — 删 `> **4.5b 是兜底地板...** ` 引用块

old_string:
```
### Step 4.5b：跑覆盖槽 prescan

> **4.5b 是兜底地板，不是与 4.5a 并列的第二轮普查。** 若 4.5a 的 baseline §5 优先 query 已覆盖 `build_search_queries` 吐的槽（scope / industry-event 等），4.5b 只需确认覆盖、补未被覆盖的边角槽即可，**不必为已覆盖槽另写 query**。它的作用是兜住"§5 写薄"的情况（机械枚举不依赖 agent 想没想到）。

调用 `prism/workflows/_web_prescan_shared.md`，参数 `recency_days=90`，`triggered_by='00-prescan'`。
```
new_string:
```
### Step 4.5b：跑覆盖槽 prescan

> 📎 *为什么 / 反例 / 历史教训 → 附录 A4.5b（执行时可跳过）*

调用 `prism/workflows/_web_prescan_shared.md`，参数 `recency_days=90`，`triggered_by='00-prescan'`。
```

- [ ] **Step 3: 从主流程删块 #2（Edit#2b）** — 删 `注意：...` 段

old_string:
```
调用 `prism/workflows/_web_prescan_shared.md`，参数 `recency_days=90`，`triggered_by='00-prescan'`。

注意：此时 thesis 还不存在、roadmap 尚无 L4，`build_search_queries` 仅会枚举 **scope + company-event / industry-event / concept-update** 覆盖槽（无 l4-hunting 槽），这是预期的——本轮目的是为"写出靠谱的 thesis_v0"打地基，K# 类覆盖留给 workflow 01 prescan。逐槽 query 措辞按 `_web_prescan_shared.md` Step A 由主 agent 写。

跑完后输出汇报模板：
```
new_string:
```
调用 `prism/workflows/_web_prescan_shared.md`，参数 `recency_days=90`，`triggered_by='00-prescan'`。

跑完后输出汇报模板：
```

- [ ] **Step 4: 验证（搬不是删）**

Run:
```bash
F=prism/workflows/00-research-topic.md
grep -c "4.5b 是兜底地板" "$F"   # 期望 1（只在附录）
grep -n "附录 A4.5b（执行时可跳过）" "$F"  # 期望命中指针
```
Expected: 第一条输出 `1`（原主流程那份已移走，附录里有 1 份）；第二条命中指针。

---

## Task 3: Step 1a / 1b 搬迁（question 三段式 — 搬走全部 inline 示例）

**Files:** Modify `prism/workflows/00-research-topic.md`

**保留主流程（Step 1a）：** 标题；`确认 type 后必须显式读出本 type 的合同终局` 那句 + bash 命令块；`industry/arena/company/macro` 四档终局 bullet（spec，留）。
**搬走 → 附录 A1a：** `**终局不是 user 可选的**（type 锁死），后续所有环节（question / thesis K# / 命门 / 收料 / critic）都围绕这个终局倒推。` 这句 justification。

**保留主流程（Step 1b）：** 标题；`**主 agent 必须按三段式收集并写出 question**：` + 三段编号结构（① 标的身份 ② 对终局赌注（含 industry/arena/company 三条 per-type 提问）③ 红线 两条）；`**重要**：...必须将地理范围列入 AskUserQuestion`；variant 确认句；`**如果是 company 类型，必须确认 ticker**`（含格式说明，留 raise 规则）；`**display_name 与 short_name 分离**` 的**规则**句（`display_name 用于...`；`company 类型 **必填 \`short_name\`**...`）；`**长 question 必须同步给 \`search_terms\`**` 的**规则**句（含 raise + topic.py:333）；`**多市场上市...必须确认 \`extra_tickers\`**` 的**规则**句。
**搬走 → 附录 A1b：**
1. `**全维度/百科式 question 的软警告规约**：` 整块（含其下三 bullet + `例：用户说「全维度...` 改写示例）。主流程改留 1 行：`> 若用户给「全维度/百科式」question：不硬收窄，改写成「终局赌注主轴 + 宽覆盖作 scope 备注」并回述确认（详例 → 附录 A1b）。`
2. short_name 的两条 `例：` 示例行（`display_name='荣昌生物...'` / `display_name='阿里巴巴...'`）。
3. search_terms 的 `例：` 行 + `这些关键词写入 \`topic.yaml\`...` 解释行。
4. extra_tickers 的三条 `荣昌生物 A+H / 阿里巴巴 H+ADR / 中芯国际 A+H` 示例 + `漏填 = 后续 06-daily-monitor...` 后果句。

- [ ] **Step 1: append A1a + A1b 到附录**（Edit#1，把上述搬走内容逐字粘到 `<!-- APPENDIX-ENTRIES -->` 上方，分 `### 附录 A1a — type→终局倒推的不可协商性` 与 `### 附录 A1b — question 三段式的 inline 示例与软警告规约` 两小节；保留占位符在最下）

- [ ] **Step 2: trim 主流程**（Edit#2 系列，逐块按上面"搬走"清单从主流程删除/替换为指针；Step 1b 标题下加一条 `> 📎 *示例 / 软警告规约 → 附录 A1b（执行时可跳过）*`；Step 1a 末加 `> 📎 *→ 附录 A1a*`）

- [ ] **Step 3: 验证**

Run:
```bash
F=prism/workflows/00-research-topic.md
for s in "全维度/百科式 question 的软警告规约" "display_name='荣昌生物" "search_terms=['ADC 商业化'" "中芯国际 A+H"; do echo -n "$s => "; grep -c "$s" "$F"; done
```
Expected: 每条输出 `1`（都只剩附录里那份）。`grep -c "三段式收集并写出 question" "$F"` 仍 = 1（结构留主流程）。

---

## Task 4: Step 3 搬迁（意图分叉 — 留分支骨架，搬深层 rationale）

**Files:** Modify `prism/workflows/00-research-topic.md`

**保留主流程：** 标题；`list_variants` bash 块；`返回 \`[]\` → 全新 slug，直接进 Step 4。` ;`返回非空...**这是一个意图分叉点，必须停下问用户**` 引导句；**四支决策骨架各留 1 句"做什么"**：
- `**续做**旧变体`：留 `不 create，读对应 \`topic.yaml\` 判 stage → 跳转对应 workflow 推进。`
- `**换模型/换架构重研**（新变体）`：留 `进 Step 4 用新 variant 名创建（变体名以 \`model_registry\` 规范名为准）。建后按"新变体复用旧料"流程（详 → 附录 A3）。`
- `**另一个 topic 撞名**`：留整句（已 1 行）。
- `**本变体已存在但只是父级 init 种的空壳 stub**`：留 `→ **不是另起变体，而是续做本变体**：在现有 stub 上正常跑 Step 4.3→6.5（详 → 附录 A3）。`

**搬走 → 附录 A3：**
1. 换模型支里的全部子项细节：`**重注册 materials**——机械抽取层...` / `**findings 必须本变体重抽（走 03）**...` / `**\`set_parent_materials\` 引父级 findings** 仍合法...` / `复用同一批 materials 可隔离变量...` 四段。
2. stub 支括号里的判据细节：`（industry 环⑥派生 arena 时 \`set_thesis(...)\` 种下继承 thesis_v0，stage 仍 \`00-init\`...）` 与 `判据：\`read_topic\` 显示 thesis 有 history 但 \`outputs_state\` 几乎空、\`manifest\` 0 料。`
3. `> 兜底（[skill-routing]）：即便跳过本步直奔 Step 4...勿依赖兜底跳步。` 整个 `>` 块。

- [ ] **Step 1: append `### 附录 A3 — Step 3 意图分叉的分支细节与兜底`**（Edit#1，逐字粘三组）
- [ ] **Step 2: trim 主流程**（Edit#2 系列；四支各留骨架 + 指针）
- [ ] **Step 3: 验证**

Run:
```bash
F=prism/workflows/00-research-topic.md
for s in "重注册 materials" "findings 必须本变体重抽" "兜底（[skill-routing]）" "本变体已存在但只是父级 init 种的空壳 stub"; do echo -n "$s => "; grep -c "$s" "$F"; done
```
Expected: 前三条 = `1`（搬到附录）；第四条 = `1`（骨架句保留在主流程，附录用的是判据细节而非这句标题）。`grep -c "意图分叉点，必须停下问用户" "$F"` = 1。

---

## Task 5: Step 4.0 / 4.3 搬迁（早期 ingest + baseline）

**Files:** Modify `prism/workflows/00-research-topic.md`

**保留主流程（4.0）：** 标题；code 块；`> **红线（保 bet-first）**：本步**只登记元数据**...不读正文、不进 thesis_v0` 约束句；`> **复核**：扫一眼返回清单...改 \`source_type='annual-report'\`` 操作句。
**搬走 → 附录 A4.0：** `**为什么**：用户常在开研前把已有料...让"建前查重"从 00 即生效。资料只在 topic 层（无全局 inbox）。` 整段；`> **增量幂等**：本步是第一遍...（已登记的跳过）。` 句。

**保留主流程（4.3）：** 标题；`**执行**：参 \`prism/workflows/_baseline_knowledge.md\` 模版...五段结构（第六节 4.5c 回写时再加）：` + **五段清单**（结构事实，留）；code 块；`**例外可跳过**：concept 类...默认必跑。` ；`**纪律**：` 下五条 do-rule（留）。
**搬走 → 附录 A4.3：** `**为什么必须做**：训练知识是研究的第一层数据源...Step 4.5a 主 agent 逐条 WebSearch 入库。` 整段。

- [ ] **Step 1: append `### 附录 A4.0 ...` + `### 附录 A4.3 ...`**（Edit#1）
- [ ] **Step 2: trim**（4.0 在 code 块后加指针；4.3 标题下加指针）
- [ ] **Step 3: 验证**

Run:
```bash
F=prism/workflows/00-research-topic.md
for s in "训练知识是研究的第一层数据源" "用户常在开研前把已有料"; do echo -n "$s => "; grep -c "$s" "$F"; done
grep -c "五段结构（第六节 4.5c 回写时再加）" "$F"   # 期望 1：结构事实留主流程
```
Expected: 前两条 = `1`（附录）；第三条 = `1`（主流程保留五段结构）。

---

## Task 6: Step 4.5 / 4.5a / 4.5c 搬迁（4.5b 已在 Task 2 处理）

**Files:** Modify `prism/workflows/00-research-topic.md`

**保留主流程（4.5 父节）：** 标题；`> **Web 搜索路径**：本步走 **adapter**...` 整个 `>` 块（含 adapter bash 命令 + sidecar 说明 + 退出码 40 fallback——这是 how-to，留）；`**执行三段：先跑 baseline 优先 query → ...三段都做完才进 Step 5。**` 概览句。
**搬走 → 附录 A4.5：** `**为什么必须做**：LLM 训练截止与当前时间往往有几个月到一年的差距...后续整轮研究偏航。` 整段。

**保留主流程（4.5a）：** 标题；sed 命令块；`主 agent 对每条优先 query 按 \`_web_prescan_shared.md\` Step B.1 并发限流规约跑：` + 四条并发规约（操作，留）；python 块；`**纪律**：第五节 5-10 条优先 query 全部尝试完才进 4.5b。...脚本会通过 Step 5.0 的 \`check_prescan_health\` 自动检测...` 纪律句（留——含硬约束）。
**搬走 → 附录 A4.5a：** `\`build_search_queries\` 只枚举 scope + 事件 + L4 的**覆盖槽**（给 hint，不代写 query），**且不读 baseline_knowledge.md**——主 agent 在 Step 4.3 baseline 第五节写的...否则等于白写。` 这段（解释为何要手动落地）。

**保留主流程（4.5c）：** 标题；`跑完 4.5a + 4.5b 后，主 agent 扫一遍...**追加到 baseline_knowledge.md 末尾**（Edit 工具）：` + markdown 模板块（输出格式，留）；`**纪律**：` 下三条（留——含"被推翻不准 cite 原 fact"硬约束）。
**搬走 → 附录 A4.5c：** （4.5c 主要是输出格式 + 硬约束，**无纯 rationale 可搬** → 本步不搬，附录无 A4.5c 小节。）

之后的 `**例外可以跳过 prescan**：concept 类...默认必跑。` 留主流程（操作）。

- [ ] **Step 1: append `### 附录 A4.5 ...` + `### 附录 A4.5a ...`**（Edit#1）
- [ ] **Step 2: trim**（4.5 与 4.5a 标题下各加指针）
- [ ] **Step 3: 验证**

Run:
```bash
F=prism/workflows/00-research-topic.md
for s in "LLM 训练截止与当前时间往往有几个月" "且不读 baseline_knowledge.md"; do echo -n "$s => "; grep -c "$s" "$F"; done
grep -c "Web 搜索路径" "$F"        # 期望 1：adapter how-to 留主流程
grep -c "三态语义" "$F"            # 后面 Task 处理，这里仅基线参考
```
Expected: 前两条 = `1`；`Web 搜索路径` = 1。

---

## Task 7: Step 5.0 搬迁（thesis — 最大头；留四段结构/三态/自检，搬 rationale）

**Files:** Modify `prism/workflows/00-research-topic.md`

**保留主流程：**
- `## Step 5` 父节 intro（`**注意**：相较旧版...` 留，1 段操作说明）；`产出以下**四部分**：...` 句。
- `### 5.0 LLM 初判 thesis`：`**硬约束**：` 三条（留）；`**要求**：写一份 ...必须包含以下四段（每段都要写，不能跳过）：` + **四段清单**（结构事实，下游引用，留；含其下的反例/正例 1 组——留 1 组即可，本就只有 1 组）；prescan 健康度 bash 块（留）；`**三态语义**：` 三条（结构事实，留）；`failed 时 thesis_v0.md frontmatter 必须加红字横幅` + 其 markdown 块（留）；`**Coverage 闭环（必须做）**：` 全块（含终局命门自检三 bullet，留——do-checklist + 终局对齐）；`Web 端会在详情页...看到红色就必须处理` 句（留）；`**v1 起的写作约定（方案 C 全快照）**：...` 句（结构事实，_shared 引用，留）。
- `### 5.0a backfill`：标题留；留 1 行 `> **默认 scope 约定下本步是 no-op，直接跳过**（仅当 prescan 材料用 \`fact-NN\` 标 addresses 时才跑；详 → 附录 A5.0a）。`

**搬走 → 附录 A5.0：**
1. `**目的**：让 LLM 在 Step 4.5 prescan 数据校准之后...强制每条资料都要回答"这支持还是推翻我的初判？"` 段。
2. `**不再单列"研究中重点验证项 V#" 段** —— V# 本质是...不引入 V# 第三维。` 整段。
3. `**后续何时更新 thesis**：` + 其下四条 + `每次 set_thesis 都 append 到 history...保留判断演化轨迹` （参考信息，非执行，搬）。

**搬走 → 附录 A5.0a：** 5.0a 标题下当前**整块**适用前提 `> ⚠️ **适用前提（F2 订正）**...`、`> 且 \`scope\` 本就不计入 K# 覆盖...`、`> **何时真要跑**...`、python `backfill_addresses_by_mapping` 代码块、`**纪律（仅在用 fact-NN 标注的前提下）**：` 五条。

> ⚠️ **5.0a 例外**：5.0a 的 python 代码块**是要搬进附录的**（与 Global Constraint「命令块留主流程」冲突？——否）。原因：5.0a 在默认约定下是 no-op，整节非执行路径；其代码块只在罕见的 fact-NN 标注模式才用，属"corner-case 参考"，随该节一起入附录。T-VERIFY 的代码块不变量 (b) 仍成立（代码块仍在**文件内**，只是从主流程移到附录；(b) 比对的是"文件全体代码块集合"，不区分主/附录）。

- [ ] **Step 1: append `### 附录 A5.0 ...` + `### 附录 A5.0a ...`**（Edit#1，逐字粘）
- [ ] **Step 2: trim 主流程**（5.0 标题下/相应位置加指针；5.0a 整节缩成标题 + no-op 指针行）
- [ ] **Step 3: 验证**

Run:
```bash
F=prism/workflows/00-research-topic.md
for s in "强制每条资料都要回答" "V# 本质是 K#/Q# 的派生细化" "后续何时更新 thesis" "适用前提（F2 订正）"; do echo -n "$s => "; grep -c "$s" "$F"; done
for s in "必须包含以下四段" "三态语义" "Coverage 闭环（必须做）" "v1 起的写作约定" "终局命门自检"; do echo -n "KEEP $s => "; grep -c "$s" "$F"; done
```
Expected: 第一组每条 = `1`（搬走）；第二组每条 ≥ `1`（结构事实/自检留主流程）。

---

## Task 8: Step 5.2 / 5.3 搬迁（5.1 不动）

**Files:** Modify `prism/workflows/00-research-topic.md`

**保留主流程（5.1）：** 整节不动（已 3 行）。
**保留主流程（5.2）：** 标题；`在对话里输出：① 哪些维度升成了 K#（指回 5.0）；② 一行 primer scope 备注...` 指令句。
**搬走 → 附录 A5.2：** 整个 `> **S1 · Q# 降级**：旧版在此另生成一套 \`Q1-Q8\`...` 引用块（含其下 bullet + `简言之：...` + `（旧 topic 已有的 Q# addresses 仍有效...）`）。

**保留主流程（5.3）：** 标题；`按 **优先级（P0/P1/P2）+ 信息差等级...**每条 todo 都必须标注 addresses` 句；`> **A 合同视角（收料地板）**：...` 块（操作地板，留）；`**信息差等级定义**：` 三条（spec，留）；`**优先级原则**：` 三条（spec，留）；`每条 todo 必填字段：\`task\` / \`priority\` / \`info_tier\` / \`addresses\`，选填 \`source_hint\`。` （spec，留）。
**搬走 → 附录 A5.3：**
1. `> **闭环语义（钉死）**：一条 todo = ...与「todo 收齐没」无关。` 整个 `>` 块。
2. `> **产即收衔接**：本阶段（00）产的 pending todo...不重抓 00 已 \`fetched\`/\`empty\` 的。` 整个 `>` 块。
3. `> **建 todo 前查重（纪律，复用 \`read_manifest\`）**` 块：**保留**首句操作 `每写一条 todo 前，主 agent 先 \`read_manifest('{slug}','{variant}')\` 扫已有料，按文档身份判：已有→建 done 填 covered_by 或不建；没有→建 pending。`，**搬走**其余展开与 `按文档身份判（不是 K# 撞 K#）...` 重复解释。

- [ ] **Step 1: append `### 附录 A5.2 ...` + `### 附录 A5.3 ...`**（Edit#1）
- [ ] **Step 2: trim**（5.2 指令句前加指针；5.3 相应位置加指针）
- [ ] **Step 3: 验证**

Run:
```bash
F=prism/workflows/00-research-topic.md
for s in "S1 · Q# 降级" "闭环语义（钉死）" "产即收衔接" ; do echo -n "$s => "; grep -c "$s" "$F"; done
for s in "信息差等级定义" "优先级原则" "每条 todo 必填字段" "A 合同视角"; do echo -n "KEEP $s => "; grep -c "$s" "$F"; done
```
Expected: 第一组 = `1`；第二组 ≥ `1`。

---

## Task 9: Step 5.4 搬迁（decomposition — 留四块结构/理解性约束/终局豁免，搬两段为什么）

**Files:** Modify `prism/workflows/00-research-topic.md`

**保留主流程：** 标题；`**产出 \`...decomposition_v0.md\`**，含四块...：` + **四块结构全体**（命门 1-3 / 每环 B 靶点（含终局环强制非空三档）/ primer 入门目标 v0（含 **性质约束·primer 回归** + **终局豁免** 两条——下游 `Step 5.4 性质约束` 引用，必留逐字）/ 机械自检六条（含"primer 是否理解性"条 + "终局环 B 靶点非空"条））；set_decomposition code 块；`> 旧 topic 无 decomposition → 缺省空壳...新 topic 此步必跑...` 句。
**搬走 → 附录 A5.4：**
1. `> **为什么前移到这里**：拆解（把"赌注"拆成...深度版（v1）留到 04 写作期做有界 delta 重拆（见 \`04-synthesize/_shared.md\`）。` 整个 `>` 块。
2. `> **冷启动断点 = 训练知识 + baseline + prescan**：此刻还没厚资料...真正的可靠性闸门是 04 厚料 delta 重拆。` 整个 `>` 块。

> ⚠️ **5.4 最易出错**：`**性质约束（primer 回归 · 必守）**` 与 `**终局豁免**` 两段、以及机械自检里对应两条，**必须留主流程逐字**（`terminal-alignment-primer-regression-fix.md` 与 `01-build-roadmap.md` 直接引用）。只搬开头两个 `> **为什么...**` 块。

- [ ] **Step 1: append `### 附录 A5.4 — decomposition 前移的理由与冷启动可靠性原理`**（Edit#1）
- [ ] **Step 2: trim**（标题下加指针，删两个为什么块）
- [ ] **Step 3: 验证**

Run:
```bash
F=prism/workflows/00-research-topic.md
for s in "为什么前移到这里" "冷启动断点 = 训练知识"; do echo -n "$s => "; grep -c "$s" "$F"; done
for s in "性质约束（primer 回归 · 必守）" "终局豁免" "每条 primer 入门目标是否理解性" "终局环 B 靶点强制非空"; do echo -n "KEEP $s => "; grep -c "$s" "$F"; done
```
Expected: 第一组 = `1`（搬走）；第二组每条 ≥ `1`（逐字保留）。

---

## Task 10: Step 6.5 / 6.5e 搬迁（eager-fetch + 硬闸门）

**Files:** Modify `prism/workflows/00-research-topic.md`

**保留主流程（6.5 父节）：** 标题；6.5a 标题 + venv 警示 `>` 行（操作，留）+ code 块；6.5b 标题 + 三步阶梯（含 adapter bash）+ `抓到 → 落 ...add_material 入库...` 句；6.5c 标题 + 五条盖戳纪律（三态 do-rule，留）；6.5d 标题 + code 块 + 表格格式 + `> **纪律**：跑完 6.5 后..."你需要做的事"里**只应剩真·\`empty\`**...回 6.5a/b 补抓。` 句。
**搬走 → 附录 A6.5：** 父节标题下整个 `> **为什么在这里**：Step 6 刚把 5.3 的 user_todos...report 类 todo 的 ticker 由主 agent 按公司名现场映射。` 三段 `>` 块。

**保留主流程（6.5e）：** 标题；code 块；`如果非 0 退出（有 \`unattempted\`），**回 Step 6.5b ...**...**\`unattempted\` 清零是进 Step 7 的前置条件。**` 句。
**搬走 → 附录 A6.5e：** 标题下两个 `> **为什么必须做**：...` 与 `> **与 01 Step 5.8 同源**：...` 块。

- [ ] **Step 1: append `### 附录 A6.5 ...` + `### 附录 A6.5e ...`**（Edit#1）
- [ ] **Step 2: trim**（6.5 与 6.5e 标题下各加指针）
- [ ] **Step 3: 验证**

Run:
```bash
F=prism/workflows/00-research-topic.md
for s in "为什么在这里" "与 01 Step 5.8 同源"; do echo -n "$s => "; grep -c "$s" "$F"; done
for s in "本段必须用 ./.venv/bin/python" "盖戳纪律" "unattempted 清零是进 Step 7 的前置条件"; do echo -n "KEEP $s => "; grep -c "$s" "$F"; done
```
Expected: 第一组 = `1`；第二组每条 ≥ `1`。

---

## Task 11: 收尾占位符 + 附录小节排序

**Files:** Modify `prism/workflows/00-research-topic.md`

- [ ] **Step 1: 删掉占位符注释**

old_string:
```

<!-- APPENDIX-ENTRIES -->
```
new_string:
```
```
（即删掉占位行及其上方空行；Read 末尾确认 verbatim）

- [ ] **Step 2: 确认附录小节顺序合理**（人读一遍，A1a→A6.5e 大致按 Step 号；顺序不影响功能，无需强制重排，仅确保无重复标题）

Run:
```bash
grep -nE "^### 附录 A" prism/workflows/00-research-topic.md
```
Expected: 列出所有 `### 附录 A...` 小节，无重复 key，无残留 `<!-- APPENDIX-ENTRIES -->`。

---

## Task 12 (T-VERIFY): 六不变量硬验证（任一失败即停、回退对应 Task）

**Files:** 只读校验；末尾删基线目录。

- [ ] **Step 1: (a) 锚点不变量 — 19 个 Step/速览 标题逐字仍在**

Run:
```bash
cd /Users/mark/investing
F=prism/workflows/00-research-topic.md
B=docs/superpowers/plans/_wf00slim_baseline
grep -nE "^#{2,4} (Step|00 速览)" "$F" | sed 's/^[0-9]*://' > /tmp/anchors_now.txt
sed 's/^[0-9]*://' "$B/anchors.txt" > /tmp/anchors_orig.txt
diff /tmp/anchors_orig.txt /tmp/anchors_now.txt && echo "✓ (a) 锚点逐字一致" || echo "✗ (a) 锚点漂移 — 停，查哪个 Task 动了标题"
```
Expected: `✓ (a) 锚点逐字一致`（diff 无输出）。

- [ ] **Step 2: (b) 代码块不变量 — 全文件代码块集合无增删**

Run:
```bash
F=prism/workflows/00-research-topic.md
B=docs/superpowers/plans/_wf00slim_baseline
awk 'BEGIN{inb=0} /^```/{inb=!inb; next} inb{print}' "$F" | sort > /tmp/codeblocks_now.txt
diff "$B/codeblocks.txt" /tmp/codeblocks_now.txt && echo "✓ (b) 代码块逐字一致" || echo "✗ (b) 代码块被改/丢 — 停，命令块只能搬位置不能改内容"
```
Expected: `✓ (b) 代码块逐字一致`（diff 无输出）。**注**：代码块从主流程搬进附录（仅 5.0a）不破坏此不变量，因为比对的是"文件全体代码块行集"。

- [ ] **Step 3: (c) 结构事实不变量 — 下游依赖的 spec 仍在主流程（附录前）**

Run:
```bash
F=prism/workflows/00-research-topic.md
# 截取"附录 A 之前"的主流程部分
MAIN=$(awk '/^## 附录 A —/{exit} {print}' "$F")
miss=0
for s in \
  "必须包含以下四段" \
  "五段结构（第六节 4.5c 回写时再加）" \
  "性质约束（primer 回归 · 必守）" \
  "终局豁免" \
  "三态语义" \
  "每条 todo 必填字段" \
  "信息差等级定义" \
  "v1 起的写作约定" \
  "Coverage 闭环（必须做）" ; do
  echo "$MAIN" | grep -qF "$s" && echo "OK keep: $s" || { echo "MISSING in MAIN: $s"; miss=1; }
done
[ $miss -eq 0 ] && echo "✓ (c) 结构事实全在主流程" || echo "✗ (c) 有结构事实被误搬进附录 — 停，搬回主流程"
```
Expected: 9 行 `OK keep`，末行 `✓ (c)`。

- [ ] **Step 4: (d) 零丢失不变量 — 每个被搬段落的特征句在附录可见**

Run:
```bash
F=prism/workflows/00-research-topic.md
APP=$(awk 'f{print} /^## 附录 A —/{f=1}' "$F")
miss=0
for s in \
  "4.5b 是兜底地板" \
  "全维度/百科式 question 的软警告规约" \
  "display_name='荣昌生物" \
  "中芯国际 A+H" \
  "重注册 materials" \
  "兜底（[skill-routing]）" \
  "训练知识是研究的第一层数据源" \
  "用户常在开研前把已有料" \
  "LLM 训练截止与当前时间往往有几个月" \
  "且不读 baseline_knowledge.md" \
  "强制每条资料都要回答" \
  "V# 本质是 K#/Q# 的派生细化" \
  "后续何时更新 thesis" \
  "适用前提（F2 订正）" \
  "S1 · Q# 降级" \
  "闭环语义（钉死）" \
  "产即收衔接" \
  "为什么前移到这里" \
  "冷启动断点 = 训练知识" \
  "为什么在这里" \
  "与 01 Step 5.8 同源" ; do
  echo "$APP" | grep -qF "$s" && echo "OK moved: $s" || { echo "MISSING in APPENDIX: $s"; miss=1; }
done
[ $miss -eq 0 ] && echo "✓ (d) 搬走内容全在附录" || echo "✗ (d) 有内容被删而非搬 — 停，从基线 git show 找回"
```
Expected: 21 行 `OK moved`，末行 `✓ (d)`。

- [ ] **Step 5: (e) 下游引用不变量 — 跨文件按 Step 号的引用仍解析**

Run:
```bash
cd /Users/mark/investing
# 下游引用的 00 Step 号都仍是主流程存在的锚点（标题里能 grep 到）
F=prism/workflows/00-research-topic.md
for step in "Step 3" "Step 4.0" "Step 4.3" "Step 4.5a" "Step 4.5c" "Step 5.0" "Step 5.4" "Step 6.5"; do
  grep -qE "^#{2,4} .*$step" "$F" && echo "OK anchor: $step" || echo "MISSING anchor: $step"
done
echo "--- 下游文件未被本次改动（应只动 00 一个文件）---"
git diff --name-only
```
Expected: 8 行 `OK anchor`；`git diff --name-only` **只列** `prism/workflows/00-research-topic.md`（外加可能的本计划临时基线目录，未 commit 不算）。若列出任何其它 workflow/.py 文件 → 停。

- [ ] **Step 6: (f) 尺寸不变量 — 主流程（附录前）≤ 原行数 1/3 附近**

Run:
```bash
F=prism/workflows/00-research-topic.md
B=docs/superpowers/plans/_wf00slim_baseline
ORIG=$(awk '{print $1; exit}' "$B/metrics.txt")   # metrics.txt 形如 "740 prism/workflows/00-research-topic.md"
MAINLINES=$(awk '/^## 附录 A —/{exit} {c++} END{print c}' "$F")
TOTAL=$(wc -l < "$F")
echo "原文件行数 ORIG=$ORIG ; 现主流程(附录前)行数=$MAINLINES ; 现总行数(含附录)=$TOTAL"
awk -v m="$MAINLINES" -v o="$ORIG" 'BEGIN{ r=m/o; printf "主流程/原文件 = %.2f\n", r; if (r<=0.45) print "✓ (f) 主流程已显著瘦身(目标~1/3, 阈值≤0.45)"; else print "✗ (f) 主流程仍偏厚 — 复查是否漏搬 rationale" }'
```
Expected: `主流程/原文件 ≤ 0.45`（理想 ~0.33；阈值放宽到 0.45 容纳保留的命令块/结构事实）。若 > 0.45，回查 Task 7/3/8 是否有大段 rationale 漏搬。

- [ ] **Step 7: 清理基线目录**

Run:
```bash
rm -rf docs/superpowers/plans/_wf00slim_baseline && echo "基线已清"
```
Expected: `基线已清`。

> **若任一不变量 ✗**：不要 commit。按提示回对应 Task 修；(d) 失败时用 `git show HEAD:prism/workflows/00-research-topic.md` 取回被误删的原文逐字补进附录。

---

## Task 13: 提交（只 stage 这一个文件）

- [ ] **Step 1: 确认 diff 只含 00 文件**

Run:
```bash
cd /Users/mark/investing && git status --short prism/workflows/00-research-topic.md && echo "--- 确认不会误带其它文件 ---"
```
Expected: 仅 `M prism/workflows/00-research-topic.md`。

- [ ] **Step 2: 提交**

Run:
```bash
cd /Users/mark/investing
git add prism/workflows/00-research-topic.md
git commit -m "docs(prism/wf00): 主流程瘦身 ~1/3 — rationale/反例/示例搬入附录 A，执行语义不变

- 搬迁不删除：每段散文逐字移入文件末「附录 A」，按 Step 号编键
- Step 锚点/命令块/结构事实(四段·五段·三态·primer性质约束·终局豁免)全留主流程
- 6 不变量 harness 校验通过(锚点/代码块/结构事实/零丢失/下游引用/尺寸)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git log --oneline -1
```
Expected: 1 个 commit，仅 1 文件改动。

---

## Out of Scope（刻意不做）

- **合并/删除/下放任何 Step 或思考产物**——经核实 baseline/K#/decomposition 都喂 03/04/05/07，删改会断 04 delta 重拆、03 cite、05 校准清单。本计划是**搬迁**，零语义改动。
- **改 .py（给 `id` 加 `mat_id` 别名 / 让 `fetch()` 自动盖 fetch_status 等）**——触碰符号需走 CLAUDE.md 的 impact 分析，属另一计划。
- **改其它 workflow 文件**——除非 (e) 不变量暴露引用断裂；那种情况停下报告，不擅自改下游。
- **重排附录小节成精美目录**——顺序不影响功能，T11 只保证无重复 key。

## Self-Review

- **Spec 覆盖**：瘦身机制（搬迁/附录）→ Task 1–11；等价性 6 不变量 → Task 12 (a)–(f)；只改一文件 + 提交范围 → Task 0/12-Step5/13；keep/move 规则 → Global Constraints + 每 Task 的「保留/搬走」清单。无遗漏。
- **无占位符**：每 Task 给了「保留清单 + 搬走清单（verbatim 定位短语）+ 指针格式」；Task 2 给了端到端 verbatim worked example；验证全是可跑 bash 带预期。被搬块按"verbatim 起始短语 + 边界规则"定位（块是逐字搬迁，执行者 Read 后取真实 verbatim 文本，不需我预抄全文）。
- **一致性**：附录 key（A1a/A1b/A3/A4.0/A4.3/A4.5/A4.5a/A4.5b/A5.0/A5.0a/A5.2/A5.3/A5.4/A6.5/A6.5e）与各 Task append 目标一致；T12 (d) 的 21 条特征句与各 Task「搬走」清单一一对应；指针格式全程统一。
- **风险兜底**：最危险的是"误删而非搬"——(d) 不变量逐句校验搬走内容在附录可见；"误把结构事实搬进附录"——(c) 不变量逐句校验 spec 留主流程；二者构成双向围栏。

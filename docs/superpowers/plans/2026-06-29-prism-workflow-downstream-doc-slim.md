# Prism 下游流程文档瘦身（01–07 + 04-synthesize · relocation, not deletion）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 workflow 00 之后的所有流程文档（`01`–`07` 与 `04-synthesize/*`）按 `00-research-topic.md` 已落地的同一套办法瘦身——把"为什么 / 反例 / 历史教训 / memory 链接 / inline worked example"**逐字搬到各文件末尾的 `## 附录 A`**（搬迁，不删除），主流程只留"做什么 + 命令块 + 规约 + 一行指针"。**不改任何执行语义、不改 Step / 章节编号、不动 .py、不动跨文件引用。**

**Architecture:** 这是**逐文件、纯文本搬迁**。`00-research-topic.md` 已经是落地的 worked example（见其 `## 附录 A` 16 个 `### 附录 A{key}` 小节 + `> 📎 *... → 附录 A{key}（执行时可跳过）*` 指针）——执行者照它的形态做每个文件即可。每个文件独立完成一轮"基线快照 → per-block 先 append 进附录后 trim 主流程 → 7 不变量硬验证 → 提交"。被移走的每一段散文都逐字重现在该文件自己的附录里，所以等价性机械可审。**有些文件经核实是 spec/契约/schema 密集型，可搬的 rationale 不足——这些按 no-op 跳过并登记理由（与 00 计划里 4.5c 的处理一致），不强行制造附录。**

**Tech Stack:** Markdown；定位/搬迁用 Read + Edit 工具做 verbatim 字符串操作；验证用 `grep`/`rg`/`diff`/`awk`/`wc`（macOS zsh —— 注意 zsh 不对未加引号变量做词分割，循环用显式 `for f in a b c`）。

---

## Global Constraints

- **只改 workflow `.md` 文件**：本计划除 Task 0（提交已存在的内容改动）外，禁止编辑任何 `.py`、禁止改 `prism/topics/...` 研究产出、禁止改 `00-research-topic.md`（它已瘦身完毕）。每个 slimming Task 只动它自己那一个文件（funnel 三件套 Task 6 动三个同构文件）。
- **搬迁不删除**：被移出主流程的每一段，必须**逐字**（含标点 / markdown 标记 / `[[memory-slug]]`）出现在该文件 `## 附录 A`。不允许改写、概括、合并被搬的散文。
- **章节锚点逐字不动**：所有 `## Step N` / `### Step N` / `### N.x` / `## n. 标题` / `#### x.y` 标题逐字保留在主流程（附录之前）。下游文件按这些标题号互相引用。
- **命令块逐字保留在主流程**：所有 ` ```python ` / ` ```bash ` / ` ```yaml ` 代码块（含块内注释，那是字段 / 行为 spec）原样留主流程，**一行都不进附录**。
- **`[TPL]` 模板块绝不动**：部分"看着像标题"的行其实是**喂给 subagent 的 prompt 模板**或**写进产出文件的输出模板**，必须原样留主流程。已知 `[TPL]` 块：
  - `05-critic-review.md`：反方 subagent prompt（`## 你的处境` / `## 你拿到的材料` / `## 攻击方向` / `## 你要交付` / `### 一、对承重假设的质疑` / `### 二、预先验尸` / `### 三、致命一击候选`）+ 评审产出模板（`## 独立反方报告` / `## 评分与裁决` / `## {timestamp_short} 批评者评审完成`）。
  - `03-extract-findings.md`：发现笔记输出模板（`## 核心数据点与事实` / `## 叙事主线` / `## 反常识/分歧点` / `## 未回答问题` / `## 质量备注`）。
  - `04-synthesize/00-primer.md`：critic prompt 模板（`## 你的角色` / `## 关键校验规则` / `## 你要校验的目标` / `## 你要做的`）。
  这些多数本就在 ` ``` ` 围栏内（受代码块不变量保护），但执行时**人也要警觉别把它们当可搬散文**。
- **跨文件引用是硬锚点**：`04-synthesize/*` 互相按 `§` 章节名引用。以下 `_shared.md` 的 `[XREF]` 标题被四个 case 文件逐字引用，**绝不可重命名、绝不可搬进附录**：`## 前置检查`、`## gap 体检（进 04 第一件事）`、`## 增量重写判定（默认开启）`、`## B 轴有界 delta 重拆 + 收敛（…）`（最 load-bearing）、`## 调度模式：主 agent 直做 + 并行 Write（**默认**）`、`## 全部产出完成后（收尾）` + `### 收尾：capped 命门 → suggested_drilldowns 回流（…）`、`### 写 thesis_v1（基于资料的修正版）：` + `#### Scheme C 写作约定（v1 起所有 thesis 强制）`、`### 终态报告（收尾必出 · 三件套兜底）`、`## 即兴 web-search（新增）`。
- **结构事实留主流程**：下游按"6 环决策链 / 元目标（逐字不改）/ primer↔case 分工 / 跨层复用护栏 / schema 原样不动 / 机制纠错八条 / 三态语义 / 字段约束"直接引用——这些**契约 / 清单 / 约束**留对应步内可见，**不进附录**。
- **逐字匹配 + 不依赖行号**：每个 Edit 的 `old_string` 必须先 Read 当前文件 verbatim 复制；前序 Edit 会让行号漂移，**用唯一字符串定位**。本计划给的"locator 起始短语"是 grep 锚，执行者 Read 后取真实 verbatim 全文。
- **不修预存在瑕疵**（仅保留、不动）：`02-gather-materials.md` 有两个 `## Step 5.7` 同名标题；`07-drilldown.md` 末尾 `## Step 5` 疑似无正文（截断）；`_arena_funnel.md` 行 265 强制重修订门句子疑似截断。**这些是预存在状态，本计划只逐字保留，不"顺手修"**——修它们属另一计划。
- **提交粒度**：Task 0 一个内容提交；其后**每个 slimming Task 各自一个提交**（只 stage 它改的那一个文件 / funnel 三文件）。绝不 `git add -A`。
- **GitNexus 纪律**：Task 0 提交 `.py` 前按 CLAUDE.md 跑 `detect_changes()`；本计划其余 Task 只改 `.md` 文档，不触碰符号，无需 impact 分析。

### keep / move 判据（统一规则，逐段套用）
对主流程里每一段，问一句：**"下游文件或执行 agent 正确做这步，必须看到这段吗？"**
- 是 spec / 命令 / 硬约束 / 输出格式 / 决策分支骨架 / do-checklist / 被别的文件按 §名引用的标题 → **留主流程**。
- 是 justification（`**为什么**` / `**为什么必须做**` 段）/ 历史教训 / 纯论证型 `>` 引用 / `[[memory-slug]]` 解释 / 第 2 个起的反例正例 / inline worked example / 纯解释型「定位与边界」「附：…关系」表 → **搬附录**，主流程留 1 行指针（标题保留，只搬正文）。

### 指针格式（主流程里替换被搬块正文的位置）
统一写成单行斜体引用（`{key}` 用该块附录小节键）：
```
> 📎 *为什么 / 反例 / 历史教训 → 附录 A{key}（执行时可跳过）*
```
（markdown 锚点不强求可点；文字指针足够导航。一个步搬多块可合用一条指针。）

### 附录骨架模板（每个要 slim 的文件，在文件最末追加一次）
```
---

## 附录 A — rationale / 反例 / 历史教训（执行时可跳过，调试 / 维护时查）

> 本附录收纳从各步主流程搬出的"为什么 / 反例 / 历史教训 / memory 链接 / inline worked example"。**主流程逐字未删、只是移出执行动线**；要看某步的来龙去脉，按对应小节查。

<!-- APPENDIX-ENTRIES -->
```

### 每个 slimming Task 的通用动作（套用 Task 2–9，不再重复写）
1. 跑 Task 1 的基线快照（针对本文件 `$F`）。
2. 在文件最末 append 附录骨架（上面的模板，`old_string` = 当前最后一行 verbatim + 模板）。
3. 对每个 move-block：**先 append**——把 `<!-- APPENDIX-ENTRIES -->` 替换成 `### 附录 A{key} — <一句话标题>\n\n<搬来的块，逐字>\n\n<!-- APPENDIX-ENTRIES -->`（占位符始终留最下，供下一块续接）。
4. **后 trim**——把主流程里那块正文 `old_string` 替换成指针行（标题与相邻保留内容不动）。
5. Task 11 收尾删掉每个文件的 `<!-- APPENDIX-ENTRIES -->` 占位符（或本 Task 末尾即删）。
6. 跑 Task 1 的 7 不变量校验（针对 `$F`）；全过才提交。

---

## File Structure

逐文件状态（来自全量扫描 + per-file 分析）：

| 文件 | 行数 | 判定 | 搬走块（附录键） | 预估搬走行数 |
|---|---|---|---|---|
| `01-build-roadmap.md` | 602 | **SLIM**（Task 2） | A1.5 · A2 · A3 · A4 · A5.6 · A5.8 | ~70–90 |
| `03-extract-findings.md` | 647 | **SLIM**（Task 3） | A0b · A2-sub · A2.1A · A2.1B | ~45–60 |
| `05-critic-review.md` | 502 | **SLIM（轻）**（Task 4） | A2 · A2.2 · A5.5 | ~12–18 |
| `04-synthesize/_shared.md` | 451 | **SLIM**（Task 5） | A-gap · A-whyB · A-drilltype · A-mainagent · A-schemeC · A-triple · A-tier | ~55–65 |
| `04-synthesize/_industry_funnel.md` | 307 | **SLIM**（Task 6） | A0 · A1.4 · A附 | ~40–50 |
| `04-synthesize/_arena_funnel.md` | 300 | **SLIM**（Task 6） | A0 · A1.4 · A附 | ~40–50 |
| `04-synthesize/_company_case.md` | 375 | **SLIM**（Task 6） | A0 · A1.3 · A附 | ~30–40 |
| `02-gather-materials.md` | 355 | **SLIM（轻）**（Task 7） | A-autofetch · A-early · A-mineru | ~15–25 |
| `04-synthesize/00-primer.md` | 234 | **SLIM（轻）**（Task 8） | A2.4 · A3.2 | ~12 |
| `04-synthesize/_macro_regime.md` | 419 | **SLIM（极轻）**（Task 9） | A附（仅尾部对照表） | ~22 |
| `06-daily-monitor.md` | 153 | **NO-OP**（Task 10 登记） | — 铁律/spec/已有内容附录，无可搬 | 0 |
| `07-drilldown.md` | 214 | **NO-OP**（Task 10 登记） | — 仅 1 句可搬，低于门槛 | 0 |
| `04-synthesize/_peer_matrix_spec.md` | 237 | **NO-OP**（Task 10 登记） | — 纯工具 spec / schema / 崩溃 gotcha | 0 |
| `04-synthesize/_arena_select_spec.md` | 181 | **NO-OP**（Task 10 登记） | — 纯工具 spec / schema | 0 |
| `04-synthesize/_decision_kit_spec.md` | 117 | **NO-OP**（Task 10 登记） | — 纯 YAML schema | 0 |
| `04-synthesize/_valuation_models.md` | 104 | **NO-OP**（Task 10 登记） | — 算法库 spec，每条都是可复用规范 | 0 |

- 临时基线目录：`docs/superpowers/plans/_wfslim_baseline/<filebasename>/`（T1 每文件建，T11 末删）——存搬迁前的标题清单 / 代码块行集 / 行数，供不变量比对。

---

## Task 0: 提交已存在的内容改动（让 slimming diff 纯净）

> 工作树当前有一批**内容**改动（venv 硬约定、A股公告分诊、score 1-5 制、decomposition 字段、snippet 兜底等），散落在 `00/01/03/04` 文档 + `gap_detector.py` / `fetch_report_prism.py` 及其测试。先把它们作一个连贯提交落地，slimming 才能从干净基线开始、diff 才是纯搬迁。`git status` 已确认工作树**只含**这些 workflow 文档 + 配套脚本，无研究产出噪声，可整体提交。

**Files:** 提交 `git status` 当前所有已修改文件（不新增、不删除内容）。

- [ ] **Step 1: 确认分支 + 待提交清单**

Run:
```bash
cd /Users/mark/investing && git branch --show-current && git status --short
```
Expected: 分支 `docs/wf00-fixes`；清单恰为 `gap_detector.py`/`test_gap_detector.py`/`00`/`01`/`03`/`04-synthesize/{_arena_funnel,_company_case,_industry_funnel,_shared}`/`_autofetch_protocol`/`_subagent_fetch_material`/`fetch_report_prism.py`/`test_fetch_report_prism.py`。若多出 `prism/topics/...` 等无关项，停下问用户。

- [ ] **Step 2: 按 CLAUDE.md 跑 GitNexus 变更检查（含 .py）**

Run:
```bash
node .gitnexus/run.cjs detect_changes 2>/dev/null || echo "（GitNexus 不可用则跳过，提交照旧）"
```
Expected: 受影响符号仅限 `fetch_report_prism` 新增的 `list_announcements_cn`/`download_announcements_cn` 与 `gap_detector` 改动范围内；无 HIGH/CRITICAL 意外。若报意外 blast radius，停下报告用户。

- [ ] **Step 3: 跑相关测试确认内容改动不破坏脚本**

Run:
```bash
cd /Users/mark/investing && ./.venv/bin/python -m pytest scripts/test_fetch_report_prism.py prism/scripts/test_gap_detector.py -q 2>&1 | tail -20
```
Expected: 全过。若失败，停下报告用户（内容改动本身有 bug，不在本计划范围）。

- [ ] **Step 4: 提交**

Run:
```bash
cd /Users/mark/investing
git add -A
git commit -m "fix(prism): A股公告显式分诊 + venv 硬约定 + score 1-5/decomposition 字段 + snippet 兜底

- fetch_report_prism: list/download_announcements_cn（公告改 LLM 标题分诊，不再一把梭）
- 文档 venv 硬约定（fetcher/extractor 用 ./.venv/bin/python）、03 公告按事件抽 1-3 条
- 04: peer_matrix score 1-5 制、decomposition_v1 summary/stage_set_at 必填

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git log --oneline -1
```
Expected: 1 个 commit；`git status --short` 干净。

---

## Task 1: 可复用的基线快照 + 7 不变量校验 harness（被 Task 2–10 引用）

> 本 Task 不改文件，只**定义两段可复用 bash**（基线 / 校验），后续每个文件把 `$F` 设成自己再跑。先把它们读懂，Task 2 给出完整 worked example。

**Files:** Create（临时，T11 删）：`docs/superpowers/plans/_wfslim_baseline/<basename>/{headings.txt,codeblocks.txt,metrics.txt}`

- [ ] **Step 1: 基线快照函数（每个文件 slim 前先跑）**

Run（把 `F=` 换成目标文件）：
```bash
cd /Users/mark/investing
F=prism/workflows/01-build-roadmap.md      # ← 每文件替换
BN=$(basename "$F" .md)
B="docs/superpowers/plans/_wfslim_baseline/$BN"
mkdir -p "$B"
# (a) 标题不变量基线：所有 markdown 标题逐字（含 [TPL]/模板标题——它们也不该消失）
grep -nE "^#{1,6} " "$F" | sed 's/^[0-9]*://' > "$B/headings.txt"
# (b) 代码块不变量基线：抽出所有 fenced code block 内容（去围栏），排序去重
awk 'BEGIN{inb=0} /^```/{inb=!inb; next} inb{print}' "$F" | sort > "$B/codeblocks.txt"
# 行数
wc -l < "$F" > "$B/metrics.txt"
echo "headings=$(wc -l < $B/headings.txt) codeblock_lines=$(wc -l < $B/codeblocks.txt) total=$(cat $B/metrics.txt)"
```
Expected: 三个文件落地；记下 headings 数与总行数。

- [ ] **Step 2: 7 不变量校验函数（每个文件 slim 后跑；任一 ✗ 即停、回退本文件）**

Run（`F=` 换成目标文件；`KEEP=(...)` / `MOVED=(...)` 用该文件 Task 的清单）：
```bash
cd /Users/mark/investing
F=prism/workflows/01-build-roadmap.md      # ← 每文件替换
BN=$(basename "$F" .md); B="docs/superpowers/plans/_wfslim_baseline/$BN"

# (a) 标题不变量：主流程（附录前）标题集 == 基线标题集（搬正文不动标题）
awk '/^## 附录 A —/{exit} {print}' "$F" | grep -nE "^#{1,6} " | sed 's/^[0-9]*://' > /tmp/h_now.txt
diff <(grep -vE "^#{1,6} (## )?附录 A" "$B/headings.txt") /tmp/h_now.txt \
  && echo "✓ (a) 标题逐字一致" || echo "✗ (a) 标题漂移 — 停"

# (b) 代码块不变量：全文件代码块集合无增删
awk 'BEGIN{inb=0} /^```/{inb=!inb; next} inb{print}' "$F" | sort > /tmp/cb_now.txt
diff "$B/codeblocks.txt" /tmp/cb_now.txt \
  && echo "✓ (b) 代码块逐字一致" || echo "✗ (b) 代码块被改/丢 — 停"

# (c) 结构事实/XREF 不变量：下游引用的 spec 仍在主流程（附录前）
MAIN=$(awk '/^## 附录 A —/{exit} {print}' "$F")
miss=0; for s in "${KEEP[@]}"; do echo "$MAIN" | grep -qF "$s" && echo "OK keep: $s" || { echo "MISSING in MAIN: $s"; miss=1; }; done
[ $miss -eq 0 ] && echo "✓ (c) 结构事实全在主流程" || echo "✗ (c) 有结构事实被误搬 — 停"

# (d) 零丢失不变量：每个被搬段的特征句在附录可见
APP=$(awk 'f{print} /^## 附录 A —/{f=1}' "$F")
miss=0; for s in "${MOVED[@]}"; do echo "$APP" | grep -qF "$s" && echo "OK moved: $s" || { echo "MISSING in APPENDIX: $s"; miss=1; }; done
[ $miss -eq 0 ] && echo "✓ (d) 搬走内容全在附录" || echo "✗ (d) 有内容被删而非搬 — 停，git show 取回"

# (e) 唯一性：每个被搬特征句全文件恰好出现 1 次（确认主流程那份已删、未重复）
for s in "${MOVED[@]}"; do c=$(grep -cF "$s" "$F"); [ "$c" = "1" ] && echo "OK once: $s" || echo "✗ (e) 出现 $c 次（应 1）: $s"; done

# (f) 占位符/单附录：恰好 1 个 ## 附录 A，无残留占位符
[ "$(grep -c '^## 附录 A —' "$F")" = "1" ] && echo "✓ (f) 单附录" || echo "✗ (f) 附录数异常"
grep -q '<!-- APPENDIX-ENTRIES -->' "$F" && echo "✗ (f) 残留占位符 — T11 未清" || echo "✓ (f) 无残留占位符"

# (g) 尺寸：主流程（附录前）较原文件显著变短
ORIG=$(cat "$B/metrics.txt"); MAINLINES=$(awk '/^## 附录 A —/{exit} {c++} END{print c}' "$F")
awk -v m="$MAINLINES" -v o="$ORIG" 'BEGIN{printf "主流程/原文件 = %.2f (orig=%d main=%d)\n", m/o, o, m}'
```
Expected: (a)(b) diff 无输出；(c) 全 `OK keep`；(d) 全 `OK moved`；(e) 全 `OK once`；(f) 单附录、无残留；(g) 比值 < 1（轻文件接近 1 属正常，无硬阈值——尺寸只作参考，等价性靠 a–f）。

> 跨文件引用完整性（第 8 个、全局不变量）放在 **Task 11** 一次性跑，不在每文件内跑。

---

## Task 2（WORKED EXAMPLE / 模板）: `01-build-roadmap.md` 瘦身

> **这是给执行者的完整范例。** 后续 Task 3–9 只给「保留清单 + 搬走清单 + 指针」，搬法照本任务 + Task 1 的通用动作 + `00-research-topic.md` 已落地的附录形态。

**Files:** Modify `prism/workflows/01-build-roadmap.md`

**保留主流程（KEEP 高亮）：** 全部 `## Step N` / `### 执行方法` / `#### 阶梯 1/2/3` / `#### 落盘与入库` / `### 判定结果汇总` / `### 纪律` 标题；所有 ` ```python/bash/yaml ` 块；Step 1.7 `**如果没有 thesis**` 决策分支；Step 5.6 `> **snippet 兜底（修 cn-adc C）**`（硬 `必须` 指令）；Step 5.6 `### 纪律` bullet（do-checklist）；Step 3/Step 5.6 各类 `**硬要求**`/`**硬规则**` 与 tier/字段定义。
`KEEP=("## Step 5.6" "## Step 5.8" "### 纪律" "**硬要求**" "snippet 兜底")`

**搬走清单（MOVE，verbatim 起始短语 → 边界）：**
- **A1.5** | «> **复用排除边界**：复用» → 止于其后空行（下一保留内容前）| 复用排除边界（prescan 校准层）rationale
- **A2** | «> **S2 · L1/L2 坍缩**：旧版» → 止于 `**硬要求**：` 前 | 为何 L1/L2 坍缩进 primer_scope
- **A3** | «> **收料不再只盯 K#**。两条轴» → 止于 `**硬要求**：` 前 | A/B 双轴 justification
- **A4** | «> **O3 接线 · 类比不再是孤儿**» → 止于其后 ` ```python ` 围栏前（代码块留）| 为何类比喂环⑤
- **A5.6** | «> **为什么必须做**：Step 5.5 只处理了» → 止于 `> **硬规则（auto-fetch 规约` 前 | why-must-do + 产即收衔接
- **A5.8** | «> **为什么必须做**：Step 5.6 的「产即收» → 止于其后 ` ```bash ` 围栏前 | 为何要硬闸门 + 静默推进教训

`MOVED=("复用排除边界" "S2 · L1/L2 坍缩" "收料不再只盯 K#" "O3 接线 · 类比不再是孤儿" "为什么必须做：Step 5.5 只处理了" "为什么必须做：Step 5.6 的「产即收")`

**指针插入（标题保留，正文换成指针）：**
- Step 1.5 下：`> 📎 *复用排除边界（prescan 校准层）→ 附录 A1.5（执行时可跳过）*`
- Step 2 标题下：`> 📎 *L1/L2 坍缩缘由 → 附录 A2（执行时可跳过）*`
- Step 3 标题下：`> 📎 *A轴/B轴 双轴 rationale → 附录 A3（执行时可跳过）*`
- Step 4 内（代码块前）：`> 📎 *为什么类比喂环⑤ → 附录 A4（执行时可跳过）*`
- Step 5.6 标题下（`### 执行方法` 前）：`> 📎 *为什么必须做 / 产即收衔接 → 附录 A5.6（执行时可跳过）*`
- Step 5.8 标题下（` ```bash ` 前）：`> 📎 *为什么必须做 / 静默推进教训 → 附录 A5.8（执行时可跳过）*`

- [ ] **Step 1: 基线快照** — 跑 Task 1 Step 1，`F=prism/workflows/01-build-roadmap.md`。
- [ ] **Step 2: append 附录骨架** — Read 文件末行，Edit 把末行替换成"末行 + 附录骨架模板"。
- [ ] **Step 3: 逐块 append→trim**（按上面 6 块，每块先 Edit#1 append 进附录、后 Edit#2 trim 主流程为指针）。Read 当前区块取真实 verbatim 文本，别依赖行号。
- [ ] **Step 4: 删占位符** — Edit 删 `\n<!-- APPENDIX-ENTRIES -->`。
- [ ] **Step 5: 7 不变量校验** — 跑 Task 1 Step 2，`F=...01-build-roadmap.md` + 上面 `KEEP`/`MOVED`。全 ✓ 才继续。
- [ ] **Step 6: 提交**

Run:
```bash
cd /Users/mark/investing && git add prism/workflows/01-build-roadmap.md && \
git commit -m "docs(prism/01): 主流程瘦身 — rationale 搬入附录 A，执行语义不变

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>" && git log --oneline -1
```
Expected: 仅 1 文件改动。

---

## Task 3: `03-extract-findings.md` 瘦身

**Files:** Modify `prism/workflows/03-extract-findings.md`

**保留主流程：** 全部 `## Step` / `### 2.x` / `#### A/B/C/D` 标题；`[TPL]` 发现笔记模板（`## 核心数据点与事实`/`## 叙事主线`/`## 反常识/分歧点`/`## 未回答问题`/`## 质量备注`，本在 ` ```markdown ` 内）；`**A.~F.**` 抽取框架 bold-label 清单；`> ⚠️ materials/ 是 slug 级共享目录`（路径硬约束）；`> 🔑 env 变量名是 MINERU_TOKEN`（操作约束）；`> Role α web-search 自动豁免` 块（含默认参数 spec）；Subagent dispatch 里的 `**所以**：`-起 do-rule（操作规则，留）。
`KEEP=("## 核心数据点与事实" "## 叙事主线" "## 质量备注" "materials/ 是 slug 级共享目录" "env 变量名是 MINERU_TOKEN" "Role α web-search 自动豁免")`

**搬走清单：**
- **A0b** | «这是诊断不是 gate» → 止于该 `>`/段尾（`[[feedback_addresses_granularity]]` 句）| 父级 finding 假覆盖教训
- **A2-sub** | «经 2026-05-22 4/4 测试» → 止于 `详见 [[subagent-write-hallucination]]`（**保留其后 `**所以**：` do-rule 在主流程**）| subagent 写文件幻觉测试始末
- **A2.1A** | «🔁 **跨 variant 复用** → 止于 `详见各 topic _process_log P1`，再续 «**段落级过滤**：故意» → 止于 `避免「凝聚态/麒麟」...漏掉` | 跨 variant 复用原理 + 段落级过滤为何不做（两段合一附录小节）
- **A2.1B** | «必须用 vlm 模型» → 止于 `详见 [[feedback_mineru_required]]`（**保留 `禁止改 convert(...)` 等硬约束句在主流程**）| 为何必须 vlm + mineru 失败教训

`MOVED=("这是诊断不是 gate" "经 2026-05-22 4/4 测试" "跨 variant 复用" "段落级过滤" "必须用 vlm 模型")`

**指针插入：**
- Step 0b 内（C bullet 处）：`> 📎 *父级 finding 假覆盖教训 → 附录 A0b（执行时可跳过）*`
- Subagent dispatch 内（移块后、`**所以**` 前）：`> 📎 *subagent 写文件幻觉测试始末 → 附录 A2-sub（执行时可跳过）*`
- §2.1 A 复用块处：`> 📎 *跨 variant 复用原理 / 段落级过滤为何不做 → 附录 A2.1A（执行时可跳过）*`
- §2.1 B（移块后）：`> 📎 *为什么必须 vlm / mineru 失败教训 → 附录 A2.1B（执行时可跳过）*`

- [ ] **Step 1–6:** 照 Task 2 流程（基线 → 骨架 → 逐块 append→trim → 删占位 → 7 不变量校验 → 提交 `docs(prism/03): 主流程瘦身 …`）。

---

## Task 4: `05-critic-review.md` 瘦身（轻 · 高 `[TPL]` 风险）

**Files:** Modify `prism/workflows/05-critic-review.md`

> ⚠️ 本文件大量 `[TPL]` 模板（见 Global Constraints）。可搬 rationale 很少（spec 密集），只搬 3 个干净的 `**为什么**`/可选增强块；其余 `>` 块多为承重裁决 mandate / 方向对称硬约束 / 喂瞒规则 / 评分口径——全留。

**保留主流程：** 全部 `## Step` / `###` 真标题 + 所有 `[TPL]` 模板标题（`## 你的处境`…`### 三、致命一击候选` / `## 独立反方报告` / `## 评分与裁决` / `## {timestamp_short} 批评者评审完成`，都在围栏内）；Step 0 承重充分性 mandate `>` 块；Step 2 `> **方向对称(别只做空)**`；2.1 喂/瞒规则；Step 3 评分口径 `>`。
`KEEP=("## 你的处境（对赌框定）" "### 三、致命一击候选" "## 评分与裁决（主 agent）" "方向对称" "批评者评审完成")`

**搬走清单：**
- **A2** | «**为什么必须独立**：同一» → 止于其后 `> **方向对称` 块前 | 为何必须独立反方（共享盲点）
- **A2.2** | «> 可选增强独立性：主 agent» → 止于该 `>` 块尾（`[[feedback_subagent_model]]` 句）| 可选换模型增强独立性
- **A5.5** | «critic 的承重充分性裁决（Step 0 mandate» → 止于 `用 Edit 在**当前` 前 | 为何裁决必须进产出本身

`MOVED=("为什么必须独立" "可选增强独立性" "critic 的承重充分性裁决（Step 0 mandate")`

**指针插入：**
- Step 2 标题下：`> 📎 *为什么必须独立（自我批评共享盲点）→ 附录 A2（执行时可跳过）*`
- 2.2 内：`> 📎 *可选换模型增强独立性 → 附录 A2.2（执行时可跳过）*`
- Step 5.5 标题下：`> 📎 *为什么裁决必须进产出本身 → 附录 A5.5（执行时可跳过）*`

- [ ] **Step 1–6:** 照 Task 2 流程（提交 `docs(prism/05): 主流程瘦身（轻）…`）。**特别校验**：(a) 标题不变量必须确认所有 `[TPL]` 模板标题仍在主流程、未漂移。

---

## Task 5: `04-synthesize/_shared.md` 瘦身（最敏感 · load-bearing XREF）

**Files:** Modify `prism/workflows/04-synthesize/_shared.md`

> ⚠️ 这是四个 case 文件的共享 spec，按 §名被逐字引用。Global Constraints 的 `[XREF]` 标题清单**绝不可动**。本 Task 只搬 7 个明确的 rationale 块，其余（gap 体检 do/don't、`### 不要做的事`、质量检验、所有 schema/命令）全留。

**保留主流程（含全部 [XREF] 标题）：** 见 Global Constraints `[XREF]` 列表逐字保留。
`KEEP=("## B 轴有界 delta 重拆 + 收敛" "#### Scheme C 写作约定" "### 终态报告" "## 全部产出完成后" "## 调度模式：主 agent 直做" "## 即兴 web-search" "## 前置检查" "## gap 体检" "## 增量重写判定")`

**搬走清单：**
- **A-gap** | «> **复用起手的 `*-mirror` 标红属预期**（坑④）» → 段尾，再续 «> ring 轴 `uncovered_ring_inputs` 直接映射到» → 段尾 | `*-mirror` 标红属预期 + ring 轴语义（两段合一）
- **A-whyB** | «> **为什么在写作期才做深度拆解**» → 止于 `这一步把它固化为 decomposition_v1。` | 写作期才深拆 rationale
- **A-drilltype** | «> **三类型差异说明（防混淆）**» → 段尾 | 三类型 drilldown 差异（防混淆）
- **A-mainagent** | «> **为什么主 agent 直做**» → 止于 `详见 [[feedback_subagent_bulk_synthesis]]。` | 为何主 agent 直做
- **A-schemeC** | «**为什么这样写**：用户阅读 thesis_vN 时» → 止于 `不作为日常 review 的依赖。`（**非代码块内**；Scheme C 约定硬约束句留主流程）| 为何全快照写法
- **A-triple** | «> 三件套兜底 = 残留缺口清单（本步）» → 止于 `不假装 04 一定收敛干净。` | 三件套兜底哲学
- **A-tier** | «> Tier 排序基于本 topic 的 thesis 最新版» → 止于 `funnel 文档 Step 1 已要求读 brief + thesis）。` | Tier 排序依据

`MOVED=("复用起手的" "ring 轴" "为什么在写作期才做深度拆解" "三类型差异说明" "为什么主 agent 直做" "为什么这样写" "三件套兜底 = 残留缺口清单" "Tier 排序基于本 topic")`

**指针插入：**
- gap 体检 actionable bullet 后：`> 📎 *复用 *-mirror 标红属预期 / ring 轴语义 → 附录 A-gap（执行时可跳过）*`
- §B 轴标题下（`### 1.` 前）：`> 📎 *为什么写作期才深拆 → 附录 A-whyB（执行时可跳过）*`
- 顽固命门 bullet 处：`> 📎 *三类型 drilldown 差异（防混淆）→ 附录 A-drilltype（执行时可跳过）*`
- 调度模式标题下：`> 📎 *为什么主 agent 直做 → 附录 A-mainagent（执行时可跳过）*`
- Scheme C 约定末（硬约束 bullet 后）：`> 📎 *为什么全快照写法 → 附录 A-schemeC（执行时可跳过）*`
- §终态报告末：`> 📎 *三件套兜底哲学 → 附录 A-triple（执行时可跳过）*`
- selection 折进 funnel 段：`> 📎 *Tier 排序依据 → 附录 A-tier（执行时可跳过）*`

- [ ] **Step 1–6:** 照 Task 2 流程（提交 `docs(prism/04-shared): 主流程瘦身 …`）。**(c) 校验必须含全部 [XREF] 标题**——任一缺失立即停、搬回。

---

## Task 6: funnel 三件套 `_industry_funnel` / `_arena_funnel` / `_company_case`（一套 playbook 套 3 次）

**Files:** Modify（三个，各自独立提交）：`prism/workflows/04-synthesize/{_industry_funnel,_arena_funnel,_company_case}.md`

> 三文件结构近同，搬走块结构一致（A0 / A1.x-why / A附），但有**两处差异必须注意**：
> 1. **§编号漂移**：funnel 两文件「决策链」= `§1.4`、「跨层复用」= `§1.3`；company **互换**（决策链 `§1.3`、跨层复用 `§1.4`）。`A1.x-why` 键据此：funnel → `A1.4`，company → `A1.3`。
> 2. **A1.x-why 段数**：两 funnel 搬 **两段**（`**为什么是紧的**` + `**与 company 的差异（刻意）**`）；company 只搬 **一段**（无"与 company 差异"句）。
> 3. **company A附 边界**：`## 附：与旧路径关系` 表后紧跟一个 **「接线现状（…）」编号清单（1-4）**——那是跨文件接线 ledger，**KEEP 不搬**；A附 只搬到表格最后一行（`critic` 行）为止。

**每个文件 KEEP：** `### 1.1 元目标（逐字不改）` / `### 1.2 理解先行…（**核心规约**）` / `### 1.x 决策链（6 环 · 这就是契约本身）`（含 6-环 ASCII 块）/ `### 1.x 跨层复用质量护栏（**硬规约**）` / `#### 3.2 逐环落地`（环①-⑥）/ `### Step 4 … schema 原样不动` / 头部 `> **调度提示**`/`> **复用上游**`/`> sidecar` 路由块 / company 的 `### Step 0.5 质量红线门控` + 宏观横切 hook（spec/code 全留）/ company A附 后的「接线现状」清单。
`KEEP=("决策链（6 环 · 这就是契约本身）" "元目标" "理解先行" "跨层复用质量护栏" "schema 原样不动" "逐环落地")`

**每个文件搬走（A0 / A1.x / A附）：**
- **A0** | «<noun> 不是终局决策——它是**漏斗**…» / company：«旧的 company 合成把内容切成 8 份**并列研究维度**» → 止于 `…01-08 不再是骨架，降级成一张"别漏维度"的对照清单。`（保留 `## 0. 定位与边界` 标题）| 定位/边界 + 与旧路径根本改动
- **A1.4（funnel）/ A1.3（company）** | «**为什么是紧的**：③ 只因②产出定价才存在» → funnel 止于 `…（喂 09/10 sidecar）。`；company 止于 `…环与环是因果序、不是并列箱。`（6-环 ASCII 块留主流程）| 为何链是紧的（+ funnel 的刻意差异）
- **A附** | «| | 旧 <noun> 路径 | 本路径 |» → 止于 `critic` 行（company：止于表末、`**接线现状**` 清单前）（保留 `## 附：与旧路径关系 + follow-up` 标题）| 与旧 8 份路径逐项对照表

`MOVED`（每文件）`=("定位与边界特征句(noun)" "为什么是紧的" "旧 <noun> 路径")` —— 执行时取该文件真实 verbatim 起始短语。

**指针插入（每文件）：**
- `## 0. 定位与边界` 下：`> 📎 *<noun> funnel/case 的定位/边界、与旧路径的根本改动 → 附录 A0（执行时可跳过）*`
- 6-环围栏后（§1.4/§1.3）：`> 📎 *为什么链是紧的 / 与 company EV 的刻意差异 → 附录 A1.4（执行时可跳过）*`（company 改 `A1.3` 且去掉"与 company 差异"措辞）
- `## 附：与旧路径关系 + follow-up` 下：`> 📎 *与旧 8-份路径的逐项对照 → 附录 A附（执行时可跳过）*`

- [ ] **Step 1: `_industry_funnel.md`** — 照 Task 2 流程跑完（基线→骨架→3 块 append→trim→删占位→7 不变量），提交 `docs(prism/04-industry): 主流程瘦身 …`。
- [ ] **Step 2: `_arena_funnel.md`** — 同上（注意行 265 截断句在 KEEP 块内，逐字保留不修），提交 `docs(prism/04-arena): …`。
- [ ] **Step 3: `_company_case.md`** — 同上（A1.3 单段；A附 止于表末、保「接线现状」清单），提交 `docs(prism/04-company): …`。

---

## Task 7: `02-gather-materials.md` 瘦身（轻）

**Files:** Modify `prism/workflows/02-gather-materials.md`

**保留主流程：** 全部 `## Step` 标题（含两个同名 `## Step 5.7`，逐字保留不合并）；Step 5.8 gap 体检 B/A 轴 bullet + 补救顺序 1-2-3（决策骨架）；Step 6 内联代码注释（auto-fetch 规约守卫，load-bearing）；`> 🔑 MINERU_TOKEN` env gotcha；mineru `禁止改 convert(...) 的第三参` 硬约束句；各 `判定与盖戳全照 _autofetch_protocol.md` 指针句。
`KEEP=("## Step 5.7" "## Step 5.8" "MINERU_TOKEN" "_autofetch_protocol.md")`

**搬走清单：**
- **A-autofetch** | «> **为什么必须做**：02 历史上把"让用户补"» → 止于 `…作用在 02 时点仍欠尝试的 todo 上。`（保留其后 `判定与盖戳全照 _autofetch_protocol.md` 句在主流程）| Step 5.7 auto-fetch 历史教训
- **A-early** | «> **早期 ingest 不替代本步**：00 Step 4.0 的 `register_inbox_materials`» → 止于 `再在 Step 4 补 addresses/rings。` | 为何 02 仍跑（早期 ingest 不替代）
- **A-mineru** | «> ⚠️ **必须用 vlm 模型**——pipeline/pymupdf 会丢» → 止于 `详见 [[feedback_mineru_required]]。`（保留 `禁止改 convert(...)` 硬约束句在主流程）| 为何必须 vlm + memory-slug

`MOVED=("为什么必须做：02 历史上把" "早期 ingest 不替代本步" "必须用 vlm 模型")`

**指针插入：**
- Step 5.7（auto-fetch 那个）标题下：`> 📎 *auto-fetch 历史教训 → 附录 A-autofetch（执行时可跳过）*`
- Step 前置 ingest 块处：`> 📎 *早期 ingest 不替代本步 → 附录 A-early（执行时可跳过）*`
- Step 4.5 mineru 处：`> 📎 *为什么必须 vlm + [[feedback_mineru_required]] → 附录 A-mineru（执行时可跳过）*`

- [ ] **Step 1–6:** 照 Task 2 流程（提交 `docs(prism/02): 主流程瘦身（轻）…`）。

---

## Task 8: `04-synthesize/00-primer.md` 瘦身（轻 · critic prompt `[TPL]`）

**Files:** Modify `prism/workflows/04-synthesize/00-primer.md`

**保留主流程：** `### 不变的元目标（…逐字不改）` blockquote；全部 `## Step`/`### 2.x` 标题；`[TPL]` critic prompt（`## 你的角色`/`## 关键校验规则`/`## 你要校验的目标`/`## 你要做的`，在围栏内）；`> 目标不从零拍脑袋`（含读种子指令）；`> O2 接线 · baseline_knowledge.md…`（含"读 §六 校准结果 / 推翻 fact 不准写"硬指令）；已验证样例 paths（lines 84-86，工作文件引用）；§2.3 来源分层表 / §2.4 depth 规则 / Step 4 frontmatter spec + F17 gate。
`KEEP=("不变的元目标" "## 你的角色" "## 你要做的" "目标不从零拍脑袋" "O2 接线")`

**搬走清单（仅 2 个干净历史教训）：**
- **A2.4** | «> **关键洞察（来自 robinhood/荣昌验证）**：稀有领域的瓶颈» → 止于 `…不编造。`（§2.4 末）| 稀有领域瓶颈在 findings 覆盖度
- **A3.2** | «> 已验证收敛速度：robinhood 首轮 4 [不够]» → 止于 `…修一轮即可。`（§3.2 末）| critic 收敛速度实例

`MOVED=("关键洞察（来自 robinhood/荣昌验证）" "已验证收敛速度：robinhood 首轮")`

**指针插入：**
- §2.4 末：`> 📎 *稀有领域瓶颈在 findings 覆盖度（robinhood/荣昌验证）→ 附录 A2.4（执行时可跳过）*`
- §3.2 末：`> 📎 *critic 收敛速度实例 → 附录 A3.2（执行时可跳过）*`

- [ ] **Step 1–6:** 照 Task 2 流程（提交 `docs(prism/04-primer): 主流程瘦身（轻）…`）。

---

## Task 9: `04-synthesize/_macro_regime.md` 瘦身（极轻 · 仅尾部对照表）

**Files:** Modify `prism/workflows/04-synthesize/_macro_regime.md`

> ⚠️ 此文件 IS 因果链契约（§1 总纲 / §3.5 机制纠错八条·多维读数·fragility / §4 schema）。§0「定位与边界」与"两处根本规约 + 与 arena/company 刻意差异"**深度交织**，拆分有误删硬约束的风险——**§0 整段保留不动**。唯一干净可搬的是尾部 `## 附：与 arena/company 路径的关系` 的**对照表正文**（纯解释型 tail）。

**保留主流程：** 全部 `## n.`/`### Step`/`### 3.5.x` 标题；§0 整段（定位 + 根本规约 + 刻意差异，全留）；所有 schema/spec/命令；§3.5 三小节；`## 附：…关系` 标题保留。
`KEEP=("## 1. 因果链总纲（这就是契约本身）" "### 3.5.1 机制纠错八条" "## 4. 执行 — L4 传导地图 sidecar" "## 0. 定位与边界")`

**搬走清单（仅 1 块）：**
- **A附** | «| | arena `_arena_funnel.md` | company» → 文件末（`## 附：与 arena/company 路径的关系` 标题下的对照表正文）| 与 arena/company 路径对照表

`MOVED=("arena \`_arena_funnel.md\` | company")` —— 执行时取真实 verbatim 表头。

**指针插入：**
- `## 附：与 arena/company 路径的关系` 下：`> 📎 *与 arena/company 路径的对照表 → 附录 A附（执行时可跳过）*`

- [ ] **Step 1–6:** 照 Task 2 流程（提交 `docs(prism/04-macro): 尾部对照表搬入附录 …`）。**(g) 尺寸比值接近 1 属预期**（只搬一块）。

---

## Task 10: NO-OP 文件登记（不改文件，只确认 + 记录判定）

> 以下 6 个文件经 per-file 分析判为 **NO-OP**（可搬 rationale 不足 / 全是 load-bearing spec / 已有内容附录）。**不动这些文件**；本 Task 只跑一次 dryness 复核 grep 留证，避免后续维护者疑惑"为何漏了它们"。

**Files:** 只读复核：`06-daily-monitor.md` / `07-drilldown.md` / `_peer_matrix_spec.md` / `_arena_select_spec.md` / `_decision_kit_spec.md` / `_valuation_models.md`

- [ ] **Step 1: dryness 复核**

Run:
```bash
cd /Users/mark/investing
for f in 06-daily-monitor 07-drilldown; do
  P=prism/workflows/$f.md; echo "== $f：为什么必须做 计数 =="; grep -c "为什么必须做" "$P"
done
for f in _peer_matrix_spec _arena_select_spec _decision_kit_spec _valuation_models; do
  P=prism/workflows/04-synthesize/$f.md; echo "== 04/$f：为什么必须做 计数 =="; grep -c "为什么必须做" "$P"
done
```
Expected: 全部 `0`（无 `**为什么必须做**` 段）——印证这些文件无成段 justification 可搬。`06-daily-monitor.md` 的 `## 附录：monitoring_tier 三档` 是内容 spec 表（非 rationale 附录），保持不动。

- [ ] **Step 2: 记录判定（无需改文件）** — 在执行记录/PR 描述里写明：6 文件 NO-OP，理由见本计划 File Structure 表。另注：`07-drilldown.md` 末 `## Step 5` 疑似无正文（预存在截断）——本计划不修，仅登记待用户确认。

---

## Task 11 (T-VERIFY-GLOBAL): 全局跨文件引用完整性 + 清基线

**Files:** 只读校验；末尾删基线目录。

- [ ] **Step 1: 单附录 / 无残留占位符（所有 slim 过的文件）**

Run:
```bash
cd /Users/mark/investing
for P in 01-build-roadmap 02-gather-materials 03-extract-findings 05-critic-review \
         04-synthesize/_shared 04-synthesize/_industry_funnel 04-synthesize/_arena_funnel \
         04-synthesize/_company_case 04-synthesize/00-primer 04-synthesize/_macro_regime; do
  F=prism/workflows/$P.md
  a=$(grep -c '^## 附录 A —' "$F"); o=$(grep -c '<!-- APPENDIX-ENTRIES -->' "$F")
  [ "$a" = "1" ] && [ "$o" = "0" ] && echo "✓ $P" || echo "✗ $P (附录=$a 占位=$o)"
done
```
Expected: 10 行全 `✓`。

- [ ] **Step 2: 跨文件 §/Step 引用完整性（核心 load-bearing 锚点仍解析）**

Run:
```bash
cd /Users/mark/investing
SH=prism/workflows/04-synthesize/_shared.md
echo "--- _shared.md 被引用的 [XREF] 锚点仍在主流程（附录前）---"
MAIN=$(awk '/^## 附录 A —/{exit} {print}' "$SH")
for s in "## B 轴有界 delta 重拆 + 收敛" "#### Scheme C 写作约定" "### 终态报告" \
         "## 全部产出完成后" "## 调度模式：主 agent 直做" "## 即兴 web-search" \
         "## 前置检查" "## gap 体检" "## 增量重写判定"; do
  echo "$MAIN" | grep -qF "$s" && echo "OK xref: $s" || echo "✗ MISSING xref: $s"
done
echo "--- 00 被下游引用的 Step 锚点仍在 ---"
F0=prism/workflows/00-research-topic.md
for step in "Step 4.0" "Step 4.3" "Step 4.5a" "Step 4.5c" "Step 5.0" "Step 5.4" "Step 6.5"; do
  grep -qE "^#{2,4} .*$step" "$F0" && echo "OK 00 anchor: $step" || echo "✗ MISSING: $step"
done
echo "--- 只动了预期文件（slim 提交后 working tree 应干净）---"
git status --short
```
Expected: 全 `OK`；`git status --short` 干净（所有改动已分 Task 提交）。任一 `✗` → 停，回对应 Task 把被误搬/误删的锚点搬回主流程。

- [ ] **Step 3: 清理基线目录**

Run:
```bash
rm -rf docs/superpowers/plans/_wfslim_baseline && echo "基线已清"
```
Expected: `基线已清`。

> **若任一不变量 ✗**：不要把该文件计入完成。按提示回对应 Task 修；零丢失 ✗ 时用 `git show HEAD:<file>` 取回被误删原文逐字补进附录。

---

## Out of Scope（刻意不做）

- **合并/删除/下放任何 Step、思考产物、契约**——本计划是**搬迁**，零语义改动；下游按 Step 号 / §名 / schema 引用，删改会断链。
- **改 .py**——Task 0 只是**提交已存在**的 .py 改动，不新写;触碰符号要走 CLAUDE.md impact 分析，属另一计划。
- **修预存在瑕疵**——02 双 `Step 5.7`、07 末 `Step 5` 空、`_arena_funnel` 行 265 截断句：只逐字保留，不修。
- **slim NO-OP 文件**——06/07/4 个 spec 文件经核实无足量可搬 rationale，强行制造附录是噪声。
- **改 `00-research-topic.md`**——已瘦身完毕。
- **重排附录小节成精美目录**——顺序不影响功能，T11 只保证单附录、无残留占位、无重复键。

## Self-Review

- **Spec 覆盖**：瘦身机制（搬迁/附录/指针/骨架）→ Global Constraints + Task 1 通用动作；逐文件 keep/move（verbatim locator）→ Task 2–9；NO-OP 判定 + 留证 → Task 10 + File Structure 表；等价性 7 不变量（标题/代码块/结构事实/零丢失/唯一性/单附录/尺寸）→ Task 1 Step 2 套每文件；**跨文件引用完整性（第 8 不变量）**→ Task 11 Step 2；脏树先提交 → Task 0；提交粒度（每文件一 commit）→ 各 Task Step 6。
- **无占位符**：每 SLIM Task 给「KEEP 数组 + MOVED 数组（verbatim 起始短语）+ 边界规则 + 指针全文」；Task 2 是端到端 worked example；`00-research-topic.md` 已落地附录作活样板；验证全是可跑 bash 带预期。被搬块逐字搬迁，执行者 Read 后取真实 verbatim（不需预抄全文，与 00 计划同策略）。
- **一致性**：附录键全程 Step/§ 派生且文件内唯一；funnel 三件套的 §编号漂移（A1.4 vs A1.3）、段数差异、company A附 边界、`[TPL]`/`[XREF]` 硬清单都已显式标注；指针格式全程统一 `> 📎 *… → 附录 A{key}（执行时可跳过）*`。
- **风险兜底**：最危险"误删而非搬"→ (d) 零丢失 + (e) 唯一性 双查；"误搬结构事实/XREF"→ (c) 结构事实 + Task 11 跨文件 §校验 双向围栏；"动了模板"→ (a) 标题不变量含 `[TPL]` 标题 + 代码块不变量；funnel 编号漂移 → Task 6 抬头三条差异显式列出。

# Prism Workflow 00 — 文档修复 + 流程精简 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 workflow 00 流程文档里 8 个会让执行者踩坑或返工的缺陷（A~H），并加一个"00 速览 + 产物依赖表"导航块降低文档认知负荷，全程不改变任何执行语义。

**Architecture:** 纯文档/示例代码编辑——改动只落在 3 个 Markdown 文件（`prism/workflows/00-research-topic.md`、`.claude/skills/prism/SKILL.md`、`prism/workflows/_web_prescan_shared.md`）。**不改任何 `.py` 代码符号**，所以 gitnexus `impact` 不适用；每个任务用 `grep` 确认编辑落地即可。

**Tech Stack:** Markdown；编辑用 Edit 工具做 verbatim 字符串替换；验证用 `grep`/`rg`。

## Global Constraints

- **只改文档，不改代码**：禁止编辑任何 `.py`。本计划所有改动是 Markdown 正文 + Markdown 内的示例代码块文本。
- **逐字匹配**：每个任务给出的 `old_string` 是从当前文件 verbatim 复制的，必须先 Read 目标文件确认该串仍存在再 Edit（文件可能已被其它任务改动而行号漂移；用唯一字符串匹配，不要依赖行号）。
- **不删除/不合并/不下放任何执行步骤或思考产物**：经核实，`baseline_knowledge.md` / `thesis_v{N}.md` 的 K# / `decomposition_v{N}.md` 的命门+primer目标 是三条不同轴、且都被下游（03/04/05/07）消费——删改它们会断 04 的 delta 重拆螺旋、03 的 cite、05 的校准清单。本计划的"精简"**只降文档表达与导航成本，不动语义**（见 Out of Scope）。
- **提交**：在新分支上做；当前分支是 `main`，先开 `git switch -c docs/wf00-fixes`。完成后 `git diff --stat` 复核仅这 3 个 `.md` 改动，再 commit。

---

## File Structure

- `prism/workflows/00-research-topic.md` — 主受影响文件（A、B、C、G、H、SIMP）
- `.claude/skills/prism/SKILL.md` — 技能路由文档（D、E）
- `prism/workflows/_web_prescan_shared.md` — prescan 共享子流程（F）

---

## Task 0: 开分支

- [ ] **Step 1: 开 feature 分支**

Run:
```bash
cd /Users/mark/investing && git switch -c docs/wf00-fixes
```
Expected: `Switched to a new branch 'docs/wf00-fixes'`

---

## Task A: fetch_report_prism 必须用 venv 解释器（缺这条会 ModuleNotFoundError）

**Files:**
- Modify: `prism/workflows/00-research-topic.md`（Step 6.5a 代码块前）

**背景：** `scripts/fetch_report_prism.py` `import requests`，仓库默认 `python3` 未装 `requests`，裸跑直接 `ModuleNotFoundError`。仓库根有 `.venv`（`./.venv/bin/python` 有 requests）。其余纯 CRUD 脚本（topic/manifest）裸 `python3` 可跑。文档当前没任何标注。

- [ ] **Step 1: 在 6.5a 的 python 代码块前插入 venv 警示**

Edit `prism/workflows/00-research-topic.md`:

old_string:
````
```python
from scripts.fetch_report_prism import fetch
from prism.scripts.topic import mark_todo_fetch, update_user_todo_status
````

new_string:
````
> ⚠️ **本段必须用 `./.venv/bin/python` 跑**：`fetch_report_prism` 依赖 `requests`，仓库默认 `python3` 未装，裸跑会 `ModuleNotFoundError: No module named 'requests'`。纯 CRUD 脚本（`prism.scripts.topic` / `prism.scripts.manifest`）才可用裸 `python3`。

```python
from scripts.fetch_report_prism import fetch
from prism.scripts.topic import mark_todo_fetch, update_user_todo_status
````

- [ ] **Step 2: 验证**

Run:
```bash
grep -n "本段必须用 ./.venv/bin/python" prism/workflows/00-research-topic.md
```
Expected: 命中 1 行。

---

## Task C: 更正"fetch() 盖 todo status"的过度承诺

**Files:**
- Modify: `prism/workflows/00-research-topic.md`（Step 6.5a 代码块内注释）

**背景：** 实测 `fetch()` 只登记 manifest、按公司名把命中 todo 的 `status` 置 `in_progress`，但**不设 `fetch_status`、不闭环 `done`**。原注释说"盖 todo status"会误导执行者以为不用手动闭环。

- [ ] **Step 1: 改注释**

Edit `prism/workflows/00-research-topic.md`:

old_string:
```
# fetch() 自己登记 manifest + 盖 todo status；主 agent 仅在跨多 ticker / 部分到位时补判 done vs in_progress
```

new_string:
```
# fetch() 登记 manifest，并按公司名把命中 todo 的 status 置 in_progress；但**不设 fetch_status、不闭环 done**
# → 必须由下面的 mark_todo_fetch + update_user_todo_status 显式闭环（闭环键 = task 子串/文档身份）
```

- [ ] **Step 2: 验证**

Run:
```bash
grep -n "不设 fetch_status、不闭环 done" prism/workflows/00-research-topic.md
```
Expected: 命中 1 行。

---

## Task B: covered_by 用 manifest 主键 `id`（不是 `mat_id`，也不是 Path）

**Files:**
- Modify: `prism/workflows/00-research-topic.md`（Step 6.5a 示例末行）

**背景：** manifest 里 material dict 的主键字段名是 **`id`**（值形如 `mat-ea14bb`），不是 `mat_id`。而 `fetch()` 返回的是 `Path` 对象。原示例 `covered_by=[m for m in got]` 把 Path 列表塞进 `covered_by`，错误。正确做法：按 filename 反查 manifest 的 `id`。

- [ ] **Step 1: 修正 covered_by 示例**

Edit `prism/workflows/00-research-topic.md`:

old_string:
```
update_user_todo_status(slug, variant, '茅五泸三家 2025 年报', 'done', covered_by=[m for m in got])
```

new_string:
```
# covered_by 要 manifest 主键：material dict 的字段名是 `id`（不是 `mat_id`）；fetch() 返回 Path，需按 filename 反查
from prism.scripts.manifest import read_manifest
_idx = {m['filename']: m['id'] for m in read_manifest(slug, variant)['materials']}
covered_ids = [_idx[p.name] for p in got if p.name in _idx]
update_user_todo_status(slug, variant, '茅五泸三家 2025 年报', 'done', covered_by=covered_ids)
```

- [ ] **Step 2: 验证**

Run:
```bash
grep -n "material dict 的字段名是 .id." prism/workflows/00-research-topic.md
```
Expected: 命中 1 行。

---

## Task D: 更正"脚本下载都进 inbox/"的不精确表述（功能无 bug，仅措辞）

**Files:**
- Modify: `.claude/skills/prism/SKILL.md`（关键规则 #5）

**背景：** 经核实这不是功能 bug——`register_inbox_materials` 同时扫 `inbox/` 和 `materials/`（manifest.py），且 `fetch_report_prism --slug` 自登记 manifest。但 SKILL.md 措辞说"脚本下载都进 inbox/"，与实际（年报落 `materials/`）不符，易误导。

- [ ] **Step 1: 改措辞**

Edit `.claude/skills/prism/SKILL.md`:

old_string:
```
5. **资料只在 topic 层**：用户手动放 / 脚本下载都进 `prism/topics/{slug}/inbox/`（已无全局 inbox），`register_inbox_materials` 登记元数据后由 02/03 处理
```

new_string:
```
5. **资料只在 topic 层**：用户手放进 `prism/topics/{slug}/inbox/`；脚本自动下载的年报/财报落 `prism/topics/{slug}/materials/`（已无全局 inbox）。`register_inbox_materials` **两个目录都扫**，`fetch_report_prism` 还会自登记 manifest——元数据登记后由 02/03 处理
```

- [ ] **Step 2: 验证**

Run:
```bash
grep -n "两个目录都扫" .claude/skills/prism/SKILL.md
```
Expected: 命中 1 行。

---

## Task E: read_topic 示例补上必填的 variant 参数

**Files:**
- Modify: `.claude/skills/prism/SKILL.md`（Python Scripts 段「读 topic」示例）

**背景：** `read_topic(slug, variant)` 的 `variant` 是必填位置参数；照原示例 `read_topic('slug')` 跑会 `TypeError: read_topic() missing 1 required positional argument: 'variant'`。

- [ ] **Step 1: 补 variant**

Edit `.claude/skills/prism/SKILL.md`:

old_string:
```
python3 -c "from prism.scripts.topic import read_topic; import json; print(json.dumps(read_topic('slug'), ensure_ascii=False, indent=2))"
```

new_string:
```
python3 -c "from prism.scripts.topic import read_topic; import json; print(json.dumps(read_topic('slug', 'opus4.8'), ensure_ascii=False, indent=2))"  # read_topic(slug, variant)：variant 必填，缺则 TypeError
```

- [ ] **Step 2: 验证**

Run:
```bash
grep -n "read_topic('slug', 'opus4.8')" .claude/skills/prism/SKILL.md
```
Expected: 命中 1 行。

---

## Task F: 在 prescan 文档暴露 register_web_search_batch 的返回 key

**Files:**
- Modify: `prism/workflows/_web_prescan_shared.md`（Step D 标题下）

**背景：** `register_web_search_batch` 返回 dict 的计数 key 是 `n_high`/`n_mid`/`n_low`/`n_dropped_low`/`drop_ratio`/`dropped_hits`/`failure_mode`（已在 `web_prescan.py` docstring，但 workflow 文档未surface）。执行者易用 `r['high']` 取值得到 KeyError/None（本次实操就踩了）。Step D 当前只展示单条版 `register_web_search_result` 的 `{mat_id, band, ...}`。

- [ ] **Step 1: 在 Step D 标题后插入返回 schema 提示**

Edit `prism/workflows/_web_prescan_shared.md`:

old_string:
```
## Step D：register 每条 hit（自动三档分流）
```

new_string:
```
## Step D：register 每条 hit（自动三档分流）

> **`register_web_search_batch` 返回 dict 的计数 key 是 `n_high`/`n_mid`/`n_low`/`n_dropped_low`/`drop_ratio`/`dropped_hits`/`failure_mode`（不是 `high`/`mid`）**——读它判救回时勿用 `r['high']`（会 KeyError/None）。单条版 `register_web_search_result` 才返回 `{mat_id, band, confidence, domain, domain_tier, filename}`。
```

- [ ] **Step 2: 验证**

Run:
```bash
grep -n "不是 .high./.mid." prism/workflows/_web_prescan_shared.md
```
Expected: 命中 1 行。

---

## Task G: 标注 4.5b 在 4.5a 充分时是兜底地板而非第二轮普查

**Files:**
- Modify: `prism/workflows/00-research-topic.md`（Step 4.5b 标题后）

**背景：** `build_search_queries` 常只吐 scope + industry-event 等少量泛槽；若 4.5a（baseline §5 优先 query）写得充分，这些槽已被覆盖，4.5b 近乎 no-op。文档没说清，执行者会以为 4.5b 是与 4.5a 并列的第二轮全量普查而重复劳动。

- [ ] **Step 1: 插入说明**

Edit `prism/workflows/00-research-topic.md`:

old_string:
```
### Step 4.5b：跑覆盖槽 prescan

调用 `prism/workflows/_web_prescan_shared.md`，参数 `recency_days=90`，`triggered_by='00-prescan'`。
```

new_string:
```
### Step 4.5b：跑覆盖槽 prescan

> **4.5b 是兜底地板，不是与 4.5a 并列的第二轮普查。** 若 4.5a 的 baseline §5 优先 query 已覆盖 `build_search_queries` 吐的槽（scope / industry-event 等），4.5b 只需确认覆盖、补未被覆盖的边角槽即可，**不必为已覆盖槽另写 query**。它的作用是兜住"§5 写薄"的情况（机械枚举不依赖 agent 想没想到）。

调用 `prism/workflows/_web_prescan_shared.md`，参数 `recency_days=90`，`triggered_by='00-prescan'`。
```

- [ ] **Step 2: 验证**

Run:
```bash
grep -n "4.5b 是兜底地板" prism/workflows/00-research-topic.md
```
Expected: 命中 1 行。

---

## Task H: Step 3 意图分叉补"父级种的空壳 stub"这一支

**Files:**
- Modify: `prism/workflows/00-research-topic.md`（Step 3 分叉 bullet 列表末）

**背景：** Step 3 的意图分叉只覆盖"slug 已有其它变体"，没覆盖"本变体已存在、但只是 industry 环⑥派生 arena 时种下的 stub（有 thesis_v0 history 但 outputs 几乎空、stage 仍 `00-init`、无 baseline/prescan/decomposition/todos）"。本次实操遇到 `cn-adc/opus4.8` 正是这种空壳，靠临场判断才走对（续做本变体、把 stub thesis 重写为 prescan 校准版 v0）。

- [ ] **Step 1: 在"撞名"bullet 后追加 stub bullet**

Edit `prism/workflows/00-research-topic.md`:

old_string:
```
  - **另一个 topic 撞名**：slug 加后缀（如 `cn-pet-industry-2`）另起。
```

new_string:
```
  - **另一个 topic 撞名**：slug 加后缀（如 `cn-pet-industry-2`）另起。
  - **本变体已存在但只是父级 init 种的空壳 stub**（industry 环⑥派生 arena 时 `set_thesis(version=0, stage_set_at='00-init-from-parent')` 种下继承 thesis_v0，stage 仍 `00-init`、无 baseline/prescan/decomposition/todos、manifest 0 料）→ **不是另起变体，而是续做本变体**：在现有 stub 上正常跑 Step 4.3→6.5（baseline → prescan → 把继承的 stub thesis **重写为 prescan 校准版 thesis_v0** → decomposition_v0 → todos → eager-fetch）。判据：`read_topic` 显示 thesis 有 history 但 `outputs_state` 几乎空、`manifest` 0 料。
```

- [ ] **Step 2: 验证**

Run:
```bash
grep -n "本变体已存在但只是父级 init 种的空壳 stub" prism/workflows/00-research-topic.md
```
Expected: 命中 1 行。

---

## Task SIMP: 在 00 顶部加"速览 + 产物依赖表"导航块（唯一的精简动作，纯加法）

**Files:**
- Modify: `prism/workflows/00-research-topic.md`（文件头 header 之后）

**背景：** 706 行密集散文的最大成本是"读懂 + 导航"。最高杠杆且零语义风险的精简，是在顶部加一个 4 幕速览 + 三产物依赖表，让执行者 20 行内拿到全貌；依赖表同时**钉死"这三个产物喂下游、不可删/合并/下放"**，避免未来执行者重蹈"以为 decomposition 是 00-local 仪式而想删"的错。

- [ ] **Step 1: 在 header 的 `---` 后插入速览块**

Edit `prism/workflows/00-research-topic.md`:

old_string:
```
# Workflow 00 — 开启新研究主题

**触发**：用户说「研究 X」或「开始研究 X」  
**产出**：创建 `prism/topics/{slug}/topic.yaml` + `manifest.yaml`，Web 页面 /prism/{slug} 可访问

---
```

new_string:
```
# Workflow 00 — 开启新研究主题

**触发**：用户说「研究 X」或「开始研究 X」  
**产出**：创建 `prism/topics/{slug}/topic.yaml` + `manifest.yaml`，Web 页面 /prism/{slug} 可访问

---

## 00 速览（先读这块，再看细节步骤）

**4 幕 / 3 思考产物**（步骤号是落地细节，幕是心智模型）：

| 幕 | 步骤 | 产出 | 一句话 |
|----|------|------|--------|
| ① 立框 | Step 1-4 | topic.yaml + manifest | type→终局倒推 + question 押注 + slug + 早期 ingest |
| ② 认知 | Step 4.3 | `baseline_knowledge.md` | 训练知识先验（fact 账本 + 置信度 + 时效标签）+ 盲点→query |
| ② 校准 | Step 4.5 a/b/c | 入库 web-search + baseline §6 | prescan 把时敏 fact 对齐最新现实（防把过期事实当赌注） |
| ③ 下注 | Step 5.0 | `thesis_v0.md` | 落在 type 终局上的赌注 + K#（可证伪）+ 反方 |
| ③ 拆解 | Step 5.4 | `decomposition_v0.md` | 从终局拆命门（机理/兑现路径）+ 每环 B 靶点 + primer 入门目标种子 |
| ④ 收料 | Step 6 / 6.5 | user_todos + 抓料入库 | K# + A 合同 派 todo → 产即收 eager-fetch → no-unattempted 硬闸门 |

**三个思考产物是三条不同轴、互不替代、且都喂下游——不要合并 / 删除 / 下放**（已核实下游消费）：

| 产物 | 轴 | 下游消费者 |
|------|----|-----------|
| `baseline_knowledge.md` | 训练知识先验 | 03-extract（findings cite `[fact-NN]`）、05-critic（列未校准 fact 清单）、04 primer |
| `thesis_v{N}.md` 的 **K#** | 论点 / 覆盖轴 | gap_detector 算 K# 覆盖率、01-roadmap、05-critic |
| `decomposition_v{N}.md` 的 **命门 / B 靶点 / primer 目标** | 终局拆解轴 | **04 `_shared.md` 的「B 轴有界 delta 重拆」以 v0 为基线逐条 diff** → v1；04 各 funnel/case 决策环；05-critic；未收敛命门 capped→07-drilldown。primer 入门目标是 04 primer 的种子，"入门目标 delta 空"是 04 收敛的必要条件 |

> **命门 ≠ K# 换个说法**：K# 是可证伪的"会改变看法的事件"（覆盖轴，喂 gap_detector）；命门是"机理/兑现路径上方向错了就翻盘"的特化问题（终局拆解轴，映射到决策环）。写 `decomposition_v0` 时**不要把命门写成"覆盖 K1/K3"的复述**——那是把终局拆解轴退化成 K# 的影子，会让 04 的 delta 重拆失去真实基线。

---
```

- [ ] **Step 2: 验证**

Run:
```bash
grep -n "00 速览（先读这块" prism/workflows/00-research-topic.md && grep -n "命门 ≠ K# 换个说法" prism/workflows/00-research-topic.md
```
Expected: 两条都命中。

---

## Task Z: 复核 + 提交

- [ ] **Step 1: 确认只改了 3 个 .md，无 .py 改动**

Run:
```bash
git -C /Users/mark/investing diff --stat
```
Expected: 仅 `prism/workflows/00-research-topic.md`、`.claude/skills/prism/SKILL.md`、`prism/workflows/_web_prescan_shared.md` 三个文件，**无任何 `.py`**。若出现 `.py`，停下排查。

- [ ] **Step 2: 全量验证 8 处修复 + 速览块都在**

Run:
```bash
cd /Users/mark/investing
for s in \
  "本段必须用 ./.venv/bin/python" \
  "不设 fetch_status、不闭环 done" \
  "material dict 的字段名是 .id." \
  "4.5b 是兜底地板" \
  "本变体已存在但只是父级 init 种的空壳 stub" \
  "00 速览（先读这块" ; do
  grep -q "$s" prism/workflows/00-research-topic.md && echo "OK 00: $s" || echo "MISSING 00: $s"
done
grep -q "两个目录都扫" .claude/skills/prism/SKILL.md && echo "OK SKILL D" || echo "MISSING SKILL D"
grep -q "read_topic('slug', 'opus4.8')" .claude/skills/prism/SKILL.md && echo "OK SKILL E" || echo "MISSING SKILL E"
grep -q "不是 .high./.mid." prism/workflows/_web_prescan_shared.md && echo "OK prescan F" || echo "MISSING prescan F"
```
Expected: 9 行全部 `OK`，无 `MISSING`。

- [ ] **Step 3: 提交**

Run:
```bash
cd /Users/mark/investing && git add prism/workflows/00-research-topic.md .claude/skills/prism/SKILL.md prism/workflows/_web_prescan_shared.md && git commit -m "docs(prism/wf00): 修 8 处执行坑(venv/盖戳/id字段/inbox措辞/read_topic/batch返回/4.5b/stub分叉) + 加速览依赖表

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
Expected: 1 个 commit，3 文件改动。

---

## Out of Scope（刻意不做，附理由）

- **删除/合并/下放任何思考产物或执行步骤**——本次核实下游消费后确认 `baseline` / K# / `decomposition`（含命门、B 靶点、primer 目标）都喂 03/04/05/07，删改会断 04 的 delta 重拆螺旋、03 的 cite、05 的校准清单。最初"过重→该删"的判断是**只看了 00 没读下游**得出的，错误，已撤回。
- **把 706 行的防御性散文/worked example/rationale 整体抽到附录**——价值是降文档体积，但属于大范围主观重排，机械执行风险高（易误删被下游引用的锚点）。如要做，应另起一个 brainstorming + 独立 plan，逐段确认每块 prose 没有被其它文档 `grep` 引用后再移，不在本 plan 范围。
- **把 B/C/D 改成代码修复（给 `id` 加 `mat_id` 别名 / 让 `fetch()` 自动盖 `fetch_status` / 让 `fetch()` 返回 mat_id）**——这些是更彻底的修法但触碰 `.py` 符号，需走 CLAUDE.md 的 `impact` 分析 + 回归。本 plan 选择风险最低的文档侧修复；代码侧改进可作后续独立 plan。

## Self-Review

- **覆盖**：A(Task A)/B(Task B)/C(Task C)/D(Task D)/E(Task E)/F(Task F)/G(Task G)/H(Task H) 八项各一任务 + 流程精简(Task SIMP) + 分支(Task 0) + 复核提交(Task Z)。无遗漏。
- **无占位符**：每个 Edit 给了 verbatim old/new 全文，每个任务带 grep 验证与预期。
- **一致性**：所有 `old_string` 均从当前文件 verbatim 取（2026-06-27 核实）；执行前若被前序任务改动导致不匹配，按 Global Constraints 重新 Read 该文件取最新 verbatim 串。三个文件路径全程一致。

# Prism Workflow 简化 · 实施计划（W-A ~ W-F）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 prism workflow 从 7465 行降到约 4300 行，消除同构复制与规约重复，让"改一条链契约/一条规约"从 3-13 处降到 1 处，且**输出质量不降**。

**Architecture:** 六个互相独立的闭环（W-A~W-F），每个一个 commit、可单独 review、可单独 `git revert`。核心手法三条：① 同构文档抽公共骨架 + type 卡（W-A/W-B）；② 重复规约反链化到唯一权威处（W-D）；③ 把"分步 how"换成"目标 + 机械闸门"（W-E）。所有改动**默认零行为变更**——凡会改变 LLM 实际执行动作的，单独列入「行为变更清单」等用户逐条批准，不夹带进重构 commit。

**Tech Stack:** Markdown workflow 文档 + Python CRUD 脚本（`prism/scripts/*.py`）+ pytest + git。无新依赖。

## Global Constraints

以下约束对**每个 Task** 都生效，逐字照抄自 `docs/superpowers/specs/2026-08-24-prism-workflow-simplification-design.md` Part 4：

- **禁止动**：脚本零 LLM 调用原则；6 环链的因果序与每环【必带硬落地】语义；双轴 gap 解耦（B=`addresses` / A=`rings`）；闭环键 = task/文档身份（禁 K# 撮合）；sidecar 严格 schema 与字段名；file-first `outputs_state`；primer-first + 独立 critic 不可省 + `primer_quality_gate`；三个思考产物本体（`baseline_knowledge` / `thesis_v{N}` / `decomposition_v{N}`）；`DESIGN.md §1.6` 表里的 8 条真闸门。
- **stage 常量不可改**：`00-init` / `01-roadmap`(+`-pending`/`-reopen`) / `02-gather-materials` / `03-extracting` / `00-quality-screen` / `04-synthesizing` / `04-post-synthesis` / `05-critic-review` / `done` / `quarantined`。web 进度条（`topic.py:STAGE_PHASE_NAMES`）与 5 处 gate 依赖它们。
- **压缩硬规约前必须逐条分类**：每条"禁止 X / 必跑 Y"只能落进三类之一——(a) 仍在主线原文；(b) 已压成反链且**点名**兜底闸门；(c) 无兜底 → 原文保留。落不进任何一类就**不动它**。
- **venv 硬约定不得改写**：凡 import `requests`/`pymupdf`/`akshare`/`yfinance` 的命令一律 `./.venv/bin/python`；纯 CRUD 才可裸 `python3`。
- **归档不改**：`prism/specs/*.md`、`docs/superpowers/specs|plans/*`（除本计划）、`prism/topics/**` 是**带日期的历史快照**，其中对旧文件名/行号的引用属于当时事实，**不回填、不修正**。
- 每个 commit 消息末尾加：`Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
- 动脚本前跑 `impact({target, direction:"upstream"})`；提交前跑 `detect_changes()`（CLAUDE.md 要求）。

---

## 交付顺序与依赖

```
W-A (case 路径去重) ──→ W-B (选拔 spec 去重) ──→ W-C (01+02 合并)
   │                        │                        │
   └──→ W-F (产物瘦身) ─────┴──→ W-D (规约反链化) ───┴──→ W-E (00 目标化)
```

- **W-A 必须最先**：W-B/W-D/W-E 都要往它建立的 `_case_chain.md` / type 卡结构里写反链。
- **W-D 依赖 W-A + W-B + W-F**：反链的目标位置由前三者定稿。
- **W-E 最后**：唯一需要真 topic 试跑验收的一项。
- W-F 可与 W-B 并行（互不触碰同一文件）。

## 文件结构总览（改造后）

| 路径 | 职责 | 行数（现→后） |
|---|---|---|
| `prism/workflows/04-synthesize/_case_chain.md` | **新建**。三类 type 共用的链骨架：定位/元方法/分工不变式/跨层护栏/Step 0-3.4/Step 5 收尾/Step 6 critic 骨架/汇报骨架 | — → ~235 |
| `prism/workflows/04-synthesize/_type_company.md` | **新建**。company 卡：元目标 + 6 环 + Step 0.5 红线门控 + 财务/macro 取数 + sidecar key + critic 特化 + 汇报模板 | — → ~140 |
| `prism/workflows/04-synthesize/_type_industry.md` | **新建**。industry 卡（同上，含🎯目标达成核对 + 强制重修订门） | — → ~125 |
| `prism/workflows/04-synthesize/_type_arena.md` | **新建**。arena 卡（同上） | — → ~120 |
| `prism/workflows/04-synthesize/_case_reference.md` | **新建**。三份旧文件的「附：与旧路径关系」+「附录 A0/A1.3/A1.4/A附」归集，执行时不读 | — → ~95 |
| `_company_case.md` / `_industry_funnel.md` / `_arena_funnel.md` | **删除**（git 历史保留） | 1037 → 0 |
| `_child_stub.md` | **新建**（W-B）。建子 topic stub + 继承父 thesis_v0，唯一差异是 child type | — → ~60 |
| `_arena_select_spec.md` / `_peer_matrix_spec.md` | 只留评分维度 + sidecar schema，stub 段移出 | 418 → ~280 |
| `01-build-roadmap.md` → `01-gather.md` | **改名+合并**（W-C）。roadmap 计划 + 自动收料 + 登记 + 一处闸门 | 634 → ~380 |
| `02-gather-materials.md` | **删除**（W-C）。独占价值已在 `03` Step 0 的 inline 02 + 幂等 `register_inbox_materials` | 384 → 0 |
| `00-research-topic.md` | 主线目标化（W-E） | 876 → ~280 |
| `_00_reference.md` | **新建**（W-E）。00 的 query 措辞规范/字段清单/盖戳判定表/inline 示例/历史教训 | — → ~300 |
| `04-synthesize/_shared.md` | 删 `_synthesis_brief` 段（W-F）、去 decomposition 双持久点（W-F）、反链化（W-D） | 485 → ~380 |

---

## Task 1: 建立覆盖回归闸门（W-A 的"测试先行"）

文档重构没有单测，替代物是**原子覆盖闸门**：把三份旧文件里"必须保住的东西"机械抽成清单，改造后逐条 grep 新文件集，缺一条即失败。

**Files:**
- Create: `prism/scripts/wa_coverage_check.sh`（临时工具，W-A commit 后删）
- Read: `prism/workflows/04-synthesize/_company_case.md` / `_industry_funnel.md` / `_arena_funnel.md`

**Interfaces:**
- Produces: `/tmp/wa_baseline.txt`（原子清单，格式 `SYM|REF|HARD <atom>`）；`wa_coverage_check.sh <新文件...>` 退出码 0=全覆盖、1=有缺失并打印缺失项。后续 Task 2-6 每步都跑它。

- [ ] **Step 1: 写抽取+校验脚本**

```bash
cat > prism/scripts/wa_coverage_check.sh <<'EOF'
#!/bin/zsh
# W-A 覆盖回归闸门：确认三份旧 case 路径里的"原子"在新文件集里一个不少。
# 用法：
#   ./prism/scripts/wa_coverage_check.sh --baseline          # 生成 /tmp/wa_baseline.txt
#   ./prism/scripts/wa_coverage_check.sh <新文件...>          # 校验覆盖
set -e
cd "$(dirname "$0")/../.."
OLD=(prism/workflows/04-synthesize/_company_case.md
     prism/workflows/04-synthesize/_industry_funnel.md
     prism/workflows/04-synthesize/_arena_funnel.md)
# 忽略清单：json.dumps 的 kwarg（非 prism 符号）+ 被替换掉的三个旧文件名自引用
IGNORE='ensure_ascii|_company_case\.md|_industry_funnel\.md|_arena_funnel\.md'

extract() {
  cat "$@" > /tmp/_wa_all.txt
  grep -ohE '\b(set|get|mark|list|read|write|register|validate|detect|build|format|ensure|resolve|append|update|create|next|primer|empty|pending|verify|extract|record|latest|find)_[a-z_]+' /tmp/_wa_all.txt \
    | sort -u | sed 's/^/SYM /'
  grep -ohE '`[_A-Za-z0-9./-]+\.(md|yaml|py)`|\[\[[_a-z0-9-]+\]\]' /tmp/_wa_all.txt \
    | tr -d '`' | sort -u | sed 's/^/REF /'
  grep -ohE '^(- )?【必带硬落地[^】]*】.{0,24}|^  ?[0-9]\. \*\*[^*]{4,30}\*\*|^- \*\*【[^】]+】\*\*.{0,20}' /tmp/_wa_all.txt \
    | sed 's/[[:space:]]\+/ /g' | sort -u | sed 's/^/HARD /'
}

if [[ "$1" == "--baseline" ]]; then
  extract "${OLD[@]}" | grep -vE "$IGNORE" > /tmp/wa_baseline.txt
  echo "baseline: $(wc -l < /tmp/wa_baseline.txt) atoms → /tmp/wa_baseline.txt"
  exit 0
fi

[[ -f /tmp/wa_baseline.txt ]] || { echo "先跑 --baseline"; exit 2; }
cat "$@" > /tmp/_wa_new.txt
missing=0
while IFS= read -r line; do
  atom="${line#* }"
  grep -qF -- "$atom" /tmp/_wa_new.txt || { echo "MISSING  $line"; missing=$((missing+1)); }
done < /tmp/wa_baseline.txt
if (( missing > 0 )); then
  echo "❌ $missing / $(wc -l < /tmp/wa_baseline.txt) atoms 缺失"
  exit 1
fi
echo "✅ 全部 $(wc -l < /tmp/wa_baseline.txt) atoms 覆盖"
EOF
chmod +x prism/scripts/wa_coverage_check.sh
```

- [ ] **Step 2: 生成基线并确认原子数合理**

Run: `./prism/scripts/wa_coverage_check.sh --baseline`
Expected: `baseline: 97 atoms → /tmp/wa_baseline.txt`（96-99 均可；SYM ~28 / REF ~30 / HARD ~39）

- [ ] **Step 3: 跑一次"红"确认闸门真会拦**

Run: `./prism/scripts/wa_coverage_check.sh prism/workflows/04-synthesize/_shared.md; echo "exit=$?"`
Expected: 大量 `MISSING` 行 + `❌ N / 97 atoms 缺失` + `exit=1`
（用一个不含这些原子的文件验证闸门不是永绿——这一步是"先跑红"）

- [ ] **Step 4: 跑一次"绿"确认闸门对旧文件自身通过**

Run: `./prism/scripts/wa_coverage_check.sh prism/workflows/04-synthesize/_company_case.md prism/workflows/04-synthesize/_industry_funnel.md prism/workflows/04-synthesize/_arena_funnel.md; echo "exit=$?"`
Expected: `✅ 全部 97 atoms 覆盖` + `exit=0`

- [ ] **Step 5: 提交闸门**

```bash
git add prism/scripts/wa_coverage_check.sh
git commit -m "$(cat <<'EOF'
chore(prism): add W-A coverage regression gate

Mechanically extracts script symbols / file refs / hard-landing fingerprints
from the three isomorphic case-path docs so the dedup refactor can be
verified atom-by-atom instead of by eyeball.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Type 卡构造规程（Task 3/4/5 共用 · 定义一次）

每张 type 卡按同一规程构造，只是"章节来源映射"和"type 专属原子"不同（各 Task 内显式给全，不互相引用）。规程：

1. **卡头（3 行）**：
   ```markdown
   # {Type} 合成 type 卡（配 `_case_chain.md` 使用）
   > 执行顺序：先读 `_case_chain.md` 骨架（定位/分工/护栏/链因果序/Step 0/Step 2/§3.1/§3.3/§3.4/Step 5/Step 6 骨架/汇报骨架），在骨架点名"→ 见本 type 卡"处回到本卡。本卡只装 {type} 专属：元目标 + 6 环【必带硬落地】+ 取数口径 + sidecar + critic 特化 + 汇报填空。
   > SKILL 路由：`{type}` → 读 `_case_chain.md` + 本卡。
   ```
2. **§元目标**：从旧文件 §1.1 **逐字**搬来（company `_company_case.md:21-24`；industry `_industry_funnel.md:21-24`；arena `_arena_funnel.md:21-24`），逐字不改。
3. **§6 环【必带硬落地】**：从旧文件 §3.2 的六个 `**环 ①..⑥**` 块**逐字**搬来（company `:211-264`；industry `:139-188`；arena `:132-181`）。**这是 type 卡的主体，不动一字**——它承载各 type 的真实差异（三梁 / 价值链 / 卡位；company 环④有 EV 加总，industry/arena 环⑥是漏斗三档；industry/arena 环②有"定价锚×证据强度张力"硬落地而 company 没有——**保留这个差异，不强行拉平**）。
4. **§取数口径**：从旧文件 Step 1 的第 2 点（company `:124-133` 财务；industry `:92-100` 行业财务+龙头估值 2b；arena `:92-97` peer 财务+估值 2b）**逐字**搬来。company 额外含 §Step 0.5 红线门控（`:88-119` 逐字）+ macro 强制 hook（`:137-179` 逐字）。
5. **§sidecar**：从旧文件 Step 4 逐字搬（company `:277-282`；industry `:200-209`；arena `:193-202`），含 sidecar key + schema 引用 + 建 stub。
6. **§critic 特化**：从旧文件 Step 6 里**逐环 checklist 那几行**逐字搬（company `:311-330`；industry `:236-264`；arena `:229-257`）。骨架里放 critic 的通用框架（dispatch 方式/四段总评/收敛），本卡只放"逐环问什么"+ type 专属核对（industry/arena 的🎯目标达成核对 + 强制重修订门；company 的终局证据强度核对）。
7. **§汇报**：从旧文件「汇报」块逐字搬（含链体检模板）。

**铁律**：type 卡里凡是旧文件 §1.1/§3.2/Step1取数/Step4/Step6特化/汇报 的**原文**，一字不改地搬；只有指向 `_shared.md`/骨架的**框架性引用**才允许改写成"见 `_case_chain.md` §X"。

---

## Task 2: 写 `_case_chain.md`（共享链骨架）

**Files:**
- Create: `prism/workflows/04-synthesize/_case_chain.md`
- Read: `_company_case.md`（取共享段的最清晰措辞为准）+ 另两份对照

**Interfaces:**
- Produces: `_case_chain.md`，含骨架章节 §0 定位 / §1 元方法 / §2 分工不变式 / §3 跨层护栏 / §4 链因果序框架 / Step 0 前置+gap+增量 / Step 2 primer / §3.1 起点诊断框架 / §3.3 来源分层+depth / §3.4 产出形态框架 / Step 5 落盘+thesis_v1 框架 / Step 6 critic 骨架 / 汇报骨架。每个 type-specific 断点写 `→ 见 type 卡 §X`。
- Consumes: Task 1 的 `wa_coverage_check.sh`。

- [ ] **Step 1: 抽共享段落到骨架**

把下列**三份逐字一致或仅 type 名不同**的段落搬进 `_case_chain.md`（措辞歧异时取 `_company_case.md` 版为基准，type 名处写 `{本 type}`）：
- §1.2 primer↔case 分工的**硬规约原则**（"primer=教科书级背景 / case①=已假定读过 primer 的决策速写、不重教、需深度写详见 primer / 例外：用户跳过 primer 则 case① 退回自带压缩版"）。分工表的"读者/干什么"单元格改成一行："读者与'干什么'按 type，见各 type 卡卡头"。
- §1.3 跨层复用质量护栏 4 点（`_company_case.md:66-75` 为基准；industry/arena 的"父/子 topic"泛化措辞并入括注）。
- §1.4 决策链 6 环的**因果序 ASCII + "必须按序、不允许断链"** 那段框架（保留 ASCII 但环内描述用"见本 type 卡环 X"占位——ASCII 骨架三份结构相同，各 type 的环名细节在卡里）。
- Step 0 前置检查+gap 双轴+增量判定（`_company_case.md:78-87`，"company 路径 output_key" → "本 type 路径 output_key 见 type 卡"）。
- Step 2 先出 primer（`:183-194`，原材料 list → "见 type 卡取数 §"）。
- §3.1 起点诊断框架（`:199-204`，命门 delta 引 `_shared.md`）。
- §3.3 来源分层 + depth 降级（`:265-270`；company 专属的"估值模型库"bullet **不进骨架**，留 company 卡）。
- §3.4 产出形态（`:271-276`，case key + "无论几份"checklist → "见 type 卡"）。
- Step 5 落盘 + thesis_v1 Scheme C + decomposition_v1 + 终态报告（`:285-310`；output key 列表 → "见 type 卡 §sidecar"）。
- Step 6 critic 骨架（`:311-330` 的 dispatch 方式/只读不写/四段总评/收敛/`05` 分工——**逐环问什么**移 type 卡）。
- 汇报骨架（结构，链体检模板占位 → type 卡）。

- [ ] **Step 2: 骨架内所有 type-specific 断点标注 `→ 见 type 卡`**

确认骨架里凡涉及"元目标/6环内容/取数/sidecar key/critic逐环/汇报填空"处都是指针而非实体，`grep -n '见 type 卡\|见本 type' _case_chain.md` 应有 ≥8 处。

- [ ] **Step 3: 骨架自查行数**

Run: `wc -l prism/workflows/04-synthesize/_case_chain.md`
Expected: 210-260 行

- [ ] **Step 4: 不单独提交**（骨架无 type 卡不可执行，与 Task 3-5 同一 commit，见 Task 7）

---

## Task 3: 写 `_type_company.md`

**Files:**
- Create: `prism/workflows/04-synthesize/_type_company.md`
- Read: `_company_case.md`（全文，逐字搬 type-specific 段）

**Interfaces:**
- Consumes: `_case_chain.md`（Task 2）。
- Produces: company type 卡。type 专属原子必须保住：`get_quality_screen_data` / Step 0.5 红线门控表 / `ensure_financials` / `get_financial_context` / `write_macro_stamp` / `read_transmission_map` / `latest_evaluation` / `register_holding_row` / 环①三梁 / 环④ EV 加总 / 环⑥ position_tier / `07_decision_kit.yaml` / `_decision_kit_spec.md` / 终局证据强度核对。

- [ ] **Step 1: 按「Type 卡构造规程」建 company 卡**

来源映射（逐字搬，勿改）：卡头 → 规程①；§元目标 ← `_company_case.md:21-24`；§Step 0.5 红线门控 ← `:88-119`；§取数（财务）← `:121-182`（含 macro 强制 hook 全段）；§6 环 ← `:211-264`；§sidecar ← `:277-282`；§critic 特化 ← `:311-330` 逐环问句 + 终局证据强度核对；§汇报 ← `:331-346`。

- [ ] **Step 2: 覆盖闸门校验（骨架+company 卡 应覆盖 company 全部原子）**

Run: `./prism/scripts/wa_coverage_check.sh prism/workflows/04-synthesize/_case_chain.md prism/workflows/04-synthesize/_type_company.md prism/workflows/04-synthesize/_type_industry.md prism/workflows/04-synthesize/_type_arena.md 2>&1 | tail -5`
（本步只要求 company 相关原子不缺；industry/arena 卡此刻可能空/半成——若报 industry/arena 原子缺失属预期，Task 4/5 补。company 专属原子如 `get_quality_screen_data`/`register_holding_row` 必须已 ✅）
Expected: 无 `get_quality_screen_data`/`ensure_financials`/`write_macro_stamp`/`07_decision_kit` 的 MISSING 行

- [ ] **Step 3: 不单独提交**（与 Task 2/4/5/6 同 commit）

---

## Task 4: 写 `_type_industry.md`

**Files:**
- Create: `prism/workflows/04-synthesize/_type_industry.md`
- Read: `_industry_funnel.md`（全文）

**Interfaces:**
- Produces: industry type 卡。type 专属原子必须保住：`get_peer_comparison_data_by_tickers` / `get_valuation_context_by_tickers` / F13 硬 checkpoint（拉不到要 log）/ 环②"定价锚×证据强度张力" / 环④ 6 维评分 / 环⑥ 三档分流+tier=吸引力×定价 / `industry_to_arenas.yaml` / `_arena_select_spec.md` / arena stub / 🎯目标达成核对 / 强制重修订门 / "与 company EV 的刻意差异"。

- [ ] **Step 1: 按「Type 卡构造规程」建 industry 卡**

来源映射（逐字搬）：§元目标 ← `_industry_funnel.md:21-24`；§取数 ← `:89-110`（行业财务 + 龙头估值 2b + F13 checkpoint 全段）；§6 环 ← `:139-188`（含环②定价锚×证据强度硬落地）；§sidecar ← `:200-209`（09 sidecar + 写完即自检 composite↔评级同向 + arena stub）；§critic 特化 ← `:236-264`（逐环问句 + 🎯目标达成核对 + 🔒终局证据强度 + 强制重修订门全段）；§汇报 ← `:265-280`。

- [ ] **Step 2: 覆盖闸门校验（industry 原子）**

Run: `./prism/scripts/wa_coverage_check.sh prism/workflows/04-synthesize/_case_chain.md prism/workflows/04-synthesize/_type_*.md 2>&1 | grep -E 'get_peer_comparison|arena stub|industry_to_arenas|目标达成|MISSING' | head`
Expected: 无 industry 专属原子 MISSING

- [ ] **Step 3: 不单独提交**

---

## Task 5: 写 `_type_arena.md`

**Files:**
- Create: `prism/workflows/04-synthesize/_type_arena.md`
- Read: `_arena_funnel.md`（全文）

**Interfaces:**
- Produces: arena type 卡。type 专属原子必须保住：`get_peer_comparison_data_by_tickers` / `_peer_matrix_spec.md` / 环②"定价锚×证据强度" / 环④ peer 横比矩阵 + K# 校准 / 环⑥ shortlist 三档 / `peer_matrix.yaml`（score 1-5 制）/ company stub / 🎯目标达成核对 / 强制重修订门。

- [ ] **Step 1: 按「Type 卡构造规程」建 arena 卡**

来源映射（逐字搬）：§元目标 ← `_arena_funnel.md:21-24`；§取数 ← `:89-103`（peer 财务 + 估值 2b + F13）；§6 环 ← `:132-181`；§sidecar ← `:193-202`（10 sidecar，score 1-5 制 + 自检 + company stub）；§critic 特化 ← `:229-257`；§汇报 ← `:258-273`。

- [ ] **Step 2: 覆盖闸门校验（全量必须全绿）**

此时四个新文件齐了，跑全量：
Run: `./prism/scripts/wa_coverage_check.sh prism/workflows/04-synthesize/_case_chain.md prism/workflows/04-synthesize/_type_company.md prism/workflows/04-synthesize/_type_industry.md prism/workflows/04-synthesize/_type_arena.md; echo "exit=$?"`
Expected: `✅ 全部 97 atoms 覆盖` + `exit=0`。**任何 MISSING 都要回对应 Task 补齐，不许放行。**

- [ ] **Step 3: 附录归集到 `_case_reference.md`**

把三份旧文件的「附：与旧路径关系」+「附录 A0 / A1.3 / A1.4 / A附」搬进新建 `_case_reference.md`（执行时不读的历史/rationale）。company `_company_case.md:347-393`；industry `:281-324`；arena `:274-317`。三份 A附（与旧 8 份对照表）合并去重成一份。

- [ ] **Step 4: 不单独提交**

---

## Task 6: 改跨仓引用 + SKILL 路由 + DESIGN

**Files:**
- Modify: `.claude/skills/prism/SKILL.md`（合成路由行）
- Modify: `prism/DESIGN.md`（§描述行 + Part 3 §3.3 首句）
- Modify: `prism/workflows/04-synthesize/_shared.md`（`:5` 头注 + `:226` 决策链引用 + `:394-395`）
- Modify: `prism/workflows/04-synthesize/00-primer.md`（`:4` 三类路径 Step 2 引用）
- Modify: `prism/workflows/04-synthesize/_macro_regime.md`（`:3` 同胞并列 + `:77` §1.3 护栏引用 + `:420` 对照表）
- Modify: `prism/workflows/04-synthesize/_valuation_models.md`（`:4` 被谁引用）
- Modify: `prism/workflows/04-synthesize/_decision_kit_spec.md` / `_arena_select_spec.md` / `_peer_matrix_spec.md`（各 `:3` 头注里对旧文件名的引用）
- Modify: `prism/workflows/_input_contract.md`（`:4` 回溯引用）

**Interfaces:**
- Consumes: 新文件名 `_case_chain.md` + `_type_{company,industry,arena}.md`。
- 规则：外部引用旧**文件名** → 指向 type 卡（type 专属锚如 §1.1/Step1/Step4/Step6）或 `_case_chain.md`（共享锚如分工/护栏/Step0/Step5）。**归档类文件（`prism/specs/*`、`docs/**` 除本计划、`prism/topics/**`）一律不动**（Global Constraints）。

- [ ] **Step 1: 列出所有活跃引用点**

Run:
```bash
grep -rln "_company_case\|_industry_funnel\|_arena_funnel" \
  prism/workflows prism/DESIGN.md .claude/skills/prism/SKILL.md prism/scripts \
  2>/dev/null
```
Expected: 上面 Files 列表那些文件（+ `input_contract.py` docstring / `market_data.py` / `financial_data.py` 注释——脚本注释按需改，不改行为）。

- [ ] **Step 2: SKILL.md 合成路由改为"骨架 + type 卡"**

`.claude/skills/prism/SKILL.md` 合成行：`company → _company_case.md` 等三处 → `company → _case_chain.md + _type_company.md`；industry/arena 同理；macro 不变。

- [ ] **Step 3: 逐文件改引用**（按 Files 列表，共享锚→`_case_chain.md`、type 锚→type 卡）

- [ ] **Step 4: 确认无活跃悬空引用**

Run: `grep -rln "_company_case\.md\|_industry_funnel\.md\|_arena_funnel\.md" prism/workflows .claude/skills prism/DESIGN.md 2>/dev/null`
Expected: 空（活跃文档不再引用旧文件名；归档文件不在此范围）

- [ ] **Step 5: 不单独提交**（与 Task 7 删旧文件同 commit）

---

## Task 7: 删旧文件 + 全量回归 + 提交 W-A

**Files:**
- Delete: `_company_case.md` / `_industry_funnel.md` / `_arena_funnel.md`
- Delete: `prism/scripts/wa_coverage_check.sh`（闸门用完即弃）

- [ ] **Step 1: 删旧三文件前最后跑一次全量覆盖（对新文件集）**

Run: `./prism/scripts/wa_coverage_check.sh prism/workflows/04-synthesize/_case_chain.md prism/workflows/04-synthesize/_type_company.md prism/workflows/04-synthesize/_type_industry.md prism/workflows/04-synthesize/_type_arena.md prism/workflows/04-synthesize/_case_reference.md; echo "exit=$?"`
Expected: `✅ 全部 97 atoms 覆盖` + `exit=0`

- [ ] **Step 2: 删旧文件**

```bash
cd /Users/mark/investing
git rm prism/workflows/04-synthesize/_company_case.md \
       prism/workflows/04-synthesize/_industry_funnel.md \
       prism/workflows/04-synthesize/_arena_funnel.md
```

- [ ] **Step 3: 脚本层无回归（脚本没动，跑 04 相关单测确认）**

Run: `.venv/bin/python -m pytest prism/scripts/test_outputs.py prism/scripts/test_gap_detector.py -q`
Expected: 全 PASS（W-A 只动文档，脚本行为不变——这步是"没误伤脚本"的证据）

- [ ] **Step 4: 人读三类各一份的执行连贯性**

对 company / industry / arena 各挑一个已完成 topic（如 `us-micron-mu` / `global-glp1-obesity` / `cn-pd1-vegf-bispecific`），**按新的"读 `_case_chain.md` + type 卡"顺序走一遍纸面执行**，确认：① 6 环硬落地一条不少；② 取数口径对；③ sidecar key 对；④ 没有指向已删文件的死链。把结论写进 commit 消息。

- [ ] **Step 5: 删闸门脚本 + 提交**

```bash
git rm prism/scripts/wa_coverage_check.sh
git add prism/workflows/04-synthesize/_case_chain.md \
        prism/workflows/04-synthesize/_type_company.md \
        prism/workflows/04-synthesize/_type_industry.md \
        prism/workflows/04-synthesize/_type_arena.md \
        prism/workflows/04-synthesize/_case_reference.md \
        prism/workflows/04-synthesize/_shared.md \
        prism/workflows/04-synthesize/00-primer.md \
        prism/workflows/04-synthesize/_macro_regime.md \
        prism/workflows/04-synthesize/_valuation_models.md \
        prism/workflows/04-synthesize/_decision_kit_spec.md \
        prism/workflows/04-synthesize/_arena_select_spec.md \
        prism/workflows/04-synthesize/_peer_matrix_spec.md \
        prism/workflows/_input_contract.md \
        prism/DESIGN.md .claude/skills/prism/SKILL.md
git commit -m "$(cat <<'EOF'
refactor(prism): dedup 3 case-path docs into chain skeleton + type cards (W-A)

_company_case/_industry_funnel/_arena_funnel (1037 lines, 100% isomorphic at
heading level) → _case_chain.md (shared contract) + _type_{company,industry,
arena}.md (per-type meta-goal + 6-ring hard-landings + fetch + sidecar +
critic) + _case_reference.md (rationale/appendices). Zero behavior change:
verified atom-by-atom via coverage gate (97/97), per-type ring content copied
verbatim (no cross-type flattening), paper-walked micron/glp1/pd1-vegf.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6: detect_changes 回归对比**

Run: `detect_changes({scope:"compare", base_ref:"main"})`（GitNexus MCP）
Expected: 只影响 workflow 文档，不触及脚本符号/执行流。

---

# W-B ~ W-F（闭环级计划 · 各自执行前展开为 bite-sized 任务）

> W-A 已是可直接执行的 bite-sized 任务。W-B~W-F 在此给**闭环级计划**（目标/文件/步骤骨架/验收）；轮到某闭环时，先按 writing-plans 展开为逐步任务再执行——因为它们的精确改法依赖 W-A 定稿后的骨架/type 卡位置。**每个闭环沿用 W-A 的三条通用手法：先建覆盖闸门（列本闭环"必须保住的原子"）→ 改 → 原子逐条校验 + 单测 + detect_changes → 单独 commit。**

---

## W-F: 中间产物瘦身（低风险 · 可与 W-B 并行）

**Goal:** 退休/降级 4 个零机器消费者的产物，去掉 decomposition 双持久点。

**Files & 动作:**
- `_synthesis_brief` **退休**：`_shared.md` 调度模式第 4 步（`:220` 附近"写 `outputs/_synthesis_brief.md`"）改为"对话内 dump v0→v1 强度校准，不落盘"；type 卡取数 §里的"写 `_synthesis_brief`"同步删；`prism/scripts/outputs.py` 的 `read_synthesis_brief_html`(`:961`) + `app/routes/prism.py:710` + `app/templates/prism/diagnostics.html:147` 三处消费端删（诊断页去掉该块）。**验收**：`grep -rn _synthesis_brief prism/workflows prism/scripts app` 仅剩历史/注释；`pytest test_outputs.py` 绿。
- `08_living_feed` **降级纯人读**：`monitor.py` 的 append 保留（人读日志有价值）；从 `_DECISION_CHAIN_OUTPUTS`(`topic.py:27-29`) 移除 `08_living_feed`，使其不再作增量源/不进 outputs_state 死槽。**⚠️ 这动 stage/outputs 注册表，属承重墙边缘**——需 `impact({target:"_DECISION_CHAIN_OUTPUTS"})` + 跑 `test_outputs.py`/`test_gap_detector.py`，确认 `list_affected_outputs` 不因缺 key 报错。若风险 HIGH 则**只改文档不改注册表**（保守退路）。
- `_prism_reading_guide` **停 per-topic 复制**：`00-primer.md:2.5`(`cp` 那步) 删；web 端（`app/routes/prism.py` 输出页）统一渲染 `_reading_guide_canonical.md`。**验收**：新 topic 不再生成该文件、web 详情/产出页仍显示阅读指南。
- `decomposition` **去双持久点**：`_shared.md` §B 轴 delta 重拆里"delta 空即可 `set_decomposition(version=1)`"的早写口（`:104` 一带）删，统一到收尾 Step 5 落盘（对齐 workflow-flow-review A6，**注意**：A6 曾被用户回退过，执行前先跟用户确认这次是否要做）。

**验收总纲:** 4 项各自 `grep` 消费端归零 + 相关 pytest 绿 + web 手检一页。**质量影响 0**（全是零机器消费者或纯位置移动）。

---

## W-B: 两张选拔 spec 去重

**Goal:** `_arena_select_spec.md`(181) + `_peer_matrix_spec.md`(237) 的"建 stub + 继承父 thesis"同构段抽成 `_child_stub.md`。

**Files:**
- Create `_child_stub.md`（~60 行）：`create_topic(topic_type={child}, parent_topic, [ticker])` → 收窄父 K# 到子视角 → 写 stub `thesis_v0.md` 强度父级 -1。唯一参数差异是 `child_type`（arena→company / industry→arena）与是否带 ticker。逐字取 `_arena_select_spec.md:49-117`（Step 6/6b）或 `_peer_matrix_spec.md:173-200`（Step 7/7b）为基准，参数化 child type。
- Modify `_arena_select_spec.md`：删 Step 6/6b，留 Step 3（6 维评分）+ Step 6.5（sidecar schema）+ 一行"建 stub 见 `_child_stub.md`（child=arena）"。
- Modify `_peer_matrix_spec.md`：删 Step 7/7b，留 Step 3/4（财务横比）+ Step 6.5（sidecar schema）+ 一行"建 stub 见 `_child_stub.md`（child=company, 带 ticker）"。
- Modify type 卡 industry/arena 的 §sidecar 里对 Step 6/6b·7/7b 的引用 → 指 `_child_stub.md`。

**验收:** 覆盖闸门（列两 spec 的 stub 相关原子：`create_topic`/`parent_topic`/继承 thesis_v0/强度父级-1）全绿；`grep` 确认 stub 逻辑只剩一处；sidecar schema 一字未动（dashboard 硬契约）。**质量影响 0**。

---

## W-D: 硬规约反链化（跨全 workflow）

**Goal:** 落地 2026-06-16 自审 B1-B5（当时只问未做）。每条重复规约收敛到唯一权威处 + 各调用点一行反链。

**权威处 → 调用点映射（先建"规约原子清单"当闸门）:**
- **产即收**（13 处）→ 权威 `_autofetch_protocol.md`；调用点改"按 autofetch 产即收规约（详见 `_autofetch_protocol.md`）"+ 本步作用域一行。
- **闭环键=文档身份**（6 处）→ 权威 `_autofetch_protocol.md`「闭环键」节；调用点一行反链。
- **auto-fetch 三阶梯**（00/01/02 三处近同文本）→ 权威 `_autofetch_protocol.md`；三处留"作用域说明"+ 反链。（W-C 后 02 已删，实际剩 00/01 两处 + type 卡即兴 web-search。）
- **gap 诊断不是 gate**（3 处）→ 权威 `DESIGN.md §1.6`；调用点一句"gap 是诊断非 gate（理念见 DESIGN §1.6），跳过=把薄弱留给下游"。
- **primer↔case 分工**（6 处）→ 已在 W-A 收敛进 `_case_chain.md §2`；确认无残留重复。

**逐条安全分类（Global Constraints 第 3 条 · 这是 W-D 唯一风险点）:** 每条压缩前对照 `DESIGN.md §1.6` 真闸门表，标 (a) 主线保留 / (b) 反链+点名兜底闸门 / (c) 无兜底原文留。**产出一张分类表进 commit 消息**。无兜底的（如 "dispatch prompt 绝不提写权限/hook/失败兜底"——`subagent-write-hallucination`，无脚本可拦）**原文保留**。

**验收:** 规约原子清单全绿（每条规约的**关键判定句**仍可 grep 到，只是从 N 处变 1 处权威 + N 个反链）；分类表每条落进 (a)/(b)/(c)；全 workflow 文档 `grep` 反链目标文件均存在。**质量影响 0**（前提是逐条分类不偷懒）。

---

## W-C: 01 + 02 合并为「收料」workflow

**Goal:** `01-build-roadmap.md`(634) + `02-gather-materials.md`(384) → `01-gather.md`(~380)；`02` 删。

**依据（已核实）:** 02 开头自述"从 01 推进过来则 Step 0-4 大概率全跳过"；02 独占价值（用户中途上传料登记 + mineru）已在 `03` Step 0 的 inline 02 完整实现 + `register_inbox_materials` 幂等；同源硬闸门（`pending_unfetched_todos`+`verify_empty_todos_searched`）在 00/01/02 写了三遍。

**Files:**
- Create `01-gather.md`：roadmap 计划（原 01 Step 1-4）+ 自动收料阶梯（原 01 Step 5.5/5.6，反链 `_autofetch_protocol`）+ 登记（含 `register_inbox_materials` + mineru，吸收 02 的独占部分）+ **一处** auto-fetch 全覆盖闸门（原 01 Step 5.8 = 02 Step 6 同源，只留一份）+ roadmap→thesis 闭环校验（原 01 Step 5.7）+ prescan（原 01 Step 8）。
- Delete `02-gather-materials.md`。
- **stage 语义（承重墙 · 最谨慎）**：`01-gather` 跑完，`unprocessed_actionable>0` → 推 `03-extracting`；否则停 `02-gather-materials`（**stage 常量保留**）等用户上传，用户"推进"直接进 `03`（03 Step 0 已能 inline 登记）。**必须 `impact` 检查 `next_stage`/`STAGE_PHASE_NAMES`/web 进度条对 `02-gather-materials` 的依赖**，确认删的是 workflow 文件不是 stage。
- Modify SKILL.md 路由「推进 {slug}」stage→workflow 映射：`02-gather-materials` → `01-gather.md`。
- Modify `03-extract-findings.md` 里"退回 02"的措辞 → "回 `01-gather.md`"。

**验收:** 覆盖闸门（列 01+02 的必保原子：三个闸门谓词、`register_inbox_materials`、mineru 批转、roadmap→thesis 校验）全绿；`pytest`（web_prescan/gap/outputs 相关）绿；**拿一个 `02-gather-materials` stage 的真 topic 纸面走一遍**确认收料+登记+闸门不缺；`impact` 确认 stage 常量无代码依赖被破坏。**质量影响 0；风险=stage 语义**，故列 W-C 为倒数第二、W-E 之前。

---

## W-E: 00 从"18 步"改成"4 幕 + 验收断言"（唯一需真跑验收）

**Goal:** `00-research-topic.md`(876) 主线 → ~280 行（4 幕 + 每幕机械验收断言）；细节沉 `_00_reference.md`。

**手法（用系统自己验证过的模式）:** 借 primer/case 的"给元目标 + 自由发挥 + 独立 critic/机械闸门校验"搬到入口。主线只留：幕（①立框 ②认知+校准 ③下注+拆解 ④收料）→ 每幕的**产物** → **验收断言（一行脚本）**。

**Files:**
- Modify `00-research-topic.md`：主线保留 4 幕 + 5 个产物 + 验收断言。**脚本闸门一个不删**：`create_topic` 的 ticker/short_name/search_terms raise、`check_prescan_health` 三态、`set_thesis(force_failed)`、Step 6.5e 双闸门（`pending_unfetched_todos`+`verify_empty_todos_searched`）。
- Create `_00_reference.md`：query 措辞规范、baseline 五段模板细节、字段清单、盖戳判定表、inline 示例、附录 A 全部历史教训。
- 现有"附录 A"（`:391+`）→ 移入 `_00_reference.md`。

**验收（用户已选：新 topic 试跑 + 逐条断言对比）:**
1. 覆盖闸门：00 的所有脚本闸门符号 + 三思考产物写盘调用，一个不少（grep 全绿）。
2. **真跑**：拿一个未研究标的用新 00 跑一遍，与既有同类 topic 逐条对比四断言——① `thesis_v0` 是否落在 type 终局上；② K# 是否可证伪（非"如果失败"式）；③ `decomposition_v0` 是否带置信度 tag；④ prescan 命中率 `check_prescan_health` 是否 ≥partial。
3. 四断言任一不达标 → `git revert` 本 commit，回退到分步版，记录哪条断言退化。
4. `pytest test_build_search_queries.py test_prescan_status_h5.py` 绿。

**质量影响：唯一需实测的一项**，故排最后、带明确 revert 判据。

---

# 全局验收（六闭环全落地后）

- `cat prism/workflows/*.md prism/workflows/04-synthesize/*.md | wc -l` → 目标 ≤4400（现 7465，-41%）。
- 一次 company 跑动读入文档字节数：现 ~326KB → 目标 ≤200KB。
- 抽 company/industry/arena 各一个**新** topic 完整跑一遍，产出质量对既有同类 topic 不退化（同 W-E 的四断言 + case 6 环齐 + critic 收敛）。
- `.venv/bin/python -m pytest prism/scripts/test_*.py -q` 全绿。
- `detect_changes({scope:"compare", base_ref:"main"})` 确认执行流未被意外改动。

# 变更即质量：本计划不做的事（防 scope 蔓延）

- **不**把 industry/arena 的"定价锚×证据强度""目标达成核对"回填给 company（那是行为变更，非 W-A 去重范围；若要做，单独提案）。
- **不**改任何 sidecar schema 字段名。
- **不**删 stage 常量。
- **不**回填归档文件（specs/plans/topics）里对旧文件名的引用。
- **不**把三个思考产物合并（只瘦格式/去双持久点）。

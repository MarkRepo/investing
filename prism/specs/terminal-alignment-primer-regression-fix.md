# Primer 偏决策修复 — 入门目标性质约束 + 收料接缝对齐

> 承接 `terminal-alignment-plan.md`。经 8 个 topic thesis_v0/primer 实证，primer 越界的根因是 **terminal-alignment 把终局贯穿到了 primer 入门目标层**（系统性，opus4.8 也受影响），让入门目标混入决策性条目 → primer 按决策目标写决策内容。次要根因是**入门目标收料接缝裂缝**（概念层"同属 B 轴驱动收料"、实现层 gap_detector/01 只算 K#）。本 plan 不动 terminal-alignment 的终局对齐、不加 P# 轴、不禁写清单，仅从入门目标层治本 + 收料接缝对齐。

## Context（最终根因，经多轮实证）

### 根因 1：terminal-alignment 让 primer 入门目标偏决策（系统性，主因）

入门目标（`decomposition_v0` §三「primer 入门目标 v0」）是 primer 写作的**方向盘 + 收料源头**——它决定 primer 从素材里筛什么写什么，且软驱动背景收料。

实证对照（入门目标性质）：

| topic | 模型 | terminal-alignment | 入门目标性质 |
|---|---|---|---|
| futu/popmart | opus4.8 | 前 | 全理解性（说清/解释/区分/教方法 X 是什么）|
| cn-commercial-aerospace | opus4.8 | 后 | **混入决策性**：第 9 条「复述 arena 三档分流结论（深挖/观察/淘汰各是谁）」+ 第 4 条「判断投资含义」|
| cn-ai-compute | glm5.2 | 后 | 决策性更重：第 11 条「判断估值是否 price-in、区分消化 vs 透支」|

**关键**：opus4.8 在 terminal-alignment 后同样偏决策（commercial-aeroscape 入门目标第 9 条决策性 + primer §7 命门3/§10 三档分流章节）——**不是 glm5.2 特性，是 terminal-alignment 系统性影响**。glm5.2 只是放大程度（opus4.8 点到为止+指向 case，glm5.2 整节铺开）。

机制：terminal-alignment 的终局强制（5.0 thesis 终局立场 / 5.2 终局命门自检 / 5.4 终局环 B 靶点强制）让 LLM 写 decomposition 入门目标时也往终局带——入门目标被要求"覆盖终局"（复述 arena 分流结论）。terminal-alignment 前（futu/popmart）入门目标纯理解性；后混入决策性。

**terminal-alignment 的终局贯穿"过广"**：终局贯穿到 K#/命门/case 是对的（case 侧终局对齐正确），但贯穿到 primer 入门目标就过了——primer 入门目标是背景教学能力，不服务终局决策。terminal-alignment 没给 primer 入门目标豁免终局化。

### 根因 2：入门目标收料接缝裂缝（次要，治背景料漏收）

概念层（`decomposition §三`）说入门目标"与命门同属 B 轴、驱动背景收料"，机械自检第 4 条要求"每条入门目标排背景资料源"。但实现层：
- `gap_detector` B 轴 = **K# 脊柱**（`uncovered_ks`/`thin_evidence` 只按 K#），**不含入门目标**
- `01` Step 3 收料 B 轴只提"命门靶点"，**没显式提入门目标**

→ 入门目标的收料是**软的、一次性的**（只有 00 Step 5.4 机械自检），不进 gap 持续催收、不在 01 收料优先级显式占位。后果：①入门目标决策性时，"排资料源"会排决策料（为"判断 price-in"收估值料），系统不纠；②入门目标理解性时，背景料也可能没真正收（gap 不查），primer 背景不足。

### 否决的前几版方案（实证推翻）

- **K# 一身二职**：错。futu 实证 K# 纯终局决策，背景走 primer scope 独立通道，K# 从未一身二职。
- **弱化 5.2/5.4 终局强制**：错。根因是 primer 入门目标偏决策非终局太强；终局对齐正确保留。
- **恢复 primer scope 段强制**（前一版 plan 的 4 处 Edit）：错。primer scope 段落地率极低（6 topic 仅 futu）、不驱动收料、与越界无关、压不住决策性入门目标。已撤回。
- **正文禁写清单**：过于具体（针对 industry 环②④⑥）、违背 primer 目标导向、覆盖不全。改用入门目标性质约束（通用、目标导向）。
- **加 P# 轴**：补丁非根因 + 注意力分散。

## 设计原则

> **入门目标性质约束（含终局豁免）治方向盘；收料接缝对齐治背景料漏收；terminal-alignment 终局对齐全保留；不加 P# 轴、不禁写清单、不强制 primer scope 段。**

1. **入门目标 = 理解性/教学性能力，非决策性**：门外人"读懂这门生意"的能力（说清/解释/区分/教方法 X 是什么、理解双面性、列出信号），不是"做投资决策"的能力（复述 arena 分流结论/判断投资含义/给 stance/定 tier）——决策归 case。
2. **终局豁免**：terminal-alignment 的终局贯穿到 K#/命门/case（正确），但**不贯穿到 primer 入门目标**——入门目标豁免终局化，它服务"理解"不服务"终局决策"。
3. **收料接缝对齐**：01 B 轴显式含入门目标背景靶点（与命门靶点并列）；gap_detector 加入门目标覆盖软提示（flag-only，不像 K# 硬催收——背景料可由训练知识兜底）。
4. **terminal-alignment 不动**：1a/1b/5.0/5.2 终局命门/5.4/04 chain-critic 全保留。case 侧终局对齐正确。
5. **primer scope 段不强制**：保留 Step 5.2 原有"坍缩进 primer scope"指引（可选白名单），但不加强制自检。撤回前一版加的强制项。

## 实施

### A. 撤回前一版 4 处 Edit（`00-research-topic.md`）

恢复到 terminal-alignment 原状（删除前一版加的 primer scope 强制）：
1. **删**行 416 旁「primer scope 背景分轨自检（与终局命门对等）」整条。
2. **行 440 恢复**：「坍缩进 primer scope 背景维度清单（与 K# 对等产出，非一行备注）...」→ 恢复原文「坍缩成一行 primer scope 备注，交给 00_primer 处理，不单列编号、不进 todo addresses。」
3. **行 445 恢复**：「写进 thesis_v0.md 文件...两轨对等产出、缺一不可」→ 恢复原文「在对话里输出：① 哪些维度升成了 K#（指回 5.0）；② 一行 primer scope 备注（primer 该覆盖的背景范围）。」
4. **删**行 494「与 thesis_v0 primer scope 衔接」整条。

### B. 入门目标性质约束（主治 · `00-research-topic.md` Step 5.4 + `00-primer.md` Step 1）

**B1. `00-research-topic.md` Step 5.4 第 3 条（primer 入门目标 v0，行 492-495）加性质约束 + 终局豁免**：

在第 3 条现有内容后追加：
```
   - **性质约束（primer 回归 · 必守）**：入门目标必须是**理解性/教学性能力**（说清/解释/区分/教方法 X 是什么、理解双面性、列出可观测信号），**不得是决策性能力**（复述 arena 分流结论/判断投资含义/给 stance/定 tier）——后者归 case 决策环。
   - **终局豁免**：terminal-alignment 的终局贯穿到 K#/命门/case（正确），但**不贯穿到 primer 入门目标**。入门目标服务"门外人读懂这门生意"，不服务"做终局决策"——不得因 5.2 终局命门自检/5.4 终局环 B 靶点而把入门目标终局化（如"复述 arena 分流结论"是 case 环⑥的活，不是入门目标）。
```

**B2. `00-research-topic.md` Step 5.4 机械自检（行 496-501）加一条**：

在现有机械自检后加：
```
   - **每条 primer 入门目标是否理解性/教学性（非决策性）？**（primer 回归 · 必守）——决策性条目（复述分流结论/判断投资含义/给 stance）必须改写为理解性（"说清 X 是什么/解释 X 机理"）或剔除。终局决策归 case，不入入门目标。
```

**B3. `00-primer.md` Step 1 目标精修（行 44-49）加性质校验**：

在 Step 1「delta 校验」后加一步：
```
3. **性质校验（primer 回归 · 必守）**：逐条审入门目标性质——理解性/教学性保留；决策性（复述分流结论/判断投资含义/给 stance/定 tier）改写为理解性或剔除。入门目标是"读懂这门生意"的能力，不是"做终局决策"的能力。终局贯穿到 K#/命门/case，但不贯穿到 primer 入门目标（终局豁免）。
```

### C. 收料接缝对齐（`01-build-roadmap.md` Step 3 + 可选 `gap_detector.py`）

**C1. `01-build-roadmap.md` Step 3 B 轴（行 175）显式含入门目标**：

原文：
```
> - **B 轴（命门靶点）**：照 `decomposition_v0.md` 每环 B 靶点收料，**低置信度命门优先砸料**（对冲薄拆解风险）。
```

改为：
```
> - **B 轴（命门靶点 + 入门目标背景靶点）**：照 `decomposition_v0.md` 每环 B 靶点收料（**低置信度命门优先砸料**，对冲薄拆解风险）+ 照 §三「primer 入门目标」每条标 uncertain/缺口的收**背景料**（入门目标与命门同属 B 轴、并列驱动收料；区别是命门喂 case 决策环、入门目标喂 primer 理解地基）。**入门目标收的是背景料（产业链/机理/玩家/沿革），不是决策料——入门目标理解性约束（B1）保证这点。**
```

**C2.（可选 · 代码改动，实施时跑 `gitnexus_impact`）`prism/scripts/gap_detector.py` 加入门目标覆盖软提示**：

加入门目标覆盖检查（读 `decomposition_v0` §三入门目标，对照 manifest 背料覆盖），输出 `uncovered_primer_goals` 字段，**flag-only 不 gate**（背景料可由训练知识兜底，不像 K# 硬催收）。让入门目标背景缺口在 gap 层可见、可软提示。

> C2 是代码改动，实施前按 CLAUDE.md 跑 `gitnexus_impact({target:"detect_gaps"/"format_summary", direction:"upstream"})` 报 blast radius。若 blast radius 大或 C1 已足够，可暂缓 C2，列为后续。

## 不做（避免过度设计）

- **不动 terminal-alignment 的 5.0/5.2/5.4/04 chain-critic**：case 侧终局对齐正确，保留。
- **不禁写清单**：过于具体、违背目标导向。改用入门目标性质约束（通用）。
- **不加 P# 轴**：补丁非根因。
- **不强制 primer scope 段**：与越界无关、压不住决策性入门目标。保留原有可选指引（A 撤回强制）。
- **不弱化终局**：根因是 primer 入门目标偏决策非终局太强。

## 验证

1. **实证对照（决定性）**：
   - terminal-alignment 前 opus4.8（futu/popmart）入门目标全理解性 → primer 守边界。
   - terminal-alignment 后 opus4.8（commercial-aerospace）入门目标第 9 条决策性 → primer 偏决策（§7 命门3/§10 三档分流章节）。
   - terminal-alignment 后 glm5.2（ai-compute）入门目标第 11 条决策性 → primer 重度越界。
   - 本 plan 落地后，重跑一个 topic 的 decomposition_v0，确认入门目标全理解性（无"复述分流结论/判断 price-in"类决策条目）→ primer 守边界。
2. **case 终局对齐不损**：5.0/5.2/5.4/04 chain-critic 全保留，K#/命门/case 仍终局化。
3. **收料接缝**：01 B 轴显式含入门目标后，入门目标背景靶点进收料优先级；入门目标理解性约束保证收的是背景料非决策料。
4. **CLAUDE.md 合规**：A/B/C1 只改 workflow 文档，不动 python 符号，无需 `gitnexus_impact`；C2 改 `gap_detector.py` 前 `gitnexus_impact`。收尾 `gitnexus_detect_changes()` 确认范围。

## 改动文件清单

| 文件 | 改动 |
|---|---|
| `prism/workflows/00-research-topic.md` | A：撤回 4 处 primer scope 强制 Edit；B1：Step 5.4 第 3 条加入门目标性质约束+终局豁免；B2：机械自检加"入门目标是否理解性"条 |
| `prism/workflows/04-synthesize/00-primer.md` | B3：Step 1 目标精修加性质校验步 |
| `prism/workflows/01-build-roadmap.md` | C1：Step 3 B 轴显式含入门目标背景靶点 |
| `prism/scripts/gap_detector.py`（可选） | C2：加 `uncovered_primer_goals` 软提示（flag-only），实施前跑 `gitnexus_impact` |

## 与既有 plan 的关系

- **`terminal-alignment-plan.md`**：本 plan 是其 **primer 侧补强 + 收料接缝补**。保留其全部终局对齐（1a/1b/5.0/5.2/5.4/04 chain-critic），仅给 primer 入门目标加终局豁免 + 性质约束。不冲突。
- **否决前一版**（`terminal-alignment-primer-regression-fix.md` 的 primer scope 段强制）：实证推翻，A 撤回。
- **`workflow-audit-20260616.md` B5**（primer↔case 分工表文档重复）：正交，可独立实施。

## 关键洞察（一句话）

primer 越界的根在**入门目标层**（terminal-alignment 把终局贯穿过广，连 primer 入门目标都终局化为决策性条目），不在 primer scope 段、不在 K# 一身二职、不在正文缺禁写清单。修法是给 primer 入门目标**性质约束 + 终局豁免**（理解性非决策性，终局归 case）+ **收料接缝对齐**（01 B 轴显式含入门目标）。terminal-alignment 的终局对齐本身正确，只是该在 primer 入门目标层停住。

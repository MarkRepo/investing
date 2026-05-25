# 产出合成 — 共享前置规范

每份产出工作流开始前必须完成以下检查，违反则停止并告知用户。

## 前置检查

```bash
python -c "
import json
from prism.scripts.topic import read_topic
from prism.scripts.manifest import material_count
t = read_topic('{slug}', '{variant}')
counts = material_count('{slug}')
print('stage:', t['stage'])
print('materials:', json.dumps(counts))
print('question:', t['scope']['question'])
"
```

- **资料量**：至少 3 份已处理资料，否则提示「资料不足，建议先收集更多资料」
- **训练知识依赖**：每份产出明确标注哪些来自训练知识，哪些来自资料

## 写入规范

输出文件路径：`prism/topics/{slug}/{variant}/outputs/{output_key}.md`

每份产出 markdown 必须包含：
1. YAML frontmatter（slug, output_key, version, generated）
2. 正文内容（按各 workflow 规定）
3. 末尾：`## 信息来源` — 列出使用的资料（mat_id + 文件名）和训练知识比例估计

---

## 调度模式：主 agent 直做 + 并行 Write（**默认**）

**默认走主 agent 直做模式**——主 agent 读完 findings 后直接 Write 11 份产出（01-08 + 07 sidecar yaml + thesis_v1），用 Write 工具并行批次（一次 message 发 4-5 个 Write 调用）。

### 为什么主 agent 直做（2026-05-22 改）

历史教训（feedback_subagent_bulk_synthesis）：用单 subagent 顺序模式 dispatch 11 份长产出，**两次测试都撞 60min subagent 硬上限被强杀，0 文件落盘**。原因：
1. **结构性超限**：11 份 × 400 行 markdown 的 token 输出本身就要 30-50min，加 findings 读取 + 推理 + cross-mat 校准必撞 60min 硬墙。
2. **Write 幻觉重试循环放大**（见 [[subagent-write-hallucination]]）。
3. **黑盒无可见性**：subagent stdout 不流式，前 30min 看不到进度，等发现已超时。

主 agent 直做的优势：
- **并行 Write**：一次 message 发 4-5 份产出的 Write 调用，比 subagent 串行快 3-5×
- **无 60min 硬墙**：主 agent 没有 wallclock 上限
- **无 Write 幻觉**：主 agent Write 工具可靠
- **可中途救**：每份 Write 实时落盘，断了可以接着写

### 执行步骤

主 agent 直做的标准流程：

1. **读 findings**：调 `format_findings_for_prompt` helper 列出自有 + 父级 findings 路径，主 agent 用 Read 工具**并行**读完所有未读 findings（同一 message 多 Read 调用）。
2. **读 thesis_v0**：作为强度 v0→v1 对照锚。
3. **写 _synthesis_brief.md**：先 dump K1-K5 v0→v1 强度调整结论到 `outputs/_synthesis_brief.md`，作为后续 06/07/08 的 cross-mat 校准锚。
4. **批次并行 Write 产出**：按 2-3 份一批的节奏 Write 01-08：
   - 批 1：01_business_panorama + 02_cycle_positioning + 03_narrative_ecology + 04_implied_expectations（4 份并行）
   - 批 2：05_historical_mirrors + 06_risk_blindspots + 07_decision_kit + 07_decision_kit.yaml + 08_living_feed（5 份并行）
   - 批 3：thesis_v1.md + 状态注册 Bash（2 个调用并行）
5. **状态注册**：用单个 Bash 脚本一次性注册 9 个 outputs status + thesis v1。
6. **收尾**：set_stage('04-post-synthesis') + 清空 user_todos + 更新 next_actions（指向 critic-review / daily-monitor / 中报回看）。

### 何时仍可考虑 subagent dispatch（**例外**）

仅当**全部满足**以下条件才考虑 dispatch：
- 主 agent 上下文已接近压缩边界（找回 findings 读取成本高）
- 产出份数 ≤4（单次 dispatch 总 token <30K，wallclock <40min 留 buffer）
- 任务可被切成多轮（例：先 dispatch 01-04，再 dispatch 05-08）

此时仍用"subagent 返内容、主 agent 落盘"架构：
- **subagent 只产内容、主 agent Write 落盘**——subagent 不调用 Write/Edit
- `subagent_type`: `general-purpose`
- `model`: **不传**，跟随主 agent
- `isolation`: **不传**

下面 dispatch prompt 模板**仅在例外路径**使用——默认走主 agent 直做。

subagent 返回格式（最关键）：final message 必须包含 8 个连续的 markdown 代码块，每块前用一行 `=== {output_key} ===` 标记，例如：

```
=== 01_business_panorama ===
```markdown
---
slug: ...
output_key: 01_business_panorama
...
---
（正文）
```

=== 02_cycle_positioning ===
```markdown
...
```
（依此类推到 08）

=== thesis_v1 ===
```markdown
（thesis_v1 内容）
```
```

主 agent 收到后用正则切分，依次 Write 到 `prism/topics/{slug}/{variant}/outputs/{output_key}.md`，然后写 thesis_v1.md。

### Dispatch 前准备 — 调 helper 列出所有 findings

主 agent 在 dispatch 之前先跑：

```bash
python3 -c "
from prism.scripts.findings import format_findings_for_prompt
print(format_findings_for_prompt('{slug}', '{variant}'))
"
```

输出会包含**自有 findings + 父级复用 findings**（来自 topic.yaml `parent_materials` 字段，由 workflow 01 写入）。把整段输出粘到 dispatch prompt 的 Step 0。

### Dispatch Prompt 模板

```
你被指派为 prism topic `{slug}` 的 variant `{variant}` 顺序生成 8 份产出（01-08）+ 07 sidecar yaml。

# 重要：你不要调用 Write/Edit 工具，也不要用 Bash heredoc 写文件
所有产出 markdown 必须以 `=== {output_key} ===` 标记 + ```markdown ``` 代码块的形式整体放在 final message 中。主 agent 会接收后切分落盘。

# 上下文
- Topic question: {question}
- Topic type: {topic_type}（industry / arena / company）
- 输出目录: prism/topics/{slug}/{variant}/outputs/
- 内容规范: prism/workflows/04-synthesize/{01..08}-*.md 8 份 sub-workflow 文件

# Step 1: 读所有 findings（自有 + 父级复用）
{粘贴上面 format_findings_for_prompt 的输出}

## Step 1.5: 内部做 K1-K5（或对应 thesis 钩子）校准
顺序生成 06/07/08 之前你必须先在上下文里形成 v0→v1 强度调整结论。建议把校准结论 dump 成 outputs/_synthesis_brief.md（供未来 critic-review/drilldown 复用，可选不强制）。

## Step 2-9: 按下列顺序生成 8 份产出（仅在 final message 中返，不落盘）
依次按对应 sub-workflow 规范填内容：

1. 读 prism/workflows/04-synthesize/01-panorama.md → 产 01_business_panorama
2. 读 02-cycle.md → 产 02_cycle_positioning
3. 读 03-narrative.md → 产 03_narrative_ecology
4. 读 04-expectations.md → 产 04_implied_expectations
5. 读 05-mirrors.md → 产 05_historical_mirrors
6. 读 06-risks.md → 产 06_risk_blindspots
7. 读 07-decision-kit.md → 产 07_decision_kit（同时产 07_decision_kit_yaml 用 ```yaml 块）
8. 读 08-feed.md → 产 08_living_feed
9. 产 thesis_v1（5 段：核心 thesis / 强度评分 / 支持理由 / 反方观点 / K1-K5 现状）

## 返回格式
final message 第一行：DONE 或 BLOCKED 状态行。
然后依次输出每份产出，格式如下（严格遵守）：

=== 01_business_panorama ===
```markdown
---
slug: {slug}
output_key: 01_business_panorama
version: 1
generated: {iso_date}
---

（正文 800-2000 字）

## 信息来源
- mat-xxx (filename): 用于...
```

=== 02_cycle_positioning ===
```markdown
...
```

（依此类推到 08_living_feed）

=== 07_decision_kit_yaml ===
```yaml
（07 sidecar yaml 内容）
```

=== thesis_v1 ===
```markdown
（thesis_v1 5 段内容）
```
```

主 agent 接到 DONE 后，依次调脚本更新 8 份产出的状态（见下方"更新状态"段），然后跑 _shared.md 收尾段判断是否自动触发 09/10。

---

## 单份产出更新状态（每份产出完成后必须执行）

```bash
python -c "
from prism.scripts.topic import set_output_status
set_output_status(
    slug='{slug}',
    output_key='{output_key}',
    status='fresh',
    version={new_version},
)
print('状态已更新')
"
```

## 全部产出完成后（收尾）

先更新 01-08 完成状态：

```bash
python -c "
from prism.scripts.topic import read_topic, set_next_actions, set_user_todos
t = read_topic('{slug}', '{variant}')
# 清除 user_todos 中「下一步：生成产出」相关行
todos = [x for x in t.get('user_todos', []) if '生成产出' not in x and '开始 01-08' not in x]
todos.append('全部产出完成（' + str(len(t['outputs_state'])) + ' 份），等待创建子 topic 或进入监控')
set_user_todos('{slug}', todos, '{variant}')
# 确认 next_actions 不再指向生成产出
actions = [x for x in t.get('next_actions', []) if '01-08' not in x and '产出' not in x]
set_next_actions('{slug}', actions, '{variant}')
print('收尾完成')
"
```

**写 thesis_v1（基于资料的修正版）**：

收尾时主 agent **必读** `outputs/_synthesis_brief.md`（如不存在 — 资料 <10 跳过，则直接读 06+07 合成 v1），把 K1-K5（或对应 thesis 钩子）的 v0→v1 强度调整结论 dump 到 `prism/topics/{slug}/{variant}/thesis_v1.md`。

thesis_v1.md 必须包含五段（同 thesis_v0 schema，但内容是基于 findings 的修正版）：

1. **核心 thesis（1 句话）** — 修正后的核心观点
2. **强度评分** — 整体 1-10（v0 强度 → v1 强度，明确写出变化值）
3. **支持理由** — 来自 findings 的实证（每条注 mat_id）
4. **反方观点（必写）** — findings 中浮现的对立信号（每条注 mat_id）
5. **Killer Questions K1-K5 现状** — 每条标注：`已验证支持` / `已验证反驳` / `仍未确定` + 关键 mat_id

写完调脚本登记：

```bash
python -c "
from prism.scripts.topic import set_thesis
set_thesis(
    slug='{slug}',
    variant='{variant}',
    version=1,
    summary='{修正后的核心 thesis，≤120字}',
    stage_set_at='04-post-synthesis',
)
print('thesis v1 已登记')
"
```

如果 brief 显示「v0 与 findings 完全契合，无需修正」，仍写 v1 但 summary 注明 `[与 v0 一致]`，便于后续 critic-review 锚定时点。

**自动触发扩展产出**：根据 topic type 判断是否需要自动生成 09/10：

- **topic_type = industry** → 自动运行 workflow `09-industry-to-arenas`（选拔 arena）
- **topic_type = arena** → 自动运行 workflow `10-peer-matrix`（公司对比矩阵）
- **topic_type = company** → 跳过，01-08 即为完整产出

自动触发时，直接读对应 workflow 文件（`prism/workflows/04-synthesize/09-industry-to-arenas.md` 或 `prism/workflows/04-synthesize/10-peer-matrix.md`），按 Step 执行。完成后将 stage 设为 `done` 并追加到 living feed。

**注意**：09/10 的 Tier 排序应基于 thesis_v1（不是 v0），workflow 09/10 已在 step 1 / step 2 中要求读 brief + thesis 最新版。

## 质量检验

产出完成后自问：
- [ ] 有具体数据/时间/主体，不只是泛泛之词
- [ ] 多空观点都有呈现，不只说一边
- [ ] 有明确的「哪里可能是错的」
- [ ] 训练知识和资料来源有区分标注
- [ ] 字数适当（800-2000字为宜，过长反而难用）

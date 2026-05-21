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

## 调度模式：单 subagent 顺序生成 01-08

**默认走单 subagent 顺序模式**，仅当资料数 <10 且主 agent 上下文宽裕时才考虑主 agent 直接生成。

### 为什么单 agent 顺序

8 份产出并行 dispatch 会让每个 subagent 各自加载 findings（N × 重复读取）。改成单 subagent 顺序后：
- Findings 只读一次
- 06/07/08 需要的 cross-mat 校准在 subagent 上下文里自然形成，不用主 agent 手搓
- 主 agent 上下文只回流一句 DONE，不被 8 份 markdown 撑爆
- 失败恢复：写一份落盘一份，中途断了下次从未写的接着写

### Dispatch 规约

- `subagent_type`: **必须用 `general-purpose`**。不能用 `Explore`（read-only 无 Write）、不能用 `Plan`（read-only）
- `model`: **不传**，跟随主 agent
- `isolation`: **不传**，复用主工作目录（要往 `prism/topics/{slug}/{variant}/outputs/` 落盘）

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

# Step 0 (validation, 必做): 测试 Write 权限
开头先 Write 一行 "ok" 到 outputs/.write_test 检查权限。成功立即继续；如果 Write 真被拦（极少数），返回 "BLOCKED: write tool denied" 并终止——主 agent 会接手。**不要预判 Write 会失败而把 markdown 塞回 final message——这是已知幻觉。**

# 上下文
- Topic question: {question}
- Topic type: {topic_type}（industry / arena / company）
- 输出目录: prism/topics/{slug}/{variant}/outputs/
- 内容规范: prism/workflows/04-synthesize/{01..08}-*.md 8 份 sub-workflow 文件

# Step 1: 读所有 findings（自有 + 父级复用）
{粘贴上面 format_findings_for_prompt 的输出}

## Step 1.5: 内部做 K1-K5（或对应 thesis 钩子）校准
顺序生成 06/07/08 之前你必须先在上下文里形成 v0→v1 强度调整结论。建议把校准结论 dump 成 outputs/_synthesis_brief.md（供未来 critic-review/drilldown 复用，可选不强制）。

## Step 2-9: 按下列顺序生成并直接 Write 落盘
依次按对应 sub-workflow 规范填内容、Write 落盘、不要等到最后批量写：

1. 读 prism/workflows/04-synthesize/01-panorama.md → 写 outputs/01_business_panorama.md
2. 读 02-cycle.md → 写 outputs/02_cycle_positioning.md
3. 读 03-narrative.md → 写 outputs/03_narrative_ecology.md
4. 读 04-expectations.md → 写 outputs/04_implied_expectations.md
5. 读 05-mirrors.md → 写 outputs/05_historical_mirrors.md
6. 读 06-risks.md → 写 outputs/06_risk_blindspots.md
7. 读 07-decision-kit.md → 写 outputs/07_decision_kit.md + outputs/07_decision_kit.yaml
8. 读 08-feed.md → 写 outputs/08_living_feed.md

每写完一份立即 Write 落盘，不要积累到最后。

## 返回
完成后返回一行：
DONE: 8 outputs + 07 yaml written. Brief: {written|skipped}. Issues: {none|描述}
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

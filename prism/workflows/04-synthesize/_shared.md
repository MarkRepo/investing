# 产出合成 — 共享前置规范

每份产出工作流开始前必须完成以下检查，违反则停止并告知用户。

## 前置检查

```bash
python -c "
import json
from prism.scripts.topic import read_topic
from prism.scripts.manifest import material_count
t = read_topic('{slug}', '{variant}')
counts = material_count('{slug}', '{variant}')
print('stage:', t['stage'])
print('materials:', json.dumps(counts))
print('question:', t['scope']['question'])
"
```

- **资料量**：至少 3 份已处理资料，否则提示「资料不足，建议先收集更多资料」
- **训练知识依赖**：每份产出明确标注哪些来自训练知识，哪些来自资料

## gap 体检（进 04 第一件事）

```bash
python3 -c "
from prism.scripts.gap_detector import detect_gaps, format_summary
print(format_summary(detect_gaps('{slug}', '{variant}')))
"
```

把 report 输出**完整贴到对话**。看三项：
- `uncovered_ks` 非空 → 该 K# 当前 0 条材料覆盖
- `thin_evidence` 非空 → 该 K# 证据 < 2 条
- `expired_web_materials` 非空 → web-search 材料 > 90 天

任一非空 → **不要硬合成**，否则 11 份产出全是"未充分论证"占位。先决定补救：即兴 web-search（_shared.md 末尾的"即兴 web-search"段）/ sub-agent 深挖 / 回 02 补资料。这是诊断不是 gate——脚本不会拒绝前进，但跳过等于让 05 critic 把雷踩回来。

## 增量重写判定（默认开启）

**目的**：避免 11 份产出每次都全重写——浪费 token 且让"未变章节"也升 version 引起噪声。

```bash
python3 -c "
from prism.scripts.outputs import list_affected_outputs
import json
r = list_affected_outputs('{slug}', '{variant}')
for k, v in r.items():
    print(f'{k}: {v[\"reason\"]} (+{len(v[\"new_mat_ids\"])} new mats)')
"
```

判定结果：
- `new`：从未合成 → 必须写
- `stale`：有新材料入库 → 必须重写
- `critic-stale`：critic verdict='request-rewrite' 显式标 stale（无新 mat 但 status='stale'） → 必须重写，**read critic-review 的反方论据作为补充输入**
- `fresh`：全部 mat 已纳入且未被 critic 标 stale → **跳过**

**写完每份产出后**，主 agent 必须调用以下一行注册引用：

```bash
python3 -c "
from prism.scripts.topic import set_output_referenced_mats
set_output_referenced_mats('{slug}', '{output_key}', {mat_ids_list}, '{variant}')
"
```

其中 `{mat_ids_list}` 是本份产出 frontmatter `## 信息来源` 段引用的所有 mat_id 列表。**未调用 → 下次仍判为 new/stale，浪费 token**。

### 触发全重写（绕过增量判定）

用户说「全重写所有 output」/「忽略增量」/「--full-rewrite」时，跳过 `list_affected_outputs`，对全部 9-11 份按 new 处理。常用于 thesis 大改、统一文风、修 schema 等场景。

## 断点续跑（修 9：workflow resume）

**目的**：11 份产出循环，单份失败不能阻断后续 10 份；失败要可见且可重跑。

**模式**：每份产出包在 try/except 里：

```bash
python3 -c "
from prism.scripts.topic import set_output_referenced_mats, set_output_error
try:
    # 主 agent 已用 Write 工具落盘 outputs/{output_key}.md
    set_output_referenced_mats('{slug}', '{output_key}', {mat_ids}, '{variant}')
except Exception as e:
    set_output_error('{slug}', '{output_key}', str(e), '{variant}')
    raise  # 主 agent 看到后继续下一份，不中断 11 份循环
"
```

实践上主 agent 是用 Write 直接落盘，"失败"通常是 frontmatter 引用错 mat_id / addresses 不合 _ADDR_RE / 文件被外部锁。失败时调 `set_output_error` 标记，下一份继续。

### 重跑失败的 output

```bash
python3 -c "
from prism.scripts.topic import list_failed_outputs
for f in list_failed_outputs('{slug}', '{variant}'):
    print(f'  {f[\"output_key\"]}: {f[\"last_error\"][\"message\"]} @ {f[\"last_error\"][\"at\"]}')
"
```

主 agent 把 `list_failed_outputs` 返回的 output_key 加进重跑队列；成功一份调一次 `set_output_referenced_mats` 自动抹掉 last_error。

### 不要做的事

- ❌ **不要 try/except 吞异常**：失败必须 raise，让用户在汇报里看到"X 份成功 / Y 份失败"
- ❌ **不要在中途 commit 文件**：失败应只反映在 `outputs_state.last_error`，不留半成品 markdown
- ❌ **不要重跑全部 11 份"为了清错"**：只重跑 `list_failed_outputs` 列出的

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

1. **读 findings（一次性全文加载）**：调 `format_findings_for_prompt` helper 列出自有 + 父级 findings 路径，主 agent 用 Read 工具**并行**读完所有未读 findings（同一 message 多 Read 调用）。

2. **建轻索引（防 compact 防误读）**：

   ```bash
   python3 -c "
   from prism.scripts.findings import build_findings_index
   print(build_findings_index('{slug}', '{variant}'))
   "
   ```

   落盘 `outputs/_findings_index.md`：每份 finding 一行 = `mat_id | filename | addresses=[K#] | quality/bias | 80字摘要`。22 份 ≈ 3-5K tokens，远低于全文 ~40K。**索引是主 agent 的"地图"——下面所有"按需补读"决策都基于它。**

3. **读 thesis_v0**：作为强度 v0→v1 对照锚。

4. **写 _synthesis_brief.md**：先 dump K1-K5 v0→v1 强度调整结论到 `outputs/_synthesis_brief.md`，作为后续 06/07/08 的 cross-mat 校准锚。

5. **批次并行 Write 产出 + 按需补读 finding**：按 2-3 份一批的节奏 Write 01-08：
   - 批 1：01_business_panorama + 02_cycle_positioning + 03_narrative_ecology + 04_implied_expectations（4 份并行）
   - 批 2：05_historical_mirrors + 06_risk_blindspots + 07_decision_kit + 07_decision_kit.yaml + 08_living_feed（5 份并行）
   - 批 3：thesis_v1.md + 状态注册 Bash（2 个调用并行）

   **每批次开始前必做**（廉价且重要）：

   - **Read `outputs/_findings_index.md`**（已落盘，~3K token）—— 即使中间发生过 compact，看一眼索引也能立即定位本批次需要哪些 mat_id
   - 对照本批次每份 sub-workflow 的 addresses 维度（如 06-risks → `[risk, K1, K6]`，01-panorama → `[scope, K3, K5]`），从索引筛出相关 mat_id
   - **自检**：你是否还能清晰回忆这些 mat_id 对应 finding 的内容？
     - **能** → 直接写，跳过 Read
     - **不能 / 模糊 / 想不起细节** → 单独 Read 那几份 finding 补回（不是全部 22 份，只补本批次需要的）

   **不要做的**：
   - ❌ 不要每份 sub-workflow Step 1 都 Read 全部 findings（22 × 8 = 176 次重读 ≈ 30 万 token 浪费）
   - ❌ 不要假定 findings 一定还在 context（compact 可能切掉，索引让你能验证）
   - ❌ 不要写完 01 后立即 Read 全部 findings 准备写 02——批次内并行 Write 多份，批次之间只看索引判断
6. **状态注册**：用单个 Bash 脚本一次性注册 9 个 outputs status + thesis v1。
7. **收尾**：set_stage('04-post-synthesis') + 清空 user_todos + 更新 next_actions（指向 critic-review / daily-monitor / 中报回看）。

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
9. 产 thesis_v1（4 段：① 核心 thesis + 强度评分 / ② 支持理由 / ③ 反方观点 / ④ K1-K5 现状；与 workflow 00 thesis_v0 段结构一致，**不再单列 V# 验证项段**）

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
（thesis_v1 4 段内容：核心 thesis+强度评分 / 支持理由 / 反方观点 / K1-K5）
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
python3 -c "
from prism.scripts.topic import read_topic, set_next_actions, append_user_todos
t = read_topic('{slug}', '{variant}')
# 仅 append 一条完成提示，不动 01/02 写的结构化 todos（修 H2）
append_user_todos('{slug}', [
    '全部产出完成（' + str(len(t['outputs_state'])) + ' 份），等待创建子 topic 或进入监控',
], '{variant}')
# 确认 next_actions 不再指向生成产出（next_actions 仍是 list[str]，OK）
actions = [x for x in t.get('next_actions', []) if '01-08' not in x and '产出' not in x]
set_next_actions('{slug}', actions, '{variant}')
print('收尾完成')
"
```

**写 thesis_v1（基于资料的修正版）**：

收尾时主 agent **必读** `outputs/_synthesis_brief.md`（如不存在 — 资料 <10 跳过，则直接读 06+07 合成 v1），把 K1-K5（或对应 thesis 钩子）的 v0→v1 强度调整结论 dump 到 `prism/topics/{slug}/{variant}/thesis_v1.md`。

#### Scheme C 写作约定（v1 起所有 thesis 强制）

任何 `thesis_v{N}.md`（N≥1）必须是**全快照**：包含当前完整的核心 thesis / 支持理由 / 反方观点 / K# 现状表 / 应对策略 / catalyst / 数据缺口 / 思维过程留痕，**不依赖 v{N-1} 章节即可独立阅读**。

强制结构：

1. **frontmatter** 加 `parent_version: {N-1}` + `writing_convention: 方案 C 全快照 + 顶部 changelog`
2. **§ 0. v{N-1} → v{N} changelog** — 5-10 行 release notes 帮 review 者快速定位增量（仅 review 用，正文不依赖）
3. **§ 1. 核心 thesis（当前完整版）** — 一句话观点 + 强度评分 + 估值带 + 时间维度
4. **§ 2. 支持理由（当前完整清单）** — 累积所有看空逻辑（含历代沉淀 + 本版新增），分类编号
5. **§ 3. 反方观点（当前完整清单）** — 累积所有看多逻辑（含历代沉淀 + 本版新增 + critic 强反驳），分类编号
6. **§ 4. Killer Question 现状表（K1-K{n} 完整）** — 表格列：K# / 主题 / 当前状态 / 触发条件
7. **§ 5. 应对策略矩阵** — 价格区间 × 动作
8. **§ 6. catalyst 时点表** — 当前完整 catalyst 序列
9. **§ 7. 数据缺口** — P0/P1/P2 分级 + 期望解决路径
10. **§ 8. 思维过程留痕** — 已知 / 刻意避开的偏见 / 关键差异
11. **§ 9. 信息来源** — 训练知识占比 + 关键 mat_id

**硬约束**：
- 禁止写「见 v{N-1} §X」「同 v{N-1} 不变」等需读老版本才能理解的引用
- 禁止只写"v{N-1} → v{N} 增量"而省略其他章节
- v0 是天然全快照（无 parent），五段式（见 00-research-topic 5.0）；v1 起改用本约定 11 段式

**为什么这样写**：用户阅读 thesis_vN 时只需打开一个文件即可看到当前完整画像；老版本（thesis_v0/v1/...）作为时点 archive 保留，仅供需要还原"当时怎么想的"时翻阅，不作为日常 review 的依赖。

#### thesis_v1.md 必须包含的核心内容（套用上述 11 段结构）

- **核心 thesis** — 修正后的核心观点（含强度评分 v0 → v1 变化值）
- **支持理由** — 来自 findings 的实证（每条注 mat_id）
- **反方观点（必写）** — findings 中浮现的对立信号（每条注 mat_id）
- **Killer Questions K1-K5 现状** — 每条标注：`已验证支持` / `已验证反驳` / `仍未确定` + 关键 mat_id

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

**stage 推进到 critic-review（修 7）**：04 完成后 stage 自动应为 `04-post-synthesis` → 由 next_stage 推到 `05-critic-review`。**company / default 类型必须跑 critic-review** 才能进 done；industry / arena 走 09/10 分支不强制（critic 是可选的）。

```bash
python3 -c "
from prism.scripts.topic import read_topic, set_stage, next_stage
t = read_topic('{slug}', '{variant}')
ns = next_stage(t['type'], t['stage'])
if ns == '05-critic-review':
    set_stage('{slug}', '05-critic-review', '{variant}')
    print('→ 05-critic-review 已就绪，告诉用户「评审 {slug}」启动 workflow 05')
"
```

**刷新仪表盘（修 S5：自动触发，无需手跑）**：

每份产出收尾调 `set_output_referenced_mats` 时已自动 fire-and-forget 重建 dashboard（异步 subprocess，~25s 在后台跑，主流程 <100ms）。**workflow 内不再需要显式 `python -m prism.scripts.dashboard`**。
后台失败仅写 `prism/logs/dashboard_auto.log`——若发现 dashboard 长期未刷新，手动跑一次 `python -m prism.scripts.dashboard` 排查。

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

---

## 即兴 web-search（新增）

合成某份产出过程中，如发现某段需要的关键事实数据**当前 manifest 缺失**（如"2025 Q3 全球 EV 销量"、"某公司最新季报营收"），主 agent 可以即兴调一次 WebSearch 而不必回退 02：

适用场景（**只在以下情况**才即兴）：
- 04 写产出时缺一个具体数字（销量/单价/市占率/估值倍数）
- 该数字训练知识无法准确给出（时效性过新）
- 已有 manifest 里搜了所有 findings 都没覆盖

执行（与 03-extract 用同一 helper）：

```python
from prism.scripts.web_prescan import register_web_search_batch
register_web_search_batch(
    slug='{slug}', variant='{variant}',
    query='缺失数据查询词，例如 "global EV sales 2025 Q3 IEA"',
    addresses=['{对应 K# 或 Q#}'],
    triggered_by='04-synth',
    hits=[...],  # WebSearch 返回的 hit
)
```

入库后在产出 frontmatter 的 `mat_ids_referenced` 列表中加入新 mat_id，确保 `set_output_referenced_mats` 调用时引用正确。

**自动产 inline finding（修 B2）**：`triggered_by='04-synth'` 时
`register_web_search_batch` 自动给每条 high/mid hit 写 `findings_{mat_id}.md`
+ `mark_processed`，返回值多 `inline_finding_paths`。**不再需要等下一轮 03 抽
finding**，05-critic 也能直接读到论据。

**纪律**：
- 单份产出合成过程即兴 web-search 不超过 5 条（避免膨胀）
- 引用 web-search 入库 material 时**仍需写 mat_id**（不准直接引 WebSearch URL，保溯源链）
- 如果即兴搜不到 → 在该段产出中标注"此处数据缺失，建议人工补充"，不要编造数字
- URL/snippet 必须来自 WebSearch 工具实际返回，不得用训练记忆补 URL
- 显式 `inline_finding=False` 关掉自动产 finding（罕见）

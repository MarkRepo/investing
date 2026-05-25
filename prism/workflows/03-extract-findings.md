# Workflow 03 — 从资料中提取发现

**触发**：有未处理资料，或说「提取发现」  
**前置**：manifest.yaml 有 processed=false 的条目  
**产出**：在 `prism/topics/{slug}/{variant}/outputs/` 中积累发现笔记（按资料 ID）

---

## Step 0：扫 topic-scope inbox（**进 03 前强制**）

用户手动放的研报/年报通常落在 `prism/topics/{slug}/inbox/`，**不一定全在 manifest 里**。直接跳 Step 1 会漏掉这些文件。

```bash
python3 << 'EOF'
from pathlib import Path
from prism.scripts.manifest import read_manifest

slug = '{slug}'
variant = '{variant}'
inbox = Path(f'prism/topics/{slug}/inbox')
if not inbox.exists():
    print('无 topic-scope inbox，跳过')
else:
    try:
        m = read_manifest(slug, variant)
        known = {x['filename'] for x in m.get('materials', [])}
    except FileNotFoundError:
        known = set()
    new_files = [f for f in inbox.iterdir() if f.is_file() and f.name not in known]
    if new_files:
        print(f'⚠ topic-scope inbox 有 {len(new_files)} 份未登记文件:')
        for f in new_files:
            print(f'  {f.name}  ({f.stat().st_size/1024:.0f}KB)')
        print()
        print('→ 必须先跑 workflow 02-gather-materials 登记 + 改名 + 自动 mineru')
        print('  (workflow 02 Step 2 会用 pdftotext 识别 H3_AP*.pdf 等无语义文件名;')
        print('   Step 4.5 自动 mineru sell-side/industry/policy PDF)')
        raise SystemExit(1)
    print(f'✓ topic-scope inbox 全部已登记 ({len(known)} 份)')
EOF
```

如果非 0 退出，**回 workflow 02 处理 inbox**，再回来跑 Step 1。

---

## Step 1：读取未处理资料清单

```bash
python -c "
import json
from prism.scripts.manifest import list_unprocessed
items = list_unprocessed('{slug}', '{variant}')
for i in items:
    print(f'{i[\"id\"]} | {i[\"filename\"]} | {i[\"source_type\"]}')
"
```

---

## Step 2：对每份资料，执行以下提取

每次处理一份资料：

### Subagent dispatch 规约（如果走 subagent）

**架构铁律：subagent 只产内容，主 agent 落盘**

经 2026-05-22 4/4 测试（含原文嵌入硬规约的 retry），subagent Write findings_{mat_id}.md 时**总会幻觉出"Write 被拦截"错误**（实际不存在 hook），且声称的"Bash heredoc 绕过"/「.write_test 写入成功」也常常是幻觉。详见 [[subagent-write-hallucination]]。

**所以**：subagent **不再负责写 findings 文件**——只负责产出 markdown 内容到 final message。主 agent 接收后用 Write 工具落盘。

dispatch subagent 时：

- `subagent_type`: **必须 `general-purpose`**
- `model`: **不传**，跟随主 agent
- prompt 末尾必须原文加入：
  > "**重要：你不要调用 Write/Edit 工具写文件，也不要用 Bash heredoc 写文件。** 你的全部 markdown 产出必须以 ```markdown\n...\n``` 代码块形式整体放在 final message 中。主 agent 会接收后落盘。final message 格式：(1) 1-2 句 key signals 摘要；(2) 一个完整的 markdown 代码块，包含 frontmatter + 全部 findings。"

主 agent 收到 subagent final message 后：
1. 提取 markdown 代码块内容
2. 用 Write 工具写到 `prism/topics/{slug}/{variant}/outputs/findings_{mat_id}.md`
3. 用 `ls -la` 验证文件 mtime + 大小

### 2.1 预处理：根据文件类型准备内容

**判断文件类型**（从 filename 和 source_type 推断）：

#### A. 年报 / 半年报（source_type = annual-report）

```bash
# 1. 找到文件位置
python -c "
from prism.scripts.manifest import get_material_path
path = get_material_path('{slug}', '{filename}', '{variant}')
print(path if path else 'FILE_NOT_FOUND')
"
# 2. 用章节提取器处理 PDF，只保留分析相关章节（管理层讨论/主营业务等，跳过财务报表）
python -m scripts.annual_report_extractor \
  "{material_path}" \
  --out "prism/topics/{slug}/{variant}/materials/{filename_stem}_extracted.md"
```

提取完成后，读取 `_extracted.md` 作为分析内容（而非原始 PDF）。

**段落级过滤**：故意不做。年报章节抽取后通常 50-80K tokens，单份 LLM 可以一口气消化，由 LLM 根据 thesis K# 自行识别相关段落比 keyword grep 准确得多——避免「凝聚态/麒麟」等非字面变体被漏掉。

```bash
# 2. 从财务 API 补充财务数据（不从 PDF 解析财务数字）
python -c "
from prism.scripts.financial_data import get_financial_context
print(get_financial_context('{slug}', '{variant}'))
"
```

将财务数据作为独立上下文附在发现笔记末尾，不计入 token 主正文。

#### B. 研报 / 行业报告（source_type = sell-side-note 或 industry-research）

```bash
# 1. 找到文件位置
python -c "
from prism.scripts.manifest import get_material_path
path = get_material_path('{slug}', '{filename}', '{variant}')
print(path if path else 'FILE_NOT_FOUND')
"
# 2. 检查是否已转换（避免重复消耗 API 配额）
test -f "prism/topics/{slug}/{variant}/materials/{filename_stem}_vlm/full.md" \
  && echo "已存在，跳过转换" \
  || .venv/bin/python -m scripts.mineru_api \
       "{material_path}" \
       --out "prism/topics/{slug}/{variant}/materials/{filename_stem}_vlm" \
       --model vlm

# 3. 转换成功后翻 mineru_state 为 done（避免 manifest 长期显示 "needs"）
python3 -c "
from pathlib import Path
from prism.scripts.manifest import set_mineru_state
md = Path('prism/topics/{slug}/{variant}/materials/{filename_stem}_vlm/full.md')
if md.exists() and md.stat().st_size > 0:
    set_mineru_state('{slug}', '{variant}', '{mat_id}', 'done')
    print('mineru_state → done')
else:
    set_mineru_state('{slug}', '{variant}', '{mat_id}', 'failed')
    print('mineru_state → failed (full.md missing or empty)')
"
```

转换完成后，读取 `prism/topics/{slug}/{variant}/materials/{filename_stem}_vlm/full.md` 作为分析内容。

> 转换规则参见 `.claude/skills/mineru/SKILL.md`。

#### C. 已是 markdown / 文本文件

直接读取，无需预处理。

```bash
# 找到文件位置
python -c "
from prism.scripts.manifest import get_material_path
path = get_material_path('{slug}', '{filename}', '{variant}')
print(path if path else 'FILE_NOT_FOUND')
"
# 读取
cat "{material_path}"
```

---

### 2.2 提取结构化发现（LLM 推断，在对话里完成）

按以下框架提取：

**A. 核心数据点与事实**（有明确数字/时间/主体的陈述）
- 格式：「[来源] [时间] [主体/指标] [数值/结论]」
- 取舍原则（保留 vs 省略）：
  - **保留**：有具体数字的事实（量、价、时间、占比）；与其他资料有分歧或矛盾的信息；具体公司进展/合同/客户关系；报告独有的测算逻辑（降本路径、市场空间拆分）
  - **省略**：无数据支撑的泛泛判断；行业背景铺垫（常识性知识）；风险提示套话；中间推导步骤（保留起终点即可）；多份资料共同出现的共识数据
- 目标 15-20 条；超过需说明原因

**B. 叙事主线**（报告核心论证链，3 句以内）
- 格式：「因为 X（数据依据）→ 所以研报判断 Y → 对投资意味着 Z」
- 这是报告的主线逻辑，不是观点列表；只写一组核心链条

**C. 反常识/分歧点**（与市场共识或其他资料相悖的内容）
- 格式：「市场预期/常识：xxx，本文表明：xxx」
- 没有则写「无」

**D. 未回答问题**（可选，1-3 条）
- 这份资料没有回答、但对本研究判断重要的问题
- 没有则省略此节

**E. 资料质量评估**
- 数据新鲜度（最新数据截至几时）
- 分析师倾向（偏多/偏空/中性）
- 可信度（高/中/低，原因）
- 与已有发现是否矛盾

### 2.3 写入发现笔记

写入 `prism/topics/{slug}/{variant}/outputs/findings_{mat_id}.md`：

```markdown
---
mat_id: {mat_id}
filename: {filename}
source_type: {source_type}
extracted: {timestamp}
quality: high|medium|low
bias: bull|bear|neutral
---

## 核心数据点与事实

{bullet list，按取舍原则筛选，目标 15-20 条}

## 叙事主线

因为 {X（数据依据）} → 所以 {研报判断 Y} → 对投资意味着 {Z}

## 反常识/分歧点

{bullet list or "无"}

## 未回答问题

{1-3 条 or 省略此节}

## 质量备注

{notes}
```

---

### 2.4 训练知识冲突触发即兴 web-search（新增）

提取 finding 时如果遇到以下情况，**主 agent 可以即兴调用 WebSearch 验证一条**（不需要回 02 让用户跑 prescan）：

- 资料中数字与 LLM 训练知识冲突（如资料说 "2024 年市占率 35%"，LLM 训练记忆是 25%）
- 资料引用的事件 LLM 训练时不知道（训练截止后的新事件）
- 资料给出的关键定性结论与 LLM 业内常识不一致

执行方式（保持原 03 主流程不被打断）：

1. 主 agent 在对话里调 `WebSearch` 工具，query 围绕冲突点构造（不超过 2 条）
2. 拿到 hit 后用 Phase 1 加的 helper 一行入库：

```python
from prism.scripts.web_prescan import register_web_search_batch
register_web_search_batch(
    slug='{slug}', variant='{variant}',
    query='冲突点查询词',
    addresses=['{相关 K# 或 Q#}'],
    triggered_by='03-extract',
    hits=[
        {'title': '...', 'url': 'https://...', 'snippet': '...'},
        # 可选: 'confidence': 0.85, 'domain_tier': 'llm-judged-official'
    ],
)
```

3. 入库的 web-search material 在下一轮 03 处理时会自然进入 unprocessed 队列
4. 在当前 finding 笔记里**注明**："此处与训练知识 / 资料 X 冲突，已即兴 web-search 入库 mat-xxx 备核"

**纪律**：
- 单份资料 03 处理过程中即兴 web-search 不超过 3 条（避免变成 prescan）
- 若冲突点超过 3 条 → 标记 user_todos，stage 回退 02-gather-materials 走完整 prescan
- 即兴 web-search 必须填 addresses，否则 manifest coverage 算不进
- URL/snippet 必须来自 WebSearch 工具实际返回，不得用训练记忆补 URL

### 2.4b 深挖循环升级（可选）

如果 2.4 的"即兴 1-3 条" 不够（如冲突点本身需要多角度验证），主 agent **升级为 dispatch sub-agent 跑深挖循环**：

```
主 agent 判断："1-3 条 query 不足以验证此冲突 → dispatch sub-agent"
  ↓
按 prism/workflows/_subagent_deep_search.md 模版构造 prompt
  ↓
Agent 工具调用（subagent_type='general-purpose', 不传 model）
  ↓
sub-agent 在自己 context 跑 1-3 轮 search → 返回 final message
  ↓
主 agent 解析 hits → register_web_search_batch（triggered_by='03-extract'）
```

**纪律**：
- 一份资料 03 处理过程最多 dispatch 1 次 sub-agent（防"sub-agent 套娃"）
- sub-agent prompt **必须**原文嵌入 _subagent_deep_search.md 的硬规约（防写文件幻觉）

---

## Step 3：标记资料已处理

```bash
python -c "
from prism.scripts.manifest import mark_processed
mark_processed('{slug}', '{mat_id}', '{variant}')
print('已标记处理完成')
"
```

对每份处理完的资料执行一次。

---

## Step 4：完成所有资料后更新状态

```bash
python -c "
from prism.scripts.topic import set_stage, set_next_actions, set_user_todos
from prism.scripts.manifest import material_count
counts = material_count('{slug}', '{variant}')
if counts['unprocessed'] == 0:
    set_stage('{slug}', '04-synthesizing', '{variant}')
    set_next_actions('{slug}', [
        '所有资料已处理完毕，可以生成产出',
        '说「生成产出 {slug} 商业全景」开始生成第一份产出',
        '或说「prism 推进 {slug}」按顺序生成所有 8 份产出',
    ])
    set_user_todos('{slug}', [
        f'资料提取完成：{counts[\"total\"]} 份全部处理完毕',
        '下一步：生成产出（说「prism 推进 {slug}」按顺序生成 8 份产出）',
    ])
else:
    set_next_actions('{slug}', [
        f'还有 {counts[\"unprocessed\"]} 份资料未处理',
    ])
    set_user_todos('{slug}', [
        f'资料提取中：{counts[\"processed\"]}/{counts[\"total\"]} 份已处理',
        f'剩余 {counts[\"unprocessed\"]} 份待处理',
    ])
"
```

---

## Step 5：选择是否更新产出

**AskUserQuestion**：

```
新资料处理完成！

已处理：{N} 份
关键发现（跨所有资料）：
- {最重要的 3-5 条数据点}

现在要不要立即更新 01-08 产出？
[ ] 更新产出（重新生成 01-08）
[ ] 暂时不更新（等更多资料一起）
```

---

## Step 6：更新状态并汇报

如果用户选择「更新产出」，设置 next_actions 为引导用户运行 synthesis。

如果用户选择「暂时不更新」，设置 next_actions 说明可以后续再更新。

```bash
python -c "
from prism.scripts.topic import set_stage, set_next_actions, set_user_todos
from prism.scripts.manifest import material_count
counts = material_count('{slug}', '{variant}')
if counts['unprocessed'] == 0:
    # 选择是否产出由用户决定，但更新状态提醒
    set_stage('{slug}', '04-synthesizing', '{variant}')
    if {user_chose_update}:
        set_next_actions('{slug}', [
            '正在更新产出...',
        ], '{variant}')
        set_user_todos('{slug}', [
            '产出更新中...',
        ], '{variant}')
    else:
        set_next_actions('{slug}', [
            '新资料已处理，等待后续再更新产出',
            '需要时说「prism 推进 {slug}」来更新 01-08',
        ], '{variant}')
        set_user_todos('{slug}', [
            '新资料已记录 ✓',
            '产出暂未更新，等待更多资料',
            '随时可以说「prism 推进 {slug}」来更新产出',
        ], '{variant}')
else:
    set_next_actions('{slug}', [
        f'还有 {counts[\"unprocessed\"]} 份资料未处理',
    ])
    set_user_todos('{slug}', [
        f'资料提取中：{counts[\"processed\"]}/{counts[\"total\"]} 份已处理',
        f'剩余 {counts[\"unprocessed\"]} 份待处理',
    ])
"
```

---

## Step 7：汇报

```
✅ 资料提取完成

已处理：{N} 份
关键发现（跨所有资料）：
- {list key findings}

你选择了「{用户选择}」
```

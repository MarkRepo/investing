# Workflow 03 — 从资料中提取发现

**触发**：有未处理资料，或说「提取发现」  
**前置**：manifest.yaml 有 processed=false 的条目  
**产出**：在 `prism/topics/{slug}/{variant}/outputs/` 中积累发现笔记（按资料 ID）

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
# 2. 用章节提取器处理 PDF，只保留分析相关章节
python -m scripts.annual_report_extractor \
  "{material_path}" \
  --out "prism/topics/{slug}/{variant}/materials/{filename_stem}_extracted.md"
```

提取完成后，读取 `_extracted.md` 作为分析内容（而非原始 PDF）。

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

# Workflow 03 — 从资料中提取发现

**触发**：有未处理资料，或说「提取发现」  
**前置**：manifest.yaml 有 processed=false 的条目  
**产出**：在 `prism/topics/{slug}/outputs/` 中积累发现笔记（按资料 ID）

---

## Step 1：读取未处理资料清单

```bash
python -c "
import json
from prism.scripts.manifest import list_unprocessed
items = list_unprocessed('{slug}')
for i in items:
    print(f'{i[\"id\"]} | {i[\"filename\"]} | {i[\"source_type\"]}')
"
```

---

## Step 2：对每份资料，执行以下提取

每次处理一份资料：

### 2.1 读取资料内容

```bash
cat prism/topics/{slug}/materials/{filename}
# 或者
cat prism/inbox/manual/{filename}
```

如果文件是 PDF，要求用户先通过 MinerU 转换为 markdown。

### 2.2 提取结构化发现（LLM 推断，在对话里完成）

按以下框架提取：

**A. 数据点与事实**（有明确数字/时间/主体的陈述）
- 格式：「[来源] [时间] [主体] [指标] = [数值]，原文：xxx」
- 最多提取 10 条最重要的

**B. 叙事与观点**（分析师/管理层的判断、预测、逻辑）
- 格式：「[来源] [多空方向] 核心逻辑：xxx，依据：xxx」
- 最多 5 条

**C. 反常识/意外信息**（与市场共识相悖的内容）
- 格式：「市场预期：xxx，本文表明：xxx，差异原因可能：xxx」

**D. 资料质量评估**
- 数据新鲜度（最新数据截至几时）
- 分析师倾向（偏多/偏空/中性）
- 可信度（高/中/低，原因）
- 与已有发现是否矛盾

### 2.3 写入发现笔记

写入 `prism/topics/{slug}/outputs/findings_{mat_id}.md`：

```markdown
---
mat_id: {mat_id}
filename: {filename}
source_type: {source_type}
extracted: {timestamp}
quality: high|medium|low
bias: bull|bear|neutral
---

## 数据点与事实

{bullet list}

## 叙事与观点

{bullet list}

## 反常信息

{bullet list or "无"}

## 质量备注

{notes}
```

---

## Step 3：标记资料已处理

```bash
python -c "
from prism.scripts.manifest import mark_processed
mark_processed('{slug}', '{mat_id}')
print('已标记处理完成')
"
```

对每份处理完的资料执行一次。

---

## Step 4：完成所有资料后更新状态

```bash
python -c "
from prism.scripts.topic import set_stage, set_next_actions
from prism.scripts.manifest import material_count
counts = material_count('{slug}')
if counts['unprocessed'] == 0:
    set_stage('{slug}', '04-synthesizing')
    set_next_actions('{slug}', [
        '所有资料已处理完毕，可以生成产出',
        '说「生成产出 {slug} 商业全景」开始生成第一份产出',
        '或说「prism 推进 {slug}」按顺序生成所有 8 份产出',
    ])
else:
    set_next_actions('{slug}', [
        f'还有 {counts[\"unprocessed\"]} 份资料未处理',
    ])
"
```

---

## Step 5：汇报

```
✅ 资料提取完成

已处理：{N} 份
关键发现（跨所有资料）：
- 最重要的 3-5 条数据点
- 主要叙事方向
- 最值得注意的反常信息

下一步：
说「生成产出 {slug} 商业全景」或「prism 推进 {slug}」
```

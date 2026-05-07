# Workflow 07 — 深度钻探 (Drill-down)

**触发**：用户说「深挖 {slug} 的 {具体问题}」  
**定位**：对某个具体问题进行专项深度研究，产出专题笔记  
**产出文件**：`prism/topics/{slug}/outputs/drilldown_{timestamp}_{topic_keyword}.md`

---

## Step 1：明确钻探问题

用户的问题可能是：
- 「深挖 {slug} 的竞争格局」
- 「分析 {slug} 里 {公司名} 的护城河」
- 「中国 vs 海外 {slug} 的格局差异」
- 「{slug} 在利率上行环境的历史表现」

如果问题不够具体，AskUserQuestion 细化。

---

## Step 2：评估信息来源

```bash
python -c "
from prism.scripts.manifest import read_manifest
import json
data = read_manifest('{slug}')
for m in data['materials']:
    print(m['id'], '|', m['filename'], '|', 'processed' if m['processed'] else 'UNPROCESSED')
"
```

判断：现有资料是否足够回答这个问题，还是需要补充资料。

---

## Step 3：深度分析

使用训练知识 + 已有 findings，对问题进行深度分析：

- 结构：问题分解 → 每个子问题的分析 → 综合结论
- 要求：比产出 01-08 更深、更具体
- 字数：不限，以回答清楚问题为准

---

## Step 4：写入专题笔记

```bash
# 文件名格式：drilldown_YYYYMMDD_keyword.md
```

格式：
```markdown
---
slug: {slug}
type: drilldown
question: {具体问题}
generated: {timestamp}
---

# 深度钻探：{问题}

{分析内容}

## 结论
{一段话}

## 后续行动
{需要验证的 1-3 件事}
```

---

## Step 5：更新 living feed（追加本次钻探摘要）

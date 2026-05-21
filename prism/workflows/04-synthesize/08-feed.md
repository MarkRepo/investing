# 产出 08 — 信息流时间线 (Living Feed)

> **调度提示**：本文件是 04-synthesize 的**内容规范**，不直接 dispatch。实际由 `_shared.md` 描述的单 subagent 顺序生成 01-08 时按本文件填内容。如需单独重生成本份产出，参考 `_shared.md` § Dispatch Prompt 模板调整范围即可。

**定位**：记录发生时序，以便日后复盘「当时知道什么，当时怎么判断」  
**训练知识比例**：约 20%（主要记录具体事实和日期）  
**产出文件**：`prism/topics/{slug}/{variant}/outputs/08_living_feed.md`

**特点**：这份产出是追加式的，不是一次性生成，每次有新信息都在末尾追加。

---

## Step 0：检查文件是否存在

```bash
cat prism/topics/{slug}/{variant}/outputs/08_living_feed.md 2>/dev/null || echo "FILE_NOT_EXISTS"
```

如果不存在，创建初始文件。如果存在，在末尾追加。

---

## Step 1：初次创建（文件不存在时）

**关键原则**：08 是**追加式日志**，不是综合产出的精华汇编。

- 不要把 brief / 06 / 07 的内容粘进来——那是冗余，等于把同一份判断写第二遍
- 初版只记录"研究启动 + 当下不确定性 + 后续 catalyst 时点"三块即可，控制在 800-1200 字
- 后续 catalyst 兑现 / 事件触发时才追加新条目（每次 200-500 字）

写入文件头部：

```markdown
---
slug: {slug}
output_key: 08_living_feed
version: 1
generated: {timestamp}
---

# 信息流时间线：{display_name}

> 按时间顺序记录重要信息和判断变化。每次更新在末尾追加，不修改历史记录。
> 综合判断与 K# 校准请看 brief / 06 / 07，本文件只记录"事件序列 + 触发反应"。

## {YYYY-MM-DD} 研究启动 v1

**来源**：用户发起 {topic_type} 研究（{父级如有}）

**主要事项**：
- 研究问题：{question}
- v0 thesis 强度（含调整）：{X/10 看多/中性/看空}
- 资料覆盖：{N} 份 findings（自有 + 父级复用）

**当时已知的主要不确定性**（每条不超过 1 句话，列 3-5 条）：
- {不确定性 1}
- {不确定性 2}
- ...

**已排好的 catalyst 时点**（仅列时间和事件名，不展开判断标准——那在 07 signposts）：
- {YYYY-MM-DD}：{事件}
- ...

> 后续条目只在以下情况追加：catalyst 时点真实兑现 / 出现 thesis 没预期的新数据 / K# 翻盘
```

**反例**：不要把 v0→v1 校准表、Tier 排序、Kill criteria 全粘到 Step 1 初版——那已经在 brief / 07 里。08 初版只是"研究启动登记 + 监控待办清单"。

---

## Step 2：追加更新（文件已存在时）

在文件末尾追加：

```markdown

---

## {YYYY-MM-DD} {触发更新的事件简述}

**来源**：{资料名称 / 市场事件 / 数据发布}  
**关键信息**：
- {具体事实，有数据就有数据}

**对已有判断的影响**：
- 支持了：{哪个假设}
- 否定了：{哪个假设，或"无"}
- 新增了：{哪个不确定性，或"无"}

**当前判断更新**（如有变化）：
{如没变化写"维持原判断"}
```

---

## Step 3：更新状态

output_key = `08_living_feed`，每次追加后 version+1。

更新 user_todos：

```bash
python -c "
from prism.scripts.topic import set_user_todos
set_user_todos('{slug}', [
    '8 份产出已全部生成（v{N}）',
    '可选操作：',
    '  1. 「评审 {slug}」—— 启动 critic review 找漏洞',
    '  2. 「深挖 {slug} 的{{具体问题}}」—— 深入研究某个方向',
    '  3. 「记录决策 {slug}」—— 记录投资决策备忘',
    '  4. 「prism 推进 {slug}」—— 进入 monitor 阶段',
])
"
```

---

## Step 4：汇报

```
✅ 信息流时间线已更新 → v{N}
本次追加事项：{一句话}
```

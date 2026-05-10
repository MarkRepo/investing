# Workflow 05 — 批评者评审 (Critic Review)

**触发**：用户说「评审 {slug}」或「steelman 反方」  
**定位**：强制用反方逻辑质疑自己的研究结论  
**前置**：产出 04（隐含预期）和 06（风险盲点）必须已生成

---

## Step 1：读取核心产出

```bash
cat prism/topics/{slug}/outputs/04_implied_expectations.md
cat prism/topics/{slug}/outputs/06_risk_blindspots.md
cat prism/topics/{slug}/outputs/07_decision_kit.md 2>/dev/null
```

---

## Step 2：扮演反方（Steelman）

**指令：现在切换为持有相反观点的分析师。**

如果当前研究结论偏多，现在用空方最强逻辑反驳。
如果当前结论偏空，用多方最强逻辑反驳。

反驳格式：

### 对「核心假设 1」的质疑

多方假设：{原假设}  
反驳：{空方为什么认为这个假设不成立}  
支撑证据：{有什么数据或逻辑}  
强度评估：{强/中/弱} — 如果弱，说明为什么仍然值得考虑

### 对「核心假设 2」的质疑

{同格式}

### 对「核心假设 3」的质疑

{同格式}

---

## Step 3：给原研究评分

| 维度 | 评分(1-5) | 评语 |
|------|-----------|------|
| 逻辑严密性 | | |
| 证据充分性 | | |
| 考虑反面观点 | | |
| 隐含假设透明度 | | |
| 整体 | | |

---

## Step 4：给出修改建议

「如果我要加强这个研究，最重要的 3 件事是：」
1. {具体建议}
2. {具体建议}
3. {具体建议}

---

## Step 5：保存评审结果到 outputs

**保存评审结果**，写入 `prism/topics/{slug}/outputs/05-critic-review.md`：

```markdown
---
slug: {slug}
output_key: 05-critic-review
version: 1
generated: {timestamp}
---

# 批评者评审：{display_name}

> 生成于 {timestamp}，基于产出 04/06/07

{评审内容完整复制}
```

---

## Step 6：追加到信息流时间线

追加到 `prism/topics/{slug}/outputs/08_living_feed.md`：

```markdown
---

## {timestamp_short} 批评者评审完成

**来源**：Workflow 05-critic-review，钢人反方视角

**关键信息**：
- {评审摘要1}
- {评审摘要2}
- {评审摘要3}

**对已有判断的影响**：
- 支持了：{...}
- 新增了：{...}
- 调整了：{...}

**当前判断更新**：
{如有变化写变化，如无写「维持原判断」}
```

---

## Step 7：更新状态

```bash
python -c "
from prism.scripts.topic import set_next_actions, set_user_todos, set_output_status
# Update next actions and user todos
set_next_actions('{slug}', [
    '批评者评审完成，根据建议补充：{重要建议}',
    '下次复盘时重点关注：{关键验证点}',
])
set_user_todos('{slug}', [
    '批评者评审已完成',
    '建议采纳：根据评审意见补充/修改（说「深挖 {slug} 的{{问题}}」）',
    '或说「记录决策 {slug}」记录最终投资决策',
])
# Bump version on living feed
try:
    from prism.scripts.topic import read_topic
    t = read_topic('{slug}')
    current = t.get('outputs_state', {}).get('08_living_feed', {}).get('version', 1)
    set_output_status('{slug}', '08_living_feed', 'fresh', version=current + 1)
except Exception:
    pass
"
```

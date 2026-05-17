# Workflow 99 — 决策记录 (Decision Record)

**触发**：用户要做出实际投资决策（买入/卖出/持有/放弃）
**定位**：在采取行动前记录决策依据，供事后复盘
**产出文件**：`prism/topics/{slug}/outputs/decision_{YYYYMMDD}.md`

---

## Step 1：了解决策意图

AskUserQuestion：
1. 打算做什么操作（买入/加仓/减仓/卖出/放弃研究）
2. 考虑的仓位或规模
3. 为什么现在（什么触发了这个决策）

---

## Step 2：决策前检查

```bash
cat prism/topics/{slug}/outputs/07_decision_kit.md
```

核对：
- [ ] 核心假设是否还成立
- [ ] 是否有 Kill Criteria 被触发
- [ ] 当前信息是否足以支撑决策

如果信息明显不足，提醒用户并给出建议。

---

## Step 3：记录决策

写入 `prism/topics/{slug}/outputs/decision_{YYYYMMDD}.md`：

```markdown
---
slug: {slug}
type: decision
date: {YYYYMMDD}
action: buy|add|reduce|sell|pass
---

# 决策记录：{YYYYMMDD}

## 决策

操作：{buy/add/reduce/sell/pass}
理由（一句话）：{一句话}

## 支撑这个决策的核心假设

1. {假设}（来自产出04）
2. {假设}
3. {假设}

## 同时考虑过的替代标的（强制 ≥ 2 个）

> 来源：从本 company topic 的 parent_topic arena 的 10_peer_matrix.md 短名单 + watchlist 抽取。

### 替代 1：{公司名} ({ticker})

- 排序优势：{相对本标的什么更好}
- 排序劣势：{相对本标的什么更差}
- 拒绝主因：{≤30字}
- 升档触发：{什么情况下应转向这个标的}

### 替代 2：{公司名} ({ticker})

（同上结构）

### 排他性检查

- 有没有可能"两个都买"而不是二选一？{是/否，理由}
- 是否存在 pair trade 机会（多 A 空 B）？{是/否，结构}

## 我知道自己不知道的事情

1. {不确定性}
2. {不确定性}

## 如果我错了，最可能错在哪里

{一段话}

## Kill Criteria（触发后重新评估）

{来自产出06的 kill criteria}

## Signposts 下一个要看的

{来自产出07的 signpost}

## 研究成熟度

{high/medium/low} — {理由}

## 心理状态自检

□ 是否受近期涨跌影响而情绪化
□ 是否对这个行业/公司有特别的偏好
□ 是否充分考虑了反方观点

## 半年后复盘约定

- 决策日 + 180天 = {YYYY-MM-DD}，强制对照本标的 vs 替代标的实际涨跌
- 复盘文件：`prism/topics/{slug}/outputs/decision_review_{YYYYMMDD}.md`
```

---

## Step 4：追加到 living feed

将决策摘要追加到 `08_living_feed.md`。

---

## Step 5：设置半年后复盘提醒

```bash
python -c "
from datetime import datetime, timedelta
from prism.scripts.topic import set_user_todos, read_topic
t = read_topic('{slug}', '{variant}')
review_date = (datetime.now() + timedelta(days=180)).date().isoformat()
current_todos = t.get('user_todos', [])
current_todos.append(f'{review_date}: 决策半年复盘 - 对比本标的 vs 替代标的实际表现')
set_user_todos('{slug}', current_todos, '{variant}')
"
```

---

## Step 6：汇报

```
✅ 决策记录已保存 → prism/topics/{slug}/outputs/decision_{YYYYMMDD}.md

操作：{action}
核心假设数量：{N}
替代标的数量：{N}
主要不确定性：{一句话}

建议：决策后 30 天回来做一次复盘对照；180 天强制复盘已加入 user_todos。
```

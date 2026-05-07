# Workflow 01 — 制定研究路线图

**触发**：stage=01-roadmap-pending 或用户说「制定路线图」  
**前置**：topic.yaml 已存在  
**产出**：`prism/topics/{slug}/roadmap.yaml`

---

## Step 1：读取 topic

```bash
python -c "
import json
from prism.scripts.topic import read_topic
print(json.dumps(read_topic('{slug}'), ensure_ascii=False, indent=2))
"
```

确认研究问题、类型、地理范围、深度。

---

## Step 2：制定学习轨道（L1→L4 问题树）

基于训练知识，为这个研究主题制定四层问题：

**L1 定向层**（3-4 个问题）：搞清楚「是什么」
- 这个行业的边界在哪里？怎么定义市场？
- 主要参与者有哪些（上游/中游/下游）？
- 市场规模多大？主要增长驱动是什么？

**L2 历史层**（3-4 个问题）：搞清楚「怎么来的」
- 过去 5-10 年经历了哪几个发展阶段？
- 有没有明显的周期性规律？
- 关键拐点（政策/技术/需求）是什么时候？

**L3 争议层**（4-5 个问题）：搞清楚「分歧在哪」
- 多空双方的核心分歧是什么？
- 市场共识是什么，哪里可能是错的？
- 最容易被忽视的风险是什么？

**L4 狩猎层**（3-5 个问题）：找错误定价
- 如果市场错了，错在哪里？
- 哪个时间节点能验证或证伪？
- 什么样的新信息会改变当前判断？

---

## Step 3：制定资料优先级

根据研究深度，列出三档资料：

**Tier 1（必读）**：对研究结论影响最大、最难被替代的 3-5 份
**Tier 2（补充）**：有助于验证但非必须的 3-5 份  
**Tier 3（可选）**：深度研究时可参考的

每份资料说明：标题方向、类型（研报/年报/政策/数据）、从哪里找、为什么重要。

---

## Step 4：识别历史类比

列出 2-3 个值得研究的历史类比案例，格式：
- 案例名称（国家+行业+时间段）
- 类比逻辑（哪里像）
- 类比局限（哪里不像）

---

## Step 5：写入 roadmap.yaml

复制 `prism/templates/roadmap.yaml.tmpl`，填入上面分析内容，写入：
`prism/topics/{slug}/roadmap.yaml`

---

## Step 6：更新 topic 状态

```bash
python -c "
from prism.scripts.topic import set_stage, set_next_actions, set_user_todos
set_stage('{slug}', '02-gathering')
set_next_actions('{slug}', [
    '收集 Tier 1 资料后运行 workflow 02-gather-materials 登记资料',
    '有资料可以处理时运行 workflow 03-extract-findings',
])
set_user_todos('{slug}', [
    '按 roadmap.yaml 的 tier1 清单收集资料，放入 prism/inbox/manual/',
    '如需自动下载可在对话里说「下载 {slug} 的 cninfo 年报」',
])
"
```

---

## Step 7：汇报

在对话输出：

```
✅ 研究路线图已生成 → prism/topics/{slug}/roadmap.yaml

L4 狩猎问题（最重要）：
{list L4 questions}

Tier 1 必读资料：
{list tier 1 items}

你现在需要做的事：
1. 收集上述资料放入 prism/inbox/manual/
2. 完成后说「prism 推进 {slug}」继续

Web 地址：http://localhost:8000/prism/{slug}
```

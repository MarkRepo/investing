# Workflow 00 — 开启新研究主题

**触发**：用户说「研究 X」或「开始研究 X」  
**产出**：创建 `prism/topics/{slug}/topic.yaml` + `manifest.yaml`，Web 页面 /prism/{slug} 可访问

---

## Step 1：确认研究对象

向用户确认以下信息（如果用户没说清楚则 AskUserQuestion）：

1. **研究对象名称**（中文，例如「中国宠物行业」「中国商业航天」「宁德时代」）
2. **研究类型**（industry / arena / company）
   - industry：整个行业（宠物、储能、机器人）
   - arena：细分竞技场（宠物食品、人形机器人执行器）
   - company：单家公司
3. **核心研究问题**（例如「中国宠物行业哪些细分赛道值得投资」）
4. **研究深度**（quick = 1-2 天 / standard = 1 周 / deep = 持续跟踪）
5. **地理范围**（CN / US / GLOBAL）

如果用户直接说「研究中国宠物行业」，可以推断：type=industry, geo=CN，然后只确认研究问题和深度。

同时需要确认当前使用的 LLM 模型变体名称（如 `gemini`、`gpt-4o` 等），后续将作为 `variant` 参数使用。默认可使用当前调用的模型名称。

**如果是 company 类型，必须确认 ticker**（格式：`{market}_{code}`，如 `SZSE_000426`、`SSE_600519`、`US_AAPL`）。ticker 用于生成行情/财务页面链接。

---

## Step 2：生成 slug

slug 规则：
- 全小写，连字符分隔
- 格式：`{geo}-{keywords}`
- 示例：`cn-pet-industry`、`cn-commercial-space`、`cn-catl`
- 不超过 30 字符

在对话里显示 slug，等用户确认或修改。

---

## Step 3：检查是否已存在

```bash
ls prism/topics/ 2>/dev/null
```

如果已有同名 slug，告知用户并询问：
- 继续已有研究并在原变体目录下推进（运行 workflow 推进）
- 在当前 slug 下使用不同模型创建一个新变体目录（如 `gemini`、`qwen3.6-plus`）
- 还是创建全新研究（slug 加后缀，如 `cn-pet-industry-2`）

---

## Step 4：创建 topic

```bash
python3 -c "
from prism.scripts.topic import create_topic
create_topic(
    slug='{slug}',
    display_name='{display_name}',
    topic_type='{type}',
    question='{question}',
    geo='{geo}',
    depth='{depth}',
    variant='{variant}',
)
print('创建成功')
"
```

```bash
python3 -c "
from prism.scripts.manifest import create_manifest
create_manifest('{slug}', '{variant}')
print('manifest 创建成功')
"
```

---

## Step 5：基于训练知识做初步定向

**注意**：这一步 100% 使用 LLM 训练知识，不需要外部资料。目的是帮用户快速建立研究框架。

产出以下三部分（直接在对话里输出，不写文件）：

### 5.1 领域概览（3-5 句话）
- 这个行业/赛道/公司是什么
- 当前处于什么发展阶段
- 市场规模量级

### 5.2 关键研究维度（5-8 个问题）
列出要深度研究这个主题，最关键的 5-8 个问题。例如：
- 谁是核心受益者，谁是受损方？
- 增长的核心驱动力是什么，是结构性还是周期性？
- 当前市场共识是什么，哪里可能有分歧？
- 风险清单里最容易被低估的是什么？
- 有哪些历史类比案例？

### 5.3 资料获取建议（用户需要收集什么）
按优先级列出 5-10 份关键资料，包括：
- 哪些卖方研报（机构、标题方向）
- 哪些公司年报/季报
- 哪些行业协会数据
- 哪些政策文件
- 是否有关键的英文资料

---

## Step 6：更新 topic 状态

```bash
python3 -c "
from prism.scripts.topic import set_stage, set_next_actions, set_user_todos
set_stage('{slug}', '01-roadmap-pending', '{variant}')
set_next_actions('{slug}', [
    '运行 workflow 01-build-roadmap：制定详细研究路线图',
    '收集初始资料后运行 workflow 02-gather-materials',
], '{variant}')
set_user_todos('{slug}', {user_todos_from_step_5_3}, '{variant}')
"
```

---

## Step 7：告知用户

输出：
```
✅ 研究主题「{display_name}」已创建

Slug: {slug}
变体目录: prism/topics/{slug}/{variant}/
Web 地址: http://localhost:8000/prism/{slug}/{variant}/

下一步：
1. 在对话里说「prism 推进 {slug}」继续制定研究路线图
2. 或者先收集资料放入 prism/inbox/manual/ 后说「prism 推进 {slug}」

你需要做的事：
{user_todos_list}
```

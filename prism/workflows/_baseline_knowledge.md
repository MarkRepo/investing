# 训练知识 Baseline 模版

**用法**：在 workflow 00 Step 4.3（新增）里被调用，让 LLM 先把"我训练时对此 topic 知道什么"写下来，作为后续 web-search / 用户资料的对照基线。

**写入位置**：`prism/topics/{slug}/{variant}/baseline_knowledge.md`

**模版**：

````markdown
---
slug: {slug}
variant: {variant}
written_at: {iso_ts}
training_cutoff_estimate: {YYYY-MM}    # LLM 自评训练截止月（如 2025-01）
---

# 训练知识 Baseline — {display_name}

> 本文记录 LLM 在**训练截止时**对该 topic 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。

## 一、关键事实记忆（{n} 条）

每条格式：
- `[fact-NN]` 训练时记得的事实，含数字/时间/主体（如 "fact-01: 2024 年全球 EV 销量 1450 万台"）
- 标注**置信度**：高 / 中 / 低（LLM 自评）
- 不确定的标 "uncertain"，跳过比编造好

## 二、关键人物 / 公司 / 产品

每条 1 句话定位 + 训练时知道的最新动作

## 三、产业链 / 竞争格局认知

3-5 段，主线 + 主要玩家相对位

## 四、训练知识盲点（自我承认）

LLM 自评以下方面训练时不够 / 不知道：
- {领域 / 时段 / 数据类型}
- {具体盲点}

## 五、需要 web-search 校准的优先项

按优先级列 5-10 条**具体 query**（不是宽泛话题，是直接能扔给 WebSearch 的 query 串）：

例：
- `特斯拉 4680 电池 2026Q1 量产爬坡进度`（fact-03 需校准）
- `2025 年中国新能源补贴退坡时间表 财政部公告`（fact-05 训练时已模糊）
- `宁德时代 2025 年报 储能业务营收占比`（第四节标"不知道储能拆分"）

**workflow 00 Step 4.5a** 会要求主 agent **逐条** WebSearch + `register_web_search_batch(triggered_by='00-prescan-baseline')` 入库——
这一节的 query 必须**精准、可执行**，宽泛话题会被默认 prescan（Step 4.5b）的模板 query 覆盖，不需要再列。

## 六、prescan 校准结果（**Step 4.5c 跑完后回写**）

> 这一节在 baseline 初次落盘时**留空或省略**；
> workflow 00 Step 4.5c 执行后由主 agent 用 Edit 工具追加。

模版（参 [[00-research-topic.md]] Step 4.5c）：

```markdown
## 六、prescan 校准结果（{iso_ts} 回写）

### 被推翻
- `[fact-NN]` 训练时 X → `[mat-xxxx]` 实际 Y → thesis_v0 不要再引用原 fact

### 被验证
- `[fact-NN]` X → `[mat-yyyy]` 一致，置信度 高 → 高+

### 仍未校准
- `[fact-NN]` ...
```
````

**纪律**：
- 自评置信度时**保守**——宁可标 "uncertain" 也不编造
- 第四节的盲点必须诚实写——它是第五节 query 的来源
- 第五节 query 必须精准可执行（直接能 WebSearch），不是话题描述
- 第六节由 Step 4.5c 主 agent 回写，初次落盘可省略
- 写完即落盘到 `prism/topics/{slug}/{variant}/baseline_knowledge.md`，后续 03/04 可 cite
- 引用 baseline 事实时使用 `[fact-NN]` 编号，不准散文化重述
- 引用已被推翻的 fact（第六节列出的）→ **必须 cite 新 mat_id 替代**，不准继续用原 fact

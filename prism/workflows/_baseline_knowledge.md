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

## 〇、基本信息（仅 company 类型，industry/arena 跳过）

- **主代码**：`{ticker}`（与 topic.yaml `scope.ticker` 一致）
- **多市场上市**：列 `scope.extra_tickers` 全部代码（无则写"单市场"）
  - 例：荣昌生物 `SSE_688331`（A 股科创板）+ `HKEX_09995`（港股）→ AH 双重上市
  - 例：阿里巴巴 `HKEX_09988`（港股主要上市）+ `NYSE_BABA`（ADR）
  - 多市场标的的研究纪律：fact 涉及估值 / 资金 / 公告时，必须**显式说明数据源自哪个市场**（A 股 vs H 股 vs ADR），不能混着说
- **市场属性快速对照**（如适用）：A 股交易窗口 9:30-15:00、北向陆股通；H 股 9:30-16:00、南向港股通、可沽空；ADR 含 ADR 比率 / 时差

## 一、关键事实记忆（{n} 条）

每条格式（**二维标签必填**）：
- `[fact-NN]` 训练时记得的事实，含数字/时间/主体（如 "fact-01: 2024 年全球 EV 销量 1450 万台"）
- **置信度（LLM 自评训练时的确定性）**：高 / 中 / 低 / uncertain
- **time_sensitivity（事实本身的时效衰减速度）**：静态 / 慢变 / 快变
  - **静态**：科学机制 / 物理常数 / 历史事件 / 已结案诉讼 / 已批准且未撤回的监管动作（多年不变）
  - **慢变**：市场份额 / 产业链格局 / 监管框架 / 专利到期时间表 / 产能布局（年级变化，但训练 vs 今天差 ≥12 月时已可能不再准确）
  - **快变**：股价 / 季度业绩 / 临床读出 / 价格 / 在研管线 readout / 监管批准 / 政策表态 / 高管变动（季级甚至月级变化，训练 vs 今天差 ≥3 月时已大概率过时）
- 不确定的标 "uncertain"，跳过比编造好
- **多市场标的**：涉及股价 / 市值 / 估值 / 沽空 / 大行持仓的 fact，**必须标 A/H/ADR 哪个市场口径**

**示例**：
- `[fact-01]` GLP-1 受体激动剂通过下丘脑食欲抑制减重（机制）→ 置信度：高 | time_sensitivity：**静态**
- `[fact-12]` Eli Lilly 2025 营收 $65B，超越 NVO 成首个 $1T 医药公司 → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-28]` 司美格鲁肽美国 COM 专利 2031-12 到期 → 置信度：中 | time_sensitivity：**慢变**

**纪律**：写完第一节后**统计**：快变类有多少条？这些条是第五节优先 query 的**强制来源**——"训练时高置信 + 快变"是最容易蒙蔽 thesis 的子集，必须用 web-search 校准。

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

**强制规则**：第一节所有 `time_sensitivity: 快变` 且 `置信度: 高/中` 的 fact 必须在本节有对应 query——这是"训练时高置信 + 已过时风险高"的子集，**最容易蒙蔽 thesis**。

例：
- `特斯拉 4680 电池 2026Q1 量产爬坡进度`（fact-03 快变 + 高 → 必须校准）
- `2025 年中国新能源补贴退坡时间表 财政部公告`（fact-05 快变 + 训练时已模糊）
- `宁德时代 2025 年报 储能业务营收占比`（第四节标"不知道储能拆分"）

**workflow 00 Step 4.5a** 会要求主 agent **逐条** WebSearch + `register_web_search_batch(triggered_by='00-prescan-baseline')` 入库——
这一节的 query 必须**精准、可执行**，宽泛话题会被默认 prescan（Step 4.5b）的模板 query 覆盖，不需要再列。

**质检自检（落盘前）**：
- 第一节统计：静态 N 条 / 慢变 N 条 / 快变 N 条
- 第五节 query 数 ≥ 第一节"快变 + 高/中"fact 数（每条快变 fact 至少一个对应 query）
- 不满足 → 补齐 query 或在第四节诚实标 "本研究放弃校准 fact-NN 的现状"

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

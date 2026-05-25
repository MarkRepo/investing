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

按优先级列 5-10 条："这条事实需要 web-search 拉最新数据" — 接下来 Step 4.5 prescan 的种子。
````

**纪律**：
- 自评置信度时**保守**——宁可标 "uncertain" 也不编造
- 第四节的盲点必须诚实写——它是 prescan 攻打方向的来源
- 写完即落盘到 `prism/topics/{slug}/{variant}/baseline_knowledge.md`，后续 03/04 可 cite
- 引用 baseline 事实时使用 `[fact-NN]` 编号，不准散文化重述

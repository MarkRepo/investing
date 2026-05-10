# Prism 投资研究系统 — 用户使用指南

> 适合对象：已安装 Claude Code 并了解基本操作的用户

---

## 快速上手（5 分钟）

**开启一个研究主题，只需在对话里说：**

```
研究中国宠物行业
```

Claude 会引导你完成：确认研究对象 → 生成 slug → 创建主题 → 给出初步定向和资料收集建议。

**查看研究进度：**

```
http://localhost:8000/prism
```

---

## 核心概念

### 研究主题（Topic）

每个研究对象叫一个「主题」（Topic），用 slug 标识。例如：
- `cn-pet-industry` — 中国宠物行业
- `cn-catl` — 宁德时代
- `cn-humanoid-robot` — 中国人形机器人竞技场

每个主题有：
- 一份 `topic.yaml` — 记录状态、阶段、产出情况
- 一份 `manifest.yaml` — 记录所有录入的研究资料
- 8 份标准产出 — 每份都是一个 markdown 文件

### 8 份标准产出

| # | 名称 | 回答的问题 |
|---|------|-----------|
| 01 | 商业全景 | 这个生意是怎么运转的？ |
| 02 | 周期定位 | 现在处于什么位置？ |
| 03 | 叙事生态 | 市场上流传哪些故事，多空分歧在哪？ |
| 04 | 隐含预期 | 当前估值隐含了什么假设？ |
| 05 | 历史镜子 | 有哪些历史案例可以类比？ |
| 06 | 风险盲点 | 市场可能低估的风险是什么？ |
| 07 | 决策工具箱 | 在什么条件下买/卖/放弃？ |
| 08 | 持续跟踪 | 最新动态和观察记录 |

---

## 完整研究流程

### 阶段 0：开启研究主题

**触发词：** 「研究 X」 / 「开始研究 X」

```
研究中国核聚变材料
```

Claude 会问你：
1. 研究类型（行业/竞技场/公司）
2. 核心研究问题
3. 研究深度（quick=1-2天 / standard=1周 / deep=持续跟踪）

完成后 Claude 会：
- 生成 slug（如 `cn-fusion-material`）
- 给出领域概览（基于训练知识）
- 列出关键研究问题
- 给出资料收集建议
- 创建主题，可在 `/prism` 看到

---

### 阶段 1：制定研究路线图

**触发：** 主题创建后 Claude 会自动提示，或说「prism 推进 {slug}」

Claude 会制定：
- **四层问题树**（L1定向→L2历史→L3争议→L4狩猎）
- **三档资料清单**（Tier1必读 / Tier2补充 / Tier3可选）
- **历史类比案例**

产出：`prism/topics/{slug}/roadmap.yaml`

---

### 阶段 2：收集和登记资料

**你需要做的：** 把研究资料（PDF、markdown、文本）放入：
```
prism/inbox/manual/
```

**触发登记：** 「登记 {slug} 的新资料」 或 「prism 推进 {slug}」

Claude 会：
1. 列出 inbox/manual/ 下的文件
2. 为每份文件询问来源类型和备注
3. 用脚本录入 manifest

录入后资料会出现在主题的 manifest，状态为「未处理」。

**支持的资料类型：**
- 卖方研报（PDF 或文本）
- 公司年报/季报
- 行业白皮书/数据报告
- 政策文件
- 新闻摘要
- 专家访谈记录

---

### 阶段 3：提炼发现

**触发：** 「提炼 {slug} 的发现」 或 「prism 推进 {slug}」

Claude 会逐份处理未处理资料：
- 提炼关键数据点、观点、矛盾
- 写入 `prism/topics/{slug}/outputs/findings_{mat_id}.md`
- 标记资料为已处理

> **提示：** 至少 3 份资料处理完后，才能生成产出。

---

### 阶段 4：生成 8 份产出

**触发：** 逐个生成

```
生成产出 cn-pet-industry 商业全景
```

或按编号：
```
生成产出 cn-pet-industry 01
```

**完整触发词列表：**

| 说 | 生成 |
|----|------|
| `生成产出 {slug} 商业全景` | 01_business_panorama |
| `生成产出 {slug} 周期定位` | 02_cycle_positioning |
| `生成产出 {slug} 叙事生态` | 03_narrative_ecology |
| `生成产出 {slug} 隐含预期` | 04_implied_expectations |
| `生成产出 {slug} 历史镜子` | 05_historical_mirrors |
| `生成产出 {slug} 风险盲点` | 06_risk_blindspots |
| `生成产出 {slug} 决策工具箱` | 07_decision_kit |
| `生成产出 {slug} 持续跟踪` | 08_living_feed |

**查看产出：**
```
http://localhost:8000/prism/cn-pet-industry/sonnet/01_business_panorama
```

> 导航路径为 主题 → 模型 → 产出，URL 格式 `/prism/{slug}/{variant}/{output_key}`。同一个主题可以用不同模型独立研究、隔离对比。

---

### 阶段 5：批评者评审（可选但推荐）

**触发：** 「评审 {slug}」 或 「steelman 反方 {slug}」

**前置：** 需要先完成产出 04（隐含预期）和 06（风险盲点）

Claude 会：
1. 切换为「持有相反观点的分析师」角色
2. 用最强逻辑反驳当前研究的核心假设
3. 给研究打分（逻辑严密性/证据充分性/多空兼顾等）
4. 给出改进建议

这一步能有效防止确认偏误。

---

### 阶段 6：专题深挖

**触发：** 「深挖 {slug} 的 {具体问题}」

```
深挖 cn-pet-industry 的宠物食品国产化率
```

适合对某个细节问题做专项分析，不生成正式产出文件，结果在对话里呈现。

---

### 阶段 7：记录决策

**触发：** 「记录决策 {slug}」

**适用场景：** 即将买入/加仓/减仓/卖出/放弃前

Claude 会引导你记录：
- 决策类型和规模
- 支撑决策的核心假设
- 已知的不确定性
- 最可能的错误方向
- Kill criteria（触发后必须重新评估的条件）

产出：`prism/topics/{slug}/outputs/decision_YYYYMMDD.md`

这份记录会成为你事后复盘的基础。

---

## 持续跟踪

### 日常监控

**触发：** 「监控 {slug}」

Claude 会：
1. 检查是否有未处理的新资料
2. 检查关键信号（来自 roadmap 的 signposts）
3. 如有异常，追加到 `08_living_feed.md`

### 产出更新

当你导入新资料后，旧产出会变为 `stale` 状态（在 Web 上显示），提示你重新生成。

重新生成产出的版本号会自动 +1，历史版本不保留（最新版本覆盖写入）。

---

## Web 界面使用

### 主题列表（/prism）

```
http://localhost:8000/prism
```

显示所有研究主题，每个主题展示可用模型及各自产出进度（如 `sonnet 3/8`、`gemini 1/8`）。

### 模型选择（/prism/{slug}）

```
http://localhost:8000/prism/cn-pet-industry
```

展示该主题下所有模型变体，列出各模型的阶段和产出完成度。点击模型进入仪表盘。

### 主题仪表盘（/prism/{slug}/{variant}）

```
http://localhost:8000/prism/cn-pet-industry/sonnet
```

左侧：8 份产出的状态表格（pending/fresh/stale + 版本号）
右侧：当前 stage、next_actions、user_todos
顶部：模型切换器（可在同一主题的不同模型间快速切换）

### 查看单份产出（/prism/{slug}/{variant}/{output_key}）

```
http://localhost:8000/prism/cn-pet-industry/sonnet/01_business_panorama
```

渲染 markdown 为 HTML，左侧有所有 8 份产出的导航链接。面包屑显示：主题 → 模型 → 产出。

---

## 常用对话命令速查

| 你说 | 效果 |
|------|------|
| `研究 X` | 开启新研究主题 |
| `prism 推进 {slug}` | 根据当前阶段继续推进 |
| `查看 {slug} 进度` | 显示 topic.yaml 当前状态 |
| `生成产出 {slug} {名称}` | 生成指定产出 |
| `更新 {slug} 的 {产出名}` | 重新生成（版本+1） |
| `评审 {slug}` | 批评者评审 |
| `深挖 {slug} 的 {问题}` | 专题深挖 |
| `监控 {slug}` | 日常监控扫描 |
| `记录决策 {slug}` | 记录投资决策 |

---

## 资料管理

### 手动放入资料

把文件（PDF/markdown/txt）直接放入：
```
prism/inbox/manual/
```

然后说「登记 {slug} 的新资料」，Claude 会帮你录入 manifest。

### 直接在对话里提供资料

你也可以把研究资料的内容直接粘贴到对话里，Claude 会提炼要点并整合进研究。

### 查看资料清单

在对话里说「查看 {slug} 的资料清单」，Claude 会读 manifest.yaml 输出表格。

---

## 常见问题

**Q：能同时研究多个主题吗？**
A：可以。每个主题独立存在，说「prism 推进 {slug}」时指定 slug 即可切换。

**Q：研究内容会影响其他系统（公司/行业档案）吗？**
A：不会。Prism 的数据完全在 `prism/topics/` 下，与 `companies/`、`industries/` 等目录相互独立。

**Q：产出文件能手动编辑吗？**
A：可以。产出是普通 markdown 文件，直接编辑后 Web 会自动展示最新内容。但建议通过对话让 Claude 更新，这样版本号和状态会一起更新。

**Q：怎么归档一个完成的研究主题？**
A：在对话里说「归档 {slug}」，Claude 会用脚本将 topic.yaml 的 status 改为 `archived`，主题继续保留但不在主列表突出显示（待实现）。

**Q：产出用的训练知识截止日期是什么？**
A：Claude 的训练知识截止到 2025 年 1 月。涉及最新市场数据的产出需要你提供最新资料。每份产出都会标注训练知识占比和资料来源。

**Q：质量怎么保障？**
A：每份产出生成后 Claude 会对照质量 rubric 自检，确保：有具体数字、多空兼顾、有「可能错在哪」、来源透明、结论在前。批评者评审（workflow 05）提供额外的反向验证。

---

## 典型研究路径示例

### 快速研究（1-2 天）

```
1. 「研究中国 AI 算力 quick」
2. Claude 给出初步定向和资料建议
3. 收集 1-2 份卖方研报放入 inbox/manual/
4. 「登记 cn-ai-compute 新资料」
5. 「生成产出 cn-ai-compute 商业全景」
6. 「生成产出 cn-ai-compute 风险盲点」
7. 查看 /prism/cn-ai-compute/sonnet 浏览结果
```

### 深度研究（1-2 周）

```
1. 「研究中国宠物行业 deep」
2. 制定路线图（workflow 01）
3. 收集 Tier 1 资料（年报 + 头部研报）
4. 逐份提炼发现（workflow 03）
5. 生成全部 8 份产出（workflow 04-01 ～ 04-08）
6. 「评审 cn-pet-industry」（批评者评审）
7. 根据建议补充资料，更新关键产出
8. 「记录决策 cn-pet-industry」（如果决定投资）
```

### 持续跟踪（季度更新）

```
每季度：
1. 收集最新研报/年报/季报
2. 「登记 {slug} 新资料」
3. 「提炼 {slug} 的发现」
4. 更新 stale 的产出
5. 「监控 {slug}」检查 signposts

事件驱动（有重要新闻/业绩）：
1. 直接在对话里说「深挖 {slug} 的 {事件}」
2. 如需要，更新 08_living_feed
3. 如影响决策，「记录决策 {slug}」
```

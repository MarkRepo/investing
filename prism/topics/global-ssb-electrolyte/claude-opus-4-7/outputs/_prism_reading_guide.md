---
slug: global-ssb-electrolyte
output_key: _prism_reading_guide
type: system-conventions
audience: prism 产出的所有读者（不限本 topic）
generated: 2026-05-29T11:00:00+08:00
sources_note: 全篇为 prism 系统约定，不依赖任何 topic 数据。若纳入 workflow，建议提到所有 topic 共用的位置（如 prism/docs/READING_GUIDE.md）
companion: 00_primer.md（领域入门）+ _glossary.md（领域术语速查）
---

# prism 阅读指南：怎么看懂 prism 产出

> 不讲领域知识。只讲 prism 这个研究系统的内部约定——编号、强度刻度、产出体系、阅读路径。任何 topic 共用。

---

## 一、产出体系：10+ 份产出每份在干什么

prism 一个 topic 的研究输出固定为以下产出。文件名是 `NN_<key>.md`：

| # | 产出 | 一句话定位 | 适合什么时候读 |
|---|------|-----------|---------------|
| 00 | primer | **领域入门**——给完全外行建心智模型 | 第一次看这个 topic |
| 01 | business_panorama | 商业全景：边界 / 价值链 / 玩家 / 当前阶段 | 想知道"这门生意长什么样" |
| 02 | cycle_positioning | 周期定位：当前在哪个阶段、类比哪段历史 | 想知道"现在是不是好时机" |
| 03 | narrative_ecology | 叙事生态：市场上几种叙事在打架、共识 / 分歧 / 盲点 | 想知道"市场在想什么" |
| 04 | implied_expectations | 隐含预期：价格已 price-in 了什么、反推市场假设 | 想知道"估值贵不贵" |
| 05 | historical_mirrors | 历史镜子：用 4-5 个类似剧本对照本剧本 | 想知道"以前发生过什么类似的" |
| 06 | risk_blindspots | 风险与盲点：R1-Rn 风险逐条 + 盲点清单 | 想知道"会怎么死" |
| 07 | decision_kit | 决策工具箱：thesis 强度 + K1-Kn v1 + KILL 体系 + What Would Have To Be True | 看一份就够时看这份 |
| 08 | living_feed | 跟踪流：接下来要盯的时点 / 催化剂 / 监测信号 | 决定"接下来盯什么" |
| 09 | industry_to_arenas | （industry 类专属）从行业切到细分战场 | industry 类研究 |
| 10 | peer_matrix | （arena 类专属）玩家横评矩阵 | arena 类研究 |

**三种 topic 类型决定哪几份产出有**：

- `industry`（行业级）→ 01-08 + 09
- `arena`（细分战场）→ 01-08 + 10
- `company`（单家公司）→ 01-08 + 个股 buy_box

辅助产出：

- `findings_mat-XXXXXX.md`：每份原始资料的研究小组提炼笔记
- `_synthesis_brief.md`：04-synthesize 阶段的内部备忘
- `_glossary.md`：本 topic 的领域术语速查表（按字母 / 拼音排序）
- `_prism_reading_guide.md`：本篇

---

## 二、内部编号约定：mat-XXX / K# / R# / F# / KILL-#

后面 10 份产出会到处出现"看着像编号"的东西——外人完全无法 google。这里一次讲清。

### 2.1 `mat-XXXXXX`：资料编号

- 形如 `mat-9fb50a`、`mat-756a01`、`mat-c660fb`
- 是研究小组对每份原始资料（年报、10-Q、券商研报、新闻、专家访谈纪要）的内部 hash 编号
- **看到这个就知道"这句话有出处"**——要查原文去同目录的 `findings_mat-XXXXXX.md`
- **不会念也没关系**——编号本身无意义，只是为了让任意一句结论都能追到原始资料
- 父级复用资料（从 `parent_topic` 继承）跟自有资料用同一套命名空间

### 2.2 `K1`~`Kn`：Killer Questions（核心可证伪假设）

- 本研究的核心赌注。每个 K# 都有"看多 / 看空"的明确证伪条件
- **可观测、可证伪**——不能是"未来不确定"这种废话
- 看产出时，"K1 强度 +7→+5" 表示"原本看多 7 分，最新资料让我们降到 5 分"
- v0 版（开研究前的初判）vs v1 版（吃完资料后的修正）—— **变化幅度本身是信号**

### 2.3 `R1`~`Rn`：Risks（风险点）

- 把"可能让 thesis 破产"的风险逐条编号
- 在 `06_risk_blindspots.md` 里集中讲
- 每条 R# 必有"正方对照"——避免单边风险叙事

### 2.4 `F1`~`Fn`：Failure cases（失败案例）

- 拿历史上类似的"看起来一样但失败了"的案例做镜子
- 在 `05_historical_mirrors.md` 里
- 例子：钠电池泡沫、燃料电池泡沫、超导体泡沫——结构上相似但结果不同

### 2.5 `KILL-1`~`KILL-n`：Kill switches（清仓信号）

- 任何一条触发就要立刻减仓 / 清仓的硬信号
- 例子：`KILL-3 = SLDP 现金 runway 跌破 18 个月` 或 `KILL-5 = SMM 硫化物 SKU 价格半年下行 >30%`
- 是 KILL 不是 alert——触发就是触发，没有"再观察"

---

## 三、强度刻度：thesis 强度 ±N

prism 用 -10 到 +10 的连续刻度表示对一条 thesis 的看法：

| 刻度 | 含义 |
|------|------|
| **+10** | 极强看多，重仓 |
| **+7** | 较强看多，仓位但有限制 |
| **+3** | 偏多但需等更多催化 |
| **0** | 中性 |
| **-3** | 中性偏空 |
| **-7** | 较强看空 |
| **-10** | 极强看空 |

每个 K# / 主 thesis 都有自己的强度。`v0` 是开研究前的训练知识初判，`v1` 是吃完研究资料后的修正。**v0→v1 的变化幅度比 v1 的绝对值更重要**——大变化意味着资料发现了违背训练共识的新事实。

---

## 四、Topic 类型与 stage

### 4.1 Topic 类型

每个 topic 在 `topic.yaml` 里有 `type` 字段：

- `industry`：行业级研究，向下分多个 `arena` 子 topic
- `arena`：细分战场（产业链一环、技术路线、地域细分）
- `company`：单家公司

**含义**：
- industry 类的 07 不给个股 buy_box，会留到 arena / company 子 topic 里给
- arena 类的 07 也不给个股 buy_box，留到 `06_arena_*` 后续产出
- 只有 company 类的 07 才直接给 buy_box

### 4.2 Stage 状态机

`topic.yaml` 里的 `stage` 字段表示 topic 当前在 workflow 哪一步：

```
01-roadmap-pending → 02-roadmap-built → 03-materials-ingested →
04-post-synthesis → 05-finalized → 06-monitoring
```

- 看到 `04-post-synthesis` = 资料已合成出 01-08，但可能还没补 arena/peer
- 看到 `06-monitoring` = 研究阶段已结束，进入跟踪期
- `monitoring_tier`: `dormant`（休眠）/ `warm`（关注）/ `hot`（高频跟踪）

---

## 五、关键术语：thesis、What Would Have To Be True、coverage

### 5.1 Thesis

**= 本研究对这个 topic 的核心判断**。一句话能讲清，必须包含：

- 看多 / 看空 / 分化（不能是"不确定"）
- 强度刻度
- 关键时间窗
- 反方观点（否则不算 thesis）

### 5.2 What Would Have To Be True（WWHTBT）

借自巴菲特 / 芒格的反向思考：**"如果 thesis 成立，什么必须为真？"**

- 列 5 条可观测的必要条件
- 满足全部 = 基础情景成立
- 满足 ≤1 条 = thesis 破产
- 是 prism 把"看多 / 看空"转换成"具体可跟踪信号"的关键工具

### 5.3 Coverage

每个 K# 必须有"覆盖资料"——证明这条赌注的资料源是哪些。在 `topic.yaml` 末尾的 `Coverage 闭环` 表格里。

`coverage` 闭环未达标 = K# 是"无源之水"，不能用来支撑 thesis 强度。

---

## 六、推荐阅读路径

### 6.1 三档时间预算

| 时间 | 推荐读法 |
|------|---------|
| **5 分钟** | 只读 07_decision_kit.md 第一节"一页摘要" |
| **30 分钟** | 00_primer + 07_decision_kit + 08_living_feed |
| **2 小时（完整）** | 00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 09/10 → 08 |

### 6.2 按身份的不同推荐

- **完全外行 / 跨领域**：00_primer 必读 → 然后 07
- **行业熟手**：跳过 00，直接 03（叙事生态）+ 07（决策）
- **风险控制视角**：06（盲点）+ 07 第三节（KILL 体系）+ 08（监测）
- **估值视角**：04（implied expectations）+ 02（cycle 定位）

### 6.3 多 topic 联读

如果一个 topic 有 `parent_topic`（如 `global-ssb-electrolyte` 的 parent 是 `global-solid-state-battery`），**先读父 topic 再读子 topic** —— 父级的 K# 和 thesis 是子 topic 的前提。

---

## 七、来源边界：怎么判断"这是研究产出还是训练知识"

prism 产出会混合三种来源：

1. **LLM 训练知识**（行业基础概念、技术路线分类、加工工艺、产业链结构、政策框架）—— **稳定知识**，截止训练截止日
2. **本研究 findings**（每份产出里所有 `(mat-XXX)` 标注）—— **当前数据**，截止 `data_freshness`
3. **本研究的特色判断**（thesis 内容、强度刻度、特色叙事）—— **研究小组的 take**，会随 v0/v1/v2 演化

**读的时候识别这三层**：

- 看到"硫化物路线包括 LPSC、LPS、LGPS"→ 训练知识，稳定
- 看到"SLDP 与 SK On 协议隐含 ¥7,500/kg (mat-756a01)"→ 研究 finding，吃资料的产物
- 看到"叙事正在从 EV 迁移到 eVTOL"→ 研究 take，是判断不是事实

**最高优先级是 finding（带 mat-XXX 的具体数据）**——这是研究的最大价值；训练知识可以在任何 LLM 那里得到，但具体数据必须读资料才能拿到。

---

## 八、frontmatter 字段速查

每份产出顶部都有 YAML frontmatter，常见字段：

| 字段 | 含义 |
|------|------|
| `slug` | topic 唯一 slug |
| `output_key` | 产出文件 key（01_business_panorama 等） |
| `version` | 该产出的版本号（v1 / v2） |
| `generated` | 生成时间 |
| `data_freshness` | 资料最新时点（如 "2026-Q1"） |
| `data_freshness_basis` | 哪几份资料决定了这个时点 |
| `topic_type` | arena / industry / company |
| `audience` | 给谁读的（多见于 00_primer） |
| `prereq` | 阅读前置依赖 |

---

## 写在最后

本指南是"系统约定层"，不讲任何具体领域知识。如果你要研究的领域本身陌生，请先读对应 topic 的 `00_primer.md`；如果你想速查某个领域术语，请查 `_glossary.md`。

如果你看到一份产出里出现了本指南没解释的编号 / 缩写 / 强度刻度，那就是 prism 自己的不一致——欢迎反馈给研究小组修订。

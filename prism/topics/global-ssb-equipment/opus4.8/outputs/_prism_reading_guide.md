---
output_key: _prism_reading_guide
type: system-conventions
audience: prism 产出的所有读者（不限任何 topic）
canonical_source: prism/workflows/_reading_guide_canonical.md
note: 本文件是 canonical 模板，由 04-synthesize/00-primer.md Step 2.5 复制到各 topic 的 outputs/。修订系统约定请改本文件，不要改各 topic 的副本。
companion: 00_primer.md（领域入门）+ _glossary.md（领域术语速查，可选）
---

# prism 阅读指南：怎么看懂 prism 产出

> 不讲任何领域知识。只讲 prism 这个研究系统的内部约定——编号、强度刻度、产出体系、阅读路径。任何 topic 共用。第一次读 prism 产出、被 `mat-XXX` / `K1` / `thesis 强度 +7` 之类看不懂的编号挡住时，来这里查。

---

## 一、产出体系：每份产出在干什么

prism 一个 topic 的研究输出是**决策链三件套**——领域入门 + 一份成稿 case（6 个命门环）+ 一份机器消费 sidecar，外加一条追踪时间线：

| 产出 | 文件 | 一句话定位 | 何时读 |
|------|------|-----------|--------|
| **领域入门** | `00_primer.md` | 给完全外行建心智模型（讲领域本身，不讲投资判断） | 第一次看这个 topic |
| **成稿 case** | `c_investment_case` / `i_industry_case` / `a_arena_case`（按 type 三选一） | 决策链正文，6 个命门环串成完整论证（见下） | **核心产出，看一份就够时看这份** |
| **sidecar** | `07_decision_kit.yaml`（company）/ `09_industry_to_arenas.yaml`（industry）/ `10_peer_matrix.yaml`（arena） | case 的机器消费面：dashboard / kill / signpost / tier / 子战场选拔直接读它 | 要结构化结论（KILL/仓位/分流）时 |
| **追踪时间线** | `08_living_feed.md` | 接下来盯的时点 / 催化剂 / 监测信号 + 事件序列（06-daily / 99-decision 追加） | 决定"接下来盯什么" |

**成稿 case 的 6 个命门环**（按 topic.type 措辞略异，骨架一致）：
- 环① 业务/价值链卡位 → 环② **定价锚**（当前价/倍数反推隐含预期，数字最硬的一环）→ 环③ WWHTBT（什么必须为真）→ 环④ 横比/竞争格局 → 环⑤ 证伪与历史镜鉴 → 环⑥ 决策分流 / tier（company 给个股 buy_box；industry 切子战场；arena 给玩家矩阵）

辅助文件：`findings_mat-XXXXXX.md`（每份原始资料的提炼笔记）、`_synthesis_brief.md`（合成阶段内部备忘）、`_findings_index.md`（findings 轻索引）、`_glossary.md`（领域术语速查，可选）、`_prism_reading_guide.md`（本篇）。

> **遗留产出（旧 topic 才有）**：决策链重构前的 topic 产 `01_business_panorama … 07_decision_kit` 八份并列维度 markdown。这套已被成稿 case 取代、不再新产；看到老 topic 仍是这八份分箱时，对应关系：01-03 业务/周期/叙事 → case 环①④；04 隐含预期 → 环②③；05 历史镜子 → 环⑤；06 风险盲点 → 环⑤；07 决策工具箱 → sidecar。`08_living_feed` 不在遗留之列——它在新流程里仍是活的追踪线。

辅助文件：`findings_mat-XXXXXX.md`（每份原始资料的提炼笔记）、`_synthesis_brief.md`（合成阶段内部备忘）、`_findings_index.md`（findings 轻索引）、`_glossary.md`（领域术语速查，可选）、`_prism_reading_guide.md`（本篇）。

---

## 二、内部编号约定

### `mat-XXXXXX`：资料编号
形如 `mat-9fb50a`。研究小组对每份原始资料（年报/季报/10-K/券商研报/新闻/访谈）的内部 hash 编号。看到它 = "这句话有出处"，查原文去同目录 `findings_mat-XXXXXX.md`。编号本身无意义，只为让任意结论可溯源。父级复用资料（从 `parent_topic` 继承）与自有资料共用命名空间。

### `K1`~`Kn`：Killer Questions（核心可证伪假设）
本研究的核心赌注。每个 K# 有"看多/看空"的明确证伪条件，必须可观测、可证伪（不能是"未来不确定"这种废话）。产出里 "K1 强度 +7→+5" = "原本看多 7 分，最新资料降到 5 分"。v0（开研究前初判）vs v1（吃完资料后修正）——**变化幅度本身是信号**。

### `R1`~`Rn`：Risks（风险点）
"可能让 thesis 破产"的风险逐条编号，集中在 case 环⑤（证伪与风险）+ sidecar 的 kill/risk 字段。每条必有"正方对照"，避免单边风险叙事。

### `F1`~`Fn`：Failure cases（失败案例）
历史上"看起来一样但失败了"的案例做镜子，在 case 环⑤的历史镜鉴段。（与 PRISM_VALIDATION 报告里的 F# 编号无关，那是另一套缺陷编号。）

### `KILL-1`~`KILL-n`：Kill switches（清仓信号）
任一触发就立刻减仓/清仓的硬信号（如"现金 runway 跌破 18 个月"/"某价格半年下行 >30%"）。是 KILL 不是 alert——触发就触发，没有"再观察"。

---

## 三、强度刻度：thesis 强度 ±N / N分制

prism 用刻度表示对一条 thesis 的看法。两种常见表达：
- **±10 制**：+10 极强看多 / +7 较强看多但仓位有限 / 0 中性 / -7 较强看空 / -10 极强看空
- **N/10 制**：6/10 温和看多 / 5/10 中性偏多（company 类常用）

`v0` = 开研究前训练知识初判，`v1`/`v2` = 吃完资料/经 critic 后修正。**v0→v1 变化比 v1 绝对值更重要**——大变化意味着资料发现了违背训练共识的新事实。

---

## 四、Topic 类型与 stage

### 类型（`topic.yaml` 的 `type`）
- `industry`：行业级，向下分多个 arena 子 topic
- `arena`：细分战场（产业链一环 / 技术路线 / 地域细分）
- `company`：单家公司

含义：industry/arena 类的 07 不给个股 buy_box（留到子 topic）；只有 company 类 07 直接给 buy_box。

### Stage 状态机
```
01-roadmap → 02-materials → 03-findings → 04-synthesize →
04-post-synthesis → 05-critic-review → 06-monitoring → done
```
`monitoring_tier`: `dormant`（休眠）/ `warm`（关注）/ `hot`（高频）。

---

## 五、关键术语

- **Thesis**：本研究对这个 topic 的核心判断。一句话讲清，必含：看多/看空/分化 + 强度 + 关键时间窗 + 反方观点（没反方不算 thesis）。
- **What Would Have To Be True (WWHTBT)**：反向思考——"如果 thesis 成立，什么必须为真？"列若干可观测必要条件，满足全部=基础情景成立，满足≤1条=thesis 破产。把"看多/看空"转成"可跟踪信号"的工具。
- **Coverage**：每个 K# 必须有"覆盖资料"证明其有据。coverage 未达标 = K# 是无源之水，不能支撑强度。
- **SOTP（Sum of the Parts）**：分部加总估值。把每块业务/每条管线单独估值再加总，常用于多元化公司 / biotech（管线 NPV）。
- **扣非净利**：剔除非经常性损益（一次性 BD 收入、金融资产浮盈等）后的真实主业利润——看盈利质量的关键指标。

---

## 六、推荐阅读路径

| 时间 | 读法 |
|------|------|
| **5 分钟** | 只读 case 环⑥（决策分流 / tier）+ sidecar 摘要 |
| **30 分钟** | 00_primer + 成稿 case 全文 + 08_living_feed |
| **2 小时（完整）** | 00_primer → case 环①→②→③→④→⑤→⑥ → sidecar → 08_living_feed |

按身份：
- **完全外行/跨领域** → 00_primer 必读 → 然后 case 环⑥
- **行业熟手** → 跳过 00，直接 case 环②（定价）+ 环⑥（决策）
- **风控视角** → case 环⑤（证伪/风险）+ sidecar 的 KILL/signpost + 08_living_feed
- **估值视角** → case 环②（定价锚/隐含预期）+ 环③（WWHTBT）

**多 topic 联读**：若 topic 有 `parent_topic`，先读父 topic 再读子 topic（父级 K# 和 thesis 是子 topic 前提）。

---

## 七、来源边界：怎么判断"研究产出 vs 训练知识"

prism 产出混合三种来源，读时识别：
1. **LLM 训练知识**（行业原理/技术分类/工艺/估值方法/政策框架）——稳定知识，截止训练截止日，不标单条出处
2. **本研究 findings**（带 `(mat-XXX)` 的具体数据）——当前数据，截止 `data_freshness`
3. **本研究特色判断**（thesis 内容/强度/特色叙事）——研究小组的 take，随 v0/v1/v2 演化

**最高价值是带 mat-XXX 的 finding**——训练知识任何 LLM 都给得出，具体数据必须读资料才有。看到 "X 路线包括 A、B、C" = 训练知识；"某协议隐含 ¥7500/kg (mat-XXX)" = finding；"叙事正从 A 迁移到 B" = 研究 take（判断不是事实）。

---

## 八、frontmatter 字段速查

| 字段 | 含义 |
|------|------|
| `slug` / `output_key` / `version` | topic / 产出 key / 版本 |
| `generated` | 生成时间 |
| `data_freshness` / `data_freshness_basis` | 资料最新时点 / 哪几份资料决定 |
| `topic_type` / `audience` / `prereq` | 类型 / 读者 / 阅读前置 |
| `depth`（仅 00_primer） | deep / shallow——shallow 表示本领域 LLM 训练知识有限，背景可靠性低 |

---

## 写在最后

本指南是"系统约定层"，不讲任何领域知识。领域陌生先读该 topic 的 `00_primer.md`；速查领域术语查 `_glossary.md`。看到本指南未解释的编号/缩写/刻度，那是 prism 自身不一致——反馈给研究小组修订（改 `prism/workflows/_reading_guide_canonical.md`）。

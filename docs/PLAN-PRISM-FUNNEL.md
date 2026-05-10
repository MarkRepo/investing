# PLAN — Prism 漏斗化改造

> **依据**：用户对 prism 系统的 4 个核心使用目的（见 §1），与对应的 7 个断点诊断。
> **定位**：把 prism 从"8 份独立产出 × N 个孤立 topic"改造成"industry → arena → company → decision"四级漏斗 + 跨 topic 知识沉淀。
> **不做**：context graph 全量基础设施、跨主题双向遍历、可视化图谱（YAGNI 已论证）。
> **版本**：2026-05-10 · v1.0

---

## 1. 战略锚 — 用户目的

prism 的使用方式不是"通用研究工具"，而是一条具体的投资工作流：

| # | 用户目的 | prism 当前覆盖 | 主要缺口 |
|---|---|---|---|
| 1 | 积累 industry / arena 知识 | 单 topic 内 8 份产出齐全 | 跨 topic 不互通；无 freshness 管理 |
| 2 | 找 arena/赛道级大机会 | 单 arena 研究质量可以 | 无 industry → arena 选拔产出；无跨 arena 比较 |
| 3 | 筛公司标的 | 03 narrative 提到龙头 | 无 arena → company peer matrix；无质量红线过滤 |
| 4 | 深研标的、判断买入 | 06/07/99 骨架完整 | 04 缺反推估值数学；07 缺买入框；99 缺 alternatives；05 有幸存者偏差 |

**结论**：prism 8 份产出方法论本身没问题，**断点都在 stage 之间和层级之间**，需要 7 件 spec/template 改动加最小化数据模型扩展。

---

## 2. 当前断点诊断（速览）

按"漏斗位置"映射：

```
[研究完 industry]                               ← 缺 1.1 industry_to_arenas（断点 1）
        │
        ▼
[决定深挖某 arena]
        │
        ▼
[研究完 arena]                                  ← 缺 1.2 peer_matrix（断点 2/3）
        │
        ▼
[挑出 N 家候选 company]
        │
        ▼
[进入 company 研究]                             ← 缺 1.3 quality_screen 红线（断点 4）
        │
        ▼
[company 8 份产出]                              ← 04 缺反推数学（断点 5）
                                                ← 05 缺失败镜像（断点 6）
                                                ← 07 缺买入框（断点 7）
        │
        ▼
[99 决策记录]                                   ← 缺 alternatives（断点 8）
        │
        ▼
[持仓 + monitor]                                ← 缺跨层假设链（断点 9）
```

**Phase 1 修 1/2/3**（漏斗 gate）；**Phase 2 修 5/6/7/8**（决策硬度）；**Phase 3 修 9 + 知识沉淀**（跨 topic 与 freshness）；**Phase 4 出横向视图与轻量 depends_on**。

---

## 3. 范围

**In scope**：
- 新增 / 修改 `prism/workflows/` 下 7 份 spec
- 新增 3 份模板（`prism/templates/`）
- 扩展 `prism/scripts/topic.py` schema（增 `concepts`、`monitoring_tier`、`data_freshness`、`depends_on` 字段）
- 新增 `prism/scripts/concepts.py`（跨 topic 概念索引）
- 新增 `app/routes/prism.py` 一个横向比较视图

**Out of scope**：
- 全量 context graph（节点 / 边 / propagate / inherit / 8 种边类型）
- 自动事件 / 财务数据爬虫（沿用现有 fetch_report / fetch_financials）
- LLM 评分自动化（沿用 critic-review 人在回路）
- 可视化图谱页（D3 / vis.js 之类，不做）
- 多 variant 横向比较（已有评估 ad-hoc 即可）

---

## 4. Phase 0 · 数据模型扩展（前置依赖，半天）

> **前提**：所有 Phase 1-4 都依赖 topic.yaml schema 升级。先做这一步，且必须向后兼容（旧 topic 可读、读出来时缺字段补默认值）。

### 4.1 topic.yaml 新增字段

| 字段 | 类型 | 默认 | 用途 | 来自 |
|---|---|---|---|---|
| `parent_topic` | str / null | null | 漏斗上层 topic slug（如 arena 节点指向 industry slug） | Phase 1 |
| `monitoring_tier` | enum | `dormant` | `deep` / `watch` / `dormant`：研究深度档位 | Phase 3 |
| `concepts` | list[str] | `[]` | 本 topic 涉及的概念 tag（"锂电池"、"星座建设"） | Phase 3 |
| `outputs_state[*].data_freshness` | str / null | null | 该产出依赖的最新数据日期（"2026-Q1"） | Phase 3 |
| `outputs_state` | 增 4 个 key | — | 见下 | Phase 1/2 |

新增 4 个 output key（不是所有 type 都启用）：

| key | 启用 type | 来源 |
|---|---|---|
| `09_industry_to_arenas` | industry only | Phase 1.1 |
| `10_peer_matrix` | arena only | Phase 1.2 |
| `00_quality_screen` | company only | Phase 1.3 |
| `assumptions` | 所有 type | Phase 4.2 |

**注意**：`outputs_state` 的 keys 现在按 topic.type 动态生成。`create_topic` 要根据 `topic_type` 决定哪些 output key 进 state。

### 4.2 改动文件

- `prism/scripts/topic.py`：
  - `_OUTPUT_KEYS` 改为 `_outputs_for_type(topic_type) -> list[str]`：
    - industry: `01..08, 09_industry_to_arenas`
    - arena: `01..08, 10_peer_matrix`
    - company: `00_quality_screen, 01..08`
  - `create_topic` 接受 `parent_topic`、`concepts`、`monitoring_tier` 参数
  - `read_topic` 向后兼容：读到旧文件时补 `monitoring_tier=dormant, concepts=[], parent_topic=null, data_freshness=null`
  - 新增 `set_concepts(slug, variant, concepts: list[str])`、`set_monitoring_tier(slug, variant, tier: str)`、`set_data_freshness(slug, variant, output_key: str, date: str)`
- `prism/templates/topic.yaml.tmpl`：增上述字段（默认值）
- `prism/scripts/manifest.py`：无改动
- `app/routes/prism.py`：UI 主页读 `monitoring_tier`、`data_freshness` 显示徽标

### 4.3 stage 状态机重画

旧 stage：`00-init → 01-roadmap-pending → 02-gathering → 03-extracting → 04-synthesizing → done`

新 stage（按 type 分支）：

```
industry:
  00-init → 01-roadmap → 02-gathering → 03-extracting → 04-synthesizing
            → 09-arena-shortlist → done

arena:
  00-init → 01-roadmap → 02-gathering → 03-extracting → 04-synthesizing
            → 10-peer-matrix → done

company:
  00-init → 01-roadmap → 02-gathering → 03-extracting
            → 00-quality-screen → (PASS) → 04-synthesizing → done
                                → (FAIL) → quarantined
```

**实现**：在 `prism/scripts/topic.py` 加 `next_stage(topic_type, current_stage) -> str` 函数集中维护。

### 4.4 验收
- [ ] 旧 topic.yaml（缺新字段）能正常读出，UI 不崩
- [ ] 新建 industry topic 时 `outputs_state` 含 `09_industry_to_arenas`，不含 `10_peer_matrix` 和 `00_quality_screen`
- [ ] `set_data_freshness('cn-commercial-space', 'sonnet', '01_business_panorama', '2026-Q1')` 写入 yaml 后能被 UI 读出

**工程量**：~150 行改动 + 单测，半天。

---

## 5. Phase 1 · 漏斗 gate 三件（★★★★★，2-3 天）

直接对应用户目的 2 和 3。**完成这 Phase 后用户已经可以从 industry 走到 candidate company 名单**。

### 5.1 Industry → Arenas 选拔（解决断点 1）

**对应目的**：找 arena 级大机会  
**新文件**：
- `prism/workflows/04-synthesize/09-industry-to-arenas.md` — workflow spec
- `prism/templates/industry_to_arenas.md.tmpl` — 产出模板

**触发**：industry topic 完成 01-08 后，stage 自动到 `09-arena-shortlist`。

**产出结构（industry_to_arenas.md.tmpl）**：

```markdown
---
slug: {slug}
output_key: 09_industry_to_arenas
version: {N}
generated: {timestamp}
---

# {industry} → 细分 Arena 选拔

## Arena 候选清单（≥ 5 个）

| Arena 名 | 利润池规模 | 增速预期 | 竞争结构 | 估值水位 | 周期位置 | 综合评分 | 决定 |
|---|---|---|---|---|---|---|---|
| {名} | {亿元} | {%} | CR3={X}% | 高/中/低 | 早/中/晚 | 1-5 | 深挖/观察/淘汰 |

## 评分维度说明
- **利润池规模**：当前及 5 年期 arena 总利润池（亿元，区间）
- **增速预期**：3 年 CAGR
- **竞争结构**：CR3 / 是否有自然垄断 / 是否同质化
- **估值水位**：当前 PE/PS 相对该 arena 历史 + 全球 peer
- **周期位置**：早期成长 / 中段加速 / 晚期分化 / 成熟饱和
- **综合评分**：1-5（5 = 最值得深挖）

## 入选深挖（深挖档）
对每个 Arena：
- 入选理由（一段话，≤ 100 字）
- 预期可获得的关键洞见
- 触发开 arena topic 的具体动作

## 进入 watchlist（观察档）
对每个 Arena：
- 暂不深挖的理由
- 升档触发条件（什么数据/事件出现就升级到 deep）
- 监控指标 1-2 个

## 淘汰记录（淘汰档）
对每个 Arena：
- 淘汰理由（≤ 50 字）
- 复活条件（如有）

## 信息来源
- 训练知识占比约 {X}%
- 引用 industry topic 的产出 01-08 + findings_mat
```

**spec workflow（09-industry-to-arenas.md）关键步骤**：
1. 前置检查：`type==industry` 且 01-08 全 fresh
2. 读取本 topic 的 01-08，提取 arena 信号
3. 至少识别 5 个细分 arena，按 6 维评分
4. 强制三档分流：深挖 / 观察 / 淘汰，每档至少有 1 项
5. 写入 `outputs/09_industry_to_arenas.md`
6. 自动从"深挖档"创建 stub arena topic（询问用户后）：
   ```bash
   python -c "
   from prism.scripts.topic import create_topic
   create_topic(slug='cn-{arena_slug}', topic_type='arena', parent_topic='{industry_slug}', ...)
   "
   ```
7. 自动从"观察档"加 arena 到 monitoring_tier=watch（不创建完整 topic，仅在 industry 的 yaml 里登记）

**验收**：
- [ ] industry topic 跑完 09 后，文件存在且至少 5 个 arena
- [ ] 至少有 1 个深挖、1 个观察、1 个淘汰
- [ ] 深挖档 arena 创建 stub topic 时 `parent_topic` 字段正确指向 industry
- [ ] /prism/{industry-slug} 主页显示 9 份产出（08 → 09 链路）

**工程量**：~300 行 spec + 100 行模板 + 50 行 topic.py 衍生逻辑，1 天。

---

### 5.2 Arena → Peer Matrix 横向矩阵（解决断点 2/3）

**对应目的**：筛公司  
**新文件**：
- `prism/workflows/04-synthesize/10-peer-matrix.md`
- `prism/templates/peer_matrix.md.tmpl`

**触发**：arena topic 完成 01-08 后，stage 到 `10-peer-matrix`。

**产出结构（peer_matrix.md.tmpl）**：

```markdown
---
slug: {slug}
output_key: 10_peer_matrix
version: {N}
generated: {timestamp}
---

# {arena} 公司对比矩阵

## 候选公司全集（≥ 5 家）

| 公司 | Ticker | 业务结构 | 收入规模 | 3Y ROIC | 毛利率 | 资产负债率 | 当前 PE | 历史 PE 区间 | 技术路线 | 客户结构 | 管理层信号 | 综合 | 短名单 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| {公司} | {代码} | {一句话} | {亿} | {%} | {%} | {%} | {x} | {x-y} | {主线} | {B/C/政府} | 看好/中性/警示 | 1-5 | ✓/✗/观察 |

## 评分逻辑（≤ 5 句话）
- 用什么权重组合得到综合评分
- 哪些维度是 hard filter（不达标直接淘汰）
- 哪些维度是软评分

## Top-N 短名单（深研档）
对每家入选公司：
- 入选理由（业务卡位 + 估值 + 催化剂，3 句话）
- 预期 thesis 一句话："如果 X 成立则 Y 实现 Z 回报"
- 下一步：开 company topic / 等数据 / 等估值

## Watchlist（观察档）
对每家：
- 暂不深研的理由
- 触发深研的具体条件（"如果 H1 季报 ROIC > 12%"，"如果股价跌至 X 元"）

## 淘汰记录
对每家：
- 淘汰主因（一句话，可重复使用："ROIC 持续 < WACC"、"质押率过高"）
- 是否进入 quarantine.md 永久归档

## 数据来源
- 财务数据：来自 `financials_cn` / `financials_us` 表（`scripts.fetch_financials`）
- 业务结构 / 客户：来自 findings_mat
- 训练知识占比约 {X}%
```

**spec workflow（10-peer-matrix.md）关键步骤**：
1. 前置检查：`type==arena` 且 01-08 全 fresh
2. 从 01 panorama / 03 narrative 抽提候选公司 ≥ 5 家
3. 对每家公司调用 `python -m scripts.fetch_financials_cn {ticker}` 拉财务（如可拉），财务数据填入矩阵
4. 强制三档：深研 / 观察 / 淘汰
5. 写入 `outputs/10_peer_matrix.md`
6. 自动询问用户："要不要为深研档创建 company topic？" → 创建并设置 `parent_topic={arena_slug}`

**验收**：
- [ ] arena topic 跑完 10 后矩阵 ≥ 5 家
- [ ] 至少 3 家有真实财务数据（其余可 N/A 但需说明）
- [ ] 短名单和 watchlist / 淘汰都至少各 1 家
- [ ] 创建 company stub topic 时 `parent_topic` 正确

**工程量**：~250 行 spec + 100 行模板，1 天。

---

### 5.3 Company 入口质量红线（解决断点 4）

**对应目的**：筛公司、深研  
**新文件**：
- `prism/workflows/03b-quality-screen.md`（位置：在 03-extract-findings 和 04-synthesizing 之间）
- `prism/templates/quality_screen.md.tmpl`

**触发**：company topic 完成 03-extracting 后，stage 到 `00-quality-screen`，必须通过才能进 04。

**红线 checklist**（写入 `00_quality_screen.md`）：

```markdown
---
slug: {slug}
output_key: 00_quality_screen
generated: {timestamp}
verdict: pass | fail | needs-review
---

# {company} 质量红线检查

## 自动数据红线（来自 fetch_financials）

| 红线 | 阈值 | 当前值 | 状态 |
|---|---|---|---|
| ROIC vs WACC | ROIC > WACC（最近 3 年） | {%} vs {%} | ✓/✗ |
| 自由现金流 | 最近 3 年 ≥ 2 年为正 | {亿} | ✓/✗ |
| 资产负债率 | 行业内非 outlier（< 行业 90 分位） | {%} | ✓/✗ |
| 商誉占净资产 | < 30% | {%} | ✓/✗ |
| 经营现金流 / 净利润 | 3 年均值 > 0.7 | {x} | ✓/✗ |

## 治理红线（来自 findings_mat 抽提）

| 红线 | 状态 | 备注 |
|---|---|---|
| 大股东质押率 < 50% | ✓/✗ | |
| 审计意见标准无保留 | ✓/✗ | |
| 关联交易占比 < 20% | ✓/✗ | |
| 无重大违规 / 立案调查 | ✓/✗ | |
| 高管 3 年内大额减持 | ✓/✗ | |

## 业务红线

| 红线 | 状态 | 备注 |
|---|---|---|
| 主业明确（CR1 > 50%）或多元化合理 | ✓/✗ | |
| 客户集中度可接受（CR5 < 80%） | ✓/✗ | |
| 无明显商业模式过气信号 | ✓/✗ | |

## 综合判定

- **PASS**：所有红线通过 / 不通过项 ≤ 1 且非致命 → 进入 04 完整研究
- **FAIL**：致命红线（财务造假迹象 / 重大违规 / ROIC 长期 < WACC）任一触发 → 归档到 `prism/quarantine/{slug}.md`，stage = `quarantined`
- **NEEDS-REVIEW**：1-2 项红线不通过但非致命 → 用户决定是否豁免

## 决策（强制）

verdict: {pass / fail / needs-review}
理由（≤ 100 字）：{一段话}
豁免项（如有）：{列出豁免红线 + 理由}
```

**spec workflow 关键步骤**：
1. 前置检查：`type==company` 且 03-extracting 完成
2. 调用 `fetch_financials_cn / fetch_financials_us` 拉数据
3. 自动填入"自动数据红线"行
4. 治理 / 业务红线由 LLM 从 findings 抽提
5. AskUserQuestion：是否豁免 needs-review 项 / 是否归档
6. PASS → set_stage 到 04，FAIL → set_stage 到 quarantined 并写 `prism/quarantine/{slug}.md`

**验收**：
- [ ] 一家 ROIC < 0、商誉超 50% 的公司能被自动判定 fail
- [ ] 一家完全干净的公司能 pass 直进 04
- [ ] 归档逻辑写入 `prism/quarantine/{slug}.md` 留半年后复盘

**工程量**：~200 行 spec + 100 行模板 + 50 行 fetch_financials 集成，1 天。

---

### 5.4 Phase 1 总验收（漏斗端到端）

跑通一遍真实场景：
- [ ] 已有 industry topic `cn-commercial-space` 跑出 09_industry_to_arenas（≥ 5 arena 候选）
- [ ] 从短名单创建 1 个 arena topic，跑完 01-08，再跑出 10_peer_matrix（≥ 5 公司）
- [ ] 从 peer_matrix 短名单创建 1 个 company topic，跑 03 后 00_quality_screen 给出 verdict
- [ ] 全程不需要用户手工创建 yaml / 手工拷贝资料 / 手工记淘汰理由
- [ ] /prism 主页能看清楚三层 topic 的父子关系

---

## 6. Phase 2 · 决策硬度四件（★★★★，2 天）

直接对应用户目的 4。**完成这 Phase 后筛出来的标的能进入"敢下判断"的研究质量**。

### 6.1 04 implied_expectations 三档分支（断点 5）

**对应目的**：深研买入决策  
**改动文件**：`prism/workflows/04-synthesize/04-expectations.md`

把现有 spec 拆成三个章节，按 `topic.type` 分支：

#### industry 版（保持现状基础上改）
- 反推对象：行业总盈利池 × 隐含 PE → 隐含 3 年 CAGR
- 与历史增速 / 全球 peer 对比

#### arena 版（新增）
- 反推对象：arena 利润池 × 龙头隐含市占率 → 是否合理
- 必须做：利润池迁移分析（这个 arena 价值正在从哪段往哪段迁）

#### company 版（重点强化）
- **必产**：反推 DCF 表（基础情景）
  - 输入：当前股价 / 流通市值 / 当前营收 / 当前净利率 / 折现率假设
  - 反推：未来 3-5 年 CAGR 假设 / 终值假设 / 隐含 IRR
- **必产**：同业反推对比（peer matrix 取 3-5 家）
  - 同样反推方法应用到同业，看本标的隐含假设相对同业是 cheap / fair / expensive
- **必产**：5 级光谱（保留原结构）+ 每档对应一个反推数学结果
  - 例：Bull = "假设 25% CAGR + 终值 PE 25" → 当前价 + 50%
  - 例：Bear = "假设 5% CAGR + 终值 PE 12" → 当前价 - 30%

**关键设计**：在 spec 里直接给出反推 DCF 的最简模板（5 行 Python 注释级别即可，不写实现）：
```
implied_cagr = lambda P, E0, terminal_PE, r, years: solve P = E0 * (1+g)**years * terminal_PE / (1+r)**years for g
```

**验收**：
- [ ] 一家 PE=30 的 company topic 跑出来后，04 必须有具体反推 CAGR 数字（而不是"乐观"二字）
- [ ] 5 级光谱每档都有一行数学，不能只给标签
- [ ] 同业对比表至少 3 家

**工程量**：~150 行 spec 重写，半天。

---

### 6.2 05 historical_mirrors 对偶强制（断点 6）

**对应目的**：深研买入、治幸存者偏差  
**改动文件**：`prism/workflows/04-synthesize/05-mirrors.md`

在现有 "Step 1：识别 3-5 个历史类比" 之后强制加一节：

```markdown
## Step 1.5：失败镜像（强制 ≥ 2 个）

找 ≥ 2 个"曾经也长得像今天的标的，但最终失败"的历史案例：

### 失败案例：{名}{年代}
**当年的相似性**（哪里和今天像）：
- 叙事相似度
- 估值水位相似度
- 政策 / 资金面相似度

**最终结局**：
- 失败模式：{颠覆 / 周期顶 / 政策反转 / 现金流断裂 / 竞争击穿 / ...}
- 损失幅度（峰谷跌幅）
- 触发崩塌的具体事件

**对当前的警示**：
- 当年最早的预警信号是什么
- 现在是否已经出现类似信号
- 如果出现，如何应对

## Step 2：综合（必须包括对偶平衡）
- 成功镜像若实现，回报区间：+ X% 到 + Y%
- 失败镜像若实现，损失区间：- X% 到 - Y%
- 现在更像哪一类，理由（≤ 200 字）
```

**关键约束**：spec 里写明"如果你只能想到成功案例，写'我没找到合适的失败案例'本身就是 red flag，应当 stop 并要求用户补失败案例资料"。

**验收**：
- [ ] 跑完 05 后必须有 ≥ 2 个失败案例
- [ ] 失败案例不能是"虚构"或泛指（必须有国家+行业+年代）
- [ ] 综合段必须包含成功 / 失败两个区间

**工程量**：~50 行 spec 增量，2 小时。

---

### 6.3 07 decision_kit 加买入框（断点 7）

**对应目的**：深研买入  
**改动文件**：`prism/workflows/04-synthesize/07-decision-kit.md`

在现有 "2.4 研究成熟度评估" 之前插入新节：

```markdown
## 2.3.5 买入框（仅 company type）

> 必须基于产出 04 的反推估值结果填写。

| 项 | 数值 | 依据 |
|---|---|---|
| 当前价 | {元} | 报告日 |
| 反推合理价中枢 | {元} | 04 base 情景 |
| 强力买入区间（IRR ≥ 15%） | {元} - {元} | 04 base + 安全边际 20% |
| 加仓区间 | {元} - {元} | 04 bear 情景边界 |
| 止损 / Kill 触发价 | {元} 或 N/A | 06 kill criteria 价格化 |

### 仓位框架
- **首仓上限**：组合的 {X}%（理由：catalyst 距离 / 信息确信度 / 流动性）
- **满仓上限**：组合的 {Y}%
- **加仓阶梯**：每跌 {Z}% 加 {W}%，最多 {N} 阶
- **集中度约束**：与已持仓 {名单} 相关性高，三者合计不超过 {M}%

### 时间维度
- **预期持有期**：{N} 个月 / 季度 / 年
- **下一关键 catalyst 时点**：{YYYY-MM}
- **若到 {YYYY-MM} 未发生 X，应**：{加仓 / 减仓 / 退出 / 重新评估}
```

**验收**：
- [ ] 任一 company topic 跑出 07 必须有买入框，且数值必须从 04 引用而非凭空
- [ ] 仓位上限必须给出具体百分比
- [ ] industry/arena 的 07 不要求买入框（仍然给 signposts 即可）

**工程量**：~80 行 spec 增量，2 小时。

---

### 6.4 99 决策记录加 alternatives（断点 8）

**对应目的**：深研买入 + 事后归因  
**改动文件**：`prism/workflows/99-decision-record.md`

在现有 "## 我知道自己不知道的事情" 之前插入：

```markdown
## 同时考虑过的替代标的（强制 ≥ 2 个）

> 来源：从本 company topic 的 `parent_topic` arena 的 `10_peer_matrix.md` 短名单 + watchlist 抽取。

### 替代 1：{公司名} ({ticker})
- 排序优势：{相对本标的什么更好}
- 排序劣势：{相对本标的什么更差}
- 拒绝主因：{≤ 30 字}
- 升档触发：{什么情况下应转向这个标的}

### 替代 2：...

### 排他性检查
- 有没有可能"两个都买"而不是二选一？{是 / 否，理由}
- 是否存在 pair trade 机会（多 A 空 B）？{是 / 否，结构}

## 半年后复盘约定
- 记录决策日 {N+180} 天后强制对照本标的 vs 替代标的实际涨跌
- 复盘文件：`prism/topics/{slug}/{variant}/outputs/decision_review_{YYYYMMDD}.md`
```

**还要在 99 末尾加约定 cron**：

```bash
# 决策日 + 180 天提醒（写入 user_todos）
python -c "
from datetime import datetime, timedelta
from prism.scripts.topic import set_user_todos
review_date = (datetime.now() + timedelta(days=180)).date().isoformat()
set_user_todos('{slug}', ['{review_date}: 决策半年复盘 - 对比本标的 vs 替代标的实际表现'], '{variant}')
"
```

**验收**：
- [ ] 99 决策必须列出 ≥ 2 个替代标的，且每个有具体拒绝理由
- [ ] user_todos 自动加入半年后复盘提醒

**工程量**：~80 行 spec 增量，2 小时。

---

### 6.5 Phase 2 总验收

跑通一个 company 标的的完整深研：
- [ ] 04 隐含预期含真实反推 CAGR 数字 + 同业对比
- [ ] 05 镜鉴含 ≥ 2 个失败案例
- [ ] 07 决策包含买入框（具体价格区间 + 仓位百分比）
- [ ] 99 决策记录含 ≥ 2 个替代标的拒绝理由
- [ ] user_todos 含 180 天复盘提醒

---

## 7. Phase 3 · 知识沉淀三件（★★★，2-3 天）

直接对应用户目的 1。**完成这 Phase 后跨 topic 知识能复用、能查 freshness**。

### 7.1 concepts.yaml 跨 topic 标签（解决知识互通）

**新文件**：
- `prism/concepts.yaml` — 概念定义（受控词表）
- `prism/scripts/concepts.py` — 读写 + 查询

**concepts.yaml 结构**：

```yaml
# Prism 概念索引（受控词表）
# 每个概念是跨 topic 复用的 tag
concepts:
  - name: 锂电池
    aliases: [动力电池, 锂离子电池]
    description: 二次锂离子电池产业链
    related_concepts: [储能, 新能源车, 上游锂资源]

  - name: 商业航天
    aliases: [民营航天, 商业火箭]
    description: 中国 / 全球非国家队的商业化航天
    related_concepts: [GW 星座, 千帆星座, 卫星互联网]

  - name: 信用利差
    description: 高低评级债券收益率差，宏观信号
    related_concepts: [流动性, 风险偏好]
```

**concepts.py API**：

```python
def list_concepts() -> list[dict]: ...
def add_concept(name: str, aliases: list[str], description: str): ...
def find_topics_by_concept(concept: str) -> list[dict]:
    # 扫描所有 topic.yaml 的 concepts 字段
def find_concepts_in_topic(slug: str, variant: str) -> list[str]: ...
```

**集成点**：
- workflow 00-research-topic 在创建 topic 时建议 3-5 个相关 concepts，写入 `topic.yaml.concepts`
- workflow 01-build-roadmap 完成后再修订一次 concepts
- /prism/concepts/{name} 页面列出所有挂这个 concept 的 topic

**验收**：
- [ ] 创建 cn-storage topic 时自动建议挂 "锂电池" concept
- [ ] /prism/concepts/锂电池 列出 cn-catl / cn-storage / cn-ev 等所有相关 topic（含 variant）
- [ ] 跨 topic 搜索 "锂电池" 能命中所有相关 finding

**工程量**：~200 行 Python + 一个 web view，1 天。

---

### 7.2 monitoring_tier 三档监控（解决"研究预算"）

**对应目的**：找 arena 大机会 + 知识广度  
**改动文件**：
- `prism/scripts/topic.py` — 字段已在 Phase 0 加好
- `prism/workflows/06-daily-monitor.md` — 改造为按 tier 不同 cadence

**三档定义**：

| Tier | 含义 | 触发 monitor | 需要的 outputs |
|---|---|---|---|
| `deep` | 持仓 / 候选标的 | 每日 + 重大事件 | 全 8/9/10 份 |
| `watch` | 值得关注但暂不投 | 每周 | 仅 01 + 02 + 06 |
| `dormant` | 历史归档 / 完成研究 | 不主动 | 全部，但不 refresh |

**Workflow 06-daily-monitor.md 改造**：

```markdown
## Step 1：按 tier 选择今日要扫的 topic

```bash
python -c "
from prism.scripts.topic import list_all_topics
import datetime
today = datetime.date.today()
deep = [t for t in list_all_topics() if t['monitoring_tier']=='deep']
weekly = [t for t in list_all_topics() if t['monitoring_tier']=='watch' and today.weekday()==1]  # Tuesday
for t in deep + weekly:
    print(t['slug'], t['monitoring_tier'])
"
```

## Step 2：对每个待扫 topic 执行轻量监控
（沿用现有逻辑）
```

**验收**：
- [ ] watchlist arena 不会被每日 monitor 打扰
- [ ] /prism 主页按 tier 分组显示
- [ ] 用户可在 UI 上快速切换 tier

**工程量**：~100 行改动，半天。

---

### 7.3 data_freshness 时间戳（解决"研究过期"）

**对应目的**：知识积累不衰减  
**改动**：所有 8 份 synthesize spec 加要求

每份产出 frontmatter 强制加 `data_freshness` 字段：

```markdown
---
slug: ...
output_key: ...
version: ...
generated: 2026-05-10T...
data_freshness: 2026-Q1   # ← 新增：本产出依赖的最新数据所在期
data_freshness_basis: "财务数据 2026Q1 / 行业数据 2026-04 / 政策 2026-03"   # ← 解释
---
```

**spec 改造**：在每份 04-synthesize/0X-*.md 的 "Step 写入文件" 之前加：

```markdown
## Step N.5：填写 data_freshness

在 frontmatter 写入：
- 用到的最晚数据所在期（季度 / 月份）
- basis 说明该期来自哪份 finding
```

**UI 集成**：
- /prism 主页每个 topic 卡片显示最旧 freshness
- 超 6 个月红色徽标 "⚠ 需要 refresh"
- 超 12 个月灰色 "📦 已归档"

**验收**：
- [ ] 现有所有 topic 的所有产出都填了 freshness（手工 backfill 一次）
- [ ] /prism 主页能按 freshness 排序
- [ ] 红色徽标在 freshness 超阈值时正确显示

**工程量**：~50 行 spec 增量 + 30 行 UI，半天。

---

## 8. Phase 4 · 横向视图与轻量假设链（★★，1-2 天）

可选项，建议跑过 Phase 1-3 一个完整 cycle 后再决定是否做。

### 8.1 /prism/arenas 横向比较页

**新文件**：
- `app/routes/prism.py` 增 `/prism/arenas` route
- `app/templates/prism/arenas.html`

**页面内容**：

| Arena slug | 父 industry | tier | implied IRR (来自 04 base) | 当前 cycle 位置 (来自 02) | 最大盲点 (来自 06) | 下一 catalyst (来自 07) | freshness |
|---|---|---|---|---|---|---|---|

支持按列排序，按 tier 过滤。

**验收**：
- [ ] 已有的 cn-commercial-space (industry) + 任意 arena 能在该页一览
- [ ] 排序正确

**工程量**：~150 行 Python + 模板，半天。

---

### 8.2 assumption depends_on（轻量版，限漏斗内）

**对应目的**：跨层假设传染（断点 9）  
**注意**：这是 context graph 想法的最小版本。**只做 industry → arena → company 这条直链**，不做通用图。

**改动**：

#### 8.2.1 topic.yaml 加 assumptions 字段

```yaml
assumptions:
  - id: a1
    text: "中国商业航天 2027 年发射次数 ≥ 200"
    status: fresh   # fresh | stale | falsified
    depends_on: []  # parent topic 的 assumption id，如 ["industry:cn-aerospace:a3"]
  - id: a2
    text: "蓝箭朱雀三号 2026 H2 首飞"
    status: fresh
    depends_on: ["arena:cn-private-rocket:a5"]
```

#### 8.2.2 assumption.py 提供操作

```python
# prism/scripts/assumptions.py
def add_assumption(slug, variant, text, depends_on: list[str] = None) -> str: ...
def mark_falsified(slug, variant, assumption_id, reason): ...
def find_downstream(slug, variant, assumption_id) -> list[dict]:
    """返回所有 depends_on 这个 assumption 的下游 topic+assumption"""
def propagate(slug, variant, assumption_id):
    """把所有下游 assumption 标 needs_review，并 append 到下游的 08_living_feed"""
```

#### 8.2.3 集成

- 04 / 06 / 07 spec 末尾加 "## Step N+1：登记本产出的核心假设"，要求把 3-5 个核心假设写入 `assumptions[]`
- 06-daily-monitor 在监控到 kill criteria 触发时调用 `mark_falsified`
- mark_falsified 自动调用 propagate

**验收**：
- [ ] industry topic 的 a3 标 falsified 后，依赖它的 arena/company topic 的 living_feed 自动追加 "上游假设 a3 已被否定，需复核 a5/a7"
- [ ] /prism/{slug}/{variant} 主页用红色高亮标 needs_review 的产出

**工程量**：~250 行 Python + spec 改动，1 天。

**何时做**：等 Phase 1-3 跑过至少 1 个完整 industry → arena → company → decision cycle，证明这条链路的假设传染确实有用再做。否则可以暂时手工处理。

---

## 9. 不做（明确边界）

- **完整 context graph**：8 种边类型、双向遍历、可视化图谱——已论证 ROI 不足
- **跨 variant 自动比较**：不同 LLM variant 的产出比较仍然 ad-hoc
- **自动 finding 抽取打分**：critic-review 仍然人在回路
- **行情驱动的实时反推估值**：04 的反推用最近一次 finding 的数据，不接实时行情
- **多语言 / 跨市场 peer matrix**：暂限 CN + US 单市场内
- **portfolio 优化器**：不计算最优权重 / 不做最优组合，只给单标的的仓位上限
- **Cron 化 daily monitor**：保持 user 手动触发，不做后台 daemon

---

## 10. 推进顺序与验收 milestones

```
Day 0     |  Phase 0: 数据模型扩展（半天）
                ├─ topic.py schema + 单测
                └─ stage state machine

Day 1-3   |  Phase 1: 漏斗 gate（★★★★★）
                ├─ Day 1:  1.1 industry_to_arenas
                ├─ Day 2:  1.2 peer_matrix
                └─ Day 3:  1.3 quality_screen + 端到端跑通
                ✓ Milestone: 已有 cn-commercial-space 能一路漏斗到 1 家 candidate company

Day 4-5   |  Phase 2: 决策硬度（★★★★）
                ├─ Day 4:  2.1 04 三档分支 + 2.2 05 对偶
                └─ Day 5:  2.3 07 买入框 + 2.4 99 alternatives
                ✓ Milestone: 该 candidate company 跑出含反推 DCF + 买入框 + 替代标的的完整 7+99

Day 6-8   |  Phase 3: 知识积累（★★★）
                ├─ Day 6:  3.1 concepts.yaml + 索引
                ├─ Day 7:  3.2 monitoring_tier
                └─ Day 8:  3.3 freshness + UI 徽标
                ✓ Milestone: /prism 主页清晰显示三层结构 + freshness + concept 跨 topic 检索

Day 9+    |  Phase 4: 视图与假设链（★★，可选）
                视 Phase 1-3 实跑后是否痛点足够再启动
```

**整体工程量估计**：8-10 个工作日（不含 Phase 4）。

---

## 11. 风险与备选

### 11.1 实施风险

- **现有 topic 兼容性**：所有 schema 改动必须能读旧 yaml，否则手动 migrate 4 个 variant × N topic 工作量大。**对策**：read_topic 始终补缺省值，create_topic 才写新字段。
- **fetch_financials 数据稀疏**：港股 / 美股 / 未上市公司没有完整财务，quality_screen 自动红线会失效。**对策**：spec 里明确"数据缺失视为 needs-review，由用户判断"。
- **LLM 输出不稳定**：要求反推 DCF 数字时模型可能给出虚构数字。**对策**：spec 里强制每个数字必须引用具体 mat_id 或注明"反推假设"。

### 11.2 实施建议

- 先在已有的 `cn-commercial-space` 上完整跑一遍 Phase 1+2，作为 dogfood——这能在小范围发现 spec 漏洞
- Phase 3 在跑通 ≥ 3 个 industry topic 后再做（否则 concepts.yaml 没数据可索引）
- Phase 4 完全可以延后到 2026-Q3 再决定

---

## 附录 A：文件改动总清单

**新建**（10 个）：
- `prism/workflows/03b-quality-screen.md`
- `prism/workflows/04-synthesize/09-industry-to-arenas.md`
- `prism/workflows/04-synthesize/10-peer-matrix.md`
- `prism/templates/quality_screen.md.tmpl`
- `prism/templates/industry_to_arenas.md.tmpl`
- `prism/templates/peer_matrix.md.tmpl`
- `prism/concepts.yaml`
- `prism/scripts/concepts.py`
- `prism/scripts/assumptions.py`（Phase 4）
- `app/templates/prism/arenas.html`（Phase 4）

**修改**（10 个）：
- `prism/scripts/topic.py`
- `prism/templates/topic.yaml.tmpl`
- `prism/workflows/00-research-topic.md`
- `prism/workflows/04-synthesize/_shared.md`
- `prism/workflows/04-synthesize/04-expectations.md`
- `prism/workflows/04-synthesize/05-mirrors.md`
- `prism/workflows/04-synthesize/07-decision-kit.md`
- `prism/workflows/06-daily-monitor.md`
- `prism/workflows/99-decision-record.md`
- `app/routes/prism.py`

**归档**（新目录）：
- `prism/quarantine/{slug}.md`（quality_screen 失败的公司）

---

## 附录 B：每件改动对应的用户目的

| 改动 | 目的 1 知识 | 目的 2 找机会 | 目的 3 筛公司 | 目的 4 深研买入 |
|---|---|---|---|---|
| 1.1 industry_to_arenas | ◐ | ●●● | | |
| 1.2 peer_matrix | | ◐ | ●●● | |
| 1.3 quality_screen | | | ●●● | ◐ |
| 2.1 04 三档分支 | | ◐ | | ●●● |
| 2.2 05 对偶 | ◐ | | | ●●● |
| 2.3 07 买入框 | | | | ●●● |
| 2.4 99 alternatives | | | | ●●● |
| 3.1 concepts.yaml | ●●● | ◐ | | |
| 3.2 monitoring_tier | ●● | ●● | | |
| 3.3 freshness | ●●● | ◐ | | |
| 4.1 /prism/arenas 视图 | ●● | ●●● | | |
| 4.2 assumption depends_on | ●● | | ◐ | ●● |

每行权重相加均 ≥ 3，证明每件改动都对至少一个用户目的有显著贡献。

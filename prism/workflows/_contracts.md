# 产物契约（单源）

> 本文件是 prism 系统产物契约的**唯一权威来源**。topic.yaml / manifest / findings frontmatter /
> 各 sidecar schema / 编号体系 / input_contract 表 / thesis_v1 结构，全部单源于此。
> 修改任一 schema 必须同时更新本文件，并同步 `prism/scripts/input_contract.py`（input_contract 部分）
> 与各路径文档的引用（`_company_case.md` / `_industry_funnel.md` / `_arena_funnel.md`）。

---

## 一、内部编号约定

### `mat-XXXXXX`：资料编号

形如 `mat-9fb50a`。每份原始资料（年报/季报/10-K/研报/新闻/访谈）的内部 hash 编号。
看到它 = "这句话有出处"，查原文去同目录 `findings_mat-XXXXXX.md`。
父级复用资料（`parent_topic` 继承）与自有资料共用命名空间。

### `K1`~`Kn`：Killer Questions（核心可证伪假设）

本研究的核心赌注。每个 K# 有"看多/看空"的明确证伪条件，必须可观测、可证伪
（不能是"未来不确定"这种废话）。产出里 "K1 强度 +7→+5" = "原本看多 7 分，最新资料降到 5 分"。
v0（开研究前初判）vs v1（吃完资料后修正）——**变化幅度本身是信号**。

### `R1`~`Rn`：Risks（风险点）

"可能让 thesis 破产"的风险逐条编号，集中在 case 环⑤（证伪与风险）+ sidecar 的 kill/risk 字段。
每条必有"正方对照"，避免单边风险叙事。

### `F1`~`Fn`：Failure cases（失败案例）

历史上"看起来一样但失败了"的案例做镜子，在 case 环⑤的历史镜鉴段。
（与 PRISM_VALIDATION 报告里的 F# 编号无关，那是另一套缺陷编号。）

### `KILL-1`~`KILL-n`：Kill switches（清仓信号）

任一触发就立刻减仓/清仓的硬信号（如"现金 runway 跌破 18 个月"/"某价格半年下行 >30%"）。
是 KILL 不是 alert——触发就触发，没有"再观察"。

### 强度刻度：thesis 强度 ±N / N分制

- **±10 制**：+10 极强看多 / +7 较强看多但仓位有限 / 0 中性 / -7 较强看空 / -10 极强看空
- **N/10 制**：6/10 温和看多 / 5/10 中性偏多（company 类常用）

`v0` = 开研究前训练知识初判，`v1`/`v2` = 吃完资料/经 critic 后修正。
**v0→v1 变化比 v1 绝对值更重要**——大变化意味着资料发现了违背训练共识的新事实。

### WWHTBT（What Would Have To Be True）

反向思考——"如果 thesis 成立，什么必须为真？"列若干可观测必要条件，满足全部=基础情景成立，
满足≤1条=thesis 破产。把"看多/看空"转成"可跟踪信号"的工具。

---

## 二、决策链输入合同（Input Contract）

> 与 `prism/scripts/input_contract.py` **同源维护**。改一处必须改另一处。
> `rings` 字段对应 `add_material(..., rings=[...])` 和 `gap_detector` 双轴。
> **训练知识不计覆盖**：合同项只认实收料/API；缺料只能标"训练知识估算"或"数据缺失"。
> **三项真·欠供**（标 hard，旧流程从不产出，收料须显式排期）：管理层/资本配置史、一致预期/估值锚、历史失败镜鉴。

### company（8 项）

| code | 环 | 必带硬落地（输入投影） | served_by | hard |
|---|---|---|---|---|
| `biz-moat-unit-econ` | ① | 生意模式/收入拆解(量×价×结构)/护城河/单位经济(毛利·单客·ROIC) | material, smm | |
| `mgmt-capital-alloc` | ① | 管理层 track record + 资本配置历史(回购/分红/并购回报) + 激励治理 | material, user | ✅ |
| `financial-arc` | ① | 多年财务弧线(3-5Y 营收/利润率/ROIC/FCF + 拐点) | financial_data | |
| `valuation-anchor` | ② | 当前价/估值倍数反推隐含 CAGR·终值PE·IRR | market_data, material | |
| `consensus` | ② | 卖方一致预期/目标价模型(反推对照基准) | material, user | ✅ |
| `valuation-percentile` | ② | 历史区间 + 全球 peer 估值水位 | market_data, material | |
| `bull-bear` | ④ | 多空论据(喂④期望收益加总) | material, web | |
| `historical-mirror` | ⑤ | 历史失败镜鉴(相似剧本怎么崩) | material, web | ✅ |

### industry（6 项）

| code | 环 | 必带硬落地（输入投影） | served_by | hard |
|---|---|---|---|---|
| `value-chain-profit-pool` | ① | 价值链全貌+利润池定位(谁赚走)+驱动因子+周期位 | material, smm | |
| `industry-financial-arc` | ① | 行业代表主体多年财务弧线(龙头/聚合 3-5Y) | financial_data | |
| `leader-valuation-anchor` | ② | 龙头/细分倍数反推增速 + 相对水位(历史+全球peer) + 叙事资金流 | market_data, material | |
| `migration-path-evidence` | ③ | 利润池迁移路径/结构性假设证据(谁攫取价值·渗透曲线·政策) | material, web | |
| `arena-scoring-inputs` | ④ | 各 arena 6 维评分料(利润池规模/增速/竞争/估值/周期) | material | |
| `industry-mirror` | ⑤ | 历史行业镜鉴(利润没兑现/迁移没发生——电信capex·光伏) | material, web | ✅ |

### arena（5 项）

| code | 环 | 必带硬落地（输入投影） | served_by | hard |
|---|---|---|---|---|
| `biz-value-chain-position` | ① | 怎么赚钱+价值链卡位+路线之争+客户结构+赛道周期位 | material | |
| `winner-variables` | ② | 关键胜负变量(成本曲线/技术代差/客户锁定/规模/牌照) | material, smm | |
| `peer-valuation-anchor` | ② | 被当赢家那几家当前估值(PE/PS 相对赛道·是否已透支) | market_data, financial_data, material | |
| `peer-comparison-financials` | ④ | 候选公司横比矩阵(≥5家·收入/ROIC/毛利/负债/PE/历史PE/路线/客户) | financial_data, material | |
| `arena-mirror` | ⑤ | 历史镜鉴(曾经赢家如何被取代——Nokia/Kodak) | material, web | ✅ |

> 环③（company/arena 的 WWHTBT）、环⑥（行动/漏斗）由前几环 derive，无独立原始输入需求，故不列合同项。
> industry/arena 的 `migration-path-evidence` / 假设类证据是例外（迁移路径需独立佐证），单列。

---

## 三、topic.yaml 完整运行时字段 schema

```yaml
slug: str
display_name: str
type: company|industry|arena|macro
created: iso8601
status: active|archived
stage: str                      # 历史保留；B 模式下 doctor 用不变量取代，但字段仍写（兼容 dashboard）
parent_topic: str|null
parent_materials: [...]         # 子 topic 复用父级资料
monitoring_tier: deep|watch|dormant
monitoring: {enabled:bool, cadence:str, tier:..., reviewed_at:iso}
concepts: [str]
scope: {geo:str, question:str, depth:str}
ticker: str                     # company 必填，格式 {EXCHANGE}_{CODE}
short_name: str                 # company 必填 ≤12 字
extra_tickers: [str]            # 多市场（A/H/ADR）
search_terms: [str]             # question>25字必填，每项≤15字
outputs_state:
  {output_key}:                 # 如 01_business_panorama / 07_decision_kit / 00_primer / c_investment_case ...
    version: int
    last_updated: iso|null
    status: pending|draft|fresh|stale
    data_freshness: str|null
    critic_passed: bool         # set_output_critic_passed
    referenced_mats: [mat_id]   # set_output_referenced_mats
    error: str|null             # set_output_error
    primer_gate: {...}          # 仅 primer，F17 软门记录
next_actions: [str]             # prescan_status=failed 时自动 prepend 警示
user_todos:
  - task: str                   # 文档身份（闭环键，非 K#）
    priority: P0|P1|P2
    info_tier: public|half_public|hard
    status: pending|in_progress|done
    fetch_status: unattempted|fetched|empty|error
    fetch_attempts: int>=0
    disposition: undecided|waived|will_collect
    addresses: [K#|Q#|K#@event-slug]
    covered_by: [str]
prescan_status: full|partial|failed|null   # 顶层当前态（H5 后绑 history）
prescan_log: [...]
pending_thesis_review: {...}|null          # daily-monitor 翻牌待重评 marker
critic_verdict: {verdict:approve|request-rewrite|request-more, ...}|null
```

---

## 四、manifest.yaml 字段 schema

```yaml
materials:
  - mat_id: str
    filename: str
    source_type: sell-side-note|annual-report|industry-research|web-article|manual-note|policy|sec-section|drilldown
    addresses: [K#|Q#|...]      # 非空（actionable 资料）；prescan 校准料标 ['scope']
    rings: [code]               # input_contract 的 ring code
    processed: bool
    mineru_state: needs|in_progress|done|failed|not_needed
    parent_mat: str             # 可选，SEC section 指向原 htm
    sec_section: str            # 可选，source_type=sec-section 时
    search_meta:                # 可选，web 入库料
      domain_tier: whitelist|llm-judged-official|other
      confidence: float
      triggered_by: 00-prescan|00-prescan-baseline|01-prescan|02-step0|03-extract|04-synth|05-critic|06-daily-monitor|07-drilldown|unknown
      prev_queries: [str]
```

---

## 五、findings frontmatter schema

写入 `prism/topics/{slug}/{variant}/outputs/findings_{mat_id}.md`：

```markdown
---
mat_id: {mat_id}
filename: {filename}
source_type: {source_type}
extracted: {timestamp}
quality: high|medium|low
bias: bull|bear|neutral
addresses: [{命中的 K#}]        # thesis 脊柱；frontmatter 优先于 manifest
rings: [{命中的决策链输入合同 code}]   # 见 §二 input_contract；没命中可省略此字段
conflicts_with: [{冲突 finding 文件名/id}]   # 可选：本 finding 与哪些 finding 证据相矛盾；无冲突则省略
conflict_note: {一句话：冲突在哪/暂如何取舍}   # 可选，仅 conflicts_with 非空时填
---

## 核心数据点与事实

{bullet list，按取舍原则筛选，目标 15-20 条}

## 叙事主线

因为 {X（数据依据）} → 所以 {研报判断 Y} → 对投资意味着 {Z}

## 反常识/分歧点

{bullet list or "无"}

## 未回答问题

{1-3 条 or 省略此节}

## 质量备注

{可选，偏差/数据局限/样本说明}
```

---

## 六、sidecar schema

### company：`07_decision_kit.yaml`

> dashboard.py 只读这一个文件、只认这套字段名。**禁自创/改名/漏字段**，否则该 topic dashboard 整行为空。
> 文件名固定 `07_decision_kit.yaml`。

```yaml
slug: {slug}
variant: {variant}
topic_type: company
display_name: {display_name}
ticker: {ticker}             # "SZSE_001270" 格式
generated: {ISO8601}
data_freshness: {date}

buy_box:
  strong_buy_max: {number or null}
  accumulate_min: {number or null}
  accumulate_max: {number or null}
  hold_min: {number or null}
  hold_max: {number or null}
  current_price: {number}
  price_as_of: {date}
  current_zone: {strong_buy|accumulate|hold|above_hold|unknown}

position_framework:
  position_tier: {试探|标准|重仓}  # 档位—首要字段；给不出有据数就 null 只留 tier
  sizing_rationale: {string}
  initial_max_pct: {number or null}  # ⚠️ 人工落点不是算出来的
  full_max_pct: {number}
  add_ladder_prices: [{number}, ...]
  max_cluster_pct: {number or null}

valuation_models:
  - name: {snake_case_id}
    label: {显示名称}
    bull_fair_value: [{low}, {high}]
    base_fair_value: [{low}, {high}]
    bear_fair_value: [{low or null}, {high or null}]

kill_criteria:
  - id: {snake_case_id}
    description: {一句话触发条件}
    status: pending|triggered_bull|triggered_bear|expired
    check_at: {date}

signposts:
  - date: {date}
    event: {事件描述}
    bull_signal: {多方信号}
    bear_signal: {空方信号}
    triggered: null  # null=pending, "bull", "bear"

cluster_tags: [{tag1}, {tag2}]

chain_links:
  rings_present: [1, 2, 3, 4, 5, 6]
  r4_anchors_r2: {true|false}
  r6_takes_r4_ev: {true|false}
  r5_has_kill_signpost: {true|false}

honest_gaps:
  - ring: {1-6}
    kind: {data-missing|training-estimate}
    note: {一句话}

market_implied:
  metric: {snake_case_id}
  value: {number}

my_vs_market_delta:
  metric: {snake_case_id}
  my_value: {number}
  delta: {string}
  direction: {long|short}
```

### industry：`industry_to_arenas.yaml`

> dashboard.py 的行业层"竞技场选择"只读 `industry_to_arenas.yaml`、只认这套字段名。

```yaml
slug: {slug}
variant: {variant}
topic_type: industry
display_name: {display_name}
generated: {ISO8601}
data_freshness: {date}
arenas:
  - name: {arena 名称}
    suggested_slug: {建议 slug}
    topic_created: {bool}
    topic_slug: {str or null}
    scores:
      profit_pool: {0-10}
      growth: {0-10}
      competition: {0-10}
      valuation: {0-10}
      cycle: {0-10}
      composite: {0-10}
    tier: deep|watch|eliminated
    tier_reason: {一句话}
    upgrade_triggers: [{str}]    # 深挖/观察必填非空
    monitor_metrics: [{str}]     # 深挖/观察必填非空
    revive_condition: {str or null}  # 淘汰档填复活条件
cluster_tags: [{tag1}, {tag2}]
```

### arena：`peer_matrix.yaml`

> dashboard.py 的竞技场层"公司排名"只读 `peer_matrix.yaml`、只认这套字段名。

```yaml
slug: {slug}
variant: {variant}
topic_type: arena
display_name: {display_name}
generated: {ISO8601}
data_freshness: {date}
companies:
  - name: {公司名}
    ticker: {str or null}
    score: {0-10}
    tier: shortlist|watch|eliminated
    topic_created: {bool}
    topic_slug: {str or null}
    thesis_one_liner: {str}
    upgrade_triggers: [{str}]
    quarantine: {bool}
cluster_tags: [{tag1}, {tag2}]
```

### macro：`transmission_map.yaml`

> dashboard 的宏观横幅（banner）只读 `transmission_map.yaml`、只认这套字段名。

```yaml
slug: {slug}
variant: {variant}
generated: {ISO8601}
regime:
  rates:     {state: ..., note: ..., confidence: <0-10>}
  liquidity: {state: ..., note: ..., confidence: <0-10>}
  fx:        {state: ..., note: ..., confidence: <0-10>}
  composite: {顶部综合判断一句话}
  conviction: <0-10>
  quadrant: {复苏|过热|滞胀|衰退}
  fragility: {low|mid|high}
holdings:
  - slug: ...
    display_name: ...
    duration: long|short
    rate_beta: high|mid|low
    usd_exposure: high|mid|low
    liquidity_beta: high|mid|low
    exposure_score: high|mid|low   # high → 进 banner 「最受影响」列表
    regime_favor: [...]
    regime_hurt: [...]
    plain: {一句大白话传导链}
    source: macro_synth|self_registered
    provisional: {bool}
    as_of_regime: {vN}
categorical_tail:
  - name: ...
    state: 平静|警示|触发
    note: {一句话}
```

---

## 七、thesis_v1 Scheme C 全快照 11 段式（v1 起强制）

任何 `thesis_v{N}.md`（N≥1）必须是**全快照**——包含当前完整的核心 thesis / 支持理由 / 反方观点 /
K# 现状表 / 应对策略 / catalyst / 数据缺口 / 思维过程留痕，**不依赖 v{N-1} 章节即可独立阅读**。

强制结构（11 段）：

1. **frontmatter**：`parent_version: {N-1}` + `writing_convention: 方案 C 全快照 + 顶部 changelog`
2. **§ 0. v{N-1} → v{N} changelog**：5-10 行 release notes（仅 review 用，正文不依赖）
3. **§ 1. 核心 thesis（当前完整版）**：一句话观点 + 强度评分 + 估值带 + 时间维度
4. **§ 2. 支持理由（当前完整清单）**：累积所有看空逻辑（含历代沉淀 + 本版新增），分类编号
5. **§ 3. 反方观点（当前完整清单）**：累积所有看多逻辑（含历代沉淀 + 本版新增 + critic 强反驳），分类编号
6. **§ 4. Killer Question 现状表（K1-K{n} 完整）**：表格列：K# / 主题 / 当前状态 / 触发条件
7. **§ 5. 应对策略矩阵**：价格区间 × 动作
8. **§ 6. catalyst 时点表**：当前完整 catalyst 序列
9. **§ 7. 数据缺口**：P0/P1/P2 分级 + 期望解决路径
10. **§ 8. 思维过程留痕**：已知 / 刻意避开的偏见 / 关键差异
11. **§ 9. 信息来源**：训练知识占比 + 关键 mat_id

**硬约束**：
- 禁止写「见 v{N-1} §X」「同 v{N-1} 不变」等需读老版本才能理解的引用
- 禁止只写 v{N-1}→v{N} 增量而省略其他章节
- v0 是天然全快照（无 parent），五段式（见 00-research-topic 5.0）；v1 起改用本 11 段式

**写完调脚本登记**：
```bash
python3 -c "
from prism.scripts.topic import set_thesis
set_thesis(slug='{slug}', variant='{variant}', version=1,
           summary='{修正后的核心 thesis，≤120字}', stage_set_at='04-post-synthesis')
"
```

---

## 八、decomposition_v1 结构

与 thesis_v1 配对升版（B 层命门拆解），包含两 section：
- 「命门现状」：命门 + 置信度 + 每环 B 靶点
- 「primer 入门目标现状」：精修后的 N 条 + 各条覆盖情况
- §changelog（命门与入门目标的增删都记）

调用 `set_decomposition(version=1, convergence_status='converged'|'open'|'capped', changelog='...')`

---

## 九、产出体系总览

| 产出 | 文件 | 一句话定位 | 主 type |
|------|------|-----------|---------|
| **领域入门** | `00_primer.md` | 给完全外行建心智模型（讲领域本身，不讲投资判断） | 全类型 |
| **成稿 case** | `c_investment_case` / `i_industry_case` / `a_arena_case` / `m_regime_read` | 决策链正文，6 个命门环串成完整论证 | 按 type |
| **sidecar** | `07_decision_kit.yaml` / `industry_to_arenas.yaml` / `peer_matrix.yaml` / `transmission_map.yaml` | case 的机器消费面，dashboard 直接读 | 按 type |
| **追踪时间线** | `08_living_feed.md` | 接下来盯的时点/催化剂/监测信号 + 事件序列 | 全类型 |
| **findings 笔记** | `findings_{mat_id}.md` | 每份原始资料的提炼笔记 | 全类型 |

> **来源边界（读产出时识别）**：
> 1. **LLM 训练知识**（行业原理/技术/估值/政策框架）——稳定，截止训练截止日，不标单条
> 2. **本研究 findings**（带 `[mat-XXX]` 的具体数据）——当前数据，截止 `data_freshness`
> 3. **本研究特色判断**（thesis 内容/强度/叙事）——研究小组的 take，随 v0/v1/v2 演化

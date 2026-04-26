# 用户指南

> 配合 [`DESIGN.md`](../DESIGN.md) 阅读。DESIGN 讲**为什么**，本文档讲**怎么用**。

本系统是个人投资决策工作流，不是研报仪表盘。核心目标：防止**踏空**（知道便宜但不敢重仓）和**情绪卖出**（被宏观叙事冲走原本正确的持仓）。它不会告诉你买什么，它逼你在买之前把买入理由冻结成文字。

---

## 1. 启动

```bash
source .venv/bin/activate
uvicorn main:app --reload
# 访问 http://127.0.0.1:8000/
```

首次启动会自动创建 `data/financials.db`（空库）。其余目录（`companies/`, `watchlist/`, `portfolio/` 等）在对应功能第一次写入时创建。

---

## 2. 首页看板：什么出现意味着什么

首页 `/` 是纪律仪表盘，不是行情页。出现的卡片都是"需要你处理的东西"：

| 卡片 | 含义 | 你该做什么 |
|---|---|---|
| 🚨 复盘跳过 | 连续 ≥2 个季度没写 `macro/review-YYYYQX.md` | 立刻补上最近一次复盘（DESIGN §8 坑 6——系统白建了） |
| 📅 未来 7 天催化剂 | `macro/catalysts.md` 里 T+0–7 的条目 | 点进去确认"什么算推翻 / 什么不算" |
| 🔔 价格触发 | 持仓/观察池里的价格条件已成立但你还没处理 | 打开对应公司 V0，决定买入/删除/重置 |
| 📉📈 单日 ±15% | 任何 ticker 相邻两天收盘价变动 ≥15% | 打开对应 V0，对照"什么不算推翻" |
| ⏰ 研究逾期 | 观察池 researching 段超过 `target_finish` | 结束研究——2-4 小时没结论说明你在绕开门禁（DESIGN §3.6） |
| 待办：财报对照 | 该公司有新财报期间但你没对过 V0 | 去 `/earnings-review/<key>` 逐条对照 |

**原则：首页空 = 你做得对。** 如果首页卡片堆了很多而你在研究新股票，就是在用"研究"回避"处理"。

---

## 3. 日常节奏（DESIGN §6）

### 每天（5 分钟）
1. 打开首页，扫看板卡片
2. 处理掉红色/黄色卡片（或明确决定"今天不处理"）
3. **不做**：打开 `/companies` 逛；读新持仓的新闻

### 每周（30 分钟）
- `/watchlist`：review 观察池
  - prefilter 里淘汰不再感兴趣的
  - researching 里结束已过期的（强行结束也行，写结论到日志）
- `/prices` 录入本周收盘价（只记你在跟踪的 ticker，不求全）

### 每月（2 小时）
- `/performance`：这月组合 vs 沪深 300 / SPY
- `/portfolio/rules` → 检查组合级规则是否被违反
- `/research-audit`：抽查本月写的 claim，防止 AI 辅助输出的东西不准却没人复核

### 每季度（半天）
- `/regime/<YYYYQX>` 更新市场钟摆判断（这会影响 `/companies/<key>/valuation` 的建议折现率）
- `/review/<YYYYQX>` 季度复盘
- 每个持仓公司 V0 逐一 review（点 `/companies/<key>/v0` 确认是否需要更新）

### 每年（一天）
- 复盘哪些行业你真正有能力圈（结果分证明），哪些是幻觉
- 审视 `industries/` 下的行业目录：哪些已经没人跟了？哪些需要重写 11 维？

### 触发式
- **想买**→必须先走 `/companies/<key>/v0`。没写完的 V0 = 不能买
- **想卖**→必须对照 V0 里"什么不算推翻"
- **财报发布**→ `/earnings-review/<key>`
- **±15% 单日**→首页卡片会提醒

---

## 4. 核心工作流：一只新公司怎么从想法走到持仓

这是系统十层主线的具象化（DESIGN §2.1）。假设你刚听说一家公司 "HIMS"。

### 第 1 步：入观察池 prefilter
`/watchlist` → 添加到 prefilter 段。必填：
- `source_type`：必须是 `quant_screen` / `qual_radar` / `product_experience` 之一（DESIGN §8 坑 9：不能写 "news"）
- `source`：具体来源（如 "自己用 GLP-1 服务 6 个月"）
- `notes`：第一眼印象

**系统会拒绝的事**：7 天冷静期没到就想升级到 researching。

### 第 2 步：冷静期过后，升级到 researching（门禁）
7 天后回到 `/watchlist`，点"升级"。弹出三问：
1. **能力圈**：你能解释它怎么赚钱吗？
2. **错定价**：为什么你觉得市场错了？
3. **真兴趣**：不是追涨/跟风，对吧？

三问**都**要回答 `yes` 且理由 ≥30 字。短理由和 `no` 都会被系统拒。

另外 researching 段有硬上限 **2 家**。要进第 3 家？先结束一家（DESIGN §8 坑 8：过度研究 = 假装在工作）。

### 第 3 步：建档（公司元信息）
`/companies/new` → 创建 `US_HIMS`。生成：
- `companies/US_HIMS/meta.md`（ticker、market、industry_slugs、themes）
- `companies/US_HIMS/v0.md`（空模板）
- `companies/US_HIMS/valuation.md`（三情景估值）
- `companies/US_HIMS/narratives/{business-model,moat,...}.md`（8 维，spec §4.5）

`industry_slugs` 是一个自由文本 list，每个 slug 对应 `industries/` 下的一个行业目录。没有白名单 —— 行业层由 `industries/` 注册表本身定义（spec §4.5）。

### 第 4 步：填能力圈问卷（硬门禁）
`/companies/US_HIMS/competence`。按题目打 ✓ / 部分 / ✗。每个 ✗ 都是缺口。

**不过关不研究**。 不过关的正确动作是**放弃**，不是"读更多研报"（DESIGN §1 哲学 3）。

### 第 5 步：B 研究（可选，只针对缺口）
`/research/US_HIMS`：
- 你在对话里（任意 LLM）让它帮你抽 claim
- 结果粘贴到 `/research/US_HIMS`（会写入 `companies/US_HIMS/claims.jsonl`）
- **硬性要求**：每条 claim 必须绑定一个 `source_file`，且文件必须存在于 `companies/US_HIMS/sources/`（DESIGN §8 坑 9——事实层不接受"新闻里说"）

时限：2-4 小时一家。拖更长 = 你在用研究回避决策。

### 第 6 步：估值
`/companies/US_HIMS/valuation`。填三情景（悲观 25% / 基准 50% / 乐观 25%）+ 相对估值 + 倒推法。

**折现率**：系统根据当前 `macro/regime-<quarter>.md` 的 `ust_10y_yield` + 市场钟摆等级给你一个建议值（hot +1%，panic +2%）。你可以不用这个建议，但系统会显示它，方便你逆向验证自己的数字。

### 第 7 步：写 V0（买入前最后一关）
`/companies/US_HIMS/v0`。七个字段（DESIGN §3.2）：
1. 买入逻辑
2. 差异化观点（二阶思维——市场共识是什么，你哪里不一样）
3. 估值锚
4. 买入区间
5. 卖出触发（基本面 + 估值两类）
6. **什么不算推翻**（噪音清单——利率/地缘/央行/宏观数据都要写在这里）
7. 当前状态

"什么不算推翻"是 V0 的灵魂。情绪卖出基本上都是"实际上不算推翻的噪音"被事后合理化成"thesis 坏了"。把噪音在买入前列清楚，卖出时才有抓手。

### 第 8 步：执行（买 / 设触发 / 放弃）
- 价格已到买入区间：去券商下单，然后在 `/journal/new` 写买入日志
- 价格还没到：`/companies/US_HIMS/triggers` 设价格触发
- 决定不买：也要在 `/journal/new` 写"放弃"日志（过程分必填）

### 第 9 步：持仓期间
- 每次买卖/加减仓 → 写日志（过程分 + 结果分分离）
- 价格触发激活 → 首页卡片提醒
- 财报发布 → `/earnings-review/US_HIMS` 对照（最新 period vs 上次 reviewed period）
- 催化剂 → `/catalysts` 手动登记重大事件日期

### 第 10 步：退出
卖出时 **必须**对照 V0 的"推翻条件"和"什么不算推翻"。如果卖出理由命中"什么不算推翻"里的词（利率、美联储、地缘政治、VIX、通胀、板块轮动、消息面……），系统会在 `/discipline` 标红。你可以卖，但你会看到自己在违反自己当初写的规则。

---

## 5. 各模块索引

### 主要入口
| 路径 | 作用 |
|---|---|
| `/` | 首页看板 |
| `/companies` | 公司列表 + 新建 |
| `/watchlist` | 观察池三段（prefilter / researching / price-triggers） |
| `/portfolio` | 持仓 |
| `/portfolio/rules` | 组合级硬性规则（单股上限、行业上限、主题上限、现金下限） |
| `/journal` | 投资日志 |
| `/earnings-review` | 财报对照待办列表 |
| `/prices` | 收盘价录入（手动，无外部 API） |
| `/performance` | 业绩 vs 基准 |
| `/regime` | 季度市场钟摆 |
| `/review` | 季度复盘 |
| `/catalysts` | 催化剂日历 |
| `/industries` | 行业 landscape / players / 能力圈地图 |
| `/competence-map` | 跨公司能力圈总览 |
| `/discipline` | 纪律仪表盘（详见下一节） |
| `/research-audit` | Claim 月度抽查 |
| `/search` | 全文搜索 markdown |
| `/prompts` | LLM 提示词模板 |

### 单公司入口（`<key>` = `US_HIMS` 形式）
- `/companies/<key>` 详情（含 8 维 narrative + 行业/arena 跨层链接）
- `/companies/<key>/meta` 编辑 ticker/market/industry/themes
- `/companies/<key>/v0` 买入逻辑
- `/companies/<key>/competence` 能力圈问卷
- `/companies/<key>/valuation` 三情景估值
- `/companies/<key>/financials` 财务数据（CSV 导入）
- `/companies/<key>/triggers` 价格触发
- `/research/<key>` B 研究（claims）

---

## 6. 纪律仪表盘 `/discipline`

专门监控自己是否在违反规则。DESIGN §8 的九个坑里，这个仪表盘直接检测其中三个：

### 无 V0 快照的买入（坑 3）
扫所有买入/加仓日志，找 `v0_snapshot_path` 字段为空的。命中 = 绕开 V0 规则买入。

### 情绪卖出（坑 2 / 哲学 4）
扫所有卖出/减仓日志，body 里出现**噪音词**（利率、美联储、央行、加息、降息、地缘政治、战争、VIX、恐慌、CPI、PPI、通胀、宏观、板块轮动、新闻、消息面）就命中。

这不是在说"你不能因为宏观调仓"。是在说"如果你的卖出理由是宏观，V0 里'什么不算推翻'一栏也应该列了这些词——你现在正在违反买入时自己写的规则"。

### 复盘跳过（坑 6）
检查过去 6 个季度每一个季度是否有 `macro/review-<quarter>.md`。连续 ≥2 个季度缺失 = 红旗。

---

## 7. Claim 月度抽查 `/research-audit`

**为什么存在**：B 研究（LLM 抽取的 claim）有低概率的"看起来正确但原文没有"。不抽查会被幻觉污染。

**怎么用**：选月份 + 抽查比例（5% / 10% / 20%），系统用确定性哈希（同一月份永远抽到同一批）给你一个清单。你打开原文手动核对 evidence_quote 是否真的在那儿。发现不对的就回 `/research/<key>` 删掉或修。

---

## 8. 价格触发 vs 事件驱动

两种触发机制，不要搞混：

- **价格触发**（`/companies/<key>/triggers`）：ticker 到达某价格自动激活 → 首页卡片。用来解决"等下跌到买入区间再买"这种承诺没被执行的问题。
- **催化剂日历**（`/catalysts`）：手动登记特定日期事件（FDA 裁定、财报窗口、政策节点）→ 首页"未来 7 天"卡片。

共同点：都不会给出操作建议，只负责把"该看这个"推到你面前。

---

## 9. 数据在哪里

一切都在 `~/investing/` 里，明文存储，断电也能用 `cat` 读：

```
companies/US_HIMS/         # 单公司所有数据
├── meta.md                # 元信息（frontmatter）
├── narratives/            # 8 维叙述（ingest 自动 append）
├── v0.md                  # 买入逻辑
├── valuation.md           # 估值
├── claims.jsonl           # B 研究结果
├── sources/               # 研报/财报原件（PDF/HTML）
├── competence/consumer.md # 能力圈问卷
└── triggers.jsonl         # 价格触发

industries/consumer/       # 行业级
├── landscape.md
├── players.md
└── competence-map.md

watchlist/
├── prefilter.md
├── researching.md
└── price-triggers.md

portfolio/
├── positions.md           # 持仓
└── rules.md               # 组合级规则

journal/
└── 2026-04-23-HIMS-buy.md # 一次决策一个文件

macro/
├── regime-2026Q2.md
├── review-2026Q1.md
└── catalysts.md

data/financials.db         # 唯一的 SQLite；派生数据，可以删了重建
```

**推论**：你可以把整个目录丢进 git 自己版本控制。你可以跨设备同步（rsync/iCloud 都行）。你可以用 `grep` 跨所有公司搜索任意字符串。系统崩溃也不会丢数据——markdown 永远可读。

---

## 10. 常见操作备忘

### 导入财报数据
1. `/companies/<key>/financials`
2. 上传 CSV（列名对上就行，详见该页说明）
3. 系统自动计算派生 ratio（毛利率、ROE 等）

### 录入收盘价
1. `/prices`
2. 粘贴多行，格式 `TICKER 价格`（宽松解析，支持 `,` 或空格分隔，支持货币符号）
3. 系统 upsert 到 SQLite，同日重复录入后覆盖

### 添加持仓
1. `/portfolio`
2. POST `/portfolio/position`（通过页面表单）

### 查找旧决策
- `/search?q=<关键词>` 全文搜 markdown
- `/journal` 按时间倒序

---

## 11. 会让系统拒绝你的动作（总览）

| 动作 | 拒绝原因 | DESIGN 出处 |
|---|---|---|
| 7 天内从 prefilter 升级到 researching | 冷静期 | §3.9 |
| 三问门禁任一回答 `no` 或理由 <30 字 | 能力圈门禁 | §3.9 |
| researching 已有 2 家时再升级第 3 家 | 上限 | §8 坑 8 |
| 创建 claim 但 source_file 不在 `sources/` | 事实层净化 | §8 坑 9 |
| 买入日志不关联 v0_snapshot_path | 坑 3 检测 | §8 坑 3 |

系统不会拦住你完成动作（你可以绕过，可以手改 markdown），它只保证你在绕过时**自己能看到在绕过**。这是"纪律在信息系统前面"的具体含义。

---

## 12. 不该做的事（DESIGN §7）

- ❌ 不要等"系统再完善一点"才开始用。完美主义在这套系统里等价于回避决策
- ❌ 不要把 B 的输出抄到 V0。V0 必须你自己写（哲学 2）
- ❌ 不要给所有公司都建档。只建你认真考虑过的
- ❌ 不要用系统去**证明**长期观点。系统是反向偏见工具，不是信念强化器（坑 7）
- ❌ 不要改首页的噪音词清单把情绪卖出的关键词删掉。这相当于作弊

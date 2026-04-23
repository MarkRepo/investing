# V1: Monday 推送 · 设计 spec

**Version**: 对应 DESIGN.md v1.3 的 §5 替换
**Date**: 2026-04-23
**Status**: 设计完成，待实施
**Supersedes**: DESIGN.md §5 V1 最小闭环（2-3 周）原有描述
**Sources**:
- office-hours 2026-04-23 Approach B（`~/.gstack/projects/investing/yangqi-nogit-design-20260423-105753.md`）
- 本次 brainstorm 会话（2026-04-23）8 项查漏补缺决策

---

## 0. 为什么重写 V1

DESIGN.md v1.0 的 V1 范围是"6 页 Web UI + 手工闭环"（观察池 / V0 编辑 / 估值 / 能力圈 / 持仓 / 研究工作台）。v1.2 的 frame 反转（新增哲学 7 "AI 主动 > 人主动"）把系统的 north star 改成"用 AI 对抗人性弱点"，office-hours 的 Approach B 进一步把 V1 落点从"信息架构"改到"主动触达的 forcing function"。

DESIGN.md v1.2 版本历史明确写了"§5 实施路线图 V1 范围待根据反转结论单独更新"——这份 spec 就是那次更新。

**V1 的唯一验证目标**：系统每周一主动找你一次，是否真的改变了你做投资决策的行为。

---

## 1. V1 目标 & 边界

### 1.1 目标
在 1-2 周内建起一个每周一 9:00 主动触达的最小 forcing function。不验证研究工作台、不验证 V0 UI、不验证共识地图——只验证"系统主动触达是否真的改变你的行为"。

### 1.2 必要前提（零代码，立即生效）
- 至少写 1 份真实候选股的 `companies/{market}_{ticker}/v0.md`，按 DESIGN.md §3.2 全 7 字段填，至少 `ticker / market / status: active / last_reviewed / entry_date` 齐。
- 至少在 `watchlist/price-triggers.md` 写 1 条触发线。

没这两份文件，脚本跑起来是空转。

### 1.3 V1 明确不做
- ❌ V0 / 估值 / 能力圈的 Web 编辑 UI（纯 markdown 编辑器即可）
- ❌ LLM 研报抽取、claims.jsonl 管道
- ❌ 研究工作台页面、共识地图
- ❌ SQLite 财务数据（V1 里所有数据都是 markdown frontmatter，不进 DB）
- ❌ 组合级规则自动化触发
- ❌ 任何 Web 页面
- ❌ SEC EDGAR 事后财报对照（留给 V2）
- ❌ 任何 LLM 调用

### 1.4 V1 的精神
系统只做"在该敲门的时刻敲门"，所有内容层、决策层仍留在 markdown + 你的大脑里。

---

## 2. 推送内容结构

### 2.1 整体说明
每周一 9:00 脚本生成 `weekly/YYYY-Www.md`（ISO 周号，如 `weekly/2026-W17.md`），同一份内容渲染成 HTML 用 SMTP 推送到你自己邮箱。

每条信号条目都是 markdown checkbox（`- [ ]`），你用编辑器打开 .md 改成 `- [x]` 即完成 ack。

### 2.2 Block 1: 价格变动 >±5%
- 范围：所有 status=active 的 v0.md 对应的 ticker
- 窗口：上周五收盘 → 本周五收盘（完整 5 交易日）
- 触发：|变动%| >= 5%
- 呈现每条：`[ ] **TICKER** $旧价 → $新价 (±X%) · [v0 链接] · 简短价位备注（基准情景目标价 / 买入区间位置）`
- 无条目时：显示"本周无公司满足 ±5% 门槛。"

### 2.3 Block 2: 12 天内有财报
- 范围：所有 status=active 的 v0.md 对应的 ticker
- 窗口：推送日当天 → 推送日 +12 天
- 数据源：
  - 美股：`yfinance` 的 `ticker.calendar`（next earnings date），免 key
  - A 股：cninfo（巨潮资讯网），endpoint 候选 `http://www.cninfo.com.cn/new/information/getPrbookInfo`（预披露时间表），具体参数实施时定
  - 港股：V1 先对齐美股走 yfinance（港股覆盖较弱，实施时评估覆盖率）
- 呈现每条：`[ ] **TICKER** 预计 YYYY-MM-DD 发 QX · [v0 链接] · 对照 V0 "什么不算推翻" 前请打开`

### 2.4 Block 3: last_reviewed > 30 天
- 范围：所有 status=active 的 v0.md（与 Block 1/2 统一）
- 阈值：30 天（office-hours 初设数字，跑一段再调）
- 字段：v0.md frontmatter 的 `last_reviewed` 字段
- 字段维护方式：**纯手工**。用户打开 V0 重新通读并评估 thesis 后，手动改 frontmatter 的 last_reviewed 字段为当天日期。系统不代写、不自动更新。
- 呈现每条：`[ ] **TICKER** last_reviewed: YYYY-MM-DD（N 天前）· [v0 链接]`

### 2.5 Block 4: 上周触发但未 ack
- 数据源 1：`watchlist/price-triggers.md`（人工维护的触发条目）
- 数据源 2：上周 `weekly/YYYY-W(N-1).md` 里 Block 4 的 checkbox 状态
- 触发判定：本周内**任一交易日最低价** <= trigger（"周内触发一次即算"，比周五收盘敏感，可能包含单日插针的误触发——V1 接受这个代价）
- 碎片规则：本周新触发的条目 + 上周 Block 4 里未 ack（`- [ ]`）的条目 merge
- 呈现每条：`[ ] **TICKER** @ $price（action）已触发 YYYY-MM-DD · 已连续出现 N 周 ▲`
- 即使 ack 后，`price-triggers.md` 本身**不**回写——trigger 仍留着，下次再触发照样提醒（这是故意的：本次没行动不代表下次不行动）

### 2.6 本周固定小块（每周都显示，空信号周也有）

#### 2.6.1 随机自检（1 条）
- 从所有 status=active 的 v0.md 中随机抽 1 个
- **排除**已在 Block 1-4 出现的 ticker（避免重复打扰）
- 如果所有 active V0 都已在 Block 1-4 出现，本项跳过
- 呈现：`本周抽到 **TICKER**（last_reviewed: YYYY-MM-DD）· 打开 v0.md 扫一眼"买入逻辑"一句话还成立吗？`

#### 2.6.2 本周 ack 统计
- 解析上周 .md 里所有 `- [ ]` / `- [x]` 数量
- 呈现：`上周推送 N 条，你 ack 了 M 条。K 条 carry over 到本周 Block 4。`

### 2.7 完整 markdown 模板

```markdown
---
week: 2026-W17
generated_at: 2026-04-27T09:00:00+08:00
prev_week_file: weekly/2026-W16.md
prev_week_ack_count: 3
prev_week_total_count: 5
---

# Monday 推送 · 2026-W17

> 上周推送 ack 总数：3 / 5 · 未 ack 条目 2 个 carry over 到 Block 4

## Block 1 · 价格变动 >±5%
参考窗口：上周五（2026-04-18）收盘 → 本周五（2026-04-25）收盘

- [ ] **HIMS** $19.20 → $21.60 (+12.5%) · [v0](../companies/US_HIMS/v0.md) · 基准情景 $25，仍在买入区间上端

## Block 2 · 12 天内有财报
窗口：2026-04-27 至 2026-05-09

- [ ] **HIMS** 预计 2026-05-06 发 Q1 · [v0](../companies/US_HIMS/v0.md) · 对照"什么不算推翻"前请打开

## Block 3 · last_reviewed 超过 30 天的 V0
- [ ] **TICKER_X** last_reviewed: 2026-03-10（48 天前）· [v0](../companies/US_TICKER_X/v0.md)

## Block 4 · 上周触发但未 ack
- [ ] **HIMS** @ $20（首建仓）已触发 2026-04-21 · 已连续出现 2 周 ▲

## 本周固定小块

### 随机自检（1 条）
本周抽到：**TICKER_Y**（last_reviewed: 2026-04-01） · 打开 v0.md 扫一眼"买入逻辑"一句话还成立吗？

### 本周 ack 统计
上周推送 5 条，你 ack 了 3 条。2 条 carry over 到 Block 4。

## 数据告警
（脚本异常时写入：拉不到价格的 ticker、SMTP 发件失败、cninfo 超时等）
```

---

## 3. 数据依赖 & 管道

### 3.1 ticker 清单来源
- 扫 `companies/*/v0.md`，读 YAML frontmatter
- 保留 `status: active`（或 frontmatter 中未填 status，兼容宽松）
- 输出结构：`[{ticker, market, v0_path, last_reviewed, entry_date, position_size_pct}]`

### 3.2 价格数据
- Python 包 `yfinance`
- 对每个 ticker 拉上周五 + 本周五收盘
- ticker 前缀映射：
  - `US_HIMS` → `HIMS`
  - `SSE_600519` → `600519.SS`
  - `SZSE_000858` → `000858.SZ`
  - `HK_0700` → `0700.HK`
- 拉不到的 ticker 记录到推送底部"数据告警"，不中断脚本

### 3.3 财报日历
- **美股**：`yfinance` 的 `ticker.calendar`。免 key，和价格同源。
- **A 股**：cninfo（巨潮资讯网）。endpoint 候选 `http://www.cninfo.com.cn/new/information/getPrbookInfo`，HTTP 直接请求，具体参数实施阶段定。
- **港股**：先走 `yfinance`，实施时评估覆盖率。
- 拉不到某 ticker 财报日期不算错误，仅在"数据告警"记一条。

### 3.4 价格触发池
- 文件路径：`watchlist/price-triggers.md`
- V1 格式（新定义，简单）：

```markdown
## HIMS
- trigger: 20, action: 首建 5%, set_at: 2026-04-15
- trigger: 16, action: 加到 15%, set_at: 2026-04-15
- trigger: 12, action: 加到 25%, set_at: 2026-04-15

## TICKER_X
- trigger: 50, action: 首建 5%, set_at: 2026-04-20
```

- 脚本用正则/简单解析器读这个格式
- DESIGN.md §3.7 定义的 SQLite `price_triggers` 表 V1 **不用**。后期重构时再把 markdown 迁移到 SQLite（v1.3 明确的技术债）。
- 触发判定：本周内任一交易日最低价 <= trigger price

### 3.5 明确不做的数据源
- ❌ 实时行情、日内分时数据
- ❌ 卖方研报、新闻流
- ❌ 三大财务表（SQLite `financials` 表 V1 不填）
- ❌ 基准指数（沪深 300 / SPY 对照）
- ❌ SEC EDGAR

---

## 4. 推送通道 & 存储

### 4.1 本地文件（权威源）
- 路径：`weekly/YYYY-Www.md`
- `weekly/` 目录随主 repo 一起进 git
- 每周一 9:00 脚本写入新文件；不覆盖历史文件
- 同一周重跑会覆盖当周文件（假设你一周只跑一次）

### 4.2 邮件 SMTP（通知通道）
- 渲染 markdown → HTML（用 `markdown` 包基本渲染）
- Subject: `Monday 推送 · YYYY-Www · N 条需要处理`
- From / To：你自己
- 配置在 `.env`：`SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS / FROM_ADDR / TO_ADDR`
- 发件失败不中断脚本。本地 .md 仍然写入，错误追加到 .md 底部"数据告警"。

### 4.3 调度
- 方式：**cron**
- 条目：`0 9 * * 1 /Users/yangqi/investing/bin/monday-push.sh >> /Users/yangqi/investing/weekly/.cron.log 2>&1`
- 已知代价：机器关机的那周推送会丢（cron 默认不补跑）。本人已接受。

### 4.4 失败信号（ack 数）
- 每周一生成新推送前，脚本先读上周 .md，数 `- [x]` 数量
- **连续 5 周 ack 数都是 0** = 系统失败信号
- V1 不做自动通知。信号体现在**月度手动复盘脚本** `bin/monthly-retro.py` 的输出中：
  - 扫 `weekly/*.md`
  - 输出过去 N 周每周的 ack 计数 / 总条目数
  - 标红连续 0 ack 周

### 4.5 目录结构新增项

```
~/investing/
├── weekly/                          # 新增
│   ├── 2026-W17.md
│   └── .cron.log                    # cron 调度日志
├── bin/                             # 新增
│   ├── monday-push.py               # 主脚本
│   ├── monday-push.sh               # cron 入口（激活 venv 调 .py）
│   ├── monthly-retro.py             # 月度复盘（手动跑）
│   ├── _io.py                       # v0.md / price-triggers.md 读写
│   ├── _price.py                    # yfinance 封装
│   ├── _earnings.py                 # 财报日历（美股 yfinance + A 股 cninfo）
│   ├── _triggers.py                 # 价格触发判定
│   ├── _prev_week.py                # 解析上周 .md checkbox
│   ├── _render.py                   # markdown 渲染
│   └── _email.py                    # SMTP 发件
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-04-23-v1-monday-push-design.md  # 本文档
├── .env                             # 新增，.gitignore
├── .env.example                     # 新增，进 git
└── .gitignore                       # 新增或更新：.env、.venv、*.pyc
```

### 4.6 技术依赖（`requirements.txt`）
- `yfinance`
- `PyYAML`
- `python-dotenv`
- `requests`（访问 cninfo）
- `markdown`（渲染 HTML）

---

## 5. 交付计划（Week-by-week）

### Week 0（零代码，启动前）
- 写 1 份真实候选股 v0.md（按 DESIGN.md §3.2 格式），status=active
- 写 `watchlist/price-triggers.md`（至少 1 条）
- 在本仓库 `git init`（如还未 init），加 `.gitignore`

### Week 1：数据管道 + 内容渲染

- **Day 1**：目录骨架、venv、`requirements.txt`、`_io.py`（读 v0.md 和 price-triggers.md）
- **Day 2**：`_price.py`（yfinance 封装 + 市场前缀映射）+ `_earnings.py`（美股 yfinance）
- **Day 3**：`_earnings.py` 的 A 股 cninfo 分支 + `_triggers.py` + `_prev_week.py`
- **Day 4**：`_render.py` + `monday-push.py` 主入口。本地手工跑出一份正确的 `weekly/YYYY-Www.md`
- **Day 5 验收**：`python bin/monday-push.py` 输出的 .md 所有 4 块 + 固定小块正确。脚本不崩。

### Week 2：通知通道 + 调度

- **Day 6-7**：`_email.py`，SMTP 发件跑通
- **Day 8**：cron 配置（先用几分钟后的测试时间），触发、写文件、发邮件跑通
- **Day 9**：改回 `0 9 * * 1`。`bin/monthly-retro.py`（手动跑）
- **Day 10 验收**：下个周一 9:00 真实收到邮件 + 本地 .md 生成。第一周推送至少 ack 1 个 checkbox。

**节奏灵活**：做完就推进，不锁死 10 天。

---

## 6. 验收 & 失败判定

### 6.1 V1 完工判定（同时满足）
- [ ] `bin/monday-push.py` 手工跑生成正确的 `weekly/YYYY-Www.md`（4 块 + 固定小块）
- [ ] cron 按时触发过至少 1 次（`.cron.log` 有记录）
- [ ] 至少收到 1 封真实推送邮件
- [ ] 至少 1 份用户写的 v0.md（status=active）已在推送中出现

### 6.2 V1 成功判定（完工后 1 个月）
- 连续 4 周至少收到 4 份推送（机器关机漏 1 周可接受）
- 至少 1 次 "系统推送 → 打开 V0 → 根据 V0 做决策或显式否决冲动" 的具体事件
- 至少 50% 周的 ack 数 >= 1

### 6.3 V1 失败判定（完工后 1 个月）
任一出现 = 严肃对话：
- 连续 **5 周** ack 数都是 0
- 用户开始给 V1 加新功能但这些功能不产生新的 forcing function（典型滑坡：加图表、加 RSS、加研报抓取——这些都是"B 优先"回潮的信号）
- 用户在没有"服务于某种系统主动行为"的论证下开始建 V2 其他模块

失败触发的自处方（office-hours 明确过）：
> **关掉系统，钱放指数基金。这不是羞耻，是诚实。**

### 6.4 V1 → V2 过渡约束（哲学 7 的精确化）

哲学 7（AI 主动 > 人主动）是硬约束，但"AI 主动" ≠ "周一推送"。新增模块分两类：

**A. 主动触达型**：必须回答"系统在什么时机以什么形式主动找人？"
- 可以是周一推送的新块（如 claims.jsonl 变动 → 推送提示某股 thesis 有新证据）
- 可以是独立触发：
  - 能力圈自检 >=6 个月未更新 → 系统弹问卷
  - V0 被编辑 → 自动 diff 高亮哪几个字段变了
  - 财报发布日 → 自动对照 V0 推翻条件
  - 估值锚变动 > 阈值 → 请你重估
- 立项时必须写清"触发条件 + 呈现形式 + 与人的交互预期"

**B. 支撑型**（数据管道、存储、解析器、导入工具、格式化规则）：
- 本身不直接触达人，但合法存在
- 开工前必须挂钩至少 1 个已存在或同批立项的 A 型模块，说明"我是谁的基石"
- **不允许纯支撑型模块独立立项**——避免"先建仓库，再找用途"的 B 优先回潮

不以"增强某种系统主动行为（A）"或"支撑某种系统主动行为（B 挂钩 A）"为目的的模块扩展，V1 完工 3 个月内原则上不做。

### 6.5 明确不在 V1 范围（留给 V2+）
- SEC EDGAR 事后财报对照 V0 推翻条件
- 任何 LLM 调用
- Web 编辑器 UI
- 共识地图 / claims.jsonl 管道
- 组合级规则自动触发（VIX 降仓等）
- 业绩对比基准（月度 vs 沪深 300 / SPY）

---

## 7. 对 DESIGN.md 的同步建议

这份 spec 落定后，DESIGN.md 需要以下同步改动：

### 7.1 §1 哲学 7 措辞扩展
当前 §1 哲学 7 的大量篇幅描述"做 B 时 B 要增强推送内容"，给人"AI 主动 = 推送"的印象。建议补一句：
> "AI 主动"有多种形式：周一推送、问卷主动弹出、变动提醒、对照提示、自动 diff……周一推送是 V1 最小闭环选中的落地形式，不等于"AI 主动"的全部。

### 7.2 §5 整节替换
把 §5 V1 最小闭环（2-3 周）的原有描述替换为本 spec §1-6 的内容。V2 / V3 保留，但 V2 抬头加一段：
> V1 完工 1 个月后确认没进入失败判定后才启动 V2。V2 每个模块开工前用 v1-monday-push-design §6.4 的 A/B 分类约束自检。

### 7.3 §9 成功标准更新
V1 条目替换为本 spec §6.2。

### 7.4 §10 版本历史新增 v1.3
```
- **v1.3** (2026-04-23)：§5 V1 范围替换为 Monday 推送优先。具体 spec 见 docs/superpowers/specs/2026-04-23-v1-monday-push-design.md。§1 哲学 7 措辞扩展（主动触达多种形式）。§9 V1 成功标准更新。
```

---

## 8. 本次 brainstorm 决策记录

| # | 决策点 | 选择 | 理由 |
|---|---|---|---|
| 1 | 推送通道 | 邮件 SMTP + 本地 .md 双通道 | 邮件覆盖不在电脑前的情况；本地 .md 是权威源，承载 ack 状态 |
| 2 | ticker 监控范围 | 所有 status≠draft 的 V0 + price-triggers | V0 是入场券——无 V0 不监控，强制承诺前置 |
| 3 | Block 4 状态管理 | 推送 .md 里打 ack，未 ack carry over | 无额外 state store；文件即状态；.md 历史诚实 |
| 4 | last_reviewed 维护 | 纯手工 | 维持 review 的含金量；"忘改就重推"接受为 forcing function |
| 5 | AI 参与度 | V1 零 LLM | "AI 主动"指系统主动触达，不指 LLM 生成；V1 纯模板 |
| 6 | 失败信号机制 | ack 数（解析 `- [x]` 数量） | 比 mtime 精确；月度复盘脚本读取 |
| 7 | 空信号周处理 | 仍然推送 + 标"本周无信号" + 固定小块 | forcing function 重节奏，不因信号缺失断链 |
| 8 | cron vs launchd | cron | 用户偏好；接受机器关机那周漏推送 |
| 9 | 美股财报源 | yfinance.calendar | 免 key、和价格同源、零额外依赖 |
| 10 | A 股财报源 | cninfo | 官方权威源 |
| 11 | V1 → V2 过渡约束 | A/B 分类（主动触达型 + 支撑型） | 原表述把哲学 7 狭义化成"必增强推送"；修订后支撑型模块合法但要挂钩 |

---

## 9. Open Questions（实施中解决）

- cninfo HTTP 接口具体参数和解析格式（实施 Day 3）
- SMTP 选哪家（Gmail App Password / Outlook / 163 业务密码），取决于用户邮箱账号可用度
- `.env` 管理是否加密（V1 先明文，macOS Keychain 是 V2 小增强）
- last_reviewed 阈值 30 天是否需要调整——跑 1 个月后根据实际节奏评估
- 港股 yfinance 覆盖率是否够用，实施 Day 2 评估
- status=closed 的 V0 是否也进 Block 3（当前 spec 定"否"，只对 active 追踪；若未来想对照复盘已平仓交易，再调）

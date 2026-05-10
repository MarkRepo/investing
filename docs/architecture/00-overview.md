# 系统概述

Investing 系统是一个**个人投资研究与决策系统**，围绕「Claim（研究断言） → Narrative（叙事档案） → Portfolio（投资组合）」三层模型构建。系统采用文件系统 + SQLite 的混合存储方案，FastAPI 作为 Web 入口，CLI 脚本处理数据流水线。

## 技术栈

| 组件 | 技术 |
|---|---|
| Web 框架 | FastAPI + Uvicorn |
| 模板引擎 | Jinja2 |
| 数据库 | SQLite（仅存行情和财务数据） |
| 文件系统 | JSONL（claims、audit trail、bundles）、YAML（meta）、Markdown（叙事） |
| 行情数据 | AkShare（A 股 / 港股）、yfinance（美股） |
| 报表解析 | PyMuPDF |
| 测试 | pytest + httpx |

## 启动方式

```bash
uvicorn main:app --reload
# 默认监听 http://localhost:8000
```

入口文件 `main.py` 创建 FastAPI 实例，注册 27 个路由路由器（router），挂载 `/static` 静态文件。

## 目录结构

```
investing/
├── main.py                      # FastAPI 应用入口
├── app/
│   ├── config.py                # 路径常量 + 维度定义 + 列映射表
│   ├── templating.py            # 共享 Jinja2 过滤器（价格格式化）
│   ├── routes/                  # 27 个 FastAPI 路由器
│   │   ├── companies.py         # /companies - 公司详情页
│   │   ├── industries.py        # /industries - 行业维度
│   │   ├── arenas.py            # /arenas - 竞技场维度
│   │   ├── bundles.py           # /bundles - ingest bundle 浏览
│   │   ├── sources.py           # /sources - 源文件浏览
│   │   ├── investment_lens.py   # /lens - 投资视角层
│   │   ├── financials.py        # 财务报表查询
│   │   ├── portfolio.py         # /portfolio - 当前持仓
│   │   ├── watchlist.py         # /watchlist - 观察池
│   │   ├── journal.py           # /journal - 决策日志
│   │   ├── valuation.py         # /valuation - 估值场景
│   │   ├── v0.py                # /v0 - 初始投资论点
│   │   ├── triggers.py          # /triggers - 价格触发器
│   │   ├── catalysts.py         # /catalysts - 催化事件
│   │   ├── regime.py            # /regime - 宏观环境判定
│   │   ├── performance.py       # /performance - 收益归因
│   │   ├── discipline.py        # /discipline - 纪律审查
│   │   ├── review.py            # /review - 季度审查
│   │   ├── earnings_review.py   # /earnings-review - 财报审查
│   │   ├── claim_audit.py       # /claim-audit - Claim 审计
│   │   ├── qa.py                # /qa - 质量缺口
│   │   ├── competence_map.py    # /competence-map - 能力圈
│   │   ├── search.py            # /search - 全文搜索
│   │   ├── prices.py            # /prices - 行情页面
│   │   ├── research.py          # /research - 研究入口
│   │   └── prompts.py           # /prompts - 提示词管理
│   ├── io/                      # 30 个 I/O 模块（纯函数 + 文件读写）
│   │   ├── claim_registry.py    # ClaimRegistry 核心类
│   │   ├── claim_matching.py    # Claim 候选匹配引擎
│   │   ├── narrative_proposals.py # 叙事提案生成与应用
│   │   ├── bundle_registry.py   # Bundle 注册表
│   │   ├── industry.py          # 行业元数据 + 叙事读写
│   │   ├── arenas.py            # Arena 元数据 + 叙事读写
│   │   ├── company.py           # 公司元数据 + 叙事读写
│   │   ├── claims.py            # Claim CRUD 操作
│   │   ├── financials.py        # 财务数据查询（SQLite）
│   │   ├── quotes.py            # 行情数据操作
│   │   ├── portfolio.py         # 持仓表操作
│   │   ├── watchlist.py         # 观察池操作
│   │   ├── journal.py           # 决策日志操作
│   │   ├── valuation.py         # 估值场景操作
│   │   ├── v0.py                # V0 投资论点操作
│   │   ├── triggers.py          # 价格触发器
│   │   ├── catalysts.py         # 催化事件
│   │   ├── regime.py            # 宏观环境
│   │   ├── performance.py       # 收益归因
│   │   ├── rules.py             # 组合规则校验
│   │   ├── discipline.py        # 纪律审查
│   │   ├── review.py            # 季度审查
│   │   ├── earnings_review.py   # 财报审查
│   │   ├── qa.py                # 质量告警
│   │   ├── search.py            # 全文搜索
│   │   ├── figure_contexts.py   # 图表引用
│   │   ├── competence_map.py    # 能力圈
│   │   ├── macro_risks.py       # 宏观风险
│   │   ├── adapters/            # 行情适配器
│   │   │   ├── base.py          # QuoteAdapter 协议
│   │   │   ├── akshare_adapter.py  # A 股 / 港股
│   │   │   └── yfinance_adapter.py # 美股
│   └── templates/               # 28 个 Jinja2 HTML 模板目录
├── scripts/                     # CLI 脚本（python -m scripts.xxx）
│   ├── preprocess_report.py     # PDF 报告预处理（提取章节/事实）
│   ├── ingest_match.py          # Claim 候选匹配
│   ├── ingest_apply.py          # 应用匹配决策到 ClaimRegistry
│   ├── ingest_aggregate.py      # 聚合 bundle → claims + proposals
│   ├── ingest_qa.py             # ingest 质量审查
│   ├── narrative_propose.py     # 生成叙事提案
│   ├── narrative_apply.py       # 应用叙事提案到档案
│   ├── narrative_flags.py       # 叙事标记扫描
│   ├── industry_narrative_*.py  # 行业叙事专用脚本
│   ├── company_narrative_*.py   # 公司叙事专用脚本
│   ├── fetch_quotes_eod.py      # 日线行情回填
│   ├── fetch_financials_cn.py   # A 股财务数据抓取
│   ├── fetch_financials_us.py   # 美股财务数据抓取
│   └── preprocess_figure_contexts.py  # 图表上下文预处理
├── claims/                      # ClaimRegistry 存储
│   ├── industries.jsonl         # industry-scoped claims
│   ├── arenas.jsonl             # arena-scoped claims
│   ├── companies.jsonl          # company-scoped claims
│   ├── cross_cutting.jsonl      # 跨领域 claims
│   └── .counters.json           # ID 自增计数器
├── audit/
│   └── claim-events.jsonl       # Claim 事件审计日志
├── data/
│   ├── financials.db            # SQLite（quotes_daily + financials_cn/us）
│   ├── bundle_registry.jsonl    # Bundle 注册表
│   ├── audit/
│   │   └── narrative-events.jsonl  # 叙事事件审计日志
│   └── pending/archive/         # 已归档的提案文件
├── industries/{slug}/           # 行业档案（每个目录含 meta.yaml + 维度 .md）
├── arenas/{slug}/               # 竞技场档案（每个目录含 definition.md + 维度 .md）
├── companies/{MARKET}_{TICKER}/ # 公司档案（meta + v0 + valuation + narratives）
├── watchlist/                   # 观察池（stage-{n}.md）
├── portfolio/                   # 持仓表（positions.md + rules.md + triggers.md）
├── journal/                     # 决策日志
│   └── decisions/{YYYY}-Q{n}/   # 按季度组织的决策记录
├── macro/                       # 宏观环境判定
├── controlled-vocab/            # 受控词汇表（claim_type 白名单等）
├── templates/                   # 公司创建模板（meta.md.tmpl, v0.md.tmpl, valuation.md.tmpl）
├── static/                      # 静态资源（CSS/JS）
└── tests/                       # 91+ 测试文件
```

## 三层知识模型

系统核心是 **Industry → Arena → Company** 三层知识模型：

```
Industry（行业）        cn-pet-industry
  ├── 11 个叙事维度    definition, market_size, lifecycle, ...
  └── 关联多个 Arenas  + 多个 Companies

Arena（竞技场）        cn-pet-food
  ├── 6 个叙事维度     definition, participants, decisive_factors, ...
  └── 有 checklist    参与者能力矩阵问答

Company（公司）        SSE_603011
  ├── 8 个叙事维度     business_model, moat, growth_engine, ...
  ├── v0.md            初始投资论点（7 节模板）
  ├── valuation.md     三场景估值模型
  ├── trade-log.md     交易执行记录
  └── claims.jsonl     公司级 claims（本地）
```

每条知识都有 **Claim（原子断言）** 支撑，Claim 通过 `scope_type` + `scope_ref` 锚定到具体层级。

## 核心设计原则

1. **文件系统优先**：绝大部分数据是纯文本文件，git 友好，可 diff/merge
2. **SQLite 仅存结构化时序数据**：行情（quotes_daily）和财务报表（financials_cn/us）
3. **Claim 是不可变的**：一旦创建只追加证据，不修改原始声明；split 操作将原 claim 标记为 retired
4. **审计追踪**：所有 claim 和 narrative 操作都追加到 JSONL 审计日志
5. **维度路由**：claim 的 `dimension_hint` 通过映射表路由到对应叙事维度文件
6. **无 LLM 调用**：Python 脚本不调用 LLM API，所有 LLM 判断在 Claude 会话中完成

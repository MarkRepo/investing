# Web 路由

FastAPI 应用入口在 `main.py`，注册了 27 个路由器。所有路由都返回 HTML 页面（Jinja2 模板渲染）。

## 路由列表

### 首页

| 路径 | 方法 | 模块 | 说明 |
|---|---|---|---|
| `/` | GET | `main.py` | 仪表盘：待审查、触发的触发器、即将到期的催化、逾期研究、大波动、报价错误、QA 缺口 |
| `/healthz` | GET | `main.py` | 健康检查 |

### 研究层

| 路径 | 方法 | 模块 | 说明 |
|---|---|---|---|
| `/companies` | GET | `companies.py` | 公司列表 |
| `/companies/{slug}` | GET | `companies.py` | 公司详情：meta + v0 + 8 维叙事 + linked industries/arenas |
| `/industries` | GET | `industries.py` | 行业列表 |
| `/industries/{slug}` | GET | `industries.py` | 行业详情：meta + 11 维叙事 + linked arenas/tickers + 图表上下文 |
| `/arenas` | GET | `arenas.py` | 竞技场列表 |
| `/arenas/{slug}` | GET | `arenas.py` | 竞技场详情：definition + checklist + participants + 5 维叙事 + industry 反向链接 |
| `/bundles` | GET | `bundles.py` | Bundle 注册表浏览 |
| `/sources` | GET | `sources.py` | 源文件浏览 |
| `/lens` | GET | `investment_lens.py` | 投资视角层：综合 bundles + claims + archive 的判断视图 |
| `/research` | GET | `research.py` | 研究入口 |

### 组合与交易层

| 路径 | 方法 | 模块 | 说明 |
|---|---|---|---|
| `/portfolio` | GET | `portfolio.py` | 当前持仓表 + 规则校验结果 |
| `/watchlist` | GET | `watchlist.py` | 观察池（按阶段分组） |
| `/triggers` | GET | `triggers.py` | 价格触发器列表 |
| `/catalysts` | GET | `catalysts.py` | 催化事件日历 |
| `/valuation` | GET | `valuation.py` | 估值场景管理 |
| `/v0` | GET | `v0.py` | V0 投资论点管理 |
| `/prices/{market}/{ticker}` | GET | `prices.py` | 个股行情页面 |

### 审查与纪律层

| 路径 | 方法 | 模块 | 说明 |
|---|---|---|---|
| `/journal` | GET | `journal.py` | 决策日志列表 |
| `/journal/{id}` | GET | `journal.py` | 单条决策详情 |
| `/regime` | GET | `regime.py` | 宏观环境判定（估值分位、VIX、情绪） |
| `/review` | GET | `review.py` | 季度审查汇总 |
| `/earnings-review` | GET | `earnings_review.py` | 财报审查 |
| `/discipline` | GET | `discipline.py` | 纪律审查（未评审的决策缺口） |
| `/performance` | GET | `performance.py` | 收益归因分析 |
| `/qa` | GET | `qa.py` | 质量缺口（按 scope 分组的 open warnings） |
| `/claim-audit` | GET | `claim_audit.py` | Claim 审计浏览 |

### 工具层

| 路径 | 方法 | 模块 | 说明 |
|---|---|---|---|
| `/search` | GET | `search.py` | 全文搜索 |
| `/prompts` | GET | `prompts.py` | 提示词索引 |
| `/competence-map` | GET | `competence_map.py` | 能力圈地图 |
| `/financials/{market}/{ticker}` | GET | `financials.py` | 财务报表查看 |

## 路由注册顺序

`main.py` 按顺序 include_router，先注册的优先级更高（影响 URL 匹配）：

```python
prompts_router       # /prompts（先注册以精确匹配 /prompts GET）
companies_router     # /companies
v0_router            # /v0
valuation_router     # /valuation
financials_router    # /financials
watchlist_router     # /watchlist
portfolio_router     # /portfolio
research_router      # /research
search_router        # /search
journal_router       # /journal
earnings_review_router  # /earnings-review
prices_router        # /prices
triggers_router      # /triggers
performance_router   # /performance
review_router        # /review
catalysts_router     # /catalysts
regime_router        # /regime
competence_map_router   # /competence-map
industries_router    # /industries
discipline_router    # /discipline
claim_audit_router   # /claim-audit
qa_router            # /qa
arenas_router        # /arenas
bundles_router       # /bundles
sources_router       # /sources
investment_lens_router  # /lens
```

注意 `/prompts` 路由先注册以确保 `/prompts` GET 命中索引页面而非静态文件挂载。

## IO 模块

所有 I/O 操作封装在 `app/io/` 目录下，路由层只做 **调用 IO 函数 → 组装模板数据**，不含业务逻辑。

```python
# 典型路由模式
@router.get("/{slug}")
def detail(request: Request, slug: str):
    data = io_module.read_entity(slug)  # 调用 IO 函数
    return templates.TemplateResponse(request, "template.html", {"data": data})
```

## 模板

所有 HTML 模板位于 `app/templates/`，按路由名分子目录：

```
app/templates/
├── base.html            # 基础布局（导航栏、样式）
├── home.html            # 仪表盘首页
├── companies/
│   ├── index.html       # 公司列表
│   └── detail.html      # 公司详情（含 narrative 循环渲染）
├── industries/
│   ├── index.html
│   └── detail.html
├── arenas/
│   ├── index.html
│   └── detail.html（含 checklist 矩阵 + 叙事 tab）
├── investment_lens/     # 投资视角页面
├── bundles/
├── sources/
├── portfolio/
├── watchlist/
├── journal/
├── valuation/
├── v0/
├── prices/
├── triggers/
├── catalysts/
├── regime/
├── review/
├── earnings_review/
├── discipline/
├── performance/
├── qa/
├── research_audit/
├── research/
├── competence_map/
└── prompts/
```

## 静态资源

`/static` 挂载 `static/` 目录，提供 CSS/JS 等静态文件。

## Jinja2 自定义过滤器

注册在 `app/templating.py`：

| 过滤器 | 用途 | 示例 |
|---|---|---|
| `fmt_price` | 价格格式化（2 位小数） | `1234.5 → "1,234.50"` |
| `fmt_big` | 大数字格式化（B/M/K 或 亿/万） | `1.2e9 → "$1.20B"` (US) / `"12.00亿"` (CN) |
| `fmt_int` | 整数带千分位 | `1000000 → "1,000,000"` |

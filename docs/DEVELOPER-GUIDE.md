# 开发者指南

> 配合 [`DESIGN.md`](../DESIGN.md)（产品设计）和 [`USER-GUIDE.md`](./USER-GUIDE.md)（使用说明）阅读。本文档讲**代码为什么这样组织**。

目标读者：刚接手这个代码库的工程师。

---

## 1. 一句话总览

单进程、本地运行的 FastAPI 应用。**markdown 文件是权威数据源，SQLite 只承载派生与定量数据**（financials / prices / ratios / price_triggers / benchmark）。没有 JavaScript 框架，没有 ORM，没有 Celery，没有后台 LLM 调用。所有"智能"都发生在用户与 LLM 的对话里，系统只负责**校验 + 存储 + 查询**。

---

## 2. 技术栈

| 组件 | 选择 | 不选什么 | 原因 |
|---|---|---|---|
| Web 框架 | FastAPI | Flask/Django | 轻量 + 类型友好；单人使用，没必要 Django |
| 模板 | Jinja2 | React/Vue | 无 JS 框架的信念：减少工具链，markdown + HTML 足够 |
| 数据 | markdown + YAML frontmatter | JSON/数据库 | 断电可读，git 可控，`grep` 可搜 |
| 结构化数据 | SQLite（单文件） | Postgres | 个人数据规模；派生层，可删重建 |
| 测试 | pytest + tmp_path fixture | unittest | BASE_PATH 注入使测试天然隔离 |
| 依赖 | 见 `requirements.txt` | 任何大框架 | `fastapi / jinja2 / uvicorn / pyyaml / pytest` 足矣 |
| LLM 调用 | **无** | OpenAI/Anthropic SDK | 见第 11 节"LLM 反转" |

**Python ≥3.11**（使用 `from __future__ import annotations`，类型提示在运行时不求值）。

---

## 3. 顶层目录

```
investing/
├── main.py                    # FastAPI 入口 + 首页 route
├── app/
│   ├── config.py              # 所有路径常量 + 受控词表
│   ├── io/                    # 纯数据层：读/写/解析
│   ├── routes/                # HTTP 层：表单验证 + 模板渲染
│   └── templates/             # Jinja2 模板
├── templates/                 # **业务** markdown 模板（新建公司时拷贝用）
├── controlled-vocab/          # 能力圈词表（yaml）
├── docs/                      # 设计、计划、本文档
├── tests/                     # pytest
├── companies/ industries/ ...  # 数据目录（运行时生成）
└── data/financials.db         # 唯一 SQLite
```

**三个 `templates/` 目录不要搞混**：
1. `app/templates/` — Jinja2 HTML 模板
2. `templates/` — 业务 markdown 模板（创建公司时 `copy_tree` 进 `companies/<key>/`）
3. `docs/prompts/` — LLM 提示词

---

## 4. 分层约定

### io/ 层（数据）
- **零 HTTP 知识**。不知道 `Request`，不 raise `HTTPException`
- **接受 `base: Path | None = None` 参数**。默认用 `cfg.BASE_PATH`，测试时传 `tmp_path`
- **抛 `ValueError` / `LookupError` / `FileNotFoundError`**，由 routes 层翻译成 HTTP 错误
- **不做 I/O 缓存**。每次查询都读磁盘（个人用，单进程，OS page cache 已经够快了）

### routes/ 层（HTTP）
- **每个路由文件一个 `APIRouter`，带 `prefix`**
- **逻辑薄**：表单 → io 调用 → 模板上下文。业务规则放 io 层
- **`response_class=HTMLResponse` 或返回 `templates.TemplateResponse`**
- **POST 之后 302 重定向到 GET**（Post/Redirect/Get 模式，防表单重提交）

### templates/ 层（视图）
- **`base.html` 提供导航 + 消息框架**；所有页面 `{% extends "base.html" %}`
- **表单 action 指向自己**，用 `method="post"` 原生 HTML，没有 AJAX
- **警示类用 `fieldset.warn-section`**，纪律红旗用 `row-overdue / row-due` CSS 类

---

## 5. 核心设计模式

### 5.1 `BASE_PATH` 注入（可测试性）
所有路径常量定义在 `app/config.py`：

```python
BASE_PATH = Path(__file__).resolve().parent.parent
COMPANIES_DIR = BASE_PATH / "companies"
...
```

io 函数签名长这样：

```python
def read_watchlist(stage: str, base: Path | None = None) -> list[dict]:
    base = base or cfg.BASE_PATH
    path = base / "watchlist" / f"{stage}.md"
    ...
```

测试里用 `monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)` 或直接 `base=tmp_path`，每个测试独立、不污染真实数据。这是整个代码库最重要的模式。

**反例**：`app/io/prompts.py` 和 prompts StaticFiles mount 都 `Path(__file__).resolve().parent / "docs/prompts"` —— 因为这些是**仓库自带资源**，不是用户数据，不应随 `BASE_PATH` 移动。判断标准：读用户数据的用 `base`；读仓库代码/资源的用 `Path(__file__)`。

### 5.2 markdown + frontmatter 解析
几乎每个数据文件都是：

```markdown
---
ticker: HIMS
market: US
industry_slugs: [us-telehealth]
themes: [telehealth, GLP-1]
---

# 正文（自由 markdown）
```

读写规约：
- **读**：每个 io 模块有自己的 `_FRONTMATTER_RE` + `yaml.safe_load`
- **写**：保留原 body，仅重写 frontmatter 区域（`write_meta` 是这个模式的参考实现）
- **列表字段**（如 `themes`）：用户可以写 `[a, b]` 或 `a, b`；io 层统一 coerce 成 list
- **没有 frontmatter 的也视为合法**（旧文件兼容），frontmatter 为空 dict

### 5.3 受控词表
所有枚举集中在 `app/config.py`：
- `VALID_MARKETS = ("US", "SSE", "SZSE", "BSE", "HK")`
- `INDUSTRY_DIMENSIONS` / `ARENA_DIMENSIONS` / `COMPANY_DIMENSIONS`（三层知识框架，spec §4.5）
- `INDUSTRY_FIELDS`（每个行业维度的结构化字段建议列表；开放词表，不强制）
- `INCOME_STATEMENT_LINES` / `BALANCE_SHEET_LINES` / `CASHFLOW_LINES`（财务 line item 规约，spec §4.7）

其他词表分散在对应 io 模块：
- `watchlist.py`: `SOURCE_TYPES = ("quant_screen", "qual_radar", "product_experience")`
- `review.py`: `POLARITIES = ("up", "down", "flat")`

**行业不再是枚举词表**：company.meta 的 `industry_slugs` 是自由文本 list，每个 slug 对应 `industries/{slug}/` 一个注册行业。新增行业 = 在 `industries/` 下 `create_industry()`，不用改代码。

**原则（维度词表）**：增/改 `*_DIMENSIONS` 元组 = 改代码 + 改测试 + 改模板。这是刻意设计的阻力。

### 5.4 控制表格分隔符
`watchlist/researching.md` 是 markdown 表格。**body 里不能出现 `|`**（会被 markdown table parser 当列分隔）。具体影响：`gate_notes` 三个理由拼接用 `" ; "` 而不是 `" | "`。遇到这类字段时注意检查。

### 5.5 Post/Redirect/Get + 消息
表单提交失败时有两条路径：
- 验证错误（ValueError）→ 回写原始表单值 + 错误消息（同页面 200）
- 成功 → 302 到列表/详情页

消息通过模板的 `{% if error %} / {% if success %}` 块显示。没做 flash middleware，单进程单会话场景不需要。

### 5.6 路由前缀冲突
FastAPI 动态段匹配顺序敏感。`/research/{key}` 会抢走 `/research/audit` —— 所以 claim 抽查路由挂在 `/research-audit`。 **新建路由时先 grep 已有的 prefix**，避免静默 route shadowing。

### 5.7 确定性采样
`app/io/claims.py::audit_sample` 使用 `hashlib.sha256(month.encode()).digest()` 作为 `random.Random` seed，保证同一月份每次抽样结果相同。用户关闭刷新回来还是同一批。任何"应当稳定"的随机行为照此办理，不要用 `random.random()` 直接起。

### 5.8 SQLite 连接
- `financials.connect(base=...)` 单次调用返回 `sqlite3.Connection`（`row_factory=Row`）
- `prices.py` 沿用同一连接池（通过 `fin_io.connect` 复用）
- io 函数有 `owns = conn is None; conn = conn or fin_io.connect(...)` 模式——既可独立调用也可参与事务
- **`conn.commit()` 每次写操作后显式调**（不依赖 autocommit）

---

## 6. 数据流走查：创建公司 → 写 V0

追踪一次典型用户动作，看请求怎么流过各层：

```
POST /companies/new
    ↓
app/routes/companies.py::new_submit
    ↓ 读表单 → 解析 industry_slugs（逗号分隔 → list）
    ↓ 验证 ticker/market
    ↓
app/io/company.py::create_company
    ↓ mkdir companies/<key>/
    ↓ 从 templates/ 拷贝 meta.md / v0.md / valuation.md / trade-log.md 骨架
    ↓ 写入 profile-YYYY.md
    ↓ 创建 narratives/ 8 维骨架（business-model / moat / ... / valuation）
    ↓
302 → /companies/<key>

GET /companies/<key>/v0
    ↓
app/routes/v0.py::v0_edit
    ↓
app/io/v0.py::read_v0
    ↓ 读 companies/<key>/v0.md → 解析 frontmatter + body
    ↓
render app/templates/v0/edit.html

POST /companies/<key>/v0
    ↓
app/routes/v0.py::v0_save
    ↓ 校验 7 字段都填了
    ↓
app/io/v0.py::write_v0
    ↓ 重写 companies/<key>/v0.md
    ↓
302 → /companies/<key>
```

**注意**：没有 Service 层，没有 UnitOfWork，没有 Repository 抽象。io 函数自己封装"读 → 改 → 写"全流程。这是单人小系统的意识形态——三层抽象会压垮可读性。

---

## 7. 测试策略

### 7.1 文件布局
- `tests/test_<module>_io.py` 对应 `app/io/<module>.py` —— 纯数据层测试
- `tests/test_routes_smoke.py` —— 所有 GET 200 冒烟 + 关键 POST 走通

### 7.2 Fixture 约定
**每个 io 测试文件**有自己的 `base` fixture：

```python
@pytest.fixture
def base(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cfg, "FINANCIALS_DB", tmp_path / "data" / "financials.db")
    return tmp_path
```

如果测试触及多个数据目录，把 `monkeypatch` 扩展到该目录对应的 `cfg.XXX_DIR`。**不够就补，不要一次性改 config 把所有 DIR 都 monkeypatch**——那会让"谁依赖什么"变隐式。

### 7.3 routes smoke 测试
`test_routes_smoke.py` 用 `fastapi.testclient.TestClient` + 一个共享 `tmp_path`，塞几个种子数据，然后挨个 GET 断 200。新建 route 必须在这里加一条。**这不是替代单测**，是"改了代码至少别把页面渲染挂了"的底线。

### 7.4 TDD 节奏
现有代码是按 "failing test → 最小实现 → commit" 走的。看 `tests/test_big_movers.py` 这种小文件，典型 5-step：

1. 空状态测试
2. 前置条件测试（需要 2 个 close）
3. 计算正确性测试
4. 阈值以上 flag 测试
5. 阈值参数测试

**加功能时沿用这个节奏**。不要写 500 行实现再补测试。

### 7.5 不 mock 的东西
- **不 mock SQLite**：用 `tmp_path` + 真实 `sqlite3` 连接（内存库都不用，就写文件——几毫秒开销换"跟生产一致"）
- **不 mock 文件系统**：`tmp_path` 原生 fixture
- **不 mock HTTP**：`TestClient` 同进程调用

整个测试套约 258 个，<3 秒跑完。保持这个速度。

---

## 8. 已知陷阱速查

| 症状 | 原因 | 解决 |
|---|---|---|
| 表格里有一行突然没显示 | body 里出现 `\|`，被当列分隔 | 换分隔符（见 5.4） |
| 路由 404 但代码里明明注册了 | Prefix 冲突被动态段抢走 | grep `APIRouter(prefix=` 查重（见 5.6） |
| 测试偶尔失败 | 用了 `random` 没 seed | 用 hash-seed（见 5.7） |
| 测试相互污染 | 忘了 `monkeypatch` 某个 `cfg.XXX_DIR` | 补 monkeypatch |
| frontmatter 读不到某字段 | 文件里写的是 list，代码期望 str（或反之） | io 层加 coerce（见 5.2） |
| 新行业加了但页面崩 | `industries/{slug}/meta.md` 没建；或 arena 维度 slug 打错 | `industry_io.create_industry()` + spec §4.5 |
| 首页加载慢 | `discipline.review_gaps` / `big_movers` 是 O(tickers × SQLite queries) | 如果持仓 >50 才考虑优化，不是现在 |

---

## 9. 扩展指南：加一个新功能

以"加一个卖方一致性预期模块 /consensus"为例：

1. **想清楚存什么**：markdown 还是 SQLite？
   - 主观判断、长文本、低更新频率 → markdown
   - 数值、时间序列、需要聚合 → SQLite

2. **先写测试**（`tests/test_consensus_io.py`）：空读、单写、覆盖写、验证失败三个

3. **写 io**（`app/io/consensus.py`）：
   - `read_consensus(ticker, base=None)` / `write_consensus(ticker, data, base=None)`
   - ValueError 抛业务错误
   - 不知道 HTTP

4. **写 route**（`app/routes/consensus.py`）：
   - `APIRouter(prefix="/companies/{key}/consensus", tags=["consensus"])`
   - GET 渲染模板，POST 调 io + 302

5. **写模板**（`app/templates/consensus/edit.html`）：继承 `base.html`

6. **注册 router**：`main.py` 加一行 `app.include_router(consensus_router)`

7. **加 smoke 测试**：`tests/test_routes_smoke.py` 加一条 GET 断言

8. **更新入口**：首页 `home.html` 的导航、详情页 `companies/detail.html` 的链接

9. **更新 DESIGN.md**：把这个模块对应 §几.几 节更新或补充

---

## 10. 提交与工作流

### 提交规范
- 原子提交：一个 commit 一件事
- 消息体：简中，jj 习惯
  - `feat: 加 consensus 模块`
  - `fix: 修复 watchlist gate 中文字符计数`
  - `test: 补 big_movers 阈值测试`
- 不要 `git add .`，显式列文件（误包含临时数据风险）

### 冻结契约
**永远不改**下列东西（会让已有数据失效）：
- `industries/{slug}/` 目录名（被 company.meta.industry_slugs 引用）
- SQLite 表主键列
- markdown frontmatter 已存在的 key（可以加新 key，不能删/改现有 key）

要改的话，走迁移脚本（`scripts/migrate_YYYY_MM_DD_*.py`，目前还没用上）。

---

## 11. LLM 反转（DESIGN v1.2/v1.3）

早期设计里有 `app/io/b_research/llm_client.py` 这样的东西——系统自己调 Anthropic API 帮用户抽 claim。v1.2 反转了：

**现在的模型**：
- LLM 对话发生在 Claude Code / 任意聊天窗口里，用户贴 prompt、拿结果
- 结果手动粘贴进 `/research/<key>`
- 系统只校验 schema（source_file 必须存在、subject_tag 必须在词表等）

**这样做的理由**：
1. 不想被 API 价格和限流影响系统能否使用
2. 断网也要能写 V0
3. "智能"如果能被工具化，用户就会把该自己写的 V0 扔给系统——违反哲学 2

**实操影响**：代码库里**不应该有**任何 `httpx.post("https://api.anthropic.com/...`）。如果你在加功能时觉得"这里让 AI 帮一下就好了"，答案是：加个 prompt 模板进 `docs/prompts/`，让用户自己去对话里跑。

唯一例外是 DESIGN v1.2 反转后留下的"AI 主动推送"这条方向（哲学 7）——目前未实现，未来做的话也是**后台独立进程**（cron/daemon）主动给用户推消息，不是 Web 请求链路里的 LLM 调用。

---

## 12. 路由一览（速查）

自动生成的列表，代码权威。更新时直接重新 `grep`：

```
/                            main.py
/healthz                     main.py
/companies                   companies.py
/companies/new               companies.py
/companies/{key}             companies.py
/companies/{key}/meta        companies.py
/companies/{key}/profile/{year}  companies.py
/companies/{key}/v0          v0.py
/companies/{key}/competence  competence.py
/companies/{key}/valuation   valuation.py
/companies/{key}/financials  financials.py
/companies/{key}/triggers    triggers.py
/industries                  industries.py (501, UI 迁移中，spec §D)
/industries/{slug}           industries.py (501)
/industries/{slug}/{kind}    industries.py (501)
/watchlist                   watchlist.py
/watchlist/add/{stage}       watchlist.py
/watchlist/move              watchlist.py
/portfolio                   portfolio.py
/portfolio/rules             portfolio.py
/portfolio/position          portfolio.py
/journal                     journal.py
/journal/new                 journal.py
/journal/{entry_id}          journal.py
/earnings-review             earnings_review.py
/earnings-review/{key}       earnings_review.py
/prices                      prices.py
/performance                 performance.py
/performance/benchmark-import  performance.py
/regime                      regime.py
/regime/{quarter}            regime.py
/review                      review.py
/review/{quarter}            review.py
/catalysts                   catalysts.py
/competence-map              competence_map.py
/discipline                  discipline.py
/research/{key}              research.py
/research-audit              claim_audit.py
/search                      search.py
/prompts                     prompts.py
```

---

## 13. 不要做的事

- ❌ 不要加 ORM（SQLAlchemy / Tortoise）。手写 SQL 和 Row 就够了
- ❌ 不要加 Redis / Celery。没有异步任务需要
- ❌ 不要加 JavaScript 框架。原生 `<form>` POST 完全覆盖
- ❌ 不要加 OpenAPI docs 暴露。没有外部消费者
- ❌ 不要加用户系统 / 权限 / 登录。单机单人
- ❌ 不要把 markdown 权威性倒过来（变成 DB 权威 + markdown 导出）。会死得很难看——markdown 是用户**用手改**的文件，DB 做不到可审计
- ❌ 不要加 auto-reload 之外的"智能"（比如后台扫描/定时刷新价格）。用户主动触发的才算决策，自动的就污染了责任归属
- ❌ 不要让 io 层打日志到文件/远程。断言失败 raise ValueError 就够，堆栈在 uvicorn 终端里看

---

## 14. 常用命令

```bash
# 启动（开发）
uvicorn main:app --reload

# 跑全部测试
pytest

# 只跑一个模块
pytest tests/test_watchlist_io.py -v

# 跑一个测试
pytest tests/test_big_movers.py::test_daily_move_pct_computes -v

# 看路由列表
python -c "from main import app; [print(r.path) for r in app.routes]"

# 备份数据
tar czf ~/investing-backup-$(date +%F).tar.gz \
    companies industries watchlist portfolio macro journal data controlled-vocab
```

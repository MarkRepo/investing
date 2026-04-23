# V1 实施计划

> **依据**：DESIGN.md §5 V1 最小闭环 + 附录 B。
> **版本**：2026-04-23 · v1.0
> **目标周期**：2-3 周
> **当前状态**：从零起。仓库已清空（只保留 `archive/`、`DESIGN.md`、`docs/PLAN.md` 以及 `.git`/`.venv`/`.gitignore`/`.obsidian` 等基础设施）。

---

## 0. V1 的范围与不做

### 0.1 V1 的一句话目标

让"候选公司 → 研究 → 决策 → 记录 → 监控"的**完整决策循环**能用本地 Web 应用完整跑通，**内容全部手工填写**，系统只提供结构、模板、界面、搜索。

### 0.2 V1 的成功判定（来自 §5）

1. 能用系统走完一遍"研究 1 只真实候选股 → 写 V0 → 做（模拟）决策"流程。
2. 所有模板逼使用者把重要字段填到位。
3. 系统能用 grep 回答："找所有研究中的白酒公司"、"找所有未完成能力圈自检的公司"。
4. 至少手工完成 1 次完整循环（含 1 次模拟买入 + 1 次模拟卖出/review）。

### 0.3 V1 明确不做（延后到 V2+）

- ❌ LLM 研报抽取（手工读研报填 V0）
- ❌ 财报数据自动抓取（手工录入或跳过）
- ❌ 价格触发自动提醒（靠自己每天看）
- ❌ 催化剂日历
- ❌ 市场钟摆层
- ❌ 业绩度量
- ❌ 投资日志的完整过程/结果分离结构（先简单文本记录）
- ❌ yfinance / finnhub 等任何外部数据 API

### 0.4 起点（从零）

仓库当前只剩：
- `archive/DESIGN-DIALOGUE.md`：设计对话历史（不动）
- `DESIGN.md`：设计总文档（权威源）
- `docs/PLAN.md`：本计划
- `.git`、`.gitignore`、`.env.example`、`.venv`、`.obsidian`：基础设施

前次 Monday 推送方向的探索代码（`bin/`、`fixtures/`、`tests/`、`weekly/`、`pytest.ini`、`requirements.txt`）已全部清空。本计划从零开始建立 §5 方向的 V1。

`.env.example` 残留的 SMTP 配置（用于推送邮件）V1 不用，但不删；V2 可能复用。
`.gitignore` 保留，V1 可能再加 `data/*.db`、`*.env` 等条目。

---

## 1. 技术栈（锁定）

| 层 | 选型 | 理由 |
|---|---|---|
| Web 框架 | FastAPI | DESIGN §4 指定；类型提示友好 |
| ASGI 服务器 | uvicorn | FastAPI 标配 |
| 模板 | Jinja2（FastAPI 内置接入） | DESIGN §4 明确「服务端渲染 HTML」，不用前端框架 |
| 表单/文件 | python-multipart | FastAPI 表单依赖 |
| 存储 | 文件系统 + markdown + YAML frontmatter | DESIGN §4 明确 |
| 查询 | grep 的 subprocess 封装 | DESIGN §5 V1 明确 |
| 测试 | pytest | 业界标准，T1.1 加回 |
| 启动 | `uvicorn main:app --reload` | DESIGN 附录 B Day 2-3 明确 |

不用：SQLAlchemy、PostgreSQL、React/Next.js、云服务。

---

## 2. 文件结构（V1 结束时应有）

```
~/investing/
├── DESIGN.md                          # 既有
├── README.md                          # T1.1 新建
├── requirements.txt                   # T1.1 新建
├── pytest.ini                         # T1.1 新建
├── main.py                            # T2.1 新建，FastAPI app 入口
├── app/                               # 后端代码
│   ├── __init__.py
│   ├── config.py                      # 路径常量、基础配置
│   ├── io/                            # 文件 I/O 层
│   │   ├── __init__.py
│   │   ├── v0.py                      # V0 读写
│   │   ├── competence.py              # 能力圈自检读写 + 评分
│   │   ├── valuation.py               # 估值读写 + 加权计算
│   │   ├── watchlist.py               # 观察池三段读写
│   │   ├── portfolio.py               # 持仓读写
│   │   ├── journal.py                 # 投资日志读写
│   │   ├── sources.py                 # 研报源读写
│   │   ├── claims.py                  # claims.jsonl 读写
│   │   ├── company.py                 # 一键建公司目录
│   │   └── search.py                  # grep 封装
│   ├── routes/                        # HTTP 路由
│   │   ├── __init__.py
│   │   ├── home.py                    # 首页（导航）
│   │   ├── companies.py               # 公司列表/详情
│   │   ├── v0.py                      # V0 编辑
│   │   ├── competence.py              # 能力圈自检
│   │   ├── valuation.py               # 估值
│   │   ├── watchlist.py               # 观察池
│   │   ├── portfolio.py               # 持仓
│   │   ├── research.py                # 研究工作台
│   │   └── search.py                  # 搜索
│   └── templates/                     # Jinja2 模板
│       ├── base.html                  # 母版（导航 + 样式）
│       ├── home.html
│       ├── companies/list.html
│       ├── companies/detail.html
│       ├── companies/new.html
│       ├── v0/edit.html
│       ├── v0/preview.html
│       ├── competence/edit.html
│       ├── competence/view.html
│       ├── valuation/edit.html
│       ├── valuation/view.html
│       ├── watchlist/index.html
│       ├── portfolio/index.html
│       ├── research/index.html
│       └── search/results.html
├── templates/                         # 业务文档模板（新建公司时拷贝）
│   ├── v0.md.tmpl
│   ├── competence-check.md.tmpl
│   ├── valuation.md.tmpl
│   ├── journal-decision.md.tmpl
│   ├── meta.md.tmpl
│   ├── profile-YYYY.md.tmpl
│   └── trade-log.md.tmpl
├── static/                            # 样式 + 轻量 JS
│   └── style.css
├── controlled-vocab/                  # DESIGN §3.1
│   ├── subjects.yaml                  # B 研究词表（V1 先放骨架）
│   ├── competence-core.yaml           # 通用 12 问
│   └── competence-sector/
│       ├── consumer.yaml              # V1 填写
│       ├── saas.yaml                  # V1 填写
│       ├── cyclical.yaml              # V1 仅占位
│       ├── bank.yaml                  # V1 仅占位
│       └── biotech.yaml               # V1 仅占位
├── companies/                         # 实际公司数据（V1 由 UI 创建）
├── industries/                        # V1 空目录 + .gitkeep
├── watchlist/
│   ├── prefilter.md                   # 空表头
│   ├── researching.md
│   └── price-triggers.md
├── portfolio/
│   ├── positions.md
│   ├── rules.md                       # 填 §3.8 内容
│   └── history.jsonl                  # 空
├── macro/                             # V1 空目录 + .gitkeep
├── journal/
│   └── decisions/                     # V1 空
├── data/                              # V1 空
├── tests/
│   ├── test_v0_io.py
│   ├── test_competence_io.py
│   ├── test_valuation_io.py
│   ├── test_watchlist_io.py
│   ├── test_portfolio_io.py
│   ├── test_search.py
│   ├── test_company_create.py
│   └── test_routes_smoke.py           # FastAPI TestClient 冒烟
└── tests/fixtures/                    # pytest 用的 V0/能力圈等最小样例
    └── companies/
        ├── US_TEST/v0.md
        └── US_TEST/competence-check.md
```

说明：fixture 放在 `tests/fixtures/` 下而不是顶层 `fixtures/`，避免被 `/companies` 页面扫到。顶层仓库保持"干净数据区"。

---

## 3. 任务分解（按 §5 附录 B 日历）

### Week 1

#### Day 1：骨架与词表

**T1.1 建目录骨架 + README + requirements + pytest 配置**
- 按 §2 新建所有空目录（含 `.gitkeep`）。
- `requirements.txt` 新建，内容：`fastapi`、`uvicorn[standard]`、`jinja2`、`python-multipart`、`PyYAML`、`markdown>=3.5`、`pytest`。
- `pytest.ini` 新建：`testpaths = tests` + `python_files = test_*.py` + `addopts = -v`。
- `README.md`：项目一句话介绍、`python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --reload` 启动说明、目录索引。
- `.gitignore` 追加：`data/*.db`、`companies/**/sources/*.pdf`（如需）。
- 验收：激活 `.venv`、`pip install -r requirements.txt` 成功，`tree -L 2` 与 §2 一致。

**T1.2 写通用能力圈 12 问词表**
- 文件：`controlled-vocab/competence-core.yaml`
- 内容：DESIGN §3.3 的 `universal_questions` 原文（12 题 id/label/prompt），结尾加评分标准说明。
- 验收：PyYAML 能加载，12 个 id 无重复。

**T1.3 写 2 个行业专属词表（你最熟的 2 个）**
- 默认填 `consumer.yaml` + `saas.yaml`（DESIGN §3.3 已给出字段）。
- 其余 3 个（cyclical/bank/biotech）只放 `# TODO V1.1 填充` 注释 + 文件头 metadata。
- 验收：PyYAML 能加载 5 个文件。

**T1.4 把 5 份业务文档模板落地到 `templates/*.md.tmpl`**
- `v0.md.tmpl`：复制 DESIGN §3.2 全文，YAML frontmatter 带 `{{ticker}}` 等 Jinja 占位。
- `competence-check.md.tmpl`：复制 §3.3。
- `valuation.md.tmpl`：复制 §3.4。
- `journal-decision.md.tmpl`：复制 §3.5。
- `meta.md.tmpl`、`profile-YYYY.md.tmpl`、`trade-log.md.tmpl`：最小骨架（标题 + 核心 frontmatter）。
- 验收：手工运行 `python -c "from jinja2 import Template; print(Template(open('templates/v0.md.tmpl').read()).render(ticker='XX', market='US'))"` 正常输出。

**T1.5 填 `portfolio/rules.md`**
- 原样拷贝 DESIGN §3.8 的组合级规则。

**T1.6 填 `watchlist/prefilter.md` / `researching.md` / `price-triggers.md` 表头**
- 按 §3.9 的三段含义，每个文件只有表头（日期、ticker、备注列）。

Day 1 提交点：目录 + 词表 + 模板 + 规则文档就位，无代码。

---

#### Day 2-3：FastAPI 骨架 + 公司列表/创建

**T2.1 FastAPI app 入口与配置**
- 文件：`main.py`（约 10 行，`app = FastAPI()` + 挂载 routers + static + templates）。
- 文件：`app/config.py`（`BASE_PATH = Path(__file__).resolve().parent`、`COMPANIES_DIR`、`TEMPLATES_DIR`、`CONTROLLED_VOCAB_DIR`）。
- 验收：`uvicorn main:app --reload` 能起，访问 `/` 返回占位首页。

**T2.2 V0 I/O**
- 新建 `app/io/v0.py`：
  - `_parse_frontmatter(text: str) -> dict`：解析首部 `---` 之间的 YAML，缺省返回空字典。
  - `read_v0(ticker, market) -> {frontmatter: dict, body: str}`
  - `write_v0(ticker, market, frontmatter, body)`：frontmatter 按固定 key 顺序输出（ticker, market, entry_date, position_size_pct, status, last_reviewed）。
  - `list_all_v0s(status_filter=None) -> list`：扫描 `companies/*/v0.md`，按状态过滤，返回 ticker/market/status/last_reviewed/entry_date/position_size_pct/v0_path。
- `tests/test_v0_io.py`：round-trip、状态过滤、frontmatter 顺序稳定、fixture `tests/fixtures/companies/US_TEST/v0.md` 能被正确读取。
- 验收：`pytest` 全绿。

**T2.3 「列出所有公司」endpoint + 页面**
- `app/routes/companies.py`：`GET /companies` 扫描 `companies/*/meta.md`，读 frontmatter，表格展示（ticker、market、名称、行业、V0 状态、能力圈分数、最后 review）。
- 模板：`app/templates/companies/list.html`。
- 验收：手工 `mkdir companies/US_HIMS && echo '---\nticker: HIMS\nmarket: US\nname: Hims & Hers\n---' > companies/US_HIMS/meta.md`，刷新页面可见。

**T2.4 「创建新公司」endpoint + 页面**
- `app/io/company.py`：`create_company(ticker, market, name) -> Path`
  - 建目录 `companies/{market}_{ticker}/`
  - 建子目录 `sources/`
  - 从 `templates/*.md.tmpl` 渲染：`meta.md`、`v0.md`、`competence-check.md`、`valuation.md`、`trade-log.md`、`profile-2026.md`
  - 建空 `claims.jsonl`
  - 若目录已存在则抛错（不覆盖）。
- `app/routes/companies.py`：`GET /companies/new` 表单、`POST /companies/new` 调用 `create_company` 后 302 到公司详情页。
- 模板：`companies/new.html`。
- 测试：`tests/test_company_create.py` 用 `tmp_path` 调 `create_company`，断言文件都在、frontmatter 正确插入 ticker。
- 验收：网页创建 `US_HIMS`，目录结构符合 §3.1。

**T2.5 公司详情页**
- `GET /companies/{market}_{ticker}`：展示 meta、V0/能力圈/估值的状态徽章（draft/active/missing）、到各编辑页的链接、`sources/` 文件列表。
- 模板：`companies/detail.html`。
- 验收：创建后的 HIMS 详情页能正确显示各状态。

**T2.6 base.html + 简陋样式 + 首页导航**
- `app/templates/base.html`：导航栏（公司 / 观察池 / 持仓 / 研究工作台 / 搜索）、`{% block content %}`。
- `app/templates/home.html`：欢迎 + 四个卡片（进入各主区域）。
- `static/style.css`：最简样式，system font，max-width 960，简单表格 + 表单样式。
- 验收：各页面继承 base.html 样式统一。

Day 2-3 提交点：能从 `/` 跳到公司列表，能创建公司并看到目录落地。

---

#### Day 4-5：V0 编辑页

**T3.1 V0 编辑表单**
- `GET /companies/{key}/v0`：解析 `v0.md`，7 段分别用独立 `<textarea>` 展示（frontmatter 每字段独立 input）。
- `POST /companies/{key}/v0`：表单提交 → 拼回 frontmatter + 7 段 markdown → `write_v0`。
- 模板：`v0/edit.html`。
- 单独输入控件：
  - frontmatter：ticker（只读）、market（只读）、entry_date、position_size_pct、status（下拉 draft/active/closed）、last_reviewed（自动填提交日期）。
  - body：按 7 段大标题拆成 7 个 textarea（1. 买入逻辑、2. 差异化观点、3. 估值锚、4. 买入区间、5. 卖出触发、6. 什么不算推翻、7. 当前状态）。
- 验收：填写后保存，磁盘 markdown 格式与模板一致，frontmatter key 顺序稳定。

**T3.2 V0 预览**
- `GET /companies/{key}/v0/preview`：用 `markdown` 包将保存的 markdown 渲染成 HTML 展示（依赖已在 T1.1 加入）。
- 模板：`v0/preview.html`。
- 验收：预览与源文件内容一致。

**T3.3 V0「差异化观点」反 B 抄袭提示**
- 编辑页在「2. 差异化观点」区域上方渲染红色提示块：「此段必须自己写。从研究工作台抄 claim 会被标记。」（文字来自 DESIGN §8 坑 2）。
- 验收：视觉明显。

**T3.4 V0 测试**
- `tests/test_v0_io.py`：增加 write→read round-trip、frontmatter 字段顺序、7 段切分测试。
- 验收：`pytest` 全绿。

Day 4-5 提交点：能完整编辑/保存/预览 HIMS 的 V0。

---

#### Day 6-7：观察池 + 持仓

**T4.1 观察池读写**
- `app/io/watchlist.py`：
  - `read_watchlist(stage) -> list[dict]`：stage ∈ {prefilter, researching, price-triggers}，解析三段 markdown 表格。
  - `append_watchlist(stage, entry)`、`move_watchlist(ticker, from_stage, to_stage)`。
- 决定 markdown 表格格式（统一 3 段都用一致列）：
  - prefilter：`| date_added | ticker | source | notes |`
  - researching：`| started | ticker | owner_of_gap | target_finish |`
  - price-triggers：`| set_on | ticker | first_entry_price | add1_price | add2_price | v0_link |`
- 测试：`tests/test_watchlist_io.py`，round-trip + 移动。

**T4.2 观察池页面**
- `GET /watchlist`：三段表并列展示。
- `POST /watchlist/{stage}/add`：表单添加。
- `POST /watchlist/move`：把条目从 A 段移到 B 段。
- 模板：`watchlist/index.html`。
- 验收：手工加 1 条 prefilter、移到 researching、再移到 price-triggers，磁盘文件正确。

**T4.3 持仓页**
- 文件格式：`portfolio/positions.md` 用表格 `| ticker | market | entry_date | avg_cost | shares | position_pct | v0_link |`。
- `app/io/portfolio.py`：`read_positions() -> list`、`upsert_position(dict)`。
- `upsert_position` 额外副作用（**来自 §7 已确认**）：当新增一笔 active 仓位且对应公司 V0 当前 `status: draft` 时，自动改为 `status: active` 并回填 `entry_date` 为本次买入日期、`position_size_pct` 为本次仓位。已经 active 的不重写。
- `GET /portfolio`：表格展示 + 总仓位 + 现金占比（现金 = 100% - Σposition_pct）、规则文件（`rules.md`）折叠展示。
- `POST /portfolio/position`：表单新增/更新。
- 模板：`portfolio/index.html`。
- 测试：`tests/test_portfolio_io.py` 覆盖：新建持仓 + draft V0 → V0 变 active / 已 active V0 不被覆盖。
- 验收：能加 1 条 HIMS 持仓，总仓位显示正确，V0 status 随之 active。

Day 6-7 提交点：观察池和持仓能完整手工操作。

---

### Week 2

#### T5 能力圈自检页

**T5.1 能力圈 I/O + 评分**
- `app/io/competence.py`：
  - `read_competence(ticker, market)`：返回 frontmatter（含 scores）+ body（markdown）。
  - `write_competence(...)`：同上。
  - `score_competence(answers: dict, sector: str)`：根据 yaml 词表计算 universal_score/sector_score/in_competence/gaps。评分规则：每题 0/0.5/1（未答/模糊/具体可证伪），通用 ≥ 8 且行业 ≥ 3 时 `in_competence=true`。
- 测试：`tests/test_competence_io.py`，覆盖空白、部分填写、满分三种情况。

**T5.2 能力圈自检页面**
- `GET /companies/{key}/competence`：
  - 从 `competence-core.yaml` 加载 12 题，每题 1 个 textarea + 1 个自评下拉（未答 / 模糊 / 具体可证伪）。
  - 基于 meta.md 的 `industry_primary` 加载对应 `controlled-vocab/competence-sector/{industry_primary}.yaml`，追加行业题。**`industry_primary` 的合法取值就是 sector yaml 文件名（`consumer` / `saas` / `cyclical` / `bank` / `biotech`）**（来自 §7 已确认）。若 meta.md 里值不在此集合内，页面显示错误提示"未知行业，请改 meta.md"。
  - 顶部显示当前 universal_score/sector_score/in_competence 徽章。
- `POST /companies/{key}/competence`：保存 + 重新计分 + 写回 frontmatter 的 `gaps`（所有"未答"或"模糊"的题 id 数组）。
- 模板：`competence/edit.html`、`competence/view.html`。
- 验收：填写 HIMS（`industry_primary: consumer`）的 12 + 消费品行业题，能显示分数与缺口清单。

**T5.3 能力圈门禁提示**
- 若 `in_competence=false`，在公司详情页对「V0 编辑」链接加红色提示「能力圈未通过，不建议继续」（但不硬禁）。
- 依据 DESIGN §1 第 3 条哲学（门禁 = 不买，不是"读更多研报"）。

---

#### T6 估值页

**T6.1 估值 I/O + 加权**
- `app/io/valuation.py`：
  - `read_valuation`/`write_valuation`（同模式）。
  - `compute_weighted(bull, base, bear, p_bull, p_base, p_bear) -> float`：`bull*p_bull + base*p_base + bear*p_bear`；要求 3 概率和为 1，否则抛错。
  - `discount_rate_default(long_term_yield: float, premium: float = 0.055) -> float`。
- 测试：`tests/test_valuation_io.py`。

**T6.2 估值页面**
- `GET /companies/{key}/valuation`：三情景 price + probability 输入、current_price、discount_rate、三段"触发/假设/依据"textarea、相对估值 textarea、倒推法 textarea、结论 textarea。
- `POST`：保存 + 计算 `weighted_expected` + `implied_return_to_base = (base - current) / current`。
- 模板：`valuation/edit.html`、`valuation/view.html`。
- 验收：HIMS 填入 §3.4 示例数据，加权价显示 $25.5。

**T6.3 估值五档信号显示**
- 在估值页顶部显示五档信号当前落在哪档（依据 §3.2 V0 模板中的"估值触发五档"规则），文字提示（如「当前价 $19 < 基准 × 0.7 = $17.5 → 有 30% 安全边际」）。

---

#### T7 研究工作台（V1 最简版）

**T7.1 sources 上传**
- `POST /companies/{key}/sources/upload`：接受 markdown 或 txt 文件，保存到 `sources/{date}-{slug}.md`。
- `GET /companies/{key}/sources`：列出文件 + 元数据（从 YAML frontmatter，可选）。

**T7.2 claims.jsonl 查看/编辑**
- `app/io/claims.py`：逐行读/写 jsonl（字段按 §3.6 Claim schema）。
- `GET /research/{key}`：表格列出 claims（subject_tag、polarity、claim_text、evidence_strength）+ 新增表单（V1 全手填，不接 LLM）。
- `POST /research/{key}/claim`：追加一行。
- 模板：`research/index.html`。
- 验收：能手工加 2-3 条 claim，jsonl 文件格式符合 schema。

**T7.3 共识地图视图（最简聚合）**
- 在研究工作台页底部：按 `subject_tag` 分组，每组展示 bull/bear/neutral 计数（无图表，纯数字 + 列表）。
- 验收：加几条不同极性的 claim，聚合显示正确。

---

#### T8 搜索

**T8.1 grep 封装**
- `app/io/search.py`：`search(pattern, scope='all') -> list[{path, line, snippet}]`，用 `subprocess.run(['grep', '-rn', ...])`。
- scope 参数：`all` / `companies` / `watchlist` / `journal`。
- 禁用 shell 拼接，关键字走 subprocess 参数数组。
- 测试：`tests/test_search.py`（用 tmp_path 建几个 md 文件，搜关键字）。

**T8.2 搜索页面**
- `GET /search?q=...&scope=...`：展示结果列表（文件链接 + 高亮行）。
- 模板：`search/results.html`。
- 验收：搜"白酒"能返回 researching.md 里的条目；搜"未完成"能返回 frontmatter 里 `in_competence: false` 的公司。

---

#### T9 样式打磨 + 快捷键

**T9.1 样式清理**
- `static/style.css` 增加：表格 zebra、徽章色（draft=灰、active=绿、closed=黑、missing=红）、顶部导航 sticky。
- 不上 Tailwind、不上组件库。

**T9.2 键盘快捷键（轻）**
- 在 base.html 里放一段 JS：
  - `g h` → 首页
  - `g c` → 公司列表
  - `g w` → 观察池
  - `g p` → 持仓
  - `/` → 聚焦搜索框
- 验收：键盘能快速跳转。

---

### Week 3

#### T10 全流程验证 + 修复

**T10.1 挑 1 只真实候选股跑一遍**
- 建议：HIMS 或任一你真在观察的公司。
- 流程：
  1. 在 `/companies/new` 创建。
  2. 填 `meta.md`（手动或扩展 new 页收集更多字段）。
  3. 把 ticker 加入 `/watchlist` prefilter 段，移到 researching。
  4. 在 `/companies/{key}/competence` 填 12 题 + 行业题。
  5. 在 `/research/{key}` 手工加 5-10 条 claim。
  6. 在 `/companies/{key}/valuation` 填三情景。
  7. 在 `/companies/{key}/v0` 填 7 段 V0（特别关注"差异化观点"和"什么不算推翻"）。
  8. `/portfolio` 加一笔模拟仓位，状态改 active。
  9. 把该 ticker 从 researching 移到 price-triggers（或移除）。
- 验收：全流程无阻塞。

**T10.2 模拟一次"想卖但对照 V0 后 hold 住"**
- 场景：手工把 HIMS 的 current_price 改低 15%，刷新估值页 → 应显示"在买入区间"而不是"推翻条件"。
- 记录感受，判断 V0 页的"什么不算推翻"清单是否足够显眼。

**T10.3 问题清单 → V1.1 与 V2 输入**
- 新建 `docs/V1-RETRO.md`：按"阻塞 / 烦人 / 改进"三类列这周暴露的问题。
- 验收标准：至少 5 条真实问题。

**T10.4 清理**
- `README.md` 补充 "V1 状态" 小节，记录完工日期与已知限制。
- 确认 `.gitignore` 覆盖 `data/`、`.env`、`*.db`、`__pycache__/` 等。
- 确认 `tests/fixtures/` 没混进 `companies/` 主路径。

---

## 4. 测试策略

### 4.1 单元测试（必做）
- 每个 `app/io/*.py` 至少覆盖：read 正常、read 缺失文件、write→read round-trip、frontmatter 顺序稳定。
- `tests/test_company_create.py`：建公司后所有模板文件落地。
- `tests/test_competence_io.py`：三种评分边界。
- `tests/test_valuation_io.py`：加权、概率和 ≠ 1 抛错。

### 4.2 路由冒烟（必做）
- `tests/test_routes_smoke.py` 用 `from fastapi.testclient import TestClient`，每个 GET 页面 200、每个 POST 能完成一次 round-trip。

### 4.3 手工验证（Week 3 T10）
- 全流程走一遍即最终验收。

### 4.4 不做
- 不做 E2E（Playwright 等）。
- 不做性能测试、负载测试。
- 不做覆盖率门槛。

---

## 5. 提交节奏

- Day 1 结束：1 个提交（目录 + 词表 + 模板）。
- Day 2-3 结束：2-3 个提交（骨架、V0 I/O、公司 CRUD）。
- Day 4-5 结束：1-2 个提交（V0 编辑 + 预览）。
- Day 6-7 结束：2 个提交（观察池、持仓）。
- Week 2 每个任务组（T5-T9）1 个提交。
- Week 3 T10 按小修复提交。

建议每个提交消息格式：`[V1-Dx] <what changed>`，例：`[V1-D2] 骨架 + 公司列表 endpoint`。

> 注：仓库已是 git repo，按 §7 第 1 条无需再 `git init`。

---

## 6. 完工判定（V1 正式收官）

复述 §5 的 V1 成功标准，落到可检查的事：

- [ ] `/companies` 可见至少 1 家真实候选公司。
- [ ] 该公司有：meta.md、competence-check.md（已计分）、valuation.md（有加权价）、v0.md（7 段全填）、至少 5 条 claims。
- [ ] `/watchlist` 三段都有至少 1 条记录。
- [ ] `/portfolio` 有至少 1 笔（模拟）持仓。
- [ ] `/search?q=白酒`（或其他真实关键字）能返回命中。
- [ ] 手工触发过"想卖但看 V0 hold 住"的对照流程。
- [ ] `docs/V1-RETRO.md` 里列出 5+ 条 V1.1/V2 输入。
- [ ] `pytest` 全绿。

---

## 7. 已确认的决定（6 条）

以下条目在 2026-04-23 规划会议上全部按"建议"确认，各任务已按此执行：

1. **git**：仓库已是 git repo（`.git` 已存在），无需 `git init`。每个任务按 §5 提交节奏产生 commit。
2. **markdown 渲染依赖**：允许 `markdown>=3.5`（见 T1.1 requirements.txt）。
3. **industry_primary 取值**：直接用 sector yaml 文件名（`consumer`/`saas`/`cyclical`/`bank`/`biotech`）。页面加载时硬校验（见 T5.2）。
4. **V0 `entry_date` 回填**：加持仓时若 V0 `status: draft`，自动改为 `status: active` + 回填 `entry_date` + `position_size_pct`（见 T4.3）。已 active 的不重写。
5. **`bin/` 目录**：已删除，V1 所有代码走 `app/` 包。
6. **fixtures 处理**：测试 fixture 放 `tests/fixtures/`（不是顶层 `fixtures/`），避免被 `/companies` 扫到（见 §2 结构）。

---

## 8. 超出 V1 范围的 parking lot

本计划**不解决**这些，记录以防跑题：

- LLM claim 抽取（V2.0-V2.1）
- 财报自动抓取、SQLite schema 落地、派生比率（V2）
- 价格触发日查（V2）
- 催化剂日历（V3）
- 市场钟摆层（V3）
- 业绩度量、月/季/年复盘工具（V3）
- 宏观层五处嵌入自动化（V3）
- 组合级硬规则的自动触发（V3）
- 能力优势图（V3）

---

## 9. 版本

- v1.0（2026-04-23）：初稿，基于 DESIGN.md §5 V1 + 附录 B。

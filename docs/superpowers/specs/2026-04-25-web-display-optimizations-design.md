# Web 显示优化：arena 知识入口 / claims 分页筛选排序 / profile 读视图

日期：2026-04-25

## 目标

修复三个 web 体验问题：

1. ingest 抽取出的 arena checklist 与 competence-notes 在 web 上没有入口
2. 研究工作台 claims 单表全量渲染，条目多了没法查
3. 公司详情 → profile 链接直接进 textarea 编辑页，没有渲染视图

## 不做

- 不新增 JS 依赖（htmx/Alpine 等）
- 不重构 claims.jsonl / competence-notes.md 存储结构
- 不引入 LLM 调用（用户在对话里做抽取）

## §1 路由/模块划分

### 新增

- `app/routes/arenas.py`
  - `GET /arenas` → `arenas/index.html`
  - `GET /arenas/{slug}` → `arenas/detail.html`
- `app/templates/arenas/index.html`, `app/templates/arenas/detail.html`
- `app/templates/companies/profile_view.html`
- `main.py` 注册 `arenas_router`

### 改动

- `app/io/arenas.py`
  - `parse_notes(slug, base=None) -> dict` — 解析 `competence-notes.md` 到 `{by_ticker, by_question}`
  - `company_summary(ticker, market, base=None) -> list[dict]` — 给公司页用的简洁摘要
- `app/routes/companies.py`
  - `detail_page()` 加载 arena 摘要传入模板
  - 新路由 `GET /companies/{key}/profile/{year}/view` 渲染 markdown
- `app/routes/research.py`
  - `index()` 接 `page/sort/order/subject_tag/polarity/source_id`
- `app/templates/companies/detail.html` 加 arena 摘要块，profile 链接改到 `/view`
- `app/templates/research/index.html` 加过滤栏 + 可点列头 + 分页条

没有新增 Python 依赖（`markdown>=3.5` 已在 `requirements.txt`）。

## §2 arenas 数据流

### `parse_notes(slug)` 返回结构

```python
{
  "by_ticker": {
    "BSE_920118": {
      "name": "太湖远大",
      "answers": {
        "q_raw_material_cost": {
          "level": "vague",
          "answer": "…",
          "quote": "…",
          "source_id": "研报-西南证券-2024-08-15-09fe9bc6",
          "checklist_version": 1,
          "date": "2026-04-25",
        },
        ...
      },
    },
  },
  "by_question": {
    "q_raw_material_cost": [
      {"ticker": "BSE_920118", "name": "太湖远大", "level": "vague", ...},
      ...
    ],
  },
}
```

解析规则（对应 `append_notes` 的输出格式）：

- ticker 块：`^## {market}_{ticker} · {name}$` 到下一个 `^## ` 或 EOF
- question 块：`^### {q_id} · level={level}$` 到下一个 `^### ` 或下一个 `^## ` 或块尾
- question 块内第一非空行是 `来源：{source_id} · checklist v{N} · {date}`
- 后续非 `>` 起始的行拼成 `answer`，`>` 起始的行去掉前缀拼成 `quote`

### `company_summary(ticker, market)`

```python
[
  {
    "slug": "cn-power-cable-polymer-material",
    "name": "...",
    "total": 15,
    "answered_specific": 5,
    "answered_vague": 8,
    "unanswered": 2,
  },
]
```

逻辑：`find_by_company` → 对每个 slug 读 checklist（总题数 + 题 id 集合）、`parse_notes` 查本 ticker 的 answers，按 level 分桶；checklist 有但 answers 没有的计为 unanswered。

## §3 模板

### `arenas/index.html`

表格列：`slug`、`name`、`participants` 数、`checklist` 题数、`last_updated`、进入链接。

### `arenas/detail.html`

三段：

- **§A 定义**：frontmatter kv 表 + markdown 渲染的 definition_body
- **§B Checklist + Q&A**：按 `checklist.items` 顺序，每题一块 — question、why_matters、tags、evidence sections；下面按 `definition.participants` 顺序列出每家公司的 level（badge）+ answer + quote + 来源；未作答的也列一行标「未作答」
- **§C Changelog**：折叠 `<details>`，展示 `checklist.changelog`

level badge 配色：`specific` 绿、`vague` 黄、`unanswered` 灰（复用 `base.html` 已有 badge 类或加三条 CSS）。

### `companies/detail.html` arena 块

位置：在「状态」和「操作」之间。

```
## 行业竞技场（arena）
  · [cn-power-cable-polymer-material]  15 题 · specific 5 / vague 8 / 未答 2
  · ...
```

空时显示「该公司尚未关联 arena。meta.md 的 arenas 字段为空。」

### `companies/profile_view.html`

- 页头 kv 表：year、profile_date、source、source_file（`<a>` 指到 `/static/.../sources/` 暂不支持也可以只显示路径；先显示）、reviewed badge
- `markdown.markdown(body, extensions=['tables', 'fenced_code'])` 渲染正文，套在 `.markdown-body` class 下（CSS 里加基础排版规则）
- 右上角「编辑」按钮 → `/companies/{key}/profile/{year}`

## §4 claims 工作台

### 路由签名

```python
@router.get("")
def index(
    request, key,
    page: int = 1,
    sort: str = "extracted_at",
    order: str = "desc",
    subject_tag: str = "",
    polarity: str = "",
    source_id: str = "",
):
    ...
```

`sort` 白名单 `{extracted_at, subject_tag, polarity, source_id}`，`order` 白名单 `{asc, desc}`，不在名单则回退默认值。

### 处理流程

1. `read_claims(ticker, market)` → 全量 list
2. 依三个 filter 过滤（`""` 代表不过滤）
3. 排序 key 为 None 时排最后
4. 分页 `per_page=50`，切 `[(page-1)*50 : page*50]`
5. `consensus_map` 基于**过滤后**的全集重算
6. `source_id` 下拉选项 = 从全量 claims 取 `source_id` 去重排序

### 模板

- 过滤栏：`<form method="get">`，三个 `<select>`（第一项空串 = 全部）+ 「应用」按钮 + 「重置」链接（回到 `/research/{key}`）
- 列头 `<th>`：`id`、`subject` (subject_tag)、`polarity`、`claim`、`evidence`、`source_id`（新增一列便于看来源）。可排序列用 `<a href="?sort=...&order=...&[filters]">` 包起来，已排序列加箭头 `↑ ↓`
- 分页条：`?page=N&[所有参数]`，`« 上一页 · N/M · 下一页 »`，边界隐藏对应箭头

## §5 profile 读视图

见 §1 / §3 说明。详情页 `/companies/{key}` 的 profile 链接从 `/profile/{year}` 改到 `/profile/{year}/view`。

## §6 测试

- `tests/test_arenas_io.py`
  - `parse_notes`：空文件、单 ticker 单问题、多 ticker + quote/multiline answer、unanswered 不出现（写入侧已过滤）
  - `company_summary`：空 arena list、checklist 全答、部分答、有未答
- `tests/test_claims_filter_sort.py` 新增
  - filter 单独生效 / 组合生效 / 全空等同不过滤
  - sort 白名单、order 白名单、None 值排最后
  - 分页边界（page=0、page 超出、最后一页不足 50）
- 轻量 smoke：`/arenas`、`/arenas/{slug}`、`/companies/{key}/profile/{year}/view` 200

## §7 CSS

在 `static/style.css` 加：

- `.badge-level-specific` / `.badge-level-vague` / `.badge-level-unanswered`
- `.markdown-body h1/h2/h3/p/ul/table` 基础排版
- `.pagination` 居中、分隔符
- `.sort-indicator` 上下箭头字符

## 风险

- `parse_notes` 正则若与 `append_notes` 的写入格式不匹配，页面会缺数据。应对：专门给 parse_notes 写 round-trip 测试（`append_notes` → `parse_notes` 能还原），作为向 arena 写入路径的兜底。
- claims 数据量到几千条时 Python 端全量过滤可能慢，但目前总和不到 200 条，无需提前优化。

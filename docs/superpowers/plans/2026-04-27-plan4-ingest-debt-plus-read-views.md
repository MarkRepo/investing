---
title: "Plan 4 · Ingest tech debt 清理 + 三层读视图"
date: 2026-04-27
status: in-progress
depends_on:
  - docs/superpowers/plans/2026-04-26-plan3-ingest-workflow-digest.md
---

# Plan 4：Ingest tech debt 清理 + 三层读视图

Plan 3 收尾时列出 5 项 tech debt。本 plan 全部吃下，按"改动性质"分 4 个阶段，共 10 个任务。

## 背景

Plan 3 已把 ingest 架构切换到 digest-subagent 派发 + 三层知识系统（industry / arena / company）。现状：
- ingest 能写进数据目录，但**读不出来**——`/industries/*` 全是 501 占位，公司 narrative 和行业 observations 没视图
- Plan 3 digest prompt 里已经让 subagent 吐 `time_type`，但 `facts_to_claims` 丢了这个字段
- 行研 workflow 只能 read-only QA preview，warnings 不落盘
- `profile-*.md` 通路在 Plan 3 里已废弃，但代码/模板/测试还在
- `industry_io` 和 `arenas_io / company_io` 的 `base=` 约定不对称，测试和 caller 容易写错

## 范围与非范围

**In scope：**
- T1 claim schema 加 `time_type` 字段并贯通 `facts_to_claims`
- T2 `industry_io._industries_dir` 约定对齐到项目根
- T3 `app/io/qa.py` 引入 scope 概念（兼容 `MARKET_TICKER` 和 `industry:{slug}`）
- T4 `scripts/ingest_qa.py` CLI + `industry-research.md` workflow 开 `--write`
- T5 profile IO + routes 硬下线
- T6 profile 模板 + 测试清理
- T7 `/industries` 读视图（index + detail）
- T8 `/arenas/{slug}` 扩展（加 narrative + 反链）
- T9 公司 narratives 读视图
- T10 导航栏 + 全量测试回归

**Out of scope：**
- 不做 profile → narratives 数据迁移（存量为 0，迁移无必要）
- 不改 digest prompt 本身（Plan 3 已定型；本 plan 仅适配其输出）
- 不加"跨层搜索"或"最近 ingest 活动"首页（视觉设计工作；留待 Plan 5）
- 不引入新的 ingest source type（A-股公告/港股年报等）

## 影响面一览

| 层 | 改动文件 | 风险 |
|---|---|---|
| IO | `app/io/claims.py` / `app/io/industry.py` / `app/io/qa.py` / `app/io/company.py` | 中：签名变更传导到 caller |
| Script | `scripts/ingest_aggregate.py` / `scripts/ingest_qa.py` | 低：纯内部调用 |
| Routes | `app/routes/industries.py` / `app/routes/arenas.py` / `app/routes/companies.py` / `app/routes/qa.py` | 中：破坏性路由变更（profile 端点消失） |
| Templates | `companies/detail.html` / `companies/profile_*.html` / `industries/*.html` / `arenas/detail.html` / `_base.html` / `prompts/index.html` | 中：删除 + 新建 |
| Workflows (md) | `.claude/skills/ingest/workflows/industry-research.md` / `sell-side-note.md` | 低：文档 |
| 测试 | `tests/test_company_meta_profile.py` 删；`test_routes_smoke.py` 改；可能新增 `test_industries_routes.py` / `test_arenas_detail_v2.py` / `test_qa_industry_scope.py` | 中 |

---

## 阶段 1：数据补完（独立于 UI，先做）

### T1 · `time_type` 贯通 claim schema

**问题**
`scripts/ingest_aggregate.py:579 facts_to_claims()` 把 digest 里的公司层 fact 转成 claim 时没带 `time_type`。卖方研报 workflow 目前只能在 `claim_text` 前头拼 `[forecast]` 绕开。

**改动**
1. `app/io/claims.py`：
   - 把 `time_type` 加进"可选字段"白名单（`time_type ∈ {"actual", "forecast"}`，默认 `actual`）
   - `validate_batch` 加一个该字段的合法值校验
   - `append_batch` 把字段透传落盘
2. `scripts/ingest_aggregate.py:589 facts_to_claims` 在 dict 里加：
   ```python
   "time_type": f.get("time_type", "actual"),
   ```
3. `.claude/skills/ingest/workflows/sell-side-note.md`：
   - Step 7 digest context 里已经让 subagent 返回 `time_type`（不改）
   - Step 10 文案里**删掉** `[forecast]` 前缀 workaround 段落，改说 "`facts_to_claims` 已贯通 `time_type`，claim 落盘自带"
4. 测试：`tests/test_ingest_aggregate_triple.py` 里加一条带 `time_type: "forecast"` 的公司层 fact，断言落盘的 claim 有 `time_type: "forecast"`

**DoD**
- `facts_to_claims` 输出带 `time_type`
- `append_batch` 落盘的 jsonl 行里有该字段
- 回归测试全绿

### T2 · `industry_io` base= 对齐

**问题**
`app/io/industry.py:29 _industries_dir(base) = base or cfg.INDUSTRIES_DIR` —— `base` 直接是 industries 目录本身。
`app/io/arenas.py:34 _arenas_dir(base) = Path(base) / "arenas" if base else cfg.ARENAS_DIR` —— `base` 是项目根。
`app/io/company.py:207` 同 arenas 模式。
三选二占多数，把 industry 拉过来。

**改动**
1. `app/io/industry.py:29`：
   ```python
   def _industries_dir(base: Path | None) -> Path:
       return Path(base) / "industries" if base else cfg.INDUSTRIES_DIR
   ```
2. 审所有 `industry_io.*(base=...)` caller：
   - `scripts/ingest_aggregate.py`：grep `industry_io\.` 全部抓一遍
   - `app/routes/industries.py`：有也改（Phase 4 会再重写路由，但改签名要同步）
   - 测试 fixture：`tests/test_industry_io.py` / `tests/test_ingest_aggregate_triple.py` / `test_ingest_aggregate_autobuild.py` 里传 `base=tmp_path / "industries"` 的地方全改成 `base=tmp_path`
3. `.claude/skills/ingest/workflows/industry-research.md`：Step 3/10 里的代码 snippet 统一成"`base=BASE_PATH`"（跟 arena/company 一致）

**DoD**
- `pytest tests/test_industry_io.py tests/test_ingest_aggregate*.py` 全绿
- grep 整 repo 没有 `Path(base) / "industries"` 以外的残留用法

**风险**
改动是"破坏性无报错"——若漏改 caller，FileNotFoundError 会在运行时才出现。通过 grep + 全量 pytest 兜底。

---

## 阶段 2：QA scope 扩展

### T3 · `app/io/qa.py` scope 化

**问题**
`qa.py` 当前 API 全部是 `(ticker, market, ...)` 形态，落盘路径硬编码 `companies/{market}_{ticker}/qa_warnings.jsonl`。行研报告写不进去。

**改动思路**
引入 `scope: str` 抽象，格式：
- `"{market}_{ticker}"` → `companies/{market}_{ticker}/`
- `"industry:{slug}"` → `industries/{slug}/`

**新增 helper**
```python
def _resolve_scope_dir(scope: str, base: Path | None = None) -> Path:
    root = Path(base) if base else cfg.BASE_PATH
    if scope.startswith("industry:"):
        slug = scope.split(":", 1)[1]
        return root / "industries" / slug
    else:
        # MARKET_TICKER
        parts = scope.split("_", 1)
        if len(parts) != 2:
            raise ValueError(f"invalid scope {scope!r}")
        market, ticker = parts
        return root / "companies" / f"{market}_{ticker}"


def _warnings_path(scope: str, base: Path | None = None) -> Path:
    return _resolve_scope_dir(scope, base) / "qa_warnings.jsonl"


def _gap_path(scope: str, base: Path | None = None) -> Path:
    return _resolve_scope_dir(scope, base) / "qa_gaps.md"
```

**签名变更**
把现有 7 个函数的 `(ticker, market, ...)` 合并为 `(scope, ...)`：

| 旧签名 | 新签名 |
|---|---|
| `read_warnings(ticker, market, *, status=None, base=None)` | `read_warnings(scope, *, status=None, base=None)` |
| `append_warnings(ticker, market, warnings, *, base=None)` | `append_warnings(scope, warnings, *, base=None)` |
| `update_status(ticker, market, warning_id, status, *, note, base)` | `update_status(scope, warning_id, status, *, note, base)` |
| `write_gap_markdown(ticker, market, markdown, *, base)` | `write_gap_markdown(scope, markdown, *, base)` |
| `read_gap_markdown(ticker, market, *, base)` | `read_gap_markdown(scope, *, base)` |
| `list_all_companies_with_qa(base)` | `list_all_scopes_with_qa(base)`（返回 `list[str]`，同时枚举 companies/ 和 industries/） |
| `summarize_by_company(base)` | `summarize_by_scope(base)`（每行加 `scope_kind: "company" \| "industry"`） |

**caller 适配**
- `app/routes/qa.py`：所有 `qa_io.*(ticker, market, ...)` 改成 `qa_io.*(f"{market}_{ticker}", ...)`
- `scripts/ingest_qa.py`：`_parse_scope` 保留但返回就是 scope 字符串（不拆），各 cmd 直接透传

**make_warning**
`make_warning(scope=..., ...)` 签名不变（它本来就接受 scope 字段），只是现在 scope 可以是 `"industry:semiconductor"`。

**DoD**
- 所有公司侧功能不回归
- 新增 `tests/test_qa_industry_scope.py`：append + read + update_status 全走 `industry:xxx`
- `_stable_id` 对 `industry:xxx` 形式正常哈希（已天然支持）

### T4 · CLI + industry-research workflow 开写盘

**改动**
1. `scripts/ingest_qa.py`：
   - `_parse_scope` 改成：支持 `MARKET_TICKER` 和 `industry:{slug}` 两种，返回 `scope_str`
   - 所有 cmd_* 传 scope 字符串给 `qa_io.*`
   - `--scope` 的 help 加 "可填 MARKET_TICKER 或 industry:SLUG"
2. `.claude/skills/ingest/workflows/industry-research.md` Step 10.5：
   - 开启 `--write --scope industry:{slug}`
   - 删"Plan 4 添 industry scope 支持"的 TODO 注释
3. `app/routes/qa.py`：列表页适配 `scope` 字段（现在可能展示 `industry:xxx`）

**DoD**
- 手动跑 `python -m scripts.ingest_qa warn --write --scope industry:semiconductor --merged tmp.json` 能落盘到 `data/industries/semiconductor/qa_warnings.jsonl`（伪造 merged.json 跑一次）
- `routes/qa.py` index 页列表不崩

---

## 阶段 3：profile 硬下线

### T5 · profile IO + routes 删除

**删除对象**
`app/io/company.py`：
- `_PROFILE_RE`（line 26）
- `list_profiles` / `read_profile` / `write_profile`（line 211-304）
- 所有 profile-YYYY.md 模板创建（查 `company_create` 里的 `write_profile` 初始调用）
- `_company_dir` 保留（narratives 还在用）

`app/routes/companies.py`：
- `GET /companies/{key}/profile/{year}`（view）
- `GET /companies/{key}/profile/{year}/edit`
- `POST /companies/{key}/profile/{year}`

**方案**
直接删，不留"只读降级"。理由：
- 用户侧存量 0
- 留着 router 会让 detail.html 的"年度快照"面板有链接可点但点了 404 更混乱
- Plan 3 已停写；保留只读意味着代码 path 还在，但没数据源，鬼打墙

**DoD**
- `grep -rn "profile" app/ scripts/` 只剩 narratives 和 docstring
- 路由表 `python -c "from app.main import app; [print(r.path) for r in app.routes]"` 没 `/profile` 出现

### T6 · 模板 + 测试清理

**删除文件**
- `app/templates/companies/profile_edit.html`
- `app/templates/companies/profile_view.html`
- `tests/test_company_meta_profile.py`

**修改文件**
- `app/templates/companies/detail.html`：删"年度快照（profile-YYYY.md）" section（line 27 附近）
- `app/templates/prompts/index.html:41`：删 profile-extraction 列项
- `tests/test_routes_smoke.py`：删 profile GET/POST 断言；若 smoke 测试靠 profile 存在才能跑 company detail，要补 fixture 让 company detail 不依赖 profile
- `tests/test_company_create.py` / `tests/test_claims_arena_refs.py`：若 fixture 依赖 profile 模板渲染，改成 narratives 或直接删 fixture

**DoD**
- `pytest tests/` 全绿
- `grep -rn "profile" tests/` 仅留无关 match（变量名等）

---

## 阶段 4：三层读视图

### T7 · `/industries` 读视图

**解除 501 占位；实装 3 个端点。**

#### `GET /industries`
列所有 industry slug。数据：`industry_io.list_industries()` 已返回 `list[dict]`（含 name, scope, slug）。额外 enrich：
- `linked_arenas` 计数（读 `meta.yaml` 的 `linked_arenas` 字段）
- `linked_tickers` 计数（同上）
- `observations` 数量（`len(industry_io.read_observations(slug))`）

模板 `templates/industries/index.html`：表格。参照 `arenas/index.html` 风格。

#### `GET /industries/{slug}`
Detail 页。数据：
- `industry_io.read_meta(slug)` → name / scope / linked_arenas / linked_tickers / segments
- `industry_io.read_observations(slug)` → 返回最近 N 条（按 added_at 倒序）
- 11 dim narratives：遍历 `cfg.INDUSTRY_DIMENSIONS`，调 `industry_io.read_narrative(slug, dim)`；用 `markdown.markdown(..., extensions=["tables", "fenced_code"])` 渲染
- 反链：列出 linked_arenas 和 linked_tickers，带跳转

模板 `templates/industries/detail.html`：
- 顶部 meta card（name / scope / slug / edit button 暂无）
- 下面 tab 或锚点导航：Observations / Narratives（11 维）/ Arenas / Tickers
- 每个 narrative dim 单独一块，带 "(空)" fallback

#### `GET /industries/{slug}/{kind}` + POST
先保留 501——不进 Plan 4。真要编辑等 Plan 5 再做。或者直接删这两行端点，让 URL 404。**选：直接删**，因为 501 占位会让用户以为 "pending" 会有。

**DoD**
- `routes/industries.py` 不再有 501
- `templates/industries/{index,detail}.html` 都重写过
- `tests/test_industries_routes.py` 新增：fixture 创建一个 industry slug + 2 observations + 3 个 narrative 文件；断言 GET 200 且 body 包含关键字段

### T8 · `/arenas/{slug}` 扩展

**问题**
现有 detail 已渲染 definition + checklist + competence-notes answers，但**没渲染 Plan 3 digest 写进去的 narratives 和 observations**。另外缺 industry 反链（"本 arena 归属行业：`semiconductor`"）。

**改动**
- `app/routes/arenas.py detail()`：
  - 读 6 个 narrative 维度：`arenas_io.read_narrative(slug, dim)` for dim in `cfg.ARENA_DIMENSIONS`（若常量未定义，加到 `app/config.py`）
  - 读反链：`industry_io.find_by_arena(slug)` → 如果返回 slug，生成 `/industries/{slug}` 链接
  - （observations 是 industry 层概念，arena 层没有；不读）
- `templates/arenas/detail.html`：加 "Narratives" section；顶部 meta 加 "属于行业：{slug}" 链接

**DoD**
- 跑带 narrative 的 fixture 能看到渲染
- `tests/test_arenas_narrative.py` 已覆盖 io 层；补一个 `test_routes_smoke.py` 条目覆盖 route 层（如果没有）

### T9 · 公司 narratives 视图

**方案**
不新开独立端点，**嵌进现有 `GET /companies/{key}` detail**。理由：narratives 本来就是公司详情的一部分；独开 `/companies/{key}/narratives/{dim}` 会让导航变复杂。

**改动**
- `app/routes/companies.py detail()`：
  - 读 8 个 narrative 维度：`company_io.read_narrative(ticker, market, dim)` for dim in `cfg.COMPANY_DIMENSIONS`
  - 读 figure_contexts：若 `app/io/figure_contexts.py` 有按 company 读的 API，调它；没有则跳过（Plan 5 补）
- `templates/companies/detail.html`：
  - 加 "Narratives（8 维）" section，取代原"年度快照（profile）"位置
  - 跨层跳链：读 `meta.arenas` → 每个列成 `<a href="/arenas/{slug}">`；读 `meta.industry_primary` → 链到 `/industries/{slug}`（如果 meta 里有 industry_primary 字段；grep 确认）

**DoD**
- 一个完整跑过 ingest 的公司，detail 页能看到 narrative 文本和跨层链接
- `tests/test_routes_smoke.py` 或 `test_company_narrative.py` 有断言

### T10 · 导航 + 全量回归

**改动**
- `app/templates/_base.html` 或 `base.html`：导航栏加 "行业" → `/industries`（已有 "竞技场" → `/arenas`？如果没有，也加）
- 跑 `pytest tests/ -x` 全量
- 跑 `python -c "from app.main import app; [print(r.path, r.methods) for r in app.routes]"` 肉眼 sanity 检查路由表
- 若 `/industries` UI 启动页无数据（真实环境），加一条 "尚未 ingest 任何行业——跑 `/industry-research` 开始" 空态提示

**DoD**
- 全量 pytest 绿
- dev server 能点进 `/industries` `/arenas` 不报错
- 所有跨层链接能互跳

---

## 执行顺序与依赖

```
T1 ─────────────┐
T2 ───┐         ├─── T7 ─── T10
      ├── T7    │
T3 ── T4        ├── T8
T5 ── T6 ───────┤
                └── T9
```

- T1 / T2 / T3 / T5 是基础设施改动，互相独立，可并行
- T4 依赖 T3
- T6 依赖 T5
- T7 依赖 T2（industry_io base= 改完）
- T8 / T9 可跟 T7 并行
- T10 收尾

**实际执行策略：串行做 T1→T2→T3→T4→T5→T6→T7→T8→T9→T10。**每完成一个就 commit。避免并行时返工。

## 回滚策略

每个 T 一个 commit。若某个 T 跑完测试炸了：
- T1 / T3 / T5 类改动：直接 `git revert` 对应 commit
- T7 / T8 / T9 类 UI 改动：revert 模板和 route 的 commit；io 层改动保留

## 验收

完成后用户应能：
- 跑一份行研报告，QA warnings 落到 `industries/{slug}/qa_warnings.jsonl`，能在 `/qa` index 看到
- 跑完一份年报，能在 `/companies/{key}` 看到 8 维 narratives 和跨层跳链
- 在 `/industries/{slug}` 看到该行业的 observations 和 11 维 narratives
- `grep -rn "profile" app/` 只剩无关 match
- 测试套全绿

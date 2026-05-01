---
name: Investment Lens — Stage 2 read-only pages
description: HTML rendering plan — FastAPI routes, Jinja2 templates, cross-links from archive detail pages
type: plan
status: done
---

## 目标

在 Stage 1 数据层之上提供可浏览的 HTML 决策视图，三个 scope 各一页面，不包含任何编辑功能。

## 路由

| Route | Scope | Slug/Key |
|-------|-------|----------|
| `GET /lens/industry/{slug}` | industry | `cn-nuclear-fusion` |
| `GET /lens/arena/{slug}` | arena | `cn-fusion-lts-wires` |
| `GET /lens/company/{key}` | company | `SSE_603011` |

每个路由：读 meta → 创建 ClaimRegistry → 遍历 VIEW_DIMENSIONS[investment_lens][scope] → 对每 field 调 fetch_lens_material → 渲染模板。

404 处理：industry 走 FileNotFound，arena 走 `read_arena().exists`，company 兜底空 meta。

## 模板结构

```
investment_lens/
  _section.html   — 单个 field 的渲染组件（material → HTML）
  industry.html   — 8 fields 的页面骨架
  arena.html      — 7 fields 的页面骨架
  company.html    — 9 fields 的页面骨架
```

**_section.html** 渲染三段：
1. Bundle excerpts（原文片段列表，带 source_id / date / confidence badge）
2. Claims（active claim 卡片，带 claim_type / confidence / evidence_count）
3. Narrative excerpts（已有 narrative 文件引用，headline count 作为"已有写作"指示）

## 中文标签

FIELD_LABELS 字典覆盖全部 24 个 field，在模板中以中文展示维度名。

## 跨页面链接

在三个 archive detail 模板中添加"投资决策视图 →"按钮：
- `industries/detail.html`
- `arenas/detail.html`
- `companies/detail.html`

## main.py 注册

```
from app.routes.investment_lens import router as investment_lens_router
app.include_router(investment_lens_router)
```

## 已验证

16 个路由测试：200 状态、中文 label 存在、跨链接指向、404 路径。

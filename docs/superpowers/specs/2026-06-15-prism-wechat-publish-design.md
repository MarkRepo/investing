# prism 产出「公众号版」一键发布 — 设计

- **日期**：2026-06-15
- **范围**：为 prism 的「领域入门 primer」与「决策链 case」两族产出，新增一个**纯显示层**的微信公众号版本——去掉对独立文章无意义的引用与内部架子，生成自包含、内联样式的富文本，供一键复制到公众号编辑器粘贴成稿。
- **硬约束**：不改动任何现有产出内容与现有渲染路径。微信版是**额外的、独立的**派生产物，**纯显示优化，正文一字不改**；原始 `.md`、`read_output_html`、`render_markdown` 等现有链路零影响。
- **零 LLM**：全流程确定性（正则清洗 + 现有 markdown 渲染 + thesis 正则抽取 + bs4 内联样式），无任何模型调用，离线可重放、可单测。

---

## 1. 背景与动机

prism 的产出正文里大量引用形如 `mat-XXXXXX`（6 位 hex）的资料编号，在系统内由 `outputs.linkify_mat_refs` 链到诊断页对应来源行。这对内部审阅有意义，但对发到公众号的独立文章是纯噪声。除引用外，文中还夹带若干**内部架子**，独立阅读时是乱码或无意义指针。

经对三类样本（company / industry / arena）逐一核查，需处理的「显示层架子」清单与判定：

| 类别 | 样例 | 处置 | 理由 |
|---|---|---|---|
| `mat-XXXXXX` 引用 | `[mat-50b810]`、`（mat-4d2cb9）`、裸 `mat-xxxxxx`、斜杠连写 `mat-c27f59/4a…` | **去除** | 显示层引用标记，独立文章无意义（用户首要诉求） |
| 承重充分性 banner | `> 🧪 **承重充分性（05-critic…）**：…` | **去除** | 纯内部 QA 裁决产物，仅出现在 case 文件头 |
| 跨产出文件名引用 | `00_primer`、`c_investment_case`、`_prism_reading_guide.md` 等 | **去除** | 系统内导航/配套指针，独立看是文件名乱码 |
| 读者画像内部指针 | primer 顶部「…拿起本 topic 的投资 case（`c_investment_case`）…」那截 | **去除** | 指向内部文件的读者漏斗，独立文章不需要 |
| frontmatter | `slug/output_key/version/companion/sources_note` | **去除** | 后台记账（`render_markdown` 已剥；本流水线再剥一遍保险） |
| `K#`（命门编号） | `K1`–`K6`，正文常已内联自解释「K2（监管尾部）」 | **保留** + 文末追加对照表 | 是分析正文的一部分，机械删会损句义、改内容；改为文末追加图例 |
| `Q#` | `Q1 2026`、`25Q4`、`Q1'26`、`Q1 营收转正`… | **不动** | **经核实全部是日历季度**，非研究编号；Q# 研究框架已在 `workflows/00-research-topic.md` 废弃（"新 topic 不再生成 Q#"），`extract_research_questions` 已是死代码 |

**「内容不变」的边界定义**：实质分析散文 = 内容（永不触碰）；引用标记、QA banner、frontmatter、内部文件/导航指针 = 显示脚手架（可去）。`K#` 介于其间——故不删正文、只**追加**澄清图例，确保净增不改写。

---

## 2. 架构选型

**采用「独立模块 + 独立路由」**，而非在现有路由加 `?format=wechat` 分支。

- 现有 `read_output_html` / `output.html` / `render_markdown` **完全不改**；微信功能纯增量。
- 彻底隔离：微信清洗逻辑不可能回归污染现有产出；清洗逻辑可独立单测。
- 代价：多一个模块 + 一个路由 + 一个模板 + 对 `output.html` 的一处**纯增**条件链接。

被否方案（`?format=wechat` 分支）会把微信逻辑耦合进 canonical 渲染函数，一次坏改动即回归线上页，违反硬约束。

---

## 3. 模块 `prism/scripts/wechat_export.py`（纯函数）

主入口：

```python
def to_wechat_html(slug: str, variant: str, output_key: str) -> str:
    """生成某产出的微信公众号版自包含内联样式 HTML 片段。纯函数、零 LLM。"""
```

流水线（每步一个小纯函数，各自单测）：

1. **读原始 `.md`**——与 `read_output_html` 同一路径 `topics/{slug}/{variant}/outputs/{output_key}.md`。
2. **Markdown 层清洗**（在渲染前对文本操作）：
   - `strip_frontmatter(raw)` —— 复用 `outputs._strip_frontmatter` 同等逻辑（确保后续正则看不到 `sources_note`）。
   - `strip_mat_refs(text)` —— 去掉 `[mat-xxxxxx]` / `（mat-xxxxxx）` / `(mat-xxxxxx)` / 裸 `mat-xxxxxx` / 斜杠连写串 `mat-xxxxxx/yy…`；并收拾残留：去掉因删引用产生的双空格、悬空的空格+标点（如 ` 。`→`。`、` ，`→`，`、空 `[]`/`（）`）。**幂等**。
   - `strip_critic_banner(text)` —— 删掉以 `> 🧪 **承重充分性` 起头的引用块行（仅 case 文件命中；primer 无此行）。
   - `strip_internal_pointers(text)` —— 去除跨产出文件名引用与读者画像内部指针。**保守策略**：只匹配「明确属于内部导航」的形态（反引号包裹的产出 key、`_prism_reading_guide.md`、含"本 topic … case"的读者画像尾句），不对裸词做全局替换，绝不碰分析正文。
3. **渲染**——走现有 `outputs.render_markdown()`；**不调** `linkify_mat_refs`（引用已删、不出链接）。
4. **追加 K# 对照表** `append_k_legend(html, slug, variant)`：
   - 用 `outputs.extract_killer_questions(slug, variant, version)` 取正文出现的 K#（version 取该 variant 最新 thesis）。
   - 解析 `thesis_v{N}.md` 的 K# 表「维度」列得 `K# → 维度`（锚定 `| K1 | 维度 | …` 行，与 `extract_k_status` 同源解析）。
   - 仅当正文确有 K# 且能解析到维度时，在文末追加一个小标题「命门编号对照（K1–K6）」+ 双列表（编号 | 含义）。无 thesis / 无 K# / 解析空 → **静默跳过**，不报错。
5. **内联样式化** `inline_styles(html)`：
   - 用 bs4 遍历渲染后 HTML，按一张 WeChat-safe 样式映射给标签写 `style="…"`：`h1/h2/h3/p/table/thead/th/td/blockquote/code/pre/ul/ol/li/strong/em/hr/a`。
   - 删除所有 `class`/`id` 属性（公众号会丢弃，留着无益）。
   - 表格补 `border-collapse:collapse;width:100%` 等公众号能保留的内联属性。
   - 产物：自包含内联样式 HTML 片段（无 `<style>`、无外链 CSS、无 JS）。

样式映射以单独常量 `_WECHAT_STYLES: dict[str, str]` 维护，便于调色。

---

## 4. 路由 + 模板

### 4.1 路由（`app/routes/prism.py`）

```
GET /prism/{slug}/{variant}/{output_key}/wechat
```

- 校验 `output_key` 在白名单 `{"00_primer", "c_investment_case", "i_industry_case", "a_arena_case"}` 内，否则 404（不对 sidecar/中间产物开放）。
- 调 `wechat_export.to_wechat_html(slug, variant, output_key)`，产出注入 `prism/wechat.html`。
- 文件缺失 → 404；与现有 `prism_output` 同款错误处理。
- **路由顺序**：须放在现有 `@router.get("/{slug}/{variant}/{output_key}")`（prism.py:1161）**之前**，否则 `{output_key}` 通配会先吞掉 `…/{output_key}/wechat`。（FastAPI 按声明顺序匹配；`/wechat` 多一段路径其实不会被单段 `{output_key}` 吞，但显式前置更稳。）

### 4.2 模板 `app/templates/prism/wechat.html`

- 继承 `base.html`。极简单页：
  - 顶部工具栏：文章标题（取 `current_output.label` + topic 名）+「📋 复制到公众号」按钮 +「← 返回产出」链接。
  - 正文容器（如 `<div id="wx-article">`）直接 `{{ html_body | safe }}`（已内联样式）。
- 复制按钮 JS：
  - `navigator.clipboard.write([new ClipboardItem({ 'text/html': htmlBlob, 'text/plain': textBlob })])`，源取 `#wx-article` 的 `outerHTML`。
  - 成功/失败给一个轻提示（按钮文案瞬变「✓ 已复制」）。
  - 降级：`navigator.clipboard` 不可用时提示用户手动全选复制。
- 工具栏样式可用 `<style>`（这是预览页自身，不进剪贴板）；**正文区**靠内联样式保证粘贴后保真。

### 4.3 现有 `output.html` 的唯一改动（纯增）

在 `output-meta` 那行，仅当 `output_key in 白名单` 时，加一个「公众号版」小链接（复用现有 `.compare-btn` 同款样式）指向 `…/{output_key}/wechat`。不动任何渲染逻辑。

---

## 5. 验证（industry / arena / company 各一）

落地后用三个真实 topic 跑通预览页 + 复制，肉眼核对「正文一字未改、只是干净了」：

- **company**：`global-futu/opus4.8` → `00_primer` + `c_investment_case`
- **industry**：`cn-commercial-aerospace/opus4.8` → `00_primer` + `i_industry_case`
- **arena**：`cn-premium-baijiu/opus4.8` → `00_primer` + `a_arena_case`

核对要点：① 全文无 `mat-` 残留；② 无承重充分性 banner；③ 无 `00_primer`/`c_investment_case` 等文件名乱码；④ Q#（季度）原样在；⑤ K# 原样在 + 文末有对照表；⑥ 表格/加粗/列表在公众号粘贴后排版保真。

---

## 6. 测试 `prism/scripts/test_wechat_export.py`（pytest，纯函数）

- `strip_mat_refs`：四种写法 + 斜杠连写全清除；残留标点/空格收拾正确；幂等（清两遍 == 清一遍）；不误删正文里非引用的 `mat`/hex 文本。
- `strip_critic_banner`：删承重充分性行；正文其他 blockquote 不误删。
- `strip_internal_pointers`：删跨产出指针与读者画像尾句；分析正文里出现的同名普通词不误伤。
- `append_k_legend`：有 thesis 正确抽维度成表；无 thesis / 无 K# / 解析空 → 返回原 HTML（静默跳过）。
- `inline_styles`：关键标签带 `style`；`class`/`id` 被清；无 `<style>`/`<script>` 泄漏。
- **回归保护**：断言本模块不 import 改动 `read_output_html`/`render_markdown` 的行为；对同一输入 `to_wechat_html` 输出稳定（可重放）。

---

## 7. 不做（YAGNI）

- 不做微信 draft/material API 直推（需认证服务号 + appid/secret + IP 白名单 + 图片上传，门槛重；用户选了复制粘贴路径）。
- 不做图片/媒体上传（现有 primer/case 无图片）。
- 不改 Q#、不改 K# 正文、不重述任何分析文字。
- 不对 sidecar（07_decision_kit/peer_matrix 等 .yaml）、thesis、中间产物开放微信版。
- 不引入新第三方依赖（bs4 已在 requirements）。

---

## 8. 涉及文件

| 文件 | 改动 |
|---|---|
| `prism/scripts/wechat_export.py` | **新增**：纯函数模块（清洗 + 内联 + K# 图例） |
| `prism/scripts/test_wechat_export.py` | **新增**：单测 |
| `app/routes/prism.py` | 加 1 个路由 `…/{output_key}/wechat`（置于通配路由前） |
| `app/templates/prism/wechat.html` | **新增**：预览页 + 复制按钮 |
| `app/templates/prism/output.html` | 纯增 1 个条件「公众号版」链接 |

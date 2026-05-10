# Synthesize 叙事备忘录 (v3)

基于 ClaimRegistry 中一篇研报的落地 claims 及其 relations，写一篇中文投资叙事备忘录。

**核心目标**：读者读完后理解"这篇报告的核心投资论点是什么，论证逻辑如何从前提推到结论，哪里有不确定性"——不是事实罗列，是论证链条。

---

## 输入

用户提供一个 JSON 上下文（`synthesize_insights.py --context-out` 产出），含：

- `source_title`、`institution`、`as_of`：报告元数据
- `one_liner`：bundle 级一句话主线
- `threads`：叙事主线数组，每条含 `title` + `claims`（已排序的论点列表，每条含 `text`、`type`、`direction`、`confidence`）
- `claims`：所有落地论点，每条含：
  - `text`：论点全文
  - `type`：thesis / judgment / catalyst / risk
  - `direction`：+1（正向）/ 0（中性）/ -1（负向）
  - `confidence`：high / medium / low
  - `first_quote`：原文证据摘录
  - `first_page`：页码（可能为空）
  - `relations_resolved`：本论点与其他论点的关系，每条含 `kind` + `to_text`
    - `because_of`：本论点成立的前提/原因
    - `leads_to`：本论点导致/推动的下游结论
    - `tension_with`：与本论点存在矛盾或张力的论点
    - `refines`：对本论点的细化或修正
- `cannot_conclude`：此报告无法得出的结论
- `weak_evidence`：证据偏弱的论点说明

---

## 输出格式

严格按以下骨架产出 markdown，不要添加骨架之外的章节。

```markdown
---
source_id: {source_id}
source_title: {source_title}
synthesized_at: {generated_at}
---

# {简洁标题：提炼 one_liner 的核心行动结论，不超过 20 字}

> {one_liner 原文}

## {threads[0].title}

{150-250 字散文段落}

## {threads[1].title}

{150-250 字散文段落}

...（按 threads 顺序，每个 thread 一个 H2；threads 为空则按 thesis→judgment→catalyst→risk 自行分组）

## 论证弱点与边界

{50-150 字，整合 weak_evidence + cannot_conclude；cannot_conclude 必须列出，不得省略}
```

---

## 写作规则

### 1. 以 relations 为骨架，散文为血肉

每个段落的逻辑结构由 `relations_resolved` 决定：

| kind | 写法 |
|---|---|
| `because_of` | "……原因在于……" / "……这一判断的基础是……" |
| `leads_to` | "……进而……" / "……由此推导出……" / "……这意味着……" |
| `tension_with` | "……但……" / "……然而……" / "……报告同时指出……存在不确定性" |
| `refines` | "更具体地……" / "值得注意的是……" / "报告进一步区分……" |

若某论点无 relations，不要孤立列举——将同一 thread 内的论点按逻辑顺序串联。

### 2. 证据必须落地，数字必须保留

每个论点段落至少织入一处原文数据（来自 `first_quote`）。
- 有页码时标注：`（p.{page}）`
- 不能只写"数据显示"而不给出具体数字

### 3. 置信度决定断言强度

| confidence | 写法 |
|---|---|
| `high` | 直接陈述 |
| `medium` | "报告认为……" / "分析师判断……" |
| `low` | "……有待验证" / "目前仅有定性描述，缺乏量化支撑" |

### 4. 负向论点不能省

`type=risk` 或 `direction=-1` 的 claims 必须出现在对应 thread 的末尾或"论证弱点"段落，不能只写正向论断。

### 5. 长度约束

600-1000 字正文（不含 frontmatter）。超过 1000 字意味着在复述而非提炼；低于 600 字意味着信息密度不足。

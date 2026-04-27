# workflow: quarterly-report

> **⚠️ 迁移中（2026-04）**：本文档里所有 `financial_rows` / `financial_line_rows` / `write_financials` / `check_financials_required` / `check_revenue_consistency` / `import_financials_csv` 相关步骤**已下线**。财务数字统一从 API（akshare / yfinance）入库，用户在 `/companies/{key}/financials` 页面点"刷新财务数据"。ingest 只产 claims + MD&A 叙述，不再产财务数字。以下步骤中涉及上述函数/字段的部分请**跳过**。`financial_profile` narrative 来源改为 `§管理层讨论与分析` / `§Item_7_MDA`。

处理季报 / 10-Q。主 agent（你）按步骤执行；subagent 只读返回数据，由你统一校验和写入。

**相比年报的核心差异**（记在心里）：

1. **不写 profile**：季报不触发事实层快照。`profile-{year}.md` 只由年报刷新。subagent 的 `profile_fragments` 字段会被你**显式丢弃**——如果 subagent 意外产出，在收尾报告里提一句，但不落盘。
2. **period 不是 fiscal_year**：`source_id` 和 `financial_rows.period` 用 `YYYYQN`（如 `2025Q3`），不是 `FY2025`。
3. **section 更薄**：季报只有三表 + MD&A 变化 + 少量 reminders；routing 表里只保留这几个 subagent。
4. **下一步建议单一**：只有 `/earnings-review/{key}`，没有"profile 审阅 / V0 重估"。
5. **meta 罕见变化**：季报几乎不更新公司简介。若 subagent 给出 `meta_updates`，默认不 apply（年报才是权威源）。

---

## 前置状态

- `SKILL.md` 已判定源类型为季报（US 10-Q / A 股季报）
- 已知：`file_path`、`market` (US/SSE/SZSE/HK)、`ticker`

**半年报不走本 workflow**：半年报结构接近年报（有 MD&A 全文、风险因素更新、治理披露），走 `annual-report.md`。10-Q/A 股季报才走这里。

---

## Step 1：输入校验

- 确认 `file_path` 存在且可读
- 推断 `market` = A 股 (SSE/SZSE) 或 US
- 预处理参数：
  - US 10-Q → `--type quarterly --market us`
  - A 股季报 → `--type quarterly --market a-share`

---

## Step 2：company 存在性检查 + 自动建 meta

```python
from app.io import company as company_io
meta = company_io.read_meta(ticker, market)
```

**季报的特殊情况**：季报触发"自动建 meta"比年报少见（因为第一次 ingest 一家新公司通常会先给年报）。但如果真发生了：

- 和 `annual-report.md` Step 2b 相同流程：推 name（从首页 HEADER 抽）、推 currency（按 market 默认）、AskUserQuestion 问 sector、`create_company(...)` 建骨架。
- 建完继续 Step 3，不中止。

---

## Step 3：预处理

```bash
.venv/bin/python -m scripts.preprocess_report "<file_path>" \
    --type quarterly \
    --market {a-share|us} \
    --out /tmp/ingest-<sha8>.sections.json
```

---

## Step 4：解析预处理输出 + 健康检查 + 推 period_code

**读预处理 JSON**，关键字段：
- `meta.sha8`
- `meta.fiscal_year`（如 `FY2025`）
- `meta.reporting_period`（US 是原始日期字符串如 `"September 30, 2025"`；A 股是 `"2025 年第三季度报告"`）
- `meta.detected_form` 和 `meta.cli_type` 要一致

**推 period_code**（`YYYYQN` 格式，贯穿 source_id 和 financial_rows.period）：

```python
import re
rp = meta["reporting_period"] or ""
fy = re.search(r"\d{4}", meta.get("fiscal_year") or "")
year = fy.group(0) if fy else None

if market == "us":
    # "September 30, 2025" → month 9 → Q3
    month_map = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
        "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
        "november": 11, "december": 12,
    }
    m = re.match(r"\s*(\w+)\s+\d{1,2},?\s+(\d{4})", rp.strip())
    if not m:
        # AskUserQuestion: 预处理没抽到报告日期，让用户给 period_code
        ...
    month = month_map[m.group(1).lower()]
    year = m.group(2)
    q = (month - 1) // 3 + 1
    period_code = f"{year}Q{q}"
else:  # a-share
    # "2025 年第三季度报告" → Q3
    qmap = {"一": 1, "二": 2, "三": 3, "四": 4}
    m = re.search(r"(\d{4})\s*年\s*第\s*([一二三四])\s*季度", rp)
    if not m:
        # AskUserQuestion
        ...
    period_code = f"{m.group(1)}Q{qmap[m.group(2)]}"
```

对 US 10-Q 注意：`period_code` 里的"季度"含义是**自然年季度**（calendar quarter）。绝大多数美股公司财年 = 自然年，简单换算即可。少数例外（如 NVDA 财年 1 月底结束、COST 财年 9 月结束）——先按报告日期月份换算成 calendar Q，后续分析时注意公司财年对应关系。若用户 ticker 属于这类特殊财年公司，在 flags 里标"公司财年非自然年，period_code 使用 calendar quarter"。

**UNKNOWN section 健康检查**：同年报流程。季报常见：A 股的"董事会决议公告"附录、PDF 页脚 OCR 错识。UNKNOWN 总字数 > 500 → AskUserQuestion。

---

## Step 4.5：Arena 复用（季报通常不 bootstrap）

季报绝大多数情况下公司已有 arena（首次建 arena 一般在年报 / 研报阶段发生）。

```python
from app.io import arenas as arenas_io
company_arenas = arenas_io.find_by_company(ticker, market)
```

- **非空** → 读 checklist 到 `item_pool`，继续 Step 5：
  ```python
  checklists_by_slug = {slug: arenas_io.read_checklist(slug) for slug in company_arenas}
  item_pool = {}
  for slug, cl in checklists_by_slug.items():
      for it in cl["items"]:
          item_pool.setdefault(it["id"], {**it, "arena_slug": slug})
  ```
- **空** → 降级走 `annual-report.md` Step 4.5b / 4.5c 的 bootstrap 全流程（罕见，但首次 ingest 一家公司而它没有 arena 时合理；季报 MD&A 对 arena 定义支撑较弱，**建议提醒用户**"季报 bootstrap arena 质量不如年报 / 研报，要不要先补 ingest 一份年报 / 研报再回来"）

同步 meta 的 arenas 字段（复用 annual 4.5d 的代码）。

---

## Step 5：source_id 生成 + 碰撞检测

读 `.claude/skills/ingest/source-id-rules.yaml`：

- US 10-Q → `10-Q-{period}-{sha8}` → 例 `10-Q-2025Q3-f2ab91c7`
- A 股季报 → `季报-{period}-{sha8}` → 例 `季报-2025Q3-f2ab91c7`

`{period}` 用 Step 4 算出的 `period_code`。

**碰撞检测**：

```python
existing = [c for c in claims_io.read_claims(ticker, market) if c.get("source_id") == source_id]
```

非空 → AskUserQuestion：overwrite（= discard，因为 append-only） / discard / new_version（`-v2` 后缀）。

---

## Step 6：原文落位到 `sources/`

```python
from app.io import claims as claims_io
with open(file_path, "rb") as f:
    content = f.read()
claims_io.save_source_markdown(ticker, market, Path(file_path).name, content)
```

---

## Step 7：Digest dispatch（单 subagent，整份季报）

### 7a：Context 组装

和 `annual-report.md` Step 7a 的代码 99% 相同，**差异**：

1. `period_code`（如 `2025Q3`）作为额外字段注入 prompt
2. `financial_line_rows` 重要性更高（季报主产物）
3. 不期待 digest 产出 `proposed_arenas`（季报素材不支持新开战场；若真产出，Step 8 丢弃 + 入 flags）
4. `checklist_items` 通常稀疏（季报多数 item 答 unanswered）

复用 annual Step 7a 代码，额外：

```python
# period_code 在 Step 4 已推出（如 "2025Q3"）
```

### 7b：拼 prompt

复用 annual Step 7b 的结构，但 digest prompt 换成 `prompts/digest/quarterly-digest.md`，并在最终 prompt 末尾多一段：

```
## 季报专属指令（覆盖 annual-digest）

- 所有 financial_rows[*].period 必须是 `{period_code}`（如 "2025Q3"），period_type="quarterly"
- 所有 key_facts 的 timeframe 主要是 `{period_code}`（少量 long-term / 跨期对比允许）
- A 股"本报告期"vs"本年累计"：只抽"本报告期"列
- 10-Q "three months ended" vs "nine months ended"：只抽 three months ended
- narratives.company 仅填 financial_profile + catalysts 两维；其它 6 维度不列 key
- meta_updates 通常留空（季报罕见更新公司简介）
- proposed_arenas 预期为空；若有，简要写原因到 flags
```

### 7c：Dispatch

```
tool: Agent
subagent_type: Explore
prompt: <上面拼好的>
```

**并发**：季报只有一个 digest subagent。**不分批、不分段**。若返回超时（>10min）→ AskUserQuestion。

**Oversize 检查** 不再派发前生效（digest 读整份报告，不按 section 分）。preprocess 的 `action: skip` 规则仍用于丢弃 10-Q Part II Item 1A 被整段复制的 10-K 风险因素场景——调整 `section-routing.yaml` 而非运行时决策。

---

## Step 8：主 agent 汇总（digest → 三桶，丢 meta_updates + proposed_arenas）

```python
from scripts import ingest_aggregate as agg
import json
from pathlib import Path

digest = agg.load_json_tolerant(subagent_raw_output)
buckets = agg.route_key_facts(digest["key_facts"])
company_facts_grouped = agg.group_company_facts(digest["key_facts"])

# 季报专属后处理：
# 1. 丢弃 proposed_arenas（季报素材不适合开新战场）
dropped_proposed = digest.pop("proposed_arenas", [])
if dropped_proposed:
    digest.setdefault("flags", []).append(
        f"季报 digest 产出了 {len(dropped_proposed)} 个 proposed_arena，已丢弃"
        f"（季报素材不适合新开战场）"
    )

# 2. 丢弃 meta_updates（季报原则不刷 meta）
dropped_meta = digest.pop("meta_updates", {})
if dropped_meta:
    digest.setdefault("flags", []).append(f"季报 digest 产出了 meta_updates，已丢弃")

# 3. company facts → claims（只处理本公司）
claims_all = []
for (t, m), facts in company_facts_grouped.items():
    if t != ticker or m != market:
        continue
    claims_all.extend(agg.facts_to_claims(facts))
claims_all = agg.dedup_claims(claims_all)

# 4. 凑兼容 merged（Step 10.5 QA 依赖）
merged = {
    "claims": claims_all,
    "financial_rows": digest.get("financial_rows", []),
    "meta_updates": {},
    "competence_findings": digest.get("competence_findings", {
        "answered": [], "proposed_additions": []
    }),
    "flags_by_subagent": {"quarterly-digest": digest.get("flags", [])},
    "empty_subagents": [],
}
Path(f"/tmp/ingest-{sha8}.merged.json").write_text(
    json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
)
Path(f"/tmp/ingest-{sha8}.digest.json").write_text(
    json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

---

## Step 9：交叉校验

```python
issues = {
    "revenue_consistency":    agg.check_revenue_consistency(merged, tol=0.02),
    "period_consistency":     agg.check_period_consistency(merged, expected=period_code),
    "empty_section":          agg.check_empty_sections(merged),
    "financials_required":    agg.check_financials_required(merged),
}
```

**period_consistency 的 expected 是 `period_code`（如 `2025Q3`）**，不是 `fiscal_year`——这是季报 vs 年报的关键差异。subagent 产出的 claims 里 timeframe 应主要是 `{period_code}`，少量可以是 `long-term` 或相邻季度对比。众数偏离 → pause。

**季报的 revenue_consistency**：当前 `check_revenue_consistency` 的正则只识别 `$N M|B` 格式（见 `scripts/ingest_aggregate.py`），对 A 股"亿元"不会误警。季报通常只有当季 revenue，量级小于年度——不要把季度 revenue 当成年度 revenue 做 ratio 检查。

`pause` 类 check 非空 → AskUserQuestion。

---

## Step 10：统一写入（前一步失败整体中止）

季报写入清单：原文 → financials → company narratives（仅 2 维）→ claims → competence。**不写** profile / meta / proposed_arena / industry observations / figure_contexts（都罕见）。

```python
from datetime import datetime, timezone
from app.io import arenas as arenas_io

extracted_by = "claude-opus-4-7"
extracted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

source_meta = {
    "source_id": source_id,
    "source_file": Path(file_path).name,
    "sha8": sha8,
    "institution": "company-primary",
    "date": period_code,
}
```

### 10.1 原文（Step 6 已做）

### 10.2 financials（季报主产物）

```python
n_fin = agg.write_financials(
    ticker, digest.get("financial_rows", []),
    source_file=Path(file_path).name,
)
```

`write_financials` 把 `{period_code}` 原样透传（已是 `2025Q3` 格式），`period_type=quarterly` 由 digest 按 prompt 要求填。

### 10.3 industry observations + figure_contexts（季报通常为空）

```python
# 仅 buckets["industry"] 非空（季报罕见）时才写
if buckets["industry"]:
    n_obs = agg.write_industry_observations(
        buckets["industry"], source_meta,
        extracted_by=extracted_by, extracted_at=extracted_at,
    )
# figure_contexts 按 annual Step 10.4 的 multi-slug 模式写；通常 n_fig = 0
```

### 10.4 narratives

```python
# 季报的 narratives.company 通常只有 financial_profile + catalysts 两维
comp_nar = digest["narratives"].get("company", {})
n_nar_comp = agg.write_company_narrative(comp_nar, source_meta)

# industry / arena narrative 通常为空
ind_nar = digest["narratives"].get("industry", {})
if ind_nar:
    # 按 annual 10.5 的 wrap 逻辑处理（单 slug → wrap；多 slug → 直接传）
    ...
arena_nar = digest["narratives"].get("arena", {})
if arena_nar:
    n_nar_arena = agg.write_arena_narrative(arena_nar, source_meta)
```

### 10.5 claims

```python
n, errors = agg.write_claims(
    ticker, market, claims_all,
    source_id=source_id,
    source_file=Path(file_path).name,
    extracted_by=extracted_by,
    extracted_at=extracted_at,
)
if errors:
    # 报给用户，建议回 Step 7 重派；不做部分写入
    ...
```

### 10.6 profile / meta（都不写）

- `profile-*.md` 不写（季报不触发事实层快照；新架构下已废弃）
- `meta.md` 不写（Step 8 已丢弃 `meta_updates`）

### 10.7 competence 写入

```python
findings = digest.get("competence_findings", {"answered": [], "proposed_additions": []})
consolidated = arenas_io.consolidate_answers(findings["answered"])
# AskUserQuestion 审阅 → 按 arena 分组写入
for slug in company_arenas:
    checklist = arenas_io.read_checklist(slug)
    answered_for_this_arena = [
        a for a in consolidated
        if item_pool.get(a["q_id"], {}).get("arena_slug") == slug
    ]
    arenas_io.append_notes(
        slug, ticker, market, name,
        answered_items=answered_for_this_arena,
        source_id=source_id,
        checklist_version=checklist["version"],
    )
    # approved_new_items 同 annual 10.11；season 罕见新增
```

季报通常新增 answer 比 annual 少、且 proposed_additions 很罕见（季报披露面窄）——用户多数情况下会 skip 或只接受少量更新。

**不再有 `proposed_arenas` 处理**——Step 8 已丢弃。

---

## Step 10.5：QA checkpoint（自动落盘告警 + 缺口清单）

Step 10 写完即跑。结果会出现在首页 `🔎 QA 未处理告警` widget 和 `/qa/{market}_{ticker}` 页面，带 fix_hint 和 resolve/dismiss 按钮。

```bash
.venv/bin/python -m scripts.ingest_qa warn \
    --merged /tmp/ingest-{sha8}.merged.json \
    --preprocess /tmp/ingest-{sha8}.sections.json \
    --arena {primary_arena_slug} \
    --write --scope {market}_{ticker}

.venv/bin/python -m scripts.ingest_qa gap \
    --company {market}_{ticker} \
    --write
```

- 6 条规则：`fidelity` / `self_contradict_specific` / `empty_evidence` / `polarity_mismatch` / `proposed_dup` / `checklist_company_contamination`
- 幂等：同 key（scope+source_id+rule+target）不重复写；`dismissed` 状态不自动重开
- 季报 ingest 常无 arena bootstrap 且 competence_findings 少，`proposed_dup` / `checklist_company_contamination` 多数情况为空——仍应跑，至少把 `fidelity` + `polarity_mismatch` 跑到
- 把两步的退出消息记下来（warn 的 `added=X skipped_dup=Y reopened=Z`；gap 的 `✓ 落盘 path`），在 Step 11 收尾报告里展示

---

## Step 11：收尾报告

```
已 ingest：companies/{market}_{ticker}/sources/{filename}
✓ claims.jsonl  +{N} 条 (source_id={source_id})
✓ financials.db +1 period ({period_code})
⊘ profile-{year}.md  季报不刷新（跳过）
⊘ meta.md         季报不更新（跳过）
{✓|⊘} arenas/{slug}/competence-notes.md  {M 条答案 / 用户跳过}
{✓|⊘} arenas/{slug}/checklist.yaml       {bump 到 vX / 无新增}
✓ companies/{key}/qa_warnings.jsonl     +{W} 告警 · open={W_open}（首页 QA widget 会提示）
✓ companies/{key}/qa_gaps.md            已刷新（/qa/{key} 可看）
Arena：{arena_names}

{若有} 丢弃的 subagent 产出：
  - profile_fragments: [§X, §Y]（季报通道不消费）
  - meta_updates: {...}（季报通道不消费）

下一步建议：
- 对照 V0 推翻条件 → /earnings-review/{key}
- 登记下期财报日 → /catalysts
- 查看 arena 认知库：`arenas/{slug}/competence-notes.md`
- 本次抽到的 flags：
  - {flag 1}
  - {flag 2}
```

---

## 失败模式

| 场景 | 处理 |
|---|---|
| 预处理 reporting_period 抽不到 | AskUserQuestion 让用户给 period_code（如 `2025Q3`） |
| period_code 和 fiscal_year 不对应（如财年非自然年的美股公司） | 接受，在 flags 里标注；calendar Q 和财报 Q 对应关系由用户自己在 earnings-review 里处理 |
| subagent 意外产出 profile_fragments | 丢弃，报告里提一句；不阻塞 |
| Part II Item 1 (legal) 和 Part I Item 1 (financials) 归并冲突 | 预处理 _dedupe_toc 已用文本长度规避（Part I 胜）；Part II 薄法律内容丢失——若用户需要，AskUserQuestion 让用户粘贴 Part II 原文重抽 |
| revenue_consistency 对季报误报 | 季报 revenue 数量级小，正则本就难误报；若触发 pause 一般是真不一致，AskUserQuestion 处理 |
| period_consistency 众数偏离 expected | 常见原因：subagent 忘了把 FY 改成 Q——AskUserQuestion 确认后用 pandas 批量改 timeframe 或重跑该 subagent |
| Step 4.5 company_arenas 为空 | 提醒用户"季报 bootstrap arena 质量不如年报/研报，建议先补 ingest 一份年报/研报"；用户坚持走 → 降级到 annual 4.5b/4.5c bootstrap 流程 |
| Step 7c 某 subagent item 数 > 30 | pause，让用户删 checklist 或裁 arena |

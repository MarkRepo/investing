# workflow: quarterly-report

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

## Step 7：Dispatch subagents（并发 ≤ 5）

读 `section-routing.yaml` 的 `us-10q` 或 `a-share-quarterly` key。

**季报 subagent 集合很小**：
- `financials-tables`：三表
- `mdna`：季度 MD&A 变化
- `risk-factors`（仅 US Part II Item 1A 存在时）：季报的"material changes"
- `related-party`（仅 A 股"其他提醒事项"存在时）

### Step 7a：派单前的 oversize 检查

对每个 `action: extract` 的 section，派单前比较 `section.char_count` 和 routing entry 的 `max_chars`（见 `section-routing.yaml` 文末"通用 dispatch 字段说明"）：

- `max_chars` 未设置 / char_count ≤ max_chars → 正常派单
- char_count > max_chars 且 `oversize_action == skip` → **不派 subagent**，在 Step 8 合并后的 `flags` 里加一条：`"[oversized] {section_name} skipped: {oversize_reason} (char_count={n} > max_chars={m})"`
- 其它 `oversize_action` 值目前未实现，按 extract 处理即可

**典型触发**：HIMS / TSLA 等在 10-Q Part II Item 1A 整段复制 10-K 风险因素。此时 10-K 的 risk claims 已存在，季报跳过无损。

### Step 7b：同名 section 合并派单（oversize 检查之后）

季报通常每个 canonical section 就一份（三表 / MD&A / 风险 / reminders），合并场景罕见。但若预处理因 fallback 或子节归类产生多个同名 section，按 `.claude/skills/ingest/dispatch-merge-rules.md` 的决策树处理：同名 ≥ 2 个且合并 ≤ 50000 → 合并派 1 个；超过则按一级章节号分组。

每个 subagent 的 prompt 拼接方式和年报相同：`_common.md` + `prompts/sections/{subagent}.md` + 公司 context + subjects_whitelist + section 文本 + targets。

**季报 MD&A 的特殊 prompt 追加**（在主 prompt 末尾加一段）：

```
本次是季度报告 (period_code={period_code}) 的 MD&A。你产出的 claims 必须：
- 每条 timeframe 都写作 `{period_code}`（如 "2025Q3"），**不**写 FY{year}
- 重点抽"季度内发生 + YoY/QoQ 变化"：例如 "Q3 收入 X 亿，YoY +25%"
- 管理层指引：若给了季度或年化指引数字，单独抽并标 `guidance_reliability`
- **不要**产出 `profile_fragments`（季报不刷新 profile）
```

**季报 financials-tables 的特殊 prompt 追加**：

```
本次是季度报告。你产出的 `financial_rows[*].period` 必须是 `{period_code}`，
`period_type` 必须是 `quarterly`。季报通常披露"当季 + 本年累计"两列——
**只抽当季列**，不抽累计列（cumulative 会和其它季度重复）。
```

**并发控制**：季报 subagent 通常 2-4 个，一把全部并发即可，不需分批。

### Step 7c：Arena checklist item 路由（若 Step 4.5 有 `item_pool`）

- 按 `typical_evidence_section` 粗分：MD&A subagent 拿 `mdna` 相关 item；risk-factors subagent 拿 `risk_factors` 相关 item
- `["any"]` → 在季报里没有纯综述类 section，优先投给 MD&A subagent
- item 密度决策树：≤20 正常 / 21-30 加"逐条对照"指令 / >30 pause
- prompt 拼接格式和 annual Step 7b 相同

季报 checklist 答题通常比年报稀——因为季报披露面窄（没 Business section），很多 item 会是 unanswered，这是预期行为。

---

## Step 8：主 agent 汇总

```python
from scripts import ingest_aggregate as agg

outputs = {name: agg.load_json_tolerant(raw) for name, raw in subagent_results.items()}
merged = agg.aggregate(outputs)
merged["claims"] = agg.dedup_claims(merged["claims"])
```

**季报特有的后处理**：
- **丢弃 `profile_fragments`**：
  ```python
  dropped_fragments = merged.pop("profile_fragments", {})
  if dropped_fragments:
      # 在最终报告里提一句："subagent 产出的 §X fragment 已丢弃（季报不刷 profile）"
      ...
  ```
- **丢弃 `meta_updates`**：
  ```python
  dropped_meta = merged.pop("meta_updates", {})
  if dropped_meta:
      # 报告里提一句；meta 变更建议用户用 /revise-meta 或走下一次年报
      ...
  ```

**必须**把 merged 落盘到 `/tmp/ingest-{sha8}.merged.json`（Step 10.5 的 QA 消费它）：

```python
import json
from pathlib import Path
Path(f"/tmp/ingest-{sha8}.merged.json").write_text(
    json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
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

按顺序：

1. **原文落 `sources/`**（Step 6 已做）

2. **写 financials**（当季行）：
   ```python
   n_fin = agg.write_financials(
       ticker, merged["financial_rows"],
       source_file=Path(file_path).name,
   )
   ```
   `write_financials` 内部把 `{period_code}` 原样透传（它已经是 `2025Q3` 格式），同时填 `period_type=quarterly`（subagent 按 prompt 要求应已填）。

3. **写 claims**：
   ```python
   from datetime import datetime, timezone
   n, errors = agg.write_claims(
       ticker, market, merged["claims"],
       source_id=source_id,
       source_file=Path(file_path).name,
       extracted_by="claude-opus-4-7",
       extracted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
   )
   if errors:
       # 报给用户，建议重跑单个 subagent；不做部分写入
       ...
   ```

4. **profile 不写**（季报不触发）；如果 Step 8 有被丢弃的 `profile_fragments`，在收尾报告里标明"丢弃 N 个 fragment"。

5. **meta 不写**（同上）；丢弃的建议记入收尾报告。

6. **competence 写入**（审阅后；流程同 annual Step 10 step 6）：

```python
from app.io import arenas as arenas_io

findings = merged.get("competence_findings", {"answered": [], "proposed_additions": []})
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
    # approved_new_items 同上
```

季报通常新增 answer 比 annual 少、且 proposed_additions 很罕见（季报披露面窄）——用户多数情况下会 skip 或只接受少量更新。

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

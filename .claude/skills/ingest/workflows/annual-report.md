# workflow: annual-report

处理年报 / 10-K / 20-F / 半年报。主 agent（你）按步骤执行；subagent 只读返回数据，由你统一校验和写入。

---

## 前置状态

- `SKILL.md` 已判定源类型为年报（或 10-K / 20-F / 半年报）
- 已知：`file_path`、`market` (US/SSE/SZSE/HK)、`ticker`

---

## Step 1：输入校验

- 确认 `file_path` 存在且可读
- 推断 `market` = A 股 (SSE/SZSE) 或 US；HK 当前按 US 通道试（未来再细分）
- 计算预处理用的 `type` 和 `market` 参数：
  - US 10-K / 20-F → `--type annual --market us`
  - A 股年报（2026 年时点）→ `--type annual --market a-share`
  - 半年报：当前版本暂按年报通道处理，下一版再加独立 template

---

## Step 2：company 存在性检查 + 自动建 meta

```python
from app.io import company as company_io
meta = company_io.read_meta(ticker, market)
```

### 2a. meta 存在 → 跳到 Step 3

### 2b. meta 不存在 → **主动建**（绝不中止引导）

1. **抽 name**：先从文件名粗抽（"2026-02-23_HIMS_10-K_2025-12-31.htm" → 推 "HIMS"），然后把 Step 3 预处理提前做（或仅提取前 2 页文本），从 HEADER/公司简介 section 找公司全名。
   - A 股：找"{XXX}股份有限公司"或"{XXX}有限公司"
   - US：找 "{XXX}, Inc." / "{XXX} Corporation"
   - 如果多个候选，AskUserQuestion 让用户选
2. **推 currency**：
   - US → `USD`
   - SSE/SZSE → `CNY`
   - HK → `HKD`
3. **问 sector**：必须走 AskUserQuestion。白名单只有 5 项：
   - `consumer` / `saas` / `cyclical` / `bank` / `biotech`
   - 问题措辞："这家公司应归为哪个 sector（用于 competence-check 分流）？"
   - 给用户的每个选项带简短描述，比如：
     - `consumer` - 消费品 / 零售 / 远程医疗类订阅消费
     - `saas` - 软件订阅 / 云服务 / 平台
     - `cyclical` - 周期品 / 大宗 / 制造
     - `bank` - 银行 / 金融
     - `biotech` - 生物科技 / 制药
4. **建**：
   ```python
   company_io.create_company(ticker, market, name, sector, currency)
   ```
   这会在 `companies/{market}_{ticker}/` 下铺所有模板（meta.md / v0.md / competence-check.md / valuation.md / trade-log.md / profile-{today.year}.md / sources/ / claims.jsonl 空文件）。
5. **告知用户**：build 完成后一句话说明"已建 `{market}_{ticker}`，继续录入财报"。

---

## Step 3：预处理

```bash
.venv/bin/python -m scripts.preprocess_report "<file_path>" \
    --type annual \
    --market {a-share|us} \
    --out /tmp/ingest-<sha8>.sections.json
```

- 若 Step 2b 已跑过前段提取，这一步可复用
- 读 stdout/out JSON，获得 `meta` + `sections`

---

## Step 4：解析预处理输出 + 健康检查

**关键字段**：
- `meta.sha8`（source_id 的一部分）
- `meta.fiscal_year`、`meta.reporting_period`
- `meta.detected_form` 和 `meta.cli_type` 要一致（不一致时告诉用户并 AskUserQuestion 是否继续）
- `sections[*]` 按 `action` 分流

**UNKNOWN section 健康检查**：
- 所有 `name.startswith("UNKNOWN_")` 的 section 总字数
- 如果 > 500 字 → AskUserQuestion 展示 UNKNOWN 的 heading_raw 和 char_count，让用户决定：继续 / 修正 `section-routing.yaml` 再重跑 / 中止

---

## Step 4.5：Arena 识别 + Checklist 引导

年报常见两种场景：**公司已绑定 arena**（跳到 4.5d 直接读 checklist） vs **首次 ingest 这家公司的年报**（走 bootstrap 全流程）。

### 4.5a：已有 arena 的复用

```python
from app.io import arenas as arenas_io
company_arenas = arenas_io.find_by_company(ticker, market)
```

- 非空 → 跳到 4.5d，读 checklist 到内存，继续 Step 5
- 空 → 走 4.5b 走 bootstrap

### 4.5b：候选 arena 推导（company_arenas 为空时）

1. 列已有 arenas：`existing = arenas_io.list_arenas()`
2. 取上下文片段：`Item_1_Business` / `第二节_公司简介` 前 2K 字 + `Item_7_MDA` / `第四节_管理层讨论与分析` 前 1K 字
3. 调 `Agent(Explore)`，prompt = `.claude/skills/ingest/prompts/arena/bootstrap-definition.md` + 片段 + 已有 arenas 列表
4. subagent 返回 `{"match": slug | null, "proposed": {...}}`

### 4.5c：用户审 + arena 落盘 + checklist 生成

和 `sell-side-note.md` Step 4.5b / 4.5c 完全一致（复用相同的 AskUserQuestion 三选项 + `write_definition` + `write_checklist` 流程，见那份 workflow）。

### 4.5d：读 checklist 到内存 + 同步 meta

```python
checklists_by_slug = {
    slug: arenas_io.read_checklist(slug) for slug in company_arenas
}
item_pool = {}
for slug, cl in checklists_by_slug.items():
    for it in cl["items"]:
        item_pool.setdefault(it["id"], {**it, "arena_slug": slug})

# 同步 company meta（若这次新加了 arena）
info = company_io.read_meta_with_body(ticker, market)
fm = dict(info["frontmatter"])
existing_arenas = set(fm.get("arenas") or [])
if set(company_arenas) - existing_arenas:
    fm["arenas"] = sorted(existing_arenas | set(company_arenas))
    company_io.write_meta(ticker, market, fm, info["body"])
```

---

## Step 5：source_id 生成 + 碰撞检测

读 `.claude/skills/ingest/source-id-rules.yaml`，按 `meta.detected_form` 选 format：

- US 10-K → `10-K-{fiscal_year}-{sha8}` → 例 `10-K-FY2025-943870e7`
- A 股年报 → `年报-{fiscal_year}-{sha8}` → 例 `年报-2025-474905de`

**碰撞检测**：
```python
existing = [c for c in claims_io.read_claims(ticker, market) if c.get("source_id") == source_id]
```

- `existing` 为空 → 继续
- `existing` 非空 → AskUserQuestion：
  - **overwrite**：跳过写入（claims 是 append-only，不能真"覆盖"，说明清楚：等于 discard 本次）
  - **discard**：放弃本次 ingest，不写任何东西
  - **new_version**：给 source_id 加 `-v2` / `-v3` 后缀（递增到无冲突），继续写入

---

## Step 6：原文落位到 `sources/`

```python
from app.io import claims as claims_io
with open(file_path, "rb") as f:
    content = f.read()
claims_io.save_source_markdown(ticker, market, Path(file_path).name, content)
```

- PDF/HTM 都按原字节保存（`save_source_markdown` 名字有点误导，其实接受任意字节）
- **幂等**：同名文件已存在时会覆盖，不建议手动更名防误覆盖

---

## Step 7：Digest dispatch（单 subagent，整份年报）

### 7a：准备 subagent context

和行研相比，年报的 digest 多了这些输入：
- `company_context`（ticker / market / name / industry_slugs / arenas）
- `subjects_whitelist`（claims subject_tag 白名单）
- `financial_line_rows`（preprocess 从三张表粗抽的候选行）
- `checklist_items`（若 Step 4.5 有 `item_pool`）

```python
import json
from pathlib import Path
from app.io import arenas as arenas_io, company as company_io, industry as industry_io, claims as claims_io
from app import config as cfg

preprocess = json.loads(Path(f"/tmp/ingest-{sha8}.sections.json").read_text())

# 7a.1 整份报告文本（所有 extract sections 按 order 串）
full_text_chunks = []
for s in preprocess["sections"]:
    if s.get("action") == "extract":
        full_text_chunks.append(f"### {s['heading_raw']}\n\n{s['text']}")
full_text = "\n\n".join(full_text_chunks)

# 7a.2 company_context
meta_info = company_io.read_meta_with_body(ticker, market)
fm = meta_info["frontmatter"]
company_context = {
    "ticker": ticker,
    "market": market,
    "name": fm.get("name"),
    "industry_slugs": fm.get("industry_slugs") or [],
    "arenas": fm.get("arenas") or [],
}

# 7a.3 industry_context（若公司绑定了 industry，取第一个作 primary）
industry_context = None
if company_context["industry_slugs"]:
    primary_slug = company_context["industry_slugs"][0]
    try:
        im = industry_io.read_meta(primary_slug)
        industry_context = {"slug": primary_slug, "name": im.get("name")}
    except FileNotFoundError:
        pass

# 7a.4 known_arenas（公司已参与的）
known_arenas = []
for slug in company_context["arenas"]:
    try:
        a = arenas_io.read_definition(slug)
        known_arenas.append({
            "slug": slug,
            "battleground_focus": a.get("battleground_focus", ""),
            "participants": [p.get("name") or p.get("ticker") for p in a.get("participants", [])],
            "industry": a.get("industry"),
        })
    except FileNotFoundError:
        pass

# 7a.5 dimension_ref + industry_fields_hint
dimension_ref = {
    "industry": list(cfg.INDUSTRY_DIMENSIONS),
    "arena":    list(cfg.ARENA_DIMENSIONS),
    "company":  list(cfg.COMPANY_DIMENSIONS),
}
industry_fields_hint = cfg.INDUSTRY_FIELDS

# 7a.6 subjects_whitelist
subjects_whitelist = [s["id"] for s in claims_io.load_subjects()]

# 7a.7 figure_contexts + detected_tickers（preprocess 产出）
figure_contexts = preprocess.get("figure_contexts", [])
detected_tickers = preprocess.get("detected_tickers", [])

# 7a.8 financial_line_rows（年报核心输入）
financial_line_rows = preprocess.get("financial_line_rows", [])

# 7a.9 checklist_items（若 Step 4.5 有 item_pool）
checklist_items_flat = [
    {"id": it["id"],
     "arena_slug": it["arena_slug"],
     "question": it["question"],
     "why_matters": it.get("why_matters", ""),
     "typical_evidence_section": it.get("typical_evidence_section", []),
     "tags": it.get("tags", [])}
    for it in item_pool.values()
]
```

### 7b：拼 prompt

```python
digest_common = Path(".claude/skills/ingest/prompts/digest/_common.md").read_text()
digest_annual = Path(".claude/skills/ingest/prompts/digest/annual-digest.md").read_text()

def _indent(text: str, prefix: str = "  ") -> str:
    return "\n".join(prefix + ln for ln in text.splitlines())

prompt = f"""
{digest_common}

---

{digest_annual}

---

## 本次输入

file_meta:
  source_id: {source_id}
  sha8: {sha8}
  fiscal_year: {meta['fiscal_year']}

company_context: {json.dumps(company_context, ensure_ascii=False)}

industry_context: {json.dumps(industry_context, ensure_ascii=False)}

known_arenas: {json.dumps(known_arenas, ensure_ascii=False, indent=2)}

dimension_ref: {json.dumps(dimension_ref, ensure_ascii=False)}

industry_fields_hint: {json.dumps(industry_fields_hint, ensure_ascii=False, indent=2)}

subjects_whitelist: {json.dumps(subjects_whitelist, ensure_ascii=False)}

figure_contexts: {json.dumps(figure_contexts, ensure_ascii=False, indent=2)}

detected_tickers: {json.dumps(detected_tickers, ensure_ascii=False, indent=2)}

financial_line_rows: {json.dumps(financial_line_rows, ensure_ascii=False, indent=2)}

checklist_items:
{json.dumps(checklist_items_flat, ensure_ascii=False, indent=2)}

full_text: |
{_indent(full_text, "  ")}

---

## 产出要求（除 _common.md 的 schema 外，年报专属）

1. **`financial_rows[]`** 必填（至少本期 + 上一期比较；用基础货币单位，A 股"万元"→元自行换算）
2. **`narratives.company.{market}_{ticker}`** 必覆盖 ≥3 维（business_model / moat / growth_engine / financial_profile 优先）
3. **`competence_findings.answered[]`**：对上面 checklist_items 里每条 item，尽量给出 `level=concrete|vague|unanswered` 的填答；附 evidence_quote
4. **`proposed_arenas`** 仅当年报明确谈及一个还不在 company_context.arenas 里的博弈焦点

现在请输出严格 JSON（顶层 keys 至少含：key_facts, narratives, proposed_arenas, financial_rows, meta_updates, competence_findings, flags）。
"""
```

### 7c：Dispatch

```
tool: Agent
subagent_type: Explore
prompt: <上面拼好的>
```

**并发**：年报只有一个 digest subagent。**不分批、不分段**。若返回超时（>10min）→ AskUserQuestion 问是继续等 / 重派 / 中止。

**Section-level merge 不再发生**：digest 直接读整份文本，无"同名 section 合并"问题。`dispatch-merge-rules.md`（在 `prompts/_v1_archived/` 下）在新架构里不再被引用。

---

## Step 8：主 agent 汇总

Subagent 的 JSON 里经常有 schema 漂移（polarity 用 `positive` 而非 `bull`、`evidence_text` 平铺而非 `evidence` 列表、偶尔还会把 JSON 包在 ```json``` 代码块里）。不要手写归一化逻辑——直接调 `scripts.ingest_aggregate`：

```python
from scripts import ingest_aggregate as agg

outputs = {
    name: agg.load_json_tolerant(raw_subagent_output)
    for name, raw_subagent_output in subagent_results.items()
}
merged = agg.aggregate(outputs)
merged["claims"] = agg.dedup_claims(merged["claims"])
```

`merged` 包含 `claims` / `profile_fragments` / `financial_rows` / `meta_updates` / `competence_findings` / `flags_by_subagent` / `empty_subagents`。合并规则：
- `claims`：concat + `normalize_claim`（polarity / evidence 容错归一化）
- `profile_fragments`：同 key 取更长者
- `financial_rows`：concat（冲突留给 cross-check）
- `meta_updates`：首次写入者胜（`setdefault`）
- `competence_findings`：`answered` 和 `proposed_additions` 分别 concat；Step 10 写入前再用 `arenas_io.consolidate_answers` 合并同 q_id
- `flags`：每个 subagent 独立保留，最终报告展示

**不要**现在给 claims 补 `ticker` / `source_id` / `source_file` / `extracted_by` / `extracted_at`——这些由 `write_claims` 的 header 负责传播（`claims_io.append_batch` 会自动填入）。

**必须**把 merged 落盘到 `/tmp/ingest-{sha8}.merged.json`（Step 10.5 的 QA 消费它）：

```python
import json
from pathlib import Path
Path(f"/tmp/ingest-{sha8}.merged.json").write_text(
    json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

---

## Step 9：交叉校验（按 `cross-checks.yaml`）

```python
issues = {
    "revenue_consistency":    agg.check_revenue_consistency(merged, tol=0.02),
    "period_consistency":     agg.check_period_consistency(merged, expected=meta["fiscal_year"]),
    "empty_section":          agg.check_empty_sections(merged),
    "financials_required":    agg.check_financials_required(merged),
}
```

含义和 `on_fail` 策略：

1. **revenue_consistency**（`pause`）——只校验明确含 `total revenue` / `营业收入` / `营业总收入` / `总收入` 的量化 claim，**自动排除** segment / united states revenue / wholesale 等子项（否则分部收入比总收入小会触发假阳性）。支持 `FY2025` / `2025A` 互查。
2. **period_consistency**（`pause`）——所有 claim 的 timeframe 众数应等于 `meta.fiscal_year`。
3. **empty_section**（`warn`）——`aggregate` 已经标出空 subagent，这里只是把它们喂进最终报告。
4. **financials_required**（`pause`）——每个 `financial_rows` 必须有 revenue + net_income。

**claim_dedup** 和 **segment_sum** 当前由 `dedup_claims`（简单前缀+tag+tf 去重）处理；fuzzy match 和 §2 表格解析留到下一版。

`pause` 类 check 返回非空 issues → 用 AskUserQuestion 让用户决定：接受差异 / 修正 / 中止。

---

## Step 10：统一写入（前一步失败整体中止）

按顺序（claims 最后写，因为要等 source 已落）：

1. **原文落 `sources/`**（Step 6 已做）

2. **写 financials**：
   ```python
   n_fin = agg.write_financials(
       ticker, merged["financial_rows"],
       source_file=Path(file_path).name,
   )
   ```
   `write_financials` 内部把 `FY2025` → `2025A`，处理 None 列，调 `fin_io.import_financials_csv`。

3. **输出 profile 草稿给用户审**：
   - 构造 profile markdown（frontmatter: ticker/market/year/source_file=filename/source="annual report"/profile_date=今天）
   - 把完整草稿打印到对话
   - AskUserQuestion：「已产出 profile-{year}.md 草稿，请审阅后确认：是否落盘（`reviewed: true`）？」
   - 同意 → `company_io.write_profile(ticker, market, fiscal_year_int, fm, body)`
   - 拒绝或修改 → 把修改意见吸收，重新出草稿再问；或直接跳过 profile 写入

4. **写 claims**：
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
       # 报给用户，建议回 Step 7 重抽有问题的 section；不做部分写入
       ...
   ```
   **不要**自己 `json.dumps({"header": ..., "claims": ...})` 然后调 `validate_batch`——`parse_batch_json` 期望 header 字段**平铺在顶层**，嵌套 `"header"` key 会被当成 unknown field 静默丢弃（历史上造成过整批 `source_id = None` 的审计断链）。`build_claims_batch` / `write_claims` 替你做对了这件事。

5. **meta 更新建议**：
   - `merged["meta_updates"]` 非空 → 打印给用户，AskUserQuestion 是否 apply
   - 同意 →
     ```python
     info = company_io.read_meta_with_body(ticker, market)   # returns {frontmatter, body, exists}
     fm = {**info["frontmatter"], **merged["meta_updates"]}
     company_io.write_meta(ticker, market, fm, info["body"])
     ```
     注意 `read_meta(...)` 只返回 frontmatter dict；需要同时拿到 body 必须用 `read_meta_with_body(...)`——别写 `fm, body = read_meta(...)`，会抛 `too many values to unpack`。
   - 默认拒绝：meta.md 保持 Step 2b 建的 placeholder

6. **competence 写入**（审阅后，和研报一致）：

```python
from app.io import arenas as arenas_io

findings = merged.get("competence_findings", {"answered": [], "proposed_additions": []})
consolidated = arenas_io.consolidate_answers(findings["answered"])
```

**AskUserQuestion** 审阅：approve 全部 / approve answered 拒绝 proposed / 逐条筛选 / 跳过写入。

**写入**（对每个 `slug in company_arenas`）：

```python
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
    approved_new_items = [...]   # 主 agent 按用户审阅结果归属
    if approved_new_items:
        arenas_io.write_checklist(
            slug, checklist["items"] + approved_new_items,
            changelog_entry={
                "source_id": source_id,
                "changes": f"added {len(approved_new_items)} item(s) from {source_id}",
            },
        )
```

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
- `--arena` 指向本次 ingest 的 arena slug；多 arena 时挑一个"主" arena 跑即可
- 把两步的退出消息记下来（warn 的 `added=X skipped_dup=Y reopened=Z`；gap 的 `✓ 落盘 path`），在 Step 11 收尾报告里展示

---

## Step 11：收尾报告

给用户一份清单：

```
已 ingest：companies/{market}_{ticker}/sources/{filename}
✓ claims.jsonl  +{N} 条 (source_id={source_id})
✓ financials.db +{M} period
{⏸|✓} profile-{year}.md {等待审|已落盘}
{⏸|✓} meta 更新 {等待审|已合并}
{✓|⊘} arenas/{slug}/competence-notes.md  {M 条答案 / 用户跳过}
{✓|⊘} arenas/{slug}/checklist.yaml       {bump 到 vX (新增 K 条) / 无新增}
✓ companies/{key}/qa_warnings.jsonl     +{W} 告警 · open={W_open}（首页 QA widget 会提示）
✓ companies/{key}/qa_gaps.md            已刷新（/qa/{key} 可看）
Arena：{arena_names}

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
| 预处理脚本报错（依赖缺/文件格式不支持） | 报错退出，提示装依赖或转文件 |
| UNKNOWN section 过大 | AskUserQuestion 选继续 / 修 routing / 中止 |
| source_id 碰撞 | AskUserQuestion 覆盖/丢弃/新 id |
| subagent 失败（≥1 个） | 整体暂停，把失败 section 列给用户，问要重跑单个还是中止 |
| 交叉校验 `on_fail: pause` 触发 | AskUserQuestion 接受/修正/中止 |
| `validate_batch` 拒绝某些 claim | 报给用户，建议回 Step 7 重抽；**不做**部分写入 |
| `import_financials_csv` 报错 | 中止，保留已落的原文和已写的 claims（已落步骤不回滚） |
| Step 4.5 bootstrap-arena 产出无效 / 四维缺 | AskUserQuestion 让用户手填或跳过 arena 环节（本次只写 claim/financials/profile，不写 competence） |
| Step 4.5 bootstrap-checklist 产出 >15 条或 tag 非白名单 | `write_checklist` 拒绝；主 agent 回审阅步让用户删到合规 |
| Step 7b 某 subagent item 数 > 30 | pause，AskUserQuestion 让用户删 checklist 或裁 arena |

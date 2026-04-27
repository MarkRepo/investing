# workflow: sell-side-note

> **⚠️ 迁移中（2026-04）**：本文档里所有 `financial_rows` / `financial_line_rows` / `write_financials` / `check_financials_required` / `check_revenue_consistency` 相关步骤**已下线**。研报的预测数字本来就走 claims 通道（time_type=forecast），不经 financials。"丢弃 financial_rows" 这层防御也废了——digest 不再产 financial_rows。以下步骤中涉及上述函数/字段的部分请**跳过**。

处理卖方研报。与财报流程的关键差异：

1. **只写 claims**。不写 profile（研报不是事实源）、不写 financials（研报里的预测数字是**未来期观点**，不是已披露历史数字）、不改 meta。
2. **polarity 以研报作者立场为准**。研报说"强烈看多"，claim 就是 `bull`，哪怕你个人不认同。
3. **目标价 / 评级无系统字段**，统一塞 `claim_text` 里，`subject_tag=consensus_direction`。
4. **当前版本只支持单公司研报**。行业研报 / 跨多家公司的研报直接拒绝（下一版再设计"先进 industries/ 还是直接建公司"）。
5. **period 覆盖多 FY**。研报预测通常跨 FY+1/FY+2/FY+3，不做 `period_consistency` 校验（expected 没有唯一值）。

---

## 前置状态

- `SKILL.md` 已判定源类型为研报
- 已知：`file_path`、目标公司 key（`market + ticker`）——若研报封面未写清楚，先 AskUserQuestion 确认

---

## Step 1：输入校验

- 确认 `file_path` 存在且可读
- 预处理参数固定：`--type sell-side --market {a-share|us}`（market 按目标公司决定；不是研报本身的属性）

---

## Step 2：company 存在性检查 + 自动建 meta

```python
from app.io import company as company_io
meta = company_io.read_meta(ticker, market)
```

- 存在 → Step 3
- 不存在 → **自动建 meta**（绝不劝退）。新股研报常常是公司第一份可 ingest 的文档——要求"先 ingest 年报"不切实际（新股根本还没发年报）。按 `annual-report.md` Step 2b 的子流程走：
  1. **抽 name**：从 HEADER / 研报封面抽。A 股研报封面通常写明 "公司简称（股票代码）行业分类"（如 "太湖远大（920118） 基础化工"），直接取中文公司名。
  2. **推 currency**：`US → USD` / `SSE/SZSE/BSE → CNY` / `HK → HKD`。
  3. **问 sector**：AskUserQuestion 走 `VALID_SECTORS = ("consumer","saas","cyclical","bank","biotech")`。研报封面的行业分类（"基础化工"/"电子"/"医药"）是 sector 选择的 hint。
  4. **建**：`company_io.create_company(ticker, market, name, sector, currency)`。
  5. 继续 Step 3，不中止。

**meta 推断弱？不怕**。研报建的 meta 是骨架（name + sector + currency），后续 ingest 年报时 `merged["meta_updates"]` 会补充 website/上市日期等；风险仅是中途一段时间 meta 不完整。比让用户在新股场景被劝退好得多。

---

## Step 3：预处理

```bash
.venv/bin/python -m scripts.preprocess_report "<file_path>" \
    --type sell-side \
    --market {a-share|us} \
    --out /tmp/ingest-<sha8>.sections.json
```

---

## Step 4：解析预处理输出 + 单公司判定 + 元数据补齐

**读预处理 JSON**，关键字段：
- `meta.sha8`
- `meta.institution`（研报专用；抽不到返回 null）
- `meta.publish_date`（研报专用；抽不到返回 null）
- `sections[*]`：按 `action` 分流

### 4a：单公司判定

研报常见三种：
- **单公司深度**（目标）：封面/HEADER 写明公司名 + ticker；investment_thesis 通篇围绕一家
- **行业 + 核心标的**：覆盖 3-10 家同行，其中 1 家用户关心 → **当前版本拒绝**，提示"多公司研报暂不支持，下一版提供行业研报通道"
- **策略宏观**：无特定公司 → **拒绝**

判定方法（主 agent 自己判，不做复杂启发式）：
1. 读 HEADER + investment_thesis 前 2K 字
2. 若里面明显提到 ≥2 家公司（2+ 个 ticker 或 2+ 个带"股份/有限公司"后缀的专名），且 thesis 部分在做同业比较 → 判"非单公司" → 终止并提示用户
3. 若只围绕 1 家（目标公司）展开 → 继续

不确定时 AskUserQuestion 让用户决定"按单公司继续 / 终止"。

### 4b：institution + publish_date 补齐

- `meta.institution` 为 null → AskUserQuestion 让用户给机构名（"中信证券"、"Morgan Stanley"）
- `meta.publish_date` 为 null → AskUserQuestion 给出版日期（ISO `YYYY-MM-DD`）

这两个字段决定 source_id，不能省。

**UNKNOWN section 处理**：研报 UNKNOWN 通常是"图表说明 / 表格页"，不走 extract。超过 3000 字 UNKNOWN → AskUserQuestion 是否继续（研报 UNKNOWN 多数不含可抽事实）。

---

## Step 4.5：Arena 识别 + Checklist 引导（研报是主要 bootstrap 触发源）

研报往往是 ingest 一家新公司的第一份文档——arena + checklist 的 bootstrap 绝大多数走这里。

### 4.5a：候选 arena 推导

1. **列已有 arenas**：
   ```python
   from app.io import arenas as arenas_io
   existing = arenas_io.list_arenas()   # [{slug, name, participants}]
   ```
2. **取上下文片段**：`investment_thesis` 前 2K 字 + `valuation` 段前 500 字 + `meta.institution` + 公司 context (`ticker / market / name / sector`)。
3. **调 Agent(Explore)**，prompt = `.claude/skills/ingest/prompts/arena/bootstrap-definition.md` + 片段 + 已有 arenas 列表（slug + name + 四维摘要）。
4. **subagent 返回** `{"match": slug | null, "proposed": {slug, name, dimensions, boundaries, participants, notes}}`。

### 4.5b：用户审 + arena 落盘

- **`match` 非 null** → 告知用户"已识别为 arena `{slug}`"，AskUserQuestion 确认复用。确认后：
  ```python
  company_arenas = [match_slug]
  arenas_io.participants_add(match_slug, ticker, market, name, role="challenger")
  ```
  跳到 4.5d（复用已有 checklist，**不跑 bootstrap-checklist**）。

- **`match` 为 null** → AskUserQuestion 给用户 3 选项：
  - "采用候选 arena（slug={proposed.slug}）"：展示四维摘要 + 参与者给用户看
  - "改用已有最接近的（下拉 existing）"
  - "自己改 slug / 改四维" → 用户提供后走下一步
- 用户确定后：
  ```python
  fm = {
      "slug": proposed_slug,
      "name": proposed_name,
      "created": today,
      "last_updated": today,
      "participants": [{"market": market, "ticker": ticker, "name": name, "role": "challenger"}],
  }
  body = f"""## 四维定义
  - **产品/服务**：{dimensions.product}
  - **客户/场景**：{dimensions.customer}
  - **地理范围**：{dimensions.geography}
  - **价位/档次**：{dimensions.tier}

  ## 边界条件（不在本 arena）
  {渲染 boundaries}
  """
  arenas_io.write_definition(proposed_slug, fm, body)
  company_arenas = [proposed_slug]
  ```

### 4.5c：Checklist 生成（仅新建 arena 时跑）

1. **调 Agent(Explore)**，prompt = `.claude/skills/ingest/prompts/arena/bootstrap-checklist.md` + 刚落盘的 `definition.md` 完整内容 + 公司 context。
2. **subagent 返回** `{"slug", "items": [...]}`，每条 item 带 `id / question / why_matters / typical_evidence_section / tags`。
3. **AskUserQuestion** 展示草稿清单，让用户批量编辑：
   - 删除不合适的 item
   - 改 question 措辞 / why_matters / tags
   - 手动追加（若用户希望加一条 LLM 没覆盖的）
4. 用户确认后落盘：
   ```python
   arenas_io.write_checklist(
       proposed_slug,
       items=approved_items,
       changelog_entry={"source_id": source_id, "changes": "initial bootstrap"},
   )
   ```

### 4.5d：读 checklist 到内存（供 Phase B 注入）

```python
checklists_by_slug = {
    slug: arenas_io.read_checklist(slug) for slug in company_arenas
}
# 合并成 item 池，按 id 去重：
item_pool = {}
for slug, cl in checklists_by_slug.items():
    for it in cl["items"]:
        item_pool.setdefault(it["id"], {**it, "arena_slug": slug})
```

### 4.5e：更新 company meta 的 arenas 字段

如果 `company_arenas` 不是 meta 里已有的 arenas 子集 → 追加：
```python
info = company_io.read_meta_with_body(ticker, market)
fm = dict(info["frontmatter"])
fm["arenas"] = sorted(set(fm.get("arenas") or []) | set(company_arenas))
company_io.write_meta(ticker, market, fm, info["body"])
```

---

## Step 5：source_id 生成 + 碰撞检测

读 `source-id-rules.yaml`，研报 format：`研报-{institution}-{date}-{sha8}`
- date 规格化为 `YYYY-MM-DD`（即便原文是"2025 年 10 月 28 日"）
- institution 取原样（"中信证券" / "Morgan Stanley"）

例：`研报-中信证券-2025-10-28-a3f91b2c`

**碰撞检测**：同年报流程。注意研报容易出现"同机构同日发两份"（上午一份业绩点评 + 下午一份路演纪要）—— sha8 不同就不算碰撞。

---

## Step 6：原文落位到 `sources/`

```python
from app.io import claims as claims_io
with open(file_path, "rb") as f:
    content = f.read()
claims_io.save_source_markdown(ticker, market, Path(file_path).name, content)
```

---

## Step 7：Digest dispatch（单 subagent，整份研报）

### 7a：Context 组装

和 annual Step 7a 代码 99% 相同，**差异**：
- 注入 `institution` + `publish_date`（研报专属）
- digest prompt 换成 `prompts/digest/sell-side-digest.md`
- 不注入 `financial_line_rows`（研报预测走 claims，不经 financials 通道）

```python
# 复用 annual Step 7a 的 full_text / company_context / industry_context /
# known_arenas / dimension_ref / industry_fields_hint / subjects_whitelist /
# figure_contexts / detected_tickers / checklist_items 代码
# 补：
file_meta = {
    "source_id": source_id,
    "sha8": sha8,
    "institution": institution,
    "publish_date": publish_date,
}
```

### 7b：拼 prompt

复用 annual Step 7b 的结构，digest prompt 换成 `sell-side-digest.md`，最终 prompt 末尾加：

```
## 卖方研报专属指令

1. polarity 以**研报作者立场**为准（分析师看多 → bull）；不是你自己的判断
2. **不要**产出 financial_rows（预测走 claims 通道，subject_tag=eps_forecast / revenue_forecast / target_price / rating）
3. 预测 claim 的 `time_type="forecast"`；历史 claim（如 FY2024A "已披露收入"）的 `time_type="actual"`；该字段已由 `facts_to_claims` 贯通落盘（Plan 4 T1）
4. meta_updates 通常留空（研报不是一手披露源）
5. claim_text 开头可选择加 `[{institution} {publish_date}]` 前缀便于下游区分
6. proposed_arenas 极少（研报少开新战场，除非主题就是"国产替代"等明确博弈）
7. narratives.company.{market}_{ticker}.valuation 必填（研报核心产出）
8. Arena checklist 填答仍走 `competence_findings.answered`，level=concrete|vague|unanswered
```

### 7c：Dispatch

```
tool: Agent
subagent_type: Explore
prompt: <上面拼好的>
```

**并发**：研报只有 1 个 digest subagent。旧版"按 heading 一级章节号拆 `thesis__lvl1/2/3` 3-5 个 subagent"不再使用——digest 读整份一次解决。

---

## Step 8：主 agent 汇总（digest → 三桶，丢 financial_rows + meta_updates）

```python
from scripts import ingest_aggregate as agg
import json
from pathlib import Path

digest = agg.load_json_tolerant(subagent_raw_output)
buckets = agg.route_key_facts(digest["key_facts"])
company_facts_grouped = agg.group_company_facts(digest["key_facts"])

# 研报专属后处理：
# 1. 丢弃 financial_rows（研报不经此通道；预测走 claims + time_type=forecast）
dropped_fin = digest.pop("financial_rows", [])
if dropped_fin:
    digest.setdefault("flags", []).append(
        f"sell-side digest 产出了 {len(dropped_fin)} 条 financial_rows，已丢弃"
        f"（预测数字应走 claims 通道 time_type=forecast）"
    )

# 2. 丢弃 meta_updates（研报不刷 meta）
dropped_meta = digest.pop("meta_updates", {})
if dropped_meta:
    digest.setdefault("flags", []).append(f"sell-side digest 产出了 meta_updates，已丢弃")

# 3. company facts → claims（研报主产物）
claims_all = []
for (t, m), facts in company_facts_grouped.items():
    if t != ticker or m != market:
        # Step 4a 已拒绝多公司研报；到此 refs 应全是本公司。
        # 若 digest 因 detected_tickers 偶尔产出可比公司 fact，进 flags 不写本公司
        continue
    claims_all.extend(agg.facts_to_claims(facts))
claims_all = agg.dedup_claims(claims_all)

# 4. 凑兼容 merged
merged = {
    "claims": claims_all,
    "financial_rows": [],
    "meta_updates": {},
    "competence_findings": digest.get("competence_findings", {
        "answered": [], "proposed_additions": []
    }),
    "flags_by_subagent": {"sell-side-digest": digest.get("flags", [])},
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

## Step 9：交叉校验（精简版）

```python
issues = {
    "empty_section":       agg.check_empty_sections(merged),
    "financials_required": agg.check_financials_required(merged),  # 用于捕获误产出；应为空
}
```

**不跑** `revenue_consistency`（研报无总收入锚）和 `period_consistency`（timeframe 跨多 FY 没有唯一 expected）。

- `empty_section` 非空 → warn，不暂停
- `financials_required` 非空 → 说明 Step 8 的"丢弃 financial_rows"没执行干净，pause 让用户排查

---

## Step 10：统一写入

研报写入清单：原文 → industry observations（若有）+ figure_contexts → narratives(industry + arena + company) → proposed_arena bootstrap → claims → competence。**不写** financials / profile / meta（原则不变，但 arena bootstrap 会同步更新 meta.arenas）。

```python
from datetime import datetime, timezone
from app.io import arenas as arenas_io

extracted_by = "claude-opus-4-7"
extracted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

source_meta = {
    "source_id": source_id,
    "source_file": Path(file_path).name,
    "sha8": sha8,
    "institution": institution,
    "date": publish_date,
}
```

### 10.1 原文（Step 6 已做）

### 10.2 industry observations + figure_contexts（研报偶有）

```python
# 仅 buckets["industry"] 非空时写（研报前几页"行业简介"可能含 TAM / 竞争）
if buckets["industry"]:
    n_obs = agg.write_industry_observations(
        buckets["industry"], source_meta,
        extracted_by=extracted_by, extracted_at=extracted_at,
    )

# figure_contexts 按 annual 10.4 的 multi-slug 模式写
slugs_touched = {
    (f.get("target_refs") or {}).get("industry_slug")
    for f in buckets["industry"]
}
for slug in slugs_touched:
    if not slug:
        continue
    agg.write_figure_contexts(slug=slug, contexts=figure_contexts, source_meta=source_meta)
```

### 10.3 narratives（industry + arena + company）

```python
from app import config as cfg

# industry narrative（研报"行业背景"段，confidence=medium）
ind_nar = digest["narratives"].get("industry", {})
first_keys = set(ind_nar.keys()) if ind_nar else set()
dim_set = set(cfg.INDUSTRY_DIMENSIONS)
if first_keys and first_keys.issubset(dim_set) and company_arenas and company_context["industry_slugs"]:
    ind_nar_payload = {company_context["industry_slugs"][0]: ind_nar}
else:
    ind_nar_payload = ind_nar
if ind_nar_payload:
    n_nar_ind = agg.write_industry_narrative(ind_nar_payload, source_meta)

# arena narratives（已存在的；newly-bootstrapped 在 10.4 后写）
arena_nar = digest["narratives"].get("arena", {})
known_slugs = set(company_arenas)
arena_nar_existing = {k: v for k, v in arena_nar.items() if k in known_slugs}
n_nar_arena = agg.write_arena_narrative(arena_nar_existing, source_meta)

# company narratives（研报主产物之一，必含 valuation dim）
comp_nar = digest["narratives"].get("company", {})
n_nar_comp = agg.write_company_narrative(comp_nar, source_meta)
```

### 10.4 proposed_arenas bootstrap（研报偶有）

同 annual Step 10.6；研报 proposed_arenas 通常 0-1 个。

```python
proposals = agg.propose_arena_bootstrap(digest.get("proposed_arenas", []))
# AskUserQuestion 审阅
approved_proposals = [...]
for p in approved_proposals:
    agg.bootstrap_arena(p)
    company_arenas.append(p["slug"])   # 更新内存映像

# 写 newly-bootstrapped arena 的 narrative
new_slugs = {p["slug"] for p in approved_proposals}
arena_nar_new = {k: v for k, v in arena_nar.items() if k in new_slugs}
if arena_nar_new:
    n_nar_arena += agg.write_arena_narrative(arena_nar_new, source_meta)
```

### 10.5 claims（研报主产物）

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

### 10.6 financials / profile / meta

- `financials.db`：研报不写
- `profile-*.md`：研报不写（研报不是事实源；新架构下 profile 整体废弃）
- `meta.md`：原则不写；**例外** —— 若 10.4 bootstrap 了新 arena，同步更新 `fm["arenas"]`：

```python
if approved_proposals:
    info = company_io.read_meta_with_body(ticker, market)
    fm = dict(info["frontmatter"])
    existing_arenas = set(fm.get("arenas") or [])
    new_arenas = {p["slug"] for p in approved_proposals}
    fm["arenas"] = sorted(existing_arenas | new_arenas)
    company_io.write_meta(ticker, market, fm, info["body"])
```

### 10.7 competence 写入（审阅后）

```python
findings = digest.get("competence_findings", {"answered": [], "proposed_additions": []})
consolidated = arenas_io.consolidate_answers(findings["answered"])
```

**AskUserQuestion 审阅**：

- 选项 A：approve 全部 answered + approve 所有 proposed_additions
- 选项 B：approve answered，拒绝所有 proposed（checklist 已成熟）
- 选项 C：逐条筛选
- 选项 D：跳过 competence 写入

**写入**（对每个 arena）：

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
    approved_new = [...]   # 主 agent 在审阅时已分好归属
    if approved_new:
        arenas_io.write_checklist(
            slug, checklist["items"] + approved_new,
            changelog_entry={
                "source_id": source_id,
                "changes": f"added {len(approved_new)} item(s) from {source_id}",
            },
        )
```

**注意**：digest 模式下 `consolidate_answers` 退化成 no-op（单 digest 无跨 subagent 合并），保留调用以兼容未来多 digest。

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
- `--arena` 指向本次 ingest 的 arena slug；多 arena 时挑一个"主" arena 跑即可（其它 arena 的 checklist 污染/dup 检查需要单独再跑）
- 把两步的退出消息记下来（warn 的 `added=X skipped_dup=Y reopened=Z`；gap 的 `✓ 落盘 path`），在 Step 11 收尾报告里展示

---

## Step 11：收尾报告

```
已 ingest 研报：companies/{market}_{ticker}/sources/{filename}
✓ claims.jsonl  +{N} 条 (source_id={source_id})
{✓|⊘} arenas/{slug}/competence-notes.md  {更新 M 条答案 / 用户跳过}
{✓|⊘} arenas/{slug}/checklist.yaml       {bump 到 vX (新增 K 条) / 无新增}
{✓|⊘} companies/{key}/meta.md.arenas    {追加 [{slugs}] / 已有}
✓ companies/{key}/qa_warnings.jsonl     +{W} 告警 · open={W_open}（首页 QA widget 会提示）
✓ companies/{key}/qa_gaps.md            已刷新（/qa/{key} 可看）
⊘ financials.db  研报不写
⊘ profile-*.md   研报不写

机构：{institution}
发布日期：{publish_date}
评级：{rating (若抽到)}
目标价：{target_price (若抽到)}
Arena：{arena_name} ({slug})

{若有} 丢弃的 subagent 产出：
  - financial_rows: {len(dropped_fin)} 条（研报不经此通道；应保留为 guidance_reliability claim）
  - profile_fragments / meta_updates: 同上

下一步建议：
- 用本次 claims 做 consensus 方向对照：`/research/{key}?subject=consensus_direction`
- 和最近一份年报的 claims 做分歧分析：对照研报作者观点 vs 公司自述
- 查看 arena 认知库：`arenas/{slug}/competence-notes.md`
- 本次抽到的 flags：
  - {flag 1}
  - {flag 2}
```

---

## 失败模式

| 场景 | 处理 |
|---|---|
| 预处理检测不出研报（form_detection 负例多） | 研报格式太乱，AskUserQuestion 确认是否强制继续 |
| 多公司研报混入 | Step 4a 判定后**拒绝**，提示"下一版支持行业研报" |
| institution / publish_date 抽不到 | AskUserQuestion 由用户输入 |
| company meta 不存在 | Step 2 自动建 meta（新股研报是常见 bootstrap 触发源，不中止） |
| Step 4.5 bootstrap-arena-definition subagent 返回无效 JSON / 四维缺 | AskUserQuestion 让用户手填 arena 四维，或跳过 arena 环节（本次 ingest 只写 claim，competence 不落盘） |
| Step 4.5 bootstrap-checklist 产出 >15 条或含未知 tag | IO 层 `write_checklist` 会拒绝；主 agent 回到审阅步让用户删到 15 条 / 修 tag |
| Step 7b 某子 subagent item 数 > 30 | pause，AskUserQuestion 让用户删 checklist 或裁 arena |
| subagent 产出 financial_rows | Step 8 丢弃并打 flag；若 `financials_required` 非空 pause |
| 预测 claim 数量异常高（>50 条单报） | dedup 后仍异常 → 通常是 forecasts subagent 把每行表格的每一列都独立抽成 claim；AskUserQuestion 让用户决定是否精简 |

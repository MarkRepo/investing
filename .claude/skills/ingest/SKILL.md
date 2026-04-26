---
name: ingest
description: 把一份财报（年报/季报/10-K/10-Q/20-F）、公司研报、或行业研报录入投资系统的三层知识系统（industry / arena / company）。触发词：ingest / 导入 / 录入 / 入库 / 10-K / 10-Q / 20-F / 年报 / 季报 / 半年报 / 研报 / 行业研报 / 行业深度 / Sector Report / Industry Report。适用于用户提供一个本地文件路径并说要把它"ingest / 导入 / 录入"到某家公司或某个行业。
allowed-tools: Bash Read Write Agent AskUserQuestion
argument-hint: "<file-path> [--key MARKET_TICKER | --industry INDUSTRY_SLUG]"
---

# ingest skill

把用户指定的一份财报 / 公司研报 / 行业研报按既定流程录入投资系统的**三层知识系统**：

- **industry/**（`industries/{slug}/`）：TAM / 竞争格局 / 生命周期 / 产业链 / 技术 / 监管 等 11 维 narrative + `observations.jsonl`（atomic 数值）+ `figure_contexts.jsonl`（图表上下文）
- **arena/**（`arenas/{slug}/`）：博弈叙事（国产替代 / 挑战者 / 演进轨迹）的 6 维 narrative + `definition.md` + `checklist.yaml`（能力圈填答版本化）
- **company/**（`companies/{market}_{ticker}/`）：business_model / moat / growth_engine / management / financial_profile / catalysts / risks / valuation 8 维 narrative + `claims.jsonl` + `financials.db`（SQLite 行）+ `sources/{filename}`

## 架构（Claude 执行前必读）

1. **直接调 `app/io/*`**，不走 HTTP 路由。服务是否启动不影响本 skill。
2. **LLM 抽取发生在对话里**（主 agent 派发 **1 个 digest subagent** 读整份报告）；Python 脚本（`scripts.preprocess_report` / `scripts.ingest_aggregate` / `scripts.ingest_qa`）只做预处理 / 校验 / 写入 / 查询，不调 LLM。
3. **digest subagent = 单 Explore**（只读，无写权限）。旧版"section-per-subagent，并发 ≤ 5"架构已废弃（v1，归档在 `prompts/_v1_archived/`）。digest subagent **返回 JSON**（key_facts / narratives / proposed_arenas / financial_rows / competence_findings / flags），主 agent 用 `route_key_facts` 分桶到三层，再统一写入 + 做交叉校验。
4. **事实层写入前必须让用户审**：`meta_updates` / `proposed_arena_bootstrap` 走 AskUserQuestion；claims / observations / narratives 校验通过后主 agent 直接写。
5. **meta / industry / company 缺失时主动建**（autobuild 纪律）——绝不中止流程引导用户去别处。`agg.ensure_industry_exists` / `agg.ensure_company_exists` 幂等。
6. **`profile-{year}.md` 不再产出**：新架构下公司事实层快照由 `companies/{key}/narratives/*.md`（8 维分文件）替代；`write_profile` / `company_io.write_profile` 已废弃。旧历史 profile 文件保留不迁移（Plan 4 做专门 migration + `/narratives/{key}` 路由）。
7. **Arena + 能力圈**是 ingest 的独立通道：digest subagent 除产 key_fact / narrative / proposed_arenas 外，还按注入的 `checklist_items` 填 `competence_findings.answered` + 可选 `proposed_additions`。用户审阅后落到 `arenas/{slug}/competence-notes.md`；新 proposed item 自增 checklist 版本。

## 输入

- 必给：文件的**绝对路径**。支持 `.pdf` / `.htm` / `.html` / `.md` / `.txt`。
- 可选（公司通道）：`MARKET_TICKER`（如 `US_HIMS`、`SSE_600519`）；不给则从文件名推断并 AskUserQuestion 确认。
- 可选（行业通道）：`INDUSTRY_SLUG`（如 `cn-cmp-material`）；不给则 workflow 自动从报告标题 / 摘要推，未匹配 → 走 `ensure_industry_exists` autobuild。

## 流程总览

1. **识别源类型** → 年报 / 季报 / 卖方研报（公司研报） / 行业研报
   - 先看文件名模式（`10-K`、`10-Q`、`20-F`、`年度报告`、`季度报告`、`半年度报告`、`行业深度`，或研报常见命名如 `citic` / `国金` / `morgan` / `goldman`）
   - 文件名只提机构名无"行业 / 公司"字样 → 读前 2 页判定（行业研报通常通篇不锚定单一 ticker）
   - 无法判定 → AskUserQuestion 让用户选
2. **确认目标**
   - 公司通道：market + ticker 二元组
   - 行业通道：industry slug（可复用已存在 or 新建）
3. **路由到对应 workflow**：
   - 年报 / 10-K / 20-F / 半年报 → `workflows/annual-report.md`
   - 季报 / 10-Q → `workflows/quarterly-report.md`
   - 卖方公司研报 → `workflows/sell-side-note.md`
   - 行业研报 → `workflows/industry-research.md`
4. **每个 workflow 第 4.5 步做 Arena 识别**（仅单公司 workflow；行业 workflow 的 arena 从 digest `proposed_arenas` 来）
5. **Step 7 派 digest subagent**（读 `prompts/digest/{source-type}-digest.md` + `_common.md` 拼 prompt，整份报告一次读完）；**Step 8** 用 `route_key_facts` 分三桶 + 凑兼容 merged；**Step 10** 三层统一写入
6. **Step 10.5 QA checkpoint**：公司通道跑 `scripts.ingest_qa warn --write + gap --write`；行业通道跑 `warn`（read-only 预览，Plan 4 支持 `industry:` scope 才 `--write`）
7. **Step 11 收尾报告**：写入清单 + 下一步建议 + digest flags

## 关键资源索引（主 agent 派单前读）

### Python 辅助
- `scripts.preprocess_report` — PDF/HTML → 结构化 JSON（`sections / figure_contexts / detected_tickers / financial_line_rows / meta / report_abstract`）
- `scripts.ingest_aggregate` — 全部 digest 后处理与写入辅助：`load_json_tolerant` / `route_key_facts` / `group_company_facts` / `facts_to_claims` / `dedup_claims` / `ensure_industry_exists` / `ensure_company_exists` / `propose_arena_bootstrap` / `bootstrap_arena` / `write_industry_observations` / `write_industry_narrative` / `write_arena_narrative` / `write_company_narrative` / `write_figure_contexts` / `write_financials` / `write_claims` / `check_revenue_consistency` / `check_period_consistency` / `check_financials_required` / `check_empty_sections`
- `scripts.ingest_qa` — QA 规则运行器（`warn` / `gap` / `list` / `resolve` / `dismiss`）

### 配置与模版
- **受控词表**：`controlled-vocab/subjects.yaml`（claims subject_tag 白名单；`claims_io.load_subjects()` 返回 `list[{id, label}]`，主 agent 用 `[s["id"] for s in load_subjects()]` 抽 whitelist）
- **preprocess 模版**：`.claude/skills/ingest/templates/{market}-{form}.yaml`（`a-share-annual/quarterly/industry` / `us-10k/10q/industry`）
- **section 路由表**：`.claude/skills/ingest/section-routing.yaml`（Plan 3 后只用于 preprocess skip 判断；digest 不按 section 分派）
- **source_id 规则**：`.claude/skills/ingest/source-id-rules.yaml`（7 种 format：us-10k / us-10q / us-20f / a-share-annual/quarterly/interim / sell-side / industry-research）
- **cross-check 规则**：`.claude/skills/ingest/cross-checks.yaml`
- **digest prompts**：`.claude/skills/ingest/prompts/digest/`
  - `_common.md`（所有 digest 共享的 schema + 铁律）
  - `industry-digest.md` / `annual-digest.md` / `quarterly-digest.md` / `sell-side-digest.md`

### 闭集与白名单
- **市场**：`app.config.VALID_MARKETS = ("US","SSE","SZSE","BSE","HK")`
- **sector**（仅 annual/sell-side 的单公司 meta.md 用）：`app.config.VALID_SECTORS = ("consumer","saas","cyclical","bank","biotech")`
- **三层维度**：`app.config.INDUSTRY_DIMENSIONS` (11) / `ARENA_DIMENSIONS` (6) / `COMPANY_DIMENSIONS` (8)
- **industry structured fields**：`app.config.INDUSTRY_FIELDS`（market_size / lifecycle / competition / benchmark / valuation 下的可选 key 集）

### 三层 IO
- `app.io.industry` — `list_industries / read_meta / write_meta / create_industry / read_observations / append_observations / read_narrative / append_narrative_block`
- `app.io.arenas` — `list_arenas / read_definition / write_definition / read_checklist / write_checklist / append_notes / consolidate_answers / find_by_industry / find_by_company / participants_add`
- `app.io.company` — `list_companies / read_meta / read_meta_with_body / write_meta / create_company / list_sources / read_narrative / append_narrative_block`
- `app.io.claims` — `load_subjects / save_source_markdown / validate_batch / append_batch / read_claims`
- `app.io.figure_contexts` — `append_figure_contexts / read_figure_contexts / filter_by_source_id / filter_by_section`
- `app.io.financials` — `import_financials_csv / load_alias_map`
- `app.io.qa` — `append_warnings / read_warnings / update_status / write_gap_markdown / summarize_by_company`

### Arena 预定义 tag
`industry_structure / competitive_position / growth_drivers / customer_structure / technology / policy_environment / financial_model / risk`（见 `prompts/arena/bootstrap-checklist.md`）

### QA 规则
`fidelity` / `self_contradict_specific` / `empty_evidence` / `polarity_mismatch` / `proposed_dup` / `checklist_company_contamination`，每条附 `fix_hint`。

## 预处理脚本

所有 workflow 第一步都调同一个：

```bash
.venv/bin/python -m scripts.preprocess_report <file> \
    --type {annual|quarterly|sell-side|industry} \
    --market {a-share|us} \
    --out <json_path>
```

输出 JSON 含顶层 keys：
- `meta.{source_file, sha8, detected_form, fiscal_year, reporting_period, institution, publish_date, cli_type}`
- `sections[{name, heading_raw, order, char_count, action, reason, text}]`
- `figure_contexts[{id, page, caption, surrounding_text, section_name}]`
- `detected_tickers[{market, ticker, name}]`
- `financial_line_rows[{raw_label, standard_key, numeric_candidates, line}]`（`--type industry` 下为空）
- `report_abstract`（封面 / 前言摘要，前 500 字）

## Digest dispatch（Step 7 核心模板）

主 agent 组装 prompt：

```python
digest_common  = Path(".claude/skills/ingest/prompts/digest/_common.md").read_text()
digest_topic   = Path(f".claude/skills/ingest/prompts/digest/{topic}-digest.md").read_text()
# topic ∈ {industry, annual, quarterly, sell-side}

prompt = f"""
{digest_common}

---

{digest_topic}

---

## 你本次要处理的输入

file_meta: ...
company_context: ...    # 公司通道才有
industry_context: ...
known_arenas: [...]
dimension_ref: {{industry: [...], arena: [...], company: [...]}}
industry_fields_hint: {{market_size: [...], ...}}
subjects_whitelist: [...]  # 公司通道才有
figure_contexts: [...]
detected_tickers: [...]
financial_line_rows: [...]   # annual/quarterly 才有
checklist_items: [...]        # 若 Step 4.5 有 item_pool

full_text: |
  <整份报告 extract sections 拼接>

现在请输出严格 JSON（顶层 keys: key_facts, narratives, proposed_arenas, flags 等；具体见 _common.md 和 {topic}-digest.md）
"""
```

派单：`Agent(subagent_type="Explore", prompt=prompt)`。返回 JSON → `agg.load_json_tolerant` 容错解析。

## 聚合/校验/写入库

Subagent 返回后的汇总、分层、归一化、交叉校验、最终写入都走 `scripts.ingest_aggregate`：

```python
from scripts import ingest_aggregate as agg
import json
from pathlib import Path

# 解析 + 分三桶
digest = agg.load_json_tolerant(raw_output)
buckets = agg.route_key_facts(digest["key_facts"])           # {industry, arena, company}
company_facts_grouped = agg.group_company_facts(digest["key_facts"])

# company facts → claims
claims_all = []
for (t, m), facts in company_facts_grouped.items():
    if t == ticker and m == market:
        claims_all.extend(agg.facts_to_claims(facts))
claims_all = agg.dedup_claims(claims_all)

# 凑 QA 兼容 merged（Step 10.5 依赖）
merged = {
    "claims": claims_all,
    "financial_rows": digest.get("financial_rows", []),
    "meta_updates": digest.get("meta_updates", {}),
    "competence_findings": digest.get("competence_findings",
                                      {"answered": [], "proposed_additions": []}),
    "flags_by_subagent": {f"{topic}-digest": digest.get("flags", [])},
    "empty_subagents": [],
}
Path(f"/tmp/ingest-{sha8}.merged.json").write_text(json.dumps(merged, ensure_ascii=False))
Path(f"/tmp/ingest-{sha8}.digest.json").write_text(json.dumps(digest, ensure_ascii=False))

# 三层 + financials + claims 写入（Step 10，见各 workflow）
agg.write_industry_observations(buckets["industry"], source_meta, extracted_by=..., extracted_at=...)
agg.write_industry_narrative({slug: dims_dict}, source_meta)
agg.write_arena_narrative({arena_slug: dims_dict}, source_meta)
agg.write_company_narrative({f"{market}_{ticker}": dims_dict}, source_meta)
agg.write_figure_contexts(slug=industry_slug, contexts=figure_contexts, source_meta=source_meta)
agg.write_financials(ticker, digest["financial_rows"], source_file=...)   # annual/quarterly
agg.write_claims(ticker, market, claims_all, source_id=..., source_file=..., extracted_by=..., extracted_at=...)

# arena bootstrap（来自 digest.proposed_arenas）
for p in approved_proposals:
    agg.bootstrap_arena(p)

# industry / company autobuild（digest 引用缺失时）
agg.ensure_industry_exists(slug=..., name=..., scope=...)
agg.ensure_company_exists(ticker=..., market=..., name=..., industry_slugs=[...], currency=...)
```

**该模块封装了**：polarity / evidence 归一化（容错旧 section-per-subagent 的漂移）、period 归一化（`FY2025 → 2025A`）、claims batch header 平铺（`build_claims_batch` / `write_claims` 替你做对）、按 `target_layer` 分桶、多-slug industry 分拣。

## 直接调用的 IO（绕过 HTTP）

| 函数 | 用途 |
|---|---|
| `claims_io.load_subjects()` | 受控词表（`list[{id, label}]`） |
| `claims_io.save_source_markdown(ticker, market, filename, content)` | 落原文到 `companies/{key}/sources/`（公司通道） |
| `claims_io.validate_batch(json_text, subjects)` | 校验 LLM 产出（`write_claims` 内部调） |
| `claims_io.append_batch(ticker, market, valid, header)` | 原子追加 claims.jsonl |
| `claims_io.read_claims(ticker, market)` | 读已有 claims（source_id 碰撞检测） |
| `company_io.read_meta(ticker, market)` | 存在性检查 |
| `company_io.read_meta_with_body(ticker, market)` | 拿 frontmatter + body |
| `company_io.create_company(...)` | **主动建 meta**（autobuild） |
| `company_io.list_sources(ticker, market)` | 已上传 source 列表 |
| `company_io.append_narrative_block(ticker, market, dim, block, source_meta)` | 写 8 维 narrative 片段 |
| `industry_io.list_industries()` | 列已有 industry slug |
| `industry_io.read_meta(slug)` | 存在性检查 |
| `industry_io.read_observations(slug)` | source_id 碰撞检测（行研） |
| `industry_io.append_narrative_block(slug, dim, block, source_meta)` | 写 11 维 narrative 片段 |
| `arenas_io.find_by_company(ticker, market)` | 反查公司参与的 arena slug |
| `arenas_io.find_by_industry(industry_slug)` | 反查 industry 下的 arena slug |
| `arenas_io.read_definition(slug)` | arena 定义（`battleground_focus / participants / industry`） |
| `arenas_io.read_checklist(slug)` / `write_checklist(...)` | checklist 版本化 |
| `arenas_io.consolidate_answers(raw)` | 跨 subagent 同 q_id 合并（digest 模式下 no-op，保留兼容） |
| `arenas_io.append_notes(slug, ticker, market, name, ...)` | 写 competence-notes.md |
| `figure_contexts_io.append_figure_contexts(slug, rows, source_meta)` | `industries/{slug}/figure_contexts.jsonl` |

函数签名和前置条件详见 `/Users/yangqi/investing/app/io/*.py`。

## 绝不做的事

- ❌ 从新闻 / 管理层展望 / 研报观点升级到事实层（`meta.md` / `narratives/*.md` 的 confidence 默认 `medium`，不写 `primary`）
- ❌ 不经用户审直接应用 `meta_updates` / 直接 bootstrap 新 arena
- ❌ 让 subagent 直接写任何文件（digest subagent 是 Explore 类型，只读返回 JSON）
- ❌ 写 `profile-{year}.md`（已废弃；company narratives 替代）
- ❌ 多公司研报直接录入（卖方 workflow 第 4a 步会拒绝；建议走行业研报通道）
- ❌ 在 Python 脚本里调 LLM（用户 feedback：LLM 判断由 Claude 在对话里做，脚本只管校验+写入）
- ❌ 跳过 `controlled-vocab/subjects.yaml` 白名单（`validate_batch` 会拒）
- ❌ preprocess / dispatch 失败走"主 agent 手工补"一次性 workaround（用户 feedback：改 template / 正则 / 白名单正向修）

## 当前版本范围（Plan 3 后）

**支持**：
- 单公司年报 / 10-K / 20-F / 半年报
- 单公司季报 / 10-Q
- 单公司卖方研报
- 行业研报（跨公司，多 ticker，新开 arena）

**不支持**（下一版）：
- 公司公告（非财报）
- 电话会纪要
- 新闻 / 社媒
- 多公司研报（请走行业研报通道）
- 行研 QA `--write`（当前只支持 read-only 预览；Plan 4 加 `industry:{slug}` scope）
- 旧 profile-*.md → narratives/*.md migration（Plan 4）

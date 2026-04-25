---
name: ingest
description: 把一份财报（年报/季报/10-K/10-Q/20-F）或研报录入投资系统。触发词：ingest / 导入 / 录入 / 入库 / 10-K / 10-Q / 20-F / 年报 / 季报 / 半年报 / 研报。适用于用户提供一个本地文件路径（或 inbox/财报/ 下的文件）并说要把它"ingest / 导入 / 录入"到某家公司。先只支持聚焦单一公司的财报+研报，行业研报待后续版本。
allowed-tools: Bash Read Write Agent AskUserQuestion
argument-hint: "<file-path> [--key MARKET_TICKER]"
---

# ingest skill

把用户指定的一份财报或研报按既定流程录入投资系统（`companies/{key}/`、`data/financials.db`、`claims.jsonl`、`profile-{year}.md`）。

## 设计要点（Claude 执行前必读）

1. **直接调 `app/io/*`**，不走 HTTP 路由。服务是否启动不影响本 skill。
2. **LLM 抽取发生在对话内**（主 agent 或派发的 subagent）；Python 脚本只做预处理/校验/写入/查询。
3. **subagent 用 `Explore` 类型**（只读，无写权限）——section 粒度并发上限 5。subagent **返回数据**，主 agent 统一写入 + 做交叉校验。
4. **事实层（profile.md / meta.md）写入前必须让用户审**；claims 校验通过后主 agent 直接写。
5. **meta 缺失时主动建**——绝不中止流程引导用户去别处（详见 `feedback_ingest_autobuild_meta.md`）。
6. **Arena + 能力圈是 ingest 的独立通道**：subagent 除产 claim/profile/financials 外，还按注入的 arena checklist 填 `competence_findings`。用户审阅后落到 `arenas/{slug}/competence-notes.md`；新 proposed item 自增 checklist 版本。和 claim 是两个独立 JSON 字段，不互相污染。

## 输入

- 必给：财报/研报文件的**绝对路径**。支持 `.pdf` / `.htm` / `.html` / `.md` / `.txt`。
- 可选：目标公司 key（`MARKET_TICKER`，如 `US_HIMS`、`SSE_600519`）。不给则从文件名推断并 AskUserQuestion 确认。

## 流程总览

1. **识别源类型** → 财报年报 / 财报季报 / 研报
   - 先看文件名模式（`10-K`、`10-Q`、`20-F`、`年度报告`、`季度报告`、`半年度报告`，或研报常见命名如 `citic`、`morgan`）
   - 无法判定 → AskUserQuestion 让用户选
2. **确认目标 company key**（如上）
3. **路由到对应 workflow**：
   - 年报 / 10-K / 20-F / 半年报 → `workflows/annual-report.md`
   - 季报 / 10-Q → `workflows/quarterly-report.md`
   - 卖方研报 → `workflows/sell-side-note.md`
4. 每个 workflow 第 4.5 步做 **Arena 识别/复用** + 必要时 Checklist 引导；第 7b/7c 步按 checklist tag 路由 item 到 subagent；第 10 步审阅后把 `competence_findings` 落到 `arenas/{slug}/`。
5. **第 10.5 步 QA checkpoint 是每次 ingest 的标配**：跑 `scripts.ingest_qa warn --write` + `scripts.ingest_qa gap --write` 把抽取告警和缺口清单落盘到 `companies/{key}/qa_warnings.jsonl` / `qa_gaps.md`，首页 `🔎 QA 未处理告警` widget 和 `/qa/{key}` 页面会自动展示。**不要跳过**——它是 ingest 闭环的质量反馈。
6. 按 workflow 执行完后，产出**写入清单 + 下一步建议**（例如 `/earnings-review/{key}`、`catalysts` 登记下期财报日、`arenas/{slug}/competence-notes.md` 查看认知库；QA 告警指引下一次 ingest 什么、哪里改 prompt）

## 关键资源索引（subagent dispatch 前要加载）

- **受控词表**：`controlled-vocab/subjects.yaml`（claims subject_tag 白名单；`app.io.claims.load_subjects()` 可直接读）
- **模版剔除规则**：`.claude/skills/ingest/templates/{market-form}.yaml`（预处理脚本消费）
- **section 路由表**：`.claude/skills/ingest/section-routing.yaml`（哪个 section 走哪个 subagent + targets）
- **source_id 规则**：`.claude/skills/ingest/source-id-rules.yaml`
- **交叉校验规则**：`.claude/skills/ingest/cross-checks.yaml`
- **公司 sector 白名单**：`app.config.VALID_SECTORS = ("consumer","saas","cyclical","bank","biotech")`
- **公司市场白名单**：`app.config.VALID_MARKETS = ("US","SSE","SZSE","BSE","HK")`
- **Arena 预定义 tag 集**：`industry_structure / competitive_position / growth_drivers / customer_structure / technology / policy_environment / financial_model / risk`（见 `prompts/arena/bootstrap-checklist.md`）
- **Arena IO**：`app.io.arenas`（`list_arenas` / `read_arena` / `write_definition` / `read_checklist` / `write_checklist` / `append_notes` / `consolidate_answers` / `participants_add` / `find_by_company`）
- **QA IO**：`app.io.qa`（`append_warnings` 幂等 / `read_warnings` / `update_status` / `write_gap_markdown` / `summarize_by_company`）；CLI 入口 `scripts.ingest_qa`（`warn` / `gap` / `list` / `resolve` / `dismiss`）
- **QA 规则**：`fidelity` / `self_contradict_specific` / `empty_evidence` / `polarity_mismatch` / `proposed_dup` / `checklist_company_contamination`，每条附 `fix_hint`

## 预处理脚本

所有 workflow 第一步都调同一个：

```bash
.venv/bin/python -m scripts.preprocess_report <file> \
    --type {annual|quarterly|sell-side} \
    --market {a-share|us} \
    --out <json_path>
```

输出 JSON 含 `meta.{source_file,sha8,detected_form,fiscal_year,reporting_period}` 和 `sections[{name, heading_raw, order, char_count, action, reason, text}]`。workflow 消费这个 JSON 做后续分派。

## 聚合/校验/写入库

Subagent 返回后的汇总、schema 归一化、交叉校验、最终写入都走同一个模块——不要在对话里手写这些逻辑：

```python
from scripts import ingest_aggregate as agg

outputs  = {name: agg.load_json_tolerant(text) for name, text in subagent_results.items()}
merged   = agg.aggregate(outputs)
merged["claims"] = agg.dedup_claims(merged["claims"])

# cross-checks
revenue_issues = agg.check_revenue_consistency(merged, tol=0.02)
period_issues  = agg.check_period_consistency(merged, expected=meta["fiscal_year"])

# writers (after user reviews profile)
n_fin          = agg.write_financials(ticker, merged["financial_rows"], source_file=fname)
n, errors      = agg.write_claims(ticker, market, merged["claims"],
                                  source_id=..., source_file=fname,
                                  extracted_by="claude-opus-4-7", extracted_at=...)
```

该模块封装了：polarity 同义词归一化（`positive→bull`）、`evidence_text → evidence` 包装、`FY2025 → 2025A` 期间转码、claims batch header **必须平铺**（嵌套 `"header"` key 会让 `source_id` 被静默丢弃）、分部/总收入的 revenue_consistency 区分等易错点。

## 直接调用的 IO 函数（绕过 HTTP）

| 函数 | 用途 |
|---|---|
| `claims_io.load_subjects()` | 受控词表 |
| `claims_io.save_source_markdown(ticker, market, filename, content)` | 落原文到 `sources/` |
| `claims_io.validate_batch(json_text, subjects)` | 校验 LLM 产出 |
| `claims_io.append_batch(ticker, market, valid, header)` | 原子追加 claims.jsonl |
| `claims_io.read_claims(ticker, market)` | 读已有 claims（source_id 碰撞检测） |
| `company_io.read_meta(ticker, market)` | 存在性检查 |
| `company_io.create_company(ticker, market, name, sector, currency)` | **主动建 meta**（meta 缺失时） |
| `company_io.list_sources(ticker, market)` | 已上传 source 列表 |
| `company_io.write_profile(ticker, market, year, fm, body)` | 写 profile（用户审后） |
| `fin_io.import_financials_csv(ticker, csv_text, source_file=filename)` | CSV → SQLite |
| `arenas_io.find_by_company(ticker, market)` | 反查公司参与的 arena slug 列表 |
| `arenas_io.read_checklist(slug)` | 读 arena 的 checklist v 最新 |
| `arenas_io.consolidate_answers(raw)` | 跨 subagent 同 q_id 合并（取 level 最高 + evidence 最长） |
| `arenas_io.append_notes(slug, ticker, market, name, ...)` | 按 ticker 分段写 competence-notes.md |
| `arenas_io.write_checklist(slug, items, changelog_entry)` | bump 版本 + 追加 changelog |

所有函数签名和前置条件详见 `/Users/yangqi/investing/app/io/*.py`。

## 绝不做的事

- ❌ 从新闻、管理层展望、研报观点升级到事实层（`meta.md` / `profile-*.md`）
- ❌ 不经用户审直接写 profile / meta
- ❌ 让 subagent 直接写任何文件（subagent 只返回数据）
- ❌ 多公司研报直接录入（当前版本拒绝，提示等行业研报支持）
- ❌ 调 HTTP 路由或开 curl 访问本地服务（directly import 即可）
- ❌ 跳过 `controlled-vocab/subjects.yaml` 白名单（`validate_batch` 会拒）

## 当前版本范围

**支持**：聚焦单公司的年报 / 10-K / 20-F / 半年报 / 季报 / 10-Q / 卖方研报。

**不支持**（下一版）：行业研报、公司公告（非财报）、电话会纪要、新闻、社媒。遇到这些类型直接告知用户并终止。

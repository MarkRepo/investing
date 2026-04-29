# Plan 5 — industry-research ingest 链路 gap 修复

**动机**：Plan 4 T4 把 industry-research workflow 的 QA step 从 read-only 翻到 `--write`；2026-04-27 用国金证券《化学机械抛光行业》研报跑了一遍端到端，暴露 13 个 gap（详见对话记录）。本 plan 按"改动小→改动大"的优先级修复其中 12 个（#8 归档为 known-issue）。

---

## Gap 覆盖矩阵

| Gap | 描述 | 修在哪 | 任务 |
|-----|------|--------|------|
| #1  | preprocess detected_tickers=[] | digest prompt fallback | T5 |
| #2  | preprocess 目录行全进 keep 桶 | preprocess 加过滤规则 | T6 |
| #3  | figure_contexts 含目录行伪装 | preprocess 同一规则扩展 | T6 |
| #4  | workflow 文档说 `narratives/` 子目录，实现是根目录 | 改文档对齐 | T2 |
| #5  | workflow 文档 `action=="extract"` 实现产 `"keep"` | 改文档对齐 | T2 |
| #6  | subagent 不遵守 JSON-only，自行 bash 写 /tmp | 显式允许 + 主 agent 加路径 fallback | T3 |
| #7  | narratives.arena key 用中文而非 slug | digest prompt 硬约束 | T5 |
| #8  | subagent 自述桶分布 vs 实际 route 不一致 | known-issue（不修） | — |
| #9  | arena 桶空但 proposed_arenas 非空 | digest prompt 硬约束（≥3 条） | T5 |
| #10 | proposed_arenas 缺 tentative_name | schema 加字段 | T5 |
| #11 | company fact subject_tag_hint=None 被拒 | digest prompt 必填 + T4 partial-success | T5 + T4 |
| #12 | QA fidelity 在 preprocess 不全时虚假告警 | 改 fuzzy match 或降级 | T7 |
| #13 | write_claims reject-all 导致好 claims 也被丢 | 改 partial-success | T4 |

---

## 任务顺序（执行次序）

T2 → T3 → T4 → T5 → T6 → T7 → T8

前 3 项纯文档/小 IO；T4 `write_claims` 一处改动；T5 覆盖 5 个 gap 集中在 digest prompt；T6 改 preprocess；T7 改 QA 规则；T8 回归。

---

## T2：workflow 文档对齐

- `action=="extract"` → `action=="keep"`（preprocess 实际产出）
- `industries/{slug}/narratives/*.md` → `industries/{slug}/*.md`（实现是根目录，arena/industry 都是）
- Step 11 收尾报告行同步

## T3：subagent 文件 fallback

- digest prompt 加："**允许**用 bash 写 `/tmp/digest_output.json` 然后在最后返回该路径；主 agent 会自动读"
- workflow Step 6 加"主 agent 从 subagent 返回文本里识别 `/tmp/*.json` 路径，若存在则读取"
- 这样 Explore subagent（无 Write 权限）用 bash heredoc 写 JSON 的行为被正式化

## T4：write_claims partial-success

`scripts/ingest_aggregate.py:482-483` 当前：
```python
if errors:
    return 0, errors
claims_io.append_batch(ticker, market, valid, header=header, base=base)
return len(valid), []
```

改为：
```python
if valid:
    claims_io.append_batch(ticker, market, valid, header=header, base=base)
return len(valid), errors
```

返回契约从 "(整批成功数, 整批错误)" 改为 "(写入条数, 被拒条数列表)"。调用方都是"报给用户"模式，自然兼容。

## T5：digest prompt 硬约束

改 `.claude/skills/ingest/prompts/digest/_common.md`：

- 铁律第 10 条改：`narratives.arena` 的 key 必须是 **kebab-case slug**，且与 `proposed_arenas[*].tentative_slug` 或 `known_arenas[*].slug` 一一对应。用中文 key 的整段会被主 agent 丢弃。
- 铁律第 11 条新增：`target_layer=company` 的 key_fact 必须填 `subject_tag_hint`（从 `subjects_whitelist` 取）。不填会导致该 fact 被转成 claim 后被拒。
- schema 新增 `proposed_arenas[*].tentative_name`（简短中文名，≤20 字，面向 UI 展示）。

改 `.claude/skills/ingest/prompts/digest/industry-digest.md`：

- "arena 识别与 proposed_arenas" 段加："**如果产出 proposed_arenas 非空，必须有至少 3 条 key_fact 的 `target_layer=arena`**。不满足则该 proposed_arena 被认为证据不足，主 agent 会拒建。"
- "Company 事实的处理" 段加："每条 company key_fact **必填** `subject_tag_hint`，从 `subjects_whitelist` 取最贴近的一个。找不到合适的就填 `other`。"
- 新增 "detected_tickers 为空的 fallback"：若 preprocess 未抽到 ticker 但 full_text 明显提到公司（如"安集科技"、"鼎龙股份"），你需要从文本推断 ticker 与 market。推断不出留空。

## T6：preprocess 目录行过滤

`scripts/preprocess_report.py`：

- 加一个正则 `_TOC_TAIL_RE = re.compile(r"\s*\.{3,}\s*\d+\s*$")`（末尾一串点 + 页码）
- `apply_skip_rules` 内：若 `sec["heading_raw"]` 匹配 `_TOC_TAIL_RE` → `action="skip"`, `reason="TOC line"`
- `extract_figure_contexts`：遍历时跳过 caption 匹配 `_TOC_TAIL_RE` 的候选（目录里的 "图表1：CMP 工作原理 ...... 4" 不是真 figure）

## T7：QA fidelity 规则降级

`scripts/ingest_qa.py`（或被它调用的 qa 规则模块）的 `fidelity_quote_match` 规则：

- 当前：evidence_quote 前 40 字做子串匹配 preprocess text，不中抛 warn
- 改：匹配不中时，再做 **去空白 fuzzy match**（把 quote 和 preprocess text 都去掉所有空白/换行/全角空格，然后 substring 匹配）
- 仍不中时 warn 措辞改为 "evidence_quote 在 preprocess 原文里匹配不到（可能是 PDF 提取损失或 subagent 改写）"，提醒这不是硬错

## T8：回归

- `.venv/bin/python -m pytest` 全量通过
- 不必重跑 CMP 报告（本次已跑通，fix 体现在下一次 ingest）

---

## 不修的（known-issue）

- **#8**：subagent 自述桶分布计数与主 agent `route_key_facts` 实际分桶数有偏差。观察性问题，不影响下游数据正确性。在 workflow Step 7 的"预期分布"行加一条注："subagent 自述不可信，以 `route_key_facts` 结果为准"。

---

## 不在范围

- PDF 提取器升级（从当前 `pdftotext` 换成 `unstructured`/`docling`）— 涉及依赖更换，独立评估
- 中文公司名 → ticker 字典（需要外部数据源）
- digest subagent 改用 general-purpose（无 Write 限制）— 目前 Explore 走 bash 写文件也能用，不值得换

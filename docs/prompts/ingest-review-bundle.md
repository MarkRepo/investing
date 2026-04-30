<!-- prompt_version: phase1.5-v1 -->

# Ingest Review Bundle 抽取 Prompt（Phase 1）

从 `scripts/preprocess_report.py` 生成的 preprocess JSON 里抽取单篇研报的 `ingest_review_bundle`。
Python 端只做 preprocess 和 `review-bundle` QA；LLM 判断发生在 Claude 对话里，不调用 LLM API。

---

## 流程

1. 运行 preprocess，得到 `preprocess.json`
2. 在 Claude 对话里贴入本 prompt
3. 贴入完整 `preprocess.json`
4. 先做 full-report pass：按 `sections` 顺序通读所有 `action != "skip"` 的正文段落，记录覆盖日志
5. Claude 只返回严格 JSON，保存为 `bundle.json`
6. 运行 `scripts/ingest_qa.py review-bundle --bundle bundle.json --preprocess preprocess.json`
7. 如果 QA 报 warning/error，优先修正 bundle；如果反复出现同类问题，再修 prompt

> 关键词检索或抽样只能用于 smoke test，不能作为正式 review bundle 的依据。

---

## 系统指令（复制到对话）

```text
你是投资研究资料整理助手。任务：根据用户提供的 preprocess JSON，生成一个 Phase 1 `ingest_review_bundle`。

Phase 1 只产出可审核的中间结果，不写入 archive，不改写 industries / arenas / companies 文件。

【输入】
用户会提供 `scripts/preprocess_report.py` 输出的 preprocess JSON。你只能使用 JSON 中的 `sections`、`meta`、`preprocess_metadata`、`figure_contexts` 等内容。

【输出要求】
只返回一个 JSON 对象。不要 markdown，不要解释，不要代码围栏。
顶层对象必须是：

{
  "bundle_version": "v2-phase1",
  "source_digest": {
    "source_id": "短 id；优先使用 preprocess meta 中的来源信息，否则用用户给出的文件名/日期/机构组合",
    "source_title": "研报或文件标题；没有就省略",
    "source_type": "industry_report | company_report | annual_report | quarterly_report | sell_side_report | transcript | unknown",
    "source_date": "YYYY-MM-DD；没有明确日期就省略",
    "source_quality": "high | medium_high | medium | low",
    "evidence_strength": "high | medium_high | medium | medium_low | low",
    "limitations": ["只写输入文本本身导致的限制"],
    "coverage_review": {
      "mode": "full_report_pass",
      "sections_total": 0,
      "sections_reviewed": 0,
      "skipped_sections": 0,
      "coverage_notes": ["说明哪些部分质量差、目录/免责声明被跳过、哪些主题被覆盖"]
    }
  },
  "insight_blocks": [
    {
      "id": "ib-001",
      "block_type": "用 2-4 个词描述内容类型，不限于预定义值，如 technology、market_size、company_exposure、development_roadmap、unit_economics、risk 等",
      "title": "不超过 30 字",
      "source_page_range": "页码或范围，如 3 或 8-10；未知则省略",
      "summary": "忠实概括这个 insight，不超过 120 字",
      "evidence_strength": "high | medium_high | medium | medium_low | low",
      "reasoning_chain": ["第一条：原文支撑的观察（可验证的事实）", "最后一条：因此对投资判断意味着什么（必须是推断，不能是事实重复）"],
      "block_relations": [
        {"block_id": "ib-001", "relation": "premise_for | corroborates | risk_to | contradicts"}
      ],
      "archive_routing_hints": {
        "target_layer": "industry | arena | company | cross_layer | unknown",
        "dimension_hint": "market_size | lifecycle | value_chain | competition | drivers | technology | regulation | benchmark | risks | valuation | financial_profile | catalysts | unknown",
        "entity_hints": ["原文明确出现的行业、arena、公司或 ticker"]
      }
    }
  ],
  "atomic_facts": [
    {
      "fact_id": "fact-001",
      "linked_block_id": "ib-001",
      "fact_text": "一句话事实；不要把观点和事实混在一起",
      "evidence_quote": "preprocess 文本中能找到的原文短句，必须直引或近似连续片段",
      "source_page": 1,
      "confidence": "high | medium | low"
    }
  ],
  "stage_gates": [
    {
      "id": "sg-001",
      "gate_type": "unit_economics | demand_validation | supply_validation | policy_validation | company_exposure_validation | valuation_validation | other",
      "title": "需要跨过的判断门槛",
      "crossed": false,
      "linked_block_ids": ["ib-001"],
      "what_would_cross_it": ["还需要什么证据才能跨过"]
    }
  ],
  "company_candidates": [
    {
      "ticker": "688019",
      "market": "SSE | SZSE | BSE | HK | US | unknown",
      "name": "公司名；原文未给则省略",
      "exposure_type": "direct_supplier | direct_customer | competitor | upstream | downstream | thematic_related | unknown（判断标准：direct_supplier/direct_customer 要求原文有明确合同、采购关系或已交付订单证据；thematic_related 指只有主题相关性、无合同或采购证据；有预期/意向但未签约用 thematic_related，不要升级为 direct_*）",
      "confidence": "high | medium | low",
      "source_block_ids": ["ib-001"],
      "verification_questions": ["进入公司 archive 前必须验证的问题"]
    }
  ],
  "arena_candidates": [
    {
      "candidate_id": "ac-001",
      "tentative_slug": "短蛇形 slug，不得是单一公司名",
      "name": "竞争格局名称（≤20 字，不得以单一公司命名）",
      "parent_industry_slug": "必填；所属行业的 slug（如 cn-nuclear-fusion）",
      "battleground_focus": "一句话说明竞争焦点是什么",
      "participant_tickers": ["MARKET_TICKER 格式，如 SSE_603011；必须对应 company_candidates 中的条目"],
      "linked_block_ids": ["ib-001"],
      "confidence": "high | medium | low",
      "verification_questions": ["确认 arena 是否成立前要验证的问题"]
    }
  ],
  "synthesis": {
    "one_sentence": "一句话结论；避免确定爆发、必然受益等过度确定措辞",
    "evidence_strength": "high | medium_high | medium | medium_low | low",
    "what_we_know": ["已由原文直接支持的结论"],
    "what_is_plausible": ["合理但仍需验证的推断"],
    "what_needs_verification": ["下一步要查的证据"],
    "investment_questions": ["投资研究问题"],
    "cannot_conclude": ["当前不能得出的结论，特别是未跨过的 stage gate"]
  },
  "schema_fit_review": {
    "fits_current_schema": true,
    "missing_schema_fields": ["描述原文中重要但 bundle 现有字段无法容纳的信息类型；没有则空数组"],
    "extra_fields_needed": [
      {
        "proposed_field": "建议字段名（短蛇形）",
        "rationale": "为什么需要",
        "example_evidence": "研报中哪一段无处安放（短引文或描述）"
      }
    ],
    "notes": "简述（≤150 字）"
  },
  "claim_candidates": [
    {
      "candidate_id": "cc-001",
      "claim_text": "单句命题，不得混合多个命题",
      "scope_type": "industry | arena | company | cross_cutting",
      "scope_ref": "industry_slug / arena_slug / MARKET_TICKER；scope_type=cross_cutting 时留空字符串",
      "claim_type": "thesis | judgment | risk | scenario | gate_assessment",
      "dimension_hint": "与 insight_block.archive_routing_hints.dimension_hint 同值域",
      "supporting_block_ids": ["ib-001"],
      "direction_on_source": "supports | refutes | neutral",
      "confidence": "high | medium_high | medium | medium_low | low",
      "as_of": "YYYY-MM-DD；等于 source_digest.source_date"
    }
  },
  "write_status": "not_applicable_phase1"
}

【硬约束】
1. `bundle_version` 必须是 `v2-phase1`。
2. `write_status` 必须是 `not_applicable_phase1`。
3. `insight_blocks` 不能为空。每个 block 必须有稳定 id：`ib-001`, `ib-002`, ...，且 `block_type` 不能为空。
4. 每个 `atomic_facts[*].linked_block_id` 必须指向已有 insight block。
5. 每个 `atomic_facts[*].evidence_quote` 必须来自 preprocess 文本；不要编造引用。
6. `fact_text` 中出现的公司名、ticker、关键数值，必须也出现在 `evidence_quote` 中；如果 quote 只支持其中一半，就拆成更小的 fact。
7. 正式输出前必须完成 full-report pass：不能只靠关键词搜索、摘要页或抽样段落。
8. 如果 evidence 来自图表重、图片重、表格重或 text_quality 低的页面，相关 fact/candidate 不要给 high confidence。
9. `company_candidates` 只是候选，不写 archive。`thematic_related` 不要给 high confidence。
10. 如果某个 stage gate 的 `crossed=false`，必须在 `synthesis.cannot_conclude` 里写出不能得出的结论。
11. 如果 `source_digest.evidence_strength` 是 `low` 或 `medium_low`，`synthesis.one_sentence` 必须保守，不能写“确定”“必然”“爆发”“显著受益”等强结论。
12. 不要把原文没有说的公司、ticker、市场空间、利润率或估值写进去。
13. 宁可少抽，也不要把推测写成事实。
14. `block_relations` 是可选字段；如果填写，`block_id` 必须指向已有 insight block 且不能是自身，`relation` 必须是 `premise_for`、`corroborates`、`risk_to`、`contradicts` 之一。
15. `claim_candidates` 从 `synthesis.what_we_know` / `what_is_plausible` / `investment_questions` 提炼。每条必须：
    - `claim_text` 是单句命题（不是主题或名词短语；不混合两个以上论点）
    - `scope_type` 在 `industry | arena | company | cross_cutting` 四值枚举内
    - `supporting_block_ids` 全部来自本 bundle 的 `insight_blocks[].id`
    - `direction_on_source` 记录本研报对该命题的方向（supports / refutes / neutral）
    - `as_of` 等于 `source_digest.source_date`
16. `claim_candidates` 粒度控制：一个 insight_block 通常对应 0-2 条 candidate。不要为每个 atomic_fact 生成 candidate（那是证据，不是命题）。也不要把整份报告合成为 1 条 candidate（过粗无法跨报告比对）。
17. `candidate_id` 稳定格式 `cc-{NNN}`（与 ib / fact id 编号规则对齐）。
18. `schema_fit_review.fits_current_schema` 为 false 时，`missing_schema_fields` 和 `extra_fields_needed` 至少一个非空（即给出具体不适配点，不允许 false + 空建议）。
19. 输出必须是可被 `json.loads()` 解析的严格 JSON。
20. `arena_candidates[*].parent_industry_slug` 必填；所属行业的 slug 不能为空字符串。
21. `arena_candidates[*].linked_block_ids` 必须全部指向本 bundle 中已有的 `insight_blocks[].id`。
22. `arena_candidates[*].participant_tickers` 使用 `MARKET_TICKER` 格式（如 `SSE_603011`），且必须对应 `company_candidates` 中的条目；不能凭空填写不在 company_candidates 里的 ticker。
23. `arena_candidates[*].tentative_slug` 和 `name` 不得是单一公司的名称或 ticker——arena 是竞争格局，必须代表多方竞争关系。
24. `arena_candidates` 中 `confidence=high` 的条目至少要有 2 条 `linked_block_ids`；只有 1 条证据 block 时，降为 `medium`。

【抽取顺序】
1. 先读 `preprocess_metadata.extracted_pages`，记住低质量、图表重、图片重、表格重页面。
2. 按 `sections` 的原始顺序通读所有 `action != "skip"` 的段落；目录、免责声明、页眉页脚可以记为低价值，但不能漏掉正文段落。对每个 section，在决定是否提炼 block 之前，先识别该 section 内的所有独立子话题，再对每个子话题独立判断是否值得成 block。不允许用 section 开头的内容类型（表格、图注、数字列等）代表整个 section 的价值。
3. 完成覆盖日志：统计 sections 总数、reviewed 数、skip 数，并在 `source_digest.coverage_review` 写明覆盖范围和低质量区域。
4. 归纳 `insight_blocks`，数量由内容自然决定，不设上限。每个 block 的 `reasoning_chain` 必须至少两条：第一条是原文支撑的可验证观察，最后一条必须是对投资判断的含义推断，不允许全部是事实陈述。不满足此条件的内容降为 `atomic_fact`，不单独成 block。
5. 为每个 block 绑定 1-5 条 `atomic_facts`，事实必须有 evidence quote。
6. 对每条 fact 做语义核对：`fact_text` 的公司名、ticker、关键数字都必须能在 `evidence_quote` 中看到。
7. 标出未被原文充分证明、但会影响投资判断的 `stage_gates`。
8. 只把原文明确点名的公司列入 `company_candidates`。
9. 最后写保守 synthesis，区分已知、可推断、待验证、不能得出。
```

## Source-type 分型字段要求

根据 `source_digest.source_type` 应用附加要求。原文有就填、没有就在 `source_digest.limitations` 里说明，**禁止编造**。

### industry_report
- `insight_blocks` 至少一条 `block_type` 涉及 `market_size` / `value_chain` / `lifecycle` / `demand_driver` / `technology` 之一
- 涉及早期行业（生物医药、低空经济、核聚变、BCI、量子、商业航天等）时，`stage_gates` 至少一条，且 `synthesis.cannot_conclude` 非空

### company_report / sell_side_report
- `company_candidates` 至少一条；每条 `exposure_type` 必填
- 若原文提及估值判断，至少一个 insight_block 的 `reasoning_chain` 明确涉及估值假设（折现率、倍数或对标）

### annual_report / quarterly_report
- `insight_blocks` 覆盖 `business_model` / `financial_profile` / `catalysts` 中至少一个
- 管理层指引或前瞻陈述若原文出现，单独作为 `insight_block` 或 `atomic_fact` 记录（不隐藏在通用 summary 里）

### transcript
- 问答涉及 forward-looking 部分，对应 `atomic_facts` 的 `confidence` 不得高于 `medium_high`；对应 `insight_blocks` 的 `evidence_strength` 同样上限 `medium_high`

不属于以上类型时不加额外约束。

把 Claude 输出保存为 `bundle.json` 后运行：

```bash
python3 scripts/ingest_qa.py review-bundle --bundle bundle.json --preprocess preprocess.json
```

如果使用 worktree 里的虚拟环境：

```bash
.venv/bin/python scripts/ingest_qa.py review-bundle --bundle bundle.json --preprocess preprocess.json
```

通过时输出：

```text
✓ review bundle QA passed
```

出现 warning/error 时，先改 `bundle.json`，再重跑 QA。

---

## 常见修正

- `missing_insight_blocks`：补 `insight_blocks`，不要只产 synthesis。
- `fact_missing_linked_block`：每条 fact 都要绑定 `linked_block_id`。
- `fact_unknown_linked_block`：`linked_block_id` 必须是已有 `ib-xxx`。
- `fact_missing_evidence_quote`：补能在 preprocess 文本中找到的原文短句。
- `fact_text_entity_missing_from_quote`：把 fact 拆小，或让 `evidence_quote` 同时包含 fact 里的公司名/ticker/关键实体。
- `high_confidence_fact_from_risky_page`：把对应 confidence 降到 medium/low，或换用更可靠页面证据。
- `stage_gate_missing_cannot_conclude`：在 `synthesis.cannot_conclude` 写明还不能得出的结论。
- `candidate_missing_exposure_type`：补候选公司的 exposure 类型。
- `candidate_missing_source_blocks`：补候选公司来自哪些 insight blocks。
- `candidate_missing_verification_questions`：补进入 archive 前必须验证的问题。
- `thematic_related_high_confidence`：主题相关候选不能 high confidence。
- `low_evidence_strong_synthesis`：降低 synthesis 结论强度。
- `candidate_overclaimed_in_synthesis`：不要把候选公司写成确定受益者。
- `block_missing_block_type`：补 `block_type`，用 2-4 个词描述内容类型。
- `block_shallow_reasoning_chain`：`reasoning_chain` 至少两条，最后一条必须是投资含义推断，不能全是事实陈述。
- `block_relations_unknown_block`：`block_relations` 里的 `block_id` 必须是已有 `ib-xxx`，且不能是自身。
- `block_relations_invalid_relation`：`relation` 只能是 `premise_for`、`corroborates`、`risk_to`、`contradicts`。
- `arena_candidate_missing_parent_industry`：补 `arena_candidates[*].parent_industry_slug`，指向所属行业 slug。
- `arena_candidate_unknown_linked_block`：`arena_candidates[*].linked_block_ids` 中的 id 必须是已有的 `ib-xxx`。
- `arena_candidate_participant_not_in_company_candidates`：`participant_tickers` 中的每个 `MARKET_TICKER` 必须在 `company_candidates` 中有对应条目（相同 market + ticker）。
- `arena_candidate_overconfident`：`confidence=high` 的 arena candidate 必须有至少 2 条 `linked_block_ids`；不足时降为 `medium`。
- `claim_refs_nonexistent_arena`：`scope_type=arena` 的 claim candidate 的 `scope_ref` 必须匹配 `arena_candidates[*].tentative_slug`；如果指向的 arena 不在本 bundle 中，改用实际存在的 slug 或在 `arena_candidates` 中补充对应条目。

---

## 反例

- 不要输出 markdown：```json 会导致后续脚本读取失败。
- 不要写 `write_status: ready_to_write`：Phase 1 不写 archive。
- 不要用 `source_page_range: "多页"`：能定位就写页码，不能定位就省略。
- 不要把 `company_candidates` 当投资推荐清单：它只是待验证候选。
- 不要因为研报标题看多就写”确定受益”：必须受 evidence strength 约束。
- 不要把 `reasoning_chain` 写成纯事实列表：`[“西部超导是唯一供应商”, “超导业务占比23%”]` 两条都是事实，没有投资含义推断，不合格。正确写法：第一条陈述观察，最后一条明确说明”因此对投资判断意味着什么”。

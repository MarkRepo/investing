<!-- prompt_version: phase2-v3 -->

# Ingest Review Bundle 抽取 Prompt（Phase 2 — MinerU + 图片分类）

从 MinerU 桌面应用产出的 `full-clean.md`（已剔除装饰图片）+ `keep_images/`（仅数据图表）目录里抽取单篇研报的 `ingest_review_bundle`。
Python 端做格式包装和图片分类，不调用 LLM API；LLM 判断发生在对话里。

---

## 流程

1. 用 MinerU 桌面应用将 PDF 转换为输出目录（包含 `full.md` + `images/`）
2. 运行 `clean_mineru` 清洗：`.venv/bin/python -m scripts.clean_mineru <mineru_dir>`
3. 运行 `mineru_ingest.py` 包装路径：`.venv/bin/python -m scripts.mineru_ingest <mineru_dir> --out /tmp/ingest-<sha8>-mineru.json`
4. 在 Claude 对话里贴入本 prompt
5. 贴入 `full-clean.md` 的完整内容；遇到 `![](keep_images/...)` 时读取对应图片
5. 先做 full-report pass：通读整份报告，记录覆盖日志
6. Claude 只返回严格 JSON，保存为 `bundle.json`
7. 运行 `scripts/ingest_qa.py review-bundle --bundle bundle.json --mineru-md full.md`
8. 如果 QA 报 warning/error，优先修正 bundle；如果反复出现同类问题，再修 prompt

> 关键词检索或抽样只能用于 smoke test，不能作为正式 review bundle 的依据。

> **图片分类规则**：`clean_mineru` 脚本会自动将 153 张图片分为 53 张数据图表（保留在 `keep_images/`）和 100 张装饰图片（移到 `delete_images/`）。分类依据：图片行的上下各 1 行内有 `图X` 标签或 `来源：` 引用即为数据图，否则为装饰图（章节 banner、签名头像、logo 等）。

---

## 系统指令（复制到对话）

```text
你是投资研究资料整理助手。任务：根据用户提供的 MinerU 转换后的 Markdown 内容，生成一个 Phase 1 `ingest_review_bundle`。

Phase 1 只产出可审核的中间结果，不写入 archive，不改写 industries / arenas / companies 文件。

【输入】
用户会提供 MinerU 产出的 `full.md` 文件内容，以及 `keep_images/` 目录中的图片引用。
你只能使用 full.md 中的文字和对应的图片来理解报告内容。

full.md 中可能包含：
- 正文文字（标题、段落、列表）
- HTML 表格（数据表格、财务数据）
- 图片引用：`![](keep_images/xxx.jpg)` — 这些是数据图表（已剔除装饰性图片）
- LaTeX 数学公式：`$$...$$` 或 `$...$`

【阅读方式】
逐段通读 full.md 全文。遇到 `![](keep_images/...)` 引用时，读取对应图片文件来理解其中的数据、趋势、图表内容。表格中的文字可以直接阅读。

如果信息来自图片（图表、表格截图），用对图片内容的文字描述作为 `evidence_quote`，并在末尾注明 `（from image）`。

【输出要求】
只返回一个 JSON 对象。不要 markdown，不要解释，不要代码围栏。
顶层对象必须是：

{
  "bundle_version": "v2-phase1",
  "source_digest": {
    "source_id": "短 id；优先使用原文中的来源信息，否则用用户给出的文件名/日期/机构组合",
    "source_title": "研报或文件标题；没有就省略",
    "source_type": "industry_report | company_report | annual_report | quarterly_report | sell_side_report | transcript | unknown",
    "source_date": "YYYY-MM-DD；没有明确日期就省略",
    "industry_archetype": "technology_driven | consumer_driven | cyclical | financial | real_asset | other（从报告封面/主题判断；判断不明时在 limitations 说明，按 other 处理）",
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
      "block_type": "用 2-4 个词描述内容类型。注意：下文 Source-type 分型字段要求 列出了每种 source_type 的必提 block_type 清单，必须全部覆盖。清单中未列出的类型也可自由新增。",
      "title": "不超过 30 字",
      "source_page_range": "页码或范围，如 3 或 8-10；未知则省略",
      "summary": "忠实概括这个 insight，不超过 120 字",
      "evidence_strength": "high | medium_high | medium | medium_low | low",
      "evidence_sparse": "可选，默认 false。当该 block 原文仅有定性描述、无可独立引用的原子事实时设为 true。此时 atomic_facts 可为空数组。",
      "sparse_reason": "当 evidence_sparse=true 时必填（≤60 字），如'原文仅第 X 段一句定性描述，无具体数据'",
      "reasoning_chain": ["第一条：原文支撑的观察（可验证的事实）", "最后一条：因此对投资判断意味着什么（必须是推断，不能是事实重复）"],
      "block_relations": [
        {"block_id": "ib-001", "relation": "premise_for | corroborates | risk_to | contradicts"}
      ],
      "archive_routing_hints": {
        "target_layer": "industry | arena | company | cross_layer | unknown",
        "dimension_hint": "market_size | lifecycle | value_chain | competition | drivers | technology | regulation | benchmark | risks | valuation | financial_profile | catalysts | unknown",
        "entity_hints": ["原文明确出现的行业、arena、公司或 ticker"]
      },
      "narrative_priority": "1-5 整数，决定该 ib 在 INSIGHTS.md 和 narrative .md 中的展开顺序。按 source_type 的含义见「narrative_priority 含义表」。",
      "transition_hint": "可选。与同一 narrative_priority 或相邻 priority ib 的逻辑关系：therefore | however | further | specifically | but_note | meanwhile"
    }
  ],
  "atomic_facts": [
    {
      "fact_id": "fact-001",
      "linked_block_id": "ib-001",
      "fact_text": "一句话事实；不要把观点和事实混在一起",
      "evidence_quote": "full.md 中能找到的原文短句，必须直引或近似连续片段",
      "source_page": 1,
      "confidence": "high | medium | low",
      "reviewer_notes": "可选。如果输入附带 suspicious_tokens.json，且 evidence_quote 中包含 flagged token，必须在此写明标记类型和提示。"
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
  // 编辑注：tentative_slug 和 name 应代表竞争格局，而非单一公司名或 ticker——arena 是多方竞争关系的概念。
  "arena_candidates": [
    {
      "candidate_id": "ac-001",
      "tentative_slug": "短蛇形 slug",
      "name": "竞争格局名称（≤20 字）",
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
      "evidence_basis": "full_fact_chain | summary_only",
      "investment_implication": "≤150 字，把 claim_text 翻译为可直接写入叙事段落的投资含义。不是复述 claim_text，而是说'这条 claim 对投资决策意味着什么'。示例：claim_text='磁体占 24.9% 金额敞口最集中' → investment_implication='超导磁体供应商在产业链中拥有最高金额敞口，磁体业务收入弹性最大。'",
      "semantic_nucleus": "≤20 字，claim_text 去停用词后的核心名词+动词组合。保证跨模型/跨 run 稳定，用于 anchor_hash 计算。示例：'磁体是 A 股金额敞口最集中环节' → '磁体 敞口 最集中'",
      "anchor_hash": "16 个 hex 字符（自动计算，LLM 不需要填写）。计算方式：sha256(scope_type|scope_ref|dimension_hint|claim_type|semantic_nucleus)[:16]",
      "as_of": "YYYY-MM-DD；等于 source_digest.source_date"
    }
  ],
  "write_status": "not_applicable_phase1",
  "narrative_arc": [
    {
      "arc_id": "arc-001",
      "arc_type": "investment_thesis | risk_scenario | technology_shift | competitive_reshuffling | demand_cycle | consumption_upgrade | supply_restructuring | regulatory_shift | earnings_upgrade | earnings_downgrade | rating_initiation | thesis_refresh | business_progress | earnings_review | strategic_pivot | guidance_update | outlook_statement | qa_insights",
      "title": "≤40 字",
      "sections": [
        {"section_name": "string", "block_ids": ["ib-xxx", ...]}
      ]
    }
  ]
}

【narrative_priority 含义表】
每个 insight_block 必须有 priority（1-5），不同 source_type 对应的含义：

industry_report:
  1 = 行业定位 / 当前阶段（domain_fundamentals, industry_stage）
  2 = 核心催化剂 / 为什么现在（quant_catalyst, policy_environment, demand_driver）
  3 = 主导范式与竞争 / 产业链分析（mainstream_paradigm, value_chain, brand_competition, alternative_paradigm）
  4 = 公司敞口 / 推荐标的（company_exposure）
  5 = 风险与边界（risk）

sell_side_report:
  1 = 公司定位 / 主营业务（company_snapshot）
  2 = 本次报告核心判断 / 投资要点
  3 = 竞争力分析 / 护城河（competitive_moat）
  4 = 盈利预测 / 估值（financial_profile, valuation）
  5 = 风险（risk）

annual_report / quarterly_report:
  1 = 公司主业定位（business_model）
  2 = 本期经营亮点 / 财务进展（catalysts, financial_profile）
  3 = 业务分部 / 业绩驱动分析
  4 = 管理层展望 / 资本开支 / 指引
  5 = 风险与治理（risk）

transcript:
  1 = 会议背景 / 发言人
  2 = 核心观点 / 对当前形势判断
  3 = 关键问答
  4 = 前瞻性内容（指引、计划、展望）
  5 = 风险或保留意见

【硬约束】
1. `bundle_version` 必须是 `v2-phase1`。
2. `write_status` 必须是 `not_applicable_phase1`。
3. `insight_blocks` 不能为空。每个 block 必须有稳定 id：`ib-001`, `ib-002`, ...，且 `block_type` 不能为空。
4. 每个 `atomic_facts[*].linked_block_id` 必须指向已有 insight block。
5. 每个 `atomic_facts[*].evidence_quote` 必须来自页面内容；不要编造引用。如果信息来自图片（图表、表格截图），用对图片内容的文字描述作为 `evidence_quote`，并在末尾注明 `（from image）`。
6. `fact_text` 中出现的公司名、ticker、关键数值，必须也出现在 `evidence_quote` 中；如果 quote 只支持其中一半，就拆成更小的 fact。
7. 正式输出前必须完成 full-report pass：不能只靠关键词搜索、摘要页或抽样段落。
8. 如果 evidence 来自图片（图表、表格截图），相关 fact/candidate 不要给 high confidence。
9. `company_candidates` 只是候选，不写 archive。`thematic_related` 不要给 high confidence。
10. 如果某个 stage gate 的 `crossed=false`，必须在 `synthesis.cannot_conclude` 里写出不能得出的结论。
11. 如果 `source_digest.evidence_strength` 是 `low` 或 `medium_low`，`synthesis.one_sentence` 必须保守，不能写"确定""必然""爆发""显著受益"等强结论。
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
23. `arena_candidates` 中 `confidence=high` 的条目至少要有 2 条 `linked_block_ids`；只有 1 条证据 block 时，降为 `medium`。
24. 如果输入附带 `suspicious_tokens.json`，凡 `atomic_facts[*].evidence_quote` 中包含 flagged token 的 fact，必须在 `fact.reviewer_notes` 写明"原文此处存在 {flag_type} 标记：{hint}"；fact 的 confidence 不得高于 medium。
25. 每条 claim 必须有 `evidence_basis` 字段（full_fact_chain | summary_only）。从 evidence_sparse=true 的 ib 派生的 claim，evidence_basis 必须为 summary_only。
26. 每个 insight_block 必须有 `narrative_priority`（整数 1-5），按 source_type 的优先级含义表赋值。所有 ib 都必须标，不只标必提类。
27. 每条 claim 必须有 `investment_implication`（≤150 字），这是 claim 的投资含义翻译，不是 claim_text 的复述。
28. bundle 顶层可产 `narrative_arc`（0-2 条），描述整篇报告的叙事骨架。选择 arc_type 不局限于 source_type 默认类型，以原文叙事气质为准。
29. 每条 claim 必须有 `semantic_nucleus`（≤20 字），从 claim_text 提取核心名词+动词组合（去停用词）。不同模型/不同 run 对同一 claim 产出的 semantic_nucleus 应稳定一致。

【抽取顺序】
1. 通读整份 full-clean.md，记住所有 `![](keep_images/...)` 出现的位置和对应的图片内容。
2. 按原文顺序逐段通读整份报告。对于图片引用的位置，结合图片内容综合判断。封面、目录、免责声明等低价值内容可以跳过，但不能漏掉正文。
3. 完成覆盖日志：统计总段落数、reviewed 数、跳过数，并在 `source_digest.coverage_review` 写明覆盖范围和低质量区域。
4. 归纳 `insight_blocks`，数量由内容自然决定，不设上限。每个 block 的 `reasoning_chain` 必须至少两条：第一条是原文支撑的可验证观察，最后一条必须是对投资判断的含义推断，不允许全部是事实陈述。不满足此条件的内容降为 `atomic_fact`，不单独成 block。
5. 为每个 block 绑定 1-5 条 `atomic_facts`，事实必须有 evidence quote。
6. 对每条 fact 做语义核对：`fact_text` 的公司名、ticker、关键数字都必须能在 `evidence_quote` 中看到（如果 quote 标注了 `from image`，只需核对文字描述部分）。
7. 标出未被原文充分证明、但会影响投资判断的 `stage_gates`。
8. 只把原文明确点名的公司列入 `company_candidates`。
9. 最后写保守 synthesis，区分已知、可推断、待验证、不能得出。
```

## Source-type 分型字段要求

根据 `source_digest.source_type` 和 `industry_archetype` 应用附加要求。**以下列出的 block_type 为强制必提项，缺失任一类 QA 会报 error。** 原文有就填、没有就在 `source_digest.limitations` 里说明，**禁止编造**。

### industry_report — 通用必提 block_type（6 类，所有行业大类都必须有）

| block_type | 含义 | 不同行业大类的典型内容 |
|---|---|---|
| domain_fundamentals | 行业根基 | tech: 物理定律/关键判据；consumer: 用户画像/消费场景；cyclical: 供需平衡/库存周期；financial: 监管/资本金；real_asset: 地段/容积率 |
| industry_stage | 行业所处阶段 | 导入期/成长期/成熟期/衰退期/重构期；含关键时间节点 |
| mainstream_paradigm | 主导范式 | tech: 主流技术路线；consumer: 主流商业模式/产品形态；cyclical: 主流工艺；financial: 主流产品结构；real_asset: 主流开发模式 |
| value_chain | 产业链价值量分布 | 成本/毛利/费率在产业链各环节的分布 |
| policy_environment | 政策/监管环境 | 国家规划、地方政策、行业监管、税收补贴 |
| company_exposure | 公司敞口 | 报告关注/推荐标的及其敞口结构 |

### industry_report — 按行业大类的扩展必提（各 2-3 类）

**technology_driven 加 3 类**
- alternative_paradigm（竞争/替代路线）
- quant_catalyst（定量催化剂：AI 精度 / 材料突破 / 良率提升，必须含具体数字）
- risk（技术/资金/路线更替风险）

**consumer_driven 加 3 类**
- demand_driver（需求驱动：人口结构/消费升级/渗透率）
- brand_competition（品牌集中度/渠道格局/市占率排名）
- risk（需求疲软/竞品/原料成本风险）

**cyclical 加 3 类**
- cycle_position（周期位置：价格/库存/产能利用率）
- supply_demand_balance（在建产能 / 退出产能 / 净新增）
- risk（需求/成本/环保限产风险）

**financial 加 2 类**
- asset_quality_or_spread（资产质量 / 息差 / 费率 / 准备金覆盖）
- risk（信用/流动性/监管/地缘风险）

**real_asset 加 2 类**
- supply_pipeline（土地/项目储备、竣工排期、REITs 发行节奏）
- risk（需求/融资/政策风险）

**other 加 1 类**
- risk（任何 source_type 都必须有风险边界 ib）

### sell_side_report — 必提 block_type（5 类，与行业大类无关）

company_snapshot / financial_profile / competitive_moat / valuation / risk

### annual_report / quarterly_report — 必提 block_type（4 类）

business_model / financial_profile / catalysts / risk

### 证据密度的三级降级

当原文对某类内容只有定性描述、无可独立引用数字或事实时，使用降级路径（禁止编造）：

| 情况 | block_type | atomic_facts | ib 字段 | 下游影响 |
|---|---|---|---|---|
| **A - 类别充分**（默认） | 存在 | ≥ 1 条，每条有 evidence_quote | evidence_strength ∈ {high, medium_high, medium} | 正常参与 claim / auto_apply |
| **B - 类别存在但事实稀疏** | 存在 | 允许 `[]` | evidence_strength ≤ medium_low；evidence_sparse: true；sparse_reason 必填（≤60 字）；source_page_range 必填 | 派生 claim 必须 evidence_basis="summary_only"，无论 confidence 如何均不走 auto_apply |
| **C - 类别缺失** | 不存在 | N/A | N/A | 必须在 source_digest.limitations 写明"原文未涉及 {block_type}" |

**量化类特例**（quant_catalyst / demand_driver / asset_quality_or_spread / cycle_position / supply_pipeline）：走 B 路径时 evidence_strength 强制为 low。

**防滥用**：单份 bundle 中 B 路径 ib 不超过必提清单的 1/3（9 类中最多 3 类稀疏）。

### company_report
- `company_candidates` 至少一条；每条 `exposure_type` 必填
- 若原文提及估值判断，至少一个 insight_block 的 `reasoning_chain` 明确涉及估值假设（折现率、倍数或对标）

### transcript
- 问答涉及 forward-looking 部分，对应 `atomic_facts` 的 `confidence` 不得高于 `medium_high`；对应 `insight_blocks` 的 `evidence_strength` 同样上限 `medium_high`

把 Claude 输出保存为 `bundle.json` 后运行：

```bash
python3 scripts/ingest_qa.py review-bundle --bundle bundle.json --mineru-md <mineru_dir>/full-clean.md
```

如果使用 worktree 里的虚拟环境：

```bash
.venv/bin/python scripts/ingest_qa.py review-bundle --bundle bundle.json --mineru-md <mineru_dir>/full-clean.md
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
- `fact_missing_evidence_quote`：补能在文本中找到的原文短句，或图片内容的文字描述（标注 `from image`）。
- `fact_text_entity_missing_from_quote`：把 fact 拆小，或让 `evidence_quote` 同时包含 fact 里的公司名/ticker/关键实体。
- `high_confidence_fact_from_image`：如果 fact 来自图片（图表、表格截图），把 confidence 降到 medium/low。
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
- 不要因为研报标题看多就写"确定受益"：必须受 evidence strength 约束。
- 不要把 `reasoning_chain` 写成纯事实列表：`["西部超导是唯一供应商", "超导业务占比23%"]` 两条都是事实，没有投资含义推断，不合格。正确写法：第一条陈述观察，最后一条明确说明"因此对投资判断意味着什么"。

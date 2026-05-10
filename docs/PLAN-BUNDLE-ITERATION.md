# Bundle Ingest Pipeline 迭代计划

> **读者**：实施此计划的工程 agent（Sonnet）。本文档自包含，无需参考其他上下文即可落地。
> **计划范围**：从当前 bundle 抽取层 + 机械 narrative 拼接，演进到"覆盖率达标 + 可读消费层 + 跨报告可融合"的三层架构。
> **不在范围内**：UI 改造、前端视图、ClaimRegistry 底层 jsonl schema 重构、多轮 LLM refinement。

---

## 1. 战略背景

### 1.1 系统定位

当前 ingest pipeline 从 MinerU 产出的 PDF Markdown 抽取投资研究知识结构（bundle.json），然后落地到三层知识系统（industry / arena / company）。

Bundle 的战略定位是**多研报融合的技术储备**，不是单篇摘要工具。对"看完一份研报做一次投资决策"这个场景，LLM 直接摘要（sonnet/gemini）已接近覆盖率上限（~87%），bundle 没有边际优势。Bundle 的真正价值在 N 份研报聚合后的能力：跨券商观点对比、stage_gate 机械触发、arena 竞争格局演化、claim 跨时间追踪。

### 1.2 覆盖率与融合价值的曲线原理

经实测对比（`mineru_summaries/he-jubian-bundle-analysis.md`），覆盖率 → 融合价值不是单调递增，而是倒 U 曲线：

| 覆盖率区间 | 单篇提升成本 | 融合边际收益 |
|---|---|---|
| 73% → 85% | 低（改 prompt 20 行） | **大**（补齐物理基础/政策/催化剂量化/竞争路线等跨报告主线类别） |
| 85% → 92% | 中（分层 prompt + 自我审视） | 中 |
| 92% → 97% | 高（人工 audit） | 小 |
| 97% → 100% | 极高 | **负**（边角事实成为 claim registry 噪声） |

**推论**：迭代目标是 73% → ~85%，且提升方式是"补类别"而不是"补数量"——某个 block_type 必须有，但那一类里 2 条 fact 还是 5 条 fact 对融合价值没差别。超过 85% 的覆盖率投入应转移到消费层和对齐层。

### 1.3 实施的三层分工

```
Layer A  抽取层（Extract）   把原料补齐到可聚合标准（覆盖契约 + 反笔误）
Layer B  消费层（Consume）    让 bundle 对人可读、对投资决策直接可用
Layer C  对齐层（Align）      让 N 份 bundle 能跨报告融合（anchor + decay + gate watcher）
```

本计划按 P0/P1/P2/P3 四阶段分配任务，P0 立即执行，其后阶段分别依赖前一阶段完成。

---

## 2. 当前系统的关键文件与产物

实施者必须先熟悉以下文件路径：

### 2.1 Ingest pipeline 核心脚本

| 文件                                    | 作用                                                              |
| ------------------------------------- | --------------------------------------------------------------- |
| `scripts/mineru_ingest.py`            | 包装 MinerU 输出目录为 ingest JSON pointer                             |
| `scripts/clean_mineru.py`             | 清洗 MinerU 产出（移除装饰图）                                             |
| `scripts/preprocess_report.py`        | 旧流程（HTM/MD/TXT）                                                 |
| `scripts/ingest_qa.py`                | Bundle QA 校验（`review-bundle` 子命令）                               |
| `scripts/ingest_match.py`             | 将 bundle claim 匹配到 ClaimRegistry（产 auto_apply + pending_review） |
| `scripts/ingest_apply.py`             | 落地已批准的 claim 到 jsonl                                            |
| `scripts/narrative_propose.py`        | 生成 narrative proposals（body=null）                               |
| `scripts/narrative_apply.py`          | 落地 narrative .md 文件                                             |
| `scripts/narrative_flags.py`          | 检测孤儿 narrative 段                                                |
| `scripts/ingest_aggregate.py` (`agg`) | 公共 helper（ensure_industry/company、write_figure_contexts）        |
| `app/io/bundle_registry.py`           | `persist_bundle` helper                                         |

### 2.2 Skill 与 prompt

| 文件                                                     | 作用                              |
| ------------------------------------------------------ | ------------------------------- |
| `.claude/skills/ingest/SKILL.md`                       | ingest skill 入口                 |
| `.claude/skills/ingest/workflows/_ingest-common.md`    | 15 步通用 workflow                 |
| `.claude/skills/ingest/workflows/industry-research.md` | 行业研报分型                          |
| `.claude/skills/ingest/workflows/sell-side-note.md`    | 券商点评分型                          |
| `.claude/skills/ingest/workflows/annual-report.md`     | 年报分型                            |
| `.claude/skills/ingest/workflows/quarterly-report.md`  | 季报分型                            |
| `.claude/skills/ingest/templates/*.yaml`               | 分型参数模板（章节检测、机构提取等）              |
| `.claude/skills/ingest/cross-checks.yaml`              | 跨文件一致性校验规则                      |
| `docs/prompts/ingest-review-bundle.md`                 | bundle LLM 抽取 prompt（核心迭代对象）    |
| `.claude/skills/report-summary-prompt.md`              | LLM 直接摘要 prompt（已加三条硬约束，作为对照基准） |

### 2.3 数据层路径

| 路径                                                 | 说明                    |
| -------------------------------------------------- | --------------------- |
| `industries/{slug}/sources/`                       | 原始研报文件                |
| `industries/{slug}/bundles/{sha8}.json`            | 持久化 bundle            |
| `industries/{slug}/bundles/{sha8}-evaluation.json` | QA 评估骨架               |
| `industries/{slug}/*.md`                           | industry 维度 narrative |
| `industries/{slug}/figure_contexts.jsonl`          | 图表上下文                 |
| `arenas/{arena_slug}/*.md`                         | arena 维度 narrative    |
| `companies/{MARKET_TICKER}/narratives/*.md`        | company 维度 narrative  |
| `data/claims/{industries,arenas,companies}.jsonl`  | ClaimRegistry         |
| `data/audit/claim-events.jsonl`                    | claim 审计日志            |
| `data/bundle_registry.jsonl`                       | bundle 注册表            |

### 2.4 Bundle JSON 结构（当前 v2-phase1）

核心实体：
- `source_digest`（source_id / source_title / source_type / source_date / source_quality / evidence_strength / coverage_review）
- `insight_blocks[]`（id / block_type / title / summary / reasoning_chain / block_relations / archive_routing_hints）
- `atomic_facts[]`（fact_id / linked_block_id / fact_text / evidence_quote / source_page / confidence）
- `stage_gates[]`（id / gate_type / title / crossed / linked_block_ids / what_would_cross_it）
- `company_candidates[]`（ticker / market / name / exposure_type / confidence / source_block_ids / verification_questions）
- `arena_candidates[]`（candidate_id / tentative_slug / name / parent_industry_slug / battleground_focus / participant_tickers / linked_block_ids / confidence / verification_questions）
- `claim_candidates[]`（candidate_id / claim_text / scope_type / scope_ref / claim_type / dimension_hint / supporting_block_ids / direction_on_source / confidence / as_of）
- `synthesis`（one_sentence / evidence_strength / what_we_know / what_is_plausible / what_needs_verification / investment_questions / cannot_conclude）
- `schema_fit_review`（fits_current_schema / missing_schema_fields / extra_fields_needed）
- `bundle_version: "v2-phase1"` / `write_status: "not_applicable_phase1"`

---

## 3. 任务清单

### Phase 0 — 立即修（抽取层止血，零成本高回报）

#### P0.1 — 加强制 `block_type` 清单到 ingest prompt

**目标**：bundle 覆盖率 73% → ~85%，通过"必提类别"而不是"补数量"实现。

**改动文件**：
- `docs/prompts/ingest-review-bundle.md` — 在"## Source-type 分型字段要求"段扩写
- `scripts/ingest_qa.py` — 在 `review-bundle` 子命令里加强制 block_type 清单校验

**具体内容**：

清单按 **"通用基础类 + 行业大类扩展"** 两级结构组织，以避免把科技类专属概念（物理基础、技术路线）错误地强加到消费/金融/地产等非技术驱动行业。

新增字段 `source_digest.industry_archetype`，枚举：
- `technology_driven`：核聚变、半导体、AI、量子、BCI、商业航天、合成生物、创新药
- `consumer_driven`：宠物、白酒、美妆、餐饮、奢侈品、运动服饰、家电
- `cyclical`：钢铁、煤炭、化工、航运、建材、有色、油气
- `financial`：银行、保险、券商、资管、支付
- `real_asset`：地产、基建、REITs、公用事业
- `other`：其他或跨类（必须在 `limitations` 说明）

行业大类由 LLM 从报告封面/主题判断；判断不明时在 `source_digest.limitations` 写明，按 `other` 处理不扣分。

在 `ingest-review-bundle.md` 的 Source-type 字段要求段追加以下**必提 block_type 清单**，缺任一类 QA 必须报 error：

```markdown
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
```

实施要点：

**证据密度的三级降级**（应对"原文对某类内容只有定性描述、无可引用数字或事实"的场景，避免强制规则反而逼 LLM 编造）：

| 情况 | block_type | atomic_facts | ib 字段 | 下游影响 |
|---|---|---|---|---|
| **A - 类别充分**（默认路径） | 存在 | ≥ 1 条，每条有 evidence_quote | `evidence_strength ∈ {high, medium_high, medium}` | 正常参与 claim / auto_apply |
| **B - 类别存在但事实稀疏** | 存在 | 允许 `[]` | `evidence_strength ≤ medium_low`；必填 `evidence_sparse: true`；必填 `sparse_reason`（≤60 字，说明稀疏的原文依据，如"原文仅第 X 段一句定性描述，无具体数据"）；`summary` 必须直接改写该段原文；`source_page_range` 必填 | 基于该 ib 的 claim 自动 `confidence ≤ medium`、`evidence_basis: "summary_only"`；无论 confidence 如何**均不走 auto_apply** |
| **C - 类别缺失** | 不存在 | N/A | N/A | 必须在 `source_digest.limitations` 写明"原文未涉及 {block_type}"；QA 将该类从必检集中移除 |

**量化类的特例**：`quant_catalyst` / `demand_driver` / `asset_quality_or_spread` / `cycle_position` / `supply_pipeline` 这 5 类本应含量化数字的 block_type，走 B 路径时的门槛更严——`sparse_reason` 必须明确说"原文此类证据仅为定性表述"，且 `evidence_strength` 被强制为 `low`（不是 `medium_low`），防止被滥用来绕过量化要求。

**通用正则**（A 路径下 `quant_catalyst` 的量化校验）：`\d+(\.\d+)?\s*(%|倍|次|秒|毫秒|天|年|公里|吨|亿|万|元|美元|港币|ppt|bps|BP)`；领域单位扩展 `MeV|keV|T|K|°C|MW|GW|mAh|nm`。

**防滥用约束**：单份 bundle 中走 B 路径的 ib 不得超过必提清单的 1/3（9 类中最多 3 类稀疏）。超过即判定为报告本身证据密度不足，`source_digest.evidence_strength` 必须降到 `low`，`synthesis.one_sentence` 必须加保守限定词。

**QA 校验算法**：`_check_required_block_types(bundle, source_type, industry_archetype)` — 先取通用清单，再按 archetype 取并集；对每类依次判定 A/B/C 分级：
- A：正常通过
- B：校验 `evidence_sparse / sparse_reason / summary / source_page_range` 四字段齐全，且派生出的 claim 确实标记了 `evidence_basis`
- C：校验 `limitations` 字段含对应说明
- 同时跑滥用阈值检查（B 路径 ≤ 必提类 1/3）
- 校验在 `scripts/ingest_qa.py review-bundle` 里新增函数 `_check_required_block_types(bundle, source_type)`

**验收**：
- 对历史 `核聚变.pdf` bundle 重跑 QA，报缺少 `physics_foundation` / `policy_environment` / `alternative_route`（因为当前 bundle 确实漏了这三类）
- 对新 bundle ingest，这三类被补上后覆盖率提升可被 52 点对照矩阵量化（> 85%）

---

#### P0.2 — MinerU 输入层的单位字典与笔误预警

**目标**：在 LLM 读到 full-clean.md 之前就把可疑单位/数字标出，阻止 `11m² → fact-007` 这种 OCR 笔误传播链。

**改动文件**：
- 新建 `scripts/validate_mineru.py`
- `scripts/mineru_ingest.py` — 调用 `validate_mineru` 并把结果写到输出 JSON
- `docs/prompts/ingest-review-bundle.md` — 加一条规则："如果输入附带 `suspicious_tokens`，涉及这些 token 的 fact 必须在 `reviewer_notes` 写明"

**具体内容**：

`scripts/validate_mineru.py` 扫描 `full-clean.md`，产出 `suspicious_tokens.json`，位于同目录。检测规则分两组：**通用规则**对所有研报都跑，**领域规则**按检测到的关键词或用户提供的 archetype 选择性启用。

```python
# 第 1 组：通用规则（跑所有研报）
COMMON_PATTERNS = [
    # 金额单位混用：同一段里 "万亿" 与 "亿" / "亿元" 与 "万元" 相邻出现易引歧义
    (r'(\d+(?:\.\d+)?)\s*万亿\s*(吨|立方米|美元|元|人民币)?', 'scale_wanyi_check', '万亿量级需核对'),
    (r'(\d+(?:\.\d+)?)\s*(亿|万|千|百)(?!元|美元|港币|欧元|股|户|人|套|辆|辆次|吨|平方|人次|小时|天|次)', 'magnitude_no_unit', '数量级后缺单位'),
    # 百分比异常：同段出现 "80%" 和 "0.8" 同指一件事时易混
    (r'(0\.\d{1,3})\s*(增长|下降|提升|下滑|提高)', 'decimal_possibly_percent', '小数后接"增长"语义模糊，可能是 % 被吞'),
    # 6 位以上数字无单位
    (r'(\d{6,})(?!\s*[a-zA-Zµμ元%度吨亿万平方])', 'large_number_no_unit', '6 位以上数字无单位'),
    # 年份异常（非预期未来年份，可能是"20 25"被 OCR 分开或"2026 年"误识为"2036 年"）
    (r'(20[4-9][0-9])\s*年', 'year_far_future_check', '40 年后的年份需区分"长期预测"vs OCR 错'),
    # 日期混乱（月份 > 12 或日 > 31）
    (r'(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', 'date_sanity', '校验月/日合法性'),
]

# 第 2 组：领域规则（按 industry_archetype 或文本关键词启用）
DOMAIN_PATTERNS = {
    "technology_driven": [
        (r'(\d+(?:\.\d+)?)\s*m²', 'unit_possible_m3', '科技文档中 m² 多为 m³ OCR 错'),
        (r'(\d{5,})\s*K\b', 'temperature_magnitude_k', '温度 5 位数以上需核对 K vs °C'),
        (r'(\d+(?:\.\d+)?)\s*(T|GHz|MHz|nm)\b', 'spec_unit_check', '物理量单位需核对是否被 OCR 改写'),
    ],
    "financial": [
        (r'(\d+(?:\.\d+)?)\s*(bps|BP|个基点)', 'bps_check', '基点单位易与百分点混淆'),
        (r'(\d+(?:\.\d+)?)\s*%\s*(同比|环比)\s*(\d+(?:\.\d+)?)\s*%', 'yoy_qoq_both', '同比环比同时出现需核对口径'),
    ],
    "real_asset": [
        (r'(\d+(?:\.\d+)?)\s*(亩|㎡|平方米|平米)', 'area_unit_check', '面积单位混用（亩 vs 平）需核对'),
    ],
    "cyclical": [
        (r'(\d+(?:\.\d+)?)\s*(万吨|亿吨)', 'tonnage_scale', '吨数量级需核对'),
    ],
    # consumer_driven / other: 暂无特化规则，只跑通用
}
```

检测流程：
1. 先跑 `COMMON_PATTERNS`
2. 再根据 `industry_archetype`（由 mineru_ingest.py 从用户输入或封面关键词推断，默认 `other` 不跑领域规则）跑对应 `DOMAIN_PATTERNS[archetype]`
3. 关键词 fallback：若文中 `"超导"|"等离子"|"制程"|"激光"|"量子"` 等科技关键词命中 ≥ 2 次，即使 archetype 未定也启用 `technology_driven` 规则

输出格式：
```json
{
  "source_path": "path/to/full-clean.md",
  "scan_at": "2026-05-05T...",
  "flags": [
    {
      "line": 742,
      "snippet": "...等离子体体积只有 11m²...",
      "token": "11m²",
      "flag_type": "unit_possible_m3",
      "hint": "科技文档中 m² 多为 m³ OCR 错"
    }
  ]
}
```

Bundle prompt 新增规则（加到 `docs/prompts/ingest-review-bundle.md` 硬约束段）：

```markdown
24. 如果输入附带 `suspicious_tokens.json`，凡 `atomic_facts[*].evidence_quote`
    中包含 flagged token 的 fact，必须在 `fact.reviewer_notes` 写明
    "原文此处存在 {flag_type} 标记：{hint}"；fact 的 confidence 不得高于 medium。
```

bundle schema 需要新增 `atomic_fact.reviewer_notes` 字段（见 P1.1）。

**验收**：
- 对 `核聚变.pdf-9314b977.../full-clean.md` 运行 `validate_mineru`，必须至少识别出 1 处 `11m²` 的 `unit_possible_m3` flag
- 新 ingest 产出的 bundle 里，相关 fact 的 reviewer_notes 非空

---

#### P0.3 — Auto-apply 对 refutes / risk 强制 pending review

**目标**：反向观点和风险类 claim 不能因为 confidence=high 就被静默入库。

**改动文件**：
- `scripts/ingest_match.py`

**具体内容**：

当前逻辑是 `confidence == "high"` → `auto_apply`，其他 → `pending_review`。新增前置规则：

```python
def _decide_route(candidate):
    # 前置：风险类或反驳类必须人工确认
    if candidate.get("claim_type") == "risk":
        return "pending_review", "risk_class_forced_review"
    if candidate.get("direction_on_source") == "refutes":
        return "pending_review", "refutes_class_forced_review"
    # 前置：稀疏派生的 claim 必须人工确认（配合 P0.1 的 B 路径）
    if candidate.get("evidence_basis") == "summary_only":
        return "pending_review", "summary_only_forced_review"
    # 原有逻辑
    if candidate.get("confidence") == "high":
        return "auto_apply", "high_confidence"
    return "pending_review", "low_or_medium_confidence"
```

**验收**：
- 对历史 `核聚变.pdf` bundle 重跑 ingest_match，`cc-007`（合锻估值批判，`direction_on_source=refutes`）必须落到 pending_review 而非 auto_apply
- 文档：在 `_ingest-common.md` 的 Step 7 下加一行"auto_apply 排除 risk 和 refutes 类"

---

#### P0.4 — MinerU 标题层次重建（H1 拍扁 → H1/H2/H3）

**目标**：MinerU 当前把所有标题输出为 `# `（72 个平铺 H1），丢失了章节 H2/H3 嵌套关系。LLM 拿到平铺标题时，fact-to-ib 归属错误率升高（无法区分"核聚变优势显著"是第 1 章的子节，还是第 3 章产业链下的子节）。本任务是**确定性预处理**，0 LLM token 成本。

**改动文件**：
- 新建 `scripts/rebuild_heading_levels.py`
- `scripts/mineru_ingest.py` — 在 `clean_mineru` 之后、生成 pointer JSON 之前调用此脚本
- `scripts/ingest_qa.py` — 新增校验：`full-clean.md` 中不得出现连续 5+ 个同级 H1（旧 MinerU 产物的特征信号）

**输入**：`full-clean.md`
**输出**：同路径的 `full-clean.md`（原地改写，或写到 `full-clean-leveled.md` 由下游 pointer JSON 引用）

**算法**（三层信号逐级降级，不依赖字体大小）：

```
Signal 1 — TOC 锚点（最强，覆盖 ~60-80% 的券商/行业研报）
  提取 "# 目录" 到 "# 图表目录"（或 "# 目录" 后连续 5+ 条带页码的标题行）之间的条目
  对每条 TOC 条目解析：章节名 + 起始页码（正则: (.+?)[.\s]{2,}\s*\.?\s*(\d+)$）
  将 TOC 章节名与正文标题做归一化模糊匹配（去空格/标点后 prefix≥6 字符匹配）
  匹配成功 → H1（章节边界）
  两个 H1 之间的所有标题 → 按规则判定 H2 或 H3

Signal 2 — 显式编号（覆盖 ~10-20% 的报告，退化为一层）
  ^[一二三四五六七八九十][、.．] → H1（中文数字章节）
  ^（[一二三四五六七八九十]） → H2（中文括号编号子节）
  ^\d+\.\d+(\.\d+)?\s → H3/H4（按点数深度）
  ^\d+[、.．] → H2（数字编号节）
  此信号与 TOC 锚点冲突时，TOC 锚点优先

Signal 3 — 模板/内容模式（兜底，覆盖券商固定模板 + 推荐标的段落）
  标题 ∈ {支撑评级的要点, 估值, 评级面临的主要风险, 盈利预测及投资建议} → H3
  标题 ∈ {投资建议, 风险提示}（且不在 TOC 章节表里）→ H2
  标题 ∈ 推荐标的公司名（从 company_candidates 或简单规则：2-4 字、不含谓语动词）→ H2
  标题紧接 H2 公司名后、且匹配模板模式 → H3
  标题 ∈ {披露声明, 评级体系说明, 风险提示及免责声明, 相关关联机构} → 跳过（附录，不参与层级）
```

**特殊处理**：
- 封面区（第一个正文章节标题之前的所有标题：评级、标题、副标题、目录）→ 全部跳过，不产出层级标记（或统一标记为 `<!-- meta -->` HTML 注释保留原文）
- 连续无层级信号的标题（如连续 5 个 H2 中间没有明显的父 H1）→ warn，不强行编造层级
- TOC 缺失的报告（如 transcript、简短点评）→ 全部退回 Signal 2 + Signal 3

**QA 校验**（`scripts/ingest_qa.py` 新增 `_check_heading_levels`）：
- 全文中 `^# ` 开头的行数不得超过总标题行数的 30%（即 70%+ 的标题应该被降到 H2/H3 或跳过）
- 不得出现连续 5+ 个同级 H1 在正文区
- 必须存在 ≥ 1 个 H2（否则层级重建基本没生效）

**验收**：
- 对 `核聚变.pdf` 的 `full-clean.md` 运行脚本，5 个 TOC 锚点章节正确识别为 H1
- 各章节下的子节（如"核聚变优势显著"/"磁约束是实现聚变能开发..."）降为 H2
- 产业链子节（"第一壁和第一壁材料"/"偏滤器和偏滤器材料"/"高温超导带材和高温超导磁体"）降为 H2
- 推荐标的区域：公司名 H2，"支撑评级的要点/估值/评级面临的主要风险" H3
- 附录（披露声明/评级体系/关联机构）正确跳过
- QA 通过（H1 占比 < 30%）

**不做**：
- 不依赖 layout.json 的字体大小（MinerU 当前版本的 title block 未暴露 font_size 字段）
- 不引入 LLM（确定性脚本）

---

### Phase 1 — Bundle schema 扩容（为消费层和对齐层铺路）

#### P1.1 — Schema 加 5 个新字段

**目标**：给后续消费层/对齐层铺必要字段，保持向后兼容。

**改动文件**：
- `docs/prompts/ingest-review-bundle.md` — 更新 JSON schema 片段、硬约束
- `scripts/ingest_qa.py` — 更新字段校验
- 新文档 `docs/architecture/bundle-schema-v2-phase2.md` — 记录新字段（可从本计划复制）

**新增字段**：

```yaml
# ib 层
insight_blocks[*].narrative_priority:
  type: integer 1-5
  required: true
  meaning: |
    叙事呈现顺序，决定 INSIGHTS.md 和 narrative .md 中该 ib 的展开位置。
    5 级是"叙事位置"的抽象，每个 source_type 对应的具体含义不同：

    industry_report:
      1 = 行业定位 / 当前阶段
      2 = 核心催化剂 / 为什么现在
      3 = 主导范式与竞争 / 产业链分析
      4 = 公司敞口 / 推荐标的
      5 = 风险与边界

    sell_side_report:
      1 = 公司定位 / 主营业务
      2 = 本次报告核心判断 / 投资要点
      3 = 竞争力分析 / 护城河
      4 = 盈利预测 / 估值
      5 = 风险

    annual_report / quarterly_report:
      1 = 公司主业定位
      2 = 本期经营亮点 / 财务进展
      3 = 业务分部 / 业绩驱动分析
      4 = 管理层展望 / 资本开支 / 指引
      5 = 风险与治理

    transcript:
      1 = 会议背景 / 发言人
      2 = 核心观点 / 对当前形势判断
      3 = 关键问答
      4 = 前瞻性内容（指引、计划、展望）
      5 = 风险或保留意见

insight_blocks[*].transition_hint:
  type: enum [therefore, however, further, specifically, but_note, meanwhile]
  required: false
  meaning: 与前一个 narrative_priority 相同或相邻 ib 的逻辑连接关系

# claim 层
claim_candidates[*].investment_implication:
  type: string (最多 150 字)
  required: true
  meaning: |
    把 claim_text 翻译为可直接写入叙事段落结尾的投资含义表达。
    不是复述 claim_text，而是说"这条 claim 对投资决策意味着什么"。
    示例：
      claim_text: "磁体占比最大（24.9%），是 A 股金额敞口最集中的环节"
      investment_implication: "超导磁体供应商（如西部超导）在产业链价值量分配中
        拥有最高的金额敞口，磁体业务收入增长弹性最大。"

# fact 层
atomic_facts[*].reviewer_notes:
  type: string
  required: false
  meaning: |
    潜在问题标注，由 P0.2 的 suspicious_tokens 机制或 LLM 自我审视触发。
    示例："原文此处存在 unit_possible_m3 标记：科技文档中 m² 多为 m³ OCR 错"

# ib 层（稀疏降级，配合 P0.1 的 B 路径）
insight_blocks[*].evidence_sparse:
  type: boolean
  required: false（默认 false）
  meaning: 标记该 ib 虽存在但原文证据稀疏（无可独立引用的原子事实）

insight_blocks[*].sparse_reason:
  type: string (≤60 字)
  required: 当 evidence_sparse=true 时必填
  meaning: 稀疏的原文依据说明，如"原文仅第 3 节一句定性表述，无具体数据"

# claim 层（稀疏派生标记）
claim_candidates[*].evidence_basis:
  type: enum [full_fact_chain, summary_only]
  required: true（默认 full_fact_chain）
  meaning: |
    full_fact_chain：claim 由含 evidence_quote 的 atomic_facts 支撑
    summary_only：claim 基于 evidence_sparse=true 的 ib 的 summary，无独立事实支撑
    summary_only 的 claim 在 ingest_match 中强制走 pending_review，无论 confidence

# bundle 顶层
narrative_arc:
  type: array
  required: false（optional，单篇 bundle 可产 1-2 条）
  schema:
    arc_id: string (如 "arc-001")
    arc_type: enum [
      # 通用（任何 source_type 都可用）
      investment_thesis, risk_scenario,
      # industry_report 常见
      technology_shift, competitive_reshuffling, demand_cycle, consumption_upgrade,
      supply_restructuring, regulatory_shift,
      # sell_side_report 常见
      earnings_upgrade, earnings_downgrade, rating_initiation, thesis_refresh,
      # annual/quarterly_report 常见
      business_progress, earnings_review, strategic_pivot, guidance_update,
      # transcript
      outlook_statement, qa_insights
    ]
    title: string (≤40 字)
    sections:
      - section_name: string
        block_ids: [ib-xxx, ...]
  meaning: 整篇报告的叙事结构骨架，消费层的 INSIGHTS.md 合成依赖此字段。
          选择 arc_type 不局限于 source_type 默认的类型，以原文叙事气质为准。
```

**硬约束（加到 prompt）**：
- 25. 每个 insight_block 必须有 `narrative_priority` 值（1-5），用于下游叙事排序。
- 26. 每条 claim 必须有 `investment_implication`（≤150 字），这是 claim 的投资含义翻译，不是 claim_text 的复述。
- 27. bundle 顶层可产 `narrative_arc`（1-2 条），用于描述整篇报告的叙事骨架。

**向后兼容**：
- `ingest_qa` 对老 bundle（无新字段）只 warn 不 error
- `narrative_propose.py` 兼容缺字段的旧 bundle（缺 `narrative_priority` 时退回按 id 排序）

**验收**：
- 新 ingest 产出的 bundle 5 个字段齐全
- 老 bundle 重跑 QA 只 warn 不 fail

---

#### P1.2 — 无新字段 LLM 成本提升说明（预算锚）

**目标**：本阶段不拆 prompt 为 Pass 1a+1b，仍维持单次 LLM 调用，但 prompt 因新字段变长。

**改动文件**：无（只是预算说明，写入本计划作为后续决策锚）。

**说明**：
- 单次 ingest LLM tokens 预期从 ~30k 增至 ~38k（+25%），因为：
  - 9 类 block_type 清单本身约 800 tokens
  - investment_implication 字段要求 LLM 额外写 12 × 150 = 1800 tokens
  - narrative_arc + transition_hint 的产出约 800 tokens
- 若后续实测产出质量不稳定（LLM 顾此失彼），再推 Pass 1a+1b 拆分（暂不列入本计划）

---

### Phase 2 — 消费层（让 bundle 对用户立即可用）

#### P2.1 — INSIGHTS.md 合成层

**目标**：每次 ingest 自动产出一份 600-1200 字中文投研备忘录，让用户不用打开 bundle.json 也能决策。

**改动文件**：
- 新建 `scripts/synthesize_insights.py`
- `.claude/skills/ingest/workflows/_ingest-common.md` — 在 Step 12 后插入 Step 12.5「生成 INSIGHTS.md」

**输入**：
- `industries/{slug}/bundles/{sha8}.json`
- `data/claims/*.jsonl`（applied 后的相关 claim）
- `applied.jsonl`（当次 ingest 落地的 claim 列表）

**输出路径**：
- industry_report：`industries/{slug}/insights/{sha8}.md`
- sell_side_report：`industries/{slug}/insights/{sha8}.md`（按主要标的所在行业归档）
- annual/quarterly：`companies/{MARKET_TICKER}/insights/{sha8}.md`
- transcript：按发言主体落到对应公司或行业路径

**实现方式**：
- 脚本内通过 general-purpose subagent 调用 Sonnet（**用 subagent 而不是调 API**，符合项目 feedback 里的 LLM 工作流规则）
- subagent prompt（保存到 `docs/prompts/synthesize-insights.md`）要求按以下**骨架**产出；不同 source_type 激活不同小节，缺数据的段落不输出空标题。

```markdown
---
source_id: {bundle.source_digest.source_id}
source_type: {source_type}
industry_archetype: {industry_archetype 或 null}
synthesized_at: {ISO time}
bundle_sha8: {sha8}
narrative_arc: {arc_id 或 "none"}
---

# {简洁的标题，反映 narrative_arc.title 或 synthesis.one_sentence 核心}

## 一句话核心
> {来自 synthesis.one_sentence}

## 主要论证（按 narrative_priority 组织）

### {section_1 标题} — narrative_priority=1 的 ib 组
{150-250 字中文散文，包含相关 ib 的 summary + reasoning_chain + investment_implication}

### ... 后续 section（priority 2-5 依次展开，按 source_type 对应的 priority 含义）

## 标的或公司层摘要（按 source_type 展现）
- industry_report / sell_side_report：按 claim 的 company 维度聚合，每家公司一段；含 exposure_type、关键 fact、investment_implication
- annual_report / quarterly_report：按业务分部或财务口径分段，含 YoY/QoQ、管理层指引
- transcript：按发言人/议题分段

## 关键数字（证据锚点）

{最多 6 条来自 atomic_facts 的关键量化数据，含 fact_id 和 source_page 供回查}

## 不能由此报告得出的结论

{直接来自 synthesis.cannot_conclude}

## 前瞻性边界（按 source_type 条件显示）
- industry_report 且 archetype=technology_driven：列出 crossed=false 的 stage_gate + what_would_cross_it
- sell_side_report：列出 verification_questions（调研议题清单）
- annual_report / quarterly_report：列出管理层指引的关键假设及潜在不达成路径
- 不适用的 source_type 此段省略
```

**验收**：
- 对 `he-jubian` bundle 跑 `synthesize_insights.py`，产出 `industries/cn-nuclear-fusion/insights/ad983472.md`
- 产出文件 5 分钟阅读可替代当前 `mineru_summaries/he-jubian.md` 的 sonnet 摘要作决策依据
- 关键差异可审计：INSIGHTS.md 必须包含 `cannot_conclude` 和 `stage_gate`（这两项 sonnet 摘要缺失）

**不做**：
- 不替换现有 `narrative_propose` / `narrative_apply` 的 claim 镜像机制。INSIGHTS.md 是**补充产物**，不替换 narrative .md。两者目标不同：INSIGHTS.md 面向人，narrative .md 面向机械聚合。

---

#### P2.2 — Company Dashboard（多报告聚合视图）

**目标**：某公司被 N 次 ingest 后，自动产 `companies/{ticker}/dashboard.md`，展示多券商观点对比、claim 演变时间线、最新共识/分歧。

**改动文件**：
- 新建 `scripts/build_company_dashboard.py`
- `.claude/skills/ingest/workflows/_ingest-common.md` — Step 15 后增加"若 applied.jsonl 含 company scope，重建相关公司 dashboard"

**实现方式**：
- 对给定 ticker，从 `data/claims/companies.jsonl` 抓取所有相关 claim
- 按 `as_of` 排序，按 `dimension_hint` 分组
- 产 markdown dashboard

**输出模板**：

```markdown
---
ticker: SSE_600363
company: 联创光电
last_rebuilt: 2026-05-05
source_count: 3
---

# 联创光电（SSE 600363） — 多源观点面板

## 观点矩阵（按维度分组）

### moat
| source | as_of | claim | direction | confidence |
|---|---|---|---|---|
| 中银证券-2025-04-10 | 2025-04-10 | 联创超导持股 40%... | supports | high |
| 中信证券-2025-06-20 | 2025-06-20 | 高温超导磁体国内双寡头之一 | supports | medium_high |

### valuation
| source | as_of | claim | direction | confidence |
|---|---|---|---|---|
| ... |

## 时间线
2025-04-10 : 首次覆盖（中银）— 强于大市
2025-06-20 : 跟踪（中信）— 维持增持
...

## 共识与分歧
- **共识**：{至少 2 份研报一致的 claim}
- **分歧**：{不同研报间 direction 相反或 confidence 差 ≥ 2 档的 claim}

## 尚待验证（聚合各 bundle 的 verification_questions）
...

## Stage gate 触发追踪
- sg-004 (A 股公司聚变收入跨过 10% 门槛)：crossed=false，最近触及证据：{某 claim}
```

**验收**：
- 对已被 1 份以上研报覆盖的公司跑脚本，产生 dashboard.md
- Dashboard 必须包含"共识与分歧"段（即使 source_count=1 也要明确说"单一来源，未形成交叉验证"）

---

### Phase 3 — 对齐层（让 N 份 bundle 能真正融合）

#### P3.1 — Claim `anchor_hash` 语义对齐机制

**目标**：不同模型（Opus/Qwen）或不同 run 对同一份研报产出的 claim 能通过 anchor 合并，而不是因为 `cc-001` 编号一致就盲目当同一条（实测相似度 <0.15）。

**改动文件**：
- `docs/prompts/ingest-review-bundle.md` — 加新硬约束
- `scripts/ingest_qa.py` — 校验 anchor_hash 存在且格式正确
- `scripts/ingest_match.py` — 在 `top_matches` 之上加 anchor_match

**新字段**：

```yaml
claim_candidates[*].anchor_hash:
  type: string (16 hex chars)
  required: true
  compute: |
    hash_input = f"{scope_type}|{scope_ref}|{dimension_hint}|{claim_type}|{semantic_nucleus}"
    anchor_hash = sha256(hash_input).hexdigest()[:16]
  where:
    semantic_nucleus: |
      claim_text 去停用词后的核心名词+动词组合（≤20 字）。
      LLM 在产 claim 时同时产 semantic_nucleus 字段，保证跨模型/跨 run 稳定
      （"磁体是 A 股金额敞口最集中环节" → "磁体 敞口 最集中"）。
```

同步增加 `claim_candidates[*].semantic_nucleus`（string，≤20 字）。

**匹配逻辑**（`ingest_match.py`）：

```python
def find_anchor_match(candidate, registry):
    target_anchor = candidate["anchor_hash"]
    for existing_claim in registry:
        if existing_claim.get("anchor_hash") == target_anchor:
            return existing_claim
    return None

# 决策树
def decide_match(candidate, registry):
    # 1. anchor match 优先（语义对齐）
    anchor_hit = find_anchor_match(candidate, registry)
    if anchor_hit:
        return "attach_by_anchor", anchor_hit["claim_id"]
    # 2. 退回当前的 top_matches（文本相似度）
    top = current_top_matches(candidate, registry)
    if top and top[0]["score"] > 0.75:
        return "attach_by_similarity", top[0]["claim_id"]
    # 3. 新建
    return "new", None
```

**验收**：
- 构造一个 synthetic 测试：用 Opus 和 Qwen 各 ingest 一次 `核聚变.pdf`，两份 bundle 的 `cc-004`（磁体敞口）anchor_hash 必须相同；`ingest_match` 在第二次运行时将其识别为 anchor_match 而非新 claim
- 相对的：对两份不同研报的"磁体"相关 claim，scope_ref 不同，anchor_hash 必须不同

---

#### P3.2 — Claim 时效 / 衰减机制

**目标**：claim 有 `as_of` 是记录时间戳，但没有自动衰减规则。实施后，过期 claim 自动降级、不再默认驱动 narrative。

**改动文件**：
- `data/claims/*.jsonl` schema 扩容（新增字段 optional，向后兼容）
- `scripts/narrative_propose.py` — 读 claim 时检查 age，过期则标记 `aged=true`
- 新建 `scripts/claim_decay_check.py` — 定期扫描并在 ClaimRegistry 的 audit 日志里记录状态变化

**新字段**（写入 `data/claims/*.jsonl` 每条记录）：

```yaml
decay_rule:
  type: object
  required: false（有默认规则表）
  schema:
    half_life_months: integer
    invalidated_by: [claim_id, ...]  # 指明哪些新 claim 会让这条失效

# 默认半衰周期（按 claim_type）
DEFAULT_HALF_LIFE = {
    "thesis": 24,       # 大主张 2 年半衰
    "judgment": 12,     # 判断 1 年
    "risk": 6,          # 风险 6 个月（风险变化快）
    "gate_assessment": 12,
    "scenario": 18,
}

# 按 industry_archetype override（从 scope 的 industry 关联查得）
ARCHETYPE_MULTIPLIER = {
    "technology_driven":  0.75,  # 技术变化快，周期整体收紧（半导体/AI 类行业）
    "consumer_driven":    1.25,  # 消费品牌/渠道格局演变较慢
    "cyclical":           1.00,  # 周期行业按默认
    "financial":          1.00,
    "real_asset":         1.50,  # 地产/基建周期长
    "other":              1.00,
}

# 实际半衰 = DEFAULT_HALF_LIFE[claim_type] × ARCHETYPE_MULTIPLIER[archetype]
# scope=cross_cutting 时取 1.00
```

**衰减逻辑**（`scripts/claim_decay_check.py`）：

```python
def status_of(claim, today):
    half_life = claim.get("decay_rule", {}).get(
        "half_life_months",
        DEFAULT_HALF_LIFE.get(claim["claim_type"], 12)
    )
    age_months = (today - parse(claim["as_of"])).days / 30.44
    if claim.get("decay_rule", {}).get("invalidated_by"):
        return "invalidated"
    if age_months < half_life:
        return "fresh"
    if age_months < half_life * 2:
        return "aged"
    return "stale"
```

`narrative_propose.py` 增加过滤：
- `fresh` / `aged`：正常驱动 narrative
- `stale`：除非被新证据支持，否则从 narrative 中剔除，narrative frontmatter 的 `supported_by_claims` 也要同步移除
- `invalidated`：立即从 narrative 中移除

**验收**：
- 对 >1 年前的 claim 跑 `claim_decay_check.py`，正确标记为 `aged` 或 `stale`
- `narrative_propose` 对 `stale` claim 产出的提案里不再包含这条

---

#### P3.3 — Stage Gate Watcher

**目标**：每次 ingest 自动 diff 所有 `crossed=false` 的 stage gate，检查新 claim 是否触发。

**改动文件**：
- 新建 `scripts/check_stage_gates.py`
- `.claude/skills/ingest/workflows/_ingest-common.md` — Step 15 后增加 Step 16「stage gate diff」
- 新建 `data/stage_gate_alerts.jsonl`（alert 历史）

**实现方式**：

```python
def check_gates_after_ingest(bundle_sha8, registry_base):
    # 1. 聚合所有 industry/arena 的 stage_gates（从各 bundle 读，或从一个 stage_gates.jsonl 全局表读）
    all_gates = load_all_stage_gates(registry_base)
    uncrossed = [g for g in all_gates if not g["crossed"]]

    # 2. 拿本次 applied.jsonl 里的新 claim
    new_claims = load_applied_claims(bundle_sha8)

    # 3. 对每个 uncrossed gate，LLM 判断是否被触发
    #    （通过 subagent 调用 Sonnet，输入 gate.what_would_cross_it + new_claims）
    alerts = []
    for gate in uncrossed:
        triggered = subagent_check_gate_triggered(gate, new_claims)
        if triggered:
            alerts.append({
                "gate_id": gate["id"],
                "gate_title": gate["title"],
                "triggered_by_claims": [c["claim_id"] for c in triggered],
                "triggered_at": now(),
                "requires_human_review": True,
            })

    # 4. 写 alerts 到 data/stage_gate_alerts.jsonl
    write_alerts(alerts)
    return alerts
```

**验收**：
- 构造假想场景：REBCO 产能扩到 10000 km/年的一条 claim，ingest 后脚本应 alert `sg-003`（REBCO 带材从 3000 km/年扩张到万公里级）
- alert 必须要求人工审核，不能自动翻转 gate.crossed=true（防止 LLM 误判把 gate 翻掉）

---

## 4. 阶段依赖与执行顺序

```
P0.1 强制 block_type 清单      ─┐
P0.2 suspicious_tokens 预警    ─┤
P0.3 refutes/risk 走 pending   ─┼── 可并行，互不依赖
P0.4 标题层次重建              ─┘
                                  ↓（完成后进入 P1）
P1.1 Schema 加 5 字段 ─── 依赖 P0.2（reviewer_notes 字段是 P0.2 的输出目的地）
                                  ↓
P2.1 INSIGHTS.md 合成 ─── 依赖 P1.1（narrative_arc / transition_hint / investment_implication 是合成的输入）
P2.2 Company Dashboard ── 依赖 P1.1（不必严格依赖，但 investment_implication 让 dashboard 质量更高）
                                  ↓
P3.1 anchor_hash        ─┐
P3.2 decay_rule         ─┼── 可并行，三者互不依赖
P3.3 stage_gate_watcher ─┘        （但 P3.3 从 P2 之后起价值更高）
```

推荐执行批次：
- **Batch 1（1-2 天）**：P0.1 + P0.2 + P0.3 + P0.4，立即运行一轮 ingest 回归验证
- **Batch 2（2-3 天）**：P1.1，重 ingest 一份研报验证新字段齐全
- **Batch 3（3-5 天）**：P2.1 + P2.2，产出首份 INSIGHTS.md 和 dashboard
- **Batch 4（5-7 天）**：P3.1 + P3.2 + P3.3，需要至少 2 份研报做聚合验证

---

## 5. 不做什么（硬排除项）

为防止 sonnet 实施时误延展，以下明确排除。标注 **[→ §8]** 的项是**本期不做但已评估**，设计、触发条件、成本在 §8 备案；未标注的是永久排除或超出项目范围。

1. **不追求单篇覆盖率 > 85%**。P0.1 做完 QA 过了就停，不要继续往 prompt 里加提取规则。（永久排除，依据 §1.2 曲线原理）
2. **不拆 ingest prompt 为 Pass 1a + 1b**。**[→ §8.1]**
3. **不重写 ClaimRegistry 的 jsonl 结构**。只加字段，不改已有字段名或含义。
4. **不重写 narrative .md 的机械拼接机制**。P2.1 的 INSIGHTS.md 是**补充**，不替换 `narrative_propose` / `narrative_apply`。**[→ §8.2]**
5. **不做前端/Web UI**。所有产出都是 .md / .json / .jsonl。`app/routes/` 不改。
6. **不做图片/图表 OCR 二次处理**。P0.2 的 suspicious_tokens 只扫 full-clean.md 文本，不触 images/。
7. **不做自动翻转 stage_gate.crossed**。P3.3 只产 alert，最终决策人工审核。
8. **不做跨语言（英文研报）适配**。**[→ §8.4]**
9. **不新增 source_type**（比如 esg_report / thematic_note 等）。维持当前 industry_report / company_report / annual_report / quarterly_report / sell_side_report / transcript。
10. **不做 claim 的自动 merge**。即使 P3.1 的 anchor_match 命中，也只标记为 `attach` 候选送 pending_review，不自动合并。
11. **不合并现有 5 套枚举**（block_type / dimension_hint / claim_type / exposure_type / gate_type）。**[→ §8.3]**

---

## 6. 整体验收

迭代完成的最终状态需满足以下全部标准：

### 6.1 抽取层（P0 + P1.1 完成后）
- [ ] 重新 ingest `核聚变.pdf`，新 bundle 的 `block_type` 清单覆盖 9 类 industry_report 必提类别
- [ ] 新 bundle 的 5 个新字段（narrative_priority / transition_hint / investment_implication / reviewer_notes / narrative_arc）齐全
- [ ] 对原有 `11m²` 笔误位置，`fact-007.reviewer_notes` 非空
- [ ] `auto_apply.json` 不再含 `direction_on_source=refutes` 或 `claim_type=risk` 的 claim
- [ ] `full-clean.md` 正文区 H1 占比 < 30%，chapter→section 嵌套关系正确
- [ ] 对 52 点关键信息矩阵重新统计，bundle 覆盖率 ≥ 85%（当前 73%）

### 6.2 消费层（P2 完成后）
- [ ] 每次 ingest 产出 `industries/{slug}/insights/{sha8}.md`（或对应公司路径）
- [ ] INSIGHTS.md 含 `cannot_conclude` 和 `stage_gate` 两段（sonnet 摘要无此内容，这是 bundle 独有价值的兑现点）
- [ ] 对联创光电（或任一被 ≥ 1 份研报覆盖的公司）运行 dashboard 脚本，产出 dashboard.md
- [ ] Dashboard 包含"共识与分歧"段

### 6.3 对齐层（P3 完成后）
- [ ] `anchor_hash` 在新 bundle 中 100% 覆盖
- [ ] Opus/Qwen 重复 ingest 同一份研报，`ingest_match` 通过 anchor_match 识别重复率 ≥ 80%（当前 0%）
- [ ] `claim_decay_check.py` 能对历史 claim 正确标记 fresh/aged/stale
- [ ] `check_stage_gates.py` 在 alert 触发时写入 `data/stage_gate_alerts.jsonl` 并要求人工审核

### 6.4 整体指标
- 单次 ingest LLM token 消耗增加控制在 +40% 以内（P1.1 后约 +25%，P2.1 的 INSIGHTS 合成额外约 +15%）
- Bundle 用户可用性：用户无需打开 bundle.json 即可从 INSIGHTS.md 获得决策依据
- Bundle 融合能力：对 3 份不同研报覆盖同一公司时，Company Dashboard 能自动识别观点共识与分歧

### 6.5 通用性回归测试（强制）

**任何单一样本（含 `核聚变.pdf`）验证通过不足以结项**。P0 / P1 完成后，必须至少跑一次覆盖以下 4 个行业大类的回归：

| 行业大类 | 建议样本 | 验证目标 |
|---|---|---|
| technology_driven | 已有的核聚变或其他科技类研报 | 9 类 block_type（通用 6 + tech 扩展 3）全部齐全 |
| consumer_driven | 宠物 / 白酒 / 美妆行业研报（industries 下已有 `cn-pet-industry`）| 9 类 block_type（通用 6 + consumer 扩展 3）全部齐全，`physics_foundation` 等科技类命名不应出现 |
| sell_side_report | 任一最近 sell-side 点评 | 5 类必提 block_type（company_snapshot / financial_profile / competitive_moat / valuation / risk）齐全，不会因为缺物理基础被判 fail |
| annual_report | 任一已 ingest 年报 | 4 类必提 block_type 齐全，INSIGHTS.md 的 priority 定义切到年报版（经营亮点/业务分部/管理层展望） |

回归未通过的 source_type 不得声称本计划完成。回归输出写入 `data/ingest_regression_report.md`。

---

## 8. Deferred — 已评估但本期不做

本段记录**讨论过、有理由不做、但保留未来启用路径**的项。每项给出：本期决定 / 决策理由 / 触发条件 / 若启用的设计草案 / 预估成本 - 收益。这是决策档案，不是 TODO。

---

### 8.1 Pass 1a + 1b — 拆分 ingest prompt 为两次 LLM 调用

**本期决定**：不做，维持当前单次 LLM 调用产 bundle。

**决策理由**：
1. P1.1 给单次 prompt 加了 5 个新字段（narrative_priority / transition_hint / investment_implication / reviewer_notes / narrative_arc），单次调用负荷已经显著增加。先观察 LLM 能否在单次调用里稳定产出新字段，再决定是否拆分。
2. 拆分带来 +30% token 成本、+1 步工作流复杂度，应在确实看到"单次产出质量不稳定"的证据之后再上，不宜未卜先投。
3. P0.1 的强制 block_type 清单已经解决了最主要的覆盖率问题（73% → ~85%）。Pass 1a+1b 的主要收益是跨模型一致性（SIM <0.15 → 提升），这个问题被 P3.1 的 `anchor_hash` 部分兜底。

**触发条件**（出现以下任一即启用）：
- P1.1 完成后，对同一份研报连续 3 次 ingest，`insight_blocks` 数量或 `block_type` 集合差异 > 20%
- 新字段 `investment_implication` / `narrative_arc` 在连续 5 次 ingest 中出现"字段存在但内容空洞/无信息"的比例 > 30%
- Sonnet 主 agent 在单次 prompt 下报告 "context 压力大，字段顾此失彼"
- P3.1 `anchor_hash` 实施后跨模型/跨 run 合并率仍 < 60%

**若启用的设计草案**：

```
Pass 1a — 骨架提取（Sonnet，~18k tokens）
  输入：full-clean.md + suspicious_tokens.json
  产出：source_digest + insight_blocks + atomic_facts
  强制：P0.1 的 block_type 清单 + A/B/C 三级降级

Pass 1b — 投资含义织入（Sonnet，~12k tokens）
  输入：Pass 1a 的中间 bundle
  产出：claim_candidates + stage_gates + block_relations
       + synthesis + schema_fit_review + narrative_arc
       + ib.narrative_priority + ib.transition_hint
       + claim.investment_implication + claim.anchor_hash
  强制：claim 数量 ≤ ib 数量 × 1.5；每个 claim 必须有 anchor_hash
```

**预估 Δ**：
- 成本：LLM tokens 从单次 ~38k（P1.1 后）增至 2 次共 ~50k，约 +30%
- 工作流：`_ingest-common.md` 的 Step 2 拆为 2a + 2b
- 质量：跨 run 一致性（SIM）预期从 <0.15 提升到 >0.6；covariate 字段（priority/implication）空洞率预期从 30% 降至 <10%

**预计评估节点**：P1.1 + P2.1 完成并跑完 §6.5 的 4 个行业大类回归后，看单次 prompt 的实际稳定性表现，再做决策。

---

### 8.2 Narrative .md 从机械拼接升级为 LLM 合成

**本期决定**：不做。P2.1 的 INSIGHTS.md 作为**补充产物**，`narrative_propose` / `narrative_apply` 保持机械拼接不变。

**决策理由**：
1. 面向人阅读的需求由 INSIGHTS.md 承担；narrative .md 的核心价值是作为 claim registry 的镜像，供跨报告聚合脚本机械遍历。两者目标不同，不应替换。
2. 替换 narrative_apply 为 LLM 合成会引入非确定性，对"相同 claim 产不同 narrative"这种噪声无法机械核对，损害聚合层的可审计性。
3. narrative .md 短期内是 Company Dashboard（P2.2）和 Stage Gate Watcher（P3.3）的上游，结构稳定比可读性重要。

**触发条件**：
- Company Dashboard（P2.2）和 Stage Gate Watcher（P3.3）稳定运行 3 个月
- 用户明确反馈"我要读 narrative .md 而不是 INSIGHTS.md"
- P2.1 的 INSIGHTS.md 不足以覆盖所有人读场景

**若启用的设计草案**：
- 新增 `scripts/narrative_synthesize.py`（与 `narrative_apply` 并列）
- `narrative_apply` 保留，产出 `*.raw.md`（机械拼接原版）
- `narrative_synthesize` 消费 `*.raw.md` + 相关 ib/fact，产 `*.md`（合成版）
- 聚合脚本统一读 `*.raw.md`（保证确定性），人读读 `*.md`

**预估 Δ**：
- 成本：每 `(scope, ref)` 一次 LLM 调用，典型一份研报 5-8 个 scope，+15k tokens
- 风险：双版本文件增加维护成本；需明确约定 "raw vs synth" 的 diverge 规则

---

### 8.3 枚举合并（5 套 → 2 套）

**本期决定**：不做，保留 `block_type` / `dimension_hint` / `claim_type` / `exposure_type` / `gate_type` 五套枚举并存。

**决策理由**：
1. 枚举合并是 schema 重构，风险大、影响 ClaimRegistry 所有历史数据、违反 §5 硬排除项 #3（不改 ClaimRegistry jsonl 结构）。
2. 5 套枚举的学习成本对用户是问题，但目前由 INSIGHTS.md 和 Company Dashboard 屏蔽（用户不直接看 jsonl）。
3. 合并后的 `entity_type` / `content_type` 表达力可能不足，会丢失 `gate_type` 的前瞻语义和 `exposure_type` 的合同语义。

**触发条件**：
- 未来若引入第 6 套枚举（真实出现扩展压力时再集中重构）
- 或用户直接操作 jsonl 的场景大量出现

**若启用的设计草案**：搁置，待触发后再设计。

---

### 8.4 跨语言（英文研报）适配

**本期决定**：不做，本计划聚焦中文 A 股研报场景。

**决策理由**：
1. 当前 MinerU 清洗规则、`suspicious_tokens` 正则、`institution_extraction` 模板均针对中文。
2. 英文研报（10-K / 20-F / 英文 sell-side）涉及不同的章节结构（Risk Factors / MD&A / Business）、不同的数字格式（万亿 vs trillion）、不同的机构枚举（Goldman / Morgan Stanley）。改造工作量大。
3. 已有的 `templates/us-10k.yaml` / `us-10q.yaml` / `us-industry.yaml` 是旧 preprocess 流程的模板，尚未在 MinerU 路径上验证。

**触发条件**：
- 用户 ingest 首份英文研报
- 美股持仓成为投资决策的主要来源

**若启用的设计草案**：
- `industry_archetype` 枚举不变
- 新增 `source_digest.language: "zh" | "en"`
- 通用 block_type 清单不变
- Suspicious tokens 正则新增英文组（billion vs million 混用、date format MM/DD/YYYY vs DD/MM/YYYY）
- INSIGHTS.md 模板新增英文版（面向英文研报用户；中文用户仍读中文 INSIGHTS.md）

**预估 Δ**：整体工作量约等于本计划 P0 + P0.2 + P2.1 重做一遍。

---

## 9. 参考资料

实施过程中如需上下文，以下文档为权威来源：

- `docs/architecture/00-overview.md` — 系统总览
- `docs/architecture/02-ingest-pipeline.md` — ingest pipeline 架构
- `docs/architecture/03-narrative-system.md` — narrative 系统
- `mineru_summaries/he-jubian-bundle-analysis.md` — Bundle vs LLM 摘要的详细对比（52 点覆盖矩阵）
- `mineru_summaries/he-jubian-compare.md` — 三模型摘要横向对比
- `/tmp/mineru-fusion-compare/QUALITY-DIFF.md` — MinerU vs preprocess 产出对比
- `/tmp/mineru-fusion-compare/QUALITY-DIFF-QWEN.md` — Opus vs Qwen 跨模型产出对比（证实跨模型 claim 相似度 <0.15 问题）

**上述参考资料全部取自核聚变（technology_driven）单一样本**。实施时以此为灵感来源，但所有规则必须对 5 个 `industry_archetype` × 5 个 `source_type` 的组合通用。若某规则只能用于特定大类，必须显式声明适用范围（如 P0.2 的 `DOMAIN_PATTERNS[technology_driven]`）。

实施前必读：
1. 本计划 §1.2 的覆盖率曲线原理。这是决定"什么该投入、什么不该投入"的最上位判断，违反此原则的任何延展（如继续推单篇覆盖率到 95%）都会降低系统整体价值。
2. 本计划 §6.5 的通用性回归测试。不得因为核聚变样本通过就声明本计划结项。

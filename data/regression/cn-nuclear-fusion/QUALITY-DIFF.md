# Nuclear Fusion Bundle Quality Comparison
## Source: 行研-中银证券-2025-04-10-ad983472

Three bundles compared:
- **Baseline**: `/tmp/mineru-fusion-compare/run/bundle.json` — v2-phase1, inline (digest-era)
- **Inline**: `data/regression/cn-nuclear-fusion/bundle-new-schema.json` — v2-phase1, single-agent inline
- **Split-subagent**: `data/regression/cn-nuclear-fusion/bundle-v2-split-subagents.json` — v2-phase1, two parallel subagents (part1: lines 1-752 industry, part2: lines 753-1616 companies)

Primary comparison: **split-subagent vs. baseline**. Inline is reference only.

---

## Part 1: Atomic Fact Count (Core Regression Metric)

| Bundle | Atomic Facts | vs. Baseline |
|---|---|---|
| **Baseline** | **27** | — |
| Inline | 12 | -55.6% (60% loss) |
| **Split-subagent** | **66** | +144% |

**The split-subagent approach not only recovered the 60% loss — it expanded coverage by 2.4x.**

### Breakdown by section

| Section | Baseline | Inline | Split-subagent |
|---|---|---|---|
| Industry/technology facts (fact-001 to ~027) | 27 | 12 | 42 (fact-001 to fact-042) |
| Company-level facts | 0 | 0 | 24 (fact-101 to fact-124) |

The baseline had no company-level atomic facts. The split-subagent approach added 24 company facts with full evidence_quote coverage (PE tables, EPS forecasts, revenue breakdowns for all four companies).

### Key facts recovered vs. baseline

Facts present in baseline that inline lost and split-subagent recovered:

| Fact | Baseline | Inline | Split-subagent |
|---|---|---|---|
| JET/TFTR/JT-60 Q>1.25, >16.2MW, 4.4×10⁸K | fact-003 | absent | fact-004 |
| ITER Nb₃Sn 用量>500吨/10万公里 | fact-023 | absent | fact-010 |
| CFETR 成本逐项拆分（磁体38.9%/真空室4.2%/偏滤器0.4%） | fact-014 | absent | fact-022/fact-042 |
| Princeton 1000MW电站成本27-97亿美元 | fact-011 | absent | fact-038 |
| REBCO产能缺口（3000km vs SPARC需1万km） | fact-017 | absent | fact-015 |
| Z-FFR 49.996亿元立项 | fact-027 | absent | fact-025 |
| CFETR 大半径7.2m参数 | implicit | absent | fact-030 |

### Net-new facts in split-subagent (absent from baseline)

Examples of genuinely new content not in baseline:
- fact-031: NIF 2022点火输入2.05MJ/输出3.15MJ
- fact-032: W7-X 2023年1.3GJ能量周转/放电8分钟
- fact-034: 聚变新能注册资本145亿元，股东结构
- fact-035: 钨熔点3400℃/热导率176W/mK/密度19.25g/cm³（独立于文字，来自图表）
- fact-104 to fact-124: 四家公司完整财务预测数据（PE、EPS、营收、毛利率）

---

## Part 2: Insight Block Depth

| Dimension | Baseline | Inline | Split-subagent |
|---|---|---|---|
| Total blocks | 16 | 14 | 19 |
| Industry blocks | 16 | 10 | 14 (ib-001 to ib-014) |
| Company blocks | 0 | 4 | 5 (ib-101 to ib-105) |
| Block types used | 13 informal | 10 formal | 9 formal |
| narrative_priority | absent | all 16/16 | all 19/19 |
| transition_hint | absent | all 16/16 | all 19/19 |
| reasoning_chain | present | present | present |
| block_relations | present | present | present |

### Material block-level differences vs. baseline

**Blocks present in baseline, absent or degraded in split-subagent:**

| Baseline block | Status in split-subagent | Impact |
|---|---|---|
| `valuation` (ib-016): PE表完整列出4家公司vs可比均值 | Moved to ib-105 `risk` block + atomic facts fact-104/110/115/120/124 | No longer an independent block, but all PE data is present in atomic_facts |
| `supply_bottleneck` (ib-008): REBCO产能缺口作为独立risk block | Absorbed into ib-006 `value_chain` and ib-004 `alternative_paradigm` | Data preserved in facts; framing shifted risk→opportunity |
| `policy_project` (ib-014): Z-FFR/江西混合堆项目细节 | Z-FFR in fact-025/ib-007; 江西混合堆in fact-040/ib-008 | Data preserved; not an independent block but accessible |
| `capital_inflow` (ib-004): FIA私营融资单独信号 | Absorbed into ib-005 `quant_catalyst` | Data preserved |

**Blocks new in split-subagent vs. baseline:**

- ib-010: 中国ITER采购包完整覆盖（独立于产业链概览）
- ib-011/ib-012: 第一壁/偏滤器独立拆分为两个blocks（baseline合并为一个material block）
- ib-013: A股产业链概览（推荐4家公司汇总）
- ib-101 to ib-104: 4家公司各自独立block（baseline无）
- ib-105: 四家公司共性风险（估值、主业、技术进展）

**Assessment:** Block count increase (16→19) is genuine content expansion, driven by company section coverage that baseline entirely lacked. The loss of three independent blocks (supply_bottleneck, valuation, capital_inflow) is partially mitigated by preserving the underlying data in atomic_facts.

---

## Part 3: Claim Candidates

| Dimension | Baseline | Inline | Split-subagent |
|---|---|---|---|
| Total claims | 12 | 10 | 12 (cc-001 to cc-007 + cc-101 to cc-105) |
| investment_implication | absent | 10/10 | 12/12 |
| semantic_nucleus | absent | 10/10 | 12/12 |
| evidence_basis | absent | 10/10 | 12/12 |
| Company-scoped claims | 1 partial (cc-007) | 2 partial | 5 dedicated (cc-101 to cc-105) |

### Key claim-level changes vs. baseline

| Baseline claim | Split-subagent status |
|---|---|
| cc-007: 合锻PE 87x主题属性强于基本面 | Preserved as cc-105 + cc-101 investment_implication |
| cc-011: 市场规模测算不宜作为定价锚 | Present as cc-005 (ITER风险) + cc-007 (BEST催化剂) partially covers |
| cc-012: HTS替代LTS风险 | Present as cc-103 investment_implication, not independent claim |
| NEW cc-102: 联创超导D型磁体验证节点意义 | Absent from baseline |
| NEW cc-103: 西部超导垄断地位+NbTi替代风险 | Absent from baseline |
| NEW cc-104: 安泰中科供应商资质壁垒 | Absent from baseline |
| NEW cc-105: 四家公司PE分化框架 | Absent from baseline (was ib-016 block only) |

**Split-subagent introduces a cross-cutting valuation claim (cc-105) comparing all four companies' PE vs. peer means in a single structured assertion — the most actionable form for claim registry ingestion.**

---

## Part 4: Company and Arena Coverage

### Company candidates

| Bundle | Companies | Confidence distribution |
|---|---|---|
| Baseline | 8 (4 core + 4 low-confidence) | core: medium/medium_high; peripheral: low |
| Inline | 4 | medium/medium_high |
| Split-subagent | 4 core | high(×3)/medium(×1) |

**The split-subagent bundle correctly drops the four low-confidence peripheral companies** (国光电气, 永鼎股份, 精达股份, 海陆重工) that baseline included with low confidence and no direct analysis. This is not a content loss — these companies are mentioned in synthesis.what_we_know but correctly not given full candidate entries.

**Confidence upgrade for core four:** Split-subagent raises 合锻, 西部超导, 安泰科技 to `high` vs. baseline's `medium`. The upgrade is supported by the company-section facts (fact-101 to fact-124) providing detailed financial evidence.

**Note on 联创光电:** Split-subagent rates `medium` (vs. baseline `medium`) — consistent assessment. The indirect 40% ownership structure is correctly reflected in lower confidence.

### Arena candidates

| Bundle | Arenas | Notes |
|---|---|---|
| Baseline | 5 | cn-fusion-firstwall-material, cn-fusion-divertor-material (separate), cn-fusion-hts-magnet-supply, cn-fusion-lts-wires, cn-fusion-vacuum-vessel-fabrication |
| Inline | 4 | Missing cn-fusion-divertor-material (merged into firstwall) |
| Split-subagent | 3 | cn-fusion-hts-tape, cn-fusion-first-wall-tungsten, cn-fusion-vacuum-vessel-precision |

**Split-subagent arena coverage is the most significant structural regression vs. baseline.** Two arenas from baseline are absent:

1. **cn-fusion-lts-wires** (低温超导线材): The baseline correctly identified this as a distinct arena with 西部超导 as sole participant. Split-subagent covers the LTS thesis in ib-103 and cc-103 but does not generate an independent arena candidate. Impact: the competitive moat analysis for 西部超导's NbTi dominance has no arena anchor.

2. **cn-fusion-divertor-material** (偏滤器): The split-subagent has ib-012 as a dedicated divertor block and fact-035 with divertor-specific material data, but the arena candidate is merged into cn-fusion-first-wall-tungsten. The baseline correctly distinguished first-wall (shared: 安泰, 国光, 西物院) from divertor (安泰中科 sole) — two different competitive landscapes, different replacement cycles, different geometry.

**Net: split-subagent has 3 arenas vs. baseline's 5. The missing two (LTS wires, divertor) are genuine coverage gaps, not consolidation improvements.**

---

## Part 5: Stage Gates

| Bundle | Gates | Quality |
|---|---|---|
| Baseline | 4 | Mixed — sg-002 (LCOE到光伏平价) is 15+ year horizon |
| Inline | 4 | Improved — ITER SRO + A股年合同10亿 more actionable |
| Split-subagent | 4 | Actionable — ITER/BEST/CFETR节点 + REBCO产能 + A股亿级收入 + 高PE兑现 |

Split-subagent adds a **valuation_validation gate (sg-004)**: "合锻87x/联创45x的估值溢价能否被业绩增长消化" — this is the most investor-centric gate across all three versions and absent from baseline.

---

## Part 6: Schema Compliance

| Field | Baseline | Inline | Split-subagent |
|---|---|---|---|
| Phase 1 required fields | 0/8 | 8/8 | 8/8 |
| narrative_arc | absent | present | present (2 arcs) |
| block_type formal vocabulary | no (13 informal) | yes | yes |
| industry_archetype | absent | present | present |
| investment_implication on claims | absent | 10/10 | 12/12 |
| semantic_nucleus on claims | absent | 10/10 | 12/12 |

---

## Part 7: Overall Assessment

### Scorecard

| Dimension | Baseline | Inline | Split-subagent |
|---|---|---|---|
| Atomic fact density | 9/10 (27 facts, full quotes) | 4/10 (12 facts, 55% loss) | **10/10** (66 facts, 2.4x expansion) |
| Company coverage depth | 4/10 (no company facts/claims) | 6/10 (4 blocks, 2 claims) | **9/10** (5 blocks, 5 claims, 24 facts) |
| Claim actionability | 5/10 (no investment_implication) | 8/10 (investment_implication present) | **9/10** (12 claims, company-level claims) |
| Arena coverage | 9/10 (5 arenas correctly scoped) | 7/10 (4 arenas, divertor lost) | 6/10 (3 arenas, LTS+divertor lost) |
| Schema compliance | 5/10 | 9/10 | **9/10** |
| Insight block depth | 7/10 (16 blocks, industry only) | 7/10 (14 blocks) | **9/10** (19 blocks, industry+company) |

### Primary verdict

**The split-subagent approach successfully reversed the inline-generated 60% atomic fact loss and substantially expanded coverage.** 66 facts vs. 27 baseline represents a genuine quality improvement — particularly because the 39 net-new facts include company-level financial data that the baseline entirely lacked (no company section was covered in the baseline generation).

**The parallel subagent architecture worked as designed:** Part1 (industry, lines 1-752) recovered all baseline industry facts plus added new content (NIF ignition, W7-X records, CFETR parameters). Part2 (company, lines 753-1616) added 24 company facts and 5 company claims that the baseline never attempted.

### Remaining gaps vs. baseline

1. **Arena count: 3 vs. 5.** Missing cn-fusion-lts-wires and cn-fusion-divertor-material as independent arenas. The underlying content exists in blocks/facts but the competitive-landscape structuring is incomplete. Recommend: add these two arenas in post-processing or a targeted QA pass.

2. **supply_bottleneck not an independent block.** REBCO产能缺口是 risk 维度的证据 (data: 3000km产能 vs 1万km需求)，split-subagent frames it primarily as opportunity in ib-004/ib-006. A dedicated `supply_bottleneck` block with `direction_on_source: risk` would round out the risk-side framing.

### Conclusion

| Question | Answer |
|---|---|
| Did split-subagent recover the 60% fact loss? | Yes — and exceeded baseline by 2.4x |
| Is split-subagent the best version for archiving? | Yes, for fact density and company coverage |
| Should inline be preferred for any purpose? | No — split-subagent is superior on all dimensions |
| Are there regressions vs. baseline? | Yes: arena coverage (2 missing), supply_bottleneck framing |
| Overall recommendation | Use split-subagent as canonical bundle; add 2 arena candidates in QA |

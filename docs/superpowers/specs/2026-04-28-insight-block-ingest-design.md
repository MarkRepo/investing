# 研报 ingest 的 source-role / insight-block 设计

**Status**: 设计草案，待用户 review 后再进入实施计划  
**Date**: 2026-04-28  
**Extends**: `docs/superpowers/specs/2026-04-26-industry-ingest-design.md`  

---

## 1. 背景与问题

现有三层知识框架（industry 11 维、arena 6 维、company 8 维）适合作为长期归档和阅读地图，但不适合作为研报 ingest 的第一步抽取框架。

如果 ingest 一开始就强行把原文内容塞进 11/6/8：

- 原文的论证链会被拆散，用户读到的是维度碎片；
- 同一段逻辑会被分散到 industry / arena / company 多个文件，失去上下文；
- atomic fact 虽然便于交叉验证，但单独使用会进一步加剧离散化；
- 最终用户仍然需要自己把事实、格局、公司、风险重新拼成投资判断。

因此，ingest 需要增加一个位于“原文”和“11/6/8 归档”之间的中间层：**source role + insight block**。

核心结论：

> 11/6/8 继续作为 archive schema；atomic facts 继续作为 evidence schema；但 ingest 的第一层结构应是保留原文逻辑的 insight blocks，最终用户入口应是 synthesis，而不是原始维度或原子事实。

## 2. 设计目标

1. **保留原文叙事逻辑**：研报如何从事实推到观点，必须被完整保留。
2. **保留可验证事实**：关键数字、份额、公司判断仍拆成 atomic facts，便于聚合、比对、追溯。
3. **兼容 11/6/8**：不推翻现有 industry / arena / company 知识框架，只改变 ingest 的前置结构。
4. **支持不同类型资料**：卖方深度、咨询白皮书、市场概览、技术报告、公司公告都可进入同一流程。
5. **降低用户理解成本**：用户先读 synthesis，再钻取 insight blocks，再进入 11/6/8 维度细节。
6. **防止弱证据污染**：低质量资料不能生成高置信投资结论，只能生成低置信事实和研究问题。

## 3. 非目标

- 不在本设计中重做 11/6/8 维度定义。
- 不要求所有历史 ingest 数据迁移到新结构。
- 不自动生成最终买入/卖出决策。
- 不把研报中的“标的池”直接升级为可投资公司结论。
- 不让脚本调用 LLM API；LLM 判断仍由 Claude 在对话中完成，脚本只做校验、写入和查询。

## 4. 总体流程

```text
source document
  -> source classification
  -> source-level digest
  -> insight_blocks[]
  -> atomic_facts[] linked to insight_block_id
  -> routing into industry 11 / arena 6 / company 8
  -> arena_candidates[] / company_candidates[]
  -> synthesis for user reading and decision preparation
```

用户阅读顺序应为：

```text
synthesis
  -> key insight blocks
  -> generated research questions
  -> routed 11/6/8 archive
  -> observations / claims for verification
  -> V0 investment memo written manually by user
```

## 5. Source-level schema

每次 ingest 先产一个 source-level record。

```yaml
source_id: 国金证券-化学机械抛光行业-2026-04-xx-abc12345
source_file: /path/to/report.pdf
source_type: sellside_industry_report
source_roles:
  primary: investment_thesis
  secondary:
    - technology_landscape
    - value_chain_mapping
    - company_screening
source_quality: high
source_quality_reason: "数据来源清楚，论证链完整，图表和公司覆盖较充分"
evidence_strength: medium_high
report_thesis: "先进制程、3D NAND、先进封装增加 CMP 步骤和材料复杂度，带动 CMP 抛光液/抛光垫市场扩容，并给国产替代厂商带来机会。"
covered_scopes:
  industries:
    - cmp-materials
  arenas:
    - cn-cmp-slurry-domestic-substitution
  companies:
    - ticker: "688019"
      market: "SH"
      name: "安集科技"
```

### 5.1 `source_type`

建议受控词表：

- `sellside_industry_report`
- `sellside_company_report`
- `company_annual_report`
- `company_quarterly_report`
- `earnings_call_transcript`
- `consulting_whitepaper`
- `industry_association_report`
- `market_overview`
- `policy_document`
- `news_or_article`

### 5.2 `source_roles`

一篇资料可以有多个角色，不能只用单值 `source_role`。

```yaml
source_roles:
  primary: investment_thesis
  secondary:
    - technology_landscape
    - value_chain_mapping
    - company_screening
    - risk_brief
```

建议角色：

- `investment_thesis`：明确提出投资主线或配置建议。
- `market_landscape`：描述市场规模、格局、增长驱动。
- `market_overview`：轻量概览，通常证据较弱。
- `consumer_research`：消费者画像、需求、渠道、行为变化。
- `policy_reference`：政策、监管、补贴、产业规划。
- `company_disclosure`：公司经营、财务、治理的一手披露。
- `technology_landscape`：技术路线、工艺、产品指标、成熟度。
- `value_chain_mapping`：产业链环节、上下游、成本结构、供应商。
- `company_screening`：标的池、供应链公司、相关公司名单。
- `risk_brief`：风险、反证、失败条件。
- `thematic_strategy_basket`：围绕一个大主题组织多条投资主线和标的池。
- `scenario_map`：围绕多个应用场景、区域或终端场景展开市场地图。

### 5.3 `source_quality` 与 `evidence_strength`

`source_quality` 评价资料整体质量；`evidence_strength` 评价其证据能支撑多强结论。

建议值：

- `high`
- `medium_high`
- `medium`
- `medium_low`
- `low`

使用规则：

- 高质量资料可以进入 narrative、observations、claims 和 synthesis。
- 中低质量资料可以进入 narrative，但 facts 默认降置信。
- 低质量资料主要生成 research questions，不应生成强投资结论。
- `source_quality` 不等于观点正确，只表示资料可用性和证据完整度。

## 6. Insight block

`insight_block` 是 ingest 的核心中间对象，用来保留原文的一个完整逻辑单元。

它不是 atomic fact，也不是 11/6/8 维度段落，而是“原文如何组织一个洞察或论证”的最小可读单元。

```yaml
id: ib-0003
block_type: demand_driver
title: "先进制程和 3D NAND 增加 CMP 步骤"
source_page_range: "6-9"
evidence_strength: medium_high
summary: "报告认为，逻辑制程微缩、3D NAND 堆叠层数增加和先进封装渗透，会提升 CMP 使用次数和耗材复杂度，从而驱动抛光液与抛光垫需求。"
reasoning_chain:
  - "芯片结构复杂度提升"
  - "CMP 步骤数量增加"
  - "抛光材料单耗和技术门槛提升"
  - "CMP 材料市场扩容"
assumptions:
  - "先进制程和 3D NAND 扩产持续"
  - "国产晶圆厂资本开支维持"
counterpoints:
  - "若半导体资本开支下行，短期需求可能被推迟"
key_facts:
  - fact_id: fact-0012
  - fact_id: fact-0013
routing:
  industry:
    - slug: cmp-materials
      dimensions: [drivers, technology, market_size]
  arena:
    - slug: cn-cmp-slurry-domestic-substitution
      dimensions: [trajectory, narratives, investment_view]
  company: []
generated_research_questions:
  - "CMP 步骤增加对抛光液/抛光垫单片价值量的弹性是多少？"
  - "国内头部晶圆厂先进制程扩产节奏是否支撑该需求假设？"
```

### 6.1 `block_type`

建议受控词表：

- `argument`：明确投资论证链。
- `market_scan`：市场规模、增速、结构扫描。
- `consumer`：消费者画像、需求、渠道行为。
- `value_chain`：产业链结构、上下游、成本和议价权。
- `policy`：政策、监管、补贴、产业规划。
- `regulatory_event`：医药、医疗器械等行业的获批、申报、CDE/NMPA/FDA 事件快报。
- `capital`：融资、资本开支、并购、上市公司关注度。
- `strategy`：企业战略、商业模式、打法。
- `risk`：风险、反证、失败条件。
- `lifecycle`：行业阶段、渗透率、成熟度。
- `competition`：竞争格局、份额、进入壁垒。
- `technology`：技术路线、工艺、产品指标。
- `benchmark`：海外或龙头对标。
- `company_screening`：标的池、供应链名单、公司筛选。
- `demand_driver`：需求驱动因素。
- `segment_structure`：子品类、品类结构、市场拆分。
- `go_to_market`：渠道、销售模式、触达方式。
- `theme_basket`：大主题下的多条投资主线组合，例如 AI 算力链同时覆盖芯片、服务器、存储、PCB、光模块、消费电子等。
- `stage_gate`：产业从概念到商业化必须跨过的门槛，例如适航取证、客户认证、资本开支兑现、良率爬坡、生态迁移。
- `scenario_map`：按应用场景组织的市场地图，例如低空经济中的物流配送、UAM、巡检、文旅、应急等。

### 6.2 Insight block 与 atomic fact 的关系

atomic fact 必须保留，但必须挂回 insight block。

```json
{
  "id": "fact-0012",
  "linked_block_id": "ib-0003",
  "fact_text": "报告称先进制程会增加 CMP 步骤数量。",
  "evidence_quote": "...",
  "target_layer": "industry",
  "target_refs": {"industry_slug": "cmp-materials"},
  "dimension_hint": "drivers",
  "confidence": "medium_high",
  "source_quality": "high",
  "evidence_strength": "medium_high"
}
```

规则：

- atomic fact 负责可验证性。
- insight block 负责上下文和叙事逻辑。
- 维度 narrative 应引用 block summary，而不是只拼接 fact 列表。
- observations / claims 聚合页面可以展示 linked block，方便用户回到原论证。

## 7. Routing 到 11/6/8

11/6/8 不作为第一抽取框架，而作为 block 和 fact 的归档目标。

### 7.1 industry routing

industry 适合承接：

- 市场规模、增速、渗透率；
- 生命周期阶段；
- 产业链结构；
- 竞争格局；
- 增长驱动；
- 技术/产品路线；
- 政策监管；
- 行业风险；
- 估值锚和行业基准。

### 7.2 arena routing

arena 只在存在明确“博弈焦点”时承接：

- 国产替代；
- 技术路线之争；
- incumbent / challenger 攻防；
- 平台迁移；
- 渠道或商业模式变化；
- 价格带或客户场景的竞争重构。

没有博弈焦点的细分市场不要自动建 arena，只保留为 industry segment。

### 7.3 company routing

company 适合承接：

- 公司业务模式；
- 护城河和竞争策略；
- 增长引擎；
- 管理层和治理；
- 财务质量；
- 催化剂；
- 公司特有风险；
- 估值。

行业级事实不要因为报告提到某家公司就塞进 company claims；只有“公司与事实直接相关”时才进入 company 层。

## 8. Arena candidates

很多行业报告会自然生成 arena 候选，但候选不等于正式 arena。

```yaml
arena_candidates:
  - slug: cn-cmp-slurry-domestic-substitution
    name: "中国 CMP 抛光液国产替代"
    battleground_focus: "国产厂商能否突破海外材料厂商在先进制程客户中的认证和份额壁垒"
    evidence_strength: medium_high
    source_block_ids: [ib-0003, ib-0005]
    suggested_action: review_before_create
    open_questions:
      - "国内晶圆厂客户认证周期和量产份额是多少？"
      - "海外厂商在先进制程 slurry 配方上的优势是否可持续？"
```

创建规则：

- 可以自动生成候选；
- 不应无审核直接创建正式 arena；
- 候选必须有 `battleground_focus`；
- 候选必须能列出核心参与者或参与者类型；
- 候选必须说明为什么不是普通 industry segment。

## 9. Company candidates

报告中的“标的池”“产业链相关公司”“受益标的”必须降级处理，不能直接变成公司结论。

```yaml
company_candidates:
  - ticker: "688019"
    market: "SH"
    name: "安集科技"
    exposure_type: direct_pure_play
    related_arenas:
      - cn-cmp-slurry-domestic-substitution
    evidence_strength: medium_high
    source_block_ids: [ib-0007]
    candidate_reason: "报告将其列为国内 CMP 抛光液龙头，并讨论其在抛光液产品线中的竞争位置。"
    verification_questions:
      - "CMP 抛光液收入占公司收入比例是多少？"
      - "先进制程客户认证和量产进度如何？"
      - "毛利率和研发费用率是否支持技术壁垒判断？"
```

医药、医疗器械、早期硬科技等公司候选可增加可选字段：

```yaml
company_candidates:
  - ticker: "xxxxxx"
    market: "SH"
    name: "示例公司"
    exposure_type: thematic_related
    technology_route: invasive | semi-invasive | non-invasive | intravascular | superconducting | tokamak | other
    regulatory_pathway: NMPA-III | FDA-PMA | FDA-IDE | consumer-exempt | other
    clinical_stage: pre-clinical | early-feasibility | pivotal | approved | commercialized
    pipeline:
      - product_name: "示例产品"
        mechanism: "GLP-1/GIP 双靶点"
        indication: "肥胖/超重"
        clinical_phase: Phase I | Phase II | Phase III | NDA-submitted | approved
        approval_status: IND-approved | NDA-submitted | approved | rejected | unknown
        reimbursement_status: included | negotiation | excluded | self-pay | unknown
    verification_questions:
      - "相关产品收入占总收入比例是多少？"
      - "客户是商业客户、医院、政府采购，还是科研/示范项目？"
      - "核心产品处于临床、注册、医保准入还是商业化放量阶段？"
```

### 9.1 `exposure_type`

建议受控词表：

- `direct_pure_play`：收入和业务高度直接暴露于该主题。
- `direct_supplier`：直接供给关键产品或服务，但公司可能还有其他业务。
- `component_supplier`：供应链零部件或材料环节，主题暴露较间接。
- `thematic_related`：主题相关，但收入暴露未验证。
- `state_owned_space_group`：央国企集团或集团下属平台，需额外验证上市公司权益和收入映射。

规则：

- `thematic_related` 不能直接进入投资结论。
- `component_supplier` 必须验证收入占比、客户、订单和利润弹性。
- 标的池必须生成 verification questions。
- 只有验证后，才可升级为 company narrative 或 V0 备选。

## 10. Thematic basket 与 stage gate

本轮验证显示，部分资料不是单一行业或单一公司报告，而是围绕一个大主题组织多条投资主线的“主题篮子”。典型例子包括 AI 算力、年度电子行业策略。

### 10.1 Thematic basket

`theme_basket` 用来表示一个跨行业、跨环节、跨公司的投资主题组合。

```yaml
theme_basket:
  id: tb-ai-computing-2026
  title: "AI 算力产业链"
  core_driver: "云端和端侧 AI 推动算力基础设施、芯片、服务器、存储、PCB/CCL、光模块等环节扩张"
  subthemes:
    - id: ai-cloud-chip
      title: "云端算力芯片国产替代"
      stage: scaling
      key_gates: [export_control, performance_gap, software_ecosystem]
    - id: ai-server
      title: "AI 服务器"
      stage: growth
      key_gates: [downstream_capex, supply_chain, margin_sustainability]
    - id: ai-pcb-ccl
      title: "AI PCB/CCL"
      stage: capex_upcycle
      key_gates: [material_upgrade, customer_validation, capacity_release]
  related_industries:
    - ai-computing
    - semiconductors
    - electronic-components
  related_arenas:
    - cn-ai-chip-domestic-substitution
    - ai-server-supply-chain
  company_candidates: []
```

规则：

- 大主题报告先生成 `theme_basket`，再拆 subthemes；
- subtheme 才能进一步 routing 到 industry / arena / company；
- 同一家公司可出现在多个 subthemes，必须记录 `theme_refs`；
- 主题篮子中的推荐股票表不能直接写成 company thesis；
- 用户入口应先显示主题篮子地图，再显示各 subtheme 的 insight blocks。

### 10.2 Stage gate

`stage_gate` 用来记录产业或公司从概念、样机、验证、量产到商业化必须跨过的门槛。

```yaml
stage_gate:
  id: sg-evtol-certification
  gate_type: certification
  title: "eVTOL 适航取证"
  current_state: "部分厂商取得 TC/AC，行业仍处于商业化早期"
  why_matters: "没有适航取证就无法进入规模化商业运营"
  evidence_strength: medium
  linked_blocks: [ib-0012, ib-0013]
  verification_questions:
    - "不同厂商 TC/AC/PC 进度分别如何？"
    - "取证后是否已有可复制商业航线和订单？"
```

常见 `gate_type`：

- `certification`：适航、医疗器械、车规、客户认证等。
- `clinical_trial`：临床前、早期可行性、关键临床、确证性临床等试验阶段。
- `ethics_review`：伦理审查、知情同意、一事一议审批等高敏感技术门槛。
- `reimbursement`：医保目录、商保支付、集采准入、支付路径闭环。
- `customer_validation`：客户导入、样品验证、订单确认。
- `mass_production`：量产、良率、产能释放。
- `ecosystem_migration`：CUDA 迁移、软件生态、开发者生态。
- `capex_realization`：资本开支是否真正落地。
- `infrastructure_readiness`：空域、起降场、通信、充电、数据中心等基础设施。
- `unit_economics`：成本、价格、毛利、规模效应是否闭环。

规则：

- 早期产业报告必须显式抽取 stage gates；
- stage gate 未跨过时，synthesis 只能写“潜在机会”，不能写强投资结论；
- 对 evidence_strength 低于 `medium`，或核心 stage gate 未跨过的资料，`synthesis.cannot_conclude` 必须明确写出“当前商业化里程碑尚未实现，不能依据本资料做买入判断”；
- company candidate 应记录其对应 gate 的状态，而不是只记录“属于该主题”；
- stage gate 是 arena 是否成立的重要依据：没有明确门槛和博弈焦点的，不应建 arena。

### 10.3 技术成熟度与场景经济性

技术路线型和场景型报告需要额外保留两个可选字段，避免把“有技术路线”误读为“已商业化”。

```yaml
technology_block_extensions:
  maturity_stage: commercial | pilot | demonstration | r_and_d
  maturity_reason: "锂电储能已规模化，钠离子处于示范，固态电池仍有界面和工艺问题。"

scenario_map_extensions:
  economics_condition: "用户侧储能经济性依赖峰谷价差、利用小时和电价机制持续性。"
```

规则：

- `maturity_stage` 用于技术路线之间成熟度差异很大的报告，例如储能、脑机接口、量子科技、核聚变；
- `economics_condition` 用于同一行业不同应用场景商业模式差异很大的报告，例如储能发电侧/电网侧/用户侧、低空经济多场景、家用医疗器械多终端；
- 这些字段只描述当前阶段，不替代 stage gate，也不能直接生成投资结论。

## 11. Synthesis

每次 ingest 最终必须生成一个面向用户阅读的 synthesis。

```yaml
synthesis:
  one_sentence: "CMP 材料的核心投资逻辑是先进制程和 3D NAND 提升 CMP 步骤与材料复杂度，在海外厂商主导的高壁垒市场中打开国产替代窗口。"
  source_quality: high
  evidence_strength: medium_high
  what_we_know:
    - "CMP 是晶圆制造关键平坦化工艺，抛光液和抛光垫是核心耗材。"
    - "先进制程、3D NAND 和先进封装会增加 CMP 工艺需求。"
  what_is_plausible:
    - "国内 CMP 材料厂商可能受益于国产替代和晶圆厂扩产。"
  what_needs_verification:
    - "国产厂商在先进制程客户中的实际认证和量产份额。"
    - "需求扩张能否传导到公司收入和利润，而不只是行业空间。"
  investment_questions:
    - "这是一场行业 beta 机会，还是少数公司 alpha 机会？"
    - "胜负手是配方技术、客户认证、产能、价格，还是服务响应？"
  cannot_conclude:
    - "仅凭本报告不能直接判断具体公司是否值得买入。"
```

Synthesis 分层：

- `what_we_know`：证据较强，可进入知识库。
- `what_is_plausible`：逻辑合理，但仍需验证。
- `what_needs_verification`：下一步研究问题。
- `investment_questions`：为 V0 决策准备的问题。
- `cannot_conclude`：明确禁止用户过度外推。

## 12. 十四类报告验证结论

### 12.1 化学机械抛光行业报告

适合类型：

```yaml
source_type: sellside_industry_report
source_roles:
  primary: investment_thesis
  secondary: [technology_landscape, value_chain_mapping, company_screening]
source_quality: high
evidence_strength: medium_high
```

验证结论：

- “argument block” 能很好保留投资论证链；
- CMP 工艺、先进制程、抛光液/抛光垫市场、国产替代、安集科技/鼎龙股份等应拆为多个 insight blocks；
- atomic facts 必须挂回对应 block，否则会丢失“先进制程 -> CMP 步骤 -> 材料复杂度 -> 国产替代”的主线。

### 12.2 2025 中国宠物行业市场报告

适合类型：

```yaml
source_type: consulting_whitepaper
source_roles:
  primary: market_landscape
  secondary: [consumer_research, segment_structure]
source_quality: medium_high
evidence_strength: medium
```

验证结论：

- 不是所有资料都是投资论证，因此 `argument_block` 必须泛化为 `insight_block`；
- 宠物食品、医疗、用品、服务等更适合生成 arena candidates 或 segment_structure blocks；
- 用户需要先读“宠物经济为什么增长、增长来自哪里、哪些子战场值得研究”，而不是直接看 industry 11 维碎片。

### 12.3 潮玩报告

适合类型：

```yaml
source_type: market_overview
source_roles:
  primary: market_overview
  secondary: [consumer_research, go_to_market]
source_quality: medium_low
evidence_strength: low_to_medium
```

验证结论：

- 低证据强度资料仍有价值，可用于行业初始框架、消费动机、渠道和 arena candidates；
- 但不能生成高置信市场规模、强公司护城河或投资结论；
- 必须把大量内容降级为 research questions。

### 12.4 商业航天报告

适合类型：

```yaml
source_type: sellside_industry_report
source_roles:
  primary: investment_thesis
  secondary:
    - technology_landscape
    - value_chain_mapping
    - company_screening
    - risk_brief
source_quality: high
evidence_strength: medium_high
```

验证结论：

- 一篇报告可以同时承担投资主线、技术科普、产业链拆解、标的筛选、风险提示多个角色；
- `source_roles` 必须支持 primary + secondary；
- 商业航天标的池必须引入 `company_candidates.exposure_type`，否则容易把主题相关公司误认为直接受益公司；
- 可生成多个 arena candidates：可回收商业火箭、火箭发动机、箭体结构、控制系统、卫星互联网发射需求。

### 12.5 AI 算力报告

适合类型：

```yaml
source_type: sellside_industry_report
source_roles:
  primary: investment_thesis
  secondary:
    - technology_landscape
    - value_chain_mapping
    - company_screening
    - thematic_strategy_basket
    - risk_brief
source_quality: high
evidence_strength: medium_high
```

验证结论：

- 该类报告不是单一产业 thesis，而是“AI 算力”主题下的多层链条：需求侧（互联网/智算中心）、AI 芯片、服务器、国产替代、CUDA 生态、公司标的和估值表；
- 必须增加 `theme_basket` block，先保留主题篮子的整体逻辑，再拆成多个 arena / company candidates；
- 芯片公司、服务器公司、互联部件公司不能只因出现在推荐表就进入 company thesis，必须用 `exposure_type` 和 verification questions 区分直接受益、间接受益和主题相关；
- 该类报告里的 EPS/PE 表应作为 valuation candidate，不应自动覆盖公司估值结论。

### 12.6 低空经济报告

适合类型：

```yaml
source_type: consulting_whitepaper
source_roles:
  primary: market_landscape
  secondary:
    - policy_reference
    - scenario_map
    - value_chain_mapping
    - risk_brief
source_quality: medium_high
evidence_strength: medium
```

验证结论：

- 低空经济是政策驱动、场景驱动、基础设施驱动共同作用的早期产业，不适合直接抽成单一投资 thesis；
- 必须增加 `scenario_map` block，保留物流配送、UAM、巡检、文旅、应急等不同场景的成熟度和商业模式差异；
- 必须增加 `stage_gate` block，记录适航取证、空域管理、基础设施、商业模式、人才体系等产业阶段门槛；
- 对 eVTOL / UAM 相关公司，`company_candidates` 需要额外记录取证状态、产品路线、商业化阶段和基础设施依赖，不能只按“制造商/运营商”分类。

### 12.7 电子行业 2026 投资策略报告

适合类型：

```yaml
source_type: sellside_industry_report
source_roles:
  primary: thematic_strategy_basket
  secondary:
    - investment_thesis
    - technology_landscape
    - value_chain_mapping
    - company_screening
    - risk_brief
source_quality: high
evidence_strength: medium_high
```

验证结论：

- 该类年度策略报告是多主题组合包，不是一个 industry：云端算力芯片、端侧算力芯片、存储、模拟、晶圆制造、消费电子、PCB/CCL 等应被切成多个 theme blocks；
- 对用户最有价值的不是直接进入 11/6/8，而是先生成“主题篮子地图”：每条主线的驱动、阶段、受益环节、候选公司、风险；
- 同一家公司可能在多个主题篮子里出现，必须记录 `theme_refs`，避免在 company 层重复写入互相矛盾或重复的 narrative；
- 对技术链条类主题，必须记录 `stage_gate`：如国产替代进度、客户验证、量产良率、资本开支兑现、材料升级周期。

### 12.8 储能研究报告

适合类型：

```yaml
source_type: consulting_whitepaper
source_roles:
  primary: market_landscape
  secondary:
    - technology_landscape
    - policy_reference
    - scenario_map
source_quality: medium_high
evidence_strength: medium
```

验证结论：

- 储能报告通常不是多主题策略包，而是单一行业下的多技术路线和多应用场景，不需要 `theme_basket`；
- 必须使用 `scenario_map` 区分发电侧、电网侧、用户侧等场景，因为价值主张和经济性闭环不同；
- 必须使用 `stage_gate` 记录钠离子、固态、液流、氢储能等路线从示范到商业化的门槛；
- `technology` block 应记录 `maturity_stage`，`scenario_map` 应记录 `economics_condition`，否则用户容易把“技术路线存在”误读为“商业模式已成立”。

### 12.9 医药生物行业周报

适合类型：

```yaml
source_type: sellside_industry_report
source_roles:
  primary: thematic_strategy_basket
  secondary:
    - investment_thesis
    - policy_reference
    - company_screening
    - market_landscape
    - risk_brief
source_quality: medium_high
evidence_strength: medium
```

验证结论：

- 医药周报常把创新药、ADC、双抗、小核酸、CAR-T、CXO、中药等多条主线放进同一标的池，必须先生成 `theme_basket`；
- 本周获批、申报、CDE/NMPA 事件适合进入 `regulatory_event`，不要和宏观政策类 `policy` 混在一起；
- 医药公司候选应记录 `pipeline`、`clinical_stage`、`approval_status` 和 `reimbursement_status`，否则无法区分“临床早期主题相关”和“已商业化收入来源”；
- 医保谈判、集采和支付路径应作为 `reimbursement` stage gate，而不只是普通风险提示。

### 12.10 生物医药年度策略报告

适合类型：

```yaml
source_type: sellside_industry_report
source_roles:
  primary: thematic_strategy_basket
  secondary:
    - investment_thesis
    - market_landscape
    - policy_reference
    - technology_landscape
    - value_chain_mapping
    - company_screening
    - risk_brief
source_quality: high
evidence_strength: medium_high
```

验证结论：

- 年度策略报告与电子行业策略类似，是多主线组合包，例如生科服务、创新药、家用器械、高端设备、耗材、中药、医药商业；
- 创新药主线必须抽取从 IND、临床、NDA、获批、医保准入到商业化放量的 stage gates；
- `scenario_map` 不只适用于低空经济，也适用于同一行业多个终端应用成熟度不同的场景，例如家用医疗器械、医疗设备更新；
- 未完成 NDA 或医保准入的 pipeline 不能写成确定收入和盈利结论。

### 12.11 脑机接口报告

适合类型：

```yaml
source_type: sellside_industry_report
source_roles:
  primary: investment_thesis
  secondary:
    - technology_landscape
    - value_chain_mapping
    - company_screening
    - policy_reference
    - risk_brief
source_quality: medium_high
evidence_strength: medium
```

验证结论：

- 脑机接口是早期技术产业，必须同时使用 `theme_basket`、`scenario_map` 和 `stage_gate`；
- 侵入式、半侵入式、非侵入式路线决定临床路径、监管类别、成本结构和应用场景，应记录在 `technology_route`；
- 医疗器械路径应记录 `regulatory_pathway` 和 `clinical_stage`，例如 NMPA 三类、FDA IDE/PMA、消费品豁免；
- 侵入式脑机接口在长期稳定性、伦理审查、临床试验和支付路径未跨过前，synthesis 只能写潜在机会，不能写强投资结论。

### 12.12 脑机行业白皮书

适合类型：

```yaml
source_type: industry_association_report
source_roles:
  primary: technology_landscape
  secondary:
    - market_landscape
    - policy_reference
    - value_chain_mapping
source_quality: medium_high
evidence_strength: medium_high
```

验证结论：

- 官方或协会白皮书适合补足技术分类、政策框架和产业链分布，但不应生成投资建议；
- 与卖方脑机接口报告配合时，应作为 cross-validation source，而不是重复覆盖同一份 synthesis；
- 脑感知、脑调控、医疗健康、消费电子、工业安全等场景应进入 `scenario_map`；
- company candidates 若只来自产业名录，默认应降级为 `thematic_related`。

### 12.13 量子科技报告

适合类型：

```yaml
source_type: sellside_industry_report
source_roles:
  primary: investment_thesis
  secondary:
    - technology_landscape
    - thematic_strategy_basket
    - value_chain_mapping
    - policy_reference
    - company_screening
    - risk_brief
source_quality: medium_high
evidence_strength: medium
```

验证结论：

- 量子科技必须拆成量子计算、量子通信、PQC 等子主线；不同主线商业化阶段差异很大，不能合成单一“量子”投资逻辑；
- NISQ、容错量子计算、PQC 迁移、量子云商业订单等应作为 stage gates；
- `scenario_map` 可记录金融优化、药物研发、网络安全、物流等应用场景的时间窗口和受益公司；
- 在没有商业订单和单位经济性验证前，工程进展不能外推为公司收入和利润。

### 12.14 核聚变报告

适合类型：

```yaml
source_type: sellside_industry_report
source_roles:
  primary: investment_thesis
  secondary:
    - technology_landscape
    - value_chain_mapping
    - company_screening
    - policy_reference
    - risk_brief
source_quality: high
evidence_strength: medium
```

验证结论：

- 核聚变报告的核心不是短期收入预测，而是工程里程碑和产业链供应商筛选；
- ITER、CFETR、BEST、Q 值、氚增殖、自持运行、发电成本等应进入 `stage_gate`；
- 真空室、磁体、包层、偏滤器、高温超导等供应商必须验证相关收入占比和客户性质，区分国家科研项目订单与商业项目订单；
- 聚变商业化时间远，`synthesis.cannot_conclude` 必须明确不能据此判断具体公司未来收入和利润。


## 13. Web 展示含义

当前页面以维度 narrative 为主要入口，未来应调整为：

1. 顶部显示 synthesis。
2. 其次显示 key insight blocks。
3. 再显示 arena / company candidates 和 research questions。
4. 最后显示 11/6/8 维度归档和 observations / claims。

这样用户先获得“这份资料到底告诉我什么”，再选择是否深入维度和事实。

## 14. 与 V0 投资 memo 的关系

Synthesis 不是 V0，也不能替代 V0。

- Synthesis 负责把 ingest 资料整理成可理解的研究结论和问题。
- V0 负责用户自己的投资判断、差异化观点、估值锚、卖出触发和噪音清单。
- Synthesis 可以为 V0 提供材料，但不能自动生成“买入逻辑”和“二阶思维”。

特别是 V0 的“差异化观点”仍必须由用户手写；从 claims 或 synthesis 直接复制应继续被视为坏实践。

## 15. 实施影响

后续实施应分阶段：

1. 增加 digest 输出 schema：`source_roles`、`source_quality`、`insight_blocks`、`linked_block_id`、`synthesis`、`theme_basket`、`stage_gates`、`maturity_stage`、`economics_condition`、医药/医疗器械候选字段。
2. 更新 prompts：从“直接抽 key_facts + narratives”改为“先切 insight blocks，再抽 facts，再 routing”。
3. 更新 ingest aggregator：校验 block / fact 关联，保留 source/block 质量字段。
4. 增加 archive 文件：保存每次 ingest 的 source digest、insight blocks、theme basket 和 stage gates。
5. 更新页面：在 industry / arena / company 详情页增加 synthesis 和 key insight blocks 入口；对主题篮子报告增加 theme map 入口。
6. 更新 QA：检查 facts 是否有 `linked_block_id`，检查高置信 conclusion 是否来自足够证据强度。
7. 更新 company candidate 校验：要求主题篮子来源的候选公司必须带 `theme_refs`、`exposure_type` 和 verification questions；医药、医疗器械、硬科技候选必须记录或追问产品阶段、监管路径、收入占比和客户性质。

## 16. 关键约束

- 不允许丢失原文证据；所有 facts 仍需 evidence quote。
- 不允许把低质量资料提升为高置信结论。
- 不允许把 company screening 当成 company thesis。
- 不允许把普通 segment 自动建成 arena。
- 不允许让 atomic facts 成为唯一用户阅读入口。
- 不允许让 11/6/8 维度倒逼原文逻辑被打散。
- 不允许把多主题策略报告强行归入单一 industry；必须先生成 theme basket。
- 不允许在 stage gate 未跨过时生成强投资结论。
- 不允许把临床前、临床中、NDA、医保准入前的 pipeline 写成确定商业化收入。
- 不允许把国家科研项目、示范项目或主题订单直接外推为公司长期商业收入。

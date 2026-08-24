---
slug: us-tempus
variant: opus4.8
written_at: 2026-08-03T13:47:34Z
training_cutoff_estimate: 2025-08    # 对 Tempus 具体财务/交易细节，可靠记忆约到 2025 年中；更晚数据置信度快速衰减
---

# 训练知识 Baseline — Tempus AI (TEM, NASDAQ)

> 本文记录 LLM 在**训练截止时**对 Tempus AI 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。
> ⚠️ Tempus 是 2024 年才 IPO 的高增长故事股，财务与交易细节时效性极强，快变 fact 占比高。

## 〇、基本信息（company 类型）

- **主代码**：`US_TEM`（NASDAQ；与 topic.yaml `scope.ticker` 一致）
- **多市场上市**：单市场（仅 NASDAQ 普通股）
- **市场属性**：美股，交易窗口 9:30-16:00 ET；IPO 2024-06；创始人控制权高（Lefkofsky 持超级投票权 B 类股，双层股权结构）
- **估值口径提示**：Tempus 未 GAAP 盈利，PE 无意义；估值须用 EV/Sales、EV/毛利、以及分部（Genomics 诊断 vs Data & AI）SOTP，警惕把商品化诊断收入按 AI 数据倍数一刀切估值

## 一、关键事实记忆（27 条）

### 公司与业务模式
- `[fact-01]` Tempus AI 成立于 2015 年，总部芝加哥，创始人兼 CEO 是 Eric Lefkofsky（Groupon 联合创始人、Uptake、Mediaocean 背景）→ 置信度：高 | time_sensitivity：**静态**
- `[fact-02]` 2024-06 在 NASDAQ IPO，发行价约 $37/股，募资约 $4.1 亿 → 置信度：中 | time_sensitivity：**静态**
- `[fact-03]` 核心业务两大分部：① Genomics（临床基因检测/诊断，肿瘤 NGS + 遗传 + 液体活检，收入主体）；② Data & AI（把去标识化多模态临床+基因组数据授权给药企，毛利更高，是"AI 溢价"来源）→ 置信度：高 | time_sensitivity：**慢变**
- `[fact-04]` 采取"以诊断换数据"飞轮模式：临床检测积累多模态数据 → 授权给药企/训练算法 → 反哺算法诊断产品（如 Tempus One、算法测试 algos）→ 置信度：中 | time_sensitivity：**慢变**
- `[fact-05]` 双层股权结构，Lefkofsky 通过 B 类股掌握多数投票权 → 治理集中，关联交易需重点审视 → 置信度：中 | time_sensitivity：**慢变**

### 财务（快变——大部分需校准）
- `[fact-06]` 2023 年营收约 $5.3 亿 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-07]` 2024 年营收约 $6.9 亿，同比增长约 30%+ → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-08]` 2025 年营收指引在收购 Ambry 后大幅上修至约 $12.4 亿量级 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-09]` 公司持续 GAAP 净亏损，adjusted EBITDA 逐季改善、管理层引导 2025 转正 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-10]` 混合毛利率约 50-60%；Genomics 诊断毛利偏低、Data & AI 毛利高（可能 70%+）→ 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-11]` Data & AI 分部有"剩余合同价值/backlog"披露（total remaining contract value），是数据业务能见度的关键指标，规模数十亿级 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-12]` IPO 后现金约 $3 亿+；有可转债/债务安排，现金消耗仍在 → 置信度：低 | time_sensitivity：**快变** ⚠️

### 关键交易与合作（快变/慢变）
- `[fact-13]` 2025 年初收购 Ambry Genetics（遗传检测），对价约 $6 亿量级 → 大幅拉升 Genomics 收入体量，但摊薄+整合风险 → 置信度：中 | time_sensitivity：**慢变**
- `[fact-14]` 与 AstraZeneca + Pathos AI 合作构建肿瘤基础模型（foundation model），Tempus 侧对价约 $2 亿量级（2025 年公布）→ 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-15]` NVIDIA 有股权/合作关系（2024 公布），用于 AI 算力/模型合作，是"AI 概念"重要背书 → 置信度：中 | time_sensitivity：**慢变**
- `[fact-16]` 与 Google Cloud 有基础设施合作 → 置信度：中 | time_sensitivity：**慢变**
- `[fact-17]` 大型药企数据客户包括 AstraZeneca、GSK、Bayer 等（具体名单与合同额需校准）→ 置信度：低 | time_sensitivity：**快变** ⚠️

### 空头/争议（快变——须校准最新进展）
- `[fact-18]` Spruce Point Capital 发布做空报告，质疑：激进/可疑会计、关联方交易（Lefkofsky 关联实体如 Pathos，及高管 Ryan Fukushima 与 Pathos 的双重角色）、Data 业务 ARR 质量与增速放缓、检测收入可持续性 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-19]` 关联交易关注点：Pathos AI 由 Lefkofsky 关联，且 Tempus COO Ryan Fukushima 兼任 Pathos CEO；AstraZeneca-Pathos-Tempus 三方交易存在循环收入质疑 → 置信度：低 | time_sensitivity：**快变** ⚠️

### 股价/估值（快变）
- `[fact-20]` IPO $37，2025 年初一度冲高至 $80-90+（AI 热潮），后大幅波动 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-21]` 市值区间大致 $50 亿-$150 亿波动（视时点）→ 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-22]` 估值倍数（EV/Sales）显著高于传统诊断同业（GH/NTRA/EXAS），溢价来自"AI+数据"叙事 → 置信度：中 | time_sensitivity：**快变** ⚠️

### 行业/竞争（慢变）
- `[fact-23]` 肿瘤 NGS/诊断竞对：Guardant Health (GH，液体活检)、Foundation Medicine (Roche 全资)、Natera (NTRA，MRD/遗传)、Exact Sciences (EXAS)、Caris Life Sciences (2025 IPO)、NeoGenomics → 置信度：高 | time_sensitivity：**慢变**
- `[fact-24]` 遗传检测竞对：Myriad Genetics、Natera、Labcorp（收购已破产的 Invitae）、GeneDx；Ambry 并入后 Tempus 增强遗传板块 → 置信度：中 | time_sensitivity：**慢变**
- `[fact-25]` 药企真实世界数据/AI 竞对：Flatiron Health (Roche)、Komodo Health、Verily、Palantir(医疗)、各类 RWD 平台 → 置信度：中 | time_sensitivity：**慢变**
- `[fact-26]` 诊断行业报销（CMS/商保覆盖、ADLT 定价、PAMA）是收入质量核心变量；肿瘤 NGS 报销环境总体改善但仍是压制毛利的结构因素 → 置信度：中 | time_sensitivity：**慢变**
- `[fact-27]` "AI 医疗诊断"整体处于叙事驱动、监管（FDA LDT 规则、AI/ML 器械审批）与报销双重不确定阶段 → 置信度：中 | time_sensitivity：**慢变**

### 第一节统计
- 静态：2 条（fact-01, 02）
- 慢变：11 条（fact-03,04,05,13,15,16,23,24,25,26,27）
- **快变：14 条**（fact-06~12, 14, 17, 18, 19, 20, 21, 22）⚠️——其中"高/中置信度 + 快变"子集：fact-06,07,13(慢),18,20(低),22 等 → 第五节须逐条对应 query

## 二、关键人物 / 公司 / 产品

- **Eric Lefkofsky**（创始人/CEO/董事长）：连续创业者，Groupon 联创；掌握 Tempus 超级投票权；是 thesis 中"创始人主导、关联交易、资本运作激进"叙事的中心。
- **Ryan Fukushima**（COO）：同时任 Pathos AI 的 CEO，双重角色是关联交易争议焦点。
- **Ambry Genetics**：2025 并入的遗传检测子公司，拉升收入但带来整合/摊薄。
- **Pathos AI**：Lefkofsky 关联的肿瘤 AI 药物研发公司，与 Tempus 有数据/模型交易，循环收入质疑的核心。
- **Tempus One / algos**：AI 算法诊断产品线，是"数据飞轮变现"的落地形态。
- **Spruce Point Capital**：做空机构，发布质疑报告。

## 三、产业链 / 竞争格局认知

Tempus 处于"精准肿瘤诊断 + 医疗数据/AI"两条产业链的交叉点。**诊断链**上，它与 Guardant、Foundation Medicine、Natera、Exact、Caris 争夺肿瘤基因检测（组织 NGS + 液体活检）市场，收入受 CMS/商保报销、检测量、单价三重驱动，毛利结构性偏低、竞争激烈、同质化压力大——这是"商品化临床实验室"的底色。

**数据/AI 链**上，Tempus 卖点是全美最大规模之一的多模态（基因组+临床+影像+病理）去标识化数据库，授权给药企做靶点发现、临床试验匹配、真实世界证据。竞对是 Flatiron（Roche）、Komodo、Verily 等。这条链毛利高、被资本市场按"AI 数据"高倍数定价——**Tempus 的全部估值溢价押在这条链能否规模化、可持续、非循环**。

**核心张力**：市场用 Data & AI 的叙事给整个公司（收入仍以诊断为主体）打高倍数。空头认为数据收入增速放缓、含关联循环成分、backlog 兑现存疑；多头认为诊断量的积累会不断喂养数据飞轮、算法产品放量、AI 溢价终会兑现。命门正落在这里。

监管/报销层：FDA 对 LDT（实验室自建检测）与 AI/ML 医疗器械的监管框架仍在演变；CMS 报销与商保覆盖决定诊断收入质量。均为慢变但方向性重要。

## 四、训练知识盲点（自我承认）

- **2025 下半年至今的财务实况**：季度营收/毛利/adj. EBITDA 是否如指引转正、Data & AI 分部增速与 backlog 最新值——我记忆模糊，置信度低。
- **Ambry 整合后的分部重述**：并表后 Genomics vs Data & AI 的收入/毛利拆分口径可能变化，我不掌握最新披露结构。
- **Spruce Point 报告后的进展**：公司回应、SEC 是否问询、做空论点是否被证伪或坐实、股价反应——我不知道最新状态。
- **AstraZeneca-Pathos-Tempus 三方交易细节**：确切金额、收入确认方式、是否被认定循环收入——不确定。
- **当前股价/市值/EV/Sales 倍数**：完全需要校准，我记忆的区间可能已过时。
- **现金跑道与融资**：最新现金、债务、是否再融资/摊薄——不掌握。
- **管线/新产品 readout**：MRD 产品、新算法测试的 FDA 进展与商业化——不掌握细节。
- **一致预期（sell-side consensus）**：分析师目标价、评级分布、2026/2027 收入预测——完全需要校准。

## 五、需要 web-search 校准的优先项

> 强制规则：第一节所有"快变 + 高/中置信度"fact 必须有对应 query。

1. `Tempus AI TEM 2025 Q2 Q3 earnings revenue guidance adjusted EBITDA`（校准 fact-07,08,09）
2. `Tempus AI Data and AI segment revenue growth 2025 total remaining contract value backlog`（校准 fact-11，命门核心）
3. `Tempus AI gross margin genomics vs data 2025 segment breakdown`（校准 fact-10）
4. `Tempus AI Ambry Genetics acquisition close revenue contribution 2025 integration`（校准 fact-13）
5. `Tempus AI Spruce Point short report response SEC accounting related party Pathos 2025`（校准 fact-18,19）
6. `Tempus AI AstraZeneca Pathos foundation model deal terms circular revenue`（校准 fact-14,19）
7. `Tempus AI TEM stock price market cap EV sales valuation multiple 2026`（校准 fact-20,21,22）
8. `Tempus AI analyst consensus price target rating 2026 2027 revenue estimate`（补一致预期盲点）
9. `Tempus AI cash runway balance sheet debt convertible dilution 2025`（校准 fact-12）
10. `Tempus AI NVIDIA partnership stake AI compute 2025 update`（校准 fact-15）

**质检**：第五节 10 条 query ≥ 第一节"快变+高/中"fact 数，覆盖全部命门相关快变项 ✓。

## 六、prescan 校准结果（2026-08-03T13:52Z 回写）

> Step 4.5a 跑 10 条优先 query + 1 条追加核实，入库 43 份 web-search material（22 high + 21 mid），对照第一节 fact-NN 更新如下。

### 🔴 被推翻 / 大幅修正（thesis_v0 不要再用原 fact）
- `[fact-07]` 训练时"2024 营收 ~$6.9 亿，增长 ~30%" → 实际增长远超预期：**Q3 2025 营收同比 +84.7%**、**Q2 2025 单季营收 $382.5M**（约 22% 有机增长口径，含 Ambry 并表后总增长更高）。全年 2025 结果已于 **2026-02-24** 披露。收入体量与增速均被大幅上修——原 fact 作废。
- `[fact-09]` 训练时"持续净亏损、引导 EBITDA 转正" → **已兑现**：Q3 2025 首次录得正的 adjusted EBITDA；**Q2 2026 adj. EBITDA $8.0M**（vs Q2 2025 -$5.6M）。方向验证且已转正。
- `[新增 fact-28]` **训练时完全不知道**：2026-07-20 Tempus 宣布 **以约 $1.5B 企业价值收购 Personalis (PSNL)**——MRD（分子残留病）检测公司，直接切入 MRD 赛道对标 Natera Signatera。这是继 Ambry 之后又一起收购驱动增长/摊薄事件，**必须进 thesis_v0**（`[mat]` tempus.com/mobihealthnews/stocktitan 2026-07-20）→ 置信度：高 | time_sensitivity：快变

### ✅ 被验证（可继续引用，置信度提升）
- `[fact-13]` Ambry 收购 → **2025-02-03 完成交割**，确认。
- `[fact-14]` AstraZeneca + Pathos 基础模型交易 → **$200M、2026… 实为 2025-04-23 公布**，金额确认。
- `[fact-18]` Spruce Point 做空报告 → 确认存在，**报告日 2025-05-28**；已有后续复盘文章（nanalyze 2026-02-27）→ 后续进展留 01/02 深挖。
- `[fact-15]` NVIDIA 合作 → 仍在（NVIDIA 2025-10-28 AI 基础设施公告含 Tempus 生态），验证。

### 仍未校准（thesis_v0 引用时标 uncertain，留 01/02 收料）
- `[fact-08]` 2025 全年营收确切值（已披露但未取全文，约 $1.2–1.5B 量级待 01 财报确认）
- `[fact-10]` Genomics vs Data & AI 分部毛利拆分（Ambry+Personalis 并表后口径会变）
- `[fact-11]` Data & AI 分部 TCV/backlog 最新值与增速（**命门核心，01 必须砸料**）
- `[fact-12]` 现金/债务/摊薄（连收 Ambry + Personalis 两笔，现金与股本结构需重算）
- `[fact-20/21/22]` 当前股价/市值/EV-Sales 倍数（EV/EBITDA 仍为负，gurufocus -93.99；具体估值 01 定）
- `[fact-19]` Pathos 循环收入质疑是否被证伪/坐实（待 01 读 Spruce Point 全文 + 公司回应）

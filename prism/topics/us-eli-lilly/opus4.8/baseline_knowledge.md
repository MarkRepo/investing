---
slug: us-eli-lilly
variant: opus4.8
written_at: 2026-06-12
training_cutoff_estimate: 2026-01
---

# 训练知识 Baseline — 礼来 (Eli Lilly, NYSE: LLY)

> 本文记录 LLM 在**训练截止时（~2026-01）**对该 topic 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。
> ⚠️ 提醒：LLY 是高时效标的（季度业绩/临床读出/股价/政策密集），快变类 fact 多，第五节 query 必须把"高置信+快变"子集全覆盖。

## 〇、基本信息

- **主代码**：`US_LLY`（NYSE 上市，与 topic.yaml `scope.ticker` 一致）
- **多市场上市**：单市场（仅 NYSE）
- **公司**：Eli Lilly and Company，总部美国印第安纳波利斯，成立 1876
- **CEO**：David A. Ricks（2017 起任 CEO/董事长）→ 置信度 中（高管变动属快变，需校准）
- **市场属性**：美股，盘后/盘前交易，无涨跌停；指数权重股（标普 500 / 一度市值居全球药企之首）

## 一、关键事实记忆（30 条）

### A. 核心 franchise — GLP-1/减重降糖（thesis 脊柱）

- `[fact-01]` GLP-1 受体激动剂通过激动肠促胰素受体抑制食欲、延缓胃排空、改善血糖实现减重降糖（机制）→ 置信度：高 | time_sensitivity：**静态**
- `[fact-02]` LLY 核心分子 tirzepatide 是 **GIP/GLP-1 双受体激动剂**，糖尿病商品名 **Mounjaro**、减重商品名 **Zepbound**（2023 年底美国获批上市）→ 置信度：高 | time_sensitivity：静态
- `[fact-03]` Zepbound 减重幅度在 SURMOUNT 试验约 **−20%~−22.5%**（最高剂量），优于司美格鲁肽的 ~−15%（Wegovy）→ 置信度：高 | time_sensitivity：静态（已读出试验）
- `[fact-04]` Mounjaro+Zepbound 合计已成 LLY 第一大增长引擎，2024 起放量极快；Zepbound 2024 年首个完整销售年快速上量 → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-05]` **orforglipron**：LLY 的口服小分子 GLP-1（非肽类），无需冷链/注射、可规模化生产，被视为 GLP-1 普及的关键武器；Phase 3（ATTAIN 减重 / ACHIEVE 糖尿病）2025 年陆续读出 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-06]` **retatrutide**：LLY 三靶点激动剂（GIP/GLP-1/胰高血糖素），Phase 2 减重达 ~−24%，Phase 3 进行中，被视为减重"下一代天花板" → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-07]` Trulicity（dulaglutide）：LLY 老一代周制剂 GLP-1（糖尿病），随 Mounjaro 上量而份额下滑 → 置信度：中 | time_sensitivity：慢变
- `[fact-08]` tirzepatide 一度列入 FDA 短缺清单，2024 年下半年 FDA 宣布**移出短缺清单**（供给追上），随后压缩复方药房（compounding）合法空间 → 置信度：中 | time_sensitivity：**快变** ⚠️

### B. 其他治疗领域管线（全管线视角）

- `[fact-09]` **donanemab（商品名 Kisunla）**：抗 β-淀粉样蛋白单抗，早期阿尔茨海默病，2024-07 美国 FDA 获批 → 置信度：中 | time_sensitivity：慢变（已获批，但海外/放量属快变）
- `[fact-10]` **Verzenio（abemaciclib）**：CDK4/6 抑制剂，HR+/HER2− 乳腺癌（含辅助治疗），LLY 肿瘤台柱，年销已达数十亿美元级 → 置信度：中 | time_sensitivity：慢变
- `[fact-11]` **Jardiance（empagliflozin）**：SGLT2 抑制剂，与勃林格殷格翰（Boehringer Ingelheim）合作分成；糖尿病/心衰/肾病 → 置信度：中 | time_sensitivity：慢变
- `[fact-12]` **Taltz（ixekizumab）**：IL-17A 单抗，银屑病/银屑病关节炎；**Omvoh（mirikizumab）**：IL-23，溃疡性结肠炎/克罗恩 → 置信度：中 | time_sensitivity：慢变
- `[fact-13]` **Ebglyss（lebrikizumab）**：IL-13 单抗，特应性皮炎，2024 美国获批 → 置信度：低 | time_sensitivity：慢变
- `[fact-14]` LLY 通过并购补管线：收购 Loxo Oncology（精准肿瘤）、Dice（口服免疫）、Point Biopharma（放射配体疗法 RLT）、Versanis、Morphic（口服整合素，免疫）等 → 置信度：低 | time_sensitivity：慢变
- `[fact-15]` 胰岛素老业务（Humalog 等）仍在，但占比下降、受 IRA 价格压制 → 置信度：中 | time_sensitivity：慢变

### C. 财务与估值（高时效，需重点校准）

- `[fact-16]` LLY 2024 全年营收约 **$45B 量级**（同比强劲增长，GLP-1 驱动）→ 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-17]` 2025 营收市场预期跳升至 **$58-62B 量级**（高速增长延续）→ 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-18]` 毛利率约 **~80%+**（大药企典型），但 GLP-1 早期产能爬坡曾压制毛利 → 置信度：中 | time_sensitivity：慢变
- `[fact-19]` 估值长期处于大药企罕见高位：远期 P/E 一度 **~50-60x**，市场给"超级成长"溢价 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-20]` LLY 股价 2023-2024 大涨，市值一度逼近/突破 **$700B-$1T 量级**，长期居全球市值最高药企 → 置信度：低（具体数字必须校准）| time_sensitivity：**快变** ⚠️
- `[fact-21]` 资本配置：大幅扩产 capex（见 fact-23）+ 持续分红 + 适度回购；杠杆温和 → 置信度：低 | time_sensitivity：快变

### D. 产能 / 供给（命门候选）

- `[fact-22]` GLP-1 需求一度远超产能，2023-2024 主要瓶颈在**注射笔灌装/制剂产能**而非原料药 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-23]` LLY 公布数十亿美元产能扩张：印第安纳 Lebanon 园区、北卡 Concord、Research Triangle Park、爱尔兰 Limerick、德国等多个新厂；累计宣布投资达数百亿美元级 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-24]` 口服 orforglipron 若获批，可绕开注射笔灌装瓶颈、大幅放量（产能逻辑反转）→ 置信度：中 | time_sensitivity：快变

### E. 竞争格局（慢变为主，个别快变）

- `[fact-25]` 头号对手 **Novo Nordisk（NVO）**：semaglutide（Ozempic 糖尿病 / Wegovy 减重 / Rybelsus 口服），与 LLY 形成 GLP-1 双寡头 → 置信度：高 | time_sensitivity：慢变
- `[fact-26]` Novo 下一代 **CagriSema**（cagrilintide+sema）2024-12 Phase 3 读出 ~−22%，**低于市场预期的 ~25%**，NVO 当日大跌——利好 LLY 相对地位 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-27]` 第二梯队在研减重药：Amgen **MariTide**（月制剂，Phase 3）、Viking **VK2735**（口服+注射）、Roche（收购 Carmot）、Pfizer danuglipron（口服，曾受挫）、Structure、Boehringer survodutide → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-28]` 减重适应症长期外延：MASH/NASH、心血管结局（SELECT 类）、睡眠呼吸暂停、肾病、HFpEF 等——适应症扩张驱动支付方覆盖 → 置信度：中 | time_sensitivity：快变

### F. 政策 / 支付（命门候选）

- `[fact-29]` **IRA Medicare 价格谈判**：礼来 Jardiance 入选首批谈判（2026 生效价）；后续批次可能纳入更多产品 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-30]` **Medicare 是否覆盖减重药**：传统上 Medicare Part D 不覆盖单纯减肥药；CMS 2024-11 曾提出拟覆盖肥胖药的规则，但在新政府下前景不明——这是 GLP-1 美国可及性的关键政策变量 → 置信度：低 | time_sensitivity：**快变** ⚠️

### 第一节统计（落盘前自检）
- **静态**：fact-01, 02, 03 → 3 条
- **慢变**：fact-07, 09, 10, 11, 12, 13, 14, 15, 18, 25 → 10 条
- **快变 ⚠️**：fact-04, 05, 06, 08, 16, 17, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30 → **17 条**
- 其中"快变 + 置信度高/中"：fact-04, 05, 06, 08, 16, 19, 22, 26, 28, 30（约 10 条）→ 第五节必须逐条对应 query

## 二、关键人物 / 公司 / 产品

- **David A. Ricks** — LLY 董事长兼 CEO，主导 GLP-1 时代扩产与并购战略
- **Daniel Skovronsky** — 首席科学官/Lilly Research Labs 总裁（研发掌门，donanemab/管线推手）→ 置信度 低
- **tirzepatide（Mounjaro/Zepbound）** — 当前最重要资产，双引擎
- **orforglipron** — 口服 GLP-1，最关键的"下一个 catalyst"
- **retatrutide** — 三靶点，减重天花板候选
- **donanemab（Kisunla）** — 阿尔茨海默，打开 CNS 第二曲线
- **Novo Nordisk** — 唯一对等竞争者（GLP-1 双寡头）
- **Boehringer Ingelheim** — Jardiance 合作方（分成）

## 三、产业链 / 竞争格局认知

**主线**：LLY 已从"传统多元化大药企"转型为"GLP-1 减重降糖超级成长股"。Mounjaro/Zepbound 的临床优效（减重幅度领先）+ 巨大未满足需求（全球肥胖/糖尿病人口）构成核心叙事。市场把 LLY 当作"医药界的成长龙头"给极高估值，赌的是 GLP-1 类市场在 2030 年前后达到 $1000 亿+ 量级、且 LLY 与 Novo 维持双寡头。

**竞争层**：GLP-1 减重赛道当前是 LLY vs Novo 双寡头，LLY 在分子优效（tirzepatide > semaglutide 减重数据）和下一代管线（orforglipron 口服 + retatrutide 三靶点）上略占上风。Novo CagriSema 读出不及预期进一步巩固了 LLY 的相对地位。第二梯队（Amgen MariTide、Viking、Roche、Pfizer）多在 Phase 1-3，2027 年前难撼动双寡头，但口服小分子赛道（orforglipron vs 后来者）是中期竞争焦点。

**供给/产能层**：过去两年的核心矛盾是"需求远超产能"，制约的是注射制剂灌装而非有效成分。LLY 砸数百亿美元扩产，并把口服 orforglipron 视为绕开灌装瓶颈的杀手锏。产能从瓶颈变为充裕的拐点，会同时影响放量斜率与定价/竞争烈度。

**支付/政策层**：美国 GLP-1 减重的天花板很大程度取决于支付方覆盖——商业保险逐步纳入，但 Medicare 对肥胖药的覆盖尚未落定（政策变量）。IRA 价格谈判则是长期利润率的结构性压力。海外（欧洲/中国）可及性与定价是增量但单价低。

**全周期视角**：LLY 的"质量"问题在于——这究竟是一个可持续数十年的 franchise（像胰岛素/CDK4/6 那样有黏性与适应症外延），还是一个会被口服化/价格战/专利到期侵蚀的高峰利润？tirzepatide 化合物专利相对较长（~2036-2039，需校准），但口服替代与生物类似药/小分子仿制的长期侵蚀路径需要厘清。

## 四、训练知识盲点（自我承认）

- **最新财务数字**：2025 各季度及全年实际营收/EPS、2026Q1 业绩——训练时只有估计，必须校准
- **股价与市值/估值倍数**：当前 LLY 股价、市值、远期 P/E 全部需要校准（fact-20 置信度低）
- **orforglipron Phase 3 实际读出结果**：ATTAIN（减重）/ ACHIEVE（糖尿病）2025 年的具体数据（减重幅度、安全性、是否达标）——这是最关键的未知，可能已读出
- **retatrutide Phase 3 进度与任何中期数据**
- **FDA/EMA 监管时间表**：orforglipron 申报/获批节奏、donanemab 海外（欧盟/日本/中国）获批状态
- **Medicare 肥胖药覆盖最终决定**：CMS 规则在 2025-2026 新政府下的命运
- **IRA 谈判后续批次**：哪些 LLY 产品入选、价格影响量级
- **产能扩张兑现进度**：宣布的工厂哪些已投产、实际产出爬坡
- **竞争最新动态**：Amgen MariTide Phase 3 数据、Novo 反击（口服 sema 高剂量获批？下一代分子）、中国玩家（信达/华东等）GLP-1 进展对全球格局的边际影响
- **专利到期精确时间表**：tirzepatide 各国 COM 专利、Verzenio、关键产品 LOE
- **诉讼/安全性**：GLP-1 长期安全性信号（甲状腺、胰腺炎、视神经病变 NAION、肌肉流失、停药反弹）的最新证据与监管态度
- **资本配置细节**：实际 capex 节奏、并购最新动作、分红/回购政策

## 五、需要 web-search 校准的优先项

> 强制：第一节"快变 + 高/中"约 10 条 fact 每条至少一个对应 query。以下按优先级排（P0 先跑）。

**P0（最可能蒙蔽 thesis）**
1. `Eli Lilly orforglipron Phase 3 ATTAIN ACHIEVE results 2025 weight loss data`（fact-05，最关键未知）
2. `Eli Lilly LLY stock price market cap forward PE June 2026`（fact-19/20，估值锚）
3. `Eli Lilly Q1 2026 earnings revenue Mounjaro Zepbound sales`（fact-04/16/17，最新业绩）
4. `Eli Lilly 2025 full year revenue results tirzepatide sales`（fact-16/17）
5. `Medicare coverage anti-obesity drugs CMS final rule 2025 2026 GLP-1`（fact-30，政策变量）

**P1（结构性变量）**
6. `Eli Lilly retatrutide Phase 3 timeline triple agonist 2025 2026`（fact-06）
7. `Novo Nordisk CagriSema vs Lilly competitive 2025 next gen obesity pipeline`（fact-26）
8. `Amgen MariTide Phase 3 results 2025 obesity Viking VK2735 competition`（fact-27）
9. `Eli Lilly manufacturing capacity expansion 2025 2026 Lebanon Indiana new plants progress`（fact-23）
10. `tirzepatide patent expiration date composition of matter LLY loss of exclusivity`（专利盲点）

**P2（补充）**
11. `Eli Lilly donanemab Kisunla sales launch 2025 EU Japan approval Alzheimer`（fact-09）
12. `IRA Medicare drug price negotiation Eli Lilly Jardiance 2026 second batch`（fact-29）
13. `GLP-1 safety long term NAION muscle loss discontinuation 2025 FDA`（安全性盲点）
14. `Eli Lilly orforglipron oral GLP-1 FDA approval timeline filing 2026`（监管节奏）

## 六、prescan 校准结果（2026-06-12 回写）

> Step 4.5 prescan 入库 ~33 份 web-search material（16 query，hit_rate 100%）后，对照第一节 fact-NN 的更新。**被推翻条目 thesis_v0 不准再引原 fact，须 cite 新 mat_id。**

### 被推翻 / 重大上修（thesis_v0 改用新数）
- `[fact-17]` 训练时"2025 营收 $58-62B" → `[mat-114ad2]`/`[mat-cdd684]` 实际 **$65.2B**（同比 +45%，2024 $45B 确认）→ 上修，估值锚必须用此
- `[fact-19]` 训练时"远期 P/E ~50-60x" → `[mat-2f80fb]` 当前**远期 P/E ~30.9x**（EPS 暴涨摊薄倍数，估值认知必须重置——不再是"50x 极端高估"，是"30x 高成长溢价"）
- `[fact-20]` 训练时"市值逼近 $700B-$1T" → `[mat-114ad2]` 股价 **~$1003-1075（2026-02-04）**，市值 ~$1T 量级；LLY 仍居全球最高市值药企
- `[fact-23]` 训练时"扩产数百亿美元级" → `[mat-048055]` 新增 **$27B 建 4 个新厂**；`[mat-eeecf3]` 自 2020 起累计美国产能投资 **>$50B**；`[mat-4bdb51]` 新建 $6.5B 德州 API 厂
- `[fact-05]` orforglipron Phase 3 → `[mat-11d170]`/`[mat-629fe7]` **ATTAIN-1 减重 ~12%（27.3 lbs）**，三个 Phase 3 全部成功、年内启动全球申报；`[mat-9eea24]` FDA **Q2 2026 决定**（即当下）、T2D 申报在轨 → ⚠️关键：口服减重幅度 ~12% **显著低于** 注射 tirzepatide ~20%，是"可及性换效力"的权衡
- `[fact-06]` retatrutide Phase 3 → `[mat-484fca]`/`[mat-b63ac0]` 首个 Phase 3 **减重 28.7%（71.2 lbs）+ 骨关节炎疼痛缓解** → best-in-class 确认，减重天花板进一步抬高
- `[fact-30]` Medicare 肥胖药覆盖 → `[mat-d48fb3]` CMS **不将肥胖药纳入常规 Medicare/Medicaid 2026**；但 `[mat-3fc7d5]`/`[mat-633bc1]` **GLP-1 Bridge 短期示范延长至 2027-12-31**（Part D 受益人 2026-07-01 起获选定 GLP-1 肥胖覆盖，$50/月 copay），BALANCE Model 无限期推迟 → 比"完全不覆盖"乐观，但仍是临时/受限

### 被验证（置信度提升）
- `[fact-04]` Mounjaro+Zepbound 为第一引擎 → `[mat-08e1e4]` Q1'26 合计 **$12.8B**（占总营收 $19.8B 的 65%），同比 +56% → 高+
- `[fact-16]` 2024 营收 ~$45B → `[mat-114ad2]` 确认 $45B → 高
- `[fact-26]` Novo CagriSema 不及预期 → `[mat-6a2b41]` Bloomberg "Novo 下一代减重针不及 Lilly 对手"；`[mat-114ad2]` Novo 警告 2026 销售或降 13% → 高，Novo 弱势比训练时更深
- `[fact-09]` donanemab(Kisunla) → `[mat-471461]`/`[mat-3e0c97]` **欧盟（EC）获批**（CHMP 初拒后逆转）→ 海外打开
- `[fact-08]` tirzepatide 移出短缺清单 → `[mat-cec370]` 共和党政府在 compounding 纠纷中维持 LLY 独占立场（利好）→ 验证
- `[fact-27]` 第二梯队 → `[mat-0364f2]` Viking VK2735 Phase 3 VANQUISH-1 入组完成(2025-11)；`[mat-b77ae5]` Amgen MARITIME Phase 3 → 在轨但落后

### 新增事实（baseline 未覆盖，prescan 浮现）
- `[mat-f804e6]`/`[mat-08e1e4]` **Q1 2026 业绩**：营收 $19.8B(+56%)，非 GAAP EPS $8.55(vs $3.34 Q1'25)，performance margin 50%(↑7pct)，股价当日 +~10%；美国 incretin 肥胖处方 +80%
- `[mat-499ce0]`/`[mat-114ad2]` **2026 指引**：营收 $80-83B，非 GAAP EPS $35.50-37.00（年内 raise $2）
- `[mat-d9588d]` **资本配置信号**：Lilly 拟用 GLP-1 现金流做 **M&A + 多元化管线**（环⑤资本配置关键）
- `[mat-15394f]`/`[mat-0f8bef]` **安全性**：NANOS+AAO 就 GLP-1 与 NAION(非动脉炎性前部缺血性视神经病变)风险发共识声明 → 长期安全性监测项
- `[mat-fbcd3f]` EBGLYSS(lebrikizumab) 获 FDA q8w 维持剂量批准（免疫管线小幅推进）

### 仍未校准（thesis 引用标 uncertain）
- tirzepatide/Zepbound 各国 COM 专利精确到期表（`[mat-d9504]` 有线索但需厚料确认，"2026 GLP-1 专利到期"措辞含混，疑指他药）
- IRA 第二批谈判是否含更多 LLY 产品（`[mat-5a7906]` 仅首批结果）
- 实际 FCF / capex 现金流节奏、净杠杆（fact-21 仍低置信，待年报）

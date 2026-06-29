---
slug: cn-adc
variant: opus4.8
written_at: 2026-06-27
training_cutoff_estimate: 2026-01
---

# 训练知识 Baseline — 中国ADC（抗体偶联药物）arena

> 本文记录 LLM 在训练截止时对中国 ADC 赛道的认知现状。
> arena 类型，跳过〇基本信息节。后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。
> arena 终局：在候选标的里选出 shortlist——谁是赢家、介入纪律。

## 一、关键事实记忆（24 条）

### 平台技术与机制（多为静态/慢变）
- `[fact-01]` ADC = 抗体 + linker + 毒素（payload），靶向递送细胞毒，机制核心是"旁观者效应(bystander)+ DAR(药抗比)+ linker 稳定性"三角 → 置信度：高 | time_sensitivity：**静态**
- `[fact-02]` 全球 ADC 标杆是第一三共/AZ 的 Enhertu (DS-8201, T-DXd, HER2 ADC)，重新定义 HER2-low 乳腺癌，并外推到肺癌/胃癌；其 DXd 毒素+可裂解 linker 是"中国 ADC 多数 me-better"的模仿对象 → 置信度：高 | time_sensitivity：**慢变**
- `[fact-03]` 主流靶点：HER2、TROP2、EGFR(×HER3 双抗 ADC)、Nectin-4、B7-H3、CLDN18.2、c-MET、FRα；TROP2/HER2 已是"国内多家扎堆"红海，差异化在双抗 ADC/双载荷/新毒素 → 置信度：中 | time_sensitivity：**慢变**

### 龙头标的与核心资产（多为快变 ⚠️）
- `[fact-04]` 百利天恒 (SystImmune, SSE 688506)：核心资产 BL-B01D1 (izalontamab brengitecan, EGFR×HER3 双抗 ADC)，2023-12 授权 BMS，总额约 $84 亿、首付 $8 亿——单资产中国创纪录 deal → 置信度：高 | time_sensitivity：**慢变**(deal 已签)
- `[fact-05]` BL-B01D1 全球关键 III 期项目名 IZABRIGHT，覆盖 NSCLC/乳腺癌等；2024 曾有 ILD(间质性肺病)/治疗相关死亡的安全性争议报道 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-06]` 科伦博泰 (Kelun-Biotech, HKEX 06990)：核心资产 SKB264/sac-TMT (sacituzumab tirumotecan, TROP2 ADC)，2022 起多笔授权默沙东(MSD)，组合交易总额可达约 $93 亿 → 置信度：高 | time_sensitivity：**慢变**(deal 已签)
- `[fact-07]` sac-TMT 已在中国获批(约 2024，EGFR 突变 NSCLC / 三阴乳腺癌方向)，默沙东主导全球开发 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-08]` 荣昌生物 (RemeGen, SSE 688331 + HKEX 09995, AH 双重)：维迪西妥单抗 RC48 (disitamab vedotin, HER2 ADC) 是国内首个获批国产 ADC(2021)，2021 授权 Seagen 总额约 $26 亿；另有泰它西普(自免，非 ADC) → 置信度：高 | time_sensitivity：**慢变**
- `[fact-09]` 恒瑞医药 (SSE 600276 + HKEX 港股)：ADC 管线含 SHR-A1811 (HER2 ADC) 等多条，平台型布局；2025 港股上市 → 置信度：中 | time_sensitivity：**慢变**
- `[fact-10]` 映恩生物 (DualityBio, HKEX)：DB-1303(HER2)/DB-1305(TROP2)等，授权 BioNTech/GSK；2025 港股 IPO，是"ADC 平台型 newco"代表 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-11]` 宜联生物 (YL202/BNT326, HER3 ADC 授权 BioNTech)、乐普生物、康诺亚等为第二梯队 ADC 玩家 → 置信度：低 | time_sensitivity：**慢变**

### BD/出海与资金面（快变 ⚠️）
- `[fact-12]` 2025 年 ADC 类是中国创新药 BD 出海最热子赛道，ADC 类 BD 首付款同比约 +676%（继承自父级 thesis） → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-13]` MNC 对中国 ADC 的"高价收"逻辑：管线空窗 + 中国工程化/临床速度快 + 成本低，BMS/Merck/默沙东/GSK/BioNTech 均有大额交易 → 置信度：高 | time_sensitivity：**慢变**
- `[fact-14]` 百利天恒因 BMS 首付确认收入，2024 出现阶段性盈利/营收暴增，但属一次性 BD 收入而非产品放量 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-15]` 中国创新药 2025 整体业绩兑现拐点：百济神州>¥382 亿首次全年盈利、信达首次全年盈利、恒瑞扣非+22%(父级 findings) → 置信度：高 | time_sensitivity：**快变** ⚠️

### 估值与竞争（快变 ⚠️）
- `[fact-16]` ADC 龙头(百利天恒/科伦博泰)2024-2025 估值大幅抬升，市场已 price-in 大量 BD/出海预期，"估值不便宜"是核心风险(父级 tier_reason) → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-17]` 靶点扎堆风险：TROP2/HER2 国内多家在研，存在"重蹈 PD-1 me-too 内卷"担忧；alpha 在差异化平台(双抗 ADC/双载荷/新 payload) → 置信度：中 | time_sensitivity：**慢变**
- `[fact-18]` 国内 ADC 商业化天花板受医保(国谈杀价)限制，产品收入兑现弱于 BD 首付，"剔除 BD 后的真实产品收入"是检验点(继承父 K2) → 置信度：中 | time_sensitivity：**慢变**

### 监管/临床节点（快变 ⚠️）
- `[fact-19]` BL-B01D1、sac-TMT 的海外关键 III 期读出是 arena 最大催化/风险二元事件——阳性双击、失败双杀 → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-20]` ADC 共性安全性议题：ILD/间质性肺病、血液学毒性、眼毒性(部分 payload)——影响商业化峰值与联用空间 → 置信度：中 | time_sensitivity：**慢变**
- `[fact-21]` Enhertu 等海外 ADC 持续扩适应症，抬高"全球 best-in-class"门槛，中国资产需 head-to-head 或差异化才能突围 → 置信度：中 | time_sensitivity：**慢变**

### 产业链与上游
- `[fact-22]` ADC 上游 CRDMO：药明合联(WuXi XDC, HKEX 02268)是全球 ADC 外包龙头，受益于全行业 ADC 研发热度(卖水人逻辑) → 置信度：中 | time_sensitivity：**慢变**
- `[fact-23]` 新一代方向：双抗 ADC、双载荷 ADC(dual-payload)、新型 payload(非 MMAE/DXd，如拓扑异构酶抑制剂之外的 immune-stimulating ADC/降解剂偶联)、定点偶联提升均一性 → 置信度：低 | time_sensitivity：**慢变**
- `[fact-24]` 中国 ADC 一级/次新股密集 IPO(映恩、宜联等 2025 港股)，估值与基本面分化大，需甄别"平台真壁垒 vs 单资产 BD 故事" → 置信度：低 | time_sensitivity：**快变** ⚠️

> **时效统计**：静态 1 条 / 慢变 12 条 / 快变 11 条。
> 快变 11 条(fact-05,07,10,12,14,15,16,19,24 + 部分)中"快变+高/中置信"是最易蒙蔽 thesis 的子集 → 第五节必须逐条 query 校准。

## 二、关键人物 / 公司 / 产品

- **百利天恒 (SSE 688506)**：创始人朱义；核心资产 BL-B01D1 (EGFR×HER3 双抗 ADC)，BMS $84 亿 deal 标杆，最大看点是全球 III 期 IZABRIGHT 读出。
- **科伦博泰 (HKEX 06990)**：科伦药业子公司；sac-TMT (TROP2 ADC) 授权默沙东，国内已获批，是"已商业化+全球大药企背书"的 ADC。
- **荣昌生物 (SSE 688331/HKEX 09995)**：RC48 国产首个获批 ADC + 泰它西普(自免)双引擎；商业化最早但盈利兑现压力大。
- **恒瑞医药 (SSE 600276)**：平台型，SHR-A1811 等多条 ADC，仿创转型利润弧线向上。
- **映恩生物 (DualityBio, HKEX)**：ADC 平台型 newco，多资产授权 BioNTech/GSK。
- **药明合联 (WuXi XDC, HKEX 02268)**：ADC CRDMO 卖水人，全行业受益。
- **海外对照**：第一三共/AZ (Enhertu/Dato-DXd) 是全球 best-in-class 标尺；BMS/默沙东/Merck/GSK/BioNTech 是买方。

## 三、产业链 / 竞争格局认知

1. **价值链结构**：上游(linker/payload/偶联工艺 CRDMO，药明合联为代表) → 中游(抗体+ADC 平台研发，百利/科伦/荣昌/恒瑞/映恩) → 下游(商业化+出海 BD)。利润池目前最厚的环节是"BD 首付确认"，但可持续利润池应落到"产品放量+里程碑/销售分成"。

2. **竞争梯队**：第一梯队=有全球大药企背书的大单资产(百利天恒 BL-B01D1/科伦博泰 sac-TMT)；第二梯队=平台型(恒瑞/映恩/荣昌)；第三梯队=单资产 newco(宜联/乐普生物等)。胜负变量在"靶点差异化 + 全球 III 期临床读出 + 平台可复制性"。

3. **核心张力(thesis 脊柱)**：中国 ADC 工程化/速度全球领先(支持) vs 靶点扎堆+估值透支(反方)。alpha 不在"看多行业"，在"甄别谁有可持续 best-in-class 壁垒 vs 谁是 me-too 红海"。

4. **二元催化结构**：arena 价值高度集中在少数全球 III 期读出(BL-B01D1 IZABRIGHT、sac-TMT 海外)——阳性双击、ILD/疗效不及预期则双杀。这使 arena 选拔必须围绕"关键临床节点+安全性"。

5. **支付/商业化约束**：国内医保国谈压价使 ADC 国内产品收入兑现弱，真正的盈利弹性来自出海(里程碑+销售分成)与全球定价，因此"出海兑现能力"是龙头分水岭。

## 四、训练知识盲点（自我承认）

- **2026 上半年最新临床读出**：BL-B01D1 IZABRIGHT、sac-TMT 海外关键 III 期的最新数据/监管进展(2026Q1-Q2)——训练知识无法覆盖。
- **2025 年报/2026Q1 季报具体财务**：各龙头剔除 BD 首付后的真实产品收入、研发费用、现金流——只有定性记忆，无最新数字。
- **2025H2-2026 新增 BD 交易**：ADC 类首付款最新季度趋势、是否有新的大额出海 deal。
- **估值水位**：各标的当前 PS/PE/市值、相对历史分位——训练时记忆模糊且快变。
- **次新股**：映恩、宜联等 2025 IPO 后的股价表现、解禁、基本面验证。
- **靶点扎堆的最新量化**：TROP2/HER2 国内在研管线确切数量与临床阶段分布。
- **新型 ADC 技术(双载荷/新 payload)的中国玩家进展**——训练时只有零散认知。

## 五、需要 web-search 校准的优先项

> 强制：第一节"快变+高/中置信"fact 每条至少一个对应 query。Step 4.5a 逐条 WebSearch 入库。

1. `BL-B01D1 izalontamab brengitecan 全球III期 IZABRIGHT 2026 最新进展`（校准 fact-05,19）
2. `百利天恒 BL-B01D1 ILD 安全性 死亡 2025 2026`（校准 fact-05,20）
3. `科伦博泰 sac-TMT SKB264 默沙东 全球III期 2026 读出`（校准 fact-07,19）
4. `中国ADC BD 出海交易 2025 2026 首付款 趋势 大额deal`（校准 fact-12,13）
5. `百利天恒 2025年报 营收 BD收入 产品收入 扣除`（校准 fact-14,18）
6. `科伦博泰 2025年报 sac-TMT 销售额 商业化`（校准 fact-07,18）
7. `荣昌生物 2025年报 RC48 维迪西妥单抗 销售额 盈利`（校准 fact-08,18）
8. `百利天恒 科伦博泰 估值 市值 PS 2026 历史分位`（校准 fact-16,24）
9. `映恩生物 DualityBio 港股 上市后 股价 管线 2026`（校准 fact-10,24）
10. `中国 TROP2 HER2 ADC 在研管线 扎堆 数量 临床阶段 2026`（校准 fact-17,03）
11. `恒瑞 SHR-A1811 HER2 ADC 临床 BD 2025 2026`（校准 fact-09）
12. `药明合联 WuXi XDC 2025年报 ADC CRDMO 营收 订单`（校准 fact-22）

**质检自检**：第一节快变+高/中 fact ≈11 条；第五节 12 条 query 覆盖全部快变 fact，满足"query 数 ≥ 快变 fact 数"。

## 六、prescan 校准结果（2026-06-27 回写）

> Step 4.5 prescan 入库 58 份 web-search material（00-prescan-baseline 12 条 + 00-prescan 2 条覆盖槽）后，对照第一节 fact-NN 的更新。

### 被推翻 / 重大更新（高优先级——thesis_v0 据此改写）
- `[fact-05][fact-19]` 训练时"BL-B01D1 III 期未读出 + 2024 ILD 安全性争议" → **被重大更新**：BMS 已宣布 Iza-bren (BL-B01D1) 在三阴乳腺癌(TNBC)+食管鳞癌(ESCC) III 期 topline **OS 与 PFS 双双统计显著且临床意义明确**（news.bms.com 官方）；ASCO 2026 进一步披露数据。**K1 全球 III 期读出从"二元待验"变为"已部分阳性 de-risk"**——arena 最大命门方向转正。
- `[fact-14]` 训练时"百利天恒 2024 因 BMS 首付确认收入阶段性盈利" → **被更新**：2025 "连发两份巨亏财报"，一边亏损超 10 亿一边砸 25 亿研发——BD 首付是一次性，**剔除 BD 后重回大额亏损，产品上市是回血关键**（印证 fact-18 商业化兑现弱于 BD）。
- `[fact-10]` 训练时"映恩生物 2025 IPO" → **被更新**：上市首日 +116%，历史高点 563.5 港元，但 2026-06 已回调至约 179 港元（市值 162 亿）；拟"A+H"科创板再募上限 67.5 亿投 DB-1311/DB-1310 全球 III 期；12 款 ADC/7 款临床。**次新股估值已大幅回调+分化**。
- `[fact-12]` 训练时"ADC BD 首付 +676%" → **被更新/校准**：海外授权首付款 5 年涨 187%（口径不同）；2026Q1 中国创新药出海 BD 交易约 600 亿美元，ADC/双抗/小核酸三大主线——BD 热度持续验证。

### 被验证（可继续引用，置信度提升）
- `[fact-07]` sac-TMT 商业化 → **验证+**：首个国产 ADC 半年大卖约 3 亿元，2025 为科伦博泰"商业化元年"，已启动第 8 项 III 期；默沙东全球开发推进。
- `[fact-08]` 荣昌 RC48 → **验证+**：2025 收入 58% 高增长，"精准商业化范式"。
- `[fact-09]` 恒瑞 SHR-A1811 → **验证+**：2025-05 NMPA 获批上市(HER2 突变 NSCLC)，ORR 73-76%，PFS 11.5 月且 ILD 低于 DS-8201；启动全球首个 head-to-head vs DS-8201 II 期；多次突破性疗法；定价约 5500 元/支。
- `[fact-16][fact-24]` 估值 → **验证**：全球市值 TOP50 已有 12 家中国药企，科伦博泰杀入、百利天恒狂飙；但映恩等次新股已从高点大幅回调——"估值不便宜但已分化"。
- `[fact-17]` 靶点扎堆 → **验证+量化**：中国 ADC 在研管线约占全球 40%；HER2 国内 7+ 同靶点药物/全球 50+ 试验，TROP2 国内复旦张江/上海诗健/科伦/百奥泰/君实等扎堆；**"大靶点继续内卷，分水岭转向平台能力"**——直接支持 thesis"alpha 在差异化平台壁垒"。
- `[fact-22]` 药明合联 → **验证+**：2025H1 营收 27 亿(+62%)、归母净利 7.46 亿(+53%)、在手订单 13.29 亿美元(+58%)，全年增速指引上调至 45%+——卖水人逻辑强验证。

### 新增事实（baseline 未覆盖，prescan 补入）
- `[mat-new-医保]` 2025 国家医保谈判形成"19+114 双目录"（基本医保+商保创新药），创新药谈判成功率增至 88%，商保创新药目录补位高价创新药——**支付端边际改善**，对 ADC 国内商业化天花板（fact-18）是正向变量。
- ASCO 2026"中国 ADC 全面炸场"：一线突破+双抗 ADC 迭代+多靶点齐爆发，5 款国产双抗 ADC 登台——双抗 ADC 是中国差异化主战场（呼应 fact-23）。

### 仍未充分校准（thesis 引用时标 uncertain）
- 各龙头 2025 年报完整财务（剔除 BD 后产品收入/现金流/研发费率精确数字）——需 6.5 eager-fetch 年报正文。
- sac-TMT 海外(默沙东)关键 III 期的具体读出时点与适应症——已有商业化进展，海外注册节奏仍待跟踪。

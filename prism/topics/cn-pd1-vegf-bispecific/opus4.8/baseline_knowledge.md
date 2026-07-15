---
slug: cn-pd1-vegf-bispecific
variant: opus4.8
written_at: 2026-07-10
training_cutoff_estimate: 2026-01
---

# 训练知识 Baseline — 中国 PD-1/VEGF 双抗 arena

> 本文记录 LLM 在**训练截止时**对该 topic 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。
> arena 类型，跳过〇节基本信息。

## 一、关键事实记忆（22 条）

### 机制层（静态）
- `[fact-01]` PD-1/VEGF 双抗把免疫检查点抑制（PD-1/PD-L1）与抗血管生成（VEGF/VEGF-A）合并到单一分子；机理假设是 VEGF 阻断使肿瘤血管正常化并逆转免疫抑制微环境，与 PD-1 阻断协同 → 置信度：高 | time_sensitivity：**静态**
- `[fact-02]` 康方依沃西（ivonescimab/AK112）宣称有"协同/亲和力增强结合"——在 PD-1 存在时对 VEGF 结合更紧（avidity effect），这是康方主张的差异化机理 → 置信度：中 | time_sensitivity：**静态**
- `[fact-03]` VEGF 通路药物的类效安全性关注点：出血、蛋白尿、高血压、伤口愈合；PD-1/VEGF 双抗需监测联合安全性（尤其鳞癌出血）→ 置信度：中 | time_sensitivity：**静态**

### 标杆临床读出（快变 ⚠️）
- `[fact-04]` 依沃西 HARMONi-2（中国 Ph3，1L PD-L1 阳性 NSCLC，单药 vs 帕博利珠单抗/K药单药）PFS 达标、head-to-head 击败 K 药，2024-09 WCLC 公布，HR 约 0.5 量级——史上首个头对头战胜 K 药单药的分子 → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-05]` 依沃西 HARMONi（全球 Ph3，EGFR 突变 NSCLC 经 TKI 治疗后，依沃西+化疗 vs 化疗）2025 年中 topline：PFS 阳性，但 **OS 未达统计学显著**——引发 Summit 股价大跌，是美国注册的关键悬念 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-06]` 依沃西在中国已获批（NSCLC 相关适应症，EGFR-TKI 经治），并向 1L PD-L1+ 扩展；具体获批时点/适应症边界记忆模糊 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-07]` 依沃西全球注册研究还有 HARMONi-3（1L 鳞/非鳞 NSCLC 联合方案）、HARMONi-6（中国鳞癌，PFS 报阳）等在读 → 置信度：中 | time_sensitivity：**快变** ⚠️

### BD/授权交易（快变 ⚠️——arena 竞争格局核心）
- `[fact-08]` 康方将依沃西美/加/欧/日权益授权 Summit Therapeutics（SMMT），首付约 $500M + 里程碑至约 $45 亿（2022 年签）→ 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-09]` 辉瑞（Pfizer）2025-05 从三生制药（3SBio, HKEX_01530）授权 SSGJ-707（PD-1/VEGF 双抗）：首付约 $12.5 亿 + 里程碑，外加股权投资——当时中国创新药最大单笔首付之一 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-10]` BioNTech 2024-11 收购普米斯（Biotheus）获得 PM8002（=BNT327，PD-L1/VEGF 双抗）；随后 2025-06 BioNTech 与 BMS 就 BNT327 达成全球共同开发，首付 + 里程碑合计超 $100 亿量级 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-11]` 默克（MSD/Merck）2024-11 从礼新医药（LaNova）授权 LM-299（PD-1/VEGF），首付约 $5.88 亿 + 里程碑至约 $27-30 亿 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-12]` 2024H2–2025 PD-(L)1/VEGF 双抗成为中国创新药 out-licensing 最热靶点，多笔 10 亿美元级首付集中出现 → 置信度：中 | time_sensitivity：**快变** ⚠️

### 玩家/管线（慢变+快变混合）
- `[fact-13]` 康方生物（Akeso，HKEX_09926）是本 arena 中国标杆，依沃西为核心资产，另有卡度尼利（PD-1/CTLA-4 双抗）已商业化 → 置信度：中 | time_sensitivity：**慢变**
- `[fact-14]` 三生制药（HKEX_01530）SSGJ-707 是辉瑞交易标的，管线相对早期（辉瑞交易时约 Ph2 阶段）→ 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-15]` 普米斯 BNT327/PM8002 是 PD-L1/VEGF（非 PD-1/VEGF），已进多个实体瘤 Ph2/Ph3；BioNTech/BMS 推全球开发 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-16]` 其他跟进者：宜明昂科 IMM2510（PD-L1/VEGF）、恒瑞、齐鲁、神州细胞等有 PD-(L)1/VEGF 双抗布局，多处早期 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-17]` "MNC 自研入局"的实际形态：截至训练截止，MNC 主要是**授权/收购中国分子**（辉瑞买 707、BMS 买 BNT327、默克买 LM-299），纯自研 PD-1/VEGF 尚不突出——thesis 措辞"MNC 自研"需与"MNC 买中国分子"区分 → 置信度：中 | time_sensitivity：**快变** ⚠️

### 竞争/终局锚（慢变）
- `[fact-18]` 被挑战的标的是 K 药（帕博利珠单抗，Merck），全球年销 $250 亿+，NSCLC 是核心适应症——PD-1/VEGF 双抗的终极商业机会在于"能否取代 K 药/PD-1 单抗一线地位" → 置信度：高 | time_sensitivity：**慢变**
- `[fact-19]` K 药核心化合物专利约 2028 年到期，Merck 面临专利悬崖，正积极通过皮下剂型 + 外部引入（含 PD-1/VEGF）防御 → 置信度：中 | time_sensitivity：**慢变**
- `[fact-20]` 中国 PD-1 单抗历史殷鉴：2018-2021 扎堆（信达/君实/恒瑞/百济等），医保谈判 + 集采式竞争把价格打到全球最低，利润池被摧毁——PD-1/VEGF 是否重演是核心风险 → 置信度：高 | time_sensitivity：**慢变**

### 估值/财务（uncertain——训练不追踪）
- `[fact-21]` 康方生物、三生制药的具体市值/估值/现金/依沃西中国销售爬坡数字，训练时不可靠 → 置信度：uncertain | time_sensitivity：**快变** ⚠️
- `[fact-22]` Summit Therapeutics（SMMT）估值高度绑定依沃西全球读出，HARMONi OS miss 后波动大；具体股价不追踪 → 置信度：uncertain | time_sensitivity：**快变** ⚠️

**第一节统计**：静态 3 条 / 慢变 4 条 / 快变 15 条（其中"快变+高/中置信"约 10 条）。快变占比极高——本 arena 事实高度依赖 prescan 校准，尤其临床读出与 BD 交易两簇。

## 二、关键人物 / 公司 / 产品

- **康方生物 Akeso（HKEX_09926）** — 夏瑜/李百勇创立，依沃西（AK112）+ 卡度尼利双双为核心；本 arena 标杆企业。
- **Summit Therapeutics（SMMT）** — 美股，依沃西北美/欧/日权益持有者，Bob Duggan 主导；股价=依沃西全球读出的高 beta 代理。
- **三生制药 3SBio（HKEX_01530）** — SSGJ-707 授权辉瑞，交易前市场认知度较低，交易后重估。
- **普米斯 Biotheus** — 已被 BioNTech 收购，BNT327/PM8002（PD-L1/VEGF）进入 BMS 全球合作。
- **礼新医药 LaNova** — LM-299 授权默克。
- **辉瑞/BMS/默克** — 三家 MNC 通过买中国 PD-(L)1/VEGF 分子集中入局，是 arena 竞争升温的直接推手。

## 三、产业链 / 竞争格局认知

主线：PD-1/VEGF 双抗是"后 PD-1 单抗时代"最被看好的 IO 骨架升级方向，中国企业（尤其康方）在分子设计与临床速度上取得阶段性领先，2024-2025 演变为 MNC 集中授权/收购中国分子的浪潮。

竞争格局呈"一个标杆 + 多个被 MNC 收编的分子"结构：康方依沃西（+Summit）临床最领先、数据最硬；三生 707（+辉瑞）、普米斯 BNT327（+BMS）、礼新 LM-299（+默克）紧随其后并获顶级 MNC 背书与全球开发资源。这既是**壁垒验证**（MNC 用真金白银投票）也是**壁垒稀释**（后来者有 MNC 全球临床/商业化火力，可能追上先发）。

终局张力：机会锚在能否撼动 K 药/PD-1 单抗 $250 亿级一线地位（fact-18/19）；风险锚在中国 PD-1 单抗价格战殷鉴是否重演（fact-20）。arena shortlist 的关键胜负变量 = 临床数据梯度（OS 硬终点 + 全球注册）× BD 交易质量（首付/里程碑/分成/保留权益）× 适应症广度。

## 四、训练知识盲点（自我承认）

- **HARMONi 全球研究的最终 OS 结果与 FDA 沟通/BLA 时点**——训练时只知 topline OS miss，不知后续成熟数据与监管路径。
- **依沃西中国获批适应症的确切边界与销售爬坡**——具体批文/时点/销售额不可靠。
- **各笔 BD 交易的确切条款**（首付、里程碑分层、销售分成、保留区域），记忆为量级估计，非精确数。
- **2025H2–2026 新增交易/新入局者**——训练截止后可能有新 deal 或 MNC 纯自研进展。
- **HARMONi-2 的 OS 成熟数据**（PFS 已知阳性，OS 是能否真正取代 K 药的关键，训练时未成熟）。
- **康方/三生的最新估值、现金、财务**——不追踪。
- **安全性长期随访**（VEGF 相关出血/蛋白尿在大样本中的表现）。

## 五、需要 web-search 校准的优先项

> 强制规则：第一节所有"快变+高/中置信"fact 必须有对应 query。

1. `康方 依沃西 HARMONi 全球三期 OS 最终结果 2025 2026 Summit`（校准 fact-05，K1 核心）
2. `依沃西 HARMONi-2 OS 数据 2025 一线 NSCLC 帕博利珠单抗`（校准 fact-04，OS 成熟度）
3. `Summit Therapeutics ivonescimab FDA BLA 提交 注册 时间表 2026`（校准 fact-05/08，美国注册路径）
4. `辉瑞 三生制药 SSGJ-707 PD-1/VEGF 授权 首付 里程碑 条款 2025`（校准 fact-09/14）
5. `BioNTech BMS BNT327 PM8002 全球合作 交易金额 2025`（校准 fact-10/15）
6. `默克 礼新 LM-299 PD-1/VEGF 授权 交易 2024 2025`（校准 fact-11）
7. `依沃西 中国 获批 适应症 销售额 2025 康方 半年报`（校准 fact-06/21）
8. `PD-1 VEGF 双抗 2025 2026 新增 授权交易 MNC license 汇总`（校准 fact-12/16/17，捕捉新 deal）
9. `康方生物 三生制药 市值 估值 现金 2025 2026`（校准 fact-21）
10. `PD-1 VEGF 双抗 安全性 出血 鳞癌 HARMONi 争议`（校准 fact-03，安全性质疑）
11. `依沃西 HARMONi-3 HARMONi-6 读出 进展 2025 2026`（校准 fact-07）
12. `康方 依沃西 vs K药 头对头 数据 争议 质疑 ASCO WCLC 2025`（校准 fact-04，捕捉对标杆的学界质疑）

## 六、prescan 校准结果（2026-07-10 回写）

> Step 4.5 prescan（4.5a 优先 12 条 + 4.5b 覆盖 2 条）入库 ~44 份 web-search material 后，对照第一节 fact-NN：

### 被推翻 / 重大更新（高优先级——thesis_v0 必须以下述新事实为准）
- `[fact-05]` 订正（比训练更差、非更好）：全球 HARMONi（2L EGFRm nsq-NSCLC）**OS 正式终点未达标**——主分析 OS HR=0.79，p=0.057，未过预设阈值 0.0448（FDA 已明确告知需统计显著 OS 方可批准）。康方/Summit 2025-09-07 补做西方患者延长随访（中位仅 13.7 月）的**事后分析**得 HR=0.78、**nominal p=0.0332**（因最终分析已过，nominal 不具统计学效力）。且存在**东西方人群不一致**：亚洲获益 24% > 西方 16%，Leerink 直指试验设计缺陷。Summit 股价当日 -24~25%。→ **全球/美国注册前景真实不确定，依赖"FDA leniency"**（Truist 语）；但 FDA 仍于 2026-01-29 受理 BLA，PDUFA **2026-11-14**。⚠️ 叠加地缘风险：NYT 报 Trump 政府拟审查中国分子授权交易。
- `[new-04]` **真·统计显著的 OS 硬赢在中国 HARMONi-6**（1L 鳞癌，依沃西+化疗 vs 替雷利珠+化疗）：**OS HR=0.66，p=0.0017（<阈值 0.0049）**，mOS 27.9 vs 23.7 月，2026 ASCO Plenary 报告——这是依沃西 head-to-head 战胜 PD-1 单抗的最强 OS 证据（区别于全球 HARMONi 的 2L EGFRm 场景）。另 HARMONi-3（全球 1L）2026-05-01 期中 PFS 未达（极低 alpha 门槛），IDMC 建议按原计划继续，最终 PFS+期中 OS 26H2 读出。
- `[fact-06]` "中国已获批但边界模糊" → **明确**：2024 年依沃西中国首次获批 EGFR-TKI 经治 nsq-NSCLC；FDA 授予 Fast Track。**2026-01-29 Summit 宣布 FDA 受理依沃西+化疗 BLA**（2L+ EGFRm nsq-NSCLC 经三代 TKI 进展，美国约 1.4 万患者/年）→ K1 美国注册从"悬念"进入"FDA 审评中"。
- `[fact-08]` 康方/Summit 交易 → **精确**：首付 $5 亿，交易总额最高 **$50 亿**（PD-(L)1/VEGF 赛道内总额最高）。
- `[fact-09]` 辉瑞/三生 → **精确**：2025-05-20 签约，首付 **$12.5 亿（创国产最高首付纪录）** + 里程碑最高 $48 亿 = 潜在总额 **$60.5 亿（~430 亿元）**，另辉瑞认购三生 $1 亿股权。SSGJ-707 中美双报，2025-04 获 CDE 突破性治疗认定，1L PD-L1+ NSCLC 已获批开展 III 期。
- `[fact-11]` 默沙东/礼新 LM-299 → **精确**：首付 $5.88 亿，总额 **$32.88 亿**。
- `[fact-16]` "宜明昂科 IMM2510 自研跟进" → **订正**：宜明昂科 PD-(L)1/VEGF 已**授权 Instil Bio**（非纯自研跟进）。中国已有 **5 款** PD-(L)1/VEGF 出海（康方→Summit、三生→辉瑞、普米斯→BioNTech、宜明昂科→Instil Bio、礼新→默沙东）。
- `[fact-17]` "MNC 自研入局" → **重大订正**：截至目前 MNC 主要是**授权/收购中国分子**（辉瑞买 707、BMS 买 BNT327、默沙东买 LM-299、Instil 买 IMM2510），**尚无突出的 MNC 纯自研 PD-1/VEGF**。业内讨论仍是"还有哪些 MNC 会买"。→ thesis 措辞"MNC 自研入局"应改为"MNC 通过授权/收购中国分子集中入局（自研为潜在远虑）"。
- `[fact-21]` 康方财务（原 uncertain）→ **有数**：2024 全年总收入 21.24 亿元，商业销售收入 20.02 亿元（+24.88%），研发投入约 12 亿元。高盛预计依沃西全球峰值销售 **$530 亿**。

### 被验证（可继续引用，置信度提升）
- `[fact-04]` HARMONi-2 head-to-head 胜 K 药 PFS → 验证（多源），且 OS 出现"有临床意义的阳性趋势"（中国监管要求的期中 OS 分析，Summit 披露）。置信度 高→高+。
- `[fact-10]` BMS/BioNTech BNT327 → 验证：交易金额最高 **$11.1 亿美元级**（up to $11.1bn）。
- `[fact-12]` PD-(L)1/VEGF 成 2024-2025 最热出海靶点 → 验证（每年至少 1 笔，2022 至今 5 款出海）。
- `[fact-18/19/20]` K 药挑战/专利悬崖/PD-1 单抗价格战殷鉴 → 框架性验证。

### 新增事实（baseline 未覆盖，进 thesis/命门考量）
- `[new-01]` **反方硬证据**：Summit 股价在 HARMONi-3 中期 PFS 读数后重挫约 25%；"康方赢了K药却没赢市场"（依沃西中国商业化爬坡慢于预期）；phirda"PD-1/VEGF 双抗的一盆冷水"——OS nominal-p 争议 + 商业化兑现慢是当前主要看空点。
- `[new-02]` **在读催化**：HARMONi-6（中国鳞癌）OS 数据 ASCO 2026 Plenary 报告（阳性）；HARMONi-3（全球 1L 鳞/非鳞）、HARMONi-7（1L PD-L1 高表达 vs 帕博）在读；康方 CD47（莱法利）+依沃西头对头 K 药头颈鳞癌 III 期。
- `[new-03]` 百利天恒双抗 ADC（EGFR/HER3）授 BMS 总额 $84 亿（首付 $8 亿）——是"国产创新药出海"更大坐标系里的对照锚（非本赛道但同为 MNC 买中国分子范式）。

### 仍未校准（thesis_v0 引用时标 uncertain）
- `[fact-14/15]` 三生 707、普米斯 BNT327 的**具体临床阶段/数据成熟度**（相对依沃西的落后幅度）——只知都在 Ph2/Ph3 推进，精确读出时点未校准。
- `[fact-22]` Summit、三生、康方的**实时估值/现金**具体数字（有定性描述，无精确当期数）。

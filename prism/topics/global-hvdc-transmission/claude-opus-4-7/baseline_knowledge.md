---
slug: global-hvdc-transmission
variant: claude-opus-4-7
written_at: 2026-05-28T03:30:00+00:00
training_cutoff_estimate: 2026-01
---

# 训练知识 Baseline — 跨州跨国 HVDC 输电（Prysmian/国电南瑞/特变电工）

> 本文记录 LLM 在训练截止时对该 topic 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。

## 一、关键事实记忆（48 条）

### 1.1 技术与机制（静态多）

- `[fact-01]` HVDC 输电相对 HVAC 在长距离（>600km 架空 / >50km 海底）+ 异步联网 + 海底场景具显著经济性 → 置信度：高 | time_sensitivity：**静态**
- `[fact-02]` HVDC 两大技术路线：LCC（电网换相，Thyristor 阀，单向潮流，大容量低成本）vs VSC（电压源换相，IGBT 阀，可双向、可黑启动、可多端组网，但容量历史小、损耗略高） → 置信度：高 | time_sensitivity：**静态**
- `[fact-03]` 海上风电跨国互联与多端 HVDC 网（North Sea Grid）只能用 VSC，LCC 物理上不支持 → 置信度：高 | time_sensitivity：**静态**
- `[fact-04]` 中国 UHVDC 主流电压 ±800kV，单回容量 8GW；±1100kV（昌吉-古泉示范）单回 12GW 是世界最高电压等级 → 置信度：高 | time_sensitivity：**静态**
- `[fact-05]` 海底 HVDC 电缆历史主流电压 320kV（VSC），近年 525kV 已商用（Viking Link、NeuConnect），640kV/700kV 在实验室 → 置信度：高 | time_sensitivity：**慢变**
- `[fact-06]` HVDC 换流站典型造价占整体项目 20-30%，海缆占 40-60%（取决于长度），土建+许可余下 → 置信度：中 | time_sensitivity：慢变
- `[fact-07]` HVDC 断路器是多端柔直组网的最后技术门槛，2026 训练时点商业化产品有限（ABB/日立 / 西门子能源各有 demo） → 置信度：中 | time_sensitivity：**快变** ⚠️

### 1.2 设备龙头产能（慢变 + 一定快变）

- `[fact-08]` 全球海缆三巨头：**Prysmian（意大利，PRY.MI）/ Nexans（法国，NEX.PA）/ NKT（丹麦，NKT.CO）** 三家寡头占欧洲 HVDC 海缆订单 >80% → 置信度：高 | time_sensitivity：慢变
- `[fact-09]` 亚洲海缆主力：**住友电工、LS Cable（韩）、中天科技（SSE_600522）、亨通光电（SSE_600487）、东方电缆（SH_603606）** → 置信度：高 | time_sensitivity：慢变
- `[fact-10]` Prysmian 2024 年 backlog ~€17B（含 power transmission + telecom），HVDC 排单到 2028+ → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-11]` Nexans 转型聚焦电力，2024 年宣布出售工业线缆业务，全部产能投 HVDC → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-12]` 换流阀/换流站全球前四：**日立能源（原 ABB Power Grids，被日立 80% 收购）/ Siemens Energy（ENR.DE）/ GE Vernova（GEV）/ 中国国电南瑞（NARI, SSE_600406）+ 许继电气（SZSE_000400）+ 中国西电（SSE_601179）** → 置信度：高 | time_sensitivity：慢变
- `[fact-13]` 中国 UHVDC 国内市场国产化率近 100%，海外仅日立能源 + 西门子能源 + GE 三家可承接非中国 UHVDC 总包 → 置信度：高 | time_sensitivity：慢变
- `[fact-14]` 特变电工（SSE_600089）UHV 变压器国内份额约 30-40%，与保变电气、中国西电三分国网招标 → 置信度：中 | time_sensitivity：慢变
- `[fact-15]` 思源电气（SSE_002028）GIS / 电气一次国产替代主力 → 置信度：中 | time_sensitivity：慢变
- `[fact-16]` 全球大型变压器（>200MVA GSU）瓶颈：训练时点北美产能严重不足，订单交期 36-48 个月（vs 历史 12-18 个月） → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-17]` HVDC IGBT 阀片供应：英飞凌（ETR_IFX）/ 三菱电机 / 日立 主导，国产替代时序模糊 → 置信度：中 | time_sensitivity：**快变** ⚠️

### 1.3 在建/规划项目管线（快变多 — 校准重点）

**中国国内（西电东送 + 沙戈荒新能源外送）**：
- `[fact-18]` 已投运标志性项目：白鹤滩-江苏 ±800kV（2022 投运）、白鹤滩-浙江 ±800kV（2022）、雅中-江西 ±800kV（2023）、青海-河南 ±800kV（2020 含新能源）、昆柳龙 ±800kV 三端柔直（2020，首条多端 UHVDC） → 置信度：高 | time_sensitivity：静态
- `[fact-19]` 训练时点在建 / 已核准 UHVDC（2024-2026 预投运）：陇东-山东 ±800kV、宁夏-湖南 ±800kV、哈密-重庆 ±800kV、藏东南-粤港澳大湾区 ±800kV → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-20]` "十四五"规划末期至"十五五"国网预计新增 8-10 条 UHVDC + 数条柔直海缆（含东海/南海风电外送） → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-21]` 国网 + 南网年度 UHV 招标总规模 2024 年约 800-1000 亿元（含交直流），2025 年指引可能上修 → 置信度：低 | time_sensitivity：**快变** ⚠️

**欧洲（北海风电 + 跨国互联）**：
- `[fact-22]` 已投运标志：NorNed（NL-NO, 700MW）、NordLink（DE-NO, 1.4GW, 2020）、IFA2（UK-FR, 1GW）、Viking Link（UK-DK, 1.4GW, 2023 末投运） → 置信度：高 | time_sensitivity：静态
- `[fact-23]` 在建/近期投运：NeuConnect（UK-DE, 1.4GW, 525kV, 2028 投运）、Greenlink（UK-IE, 500MW, 2024）、IceLink（UK-IS, 提案中）、EuroAsia / EuroAfrica（希腊-塞浦路斯-以色列 / 埃及） → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-24]` Tennet（荷兰/德国）2GW Programme — 14 条 2GW 525kV 海上风电外送 HVDC 系统，2024 年总框架订单 ~€30B 给 Prysmian / Nexans / Hitachi / GE / Siemens Energy → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-25]` 北海能源岛（Bornholm DK、Princess Elisabeth BE）作为 HVDC 多端组网枢纽，2030 前规划 → 置信度：中 | time_sensitivity：慢变
- `[fact-26]` 英国 ESO 2024 年 Beyond 2030 报告规划新增 >10GW HVDC 跨苏格兰-英格兰（Eastern Green Link 1-4） → 置信度：中 | time_sensitivity：**快变** ⚠️

**美国/北美**：
- `[fact-27]` Champlain Hudson Power Express（CHPE, NY-Quebec, 1.25GW HVDC, 2026 投运目标）— 第一条进入纽约市的 HVDC → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-28]` SunZia（NM-AZ, 3GW HVDC + 风电 3GW）2025 开工，2026 调试 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-29]` TransWest Express（WY-CA）/ Grain Belt Express（KS-IN, Invenergy）HVDC 项目长期受许可拖累，训练时点仍未全部开工 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-30]` 美国 DOE Grid Deployment Office 推出 Transmission Facilitation Program（$2.5B），用于跨州输电（含 HVDC）启动期信用 → 置信度：中 | time_sensitivity：慢变
- `[fact-31]` 训练时点 Pacific DC Intertie（PNW-LA, 1970 投运，3.1GW）升级 / 翻新计划在讨论 → 置信度：低 | time_sensitivity：快变

**其他地区**：
- `[fact-32]` 印度 Adani / Power Grid Corp 主导 ±800kV UHVDC（Champa-Kurukshetra、Raigarh-Pugalur、北电送南电），日立能源参与多个 → 置信度：中 | time_sensitivity：慢变
- `[fact-33]` 跨大陆超长距：Xlinks Morocco-UK 项目（3.6GW, 4000km 海缆，史上最长），训练时点融资 / 许可仍在推进 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-34]` 澳洲 Sun Cable（澳-新加坡 4200km, 17-20GW，Marinus Link）训练时点反复重组（Mike Cannon-Brookes vs Andrew Forrest 之争） → 置信度：低 | time_sensitivity：**快变** ⚠️

### 1.4 政策与监管（慢变 + 部分快变）

- `[fact-35]` 欧盟 PCI（Projects of Common Interest）名单第 6 期含多个跨国 HVDC，享受加速许可 + CEF Energy 补贴 → 置信度：高 | time_sensitivity：静态
- `[fact-36]` IRA Section 48E（清洁电力 ITC）+ Transmission Facilitation Program 是美国 HVDC 项目补贴主源；训练时点 2025 大选后 IRA 部分条款不确定 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-37]` 中国"十四五"末"十五五"初新型电力系统建设：2025 年储能 + UHVDC + 新能源外送是核心抓手；国家发改委 / 能源局年度文件 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-38]` 英国 Ofgem 2024 年 ASTI（Accelerated Strategic Transmission Investment）框架批准 26 个项目（约 £20B），含多条 Eastern Green Link → 置信度：中 | time_sensitivity：**快变** ⚠️

### 1.5 财务/估值快照（快变 — 校准重点）

- `[fact-39]` Prysmian（PRY.MI）2024 年营收约 €15-17B，市值约 €17-20B（训练时点），EV/EBITDA ~10x → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-40]` Nexans（NEX.PA）2024 年营收 ~€8B，市值 ~€4-5B（训练时点） → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-41]` NKT（NKT.CO）2024 年营收 ~€3B，市值 ~€3-4B（训练时点），纯电力 pure-play → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-42]` Siemens Energy（ENR.DE）2024-2025 年营收约 €34-38B，HVDC/Grid Technologies 部门 ~25-30% 营收，市值 2024 末复苏到 €40-50B（从 2023 低谷） → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-43]` GE Vernova（GEV，2024 年 4 月 GE 分拆上市）—— Power + Wind + Electrification 三段；Electrification（含 Grid Solutions HVDC）2024 年营收 ~$8B → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-44]` 国电南瑞（SSE_600406）2024 年营收 ~500-550 亿元，市值 ~1800-2200 亿元（训练时点） → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-45]` 特变电工（SSE_600089）2024 年营收（含煤炭/多晶硅）~1000 亿元，UHV 设备业务约 200-250 亿，市值 ~700-900 亿元（训练时点） → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-46]` 中天科技（SSE_600522）2024 年营收 ~500 亿元，海缆业务 ~80-100 亿，市值 ~500-700 亿（训练时点） → 置信度：低 | time_sensitivity：**快变** ⚠️

### 1.6 行业结构性变量

- `[fact-47]` 全球海缆铺设船全球总数 <15 条（深水级），是 HVDC 海缆项目交付的另一瓶颈 — Prysmian Leonardo da Vinci、Nexans Aurora、NKT Victoria、CNOOC 海洋石油 286 → 置信度：中 | time_sensitivity：慢变
- `[fact-48]` 中国 UHVDC 设备出海首单：训练时点已有印度 Champa-Kurukshetra 部分换流变压器订单（特变电工）、巴西美丽山 ±800kV（国家电网+CTG 投资但设备主要 ABB/Siemens），整套国产换流站海外承接还未突破 → 置信度：中 | time_sensitivity：**快变** ⚠️

**第一节统计**：48 条 fact
- 静态：9 条（fact-01/02/03/04/06/22/35/47 + 部分 18）
- 慢变：19 条
- **快变：20 条**（其中置信度高/中：18 条 → 第五节必须有对应 query）

## 二、关键人物 / 公司 / 产品

**设备龙头**：
- **日立能源（Hitachi Energy，日立 80% + ABB 20%）**—— 全球 HVDC 总包 #1，HVDC Light（VSC）技术原创方，主战场欧洲/印度
- **Siemens Energy（ENR.DE）**—— HVDC Plus（VSC），北海 Tennet 2GW 主要供应商，2023 年风电业务（Siemens Gamesa）巨亏拖累整体，2024 复苏
- **GE Vernova（GEV）**—— Grid Solutions HVDC 业务，订单近年加速；2024 年从 GE 分拆，Larry Culp 操盘
- **Prysmian（PRY.MI）**—— 海缆 #1，2018 年并购 General Cable，2024 年并购 Encore Wire，主战场欧洲跨国互联 + 北海风电
- **Nexans（NEX.PA）**—— 海缆 #2，CEO Christopher Guérin 主导"电力 pure-play"转型
- **NKT（NKT.CO）**—— 海缆 #3，丹麦 pure-play，Karlskrona 工厂扩产
- **国电南瑞（SSE_600406）**—— 国网系，中国 UHVDC 换流阀 + 控保系统国内 #1
- **许继电气（SZSE_000400）**—— 国网系，UHVDC 换流阀
- **中国西电（SSE_601179）**—— 国网系，换流变压器 + GIS
- **特变电工（SSE_600089）**—— 民营，UHV 变压器 + 沙戈荒新能源 + 多晶硅，多元化
- **中天科技 / 亨通光电 / 东方电缆**—— 中国海缆三强（东方电缆海风纯度最高）

**项目业主**：
- 中国：国家电网（State Grid）、南方电网
- 欧洲：Tennet（NL/DE）、National Grid（UK）、Statnett（NO）、Energinet（DK）、50Hertz（DE）、RTE（FR）
- 美国：PJM/MISO/ERCOT/CAISO + Invenergy（Grain Belt）、Anbaric、SOO Green、TransWest Express

**关键个人**：
- Claudio Facchin —— 日立能源 CEO（前 ABB Power Grids CEO）
- Christian Bruch —— Siemens Energy CEO
- Massimo Battaini —— Prysmian CEO（2024 接任 Valerio Battista）

## 三、产业链 / 竞争格局认知

**主线**：HVDC 在 2020-2030 是"沉睡四十年的老技术 + 三股 demand 同时爆发"的赛道——(1) 海上风电（北海/亚太）规模化需要 HVDC 海缆 + VSC 多端组网；(2) AI 数据中心电力跨州/跨区供给（美国西部太阳能+德州风电送东海岸）；(3) 中国"沙戈荒"新能源外送 + 西电东送下半场。三股 demand 共同把全球 HVDC 设备 + 海缆订单从 2020 年的低位推到 2030 年的供不应求。

**关键产业链层级**：
1. **海缆**（最紧）：欧洲三巨头 + 亚洲六玩家；新建产能至少 36-48 个月（绕组车间 + 立式硫化塔 + 铺缆船）；
2. **换流站/换流阀**（次紧）：日立/西门子能源/GE/中国三大家，订单交付期 24-36 个月；
3. **换流变压器**（最紧之一）：>500MVA HVDC GSU 全球产能稀缺，特变/西电/Siemens Energy/Hitachi 几乎排单到 2028+；
4. **GIS / 一次设备**（中等紧）：ABB / 西门子能源 / 思源电气 / 平高电气；
5. **EPC + 海缆安装船**：Prysmian Leonardo / Nexans Aurora / NKT Victoria / Jan De Nul / Subsea 7；安装窗口期短（夏季）；
6. **业主/电网**：差异巨大——欧洲 TSO（Tennet/National Grid）通过 RAB / framework agreement 锁单；美国靠 IRA + DOE TFP 信用 + 长期合同（PPA-like）；中国按"十五五"规划批准。

**寡头分布**：
- 海缆 HVDC 段：Prysmian + Nexans + NKT 占欧洲 ≥80%；亚太靠中天+亨通+住友+LS Cable
- 换流阀：日立 + Siemens Energy + GE + 中国三大家
- 中国市场：国产替代基本完成（除少量 IGBT 还进口）
- 海外市场：中国设备出海仍是单点突破，整体被欧日美锁定

**最被低估的链条**：换流变压器（GSU）+ 海缆铺设船——这两个是物理 capex 重投资 + 长建设周期，谁有产能谁就 pricing power。

## 四、训练知识盲点（自我承认）

LLM 自评以下方面训练时不够 / 不知道：

1. **2025-2026 实际新签订单**：训练数据可能停在 2025 上半年，下半年 Tennet 2GW 框架协议第二批 / 国网 2025 年度集采 / Siemens Energy 订单簿 / GE Vernova 订单 / 各家 backlog 实时增量，**全部需要 web-search 校准**
2. **股价 / 估值快照**：所有 fact-39~46 都标了"训练时点"，2026Q2 实际市值 / PE / EV/EBITDA 需要校准
3. **IRA / DOE TFP 2026 实际执行**：2024 年大选后 Trump 政府的 IRA 修订动态、2025-2026 TFP 实际放款、跨州输电许可加速法案（如 Sen. Manchin 的 Energy Permitting Reform Act）的最新状态
4. **NeuConnect / Eastern Green Link 1-4 / SunZia / CHPE 投运延迟或提前**：HVDC 大项目延期是常态，训练时点的"2028 投运"可能已经被推到 2029-2030
5. **中国"十五五"规划具体 UHVDC 名单**：能源局 / 国网 2025 年公布的具体在哪、何时核准
6. **海缆产能扩张**：Prysmian、Nexans、NKT 在 2024-2026 宣布的产能投资（新工厂、新铺缆船）是否落地、订单是否填满
7. **HVDC 断路器商业化突破**：日立 / 西门子能源 / ABB 任何一家有 demo 项目落地的最新动态
8. **国产 HVDC 设备海外突破**：中国设备厂家是否在沙特、巴基斯坦、中亚拿到新整套换流站订单
9. **特变电工 / 国电南瑞 / 中天科技 2025 年报数据**：营收 / UHV 业务拆分 / 海缆订单
10. **AI 数据中心专用 HVDC 需求**：hyperscaler（Microsoft / Google / Amazon / Meta）是否直接采购 HVDC 跨州输电（如 Champlain Hudson 之外的新项目），是否签 PPA-like 输电容量合同

## 五、需要 web-search 校准的优先项

**强制规则**：第一节 20 条快变 fact（高/中置信度的 18 条）必须有对应 query。下面列 14 条（部分一个 query 覆盖多个 fact）：

1. `Tennet 2GW Programme 2025 2026 HVDC offshore wind framework award` — 覆盖 fact-24 + 02 节产业链
2. `Eastern Green Link 1 2 3 4 contract award 2025 Hitachi Siemens GE Prysmian` — 覆盖 fact-26
3. `NeuConnect HVDC interconnector commissioning 2027 2028 schedule update` — 覆盖 fact-23
4. `Champlain Hudson Power Express CHPE commercial operation 2026 update` — 覆盖 fact-27
5. `SunZia transmission line construction progress 2026` — 覆盖 fact-28
6. `China State Grid UHVDC tender 2025 2026 award list 国网 特高压 直流 招标` — 覆盖 fact-19/20/21
7. `Prysmian Q1 2026 results HVDC backlog Tennet order book` — 覆盖 fact-10 + fact-39
8. `Nexans 2026 H1 results HVDC submarine cable order intake` — 覆盖 fact-11 + fact-40
9. `Siemens Energy Grid Technologies 2026 H1 order intake HVDC` — 覆盖 fact-42
10. `GE Vernova Electrification HVDC orders 2026 Q1` — 覆盖 fact-43
11. `特变电工 2025 年报 输变电业务营收 ultra high voltage transformer` — 覆盖 fact-14 + fact-45
12. `国电南瑞 2025 年报 直流输电 换流阀 营收` — 覆盖 fact-44
13. `中天科技 东方电缆 2025 海缆订单 海上风电` — 覆盖 fact-09 + fact-46
14. `Xlinks Morocco UK HVDC submarine cable financing 2026 update` — 覆盖 fact-33

**质检自检**：
- 第一节快变高/中置信 fact 18 条 → 第五节 14 条 query（部分 query 覆盖多 fact，且 fact-29/31/34 已标"低置信度"未必强 query）
- 满足"每条快变 + 高/中 fact 至少一个对应 query"原则

## 六、prescan 校准结果（2026-05-28T14:55+00:00 回写）

> 数据源：Step 4.5a (14 query, 入库 52) + Step 4.5b (5 query, 入库 18) = 累积 66 unique mat_ids。
> 详细 mat-NN 待后续 03-extract 阶段引用；本节只标"哪条 fact 该被怎么处理"，引用具体 mat 留给 thesis_v0 / 03。

### 被推翻

- `[fact-33]` Xlinks Morocco-UK 项目融资仍在推进 → **英国政府 2025-06 决定不批 CfD，Xlinks 主推方案被官方放弃**（xlinks.co 官方 + Energy Institute 综述确认）。已花 ~£100mn 前期开发但无政府支持难推进。thesis_v0 不要再把 Xlinks 当"在建跨大陆项目"的有效信号
- `[fact-48]` 国产 HVDC 设备海外仅单点突破，整套国产换流站海外承接还未突破 → **已显著突破**：
  - 特变电工 2025 H1 国际订单 +65.91% YoY，斩获沙特 164 亿元大单（ditan.com）；1-8 月出口额 >60 亿元
  - 中国西电 2025 海外收入 21.71 亿元 +64.05% YoY
  - 中企中标智利 Kimal-Lo Aguirre HVDC（goalfore）
  - 中企中标沙特-埃及 HVDC（goalfore）
  - thesis_v0 应把"国产 HVDC 出海"列为已成立 + 加速中的论据

### 被验证（强证据 + 数据校准）

- `[fact-23]` NeuConnect 1.4GW UK-DE 525kV 2028 投运 → **强验证**：neuconnect-interconnector.com 2025-07 + agentzero 2026-02 双口径均确认 2028 commissioning 在路上，transformer 已交付，换流站施工 through 2026-2027；Sumitomo 已交付 150km 525kV HVDC 海缆
- `[fact-24]` Tennet 2GW Programme 总框架 ~€30B 给 Hitachi/Prysmian/Nexans/Hitachi/Siemens Energy/GE → **强验证 + 新增订单**：
  - 2023-03 Hitachi Energy + Petrofac €13B framework
  - 2023 早期 €5.5B 批次给 NKT/Nexans/Jan De Nul/LS Cable/Denys
  - **2025-12-11 NEW 大单：GE Vernova + Seatrium 中标 BalWin5 (2.2GW)**（gevernova.com）
  - **NKT 2 个 TenneT 2GW 项目合同 ~€10亿**（chinacable 报道）
- `[fact-26]` Eastern Green Link 1-4 大规模订单已落地 → **超预期验证**：
  - EGL1 £1.8bn 给 Prysmian（easterngreenlink1.co.uk）
  - EGL4 总 £3bn 给 Siemens Energy + Prysmian；其中 Prysmian £2bn cable contract（530km 海缆 + 116km 陆缆，scottishpower.com）
  - Iberdrola SP Energy Networks 业主总盘 €3.5bn（iberdrola.com）
- `[fact-27]` CHPE NY-Quebec 2026 投运 → **验证但有微调**：chpexpress.com 官方"full operation date is now anticipated to be spring of 2026, shifting from the previous expected date"——确认 2026 但承认相对早期计划有延期
- `[fact-28]` SunZia 2026 调试 → **强验证**：energiesmedia/blackridgeresearch/wiki/wecc.org/nmreta 五口径一致：2023 开工，2026 商运，$11B 总投资，Pattern Energy/RETA 联合开发
- `[fact-45]` 特变电工财务（粗估） → **数据校准**：2025 H1 营收 483.51 亿（+1.11% YoY），利润总额 44.23 亿（+15.62%），归母净利 31.84 亿（+5%），输变电高端装备是核心业务（tbea.com 官方 + sse.com.cn 科创公告）
- `[fact-44]` 国电南瑞财务 → **结构验证**：智能电网（含直流输电、柔性交流、电网调度自动化、变电站监控、继电保护）为核心营收来源；2025 H1 信用减值损失同比增加（主因收入增长+应收增加）；2026-04 已发 2025 年度报告摘要（10jqka pdf）—— 具体 2025 全年营收数 thesis_v0 阶段需 02-gather 拉年报正文
- `[fact-39]` Prysmian 2024 营收 €15-17B → **粗校准上调**：Q1 2026 单季营收 €5.218B，简单年化 ~€20B（实际有季节性，需看完整四季）；继续 organic growth + 利润率提升 + 强自由现金流；订单簿继续扩张
- `[fact-40]` Nexans 转型聚焦电力 → **强验证**：Q1 2026 Electrification 业务有机增长 +4.9%，PWR-Transmission + PWR-Grid 推动；并购 Republic Wire（c.€520M 营收）进入美国
- `[fact-43]` GE Vernova Electrification 2024 营收 ~$8B → **方向验证 + 上调动能**：Q1 2026 Electrification 订单同比快速增长，2026 Power equipment 新单 pricing 高于 Q4 2024 10-20%
- `[fact-21]` 国网 2025 UHV 集采约 800-1000 亿 → **部分验证**：news.metal.com 报道 2025-04 国网 UHV 项目"第 15 批集采"启动；华菱电缆中标 4.56 亿（单批次单家），具体年度总盘仍待 02-gather 拉公告完整列表
- `[fact-37]` 中国"新型电力系统"政策 → **验证 + 新动态**：国网 2026 年承诺花 310 亿（$4.5B）建抽水蓄能，目标 70%+ 装机扩张（energyconnects 引彭博）——配套 UHVDC 的新能源消纳储能加大投入

### 仍未校准（thesis_v0 / 02-gather 阶段重点补）

- `[fact-07]` HVDC 断路器商业化突破 → 本轮 prescan 无直接 hit，需后续单独 query 或参 CIGRE/IEC 文献
- `[fact-10/11]` Prysmian/Nexans **2024 backlog 总数**（不是 Q1 营收）→ 本轮拿到 Q1 营收，没拿到 backlog 公告数；02-gather 阶段读年报正文
- `[fact-13]` 海外仅日立/西门子能源/GE 三家可承接非中国 UHVDC 总包 → 被 fact-48 部分推翻（中企已突破沙特/智利/沙特-埃及）；但欧洲北海仍未见中企；需细化语义
- `[fact-16]` 北美大型变压器交期 36-48 月 → 本轮无 hit；02-gather 阶段读 GEV/西门子能源年报或 NERC/EIA 报告
- `[fact-17]` IGBT 阀片国产替代时序 → 本轮无 hit；专项需求
- `[fact-19/20]` 中国"十五五"具体 UHVDC 名单 → 仅拿到 2025 年招标第 15 批信息，全名单需国网 / 能源局官方文件
- `[fact-29/30/31]` 美国 TransWest Express / Grain Belt / Pacific DC Intertie / DOE TFP 实际放款 → 本轮 SunZia/CHPE 已覆盖，其余美国项目下一轮专项 query
- `[fact-36]` IRA Section 48E 在 Trump 政府下的修订状态 → 本轮无政策更新 hit；需专项政策 query
- `[fact-46]` 中国海缆三强（中天/东方/亨通）2025 财务 + 海外订单 → 仅拿到 stcn.com "订单大爆发"软文，缺 IR 一手数据；02-gather 阶段拉年报
- `[fact-22]` 已投运欧洲 HVDC 项目（NorNed / NordLink / IFA2 / Viking Link）→ 本轮无 hit 校准，但属"静态历史事实"，无需强校准

### 新增 fact（thesis_v0 可直接引用）

- `[fact-49 NEW]` GE Vernova + Seatrium 联合体 2025-12-11 中标 TenneT BalWin5 (2.2GW HVDC, 德国北海)，进一步证实 2GW 框架持续放量
- `[fact-50 NEW]` NKT 拿下 TenneT 2GW 项目两个标段，合同总额 ~€10 亿（陆上 + 海上 HVDC 电力电缆）
- `[fact-51 NEW]` Sumitomo Electric 2022-11 中标 Prysmian 总包下 NeuConnect 150km 525kV HVDC 海缆 sub-supply
- `[fact-52 NEW]` 特变电工 2025 H1 国际订单同比 +65.91%，斩获沙特 164 亿元大单；1-8 月出口额超 60 亿元——确认中国 HVDC 设备出海加速
- `[fact-53 NEW]` 中国西电 2025 海外收入 21.71 亿元 +64.05% YoY，欧洲市场占比提升
- `[fact-54 NEW]` 中企中标智利 Kimal-Lo Aguirre HVDC + 沙特-埃及 HVDC 两个跨国项目
- `[fact-55 NEW]` 国网 2026 年承诺 310 亿元 ($4.5B) 用于抽水蓄能，配套新能源消纳——侧证 UHVDC 新能源外送场景持续放量
- `[fact-56 NEW]` Xlinks Morocco-UK 项目 2025-06 被英国政府否决 CfD，原推方案搁置——4000km 跨大陆 HVDC 海缆叙事降级
- `[fact-57 NEW]` EGL4 业主 Iberdrola SP Energy Networks 总盘 €3.5bn（>fact-26 中估算的 £2bn cable 单标），Siemens Energy + Prysmian 联合供货

### 校准统计

- 本轮校准 fact 数：被推翻 2 + 被验证强证 11 + 新增 9 = 22 条
- 仍未校准的快变 + 高/中置信 fact：8-10 条（02-gather 阶段拉 IR 年报正文 + 政策原文）
- thesis_v0 写作纪律：所有"被推翻"的 fact 必须改 cite 新 mat（02-gather 后定 mat_id）；所有"被验证"的 fact 可继续以 fact-NN 引用，但建议同步 cite 验证 mat 增强证据密度

---
slug: global-autonomous-driving
variant: opus4.8
written_at: 2026-07-28
training_cutoff_estimate: 2025-01
---

# 训练知识 Baseline — 自动驾驶行业 (Autonomous Driving, GLOBAL)

> 本文记录 LLM 在**训练截止时（估 2025-01）**对该 topic 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。
> ⚠️ 本行业时效性极强（芯片 SOP / robotaxi 单量 / IPO 估值 / 端到端渗透率均季级变化），当前 2026-07 距训练截止 ~18 月，快变类 fact 已大概率过时。

## 一、关键事实记忆（30 条）

### A. 范式与技术路线
- `[fact-01]` 自动驾驶分级 SAE L0-L5；量产乘用车主流停在 L2/L2+（人监管），L3（有条件脱手，责任转移车厂）2023-24 起德日（奔驰 Drive Pilot、本田）少量落地；L4（限定域无人）仅 robotaxi/干线物流试点 → 置信度：高 | time_sensitivity：静态
- `[fact-02]` 2023-2024 是"端到端（end-to-end）"范式转折年：从"感知-预测-规划-控制"模块化管线转向神经网络端到端；2024 下半年进一步向 VLA（Vision-Language-Action）/世界模型演进 → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-03]` "去高精地图 + 去激光雷达"是中国智驾降本主线：城市 NOA 从依赖高精地图转向"无图"BEV+Transformer；纯视觉（Tesla 路线）与"视觉+激光雷达"路线并存争论 → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-04]` Tesla FSD 从 v11 模块化切到 v12（2024，端到端神经网络）再到 v13；纯视觉（2021 起弃用毫米波雷达/超声波），坚持不用激光雷达 → 置信度：高 | time_sensitivity：**快变** ⚠️

### B. 上游：AD 计算芯片
- `[fact-05]` Nvidia Drive Orin（254 TOPS）是 2022-2024 中高端智驾主控事实标准；后继 Thor（~2000 TOPS，Blackwell 架构，舱驾一体）2024 发布、2025 起量产上车 → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-06]` 地平线（Horizon Robotics）征程（Journey）系列国产龙头：J2/J3/J5 累计出货数百万，征程6（J6，含 J6P 高阶）2024 发布；2024-10 港股 IPO（09660.HK）→ 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-07]` 黑芝麻智能（Black Sesame，2533.HK）2024-08 港股 IPO，A1000/华山系列大算力芯片；行业第二梯队 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-08]` Mobileye（MBLY，Intel 系）EyeQ 系列长期 ADAS 视觉芯片霸主，但 2024 遭遇库存/订单下修，股价大跌；SuperVision（含 Zeekr）为高阶方案；EyeQ6 推进中 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-09]` 高通 Snapdragon Ride（含 Ride Flex 舱驾一体）为智驾芯片重要竞争者；特斯拉自研 FSD 芯片（HW4，HW5/AI5 规划中）→ 置信度：中 | time_sensitivity：**快变** ⚠️

### C. 上游：激光雷达 / 传感器
- `[fact-10]` 禾赛科技（Hesai，HSAI，2023-02 纳斯达克 IPO）与速腾聚创（RoboSense，2498.HK，2024-01 港股 IPO）为全球车载激光雷达出货双龙头，均为中国厂商 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-11]` 车载激光雷达单价从早期数千美元降至 2024 约数百美元（禾赛 ATX、速腾 MX 等低价车规款推动 ADAS 前装放量）→ 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-12]` 美系激光雷达 Luminar（LAZR）、Innoviz、Ouster 商业化困难、持续亏损/股价低迷；Luminar 2024 多次裁员/重组 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-13]` 纯视觉端到端一旦跑通，会压缩激光雷达在乘用车 ADAS 的 TAM 上限——这是激光雷达多头/空头核心分歧 → 置信度：中 | time_sensitivity：慢变

### D. 中游：智驾软件 / 方案商
- `[fact-14]` 华为智驾（乾崑 ADS，含 ADS 2.0/3.0）为中国高阶智驾第一梯队；通过鸿蒙智行（问界 AITO/智界/享界/尊界）+ HI 模式（长安阿维塔、北汽等）扩张 → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-15]` Momenta 数据驱动"飞轮"两条腿（量产 Mpilot + Robotaxi），定点上汽智己、比亚迪、丰田等多家；2024 传出赴美 IPO → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-16]` 大疆车载/卓驭（成行平台）主打低价"普惠"高阶智驾（无激光雷达/低成本），上车宝骏/比亚迪等 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-17]` 其他第三方：商汤绝影、Momenta、元戎启行、轻舟智航、知行科技（1274.HK）、纵目、福瑞泰克等构成中游长尾 → 置信度：中 | time_sensitivity：慢变

### E. 中游：OEM 自研
- `[fact-18]` 小鹏（XPeng）XNGP + 图灵自研芯片、端到端；理想（Li Auto）AD Max + 端到端+VLM 双系统；蔚来 NIO 自研神玑芯片 + NAD → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-19]` 比亚迪 2025 起推"天神之眼"全系智驾平权（含低价车型标配高阶智驾），走自研+外采（含 Momenta/地平线）混合路线 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-20]` 特斯拉 FSD 为软件订阅/买断模式（美国约 $8000 买断或月订阅），高毛利递延收入；FSD 入华受监管+数据合规卡点，2024 末仍未落地 → 置信度：中 | time_sensitivity：**快变** ⚠️

### F. 下游：Robotaxi / L4 运营
- `[fact-21]` Waymo（Alphabet 系）为全球 L4 robotaxi 规模领先者，运营旧金山/凤凰城/洛杉矶/奥斯汀，2024 付费单量快速攀升（周付费单达数十万级）→ 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-22]` Cruise（GM 系）2023-10 加州事故后吊销牌照、停运；2024-12 GM 宣布停止对 Cruise robotaxi 业务注资、并入个人辅助驾驶——美国 robotaxi 竞争者出清重大事件 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-23]` Tesla 2024-10 发布 Cybercab（无方向盘/踏板 robotaxi），规划 2025 无监督 FSD + robotaxi 商用（Austin 首发）；估值叙事高度依赖此兑现 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-24]` 百度 Apollo Go/萝卜快跑 2024 中武汉全无人运营引发关注（第六代 RT6 整车成本大降至 ~20 万人民币），但单位经济学盈利与规模化争议未决 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-25]` 小马智行（Pony.ai，PONY）2024-11、文远知行（WeRide，WRD）2024-10 相继赴美 IPO；两者 robotaxi+robobus/robotruck 多线；均未盈利 → 置信度：中 | time_sensitivity：**快变** ⚠️

### G. 市场 / 结构
- `[fact-26]` 中国是全球高阶智驾（城市 NOA）渗透最快市场，2024 城市 NOA 从旗舰下探至 15-20 万价格带；美国是 robotaxi 商业化最前沿 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-27]` 中国乘用车 L2 及以上辅助驾驶渗透率 2024 已过半（约 50%+），高阶（城市 NOA）渗透仍个位数到低双位数 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-28]` 干线物流/矩阵 robotruck（图森未来退市、赢彻、Kodiak、Aurora）商业化进度慢于乘用车 robotaxi；Aurora 2024 规划德州无人干线 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-29]` 监管：中国 2023 起"准入+上路通行"L3/L4 试点通知、多城开放测试；美国 NHTSA 逐州牌照 + 联邦框架推进；欧盟 UN-R157 L3 框架 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-30]` "卖铲人"逻辑：无论哪条路线赢，AD 计算芯片（Nvidia/地平线）与数据/仿真工具链是相对确定受益环——但芯片存在被 OEM 自研（特斯拉/小鹏/蔚来）侵蚀的反向风险 → 置信度：中 | time_sensitivity：慢变

**第一节时效统计**：静态 3 条 / 慢变 4 条 / **快变 23 条** ⚠️ —— 快变占比极高（本行业本质），第五节 query 必须密集覆盖。

## 二、关键人物 / 公司 / 产品

- **Nvidia**（黄仁勋）— Drive Orin/Thor，智驾主控事实标准，向舱驾一体+机器人延伸
- **地平线 Horizon**（余凯）— 征程系列国产芯片龙头，港股上市
- **华为**（余承东/靳玉志）— 乾崑 ADS，鸿蒙智行"界"字辈+HI 模式
- **Momenta**（曹旭东）— 数据飞轮，量产+robotaxi 两条腿，拟美股 IPO
- **Tesla**（马斯克）— FSD 纯视觉端到端 + Cybercab robotaxi，估值叙事核心
- **Waymo**（Tekedra Mawakana / Dmitri Dolgov）— 全球 robotaxi 规模领先
- **百度**（李彦宏/王云鹏）— Apollo Go/萝卜快跑，RT6 降本
- **小马智行 Pony.ai**（彭军/楼天城）、**文远知行 WeRide**（韩旭）— 中国 L4 双子星，赴美上市
- **禾赛 Hesai**（李一帆）、**速腾聚创 RoboSense**（邱纯鑫）— 激光雷达双龙头
- **Mobileye**（Amnon Shashua）— ADAS 视觉芯片老牌霸主，2024 承压
- 关键产品：Orin/Thor 芯片、征程6、EyeQ6、ADS 3.0、FSD v13、Cybercab、RT6、天神之眼

## 三、产业链 / 竞争格局认知

**分层结构（本研究全栈视角）**：
1. **上游硬件**：AD 计算芯片（Nvidia/地平线/黑芝麻/Mobileye/高通/特斯拉自研）、激光雷达（禾赛/速腾/Luminar）、毫米波雷达、摄像头、域控制器（德赛西威/经纬恒润/华为）。
2. **中游软件/方案**：全栈方案商（华为/Momenta/大疆卓驭/元戎/商汤）vs OEM 自研（特斯拉/小鹏/理想/蔚来/比亚迪）。核心资产是数据+算法飞轮。
3. **下游运营**：robotaxi（Waymo/Tesla/百度/小马/文远/Cruise 出局）、robotruck（Aurora/Kodiak/赢彻）。

**两大范式路线之争**：
- **渐进派（乘用车量产 L2→L4）**：从辅助驾驶起步，靠海量车队数据迭代（Tesla、华为、Momenta、小鹏、比亚迪）。收入当下就有（软件订阅/硬件加价），飞轮自持。
- **跃进派（直接 L4 robotaxi）**：Waymo、百度、小马、文远。技术天花板高但资本消耗大、单位经济学与规模化未证、监管逐城谈判慢。

**关键格局判断（训练时先验，需校准）**：
- 芯片环双寡头化（Nvidia 高端 + 地平线中高端国产替代），但 OEM 自研是长期反噬风险。
- 激光雷达受"纯视觉端到端能否跑通"这一技术分叉决定 TAM——最大不确定。
- robotaxi 是"赢家通吃但兑现最慢"，Cruise 出局说明烧钱门槛已淘汰弱者。
- 中国"智驾平权"（比亚迪天神之眼）把高阶智驾打成红海，方案商价格战风险。

## 四、训练知识盲点（自我承认）

- **2025-01 之后的一切进展全部盲区**：Tesla robotaxi 是否真在 2025 落地 Austin、FSD 是否入华、Nvidia Thor 实际量产上车节奏、地平线征程6 出货、华为 ADS 4.0、各家 2025-2026 财报与估值——全部需校准。
- **单位经济学具体数字**：robotaxi 单公里成本/单车日订单/毛利，我只有定性认知，无近期实数。
- **激光雷达单价与出货具体数**：2025-2026 价格曲线、ADAS 前装定点数不掌握。
- **各芯片/方案商市占率具体百分比**：只有相对位次，无精确份额。
- **中国城市 NOA / 高阶智驾渗透率精确数字**：2025-2026 实际渗透率不掌握。
- **IPO 后估值/市值**：地平线、黑芝麻、速腾、小马、文远、禾赛的当前市值与估值倍数全不掌握。
- **一级市场融资/并购**：Momenta IPO 是否成行、估值；行业整合动态盲区。
- **监管最新动作**：2025-2026 中美欧 L3/L4 立法与牌照具体进展盲区。

## 五、需要 web-search 校准的优先项

> 强制规则：第一节 23 条快变 fact 必须被本节 query 覆盖。以下按投资决策重要性排序。

1. `Waymo 2026 robotaxi 每周付费订单量 运营城市 扩张 latest`（fact-21）
2. `Tesla robotaxi Austin 2025 2026 无监督 FSD unsupervised 商用进展 车队规模`（fact-23）
3. `特斯拉 FSD 入华 2025 2026 监管审批 数据合规 落地进展`（fact-20 fact-04）
4. `Nvidia Thor 智驾芯片 2025 2026 量产 上车车厂 SOP 出货`（fact-05）
5. `地平线 征程6 J6P 2026 出货量 定点车厂 市占率 市值`（fact-06）
6. `黑芝麻智能 2533.HK 2025 2026 营收 出货 定点`（fact-07）
7. `Mobileye 2025 2026 营收 SuperVision EyeQ6 定点 股价`（fact-08）
8. `华为 乾崑 ADS 4.0 2026 装机量 问界 享界 尊界 智驾 份额`（fact-14）
9. `Momenta IPO 2025 2026 美股上市 估值 定点车厂 出货`（fact-15）
10. `禾赛 速腾聚创 2026 激光雷达 出货量 单价 ADAS 前装定点 市值`（fact-10 fact-11）
11. `百度 萝卜快跑 2026 单量 盈利 unit economics 单位经济学 车队规模 出海`（fact-24）
12. `小马智行 Pony 文远知行 WeRide 2026 robotaxi 车队 盈利 营收 股价`（fact-25）
13. `端到端 VLA 智驾 2026 城市NOA 渗透率 中国 高阶辅助驾驶`（fact-02 fact-27）
14. `比亚迪 天神之眼 2025 2026 高阶智驾 装机 渗透 智驾平权 供应商`（fact-19）
15. `Cruise GM robotaxi 2024 2025 关停 后续 Aurora robotruck 干线 商业化`（fact-22 fact-28）
16. `激光雷达 纯视觉 端到端 2025 2026 TAM 之争 特斯拉 中国车厂 去激光雷达`（fact-13 fact-03）

## 六、prescan 校准结果（2026-07-28 回写）

> Step 4.5 prescan 跑 12 条 query、入库 43 份 web-search material（high 14 / mid 29）后，对照第一节 fact-NN 的更新。**本轮对 thesis 方向有重大冲击的两条：Nvidia 卖铲人确定性下修、激光雷达空头方向可能押反。**

### 被推翻 / 重大更新（thesis_v0 不要再引用原 fact 的乐观版本）

- `[fact-05]` 训练时"Nvidia Thor 2024 发布、2025 起顺利量产、~2000 TOPS" → **严重跳票 + 货不对版**：Thor 承诺 2024 上车未兑现、2025 才交付且算力仅 **~750 TOPS（原定一半）**，且 2026 仍"再度延期"（36氪）；小鹏 P7+ 被迫弃 Thor 改双 Orin-X。同时**"去英伟达化"成真**——蔚来/小鹏/理想/比亚迪自研芯片相继台积电流片成功（不是 PPT），**舱驾融合**（地平线/黑芝麻/比亚迪定点，一颗芯片管舱+驾）进一步侵蚀 Nvidia+高通双税。→ **动摇 thesis 中"Nvidia 双寡头卖铲人确定性最高"的 Nvidia 一半。**
- `[fact-13][fact-03]` 训练时押"纯视觉端到端压缩激光雷达 TAM、激光雷达是我与共识的空头分歧点" → **方向可能押反**：`[mat]` 禾赛 ADAS 主激光雷达出货**全球第一（Yole 2026）**、robotaxi 厂商反而**转向使用 ADAS 激光雷达**、中国"智驾平权"（比亚迪天神之眼等）带动激光雷达**前装放量**。纯视觉主要是特斯拉一家路线，中国主流仍在上激光雷达。→ **共识（ADAS 放量利好禾赛/速腾）似在兑现，我的激光雷达空头需重估**（真正的空头逻辑应收窄为"车载走量薄利、盈利分化"而非"TAM 崩塌"）。
- `[fact-15]` 训练时"Momenta 传赴美 IPO" → 实际**赴港 IPO、千亿估值**；纯软路线护城河受质疑（vs 地平线软硬一体 / 华为生态，"单一算法优势已不足以构建护城河"）。
- `[fact-23]` 训练时"Tesla 规划 2025 Austin robotaxi 商用" → 已落地但**车队极小（仅 25-42 辆）**，Musk 将规模化**推迟到 FSD V15**。→ robotaxi 兑现慢于早期叙事（**印证** thesis"robotaxi 兑现最慢"，但特斯拉尤甚）。
- `[fact-14]` 训练时"华为 ADS 3.0" → 已迭代到 **ADS 5（WEWA 2.0 架构）**，总搭载量突破 **190 万台（2026-07，25+ 品牌 50+ 车型）**、累计辅助里程 128 亿公里、8 月底预计破 200 万。→ 华为方案商规模领先坐实。

### 被验证（可继续引用，置信度提升）

- `[fact-06]` 地平线征程家族出货**突破 600 万、市占率双榜第一** → 国产芯片龙头坐实，**thesis 卖铲人赌注应向地平线一侧倾斜**（国产替代 + 舱驾融合受益，对冲 Nvidia 下修）。
- `[fact-21]` Waymo 目标 **2026 年 100 万单/周**、扩张至 San Diego/Vegas/Tampa/Denver/20+ 城市 → 全球 robotaxi 规模领先坐实。
- `[fact-24]` 百度萝卜快跑累计 **700 万单、谋出海** → 中国 robotaxi 规模领先坐实。
- `[fact-25]` 小马智行/文远知行争夺**"港股 Robotaxi 第一股"**（二次上市港股）、文远 Q1 营收 **+58%、毛利率 35%** → L4 双子星商业化推进但仍未盈利。
- `[fact-19]` 比亚迪天神之眼**全面无图化、自研 4nm 芯片 2100 TOPS、端到端上车、全民智驾战略** → OEM 自研 + 智驾平权双坐实（既侵蚀芯片外采、又打成红海）。
- `[fact-02][fact-27]` 城市 NOA 被行业蓝皮书称"**自动驾驶商业化转折点**"、2026 高阶智驾"迎来拐点" → 端到端范式 + 城市 NOA 渗透加速验证。

### 仍未校准（thesis_v0 引用时标 uncertain，留 02/03 深挖）

- robotaxi **单位经济学具体数字**（单公里成本/单车日订单/毛利）——仍是命门级空白。
- 各芯片/方案商/激光雷达厂商**精确市占率 %** 与 **IPO 后市值/估值倍数**。
- Mobileye 2026 **具体营收数字**（仅知 Q1 beat + raised outlook，方向 recovery，量级未定）。
- 干线物流 robotruck（Aurora/Kodiak）2026 商业化进度。


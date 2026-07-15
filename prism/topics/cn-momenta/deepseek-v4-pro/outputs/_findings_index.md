# Findings Index — cn-momenta/deepseek-v4-pro

> 主 agent 调度提示：写每批 output 前重读本文件，按 addresses(K# 脊柱) + rings(决策链输入合同) 判断 context 是否覆盖所需维度；
> 记忆模糊的 mat_id 单独 Read `outputs/findings_{mat_id}.md` 补回。

## 自有 findings（26 份）

- `mat-11a1c2` | 2025-03-31_华为引望估值1150亿-工商变更与财务数据.md | addresses=[K3] | rings=[valuation-anchor,peer-comparison-financials] | medium/neutral | [引望估值] 注册资本10亿→估值1150亿元人民币（约158亿美元）
- `mat-12eadb` | historical-mirror-argo-cruise-uber-atg-failures.md | addresses=[K2,K4] | rings=[historical-mirror,arena-mirror] | high/neutral | [Argo AI·2016-2022] 2017年福特投10亿美元，2019年大众加投10亿现金+16亿美元（Audi自驾部门）；员工>2000人；2021年错过商用Robotaxi目标；2022年1…
- `mat-16b021` | 2026-06-29_2026-the-first-year-of-robotaxis-waymo-tesla-uber三.md | addresses=[K4] | rings=[bull-bear,arena-mirror] | low/neutral | [Waymo 安全数据] 安全记录127M英里，严重事故减少90%
- `mat-17d88d` | 2025_HK09660_annual_2026-04-30_HORIZONROBOT-W.pdf | addresses=[K3] | rings=[valuation-anchor,peer-comparison-financials,biz-moat-unit-econ] | high/neutral | [市场地位] 2025全年地平线在中国国产乘用车基础ADAS市场市占率47.7%排名第一；高阶NOA市场市占率14.4%，与某领先中国科技企业（华为15.2%）+某美国科技公司构成三强（CR3=89%…
- `mat-205a7c` | sec/2025_PONY_20-F_2026-04-22/item_11_quant_risk.md | addresses=[K2,risk] | rings=[risk] | low/neutral | Item 11定量风险敞口内容极少（~1,900字节），未提供可量化的市场/信用/流动性风险暴露数据
- `mat-21332f` | 2026-03-04_东吴证券-2026年智驾平权之车企智驾方案梳理.md | addresses=[K2,K3] | rings=[biz-moat-unit-econ,peer-comparison-financials] | medium/neutral | [比亚迪方案分层] 天神之眼A（508TOPS, 3激光雷达, 双Orin-X）：Momenta算法→仰望；天神之眼B（254TOPS, 1激光雷达, 单Orin-X）：Momenta算法→腾势/中高…
- `mat-264896` | 2026-06-29_曹旭东-momenta创始人-ceo-完整履历及创业经历.md | addresses=[K2] | rings=[mgmt-capital-alloc] | low/neutral | [曹旭东履历] 清华毕业 → 微软亚洲研究院 → 商汤科技 → 2016年创办Momenta
- `mat-2acc22` | sec/2025_WRD_20-F_2026-04-23/item_4_business.md | addresses=[K3,K5,Q1,scope] | rings=[biz-moat-unit-econ,arena-mirror,peer-comparison-financials] | high/neutral | [产品矩阵] WeRide L4四线并进 Robotaxi（2025年销123辆）+ Robobus（156辆）+ Robovan（28辆）+ Robosweeper（91辆）+ L2 ADAS We…
- `mat-36233b` | sec/2025_PONY_20-F_2026-04-22/item_5_mda.md | addresses=[K2,K4,K5,Q1] | rings=[financial-arc,biz-moat-unit-econ,peer-comparison-financials] | high/neutral | [营收] 2025年$90.0M（+20.0% YoY）。Robotaxi服务$16.6M（+128.6%，付费收入+400%）；Robotruck$40.6M（+0.6%）；许可与应用$32.8M（…
- `mat-432c7b` | 2026-06-29_robotaxi-cost-per-mile-2026-0-18-target-breakdown.md | addresses=[K4] | rings=[bull-bear,biz-moat-unit-econ] | low/neutral | [成本目标] 2026年Robotaxi每英里成本目标$0.18
- `mat-478b0c` | sec/2025_WRD_20-F_2026-04-23/item_5_mda.md | addresses=[K2,K4,K5,Q1] | rings=[financial-arc,biz-moat-unit-econ,peer-comparison-financials] | high/neutral | [收入结构质变] 2025年营收RMB684.6M（+89.6% YoY）。产品收入RMB359.8M（52.6%，+310.3% YoY）首次超过服务收入RMB324.7M（47.4%，+18.8%…
- `mat-48a1d3` | 2026-06-29_21对话-momenta曹旭东-大逃杀时刻-中国智驾公司只剩3家.md | addresses=[K2] | rings=[mgmt-capital-alloc,biz-moat-unit-econ] | low/neutral | [曹旭东判断] 中国智驾公司最终只剩3家，竞争格局将在2025底/2026年初定型
- `mat-5f0b68` | sec/2025_PONY_20-F_2026-04-22/item_4_business.md | addresses=[K3,K5,Q1,scope] | rings=[biz-moat-unit-econ,bull-bear,arena-mirror,peer-comparison-financials] | high/neutral | [Robotaxi车队] 截至2026-03-31，运营超1,400辆Robotaxi，累计自动驾驶里程>65M公里。2026年底目标超3,000辆/20+城市全球部署
- `mat-62846c` | 2026-06-29_对话曹旭东-创业8年-为何选择-一个飞轮两条腿-战略.md | addresses=[K2] | rings=[mgmt-capital-alloc,biz-moat-unit-econ] | low/neutral | [曹旭东路径] 清华退学→微软→商汤→创业
- `mat-657deb` | historical-mirror-mobileye-cycle.md | addresses=[K2,K3] | rings=[historical-mirror,arena-mirror,valuation-anchor] | high/neutral | [Mobileye时间线] 1999成立→2004首颗EyeQ1→2014 NYSE IPO（$890M）→2017 Intel $153亿收购（$63.54/股）→2021出货第1亿颗EyeQ→20…
- `mat-666373` | 2026_WRD_6-K-earnings_2026-06-29.htm | addresses=[-] | rings=[financial-arc] | low/neutral | [股份回购] WeRide (00800.HK) 于2026-06-26在纳斯达克回购1,242,285股A类普通股，均价USD 1.8067/股，成交总额$2,244,410.57
- `mat-690006` | sec/2025_PONY_20-F_2026-04-22/item_3_key_info.md | addresses=[K1,K6,risk] | rings=[risk,bull-bear,mgmt-capital-alloc] | high/neutral | [VIE架构] 2024年2月解除VIE，前VIE已成为全资子公司。自动驾驶行业不在《外商投资负面清单(2024版)》，属外资鼓励类。Momenta同理
- `mat-75eb22` | 2026-06-29_momenta港股ipo-物理ai第一股的估值叙事与智驾赛道分析.md | addresses=[K1] | rings=[valuation-anchor] | low/neutral | [IPO 估值] 中金+德意志联席保荐，IPO估值约1000亿人民币（~140亿美元）——与另一篇90亿美元估值不一致
- `mat-986f3c` | sec/2025_WRD_20-F_2026-04-23/item_3_key_info.md | addresses=[K1,K6,risk] | rings=[bull-bear,risk] | high/neutral | [行业风险] WeRide 自2017年至今仍未盈利，2025年亏损RMB1,655M，经营现金净流出RMB1,322M；三年累计亏损RMB6,121M，经营现金净流出RMB2,390M。明确提示"l…
- `mat-a6dcac` | 2026-06-29_千亿独角兽即将ipo-momenta估值90亿美元-募资约10亿美元.md | addresses=[K1] | rings=[valuation-anchor] | low/neutral | [IPO 估值] 约90亿美元（约650亿人民币）
- `mat-aa82d8` | 2026_HK06880_prospectus_2026-06-29_MOMENTA-W.pdf | addresses=[K1,K2,K3,K4,K5] | rings=[biz-moat-unit-econ,financial-arc,mgmt-capital-alloc,valuation-anchor,consensus,bull-bear,peer-comparison-financials] | high/neutral | [营收] 7.43亿→13.25亿→24.13亿，增速78.4%→82.1%
- `mat-df5080` | 2026_PONY_6-K-earnings_2026-06-10.htm | addresses=[-] | rings=[financial-arc] | low/neutral | [公司治理] Pony AI 任命 CFO 王奂俊（Haojun Wang）为联席公司秘书，2026-06-10生效
- `mat-e24f1c` | sec/2025_WRD_20-F_2026-04-23/item_18_financial.md | addresses=[Q1,valuation] | rings=[financial-arc,valuation-anchor] | low/neutral | Item 18仅含一句话索引：「合并财务报表附于本年度报告末尾」
- `mat-f0db64` | sec/2025_WRD_20-F_2026-04-23/item_11_quant_risk.md | addresses=[K2,risk] | rings=[risk,financial-arc] | medium/neutral | [外汇敞口] 美元现金US$207M+美元应收US$9.4M+美元应付US$146M。人民币对美元±10%→亏损变动RMB49.2M。未使用衍生品对冲
- `mat-f997d9` | 2026-06_城市NOA市场份额更新-Momenta华为元戎三强.md | addresses=[K1,K3] | rings=[biz-moat-unit-econ,bull-bear] | high/neutral | [Momenta 市占率] 第三方城市NOA供应商市场：Momenta 65%（CIC 2025-03至2026-02）/ 61.06%（中汽协 2025年1-11月）
- `mat-fbe9d7` | sec/2025_PONY_20-F_2026-04-22/item_18_financial.md | addresses=[Q1,valuation] | rings=[financial-arc,valuation-anchor] | low/neutral | 完整财务报表在20-F末尾，未包含在此sec-section切片中

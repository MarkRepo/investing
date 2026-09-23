---
mat_id: mat-41683c
filename: sec/_raw/2019_AAOI_10-K_2020-02-28.htm
source_type: annual-report
extracted: 2026-09-01
quality: high
bias: neutral
addresses: [K1, K2, K6, K9]
rings: [historical-mirror, biz-moat-unit-econ, peer-comparison-financials]
resolves: c_investment_case 镜鉴 1（2017-2019）此前 100% 为训练知识级回忆
note: 05-critic Step 6.5 兜底，自 SEC EDGAR 直下 FY2019 10-K 全文（3.16MB）。split_file 只切出 1 节（已知老毛病），改按 _extract_lines 手工定位。
---

## 核心数据点与事实

### 一、镜鉴 1 的机理与量级（全部一手，替代训练记忆）

- [FY2019 10-K 原文，Item 1 与 Item 7 各出现一次] **"In 2019, 2018 and 2017, our revenue was $190.9 million, $267.5 million, and $382.3 million and our gross margin was 24.2%, 32.8%, and 43.5%."**
  → 收入 **$382.3M(2017) → $267.5M(2018，−30.0%) → $190.9M(2019，−28.6%)**，两年累计 **−50.1%**；毛利率 **43.5% → 32.8% → 24.2%**，两年 **−19.3pp**。
- [原文，收入下滑归因] **"The decrease in revenue for the year was driven primarily by decreased demand for our 40 Gbps and 100 Gbps transceivers. The decrease in 100 Gbps demand was mostly from one major customer."**
  → 校正 case 的记忆版归因（"40G 见顶而 100G 未接棒"）：**一手口径是 40G 与 100G 需求同时下滑，且 100G 的下滑主要来自单一大客户**。即当年的杀伤不是"世代没接上"，而是**世代切换 + 单一大客户抽单叠加**。
- [原文，负经营杠杆] "Cost of goods sold **decreased by $35.0 million, or 19.5%**, from 2018 to 2019, primarily due to a **28.6% decrease in sales**."
  → 收入 −28.6% 而成本仅 −19.5% → 下行期成本刚性，毛利率被双重挤压。
- [原文，客户集中] 前十大客户占收入 **94.9%(2017) / 92.9%(2018) / 88.1%(2019)**；**2019 年单客户：Microsoft 32.2%、Amazon 24.0%、Facebook 10.9%、Cisco 10.0%**（前四合计 77.1%）。
- [原文，分市场] 2019 年：互联网数据中心 **75.2%**、CATV **19.6%**、telecom 4.4%、FTTH 0.1%。
- [原文，风险因素] **"Historically, our revenue has been significantly concentrated, first within the CATV market and in 2016-2019 within the internet data center market."**
  → 公司自陈其收入集中度**在 CATV 与数据中心之间来回摆**——与今天"CATV 53.8% / 数据中心 42.9%"的两条腿结构是**同一台机器的第三次摆动**，不是新形态。
- ⚠️ **仍未一手化的一项**：case 镜鉴 1 写的"2017 高点约 $103 → 2019 低点约 $8-10，约 −90%"是**股价序列**，10-K 不含股价，故该数值**仍为训练知识级回忆**。但其**基本面对应物已一手化**（收入腰斩 + GM −19.3pp），足以支撑"标出量级"的用途。

### 二、★ 与 case 核心论断相冲突的一条（本份最重要的发现）

> **AAOI 自己的历史毛利率峰值是 43.5%（FY2017）。**

`c_investment_case` 环④ 分歧 1 的整个基础是「**GM 上限就是 CEO 亲口的 32-33%**」，并把 40% 目标当作已退坡的幻想（"退回长期目标、无时间表"）。但一手记录显示：**这家公司在 2017 年实际运行在 43.5% 毛利率**，即 40%+ 对 AAOI 不是没有先例的目标，而是**它自己达到过的水平**。

- 对 case 的削弱：把"32-33% 是结构性天花板"改述为"**32-33% 是当前扩产/物料溢价阶段的出口值**"更贴合证据。反方（独立多头）的质疑①在这一点上**得到一手支持**，且反方当时并不掌握这条数据。
- 对 case 的保留：2017 年的 43.5% 是在**AAOI 作为 40G/100G 先行者、面对 Microsoft 32%+Amazon 24% 的强需求**时取得的；随后两年即崩到 24.2%。因此正确的推论不是"40% 可期"，而是「**这家公司的毛利率是强周期 + 强客户议价的函数，43.5% 与 24.2% 都是它，区间极宽**」——这反而支持 case 环②"必须情景化、不能给单一倍数"的方法选择，也支持把 Bull/Bear 的毛利率带拉宽。

### 三、★ 管理层措辞的跨周期重复模式

| 10-K | 原文 |
|---|---|
| **FY2019** | "We expect continued sales of our 40 Gbps and 100 Gbps products in 2020, and we expect that **sales of 100 Gbps products will likely grow and exceed sales of 40 Gbps** …" |
| **FY2024**（mat-f6b7aa） | "We expect continued sales of our 40 Gbps and 100 Gbps products in 2025, and we expect that **sales of 400 Gbps products will likely exceed sales of 100 Gbps products later in 2025**. However, **quarter-to-quarter results may show considerable variability as is usual in a period of technology transition**." |

→ **同一句式、同一预期结构，相隔五年**。这条对 case 环①梁二（管理层判断可靠性）与环③假设 1（单季台阶可信度）都是新证据：公司在每一轮世代切换都发出"下一代将超越上一代"的预期，**FY2019 那次说完之后紧接着是收入腰斩**。同时公司自己也在 FY2024 承认"技术过渡期的季度业绩会有相当波动"——这句可直接用于环③假设 1 的证据支持度评级。

## 对 case 的处置建议

1. **镜鉴 1 全表重写为一手**：峰谷幅度改用收入 −50.1% / GM −19.3pp（一手），股价 −90% 降级为附注并保留训练记忆标注；"当年最早预警信号"三条改为一手版：① 40G 与 100G **同时**需求下滑；② **单一大客户**抽单为 100G 下滑主因；③ 成本刚性（−19.5% vs 收入 −28.6%）。
2. **"现在是否已现"一栏须重判**：当年的致命组合是"世代切换 + 单一大客户抽单"。今天前三客户占 92%（42/26/24），**第三大客户一年从 6% 跳到 24% 且身份未披露**——按一手镜鉴口径，这比 case 现在列的"规模 1/32"更贴近当年的真实死因。建议把 case 环⑤ 盲点 3（第三大客户身份）的优先级从盲点提到**风险**。
3. **环④ 分歧 1 必须回应 43.5% 这个历史事实**，否则"GM 上限 32-33%"是一个被自家历史反驳的断言。

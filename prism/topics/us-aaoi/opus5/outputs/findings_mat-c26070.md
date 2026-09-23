---
mat_id: mat-c26070
filename: 2026-08-26_sec-filing-applied-optoelectronics-inc---investor-.md
source_type: web-search
extracted: 2026-08-26
quality: medium
bias: bull
addresses: [K3, K6]
rings: [mgmt-capital-alloc, biz-moat-unit-econ]
---

## 核心数据点与事实
- [AAOI IR / SEC filing 原文（Amazon 认股权证 Warrant 全文附件）] **Vesting Event 定义（原文）**：(a) 对 **1,324,233 份 Warrant Shares**，**在权证签署时（the execution of the Warrant）即归属**；(b) 对剩余 [已遮蔽] 份，按 [遮蔽] 个增量档，每档在**公司及/或其关联方累计收到 Amazon 及/或其相关方在商业协议（Commercial Agreement）下或其他形式的累计毛付款（aggregate gross payments）达到 $[遮蔽]** 时归属。
- [同上] **反稀释**：Warrant Shares 数量适用**惯例反稀释调整（customary anti-dilution adjustments）**。
- [同上] **登记权**：在 Transaction Agreement 下，公司已就 Warrant Shares 授予 Amazon **惯例登记权（registration rights）** —— 即 Amazon 可要求公司登记这些股份以便公开出售。
- [同上] 权证附 **Annex A「Form of Notice of Vesting Event」**（致 Amazon.com, Inc. 的归属通知格式）→ 归属由公司**逐档通知**触发，节奏可被外部追踪。
- [同上] 签署方代表：**Michael Phillips，Authorized Signatory**（Amazon 方签署页）。
- [推算，非原文] 以 brief 记的权证总额 **7.945M 股**为分母：**签署即归属的 1,324,233 股 = 16.7%**，**其余 83.3%（~6.62M 股）需 Amazon 实际付款才归属**。
- [推算，非原文] 对 K3 的影响：**7.945M 全部计入完全稀释是"最坏情形"口径**；若按已归属计，当期仅 1.32M —— 二者对 2027Q4 股数的差异达 **6.6M 股（约 7% 股本）**，足以决定 K3 落在 105M 一侧还是 115M 一侧。

## 叙事主线
因为权证 83.3% 的份额**与 Amazon 累计实际付款挂钩、逐档归属并需书面通知**，而非签约即全额发行 → 所以这 7.945M 股稀释在会计上是「或有」的，且**归属越多 = Amazon 采购越多 = 收入越好**（稀释与业绩正相关，是自我对冲结构）→ 对投资意味着 K3 若把 7.945M 全额计入完全稀释，会**同时低估收入而高估股数**（双重罚），brief 提醒的「EV 情景禁双重计价」原则在此适用。

## 反常识/分歧点
1. 市场预期/常识（也是 thesis_v0 的口径）：Amazon 权证 7.945M 股是既定稀释。本文表明：**仅 1,324,233 股（16.7%）在签署时归属**，剩余全部锚定 Amazon 累计付款里程碑 —— **稀释是业绩的函数，不是常数**。
2. **对多方的反向提醒**：权证含**反稀释调整**条款 —— 意味着 AAOI 后续每一次 ATM 增发/转债，都可能**自动上调 Amazon 的权证股数**，即 ATM 的稀释成本被放大（存在乘数效应）。同时 Amazon 拥有**登记权**，具备随时变现的通道（潜在抛压）。
3. 对 K6（客户结构升级）：权证 + 商业协议 + 登记权 + 分档归属的完整结构确认了 **Amazon 侧是「需求担保 + 股权绑定」的真实法律结构**，不是软性 MOU。

## 未回答问题
1. **归属档位的具体金额门槛与每档股数被 SEC 保密处理遮蔽（[***]）** —— 无法据此建模稀释时间表。这是 K3 建模的核心盲点。
2. 权证的**行权价与到期日**未在片段内（brief 记 @$23.6954，本材料无法验证）。
3. 「customary anti-dilution adjustments」的**具体触发条款**（是否含 ATM 低价发行的 weighted-average 保护）—— 若含，$113 位置的 ATM 会额外放大 Amazon 权证股数。
4. 任务预期的**内部人交易 / 13F 持股变动 / 近期 filing 流**在本片段内**完全不存在**（该 IR node 页抓取到的是权证附件正文），未硬榨。

## 质量备注
- 数据新鲜度：权证签署日未在片段内（brief 记 Amazon 结构为近期事件）；文件本身是一次性法律附件，无时效衰减。
- 可信度：**中偏高** —— 来源为公司 IR 的 SEC filing 原文（whitelist，confidence 0.9），引文是法律文本原句；但**关键数字被 SEC 保密遮蔽**，且未抓到行权价/总股数，故整体降为 medium。
- 与已有发现关系：与 mat-ac79e5 存在**机制耦合**（ATM 增发可能通过反稀释条款放大权证股数），这一交互在 thesis_v0 中似未计入，建议在 K3 环节单列。

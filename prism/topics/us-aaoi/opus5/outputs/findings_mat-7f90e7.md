---
mat_id: mat-7f90e7
filename: 2026-08-26_warrant-to-purchase-common-stock.md
source_type: web-search
extracted: 2026-08-26
quality: medium
bias: neutral
addresses: [K3, K6]
rings: [mgmt-capital-alloc, bull-bear]
conflicts_with: [findings_mat-68f8ef.md]
conflict_note: 新闻稿称剩余份额"随亚马逊自主采购逐步归属、最高 $40 亿"，但权证原文的归属触发数字（份数、档数、每档金额）全部被删节，无法核实新闻口径。
---

## 核心数据点与事实（严格限于本材料抓到的 Exhibit 4.1 原文片段）

- [SEC EDGAR, Applied Optoelectronics Exhibit 4.1（appliedopto_ex0401.htm）"Warrant to Purchase Common Stock"] **"Commercial Agreement" 的定义 = 一份 Manufacturing and Development Services Agreement（制造与开发服务协议），签约方为 Amazon Data Services, Inc. 与本公司及其关联方，且"as it may be amended from time to time"（可不时修订）。**
  - 关键含义：与权证挂钩的商业协议**主体是 Amazon Data Services, Inc.**（AWS 基础设施实体），且是**制造与开发服务协议**（服务/制造性质），**不是采购承诺协议（purchase agreement / supply agreement）**，并且**可被随时修订**。
- [同上] "Common Stock" 定义为本公司**每股面值 $0.001** 的普通股；"Company" = Applied Optoelectronics, Inc.，**特拉华州公司**。
- [同上] **"Vesting Event"（归属事件）条款原文结构**：
  - **(a) 关于 1,324,233 份 Warrant Shares：权证的签署即为归属事件**（"the execution of the Warrant"）——即**签署即刻无条件归属 1,324,233 份**。
  - **(b) 关于 [删节] 份 Warrant Shares：分为 [删节] 个每档 [删节] 份的增量，以及 [删节] 个每档 [删节] 份的增量**（"[***] increments of [***] Warrant Shares and [***] increments of [***] Warrant Shares"），**每一档的触发条件为：公司及/或其任何关联方累计收到亚马逊及/或其任何[关联方]在 Commercial Agreement 项下或其他形式的累计总付款达到 $[删节]**（"aggregate gross payments under the Commercial Agreement or otherwise totaling $[***] from or on behalf of Amazon and/or any of…"）。
- [同上] 归属计量口径的两个重要细节（原文用词）：①计量的是 **"aggregate gross payments"（累计总付款）而非订单额/发票额**——以现金实收为准；②**"under the Commercial Agreement or otherwise"**——不限于该商业协议，其他形式付款也计入，即归属口径比"该协议下的采购"更宽。
- [同上] 权证含 **Annex A「Vesting Event 通知书格式」（Form of Notice of Vesting Event）**，收件方为 **Amazon.com, Inc.**——即归属需由公司发出书面通知，存在**通知/确认程序**。
- [同上] 签署页由 **Michael Phillips（Authorized Signatory）**代表一方签署。
- [同上] 文件片段可见页码标记为第 12 页与第 16 页（定义章节位于第 12 页附近，签署页在第 16 页），说明权证正文篇幅约 16 页 + Annex。

## ★ 明确记录：本材料中被删节 / 未抓到的关键数字（K3/K6 的已知盲区）

**被 [***] 删节（原文确实存在但内容遭保密处理，属公司向 SEC 申请的机密处理，无法通过公开文件补齐）：**
1. 分档归属的**总份数**（(b) 项下 Warrant Shares 总量）；
2. **档数**（两组增量各有几档）；
3. **每档增量的份数**（两组各是多少份/档）；
4. **每档触发所需的累计总付款金额 $[删节]**。
→ 后果：**无法计算"亚马逊要付多少钱才解锁多少股"这条最关键的斜率**，也就**无法把 K3 的稀释与 K6 的客户绑定强度量化**。任何关于"$X 采购 → Y 股归属"的推算若无原文支持，都是不可采信的。

**本材料片段中未出现（不能从本 finding 引用，需由其他材料/文件提供）：**总股数 7,945,399、行权价 $23.6954、到期日 2035、$40 亿采购上限、无现金行权（cashless exercise）条款、反稀释条款正文、登记权条款正文——**本材料抓取的仅为定义章节 + Vesting Event 定义 + 签署页/Annex 标题**，行权价、期限、行权机制、反稀释的正文条款均未抓到。

## 叙事主线
因为权证的归属挂钩的是一份**可随时修订的"制造与开发服务协议"下的累计实收现金**、且分档的份数与金额门槛**全部被保密删节** → 所以外部投资者**在结构上无法验证**"亚马逊绑定有多深、稀释按什么斜率发生" → 对投资意味着 K3（稀释边界）与 K6（客户结构升级）在这条最重要的证据上是**永久性盲区**，只能用"1,324,233 份已即刻归属"作为唯一确定数、其余按上限情形做压力测试。

## 反常识/分歧点
市场预期/常识：Amazon 权证 = 采购承诺 = 需求担保（thesis 列的多方论据②）。本材料原文表明：①挂钩协议是 **Manufacturing and Development Services Agreement**（制造与开发服务），**不是供货/采购承诺协议**；②该协议**可被不时修订**；③归属计量是**累计实收总付款**，且**"or otherwise"** 把口径放宽到该协议之外——**整个结构是"亚马逊付了钱才拿股权奖励"的事后激励，而不是亚马逊承诺买多少的事前担保**。即权证是**需求的计量器与折扣券，不是需求的保证书**；且方向上是"亚马逊多买 → 亚马逊多得股权 → 现有股东多被稀释"，对多方论据②构成实质性削弱。

## 未回答问题
1. 分档的份数/档数/每档金额门槛（4 项删节）——需查后续 10-K/10-Q 是否披露"截至期末已归属份数"来反推斜率。
2. 已归属份数与已行权份数截至最近报告期各为多少？本材料无。
3. 行权价、到期日、是否可无现金行权、反稀释的具体机制（是否含向下重定价）——本材料片段未含。
4. 该权证在公司稀释每股计算中按何方法计入（库存股法 / 是否仅计已归属部分）？直接影响 K3 的 105M/115M 判定。

## 质量备注
质量给 medium 而非 high：**来源权威性最高**（SEC EDGAR 一手 Exhibit 4.1 原文），但**抓取覆盖度低**——只抓到定义章节（第 12 页附近）与签署页/Annex 标题，且最关键的 Vesting Event 分档数字**在原文即被 [***] 删节**，不是抓取缺失而是公司主动保密。因此本 finding 的价值不在数字（只有 1,324,233 一个硬数）而在**条款性质的定性纠偏**（"制造与开发服务协议"而非采购协议、"累计实收付款"计量、可修订、or otherwise 放宽口径）。本 finding **严格未引入**同批新闻材料（mat-68f8ef）中的 7.95M / $23.70 / 2035 / $40 亿，也未用训练记忆补全任何条款——凡新闻口径与原文关系不明处已在 conflicts_with 标出。

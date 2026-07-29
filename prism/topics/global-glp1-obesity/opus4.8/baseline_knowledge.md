---
slug: global-glp1-obesity
variant: opus4.8
written_at: 2026-07-22
training_cutoff_estimate: 2026-01
---

# 训练知识 Baseline — 全球肥胖/GLP-1 减重药物行业

> 本文记录 LLM 在**训练截止时（约 2026-01）**对该 topic 的认知现状。
> 今天 2026-07-22，快变 fact 已有约 6 个月衰减风险。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。

## 一、关键事实记忆（32 条）

### A. 机理与适应症（多为静态）
- `[fact-01]` GLP-1 受体激动剂经下丘脑抑制食欲 + 延缓胃排空减重；incretin 类还改善血糖 → 置信度：高 | **静态**
- `[fact-02]` 多靶点趋势：GLP-1 单靶 → GLP-1/GIP 双激动（tirzepatide）→ GLP-1/GIP/glucagon 三激动（retatrutide）→ 疗效阶梯上移，减重从 ~15% 迈向 ~24% → 置信度：高 | 慢变
- `[fact-03]` amylin 通路（cagrilintide 等）是 incretin 之外第二大机制，与 GLP-1 联用（CagriSema）主打疗效叠加 + 肌肉保留 → 置信度：中 | 慢变
- `[fact-04]` 口服小分子 GLP-1（orforglipron / GSBR-1290）绕开多肽的注射 + 冷链 + 产能瓶颈，是"平权化/放量"关键变量；口服多肽（Rybelsus）生物利用度低 → 置信度：高 | 慢变
- `[fact-05]` GLP-1 已从减重外延到 MASH、心衰(HFpEF)、CKD、OSA、成瘾、阿尔茨海默等，标签扩张是 TAM 上修主逻辑（SELECT 试验证 CV 获益）→ 置信度：高 | 慢变

### B. 双寡头在位者（NVO / LLY，快变密集 ⚠️）
- `[fact-06]` Novo Nordisk：semaglutide 三剂型 Ozempic(糖尿病针)/Wegovy(减重针)/Rybelsus(口服)；减重针 Wegovy 是核心 → 置信度：高 | 慢变
- `[fact-07]` Eli Lilly：tirzepatide 双靶 Mounjaro(糖尿病)/Zepbound(减重)，疗效领先 sema；LLY 2025 借减重登顶全球市值最大药企、逼近/超 $1T → 置信度：高 | **快变** ⚠️
- `[fact-08]` LLY orforglipron（口服小分子 GLP-1）2025 年多项 3 期减重/糖尿病读出，减重约 -11%~-12%，拟 2026 提交上市 → 置信度：中 | **快变** ⚠️
- `[fact-09]` LLY retatrutide（三激动）3 期进行中，2 期减重 ~24%（48 周），是疗效天花板候选 → 置信度：中 | **快变** ⚠️
- `[fact-10]` NVO CagriSema（cagrilintide+sema）3 期 REDEFINE 减重约 -22.7%，低于市场此前 ~25% 预期，2024Q4 令 NVO 股价大跌 → 置信度：中 | **快变** ⚠️
- `[fact-11]` NVO 下一代 amycretin（GLP-1+amylin 单分子，皮下+口服）早期数据亮眼，是 NVO 追赶 LLY 的关键管线 → 置信度：中 | **快变** ⚠️
- `[fact-12]` NVO 2025 因 CagriSema 不及预期 + Wegovy 增速放缓 + 美国 compounding 冲击，股价大幅回撤、CEO 换帅（Jørgensen 卸任）→ 置信度：中 | **快变** ⚠️
- `[fact-13]` LLY vs NVO 减重针全球二分天下，合计占绝对份额；LLY 份额持续抢占 NVO → 置信度：高 | **快变** ⚠️

### C. 挑战者 / 第二梯队（快变 ⚠️）
- `[fact-14]` Amgen MariTide(maridebart cafraglutide)：GLP-1 激动 + GIP **拮抗**，月度给药差异化；2024 末 2 期减重约 -20%，但胃肠道副作用/剂量爬坡受关注，2025 推进 3 期 → 置信度：中 | **快变** ⚠️
- `[fact-15]` Viking Therapeutics VK2735(双 GLP-1/GIP)：皮下 2 期 VENTURE 减重 ~-13.8%(13 周)，口服版并行；市值小、长期并购传闻标的 → 置信度：中 | **快变** ⚠️
- `[fact-16]` Roche：2023 收购 Carmot 得 CT-388(双 GLP-1/GIP)，2 期减重 ~-19%(24 周)；另有口服 CT-996；大药厂入场信号 → 置信度：中 | **快变** ⚠️
- `[fact-17]` Structure Therapeutics(GPCR) GSBR-1290：口服小分子 GLP-1，与 orforglipron 同赛道但落后一个身位 → 置信度：中 | **快变** ⚠️
- `[fact-18]` AstraZeneca、辉瑞（danuglipron 口服，曾受挫）、勃林格(survodutide 双 GLP-1/glucagon 主打 MASH) 等亦在场 → 置信度：中 | 慢变

### D. 中国玩家 + 仿制潮（快变 ⚠️）
- `[fact-19]` 恒瑞医药 HRS9531(双 GLP-1/GIP)：2 期减重亮眼；2024 将海外权益 license 给 Kailera Therapeutics(Bain 支持，含 $60M 首付 + 里程碑，总额约 $6B) → 置信度：中 | **快变** ⚠️
- `[fact-20]` 信达生物 mazdutide(IBI362，双 GLP-1/glucagon，源自 Lilly 授权)：2025 在华获批肥胖适应症，中国首批国产双靶减重药之一 → 置信度：中 | **快变** ⚠️
- `[fact-21]` 华东医药：利拉鲁肽生物类似药(利鲁平)国内获批减重；布局司美/口服管线，减重是其创新转型主线 → 置信度：中 | **快变** ⚠️
- `[fact-22]` 中国 semaglutide 化合物专利约 2026 到期（早于美国），触发国产仿制大潮；九源基因(甘李关联)等司美格鲁肽生物类似药 2026 拟获批 → 置信度：中 | **快变** ⚠️
- `[fact-23]` 美国 semaglutide 化合物专利约 2031-2033 到期（说法不一），tirzepatide 更晚 → 置信度：低 | 慢变
- `[fact-24]` 中国是全球最大肥胖人口国之一，本土市场 + 出海双逻辑；国产双靶多走"me-better + 价格/BD 出海" → 置信度：中 | 慢变

### E. 定价 / 支付 / 分销 / 监管（快变 ⚠️）
- `[fact-25]` 美国现金支付渠道兴起：LillyDirect(Zepbound 现金价 ~$349-499/月)、NovoCare(Wegovy ~$499)，绕开 PBM 降低净价 → 置信度：中 | **快变** ⚠️
- `[fact-26]` FDA 2025 宣布 sema/tirzepatide 短缺结束 → 复方(compounding)药合法窗口关闭，冲击 compounding 生态与 telehealth → 置信度：中 | **快变** ⚠️
- `[fact-27]` HIMS & Hers：短缺期靠复方 semaglutide 放量，后与 NVO 合作又告吹(NVO drops HIMS)，2026 战略转向 → 置信度：中 | **快变** ⚠️
- `[fact-28]` Medicare：IRA 药价谈判把 semaglutide 纳入某一轮；Trump 政府阻止 Medicare 覆盖"纯减肥"用途、CMS 取消面向老人的 GLP-1 试点 → 置信度：中 | **快变** ⚠️
- `[fact-29]` 商业保险覆盖减重药仍是放量最大摩擦点；雇主计划因成本回撤覆盖是逆风 → 置信度：中 | 慢变
- `[fact-30]` 供给端：多肽注射产能(灌装/司美原料/GLP-1 API)曾是硬约束，NVO(收 Catalent 三厂)/LLY 巨额扩产；口服小分子改变产能格局 → 置信度：中 | 慢变

### F. 市场规模 / 估值锚（快变 ⚠️）
- `[fact-31]` 卖方对 2030 全球肥胖药 TAM 普遍 $100-150B（部分乐观 $150B+），是全行业最大单一增长叙事 → 置信度：中 | 慢变
- `[fact-32]` 估值：LLY 训练时 forward PE 约 30-40x（成长溢价）；NVO 回撤后 PE 大幅压缩(~15-20x)；小玩家(VKTX/GPCR)无盈利、按管线期权/并购价值定 → 置信度：低 | **快变** ⚠️

**第一节统计**：静态 ~2 条 / 慢变 ~11 条 / 快变 ~19 条 ⚠️。
**快变 + 高/中置信** 占绝对多数（临床读出、股价/估值、定价政策、仿制/获批），是最易蒙蔽 thesis 的子集 → 第五节逐条对应 query。

## 二、关键人物 / 公司 / 产品

- **Eli Lilly (LLY)**：疗效+口服双领先者。产品 tirzepatide(Zepbound)、管线 orforglipron(口服)、retatrutide(三激动)。行业定盘星。
- **Novo Nordisk (NVO)**：在位龙头承压者。semaglutide 全家桶 + 管线 CagriSema/amycretin。2025 换帅、股价重挫。
- **Amgen (AMGN)**：差异化挑战者。MariTide 月度给药 + GIP 拮抗独特机制。
- **Viking (VKTX)**：纯 biotech 高 β + 并购标的。VK2735 皮下/口服。
- **Roche**：大药厂后入场者（Carmot CT-388）。
- **Structure Tx (GPCR)**：口服小分子挑战者（GSBR-1290）。
- **恒瑞医药 (600276)**：中国龙头，HRS9531 → Kailera 出海样板。
- **信达生物 (01801)**：mazdutide 国产双靶先发获批。
- **华东医药 (000963)**：类似药 + 创新减重转型。
- **HIMS & Hers (HIMS)**：telehealth 分销，复方红利退潮后转型。
- **Kailera Therapeutics**：Bain 系，接盘恒瑞管线出海的美国壳。

## 三、产业链 / 竞争格局认知

**主线**：肥胖药是十年一遇的超级增长赛道，机制从单靶→多靶+amylin 疗效上移，剂型从注射→口服平权化，双寡头(LLY/NVO)吃绝大部分利润池，但格局在多点松动。

**利润池当前分布**：注射 incretin 双寡头拿走绝对份额，LLY 凭疗效(tirzepatide)+口服(orforglipron)+三激动(retatrutide)三张牌全面压制 NVO；NVO 靠先发装机 + amylin/amycretin 追赶。

**松动点（利润池潜在迁移方向）**：
1. **口服小分子平权化**——若 orforglipron 顺利上市，口服放量把 TAM 从"能负担注射+愿打针"的窄口扩到全球基层，规模逻辑压过单价，利好有口服牌的玩家(LLY 领先，GPCR/VKTX 跟随)。
2. **疗效深化(三激动/amylin combo)**——retatrutide/MariTide/CagriSema 争 24%+ 减重天花板，若临床兑现则高端市场重新洗牌。
3. **仿制/价格战**——中国 sema 专利 2026 先到期引国产仿制潮，压中国市场价格；美国 2031+ 才轮到，时间差是关键。
4. **分销/支付**——现金支付(LillyDirect/NovoCare)+ 保险覆盖 + Medicare 政策决定净价与放量斜率；telehealth(HIMS)红利退潮。

**中美两套逻辑**：美国是净价+覆盖+疗效战；中国是仿制+医保谈判+国产双靶 me-better+BD 出海。

## 四、训练知识盲点（自我承认）

- **近 6 个月(2026-01→07)所有临床读出**：orforglipron 3 期完整头对头数据、retatrutide 3 期进展、MariTide 3 期剂量方案、VK2735 3 期入组/读出、Roche CT-388 2 期后续——训练后大概率有更新。
- **最新股价/估值/市值**：LLY 是否已破 $1T、NVO 回撤后当前 PE、VKTX/GPCR 并购是否落地——快变，训练值已过时。
- **2026 定价与政策落地**：Medicare/IRA 谈判价公布、Trump 政府减重药覆盖最新表态、雇主/PBM 覆盖趋势——快变。
- **中国仿制获批时间表**：九源基因/其他司美类似药是否已获批上市、国产双靶最新获批适应症——快变。
- **HIMS 2026 战略转向的具体内容与财务影响**——快变。
- **各公司最新季报的减重药收入拆分**（Wegovy/Zepbound 季度销售、增速）——快变，需读财报。
- **供给端产能最新状态**（短缺是否彻底解除、扩产进度）——慢变但训练后可能变化。

## 五、需要 web-search 校准的优先项

> 强制：第一节快变+高/中 fact 逐条对应。以下 query 直接可 WebSearch。

1. `orforglipron Phase 3 obesity results 2026 weight loss data FDA submission`（fact-08 快变+中）
2. `retatrutide Phase 3 TRIUMPH results 2026 weight loss`（fact-09 快变+中）
3. `Amgen MariTide Phase 3 dosing 2026 tolerability results`（fact-14 快变+中）
4. `Viking Therapeutics VK2735 Phase 3 enrollment results 2026 acquisition`（fact-15 快变+中）
5. `Novo Nordisk 2026 stock CagriSema amycretin CEO new outlook`（fact-10/11/12 快变+中）
6. `Eli Lilly market cap 2026 trillion Zepbound orforglipron sales`（fact-07/13 快变+高）
7. `semaglutide China patent expiry 2026 generic biosimilar approval 九源基因`（fact-22 快变+中）
8. `恒瑞 HRS9531 Kailera 2026 临床进展 出海`（fact-19 快变+中）
9. `信达 mazdutide 2026 销售 获批适应症 中国减重`（fact-20 快变+中）
10. `Medicare GLP-1 obesity coverage 2026 IRA negotiation price Trump`（fact-28 快变+中）
11. `HIMS Hers 2026 GLP-1 strategy shift weight loss revenue`（fact-27 快变+中）
12. `Roche CT-388 obesity Phase 2 2026 update pipeline`（fact-16 快变+中）
13. `Wegovy Zepbound Q1 2026 sales growth Novo Lilly obesity revenue`（fact-13/32 快变，需财报交叉）

**质检自检**：第一节快变+高/中 fact ≈ 15 条 ≤ 第五节 query 13 条覆盖主簇（部分 query 一条盖多 fact，如 #5 盖 fact-10/11/12、#6 盖 fact-07/13）。fact-32 估值走财报+#6 交叉；fact-26(compounding) 由默认 prescan 覆盖。满足覆盖要求。

## 六、prescan 校准结果（2026-07-22 回写）

> Step 4.5 prescan 跑 18 条 query（13 baseline 优先 + 5 覆盖槽），入库 54 份新 web-search material（health=full, hit_rate=1.0）。以下逐条对照第一节 fact-NN。资料多为 2025-06~2026-05 事件，晚于原材料库截止 05-26。

### 被推翻 / 需重置（高优先级——thesis_v0 不要再引用原 fact 措辞）
- `[fact-10/12]` **NVO CagriSema 从"不及预期"恶化为"直接失败"**：2026-02-23 头对头 III 期**未能击败 LLY Zepbound**，NVO 股价单日 -15%；2026 销售指引 -5~-13%，全面落后 LLY。→ NVO 追赶叙事重创，thesis 对 NVO 应更空。
- `[fact-27]` **HIMS 反转**：训练时"NVO 合作告吹"，现校准为 **HIMS 2026 新签 NVO 合作**、从复方转品牌 GLP-1、停复方广告；但 Q1 2026 净亏 $92M、EPS -$0.40 远逊预期。→ 分销叙事变复杂，非单向利好。
- `[fact-28]` **Medicare 覆盖反转（关键政策）**：训练时"Trump 阻止 Medicare 覆盖减重"，现校准为 **2026 Medicare 首次把肥胖作为独立适应症纳入 GLP-1 覆盖**（里程碑）；叠加 2025-11 Trump-LLY-NVO 自愿协议价 ~$245/月经 TrumpRx.gov；IRA 第二轮谈判价更高（Wegovy 最高剂量 $385.63/月）。→ 支付端从纯逆风转为"覆盖扩张 + 净价下压"双向。
- `[fact-31]` **TAM 口径下修**：Grand View 定 2030 肥胖治疗市场 **$60.5B**（$29B@2026，CAGR 22.3%），低于训练时卖方 $100-150B——口径/范围差异大，引用 TAM 时须标来源与口径，勿用单一乐观数。

### 被验证 / 升级（可继续引用，置信度提升）
- `[fact-07/13]` LLY 确认破 **$1T 市值**，2026 指引 **$80-83B**(+25%)，Zepbound Q1 2026 美国收入 **+79% 至 $4.1B** → 高+。定盘星地位强化。
- `[fact-08]` orforglipron 确认+升级：**已获批商品名 Foundayo**，1H2026 上市；ATTAIN-2 肥胖+T2D 减重 10.5% → 口服平权化落地在即。
- `[fact-09]` retatrutide 确认+升级：TRIUMPH-1 顶线 12mg 80周 **28.3%**、104周(BMI≥35)**30.3%**、n=2,339 → 疗效天花板兑现。
- `[fact-14]` MariTide 确认：III 期已启（72周/3剂量/8周滴定），**耐受性(呕吐)是命门**，数据日 AMGN -6%。
- `[fact-15]` VK2735 确认：VANQUISH-1/-2 皮下入组完成，**VANQUISH-2 顶线预计 2026Q3**；口服 III 期 4Q26 启。
- `[fact-16]` Roche CT-388 确认+升级：II 期 24mg 48周**安慰剂校正 22.5%**、无平台期，ADA2026 出更多数据。
- `[fact-19]` 恒瑞 HRS9531 确认+升级：III 期 6mg 48周 **19.2%** 无平台期，近期递 NMPA NDA；**Kailera 2026-04 纳斯达克 IPO** → 出海样板兑现。
- `[fact-20]` 信达 mazdutide(信尔美®) 确认：NMPA **2025-06-27 获批**、6 天闪电商业化，~¥1260/月，峰值销售预测 >¥50 亿 → 国产双靶先发落地。

### 仍未校准（thesis_v0 引用时标 uncertain）
- `[fact-22]` 中国 sema 专利 2026 到期确认，九源/丽珠/华东/联邦已申报仿制；但**到期约一月后中国尚无仿制获批**（来源为已 drop 的 substack，未验证）→ 仿制潮"申报≠获批放量"，节奏 uncertain，thesis 勿假设 2026 内价格战全面爆发。
- `[fact-23]` 美国 sema 专利到期（2030s 初）说法仍不一 → 保持低置信。
- `[fact-32]` NVO 回撤后 PE 进一步压缩、VKTX/GPCR 期权价值 → 具体倍数走财报交叉，未独立校准。

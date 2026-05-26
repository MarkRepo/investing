---
slug: global-glp1-obesity
variant: claude-opus-4-7
written_at: 2026-05-26
training_cutoff_estimate: 2026-01
---

# 训练知识 Baseline — GLP-1 减肥药

> 本文记录 LLM 在训练截止时对该 topic 的认知现状。后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。

## 一、关键事实记忆（36 条）

### A. 科学机制与代际划分
- `[fact-01]` GLP-1 = Glucagon-Like Peptide-1，肠促胰岛素激素，通过 GLP-1R 受体激动作用降低血糖、延缓胃排空、抑制食欲。置信度：高
- `[fact-02]` 减重机制主要来自中枢食欲抑制（下丘脑 POMC/AgRP）+ 胃排空延缓，不是单纯"代谢加速"。置信度：高
- `[fact-03]` 第一代：每日注射利拉鲁肽（Saxenda 减重指征 2014 FDA 批），减重幅度 ~5-8%。置信度：高
- `[fact-04]` 第二代：每周注射司美格鲁肽（Wegovy 2021-06 FDA 批减重指征），STEP 1 试验 68 周减重 ~14.9%。置信度：高
- `[fact-05]` 第三代：双靶点 GLP-1/GIP——替尔泊肽（Zepbound 2023-11 FDA 批减重指征），SURMOUNT-1 试验 72 周减重 ~22.5%（15mg 组）。置信度：高
- `[fact-06]` 第四代候选：三靶点 GLP-1/GIP/GCG（Lilly retatrutide），Phase 2 数据 48 周减重 ~24.2%，可能达 ~30% 长期。置信度：中（Phase 3 数据未读出）
- `[fact-07]` CagriSema（NVO 司美格鲁肽 + Cagrilintide amylin agonist）REDEFINE 1 试验 2024-12 读出令市场失望，68 周减重 ~22.7%（vs 预期 25%+），NVO 股价当日跌 18%。置信度：高
- `[fact-08]` 口服小分子 GLP-1：Lilly orforglipron（非肽类），无需冷链/食物限制，ACHIEVE-1（T2D）/ATTAIN-1（obesity）Phase 3 数据 2025 读出。置信度：中

### B. 头部公司与产品
- `[fact-09]` Novo Nordisk（NVO）2024 全年营收约 DKK 290B（~$42B），Ozempic（糖尿病）+ Wegovy（减重）合计 ~$30B+。置信度：中（精确数字需校准）
- `[fact-10]` Eli Lilly（LLY）2024 全年营收约 $45B，Mounjaro（糖尿病）+ Zepbound（减重）合计 ~$16-20B。置信度：中
- `[fact-11]` 2024 年 NVO 市值最高约 $650B（2024-06 顶），2024 H2 因 CagriSema 失望 + 供应改善但需求质疑跌至 $400B 区间。置信度：中
- `[fact-12]` 2024 年 LLY 市值最高约 $900B+，超越 JPM 一度成美国最大医药股。置信度：中
- `[fact-13]` 供应瓶颈：2022-2024 NVO/LLY 都长期处于 FDA 短缺名单，NVO 2024 通过母公司 Novo Holdings $16.5B 收购 Catalent（合同制药）锁定灌装产能。置信度：高
- `[fact-14]` 2025-02 FDA 宣布司美格鲁肽短缺解决，触发 503A/503B compounded（复方调制）GLP-1 退出市场倒计时（503B 90 天，503A 60 天）。置信度：中（具体生效日期需校准）

### C. 国内玩家
- `[fact-15]` 信达生物（1801.HK）mazdutide（玛仕度肽，IBI362）GLP-1/GCG 双靶点，从 Lilly 授权引进，2024-06 NMPA 受理减重指征 NDA，2025 上半年获批预期高。置信度：中
- `[fact-16]` 恒瑞医药（600276/1276.HK）HRS9531 GLP-1/GIP 双靶点（替尔泊肽 me-too），Phase 2 减重数据 36 周 ~22%，2024-05 license-out 给美国 Hercules CM（先付 $110M + 里程碑 $6B），市场视为重大利好。置信度：中
- `[fact-17]` 华东医药（000963）利拉鲁肽生物类似药"利鲁平"2023-07 国内首仿获批，定价 ~¥500/支，国内糖尿病/减重双指征。置信度：中
- `[fact-18]` 其他在研：鸿运华宁（GMA106 GLP-1）、翰宇药业（仿制肽）、博瑞医药（GLP-1 小分子）、九源基因（利拉鲁肽生物类似药）。置信度：低（管线动态变化快）

### D. 市场规模与渗透
- `[fact-19]` 全球 GLP-1 类药物 2024 总销售额 ~$50B，其中减重适应症 ~$20-25B（其余为糖尿病）。置信度：中
- `[fact-20]` 卖方一致预期 GLP-1 类药物 2030 全球峰值销售 $130-150B，部分激进预测看到 $200B+。置信度：中
- `[fact-21]` 美国成人 ~9% 报告曾用过 GLP-1（KFF 2024 调查），其中 ~6% 为减重目的。中国渗透率极低 <0.5%。置信度：中
- `[fact-22]` 适用人群天花板（理论）：美国成人 BMI≥27 ~40%（~1 亿人），全球 ~10 亿人。实际付费意愿/可及性筛选后 TAM 远小于此。置信度：中

### E. 支付与政策
- `[fact-23]` 美国定价：Wegovy 月费 ~$1,349 list，Zepbound ~$1,059 list；商业保险覆盖率 2024 提升至 ~40%（雇主计划），Medicare 长期禁止覆盖减重药（1003 法案）。置信度：中
- `[fact-24]` Biden 政府 2024-11 提议修改 Part D 规则允许 Medicare 覆盖肥胖药（影响 ~340 万 Medicare 受益人），需经 CMS 终规。Trump 当选后政策方向不明。置信度：中
- `[fact-25]` RFK Jr 出任 HHS 部长（2025-02 确认）公开质疑 GLP-1 减重药"应被生活方式干预替代"，对该类药物 Medicare 覆盖立场偏负面。置信度：中（最新表态需校准）
- `[fact-26]` IRA 谈判：Ozempic/Wegovy 因属同一活性物质（司美格鲁肽），可能在 2027 谈判年度被纳入降价名单（首批 10 药已不含 GLP-1，第二批 15 药 2026 公布）。置信度：中
- `[fact-27]` 中国 NRDL：司美格鲁肽（糖尿病诺和泰）已入医保乙类，Wegovy（减重）2024-06 国内获批后未入医保（自费）。置信度：中

### F. 专利与生命周期
- `[fact-28]` 司美格鲁肽 COM 专利：美国 2031-12（含 PTE 延期），欧洲 2031-03，中国 2026-03（NVO 已就专利延期申请异议），印度/巴西更早。置信度：中
- `[fact-29]` 替尔泊雕 COM 专利：美国 2036-08（含 PTE 待批），中国/印度 2034 前后。置信度：中
- `[fact-30]` 司美格鲁肽中国专利 2026-03 到期 → 国内生物类似药竞争 2027 起开闸，恒瑞/翰宇/九源等多家已布局。置信度：中
- `[fact-31]` 利拉鲁肽 COM 专利 2023 全球到期，已有华东医药/通化东宝/翰宇等生物类似药上市。置信度：高

### G. 临床证据扩展
- `[fact-32]` SELECT 试验（2023-08 NEJM）：超重/肥胖+心血管病患者用司美格鲁肽 2.4mg，MACE 风险降 20%，首次证明减重药有 CV outcome benefit，推动支付方扩展覆盖。置信度：高
- `[fact-33]` 适应症扩展进行时：阻塞性睡眠呼吸暂停（OSA）、慢性肾病（FLOW 试验 2024-05 阳性）、心衰（STEP-HFpEF 阳性）、阿尔茨海默症（evoke 试验 2026 读出）、酒精/药物成瘾（学术研究中）。置信度：中
- `[fact-34]` 安全性问题：胃轻瘫（gastroparesis）诉讼数百例已在 MDL 整合，自杀意念信号（EMA 调查后未确认）、甲状腺髓样癌动物模型信号、NAION（视神经病变）2024-07 哈佛研究信号。置信度：中

### H. 衍生 + 二阶受益
- `[fact-35]` 设备：Ypsomed（瑞士笔形注射器供应商，为 NVO/LLY 供 Wegovy/Zepbound auto-injector）2024 营收受益显著；Stevanato Group（玻璃瓶供应商）。置信度：中
- `[fact-36]` 二阶受损：减肥手术（Intuitive Surgical 等）、零食食品（Hershey/PepsiCo）2023-2024 部分研究显示 GLP-1 用户食量降 20-30%，但实际营收冲击有限；OSA 设备（ResMed/Inspire Medical 2024 股价压力）；透析（DaVita 2024 受 FLOW 试验冲击）。置信度：中

## 二、关键人物 / 公司 / 产品

### 高管/科学家
- **Lars Fruergaard Jørgensen** — NVO CEO（2017 至今），2024 Q4 CagriSema 失望后承压。
- **David A. Ricks** — LLY CEO，主导 Mounjaro/Zepbound 商业化。
- **Daniel J. Drucker** — 多伦多大学教授，GLP-1 生物学奠基人，理论权威。

### 公司管线对照
- **NVO**: Wegovy（在售）/ Ozempic（在售）/ Rybelsus（口服 sema 在售）/ CagriSema（Phase 3 失望）/ amycretin（口服 GLP-1+amylin Phase 2 数据强）。
- **LLY**: Zepbound（在售）/ Mounjaro（在售）/ retatrutide（GLP-1/GIP/GCG Phase 3）/ orforglipron（口服小分子 Phase 3）/ eloralintide（amylin Phase 2）。
- **Amgen**: MariTide（GLP-1R agonist + GIPR antagonist 月针）Phase 2 2024-11 数据低于预期。
- **Pfizer**: danuglipron（口服小分子）2023-12 因肝毒性终止，2024-04 重启另一构型。
- **Roche**: CT-388（口服双靶点，2023 从 Carmot 收购 $2.7B）Phase 2 中。
- **Structure Therapeutics**: GSBR-209（口服小分子）Phase 2。
- **Viking Therapeutics**: VK2735（双靶点皮下/口服）Phase 2 数据强劲，2024 被市场视为收购标的。

### 衍生玩家
- **Catalent**（NVO 母公司收购）/ **Thermo Fisher**（CDMO）/ **Ypsomed**（注射器）/ **Stevanato**（玻璃瓶）/ **West Pharmaceutical**（橡胶塞）/ **Becton Dickinson**（耗材）。
- **Hims & Hers**（HIMS）/ **Ro** / **Noom** — telehealth 渠道 compounded GLP-1（2025-02 起退出）。

## 三、产业链 / 竞争格局认知

**主线**：NVO/LLY 双寡头格局，临床证据 + 上游产能 + 商业化网络三重护城河。LLY 凭替尔泊雕"减重幅度更高"+ retatrutide/orforglipron 储备成为 2024-2025 市场宠儿，NVO 2024 H2 因 CagriSema 失望进入"产品力质疑"阶段。

**第二梯队**：Amgen / Roche / Pfizer / Viking 等公司在研管线，但 2024 多轮数据失望（Amgen MariTide / Pfizer danuglipron / Roche CT-388）显示"快速 me-too"难度极高，靠 GLP-1 翻盘的概率下降。

**国内**：信达 mazdutide 是最接近商业化的国产 GLP-1 减重药（2025 H1 获批高概率），恒瑞 HRS9531 license-out 后估值重塑，华东医药仿制药代际落后但渠道强。其他玩家管线靠后。整体格局是"国内市场国产化提速 + 海外授权出海"两条线。

**支付端**：美国商保覆盖率上升 + Medicare 覆盖辩论是最大变量，2025-2026 RFK Jr / Trump 政府态度决定 TAM 上限。IRA 谈判 2027 落地是中期估值压力。

**产能瓶颈**：已基本缓解（NVO Catalent / LLY 自建 IN/NC/OH 工厂 + 自建 Lebanon 灌装），2025 起从"供应限制需求"转为"需求挖掘"阶段，定价权下行风险增加。

## 四、训练知识盲点（自我承认）

我训练时**不够 / 不知道**以下方面：

1. **最新季报（2026 Q1）业绩** — NVO 和 LLY 2026 Q1 GLP-1 销售数据、指引调整、市场份额最新切片。
2. **CagriSema REDEFINE 2/3 后续数据** — 2025-2026 是否有翻盘性子集分析或额外指征数据。
3. **retatrutide TRIUMPH Phase 3 数据** — TRIUMPH-1/2/3 临床试验完整数据读出时间和结果（应在 2025 末-2026 中）。
4. **orforglipron Phase 3 ACHIEVE/ATTAIN 数据** — 完整读出数据和市场反应。
5. **Trump/RFK Jr 对 GLP-1 政策的实际动作** — 2025-2026 实际监管/支付政策变化。
6. **CMS Medicare 覆盖最终规则** — Biden 2024-11 提议的命运，Trump 政府是否撤回。
7. **司美格鲁肽中国专利到期后的实际竞争格局** — 2026-03 到期后哪些生物类似药 2026-2027 实际上市，定价情况。
8. **国内 GLP-1 减肥药 NRDL 谈判** — 2025-2026 国谈是否纳入 Wegovy/Mounjaro。
9. **信达 mazdutide 商业化进度** — 2025 H1 是否如期获批、定价、初期销售爬坡。
10. **新一代候选药物 readout** — Amgen MariTide Phase 3 启动情况、Viking VK2735 Phase 3 启动、Roche CT-388 Phase 2 完整数据。
11. **食品/餐饮二阶冲击的最新研究** — 2025-2026 是否有更扎实的实际营收冲击数据（非问卷调研）。
12. **alpha 标的估值** — NVO/LLY 当前 PE/EV-EBITDA、2026 一致预期、国产小票当前估值水平。

## 五、需要 web-search 校准的优先项

按 thesis 影响排序，主 agent Step 4.5a 逐条 WebSearch + 入库：

1. `Novo Nordisk 2026 Q1 earnings Wegovy Ozempic sales revenue guidance` — 校准 fact-09/11，定 NVO 增速锚
2. `Eli Lilly 2026 Q1 earnings Zepbound Mounjaro sales tirzepatide revenue` — 校准 fact-10/12，定 LLY 增速锚
3. `Lilly retatrutide TRIUMPH Phase 3 results data readout 2025 2026` — 校准 fact-06，决定下一代竞争格局
4. `Lilly orforglipron Phase 3 ACHIEVE ATTAIN results 2025 oral GLP-1` — 校准 fact-08，口服 GLP-1 商业化时间
5. `Trump administration Medicare GLP-1 obesity coverage CMS rule 2025 2026 RFK` — 校准 fact-24/25，定支付端 TAM
6. `信达生物 mazdutide 玛仕度肽 NMPA 获批 减重 2025 商业化 定价` — 校准 fact-15，国产代表标的
7. `恒瑞医药 HRS9531 Hercules CapMan 进展 GLP-1 GIP 2025 2026` — 校准 fact-16，国产授权出海标的
8. `司美格鲁肽 中国专利 2026 到期 生物类似药 上市 竞争` — 校准 fact-28/30，国内仿制竞争
9. `Wegovy Zepbound 价格战 PBM 直销 LillyDirect NovoCare 2025 2026` — 校准 fact-23，定价权变化
10. `Amgen MariTide Phase 3 Viking VK2735 Roche CT-388 latest data 2026` — 校准 fact-06，第二梯队管线

## 六、prescan 校准结果（2026-05-26 回写）

> Step 4.5 prescan 实际入库 10 份 Wikipedia material（WebSearch 全军覆没，转 WebFetch 兜底），对照第一节 fact-NN 的更新如下：

### 被推翻（高优先级 — thesis_v0 不要再引用原 fact）

- `[fact-09]` 训练时"NVO 2024 营收 ~$42B"，被 `[mat-2bbc64]` **基本验证但更精确**：实际 2024 营收 $42.1B (+25% YoY)，净利 $14.5B；Wegovy+Ozempic 占 2023 营收 **55%**（vs 我估计 "$30B+"）。**升级置信度但数字要 cite mat-2bbc64**
- `[fact-10]` 训练时"LLY 2024 营收 ~$45B、糖尿病+减重 $16-20B"，被 `[mat-6ddfd9]` 大幅更新：**2025 全年营收 $65.18B**（不是 2024）+ 净利 $20.64B + 营业利润 $26.3B；**Mounjaro+Zepbound 2025 占 56% 营收 ≈ $36.5B**（vs 我估 $16-20B，**远超预期**）。LLY 2025-11 成首个 $1T 市值医药公司。
- `[fact-11]` 训练时"NVO 市值高点 $650B，跌至 $400B"，被 `[mat-2bbc64]` 更新：2025-07 NVO 跌至**全球药企第五**（2024-10 还是第二），仿制药压力为主因。
- `[fact-12]` 训练时"LLY 市值 $900B+，一度超过 JPM"，被 `[mat-6ddfd9]` 推翻并升级：**2025-11 LLY 首达 $1T**，是全球首个市值万亿医药公司。
- `[fact-15]` 训练时"信达 mazdutide 2025 H1 获批预期高"，被 `[mat-25971d]` `[mat-5d9b4d]` 验证：**2025-06 NMPA 实际获批**，时间符合预期；**首个**国产 GLP-1 减重药；信达 2024 营收 ¥9.42B、仍净亏 ¥94.63M；与京东健康合作分销；2025-11 入恒生指数。
- `[fact-07]` 训练时"CagriSema 2024-12 失望，68w 减重 22.7%"，被 `[mat-ce4112]` **更精确**：REDEFINE 1 实际 **20.4%**（vs 替尔泊雕 15mg 22.5%）；**REDEFINE 2 T2D 患者仅 13.7%**（T2D 减重难度高，但仍是真正弱点）；Phase 3 数据 2025-06 发表。NVO 暴跌原因更接近"未达预期"而非"完全失败"。
- `[fact-23]` 训练时"Wegovy ~$1349/月 list、Zepbound ~$1059/月"，被 `[mat-7edea3]` **重大推翻**：NVO 宣布 2027-01 起 Wegovy/Ozempic/Rybelsus 全部 list 降至 **$675/月**（near 50% 降价）；`[mat-31e7e6]` 补充 TrumpRx 提供 tirzepatide **$50/月** 给 Medicare 患者。**定价战已进入第二阶段，是 thesis 头号变量。**
- `[fact-24]` 训练时"Biden 2024-11 提议 Medicare 覆盖肥胖药"，被 `[mat-31e7e6]` 部分推翻：**Trump 政府拒绝强制 Medicare/Medicaid 覆盖 GLP-1**，但推 TrumpRx 自付价（$50/月）。Biden 规则可能被替代。
- `[fact-28]` 训练时"sema 印度/巴西专利 2026-03 到期"，被 `[mat-7edea3]` 验证并扩展：**加拿大数据保护 2026-01 已到期 + 印度 2026-03 已到期 + 巴西 2026-03 即将到期**；印度已有 **40-50** 个生物类似药上市；加拿大 Dr. Reddy / Apotex 获批。仿制竞争**已实际开闸**（早于训练认知）。
- `[fact-06]` 训练时"retatrutide Phase 2 48w 减重 24.2%"，被 `[mat-5804fb]` 更新：综述数据 **15-24% 范围**（48-72w），TRIUMPH-3（肥胖+CVD）Phase 3 进行中，未读出。
- `[fact-08]` 训练时"orforglipron Phase 3 数据 2025 读出"，被 `[mat-dc8a8e]` 推翻：**2026-04 已 FDA 获批**（品牌 Foundayo）；ACHIEVE-1 T2D 40w 减重仅 **~8%（16 lbs）**——**显著低于注射 sema 14.9% / 注射 tirzepatide 20.9%**，口服小分子效价代差已被市场看到。
- `[fact-33]` 训练时"适应症扩展进行时含阿尔茨海默症 evoke 2026 读出"，被 `[mat-2bbc64]` 推翻：**2025-11 NVO 宣布 sema 治阿尔茨海默 evoke 失败**（认知/功能无改善）。一个潜在 TAM 扩张故事**死亡**。
- `[fact-34]` 部分补充：Tirzepatide 安全性正向，`[mat-31e7e6]` 报 **SURMOUNT-1 三年随访 T2D 风险降 94%、心衰 MACE 降 38%、2024-12 OSA 适应症首批**——SURMOUNT 系列长期数据**惊艳**，强化 LLY 临床证据护城河。

### 被验证（可继续引用，置信度提升）

- `[fact-04]` Wegovy 14.9% 减重 → `[mat-524100]` `[mat-7edea3]` 一致，置信度 高 → 高+
- `[fact-05]` Zepbound 15mg 减重 22.5% → `[mat-31e7e6]` 精确给到 20.9%（72w 15mg vs 训练时 22.5% 可能是不同子集，差异不重大）→ 高
- `[fact-13]` NVO 收购 Catalent 锁产能 → 训练时记忆，未在本轮 prescan 中校准，但下游影响（仿制药 + LLY 自建产能）已通过 mat-2bbc64/mat-6ddfd9 间接证实"产能瓶颈已让位于需求/定价质疑"→ 中
- `[fact-19]` 全球 GLP-1 类 2024 ~$50B → 通过 NVO+LLY 加总反推**保守低估**，实际 2025 已 >$80B（NVO 减重+糖尿病 ~$30B + LLY ~$36.5B + Saxenda 等老品种 + 信达/华东+ 仿制 ~$5B+）→ 中-，需 user 补一手卖方研报核
- `[fact-21]` 美国 ~9% 成人用过 GLP-1 → 未直接校准，但 LLY 56% 营收占比 + NVO 持续高增意味着渗透率持续提升 → 中
- `[fact-32]` SELECT 试验 sema MACE 降 20% → 未在 prescan 中复述，但 SURMOUNT 类似 CV benefit 数据强化"GLP-1 是 cardiometabolic 药"叙事 → 高
- `[fact-35]` Ypsomed 受益注射器 → 未校准，置信度保持中

### 仍未校准（thesis_v0 引用时标 uncertain，需 user_todos 补抓）

- `[fact-16]` **恒瑞 HRS9531 Hercules CapMan 授权出海最新 status** — Wikipedia 限流抓不到，需 user 提供卖方研报或公司公告
- `[fact-17]` 华东医药 利拉鲁肽 生物类似药 销售爬坡 + 国产 GLP-1 减重药管线进度
- `[fact-18]` 其他在研（鸿运华宁/翰宇/博瑞/九源）— **完全无更新**
- `[fact-20]` 2030 全球峰值预期 $130-150B — 需 user 提供最新卖方研报核（Goldman/Morgan Stanley/UBS 等）
- `[fact-22]` TAM 测算 — 需更精细数据（雇主计划 / Medicaid 州覆盖 / 国际 OOP 患者数）
- `[fact-25]` RFK Jr **最新具体表态** — 仅有 TrumpRx 间接信号，缺直接 quote
- `[fact-26]` IRA 2027 谈判**最终名单**是否含 sema/tirzepatide — 完全无更新
- `[fact-27]` Wegovy 国内 NRDL 2025 国谈结果 — 完全无更新
- `[fact-29]` Tirzepatide 全球专利到期时间表细节 — 未校准
- `[fact-36]` 二阶受损（OSA 设备 / 减肥手术 / 食品）2025-2026 实际营收冲击 — 完全无更新
- **新需校准（baseline 漏写）**：Hims & Hers compounded GLP-1 业务在 2025-02 FDA 短缺解决后的实际营收冲击；Viking VK2735 Phase 3 数据 + 收购传闻；Amgen MariTide / Roche CT-388 / Structure Therapeutics GSBR-209 Phase 2 后续 readout

---

## 七、第二轮 prescan 校准（2026-05-26 第二批入库 13 份后追加）

> 用户要求重跑遗漏 query 并按新规约（5 并发 + 10s 间隔）跑完。结果零 silent_failure，全部 high band。
> 重大事实更新——thesis_v0 已基于这一节升级为 thesis_v1。

### 重大被推翻 / 重大新事实（升 thesis_v1 强制依据）

- `[fact-24]` 训练时"Biden 提议 Medicare 覆盖肥胖药"被 `[mat-31e7e6]` 部分推翻，再被 `[mat-kff-balance]` **彻底翻转**：Trump 政府最终与 LLY/NVO 达成 **BALANCE Model** 协议——Medicare/Medicaid 月费 $245，**患者自付仅 $50**；GLP-1 Bridge 延至 **2027 末**；CMS 2026-04 取消独立 GLP-1 试点。**关键含义**：政府从"不覆盖"变成"以政府托管价大幅压价覆盖"——既不是 Biden 路径也不是单纯 RFK 路径，是第三条路。`[mat-kff-balance][mat-stat-cms][mat-kiplinger]`
- `[fact-26]` 训练时"IRA 2027 谈判第二批 15 药"被 `[mat-fierce-ira]` 验证并精确化：**sema 已在第二批**；Ozempic 谈判价 **$274/月**（vs list $959 降 71.4%）、Wegovy 高剂量 **$385/月**；**2027-01 生效**；tirzepatide 不在第二批（但 LLY 签 MFN + 参与 BALANCE）。**双重压制**：sema 同时面临 IRA $274 + BALANCE $245。
- `[fact-30]` 训练时"sema 中国专利 2026-03 到期 → 国内仿制 2027 起开闸"被 `[mat-pharnexcloud-sema][mat-sina-jiuyuan][mat-jiemian-sema]` **实际开闸早 1 年**：CN 2026-03-20 到期，**九源 JY29-2 减重 2026-02-25 NMPA 受理**（早于到期 1 个月）；至少 10 家国内药企已申报；**价格已先于到期降 50%+**——糖尿病 ¥1120→¥478.8、减重 ¥1893→¥987。
- `[fact-17]` 训练时"华东医药利拉鲁肽国内首仿 2023-07 获批"被 `[mat-21jingji-huadong]` 扩展：华东医药 2 个月达 **30% 国内利拉鲁肽市场份额**；¥3.2 亿研发投入；**单品种铺货 3 万家终端药店目标**——是 sema 仿制大潮的"商业化预演"，国内药企真有渠道执行力。
- `[fact-20]` 训练时"2030 全球峰值 $130-150B"在中国侧被 `[mat-pharnex-glp1]` 校准：**中信证券预测 GLP-1 减重 2030 中国 ¥383 亿**；中国减肥药总市场 2025 ¥87 亿 → 2030 ¥149 亿（其中 GLP-1 占大头）。
- `[fact-16]` 训练时"恒瑞 HRS9531 license-out 美国 Hercules CM \$110M + \$6B"被 `[mat-kailera-additional][mat-biospace-hrs9531][mat-medcity-kailera]` **大幅扩展且精确**：Hercules CM **2024-10 更名 Kailera Therapeutics**；累计融资 **$600M**（$400M Series A + $200M）；恒瑞首付 **$100M + 里程碑 $10M 近期 + dev/reg \$200M + 销售里程碑 up to $5.725B + 版税**；恒瑞保留中国权益。**HRS9531 中国 Phase 3 阳性数据 17.7% 减重**（2025-07 topline、2025-11 ObesityWeek 更新）；恒瑞同时授权 oral HRS7535 给 Kailera。**这是中国创新药"研产授权出海"标杆**。
- `[fact-25]` 训练时"RFK Jr 公开质疑 GLP-1"被 `[mat-kff-balance][mat-pharmavoice-maha]` 验证但**有妥协**：RFK 公开称 GLP-1 "extraordinary drugs"，关键阻力是"成本"——最终通过 BALANCE 协议把价格压到 $245/月 落地覆盖。**MAHA 路线 + BALANCE 妥协的二元结构**。

### 全新事实（baseline 漏写或大幅更新）

- `[fact-37]` **NEW**：**Roche CT-388 Phase 2 (2026-01-27 公布)：24mg 48w 减重 22.5%**（efficacy estimand，treatment-regimen 18.3%）；6% 因不良反应停药；Phase 3 ENITH-1/2 启动 **2026 Q1**。**Roche $2.7B 收购 Carmot 押对了**——第二梯队**实质进入**，替尔泊肽不再独霸 GLP-1/GIP 双靶点格局。`[mat-roche-ct388][mat-biospace-ct388]`
- `[fact-38]` **NEW**：**Viking VK2735 注射 Phase 3 VANQUISH-1/2 已完成入组**；oral VK2735 Phase 2 **13w 减 12.2%**（与 LLY orforglipron 40w 8% 对比有效率代差占优）；oral Phase 3 计划 **2026 Q3** 启动；Q1 2026 现金 **$603M** 撑到 2028。**Wall Street 目标价 ~$95 vs 当前 $30**——big pharma 买它最便宜，可能成 Roche/Amgen/Pfizer 下一笔收购。`[mat-prnewswire-viking][mat-fool-viking]`
- `[fact-39]` **NEW**：**Amgen MariTide Phase 3 readouts 2027（不是 2026）**；Phase 2 高停药率 + 呕吐率致剂量方案重新调整；Phase 2 52w 减重 ~20%（无糖尿病）/~17%（糖尿病），未平台。**Amgen 在下一代竞争中时间表落后**。`[mat-amgen-maritide][mat-fierce-amgen]`
- `[fact-40]` **NEW**：**LillyDirect Zepbound $299-449/月 / NovoCare Wegovy $149-349/月**（注射+口服）；DTC 平台绕过 PBM；与 BALANCE $245 + IRA $274 形成"两轨定价"——商保走 list price ~$1000+，自费走 DTC $149-449，Medicare/Medicaid 走政府定价 $245。**单位营收已被多渠道压制，三轨复杂度上升**。`[mat-cnbc-lilly-dtc][mat-peptide-pricing]`
- `[fact-41]` **NEW**：**HIMS 2025 营收 $2.35B (+57% YoY)、净利仅 $128M**（几乎平），2026 指引 $2.7-2.9B；compounded GLP-1 业务转型——**2026-03-09 与 NVO 和解 + 合作**改卖品牌 Ozempic/Wegovy；FDA 警告函 + DOJ 加强监管使整个 503A/B compounded GLP-1 行业洗牌完成。`[mat-hims-ir][mat-pharmacytimes-hims]`
- `[fact-42]` **NEW**：**司美格鲁肽中国生物类似药 2027 集采概率高**：至少 10 家国内药企申报；价格已先降 50%；带量采购窗口 2027 后大概率开闸 → **NVO 中国市场 sema 长尾营收 2027 后归零**。`[mat-jiemian-sema][mat-pharnexcloud-sema]`

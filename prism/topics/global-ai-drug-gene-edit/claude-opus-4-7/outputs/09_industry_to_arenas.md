---
slug: global-ai-drug-gene-edit
output_key: 09_industry_to_arenas
version: 1
generated: 2026-05-22
data_freshness: 2026-Q1
data_freshness_basis: mat-1fe402 (VRTX 10-Q 2026-05-05), mat-3a51f9 (NTLA 10-Q 2026-05-11), mat-2b431a (BEAM 10-Q 2026-05-07), mat-a66935 (CRSP 10-Q 2026-05-04)
---

# AI 辅助药物研发与基因编辑 → 细分 Arena 选拔

> 生成于 2026-05-22；基于 6 份 outputs (01-04, 06-07) + 8 份 findings 综合判断；训练知识约 45%
> Topic question 的两条主线（AI 制药 / 基因编辑 + 交叉点）拆为 8 个 arena 候选，分 3 档处置

---

## Arena 候选清单（8 个）

| Arena 名 | 利润池规模 | 增速预期 | 竞争结构 | 估值水位 | 周期位置 | 综合评分 | 决定 |
|---------|-----------|---------|---------|---------|---------|---------|------|
| 1. In vivo CRISPR/base editing 罕见病（HAE/AATD/HSD） | 4 | 5 | 4 | 4 | 5 | 4.4 | 深挖 |
| 2. In vivo 心血管编辑（PCSK9/ANGPTL3/Lp(a)） | 5 | 5 | 3 | 4 | 4 | 4.2 | 深挖 |
| 3. Base editing 平台型公司（BEAM 为代表） | 3 | 4 | 4 | 5 | 5 | 4.2 | 深挖 |
| 4. Ex vivo CRISPR 商业化（Casgevy / SCD-TDT） | 3 | 2 | 5 | 4 | 2 | 3.2 | 观察 |
| 5. AI 制药 SaaS / "卖铲子"平台（SDGR/RXRX/RLAY/ABCL） | 3 | 3 | 2 | 4 | 3 | 3.0 | 观察 |
| 6. 中国 in vivo 基因编辑（YolTech / 博雅辑因 / Argo Bio） | 3 | 5 | 3 | 4 | 5 | 4.0 | 观察 |
| 7. 通用 AI 设计药物纯标的（Insilico / Exscientia / BenevolentAI） | 2 | 2 | 1 | 3 | 2 | 2.0 | 淘汰 |
| 8. Prime editing 平台（PRME 等） | 2 | 3 | 4 | 3 | 2 | 2.8 | 淘汰 |

---

## 评分维度说明

- **利润池规模**：当前 + 5 年期 arena 总利润池估算（1: <10 亿美元 / 5: >1000 亿美元）。基因编辑罕见病按"美国可寻址患者 × 假定首年渗透 × $200-300 万/例 - 制造成本"估算；心血管按"全球 dyslipidemia 千万级患者 × 0.5-1% 渗透 × 长期重复给药"计算
- **增速预期**：3 年 CAGR（1: <5% / 5: >30%）。in vivo 路线均处早期，CAGR 高；ex vivo 已被 Casgevy 商业化失利定价
- **竞争结构**：1: 完全竞争 / 5: 自然垄断。基因编辑头部 3-4 家寡占，AI 制药高度分散
- **估值水位**：1: 历史高位 / 5: 历史低位。CRSP/NTLA/BEAM 从 2021 高点跌幅 60-90%（来自 02 周期定位），普遍处于历史低位
- **周期位置**：1: 衰退/饱和 / 5: 早期成长。in vivo BLA 前夜 = 早期成长；Casgevy ex vivo 已坐实天花板
- **综合评分**：加权均值（profit_pool×0.20 + growth×0.25 + competition×0.15 + valuation×0.15 + cycle×0.25）

---

## 入选深挖（深挖档）

### 1. In vivo CRISPR / base editing 罕见病（HAE / AATD / HSD）

- **建议 slug**: `global-in-vivo-gene-edit-rare-disease`
- **入选理由**：K1 锚定赛道。HAELO Phase 3 减发作 87%/p<0.0001/0 SAE（来自 mat-3a51f9）+ BEAM-302 60mg AAT 16.1 µM 超治疗阈值 11 µM（来自 mat-2b431a）= 2026-2027 首份 in vivo CRISPR 商业产品几乎确定。NTLA 已 rolling BLA、BEAM-302 加速审批共识达成（来自 mat-3a51f9 + mat-2b431a）。这是整个赛道"从导入期到成长期"的范式切换核心证据
- **预期关键洞见**：
  - HAE 首年实际渗透率（5-15% vs 卖方 30-50%）将决定整个 in vivo 估值锚（来自 04 隐含预期）
  - LNP 重复给药肝毒性是平台共性瓶颈：BEAM-302 双剂 2x60mg 已出 Grade 4 ALT（来自 mat-2b431a）
  - AAT 类生物标志物驱动加速审批可能比 HAE 临床终点路径更快兑现
  - lonvo-z 上市后将面临 KalVista 口服 plasma kallikrein 抑制剂二代竞争（盲点 B / 来自 06 风险）
- **预填 L4 狩猎问题**：
  1. 2027 H1 lonvo-z 上市后首 6-12 月真实渗透率能否突破 10%？若 <5% 则空方观点（HAE 患者已被 BioCryst/Takeda/CSL 锁定）成立
  2. BEAM-302 pivotal 50 例中是否出现第二例 Grade 4+ ALT？若有则触发 Kill Criteria #1，整个 in vivo 路线杀估值 30-50%
  3. NTLA HAE BLA 是否获 Priority Review 6 个月加速？标准 12 个月路径会让 BEAM-302 反超
- **触发创建的动作**：用户决定开 arena topic 后由主 agent 创建 `prism/topics/global-in-vivo-gene-edit-rare-disease/` 并 dispatch workflow 02
- **upgrade_triggers**：N/A（已是深挖档）
- **monitor_metrics**：N/A

### 2. In vivo 心血管编辑（PCSK9 / ANGPTL3 / Lp(a)）

- **建议 slug**: `global-in-vivo-gene-edit-cardiovascular`
- **入选理由**：最大利润池赛道（来自 01 商业全景：dyslipidemia 千万级潜在患者）。LLY 已收 Verve $1.3B（K4 部分验证，来自 03 叙事 + 02 周期）。CRSP CTX310 ANGPTL3 -73% Phase 1b 数据（来自 mat-ae69f9）证明 in vivo 心血管路径可行。AT 心血管 + 慢病 = 一次性疗法颠覆传统订阅式 statin/Repatha 模式的最大机会
- **预期关键洞见**：
  - LLY-Verve 整合后 PCSK9 项目 NDA 候选时间（2027 估计）= 该 arena 第一个商业拐点
  - 与 Repatha/Leqvio（订阅式 PCSK9 抑制剂）的支付方比较：一次性 $50-100 万 vs 终生 $6,000/年——经济学拐点在第 8-10 年
  - CRSP CTX310 长期看点（来自 07 决策辅助）使 CRSP 不被完全减配
  - 心血管比罕见病更易吸引 IRA 政策关注（盲点 C，来自 06 风险）
- **预填 L4 狩猎问题**：
  1. LLY-Verve PCSK9 项目 Phase 2 关键数据（2027 H1）能否复现 inclisiran 级别 LDL 降幅 + 无肝毒性？
  2. 一次性 in vivo 心血管编辑相对订阅式 PCSK9 inh（Repatha/Leqvio）的 break-even 在哪一年？支付方真实接受度如何？
  3. CRSP CTX310 / VERVE-201 是否会在 2027-2028 进入 BP 收购视野？大药企（PFE/Roche/NVS）现金 + 心血管 BD 战略如何
- **触发创建的动作**：建议主 agent 创建 arena topic + 在 LLY/CRSP 公司页打通跳转
- **upgrade_triggers**：N/A
- **monitor_metrics**：N/A

### 3. Base editing 平台（BEAM 为代表）

- **建议 slug**: `global-base-editing-platform`
- **入选理由**：边缘叙事 #1（来自 03 叙事生态）值得验证——base editing 不切断双链 = 长期取代 CRISPR-Cas9 多数适应症的范式候选。BEAM 同时具备 risto-cel SCD BLA 2026 末 + BEAM-302 AATD 加速审批 + Pfizer/Lilly/Apellis 三家 BP 合作（来自 mat-797ff7）= 平台广度第一。$1.2B 现金 + $500M Sixth Street 信贷延长跑道至 2028+（来自 mat-2b431a）。BP 收购候选（边缘叙事 #3，来自 03）= K4 重磅催化剂
- **预期关键洞见**：
  - BEAM 估值 vs NTLA：base editing 平台是否值得 NTLA 估值溢价？sum-of-parts 估值能否真正反映平台期权（来自 04 隐含预期）
  - 与大药企（LLY/PFE/BMS/Roche）合作 royalty 5-15% 实际兑现节奏
  - risto-cel BLA 仅 31 例数据（来自 mat-797ff7）的 RTF 风险被市场低估（来自 06 风险 #5）
  - BEAM 被整体收购的概率 + 估值锚（$15-25B 边缘叙事 #3）
- **预填 L4 狩猎问题**：
  1. risto-cel BLA 2026 年底递交后 FDA 是否 RTF？31 例数据 + RMAT 标签是否足够？
  2. BEAM-302 H2 pivotal cohort 启动后 12 个月数据（2027 H2）是否复现 60mg 单剂效果？双剂安全性能否过关？
  3. BEAM 被 BP 整体收购溢价区间？最可能买方（PFE/LLY/Roche）现金 + 战略匹配度
- **触发创建的动作**：建议同时开 BEAM 公司级 prism topic（来自 07 决策辅助"启动 BEAM 单独公司级 prism topic"建议）
- **upgrade_triggers**：N/A
- **monitor_metrics**：N/A

---

## 进入 watchlist（观察档）

### 4. Ex vivo CRISPR 商业化（Casgevy / SCD-TDT）

- **暂不深挖理由**：K2 已被强反驳（VRTX 全年 64 例输注 + 2025 全年 $115.8M，远低 K2 千例目标，来自 mat-49861e）。01 商业全景 + 04 隐含预期已确认市场对 ex vivo 路线天花板的定价基本到位。当前研究价值低于深挖档三个 arena。但需保持监控因为是反例锚——若 H2 2026 突然 step-up 则证伪叙事 B
- **升档触发条件**：
  - Casgevy H2 2026 输注数年化突破 300 例（漏斗结构性改善）
  - VRTX 重新披露季度漏斗（300/147/64 模式恢复透明度）
  - 德国/日本支付方协议落地 + ATC 数量翻倍
- **监控指标**：
  1. VRTX 季度 "Other product revenues" Casgevy 分项（阈值：单季 >$60M = 升档触发）
  2. ATC 网络数（来自 01 商业全景，是 ex vivo 商业化关键瓶颈）

### 5. AI 制药 SaaS / "卖铲子"平台（SDGR / RXRX / RLAY / ABCL）

- **暂不深挖理由**：K3 (AI 制药 Phase 3 突破) pending 验证；当前 8 份 findings 不覆盖 SDGR/RXRX/RLAY 任何一家。盲点 F（卖铲子模式被大药企内化，来自 06 风险）+ 叙事 C（AI 制药泡沫破灭，来自 03）暗示该 arena 短期下行风险大。等 16 份 findings 抽完 + Insilico INS018_055 Phase 2 数据出炉后再决定是否升档（来自 07 决策辅助"下一步"建议）
- **升档触发条件**：
  - Insilico INS018_055 或 Isomorphic 类 AI 设计药物进入 Phase 3
  - SDGR/RXRX 季度软件收入 YoY 增速反弹至 >15%
  - 任一大药企（LLY/Roche/Novartis）公开收购 AI 制药平台公司 >$5B
- **监控指标**：
  1. SDGR/RXRX 季度软件订阅收入 YoY（阈值：来自 06 风险 #F，<10% = 警报 / >15% = 升档）
  2. AI 设计候选化合物 Phase 3 入组数（全行业）

### 6. 中国 in vivo 基因编辑（YolTech / 博雅辑因 / Argo Bio）

- **暂不深挖理由**：K5 (NMPA 基因编辑批准) pending；当前 findings 仅 mat-8d4e6d 间接覆盖（NTLA 10-K 提及 YolTech 是 ATTR 竞争对手）。边缘叙事 #2 + 盲点 D 都强调中国弯道超车可能性，但美股投资者对中国监管/退出风险定价过严（来自 03 叙事）+ 港股流动性差 = 当前缺乏清洁可投资标的。等 NMPA 首批 IND/BLA 后 + 港股 18A 通道再判断
- **升档触发条件**：
  - 任一中国 in vivo 编辑公司在 NMPA / FDA 同步申报（来自 06 盲点 D 触发条件）
  - 中国本土支付方对基因编辑给予 ≥50 万人民币定价（盲点 D）
  - YolTech / 博雅辑因 / Argo Bio 任一公司港股 IPO 或被海外 BP 大额合作
- **监控指标**：
  1. CDE 受理中国 in vivo 基因编辑 IND 数量
  2. 港股 18A 基因编辑公司融资节奏 + 估值锚

---

## 淘汰记录（淘汰档）

### 7. 通用 AI 设计药物纯标的（Insilico / Exscientia / BenevolentAI）

- **淘汰理由**：2024-2025 多个 AI 设计管线临床失败 + AI 制药范式革命论已被证伪（来自 03 叙事 C）。Exscientia/BenevolentAI 已被并购或退市。纯"AI 设计药物"标的从赛道结构看缺乏护城河（大药企内化 + AlphaFold 3 开源压低天花板）
- **复活条件**：(1) Insilico INS018_055 IPF Phase 2 结果显著阳性 + Phase 3 入组；或 (2) 至少 1 个 AI 设计候选药物（任何公司）获 FDA 批准

### 8. Prime editing 平台（PRME / Prime Medicine 等）

- **淘汰理由**：技术潜力强（不切断双链 + 不依赖 base editing 限定碱基类型），但当前临床进度落后 BEAM 18-24 月，无 Phase 2/3 数据可锚定。BEAM 已通过 base editing 占据"下一代编辑"叙事位置（来自 03 边缘叙事 #1）。投资性价比当前不如直接配置 BEAM
- **复活条件**：PRME 任一候选药物（如 PM359 慢性肉芽肿病）公布 Phase 1 阳性数据 + 启动 Phase 2

---

## 信息来源

- 训练知识占比约 45%（arena 分类框架 + 行业类比）
- 引用前置产出：
  - 01_business_panorama（行业边界 + 价值链 + 商业模式分层）
  - 02_cycle_positioning（技术 S 曲线 + 资本周期定位）
  - 03_narrative_ecology（主流叙事 A/B/C + 边缘叙事 #1/#2/#3）
  - 04_implied_expectations（5 级观点光谱 + 关键分歧点）
  - 06_risk_blindspots（盲点 A-F + Kill Criteria）
  - 07_decision_kit（标的级配置建议 + 下一步研究方向）
- 引用 findings：
  - mat-ae69f9（CRSP 10-K：CTX310 心血管证据 + ToolGen 诉讼）
  - mat-a66935（CRSP 10-Q：$600M 可转债 + Q1 collab 拐点）
  - mat-8d4e6d（NTLA 10-K：HAE 患者池 + YolTech 中国竞品提及）
  - mat-3a51f9（NTLA 10-Q：HAELO 87% + $195M 增发，K1 锚定证据）
  - mat-797ff7（BEAM 10-K：risto-cel BLA + Pfizer/Lilly/Apellis 三家 BP + Sixth Street 信贷）
  - mat-2b431a（BEAM 10-Q：BEAM-302 60mg pivotal + 双剂 Grade 4 ALT 盲点 A 证据）
  - mat-49861e（VRTX 10-K：Casgevy 64 例 = K2 反驳铁证）
  - mat-1fe402（VRTX 10-Q：Casgevy Q1 $42.9M + 透明度倒退）

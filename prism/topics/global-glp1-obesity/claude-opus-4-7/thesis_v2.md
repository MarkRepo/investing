---
slug: global-glp1-obesity
variant: claude-opus-4-7
version: 2
written_at: 2026-05-26
parent_version: 1
revised_after_prescan: true
prescan_status: full
data_freshness: 2026 Q1（LLY/NVO/HIMS 季报）+ 2025 全年（信达/恒瑞/华东 + SEC 10-K + NVO 20-F）+ 33 web-search 涵盖 BALANCE/IRA/sema 仿制/二梯队
writing_convention: 方案 C 全快照 + 顶部 changelog
---

# Thesis v2 — GLP-1 减肥药全球赛道

## § 0. v1 → v2 changelog

**重大修订（基于 03-extract 的 59 个 finding 实证）**：

| 维度 | v1 | v2 修正 | 来源 |
|------|----|---------|------|
| 整体强度 | 7/10 | **7.5/10**（小幅升） | 综合 |
| **信达定位** | "主题性配置不重仓" | **"主题 + 业绩双驱动重仓候选"** — 2025 营收 +38%/首次盈利/Non-IFRS +420%/EBITDA +384%/自研口服 GLP-1 双管线 | mat-11a269 |
| **NVO 临床劣势** | "CagriSema 20.4% < tirz 22.5%" | **"Wegovy 7.2mg STEP UP 20.7% 已实质追平 tirz"** | mat-606af8 |
| **BALANCE 框架** | "无限期延迟"模糊 | **"系统 pilot 延迟 vs LLY 单边 Bridge 2026-07-01 - 2027-12-31"双轨 | mat-3a4b6e + mat-20e63b + mat-a29026 |
| **LLY 业务集中度** | "tirz 占 56%" | **"56% → 65% 一年内加速集中"** | mat-20e63b |
| **LLY 量价剪刀差** | 假设可承受 | **"2025 +45% 营收 + gross margin +1.7pp 已实证"** | mat-3a4b6e |
| **恒瑞** | "中国创新药龙头" | **"创新药占比首次 >50% + 5 笔 BD 出海 ¥33.92 亿常态"** | mat-3c1ced |
| **NVO 多元化** | 未提及 | **Akero $4.7B 收购**（MASH efruxifermin Phase 3） | mat-653869 |
| **Oral GLP-1** | LLY orforglipron 独占 | **四家同台**（LLY orforglipron + VKTX + GPCR + 信达 IBI3042/IBI3032） | mat-11a269 + mat-1f9505 + mat-0ed0b9 + mat-dc8a8e |
| **MFN 协议** | 未提及 | **LLY+NVO 都签 → 国际定价对齐长期传导** | mat-20e63b + mat-653869 |
| 二梯队 | 仅 Viking | **Viking + Structure 双候选 + Roche $2.7B Carmot 已先例** | mat-1f9505 + mat-0ed0b9 + mat-dfd8f0 |
| HIMS Q1 | 未提及 | **2026 Q1 美国营收 -8% 战略转型阵痛** | mat-69b291 |
| NVO 340B | 未提及 | **2026 Q1 一次性 $4.2B 收入确认** — 非经常性 boost | mat-5b9ef4 |

**保留判断**：LLY > NVO > 信达 排序变为 **Innovent ≈ LLY > NVO** 的 pair-trade 路径（v1 中 NVO 在第二位置不变但权重上升，信达从主题性升到 Tier 1 重仓）

---

## § 1. 核心 thesis（强度 7.5/10）

**长 LLY + 长 NVO + 长 Innovent 三轨配置 + 期权式 VKTX + 边际持 恒瑞**——GLP-1 减肥药 2026-2030 仍是医药板块最大 structural alpha 来源；2026 Q1 已实证"量增 +50% 抵消价跌 -10-15% 量价剪刀差正向"是可持续的（LLY 2025 +45% 营收 + gross margin +1.7pp）。但单标的依赖型 thesis 在 2026 Q2 已不再适用——LLY 业务集中度 65% + 第二梯队 Phase 3 顶线 2026-2027 集中读出 + 中国国产 GLP-1 业绩拐点（信达 +38% 营收 + 首次盈利） → **重塑为四标的核心组合**：

**估值带（核心 5 标的目标）**：
- LLY：当前 ~$1000 / PE 50x → 公允区 PE 42-55x（量增延续 + reta 期权）
- NVO：当前 ~$76 / PE 22x → 公允区 PE 22-28x（反弹 + 多元化）
- Innovent (HK)：当前 ~HK$70 / forward PE 50x → 公允区 PE 45-65x（业绩 + BD 双轨）
- 恒瑞 (A)：当前 ~¥55 / PE 30x → 公允区 PE 28-35x（创新药结构性重估）
- VKTX：当前 ~$30 → 二元 binary（Phase 3 + 收购，$25-30 加 / $80+ 减）

**时间维度**：
- 2026 H2 - 2027 H1：retatrutide TRIUMPH-3 + VK2735 VANQUISH + CT-388 ENITH 三家 Phase 3 + amycretin Phase 2 顶线集中读出窗口 → thesis 重大调整
- 2027-12：BALANCE Bridge 终止，Medicare 长期机制重新谈判
- 2028 起：Trulicity IRA 生效 + 第二梯队潜在商业化 → 长期单价压制阶段

---

## § 2. 支持理由（当前完整清单）

### S1. 替尔泊肽临床数据 + 适应症爆发持续（K1+K5）

LLY tirzepatide SURMOUNT 72w 减重 20.9% (15mg)；SURMOUNT-1 三年随访 T2D 风险降 94%；心衰 MACE 降 38%（mat-31e7e6）；2024-12 OSA 首批；多个 Phase 3 衍生适应症（MASH/sleep apnea/HFpEF/T1D/orthopedic）持续推进（mat-3a4b6e）。LLY 2025 Mounjaro+Zepbound 占总营收 56% ≈ $36.5B，2026 Q1 上升至 65%。**[来源 mat-3a4b6e + mat-20e63b + mat-31e7e6]**

### S2. 专利护城河差距 5 年 + sema 仿制实际已开闸（K3）

sema 加拿大 2026-01 / 印度 2026-03 / 巴西 2026-03 / 中国 2026-03-20 已到期；印度 40-50 个仿制药已上市；中国 10 家国内药企申报；九源 JY29-2 减重 2026-02-25 NMPA 受理；中国 sema 价格已先降 50%（**¥1893→¥987 减重剂型**）。**替尔泊肽美国 2036 / CN+IN 2034**——再多 10 年护城河，是 LLY 相对 NVO 5 年优势。**[来源 mat-7edea3 + mat-60e1ab + mat-cc70d1 + mat-a070ec]**

### S3. 量价剪刀差正向 — 2025 已实证（K5 核心）

LLY 2025 营收 **$65.18B (+45%)** + 净利 $20.64B (+95%) + EPS $22.95 (+96%)；**gross margin +1.7pp**（即使净价下行 10-15%）；Mounjaro 海外 2025 +258% 量驱（$2.6B → $9.3B）；2026 Q1 海外又翻 4 倍（$1.2B → $4.4B）；Zepbound 美国 2026 Q1 +79%。LLY 自承 2026 Q1 业务集中度上升至 65%（一年内 +9pp）。这是 K5 阈值"unit volume +50% + unit net price -20% → 估值可承受"的最强实证。**[来源 mat-3a4b6e + mat-20e63b]**

### S4. 管线代际接力但有竞争者（K1）

LLY 储备 retatrutide（GLP-1/GIP/GCG 三靶 Phase 3）+ orforglipron 2026-04 已批 Foundayo + eloralintide（amylin）。NVO 储备 amycretin + oral CagriSema + Wegovy 7.2mg HD（STEP UP 20.7%）+ CagriSema 肥胖。**第二梯队实质入场**：Roche CT-388 22.5% Phase 3 启动 2026 Q1 + Viking VK2735 注射 Phase 3 已完成入组（VANQUISH-1 2025-11） + oral 13w 12.2% + Structure aleniglipron Phase 3 启 2026 H2 + 信达 IBI3042/IBI3032 自研口服 GLP-1。**LLY 一家独大叙事被压缩，但综合储备仍最厚**。**[来源 mat-5804fb + mat-dc8a8e + mat-606af8 + mat-6c585f + mat-1f9505 + mat-0ed0b9 + mat-11a269]**

### S5. 中国 GLP-1 国产化 + BD 出海格局成形（K4 大幅升级）

**信达 2025 业绩拐点**：营收 RMB 13.04B (+38%)、首次盈利 IFRS 净利 RMB 813.6M、Non-IFRS 净利 RMB 1.72B (+419.6%)、EBITDA RMB 1.99B (+383.7%)。三个 BD 大单：武田 $1.2B upfront + Roche $80M + 另一 $350M。自研口服 GLP-1 IBI3042/IBI3032 Phase 1。**恒瑞 2025**：营收 ¥316.29 亿 (+13%)，归母净利 ¥77.11 亿 (+22%)；**创新药占比首次过半 ¥163.42 亿 (+26%)**；BD 5 笔 ¥33.92 亿（MSD $2 亿/IDEAYA $7500 万/Merck KGaA €1500 万/Braveheart $6500 万/+1 笔）。**HRS9531/HRS7535 Kailera 出海**：恒瑞首付 $100M + 总里程碑 up to $5.925B + 销售版税。华东利鲁平 30% 国内市场份额。**[来源 mat-11a269 + mat-3c1ced + mat-214fbe + mat-cb3706]**

### S6. NVO 多元化 + Wegovy 高剂量追平 — 反弹 catalyst 已具备（K1+反方 2 增强）

Wegovy 7.2mg STEP UP 20.7% 已 EU CHMP 推荐 + 美国 Wegovy HD 已上市（mat-606af8）。Akero $4.7B 收购完成 2025-12-09（efruxifermin MASH Phase 3 + CVR $0.5B）— NVO 多元化进 MASH 蓝海。HIMS 2026-03 和解合作 + NovoCare DTC $149-349 + 340B 一次性 $4.2B 2026 Q1 收入确认（mat-5b9ef4）。**[来源 mat-606af8 + mat-653869 + mat-5b9ef4 + mat-c11032]**

### S7. DTC + 渠道结构变化（K3+K5）

LLY LillyDirect Zepbound $299-449 + NovoCare Wegovy $149-349（mat-e84be3）。HIMS 50M+ 累计 telehealth + 自营 pharmacy + Eucalyptus $1.15B 国际化收购（mat-d45d79 + mat-f38030）。DTC 平台是 GLP-1 vs PCSK9 时代的关键差异化（cash-pay 部分绕过 PBM/商保）。**[来源 mat-7a6003 + mat-e84be3 + mat-f38030]**

---

## § 3. 反方观点（当前完整清单）

### O1. LLY PE 50x 戴维斯双杀风险（K5+K2，反方 1 增强）

PE ~50x；Roche CT-388 22.5% 已同档 + VK2735 oral 12.2% + Amgen MariTide Phase 3 2027；同时 BALANCE Bridge $245+50 + IRA sema $274 + LillyDirect $299-449 DTC 三轨压制。Trulicity 2028 IRA 是 LLY 第一波直接打击。**[来源 mat-3a4b6e + mat-20e63b + mat-92bc1e + mat-6c585f]**

### O2. NVO 反弹胜率显著高于看上去（反方 2 增强）

NVO 已 price in CagriSema 失望 + sema 仿制 + evoke 失败 + 2024-10 → 2025-07 跌 50%+；amycretin Phase 2 数据 + 2025-12 oral Wegovy + Wegovy 7.2mg HD（mat-606af8）+ NovoCare DTC + HIMS 合作 + Akero MASH 多元化 = 5 个反弹 catalyst。**短期 0.5-1 年 NVO 估值修复胜率不低于 LLY 续涨**。**[来源 mat-2bbc64 + mat-606af8 + mat-653869]**

### O3. GLP-1 终身服药支付方收紧风险（K2 长期）

停药 1 年内反弹 50-70%（mat-524100）→ 终身服药 → 政府"年复年成本意识" + IRA 长期会扩展（LLY 自承 mat-3a4b6e）。BALANCE Bridge 2027-12 后机制不确定；MFN 协议（LLY+NVO 都签）对国际定价对齐传导是新长期阻力。**[来源 mat-524100 + mat-a29026 + mat-20e63b]**

### O4. 第二梯队收购改变 LLY 估值锚（K6 + 反方 4 增强）

Viking $30 → 目标 $95；Structure 同列收购候选；Roche $2.7B 收购 Carmot 已是先例；Big pharma（Pfizer/Merck/AbbVie）仍未拥有 GLP-1 暴露 → 2026-2027 收购窗。VKTX 自有产能 100M 注射器 + 1B+ oral tablets（自营商业化能力 + 谈判杠杆强，mat-20420a）。**[来源 mat-1f9505 + mat-ef091e + mat-20420a + mat-dfd8f0]**

### O5. Oral GLP-1 四家同台 → 注射价值主张减弱（O5，新加）

LLY orforglipron 2026-04 已批 8% + VK2735 oral 13w 12.2% + GPCR aleniglipron Phase 3 启 2026 H2 + 信达 IBI3042/IBI3032 → oral GLP-1 不再 LLY 独占 → 注射 GLP-1 类 2028+ 价值主张减弱。**[来源 mat-dc8a8e + mat-1f9505 + mat-0ed0b9 + mat-11a269]**

### O6. LLY 业务集中度上升 + 单产品依赖加重（O6，新加）

2025 56% → 2026 Q1 65% 一年内 +9pp。NVO 1990s → 2010s 胰岛素霸权被 LLY/Sanofi 长效胰岛素侵蚀的"单产品依赖型增长长期一定衰减"教训正在 LLY 重演。**[来源 mat-20e63b + mat-2bbc64 历史镜像]**

### O7. 中国 BD 现金流可持续性（O7，新加）

信达 2025 BD $1.5B+ 含三个大单 + 恒瑞 5 笔 ¥33.92 亿 — **市场可能视为一次性而非常态化**。如果 2026 BD 大幅回落（比如仅 1-2 笔）→ 信达/恒瑞 2026 营收增速失望。**[来源 mat-11a269 + mat-3c1ced]**

---

## § 4. Killer Question 现状表

| K# | 主题 | 当前状态 | 触发条件 | 关键 mat_id |
|----|------|---------|---------|-------------|
| K1 | 下一代代际竞争 | **仍未确定**（2026 H2-2027 H1 集中读出） | reta TRIUMPH-3 顶线 ≥25% / ≤22.5% / CT-388 ≥23% | mat-5804fb / mat-6c585f / mat-1f9505 / mat-0ed0b9 |
| K2 | BALANCE + IRA + Medicare 长期 | **已部分验证（LLY Bridge 2026-07 起）/ 长期未定（2027-12 后）** | BALANCE 实际 enrollment 数据 / 2027-12 后机制 | mat-3a4b6e / mat-20e63b / mat-a29026 / mat-92bc1e |
| K3 | sema 全球净价衰减 | **已部分验证（NVO 2025 自承下行）/ 待 2027 IRA 验证** | NVO sema 2027 营收 vs 2025 同比 | mat-5b9ef4 / mat-92bc1e / mat-60e1ab |
| K4 | 国产 GLP-1 出海 + 国内市占 | **大幅超预期**（信达拐点 + 恒瑞 BD 常态） | 2026 mazdutide 销售 ≥¥15 亿 / HRS9531 美国 Phase 3 启动 | mat-11a269 / mat-3c1ced / mat-214fbe |
| K5 | LLY 单位 net price + 量价剪刀差 | **2025 已实证可承受 / 长期 2028+ 待验证** | LLY 2027 营收增速 / unit net price 拆分 | mat-3a4b6e / mat-20e63b |
| K6 | 二梯队收购溢价 | **窗口逐步打开**（2026 H2 - 2027 H2 集中） | Viking 收购溢价 ≥3x / 无收购则维持 | mat-1f9505 / mat-ef091e / mat-20420a / mat-dfd8f0 |

---

## § 5. 应对策略矩阵

| 价格区间 | LLY 动作 | NVO 动作 | Innovent 动作 | VKTX 动作 |
|---------|---------|---------|--------------|----------|
| 大幅下跌（-20% 以上） | 加 5-10% | 加 5-10% | 加 3-5% | 期权式持有不动 |
| 当前价 | 持仓 25-30% | 持仓 15-20% | 持仓 20-25% | 期权式 3-5% |
| 大幅上涨（+20% 以上） | 减 5-10% | 减 3-5% | 减 5-10% | 减仓接近目标价 |
| 重大 catalyst（reta ≥25%） | 加 10% | - | - | 加 5% |
| 重大 catalyst（reta ≤22.5%） | 减 10-15% | 加 5% | 加 5% | 加 5%（V 收购概率上调） |
| 重大 catalyst（VKTX 被收购溢价 ≥3x） | 减 10% | - | - | 退出 |

---

## § 6. catalyst 时点表

参 08_living_feed.md 6 大事件流。压缩版：

- **2026-07-01**：LLY BALANCE Bridge 生效 — 量驱 catalyst
- **2026 H2**：retatrutide TRIUMPH-3 顶线 / VK2735 VANQUISH-1 顶线 / amycretin Phase 2 顶线
- **2027-01**：IRA sema $274 在 Medicare 生效 — NVO 净价跳水
- **2027 H1**：CT-388 ENITH-1 中期 / mazdutide 2026 全年销售披露
- **2027-12**：BALANCE Bridge 终止 — Medicare 长期机制谈判窗口
- **2028 起**：Trulicity IRA 生效 + 第二梯队潜在商业化

---

## § 7. 数据缺口（P0-P2）

### P0 — 必须补的（影响核心 thesis）

1. NVO 2026 Q1 完整季报（剔除 340B 一次性 $4.2B 后基本盘增速）
2. LLY 2027 H1 真实 unit net price 拆分（list / DTC / PBM rebate / BALANCE 渠道差）
3. 信达 mazdutide 2025 全年实际销售拆分 + 2026 H1 半年报
4. CMS BALANCE Bridge 2026 H2 实际 enrollment 月度数据
5. retatrutide TRIUMPH-3 / VK2735 VANQUISH 顶线读出

### P1 — 需要补的（影响 sub-thesis）

1. amycretin Phase 2 顶线
2. 信达自研口服 GLP-1 IBI3042/IBI3032 Phase 1 完整数据
3. 恒瑞 2026 H1 BD 现金流（验证 2025 5 笔是否常态）
4. HIMS 2026 Q2 GLP-1 业务恢复速度
5. 中国 sema 集采时点（2027 概率）

### P2 — 可补的（边际信号）

1. Roche RHHBY 2025 年报 CT-388 商业化披露
2. AMGN MariTide Phase 3 dosing 调整后的安全性数据
3. Structure GPCR 2025 10-K 完整 aleniglipron 数据

---

## § 8. 思维过程留痕

### 已知偏见

- **看多医药板块的情绪偏好**：本研究在 2025-2026 GLP-1 强 hype 期完成，论据筛选可能偏向"看多" — 反方观点 7 条已尝试系统性反向抵消
- **中国创新药主题偏好**：信达 / 恒瑞业绩拐点确实强但**估值已部分反映**，需警惕"BD 一次性 vs 常态化"假设破裂
- **LLY 长期叙事的锚定效应**：2025 Q4 - 2026 Q1 LLY 量价剪刀差正向已经发生 → 强化"看多 LLY"，但 2028+ 的结构性长期阻力可能被低估

### 刻意避开的偏见

- 避免把 NVO 全部困境视为"无可救药"——over-sold 反弹胜率被刻意 calibrate 在 30-40%
- 避免把 VKTX 视为"必然被收购"——Phase 3 失败 30-40% 概率诚实纳入
- 避免假设"中国 BD 出海是新时代起点" — 信达 sintilimab FDA 失败前科被纳入反方

### 关键差异

- **vs sell-side 共识**："看多 LLY 一家独大"是当前 sell-side 主流 → 本 thesis 已演化到"长 LLY + 长 NVO + 长 信达 + 期权式 VKTX"四标的，与共识不同
- **vs buy-side bear**：buy-side 部分 bear 视 GLP-1 为"政策杀价 + 第二梯队成熟双重压制" → 本 thesis 仍看多板块，但承认 2028+ 长期阻力
- **vs 中国本土投资者**：中国本土对信达/恒瑞业绩拐点已 price in → 本 thesis 海外配置 + 中国配置 mix 的角度

---

## § 9. 信息来源

**训练知识占比**：约 30%（GLP-1 类机制 / 历史代际跃迁 / 监管框架 / 估值方法 / 历史镜像）

**59 个 finding 全引用**（详见 outputs/_findings_index.md）。最关键 mat_id：

- 一手最新（2026 Q1）：mat-3a4b6e (LLY 10-K) / mat-20e63b (LLY 10-Q) / mat-606af8 (NVO 6-K Wegovy 7.2mg) / mat-69b291 (HIMS 10-Q)
- 中国创新药拐点：mat-11a269 (信达年报) / mat-3c1ced (恒瑞年报) / mat-214fbe (HRS9531 17.7%) / mat-841512 (Kailera $600M)
- 政策 + IRA：mat-92bc1e (FiercePharma IRA $274) / mat-a29026 (KFF BALANCE) / mat-36eaeb (AJMC IRA)
- 第二梯队：mat-6c585f (Roche CT-388 22.5%) / mat-1f9505 (VKTX VANQUISH-1) / mat-20420a (VKTX 10-K) / mat-0ed0b9 (GPCR aleniglipron)
- 行业全景：mat-524100 (anti-obesity 全景) / mat-6672e4 (中国 GLP-1 ¥383 亿 TAM) / mat-7edea3 (sema)

**Web-search 时效**：33 份均 2026-05-26 入库；20 个 query 全部 100% 命中；prescan_status=full

---

## 总结

GLP-1 减肥药 2026-2030 仍是医药板块最大 structural alpha 来源。**核心策略从 v1 的"看多 LLY 一家独大" → v2 的"长 LLY + 长 NVO + 长 Innovent + 期权式 VKTX 四标的组合 + 边际持 恒瑞"**。强度 7.5/10。下一次重大调整窗口为 2026 H2 - 2027 H1（reta + VK2735 + CT-388 + amycretin 4 个 Phase 3/2 数据集中读出）。

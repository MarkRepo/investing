---
slug: us-sandisk
variant: opus4.8
version: 2
parent_version: 1
writing_convention: 方案 C 全快照 + 顶部 changelog
generated: 2026-08-07
trigger: 05-critic request-rewrite（独立多方 + web 三角验证）
---

# SanDisk (SNDK) thesis_v2 — 全快照

## § 0. v1 → v2 changelog（release notes）

- **立场翻转（幅度非方向）**：回避/趋卖（EV −20%）→ **中性/持有（EV ≈ 0%，band −12%~+8%）**。方向仍偏谨慎（cyclical-not-structural，与 Morningstar 同侧），但不再是做空/回避判断。
- **正常化 EPS 锚**：$35-50 → **$65-85**。根因：v1 把"下行谷底年 EPS"误当"穿越周期中枢 EPS"×中枢倍数（对坏年景罚两次），且未把 NBM floor 计入中枢。
- **Bear FV**：$400（假设 2029 重演 GM −12%）→ **$720**。锚可信已发布空头 Morningstar $1,000，NBM 覆盖 1/3-1/2 + 净现金令谷底不再那么深。
- **Base FV**：$850 → **$1,150**（中枢 EPS 上修 + NBM 托底）。
- **新增证据**：Bernstein floor 测算（$214 FY30 EPS@60%覆盖@$0.11/GB）、Morningstar 1/3 覆盖 + $1,000 目标、consensus 多源（30 家均值 $1,659，2029 −51% 但出年仅 1 家覆盖）、HBF（NAND+HBM/SK海力士 MoU/OCP）、mix-shift 拆解。
- **命门1 重定义**：从"NBM floor 毛利率绝对值"→"**NBM 覆盖比例(1/3 vs 60%)×floor 单位经济**"，现被外部分析师区间夹住但仍未公司披露。

## § 1. 核心 thesis（当前完整版）

**一句话**：SanDisk 是一门被 NBM 长约真实改善、AI eSSD 需求可能部分结构化的强周期 NAND 生意；现价 $1,260（自 $2,354 回落 −46% 后）大致公允——落 consensus 均值目标 $1,659 之下、可信空头 Morningstar $1,000 之上。**穿越周期中枢 EPS ~$65-85**，我仍略低于街道隐含的 ~$110（保留温和看空倾向），但差距不足以支撑做空。

- **强度评分**：3/5（中性，信心中）。
- **估值带**：Bull ~$2,000（+59%）/ Base ~$1,150（−9%）/ Bear ~$720（−43%）；**EV ≈ 0%（中枢，band −12%~+8%）**。
- **时间维度**：周期思维 + 部分结构性期权，12-24 月。

## § 2. 支持理由（看多/托底逻辑 · 当前完整清单）

1. **NBM 长约把商品股向"有可见度"推**：$93.9B 最低合同营收 + $16.5B 担保 + variable 段 floor/ceiling，加权久期 >4 年 [mat-91210f]。连空方 Morningstar 都承认"genuinely different from prior cycles"[mat-dbd19e]。
2. **AI eSSD 需求含结构成分**：数据中心占比 12%→38%、+437% [mat-91210f]；25EB/GW 换算；QLC 替代 HDD 是存量迁移。
3. **mix-shift 支撑盈利质量**："出货持平"背后是低毛利消费量被高毛利数据中心量替换 + 管理层刻意压 bit 增长在 mid-high teens 维持定价权 [mat-d60fa4]。
4. **HBF 期权**：NAND+HBM 架构、SK海力士 MoU、OCP 标准化 [mat-d60fa4]——纯 NAND 玩家罕见的差异化技术位（早期，按期权计）。
5. **资产负债表排雷**：FY26 还清 Term Loan、净现金、股东权益 −$1.78B→+$13.8B [mat-91210f]，下行抗打击力远超 2022-23 时的 WDC。
6. **估值不再极端**：现价已 −46%，落 consensus 均值目标下方；Bernstein/BofA 目标 $2,500-3,000 [mat-8db6a2][mat-dde2cb]。

## § 3. 反方观点（看空/风险逻辑 · 当前完整清单）

1. **cyclical-not-structural（Morningstar 核心）**：NAND 高度同质、无定价权，earnings 随供需波动；峰值 ~2028、2029 回落 [mat-dbd19e]。$1,000 目标。
2. **P/B 13.5x 周期高位**：vs 周期底 ~1x，最硬的看空信号，下行空间真实。
3. **未覆盖段敞口**：NBM 若仅覆盖 ~1/3（Morningstar），剩 2/3 随市价，2029 下行可深跌 [mat-dbd19e]。
4. **FV 固定成本刚性**：$2,967M 敞口，无论提货付一半固定成本 [mat-f13cc1]，下行期无法轻资产收缩。
5. **需求侧领先警报**：hyperscaler capex 增速 76%→25%→6% [mat-8db6a2]；合约价涨幅 +75%→+10-15%。
6. **供给冲击风险**：三星逆周期扩产史、YMTC 制裁松动、新产能 2027-28 放量。
7. **命门1未披露**：NBM 覆盖/floor 毛利率公司未公布，正常化 EPS 中枢仍有 $65↔$100 的不确定。
8. **街道隐含仍略乐观**：均值目标 $1,659 隐含正常化 EPS ~$120+，高于我判 $75。

## § 4. Killer Question 现状表

| K# | 主题 | 当前状态 | 触发条件 |
|----|------|---------|---------|
| K1 | NAND 高价周期延续性 | 中性（合约价放缓但仍正、Morningstar 亦判峰值~2028） | 连续 2 季合约价环比转跌 |
| K2 | NBM 覆盖比例×floor 经济（命门1） | 未决（1/3 Morningstar vs 60% Bernstein，未公司披露） | 10-K 披露覆盖 ≥1/2 且 GM ≥40% → 上修；仅 1/3 且薄 → 下修 |
| K3 | SanDisk 成本/技术位 + HBF | 中性（8 家客户/HBF MoU 正面；Solidigm QLC 领先） | HBF 获量产客户 / BiCS 成本落后 |
| K4 | 正常化 EPS 中枢（估值锚） | 上修至 ~$65-85（多源 consensus 三角验证后） | 覆盖比例明朗 → 收敛成点估 |
| K5 | 资本配置纪律 | 中性偏正（净现金；高位回购待观察） | 峰值继续激进扩张/回购 |
| K6 | 供给冲击（三星/YMTC/新产能） | 风险敞口存在 | 逆周期扩产公告 |

## § 5. 应对策略矩阵（价格 × 动作）

| 价格区间 | 动作 |
|---------|------|
| > $1,300 | 减持/不追（超 hold 区上沿） |
| $850-1,300（现价 $1,260） | 持有/观望，不建仓不做空 |
| $700-850 | 试探建仓（≤满仓 4% 的首档） |
| $550-700 | 加仓（较好赔率） |
| < $550 | 深度恐慌重仓 |

## § 6. catalyst 时点表

- **2026-Q4**：FY2026 完整 10-K（NBM 覆盖/floor 细节 — 命门1钥匙）；TrendForce Q4 NAND 合约价方向。
- **2027-Q1**：hyperscaler FY2027 capex 指引；三星/YMTC 扩产公告；WDC-Kioxia 合并进展；HBF/OCP 进展 + 首个量产客户。
- **持续**：每季 bit 出货 vs ASP 分解、库存 DIO、RPO。

## § 7. 数据缺口

- **P0**：NBM 覆盖比例（1/3 vs 60%）+ floor 绝对毛利率——命门1，未公司披露，现被 Morningstar/Bernstein 区间夹住。→ 07-drilldown `nbm_coverage_and_floor_economics`。
- **P1**：HBF 商业化时间线/客户/营收贡献——OCP 标准化落地节奏。
- **P2**：穿越周期倍数 13-16x 为训练知识估算，非精确锚。

## § 8. 思维过程留痕

- **已知**：v1 因方法论错误（谷底数当中枢 + Bear 无视 NBM 托底）过度看空 −20%；05 独立多方 + web 三角验证纠偏至中性。
- **刻意避开的偏见**：(a) 不因在 web 搜到 Bernstein 多方证据就翻多——保留 P/B 周期高位 + 未覆盖段风险 + 街道隐含仍偏乐观的看空成分；(b) 不把 2029 −51% 当铁证（出年仅 1 家覆盖 + 无视 NBM）；(c) 不把 HBF 当已兑现护城河（按期权计）。
- **关键差异**：本 case 与 Morningstar 同判 cyclical，但认为其 $1,000 目标/1/3 覆盖偏保守；与 Bernstein 同认 NBM 有牙，但认为 60% 覆盖/$3,000 偏乐观——落在两者之间。

## § 9. 信息来源

- 训练知识占比 ~18%（周期机制/估值方法/竞争格局）。
- 关键 mat：mat-91210f、mat-e0fafe、mat-04096b、mat-f13cc1、mat-572c9f、mat-2394bf、mat-c68feb、mat-d1581f、mat-dbd19e、mat-8db6a2、mat-07630c、mat-dde2cb、mat-d60fa4 + market_data(2026-08-06) + macro_stamp(regime v4)。

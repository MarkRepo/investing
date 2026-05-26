---
slug: cn-rongchang-bio-688331
output_key: 05-critic-review
version: 1
generated: 2026-05-26T10:30:00+00:00
thesis_version_reviewed: 1
verdict: request-rewrite
rewrite_keys:
  - 04_implied_expectations
  - 07_decision_kit
  - 05_historical_mirrors
---

# 批评者评审：荣昌生物 (RemeGen) — thesis_v1

> 生成于 2026-05-26，基于产出 04_implied_expectations / 06_risk_blindspots / 07_decision_kit + thesis_v1.md
> prescan_status: None（thesis v1 写时旧 topic）；gap_detector: 0 gap

---

## Step 0 体检

- prescan_status=None（旧 topic 在 thesis_v1 写时未记录写时状态，按规约「None → 正常推进」）
- gap_detector: ✅ no gaps — 所有 K# 均有充分材料覆盖（mat-6601a1 主载体 + mat-9ad4f3 + mat-cf360d + mat-75c2be 校准基线）

不构成 verdict 升级到 request-more 的理由——所有反方论据从**已入库材料 + 内部一致性**就能展开。

---

## Step 2：钢人反方（空方视角）

### 对「K2 RC18 自免兑现 stronger_bull (my_prob=0.75)」的质疑

**多方假设**：IgAN BLA 优先审评 + MG 进医保 + SD NDA 已交 → 75% 兑现概率

**反驳**：
- **BLA 受理 ≠ 获批**：CDE 优先审评通过率历史约 60-65%（PD-1/IL-17 类已饱和参考），不是 90%+ 自动通过
- **进医保 ≠ 销量爆发**：[mat-6601a1] 泰它西普 2025 销量 +47.92% 但库存 +64% → 渠道压货已暴露需求滞后；进医保后单价砍 30-50%，量价能否弥补未有定数（参恒瑞卡瑞利珠单抗 2018-2020 案例）
- **多适应症同时申报 = 资源稀释**：单家 NMPA pre-IND meeting 资源有限，IgAN/SD/MG 同期推进可能延误某条线

**支撑证据**：mat-6601a1 库存比 + 2026Q1 营收增速从 +89% 降到 +25% + 2025-04 上交所对收入确认时点提问未消除疑虑

**强度评估**：**中** — my_prob=0.75 vs market=0.70 仅 5pp 差距，但向下风险（BLA 退回 / 医保降价 50%+ / 库存去化）的左尾未充分加权

---

### 对「K3 Pfizer 仍合作 (neutral_bull, my_prob=0.30)」的质疑

**多方假设**：Pfizer 仍是前 5 大供应商 + "1L UC III 期 enrollment underway" → 30% 兑现概率 (vs market 10%)

**反驳**：
- **供应商关系 ≠ 临床合作活跃**：年报披露的"前 5 大供应商"金额仅 0.36 亿，可能是历史合同尾款 / 原料采购残留，与 RC48 海外开发优先级无直接因果链
- **公司年报口径 vs 一手报道分歧未解**：fiercebiotech/apexonco 2024-02 报道 Pfizer 减值 USD200M + 2025-02 报道 "permanent termination" → 这些一手报道**可信度未必低于公司单方年报披露**，市场可能定价"信任公司披露"程度只有 30-50%
- **Pfizer 战略转向**：2023 收购 Seagen 后 ADC 战略已转向 zanidatamab/ARX788/EV (enfortumab vedotin) → RC48 在 Pfizer 管线优先级实质下沉
- **时间窗放大不确定性**：NCT05911295 III 期 readout 在 2027-2028，期间 Pfizer 任何季报"未提 disitamab"都是减弱信号；my_prob=0.30 在 24 个月窗口被 review 多次后实质回落到 0.10-0.15

**支撑证据**：训练知识 + Pfizer 2023-2024 oncology 重组减值历史 + Pfizer 2024Q4 10-K 已不强调 disitamab + Genentech ADC 重组案例

**强度评估**：**强** — 这是 v1 最大反转点，但 my_prob 从 v0 偏空直接跳到 0.30 是过激；**实际应在 0.15-0.20**。v1 K3 修订对市场情绪信号定价不足

---

### 对「SOTP 540 亿 + 风险加权 -21.5% 下行 vs 整体 6/10 温和看多」内部一致性的质疑（**最关键反驳**）

**多方假设**：SOTP 加权 NPV 540 亿 + 风险加权 -21.5% 下行预期 → 仍维持 6/10 温和看多评分

**反驳**——**这是 thesis 内部逻辑断裂的最大盲点**：

- **SOTP 540 亿已是温和乐观加权值**：情景概率加权 30% bear @350 + 50% base @580 + 15% bull @800 + 5% super_bull @1200；当前市值 720 亿 → 隐含 -25% 高估
- **风险量化加权 -21.5% 是独立口径**：06_risk_blindspots Step 7 表的 6 项风险概率 × 单次影响加权得出
- **两个独立量化口径同向 → 评分应在 4-5/10 中性 或 中性偏空**，不应是 6/10 温和看多
- **决策矩阵价格区间设置滞后**：650-800 亿"持有"区间过宽 → 真实 fair value 在 425-540 亿，"持有"区间应下移到 540-650 亿；现价 720 亿应该是"小幅减仓"区间而非"持有"
- **6/10 评分实际是 thesis_v0 的延续**：未随 v1 K# 5 处修订（K1↓ / K3↑ / K4↓ / K5↓）重新校准——v1 K# 修订方向净偏空（K2 升 + K3 升 vs K1 降 + K4 降 + K5 降，3 降 vs 2 升）

**支撑证据**：04_implied_expectations 隐含市值反推 + 06_risk_blindspots Step 7 风险加权表 + 07_decision_kit 价格区间设置

**强度评估**：**强** — 这是结构性逻辑错误，比单 K# 错估影响面更大；直接动摇 thesis 评分基础

---

### 对「K1 RC148 SOTP 估值 + 历史镜鉴」隐含假设的质疑

**多方假设**：RC148 全球峰值销售 USD500M-1B（05_historical_mirrors 镜鉴 2 提及但未明确锚定到 SOTP）→ AbbVie 上付 USD650M + 里程碑 USD4.95B

**反驳**：
- **峰值估算未与竞品同步压制**：康方 AK112 已 FDA 受理 (2025-Q4)，临床数据领先 18-24 个月；Roche CT-388 / Merck PD-L1xVEGF 多款双抗在跑——RC148 即使 III 期成功，全球峰值更可能在 USD300-500M 中位数（被 best-in-class AK112 抢占首发优势后）
- **AbbVie 经济条款的"金额"未被 A 股年报披露 →** 监管审批 + 签订条件未完，USD650M 的"上付"在文件签订前不构成会计认定
- **2027-2028 III 期 readout** 时点远，期间任何"PFS HR 仅 0.7-0.85"非显著优势 readout 都构成 K1 大幅减弱
- **SOTP 540 亿对 K1 应给 50-100 亿权重**（reflect 30% × USD500-1000M peak × 8x P/Sales × HR=0.5 折现），目前 SOTP 似乎给了 K1 过高权重

**支撑证据**：训练知识 + AK112 / Summit Therapeutics 2024-09 HARMONi-2 数据 + Pfizer-Seagen 2023 整合后 disitamab 减值

**强度评估**：**中-强** — 隐性假设透明度不足；建议在 04 重写时显式列出 RC148 峰值假设 + 折现率 + 竞品压制因子

---

## Step 3：原研究评分

| 维度 | 评分 (1-5) | 评语 |
|---|---|---|
| 逻辑严密性 | **3** | SOTP 加权 NPV / 风险加权下行 / 整体评分三口径不对账；K3 my_prob 跨度过激；决策矩阵价格区间未随 v1 同步下移 |
| 证据充分性 | **4** | 4 份财报全用 + 索引完整；mat-6601a1 与 mat-9ad4f3 互校良好；Vor Bio warrants 数据已挖到 |
| 考虑反面观点 | **3** | K3 反方论证有但 my_prob 过激；K2 向下尾部（库存去化 + BLA 退回）未充分量化；6/10 评分对反方加权未生效 |
| 隐含假设透明度 | **4** | warrants/扣非主业已显式分离；但 RC148 全球峰值 USD500M-1B 假设未明确入 SOTP；AbbVie 监管条件未明示 |
| **整体** | **3.5** | thesis_v1 K# 修订方向对，但量化口径未跨产出对账 |

---

## Step 4：3 条最重要修改建议

1. **SOTP 540 亿 + 风险加权 -21.5% 必须与整体评分对账** → 重写 04_implied_expectations + 07_decision_kit；评分应降到 **5/10 中性偏多** 或者重审情景概率（bear 30% 是否过低？）；07_decision_kit 价格区间下移：540-650 亿"持有"，650-800 亿"小幅减仓"，720 亿现价应在"小幅减仓"区间
2. **K3 Pfizer my_prob 从 0.30 → 0.15-0.20** → 重写 04_implied_expectations 概率表；重写 07_decision_kit K3 加仓阈值（NCT05911295 中期分析阳性 my_prob 应配 0.10-0.15 而非 0.20）；K3 SOTP 权重相应下调
3. **K1 RC148 全球峰值假设显式化 + 竞品环境同步压制** → 重写 05_historical_mirrors，加入 AK112 (FDA 受理 2025-Q4 已确认) / CT-388 / MariTide / VK2735 / MK-7240 III 期/上市时间表；重写 04_implied_expectations 的 SOTP 反推，明确 RC148 峰值取 USD500M 中位数而非 USD500M-1B 区间，对应 K1 SOTP 权重 50-80 亿（不是 100-150 亿）

---

## Step 6.5：缺口判定 — 不需 web-search 兜底

修改建议指向**内部口径对账 + 可比公司参数刷新**，所有数据已在训练知识 / 现有 mat 内可解决：

- 建议 1（评分对账）：纯内部一致性 → 04 重写直接修
- 建议 2（K3 my_prob 重估）：mat-6601a1 + 训练知识 → 04 重写直接修
- 建议 3（竞品环境）：AK112 / CT-388 / MariTide 已是训练知识里的标准案例 → 05 重写直接修

**结论**：不触发 Step 6.5 web-search 兜底。

---

## Step 7：verdict — `request-rewrite`

**verdict**: `request-rewrite`
**theory_version_reviewed**: 1
**rewrite_keys**: `04_implied_expectations`, `07_decision_kit` (含 sidecar yaml), `05_historical_mirrors`
**why not approve**: 评分 3.5/5 < 4，且存在结构性逻辑错误（SOTP/风险加权/评分不对账）
**why not request-more**: 0 gap + 反方论据均可在内部对账解决；不需新一手资料

**对 thesis_v1 评分的影响**：
- 维持 K2/K3/K4/K5 修订方向不变
- 整体评分应从 6/10 降到 **5/10 中性偏多**（基于 SOTP 隐含 -25% + 风险加权 -21.5%）
- 是否触发 thesis_v2 升版：rewrite 影响 3 份产出（≥3 但 <5），不强制升版；但建议在 04 重写中保留"SOTP 数字 540 亿 + 评分 5/10"的内部一致版本

---

## Step 7.5a 预告：rewrite 范围确认

待用户 confirm 后续跑：
- `04_implied_expectations` (critic-stale) — 重写 K3 my_prob + SOTP 加权
- `07_decision_kit.md + .yaml` (critic-stale) — 重写价格区间 + 加仓/减仓阈值
- `05_historical_mirrors` (critic-stale) — 加入 AK112/CT-388/MariTide 竞品时间表

预计 ~6-8K token/份 × 3 份 = ~20-25K 总输出，主 agent 直做（不 dispatch sub-agent，参 [[feedback_subagent_bulk_synthesis]]）。

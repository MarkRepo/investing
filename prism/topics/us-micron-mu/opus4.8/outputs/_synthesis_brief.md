# _synthesis_brief — us-micron-mu/opus4.8

> 04 合成期 cross-mat 校准锚。dump K1-K5 的 v0→v1 强度调整结论，供 ④⑤⑥ 与 chain-critic 复用。

## ⚠️ 价格口径校正（合成第一要务）

thesis_v0 frontmatter 写 "$406 / forward PE 10.7x"——**这是 prescan 早期快照，与 v0 自身的 $1.12T 市值和 findings 全部冲突，作废**。

合成统一采用 **market_data 实时口径（2026-06-11）**：
- 股价 **≈$996**（当日 +11.66%），52 周高 **$1,089** / 低 **$103.38** → **12 个月 +~9x**（mat-f3679c/mat-8dc9dc 印证 +~900%）。
- 总市值 **≈$1.12T**，PE(TTM) **46.9x**，PB **15.5x**，PS 19.3x。
- 刚破 $1T 俱乐部（mat-398207，曾单日 +19%），现处 ATH 区间。

含义：thesis 方向（一流 franchise、当前价位计入乐观情景、追高赔率差）**不变且更锐利**——股价现已**高于卖方一致目标价**（street mean ~$613-717，mat-dda82b/Goldman$900 mat-3824d5 仍低于现价）。"priced for perfection" 从定性变成字面事实。

## "便宜 PE" 的真相（K5 命门数字）

forward "10-14x" 是**峰值 EPS 倍数**：
- Q2FY26 摊薄 EPS $12.07、H1 $16.68（mat-4783c9/mat-dd8b66）；年化 run-rate ~$85B 利润（mat-85c74c）→ 峰值 EPS 锚 ~$50-74+。
- 跨多十年 **normalized GM ~40%**（vs 当前 74%），normalized EPS 远低 → mat-85c74c：**14x 峰值 ≈ 50x normalized**。
- FY23 摊薄 EPS **-$5.34**、FY24 $0.70、FY25 $7.59（mat-5a387b）——三年留存收益仅净增 $1.3B，证明穿越周期正常化盈利远低于峰值。

## K1-K5 v0→v1 强度调整

| K# | 主题 | v0 | 厚料结论（v1） | 强度 |
|----|------|----|----|------|
| K1 | HBM 护城河耐久性 | 中 | Micron 已被**结构性接纳为第三供应商**（HBM4 三家齐过 Vera Rubin 认证 mat-14a5a4），但 SK Hynix 仍占 Vera Rubin 初期分配 **60-70%**、Micron HBM 份额仅 **~10-20%**（mat-1aae1a）。结论=**"已脱离淘汰风险、但非领导者，份额天花板可见"**（mat-e85217：份额由认证决定、Micron 认证节奏快但 HBM4 世代护城河转为良率/价格）。命门2"水涨船高第三名"被证实为真实风险，但下行期被挤出的尾部风险下降（认证已过）。 | 中性偏稳 |
| K2 | 周期顶判定 | 中 | **74% GM 是无可争议峰值**（历史峰值 ~60%、normalized ~40%，mat-85c74c）。增长**几乎全靠 ASP**（DRAM bit 出货 QoQ 仅 mid-single，mat-dd8b66）= 典型价格峰值。2022 镜鉴：GM 47%→40%→22.9%→指引 8.5%，~3 季完成顶→亏（mat-bc352c）；历史更惨尾部 DRAM -89%（2001，mat-6a8149）。 | 命门1确认·偏空 |
| K3 | 供给拐点时机 | 低 | capex 升（行业 DRAM +14%、Micron DRAM capex +23% mat-035fad）**但 bit 受限**（洁室上限+资金转工艺/HBM 非裸产能，Micron ID1 2027 前不投产）→ 供给洪水**后置到 2027+**。早期裂痕：HBM 单 wafer 经济性 1Q26 已跌破 DDR5 RDIMM、产能开始回流标准 DRAM（mat-c3ac1f）。CXMT 仅低端 ~7.67%（prescan mat-8f0602）。 | 时点仍低·2027 为交汇年 |
| K4 | AI 需求结构性 vs 泡沫 | (并入命门3) | 多空收敛到**单一变量 = 2027 hyperscaler capex**（mat-398207）。bull：CY2026 售罄、CEO 只能满足 50-65% 需求、客户预付款（罕见）。bear：hyperscaler 已举债 $260B、Northland 模型 CY2027 datacenter 支出**下降**、AI 效率 30x 或在 2029-30 压缩 HBM 需求（mat-85c74c）、TrendForce"营收 2027 见顶"（mat-feabed）。Micron 10-K 自陈 AI 需求"新、可能不兑现/不持续"（mat-c6503b/64ca13）。 | 真两难·2027 命门 |
| K5 | 穿越周期盈利质量与估值锚 | 中 | 现价 $996 **高于 street mean target ~$613-717**、高于 Goldman 上调后 $900（mat-3824d5）；仅 UBS $1,625 以"AI-infra 非周期股"范式给高（EPS>$100 贯穿 2027-29，mat-dda82b）。PB 15.5x 高位；$25B+ capex 吞噬 FCF（mat-dd8b66/8dc9dc）。估值锚完全取决于"周期股 vs AI-infra"框架选择。 | 命门1确认·偏空 |

## 强度评分 v0→v1

**维持 4/10**（生意 8/10 × 入场时点 3/10 加权）。厚料**确认并锐化** v0：
- 不变：一流存储 franchise、HBM 真实结构性内核、资产负债表已质变（净去杠杆、$16.6B 现金）。
- 锐化：股价已破 $1T/ATH 且**高于卖方一致目标**、74% 峰值 GM + 全 ASP 驱动 = 教科书周期顶、normalized 估值 ~50x。
- 一句话：**伟大公司、峰值利润率、超越共识的价格——耐久价值属于买在下一周期底者，不是此刻追 ATH。**

## 命门 delta（B 轴重拆预判）

v0 三命门（盈利可持续性/HBM 护城河/供给拐点）厚料后**全部确认、无坍缩、无新增**。微调：命门1（周期顶）与命门3（供给/需求 2027 拐点）置信度由厚料从"中/低"升至"中高/中"（2027 成为多条线交汇的可观测时点）。命门2（HBM 护城河）维持"中"。→ delta 实质为空（仅置信度更新），decomposition_v1 判 converged。

# Synthesis Brief — global-glp1-obesity/opus4.8

> 04 合成期 cross-mat 校准锚。dump K1-K5 v0→v1 强度调整 + ② 定价锚数字 + 命门 delta。供 primer/case/critic 复用。

## ② 定价锚（Step 1 point 2b · F13 拉数结果）

| 主体 | ticker | PE(TTM) | PS | PB | 市值 | 来源/日期 |
|---|---|---|---|---|---|---|
| **Eli Lilly** | LLY | **41.8** | 14.6 | 33.8 | **$1.05T** | 本地 yfinance 2026-07-17 ✓ |
| **Novo Nordisk** | NVO | ~12（trailing）/ 14-17（fwd） | — | — | ~$218-225B | web-search fallback [mat-21a243] 2026-07-20 |
| **Amgen** | AMGN | ~16.6（fwd） | — | — | ~$200.5B | web-search fallback [mat-21a243] |
| **Hims&Hers** | HIMS | 58.3 | 2.9 | 12.5 | $6.8B | 本地 yfinance 2026-04-27 ✓ |
| **恒瑞医药** | 600276 | **44.9** | 11.2 | 5.7 | ¥364.6B (~$51B) | 本地 akshare 2026-07-21 ✓ |
| **信达生物** | 01801 | **170.6** | 10.6 | 7.1 | HK$160.4B (~$20.5B) | 本地 yfinance 2026-07-21 ✓ |
| **华东医药** | 000963 | 15.5 | 1.2 | 2.1 | ¥54.2B (~$7.6B) | 本地 akshare 2026-07-21 ✓ |
| VKTX / GPCR | — | 无盈利 | — | — | 期权/并购价值 | 拉不到；findings：VKTX ~$30 vs 目标$95 [mat-2a5b8f] |

**F13 缺口 log**：NVO/AMGN/VKTX/GPCR 本地 yfinance 连续 2 次返 "no quote data"（API 侧 ticker 问题，非我方口径错）→ NVO/AMGN 走 web-search fallback（多源交叉 Yahoo/StockAnalysis/Investing.com，可信）；VKTX/GPCR 无盈利、按期权价值定，用 findings 锚。**② 主锚 LLY 41.8x 为实拉，脊柱不塌。**

**定价锚一句话**：市场把 GLP-1 利润池的绝对领导+扩张预期几乎全押在 LLY（41.8x PE / 14.6x PS / $1.05T，成长溢价拉满）；NVO 被 de-rate 到 ~12x trailing（-29% YoY，"价值/困境反转"叙事）；恒瑞 44.9x（肿瘤+代谢双极）、信达 170.6x（首年盈利+高成长溢价）、华东 15.5x（仿制/存量属性）。**定价笃定度最高（LLY）的地方，恰是③里"口服平权化真放量+疗效阶梯兑现"两条最弱结构假设付溢价处。**

## K1-K5 v0→v1 强度调整

- **K1 口服平权化（v0：深挖档主支柱，LLY 侧 8/10）→ v1：路径证实但主角分化，8/10 维持**
  - 兑现：orforglipron/Foundayo 2026-04 FDA 获批肥胖 [mat-c9c6aa]；口服 Wegovy pill (sema 25mg) 亦获批，**占美国新增 GLP-1 处方 ~65%** [mat-21a243] → 口服放量比 v0 预期更快。
  - **v1 关键 refine**：orforglipron 本身减重仅 10.5%（ATTAIN，弱于注射 20%+）；而 GPCR aleniglipron ACCESS II 44wk **-16.3% 无平台期** [mat-63a6fb]、VKTX 口服 13wk **12.2%** [mat-b1dcfc] 反而更强 → **LLY 是口服"速度/规模"领跑者，不必然是口服"疗效"领跑者**。命门1（疗效↔可及性权衡）仍 open。

- **K2 三激动/amylin 疗效天花板（v0：深挖档，8/10）→ v1：LLY retatrutide 独占天花板，8/10 维持**
  - retatrutide TRIUMPH-1 80wk **28.3%** / 104wk(BMI≥35) **30.3%** [prescan]；Roche CT-388 22.5% [mat-c68134]；VKTX 皮下 14.7% [mat-b1dcfc]。
  - 挑战者掉队：MariTide III 期高停药/高呕吐、读出**推迟到 2027** [mat-cf0f51]（与 10-K 乐观口径对撞 [mat-420fa5]）；NVO CagriSema 20.4% 头对头**败于** Zepbound [mat-54d41a]。
  - NVO 反制：sema 7.2mg STEP UP **20.7%**、1/3 达≥25% [mat-76802d] → 单分子加量 ≈ combo，NVO 高端未落一个代差。

- **K3 NVO 止血（v0：淘汰/低配档，3/10）→ v1：结构承压确认，但"已 price-in"张力上升，3-4/10**
  - 承压确认：2025 美国肥胖+糖尿病处方量第一双双被 LLY 夺走、全年丢份额 [mat-77d015]；2026 指引销售下滑 vs LLY 跳增 [mat-715f0d]；evoke 阿尔茨海默失败 [mat-4ce150]；市值排名 #2→#5。
  - **反方增强**：NVO trailing PE ~12x、-29% YoY [mat-21a243]，悲观已深度定价；oral Wegovy 65% 新处方 + sema 7.2mg 是真实反击子弹 → 命门2（衰减是斜率 vs 断崖）是低配 NVO 的时点/幅度风险，做空拥挤。

- **K4 国产双靶+仿制（v0：观察档，期权非耐久池）→ v1：确认观察档，出海期权兑现、本土池薄**
  - 双靶落地：信达 mazdutide 2025-06 获批、首年盈利 [mat-97c2bb]；恒瑞 HRS9531 17.7% + Kailera $6B 出海 [mat-479a41]、恒瑞代谢成第二极。
  - 仿制潮：sema 中国专利 2026-03-20 到期，10+ 家申报，价格预降 50%+ [mat-7de0c1]；九源领跑 [mat-6bf701]。**申报≠获批放量**（截至 07 中国尚无 sema 仿制获批）→ 节奏 uncertain。
  - 利润率天花板低（华东毛利 32%、净利微降 [mat-70c031]；10+ 家内卷）→ 期权价值 > 耐久利润池。

- **K5 净价 vs 放量 = 利润池总闸（v0：行业总 beta 6/10）→ v1：TAM 下修，beta 5-6/10，最大不确定源**
  - 净价压：IRA 2nd round sema Ozempic $274 / Wegovy $385，2027-01 生效 [mat-331b3f]（tirzepatide **不在**本轮 [mat-678c60]）；TrumpRx ~$245 自愿协议价 + tirzepatide Medicare opt-in $50/月 [mat-8b9937]；LLY 美国价 -7%、国际 -25%（中国 NRDL）[mat-c9c6aa]。
  - 覆盖扩：2026 Medicare 首次把肥胖作独立适应症纳入；LLY Medicare Bridge Program 2026-07~2027-12 [mat-c9c6aa]。
  - **TAM 下修**：Jefferies 2026-01 峰值预测 -20% 至 **$80B**（原 >$100-150B）[mat-ee7fd6]，Gabelli $30B→$80B [mat-36647e]。命门3（净价路径=总闸）是"深挖档是否值得深挖"的行业级 beta 风险。

## 命门 delta（B 轴 · 详见 decomposition_v1）
- 命门1（口服疗效↔可及性权衡）：**厚料细化未坍塌** — 新增"LLY 口服是规模领跑非疗效领跑"这一层，权衡仍 open。
- 命门2（NVO 衰减斜率 vs 断崖）：**升信心为"结构性慢衰减 + 估值已定价"** — 断崖证据不足，低配 NVO 的赔率不对称风险上升。
- 命门3（净价路径=利润池总闸）：**从"低置信优先砸料"升为"证据充分、TAM 已被下修"** — 仍是最大 beta 不确定，进环⑤ signpost。
- primer 入门目标 delta：新增 1 条"区分口服'规模领跑'与'疗效领跑'"；其余 12 条 v0 种子厚料确认。

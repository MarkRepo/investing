# Synthesis Brief — global-glp1-oral-small-molecule/opus4.8

> Step 1 收口：K# v0→v1 强度校准 + 命门校准 + peer 财务/估值锚。供 ④⑥ 与 chain-critic 复用。

## 数据校准（合成前必读，防口径错）

- **aleniglipron(GPCR/GSBR-1290) 疗效须区分剂量/时点**：核心 120mg / 36wk 安慰剂调整 **−11.3%**[mat-124143, mat-0b4c14]；探索性 240mg/36wk −15.3%；**44wk 高剂量 180mg −16.3% / 240mg −16.0%（OLE 无平台期）**[mat-63a6fb]。thesis_v0 引用的"−16.3%"= 44wk 高剂量，不是核心基准。合成一律双标注（核心 11.3% / 高剂量 16.3%）。
- **VK2735(VKTX) 口服** VENTURE-Oral 13wk −12.2% vs 安慰剂 1.3%[mat-b1dcfc]；皮下 −14.7%。
- **orforglipron(LLY)** Phase 3 减重约 **10.5%**（vs 口服司美 5.3%）[mat-e0d600]；2026-04-01 FDA 批准(Foundayo)[mat-f39c3c, mat-c9c6aa]。
- **估值时点** peer 行情均为 2026-07-21：VKTX $37.95/市值 $4.4B（较 Feb $30.45 已涨）、GPCR $49.35/市值 $3.5B——**VKTX 市值已反超 GPCR**（thesis_v0/父级用的 EV VKTX $2.65B < GPCR $4.05B 已过时）。

## K# 强度校准（v0 → v1）

| K# | 主题 | v0 | v1 校准 | 依据 |
|---|---|---|---|---|
| K1 | 放量斜率(平权化真放量?) | open | **方向兑现、斜率被支付摩擦压制**——orforglipron 获批+口服 Wegovy 65% 新处方[mat-21a243]，但商业保险仅 1/3 覆盖肥胖、Medicare Part D 肥胖覆盖迟至 2027、净价下行(DTP/去回扣)[mat-fd18f6, mat-1cc9d9, mat-f39c3c]。量增价减、慢坡风险真。 |
| K2 | 规模 vs 疗效领跑 | open(新增) | **规模领跑收敛到 LLY、疗效领跑者是 M&A 期权**——LLY 已获批+$1.5B 库存+$1T 市值+多适应症；GPCR/VKTX 疗效更强(11-16%)但落后 3-4 年、pre-rev、商业化 2029/30[mat-124143, mat-63a6fb, mat-b1dcfc, mat-87d0af]。 |
| K3 | 长期 generic 自毁? | open(新增) | **近期专利护、长期悬崖陡+IP 诉讼**——小分子 ANDA generic 比多肽 biosimilar 更快(DPP-4/丙肝镜鉴)[mat-daac55, mat-da05cc]；但 orforglipron/aleniglipron 专利到 2040s(aleniglipron 2041-45)[mat-124143]，近期利润池护；IP 诉讼风险(Gilead→Merck $2.54B)[mat-56ee94]。 |

## 命门校准（无 v0 种子 → 据厚料直接立 v1）

1. **疗效↔可及性权衡（主命门）**：口服 10.5% 是"利润池迁移目标"还是"可及性补充入口"？——放量兑现但疗效 gap 真，他汀/PCSK9 镜鉴支持"可及性可压倒边际疗效"[mat-a6e783]，但 10.5% vs 20%+ 落差远大于他汀-PCSK9。
2. **规模 vs 疗效领跑谁最终赢**：LLY 规模(卡位/渠道/产能/多适应症) vs GPCR/VKTX 疗效(落后+pre-rev)——收敛到 LLY 还是纯标的成独立利润池/被并购。
3. **generic 悬崖陡度 + IP 位势**：小分子 generic 比多肽 biosimilar 更陡、更快；但复杂结构专利 + IP 组合(GPCR 最强、Roche $100M 背书)是护城河博弈[mat-875aa5]。
4. **支付摩擦/净价 = 放量总闸**：1/3 覆盖 + Part D 2027 + 净价下行——放量斜率被限速。

## Peer 财务 + 估值锚（2026-07-21，financial_data + market_data）

| 公司 | Ticker | 收入 | 毛利率 | 3Y ROIC | 资产负债率 | PE(TTM) | 市值 |
|---|---|---|---|---|---|---|---|
| 礼来 LLY | LLY/US | $65.2B | 83.0% | 27.2 | 1.60 | 40.8 | $1.05T |
| 诺和诺德 NVO | NVO/US | DKK 309B | 81.0% | 42.8 | 0.67 | 11.9 | $218B |
| Viking VKTX | VKTX/US | $0(pre-rev) | n/a | -35.9 | 0.0002 | n/a(PB 8.8) | $4.4B |
| Structure GPCR | GPCR/US | $0(pre-rev) | n/a | -17.7 | 0.004 | n/a(PB 2.4) | $3.5B |
| 恒瑞医药 | 600276/SSE | ¥316亿 | 86.2% | 12.6 | 0.0 | 44.9 | ¥3646亿 |
| 华东医药 | 000963/SZSE | ¥436亿 | 32.4% | 13.5 | 0.07 | 15.5 | ¥542亿 |
| 阿斯利康 AZN | AZN/US | $58.7B | 81.9% | 11.6 | 0.60 | 24.8 | $263B |

- pre-rev biotech(VKTX/GPCR)：PE/收入/毛利率 不适用，用 现金 runway + 管线阶段 + 市值/期权价值 替代。VKTX 现金 $705.7M(到 2027Q1)、GPCR $1.46B(到 2028)。
- 定价锚×证据强度张力：市场为 LLY 会赢付 **40.8x PE / $1T**，该溢价踩在 WMBT 最弱两块——orforglipron 10.5% 疗效够用 + 放量不被支付摩擦压制。

## 环⑥ 分档预判（tier = 卡位/质量 × 当前定价）

- **深研**：VKTX（口服+皮下双剂型、12.2% 逼近注射、产能锁定、弹性最大、M&A 期权）、GPCR（小分子纯口服、IP 最强+Roche 背书、amylin 期权、现金到 2028）。
- **观察**：LLY（规模卡位 A 级但 40.8x 已贵→回调<28x 或 orforglipron TRx 斜率触发）、恒瑞（国产小分子 HRS-7535 Phase 3 完成入组+BD 出海货币化，但 44.9x 贵+国产内卷）。
- **淘汰**：华东医药（毛利率 32% 商业模式硬伤+减重小基数，quarantine=false 可 revive）、NVO 口服司美（oral peptide 结构劣势：需 SNAC/成本高/难规模化+已在 injectable arena）、AZN（AZD5004 仅 Phase 2b 太早+差异化偏耐受性非疗效）。

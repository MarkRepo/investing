# Findings Index — pinduoduo/qwen3.7-max

> 主 agent 调度提示：写每批 output 前重读本文件，按 addresses(K# 脊柱) + rings(决策链输入合同) 判断 context 是否覆盖所需维度；
> 记忆模糊的 mat_id 单独 Read `outputs/findings_{mat_id}.md` 补回。

## 自有 findings（24 份）

- `mat-00c2f5` | sec/2025_PDD_20-F_2026-04-29/item_3_key_info.md | addresses=[K1,K6] | rings=[bull-bear] | high/neutral | F Item 3 为 Key Information 章节，覆盖风险因素、关键财务数据
- `mat-0a278b` | 2026-06-04_eu-commission-press-release-on-temu-dsa-enforcemen.md | addresses=[K1] | rings=[bull-bear] | low/neutral | EU Commission DSA enforcement press release (ip_26_1178)
- `mat-0b86da` | sec/2025_PDD_20-F_2026-04-29/item_11_quant_risk.md | addresses=[K2] | rings=[-] | low/neutral | FX 风险：大部分收入和费用以人民币计价，ADS 价值受 USD/RMB 汇率影响
- `mat-116f72` | 2026-06-04_pdd-holdings---earnings-calls-investor-presentatio.md | addresses=[K4,K5] | rings=[consensus] | low/neutral | Quartr 平台 PDD earnings call 索引页
- `mat-170950` | 2026-06-04_is-pdd-holdings-inc-pdd-stock-a-good-investment---.md | addresses=[K4,K5] | rings=[bull-bear,valuation-anchor] | low/neutral | 核心观点已在卖方报告 (mat-2a4589/mat-57266c/mat-f66988/mat-ae2252) 中覆盖
- `mat-1d45a7` | 2026-06-04_china-estimated-top-online-retailers-ecommerce-mar.md | addresses=[K3] | rings=[biz-moat-unit-econ] | low/neutral | 核心数据已在 mat-fb9065 中覆盖
- `mat-2a4589` | goldman_sachs_pdd_research_2026.md | addresses=[K1,K4,K5,K2] | rings=[consensus,valuation-anchor,bull-bear,biz-moat-unit-econ] | high/bull | Goldman Sachs Buy, $145 目标价（Q1 2026 earnings 后从 $158 下调）
- `mat-2ab8a2` | eu_dsa_temu_fine_200m_detailed.md | addresses=[K1] | rings=[bull-bear,historical-mirror] | high/neutral | €200M (~$232M) 罚款：DSA 史上第二大罚（仅次于 X 的 €120M in 2025-12）
- `mat-2cf4e0` | 2026-06-04_pdd-holdings-announces-fourth-quarter-2025-and-fis.md | addresses=[K4,K5] | rings=[financial-arc] | medium/neutral | Q4 2025 总收入 ¥123.9B (+12% YoY, vs Q4 2024 ¥110.6B)
- `mat-4d12b0` | sec/2025_PDD_20-F_2026-04-29/item_5_mda.md | addresses=[K2,K4,K5,K3] | rings=[financial-arc,biz-moat-unit-econ,mgmt-capital-alloc,valuation-anchor] | high/neutral | FY2025 收入 ¥431.8B (+9.7% YoY): Online marketing ¥217.8B (+10.0%), Transaction services ¥214.1B (+9.3…
- `mat-57266c` | morgan_stanley_jpmorgan_pdd_2026.md | addresses=[K4,K5,K1] | rings=[consensus,valuation-anchor,bull-bear] | high/neutral | Morgan Stanley Overweight, $129 (从 $148 下调)
- `mat-5c37f7` | 2026-06-04_temu-loses-more-than-half-of-daily-us-users-but-li.md | addresses=[K2] | rings=[bull-bear] | medium/bear | 标题表明 Temu 美国 DAU 下降超过 50%
- `mat-6f8015` | 2026_PDD_6-K-earnings_2026-05-28.htm | addresses=[K4,K5,K2,K3] | rings=[financial-arc,biz-moat-unit-econ,mgmt-capital-alloc] | high/neutral | Q1 2026 总收入 ¥106.2B ($15.4B) (+11% YoY, vs Q1 2025 ¥95.7B)
- `mat-92c2b6` | 2026-06-04_eu-de-minimis-reform-impact-on-cross-border-ecomme.md | addresses=[K1,K2] | rings=[bull-bear] | low/neutral | Marketplace Universe EU de minimis 改革分析
- `mat-ae2252` | pdd_independent_deep_research.md | addresses=[K1,K4,K5,K2] | rings=[bull-bear,valuation-anchor,consensus] | high/bear | 纵横研报 评级: 观察 (Hold), 合理买入价 ≤$65 (当前 $87.55 → "可以持有"但非买入区间)
- `mat-ae25dd` | 2026-06-04_pdd-holdings-20-f-annual-report-2025.md | addresses=[K4,K5] | rings=[financial-arc] | low/neutral | 已被自动切片为 sec-section 子条目 (mat-00c2f5/mat-b49d21/mat-4d12b0/mat-0b86da/mat-c7c39f)
- `mat-b49d21` | sec/2025_PDD_20-F_2026-04-29/item_4_business.md | addresses=[K3,K5,K1,K6] | rings=[biz-moat-unit-econ,mgmt-capital-alloc] | high/neutral | FY2025 营收 ¥431,845.7M ($61.8B)，同比 +9.7%（从 FY2024 ¥393.8B）；净利润 ¥97,842.5M ($14.0B)，同比 -13.0%
- `mat-b6c953` | 2026-06-04_pdd-holdings-q1-2026-earnings-call-transcript.md | addresses=[K1,K2,K3,K5] | rings=[mgmt-capital-alloc] | low/neutral | Investing.com Q1 2026 earnings call transcript
- `mat-c77d22` | 2026-06-04_china-ecommerce-market-data---business-of-apps.md | addresses=[K3] | rings=[biz-moat-unit-econ] | low/neutral | BusinessOfApps 中国电商市场数据
- `mat-c7c39f` | sec/2025_PDD_20-F_2026-04-29/item_18_financial.md | addresses=[K4,K5] | rings=[valuation-anchor] | low/neutral | Item 18 仅为指针：完整审计报告在 20-F 末尾（未切片到此文件）
- `mat-ddcb99` | 2026-06-04_china-e-commerce-market-report---mordor-intelligen.md | addresses=[K3] | rings=[biz-moat-unit-econ] | low/neutral | Mordor Intelligence 中国电商市场报告
- `mat-f66988` | chinese_broker_pdd_consensus_2026.md | addresses=[K1,K3,K4,K5] | rings=[consensus,valuation-anchor,bull-bear] | high/bull | 一致目标价 ~$122.71（当前 $87.55 → 隐含上行 ~40%）
- `mat-faeb8f` | 2026-06-04_pdd-holdings-investor-relations.md | addresses=[K5] | rings=[mgmt-capital-alloc] | low/neutral | PDD Holdings IR 官方页面入口
- `mat-fb9065` | china_ecommerce_market_share_2025.md | addresses=[K3] | rings=[biz-moat-unit-econ,bull-bear] | medium/neutral | GMV 份额 (2025, BXTData/36Kr 口径): 天猫 31-39% / 京东 16-25% / 拼多多 8-19% / 抖音 14-24%

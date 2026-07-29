# Findings Index — us-nvidia/opus4.8

> 主 agent 调度提示：写每批 output 前重读本文件，按 addresses(K# 脊柱) + rings(决策链输入合同) 判断 context 是否覆盖所需维度；
> 记忆模糊的 mat_id 单独 Read `outputs/findings_{mat_id}.md` 补回。

## 自有 findings（31 份）

- `mat-211826` | 2026-07-23_nvidia-nasdaqgs-nvda-stock-forecast-analyst-predic.md | addresses=[K6] | rings=[consensus,valuation-anchor] | medium/bull | [SimplyWall.st][预测][NVDA盈利&营收增速][+22.8%(年化)]
- `mat-2e1732` | sec/2026_NVDA_10-K_2026-02-25/item_1_business.md | addresses=[scope,K2,K3,K5] | rings=[biz-moat-unit-econ,peer-comparison-financials] | high/neutral | [10-K FY2026][业务全景] 两大报告分部：Compute & Networking（数据中心+网络+汽车）+ Graphics（GeForce游戏、RTX工作站）。四大终端市场：数据中心、…
- `mat-3644ae` | sec/2026_NVDA_10-Q_2026-05-20/item_1a_risk.md | addresses=[risk,K1,K2,K5,K6] | rings=[bull-bear,historical-mirror] | high/neutral | [10-Q Q1FY27][K2 ASIC 升级措辞] 竞争风险因子新增明确表述："部分客户正在自研ASIC及其他产品，针对特定workload优化、可能不需要我们数据中心系统的全部功能特性"——较1…
- `mat-469616` | sec/2026_NVDA_10-K_2026-02-25/item_8_financial.md | addresses=[valuation] | rings=[-] | low/neutral | [10-K FY2026][空章节] 本切片仅含指引性文字："所需信息见本10-K内合并财务报表及附注"，无实际财务数据表。实际FY2026财务数据见MD&A(mat-a048c7)。
- `mat-495eaa` | 2026-07-23_wall-street-s-most-watched-researcher-just-predict.md | addresses=[K6] | rings=[consensus,valuation-anchor] | medium/bull | [Yahoo Finance][Q1 FY2027][NVDA non-GAAP摊薄EPS(实际)][$1.87 vs 预期$1.77(超预期+5.6%)]
- `mat-5f3287` | 2026-07-23_big-tech-s-725b-ai-capex-in-2026-up-77-from-2025.md | addresses=[K1] | rings=[capex] | medium/bull | [valueaddvc][2026年][四大超大厂(MSFT/AMZN/GOOGL/META)合计AI基础设施capex][$725B]
- `mat-64ffdb` | 2026-07-23_nvidia-corp-nvda-forecast-price-target-analyst-rat.md | addresses=[K6] | rings=[consensus,valuation-anchor] | medium/neutral | [Chartmill][下一次财报(应为Q2 FY2027)][EPS一致预期][$2.12]
- `mat-6787a2` | 2026-07-23_nvidia-nvda-share-buybacks---current-historical-da.md | addresses=[K6] | rings=[mgmt-capital-alloc] | high/neutral | [Financecharts][截至 2026-04-26 期间][NVDA 回购金额][$19.312 billion（单期/季度量级）]
- `mat-6a2059` | 2026-07-23_amd-unveils-instinct-mi400-and-mi500-to-challenge.md | addresses=[K2] | rings=[peer-comparison-financials] | low/neutral | [theoutpost.ai][2026][AMD 产品线] AMD 发布 Instinct MI400 与 MI500 两代加速器（标题级，snippet 正文为空）
- `mat-6e3eea` | 2026-07-23_nvidia-corporation-nvda---the-henry-fund.md | addresses=[K1,K6] | rings=[consensus] | medium/bull | [Henry Fund][报告目标价][NVDA target $152][评级 BUY]
- `mat-7205ca` | 2026-07-23_nvidia-stock-analysis-2026-is-nvda-still-a-buy-for.md | addresses=[K1,K6] | rings=[consensus] | low/neutral | [Intellectia.ai][2026][$20T 情景条件][需 NVDA 维持/扩大市场份额，同时 AI 市场扩至约 $3–4 trillion]
- `mat-74ec46` | sec/2026_NVDA_10-Q_2026-05-20/item_1_financial.md | addresses=[valuation,K1,K4,K5] | rings=[valuation-anchor,mgmt-capital-alloc,biz-moat-unit-econ] | high/neutral | [10-Q Q1FY27][业绩] 季度(截至2026-04-26)营收$81.6B、毛利$61.2B(GM 74.9%)、营业利润$53.5B、净利$58.3B、摊薄EPS $2.39(vs 去年$…
- `mat-960d53` | sec/2026_NVDA_10-K_2026-02-25/item_7a_quant_risk.md | addresses=[risk,K2] | rings=[-] | medium/neutral | [10-K FY2026][市场风险] 上市股权投资10%下跌将使公允价值减少$1.8B(FY2026末) vs FY2025几乎为0——反映公司股权投资敞口从无到有快速膨胀(Intel等)。
- `mat-9c7086` | 2026-07-23_custom-silicon-inflection-2026-introl-blog.md | addresses=[K2] | rings=[bull-bear] | low/bear | [Introl blog][2026][主题定性] 命题为"定制硅拐点(Custom Silicon Inflection Point)"——超大厂 ASIC 于 2026 年正面挑战 NVIDIA …
- `mat-a048c7` | sec/2026_NVDA_10-K_2026-02-25/item_7_mda.md | addresses=[K1,K2,K4,K5,valuation] | rings=[valuation-anchor,mgmt-capital-alloc,biz-moat-unit-econ] | high/neutral | [10-K FY2026][业绩] FY2026(截至2026-01-25)营收$215.9B(+65%)；毛利率71.1%(vs 75.0%，-3.9pt)；营业利润$130.4B(+60%)；净利…
- `mat-a1ff4a` | 2026-07-23_amd-previews-instinct-mi400-series-helios-ai-rack.md | addresses=[K2] | rings=[peer-comparison-financials] | low/neutral | [Phoronix][2026][AMD 产品] AMD 预览 Instinct MI400 系列加速器（标题级，snippet 正文为空）
- `mat-b818ba` | 2026-07-23_hyperscaler-custom-ai-chips-in-2026-trainium-3-go.md | addresses=[K2] | rings=[bull-bear,peer-comparison-financials] | low/bear | [Spheron blog][2026][NVDA 推理份额预测] 声称 NVIDIA 推理(inference)份额将从 ~90% 下滑至 2028 年约 20-30%（激进空头口径，未见测算过程）
- `mat-c138a5` | 2026-07-23_nvidia-and-the-cautionary-tale-of-cisco-systems.md | addresses=[K6,K1] | rings=[historical-mirror] | medium/bear | [Harding Loevner][1995-2000][Cisco 营收增长][+850%，从约 US$2B 增至 US$19B（5年）]
- `mat-c1a75f` | sec/2026_NVDA_10-Q_2026-05-20/item_2_mda.md | addresses=[K1,K2,K4,K5,valuation] | rings=[valuation-anchor,biz-moat-unit-econ] | high/neutral | [10-Q Q1FY27][业绩] 营收$81.6B，同比+85%、环比+20%；GM 74.9%(环比-0.1pt、同比+14.4pt)；营业利润$53.5B(同比+147%)；净利$58.3B(同…
- `mat-c425c0` | 2026-07-23_the-ai-deep-dive-the-rise-of-the-custom-silicon-p.md | addresses=[K2] | rings=[-] | low/neutral | [Outperforming the Market (Substack)][2026][主题] 系列深度第 3 部分，主题为"定制硅崛起(The Rise Of The Custom Silicon)…
- `mat-cfcbc6` | 2026-07-23_nvidia-2023-vs-cisco-1999-will-history-repeat.md | addresses=[K6,K1] | rings=[historical-mirror] | medium/bear | [Morningstar][2000-03-27][Cisco 股价峰值][约 $80（£63.66）]
- `mat-d0bfc5` | sec/2026_NVDA_10-K_2026-02-25/item_1a_risk.md | addresses=[risk,K1,K2,K5,K6] | rings=[historical-mirror,mgmt-capital-alloc,bull-bear] | high/neutral | [10-K FY2026][K1 capex命门] 明确将"数据中心、能源、资本可得性"列为客户/伙伴AI基建buildout的关键约束；扩能源是多年期复杂工程；资本市场对欠资本化公司(如Neoclo…
- `mat-d6214a` | 2026-07-23_nvidia-s-80-billion-stock-buyback-and-bigger-divid.md | addresses=[K6] | rings=[mgmt-capital-alloc] | high/bull | [Yahoo Finance][2026][新增回购授权][$80 billion 新回购计划]
- `mat-d98abd` | 2026-07-23_microsoft-meta-and-google-just-silenced-ai-spendin.md | addresses=[K1] | rings=[capex] | medium/bull | [Stocktwits][最新财报季][Google上调2026 capex指引][+$5B]
- `mat-db8e5d` | 2026-07-23_meta-microsoft-amazon-and-alphabet-are-about-to-sp.md | addresses=[K1] | rings=[capex] | medium/bull | [Yahoo Finance][2026年][GOOGL/AMZN/MSFT/META合计capex计划][$725B]
- `mat-e439b9` | 2026-07-23_microsoft-and-meta-earnings-previews.md | addresses=[K1] | rings=[capex] | medium/neutral | [S&P Global Market Intelligence][2026年(4月preview)][相关科技厂商合计capex一致预期同比增量][近+$250B]
- `mat-ea3a1f` | 2026-07-23_nvidia-s-20-trillion-thesis-is-intact-my-2026-allo.md | addresses=[K1,K6] | rings=[consensus] | medium/bull | [I/O Fund][2026][NVDA 市值目标][$20 trillion 论点重申]
- `mat-ed0097` | sec/2026_NVDA_10-Q_2026-05-20/item_3_quant_risk.md | addresses=[risk,K2] | rings=[-] | medium/neutral | [10-Q Q1FY27][股权敞口翻倍] 上市股权10%下跌将使公允价值减少$3.9B(截至2026-04-26) vs $1.8B(2026-01-25)——一个季度内股权投资市场敞口翻倍以上。
- `mat-f39ae9` | 2026-07-23_nvda-nvidia-corp-analyst-estimates-ratings.md | addresses=[K6] | rings=[consensus,valuation-anchor] | medium/bull | [WSJ][当前][NVDA FY2028 EPS一致预期][$12.75]
- `mat-f3c93c` | 2026-07-23_nvidia-just-like-cisco-in-2000-nvda.md | addresses=[K6,K1] | rings=[historical-mirror,consensus] | medium/bear | [Seeking Alpha][2000-03 峰值][Cisco PE][约 200× earnings]
- `mat-f76641` | 2026-07-23_nvidia-to-return-1-billion-to-shareholders-in-curr.md | addresses=[K6] | rings=[mgmt-capital-alloc] | low/neutral | [NVIDIA IR 新闻稿][历史(疑早年)][当年股东回报计划][返还 $1 billion 给股东]

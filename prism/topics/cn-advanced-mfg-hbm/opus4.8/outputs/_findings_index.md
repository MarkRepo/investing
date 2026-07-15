# Findings Index — cn-advanced-mfg-hbm/opus4.8

> 主 agent 调度提示：写每批 output 前重读本文件，按 addresses(K# 脊柱) + rings(决策链输入合同) 判断 context 是否覆盖所需维度；
> 记忆模糊的 mat_id 单独 Read `outputs/findings_{mat_id}.md` 补回。

## 自有 findings（28 份）

- `mat-080ac4` | 2026-07-02_借长鑫科技东风把存储讲透-长鑫招股书深度.md | addresses=[K2,K5] | rings=[arena-mirror,biz-moat-unit-econ,biz-value-chain-position] | high/neutral | [长鑫招股书][2026Q1][长鑫财务][营收508亿，归母净利247.62亿]
- `mat-20fbcc` | 2026-07-02_中芯横纵深度-战略重要生意薄价格贵-纵横-现价hk-86合理-hk-42.md | addresses=[K1,K4,K5] | rings=[valuation-anchor,consensus,peer-comparison-financials,arena-mirror,bull-bear,biz-value-chain-position] | high/bear | [纵横深度][FY25][中芯营收]93.3亿美元
- `mat-2307da` | 2026-07-02_澜起科技2026年第一季度报告-官方.md | addresses=[K3,K5] | rings=[biz-moat-unit-econ,biz-value-chain-position,winner-variables] | high/neutral | [澜起官方][2026Q1][营收][14.61亿, +19.5%]（单季新高）
- `mat-29e511` | 2026-07-02_澜起深度-内存互连全球龙头发力ai运力-开源证券.md | addresses=[K3,K5] | rings=[biz-moat-unit-econ,biz-value-chain-position,winner-variables,valuation-anchor,consensus] | high/bull | [开源证券][2026-05][内存接口2025营收][51.39亿, +53.43%]
- `mat-2b3a57` | 2026_002156_quarterly_2026-04-29_通富微电.PDF | addresses=[K3] | rings=[biz-moat-unit-econ,peer-comparison-financials] | medium/neutral | [通富2026Q1季报][2026Q1][营业收入]74.82亿元，同比+22.80%（增速较2025全年16.92%加速，中高端产品放量）。
- `mat-2d0527` | 2026_600584_quarterly_2026-04-28_长电科技.PDF | addresses=[K3] | rings=[biz-moat-unit-econ,winner-variables] | high/bull | [长电26Q1季报][2026Q1][营业收入]91.71亿元，同比-1.76%。
- `mat-3d9a5f` | 2025_688629_annual_2026-04-14_华丰科技.PDF | addresses=[K3,K5] | rings=[biz-moat-unit-econ,mgmt-capital-alloc,biz-value-chain-position,winner-variables,peer-comparison-financials,bull-bear] | high/neutral | [2025年报][2025FY][总营收] 25.28亿元（2,527,729,770.66元），同比+131.50%（上年10.92亿元）——AI服务器/数据中心+新能源汽车三重驱动。
- `mat-47d25e` | 2026-07-02_澜起深度-retimer全球前二cxl可期-国海证券.md | addresses=[K3,K5] | rings=[biz-moat-unit-econ,valuation-anchor,consensus,peer-valuation-anchor,winner-variables,bull-bear] | high/bull | [国海证券][2025-11][内存互连全球市占][36.8% (2024)]
- `mat-4fa915` | 2025_002436_annual_2026-04-24_兴森科技.PDF | addresses=[K3,K5] | rings=[biz-moat-unit-econ,mgmt-capital-alloc,biz-value-chain-position,winner-variables,peer-comparison-financials,bull-bear] | high/neutral | [兴森2025年报][2025][总营收][71.95亿元(7,194,624,804.67元),同比+23.68%]
- `mat-6616e5` | 2026-07-02_ai芯片先进封装-hbm-测试深度-复合瓶颈-纵横研报.md | addresses=[K3,K4] | rings=[biz-value-chain-position,winner-variables,bull-bear] | medium/neutral | [纵横研报][2026][AI芯片复合瓶颈定位][高端HBM + CoWoS/大尺寸封装 + N3/HBM base die + 测试探针 四环复合稀缺]
- `mat-717b7c` | 2025_688008_annual_2026-03-30_澜起科技.PDF | addresses=[K3,K5] | rings=[biz-moat-unit-econ,mgmt-capital-alloc,biz-value-chain-position,winner-variables,peer-valuation-anchor,bull-bear] | high/neutral | [年报][2025FY][营收][54.56亿元，YoY+49.94%；净利22.36亿元(归母)，YoY+58.4%；扣非净利20.22亿元，YoY+62.0%；净利率41.0%(+2.2pct)]…
- `mat-745d0f` | 2026-07-02_中芯-688981-再上新台阶-中邮证券-26q1点评.md | addresses=[K1,K4,K5] | rings=[consensus,peer-comparison-financials,winner-variables,biz-value-chain-position,bull-bear] | high/bull | [中邮2026-05][26Q1][营收]25.05亿美元(环比+0.7%)
- `mat-746a53` | 2026-07-02_澜起25年报点评-国元证券-目标价152-30-pe26-64x.md | addresses=[K3,K5] | rings=[biz-moat-unit-econ,valuation-anchor,consensus,winner-variables,biz-value-chain-position,bull-bear] | high/bull | [国元证券][2026-04][澜起2025营收][54.56亿, +49.94%]
- `mat-753e59` | 2026-07-02_长电高端封装提速-cpo样品出货-玻璃基板fcbga突破-爱集微.md | addresses=[K3] | rings=[biz-value-chain-position,winner-variables] | medium/bull | [爱集微][2026][CPO进度]CPO产品(XDFOI硅光引擎)已完成客户样品交付并通过验证（与年报一致，交叉印证）。
- `mat-990889` | 2026-07-02_cowos-3d封装技术交流-君实财经-梯队-良率-产能.md | addresses=[K3] | rings=[biz-value-chain-position,winner-variables,peer-comparison-financials,bull-bear] | medium/bull | [163/君实财经][2026][国产CoWoS梯队排序][通富微电 > 长电 > 盛合晶微]
- `mat-9b6657` | 2026_002436_quarterly_2026-04-24_兴森科技.PDF | addresses=[K3] | rings=[biz-moat-unit-econ,peer-comparison-financials,bull-bear] | medium/neutral | [兴森2026Q1季报][2026Q1][营业收入][18.18亿元(1,818,166,949.77元),同比+15.10%]
- `mat-a97cd1` | 2026-07-02_长鑫把中国半导体带进-重工业时代-网易-逻辑与常识.md | addresses=[K2] | rings=[biz-value-chain-position,winner-variables,arena-mirror] | medium/bull | [网易/逻辑与常识][2024初→2025底][长鑫三厂DRAM产能][10万片/月→28-30万片/月满产]
- `mat-ab6480` | 2026-07-02_中芯深度-受益本土崛起-国信证券-合理75-78-86-61港元.md | addresses=[K1,K4,K5] | rings=[consensus,valuation-anchor,peer-comparison-financials,winner-variables] | high/bull | [国信2026-03][地位][全球代工]第三
- `mat-b487ac` | 2025_002156_annual_2026-04-16_通富微电.PDF | addresses=[K3,K5] | rings=[biz-moat-unit-econ,mgmt-capital-alloc,biz-value-chain-position,winner-variables,peer-comparison-financials,bull-bear] | high/neutral | [通富2025年报][2025FY][营业收入]279.21亿元（27,921,424,656元），同比+16.92%。
- `mat-bd53c5` | 2025_600584_annual_2026-04-09_长电科技.PDF | addresses=[K3,K5] | rings=[biz-moat-unit-econ,mgmt-capital-alloc,biz-value-chain-position,winner-variables,peer-comparison-financials] | high/neutral | [长电2025年报][2025][营业收入]388.71亿元，同比+8.09%。
- `mat-c06719` | 2026_688008_quarterly_2026-04-27_澜起科技.PDF | addresses=[K3,K5] | rings=[biz-moat-unit-econ,biz-value-chain-position,winner-variables,peer-valuation-anchor,bull-bear] | high/neutral | [季报][2026Q1][营收][14.61亿元，YoY+19.51%；毛利率69.8%(+9.3pct)，创单季历史新高]。营收增速较2025全年(+50%)明显放缓，但毛利率大幅跳升。
- `mat-c2ec5a` | 2026_688981_quarterly_2026-05-14_中芯国际.PDF | addresses=[K4,K5] | rings=[biz-moat-unit-econ,biz-value-chain-position,peer-comparison-financials,arena-mirror] | high/neutral | [中芯2026Q1季报][2026Q1][营收/净利]营业收入17,617.2百万元(同比+8.1%)；归母净利1,361.2百万(同比+0.4%，几乎零增长)；利润总额1,763.9百万(同比-28…
- `mat-d0b3dd` | 2026-07-02_长鑫拟2027量产12层hbm3e-差距缩至2-3年-腾讯-cnmo.md | addresses=[K2] | rings=[winner-variables,biz-value-chain-position,arena-mirror] | medium/bull | [腾讯/CNMO][—][HBM3现状][已推HBM3样件供华为等，处"量产前验证"阶段]——三级跳定位：送样→(验证中)→量产
- `mat-d1c9db` | 2026-07-02_长电78亿落子临港-高端封测扩产-ofweek.md | addresses=[K3] | rings=[biz-value-chain-position,winner-variables,mgmt-capital-alloc] | medium/bull | [OFweek][2026-06][临港扩产]长电78亿元落子上海临港，纯高端封测厂，占CapEx约78%，计划2028年下半年投产，规划高端产能利用率>90%满载。
- `mat-d57d3d` | 2026-07-02_国产hbm3突破-长鑫向华为交付hbm3样品-与非网.md | addresses=[K2] | rings=[biz-value-chain-position,winner-variables] | medium/bull | [与非网][—][长鑫HBM3客户][向华为交付HBM3样品，集成于昇腾910C]——三级跳中的"送样"级已确认，对象=昇腾910C
- `mat-e654e9` | 2025_688981_annual_2026-03-26_中芯国际.PDF | addresses=[K4,K5] | rings=[biz-moat-unit-econ,mgmt-capital-alloc,biz-value-chain-position,peer-comparison-financials,winner-variables] | high/neutral | [中芯2025年报][2025FY][营业收入]人民币67,323.2百万元，同比+16.5%（上年57,795.6百万）
- `mat-ed7074` | 2026_688629_quarterly_2026-04-27_华丰科技.PDF | addresses=[K3,K5] | rings=[biz-moat-unit-econ,peer-comparison-financials,peer-valuation-anchor,winner-variables,bull-bear] | high/neutral | [2026Q1季报][2026Q1][营业收入] 6.33亿元（633,223,075元），同比+56.15%（上年同期4.06亿元）——AI服务器/数据中心需求延续+防务重点项目交付。
- `mat-f729d8` | 2026-07-02_中芯国际-0981-hk-深度-扩产与先进制程突破-m8.md | addresses=[K1,K4,K5] | rings=[winner-variables,biz-value-chain-position,valuation-anchor,peer-comparison-financials] | medium/bear-leaning-neutral | [m8深度][FY25][中芯营收]~81亿美元(+27% YoY) — 注: 低于其余三份93亿口径

## 父级复用 findings（5 份）

- `mat-bcc950` | 2026_昇腾产业链拆解_供应链国产化率.md | addresses=[K1,K2,K3] | rings=[migration-path-evidence,value-chain-profit-pool] | high/neutral | [香农研究院/SemiAnalysis][2026-05][晶圆制造国产化率] 台积电占比 80%——昇腾 910B/910C 绝大多数仍用台积电 7nm；华为经算能 Sophgo 采购约 5 亿美元… (parent=cn-ai-compute)
- `mat-1d1f97` | 2026_半导体国产替代历史镜鉴_面板存储.md | addresses=[K4,K5] | rings=[historical-mirror,industry-mirror] | high/neutral | [TechNews/2026-04-23][京东方][全球显示面板市占] 约 25%，营收逼近 300 亿美元，但利润率仅约 2.7%，净利始终无法有意义增长。 (parent=cn-ai-compute)
- `mat-9bbdca` | 2026_华为资本配置与战略史_mgmt_capital_alloc.md | addresses=[K1] | rings=[mgmt-capital-alloc] | high/bull | [华为2025年报][研发投入] 2025 研发投入 1923 亿、占销售收入 21.8%；经营现金流 1274 亿(+44%)；销售收入 8809 亿、净利润 680 亿、营业利润率 11.0%。 (parent=cn-ai-compute)
- `mat-27eea4` | 2026_算力链估值锚_consensus_PE_PS_市值横向对比.md | addresses=[K4,K5] | rings=[consensus,leader-valuation-anchor,peer-comparison-financials] | high/neutral | [东方财富/2026-05-06][寒武纪 688256][估值锚] 市值 ~5600-8288 亿、2025 净利 20.59 亿、PE(TTM) 154~305x、2026E PE 63~154x… (parent=cn-ai-compute)
- `mat-f3c41b` | 2026_智算中心利用率_回报模型_过剩.md | addresses=[K1] | rings=[historical-mirror,arena-scoring-inputs] | high/bear | [36氪智能涌现][2026-05-21][利用率] 机房出租率普遍 20-30%，企业级智算中心甚至仅 10% 左右；部分国产算力利用率不足 20%。 (parent=cn-ai-compute)

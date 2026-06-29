# Findings Index — global-roller-screw/glm5.2

> 主 agent 调度提示：写每批 output 前重读本文件，按 addresses(K# 脊柱) + rings(决策链输入合同) 判断 context 是否覆盖所需维度；
> 记忆模糊的 mat_id 单独 Read `outputs/findings_{mat_id}.md` 补回。

## 自有 findings（4 份）

- `mat-228d8e` | 2023-09_开源证券_丝杠直线传动精密部件.pdf | addresses=[K2,K3,K4,K5] | rings=[consensus,mgmt-capital-alloc,arena-mirror,biz-moat-unit-econ,peer-comparison-financials,bull-bear] | high/bull | [开源证券 2023.09][市场规模] 2023 年国内丝杠市场 173 亿元，2030 年达 747 亿元（扩大 4.3 倍）。拆分：汽车 75.8→389 亿（5.1 倍）、机床 97→190.…
- `mat-4aa49d` | 2026-06-23_与非网_六万美元Optimus中国供应商.md | addresses=[K1,K5] | rings=[winner-variables,peer-valuation-anchor,biz-value-chain-position] | high/neutral | [与非网 2026-06-23][Counterpoint V3供应链报告] 特斯拉已搭建成熟人形机器人供应体系，超 10 家中国供应商进入 Optimus V3 供应链：拓普集团、三花智控、旭升集团…
- `mat-8241d9` | 2024-03_华鑫证券_行星滚柱丝杠高精技术集成.pdf | addresses=[K2,K4,K5] | rings=[consensus,biz-moat-unit-econ,peer-comparison-financials,bull-bear] | medium/bull | [华鑫 2024-03][Tesla Optimus] 单台 14 个 PRS，单价约 2000 元/个，单台价值量 2.8 万元，PRS 占人形机器人核心部件成本约 15%，毛利率可达 60%
- `mat-91c1f1` | 2023-07_华金证券_行星滚柱丝杠卡脖子零件.pdf | addresses=[K1,K5] | rings=[consensus,biz-value-chain-position,winner-variables] | medium/bull | [华金证券 2023.07][Tesla Optimus] 推测单台机器人用到 14 个线性执行器，均采用倒置（反式）行星滚柱丝杠；躯干共 28 个关节（旋转/直线各 14），手部另有 12 个执行器…

## 父级复用 findings（6 份）

- `mat-5bd1f9` | 2026-01-29_TSLA_10-K_2025-12-31_optimus_excerpts.md | addresses=[K1,K2] | rings=[migration-path-evidence] | medium-high/官方法律披露口径，系统性保守/forward-looking 免责；关键词命中片段集(命中77/全文429673字符) | Optimus 定位："a general purpose, autonomous humanoid robot in development"，归入"AI robots(Bots)"，与 FSD/R… (parent=global-humanoid-robot)
- `mat-c5a73f` | Tesla 10-Q Q1 FY2026（2026-04-23 提交，季度截至 2026-03-31）Optimus 摘录 | addresses=[K1,K2] | rings=[migration-path-evidence] | low/company-issued，发行人自述乐观措辞；关键词命中片段集，10-Q对Optimus着墨极少 | Optimus 仍处"大规模量产前的准备与投资"——"advance the development of Optimus...as we make preparations and investme… (parent=global-humanoid-robot)
- `mat-215f5f` | 中国信通院 人形机器人产业发展研究报告(2024年) | addresses=[K5,K6] | rings=[value-chain-profit-pool,arena-scoring-inputs] | medium-high/官方智库/政策导向，宏观定调权威但缺二级市场利润池量化与个股竞争结构 | 产业链结构定调（权威）：上游核心硬件=减速器、电机、丝杠、控制器、传感器。报告明确"当前传感器、减速器、电机和丝杠等核心零部件的价值占比较高，增量空间显著"。[value-chain-profit-p… (parent=global-humanoid-robot)
- `mat-529f3d` | 前瞻产业研究院 2025 人形机器人产业发展蓝皮书（聚焦量产及商业化关键挑战） | addresses=[K1,K5] | rings=[migration-path-evidence,value-chain-profit-pool] | medium/招商咨询机构，倾向乐观叙事；风险量化偏弱 | 量产时间表(海外)：特斯拉预计2026年开始对外大规模量产；Optimus二代2024.6已在厂做电池分拣训练。[K1] (parent=global-humanoid-robot)
- `mat-0d452c` | 华泰证券 雷赛智能(002979) 首次覆盖——运动控制老将，人形机器人新星 | addresses=[K3,K6] | rings=[arena-scoring-inputs] | high/bull | 首次覆盖"买入"，目标价 58.48元；报告日(2025-08-08)收盘 47.97元，隐含 +22%。市值 150.69亿。52周区间 18.49–53.86（报告时已处高位）。 (parent=global-humanoid-robot)
- `mat-ac86a8` | 人形机器人行业点评——情绪向左，产业向右（2025.11） | addresses=[K4] | rings=[leader-valuation-anchor] | high/sell-side-bullish（行业"看好"，强多头叙事；估值水位偏定性） | 板块当周跑输：人形核心公司指数当周 -4.13%；沪深300 -1.08%、科创50 -3.85%、申万机械 -2.22%。板块跌幅最大。 (parent=global-humanoid-robot)

# 决策链输入合同（A 层 · prose 版）

> 与 `prism/scripts/input_contract.py` **同源维护**——改一处必须改另一处，且回溯到三条 case 路径
> （`04-synthesize/_company_case.md` / `_industry_funnel.md` / `_arena_funnel.md`）§3.2【必带硬落地】。
> 本文件给 **LLM 读**（收料/抽料/gap 时对照）；`.py` 给脚本读（gap_detector 双轴）。

## 它是什么

合成层 6 环决策链每一环都有【必带硬落地】（不可省的决策机制保证）。把这些"要落地什么"
**反投影到输入**，就得到"上游必须供给哪几类资料/数据"——这就是输入合同。

- **type 常量、不依赖具体标的**：研究任何 company/industry/arena 之前就已知，**无循环依赖**。
  （命门特化深度是 B 层 `decomposition_v{N}.md`，知识驱动、迭代，不在此。）
- 与 thesis 的 **K# 解耦**：K# 走 `addresses` 字段（thesis 脊柱）；合同项走 `rings` 字段（输入脊柱）。
- **训练知识不计覆盖**：合同项只认实收料 / API；缺料只能标"训练知识估算"或"数据缺失"，不冒充。
- **三项真·欠供**（标 `hard`，旧流程从不产出，收料须显式排期）：管理层/资本配置史、一致预期/估值锚、历史失败镜鉴。
  可得性受限时（如 A 股前瞻 consensus 在付费墙后）允许诚实降级为 user todo / 数据缺失。

材料/findings 用 `code` 作 `rings` 标签（`add_material(..., rings=[...])`）；
gap ring 轴按每项 `served_by` 查源：实收文件类（material/fetch_report/web/user）查材料 rings；
结构化数据类（financial_data/market_data/smm）查 API/缓存存在性。

---

## company（8 项）

| code | 环 | 必带硬落地（输入投影） | served_by | hard |
|---|---|---|---|---|
| `biz-moat-unit-econ` | ① | 生意模式/收入拆解(量×价×结构)/护城河/单位经济(毛利·单客·ROIC) | material, smm | |
| `mgmt-capital-alloc` | ① | 管理层 track record + 资本配置历史(回购/分红/并购回报) + 激励治理 | material, user | ✅ |
| `financial-arc` | ① | 多年财务弧线(3-5Y 营收/利润率/ROIC/FCF + 拐点) | financial_data | |
| `valuation-anchor` | ② | 当前价/估值倍数反推隐含 CAGR·终值PE·IRR | market_data, material | |
| `consensus` | ② | 卖方一致预期/目标价模型(反推对照基准) | material, user | ✅ |
| `valuation-percentile` | ② | 历史区间 + 全球 peer 估值水位 | market_data, material | |
| `bull-bear` | ④ | 多空论据(喂④期望收益加总) | material, web | |
| `historical-mirror` | ⑤ | 历史失败镜鉴(相似剧本怎么崩) | material, web | ✅ |

## industry（6 项）

| code | 环 | 必带硬落地（输入投影） | served_by | hard |
|---|---|---|---|---|
| `value-chain-profit-pool` | ① | 价值链全貌+利润池定位(谁赚走)+驱动因子+周期位 | material, smm | |
| `industry-financial-arc` | ① | 行业代表主体多年财务弧线(龙头/聚合 3-5Y) | financial_data | |
| `leader-valuation-anchor` | ② | 龙头/细分倍数反推增速 + 相对水位(历史+全球peer) + 叙事资金流 | market_data, material | |
| `migration-path-evidence` | ③ | 利润池迁移路径/结构性假设证据(谁攫取价值·渗透曲线·政策) | material, web | |
| `arena-scoring-inputs` | ④ | 各 arena 6 维评分料(利润池规模/增速/竞争/估值/周期) | material | |
| `industry-mirror` | ⑤ | 历史行业镜鉴(利润没兑现/迁移没发生——电信capex·光伏) | material, web | ✅ |

## arena（5 项）

| code | 环 | 必带硬落地（输入投影） | served_by | hard |
|---|---|---|---|---|
| `biz-value-chain-position` | ① | 怎么赚钱+价值链卡位+路线之争+客户结构+赛道周期位 | material | |
| `winner-variables` | ② | 关键胜负变量(成本曲线/技术代差/客户锁定/规模/牌照) | material, smm | |
| `peer-valuation-anchor` | ② | 被当赢家那几家当前估值(PE/PS 相对赛道·是否透支) | market_data, financial_data, material | |
| `peer-comparison-financials` | ④ | 候选公司横比矩阵(≥5家·收入/ROIC/毛利/负债/PE/历史PE/路线/客户) | financial_data, material | |
| `arena-mirror` | ⑤ | 历史镜鉴(曾经赢家如何被取代——Nokia/Kodak) | material, web | ✅ |

> 环③（company/arena 的 WMBT）、环⑥（行动/漏斗）由前几环 derive，无独立**原始输入**需求，故不列合同项。
> industry/arena 的 `migration-path-evidence` / 假设类证据是例外（迁移路径需独立佐证），单列。

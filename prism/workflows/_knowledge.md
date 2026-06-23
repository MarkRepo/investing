# 投资领域知识（不可压 IP）

> 本文件是 prism 投资框架的**知识库单源**。内容从原 `04-synthesize/` 全部文件逐字搬运去重。
> **禁止改写投资框架/估值模型/机制纠错的实质表述**——重写会引入质量损失。
> 合成时参照本文件 + `_contracts.md`（schema）+ `_arc.md`（不变量）即可，不需要读旧 stage 文档。

---

## 一、六环决策链（参数化骨架 + 三类差异）

> 六环是所有 type 共用的**决策因果序**，环与环之间是逼出关系，不是并列箱。
> 不允许断链（有④无⑤、有⑥无②）。每环必须落地（见各 type 差异节）。
> **chain-critic 必查**：链通不通、目标达成、primer↔case 分工干净、来源分层合法。

### 公共骨架（六环元问题）

```
① 能不能看懂这个标的？           → 这是闸门，看不懂就不下注
② 市场怎么定价？当前锚在哪？     → 脱离定价谈卡位无决策意义
③ 这套定价需要什么为真？         → WWHTBT：把"赢"翻成可证伪前提
④ 我怎么下注？                   → 真正表态：概率×回报 / 横比漏斗
⑤ 错了怎么知道？                 → 证伪机制：kill + 镜鉴 + signpost
⑥ 行动是什么？                   → 收口：买入框/三档漏斗/peer shortlist
```

### 各环公共约束

- **环③ WWHTBT 通用要求**：3-5 条假设，每条具体/可观测/可验证（6 个月内能验证？能=合格）；标当前证据支持度；②定价笃定度 > ③证据强度的缺口 = 最值得盯的卖空/谨慎点
- **环⑤ 历史镜鉴通用要求**：≥2 个案例，每个标：失败模式 + 峰谷损失幅度% + 最早预警信号及"现在是否已现" + 教训一句话；只想到成功案例本身就是 red flag
- **环⑤ signpost 通用要求**：未来 3-12 月验证/证伪事件，直接喂 sidecar signposts 字段
- **来源分层三类**（合成必做）：训练知识不标单条 / findings 凡引必标 `[mat-XXX]` / 特色判断文末指向 thesis_v1

---

### 1. company：六环差异

**环① 理解（company 特有内容）**
- 生意模式：收入拆解（量×价×结构）/ 护城河 / 单位经济（毛利·单客·ROIC）
- 管理层 track record + 资本配置历史（回购/分红/并购回报）+ 激励治理（**hard 资料**）
- 多年财务弧线（3-5Y 营收/利润率/ROIC/FCF + 拐点识别）

**环② 定价锚（company 特有内容）**
- 当前价 / 估值倍数反推隐含 CAGR·终值PE·IRR（= Reverse PE-DCF，见 §二 模型 A）
- 卖方一致预期/目标价（**hard 资料**，作反推对照基准）
- 历史估值区间 + 全球 peer 估值水位（分位判断）

**环③ WWHTBT（company）**
- 公共格式，把"thesis 成立"翻成 3-5 个可观测必要条件
- 关联 K# （每个 K# 应有至少一个 WWHTBT 条件覆盖）

**环④ 下注（company 特有：EV 加总）**
```
期望收益 EV = Σ (概率_i × 情景回报_i)

情景框架（推荐三情景）：
  Bull: 核心假设全实现  → 回报 = {N}%，概率 = {P_bull}
  Base: 核心假设部分实现 → 回报 = {N}%，概率 = {P_base}
  Bear: 核心假设不实现  → 回报 = {N}%，概率 = {P_bear}

EV = P_bull×Bull + P_base×Base + P_bear×Bear
核心分歧一句话：我和市场共识的差异在哪（是 Bull 情景概率还是 Bear 情景幅度？）
```
> ⚠️ EV 加总是**结构化思维工具**，不是精度承诺——概率主观，诚实标注

**环⑤ 证伪（company 特有质量红线）**
> 这些红线是**环⑤ 证伪/kill 诊断内容，不是进 case 前的 quarantine 门控**——用户既已选定研究本公司（默认已过基础调研），红线落地为风险条目 / kill 触发，不自动否决立项（合 F6：诊断非 gate）。
- ROIC vs WACC：ROIC 持续 < WACC = 价值毁灭，无论 PE 多低
- FCF 转化率：净利润 > 0 但 FCF < 0 连续 2Y+ → 盈利质量存疑
- 治理红线：关联交易规模 / 控股股东占款 / 审计师意见
- K# kill switch：任一命中即立刻重评（不是"再观察"）
- 历史失败镜鉴（**hard 资料**，相似剧本怎么崩的）

**环⑥ 行动（company 特有：买入框 + 仓位档）**
- buy_box 四区（强买·累积·持有·高于持有区）+ 对应当前价区间
- 仓位档（三档，`position_tier` 是首要字段）：
  - **试探**：黑箱/低信息/低信心标的，首仓上限 ≤2-3%，论证后加仓
  - **标准**：信息充分 + 信心足，首仓上限 3-5%
  - **重仓**：强确信 + 宽安全边际，首仓上限 >5%
  > ⚠️ `initial_max_pct` 是档位的人工落点，**不是机械算出的**——给不出有依据的数就填 `null`、只留 `position_tier`；禁止用一个拍出来的精确 % 伪装严谨。满仓上限走 `full_max_pct`。
- 加仓阶梯价（`add_ladder_prices`，升序）
- 输出 sidecar：`07_decision_kit.yaml`（见 `_contracts.md` §六）

---

### 2. industry：六环差异

**环① 理解（industry 特有内容）**
- 价值链全貌 + 利润池定位（谁赚走了利润）+ 驱动因子 + 周期位
- 行业代表主体多年财务弧线（龙头/聚合 3-5Y）
- **不评个股**——行业层的①是"利润在哪、谁卡"

**环② 定价锚（industry 特有内容）**
- 龙头/细分估值倍数反推隐含增速（对标 company 的 Reverse PE-DCF）
- 相对历史水位 + 全球 peer 行业水位（哪个子赛道定价最贵/最便宜）
- 叙事资金流：市场资金在吹什么故事进来

**环③ 迁移路径证据（industry 特有）**
- 利润池迁移路径 / 结构性假设证据：谁在攫取价值·渗透曲线·政策加速/阻塞
- **需独立佐证**（不能靠训练知识估算），见 input_contract `migration-path-evidence`

**环④ 下注（industry 特有：arena 6维评分）**

6维评分口径（**1-5 标度**，详见 §五；sidecar `industry_to_arenas.yaml` 同标度）：
- `profit_pool`（1-5）：利润池规模 + 护城河深度
- `growth`（1-5）：行业成长率 + 渗透空间
- `competition`（1-5）：竞争集中度（反向：越集中越高分）
- `valuation`（1-5）：当前估值相对性价比（反向：越低估越高分）
- `cycle`（1-5）：周期位有利程度（向上拐点期高分）
- `composite`（1-5，float）：加权综合（权重由命门判断）

每个 arena 出评分 + tier（deep/watch/eliminated）+ tier_reason

**环⑤ 证伪（industry 特有镜鉴）**
- "利润没兑现"镜鉴：电信 capex（运营商投了，但设备商拿走利润）
- "迁移没发生"镜鉴：光伏（产能过剩抹平利润池迁移）
- **行业层镜鉴关注"假设链断在哪一节"**，不是个股失败

**环⑥ 行动（industry 特有：三档 arena 分流）**
- **deep**：利润池足够大 + 竞争格局好 + 估值合理 → 进 arena 深研
- **watch**：有潜力但当前定价透支/竞争未明朗 → 写触发升级条件
- **eliminated**：利润池太小/竞争太散/结构恶化 → 写复活条件（以防时移势易）
- 输出 sidecar：`industry_to_arenas.yaml`（见 `_contracts.md` §六）

---

### 3. arena：六环差异

**环① 理解（arena 特有内容）**
- 怎么赚钱 + 价值链卡位 + 路线之争（是什么，不判胜负）+ 客户结构 + 赛道周期位
- **"路线是什么"归 primer，"哪条路线会赢"归 case**（arena primer↔case 分工边最重要）

**环② 定价锚（arena 特有：被当赢家那几家）**
- 关键胜负变量（成本曲线/技术代差/客户锁定/规模效应/牌照）
- 被当成赢家那几家的当前估值（PE/PS 相对赛道·是否已透支）
- 隐含预期一句话 + **定价笃定度 × 证据强度张力**（市场在为③里哪条最弱假设付溢价？）

**环③ WWHTBT（arena 特有）**
- 把"谁会赢"翻成 3-5 条具体假设（某路线胜出/份额向头部集中/某大客户放量/成本拐点兑现）

**环④ 下注（arena 特有：peer 横比矩阵）**

横比矩阵维度（≥5 家）：
```
| 公司 | 收入规模 | 3Y ROIC | 毛利率 | 资产负债率 | 当前PE | 历史PE区间 | 技术路线 | 客户结构 | 管理层信号 | 综合分 |
```
- 每家挂回③的假设 + 一句话 thesis
- K# 校准：被 K# 翻盘的公司不进 shortlist，K# 强支持的优先
- 已有成稿 company case 的候选用实证替代估算（按 §1.3 标来源 + 本维度复核）
- Hard filter（必须全过）→ 软评分（按命门权重）→ 综合分排序
- 输出 sidecar：`peer_matrix.yaml`（见 `_contracts.md` §六）

**环⑤ 证伪（arena 特有镜鉴）**
- arena 级 kill（路线被颠覆/共识赢家失速/新进入者改写格局）
- 历史镜鉴重点：曾经的赢家如何被取代（Nokia/Kodak/被新路线颠覆的龙头）

**环⑥ 行动（arena 特有：peer shortlist 三档）**
- **shortlist**：卡位好 + 估值合理 → 建 company stub，进 company 深研
- **watch**：卡位好但定价透支 → 写价格触发器（到什么价位进深研）
- **eliminated**：卡位差/路线落败/quarantine → 写复活条件
- tier 判定 = 卡位/质量 × 当前定价（好公司但贵 → 进 watch，不直接深研）

---

## 二、八估值模型

> 来源：`04-synthesize/_valuation_models.md`（逐字搬运）。公司 case 环② 必用，行业/arena 按需引用。

### 估值原型识别 → 选 2-3 个模型

先判原型，再选模型（每模型独立给估值范围，不做交叉验证，并列呈现暴露假设差异）：

| 原型 | 典型特征 | 推荐模型（按优先级） |
|------|---------|-------------------|
| **高 PE 成长/概念股** | PE>50x，增速是核心矛盾，部分价值来自期权 | Reverse PE-DCF ✦、基本盘+期权拆解 ✦、PEG |
| **政府/订单驱动（军工/基建）** | 收入能见度依赖合同/政策，有五年计划周期 | Reverse PE-DCF ✦、五年均值 PE ✦、同业横截面 |
| **成熟平台/现金流** | PE 15-25x，FCF 稳定，资本回报可计算 | Forward DCF ✦、EV/EBITDA 历史分位 ✦、Reverse PE-DCF |
| **周期股/反转股** | 盈利波动剧烈，当前 PE 因低基数可能失真 | Normalized PE ✦、EV/EBITDA 分位 ✦、PB 历史分位 |
| **资产/资源/项目型** | 价值来自资产/储量/在建项目，非当期盈利 | NAV/SOTP ✦、Forward DCF、订单簿×毛利 |
| **银行/保险** | 特殊会计，杠杆驱动 | PB-ROE ✦、DDM ✦、SOTP |

**在产出中明确写出**：
```
估值原型：{原型名称}（判断依据：{2-3 句话}）
选用模型：
  - 模型 A：{名称}（选择原因）
  - 模型 B：{名称}（选择原因）
```

### 模型 A：Reverse PE-DCF（逆向 PE-DCF）
- 输入：当前价 P、当前净利润、折现率 r（默认 10%）、终值 PE（参考同业历史区间）
- 反推：隐含 3-5 年净利润 CAGR
- 输出：「当前 {X}x PE，隐含 5 年 CAGR = {g}%，终值 PE {pe}x，隐含 IRR = {irr}%」
- 表格：终值 PE × CAGR 二维矩阵 → 对应公允值（3×3 或 4×4）

### 模型 B：基本盘 + 期权拆解
- 适用：PE 中有显著部分来自"尚未兑现的期权价值"（如卫星互联网、新产品线）
- 步骤：
  1. 识别已落地业务（基本盘）的合理 PE × 当前净利润 = 基本盘价值
  2. 当前市值 - 基本盘价值 = 期权隐含市场定价
  3. 独立估算期权 NPV：成功概率 × 成功情景净利润 × PE / (1+r)^n
  4. 对比：市场给的期权价格 vs 你算的期权 NPV
- 输出：「基本盘价值 {V1} 元，期权溢价 {V2} 元，你的期权 NPV 估算 {V3} 元 → 期权{高估/低估/合理}」

### 模型 C：Forward DCF（正向现金流折现）
- 适用：FCF 可预测的成熟公司
- 输入：未来 5 年收入/净利率/资本开支预测 → FCF；折现率 WACC；终值增长率 g
- 输出：NPV + 牛/熊情景公允值区间

### 模型 D：EV/EBITDA 历史分位
- 适用：资本密集、折旧大、跨周期对比有意义
- 步骤：取当前 EV/EBITDA，对比过去 5-10 年历史区间 + 全球 peer 中位数
- 输出：「当前 {X}x，历史均值 {Y}x（区间 {low}-{high}x），当前处于历史 {Z}% 分位」

### 模型 E：Normalized PE（周期均值利润法）
- 适用：周期股或反转股（当期利润因基数效应失真）
- 步骤：取过去完整周期（通常 5-8 年）的平均净利润率 × 当前营收 = normalized EPS；合理 PE × normalized EPS = 公允值
- 输出：「Normalized EPS = {X} 元，合理 PE {Y}x，公允值 {Z} 元」

### 模型 F：同业横截面
- 适用：存在 3+ 家估值可比的同业公司
- 步骤：取同业 PE/PS/EV-Sales 中位数，按差异化因素（增速、毛利率、护城河）做折溢价
- 输出：「同业中位 PE {X}x，本公司增速溢价/折价 {±Y}%，对应公允 PE {Z}x → 公允值 {V} 元」

### 模型 G：NAV/SOTP（分部加总法）
- 适用：多业务 / 重资产 / 资源储量型
- 步骤：各业务/资产分别估值 → 加总 → 折价（控股结构/流动性）
- 输出：各部分价值 + 汇总表

### 模型 H：PEG
- 适用：增速对比是核心逻辑，市场在用 PEG 定价
- 步骤：PE / 预期 CAGR；与历史 PEG 均值和同业对比
- 输出：「当前 PEG = {X}（历史均值 {Y}，同业 {Z}）→ {cheap/fair/expensive}」

### 估值矩阵汇总（环② 末尾必给）

```markdown
## 估值矩阵汇总

> 各模型独立运算，不做交叉验证；并列呈现是为了暴露假设差异，而非取平均。

| 模型 | 核心假设 | Bull 公允值 | Base 公允值 | Bear 公允值 |
|------|--------|----------|----------|----------|
| {模型 A 名称} | {最关键的 1 个输入假设} | {元 or 元区间} | {元 or 元区间} | {元 or 元区间} |
| {模型 B 名称} | {最关键的 1 个输入假设} | ... | ... | ... |

**当前价**：{P} 元（{date}）

**模型间主要分歧**：{1-2 句话说明哪个模型给最高/最低，分歧来自哪个假设}
```

---

## 三、宏观四层因果链（macro type 专用）

> 来源：`04-synthesize/_macro_regime.md`（逐字搬运）。**只在 macro type topic 中使用。**
> macro 不做 EV 加总、不选标的，终点是三体制读数 + 每持仓倾斜标签。

### 因果链总纲（L1→L4）

```
[L1 输入源] → [L2 驱动变量]          → [L3 目标·三体制读数]         → [L4 传导·决策]
   数据          增长 / 通胀              利率 / 流动性 / 汇率              每持仓敏感度
              政策反应 / 财政            (各自小框架 + 大白话)             → 仓位/久期倾斜
```

- **左半段 = 输入**：L1 数据源 + L2 驱动变量（增长/通胀/政策反应/财政是利率/流动性的上游输入，央行盯着它们行动）
- **中段 = 传导逻辑**：L3 三体制各有小框架
- **右段 = 决策**：L4 transmission_map 每持仓敏感度 → 组合倾斜

**三体制各自的小框架**：
- **利率体制**：费雪分解（名义=实际+通胀预期）；短端看央行、长端看预期+期限溢价；曲线四形态（牛陡/熊陡/牛平/熊平）。大白话 = 钱的**价格**
- **流动性体制**：央行→银行→市场三层传导；宽货币×宽信用四象限；净流动性 + 信用利差。大白话 = 钱**多不多、愿不愿冒险**
- **汇率体制**：利差→汇率→资本流动套利链；中美 10Y 利差 / DXY / USDCNY / 北向资金。大白话 = 钱往**中国流还是往外跑**

**四条传导渠道（L4）**：贴现率渠道 / 风险偏好渠道 / carry-久期渠道 / 汇率渠道

**地理主线**：美/全球为主线，中国第二块——全球利率总闸门在美国；汇率对 A股/中概组合不可省。primer 与 regime_read 都**先讲美/全球、再单列中国第二节**。

### 机制纠错八条（spec §5，合成时逐条遵循）

> 这是校准红队推翻/修正后的**硬约束**，写 `m_regime_read.md` 时必须照此落，不得回退旧机制：

1. **中美10Y利差 → 人民币贬（carry）**：现 regime 下该链路**断裂/反向因果**（高信）。**A→B**，由因果驱动降为**压力表**（只读不当成因）；人民币真 A 级驱动是**中间价/逆周期因子 + 资本管制 + 贸易顺差**
2. **黄金 = 实际利率 + DXY**：机制过时（高信）。**层级保留 B，但机制改写**——2023-25 黄金与实际利率/DXY **脱钩**（央行购金主导），是更好的**去美元化读数**，**不得再当实际利率代理**
3. **信用利差 OAS**：删去"领先"标签，改标**同步**（高信）
4. **净流动性 → 风险偏好**：A 级**保留但降权**；**SOFR−IORB** 升为 **binding driver**（资金面真正咬合处）；RRP 已基本耗尽（中高信）
5. **核心 PCE/CPI → 利率↑**：维持 A，须**分期限**读（短端正相关/长端可反向）；触发条件用**超预期**（surprise）而非绝对水平
6. **日元 carry**：**A 级保留**，但标为**条件/阈值的尾部触发**（拥挤平仓型），非常态驱动（高信）
7. **DXY → 中国 FX**：改用 **CFETS/广义美元** 指数；DXY 降为 B（DXY 约 57% 是欧元权重）
8. **比特币**：**维持 C**（被利率驱动的相关资产，非独立因果，红队确认）

### 多维读数（合成必做）

- **三体制各自给读数 + 分维信心**（per-dimension confidence 0-10，落 `transmission_map.regime.*.confidence`）
- **增长/通胀象限**（独立于三体制）：复苏 / 过热 / 滞胀 / 衰退（落 `transmission_map.regime.quadrant`）
- **fragility 罚分**：强度分与突变风险反相关——脆弱度由 **利差极窄 + 低波动 + carry 拥挤 + 承重假设数** 构成；high 时明示"**信心X / 脆弱度高**"（落 `transmission_map.regime.fragility`）

### 闭环重估（macro 的质量护城河，每次 regime_read 改版必做）

> macro 是高频重估 type。判断不存档、不对账，就退回"讲故事"。这套闭环让宏观读数**可对账、可打分、随体制变化自动联动持仓**。脚本零 LLM、全在 `eval_snapshot` / `eval_score` / `macro_xcut`，合成/重估时按下面纪律调用——不是可选项。

- **存快照（`eval_snapshot.record_evaluation`）**：每出一版 regime_read，把当时读的输入 + 每条结论落一份带时间戳的快照（`regime_eval_log.yaml`，version 自增、append-only）。`snapshot_inputs` 自动列全 registry 输入（不许手工漏列），结论用 `based_on` 把每条挂到它依赖的输入上。
- **可证伪预测（硬要求，缺则 `record_evaluation` 直接 raise）**：每条**承重边**（`role=load_bearing` 且该输入有数值/stance）必须带 `expected` 方向词（如 利率 `up` / 流动性 `tighten`）。没有方向就无法事后判对错——这是把宏观从玄学变成可打分的关键，校验在 `_validate_evaluation` 强制。
- **战绩对账（`prior_verdict` + `eval_score.score_evaluation` / `edge_ledger`）**：下一版重估时，对上一版每条预测盖章 `held` / `partial` / `wrong`，落在**新**条目上（旧条目不可变）。`edge_ledger` 跨所有版本按 (结论, 输入) 累计命中/落空，老判错的机制边浮成**降级候选**——客观决定哪条机制该降权，而不是拍脑袋。
- **体制变 → 持仓盖戳（`macro_xcut.scan_holding_staleness` / `apply_holding_staleness`）**：某体制读数翻向（如 流动性 宽→紧）时，自动找出所有依赖该体制的持仓，盖 `stale / 待重判` 戳 + 写 proposal（仍 `awaiting_confirm`，人工确认）。防止"宏观变了、具体持仓判断还停在旧体制"。
- **持仓全覆盖（`macro_xcut.coverage_gaps`）**：transmission_map.holdings 必须覆盖**每个现存 company 持仓**——先 `topic.list_topics` 枚举 company-type，再逐个填；缺料标"数据缺失"，漏注册/provisional 被显式暴露（沉默≠确认，合 F1）。
- **待重判戳（`assemble_reeval_brief` / `stamp_reeval_pending` → `reeval_pending`）**：监控发现输入到期/越带/变化时，零 LLM 组装重估简报并盖 `reeval_pending` 戳（doctor/monitor 会暴露）；下次 `record_evaluation` 落新版后自动清戳。

---

## 四、primer 规约（全 type 共用）

> 来源：`04-synthesize/00-primer.md`（逐字搬运）。primer-first = 先于 case 生成，所有 type 统一。

### 定位与分工

- **primer（00_primer）**：给**完全外行**写领域教科书第一章——读完能对"研究对象本身"建立完整心智模型，足以跟从业者聊半小时不露怯
- **case（c_/i_/a_/m_）**：给**已入门者**的结构化分析与下注决策
- **二者绝对不重叠**：路线"是什么"归 primer，"哪条会赢"归 case

### 核心方法（元目标 + 目标生成 + 自由发挥 + 独立 critic）

**不变的元目标（逐字不改）**：
> 门外人为了投资，正在研究这个 topic，他需要知道什么——以让他读完一篇就能入门该领域本身。先不限制内容长度。

**目标生成流程**（不从零拍脑袋）：
1. 读 `decomposition_v0.md` 的「primer 入门目标 v0」（种子）
2. delta 校验：读 findings + thesis_v0，逐条问"该补哪些新入门目标？哪些可坍缩？"
3. 性质校验：**理解性/教学性**保留；**决策性**（"能判断 V 贵不贵"）剔除或改写
4. 出定稿清单（N 条，通常 8-13）；记录增删（交 decomposition_v1 持久化）

每条必须是**门外人可观察的具体能力**：「能跟人解释 X / 能区分 Y 和 Z / 听到术语 W 知道在说什么」

**type 视角适配**（LLM 自行判断）：
- industry/arena → 层层递进理解（科学原理→路线→产业链→玩家→争议）
- company → 主体画像（领域速写→是什么/做什么→怎么赚钱→竞争→财务→估值→争议→时点）
- science-heavy company → 混合：先 industry 式铺科学背景，再 company 式讲主体

### 起点诊断（写正文前必做）

1. 读者**已知的最近概念**是什么？（固态电池→锂电池；荣昌→"创新药是热门赛道"）
2. 从这个起点到 topic，需要哪几步**知识阶梯**？（每步一句话，5-8 步）
3. 起点是大学通识级 / 行业入门级 / 更专？
4. 从 `display_name` + `scope.question` + `thesis` 抽出 **1-3 个特色点**，强制给独立章节

### 自由发挥写作硬规约（质量来源，不是章节）

- **预设读者**：理工/金融背景但完全没碰过本领域；讲解语气，不是同行速记
- **首次出现锚定**：任何术语/缩写/化合物/病名/法案首次出现 = 中英全名 + 一句定义 + 类型归属
- **类比**：核心概念尽量给类比（硫化锂≈光刻胶 / ADC≈生物导弹 / PFOF≈浏览器卖搜索流量）；写不出好类比宁可多讲两句机制，不硬塞牵强类比
- **横向对比表**：2 项以上并列概念（技术路线/竞品/产品线）尽量给表
- **争议必现**：必有一节列 5-7 条尚未消解的根本争议 + 各方理由（不能假装确定）
- **自检清单结尾**：列"读完后读者应能做到的 N 条"（对应 Step 1 目标）

### 来源分层（强约束）

| 来源 | 标注方式 |
|------|---------|
| LLM 训练知识（行业原理/技术/工艺/估值方法/政策框架） | 不标单条；文末来源说明统一声明"行业稳定知识" |
| 本研究 findings（具体数字/时间表/公司动态/财务/BD 条款） | 凡引用必标 `[mat-XXX]` 或 `(mat-XXX)` |
| 本研究特色判断（thesis take / 强度 / 特色叙事） | 文末点到 + 指向 thesis_v1 / sidecar，正文不展开重述 |

文末 `## 来源说明` 给三者大致占比 + 引用的 mat 列表（表格）

### depth 降级（稀有领域诚实标注，不假装深）

- **行业层训练知识厚**→ 正常写，frontmatter `depth: deep`
- **行业层也薄**（训练截止后才热/极冷门）→ frontmatter `depth: shallow` + 正文声明"本领域 LLM 训练知识有限，背景部分可靠性低，建议补充阅读 [外部资料]"
- **公司层薄但行业层厚是常态**（如荣昌 primer）→ 来源说明里显式说明"行业背景可信 + 公司事实依赖 findings 标注"

**关键洞察**：稀有领域瓶颈不在 LLM 写作能力，在 findings 数据覆盖度；critic 反馈"市场规模缺/估值拆解黑箱"多数是底层资料没挖到。

### 深度门禁 F17（depth: deep 的机械 gate）

`depth: deep` 的 primer 必须同时满足（由 `primer_quality_gate` 机械检查）：
- `char_count ≥ 6000`
- `has_controversy`（正文含"争议"）
- `has_selfcheck`（含"自检"或"自测"）
- `critic_passed`（独立 critic 收敛后调 `set_output_critic_passed`）

任一不过 → `set_output_status` 自动降级 `draft` + 写 `primer_gate.warnings`

**收尾注册顺序（硬要求）**：critic 收敛 → 先 `set_output_critic_passed` → 再 `set_output_status(..., 'fresh', ...)` → 最后 `primer_quality_gate` 核门禁结果

---

## 五、arena 6维评分 + peer 财务脊柱

> 来源：`04-synthesize/_arena_select_spec.md` Step 3（6维评分口径）+ Step 4（强制三档分流）。

### 6维评分口径（industry 环④喂 arena tier，详见 §一.2 环④）

至少识别 **5 个细分 arena**（来源：findings + 决策链①③ 的价值链/迁移路径判断），每维 **1-5** 评分；每个数字注明来源（findings mat_id 或"训练知识假设"）：

| 维度 | 说明 | 评分标准 (1-5) |
|------|------|----------------|
| `profit_pool` 利润池规模 | 当前及 5 年期 arena 总利润（亿元，区间） | 1: <10亿, 5: >1000亿 |
| `growth` 增速预期 | 3 年 CAGR | 1: <5%, 5: >30% |
| `competition` 竞争结构 | CR3 / 是否自然垄断 / 是否同质化 | 1: 完全竞争, 5: 自然垄断 |
| `valuation` 估值水位 | 当前 PE/PS 相对该 arena 历史 + 全球 peer | 1: 历史高位, 5: 历史低位 |
| `cycle` 周期位置 | 早期成长/中段加速/晚期分化/成熟饱和 | 1: 衰退/饱和, 5: 早期成长 |
| `composite` 综合评分 | 以上维度加权平均（权重按命门判断，不强制等权） | 1-5（float） |

**tier 判定（强制三档，每档至少 1 个 arena）**：
- `deep` 深挖档：综合评分 **≥ 4**，或有强催化剂
- `watch` 观察档：综合评分 **2-3**，或有不确定性
- `eliminated` 淘汰档：综合评分 **≤ 2**，或有硬伤

> 以上为参考基准——命门判断可调整（写清楚为什么偏离）。深挖/观察档必填非空 `upgrade_triggers` + `monitor_metrics`；淘汰档写复活条件（如有）。

### peer 财务脊柱选择（arena 环④ 横比矩阵维度）

**必须包含的维度**（从 `financial_data.get_peer_comparison_data_by_tickers` 取）：
- 收入规模（LTM 营收，元/美元）
- 3年平均 ROIC（%）
- 毛利率（%，LTM）
- 资产负债率（%，最新季度）
- 当前 PE（TTM）
- 历史 PE 区间（近 3-5 年 10%-90% 分位）

**扩展维度**（按赛道判断取舍）：
- PS（适用于早期/高增速）
- EV/EBITDA（适用于资本密集）
- NTM 收入增速预期（适用于成长赛道）
- FCF Yield（适用于成熟/分红赛道）

**取数规范**：
- A股：`SZSE/SSE/BSE`，用 akshare，单位元
- 港股：`HKEX`，用 yfinance，单位 HKD
- 美股：`NASDAQ/NYSE`，用 yfinance，单位 USD
- 非上市公司：训练知识估算 + 明确标注"估算，非 findings"

**F13 硬 checkpoint**：取不到的必须 log（缺哪个 + 为何）；不许让环②/④的估值列空着；fallback 到研报 PE 表或明写"数据缺失"

---

## 六、合成调度模式（全 type 共用）

> 来源：`04-synthesize/_shared.md`（精华提炼）。

### 调度默认规则

- **主 agent 直做 + 并行 Write**：所有 case 文件由主 agent 直接写
- **唯一 subagent 是 critic**：critic 只读不写（F2 强制：subagent 只产 markdown 到 final message，主 agent Write）
- **绝不无限制 dispatch**：深挖 subagent ≤ 1 层嵌套；任务分解≤ 3 个 subagent

### gap 体检（进合成前必做）

```python
from prism.scripts.gap_detector import detect_gaps
result = detect_gaps(slug, variant)
# 返回：uncovered_ks / uncovered_ring_inputs / single_source / autofetch_debt
# F6：detect_gaps 不 raise，只报告，LLM 判断是否补救
```

三项任一非空 → 不要硬合成，先判断是否补救（见 F6 gap 仅诊断）。

`*-mirror` 类 gap 几乎必报红（复用旧料缺历史镜鉴类），通常可用训练知识 depth 降级处理，不是真缺口。

### 增量重写判定

```python
from prism.scripts.topic import list_affected_outputs
outputs = list_affected_outputs(slug, variant)
# fresh → 跳过；stale/new → 写/重写
```

**B 轴有界 delta 重拆**：命门有重大修订（命门变化≥2个 / 置信度跳动≥2档）时触发 decomposition_v2 重拆；轻微修订在 decomposition 内记 changelog，不升版

**incremental rewrite 判定**：
- `fresh`：上游 findings 未变，不重写
- `stale`：findings 更新但 case 未同步，重写受影响章节（不是全文）
- `new`：首次写

### 即兴 web-search（合成中发现缺口时）

场景：合成中发现某关键 fact 缺失，启动补搜：
1. 确认缺口类型（快变 fact = 必须补；静态 = 训练知识可用）
2. 补搜后用 `register_web_search_batch` 入库（标 triggered_by='04-synth'）
3. 入库后更新 findings（新建 `findings_{mat_id}.md`）
4. H2 救回判断（F9，drop_ratio > 0.8 必救）

### chain-critic（所有 case 通用）

chain-critic 检查清单（让 subagent 以"刚读完 case，之前没看写作过程"视角对抗）：

1. **链通不通**：每环是否被上一环逼出？有无断链？
2. **primer↔case 分工干净**：case 有无重教 primer 已讲透的背景？
3. **目标达成**：贴出 scope.question 原文，逐子句核对是否答到可执行层
4. **来源分层**：findings 数字是否标 `[mat-XXX]`？训练知识估算是否标注？
5. **硬落地核对**：每环的 input_contract 硬落地是否都出现了？
6. **四段总评**：链通不通 / 最严重 2-3 断点 / 目标达成判定 / 只补一处补哪

首轮若链断 OR 目标未达成，**必须跑第二轮**。

### 终态报告（合成收尾硬要求）

合成落盘后，向用户报告：
```
【合成完成报告】
slug: {slug} | variant: {variant}
产出：{列出所有写了的文件}
时间线变化：
  - thesis: v{N}（Scheme C 全快照）
  - decomposition: v{N}（收敛状态: converged/open/capped）
数据缺口（合成中诚实标注）：
  - P0 缺口：{...}（阻断 I7 critic）
  - P1 缺口：{...}（降低 conviction）
新增 todos（收料）：
  - {任务描述} | priority={P0/P1/P2} | addresses=[{K#}]
stage 推进：→ 05-critic-review
```

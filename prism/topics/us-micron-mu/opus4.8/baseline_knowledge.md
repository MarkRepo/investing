---
slug: us-micron-mu
variant: opus4.8
written_at: 2026-06-12
training_cutoff_estimate: 2026-01
---

# 训练知识 Baseline — 美光科技 (Micron, NASDAQ: MU)

> 本文记录 LLM 在**训练截止时**对该 topic 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。

## 〇、基本信息（company）

- **主代码**：`US_MU`（NASDAQ: MU；与 topic.yaml `scope.ticker` 一致）
- **多市场上市**：单市场（仅 NASDAQ）
- **总部**：美国爱达荷州博伊西（Boise, Idaho）
- **财年特殊性** ⚠️：Micron 财年**非自然年**——FY 截止于 8 月底/9 月初（如 FY2025 ≈ 截止 2025-08-28）。季度划分：Q1≈9-11月、Q2≈12-2月、Q3≈3-5月、Q4≈6-8月。**做任何"最新季度"判断必须先确认是 FYxx Qx 而非日历季**。
- **市场属性**：美股，盘后财报披露，季度 earnings call。

## 一、关键事实记忆（28 条）

### 公司定位与产品
- `[fact-01]` Micron 是全球三大 DRAM 厂之一（与 Samsung、SK Hynix 并列），也是主要 NAND 厂之一 → 置信度：高 | time_sensitivity：慢变
- `[fact-02]` Micron 产品线：DRAM（约占营收 70%+）、NAND（约 25-30%）；终端覆盖数据中心、PC、手机、汽车、工业 → 置信度：高 | time_sensitivity：慢变
- `[fact-03]` HBM（高带宽内存）是当前最核心成长引擎，用于 AI 加速器（NVIDIA GPU 等）；Micron 已量产 HBM3E（8-high 与 12-high），供货 NVIDIA H200/B200 等 → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-04]` HBM 市场格局：SK Hynix 为份额领导者，Micron 与 Samsung 竞争第二/三位；Samsung 在 NVIDIA HBM 认证上一度受阻 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-05]` Micron 曾表示其 HBM 产能在 2024、2025 已"售罄/全部分配"（sold out） → 置信度：中 | time_sensitivity：**快变** ⚠️

### 技术节点
- `[fact-06]` DRAM 工艺：1-alpha、1-beta、1-gamma（1γ 引入 EUV 光刻）；Micron 相对 Samsung/SK Hynix 较晚引入 EUV，约 2025 年于 1γ 节点采用 → 置信度：中 | time_sensitivity：慢变
- `[fact-07]` NAND：232 层为主力节点，向更高层数推进 → 置信度：中 | time_sensitivity：慢变
- `[fact-08]` HBM4 路线图：目标约 2026 年量产爬坡 → 置信度：中 | time_sensitivity：**快变** ⚠️

### 财务（高时效——训练记忆多为区间估计，必须校准）
- `[fact-09]` 内存行业 2022-2023 经历严重下行周期，毛利率一度转负；2024 起在 AI/HBM 驱动下复苏 → 置信度：高 | time_sensitivity：慢变
- `[fact-10]` 营收轨迹（财年）：FY2023 约 $15.5B（周期底）、FY2024 约 $25B、FY2025 估约 $35-37B（强劲反弹） → 置信度：中（FY2025 为推断） | time_sensitivity：**快变** ⚠️
- `[fact-11]` 毛利率从周期底的负值恢复到 30-40%+ 区间（HBM/DDR5 涨价驱动） → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-12]` Q4 FY2025（截止 2025-08）创季度营收纪录，单季营收约 $9-11B（区间记忆，不确定） → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-13]` 股价：2024 年约 $80-100 区间，2025 年大幅上涨；2025 年末可能 $150-200+（高度不确定） → 置信度：uncertain | time_sensitivity：**快变** ⚠️
- `[fact-14]` 估值：内存股 PE 在周期中失真（底部 EPS 为负 PE 无意义，顶部 PE 压缩）；市场更看 P/B 与峰值盈利能力 → 置信度：中 | time_sensitivity：慢变

### 资本开支与产能
- `[fact-15]` CapEx 量级约 $8-14B/年；FY2025 资本开支指引偏高（约 $14B 量级，含 WFE 与建厂） → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-16]` 在建大型晶圆厂：美国爱达荷 Boise、纽约 Clay（NY）——多年期巨额项目，受 CHIPS Act 支持；另有日本广岛、台湾、新加坡产能 → 置信度：高 | time_sensitivity：慢变
- `[fact-17]` CHIPS Act：Micron 获得约 $6.1B 联邦拨款用于美国建厂 → 置信度：中 | time_sensitivity：慢变
- `[fact-18]` 内存行业资本强度高、产能爬坡周期长（fab 18-24 月）；供给纪律是周期波动核心变量 → 置信度：高 | time_sensitivity：静态

### 竞争与地缘
- `[fact-19]` CXMT（长鑫存储，中国）正崛起为 DRAM 新进入者，主攻中低端 DDR4/DDR5，可能压制低端价格 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-20]` 2023 年中国 CAC 对 Micron 启动网络安全审查并禁止其产品用于关键信息基础设施，冲击 Micron 在华营收 → 置信度：高 | time_sensitivity：慢变
- `[fact-21]` 内存定价回升伴随供给纪律（三大厂减产/控制 capex）；HBM 占用 wafer 产能挤压标准 DRAM 供给，对整体涨价有结构性支撑 → 置信度：中 | time_sensitivity：慢变

### 管理层
- `[fact-22]` CEO：Sanjay Mehrotra（长期任职，SanDisk 联合创始人出身） → 置信度：高 | time_sensitivity：慢变
- `[fact-23]` CFO：Mark Murphy → 置信度：中 | time_sensitivity：**快变**（高管可能变动）⚠️

### 行业机制（静态/慢变）
- `[fact-24]` 内存是商品化周期品：价格由供需边际决定，盈利大起大落；差异化主要靠 HBM/高端 DDR5/LPDDR 等高附加值产品 → 置信度：高 | time_sensitivity：静态
- `[fact-25]` HBM 单位 wafer 消耗远高于标准 DRAM（die size 大 + 良率爬坡），故 HBM 扩产会"双重"收紧标准 DRAM 供给 → 置信度：中 | time_sensitivity：静态
- `[fact-26]` Micron 在汽车/工业内存（长生命周期、高毛利）有较强地位 → 置信度：中 | time_sensitivity：慢变
- `[fact-27]` 内存价格领先指标：DRAMeXchange/TrendForce 现货价与合约价；DDR5、LPDDR5、HBM 定价分层 → 置信度：高 | time_sensitivity：静态
- `[fact-28]` AI 服务器内存含量（DRAM + HBM）远高于传统服务器，是本轮"内存超级周期"叙事的需求侧根基 → 置信度：高 | time_sensitivity：慢变

**第一节统计**：静态 5 条 / 慢变 10 条 / 快变 13 条。
**快变 + 高/中置信子集（必须第五节有对应 query）**：fact-03、04、05、08、10、11、15、19、23（fact-12/13 已是 low/uncertain，仍尽量校准）。

## 二、关键人物 / 公司 / 产品

- **Sanjay Mehrotra**（CEO）：内存行业老将，掌舵 Micron 周期转型与 HBM 战略。
- **SK Hynix**（韩，最大对手）：HBM 份额领导者，NVIDIA 主供。
- **Samsung**（韩，最大综合内存厂）：DRAM 龙头，但 HBM 在 NVIDIA 认证一度落后。
- **CXMT 长鑫存储**（中）：DRAM 新进入者，低端价格扰动来源。
- **NVIDIA**：HBM 最大下游客户，AI GPU 决定 HBM 需求节奏。
- **HBM3E / HBM4**：核心高端产品，HBM4 是下一代竞争焦点。
- **TrendForce / DRAMeXchange**：内存价格数据权威来源。

## 三、产业链 / 竞争格局认知

**主线**：内存是高度周期的商品半导体，三大 DRAM 寡头（Samsung / SK Hynix / Micron）合计占绝大部分份额，供给纪律决定周期幅度。本轮（2024-2026）周期由 AI 驱动——AI 服务器对 HBM 和高容量 DDR5 的需求拉动量价齐升，叠加三大厂将 wafer 产能向 HBM 倾斜（HBM die 大、良率低，挤占标准 DRAM 供给），形成"AI 内存超级周期"叙事。

**Micron 相对位**：综合内存厂中规模第三，但在 HBM 上从追赶者转为有竞争力的供应商（HBM3E 已上量、12-high 推进），并强调其 HBM 能效/良率优势。技术节点上历史略慢（EUV 引入晚），但 1γ 节点正在追赶。地缘上受中国 CAC 禁令拖累在华业务，同时是 CHIPS Act 美国本土建厂最大受益者之一。

**竞争格局变量**：①HBM 认证与份额（SK Hynix 领先，Micron/Samsung 争二三）；②CXMT 在低端 DRAM 的渗透对标准品价格的扰动；③三大厂的供给纪律（capex 是否克制）；④HBM4 节点的技术领先权。

**周期位置（训练时判断）**：2024-2025 处于上行周期，量价齐升、毛利率快速修复，市场押注本轮因 AI 结构性需求而比历史周期更持久、波幅更小——但这是 thesis 待验证的核心赌注，并非定论。

## 四、训练知识盲点（自我承认）

- **最新财报具体数字**：FY2025 全年与各季、以及 FY2026 Q1/Q2（甚至 Q3，截止约 2026-05，可能 6 月底才报）的精确营收/毛利率/EPS/HBM 营收占比，训练记忆模糊或缺失。
- **当前股价与估值**：MU 2026 年的股价、市值、P/B、forward PE 完全不确定。
- **HBM 份额最新数据**：Micron HBM 在 2025-2026 的实际份额、HBM4 量产进度、与 SK Hynix 差距的最新状态。
- **DRAM/NAND 2026 现货与合约价走势**：本轮周期是否见顶/续涨/回落的最新信号。
- **FY2026 CapEx 指引**与美国/纽约 fab 的最新进度（是否延期）。
- **CXMT 威胁的量化进展**：其 DDR5 产能/良率/份额在 2026 的实际状态。
- **股东回报政策**：Micron 是否恢复/扩大回购、股息政策最新状态（训练记忆不清）。
- **关税/出口管制**：2025-2026 美中半导体管制、对等关税对内存的最新影响。

## 五、需要 web-search 校准的优先项

> 强制：第一节"快变 + 高/中"fact 均有对应 query。

1. `Micron MU FY2026 latest quarter earnings revenue gross margin guidance`（校准 fact-10/11/12，最新财季）
2. `Micron HBM3E HBM4 market share 2026 ramp NVIDIA`（校准 fact-03/04/05/08）
3. `Micron MU stock price market cap valuation forward PE 2026`（校准 fact-13/14）
4. `Micron capex FY2026 guidance New York Idaho fab schedule`（校准 fact-15/16）
5. `DRAM NAND price trend 2026 TrendForce contract spot DDR5`（校准 fact-21/27 周期位置）
6. `CXMT ChangXin DRAM DDR5 capacity 2026 competition Micron`（校准 fact-19）
7. `Micron HBM revenue percentage data center 2026`（校准 HBM 兑现，fact-03/28）
8. `memory super cycle 2026 outlook peak Micron analyst`（校准周期顶/续 judgment）
9. `Micron share buyback dividend capital return 2026`（盲点：股东回报）
10. `Micron China CXMT tariff export control memory 2026`（盲点：地缘/关税）

## 六、prescan 校准结果（2026-06-12 回写）

> Step 4.5 prescan 入库 17 份 web-search material（6 high / 11 mid）后，对照第一节 fact-NN 的更新。
> **总判断：本轮校准是颠覆性的——训练记忆严重低估了 2026 内存超级周期的烈度与 Micron 的兑现程度。**

### 被推翻（高优先级——thesis_v0 不要再引用原 fact）
- `[fact-11]` 训练"毛利率 30-40%"，被 `[mat-2abb63]` 推翻：**Q2 FY2026 毛利率 74%**（去年同期 37%）→ 已是历史级峰值利润率，认知必须重置
- `[fact-12]` 训练"Q4 FY2025 单季 ~$9-11B"，被 `[mat-f03161]`/`[mat-2abb63]` 大幅上修：**Q2 FY2026 单季营收 $23.86B**（+196% YoY），EPS $12.20 adj，净利 $13.79B
- `[fact-13]` 训练"股价 $150-200"，被 `[mat-baf4bf]` 推翻：**2026-03-12 收 $406.36**，52 周高 $455.50，12 个月 +323%；`[mat-145d4e]` 市值 **$1.12 万亿**（已是万亿巨头）
- `[fact-10]` 训练"FY2025 ~$35-37B"，被 `[mat-baf4bf]` 上下文校准：**FY2026 营收一致预期 ~$79B**，TTM 已 $58.12B（`[mat-145d4e]`）→ FY2026 翻倍式增长
- `[fact-15]` 训练"capex ~$14B"，被 `[mat-8494eb]` 上修：**FY2026 capex 提至 ~$20B**（从 $18B），主投 HBM + 1-gamma；H1 已 capex $11.78B
- `[fact-23]` CFO Mark Murphy → 未校准到最新，标 uncertain（本轮未查证）

### 被验证（可继续引用，置信度提升）
- `[fact-05]` HBM 售罄 → `[mat-baf4bf]`/`[mat-8494eb]` 确认：**整个 CY2026 HBM 已全部售出**，置信度 中→高
- `[fact-08]` HBM4 2026 量产 → `[mat-8494eb]` 确认：HBM4（>11 Gbps）**Q2 CY2026 高良率爬坡**，1-gamma 同步，置信度 中→高
- `[fact-25]` HBM 挤占标准 DRAM 供给 → `[mat-8494eb]` 量化为 **HBM 与 DDR5 的 3:1 wafer 折算比**，置信度 中→高
- `[fact-19]` CXMT 崛起 → `[mat-8f0602]` 确认：CXMT 激进扩产、**~7.67% 份额、2026 拟 ~$4.1B IPO**，置信度 中→高（仍主攻低端，对高端/HBM 暂无威胁）
- `[fact-20]`/`[fact-21]` 地缘 + 供给纪律 → `[mat-fe28d7]` Micron 游说美国国会遏制中国对手；`[mat-8494eb]` 供给短缺持续"贯穿并超越 CY2026"，置信度维持高
- `[fact-22]` CEO Sanjay Mehrotra → 未见变动信号，维持高

### 新增关键事实（baseline 未覆盖，thesis_v0 直接用）
- `[mat-145d4e]` ROE 39.82% / ROIC 37.40% / PEG 0.07 / 净现金 $5.83B；TTM OCF $30.65B、capex -$20.37B、**FCF $10.28B**（已转正且强劲）
- `[mat-baf4bf]` **forward PE 仅 10.7x**（基于 ~$35 FY2026 EPS）——典型"峰值盈利 × 低倍数"周期股估值；26/27 分析师 Buy、1 Hold、0 Sell
- `[mat-ac10a1]` BofA 目标价 $500→$950（Buy）；DA Davidson 首予 Buy 目标价 $1,000——卖方极度乐观（反向需警惕一致性风险）
- `[mat-2abb63]` 资本回报恢复：Q2 回购 $650M、季度股息 $0.115→$0.15；H1 偿债 $4.37B、总债降至 $10.14B（去杠杆）；披露多项专利/证券诉讼
- `[mat-145d4e]` **下一次财报 2026-06-24 盘后**（Q3 FY2026）——本研究启动后约 2 周的关键事件
- `[mat-dc56cb]` TrendForce：**DDR5 现货走强**（品牌需求+更高出价）、DDR4 走弱；1Q26 DRAM/NAND 价格大涨

### 仍未校准（thesis_v0 引用时标 uncertain）
- `[fact-23]` CFO 现任 / 高管最新
- NAND 具体层数节点最新（fact-07）、Micron HBM 精确份额 vs SK Hynix（仅知"有竞争力的第二/三"）

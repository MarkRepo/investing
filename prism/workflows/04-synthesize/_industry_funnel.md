# Industry 合成（理解先行 · 决策链驱动 · 漏斗终局 · 自由发挥版）

> **调度提示**：本文件是 **industry 类型 topic 在 04-synthesize 阶段的完整规范**，整体替代 `_shared.md` + `01-08` 的 8 份分箱 spec + 旧 `_arena_select_spec.md` 的独立 markdown。`company` 走 `_company_case.md`，`arena` 走 `_arena_funnel.md`。
>
> **复用上游、不重写**：00-research → 01-roadmap → 02-materials → 03-findings 的 findings、`gap_detector`、增量重写判定、`financial_data`、`thesis`、`00-primer.md`、09 sidecar schema/stub 创建机制全部沿用。本文件只重做"合成"这一段。
>
> **09 sidecar 与 arena stub 机制保留**：`_arena_select_spec.md` 不删——它作为 **④ 的 6 维评分工具** + **⑥ 的 sidecar schema(Step 6.5) + arena stub 创建/继承(Step 6/6b)** 被本文件引用（查规范，不照搬结构）。

---

## 0. 定位与边界

industry 不是终局决策——它是**漏斗**：终点不是"买/卖一只股票"，而是**把资本/注意力分配给哪几个细分 arena**。旧路径把 industry 合成切成 8 份并列维度 + 一份 09 选拔表，骨架按通用形状刻、industry 硬套；且把"领域入门(primer)"放在最后生成——先下结论再补领域解释。

本文件两处根本改动（与 `_company_case.md` 同构）：

1. **理解先行**：先出 `00_primer`（行业理解地基，critic 校验"门外人真懂了"），**决策链显式站在它之上**。
2. **按决策因果链组织**（不是并列维度）：每一环都是上一环**逼出来的**，读者顺着读就是顺着一次完整的"这行业的钱该投向哪"在想。

- **不变的是骨架（理解先行 + 决策链 6 环 + 09 sidecar schema）**——保证逻辑紧、漏斗机制不丢、跨 topic 可比。
- **自由的是血肉**——每环问什么、怎么组织、详略、产出拆几份，交给 LLM 针对这个行业的命门判断。
- 01-08 不再是骨架，降级成一张"别漏维度"的对照清单。

---

## 1. 核心方法

沿用 `00-primer.md` 已验证的"给目标 + 自由发挥 + 独立 critic 校验"闭环，分两层落地：**primer 是上游理解地基（纯自由发挥），case 是下游决策（自由发挥锚定在决策链上）。**

### 1.1 元目标（逐字不改）

> **一个门外人为了配置资本，正在研究这个行业。先让他读懂这门生意/技术/赛道本身（primer）；再带他走完一条决策链：看懂行业 → 市场给这行业定了什么价 → 这价要什么结构性假设为真 → 利润池会落到哪几个 arena、我信哪条迁移路径 → 错了怎么知道 → 那资本/注意力就怎么分配。读完既入了门，也拿到一套可执行的 arena 分流机制。**

### 1.2 理解先行：primer 与 case 的依赖与分工（**核心规约**）

| | 谁先生成 | 读者 | 干什么 | 谁依赖谁 |
|---|---|---|---|---|
| **00_primer** | **先**（理解地基） | 完全门外人 | 看懂行业**本身**，不被术语挡住 | 被 case 依赖 |
| **i_industry_case** | **后**（站在 primer 上） | 要分配资本/注意力的人 | 看懂**利润池往哪迁、哪几个 arena 值得投** | 依赖 primer |
| **thesis_v1** | **最后**（提炼快照） | 持续追踪者 | 把行业层判断提炼成可追踪快照 | 依赖 case |

时间轴：**学懂行业(primer) → 做分流决策(case) → 持续追踪(thesis)**。生成顺序 = 阅读顺序。

**primer↔case 分工（杀掉重复，硬规约）**：
- **primer** = 静态全景地图，中立教全部（价值链/技术路线/玩家/争议），可独立读懂。
- **case ①** = **已假定读者读过 primer** 的"决策导向速写"——只点"利润池此刻在哪段 + 哪个张力直接驱动迁移判断"，**不重教 primer 已讲透的背景**，需要深度就写"详见 primer"。
- **地图归 primer，动态方向判断（利润池往哪迁、定价对不对）归 case。** industry 的 primer↔case 重叠面比 company 大（同一主题两种框法），这条边尤其要守，chain-critic 必查。

### 1.3 跨层复用质量护栏（**硬规约 · 与 Step 1 亲属 hook 配套**）

跨层复用是"站在肩膀上"，**不是"继承结论"**。亲属（父/子 topic）的蒸馏产出只作输入/参照，质量永远按本维度、本 topic 自身的 findings + 自身的 critic 来卡：

1. **本维度自己跑完整链**：照常跑 primer + 6 环 + critic，全程按 industry 级分辨率要求。亲属产出是脚手架不是正文。
2. **质量闸门一律本地**：`gap_detector`、chain-critic、05-critic、来源分层都对着**本 topic 自己的 K# 和 findings** 跑，不因"亲属已覆盖"放水。借来的判断要么有本 topic 自己的证据撑，要么明标继承、降信心。
3. **借来必标来源**：正文里 borrowed-from-relative 的内容可见地标出（对齐 mat-XXX 分层惯例），不许借来的框架冒充本 topic 自验证的结论。
4. **冲突时本维度赢**：亲属观点与本 topic 自己的 findings 打架 → 以本 topic 为准，允许背离（深挖恰恰可能证明亲属判断错了）；这种背离触发向上路径把亲属标 stale。

### 1.4 决策链（6 环 · 这就是契约本身）

**必须按序走完整条链，每一环必须落地（见 §3.2 各环硬约束）。不允许断链（如有 ④ 下注却无 ⑤ 证伪、有 ⑥ 分流却无 ② 定价锚）。**

```
① 能不能看懂这个行业？
   └─ 看不懂就不配。价值链全貌 + 利润池此刻在哪段 + 由什么驱动 + 周期位 + 行业层多年财务弧线。这是闸门。
        ↓ 看懂了，那市场现在怎么给它定价——
② 市场/共识此刻替这行业定了什么价？【硬锚 · 命门环】
   └─ 行业没有单一价格：用龙头/细分的估值倍数反推 priced-in 的增速 + 相对历史&全球 peer 的估值水位 + 主流叙事。必须有数字，否则整链失去脊柱。
        ↓ 这套定价/叙事，
③ 需要什么结构性假设为真？
   └─ What-Must-Be-True：把②翻成 3-5 条可证伪的结构性假设（利润池往哪迁、谁攫取价值、渗透曲线）。
        ↓ 这些假设，
④ 我对这行业整体什么立场 + 利润池落到哪几个 arena？【下注】
   └─ 行业整体 stance 一句话 + 我和共识的迁移路径分歧 + 各 arena 沿 6 维判断（现 09 评分作工具）。这是下注。
        ↓ 我这套判断，
⑤ 如果错了会怎样、怎么第一时间知道？
   └─ 行业级 kill + 历史行业镜鉴（热过但利润没兑现）+ signpost。这是证伪机制。
        ↓ 综合①-⑤，
⑥ 那资本/注意力就怎么分配？【行动 = 漏斗】
   └─ 深挖/观察/淘汰三档（tier=吸引力×当前定价）+ 注意力预算 + 触发器 + 建 arena stub。这是行动。
```

**为什么是紧的**：③ 只因②产出定价才存在；④ 把③的假设判成行业 stance + arena 分布；⑥ 的 tier 由②的定价 + ④的吸引力共同决定（不是只按好坏排）；⑤ 只因④下注才需要。环与环是因果序、不是并列箱。

**与 company 的差异（刻意）**：company ④ 有 EV 加总（概率×回报）；漏斗的"回报"非单一数字，硬算是假精度——**industry 不做 EV 加总**，定量终点是 ⑥ 的 tier 分 + 触发器（喂 09 sidecar）。

---

## 2. 执行 — 上游准备与 primer 先行

### Step 0：前置检查 + gap 体检（双轴）+ 增量判定 + 命门 delta 重拆（**引用 `_shared.md`，不重抄**）

进 04 第一件事，照 `_shared.md` 跑三段，结果完整贴对话：

1. **前置检查**（资料 ≥3 份，否则停）。
2. **gap 体检**（`detect_gaps` 三项任一非空 → 不要硬合成，先补救）。
3. **增量重写判定**（`list_affected_outputs` 判 new/stale/fresh；`fresh` 跳过）。industry 路径 output_key 见 §5。

> Web 搜索路径见 [[_web_search_routing]]；即兴 web-search 规约见 `_shared.md`。

### Step 1：加载 findings + thesis_v0 + 行业财务 + **亲属产出（图谱层 hook）**

1. 照 `_shared.md` § 调度模式：`format_findings_for_prompt` 列 findings（含 `parent_materials` 复用的父级 findings）→ 主 agent 并行 Read；`build_findings_index` 落盘 `_findings_index.md`（防 compact 地图）；读 `thesis_v0.md`（强度 v0→v1 锚）。
2. **拉行业层财务轨迹**（喂①的财务弧线 + ②反推口径）：对行业代表性龙头/聚合调 `financial_data`（`get_financial_context` 单家 / `get_peer_comparison_data_by_tickers` 多家聚合），取多年营收/利润率/ROIC/FCF 走势。这是①财务弧线梁与②反推的一手锚；不在 findings 里手抽。
2b. **拉龙头估值倍数**（喂②定价锚 —— 数字最硬的一环，F13 接线）：对代表龙头 ticker 调 `market_data.get_valuation_context_by_tickers([{ticker,market,name},...])` 拿 PE(TTM)/PS/PB/市值（港股经 yfinance 路由，HKD 计价；A 股 akshare，元）。这是②"当前价已 priced-in 什么"反推的一手锚，**不靠 web 现采、不在 findings 手抽**。
   ```python
   from prism.scripts.market_data import get_valuation_context_by_tickers
   print(get_valuation_context_by_tickers([
       {'ticker': '600276', 'market': 'SSE', 'name': '恒瑞'},
       {'ticker': '01801', 'market': 'HKEX', 'name': '信达'},  # 港股可取
   ]))
   ```
   > ⚠️ **硬 checkpoint（F13：拉不到要 log，不静默跳）**：函数对取不到的龙头显式标 *(取不到)*。若某龙头倍数缺，**必须在对话里 log 缺哪个 + 为何**（ticker/market 错？该标的真无行情？），再决定用研报 PE 表 fallback 或标注缺口——**不许默默让环②退化成纯定性**（这正是上轮环②脊柱塌的根因）。
3. 写 `outputs/_synthesis_brief.md`：dump 核心 thesis / 关键假设 / v0→v1 强度调整，供 ④⑤⑥ 与 critic 复用。

> **亲属复用 hook（已生效）**：若本 topic 有 `parent_topic`（或 `find_child_topics` 返回非空），调 `get_relative_outputs('{slug}','{variant}')` 取亲属的 primer / 最新 thesis / case·09·10 **路径**并 Read。**借来内容受 §1.3 约束**——脚本只返路径不读内容，借用永远是输入/参照：必标来源、质量按本维度自跑、冲突时本 topic 赢。
> - **向下（父→子）**：行业极少有父；若有（如更大产业），primer 站其上、不重教。
> - **向上（已研究的子 arena → 本行业）**：把已研究子 arena 的成稿 case/thesis 当**一等证据**喂 ④ 的 arena 评分（让该 arena 的判断变实证而非估算），并按 §1.3 护栏标来源、本维度自己复核。
> - 无亲属 → 返空 → 退化为独立合成，零特判。

> **调度模式**：industry case 默认**主 agent 直做 + 并行 Write**（同 `_shared.md` 默认；勿 dispatch subagent 写长产出，见 [[subagent-write-hallucination]] / feedback_subagent_bulk_synthesis）。唯一 subagent 是 critic（只读不写）。

### Step 2：**先出 `00_primer`（理解地基）**

按 `00-primer.md` Step 1-5 执行，产 `outputs/00_primer.md` + `_prism_reading_guide.md`。

**本路径走 primer-first**（00-primer.md 已 primer-first 单一路径，见其头部）：
- 原材料 = **findings + `thesis_v0` + K# + 行业财务 + 亲属 primer（若有）**。
- 投资加权（"该讲技术原理/产业链/利润池/玩家/争议"）来自元目标 + thesis_v0 + K#。
- primer 其余流程（目标生成 / 起点诊断 / 自由发挥 / 来源分层 / depth 降级 / **独立 critic 校验**）照走，critic 不可省。
- primer 写完即 critic 收敛后，才进 Step 3 写 case——**case 站在已校验的 primer 上**。

---

## 3. 执行 — case 决策链（站在 primer 上）

### Step 3：走决策链写 i_industry_case

#### 3.1 起点诊断（写正文前必做 · 借 `00-primer.md` §2.1）

因 primer 已建好行业地基，case 的起点诊断**轻量化**：只需确认 (a) 这个行业的**命门/特色** 1-3 个（利润池迁移最关键的张力在哪、给足篇幅）；(b) case① 该把哪些背景"甩给 primer"、自己只留决策导向速写。

> 命门**不从零拍脑袋**：以 00 的 `decomposition_v0` 为种子，读完 findings 后按 `_shared.md` §"B 轴有界 delta 重拆 + 收敛"做 delta 校验 → delta 非空则有界第二收料趟（封顶 2 轮）→ 落 `decomposition_v1`（changelog 防震荡）。

#### 3.2 逐环落地（链内无固定子节模板，每环给"必须落地什么"）

每环五样：**【元问题】/【为何由上一环逼出】/【必带硬落地】(决策机制保证，不可省)/【别漏的 lens】(01-08 当 checklist)/【自由区】**。

---

**环 ① 看懂这个行业（理解闸门）**
- 【元问题】这门生意/技术/赛道怎么运作？价值链长什么样、利润池此刻在哪段、由什么驱动？
- 【为何逼出】闸门——看不懂利润池在哪、被什么驱动，后面四环都是空中楼阁。
- 【必带硬落地】① **价值链全貌 + 利润池定位**：一句话行业模式 + 价值链各段 + 利润此刻集中在哪段、谁赚走（量×价×结构）；② **驱动因子 + 周期定位**：什么在推这个行业（技术/政策/需求/资本周期）+ 周期位（早期成长/中段加速/晚期分化/成熟饱和）。**周期定位 lens**（折自旧 02）：先判周期类型（需求 / 产能扩产-出清 / 库存补去 / 技术 S 曲线，多重叠加时说明主次），再用关键指标对照历史均值定位（库存天数 / 价格同比 / 产能利用率 / ROE 趋势），并指出"本轮周期的结束信号是什么"；③ **行业层多年财务弧线**：基于 Step 1 财务数据，给行业代表性主体 3 年（能取到则 5 年）营收/利润率/ROIC/FCF 走势 + 拐点，一句话定性这条弧线。直接为②反推提供根。
- 【别漏的 lens】旧 01 全景 / 02 周期 / 03 叙事的"这是什么生意"部分。
- 【自由区】三梁篇幅、用不用表；**背景深度甩给 primer，此处只留决策相关的（§1.2 分工）**。

**环 ② 市场/共识此刻替这行业定了什么价（定价锚 · 命门环）**
- 【元问题】当前估值/叙事反推出市场对这行业隐含了什么预期？偏乐观/中性/悲观？
- 【为何逼出】看懂了下一步必须问"现在多少钱"——行业没有单一价格，但脱离定价谈好坏无决策意义。
- 【必带硬落地 · 数字最硬的一环，否则整链失去脊柱】
  1. **带数字的反推**：用龙头 / 各细分代表的**估值倍数（PE/PS/EV-EBITDA）反推倍数隐含的增速预期**；写出最简式 `当前倍数 ⇐ 隐含增速 g × 终值倍数 × 折现率 r`。
  2. **相对水位**：相对**该行业自身历史区间 + 全球 peer** 的估值水位（历史高位/中位/低位）。
  3. **叙事 + 资金流**：主流叙事一句话 + 钱在追哪个子主题（拥挤）/ 冷落哪段。
  4. **隐含预期落成一句话** + 归类。
  5. **定价锚 × 证据强度张力（硬落地 · 与③缝合）**：②的隐含预期收口必须与③的结构性假设支持度交叉，**显式点出"市场在为③里哪条最弱的结构假设付溢价"**（定价笃定度 > 证据强度的陷阱）。不点透即视为②停在"定了什么价"、漏掉"这价踩在哪块虚地上"——chain-critic 必查。
- 【别漏的 lens】旧 02 周期/生命周期位置（影响反推口径）、旧 04 隐含预期与估值矩阵。
- 【自由区】用哪几个倍数、要不要同业横截面、矩阵怎么摆。

**环 ③ 这个价需要什么结构性假设为真（What-Must-Be-True）**
- 【元问题】要让②的定价成立，哪 3-5 件具体的结构性事必须发生/为真？
- 【为何逼出】把定价（结果）拆成前提（可证伪命题），④才能逐条判断、⑤才知道盯什么。这是②与④⑤的缝合环。
- 【必带硬落地】3-5 条结构性假设（利润池往哪迁、谁攫取价值、渗透曲线斜率、政策路径），每条具体、可观测、可验证，并标当前证据支持度。
- 【别漏的 lens】新链补的关键缺环，旧 8 份无独立对应。
- 【自由区】假设按对定价的杠杆排序。

**环 ④ 我对这行业整体什么立场 + 利润池落到哪几个 arena（下注）**
- 【元问题】围绕③的假设，我对这行业整体看多/中性/谨慎？利润池会落到哪几个细分 arena？我和共识在哪条迁移路径上分歧？
- 【为何逼出】③给了赌桌命题，这一环真正下注：先表行业整体 stance，再把判断分解到 arena 层。
- 【必带硬落地】
  1. **行业整体 stance 一句话**（看多/中性/谨慎）+ **我和共识的核心分歧一句话**（共识押哪条迁移路径、我押哪条、为什么）；
  2. **各 arena 沿 6 维判断**（利润池规模 / 增速 / 竞争结构 / 估值水位 / 周期位 / 综合）——**现 `_arena_select_spec.md` Step 3 的 6 维评分在此作下注工具**（查评分维度与口径，不照搬其表格结构）；每个 arena 判断**挂回③的具体假设**；
  3. **已研究子 arena 用实证**（亲属 hook）：若某 arena 已有成稿 case，用它的结论替代估算，按 §1.3 标来源 + 本维度复核。
- 【别漏的 lens】旧 03 叙事、旧 04 多空分歧、旧 09 的 arena 信号提取。
- 【自由区】arena 个数（≥5）、评分权重组合方式。

**环 ⑤ 如果错了会怎样、怎么第一时间知道（证伪机制）**
- 【元问题】行业判断错在哪种情形？哪些信号最早告诉我利润池没按我想的迁移？
- 【为何逼出】④下注后，理性立刻要求"怎么知道我错了"——无证伪的下注是信仰。
- 【必带硬落地】① 已知风险 + **盲点风险**各 ≥1；② **行业级 kill 触发条件**（叙事破灭 / 利润池没迁移 / 政策反转，尽量数据化）；③ **≥2 个历史行业镜鉴**（哪个曾经热门的行业利润没兑现 / 迁移没发生——如电信 capex、光伏）——每个标：失败模式 + 峰谷损失幅度% + 当年最早预警信号及"现在是否已现"，教训各一句话；**只想得到成功案例本身就是 red flag**；行业层镜鉴比 company 更值钱，给足篇幅；④ signpost（未来 3-12 月验证/证伪事件）。
- 【别漏的 lens】旧 05 镜鉴、旧 06 风险盲点。
- 【自由区】风险分组、镜鉴选案。

**环 ⑥ 资本/注意力怎么分配（行动 = 漏斗）**
- 【元问题】综合①-⑤，钱和注意力该投向哪几个 arena？哪些观察、哪些淘汰？
- 【为何逼出】①-⑤的收口——行业研究终点是可执行的 arena 分流。
- 【必带硬落地】① **强制三档分流**（深挖/观察/淘汰，每档 ≥1 个 arena）；② **tier = 吸引力 × 当前定价**：好 arena 但②判贵 → 进观察档 + 价格触发器，不直接深挖；③ **注意力预算**：深挖档建议 ≤N 个 + 为什么这几个优先（资源有限）；④ 每档触发器（深挖/观察必填非空 `upgrade_triggers` + `monitor_metrics`；淘汰填复活条件）；⑤ 建 arena stub（见 Step 4）。
- 【别漏的 lens】旧 09 全部（三档分流 + 评分 + 建议 slug）。
- 【自由区】档内排序、触发器形态。

#### 3.3 来源分层 + depth 降级

- **来源分层**（照搬 `00-primer.md` §2.3）：训练知识不标单条 / findings 凡引必标 `[mat-XXX]` / 亲属借用按 §1.3 标 / 特色判断文末点到指向 thesis_v1。文末 `## 信息来源` 给占比 + mat 列表。
- **depth 降级**（照搬 §2.4）：关键环数据缺口能训练知识粗估则标注"训练知识估算"，补不了明写"数据缺失"，**不编造**。瓶颈通常在 findings 覆盖度。

#### 3.4 产出形态（份数交给 LLM）

- **默认一份连贯文档** `i_industry_case.md`：决策链 ①→⑥ 作为主脉络，⑥ 的三档分流即旧 09 的 markdown 内容（不再单出 `industry_to_arenas.md`）。
- 长度逼迫（自评 >8000 字且体验下降）可拆 2-3 份，**必须保持链序** + 每份开头交代"在链哪一环、承接上一份什么结论"。拆分键名见 §5。
- 无论几份：**起点诊断、6 环（①三梁齐、②带数字、④含 stance + 6 维、⑥三档+tier）、09 sidecar、来源分层缺一不可**。

### Step 4：写 09 sidecar + 建 arena stub（**硬契约 · schema 原样不动**）

⚠️ dashboard.py 的行业层"竞技场选择"只读 `industry_to_arenas.yaml`、只认这套字段名。**禁自创/改名/漏字段**。

1. **写 `outputs/industry_to_arenas.yaml`**：字段从 ④/⑥ 提取，schema **逐字照 `_arena_select_spec.md` Step 6.5**（`slug / variant / topic_type=industry / display_name / generated / data_freshness / arenas[{name, suggested_slug, topic_created, topic_slug, scores{profit_pool,growth,competition,valuation,cycle,composite}, tier(deep/watch/eliminated), tier_reason, upgrade_triggers, monitor_metrics, revive_condition}] / cluster_tags`）。数字不加引号，缺失 null。`write_text` 落盘。
   > ⚠️ **写完即自检（机器↔叙事一致性 · dashboard 直接消费）**：① **composite 排序必须与 case ④综合评级同向**——同档内若 composite 与评级倒挂，必须在 case 显式写一句解释，否则 dashboard 按分排序会与叙事方向相反；② **tier 枚举 ↔ case 中文档名映射必须在 case 显式写一行**（深挖=deep / 观察=watch / 淘汰=eliminated），别让 dashboard 靠猜对齐档名。
2. **建 arena stub + 继承 thesis_v0**：对每个深挖档 arena，照 `_arena_select_spec.md` Step 6 + 6b **逐字执行**（`create_topic(topic_type='arena', parent_topic='{slug}')` → 收窄父 K# 到 arena 视角 → 写 stub `thesis_v0.md` 强度父级 -1）。这是父子链的自顶向下建链路径之一（图谱层 relink 是另一路径）。

---

## 4. 执行 — 收尾

### Step 5：落盘 + 状态注册 + **thesis_v1（最后）**

每份落盘后注册引用（键名：`00_primer` / `i_industry_case` / `industry_to_arenas`）：

```bash
python3 -c "
from prism.scripts.topic import set_output_status, set_output_referenced_mats, read_topic
t = read_topic('{slug}', '{variant}')
for key, mats in {'00_primer': [...], 'i_industry_case': [...], 'industry_to_arenas': [...]}.items():
    cur = t['outputs_state'].get(key, {}).get('version', 0)
    set_output_status('{slug}', key, 'fresh', '{variant}', version=cur+1)
    set_output_referenced_mats('{slug}', key, mats, '{variant}')
print('primer + case + 09 sidecar 已注册')
"
```

> 新键 `i_industry_case` 靠 `set_output_status` 的 `setdefault` 自动注册，**不用改 topic.py**。

**thesis_v1（决策链跑完后才写）**：照 `_shared.md` § thesis_v1 的 **Scheme C 全快照 11 段式**，不改。先读 `_synthesis_brief.md`，dump v0→v1 强度调整，写 `thesis_v1.md`，调 `set_thesis(version=1, ...)`。**同时写 `decomposition_v1.md` + `set_decomposition(version=1, summary, stage_set_at, convergence_status, changelog)`**（`summary`/`stage_set_at` 必填；`convergence_status ∈ {open, converged, capped}`；完整示例见 `_shared.md` §B 轴有界 delta 重拆）。收尾出**终态报告**（双轴 gap + 收敛状态 + 残留缺口诚实清单）。

**收尾**：照 `_shared.md` § 全部产出完成后（含 capped→suggested_drilldowns 回流）——`append_user_todos` + 清 `next_actions` + stage 推进。industry 合成完后 stage 置 `05-critic-review`（第 6 阶段「评审」，与 company/arena 统一）；**critic 对 industry 非强制（可选）**——可在对话里说「评审 {slug}」跑对抗式 steelman，或在 web 详情页点「✓ 标记完成」直接 `done`（旧名 `09-arena-shortlist` 已退休，勿再用）。

> **宏观横切（软提示 · 不强制）**：赛道/行业层多跨标的，宏观敏感度偏糊；如该赛道有显著利率/流动性/汇率暴露，**建议**（非强制）跑一遍 macro hook（见 `_company_case.md` Step 1 宏观横切 hook）补一段体制敏感度。不落 macro_stamp、不参与 staleness/coverage。

### Step 6：critic 校验（**对着决策链** · 写完即跑一轮内嵌 chain-critic）

写完即跑一轮**内嵌 chain-critic**（合成期质控，模型同 `00-primer.md` Step 3，已验证 2 轮内收敛）。它与下游 05-critic 分工：chain-critic 查"链有没有走通、有没有断"，05 做对抗式 steelman 重审。

dispatch 独立 critic（`subagent_type: general-purpose`，不传 model，**只读不写**），逐环校验链是否走通（文里没讲清就标"断"，不用文外知识补）：
- ① 看懂价值链 + 利润池定位 + 财务弧线？② **有带数字反推估值倍数/水位还是定性"很热"带过，且是否点出②的定价在为③里哪条最弱结构假设付溢价（定价锚×证据强度）**？③ 把②翻成 3-5 条可证伪结构假设？④ 行业整体 stance + 核心分歧一句话 + 各 arena 6 维评分？⑤ 有 kill+signpost+行业镜鉴？⑥ 三档齐 + **tier 锚在②的定价（不是只按好坏排）** + 注意力预算 ≤N？
- 断链检查：④下注↔⑤证伪、⑥分流↔②定价锚、⑥ tier↔④吸引力是否一致？**sidecar composite 排序↔case ④综合评级是否同向**（同档内倒挂必须在 case 显式解释，否则 dashboard 按分排序与叙事相反）？**tier 枚举↔case 中文档名映射**是否在 case 显式写明（深挖=deep/观察=watch/淘汰=eliminated）？
- primer↔case 是否有重复（case① 该甩 primer 的背景有没有甩）？
- 跨层复用护栏（§1.3）：借来的判断标了来源吗、有没有冒充本维度自验证？
- 源分层：findings 数字标 [mat-XXX]？
- 🎯 **目标达成核对（最重要 · 独立于上面所有"链内"检查）**：把本 topic `scope.question` 原文逐子句贴出
  ```bash
  python3 -c "from prism.scripts.topic import read_topic; print(read_topic('{slug}','{variant}')['scope']['question'])"
  ```
  逐子句核对 case 是否答到**可执行层**。**funnel 链"自洽走通" ≠ "答到了用户的问题"**——若问题终点超出 funnel 合同终点（典型：问"核心受益标的是谁"，而环⑥ 只停在 arena/赛道分流没落到可买标的），这是**结构性盲区，前面所有链内检查与 05 steelman 都查不出**（它们只评"在场的链/假设"，查不出"没摆上来但用户问了的维度"），必须在这一条抓。停浅即判**致命缺口**，不是扣分项。
- 🔒 **type-contract 终局证据强度核对（终局对齐 · 新增 · 独立于 question）**：不管 question 怎么写，**强制**检查终局环（环④ stance + 环⑥ arena 分流）的判断有几维靠**定性/data-missing**。
  - 读 sidecar `industry_to_arenas.yaml`（若存在）的 `honest_gaps` + case 环④/环⑥ 自述
  - 逐终局维度核：competition（竞争格局）/ valuation（估值水位）/ moat（护城河）/ growth（增长）——各判 `定量` / `定性有据` / `定性/data-missing`
  - **终局证据强度判定**：
    - ≥3 维 定量 → **强度可接受**，放行
    - ≥2 维 定性/data-missing（尤其 competition/valuation 双定性）→ 判 **「终局证据薄」**
  - **终局证据薄时的 escalate**：不放行浅终局，将薄弱维度翻成 `suggested_drilldowns`（`source=critic_weak_k`，`priority=P0`），附在 critic 修订清单中让主 agent 调 `set_suggested_drilldowns(mode='append')` 挂上。若 decomposition 对应命门已两轮未解 → 必要时 `set_decomposition(convergence_status='capped')`。

四段总评（链通不通 / 最严重 2-3 个断点 / **🎯 目标达成判定：原问题每个子句答到可执行层了吗、停浅在哪** / **🔒 终局证据强度：定量{}/定性有据{}/定性{}/，可接受或证据薄** / 只补一处补哪），苛刻直接，1800 字内。按反馈修订（主 agent 直接 Edit）。

**强制重修订门（有牙，非建议）**：首轮若判**断链** OR **目标未达成（停浅）** OR **终局证据薄**，必须跑第二轮。其中"目标未达成"的修订**不是改字，是实打实补回答缺口**——例如补"核心受益标的指认"段：标的 × 质地 × 定价 × 弹性 × 介入纪律矩阵 + 被 eliminated 的边界诚实反思（这正是本 variant eval→case v2 跑通的闭环）。"终局证据薄"时**不放行浅终局**——将薄弱维度翻成 `suggested_drilldowns`（`source=critic_weak_k`，`priority=P0`），主 agent 调 `set_suggested_drilldowns(mode='append')`；若 decomposition 对应命门已两轮未解，必要时 `set_decomposition(convergence_status='capped')`。补完重判，直到原问题每个子句都落到可执行层 + 终局证据可接受，chain-critic 才放行。

**critic-review 阶段（05）**：industry 可选进 `05-critic-review` 做对抗式重审。`05-critic-review.md` Step 1 已按 type 读 `i_industry_case.md`、rewrite_keys 用 `i_industry_case`。

### 汇报

```
✅ Industry 合成已生成（理解先行 → 决策链 ①→⑥ → thesis）
   00_primer v{N}（depth={deep/shallow}，critic {轮}轮收敛）
   i_industry_case v{N}{若拆分列出}
   industry_to_arenas.yaml（sidecar，dashboard 行业层契约）+ {n} 个 arena stub
   thesis_v1 v1{强度评分}

链体检：①看懂(价值链/利润池/财务弧线) ✓ / ②定价(隐含增速 {g}%/水位 {高中低}) ✓ / ③结构假设{n}条 ✓ / ④stance({看多/中性/谨慎}, arena {n}个) ✓ / ⑤kill{n}+行业镜鉴{n} ✓ / ⑥深挖{n}/观察{n}/淘汰{n} ✓
行业整体 stance：{一句话} / 深挖档：{arena 列表}
下一步：为深挖档 arena 推进研究（说「prism 推进 {arena-slug}」）或进入监控
```

---

## 附：与旧路径关系 + follow-up

| | 旧 industry 路径 | 本路径 |
|---|---|---|
| 组织原则 | 8 份并列维度 + 09 选拔表 | 理解先行 + 6 环决策链（⑥含选拔） |
| primer | 最后生成，消费 01-08 | **最先**生成，case 站其上（消费 findings+thesis_v0+K#+行业财务） |
| 结构约束 | 固定子节 + 09 模板 | 仅链 + 每环"必带硬落地"，子节自由 |
| ② 定价锚 | 04 隐含预期分散 | ①命门环：龙头倍数反推增速 + 相对水位（硬数字） |
| ④ 总体 stance | 无（仅逐 arena 打分） | 行业整体 stance + 共识分歧 + 6 维评分（作工具） |
| tier 排序 | 主要按吸引力（估值占 1/6 权重） | **吸引力 × 当前定价**（②做闸门） |
| 期望收益 | 无 | 刻意不做 EV（漏斗终点是 tier 分+触发器） |
| 产出份数 | 8 份 + 09 | 默认 1 份连贯 case（可拆，⑥含旧 09 内容） |
| 09 sidecar / arena stub | 09 内 | **不变，复用**（Step 4 引 `_arena_select_spec.md`） |
| 上游 findings / 财务 / thesis | — | **不变，复用** |
| 跨层复用 | 仅 parent_materials（raw findings） | Step1 亲属 hook（已生效）：向下站父 primer、向上拿子 case 当实证；借用受 §1.3 约束 |
| critic | 05（可选） | 内嵌 chain-critic + 05（已按 type 读 i_industry_case） |

# Company 投资 Case 合成（理解先行 · 决策链驱动 · 自由发挥版）

> **调度提示**：本文件是 **company 类型 topic 在 04-synthesize 阶段的完整规范**，整体替代 `_shared.md` + `01-08` 的 8 份分箱 spec。`industry` 走 `_industry_funnel.md`、`arena` 走 `_arena_funnel.md`（同构的漏斗决策链）。
>
> **复用上游、不重写**：00-research → 01-roadmap → 02-materials → 03-findings 产出的 findings、`gap_detector`、增量重写判定、`financial_data` 财务模块、dashboard sidecar、`00-primer.md`、`thesis` 全部沿用，本文件只重做"合成"这一段。
>
> **07 sidecar schema 保留**：`07-decision-kit.md` 不删——它作为 **⑥ 的 sidecar schema(Step 3.5)** 权威定义被本文件 Step 4 + `_shared.md` 逐字引用（查 schema，不照搬结构）。与 industry 的 `09-industry-to-arenas.md` / arena 的 `10-peer-matrix.md` 同性质（均为保留的工具/schema 规范）。

---

## 0. 定位与边界

旧的 company 合成把内容切成 8 份**并列研究维度**，骨架按 industry 形状刻、company 硬套；且把"领域入门(primer)"放在**最后**生成——等于先下结论、再补领域解释，让决策建在作者未经校验的隐式理解上。

本文件两处根本改动：

1. **理解先行**：先出 `00_primer`（领域/公司理解地基，critic 校验"门外人真懂了"），**决策链显式站在它之上**。理解永远在决策上游——你不能给看不懂的生意估值。
2. **按决策因果链组织**（不是并列维度）：每一环都是上一环**逼出来的**，读者顺着读就是顺着一次完整的买卖决策在想。

- **不变的是骨架（理解先行 + 决策链 6 环 + sidecar schema）**——保证逻辑紧、决策机制不丢、跨 topic 可比。
- **自由的是血肉**——每环问什么子问题、怎么组织、详略、用什么方式让门外人最好懂、产出拆几份，交给 LLM 针对这家公司的命门判断。
- 01-08 不再是骨架，降级成一张"别漏维度"的对照清单。

---

## 1. 核心方法

沿用 `00-primer.md` 已验证的"给目标 + 自由发挥 + 独立 critic 校验"闭环，但分两层落地：**primer 是上游理解地基（纯自由发挥），case 是下游决策（自由发挥锚定在决策链上）。**

### 1.1 不变的元目标（逐字不改）

> **一个门外人为了做出买/卖/不动的决策，正在研究这家公司。先让他读懂这门生意所在的领域与公司本身（primer）；再带他走完一条决策链：看懂生意 → 市场定了什么价 → 这价要什么为真 → 我信哪边 → 错了怎么知道 → 那就怎么做。读完既入了门，也拿到一套可执行的决策机制。**

### 1.2 理解先行：primer 与 case 的依赖与分工（**核心规约**）

|                       | 谁先生成               | 读者       | 干什么                  | 谁依赖谁      |
| --------------------- | ------------------ | -------- | -------------------- | --------- |
| **00_primer**         | **先**（理解地基）        | 完全门外人    | 看懂领域/公司**本身**，不被术语挡住 | 被 case 依赖 |
| **c_investment_case** | **后**（站在 primer 上） | 要做买卖决定的人 | 看懂**该不该买、什么价、会怎么错**  | 依赖 primer |
| **thesis_v1**         | **最后**（提炼快照）       | 持有期追踪者   | 把下好的注，提炼成可追踪快照       | 依赖 case   |

时间轴：**学懂领域(primer) → 做决策(case) → 持续追踪(thesis)**。生成顺序 = 阅读顺序。

**primer↔case 分工（杀掉两者重复，硬规约）**：
- **primer** = 教科书级、可独立读懂的领域/公司背景（深讲商业模式机理、术语、产业链、玩家）。
- **case 环①** = **已假定读者读过 primer** 的"决策导向速写"——只点"钱怎么来 + 哪个张力直接影响估值"，**不重教 primer 已讲透的背景**，需要深度就写"详见 primer"。
- 例外：若用户明示跳过 primer，则 case① 退回"自带压缩版理解"（自洽，可独立读）。原则不变：**理解永远在决策上游；primer 是这份上游理解的完整外化形态，存在时排最前。**

### 1.3 决策链（6 环 · 这就是契约本身）

**必须按序走完整条链，每一环必须落地（见 §3.2 各环硬约束）。不允许断链（如有 ④ 下注却无 ⑤ 证伪、有 ⑥ 行动却无 ② 锚）。**

```
① 能不能看懂这家公司？
   └─ 看不懂/信不过就不投。三梁：生意怎么赚钱+护城河+单位经济 / 管理层与资本配置 / 多年财务轨迹。这是闸门。
        ↓ 看懂也信得过了，那它现在被定了什么价——
② 市场此刻替它定了什么价？
   └─ 反推当前价隐含的预期（必须有数字）。这是后面一切判断的锚。
        ↓ 这个定价，
③ 需要什么假设为真？
   └─ What-Must-Be-True：把②的定价翻译成 3-5 条可证伪的具体假设。
        ↓ 这些假设，
④ 我信哪边，凭什么？
   └─ 多空交锋 + 核心分歧一句话 + 观点光谱 + 我的判断 + 期望收益加总（概率×回报求和）。这是下注。
        ↓ 我这个判断，
⑤ 如果错了会怎样、怎么第一时间知道？
   └─ 风险/盲点 + 历史失败镜鉴 + kill 触发 + signpost。这是证伪机制。
        ↓ 综合①-⑤，
⑥ 那就在什么价、什么仓位、什么时点，做什么？
   └─ 买入框 + 仓位框架(接④的EV) + 加减仓阶梯 + 时间维度 + 什么会让我改主意。这是行动。
```

**为什么是紧的**：③ 只因②产出定价才存在；④ 的 EV 加总把光谱压成一个数；⑥ 的仓位由④的 EV 决定；⑤ 只因④下注才需要。环与环是因果序、不是并列箱。

### 1.4 跨层复用质量护栏（**硬规约 · 与 Step 1 亲属 hook 配套**）

跨层复用是"站在肩膀上"，**不是"继承结论"**。亲属（父 arena / 父 industry；company 通常是叶子，子级多为空）的蒸馏产出只作输入/参照，质量永远按本维度、本 topic 自身的 findings + 自身的 critic 来卡：
1. **本维度自己跑完整链**：照常跑 primer + 6 环 + critic，全程按 company 级分辨率要求。亲属产出是脚手架不是正文。
2. **质量闸门一律本地**：`gap_detector`、chain-critic、05-critic、来源分层都对着**本 topic 自己的 K# 和 findings** 跑，不因"父 arena/industry 已覆盖"放水。
3. **借来必标来源**：正文里 borrowed-from-relative 的内容可见地标出（对齐 mat-XXX 分层惯例），不许借来的框架冒充本 topic 自验证的结论。
4. **冲突时本维度赢**：亲属观点与本 topic 自己的 findings 打架 → 以本 topic 为准，允许背离；背离触发向上路径把亲属标 stale（`gap_detector` 的 `relative_updated` flag 会提示亲属产出比本 case 新）。

---

## 2. 执行 — 上游准备与 primer 先行

### Step 0：前置检查 + gap 体检（双轴）+ 增量判定 + 命门 delta 重拆（**引用 `_shared.md`，不重抄**）

进 04 第一件事，照 `_shared.md` 跑三段，结果完整贴对话：

1. **前置检查**（资料 ≥3 份，否则停）。
2. **gap 体检**（`detect_gaps` 三项任一非空 → 不要硬合成，先补救）。
3. **增量重写判定**（`list_affected_outputs` 判 new/stale/fresh；`fresh` 跳过）。company 路径 output_key 见 §5。

> Web 搜索路径见 [[_web_search_routing]]；本阶段默认走 adapter。即兴 web-search 规约见 `_shared.md`。

### Step 0.5：质量红线门控（company 专属 · 折自旧 03b · 写正文前先筛）

进 case 正文前先过一遍质量红线，过滤明显不合格的公司——避免对早该 quarantine 的标的做完整深研。**仅 company 跑**（industry/arena 无此闸门）。

1. **拉财务自动红线数据**：
   ```bash
   python -c "from prism.scripts.financial_data import get_quality_screen_data; print(get_quality_screen_data('{slug}', '{variant}'))"
   ```
   财务红线（无数据则标"数据缺失，用户判断"，不编造）：

   | 红线 | 阈值 |
   |------|------|
   | ROIC vs WACC | 最近 3 年 ROIC > WACC |
   | 自由现金流 | 最近 3 年 ≥2 年为正 |
   | 资产负债率 | 行业内非 outlier（< 行业 90 分位） |
   | 商誉占净资产 | < 30% |
   | 经营现金流/净利润 | 3 年均值 > 0.7 |

2. **从 findings 查治理 + 业务红线**：
   - 治理：大股东质押率 < 50% / 审计意见标准无保留 / 关联交易占比 < 20% / 无重大违规立案 / 无高管 3 年内大额减持
   - 业务：主业明确（CR1 > 50% 或多元化合理）/ 客户集中度可接受（CR5 < 80%）/ 无明显商业模式过气信号

3. **综合判定**：
   - **PASS**（全过 / 不通过 ≤1 且非致命）→ 继续 Step 1 完整合成。
   - **FAIL**（致命红线任一触发：财务造假 / 重大违规 / ROIC 长期 < WACC）→ quarantine，不再深研：
     ```bash
     python -c "from prism.scripts.topic import set_stage, set_next_actions; set_stage('{slug}','quarantined','{variant}'); set_next_actions('{slug}',['已 quarantine，不再继续研究'],'{variant}')"
     ```
     并把 quarantine 摘要归档到 `prism/quarantine/{slug}.md`。
   - **NEEDS-REVIEW**（1-2 项非致命不通过）→ `AskUserQuestion` 问用户是否豁免；豁免则继续，否则 quarantine。

> 门控结果完整贴对话。命门若正落在某条红线上（如治理风险即命门），该红线在 case 环①管理层梁 / 环⑤证伪里要展开，不只在门控里打勾。

### Step 1：加载 findings + thesis_v0 + **财务数据（finance 模块）**

1. 照 `_shared.md` § 调度模式：`format_findings_for_prompt` 列 findings → 主 agent 并行 Read；`build_findings_index` 落盘 `_findings_index.md`（防 compact 地图）；读 `thesis_v0.md`（强度 v0→v1 锚）。
2. **拉财务数据（多年轨迹来源，喂①的财务梁 + ②的反推口径）**：

   ```bash
   python3 -c "
   from prism.scripts.financial_data import ensure_financials, get_financial_context
   ensure_financials('{slug}', '{variant}')
   print(get_financial_context('{slug}', '{variant}'))
   "
   ```

   返回：最新报告期 / 营收 / 归母净利 / 毛利率 / ROE / 资产负债率 / FCF / 商誉占净资产 + **3 年 ROIC + 3 年 FCF**。这是①财务轨迹梁与②反推的一手锚；不在 findings 里手抽。市价/估值口径另调 `market_data.get_valuation_context`。
3. 写 `outputs/_synthesis_brief.md`：dump 核心 thesis / 关键假设 / v0→v1 强度调整，供 ④⑤⑥ 与 critic 复用。

> **亲属复用 hook（已生效）**：若本 topic 有 `parent_topic`（或 `find_child_topics` 返回非空），调 `get_relative_outputs('{slug}','{variant}')` 取亲属**成稿产出路径**并 Read。**借来内容受 §1.4 约束**——脚本只返路径不读内容，借用永远是输入/参照：必标来源、质量按本维度自跑、冲突时本 topic 赢。
> - **向下（父 arena/industry → 本 company）**：company primer 站在父 primer 上扩写、不重教；读父最新 thesis；读**父 sidecar（`10_peer_matrix` / `09_industry_to_arenas`）里点名本公司的那行 = 本 company 的"mandate"**（父级为什么把我放深研档、预期洞见、预填狩猎问题），①从这里起、②③去验证/修正它。
> - **向上（子 → 本 company）**：company 通常是叶子，`children` 多为空；若有（极少，如控股母子结构），按 §1.4 护栏当一等证据、本维度复核。
> - 无亲属 → 返空 → 退化为独立合成，零特判。

> **调度模式**：company case 默认**主 agent 直做 + 并行 Write**（同 `_shared.md` 默认；勿 dispatch subagent 写长产出，见 [[subagent-write-hallucination]] / feedback_subagent_bulk_synthesis）。唯一 subagent 是 critic（只读不写）。

### Step 2：**先出 `00_primer`（理解地基）**

按 `00-primer.md` Step 1-5 执行，产 `outputs/00_primer.md` + `_prism_reading_guide.md`。

**走 `00-primer.md` 的 primer-first 路径**（00-primer.md 已全类型统一 primer-first，见其头部调度提示）：
- 原材料 = **findings + `thesis_v0` + K# + 上面的财务数据**。
- 投资加权（"该讲商业模式/估值锚/风险/催化剂"）来自元目标 + thesis_v0 + K#，**不需要等 case**。
- primer 其余流程（目标生成 / 起点诊断 / 自由发挥 / 来源分层 / depth 降级 / **独立 critic 校验**）照走，critic 不可省。
- primer 写完即 critic 收敛后，才进 Step 3 写 case——**case 站在已校验的 primer 上**。

---

## 3. 执行 — case 决策链（站在 primer 上）

### Step 3：走决策链写 c_investment_case

#### 3.1 起点诊断（写正文前必做 · 借 `00-primer.md` §2.1）

因 primer 已建好领域地基，case 的起点诊断**轻量化**：只需确认 (a) 这家公司的**命门/特色点** 1-3 个（命门所在的环重点打、给足篇幅）；(b) case① 该把哪些背景"甩给 primer"、自己只留决策导向速写。

> 命门**不从零拍脑袋**：以 00 的 `decomposition_v0` 为种子，读完 findings 后按 `_shared.md` §"命门有界 delta 重拆 + 收敛"做 delta 校验（新增/掉队/重排/置信度更新）→ delta 非空则有界第二收料趟（封顶 2 轮）→ 落 `decomposition_v1`（changelog 防震荡）。

#### 3.2 逐环落地（链内无固定子节模板，每环给"必须落地什么"）

每环五样：**【元问题】/【为何由上一环逼出】/【必带硬落地】(决策机制保证，不可省)/【别漏的 lens】(01-08 当 checklist)/【自由区】**。子问题、子标题、表格、详略、类比全在自由区。

---

**环 ① 看懂并信得过这家公司（理解闸门 · 三梁）**
- 【元问题】这门生意怎么赚钱、护城河强弱？掌舵的人靠不靠谱、钱配得好不好？多年的财务弧线长什么样？
- 【为何逼出】闸门——看不懂的生意 / 信不过的管理层，后面四环都是空中楼阁。**"是否值得长期持有"尤其吃这一环**。
- 【必带硬落地 · 三梁缺一不可】
  1. **生意与护城河**：一句话生意模式 + 收入拆解（量×价×结构）；护城河类型 + 正在变强/变弱的判断；至少一组单位经济数字（毛利/单客/ROIC 取最关键那个）。
  2. **管理层与资本配置**（长期持有的一等公民，不再只当风险脚注）：① 谁在掌舵 + 任期/track record；② **资本配置记录**（回购/分红/并购/再投资的历史回报与去向）；③ 激励是否与小股东对齐（薪酬结构 / 持股 / dual-class 等治理）；④ 一句话评：这是一个值得托付 3-5 年的配置者吗？（与 ⑤ 治理风险、⑥ 持有期呼应）
  3. **多年财务轨迹**（趋势，不是快照）：基于 Step 1 的 `get_financial_context`，给 **3 年（能取到则 5 年）的营收/利润率/ROIC/FCF 走势 + 拐点**，一句话定性这条弧线（持续复利 / 见顶回落 / 反转早期）。这条直接为②的反推估值提供根。
- 【别漏的 lens】旧 01 全景 / 03 叙事的"这是什么生意"部分。
- 【自由区】三梁的篇幅分配、用不用表、类比；**背景深度甩给 primer，此处只留决策相关的（primer↔case 分工，§1.2）**。

**环 ② 市场此刻替它定了什么价（定价锚）**
- 【元问题】当前价/估值反推出市场隐含了什么预期？偏乐观/中性/悲观？
- 【为何逼出】看懂也信得过了，下一步必须问"现在多少钱"——脱离定价谈好坏无决策意义。
- 【必带硬落地 · 数字最硬的一环】
  1. **带数字的反推**：以当前价反推隐含的 3-5 年净利润 CAGR / 终值 PE / 隐含 IRR。最简式写出：`当前价 P ⇐ CAGR g × 终值PE × 折现率 r`。
  2. **估值原型识别 → 选 2-3 个模型独立估值**（§3.3 工具箱）。各自给 bull/base/bear，不取平均。
  3. **隐含预期落成一句话** + 归类。
- 【别漏的 lens】旧 02 周期/生命周期位置（影响反推口径）、旧 04 隐含预期与估值矩阵。
- 【自由区】用哪几个模型、矩阵怎么摆、要不要同业横截面反推。

**环 ③ 这个价需要什么为真（What-Must-Be-True）**
- 【元问题】要让②的定价成立，哪 3-5 件具体的事必须发生/为真？
- 【为何逼出】把定价（结果）拆成前提（可证伪命题），④才能逐条判断、⑤才知道盯什么。这是②与④⑤的缝合环。
- 【必带硬落地】3-5 条假设，每条具体、可观测、可验证，并标当前证据支持度。
- 【别漏的 lens】新链补的关键缺环，旧 8 份无独立对应。
- 【自由区】假设按对定价的杠杆排序。

**环 ④ 我信哪边，凭什么（下注 + 期望收益加总）**
- 【元问题】围绕③的假设多空各怎么说？核心分歧？我信哪边、信心多少？**这注的期望收益是正是负？**
- 【为何逼出】③给了赌桌命题，这一环真正下注：表态 + 给理由 + 把光谱算成一个数。
- 【必带硬落地】
  1. **核心分歧一句话**；
  2. **观点光谱**（5 级或多空双方，每档挂到③的具体假设 + 概率 + 对应估值/回报）；
  3. **期望收益加总**（新增）：`E[return] = Σ(各档概率 × 该档回报中点)`，算出一个数并判正负。这是把定性光谱压成定量下注，**直接喂⑥的仓位**（EV≤0 → 当前价不建仓/等回调；EV 显著为正 → 可放大首仓）。
  4. **我的判断 + 信心度（高/中/低）+ 凭什么**——资料够才下，不够明说"待 X 才判"。
- 【别漏的 lens】旧 03 叙事、旧 04 多空分歧。
- 【自由区】光谱档数、回报区间取点方式。

**环 ⑤ 如果错了会怎样、怎么第一时间知道（证伪机制）**
- 【元问题】判断错在哪种情形？错了亏多少？哪些信号最早告诉我错了？
- 【为何逼出】④下注后，理性立刻要求"怎么知道我错了"——无证伪的下注是信仰。
- 【必带硬落地】① 已知风险 + **盲点风险**各 ≥1；② **kill 触发条件**（具体、可观测、尽量价格化/数据化 → 喂 sidecar `kill_criteria`）；③ **≥2 个历史失败镜鉴**（相似剧本怎么崩）——每个标：失败模式（颠覆/周期顶/政策反转/现金流断裂/竞争击穿）+ 峰谷损失幅度% + 当年最早预警信号及"现在是否已现"，教训各一句话；**只想得到成功案例本身就是 red flag**；④ signpost（未来 3-12 月验证/证伪事件 → 喂 sidecar `signposts`）。治理类风险与①的管理层梁呼应。
- 【别漏的 lens】旧 05 镜鉴、旧 06 风险盲点。
- 【自由区】风险分组、镜鉴选案。

**环 ⑥ 在什么价/仓位/时点做什么（行动）**
- 【元问题】综合①-⑤现在买/加/持/减/弃？什么价？首仓/满仓多少？分几档加？持多久？什么会让我改主意？
- 【为何逼出】①-⑤的收口——研究终点是可执行动作。
- 【必带硬落地】① **买入框**（基于②反推估值，不凭空 → 喂 sidecar `buy_box`）；② **仓位框架**（首仓/满仓上限/加仓阶梯/集中度，**首仓大小参考④的 EV** → 喂 sidecar `position_framework`）；③ 时间维度（持有期 + 下一 catalyst 时点 + "到 X 未发生 Y 怎么办"，持有期与①管理层信任度呼应）；④ **什么会让我改主意**（与⑤的 kill 呼应 + 上修 thesis 的正向信号）；⑤ 研究成熟度自评。
- 【别漏的 lens】旧 07 决策辅助全部。
- 【自由区】区间/阶梯怎么分。

#### 3.3 来源分层 + depth 降级 + 估值模型库

- **来源分层**（照搬 `00-primer.md` §2.3）：训练知识不标单条 / findings 凡引必标 `[mat-XXX]` / 特色判断文末点到指向 thesis_v1。文末 `## 信息来源` 给三者占比 + mat 列表。
- **depth 降级**（照搬 §2.4）：关键环数据缺口能训练知识粗估则标注"训练知识估算"，补不了明写"数据缺失"，**不编造**。瓶颈通常在 findings 覆盖度（robinhood/荣昌验证）。
- **估值模型库**（环②工具箱）：先判原型（高 PE 成长 / 订单驱动 / 成熟现金流 / 周期反转 / 资产资源 / 银行保险）再选 2-3 模型独立估值。原型识别表 + 模型 A–H 算法 + 估值矩阵汇总格式见 **`_valuation_models.md`**（共享规范，**仅查算法，结构不照搬**）。末尾给"估值矩阵汇总"表 + 一句"分歧来自哪个假设"。

#### 3.4 产出形态（份数交给 LLM）

- **默认一份连贯文档** `c_investment_case.md`：决策链 ①→⑥ 作为主脉络，读者顺读即顺着决策走。
- 长度逼迫（自评 >8000 字且体验下降）可拆 2-3 份，**必须保持链序** + 每份开头交代"在链哪一环、承接上一份什么结论"。拆分键名见 §5。
- 无论几份：**起点诊断、6 环（①三梁齐、④含 EV）、sidecar、来源分层缺一不可**。

### Step 4：写 sidecar `07_decision_kit.yaml`（**硬契约 · schema 原样不动**）

⚠️ dashboard.py 只读这一个文件、只认这套字段名。**禁自创/改名/漏字段**，否则该 topic dashboard 整行为空。文件名固定 `07_decision_kit.yaml`（即使主文档已改名）。字段从②/④/⑤/⑥提取，schema **逐字照 `07-decision-kit.md` Step 3.5**：`slug / variant / topic_type=company / display_name / ticker / generated / data_freshness / buy_box / position_framework / valuation_models / kill_criteria / signposts / cluster_tags`。数字不加引号，缺失 null。写入用 `Path(...).write_text(...)`。

---

## 4. 执行 — 收尾

### Step 5：落盘 + 状态注册 + **thesis_v1（最后）**

每份落盘后注册引用：

```bash
python3 -c "
from prism.scripts.topic import set_output_status, set_output_referenced_mats, read_topic
t = read_topic('{slug}', '{variant}')
for key, mats in {'00_primer': [...], 'c_investment_case': [...], '07_decision_kit': [...]}.items():
    cur = t['outputs_state'].get(key, {}).get('version', 0)
    set_output_status('{slug}', key, 'fresh', '{variant}', version=cur+1)
    set_output_referenced_mats('{slug}', key, mats, '{variant}')
print('primer + case 产出已注册')
"
```

**thesis_v1（决策链跑完后才写）**：照 `_shared.md` § thesis_v1 的 **Scheme C 全快照 11 段式**，不改。先读 `_synthesis_brief.md`，dump v0→v1 强度调整，写 `thesis_v1.md`，调 `set_thesis(version=1, ...)`。**同时写 `decomposition_v1.md` + `set_decomposition(version=1, convergence_status, changelog)`**（B 层与 thesis 配对升版，见 `_shared.md` §命门有界 delta 重拆）。收尾出**终态报告**（双轴 gap + 收敛状态 + 残留缺口诚实清单），见 `_shared.md` §终态报告。

**收尾**：照 `_shared.md` § 全部产出完成后——`append_user_todos` + 清 `next_actions` + stage 推进。company 必须进 `05-critic-review` 才能 `done`：

```bash
python3 -c "from prism.scripts.topic import set_stage; set_stage('{slug}', '05-critic-review', '{variant}'); print('→ 评审 {slug}')"
```

> **可选 primer 补丁**：若 case 暴露 primer 漏讲的命门（如某条命门假设需要的背景 primer 没铺），回头给 primer 打一个便宜补丁（局部 Edit + 升 version），不重写。primer 是上游，但允许一次下游反馈触碰。

### Step 6：critic 校验（**对着决策链** · 写完即跑一轮内嵌 chain-critic）

写完即跑一轮**内嵌 chain-critic**（合成期质控，模型同 `00-primer.md` Step 3，已验证 2 轮内收敛）。它与下游 05-critic 分工：chain-critic 查"链有没有走通、有没有断"，05 做对抗式 steelman 重审。

dispatch 独立 critic（`subagent_type: general-purpose`，不传 model，**只读不写**），逐环校验链是否走通（文里没讲清就标"断"，不用文外知识补）：
- ① 看懂生意 + 管理层可信 + 财务轨迹清楚？② 有带数字反推还是定性带过？③ 把②翻成 3-5 条可证伪假设？④ 核心分歧一句话 + 真表态 + **EV 算出来了吗**？⑤ 有 kill+signpost+镜鉴？⑥ 买入框锚在②、首仓参考④的 EV？
- 断链检查：④下注↔⑤证伪、⑥行动↔②锚、⑥仓位↔④的 EV 是否一致？
- primer↔case 是否有重复（case① 该甩 primer 的背景有没有甩）？
- 源分层：findings 数字标 [mat-XXX]？

三段总评（链通不通 / 最严重 2-3 个断点 / 只补一处补哪），苛刻直接，1800 字内。按反馈修订（主 agent 直接 Edit）；首轮涉断链则跑第二轮。

**critic-review 阶段（05）**：仍按 company 规则进 `05-critic-review` 做对抗式重审。`05-critic-review.md` Step 1 已按 type 读 `c_investment_case.md`、rewrite_keys 用 `c_investment_case`——用户说「评审 {slug}」直接跑，无需手动替换。

### 汇报

```
✅ Company 投资 Case 已生成（理解先行 → 决策链 ①→⑥ → thesis）
   00_primer v{N}（depth={deep/shallow}，critic {轮}轮收敛）
   c_investment_case v{N}{若拆分列出}
   07_decision_kit.yaml（sidecar，dashboard 契约）
   thesis_v1 v1{强度评分}

链体检：①看懂(生意/管理层/财务轨迹) ✓ / ②定价(隐含IRR {irr}%) ✓ / ③假设{n}条 ✓ / ④判断({信心度}, EV={ev}%) ✓ / ⑤kill{n}+signpost{n} ✓ / ⑥买入框({zone}) ✓
当前价 {P} / base 中枢 {V} / 强力买入 {lo}-{hi} / 期望收益 {ev}%
下一步：说「评审 {slug}」进 05 对抗式重审
```

---

## 附：与旧路径关系 + follow-up

| | 旧 company 路径 | 本路径 |
|---|---|---|
| 组织原则 | 8 份并列维度 | 理解先行 + 6 环决策链 |
| primer | **最后**生成，消费 01-08 | **最先**生成，case 站其上（消费 findings+thesis_v0+K#） |
| 结构约束 | 固定子节 + `{content}` 骨架 | 仅链 + 每环"必带硬落地"，子节自由 |
| 管理层&资本配置 | 风险脚注 | ①一等公民（三梁之一） |
| 财务轨迹 | 单期快照散落 | ①多年趋势梁（`get_financial_context`） |
| 期望收益 | 无 | ④概率×回报加总 → 喂⑥仓位 |
| 产出份数 | 固定 8 份 | 默认 1 份连贯 case（可拆），LLM 定 |
| sidecar | `07_decision_kit.yaml` | **不变**（硬契约） |
| 上游 00-03 / 财务模块 / thesis | — | **不变，复用** |
| 估值模型库 | 04 内 | **抽成共享片段 `_valuation_models.md`**（§3.3 工具箱引用） |
| critic | 05-critic（旧键） | 内嵌 chain-critic + 05（已按 type 读 c_investment_case） |

**接线现状（均已落到被调用方自身，无内联兜底）**：
1. `05-critic-review.md` Step 1 已按 type 读 `c_investment_case` / `i_industry_case` / `a_arena_case`（旧 8 份路径仍读 04/06/07）；rewrite_keys 注释含三个决策链键。✓
2. `00-primer.md` 已**全类型统一 primer-first**（findings+thesis_v0+K#，不依赖 01-08/thesis_v1，旧 primer-last 已退休）。✓
3. `SKILL.md`：合成路由按 type 指向 `_company_case` / `_industry_funnel` / `_arena_funnel`；primer 路由行已统一 primer-first。✓
4. industry/arena 同构路径见 `_industry_funnel.md` / `_arena_funnel.md`（漏斗终局，⑥ 折入旧 09/10 选拔，sidecar schema 不变）。✓

# Industry 合成 type 卡（配 `_case_chain.md` 使用 · 漏斗终局）

> 执行顺序：先读 `_case_chain.md` 骨架（定位/分工/护栏/链因果序/Step 0/Step 1 调度/Step 2 primer/§3.1/§3.3/§3.4/Step 5/Step 6 骨架/汇报骨架），在骨架点名"→ 见 type 卡"处回到本卡。本卡只装 industry 专属：元目标 + 6 环【必带硬落地】+ 取数口径（行业财务 + 龙头估值 + F13 checkpoint + 亲属 hook）+ 产出形态 + sidecar + 收尾 + critic 特化（含🎯目标达成核对 + 强制重修订门）+ 汇报填空。
> SKILL 路由：`industry` → 读 `_case_chain.md` + 本卡。
> case key = `i_industry_case`；sidecar = `industry_to_arenas.yaml`（schema 见 `_arena_select_spec.md`）。primer↔case 分工表（读者=要分配资本/注意力的人 / 干什么=看懂利润池往哪迁、哪几个 arena 值得投）；边界侧重：**地图归 primer，动态方向判断（利润池往哪迁、定价对不对）归 case**，industry 的 primer↔case 重叠面比 company 大，chain-critic 必查。

---

## §元目标（逐字不改）

> **一个门外人为了配置资本，正在研究这个行业。先让他读懂这门生意/技术/赛道本身（primer）；再带他走完一条决策链：看懂行业 → 市场给这行业定了什么价 → 这价要什么结构性假设为真 → 利润池会落到哪几个 arena、我信哪条迁移路径 → 错了怎么知道 → 那资本/注意力就怎么分配。读完既入了门，也拿到一套可执行的 arena 分流机制。**

---

## §取数口径（Step 1：行业财务 + 龙头估值 2b + F13 checkpoint + 亲属 hook）

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

---

## §6 环【必带硬落地】（决策链主体 · 一字不改 · 含环②定价锚×证据强度张力）

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


---

## §产出形态（补 `_case_chain.md` §3.4 的 industry 专属项）

- **默认一份连贯文档** `i_industry_case.md`：决策链 ①→⑥ 作为主脉络，⑥ 的三档分流即旧 09 的 markdown 内容（不再单出 `industry_to_arenas.md`）。
- 长度逼迫（自评 >8000 字且体验下降）可拆 2-3 份，**必须保持链序** + 每份开头交代"在链哪一环、承接上一份什么结论"。拆分键名见 §5。
- 无论几份：**起点诊断、6 环（①三梁齐、②带数字、④含 stance + 6 维、⑥三档+tier）、09 sidecar、来源分层缺一不可**。

---

## §sidecar（Step 4：写 09 sidecar + 建 arena stub · 硬契约 schema 原样不动）

⚠️ dashboard.py 的行业层"竞技场选择"只读 `industry_to_arenas.yaml`、只认这套字段名。**禁自创/改名/漏字段**。

1. **写 `outputs/industry_to_arenas.yaml`**：字段从 ④/⑥ 提取，schema **逐字照 `_arena_select_spec.md` Step 6.5**（`slug / variant / topic_type=industry / display_name / generated / data_freshness / arenas[{name, suggested_slug, topic_created, topic_slug, scores{profit_pool,growth,competition,valuation,cycle,composite}, tier(deep/watch/eliminated), tier_reason, upgrade_triggers, monitor_metrics, revive_condition}] / cluster_tags`）。数字不加引号，缺失 null。`write_text` 落盘。
   > ⚠️ **写完即自检（机器↔叙事一致性 · dashboard 直接消费）**：① **composite 排序必须与 case ④综合评级同向**——同档内若 composite 与评级倒挂，必须在 case 显式写一句解释，否则 dashboard 按分排序会与叙事方向相反；② **tier 枚举 ↔ case 中文档名映射必须在 case 显式写一行**（深挖=deep / 观察=watch / 淘汰=eliminated），别让 dashboard 靠猜对齐档名。
2. **建 arena stub + 继承 thesis_v0**：对每个深挖档 arena，照 `_arena_select_spec.md` Step 6 + 6b **逐字执行**（`create_topic(topic_type='arena', parent_topic='{slug}')` → 收窄父 K# 到 arena 视角 → 写 stub `thesis_v0.md` 强度父级 -1）。这是父子链的自顶向下建链路径之一（图谱层 relink 是另一路径）。

---

## §收尾（Step 5 · industry 专属：stage 推进 + 退休 stage 名 + 宏观软提示）

**收尾**：照 `_shared.md` § 全部产出完成后（含 capped→suggested_drilldowns 回流）——`append_user_todos` + 清 `next_actions` + stage 推进。industry 合成完后 stage 置 `05-critic-review`（第 6 阶段「评审」，与 company/arena 统一）；**critic 对 industry 非强制（可选）**——可在对话里说「评审 {slug}」跑对抗式 steelman，或在 web 详情页点「✓ 标记完成」直接 `done`（旧名 `09-arena-shortlist` 已退休，勿再用）。

> **宏观横切（软提示 · 不强制）**：赛道/行业层多跨标的，宏观敏感度偏糊；如该赛道有显著利率/流动性/汇率暴露，**建议**（非强制）跑一遍 macro hook（见 `_type_company.md` §取数 宏观横切 hook）补一段体制敏感度。不落 macro_stamp、不参与 staleness/coverage。

---

## §critic 特化（Step 6 逐环问句 + 🎯目标达成核对 + 🔒终局证据强度 + 强制重修订门）

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

---

## §汇报

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

# Arena 合成 type 卡（配 `_case_chain.md` 使用 · 漏斗终局）

> 执行顺序：先读 `_case_chain.md` 骨架（定位/分工/护栏/链因果序/Step 0/Step 1 调度/Step 2 primer/§3.1/§3.3/§3.4/Step 5/Step 6 骨架/汇报骨架），在骨架点名"→ 见 type 卡"处回到本卡。本卡只装 arena 专属：元目标 + 6 环【必带硬落地】+ 取数口径（peer 财务 + 估值 2b + F13 + 亲属 hook）+ 产出形态 + sidecar + 收尾 + critic 特化（含🎯目标达成核对 + 强制重修订门）+ 汇报填空。
> SKILL 路由：`arena` → 读 `_case_chain.md` + 本卡。
> case key = `a_arena_case`；sidecar = `peer_matrix.yaml`（schema 见 `_peer_matrix_spec.md`，`score` 用 1-5 制）。primer↔case 分工表（读者=要选标的的人 / 干什么=看懂谁会赢、押哪几个玩家）；边界侧重：**路线"是什么"归 primer，"哪条路线/哪个玩家会赢"的判断归 case**，arena 的 primer↔case 边比 industry 干净但仍要守，chain-critic 必查。

---

## §元目标（逐字不改）

> **一个门外人为了选标的，正在研究这个竞技场。先让他读懂这块生意/技术/路线之争本身（primer）；再带他走完一条决策链：看懂赛道 → 赢家由什么决定、市场已把谁当赢家定价 → 这套"谁会赢"的定价要什么为真 → 我押哪个/哪几个玩家 → 错了怎么知道 → 那就 shortlist 谁、谁进 company 深研。读完既入了门，也拿到一套可执行的选股漏斗。**

---

## §取数口径（Step 1：候选 peer 财务 + 估值 2b + F13 checkpoint + 亲属 hook）

2. **拉候选公司 peer 财务**（喂①卡位 + ④横比）：照 `_peer_matrix_spec.md` Step 3，对 findings 里有 ticker 的候选公司调 `financial_data.get_peer_comparison_data_by_tickers`（A股 SSE/SZSE/BSE、美股 NASDAQ/NYSE、港股 HKEX），取收入/毛利率/3年ROIC/资产负债率；非上市公司训练知识估算 + 标注。这是④横比的一手锚；不在 findings 里手抽。
2b. **拉候选公司估值倍数**（喂②估值锚 + ④横比的 PE 列，F13 接线）：对候选 ticker 调 `market_data.get_valuation_context_by_tickers([{ticker,market,name},...])` 拿 PE(TTM)/PS/PB/市值（港股经 yfinance，HKD；A 股 akshare，元）。
   > ⚠️ **硬 checkpoint（F13：拉不到要 log，不静默跳）**：取不到的会标 *(取不到)*——必须 log 缺哪个 + 为何，再 fallback 研报 PE 表或标缺口，不许默默让环②/④的估值列空着。
3. 写 `outputs/_synthesis_brief.md`：dump 核心 thesis / 关键假设 / v0→v1 强度调整 / **K# 校准（哪些公司被 K# 翻盘/强支持）**，供 ④⑥ 与 critic 复用。

> **亲属复用 hook（已生效）**：若本 topic 有 `parent_topic`（或 `find_child_topics` 返回非空），调 `get_relative_outputs('{slug}','{variant}')` 取亲属**成稿产出路径**并 Read。**借来内容受 §1.3 约束**——脚本只返路径不读内容，借用永远是输入/参照：必标来源、质量按本维度自跑、冲突时本 topic 赢。
> - **向下（父 industry → 本 arena）**：arena primer 站在父 industry primer 上扩写、不重教；读父最新 thesis；读**父 09 里点名本 arena 的那行 = 本 arena 的"mandate"**（industry 为什么把我放深挖档、预期洞见、预填狩猎问题），①从这里起、②③去验证/修正它。
> - **向上（已研究的子 company → 本 arena）**：把已研究子 company 的成稿 case/thesis 当 ④ 横比的**一等证据**（让该公司在 peer matrix 里是实证而非估算），按 §1.3 护栏标来源、本维度复核。这正是"先研究 company、后研究 arena"的复用路径。
> - 无亲属 → 返空 → 退化为独立合成，零特判。

---

## §6 环【必带硬落地】（决策链主体 · 一字不改 · 含环②定价锚×证据强度张力）

**环 ① 看懂这个赛道（理解闸门）**
- 【元问题】这块生意怎么赚钱？价值链怎么卡位、有哪些技术/商业路线之争、客户结构如何、赛道处在周期哪段？
- 【为何逼出】闸门——看不懂胜负由什么决定，后面四环都是空中楼阁。
- 【必带硬落地】① **怎么赚钱 + 价值链卡位**（这块利润从哪来、谁卡在哪段）；② **路线之争（是什么，不判胜负）**+ 客户结构（B/C/政府、集中度）；③ **赛道周期位**（早期成长/中段加速/晚期分化/成熟饱和）。
- 【别漏的 lens】旧 01 全景 / 02 周期 / 03 叙事的"这是什么生意"部分。
- 【自由区】路线对比表、篇幅；**背景深度甩给 primer（§1.2 分工）**。

**环 ② 赢家由什么决定 + 市场已把谁当赢家定价了（锚 · 天然硬）**
- 【元问题】这赛道决定胜负的关键变量是什么？市场当前估值已经把谁当赢家定价了？
- 【为何逼出】看懂赛道下一步必须问"谁会赢、定价了没"——脱离定价谈卡位无决策意义。
- 【必带硬落地 · 锚得实】
  1. **关键胜负变量**（成本曲线 / 技术代差 / 客户锁定 / 规模效应 / 牌照——哪个最决定性）；
  2. **被当成赢家那几家的当前估值**：用 Step 1 peer 财务 + 市价，指出"市场是不是已经在为 X 会赢付钱"（PE/PS 相对赛道 + 相对其卡位是否已透支）；
  3. **隐含预期落成一句话**（市场共识的赢家是谁、付了多少溢价）。
  4. **定价锚 × 证据强度张力（硬落地 · 与③缝合）**：②的赢家定价收口必须与③的 WMBT 支持度交叉，**显式点出"市场在为③里哪条最弱的假设付溢价"**（定价笃定度 > 证据强度的陷阱）。不点透即视为②停在"谁被定价"、漏掉"这定价踩在哪块虚地上"——chain-critic 必查。
- 【别漏的 lens】旧 02 估值水位、旧 04 隐含预期。
- 【自由区】用哪几个估值口径、要不要画赢家溢价图。

**环 ③ 这套"谁会赢"的定价需要什么为真（What-Must-Be-True）**
- 【元问题】要让②的赢家定价成立，哪 3-5 件具体的事必须为真？
- 【为何逼出】把"X 会赢"（结果）拆成前提（可证伪命题），④才能逐条判断、⑤才知道盯什么。
- 【必带硬落地】3-5 条假设（某路线胜出 / 份额向头部集中 / 某大客户放量 / 成本拐点兑现），每条具体、可观测、可验证，并标当前证据支持度。
- 【别漏的 lens】新链补的关键缺环。
- 【自由区】假设按对赢家归属的杠杆排序。

**环 ④ 我押哪个/哪几个玩家，凭什么（下注）**
- 【元问题】围绕③的假设，候选公司里我押谁？核心分歧在哪？
- 【为何逼出】③给了赌桌命题，这一环真正下注：横比 + 表态。
- 【必带硬落地】
  1. **核心分歧一句话**（我和共识的赢家判断差异）；
  2. **候选公司横比矩阵**（≥5 家，沿 业务结构/收入规模/3Y ROIC/毛利率/资产负债率/当前PE/历史PE区间/技术路线/客户结构/管理层信号 横比 + 综合分）——**现 `_peer_matrix_spec.md` Step 4 的 peer matrix + `financial_data` 在此作下注工具**（查矩阵维度与拉数口径，不照搬其表格结构）；评分逻辑（hard filter + 软评分权重）写清；
  3. **每家挂回③的假设 + 一句话 thesis**；**K# 校准做锚**（被 K# 翻盘的公司不进 shortlist，强支持的优先）；
  4. **已研究子 company 用实证**（亲属 hook）：若某候选已有成稿 case，用其结论替代估算，按 §1.3 标来源 + 本维度复核。
- 【别漏的 lens】旧 10 全部 + 旧 04 多空分歧。
- 【自由区】候选个数、权重组合。

**环 ⑤ 如果错了会怎样、怎么第一时间知道（证伪机制）**
- 【元问题】赢家判断错在哪种情形？哪些信号最早告诉我押错了？
- 【为何逼出】④下注后，理性立刻要求"怎么知道我错了"。
- 【必带硬落地】① 已知风险 + **盲点风险**各 ≥1；② **arena 级 kill 触发条件**（路线被颠覆 / 共识赢家失速 / 新进入者改写格局，尽量数据化）；③ **≥2 个历史镜鉴**（曾经的赢家如何被取代——Nokia/Kodak/被新路线颠覆的龙头）——每个标：失败模式 + 峰谷损失幅度% + 当年最早预警信号及"现在是否已现"，教训各一句话；**只想得到成功案例本身就是 red flag**；arena 层镜鉴比 company 更值钱，给足篇幅；④ signpost（未来 3-12 月验证/证伪事件）。
- 【别漏的 lens】旧 05 镜鉴、旧 06 风险盲点。
- 【自由区】风险分组、镜鉴选案。

**环 ⑥ shortlist 谁、谁进 company 深研（行动 = 漏斗）**
- 【元问题】综合①-⑤，shortlist 哪几家进 company 深研？哪些观察、哪些淘汰？
- 【为何逼出】①-⑤的收口——arena 研究终点是可执行的 peer shortlist。
- 【必带硬落地】① **强制三档分流**（深研/观察/淘汰，每档 ≥1 家）；② **tier = 卡位/质量 × 当前定价**：好公司但②判贵 → 进观察档 + 价格触发器，不直接深研；③ **深研档 ≤N 家** + 每家 `thesis_one_liner` + 为什么这几家优先；④ 观察档触发深研条件；淘汰档主因 + 是否 quarantine；⑤ 建 company stub（见 Step 4）。
- 【别漏的 lens】旧 10 全部（三档分流 + 短名单 + 建议 slug）。
- 【自由区】档内排序、触发器形态。


---

## §产出形态（补 `_case_chain.md` §3.4 的 arena 专属项）

- **默认一份连贯文档** `a_arena_case.md`：决策链 ①→⑥ 作为主脉络，⑥ 的三档分流即旧 10 的 markdown 内容（不再单出 `peer_matrix.md`）。
- 长度逼迫（自评 >8000 字且体验下降）可拆 2-3 份，**必须保持链序** + 每份开头交代承接关系。拆分键名见 §5。
- 无论几份：**起点诊断、6 环（②带估值锚、④含 peer 矩阵 + K# 校准、⑥三档+tier）、10 sidecar、来源分层缺一不可**。

---

## §sidecar（Step 4：写 10 sidecar + 建 company stub · 硬契约 schema 原样不动）

⚠️ dashboard.py 的竞技场层"公司排名"只读 `peer_matrix.yaml`、只认这套字段名。**禁自创/改名/漏字段**。

1. **写 `outputs/peer_matrix.yaml`**：字段从 ④/⑥ 提取，schema **逐字照 `_peer_matrix_spec.md` Step 6.5**（`slug / variant / topic_type=arena / display_name / generated / data_freshness / companies[{name, ticker, score, tier(shortlist/watch/eliminated), topic_created, topic_slug, thesis_one_liner, upgrade_triggers, quarantine}] / cluster_tags`）。**`score` 用 1-5 制**（详见 `_peer_matrix_spec.md`；勿用 1-100），与 case ④综合评级同向。数字不加引号，缺失 null。`write_text` 落盘。
   > ⚠️ **写完即自检（机器↔叙事一致性 · dashboard 直接消费）**：① **score 排序必须与 case ④综合评级同向**——同档内若 score 与评级倒挂（如 K5 hard-filter 把高 upside 公司压到低分），必须在 case 显式写一句解释，否则 dashboard 按 score 排序会与叙事方向相反；② **tier 枚举 ↔ case 中文档名映射必须在 case 显式写一行**（深研=shortlist / 观察=watch / 淘汰=eliminated），别让 dashboard 靠猜对齐档名。
2. **建 company stub + 继承 thesis_v0**：对每个深研档公司，照 `_peer_matrix_spec.md` Step 7 + 7b **逐字执行**（`create_topic(topic_type='company', parent_topic='{slug}', ticker=...)` → 收窄父 arena K# 到公司视角 → 写 stub `thesis_v0.md` 强度父级 -1）。这是父子链的自顶向下建链路径之一（图谱层 relink 是另一路径）。

---

## §收尾（Step 5 · arena 专属：stage 推进 + 退休 stage 名 + 宏观软提示）

**收尾**：照 `_shared.md` § 全部产出完成后（含 capped→suggested_drilldowns 回流）——出**终态报告**（双轴 gap + 收敛状态 + 残留缺口诚实清单）；——`append_user_todos` + 清 `next_actions` + stage 推进。arena 合成完后 stage 置 `05-critic-review`（第 6 阶段「评审」，与 company/industry 统一）；**critic 对 arena 非强制（可选）**——可在对话里说「评审 {slug}」跑对抗式 steelman，或在 web 详情页点「✓ 标记完成」直接 `done`（旧名 `10-peer-matrix` 已退休，勿再用）。

> **宏观横切（软提示 · 不强制）**：赛道/行业层多跨标的，宏观敏感度偏糊；如该赛道有显著利率/流动性/汇率暴露，**建议**（非强制）跑一遍 macro hook（见 `_type_company.md` §取数 宏观横切 hook）补一段体制敏感度。不落 macro_stamp、不参与 staleness/coverage。

---

## §critic 特化（Step 6 逐环问句 + 🎯目标达成核对 + 🔒终局证据强度 + 强制重修订门）

- ① 看懂赚钱方式 + 卡位 + 路线 + 客户 + 周期位？② **指出关键胜负变量 + 用具体公司估值锚"谁被当赢家定价"还是泛泛而谈，且是否点出②的定价在为③里哪条最弱假设付溢价（定价锚×证据强度）**？③ 把②翻成 3-5 条可证伪假设？④ 核心分歧一句话 + peer 横比矩阵 + K# 校准做锚 + 每家 thesis？⑤ 有 kill+signpost+赢家被取代镜鉴？⑥ 三档齐 + **tier 锚在②的定价（不是只按好坏排）** + 深研档 ≤N？
- 断链检查：④下注↔⑤证伪、⑥分流↔②定价锚、⑥ tier↔④卡位是否一致？**sidecar score 排序↔case ④综合评级是否同向**（同档内倒挂——如 hard-filter 把高 upside 公司压低分——必须在 case 显式解释，否则 dashboard 按 score 排序与叙事相反）？**tier 枚举↔case 中文档名映射**是否在 case 显式写明（深研=shortlist/观察=watch/淘汰=eliminated）？
- primer↔case 是否有重复（case① 该甩 primer 的背景有没有甩）？
- 跨层复用护栏（§1.3）：借来的判断标了来源吗、有没有冒充本维度自验证？
- 源分层：findings 数字标 [mat-XXX]？
- 🎯 **目标达成核对（最重要 · 独立于上面所有"链内"检查）**：把本 topic `scope.question` 原文逐子句贴出
  ```bash
  python3 -c "from prism.scripts.topic import read_topic; print(read_topic('{slug}','{variant}')['scope']['question'])"
  ```
  逐子句核对 case 是否答到**可执行层**。**funnel 链"自洽走通" ≠ "答到了用户的问题"**——arena 合同终点虽近"标的"（环⑥ 出 company shortlist），但仍可能停浅（只点名玩家却无定价/弹性/介入纪律 = 没到可执行层；或只判"哪条路线赢"没落到"哪家可买"）。这类盲区**前面所有链内检查与 05 steelman 都查不出**（它们只评"在场的链/假设"），必须在这一条抓。停浅即判**致命缺口**，不是扣分项。
- 🔒 **type-contract 终局证据强度核对（终局对齐 · 新增 · 独立于 question）**：不管 question 怎么写，**强制**检查终局环（环④ peer 横比 + 环⑥ shortlist 筛选）的判断有几维靠**定性/data-missing**。
  - 读 sidecar `peer_matrix.yaml`（若存在）的评分明细 + case 环④/环⑥ 自述
  - 逐胜负变量维核：定价锚（谁被当赢家定价）/ 卡位/ 路线/ 客户集中度/ 周期位——各判 `定量` / `定性有据` / `定性/data-missing`
  - **终局证据强度判定**：
    - ≥3 维 定量 → **强度可接受**，放行
    - ≥2 维 定性/data-missing（尤其定价锚 + 卡位双定性）→ 判 **「终局证据薄」**
  - **终局证据薄时的 escalate**：不放行浅终局，将薄弱维度翻成 `suggested_drilldowns`（`source=critic_weak_k`，`priority=P0`），附在 critic 修订清单中让主 agent 调 `set_suggested_drilldowns(mode='append')` 挂上。若 decomposition 对应命门已两轮未解 → 必要时 `set_decomposition(convergence_status='capped')`。

四段总评（链通不通 / 最严重 2-3 个断点 / **🎯 目标达成判定：原问题每个子句答到可执行层了吗、停浅在哪** / **🔒 终局证据强度：定量{}/定性有据{}/定性{}/，可接受或证据薄** / 只补一处补哪），苛刻直接，1800 字内。按反馈修订（主 agent 直接 Edit）。

**强制重修订门（有牙，非建议）**：首轮若判**断链** OR **目标未达成（停浅）** OR **终局证据薄**，必须跑第二轮。其中"目标未达成"的修订...补完重判，直到原问题每个子句都落到可执行层 + 终局证据可接受，chain-critic 才放行。

---

## §汇报

```
✅ Arena 合成已生成（理解先行 → 决策链 ①→⑥ → thesis）
   00_primer v{N}（depth={deep/shallow}，critic {轮}轮收敛）
   a_arena_case v{N}{若拆分列出}
   peer_matrix.yaml（sidecar，dashboard 竞技场层契约）+ {n} 个 company stub
   thesis_v1 v1{强度评分}

链体检：①看懂(赚钱/卡位/路线/客户/周期) ✓ / ②赢家变量+定价锚({谁被定价}) ✓ / ③假设{n}条 ✓ / ④押注({核心分歧}, peer {n}家) ✓ / ⑤kill{n}+镜鉴{n} ✓ / ⑥深研{n}/观察{n}/淘汰{n} ✓
shortlist：{深研档公司列表}
下一步：为深研档公司推进研究（说「prism 推进 {company-slug}」）或进入监控
```

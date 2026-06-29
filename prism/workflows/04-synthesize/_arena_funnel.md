# Arena 合成（理解先行 · 决策链驱动 · 漏斗终局 · 自由发挥版）

> **调度提示**：本文件是 **arena 类型 topic 在 04-synthesize 阶段的完整规范**，整体替代 `_shared.md` + `01-08` 的 8 份分箱 spec + 旧 `_peer_matrix_spec.md` 的独立 markdown。`company` 走 `_company_case.md`，`industry` 走 `_industry_funnel.md`。
>
> **复用上游、不重写**：00-research → 01-roadmap → 02-materials → 03-findings 的 findings、`gap_detector`、增量重写判定、`financial_data`、`thesis`、`00-primer.md`、10 sidecar schema/stub 创建机制全部沿用。本文件只重做"合成"这一段。
>
> **10 sidecar 与 company stub 机制保留**：`_peer_matrix_spec.md` 不删——它作为 **④ 的 peer matrix + financial_data 横比工具** + **⑥ 的 sidecar schema(Step 6.5) + company stub 创建/继承(Step 7/7b)** 被本文件引用（查规范，不照搬结构）。

---

## 0. 定位与边界

> 📎 *arena funnel 的定位/边界、与旧路径的根本改动 → 附录 A0（执行时可跳过）*

---

## 1. 核心方法

沿用 `00-primer.md` 已验证的"给目标 + 自由发挥 + 独立 critic 校验"闭环，分两层落地：**primer 是上游理解地基（纯自由发挥），case 是下游决策（自由发挥锚定在决策链上）。**

### 1.1 元目标（逐字不改）

> **一个门外人为了选标的，正在研究这个竞技场。先让他读懂这块生意/技术/路线之争本身（primer）；再带他走完一条决策链：看懂赛道 → 赢家由什么决定、市场已把谁当赢家定价 → 这套"谁会赢"的定价要什么为真 → 我押哪个/哪几个玩家 → 错了怎么知道 → 那就 shortlist 谁、谁进 company 深研。读完既入了门，也拿到一套可执行的选股漏斗。**

### 1.2 理解先行：primer 与 case 的依赖与分工（**核心规约**）

| | 谁先生成 | 读者 | 干什么 | 谁依赖谁 |
|---|---|---|---|---|
| **00_primer** | **先**（理解地基） | 完全门外人 | 看懂赛道**本身**，不被术语挡住 | 被 case 依赖 |
| **a_arena_case** | **后**（站在 primer 上） | 要选标的的人 | 看懂**谁会赢、押哪几个玩家** | 依赖 primer |
| **thesis_v1** | **最后**（提炼快照） | 持续追踪者 | 把赛道层判断提炼成可追踪快照 | 依赖 case |

时间轴：**学懂赛道(primer) → 做选股决策(case) → 持续追踪(thesis)**。生成顺序 = 阅读顺序。

**primer↔case 分工（杀掉重复，硬规约）**：
- **primer** = 静态全景地图，中立教全部（赛道怎么赚钱/技术路线有哪些/玩家/客户结构/争议），可独立读懂。
- **case ①** = **已假定读者读过 primer** 的"决策导向速写"——只点"胜负关键变量 + 直接驱动选股的张力"，**不重教 primer 已讲透的背景**，需要深度就写"详见 primer"。
- **路线"是什么"归 primer，"哪条路线/哪个玩家会赢"的判断归 case。** arena 的 primer↔case 边比 industry 干净（peer 横比天然是决策活），但仍要守，chain-critic 必查。

### 1.3 跨层复用质量护栏（**硬规约 · 与 Step 1 亲属 hook 配套**）

跨层复用是"站在肩膀上"，**不是"继承结论"**。亲属（父 industry / 子 company）的蒸馏产出只作输入/参照，质量永远按本维度、本 topic 自身的 findings + 自身的 critic 来卡：

1. **本维度自己跑完整链**：照常跑 primer + 6 环 + critic，全程按 arena 级分辨率要求（路线/玩家/客户更深更窄）。父 primer 是脚手架不是正文——arena primer 必须是 arena 级，不是把 industry primer 裁一刀。
2. **质量闸门一律本地**：`gap_detector`、chain-critic、05-critic、来源分层都对着**本 topic 自己的 K# 和 findings** 跑，不因"父已覆盖"放水。
3. **借来必标来源**：borrowed-from-relative 的内容可见地标出（对齐 mat-XXX 分层惯例），不许借来的框架冒充本 topic 自验证的结论。
4. **冲突时本维度赢**：亲属观点与本 topic 自己的 findings 打架 → 以本 topic 为准，允许背离；背离触发向上路径把亲属标 stale。

### 1.4 决策链（6 环 · 这就是契约本身）

**必须按序走完整条链，每一环必须落地（见 §3.2 各环硬约束）。不允许断链（如有 ④ 下注却无 ⑤ 证伪、有 ⑥ 分流却无 ② 定价锚）。**

```
① 能不能看懂这个赛道？
   └─ 看不懂就不选。这块怎么赚钱 + 价值链卡位 + 路线之争(是什么) + 客户结构 + 赛道周期位。这是闸门。
        ↓ 看懂了，那谁会赢、市场怎么看——
② 赢家由什么决定 + 市场已把谁当赢家定价了？【锚 · 天然硬】
   └─ 关键胜负变量(成本/技术/客户锁定/规模) + 被当成赢家那几家的当前估值（直接指向具体公司，锚得实）。
        ↓ 这套"谁会赢"的定价，
③ 需要什么为真？
   └─ What-Must-Be-True：把②翻成 3-5 条可证伪假设（某路线胜出/份额集中/某客户放量）。
        ↓ 这些假设，
④ 我押哪个/哪几个玩家，凭什么？【下注】
   └─ 核心分歧一句话 + 候选公司沿"财务+卡位+路线+客户+管理层"横比（现 10 peer matrix 作工具）+ 每家一句话 thesis。这是下注。
        ↓ 我这套判断，
⑤ 如果错了会怎样、怎么第一时间知道？
   └─ arena 级 kill + 历史镜鉴（曾经的赢家如何被取代）+ signpost。这是证伪机制。
        ↓ 综合①-⑤，
⑥ 那就 shortlist 谁、谁进 company 深研？【行动 = 漏斗】
   └─ 深研/观察/淘汰三档（tier=卡位/质量×当前定价）+ 每家 thesis_one_liner + 建 company stub。这是行动。
```

> 📎 *为什么链是紧的 / 与 company EV 的刻意差异 → 附录 A1.4（执行时可跳过）*

---

## 2. 执行 — 上游准备与 primer 先行

### Step 0：前置检查 + gap 体检（双轴）+ 增量判定 + 命门 delta 重拆（**引用 `_shared.md`，不重抄**）

进 04 第一件事，照 `_shared.md` 跑三段，结果完整贴对话：

1. **前置检查**（资料 ≥3 份，否则停）。
2. **gap 体检**（`detect_gaps` 三项任一非空 → 不要硬合成，先补救）。
3. **增量重写判定**（`list_affected_outputs` 判 new/stale/fresh；`fresh` 跳过）。arena 路径 output_key 见 §5。

> Web 搜索路径见 [[_web_search_routing]]；即兴 web-search 规约见 `_shared.md`。

### Step 1：加载 findings + thesis_v0 + peer 财务 + **亲属产出（图谱层 hook）**

1. 照 `_shared.md` § 调度模式：`format_findings_for_prompt` 列 findings（含 `parent_materials` 复用的父级 findings）→ 主 agent 并行 Read；`build_findings_index` 落盘 `_findings_index.md`；读 `thesis_v0.md`。
2. **拉候选公司 peer 财务**（喂①卡位 + ④横比）：照 `_peer_matrix_spec.md` Step 3，对 findings 里有 ticker 的候选公司调 `financial_data.get_peer_comparison_data_by_tickers`（A股 SSE/SZSE/BSE、美股 NASDAQ/NYSE、港股 HKEX），取收入/毛利率/3年ROIC/资产负债率；非上市公司训练知识估算 + 标注。这是④横比的一手锚；不在 findings 里手抽。
2b. **拉候选公司估值倍数**（喂②估值锚 + ④横比的 PE 列，F13 接线）：对候选 ticker 调 `market_data.get_valuation_context_by_tickers([{ticker,market,name},...])` 拿 PE(TTM)/PS/PB/市值（港股经 yfinance，HKD；A 股 akshare，元）。
   > ⚠️ **硬 checkpoint（F13：拉不到要 log，不静默跳）**：取不到的会标 *(取不到)*——必须 log 缺哪个 + 为何，再 fallback 研报 PE 表或标缺口，不许默默让环②/④的估值列空着。
3. 写 `outputs/_synthesis_brief.md`：dump 核心 thesis / 关键假设 / v0→v1 强度调整 / **K# 校准（哪些公司被 K# 翻盘/强支持）**，供 ④⑥ 与 critic 复用。

> **亲属复用 hook（已生效）**：若本 topic 有 `parent_topic`（或 `find_child_topics` 返回非空），调 `get_relative_outputs('{slug}','{variant}')` 取亲属**成稿产出路径**并 Read。**借来内容受 §1.3 约束**——脚本只返路径不读内容，借用永远是输入/参照：必标来源、质量按本维度自跑、冲突时本 topic 赢。
> - **向下（父 industry → 本 arena）**：arena primer 站在父 industry primer 上扩写、不重教；读父最新 thesis；读**父 09 里点名本 arena 的那行 = 本 arena 的"mandate"**（industry 为什么把我放深挖档、预期洞见、预填狩猎问题），①从这里起、②③去验证/修正它。
> - **向上（已研究的子 company → 本 arena）**：把已研究子 company 的成稿 case/thesis 当 ④ 横比的**一等证据**（让该公司在 peer matrix 里是实证而非估算），按 §1.3 护栏标来源、本维度复核。这正是"先研究 company、后研究 arena"的复用路径。
> - 无亲属 → 返空 → 退化为独立合成，零特判。

> **调度模式**：arena case 默认**主 agent 直做 + 并行 Write**。唯一 subagent 是 critic（只读不写）。

### Step 2：**先出 `00_primer`（理解地基）**

按 `00-primer.md` Step 1-5 执行，产 `outputs/00_primer.md` + `_prism_reading_guide.md`。

**本路径走 primer-first**：
- 原材料 = **findings + `thesis_v0` + K# + peer 财务 + 父 industry primer（若有）**。
- 投资加权（"该讲技术路线/客户/玩家/估值锚/争议"）来自元目标 + thesis_v0 + K#。
- primer 其余流程（目标生成 / 起点诊断 / 自由发挥 / 来源分层 / depth 降级 / **独立 critic 校验**）照走，critic 不可省。
- primer 写完即 critic 收敛后，才进 Step 3 写 case。

---

## 3. 执行 — case 决策链（站在 primer 上）

### Step 3：走决策链写 a_arena_case

#### 3.1 起点诊断（写正文前必做 · 借 `00-primer.md` §2.1）

因 primer 已建好赛道地基，case 的起点诊断**轻量化**：只需确认 (a) 这个 arena 的**命门/特色** 1-3 个（决定胜负的关键变量、路线之争的焦点，给足篇幅）；(b) case① 该把哪些背景"甩给 primer"。

> 命门**不从零拍脑袋**：以 00 的 `decomposition_v0` 为种子，读完 findings 后按 `_shared.md` §"B 轴有界 delta 重拆 + 收敛"做 delta 校验 → delta 非空则有界第二收料趟（封顶 2 轮）→ 落 `decomposition_v1`（changelog 防震荡）。

#### 3.2 逐环落地（链内无固定子节模板，每环给"必须落地什么"）

每环五样：**【元问题】/【为何由上一环逼出】/【必带硬落地】/【别漏的 lens】/【自由区】**。

---

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

#### 3.3 来源分层 + depth 降级

- **来源分层**（照搬 `00-primer.md` §2.3）：训练知识不标单条 / findings 凡引必标 `[mat-XXX]` / 亲属借用按 §1.3 标 / 特色判断文末点到指向 thesis_v1。文末 `## 信息来源` 给占比 + mat 列表。
- **depth 降级**（照搬 §2.4）：关键环数据缺口能训练知识粗估则标注"训练知识估算"，补不了明写"数据缺失"，**不编造**。

#### 3.4 产出形态（份数交给 LLM）

- **默认一份连贯文档** `a_arena_case.md`：决策链 ①→⑥ 作为主脉络，⑥ 的三档分流即旧 10 的 markdown 内容（不再单出 `peer_matrix.md`）。
- 长度逼迫（自评 >8000 字且体验下降）可拆 2-3 份，**必须保持链序** + 每份开头交代承接关系。拆分键名见 §5。
- 无论几份：**起点诊断、6 环（②带估值锚、④含 peer 矩阵 + K# 校准、⑥三档+tier）、10 sidecar、来源分层缺一不可**。

### Step 4：写 10 sidecar + 建 company stub（**硬契约 · schema 原样不动**）

⚠️ dashboard.py 的竞技场层"公司排名"只读 `peer_matrix.yaml`、只认这套字段名。**禁自创/改名/漏字段**。

1. **写 `outputs/peer_matrix.yaml`**：字段从 ④/⑥ 提取，schema **逐字照 `_peer_matrix_spec.md` Step 6.5**（`slug / variant / topic_type=arena / display_name / generated / data_freshness / companies[{name, ticker, score, tier(shortlist/watch/eliminated), topic_created, topic_slug, thesis_one_liner, upgrade_triggers, quarantine}] / cluster_tags`）。**`score` 用 1-5 制**（详见 `_peer_matrix_spec.md`；勿用 1-100），与 case ④综合评级同向。数字不加引号，缺失 null。`write_text` 落盘。
   > ⚠️ **写完即自检（机器↔叙事一致性 · dashboard 直接消费）**：① **score 排序必须与 case ④综合评级同向**——同档内若 score 与评级倒挂（如 K5 hard-filter 把高 upside 公司压到低分），必须在 case 显式写一句解释，否则 dashboard 按 score 排序会与叙事方向相反；② **tier 枚举 ↔ case 中文档名映射必须在 case 显式写一行**（深研=shortlist / 观察=watch / 淘汰=eliminated），别让 dashboard 靠猜对齐档名。
2. **建 company stub + 继承 thesis_v0**：对每个深研档公司，照 `_peer_matrix_spec.md` Step 7 + 7b **逐字执行**（`create_topic(topic_type='company', parent_topic='{slug}', ticker=...)` → 收窄父 arena K# 到公司视角 → 写 stub `thesis_v0.md` 强度父级 -1）。这是父子链的自顶向下建链路径之一（图谱层 relink 是另一路径）。

---

## 4. 执行 — 收尾

### Step 5：落盘 + 状态注册 + **thesis_v1（最后）**

每份落盘后注册引用（键名：`00_primer` / `a_arena_case` / `peer_matrix`）：

```bash
python3 -c "
from prism.scripts.topic import set_output_status, set_output_referenced_mats, read_topic
t = read_topic('{slug}', '{variant}')
for key, mats in {'00_primer': [...], 'a_arena_case': [...], 'peer_matrix': [...]}.items():
    cur = t['outputs_state'].get(key, {}).get('version', 0)
    set_output_status('{slug}', key, 'fresh', '{variant}', version=cur+1)
    set_output_referenced_mats('{slug}', key, mats, '{variant}')
print('primer + case + 10 sidecar 已注册')
"
```

> 新键 `a_arena_case` 靠 `set_output_status` 的 `setdefault` 自动注册，**不用改 topic.py**。

**thesis_v1（决策链跑完后才写）**：照 `_shared.md` § thesis_v1 的 **Scheme C 全快照 11 段式**，不改。**同时写 `decomposition_v1.md` + `set_decomposition(version=1, summary, stage_set_at, convergence_status, changelog)`**（`summary`/`stage_set_at` 必填；`convergence_status ∈ {open, converged, capped}`；完整示例见 `_shared.md` §B 轴有界 delta 重拆）。

**收尾**：照 `_shared.md` § 全部产出完成后（含 capped→suggested_drilldowns 回流）——出**终态报告**（双轴 gap + 收敛状态 + 残留缺口诚实清单）；——`append_user_todos` + 清 `next_actions` + stage 推进。arena 合成完后 stage 置 `05-critic-review`（第 6 阶段「评审」，与 company/industry 统一）；**critic 对 arena 非强制（可选）**——可在对话里说「评审 {slug}」跑对抗式 steelman，或在 web 详情页点「✓ 标记完成」直接 `done`（旧名 `10-peer-matrix` 已退休，勿再用）。

> **宏观横切（软提示 · 不强制）**：赛道/行业层多跨标的，宏观敏感度偏糊；如该赛道有显著利率/流动性/汇率暴露，**建议**（非强制）跑一遍 macro hook（见 `_company_case.md` Step 1 宏观横切 hook）补一段体制敏感度。不落 macro_stamp、不参与 staleness/coverage。

### Step 6：critic 校验（**对着决策链** · 写完即跑一轮内嵌 chain-critic）

写完即跑一轮**内嵌 chain-critic**（合成期质控，模型同 `00-primer.md` Step 3，已验证 2 轮内收敛）。与 05 分工：chain-critic 查"链通不通"，05 做对抗式 steelman。

dispatch 独立 critic（`subagent_type: general-purpose`，不传 model，**只读不写**），逐环校验链是否走通：
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

**critic-review 阶段（05）**：arena 可选进 `05-critic-review` 做对抗式重审。`05-critic-review.md` Step 1 已按 type 读 `a_arena_case.md`、rewrite_keys 用 `a_arena_case`。

### 汇报

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

---

## 附：与旧路径关系 + follow-up

> 📎 *与旧 8-份路径的逐项对照 → 附录 A附（执行时可跳过）*

---

## 附录 A — rationale / 反例 / 历史教训（执行时可跳过，调试 / 维护时查）

> 本附录收纳从各步主流程搬出的"为什么 / 反例 / 历史教训 / memory 链接 / inline worked example"。**主流程逐字未删、只是移出执行动线**；要看某步的来龙去脉，按对应小节查。

### 附录 A0 — arena funnel 的定位/边界、与旧路径的根本改动

arena 不是终局决策——它是**漏斗**：终点不是"买/卖一只股票"，而是**这个赛道里押哪几个玩家、谁进 company 深研**。旧路径把 arena 合成切成 8 份并列维度 + 一份 10 peer 矩阵；骨架按通用形状刻、arena 硬套；且把"领域入门(primer)"放在最后生成。

本文件两处根本改动（与 `_company_case.md` 同构）：

1. **理解先行**：先出 `00_primer`（赛道理解地基，critic 校验"门外人真懂了"），**决策链显式站在它之上**。
2. **按决策因果链组织**（不是并列维度）：每一环都是上一环**逼出来的**，读者顺着读就是顺着一次"这赛道谁会赢、我押谁"在想。

- **不变的是骨架（理解先行 + 决策链 6 环 + 10 sidecar schema）**。
- **自由的是血肉**——每环问什么、怎么组织、详略、产出拆几份，交给 LLM 针对这个 arena 的命门判断。
- 01-08 不再是骨架，降级成一张"别漏维度"的对照清单。

### 附录 A1.4 — 为什么链是紧的 / 与 company EV 的刻意差异

**为什么是紧的**：③ 只因②产出定价才存在；④ 把③的假设判成押哪几个玩家；⑥ 的 tier 由②的定价 + ④的卡位/质量共同决定（不是只按好坏排）；⑤ 只因④下注才需要。环与环是因果序、不是并列箱。

**与 company 的差异（刻意）**：company ④ 有 EV 加总（概率×回报）；漏斗的"回报"非单一数字，硬算是假精度——**arena 不做 EV 加总**，定量终点是 ⑥ 的 tier 分 + 触发器（喂 10 sidecar）。

### 附录 A附 — 与旧 8-份路径的逐项对照

| | 旧 arena 路径 | 本路径 |
|---|---|---|
| 组织原则 | 8 份并列维度 + 10 矩阵 | 理解先行 + 6 环决策链（⑥含选拔） |
| primer | 最后生成，消费 01-08 | **最先**生成，case 站其上（消费 findings+thesis_v0+K#+peer财务） |
| 结构约束 | 固定子节 + 10 模板 | 仅链 + 每环"必带硬落地"，子节自由 |
| ② 定价锚 | 04 隐含预期分散 | 命门环：关键胜负变量 + 具体公司估值"谁被当赢家定价" |
| ④ 押注工具 | 10 peer matrix 独立产出 | ④ 内嵌 peer matrix（作下注工具）+ 核心分歧 + K# 校准锚 |
| tier 排序 | 主要按综合分 | **卡位/质量 × 当前定价**（②做闸门） |
| 期望收益 | 无 | 刻意不做 EV（漏斗终点是 tier 分+触发器） |
| 产出份数 | 8 份 + 10 | 默认 1 份连贯 case（可拆，⑥含旧 10 内容） |
| 10 sidecar / company stub | 10 内 | **不变，复用**（Step 4 引 `_peer_matrix_spec.md`） |
| 上游 findings / 财务 / thesis | — | **不变，复用** |
| 跨层复用 | 仅 parent_materials（raw findings） | Step1 亲属 hook（已生效）：向下站父 primer/mandate、向上拿子 case 当实证；借用受 §1.3 约束 |
| critic | 05（可选） | 内嵌 chain-critic + 05（已按 type 读 a_arena_case） |

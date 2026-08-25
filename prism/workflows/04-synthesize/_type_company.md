# Company 合成 type 卡（配 `_case_chain.md` 使用）

> 执行顺序：先读 `_case_chain.md` 骨架（定位/分工/护栏/链因果序/Step 0/Step 1 调度/Step 2 primer/§3.1/§3.3/§3.4/Step 5/Step 6 骨架/汇报骨架），在骨架点名"→ 见 type 卡"处回到本卡。本卡只装 company 专属：元目标 + 6 环【必带硬落地】+ Step 0.5 红线门控 + 取数口径（财务 + macro 强制 hook + 亲属 hook）+ 产出形态 + sidecar + critic 特化 + 汇报填空。
> SKILL 路由：`company` → 读 `_case_chain.md` + 本卡。
> case key = `c_investment_case`；sidecar = `07_decision_kit.yaml`。primer↔case 分工表（读者=要做买卖决定的人 / 干什么=看懂该不该买、什么价、会怎么错）。

---

## §元目标（逐字不改）

> **一个门外人为了做出买/卖/不动的决策，正在研究这家公司。先让他读懂这门生意所在的领域与公司本身（primer）；再带他走完一条决策链：看懂生意 → 市场定了什么价 → 这价要什么为真 → 我信哪边 → 错了怎么知道 → 那就怎么做。读完既入了门，也拿到一套可执行的决策机制。**

---

## §Step 0.5：质量红线门控（company 专属 · 折自旧 03b · 写正文前先筛）

进 case 正文前先过一遍质量红线，过滤明显不合格的公司——避免对早该 quarantine 的标的做完整深研。**仅 company 跑**（industry/arena 无此闸门）。

1. **拉财务自动红线数据**：
   ```bash
   python3 -c "from prism.scripts.financial_data import get_quality_screen_data; print(get_quality_screen_data('{slug}', '{variant}'))"
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
     python3 -c "from prism.scripts.topic import set_stage, set_next_actions; set_stage('{slug}','quarantined','{variant}'); set_next_actions('{slug}',['已 quarantine，不再继续研究'],'{variant}')"
     ```
     并把 quarantine 摘要归档到 `prism/quarantine/{slug}.md`。
   - **NEEDS-REVIEW**（1-2 项非致命不通过）→ `AskUserQuestion` 问用户是否豁免；豁免则继续，否则 quarantine。

> 门控结果完整贴对话。命门若正落在某条红线上（如治理风险即命门），该红线在 case 环①管理层梁 / 环⑤证伪里要展开，不只在门控里打勾。

---

## §取数口径（Step 1：财务数据 + 亲属 hook + 宏观横切 hook）

2. **拉财务数据（多年轨迹来源，喂①的财务梁 + ②的反推口径）**：

   ```bash
   python3 -c "
   from prism.scripts.financial_data import ensure_financials, get_financial_context
   ensure_financials('{slug}', '{variant}')
   print(get_financial_context('{slug}', '{variant}'))
   "
   ```

   返回：最新报告期 / 营收 / 归母净利 / 毛利率 / ROE / 资产负债率 / FCF / 商誉占净资产 + **3 年 ROIC + 3 年 FCF**。这是①财务轨迹梁与②反推的一手锚；不在 findings 里手抽。市价/估值口径另调 `market_data.get_valuation_context`。
3. **对话内 dump**（不落盘）：核心 thesis / 关键假设 / v0→v1 强度调整，供 ④⑤⑥ 与 critic 复用。

> **亲属复用 hook（已生效）**：若本 topic 有 `parent_topic`（或 `find_child_topics` 返回非空），调 `get_relative_outputs('{slug}','{variant}')` 取亲属**成稿产出路径**并 Read。**借来内容受 §1.4 约束**——脚本只返路径不读内容，借用永远是输入/参照：必标来源、质量按本维度自跑、冲突时本 topic 赢。
> - **向下（父 arena/industry → 本 company）**：company primer 站在父 primer 上扩写、不重教；读父最新 thesis；读**父 sidecar（`peer_matrix` / `industry_to_arenas`）里点名本公司的那行 = 本 company 的"mandate"**（父级为什么把我放深研档、预期洞见、预填狩猎问题），①从这里起、②③去验证/修正它。
> - **向上（子 → 本 company）**：company 通常是叶子，`children` 多为空；若有（极少，如控股母子结构），按 §1.4 护栏当一等证据、本维度复核。
> - 无亲属 → 返空 → 退化为独立合成，零特判。

> **宏观横切 hook（company 强制 · 紧随亲属 hook）**：company case 必接入 macro 体制。
>
> 1. **读 macro 产出**：`python3 -c "from prism.scripts import macro_registry as r; import json; tm=r.read_transmission_map('global-macro-rates-liquidity','{variant}'); print(json.dumps([h for h in tm.get('holdings',[]) if h.get('slug')=='{slug}'], ensure_ascii=False))"` 取本持仓行；并 Read `topics/global-macro-rates-liquidity/{variant}/outputs/m_regime_read.md` 的相关体制节。
> 2. **织进决策链**：把四渠道敏感度（贴现率/风险偏好/carry-久期/汇率）+ `regime_favor/hurt` 织进 ⑤风险 与 ②估值——**定性为主**。
> 3. **DCF 锚（仅当 case 跑 DCF）**：取 macro 的 10Y 实际利率（regime_read / 登记表「10Y 实际利率 TIPS」），作无风险腿 → 跑**贴现率 ±50bp 估值弹性**；落进 `macro_stamp.discount_rate`。
> 4. **落 `macro_stamp.yaml`**（反查锚 · 硬要求）：记站在哪版 regime + 依赖哪些体制状态 + 贴现率：
>
> ```bash
> python3 -c "
> from prism.scripts import macro_xcut as mx, eval_snapshot as es
> latest = es.latest_evaluation('global-macro-rates-liquidity', '{variant}')
> mx.write_macro_stamp('{slug}', '{variant}', {
>     'as_of_regime_version': (latest or {}).get('version'),
>     'regime_composite': '<合成时综合判断一句话>',
>     'depends_on_states': [  # 本 case 倚赖的体制状态；conclusion 须是 regime eval 里的真实 id
>         {'conclusion': 'fx_cny',   'state': '<现读数>', 'role': 'load_bearing'},
>         {'conclusion': 'rates_us', 'state': '<现读数>', 'role': 'confirming'},
>     ],
>     'discount_rate': None,  # 跑 DCF 则填 {risk_free, applied_wacc, rate_sensitivity, source_input}
> })
> print('macro_stamp 已落')
> "
> ```
> 5. **不在表则自注册**：若 step 1 取回空（本持仓不在 transmission_map）→ 就着当下 regime **自判一行四渠道标签**，写回（标 provisional 待 macro 复核）：
>
> ```bash
> python3 -c "
> from prism.scripts import macro_xcut as mx, eval_snapshot as es
> latest = es.latest_evaluation('global-macro-rates-liquidity', '{variant}')
> ver = f\"v{(latest or {}).get('version')}\" if latest else None
> print(mx.register_holding_row('global-macro-rates-liquidity', '{variant}', {
>     'slug': '{slug}', 'display_name': '<名>', 'duration': 'long|short',
>     'rate_beta': 'high|mid|low', 'liquidity_beta': 'high|mid|low',
>     'usd_exposure': 'high|mid|low', 'exposure_score': 'high|mid|low',
>     'regime_favor': [...], 'regime_hurt': [...], 'plain': '一句传导链', 'as_of_regime': ver}))
> "
> ```
> **软降级**：无 macro topic / 无 regime eval（`latest is None`）→ 标"无宏观基准"，仍落 stamp（`as_of_regime_version: null`、`depends_on_states: []`），**不阻塞 case 合成**。

---

## §6 环【必带硬落地】（决策链主体 · 一字不改）

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
  0. **【强制·先拉实时同业倍数，再谈估值】** 对标 peer / 龙头的 P/S·PE·市值**必须**用 `.venv/bin/python` 调 `market_data.get_valuation_context_by_tickers([{ticker,market,name},...])` **现采**（港股 yfinance/HKD、A 股 akshare/元）——**不靠 web 现采、不在 findings 手抽**。findings 里的行情/市值有保质期（收料时点静态值），pre-IPO 或板块剧烈波动时数月可漂 40%+，直接当估值锚会误导对标结论（cn-momenta 2026-06 即栽在此：用了 3 个月前 stale 的地平线 1000 亿/24x，实际已 derate 到 595 亿/15.8x）。**裸 `python3` 会因缺 jinja2/pandas 静默返回 "no quote data"——一律用 `.venv/bin/python`**（[[prism-venv-python]]）。每个倍数在 case 里**标 as-of 日期**，便于 06 监控判断是否需刷新。
  1. **带数字的反推**：以当前价反推隐含的 3-5 年净利润 CAGR / 终值 PE / 隐含 IRR。最简式写出：`当前价 P ⇐ CAGR g × 终值PE × 折现率 r`。
  2. **估值原型识别 → 选 2-3 个模型独立估值**（§3.3 工具箱）。各自给 bull/base/bear，不取平均。**同业横截面（模型 F 等）的倍数 = Step 0 拉的实时值**。
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
  1. **核心分歧一句话——锚回环②的隐含数（edge 收口）**：把分歧落成"我 vs 市场已定价的那个数"的 delta，**咬环②同一条 driver、同一组单位**（市场隐含 X、我判 Y、delta 踩在哪块证据上）。环②有几条被定价的杠杆（如增长率 + 终值倍数）就**可几条并列，逐条点出我和价里那个数差多少**；定性的 archetype/档位判断（如"超级App PE30+ vs 券商PE22"）是倍数杠杆上的合法表达，**保留**——但须点明市场当前坐在哪端。⚠️ **只铺多空辩论、不落到"我 vs 价里那个数"的 delta = 没回答本环命门（edge：共识已在价里，照着买不赚钱），chain-critic 必查。**
  2. **观点光谱**（5 级或多空双方，每档挂到③的具体假设 + 概率 + 对应估值/回报）；
     - **【记法约定·必守】** 情形的「概率 + 回报」一对数若用斜杠紧凑写（如 `30%/−40%`），**首次出现必紧跟 `〔概率/跌幅〕` 图例**，让读者无需反推即知斜杠两边是什么；情形变动一律写 `旧 → 新` 并**显式点明方向**（概率 30%→35%、跌幅 −26%→−40%），**禁用「拉宽/收窄」这类需读者自行反推两个数才懂的隐喻**。同一约定同样适用于 thesis 修订日志（changelog）与 critic 改动表——凡出现该斜杠对，都按此标注。
  3. **期望收益加总**（新增）：`E[return] = Σ(各档概率 × 该档回报中点)`，算出一个数并判正负。这是把定性光谱压成定量下注，**喂⑥的仓位档位**（EV≤0 → 当前价不建仓/等回调；EV 显著为正且信息充分 → 可上更高档）。**注：EV 是定量的，但 EV→仓位是档位级判断，不是机械精确 %——见⑥。**
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
- 【必带硬落地】① **买入框**（基于②反推估值，不凭空 → 喂 sidecar `buy_box`）；② **仓位框架**（**先定档位 `position_tier` 试探/标准/重仓**——黑箱/低信息/低信心标的落"试探"，信息充分+信心足才上"标准/重仓"；档位参考④的 EV+信心度+信息完备度。`initial_max_pct` 是档位的**人工落点不是算出来的**，给不出有依据的数就填 null 只留档位，**禁用拍出来的精确 % 伪装严谨**；另带满仓上限/加仓阶梯/集中度 → 喂 sidecar `position_framework`）；③ 时间维度（持有期 + 下一 catalyst 时点 + "到 X 未发生 Y 怎么办"，持有期与①管理层信任度呼应）；④ **什么会让我改主意**（与⑤的 kill 呼应 + 上修 thesis 的正向信号）；⑤ 研究成熟度自评。
- 【别漏的 lens】旧 07 决策辅助全部。
- 【自由区】区间/阶梯怎么分。


---

## §产出形态（补 `_case_chain.md` §3.4 的 company 专属项）

- **默认一份连贯文档** `c_investment_case.md`：决策链 ①→⑥ 作为主脉络，读者顺读即顺着决策走。
- 长度逼迫（自评 >8000 字且体验下降）可拆 2-3 份，**必须保持链序** + 每份开头交代"在链哪一环、承接上一份什么结论"。拆分键名见 §5。
- 无论几份：**起点诊断、6 环（①三梁齐、④含 EV）、sidecar、来源分层缺一不可**。

---

## §sidecar（Step 4）

⚠️ dashboard.py 只读这一个文件、只认这套字段名。**禁自创/改名/漏字段**，否则该 topic dashboard 整行为空。文件名固定 `07_decision_kit.yaml`（即使主文档已改名）。字段从②/④/⑤/⑥提取，schema **逐字照 `_decision_kit_spec.md` Step 3.5**：`slug / variant / topic_type=company / display_name / ticker / generated / data_freshness / buy_box / position_framework / valuation_models / kill_criteria / signposts / cluster_tags`。数字不加引号，缺失 null。写入用 `Path(...).write_text(...)`。

---

## §critic 特化（Step 6 逐环问句 + 终局证据强度核对）

- ① 看懂生意 + 管理层可信 + 财务轨迹清楚？② 有带数字反推还是定性带过？③ 把②翻成 3-5 条可证伪假设？④ 核心分歧一句话 + 真表态 + **EV 算出来了吗**？⑤ 有 kill+signpost+镜鉴？⑥ 买入框锚在②、首仓参考④的 EV？
- 断链检查：④下注↔⑤证伪、⑥行动↔②锚、⑥仓位↔④的 EV 是否一致？
- primer↔case 是否有重复（case① 该甩 primer 的背景有没有甩）？
- 源分层：findings 数字标 [mat-XXX]？
- 🔒 **type-contract 终局证据强度核对（终局对齐 · 新增）**：不管 thesis 怎么写，**强制**检查终局环（环④ EV + 目标价）的判断有几维靠**定性/data-missing**。
  - 逐维度核：估值锚（consensus/业务倍数/DCF）/ 管理层能力 / 财务轨迹 / 竞争壁垒——各判 `定量` / `定性有据` / `定性/data-missing`
  - **终局证据强度判定**：
    - ≥3 维 定量 → **强度可接受**，放行
    - 估值锚或管理层双定性 → 判 **「终局证据薄」**
  - **终局证据薄时的 escalate**：不放行浅终局，将薄弱维度翻成 `suggested_drilldowns`（`source=critic_weak_k`，`priority=P0`），附在 critic 修订清单中让主 agent 调 `set_suggested_drilldowns(mode='append')` 挂上。若 decomposition 对应命门已两轮未解 → 必要时 `set_decomposition(convergence_status='capped')`。

四段总评（链通不通 / 最严重 2-3 个断点 / **🔒 终局证据强度：定量{}/定性有据{}/定性{}/，可接受或证据薄** / 只补一处补哪），苛刻直接，1800 字内。按反馈修订（主 agent 直接 Edit）；首轮涉断链**或终局证据薄**则跑第二轮。

**critic-review 阶段（05）**：仍按 company 规则进 `05-critic-review` 做对抗式重审。`05-critic-review.md` Step 1 已按 type 读 `c_investment_case.md`、rewrite_keys 用 `c_investment_case`——用户说「评审 {slug}」直接跑，无需手动替换。


---

## §汇报

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

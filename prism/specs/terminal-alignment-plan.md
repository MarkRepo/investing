# Prism 立项终局对齐 — type 独占终局，question 降级为「终局上的赌注」

## Context（病根，已三轮核实）

prism 的「终局倒推」设计**只在 04 生效**（funnel 6 环、环⑥ arena 分流、case EV、sidecar schema 全按 type 倒推强制）。但研究的入口 00 还开着一个**自由文本的洞**：`scope.question` 是自由散文，`thesis_v0` 的 K# 与 `decomposition_v0` 的命门都是自由命门式——没有任何闸门把它们校验到 **topic TYPE 的合同终局**上。

cn-commercial-aerospace（industry）实证了这条因果链怎么断：

1. question = 「**全维度研究**：市场空间…竞争格局…政策…技术路线…**投资赛道筛选**」——把漏斗终局（arena 分流）降格成五选一、排最后；「全维度」本身就是 thesis-driven 设计明令禁止的百科框法（00 Step 5.0 原文：先押赌注「避免研究变成百科全书式覆盖」）。
2. thesis K1-K5 全是**行业多空赌注**（火箭闭环/民营份额/降本/估值/政策），无一条是**跨 arena 横向选择**型命门。
3. `decomposition_v0` 三条命门同样全是行业多空（topic.yaml: 命门1可复用闭环/命门2民营份额/命门3估值），终局（选哪个赛道）落在拆解视野外。
4. 收料随脊柱走 → 10 条 todo 全是行业叙事料，无一以「6 个 arena 摆同口径可比」为目标。
5. **A 合同地板 `arena-scoring-inputs` 已存在且被判 covered**——有料挂上了 ring 标签，但 ring 轴二元（不测深度），是行业叙事顺手挂的浅达标。
6. 结果 `industry_to_arenas.yaml` 的 `honest_gaps` 自招：competition/valuation 两维「靠定性 / data-missing」——决定排序的维度基本是定性。
7. gap_detector 二元判「covered」，没有任何信号提示「终局产出浅」。

**关键结论**：
- 扣点在 **00 的脊柱朝向**（question→K#→命门→收料一路没对准终局），**不在**收料地板（地板早在、还达标了），**也不在** ring 覆盖检查（二元，过了）。
- 所以上一轮设想的 option ②（加 A 合同地板）**作废**；option ①（钉 terminal）应当**前移并收归 type**，成为根因级修法。

## 设计原则（本 plan 的核心命题）

> **终局归 type 独占（a priori 倒推、不可协商）；question 降级为「对终局的先验赌注」，结构上无法再稀释终局。**

- **type 决定的（锁死）**：合同终局——industry→arena 分流 / arena→标的 shortlist / company→买卖+EV(+目标价) / macro→体制定位+传导。这是 type 常量，研究任何标的前已知，无循环依赖（与 `_input_contract.md:12` 同源逻辑）。
- **question 必须扛、type 给不了的**：① 标的身份；② scope 切片（geo/depth/研究哪一刀，如商业航天含不含军工邻接/一级 pre-IPO）；③ **赌注/角度**（不可倒推的人类/模型先验，是 alpha 本身）。
- **修法不是删 question**：删了→每个 industry 退化成同一句「扫所有 arena」的通用扫描，丢掉 thesis-driven 的方向性。**而是把 question 重述成「对 type 终局的答案尝试」**——这样它既保留赌注（alpha），又**结构上无法把终局埋成五选一**（因为它被表述为「对终局的判断」，不是「要不要把终局列进来」）。

## 关键架构事实（已核实）

- `create_topic`（topic.py:260）构造 `scope = {geo, question, depth, (ticker/short_name/search_terms…)}`；无 terminal 概念。**修改 `create_topic` 属核心符号改动——动前必跑 `gitnexus_impact`（CLAUDE.md 铁律）**。
- `read_topic`（topic.py:408）一串 `setdefault` 做向后兼容——新字段在此补缺省即向后兼容。
- 终局是 type 派生、a priori，**识别终局不是判断、是读合同** → 放 00（即便薄知识、v0 不做 critic）照样可靠，不违「薄知识不做重判断」铁律。
- 三类型 04 路径的 chain-critic 收尾各自有「🎯 目标达成核对」（`_industry_funnel.md:257` 贴 `scope.question` 逐句核对）——**但问题框偏时核对的是错标尺**，查不出「问题本身没对准 type」。这是要补强的接缝。
- 与既有 plan（`quirky-cuddling-diffie.md`「建议深挖」钩子）**正交互补**：那份解决「研究跑完命门没收敛→事后建议深挖」；本份解决「研究一开始方向就偏→终局从没当收料目标」（事前）。两者在 **04 critic 的终局证据强度核对 → escalate 成 capped 命门 / suggested_drilldown** 处接缝。

---

## 实施方案

### A. 脚本层 — `prism/scripts/topic.py`（终局登记 + 倒推注入，低风险）

1. **新增常量 `_TYPE_TERMINALS: dict[str,str]`** —— type → 合同终局一句话（与 `_input_contract.md` 终环同源；改一处回溯另一处）：
   - `industry`: 把资本/注意力分配给哪几个细分 arena（深挖/观察/淘汰三档分流）
   - `arena`: 在候选标的里选出 shortlist（谁是赢家/介入纪律）
   - `company`: 买/卖/持有 + 期望收益(EV) + 目标价/介入纪律
   - `macro`: 体制定位 + 传导地图下的资产含义
2. **新增 `terminal_for_type(topic_type) -> str`** —— 纯查表 helper（未知 type 返回兜底通用句 + stderr 提示）。供工作流/critic/web 引用，零推断、守铁律。
3. **`create_topic` 注入** —— 构造 scope 时加 `scope["terminal"] = terminal_for_type(topic_type)`（1 行；不改函数签名，question 参数保留、角色靠工作流文档重述）。
4. **`read_topic` 向后兼容** —— `scope` 无 `terminal` 的老 topic：`data["scope"].setdefault("terminal", terminal_for_type(data["type"]))`（派生，不写盘）。

> **风险**：纯增量。`create_topic` +2 行（helper 调用 + scope 注入）、`read_topic` +1 行 setdefault、新增 1 常量 + 1 helper。动 `create_topic` 前按铁律跑 `gitnexus_impact({target:"create_topic", direction:"upstream"})` 报 blast radius。

### B. 00 立项问题塑形 — `prism/workflows/00-research-topic.md` Step 1

5. **Step 1 加 type→终局倒推框**：确认 type 后，工作流显式向主 agent 声明本 type 的合同终局（引 `terminal_for_type`），并规定 **question 三段式收集**，替代「随便问一句研究问题」：
   - **标的身份 + scope 切片**（geo/depth/研究哪一刀）；
   - **对终局的先验赌注**（核心提问按 type 改写）：
     - industry → 「你预判利润池会落到哪几个 arena、押哪条迁移路径？共识押哪条、你和它哪里分歧？」
     - arena → 「候选里你赌谁是赢家、凭哪个胜负变量？」
     - company → 「你赌买还是卖、核心命门是什么、目标价区间的赌注？」
   - **红线**：question **不得**重新枚举/降格终局（如 industry 写「全维度…赛道筛选作其一」即违规）；终局由 type 独占、永远在场，question 只能往这个固定终局里灌赌注。
6. **Step 1 加一句软警告规约**：若用户给的是「全维度/百科式」question，主 agent **不硬收窄**（宽行业地图有时本身是目的），但**必须**把 question 改写成「以终局赌注为主轴 + 宽覆盖作 scope 备注」，并在对话显式回述改写后的终局赌注让用户确认。

### C. thesis 对齐终局 — `00-research-topic.md` Step 5.0 / 5.2

7. **Step 5.0 核心 thesis 必须是「终局上的立场」**：一句话 thesis 要落在 type 终局上（industry→倾向哪几个 arena/迁移路径；不能只写「看多行业」）。
8. **Coverage 自检升级**：现有自检只验「每个 K# 有 todo 攻打」（thesis 内部自洽）。**新增一条**：thesis 的 K# 谱系 **或** decomposition 命门里，必须有**至少一条直接服务于 type 终局决策**；否则在对话报警并补。（语义判断归 LLM；脚本只提供 `terminal_for_type` 作核对锚。）

### D. decomposition_v0 钉终局 — `00-research-topic.md` Step 5.4

9. **「每环 B 靶点」对 type 终局环强制非空**：industry→环⑥ arena 比较料靶点 / arena→环⑥ shortlist 料 / company→环④ EV 输入料，必须写出且排进 5.3/01 收料优先级（不能空着等环⑥「必产」硬挤）。
10. **机械自检加第 5 条**（照单核对、无需 LLM 重判）：
    > 「type 终局环（`terminal_for_type` 指向的环）的 B 靶点是否非空？是否在 5.3/01 排了对应收料优先级？」——否则报警。形态对齐现有第 4 条「每条 primer 入门目标是否排了背景料」。

### E. 04 chain-critic 终局证据强度核对 —（接缝既有 drilldown plan）

11. **三路径 Step 6 chain-critic 升级**（`_industry_funnel.md:257` / `_company_case.md` / `_arena_funnel.md` 对应处）：在「🎯 目标达成核对（贴 question 逐句）」之外，**增 type-contract 终局证据强度核对**——不管 question 怎么写，强制检查终局环（industry 环④/⑥、arena 环④/⑥、company 环④）的判断有几维靠**定性/data-missing**（读 sidecar `honest_gaps` + case 自述）。
12. **escalate 接缝**：若决定排序/选择的维度（如 industry 的 competition/valuation）多数定性 → 判「终局证据薄」，**不放行浅终局**，并按既有 `quirky-cuddling-diffie.md` 钩子：把该薄终局翻成 `set_suggested_drilldowns`（`source=critic_weak_k`）/ 必要时 `decomposition convergence_status='capped'`。两份 plan 在此咬合。

### F. Web（可选）— `app/templates/prism/detail.html`

13. **(可选)** scope 卡片显示 `scope.terminal`（「本研究合同终局：…」），让终局对齐在 web 可见。route 已传 `topic`，模板直接读 `topic.scope.terminal`，无需改 route。

---

## 明确不做（已核实，避免过度设计）

- **A 合同加收料地板**（上一轮 option ②）：作废。`arena-scoring-inputs` 等终局环地板**已存在**，cn 案例还被判 covered——加地板治不了「浅达标」。
- **gap_detector ring 轴改成深度感知**（二元→分级）：能根治「浅达标不报警」，但属 gap_detector 核心重构、blast radius 大，**本 plan 不含**；先用 E（critic 终局证据强度）兜住，列为后续可选项。
- **删除 question / 全自动倒推**：会退化成百科扫描、丢 thesis-driven alpha，明确不做（见设计原则）。
- **thesis 加 `terminal_k` 专用字段**：不加。终局是交付结构不是证伪命题，塞 K# 别扭；改由 decomposition 命门 + 自检承载。

## 验证

1. **脚本单元**（REPL）：`terminal_for_type` 四类型返回正确 + 未知兜底；新建一个 industry/company topic 验 `scope.terminal` 写入；对**无 terminal** 的老 topic（如 cn-commercial-aerospace）跑 `read_topic` 验 setdefault 派生不报错、不写盘。
2. **向后兼容**：遍历现有 topic.yaml 跑 `read_topic` 全通过；`scope.terminal` 缺失时按 type 派生。
3. **回归实证（cn-aerospace 反向验证）**：用本 plan 的 Step 1 三段式 + Step 5.4 自检**重走一遍该 topic 的立项设问**（纸面推演即可），确认终局赌注会逼出一条 arena-selection 命门 + 环⑥ B 靶点 → 会产出「跨 arena 可比料」todo（即能堵住原扣点）。
4. **流程文档自洽**：通读 00（Step1/5.0/5.4）+ 三条 04 路径 critic 改动，确认终局表述一致、与 `_input_contract.md` 终环同源、与 `quirky-cuddling-diffie.md` 钩子接缝无冲突。
5. **CLAUDE.md 合规**：改 `create_topic`/`read_topic` 前跑 `gitnexus_impact`；收尾跑 `gitnexus_detect_changes()` 确认改动范围只含下表文件。

## 改动文件清单

| 文件 | 改动 |
|---|---|
| `prism/scripts/topic.py` | 新增 `_TYPE_TERMINALS` 常量 + `terminal_for_type()` helper；`create_topic` 注入 `scope.terminal`；`read_topic` setdefault 向后兼容 |
| `prism/workflows/00-research-topic.md` | Step 1 type→终局倒推框 + question 三段式（含「赌注」重述）+ 全维度软警告；Step 5.0/5.2 thesis 对齐终局 + Coverage 自检加「终局命门」条；Step 5.4 终局环 B 靶点强制 + 机械自检第 5 条 |
| `prism/workflows/04-synthesize/_industry_funnel.md`<br>`_company_case.md`<br>`_arena_funnel.md` | Step 6 chain-critic 加「type-contract 终局证据强度核对」+ escalate 到 suggested_drilldown/capped（接缝既有 plan） |
| `prism/workflows/_input_contract.md` | 终环一句话与 `_TYPE_TERMINALS` 同源标注（仅注释级，保两处一致） |
| `app/templates/prism/detail.html` (可选) | scope 卡片显示 `scope.terminal` |

## 与既有 plan 的关系

- **本 plan（立项终局对齐）= 事前治本**：把终局收归 type，堵住「方向一开始就偏」。
- **`quirky-cuddling-diffie.md`（建议深挖钩子）= 事后捞**：研究跑完命门没收敛→结构化建议深挖。
- **接缝在 E**：04 critic 发现「浅终局」→ 复用既有 `set_suggested_drilldowns`/`capped` 钩子。两份可独立实施、独立验证；E 段需既有 plan 的 `set_suggested_drilldowns` 已落地（或同批实施）。

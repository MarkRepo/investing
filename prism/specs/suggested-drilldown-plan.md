# Prism「建议深挖」自动钩子 + Web 提示 + drilldown 深度分级

## Context（为什么做）

prism 目前对「深挖」的自动化只覆盖一种:industry funnel 环⑥ 会自动建议「深挖档 arena 子 topic」(派生独立 topic)。而 `07-drilldown`(同 topic/variant 内的专题笔记)**没有任何自动触发/提示点**——它 100% 靠用户主动说「深挖 {slug} 的 {问题}」。

`_shared.md:132` 其实已写了一句软规约:"顽固命门(撞 2 轮顶仍未解)→ `convergence_status='capped'` + 踢 07-drilldown(在终态报告里列出 + set_next_actions 提示)"。但它①只塞进纯文本 next_actions、和别的 action 混在一起;②web 无专属展示;③是 LLM 自觉行为,无脚本钩子保证,LLM 漏写就没了;④critic(05)发现的薄弱 K# 没有同等回流。

延伸发现:07-drilldown 对**承重式深挖**(攻 capped 命门 / thin_evidence 薄弱 K#)质量不稳——缺独立校验、Step 4.6「是否动摇 thesis」判定全靠自觉。而钩子触发的恰恰都是承重式深挖,两者是同一处暴露,需配套补强。

**目标**:把「capped 命门 / critic 薄弱 K#」升级为结构化的「建议深挖」,自动回流 topic.yaml 并在 web 醒目提示(LLM 漏写时脚本兜底信号仍提示);给 drilldown 加「深度分级」轻闸门保证承重式质量;并把建议→深挖→收口形成闭环。三种 type(industry/arena/company)统一覆盖。

## 已确认的设计取舍（用户逐项选定）

1. **载体** = 新增结构化字段 `suggested_drilldowns` + web 独立「🔍 建议深挖」块(非复用 next_actions 纯文本)。
2. **触发点** = 04 合成收尾(capped 命门) + 05 critic 收尾(thin_evidence 薄弱 K# / 单线承重)双收尾。
3. **自动强度** = LLM 写文案(符合 prism 铁律:脚本不做推断) + 纯脚本兜底信号(LLM 漏写时 web 仍提示)。
4. **drilldown 产出** = 保持独立 output(不物理合并进 primer/case);靠 manifest 入库 + 显式 stale 让 case 下次重写时逻辑吸收。
5. **drilldown 流程** = 加「深度分级」轻闸门(不重设计成 7 stage):quick 维持现状;load-bearing 加单轮自检 + 强制命门判定。

## 关键架构事实（已核实）

- **三类型收尾统一**:company→`_company_case.md §4`、arena→`_arena_funnel.md §4`、industry→`_industry_funnel.md §4`,三者的 thesis_v1 / decomposition_v1 / 终态报告 / next_actions 收尾**都引用 `_shared.md`**(`_shared.md:240` / `:259` 全部产出完成后收尾 / `:335` decomposition_v1 / `:337` 终态报告)。→ **改 `_shared.md` 一处即覆盖三类型**。
- **数据来源可程序化**:`gap_detector.detect_gaps()` 返回 `uncovered_ks`(0 证据)与 `thin_evidence`(<min_evidence);`snapshot_gaps()` 已把 gap 存进 `stage_history[-1].gap_snapshot`。`decomposition.history[-1].convergence_status=='capped'` 标记顽固命门(命门文本在 `summary`)。
- **drilldown 现状(07 共 154 行)**:已是「缩小版主流程」——Step 2/2b 专项 prescan(收料)、Step 4.5 入 manifest(溯源,引文必来自 material)、Step 4.6 三类决策(与 04 联动:补佐证/边缘修正/动摇→`set_output_status(stale)`)。缺的是独立校验 + 4.6 判定为软自评。`outputs.py` 已有 `is_drilldown` 标记 + `_DEFAULT_IGNORED_SOURCE_TYPES=('drilldown',)`(M6:drilldown 默认不触发 04 重写)。
- **web 自动反映机制**:`topic.yaml` → `app/routes/prism.py::prism_detail`(`topic_io.read_topic`)→ `app/templates/prism/detail.html`(Jinja2 直接读 `topic.*`)。改 topic.yaml 后刷新即显示。计算值(如 `pending_thesis_review`)由 route 算好传模板——脚本兜底信号走同一通道。
- **风险**:唯一改动的现有核心函数 `read_topic` 仅加一行 `setdefault`,`gitnexus_impact` 判 **LOW**、纯向后兼容。其余均为新增函数 / 新增渲染块 / workflow 文档。

---

## 实施方案

### A. 脚本层 — `prism/scripts/topic.py`（4 处)

1. **字段默认值**:`_DEFAULT_TOPIC`(~395) 加 `"suggested_drilldowns": []`;`read_topic`(~417) 加 `data.setdefault("suggested_drilldowns", [])`。〔已落地〕
2. **`set_suggested_drilldowns(slug, variant, items, *, mode="replace")`**(仿 `set_next_actions`,纯文件写、零推断)。每项规范化:
   ```yaml
   - question: str        # 深挖问题(LLM 写)
     rationale: str       # 为什么深挖(哪条命门 capped / 哪个 K# 薄弱)
     source: str          # capped_decomposition | critic_weak_k | auto_capped/auto_thin(兜底)
     related: [K#, ...]
     priority: P0|P1|P2
     status: open         # open | done | dismissed
     suggested_at: iso
   ```
   `mode=replace` 全量覆写(04 用);`mode=append` 按 question 去重追加(05 用,不冲掉 04)。末尾 `_trigger_dashboard`。
3. **`detect_drilldown_candidates(slug, variant) -> dict`**(零推断、只读兜底信号):读 `decomposition.history[-1].convergence_status=='capped'` + `gap_detector.detect_gaps()` 的 `thin_evidence`/`uncovered_ks` + `critic.verdict`,返回 `{has_signal, capped, capped_summary, thin_evidence, reason}`。
4. **`resolve_suggested_drilldown(slug, variant, question_substr, *, status="done", drilldown_file=None)`**(仿 `update_user_todo_status`,子串匹配,把某条建议 `open→done/dismissed` + 关联 drilldown 文件名)。

### B. 04 合成收尾钩子 — workflow 文档（流程规约，无代码）

5. **`_shared.md`** 把 `:132` 软规约升级为收尾硬步骤(置于 §"全部产出完成后(收尾)" `:259` 与 §终态报告 `:337` 之间):
   - 写完 `set_decomposition(convergence_status=...)` 后,**若 `=='capped'`**:LLM 把每条残留命门翻成 1 条建议(`source=capped_decomposition`、related 填 K#),调 `set_suggested_drilldowns(mode='replace')`。
   - **三类型差异说明**(防混淆):此 drilldown 是「同 topic 内专题深挖」,与环⑥「派生 arena/company 子 topic」两条线、不重叠——命门指向某子赛道/子公司证据不足→优先建子 topic stub(环⑥已管);`suggested_drilldowns` 专管「留在本 topic、一篇 07 笔记就能补强」的未收敛命门。
   - **收尾断言**:`detect_drilldown_candidates().has_signal and not suggested_drilldowns` → 打印提醒 LLM 补(不强 raise,避免卡死合成)。
6. **各路径 §4 各加一行指针**(防漏读):`_company_case.md:309`、`_arena_funnel.md:234`、`_industry_funnel.md` 收尾段,在"照 `_shared.md` § 收尾"旁补"(含 capped→suggested_drilldowns 回流)"。

### C. 05 critic 收尾钩子 — `prism/workflows/05-critic-review.md`

7. **Step 7**(verdict 之后):若 Step 0 gap report 有 `thin_evidence`≥1 或 Step 5.5 判「单线承重」,LLM 把薄弱 K# 翻成建议(`source=critic_weak_k`),调 `set_suggested_drilldowns(mode='append')`(不覆盖 04)。`request-more/request-rewrite` 走主线时可并行挂建议。

### D. drilldown「深度分级」轻闸门 + 闭环 — `prism/workflows/07-drilldown.md`

8. **Step 1 加深度分级**:quick(日常问答)vs load-bearing(攻 capped 命门 / thin_evidence / 可能动摇 thesis = 钩子触发那种)。写进笔记 frontmatter `weight: quick|load-bearing`。
9. **load-bearing 专属(Step 3→4 之间插单轮自检)**:主 agent 写完跑一次性自检清单,或 dispatch 只读 subagent 单轮反方(**不写文件**,照 `feedback_subagent_write_hallucination`)——查「单线承重 / 证据够不够 / 是否过度外推」。quick 跳过。
10. **Step 4.6 对 load-bearing 升级为强制**:必须显式回答「我 `addresses` 的那条 capped 命门 / 薄弱 K#,这次解没解决」,据此走三类决策(动摇→`set_output_status(stale)`)。
11. **新增 Step 4.7 闭环**:按 question/related K# 匹配,调 `resolve_suggested_drilldown` 把对应建议 `open→done` + 关联本次 drilldown 文件名(否则建议永远挂 web)。
12. 产出**保持独立 output**(现状正确);逻辑吸收靠 Step 4.6 第三类(已存在),不物理合并。

### E. Web 层 — `app/`

13. **`app/routes/prism.py::prism_detail`(~423)**:加 `drilldown_candidates = topic_io.detect_drilldown_candidates(slug, variant)` 传模板(同 `pending_thesis_review` 套路)。
14. **`app/templates/prism/detail.html`**:右侧 `actions-panel`「下一步」section 后新增「🔍 建议深挖」section:
    - `topic.suggested_drilldowns` 非空 → 列每条:question(加粗)+ rationale(hint)+ related K# chips(复用 `chip-addr`)+ priority chip;done/dismissed 折叠或置灰。
    - 字段空但 `drilldown_candidates.has_signal` → 兜底块(借 `thesis-review-banner` 浅黄样式):"⚠ 有未收敛命门/薄弱 K#:{reason} —— 可说「深挖 {slug} 的 {命门}」"。
    - 两者都无 → 不渲染。
15. **(可选)产出表视觉区分**:`detail.html` 左侧产出表给 `is_drilldown=True` 行加 🔍 标记/分组。
16. **(可选)列表角标**:`index.html` 仿 `v.needs_review`(:24-25)给有 open 建议/has_signal 的 variant 加 `🔍可深挖` chip(需 `list_variants` 补 `has_drilldown` 布尔)。主方案先做 detail 页。

---

## 验证

1. **脚本单元**(REPL):造一个 capped 样例或用现有 topic 调 `set_suggested_drilldowns` / `read_topic` / `detect_drilldown_candidates` / `resolve_suggested_drilldown`——验证写入可读、`mode=append` 去重、capped/thin_evidence 下 `has_signal=True`、resolve 正确翻 done。
2. **向后兼容**:对**没有** `suggested_drilldowns` 字段的老 topic.yaml 跑 `read_topic`,确认补 `[]` 不报错。
3. **web 端到端**:启 app(用户 `! <cmd>` 跑 server),访问 `/prism/{slug}/{variant}`:有建议→「🔍 建议深挖」块渲染;无建议但有 capped→兜底块出现;干净 topic→不渲染。
4. **流程文档自洽**:通读 07/_shared/05 改动,确认 quick/load-bearing 分级与闭环步骤无矛盾、指针指向正确。
5. **CLAUDE.md 合规**:改 `read_topic`/新增函数前跑 `gitnexus_impact`(已预跑 read_topic=LOW);收尾跑 `gitnexus_detect_changes()` 确认改动范围只含下表文件。

## 改动文件清单

| 文件 | 改动 |
|---|---|
| `prism/scripts/topic.py` | 加 `suggested_drilldowns` 默认值 + `set_suggested_drilldowns` + `detect_drilldown_candidates` + `resolve_suggested_drilldown` |
| `prism/workflows/04-synthesize/_shared.md` | `:132` 软规约升级为收尾硬步骤 + 三类型差异说明 + 收尾断言 |
| `prism/workflows/04-synthesize/_company_case.md`<br>`_arena_funnel.md`<br>`_industry_funnel.md` | §4 收尾各加一行指针 |
| `prism/workflows/05-critic-review.md` | Step 7 加 thin_evidence/单线承重 → suggested_drilldowns(append) |
| `prism/workflows/07-drilldown.md` | Step 1 深度分级 + load-bearing 单轮自检 + Step 4.6 强制命门判定 + Step 4.7 闭环 |
| `app/routes/prism.py` | `prism_detail` 传 `drilldown_candidates` |
| `app/templates/prism/detail.html` | 新增「🔍 建议深挖」section + 兜底块(+可选产出表 🔍 标记) |
| `app/templates/prism/index.html` (可选) | 列表 `🔍可深挖` 角标 |

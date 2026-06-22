# 运行问题记录 — cn-commercial-aerospace-upstream / variant glm-5.2

> 目标：完整重跑 prism 研究(00→05)，记录运行中遇到的问题（工具 bug、流程冗余、混乱、设计不合理、目标偏离）。
> 记录时间：2026-06-19。运行者：glm-5.2（本会话）。
>
> **订正声明**：第一版把"新变体无复用机制 / thesis 不该不继承"当成问题，是误读 00 Step 3。Step 3 明确写了复用策略：materials 物理在 slug 层共享、`register_inbox_materials` 命中即跳过；findings 必须本变体重抽（模型对比意图，非 bug）；`set_parent_materials` 引父级 findings；**thesis 是本变体自押注（bet-first，本就不该继承）**。第一版还跳过 00 直接跑 01，是流程错位。下面条目已订正：真问题在闸门对空变体空过、周边工具链缺继承/fallback、fetch fan-out 抓噪音，而非核心复用机制缺失。

分类图例：`[BUG]` 工具行为与预期不符 · `[REDUNDANCY]` 流程冗余 · `[CONFUSION]` 命名/路由/结构混乱 · `[DESIGN]` 设计权衡/不合理 · `[DRIFT]` 目标偏离

---

## P1 — `glm-5.2` vs `glm5.2` 变体名静默归一，registry 连字符策略不自洽 `[CONFUSION]`

**现象**：model_registry 规范名是 `glm5.2`（无连字符）。用户自然输入 `glm-5.2`（带连字符），`create_topic` 靠 `canonical()` 静默归一为 `glm5.2`，只往 stderr 打一行 `ℹ 变体名归一`。变体名同时是目录名和 yaml variant 字段。

**问题**：跑完发现目录名（`glm5.2/`）跟输入（`glm-5.2`）不一致，难对应。registry 里 `gpt-5-4` 带连字符、`glm5.2` 不带——同一套命名规则不自洽。归一只在 create 这处做，别处拼字符串 `{variant}` 会拿到未归一名。

**建议**：registry 统一连字符策略；或归一做成 loud（返回新名 + 调用方显式确认），不要静默改用户输入。

---

## P2 — skill 文档说 `topic.yaml` 在 `{slug}/` 根，实际是 `{variant}/topic.yaml` `[CONFUSION]`

**现象**：skill 触发表「Prism Root」段写 `topic.yaml` 在 `prism/topics/{slug}/`，实际 file-first 改造后是 `prism/topics/{slug}/{variant}/topic.yaml`。`cat prism/topics/{slug}/topic.yaml` → file-not-found。canonical 标记只在一个 variant 上，「查看进度」路由说"读 topic.yaml"没说读哪份。

**建议**：文档「Prism Root」更新为 `{variant}/topic.yaml` 布局，并指明默认读 canonical。

---

## P3 — `resolve_parent_variant` 在多变体父上停 None，每次手工指定 `[REDUNDANCY][CONFUSION]`

**现象**：父 `cn-commercial-aerospace` 有 3 变体（deepseekv4pro / opus4.8 / qwen3.7-max），`resolve_parent_variant('glm5.2', pvs)` 返回 `confident=False`、`chosen=None`、`candidates=全部3个`、reason「多个异模型父且含未登记变体，拿不准」。01 Step 1.5 要求显式问用户该引哪个父变体。

**问题**：glm5.2 与 opus4.8 在 registry 属不同模型族，无启发式自动选——**每新建下游变体都得手工指定父变体**。单用户工作流更顺的是默认取父的 canonical 变体 + 一行覆盖。父有 `qwen3.7-max` 变体**不在 model_registry**（只有 qwen3-6-plus）→ 正是 reason 里"含未登记变体"来源。registry 与实际目录漂移。

**建议**：父 resolve 不自信时 fallback 到父的 `canonical:true` 变体（opus4.8 应是 canonical）而非停 None；registry 补登 qwen3.7-max。

---

## P4 — coverage/auto-fetch 闸门对「跳过 00」的空变体全部空过(vacuous pass) `[CONFUSION]`

**现象**：新变体 `thesis.current_version=None`。若没写 thesis_v0 就跑 01：`validate_roadmap_thesis_coverage(version)` 里 version 无对应文件 → `thesis_ks=[]`，进而 `uncovered=[]`、`ok = not [] and not [] = True`。已实测：写好 roadmap 但无 thesis 时返回 `ok=True`。Step 1.7 提示「先回 00 写 thesis_v0」，但 5.7 硬闸门**形上通过、不报红**。5.8 `pending_unfetched_todos=[]` 也"通过"。

**问题**（订正：thesis 不该继承是设计；真问题在闸门）：三个闸门(1.7/5.7/5.8)对"跳过 00 直接跑 01"的错位路径全空过，不报任何警告——主 agent 容易以为"绿灯=真覆盖"。根因是流程错位（第一版就犯了）：新变体应在 00 写完 thesis_v0 再进 01，闸门假设 thesis 已存在。

**建议**：coverage 校验对 `thesis_ks==[]` 应**报 warn 而非 pass**；或在 01 Step 1.7 检测 `current_version is None` 时硬 raise（现在只是软提示）。

---

## P5 — `list_parent_materials` 返回纯文件名 list[str]，不带 mat_id/metadata `[DESIGN]`

**现象**：父有 151 份 materials。`list_parent_materials('...','glm5.2')` 返回 151 个**纯文件名字符串**（如 `2026-06-13_...中信证券...md`），不带 mat_id / addresses / rings / source_type / notes。但 01 Step 1.5 后续 `set_parent_materials` 要求 `{parent_slug, parent_variant, mat_id, addresses, note}`——**mat_id 必填**。

**问题**：拿到文件名后要复用某材料，还得再 `read_manifest(父slug, 父variant)` 按 filename 反查 mat_id——一次能拿到的信息拆成两次调用，靠 filename 字符串 join 易脆（日期前缀/重名/改名对不上）。151 条全靠目测挑哪些对 arena 上游有用，机械层可按 addresses(K#)/rings 预过滤。

**建议**：`list_parent_materials` 返回 `[{mat_id, filename, addresses, rings, source_type, notes}]`，提供 `--addresses-contains` 过滤参数。

---

## P6 — workflow 01 有 14 子步骤 + 双硬闸门，复用场景认知负荷极高 `[DESIGN]`

**现象**：01 有 Step 1/1.5/1.7/2/3/4/5/5.5/5.6/5.7/5.8/6/7/8 共 14 个子步骤，含 5.7 coverage、5.8 auto-fetch 两硬断言，外加 5.5 多 ticker 下载 + 5.6 三阶梯抓取 + 8 prescan。

**问题**：闸门动机都对（防漏抓/防空过），叠加后认知负荷与 token 成本极高，对"换模型重研"复用场景尤重。隐式时序依赖(5.6→5.8、1.7→5.7)散落不同 Step，无"前置依赖 DAG"，易跳步被打回重跑。

**建议**：① 复用兄变体的新变体提供 fast-path：父已 `fetched`/`done` 的 todo 直接标 `reused` 跳过 5.8。② 01 顶部画 step 依赖 DAG。

---

## P7 — `fetch(annual)` fan-out 抓成公告大杂烩，全标 `quarterly-report`+错 ring `[BUG][DRIFT]`

**现象**：roadmap 列 1 条 `annual-report`（斯瑞 SSE_688102, 2024）。跑 `fetch('SSE_688102', report_type='annual', year=2024)` 后 glm5.2 manifest 登记 **28 份**——除真年报外，把 cninfo「该 ticker 近期所有披露」全拉下：定增募集说明书、保荐书、法律意见书、股东会决议、行权结果、券商持续督导意见、异常波动公告……**全部 source_type=`quarterly-report`、rings 全标 `peer-comparison-financials`**。

**问题**：`annual` 一次调用触发公告 fan-out，没过滤"与年报/财报相关"，也没按 report_type 区分落库类型——保荐/法律/股东会/异常波动全当 quarterly-report。污染下游：03 去读不相关 PDF；coverage/affected_outputs 虚高以为"28 份财报料很足"；synthesis referenced_mat_ids 塞噪声。ring 机械套固定串，与材料实际性质完全不符。**DRIFT**：初心是「拿到 roadmap 点名那份年报」，结果「搬整个披露页」。

**建议**：① `fetch(annual)` 只下命中年报（cninfo category 严格对齐），公告 fan-out 改显式 opt-in。② 落库按 announce category 前缀推 source_type（`yjdbg`=业绩快报/`kzz`=股东大会类/`zf`=再融资…），不一律 quarterly-report。③ ring 由 category 语义映射。

---

## P8 — manifest 每 variant 独立 mat_id，跨变体引用脆弱 `[DESIGN]`

**现象**（manifest 设计已核实源码）：materials 物理在 topic 层 `topics/{slug}/materials/`（跨 variant 共享），manifest 每 variant 独立 `topics/{slug}/{variant}/manifest.yaml`。`add_material` 的 filename 去重是**单 variant 内**——同一物理 PDF 在 opus4.8 是 mat-aaa、在 glm5.2 register 后是 mat-bbb。

**问题**：跨变体引用（如想指 opus4.8 某具体 mat）靠 mat_id 对不上，只能靠 filename join（与 P5 同源脆弱）。复用场景：`register_inbox_materials('slug','glm5.2')` 会把 topic 层所有料重新登记一份新 mat_id 进 glm5.2 manifest——逻辑隔离成立（模型对比），但物理去重靠 filename，重命名即断链。

**建议**（权衡，未必必修）：manifest 引入 topic 层 canonical 索引（filename→canonical mat_id），variant manifest 只存引用。记录为 friction——模型对比要隔离，是否改取决于是否常需跨变体引用。

---

## 运行结论（meta）

主摩擦集中在**「多变体对比/换模型重研」工作流未被当主路径一等公民设计**：周边工具链缺继承/fallback、闸门对空变体空过、fetch fan-out 抓噪音、父料接口信息不全。但**核心复用机制（materials slug 共享 + set_parent_materials + findings 本变体重抽 + thesis 自押注）设计是自洽的**——是周边工具链与文档没跟上。

按 ROI 排序修复：① P7(fetch fan-out 噪音，影响下游全链) ② P4(coverage 空过报 warn) ③ P5(list_parent_materials 给 metadata) ④ P3(resolve_parent_variant fallback canonical) ⑤ P1/P2(命名/文档) ⑥ P8(权衡，未必改)。

---

# 附录：完整重跑（00→05）新增问题（2026-06-19 第二轮，glm5.2）

> 第一轮只跑 01 部分 + 抓问题；本轮按用户要求完整重跑 00→05。下面是完整跑流程中新发现/复现的问题。

## P9 — `fetch(annual/quarterly)` 公告 fan-out 噪音在完整流程中**重现并放大** `[BUG][DRIFT]`

**现象（重跑实测）**：跑 6.5a eager-fetch 下 3 份年报/季报（斯瑞 2025年报、斯瑞 2026Q1、铂力特 2025年报），实际下载并登记 **57 份材料**（3 份真报告 + 54 份噪音公告）。噪音构成：斯瑞 24 份（定增募集说明书/保荐/法律意见/股东会/行权/异常波动…）、铂力特 30 份（减持/分红/外汇套保/董秘离任/异常波动…）。全部 source_type=`quarterly-report`、rings 全标 `peer-comparison-financials`、addresses=None。**噪音占比 54/57 = 95%**。

**完整流程的下游影响（实测）**：
- `read_manifest` 返回 57 条，gap_detector / coverage 虚高（以为 K4 有 30+ 份财报料）。
- 03 findings 若不剔除，会把保荐书/法律意见当财报读。
- 我不得不手动 `remove_material(delete_file=True)` 清掉 54 份噪音 PDF + manifest 条目。

**结论**：P7 不是偶发——只要 `fetch(annual)` 就稳定触发 fan-out，且噪音占绝对多数。这是阻断"换模型重研"复用场景的最大工具 bug。

---

## P10 — MinerU 200 页限直接撞墙（年报），需手工切到 `annual_report_extractor` `[CONFUSION][DESIGN]`

**现象**：03 Step 2.1 对 PDF 默认走 `scripts.mineru_api.convert`，但年报普遍 >200 页，MinerU 直接报"number of pages exceeds limit (200 pages), please split"并重试 3 次全失败（每次等 10s，浪费时间）。

**问题**：
- 年报 / 10-K 是最常超 200 页的料型，mineru 对它必然撞墙。
- 工具分工设计（DESIGN.md：年报走 `annual_report_extractor` 不走 mineru）是清楚的，但 03 workflow 默认脚本路径仍可能先撞 mineru；没有"按 source_type 自动路由 extractor"的前置分流，靠主 agent 记得换工具。
- manifest 里 `annual-report` 的 `mineru_state` 已默认 `not_needed`（知道不走 mineru），但 03 Step 2.1 的文档引导仍把人带到 mineru convert。

**实测**：手工换 `python3 -m scripts.annual_report_extractor` 成功（斯瑞年报提 83915 字，2 章节：第三节管理层讨论+第五节重要事项）。**但 extractor 不接 `--slug/--variant` 参数**，输出路径要手工指定，且不自动登记进 manifest / 不 mark_processed——又是"机械活但脚本没接全"。

**建议**：① 03 Step 2.1 按 `source_type` 自动分流（annual-report→annual_report_extractor，sell-side→mineru-vlm），不要靠人记。② `annual_report_extractor` 接受 `--slug/--variant` 自动落盘 slug 级 `materials/{stem}_extracted.md` + mark_processed（与 fetch_report_prism 对称）。

---

## P11 — `register_web_search_batch` 频繁 all_low_band，权威源被当 low 丢 `[DESIGN]`

**现象（重跑实测多次）**：WebSearch 命中的合法权威源反复被判 `band='low'` 全 drop：
- **NASA NTRS**（ntrs.nasa.gov，NASA 官方技术报告库）→ low band，drop。
- **慧博研报库**（hibor.com.cn，卖方研报聚合）→ low band，drop。
- **同花顺 F10**（basic.10jqka.com.cn）→ low band，drop。
- **metal-am.com**（增材制造行业期刊）→ low band，drop。
- **wikipedia / mountbonnell**（百科/分析）→ low band，drop。

**问题**：
- 这些都是合法甚至权威的研究源，但 confidence 启发式（domain_tier 自动判）把它们打到 <0.5，全 drop，`failure_mode='all_low_band'`。
- workflow 要求"走 H2 救回：extract_url_features → LLM 判 tier → 带 `domain_tier='llm-judged-official'` 重 register"。**这是有效但极重**：每条丢的料要手工判 + 重调一次。本轮光 H2 救回就做了 3 批（光启、K4 估值、K2/K3）共 6 次 register 调用。
- 对"换模型重研"场景，同一个 query 不同模型跑会重复触发同样的 low-band drop + 救回，重复劳动。

**建议**：① 把"研报聚合库(hibor/慧博/wind 公开)、NASA/gov 域、行业期刊"扩进 whitelist 或提高 confidence 默认，减少误 drop。② H2 救回做成批量（一次传多 url + 批量 tier 判定），而非逐条。

---

## P12 — API 签名顺序不一致：`mark_processed(slug, mat_id, variant)` vs `set_output_status(slug, output_key, status, variant)` `[CONFUSION]`

**现象**：
- `mark_processed(slug, mat_id, variant)` — variant 在最后
- `set_output_status(slug, output_key, status, variant)` — variant 在最后 ✓
- `mark_todo_fetch(slug, variant, task, status)` — variant 在第二
- `update_user_todo_status(slug, variant, task, status)` — variant 在第二
- `set_parent_materials(slug, variant, items)` — variant 在第二

variant/mat_id/输出key 这些"上下文锚"的参数位置，**`mark_processed` 把 mat_id 放 variant 前面，其余 todo 类把 variant 放第二**——两套顺序。我在重跑中 `mark_processed(slug, mid, 'glm5.2')` 第一次写反成 `(slug, 'glm5.2', mid)` 报 FileNotFoundError。

**建议**：统一 variant 参数位置（建议都在 mat_id/key 之后、或都在第二）；至少在 docstring 顶部标注。

---

## 完整流程跑通总结

**已实际产出（glm5.2 variant，落盘文件）**：
- `topic.yaml` / `manifest.yaml`（21 份有效材料，噪音已清）
- `baseline_knowledge.md`（10 facts + 8 优先 query）
- prescan：18 high-band web-search mat（含 H2 救回）
- `thesis_v0.md`（6/10）→ `thesis_v1.md`（合成后）→ `thesis_v2.md`（critic 下修至 4/10）
- `decomposition_v0.md`（3 命门 + 8 primer 目标）
- `roadmap.yaml`（K1/K4 L4 hunting）
- 2 份年报 `_extracted.md`（斯瑞 + 铂力特，pymupdf，slug 级复用产物）
- 2 份 `findings_mat-*.md`
- 3 份合成产出：`00_primer.md` / `a_arena_case.md`（6 环决策链）/ `peer_matrix.yaml`（financial_data 实拉数）
- `critic_review.md`（独立反方，下修 verdict）

**流程真实结论**：prism 的核心研究链（baseline→prescan→thesis→decomposition→roadmap→fetch→findings→synthesize→critic）是**可跑通且产出质量在线**的——financial_data 实拉数、年报 extractor 实提取、critic subagent 给出了真有杀伤力的反方（K3 耐用品矛盾）。主要摩擦都在**周边工具链**（fetch fan-out 噪音 P9、MinerU 200 页 P10、low-band 误 drop P11、参数顺序 P12）和**多变体复用的一等公民缺失**（P3-P5），核心方法论（bet-first thesis + 6 环决策链 + 独立 critic）本身稳健。

最高 ROI 修复仍是 **P9（fetch 噪音，95% 噪音占比）**——它污染整条下游链路且每次复用都重现。

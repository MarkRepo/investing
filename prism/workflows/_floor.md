# 血教训不变量（Floor · F1-F11 + 附加铁律）

> **横切不变量，恒成立**。可进 guard 的已标"已下沉脚本"；无法机械化的留散文。
> 删改本文件任何一条前，必须确认该条不在附录 D——在的只能"散文→guard"搬移，**不能删除**。
>
> 格式：**铁律** | 出处 | 为什么（踩坑） | 当前强制方式 | 可否机械化

---

## F1 — web finding 必来自真实 hit，禁凭记忆补 URL

**铁律**：任何写进 manifest/finding 的 web URL，必须来自 WebSearch/exa 工具真实返回的命中，
禁止用训练记忆补写 URL，禁止猜测或伪造。

- **出处**：`_web_prescan_shared.md`:68/350、`03-extract-findings.md`:495、`_subagent_deep_search.md`:48
- **为什么**：训练记忆幻觉 URL 污染 manifest，下游产出不可靠，无法溯源，
  被动探针抽检时 URL 为 404 或指向无关内容。
- **当前强制**：散文 + `register_web_search_result` 拒绝占位/编造特征 URL（已 raise）
- **可否机械化**：难（合法格式无法区分真假，需 hook 验活）

---

## F2 — subagent 只产 markdown 到 final message，主 agent 落盘；禁 subagent 写文件/heredoc

**铁律**：dispatch 的 subagent 只负责"产出文字到 final message"，
主 agent 读 final message 后用 Write 工具落盘；禁止在 subagent prompt 里让它用 Write/heredoc 直接写文件。

- **出处**：`_subagent_deep_search.md`:35、`03-extract-findings.md`:217-233
- **为什么**：2026-05-22 实测 4/4：subagent Write 总幻觉"被拦截"错误，
  声称的 heredoc 绕过也是幻觉。subagent 无论如何都不能写文件，声称写成了=幻觉。
- **当前强制**：散文（dispatch prompt 内嵌提示）
- **可否机械化**：中（主 agent 侧 watchdog 可检测 subagent final message 中 Write 命令痕迹）

---

## F3 — 研报/行业报告必经 mineru vlm；失败必报+跳过，禁 pymupdf 偷工

**铁律**：source_type∈{sell-side-note, industry-research, policy} 的 PDF 必须走 mineru vlm 提取，
不得用 pymupdf/pdfplumber 等直接读 PDF。失败则报告错误并跳过，不降级用其他工具。

- **出处**：`02-gather-materials.md`:170、`03-extract-findings.md`:279-282/317-323
- **为什么**：pymupdf 丢表格/公式/多栏，研报关键数据在表格（估值矩阵/财务拆解），
  直接读 PDF 会漏掉最有价值的数字。
- **当前强制**：散文 + `test -f {stem}_vlm/full.md` 检查；add_material 自动标 mineru_state=needs
- **可否机械化**：部分（入口检查 mineru_state；绕过直读需 hook 拦截）
- **MINERU 精确调用**：`.venv/bin/python -m scripts.mineru_api "{path}" --out "{stem}_vlm" --model vlm`
  产物路径：`prism/topics/{slug}/materials/{stem}_vlm/full.md`（slug 级共享）
  环境变量：`MINERU_TOKEN`（不是 MINERU_API_KEY）；禁止改第三参 vlm 为 pipeline/pymupdf

---

## F4 — `_extracted`/`_vlm` 是 slug 级确定性产物，findings 按 variant 隔离

**铁律**：年报 `_extracted.md` 和研报 `_vlm/full.md` 是 slug 级共享产物（路径在 `materials/`），
跨 variant 不重跑。findings 笔记（`findings_{mat_id}.md`）按 variant 隔离（在 `{variant}/outputs/`）。

- **出处**：`03-extract-findings.md`:250-264
- **为什么**：跨 variant 重跑 mineru 浪费配额；把 findings 写错路径会导致 FileNotFoundError
  或读到错误 variant 的笔记。
- **当前强制**：散文 + 幂等跳过（已有则不重跑）；`add_material` 校验路径属 slug 级 materials/
- **可否机械化**：低

**变体复用与隔离边界（物理目录即规则）**：

| 产物 | 目录 | 共享/隔离 |
|------|------|---------|
| `materials/`（PDF、`_vlm/full.md`、`_extracted.md`） | `prism/topics/{slug}/materials/` | slug 级共享 |
| 其余一切——`manifest.yaml`、`findings_*.md`、`roadmap.yaml`、`thesis_v*.md`、`decomposition_v*.md`、`outputs/`（primer/case/sidecar）、`topic.yaml` | `prism/topics/{slug}/{variant}/` | variant 级隔离 |

**硬规则**：同 slug 不同 variant **禁止跨 variant 目录引用**（如 deepseekv4pro 产出不得引 opus4.8 的 findings）。父 topic 借料见 F7，父级复用指定 variant 规则见 `set_parent_materials`（`parent_variant` 显式传或 `model_registry` 兜底解析；不确定时不猜、AskUserQuestion）。

---

## F5 — todo 身份=文档，非 K#；脚本零自动撮合，闭环须显式

**铁律**：user_todo 的闭环键是 `task`（文档身份描述），不是 K# 标签。
一个 K# 可能被多条不同文档的 todo 共享，不代表任意一条到手就能闭合其他条。
禁止用 K# 交集自动撮合 todo。闭环只走按 task 子串的显式调用。

- **出处**：`_autofetch_protocol.md`:42-51
- **为什么**：旧 K# 交集自动闭环：共享 K# ≠ 文档到齐，导致已删 `auto_resolve_todos` 曾误闭环。
  错误示例：年报和研报都挂 K2，年报到手不等于研报任务完成。
- **当前强制**：散文（旧 auto_resolve_todos 已彻底删除）；
  `update_user_todo_status` 拒绝无 task 子串的批量闭环（guard 增强，见阶段 2）
- **可否机械化**：低（update_user_todo_status 已加 guard 防 K# 批量自动撮合）

---

## F6 — gap 是诊断不是 gate

**铁律**：`detect_gaps` / `gap_detector` 的输出只是诊断报告，由 LLM 读后判断是否补救。
脚本不因 gap 存在而拒绝前进（不 raise）。gap 缺口是"写时要诚实标注"，不是"不允许推进"。

- **出处**：`02-gather-materials.md`:291、`03-extract-findings.md`:36/64、`04-synthesize/_shared.md`:45
- **为什么**：设计选择——LLM 的判断比机械 gate 更灵活；
  比如 `*-mirror` 类 gap 几乎必报红（复用旧料缺历史镜鉴类资料），但这不是真正的数据缺口，
  可以用训练知识 depth 降级处理，不应卡死流程。
- **当前强制**：半（detect_gaps 不 raise；set_stage 不拒）；**不应完全机械化**（设计选择）
- **可否机械化**：不应完全机械化（设计选择，LLM 判读 gap 意义）

---

## F7 — 跨层借料必标来源、本维度自跑、冲突本 topic 赢；父级 finding 缺失须查

**铁律**：
1. 从父/子 topic 借来的判断/产出，正文里必须可见地标出（borrowed-from-relative，类似 mat-XXX 分层）
2. 本 topic 不能因"亲属已覆盖"放水，必须本维度自跑完整链（gap 检查、critic 等）
3. 亲属观点与本 topic findings 冲突时，以本 topic 自己的 findings 为准，允许背离，并触发把亲属标 stale
4. 父级 finding 缺失（`list_missing_parent_findings` 返回非空），须主动查原因

- **出处**：`03-extract-findings.md`:42-64/430-435
- **为什么**：feedback_addresses_granularity：父级假覆盖，子 topic 相关 K# 静默跳过。
- **当前强制**：`list_missing_parent_findings` 已机械化 + `conflicts_with` optional field
- **可否机械化**：中（存在性可检查，冲突仲裁需 LLM）

---

## F8 — prescan 与 todo 无交集

**铁律**：prescan（web 事实校准）只入库校准事实（addresses=['scope']）+ 写 log，
不产生、不闭环任何 user_todo。禁止用 prescan 的搜索结果去闭合 todo。

- **出处**：`_autofetch_protocol.md`:14、`_web_prescan_shared.md`:297-300
- **为什么**：旧 `suggest_todo_coverage_candidates` 函数造假覆盖已删除——prescan 是校准事实的工具，
  不是收料任务的替代。prescan 入库料标 triggered_by='00-prescan'，不对应任何具体文档 todo。
- **当前强制**：散文（assert prescan triggered_by 不得调 todo 闭环）
- **可否机械化**：低

---

## F9 — H2 tier 救回闭环

**铁律**：web search 入库时，若 drop_ratio > 0.8（高失血），必须执行 H2 救回：
调 `extract_url_features` 对被丢弃的 hits 做 LLM tier 判定，
对判断为官方/高可信的结果带 `domain_tier='llm-judged-official'` 重新 register，
不得静默丢弃大量高质量 hit。

- **出处**：`_web_prescan_shared.md`:135-143/226-265
- **为什么**：2026-05 荣昌案例：P0 6 条 query 共 40 hits，仅 4 条入库（80% 失血）——
  因非白名单域名默认 confidence 0.4，被判 low，全丢。导致关键证据丢失。
- **当前强制**：散文 + `register_web_search_batch` 返回 drop_ratio/dropped_hits 供 LLM 判断；
  `extract_url_features` 提供 H2 救回工具；F4 域族晋升（自动）
- **可否机械化**：部分（drop_ratio>0.8 自动提醒救回，但 tier 判定仍需 LLM）
- **`prism search` 动词**（阶段 2 新增）：包装此完整流程（枚举覆盖槽→搜→落盘→去重→健康检查→H2 救回）

---

## F10 — 三态盖戳 fetched/empty/error + R1/R2/R3

**铁律**：
- **R1 全覆盖**：所有 tier（含 tier3）、所有 info_tier（含 hard）的缺口都要尝试；info_tier 只决定努力强度，不作为跳过门槛
- **R2 有效尝试**：一次有效尝试=搜索真的跑了且公开确实没有→才可降级；工具/网络/限流故障不算尝试，必须重试，不得据此降级
- **R3 消费前兜底**：消费某 todo 的材料前确认它已被有效尝试（`pending_unfetched_todos` 检查）

每次尝试后必须用 `mark_todo_fetch` 盖 fetch_status：`fetched`/`empty`/`error`。
fetch_status=empty 触发 empty 硬闸门（必须 AskUserQuestion 让用户决策 waived/will_collect）。

- **出处**：`_autofetch_protocol.md` 全文
- **为什么**：旧 info_tier=hard 当跳过门槛；error 当"没有"降级，可获取料静默缺失。
- **当前强制**：散文 + `pending_unfetched_todos` 阻断升 stage（guard 增强，见阶段 2）
- **可否机械化**：低-中

---

## F11 — time_sensitivity 三分类 + 多市场口径

**铁律**：
- **time_sensitivity 三分类**（合成时必区分）：
  - **静态**（多年不变）：工艺原理/商业模式类型/估值框架——用训练知识无须标时效
  - **慢变**（年级，训练截止 vs 今 ≥12 月可能不准）：市场份额/财务率/监管框架——标训练知识估算
  - **快变**（季月级，≥3 月大概率过时）：价格/库存/汇率/利率/政策细则——必须有实收料，禁用训练知识
- **快变+高/中置信 fact 必在第五节有校准 query**（prescan 或 todo）
- **多市场口径**：持有 A/H/ADR 时，估值/资金/公告 fact 必标市场口径；`topic.yaml.extra_tickers` 表达多 ticker

- **出处**：`_baseline_knowledge.md`:34-48/68-80
- **为什么**：PRISM_VALIDATION F3：旧版对所有行业写死"产能变化"——没有区分时效，导致快变 fact 用了过期训练知识
- **当前强制**：散文 + baseline 自检清单
- **可否机械化**：低-中

---

## 附加铁律

### A1 — empty 硬闸门

**empty_undecided_todos 非空前，不进决策链、不写任何缺口。**
非空时必须 `AskUserQuestion`（multiSelect）逐条让用户选 waived/will_collect。
只有全部处置完（`empty_undecided_todos` 空）才继续。

- **出处**：`_autofetch_protocol.md`:95
- **当前强制**：散文 + `_shared.md` 调度模式第 0 步硬闸门

### A2 — AskUserQuestion 禁中文弯引号

AskUserQuestion 的 label/description 禁止使用中文弯引号 `""`（U+201C/U+201D），
否则触发 InputValidationError。改用直角引号 `「」` 或不加引号。

- **出处**：计划第 8 部分规矩 6
- **当前强制**：散文规约

### A3 — WebSearch 静默返空靠 failure_mode 字符串分流

WebSearch/exa 返回空时必须检查 `failure_mode` 字段：
- `upstream_empty`：真没有（有效空，可标 empty）
- `all_low_band`：有命中但全低质丢弃（不算空，先走 H2 救回，见 F9）
- `none`：正常入库
不得把 failure_mode 非 upstream_empty 的情况当"公开没有"降级。

- **出处**：`_web_prescan_shared.md` + `_autofetch_protocol.md` 判定表 A
- **当前强制**：散文规约

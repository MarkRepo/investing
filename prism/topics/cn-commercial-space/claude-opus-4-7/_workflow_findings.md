---
slug: cn-commercial-space
variant: claude-opus-4-7
written_at: 2026-05-26
scope: workflow 00 全流程实跑观察
---

# Workflow 00 流程缺陷与可优化点

> 本文档记录在执行 workflow 00（新建 topic）跑 cn-commercial-space/claude-opus-4-7 变体过程中观察到的流程问题。
> **写作原则**：只记可重现的问题，附"复现条件 / 影响 / 建议修法"。

---

## 使用提示 #1（非缺陷）：Step 3 没显式提示"跨 variant 资料天然共享"

**澄清**：原以为"多 variant 不能复用资料"是 workflow 缺陷，**实际架构已支持**：

- `prism/topics/{slug}/inbox/web-search/` 和 `prism/topics/{slug}/materials/` **是 slug 级共享池**，所有 variant 看到同一份文件
- `add_material` 内置 dedup（filename 命中即跳过）
- `get_material_path` 三级查找 `materials/` → `inbox/manual/` → `inbox/auto/`

新 variant 想用旧 variant 已下载的资料，只需要 `add_material(slug, variant=新variant, filename=已有文件名, source_type=...)` 把它加进自己 manifest 即可，**不需要任何额外软链接机制**。

**轻量改进建议**（非阻断）：
- workflow 00 Step 3 在"创建新变体"分支里加一句提示："`ls prism/topics/{slug}/inbox/` 和 `prism/topics/{slug}/materials/` 可看到其他 variant 已有的共享资料，可用 `add_material(filename=...)` 直接复用，无需重复下载"
- 可选：提供 `prism.scripts.manifest.import_from_variant(src_variant, dst_variant, filter=None)` 把另一个 variant manifest 里所有 mat 条目批量加进当前 variant manifest（按 filename 共享同一物理文件）—— 这只是便利脚本，不修核心

---

## 缺陷 #2：baseline 模版第五节 query 数量上限无指引（严重度：低）

**复现条件**：写 baseline_knowledge.md 第五节"需要 web-search 校准的优先项"时。

**现状**：模版只说"5-10 条"，没说"过多"会撞 Step 4.5a 的耗时上限。

**影响**：本次我列了 12 条 query（已超上限），每条 WebSearch 约 5-10 秒 + 入库写盘约 1 秒，12 条耗时 2-3 分钟。如果用户列 30 条会拖到 10 分钟+。

**建议修法**：模版明确"**严格 5-10 条上限**，超出请拆分到 workflow 01 prescan"，或显式增加"按重要性排序，前 8 条必跑、9-10 条选跑"的纪律。

---

## 缺陷 #3：默认 build_search_queries 生成的 query 过于宽泛 + Q1 含问号（严重度：高）

**复现条件**：Step 4.5b 默认模板 prescan 阶段调 `build_search_queries`。

**现状**：脚本生成 5 条 query：
1. `中国商业航天 中国商业航天产业链上 A 股可投标的目前的真实位置在哪？哪些是 alpha、哪些是主题炒作？2026 当下能不能买、买什么、什么价位、什么情形止损？`（**87 字 + 含问号 + 重复"中国商业航天"前缀**）
2. `中国商业航天 行业政策`
3. `中国商业航天 技术突破`
4. `中国商业航天 产能变化`
5. `中国商业航天 龙头新闻`

**问题**：
- Q1 把 topic.yaml.scope.question 原文塞进 query，长度+问号让搜索引擎命中崩塌（实测确实命中差）
- Q2-Q5 "行业政策/技术突破/产能变化/龙头新闻"四个模板词太宽泛，**4 条 query 的命中域重叠严重**（都是同样的"商业航天 2026"展望类文章），信息密度低

**影响**：默认模板 prescan 信息密度远低于 Step 4.5a baseline 优先 query；4.5b 跑得越多反而越浪费 quota。

**建议修法**：
- Step A 构造 query 时**截断 scope.question** 到 60 字以内 + 去除问号
- 模板词从"政策/技术/产能/龙头"改为更具体的事件型查询："{topic} 2026 政策文件 国务院"、"{topic} 2025 年报 业绩"、"{topic} IPO 上市公司"、"{topic} 与 {竞品/国际对标} 差距"
- 或在 baseline 第五节有 >8 条优先 query 时**自动跳过 4.5b 模板**（避免重复消耗 quota）

---

## 缺陷 #4：thesis 模板 V# 与 user_todos 契约不一致（严重度：中 — 致流程报错，但本质是模板冗余）

**复现条件**：Step 5.0 thesis 模板"研究中重点验证项"明确使用 V1-V5 编号；Step 6 用 set_user_todos 时把 V# 写入 addresses。

**现状**：`_normalize_todo` 仅接受 `K#` / `Q#` / `K#@event-slug`，传 `V3` 直接 `raise ValueError`。

**影响**：本次我第一次提交 set_user_todos 因为 `['Q1', 'V3']` 报错，被迫把 V# 全部映射回 Q#。

**深思后的修法（修模板，不是修脚本）**：

V# 在模板里的定义是"把支持理由 + 反方观点 + **Killer Question** 转成具体待查清单，引导后续 workflow 01 路线图"——它本质就是 K#/Q# 的派生细化，**不是新维度**。让 addresses 同时认 V# 会：
1. K# 覆盖闭环 self-check 矩阵复杂化（todo 要在 K/Q/V 三层都查覆盖）
2. 同一论证目标在 thesis 里出现三次（支持/反方 → K# → V#），冗余
3. V# 是 thesis 内部"行动转译"，作用是引导 workflow 01，不该跨界进 todo addresses

**推荐修法**：删除 thesis 模板第 5 段"研究中重点验证项 V#"，把它合并进 Step 5.3 user_todos —— **todo 本身就是验证项**，每条 todo 用 `addresses=[K#, Q#]` 标明它在攻打哪个论证目标。这样：
- thesis 收敛为 4 段（核心 / 支持 / 反方 / Killer Question）
- user_todos 直接承担"验证项"角色，无重复
- K# 覆盖闭环 self-check 矩阵保持简单

脚本 `_normalize_todo` 不动 —— 让契约保持紧凑。

---

## 缺陷 #5：append_search_log 的 n_results 等参数没有自动汇总能力（严重度：低）

**复现条件**：Step F 写 search log 汇总时。

**现状**：n_results / n_high / n_mid / n_low 需要主 agent 手数。本次 17 条 query，我手算"11 high + 6 mid"——容易错。

**建议修法**：`register_web_search_batch` 返回的 dict 累积计数，最后 `append_search_log` 直接读 `count_band_since(triggered_by)`。

---

## ~~缺陷 #6~~（撤回）：Step 4.5c 校准回写仍人工

**原以为**：15 分钟手工扫 41 fact × 17 hit 太累，要脚本化。

**复盘**：4.5c 的本质是"对照新事实判断 fact 是否被推翻"——这是**语义判断**，本就该 LLM 做。脚本只能按 mat.addresses 机械匹配，但 addresses 颗粒度是 K#/Q#（不是 fact-NN），强行预填"骨架"反而会误导主 agent。Edit 工具追加足够。

且 `_baseline_knowledge.md` 前置已有缩 4.5c 范围的机制：
- 第一节加 `time_sensitivity`（静态/慢变/快变）二维标签
- 第五节强制"快变+高/中 fact 必须有对应 query"
- 第一节落盘前自检：静态 N 条/慢变 N 条/快变 N 条 + query 数 ≥ 快变 fact 数

跑出来的效果是：4.5c 只需要重点扫"快变 fact"（静态/慢变跳过或快速扫），手工成本天然受控。

**实际是执行偏差**：我跑 4.3 时用了旧版结构（只标"置信度：高/中/低"，没标 time_sensitivity），导致 4.5c 没法按时效快速分流——这是我自己漏看模版更新，不是 workflow 缺陷。

---

## 缺陷 #7：thesis Killer Question 覆盖闭环 self-check 是手工表，无脚本辅助（严重度：低）

**现状**：Step 5.0 要求 thesis 写完后做 self-check：`列出每个 K# → 检查是否至少有一个 todo 的 addresses 引用了它`。本次我手做了一个表格，但如果 Killer Question 多（10 个+）容易漏。

**建议修法**：提供 `python3 -m prism.scripts.thesis_coverage_check {slug} {variant}`：
- 解析 `thesis_v0.md` 提取所有 K# 编号
- 读 topic.yaml user_todos.addresses
- 输出覆盖矩阵 + 漏覆盖 K# 警告
- Web /prism/{slug}/{variant}/ 详情页那个 `K1✓ K2✓ K3✗` strip 应该直接走这个脚本

---

## ~~缺陷 #8~~（撤回）：multi-variant inbox 数据混淆

**复盘**：原以为 51 个 inbox 文件 = 17 条本次 + 34 条其他 variant 残留 → 怀疑 confidence 混淆。
**实际**：51 个文件全是本次 2026-05-26 创建（17 条 query × 平均 3 hit ≈ 51）；其他 5 个 variant 之前根本没跑过 prescan（他们的 manifest 各 5 条都是 5-09 用户手放的 sell-side-note PDF）。

inbox/web-search 是 slug 级共享池**是设计**：filename dedup 节省下载/存储，每个 variant 各自维护 manifest 引用同一物理文件 → 多 LLM 评测时反而**便于横向对照**（同一份资料喂不同模型）。无问题。

---

## 高优先排序

| 缺陷 | 严重度 | 立即影响 | 建议 |
|---|---|---|---|
| #4 V# 不支持 | 中 | 致 set_user_todos 报错 | **修模板**：删 thesis 第 5 段 V#，让 user_todos 承担验证项角色（V# 本就是 K#/Q# 派生） |
| #3 build_search_queries 太宽泛 | 高 | 4.5b prescan 信息密度低 | 修脚本 query 模板 |
| ~~#6~~ baseline 校准回写靠人工 | **撤回** | 4.5c 是语义判断本就该 LLM 做；模版 time_sensitivity 标签+第五节"快变 fact 必须有 query"已经做了前置防漏。我跑 4.3 漏标 time_sensitivity 是执行偏差 | — |
| ~~#1~~ 多 variant 不复用 | **撤回** | 架构已支持（inbox/materials 是 slug 级共享池，add_material 自带 dedup）| 仅可加文档提示（非阻断）|
| #2 baseline query 数量无上限 | 低 | 拖长 prescan | 模版加纪律 |
| #5 search_log 手数 | 低 | 易统计错 | 自动汇总 |
| #7 Killer Question 覆盖 self-check 无脚本 | 低 | 大 thesis 易漏 | 补脚本 |
| ~~#8~~ multi-variant inbox 混淆 | **撤回** | 实际是设计：inbox/web-search 是 slug 级共享池 + filename dedup。我入库 17 query × 平均 3 hit ≈ 51 文件，数对得上，无混淆 | — |

---

## 业务侧观察（非流程缺陷，但对"高密度知识"目标重要）

**A. baseline 优先 query 比模板 prescan 信息密度高 5-10 倍** — 本次 4.5a 12 条 baseline query 拿到的高质量事实数 ≈ 4.5b 5 条模板 query 的 5 倍以上。说明 **baseline-driven prescan > template prescan**，应该把模板 prescan 权重降低、把 baseline 第五节 query 数量适度放宽。

**B. 卖方研报快讯 + 财经新闻是商业航天领域最有用的源** —— 行业垂直站点（航天网、卫星与网络）反而搜索权重低。

**C. 中文金融搜索"2026年"等关键词带年份的查询，会被搜索引擎补"未来展望"类垃圾结果稀释** —— 建议 query 用"yyyy年 + 实证关键词（业绩/订单/发射次数）"组合，避免"2026 + 展望"类被绑定。

**D. ITU 频段保留这类"已发生 but 未被市场定价"的事实** —— prescan 第一轮就能找到，但需要主 agent 在 thesis 中主动提炼为"未定价空头逻辑"。这正是 thesis-driven 研究相对于"百科全书式覆盖"的核心价值。

---

# Workflow 02 流程缺陷与可优化点（2026-05-26 推进时观察）

## 观察 #9（架构演进后劲）：workflow 02 几乎"空跑" — **已修（2026-05-26）**

**修法**：workflow 02 文件开头加 "⚠️ 前置自检" 段，含：
- 一段脚本 echo `should_run_step0` / `list_pending_mineru` / `material_count` / inbox 残料三方现状
- 4 条主 agent 行为约束（不要怀疑 inbox/materials 已有文件 / 不要硬找事 / Step 5.7/5.8/6 必跑）
- 3 个"才需从 Step 0 跑起"的反例条件（用户新放料 / prescan >7d / 01 没跑 auto-download）


**复现**：workflow 01 已完成自动下载 + prescan 入库后，跑 workflow 02：
- Step 0：`should_run_step0` 判跳过（prescan 0 天前刚跑）
- Step 1-4：107 mats 全部在 workflow 00/01 阶段已登记（web-search 84 + annual-report 23）
- Step 4.5 mineru：23 份年报全 `mineru_state=not_needed`（设计：走 annual_report_extractor）
- Step 5.7：100% K# coverage
- Step 5.8：0 gap

**实际只跑 Step 5.7/5.8/6（升 stage）。**

**复盘**：这不是 bug，是 workflow 01 自动化吃掉了 02 的 80% 工作量（原设计 01=规划 / 02=收齐+登记，现在 01 已能 auto-download + prescan）。

**建议轻量修法**（非阻断）：workflow 02 文件开头加一段"前置自检"：
```
若上一步 workflow 01 已完成 auto_download_annual_reports + prescan，
本 workflow Step 0-4 大概率全跳过，直接进 Step 5.7。
不要把"必须跑完每个 Step"理解为"必须重做"。
```

## 观察 #10（已实证 → 已修 2026-05-26）：annual_report_extractor 表格丢失

**现状**：`_default_mineru_state` line 91 注释 "年报走 annual_report_extractor 不走 mineru"，annual_report_extractor 走 PyMuPDF + TOC 关键词圈章节。

**覆盖**：管理层讨论 / 主营业务 / 行业情况 / 核心竞争力 / 风险因素 / 研发情况 / 未来发展。

**SKIP 关键词**：财务数据 / 股东情况 / 公司治理 / 环境社会责任 / 债券 / 释义。

**潜在丢失**：
1. 经营段内嵌**子表格**（分产品营收占比、产能数据、客户集中度、关联交易）— PyMuPDF 抽文字时保留，**但表格行列对齐质量低**，LLM 抽数易出错
2. 「重大事项」段（再融资 / 收购 / 诉讼 / 政府补助）有时在「公司治理」邻近，被 SKIP 规则误杀
3. 科创板早期年报 TOC 不规范 → 章节漏匹配（电科蓝天 SSE_688818 这种新上市的特别要关注）

**实证**（对比 4 份历史年报 + 1 份现场跑）：所有抽取结果 markdown 表格行数全部为 0，表格被 flatten 成纯文本流。中国卫星「主营业务分行业 11 行 × 7 列」、子公司汇总「7 行 × 9 列」全部丢结构。

**修法**（已实施）：`scripts/annual_report_extractor.py:_extract_page_text` 加入 PyMuPDF `find_tables()`：
- 每页同时抽 `get_text("blocks")` + `find_tables()`
- 用 bbox 中心点判 block 是否落在表内 → 剔除避免重复
- 表格转 markdown（`_table_to_markdown` 新函数）
- 按 y_top 顺序穿插回文字流

**效果对比**（铖昌科技 2025 年报）：
| 指标 | 老版 | 新版 |
|---|---|---|
| markdown 表行 | 0 | 644 |
| 数字密度 | 38 | 37（一致） |
| 总行数 | 7798 | 2722（精简：表内文字不再重复） |

**遗留限制**（暂不修）：
- 合并表头 PDF（如铖昌「2025 年/2024 年/同比增减」三级嵌套）被 pymupdf 拆成 19 列（含 13 空列）— 数字仍按行连续可读，但视觉冗余。可后置加 "merge empty columns" 后处理
- 同一表在「营业收入构成」+ L2 章节抽取时**重复出现两次** — 这是 `extract()` 函数 L1+L2 嵌套页范围导致的**老 bug**（老版也有，只是表是扁平文字看不出），不在本次修复范围

**比 VLM 路线优势**：每页 +50ms（vs VLM 5-20s/页），23 份年报总耗时 +30s（vs VLM 12 小时）。Born-digital PDF 表格用 PyMuPDF 完全够用。

## 观察 #11（低）：validate_manifest_coverage 返回 per_k 为空

**现状**：脚本返回 `coverage_pct=100` + `covered=[K1...K6]`，但 `per_k` dict 为空，**无法看每个 K# 实际收料数**。

**影响**：无法识别"K1 有 20 份 / K6 仅 3 份"的不均衡，"全覆盖"假象可能掩盖结构性偏科。

**建议**：扩展 `validate_manifest_coverage` 返回 `per_k = {K#: [mat_id, ...]}` 而非只算 set 覆盖率；workflow 02 Step 5.7 同步打印 "min K# 收料数 / max K# 收料数 / 倍差" 三个数字，>5x 倍差时告警。

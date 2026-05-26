# Workflow Review — global-glp1-obesity 研究全程发现的流程缺陷

> 用户研究 GLP-1 减肥药期间，逐项记录 prism workflow 的流程缺陷与优化建议。
> 全程跑完后整理为正式 PR / 改进 backlog。

---

## ISSUE-001 [Step 4.5a] 并行 WebSearch 全部返回空结果，workflow 无失败检测/重试机制

**触发场景**：00-research-topic Step 4.5a，10 个 baseline 优先 query 并行调 WebSearch。

**现象**：10 次调用全部只返回 `Web search results for query: "..."` 标题 + reminder，无任何 result block，无报错。

**workflow 层缺陷**：
- `_baseline_knowledge.md` / `00-research-topic.md` Step 4.5a 假设 WebSearch 一定有结果，没有"返回为空就重试/降级"的硬规约
- `register_web_search_batch` 接受 `hits=[]` 时不会 raise，只会写空 search_log，主 agent 容易"以为跑完了"实际上一份资料没入库
- 当并行 N 个 query 全部为空时（疑似 rate-limit / 区域限制 / token 问题），workflow 没有兜底要求主 agent 切到 WebFetch / 改 query 重试

**建议修复**：
1. `_baseline_knowledge.md` 第五节落盘后，Step 4.5a 入口加"先用 1 条短 English query 试探 WebSearch 健康度，0 hit 即换 WebFetch / 拆 query / 降级"
2. `register_web_search_batch` 当 `hits=[]` 时 print warning（"⚠️ 本轮入库 0 hit，疑似 search 失败"），让主 agent 一眼看到
3. workflow 文档增加"WebSearch 异常应对"小节：单 query 0 hit → 重试；3 query 连 0 → 切 WebFetch 已知权威 URL；10 query 0 → 暂停 prescan 改用纯 baseline 起步并标 `prescan_skipped: true`

**影响**：高。本次 prescan 全军覆没意味着 baseline 第六节无法回写、thesis_v0 退化为"100% 训练知识"，与 workflow 修正 H1（thesis_v0 必须先 prescan）的初衷直接冲突。

**本次实际处置**：转 WebFetch 拉 Wikipedia 替代（NVO 官网动态/SEC 阻断/LLY 超时后唯一可达源）。Wikipedia 虽是二手聚合，但对已确立的临床数据/监管批准/专利日期是**可接受的中等权威源**。

---

## ISSUE-002 [web_prescan.classify_domain] Wikipedia 默认归 'other' → 0.4 → low band 静默丢弃

**触发场景**：WebFetch 兜底拉 en.wikipedia.org 后调 `register_web_search_batch`，5 份资料若不显式 override `confidence=0.65` 会全部归 low band 直接丢弃（不写 inbox、不进 manifest）。

**workflow 层缺陷**：
- `WHITELIST_DOMAINS` 列表（reuters / FT / SEC / 头部券商 IR 等）合理，但 Wikipedia 对**已确立的临床数据/监管批准/专利日期**是可接受的中等权威源（其页面直接引用 NEJM/FDA/EMA 一手）
- 当前 `classify_domain` 返回 `other`，confidence 默认 0.4 → low → 静默丢弃，主 agent 不知道发生了什么
- 没有"已知中等权威源 → 默认 mid band"的中间档位

**建议修复**：
1. 在 `classify_domain` 加 `MID_TIER_DOMAINS` 列表（en.wikipedia.org / zh.wikipedia.org / nih.gov 摘要页 / clinicaltrials.gov / 等），命中返回 `'mid-tier'`，confidence_for_tier 给 0.6
2. 或在 `register_web_search_result` 当 band='low' 且域名 ∈ Wikipedia 时 print warning 提示主 agent 显式 override
3. workflow 文档 `_web_prescan_shared.md` 加"Wikipedia / clinicaltrials.gov / NIH 摘要等中等权威源应显式 confidence=0.6-0.7"

**影响**：中。本次没踩坑只因为主 agent 主动 override，但 workflow 默认行为对中等权威源不友好，新 topic 主 agent 容易踩。

---

## ISSUE-003 [WebFetch] 同域名前几次成功后突然返回"Unable to verify if domain is safe"

**触发场景**：连续 6-7 次 WebFetch en.wikipedia.org 成功后，第 8 次起返回"Unable to verify if domain en.wikipedia.org is safe to fetch"。同时第 9/10/11 次也全部失败。

**workflow 层缺陷**：
- prism workflow 没有"WebFetch 异常重试 / 切换 URL 模式"的提示
- 主 agent 看到"safe to fetch"消息容易误以为是永久阻断（实际是软限流），可能放弃后续抓取
- `register_web_search_batch` 接受多 hit 入库，但 WebFetch 是一次拉一份 — 当某些 URL 失败时没有"已成功部分继续/失败部分降级"的协议

**建议修复**：
1. workflow 文档加"WebFetch 短时间内 8+ 次同域调用易触发限流，每 5 次后插 60 秒等待或切其他域名"
2. 主 agent 看到"Unable to verify... safe to fetch"应理解为软限流（非永久阻断）
3. `register_web_search_batch` 增加 `register_partial(slug, query, successful_hits, failed_urls)` 支持只入库成功部分 + 记录失败 URL 供后续重试

**影响**：中。本次拉了 10 份后停手，关键 gap（恒瑞/Viking/Hims/CMS final rule/华东）只能转 user_todos。

---

## ISSUE-004 [00 Step 4.5] prescan 失败/部分成功时 thesis_v0 该如何处置缺失明确规约

**触发场景**：Step 4.5a WebSearch 全军覆没，Step 4.5b 跳过（因为 build_search_queries 也是用 WebSearch 跑），实际只靠 WebFetch 凑 10 份 Wikipedia。

**workflow 层缺陷**：
- `00-research-topic.md` Step 4.5/5.0 假设 prescan 一定能跑完，prescan 失败时 `revised_after_prescan: true` 这个 frontmatter 标记意义模糊（部分成功算不算 revised？）
- 没有"prescan_quality" 字段量化本轮 prescan 实际覆盖了 baseline 第五节的多少条优先 query
- thesis_v0 frontmatter 缺少 `prescan_status: full/partial/skipped` 字段，下游 03/04 引用 thesis 时无法判断"这份 thesis 是基于完整 prescan 还是退化版"

**建议修复**：
1. set_thesis 加 `prescan_status` 字段（full/partial/skipped），partial 要求附"未校准条目清单"
2. `00-research-topic.md` Step 5.0 加"prescan 部分失败时的 thesis 写法"小节：明确标注哪些事实仍依赖训练知识、哪些 K# 因数据缺失暂为"低置信度赌注"
3. workflow 05 critic-review 必须扫 `prescan_status: partial`，对未校准条目要求"加 user_todo 补抓"或"明确降级该 thesis 论断的强度"

**影响**：中。本次 thesis_v0 因 prescan 部分成功，必须显式标 partial 并附"仍未校准清单"，否则 03/04 误用退化 thesis 做合成会失真。

---

## ISSUE-005 [Step 5.3 user_todos] info_tier='public' 的资料用户常常依然取不到（环境限制 + 反爬）

**触发场景**：本次 user_todos 列了 4 条 'public' 资料（NVO 6-K / LLY 10-Q / CMS 公告 / HIMS 财报），但实际上：
- SEC EDGAR 在本环境被阻断
- NVO 官网动态加载 WebFetch 看不到内容
- LLY 官网超时

**workflow 层缺陷**：
- info_tier 'public' 假设"Google/Wind 一搜就有"，但当用户委托 LLM 拉取时，**LLM 能否拉到取决于环境**，不是 info_tier 本身
- 现实里"public" 资料常出现"用户自己能拿，但 LLM 拉不到"——需要在 todo 模型里加 `lookup_path: user_only / llm_capable / both`，避免 LLM 重复在已知拉不到的源上浪费

**建议修复**：
1. `_normalize_todo` 加 `lookup_path` 字段（user_only / llm_capable / both），默认 `both`
2. workflow 02-gather-materials 跑 dispatch 抓取前先 filter 出 `llm_capable / both`，user_only 直接转待人工
3. workflow 文档说明：SEC / 公司 IR 静态 PDF / 政府公告主页常被 enterprise security 拦或动态加载失败 → 默认 `user_only` 更安全

**影响**：低-中。本次只是 todo 标签不精，下游 dispatch 跑空一轮才发现。但批量化研究后会成为隐性时间杀手。

---

## ISSUE-006 [WHITELIST_DOMAINS] 缺医药垂直权威源（NEJM / FDA / EMA / clinicaltrials.gov / Endpoints / FierceBiotech）

**触发场景**：本次 thesis 的 K1-K5 中：
- K1 retatrutide 数据 → 一手来源是 NEJM / JAMA / Lancet（学术）+ Endpoints / FierceBiotech / STAT（行业媒体）
- K2 CMS 政策 → 一手来源是 cms.gov（政府）
- K3 sema 专利 → 一手是 USPTO（政府）+ KEI（NGO）+ Bloomberg Law（垂直媒体）
- 现有 WHITELIST_DOMAINS 主要是 reuters/bloomberg/ft/wsj/经济类券商 IR，**医药垂直权威源全部不在列**

**workflow 层缺陷**：
- 医药 / 科技 / 能源等领域的核心一手源都是垂直权威源（行业媒体 + 学术期刊 + 监管），不是综合财经媒体
- 当 prescan 命中这些域名时被归 'other' → 0.4 → low → 丢弃，导致 prescan 实际偏向"二手聚合的综合财经新闻"

**建议修复**：
1. WHITELIST_DOMAINS 按 vertical 分组，medicine 类自动加 nejm.org / jamanetwork.com / thelancet.com / fda.gov / ema.europa.eu / clinicaltrials.gov / endpoints.com / fiercebiotech.com / statnews.com
2. topic.yaml 加 `vertical: medicine / energy / fintech / robotics / ...`，prescan 按 vertical 选 WHITELIST 子集
3. workflow 00 Step 4 创建 topic 时让主 agent 设置 vertical

**影响**：高。垂直权威源缺失意味着即便 WebSearch 健康，prescan 也会**偏向二手聚合的财经资讯**而非真正的科学/监管/产业一手——长期会让 thesis 系统性偏向"市场叙事"而非"实证基本面"。

---

## ISSUE-007 [Step 4.3 baseline] 模版未要求 LLM 自评"训练知识被 12 个月时差稀释程度"

**触发场景**：本次 baseline 第一节列 36 条 fact，置信度自评以高/中/低/uncertain 4 档，但**没有"时效衰减"维度**——GLP-1 减肥药是动态领域，2024-09 训练截止 vs 2026-05 今天差 20 个月，多数 fact 实际上是"训练时高置信但今天可能已过时"。

**workflow 层缺陷**：
- baseline 第一节只标静态置信度（基于训练时的确定性），没标"时效衰减风险"
- 这会让主 agent 在写 thesis_v0 时低估"训练知识已过时" 的概率，把训练时 fact 误当现状（本次 fact-23 Wegovy 价格 $1349 就是典型——训练时高置信但已被 2027-01 降到 $675 推翻）
- baseline 第四节"自我承认盲点"覆盖了**未知**的盲点，但**已知但已过时**的不在此列

**建议修复**：
1. baseline 第一节每条 fact 加二维标签：`confidence: 高/中/低/uncertain` + `time_sensitivity: 静态/慢变/快变`
   - 静态：科学机制 / 历史事件（多年不变）
   - 慢变：市场份额 / 监管框架（年级变化）
   - 快变：股价 / 季度业绩 / 临床数据读出（季级变化）
2. 第五节"优先 query" 必须先列"快变 + 高 confidence"的 fact——因为这类最容易被训练时高置信度蒙蔽
3. workflow 文档加示例

**影响**：高。这是 thesis_v0 准确性的根源问题。本次 fact-23 / fact-10 / fact-11 / fact-12 全部因"训练时确定但已过时"而需要 prescan 大幅修正——如果 prescan 失败（如 ISSUE-001 场景）这种修正机会就丢了。

---

## ISSUE-008 [00-research-topic Step 7] 汇报模版没区分"prescan 充分 vs 部分 vs 失败"对应不同 next_actions

**触发场景**：本次 prescan partial（WebSearch 0/10，转 WebFetch 凑 10 份 Wikipedia），但 Step 7 汇报模版还是统一的"下一步 workflow 01"。

**workflow 层缺陷**：
- prescan 部分失败应该在 next_actions 里**自动加入 "workflow 01 / 02 第一步重跑 prescan"**——既然 Step 4.5 没跑透，等用户收集 P0 资料时正好搭车补 prescan
- 现在用户看到的 next_actions 是"标准 happy path"，看不出本次研究的起点比正常更脆弱

**建议修复**：
1. Step 7 模版按 `prescan_status` 分支：full → 标准 next_actions；partial → 多加 "workflow 02 入口重跑剩余 baseline 优先 query"；skipped → 警示"thesis_v0 是纯训练知识赌注，01-roadmap 必须先补 prescan"
2. 汇报模版增加"本研究的脆弱点 + 用户最该优先做的 1 件事"小节

**影响**：低。本次手工补救即可，但批量化研究中会让用户错把"退化版 thesis"当成稳定起点。

---

## ISSUE-009 [01-build-roadmap Step 8] 一次性 prescan 没有"最近时间检查"硬规则，会与 workflow 00 prescan 重复

**触发场景**：刚跑完 workflow 00 两轮 prescan（20 query 入库 33 mat，几小时前），随即进入 workflow 01 Step 8 又被要求"立即跑一次性 prescan recency_days=90"。

**workflow 层缺陷**：
- 01 Step 8 假设 thesis 形成后才知道 K# 才能扫——但 workflow 00 修复后 thesis_v0/v1 就已经按 K# 扫过了
- 没有"读 web_search_log 看最近一次 prescan 时间，<7 天明显跳过 / <14 天小补 / >30 天完整跑"的硬规则
- 重复跑会消耗 WebSearch 配额、可能再次触发 ISSUE-001 限流，且没有信息增量

**建议修复**：
1. `01-build-roadmap.md` Step 8 入口加：

   ```python
   from prism.scripts.web_prescan import days_since_last_prescan
   d = days_since_last_prescan(slug, variant, triggered_by_prefix='00-prescan')
   if d is not None and d < 7:
       print(f'⏭️ 跳过 Step 8：{d} 天前刚跑过 prescan，按 K# 扫描已饱和')
   elif d is not None and d < 30:
       print(f'⚠️ 仅补 L3-debate 视角 query（争议视角，非 K# 维度）')
   else:
       # 完整 prescan
       ...
   ```

2. 新增 helper `days_since_last_prescan(slug, variant, triggered_by_prefix)` 在 `prism/scripts/web_prescan.py`
3. 文档强调："Step 8 prescan 的目的是补 L3-debate 视角和 90 天最新事件，不是重复 K# 维度"

**影响**：中。批量推进研究时会造成系统性的 WebSearch 配额浪费 + 重复入库噪声。

**本次实际处置**：明确跳过 Step 8 完整 prescan；把"L3-debate 视角的多空对峙 query"作为可选下一步推荐给用户（如需深挖）。

---

## 缺陷观察 [Step 5.5 自动下载 ticker 命名不一致]

**触发场景**：roadmap.yaml 写 `ticker: HKEX_01801` → fetch() 失败（应为 `HK_01801`）。原因是 SEC adapter 用 `LSE_/SSE_/SZSE_/KRX_` 前缀，但 HK 用 `HK_` 不是 `HKEX_`。

**workflow 层缺陷**：
- Step 5.5 文档示例混用了 `HKEX_` 和 `HK_`，roadmap 模版没明确格式
- `fetch()` 报错信息提示了正确格式，但浪费一次重试

**建议修复**：
1. `01-build-roadmap.md` Step 5.5 ticker 规则统一只列 `HK_` 不列 `HKEX_`
2. `fetch_report_prism.py` 加 alias 容忍 `HKEX_xxxxx` 自动转 `HK_xxxxx`
3. roadmap.yaml.tmpl 注释里加完整 ticker 格式表

**影响**：低。一次性纠正即可，但每次新研究都会踩。

---

## 缺陷观察 [Step 5.5 年份默认行为 — guess_year 取最大年导致 2026 年报永远失败]

**触发场景**：roadmap.yaml material title "华东医药 2025-2026 季度销售" → guess_year 取 2026 → fetch() "No annual report found for 2026"（2026 年报还没披露）。

**workflow 层缺陷**：
- `guess_year` 优先取 title 里最大年份，但年报披露通常滞后（2026 年报要 2027 春季才出）
- fetch() 失败应自动 fallback 到 year-1，否则 roadmap 写"2025 全年报 + 2026 Q1"会因 2026 永远失败而需手工兜底

**建议修复**：
1. `fetch_report_prism.py` annual fetch 失败时自动 fallback `year-1` 一次（再失败才报错）
2. 或 `guess_year` 限制 `max_year=date.today().year - 1`（年报视角）
3. 文档强调 roadmap material title 写"2025 全年报"而不是"2025-2026 季度销售"以避免歧义

**影响**：低。一次手工纠正即可。

---

## ISSUE-010 [annual_report_extractor] 港股 PDF 英文 TOC 0 章节匹配（已修复）

**触发场景**：信达 HK01801 PDF（港股年报，2.9MB）TOC 是英文章节名（"Chairman's Statement" / "Management Discussion and Analysis" / "Business Highlights"），`_INCLUDE_KEYWORDS` 列表全是中文（"管理层讨论"、"风险因素"），子串匹配返回 0 章节 → 报"未找到匹配的章节"且 exit 1。

**workflow 层缺陷**：
- `annual_report_extractor.py` 文档头说"A-share annual report PDFs"，但 fetch_report_prism 用同一脚本下载港股 + 海外，extractor 不识别非中文 TOC
- TOC 是有的（list-toc 输出 18 个英文章节），只是匹配失败
- 没有兜底/警告，直接 exit 1 让下游 03-extract 拿不到资料

**已修复**（commit pending）：
- 加 `_INCLUDE_KEYWORDS_EN` + `_SKIP_KEYWORDS_EN` 列表（小写英文 keyword）
- `_should_include` 同时跑中英两套子串匹配
- 中文 PDF 行为完全不变（恒瑞回归测试无 diff）；港股信达从 0 章节 → 4 章节（Chairman / Business Highlights / MD&A / Directors），180KB 输出

**影响**：高。所有港股 / 美股 PDF 年报本来都拿不到切片输出，被迫读全文 → 输入成本翻倍。

---

## ISSUE-011 [annual_report_extractor] PDF 无 outline 时直接兜底全文，浪费切片机会（已修复）

**触发场景**：华东 SZSE_000963 PDF 没有 PDF bookmark（`doc.get_toc()` 空），extractor 直接 `pages_text=...全文` 兜底。但 PDF 文本里**有"第N节 标题"heading**，每个出现 2 次（TOC + body），完全可以扫文本恢复 TOC。

**workflow 层缺陷**：
- 目录失败 → 全文兜底是惰性设计，错失了"PDF 无 outline 但文本有 heading"的常见场景（A 股很多 PDF 不打 bookmark 但 body 有"第N节"标准 heading）
- 全文兜底输入成本约是切片的 2 倍（华东 75K vs 38K token）

**已修复**（commit pending）：
- 加 `_text_heading_fallback(doc)` — 当 outline 空时扫每页文本提"第N节 标题"，每个 unique heading 取最后一次出现作 body anchor，返回与 PyMuPDF TOC 兼容的 list
- 华东实测：8 unique heading 提取，配 SKIP keyword 过滤后切到 2 个核心章节（管理层讨论 + 重要事项），114K 字符 vs 全文 326K 字符（**省 65%**）

**影响**：高。所有"无 outline 但有 heading"PDF（A 股部分中型公司常见）原本走兜底全文，输入成本 2 倍。

---

## ISSUE-012 [sec_section_split] 20-F (外国发行人年报) 不切片（已修复）

**触发场景**：NVO 是丹麦公司，SEC 用 20-F 而非 10-K。`fetch_report_prism` 下载成功，`split_file` 检测到 form='20-F' 但只对 10-K/10-Q 分发 → 返回 `unsupported form` 不切片 → 03-extract 必须读 NVO 20-F 全文（~150K token）。

**workflow 层缺陷**：
- 20-F 结构与 10-K 不完全相同：Risk Factors 在 Item 3.D（不是独立 1A）、MD&A 在 Item 5（不是 Item 7）、Financial Statements 在 Item 18
- 20-F body 内每页用"ITEM N TITLE"作 page header → `_select_body_anchors_10k` 取最后一次会落到 page header tail → 不能直接复用
- 没有 split_20f 函数

**已修复**（commit pending）：
- 加 `_20F_SECTIONS` (Item 3/4/5/11/18) + `_20F_DEFAULT_ADDRESSES`
- 加 `split_20f()`，body anchor = body region (last PART I) 内首次出现 lineno
- `split_file()` 加 20-F 分支；`fetch_report_prism.py` 加 20-F 进切片白名单
- NVO 实测：5 段成功（Item 3 Key Info + Item 4 Business 32KB + Item 5 MD&A 22KB + Item 11 Quant Risk + Item 18 FS），合计 11K words ≈ 19K token vs 全文 ~150K token（**省 87%**）

**影响**：高。所有外国发行人（NVO/SHELL/ASML/UL/AZN/BP/...）20-F 原本不切片，全文 input cost 高 5-10x。

---

## 总结：本次研究暴露的 3 大系统性 workflow 缺陷

1. **【M1 数据获取兜底】** WebSearch 失败 / WebFetch 限流 / SEC 阻断时，workflow 没有"自动降级 → Wikipedia / 中文垂直站 / 等待"的兜底协议；prescan 失败时 thesis_v0 静默退化为训练知识赌注
2. **【M2 垂直权威源】** WHITELIST_DOMAINS 偏综合财经，缺医药/科技/能源/金融等垂直权威源 → prescan 系统性偏向二手聚合
3. **【M3 训练知识时效衰减】** baseline 模版只标静态置信度，不标 time_sensitivity → "训练时高置信但已过时" 是 thesis_v0 最大隐藏 bug 类型

**建议优先级**：M3 > M1 > M2（按对 thesis 准确性的影响）

---

> 整改建议：把本文档转 issue 列表，提 PR 修 workflow 00 / _baseline_knowledge / _web_prescan_shared / web_prescan.py classify_domain。可作为下一轮 workflow 评审的输入。

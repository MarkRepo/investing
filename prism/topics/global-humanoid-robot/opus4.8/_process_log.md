# opus4.8 研究流程问题与优化点日志

> 本文记录用 opus4.8 重跑 global-humanoid-robot 研究全流程中遇到的 workflow 问题、摩擦点、可优化项。
> 评价基准 = 最终研究目标：**人形机器人产业链中哪些环节最有投资价值？核心受益标的是谁？**

## 流程概况
- topic: global-humanoid-robot / type=industry / geo=GLOBAL / depth=deep
- variant: opus4.8（已有 deepseek-v4-pro 旧变体，走旧 01-08 流程，无 thesis_v0/K#）
- 资料：复用 slug 级 14 份（6 A股年报 + TSLA 10-K/10-Q + 6 份研报/行业报告）

---

## 问题与优化点（按发现顺序）

### P1 [复用断层] 机械转换层未在 slug 级留存（认知已修正）
- **三层要分清**（之前日志把前两层混为一谈，错了）：
  1. **机械转换层①** mineru `_vlm/`：外部 VLM OCR，**不调本研究的模型**，输出确定、与 variant 无关。
  2. **机械转换层②** `_extracted.md`：来自 `annual_report_extractor.py`，**纯 pymupdf**（find_tables+TOC，grep 确认零 LLM 调用，"LLM" 仅出现在注释），同样确定、与 variant 无关。"extracted" 命名误导——它是"pymupdf 抽表"不是"模型抽取"。
  3. **LLM 解读层** `findings_mat-*.md`：本 variant 模型按本 thesis 的 K# 读材料抽解读，**随模型/thesis 变** → 正确地落 variant 级（见 P9）。
- **结论**：①②都该 slug 级共享、跨 variant 直接复用；只有③该按 variant 分开。同一份年报 opus4.8 与 deepseek 的 `_extracted.md` 字节级相同，没有"按模型不同"一说。
- **现象（修正）**：deepseek-v4-pro(5/17) 跑完只在 `deepseek-v4-pro/outputs/` 留了 findings，**没把机械转换层留在 slug 级 `materials/`** → opus4.8 起手时 slug materials 只有原始 PDF/HTM，被迫重跑 mineru + extractor（确定性产物的无谓重算，mineru 还是分钟级外部 API）。之前写"materials 下无 _vlm/_extracted"是错的。
- **已自然修复一半**：opus4.8 本次把 `_vlm/`(6份) + `_extracted.md`(6份) 落进了 slug 级 materials/，下一个 variant 可直接复用。
- **✅ 已修（本轮）**：发现根因其实只是 03 Step A 缺存在性守卫——mineru 层（02 Step4.5 + 03 Step B）早已带 `test -f .../full.md && skip`，唯独年报 extractor（03 Step A）无条件重跑。已给 03 Step A 补上对称守卫 `test -f {stem}_extracted.md && 跳过 || extract`，实测 4 份年报全命中跳过。两个机械转换层（mineru `_vlm` + extractor `_extracted`）现都跨 variant 复用，只有 `findings_mat-*` 按 variant 隔离。原以为要建 manifest `converted_path` 索引，过度设计——确定性路径 + 一个守卫即足。

### P2 [环境噪声] gitnexus FTS read-only DB 告警刷屏
- 现象：每次 Bash 调用前注入 5 行 `[gitnexus] FTS index ensure failed ... read-only database` hook 噪声。
- 影响：与 prism 研究无关，污染上下文。
- 优化点：prism 研究会话里 gitnexus PreToolUse hook 可关闭，或 index 置只读时静默。

### P3 [env 变量名] mineru token 名不一致
- 现象：`.env` 用 `MINERU_TOKEN`，直觉会查 `MINERU_API_KEY`（不存在）。文档/脚本内部一致用 TOKEN，但易踩。
- 优化点：文档 Step 明示 env 变量名。

### P4 [关键] WebSearch 工具返回叙事摘要而非干净 hit 块
- 现象：直接调 WebSearch tool（prescan 文档 Step B 的推荐路径）返回的是合成式叙事段落 + "Would you like sources?"，**没有干净的 {title,url,snippet} block**，无法喂 register_web_search_batch（会逼出幻觉 URL）。
- 影响：prescan 文档假设 WebSearch 返回 search_result block，但本 harness 下 WebSearch 是摘要器。
- 优化点：**prescan 应默认走 adapter（`python3 -m prism.scripts.web_search search ... --output sidecar`）**——它返回结构化 hit 写 sidecar，再 review-digest 判 tier，干净可靠。文档 Step B"主 agent 直接调 WebSearch"在此 harness 不适用，建议改为 adapter-first。本次全程改用 adapter，11+5 query 全部 hit_rate=1.0。

### P5 [噪声] financial_data 刷 "unmapped CN column" 警告
- 现象：get_peer_comparison_data_by_tickers 对每个 ticker 打几十行 "unmapped CN column '房地产销售收入'..." stderr。
- 影响：污染上下文，需 `2>/dev/null` 过滤才能看结构化返回。
- 优化点：未映射列降为 debug 级或汇总一行。

### P6 [文档不符] get_peer_comparison_data_by_tickers 需 'key' 字段
- 现象：funnel 文档示例只传 {ticker,market,name}，实际函数 `p["key"]` 必填，漏传 KeyError。
- 优化点：文档示例补 'key' 字段，或函数 fallback 用 name。

### P7 [gap 语义] industry-financial-arc 拉了 API 仍报缺
- 现象：环①已调 financial_data 拉多年弧线并写进 case，但 gap detector 仍列 industry-financial-arc(环1)。属 api_pending（非红、设计如此——结构化项不作为 material 计入 ring 覆盖），但每次体检都出现易误判为"漏做"。
- 优化点：gap report 对 api_pending 项显式标 "(api_pending, 已合成期拉取)" 与真红项区分（🔴 已区分，但文字仍混在"缺输入"行）。

### P8 [转换] mineru 快但有瞬时失败
- 现象：6 份研报 mineru 4 份一次成功(6-49s，比预期快)，report.pdf + 情绪向右 首轮 "parsing failed, please try again later"，report.pdf 重试 3 次才成。
- 优化点：驱动脚本内置 2-3 次重试（本次已加 retry 兜住）。

### 正面观察 [独立 eval 有效 + 闭环修订]
- 独立评价 subagent（以最终目标为基准）给 6.5/10，抓到**致命缺口**：研究答好了"哪个环节最有价值"(8/10)，但最终目标后半句"核心受益标的是谁"只停在 arena 层、没落到可买标的(4/10)，且回避了"最好环节恰恰最贵最难=暂时无解"的对抗。
- **闭环修订**：据此给 case 加"核心受益标的指认"段（标的×质地×定价×弹性×介入纪律矩阵 + 整机 eliminated 边界反思），case 升 v2。eval→修订闭环跑通，证明"独立 subagent 评价"对最终质量是真有用的杠杆（不是走过场）。
- 优化点：prism workflow 可考虑把"以最终目标为基准的独立 eval"固化为 04 收尾的必跑环（现仅 chain-critic 查链通、05-critic 查 steelman，缺"是否答到用户原始问题"这一维）。

### 正面观察 [chain-critic 有效]
- 内嵌 chain-critic（funnel Step 6）抓到一个真实硬伤：深挖档（行星滚柱丝杠）的 tier 锚定建立在"标的估值不如绿的夸张"的无数字断言上，环②定价锚表不含任何丝杠纯玩家 PE。补拉后发现五洲新春 326x/北特 135x **同样极端透支**——critic 直接纠正了一个会误导决策的乐观判断。embedded critic 的"只依文本判断"约束有效。

### P9 [findings 复用断层延续] 13 份 findings 仍是 variant 级
- 现象：本次重抽的 13 份 findings 落在 opus4.8/outputs/，与 deepseek-v4-pro 的 findings 完全隔离。转换产物(_vlm/_extracted)本次落了 slug 级（已修 P1 的一半），但 findings 仍 variant 级。
- 评估：findings 是 LLM 判断层（按本 variant thesis 的 K# 抽），variant 级隔离是**合理的**（不同模型/thesis 抽取角度不同）。但纯"数据点摘录"部分其实可跨 variant 复用——可考虑分离"客观数据层"与"thesis-relevant 解读层"。

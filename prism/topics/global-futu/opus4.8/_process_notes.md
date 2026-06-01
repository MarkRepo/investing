# opus4.8 研究流程问题 & 可优化点（实时记录）

> 本文件在研究全程实时记录：① 流程摩擦/卡点 ② 工具/脚本问题 ③ 可优化建议。
> 最终汇入交付报告的「流程复盘」一节。

## 设置阶段

- **[流程][reuse]** 变体目录是按 `{slug}/{variant}/` 隔离的，但原始资料在 topic 级 `materials/` 共享 → 跨变体复用资料很干净（新 manifest 只需按 filename 重新登记，文件不拷贝）。✅ 体验好。
- **[摩擦][addresses 耦合]** 旧变体 manifest 的 `addresses` 是按该变体自己的 K# 编号打的（K1-K8/Q3/Q5/Q7）。新变体要做独立 thesis → 不能直接继承 addresses，否则等于继承了旧 K# 框架、污染独立性。**结论**：本轮 add_material 先不带 addresses，等 opus4.8 自己的 thesis_v0 定了 K# 再批量回填。→ **可优化点 #1**：脚本可提供 `retag_addresses_by_filename(slug, variant, mapping)` 批量按文件名打 K#，避免 32 条逐条调。
- **[环境]** gitnexus PreToolUse hook 反复报 "Cannot execute write operations in a read-only database"（FTS 索引）。与 prism 任务无关，但每条 Bash 都刷一遍噪声 → **可优化点 #2**：本会话 gitnexus 索引只读，建议任务期间静音该 hook。
- **[资料盘点]** materials/ 42 文件，旧 manifest 收 32（earnings call 取 .md 弃 .html 重复；2 个 smoke-test、若干 .html 未收）。复用合理。

## baseline 阶段
- **[正向]** 训练截止 2026-01 → 2026-05-22 CSRC 罚没是真·post-cutoff 盲点，baseline 第四节诚实标 uncertain，§6 校准时被「推翻」→ 流程按设计工作。
- **[正向]** financial_data + market_data 两个 pipe 对 **US/HK 标的（FUTU）均可取数**（yfinance 兜底）：拿到 2025A 财务全套 + 实时 PE/股价/52周。**纠正了我对 memory「akshare 不支持 HKEX」的过度泛化**——market_data 走 yfinance 对美股 ADR 可用。✅ 关键，否则 company 环②反推无锚。
- **[数据口径警示][可优化点 #3]** financial_data 返回 **ROIC = 2858%/1959%/1721%**（券商轻资本+客户资金并表使分母失真）。脚本直接吐出会误导红线判定（ROIC>WACC 形同虚设）。建议：金融/券商类 topic 的 quality_screen 对 ROIC 做行业特例标注，或改用 ROE/ROTCE。

## prescan 阶段
- **[流程缺口][可优化点 #4]** 「复用已有资料」模式与 `check_prescan_health` 冲突：健康检查只统计**本轮** triggered_by='00-prescan*' 的 web_search 注册数；复用模式下本轮 0 注册 → 会误报 status=failed，即使校准其实很充分。需要一种「prescan 复用/继承」语义。本轮手动按实际覆盖判 partial（唯一真缺口=Q1 2026 业绩未收）。
- **[freshness gap]** 资料 5-25 收，FUTU Q1 2026 业绩 5-28 才披露 → 最关键的近期财报不在库。market_data 价（5-29）已反映财报后，但财报明细（大陆收入拆分/罚没计提）缺。本轮如实标注，不阻断（用户要求不等待收料）。

## thesis / decomposition 阶段
（待补）

## roadmap / findings 阶段
- **[方法][正向]** 大材料（FUTU 20-F 1.18M 字符、8 份同业 SEC 文件）用 3 个并行 read-only subagent 抽取、**返回文本由主 agent 落盘**——干净绕开 memory 记录的「subagent 脑补 Write 被拦截」幻觉问题（subagent 不写文件就不会幻觉 Write）。3/3 成功返回高密度结构化 findings。✅ 验证：findings 抽取（读重写轻）适合 subagent，合成（写重）才必须主 agent 直做。
- **[整合][质量差异化·重要]** subagent 主动标注：**「大陆占比 45%(25Q2)→13%(26Q1)」断崖在 7 份业绩会材料中零佐证**——唯一相关是 25Q2「港外 >50%」（香港口径非大陆口径），13% 来自 5-22 6-K。旧 opus4.7 finding 曾把「45%」当事实写入。opus4.8 把它标 **unverified** 并入 §反常识。→ 这是 prescan/findings 纪律带来的**真实质量提升**（不继承未证实数字）。
- **[发现] 命门1 的官方料本就是黑箱**：FUTU 20-F 地域披露只到「香港 vs 其他」（香港占佣金 74%），大陆收入/利润完全不单列，VIE 仅「a small portion」。→ 命门1（13% 账户=多少利润）**无法用一手报表回答**，这本身是最重要的研究结论：多空分歧的总开关，数据上无法证伪，只能靠 Q1 财报/卖方测算补。
- **[数据] financial_data 与 20-F 对账一致**：收入 228.47 亿 = HK$22,846.9M ✓；净利 113.38 亿 = HK$11,301.9M ✓。两个来源交叉验证可信。

## 合成阶段
- **[正向] primer-first + 独立 critic 闭环有效**：primer critic 一轮即 8/11 [够]，3 个缺口（可观测信号表/加速vs见顶/pair-trade机理）按"补一处"修复后达标，gate 自动判 deep+fresh。critic 主动抓到"§8 列的是争议不是可观测信号"——单轮自检抓不到（作者中心化偏见），印证 critic 不可省。
- **[正向] chain-critic 抓到真断点**：环⑥买入框口称"锚 SOTP"但 $85 既当 SOTP-bear 公允价又当"深度安全边际"，语义矛盾。已修：明确主锚相对倍数模型 + $85 重定义为"bear 已被定价处"+ sidecar 加 anchor_model。② 的 TTM 净利/罚没数补 mat 引用。→ ⑥↔②锚、⑥仓位↔④EV 经独立校验闭合。
- **[设计] EV 量化下注是亮点**：环④ 概率×回报加总出 EV≈+21%、赔率 2.9:1，直接喂⑥首仓 2.5%。chain-critic 指"EV 量级未严格挂钩首仓公式（非 Kelly）"——可接受瑕疵，提示可加 EV→仓位机械映射。
- **[命门洞察] 最重要研究结论是"命门1 不可证伪"**：FUTU 一手报表系统性不披露大陆贡献 → "13% 账户=多少利润"无法用一手料回答。诚实标黑箱+小仓位+硬kill对冲，比假装能算更可信。

## 评审 / 质检阶段
- **[复用模式根本局限·呼应 [[project_variant_reuse_gotchas]]]** 本轮验证"复用起手=形式完整但一手深度薄"：① Q1 2026 业绩（5-28）晚于资料收集日未入库——最关键近期财报缺；② consensus（卖方一致预期/目标价/利率敏感模型）整条 ring 未覆盖（gap 标 🔴）；③ 命门1 黑箱本可由卖方大陆敞口测算补，但无料。→ EV/估值带建立在"无卖方锚校准"的自推上，置信度只能到"中"。
- **[mat_id churn]** 复用时 add_material 生成全新 mat_id，旧变体 findings 的 mat 引用作废 → 跨变体不能直接搬 findings 正文。本轮重抽，干净但费 token。
- **[最终独立评价]** 见下方 Task 8 dispatch 的独立 evaluator 结论 + 交付报告。

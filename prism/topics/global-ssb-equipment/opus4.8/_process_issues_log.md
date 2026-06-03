# global-ssb-equipment / claude-opus-4-8 — 流程问题与可优化点日志

> 本次研究（variant=claude-opus-4-8）全程记录 prism 流程中遇到的问题、摩擦点、可优化建议。
> 时间起点：2026-06-01。复用 claude-opus-4-7 已有资料，不等待用户收集。

## 格式
- `[阶段]` 问题描述 → 影响 → 建议

---

## 启动阶段

- `[skill-routing]` SKILL.md 路由表里「研究 X」直接路由到 `00-research-topic.md`，但本 topic 已存在（claude-opus-4-7 变体）。00 Step 3 有"已存在 slug"分支（新变体），但路由表入口没提示"先检查是否已存在"。主 agent 需自己判断走"新变体"路径。→ 建议：路由表「研究 X」行加一句"先 `ls prism/topics/` 查是否已存在 → 已存在则走 Step 3 新变体分支"。

  **根因复盘**：不是缺校验，而是校验落点与分叉对不上。三层：①脚本 `create_topic` 第 268-270 行有硬校验 `FileExistsError`，但键是 `_topic_path(slug, variant)` 联合键——新变体目录天然不存在故不 raise（设计如此，否则会堵死"同 slug 建新变体"这条合法复用路径）；②"slug 已存在但变体不同"该走哪条（续做/建新变体/另起 slug）本质是**用户意图判断**，不能下沉脚本，天然只能是文档提示主 agent 去问；③真正缺口是唯一的人机确认点 Step 3 是**软性文档文字、无机械强制**，主 agent 一旦自认意图明确（如本次用户原话已给 variant+复用）就会跳过 Step 3 直奔 create_topic。路由表入口加"先 ls 查重"治标（把提示从 Step 3 前移、降跳步概率），仍是软提示。

  **治本方向（两层防御纵深，应同时做，非二选一）**：两者作用在流程两个不同点、各补一个失效模式，且复用同一原语 `list_variants(slug)`（**该函数 topic.py:1196 已存在**，只是没被接进创建路径/文档）。
  - **上游（决策点）**：路由表/Step 3 显式调 `list_variants(slug)`，把查重从 `ls` 肉眼判断变成结构化返回，三分支（续做/新变体/另起 slug）基于结构化数据呈现——挡"按顺序走 Step 3"时的判断模糊。
  - **下游（创建兜底）**：`create_topic` 在 slug 目录已存在、但 variant 是新值时打印 stderr 提示（不 raise，不堵合法路径），消息直接调 `list_variants(slug)` 生成，如 `⚠ slug={slug} 已存在变体 {list_variants(slug)}，你正在创建新变体 {variant}——确认不是想推进旧变体? 复用旧料见 clone_variant_materials`——挡"跳过 Step 3 直奔 create_topic"时的盲建（本次正是此路径）。
  - **为什么必须两层**：上游只改文档挡不住跳步；下游只加 stderr 则每次都拖到最后一刻提示且信息不结构化。本次故障恰是"跳步"路径，缺下游就漏。两层共用 `list_variants`，故"都做"是一个原语喂两个消费点，非双倍成本。原"轻/重"分级仅按改动量，因 `list_variants` 已存在而失去意义。

  **为什么这两个查重值得做（意图）**：① `FileExistsError`（slug+variant 精确）意图=防覆盖保数据完整性，纯机械、无意图判断；② Step 3 软查重（slug 存在、variant 不同）意图=在意图模糊的分叉点归一意图，核心作用**不是防创建而是解锁复用**——只有先认出旧变体存在，才会去 clone materials/findings + set_parent，本次"不收料、复用资料"能跑通全靠这步。最终意图链：认出旧变体→复用其料→隔离变量→让"换模型/换架构重研同一 topic"的模型/架构优劣可苹果对苹果对比（本次 4-7 八维并列 vs 4-8 六环决策链的干净归因即依赖此）。

- `[variant-naming]` 用户说"variant opus4.8"，但既有变体目录命名是 `claude-opus-4-7`。需主 agent 推断规范化为 `claude-opus-4-8`。→ 建议：脚本层 normalize variant 名（opus4.8 → claude-opus-4-8）或在 00 Step 1 明确命名规范。

## Step 4.5 Prescan 阶段

- `[prescan-health]` check_prescan_health 按"已 register 的 query 批次"算 queries_with_hits=4/7=57%=partial。实际 7 条 query 都 WebSearch 成功（各 5 hits），只是 3 条 query 的 best hits 与已入库重复/低 tier，主 agent 主动没 register。→ health 把"主动不入库"误判为"无 hit"，partial 信号偏悲观。建议：register_web_search_batch 增一个"query 已跑但主动判定无需入库"的显式标记，让 health 区分"限流无 hit" vs "跑了但低质不值得入库"。

- `[prescan-yield]` 12 天 drift 下 prescan 仍捞到 1 条极高价值一手口径（先导董秘股东会 mat-cc96dd：单GWh价值量5亿/2-3倍、固态占订单<5%、Q1订单+60%、转收入周期）。说明即便复用旧资料、drift 很短，prescan 对"管理层最新口径/股东会问答"这类训练知识盲区仍有不可替代价值。值得保留为硬步骤。
  - **复核确认（2026-06-01）：这一条不是缺陷，是设计验证记录（误归在"问题与可优化点"标题下）。** 无需修复；结论=prescan 应维持为硬步骤。佐证：该料原始 raw 在 `_websearch_raw/20260531T170525Z_7a00c207.json`（query='先导智能 固态电池 订单 2026 半年报'），idx0 即《财闻在现场·股东会｜固态电池设备价值量激增，先导智能董秘称行业陷"军备竞赛"》——一手董秘口径，训练知识与年报均无。

- `[adapter-snippet]` review-digest `--show 0` 偶发空输出（idx 0 时），换 `--show 0,2` 或单独 `--show 0` 重试才出。疑似 sed 管道/边界问题，非阻断但需重试。
  - **确诊（2026-06-01，已修）**：不是 `--show` 解析 bug（现有 7 个 raw 上 `--show 0` 复现，确定性正常、不空）。真因两个叠加：
    ① **`--slug` 恒取"最新"json**（web_search.py:322 `candidates[-1]`，help 自承"取最新"）。prescan 7 条 query 秒级连发（170509Z→170537Z），`--slug --show 0` 在 digest 哪条取决于谁最后写——故"偶发选错"。若最后写的那条恰是 0-hit query（限流/无果）→ idx0 越界 → EXIT_CONFIG。实测 case A：`--show 0` 自动选到的是"海目星/利元亨"query 而非想要的"先导董秘"query，正是此坑。
    ② **所有错误只走 stderr + 返回 EXIT_CONFIG**（web_search.py 越界/坏路径分支）。snippet 是数 KB 单行长文，agent 为防爆上下文必 `| sed`/`head`，stderr 被丢 → config_error 看着像"静默空 stdout"。重试时 `--slug` 指向有 hit 的文件 → 内容才"出"。
  - **修复（web_search.py `_cmd_review_digest`，LOW risk，仅 main 调用）**：(a) `--show` 输出前打一行 **stdout 溯源横幅**（`# raw: <文件名> query: <q> n_hits: N`）；`--slug` 自动选且同目录候选>1 时追加 `⚠ 自动选了 N 个里最新一个，非你要的请用 --raw-path`——选错一眼可见，不再靠重试盲猜。(b) 越界时**同时写 stdout 可见标记**（`[idx X 越界：仅 N 条 hit]`）+ 原 stderr JSON + EXIT_CONFIG 不变——`| sed` 丢 stderr 也不再像空。补 2 测试（横幅必出 / 越界 stdout 非空），10 passed。
  - **操作侧规约**：digest 特定 query 用 `--raw-path` 显式指定，勿依赖 `--slug` 自动选最新（多 query 场景必踩）。

## Step 01/02/03 复用资料阶段

- `[reuse-matid-churn]` 复用旧变体资料的最大摩擦：add_material 自动生成新 mat_id，与旧 findings 文件名（findings_mat-{旧id}.md）脱钩。必须手动建 mat_id 映射 + 复制 findings 改 frontmatter mat_id。→ 建议：脚本提供 `clone_variant_materials(old_variant, new_variant)` 一键复制材料（保留或重映 mat_id）+ findings，跨变体复用是常见场景（同 topic 换模型重研）。

- `[gap-addresses-source]` **关键坑**：gap_detector 的 evidence_count 只数 **manifest material 的 addresses 字段**，不数 findings 文件 frontmatter 的 addresses。复制 findings 时 frontmatter 有 addresses=[K1,K2,K5]，但 add_material 没传 addresses → manifest 里为空 → gap_detector 报 K4 uncovered/K5 thin（假缺口）。必须手动把 addresses 回写 manifest。→ 建议：①add_material 时若对应 findings 已存在，自动从 findings frontmatter 同步 addresses；②或 gap_detector 同时读 findings frontmatter 兜底。

- `[prescan-addresses-scope]` 4 份 prescan 材料默认 addresses=scope（不计 K# 覆盖，符合约定），但它们内容明确攻打 K1/K2/K4/K5（如蔚来交付=K4 唯一直接证据）。合成前需主 agent 手动把 scope 改成具体 K#，否则 K4 假 uncovered。→ 与 feedback_addresses_granularity 同源：scope 占位的代价是合成前要手动重标。

- `[ring-axis-mirror]` ring 轴 arena-mirror（历史镜鉴，hard=True）复用资料天然无覆盖——年报/卖方研报不含"曾经赢家如何被取代"。这是 A 合同真欠供项，合成 ⑤ 必须从训练知识补（标 depth 降级"训练知识估算"）。属预期，非 bug，但提示复用资料起手的 arena 几乎必缺 historical-mirror。

## Step 04 合成阶段

- `[primer-critic-yield]` primer 独立 critic（门外人视角）1 轮收敛，捞到 1 个实质漏洞（路线"正交维度"与"半固态=氧化物/全固态=硫化物"自相矛盾）——这是主 agent 自己看不到的作者中心化盲区（写时默认读者懂两维度交叉）。验证了"primer 不能自检、必须独立 critic"的硬规约价值。

- `[chain-critic-yield]` 内嵌 chain-critic 判"链通、可用"，但捞到 2 个机器层裂纹：①sidecar tier 枚举(shortlist/watch/eliminated)与 case 叙事档名(深研/观察/淘汰)口径未显式映射，dashboard 消费会对不上；②sidecar score 倒挂(联赢2.7>海目星2.6)与 case 叙事方向相反、无解释。→ 两者都是"机器文件与人读叙事脱钩"类问题，主 agent 写时易漏。建议：合成路径加一条机械自检"sidecar score 排序必须与 case ④综合评级同向 + tier 档名映射必须显式写"。

- `[estimate-vs-evidence]` chain-critic 还指出环②"市场给先导 PS5.7"的定价锚，其最核心支撑假设(WMBT-2 价值量转收入)恰是③里证据最弱的——估值锚与证据强度脱钩。这是 arena ②③ 环常见的"定价笃定度 > 证据强度"陷阱，主 agent 初稿没点透。已补"定价含固态期权"风险段。→ 建议：funnel ②隐含预期段加硬要求"必须交叉③的 WMBT 支持度，标出市场在为哪条弱假设付溢价"。

- `[reuse-fresh-judgment]` 复用 4-7 资料但用 opus4.8 全新合成（新 6 环架构 vs 旧 01-08），产出质的差异：4-7 是 8 份并列维度，4-8 是因果决策链 + K5 升格选拔 hard filter + 估值锚一手数据。说明"换模型重研同一 topic"的价值不在新资料，而在新架构 + 新判断框架——复用资料反而让两个变体可直接对比模型/架构差异。

## Step 05/终评阶段

- `[fabricated-url]` **真实瑕疵（自我捕获前由独立 critic 捕获）**：注册潍柴招标 prescan 材料(mat-517cd3)时，主 agent 未保留 review-digest 里的真实 URL，写了占位符 `...2026-xxxx/weichai.shtml`。独立终评一眼识破。→ 教训：register_web_search_batch 的 url 必须从 review-digest 原样拷贝，不能凭记忆/构造；建议脚本对明显占位 URL（含 `xxxx`/`example`）做校验 raise。已降 confidence 0.35 + 标 url_unverified。

- `[reuse-structural-limit]` 独立终评核心结论：本次"复用旧资料 + 12 天短 drift + 4 条 prescan query"导致**形式完整（6环骨架漂亮）但一手深度薄（关键催化单源）**。这是"复用资料、不等待收料"约束的结构性代价——产出适合做"看盘框架/入门"，不适合做"今天下单的结论"。→ 对流程的启示：复用资料起手的研究，合成路径应在终态报告强制标注"本轮证据深度等级"（一手深挖 vs 复用拼装），避免"骨架完整"被误读为"结论可执行"。

- `[critic-value-confirmed]` 三个独立 critic（primer门外人 / chain-critic / 终评主管）各自捞到不同层级的真问题：primer critic→路线两维度矛盾(写作)；chain-critic→sidecar口径/估值锚脱钩(结构)；终评→押注共识性/一手深度/伪造URL(战略+完整性)。三层 critic 无冗余、互补，验证了 prism "多层独立 critic" 设计的有效性。本次最严重问题(伪造URL+押注无alpha)恰恰是主 agent 自己最难自检的——独立 subagent 评价不可替代。

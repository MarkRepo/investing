# global-ssb-equipment / claude-opus-4-8 — 流程问题与可优化点日志

> 本次研究（variant=claude-opus-4-8）全程记录 prism 流程中遇到的问题、摩擦点、可优化建议。
> 时间起点：2026-06-01。复用 claude-opus-4-7 已有资料，不等待用户收集。

## 格式
- `[阶段]` 问题描述 → 影响 → 建议

---

## 启动阶段

- `[skill-routing]` SKILL.md 路由表里「研究 X」直接路由到 `00-research-topic.md`，但本 topic 已存在（claude-opus-4-7 变体）。00 Step 3 有"已存在 slug"分支（新变体），但路由表入口没提示"先检查是否已存在"。主 agent 需自己判断走"新变体"路径。→ 建议：路由表「研究 X」行加一句"先 `ls prism/topics/` 查是否已存在 → 已存在则走 Step 3 新变体分支"。

- `[variant-naming]` 用户说"variant opus4.8"，但既有变体目录命名是 `claude-opus-4-7`。需主 agent 推断规范化为 `claude-opus-4-8`。→ 建议：脚本层 normalize variant 名（opus4.8 → claude-opus-4-8）或在 00 Step 1 明确命名规范。

## Step 4.5 Prescan 阶段

- `[prescan-health]` check_prescan_health 按"已 register 的 query 批次"算 queries_with_hits=4/7=57%=partial。实际 7 条 query 都 WebSearch 成功（各 5 hits），只是 3 条 query 的 best hits 与已入库重复/低 tier，主 agent 主动没 register。→ health 把"主动不入库"误判为"无 hit"，partial 信号偏悲观。建议：register_web_search_batch 增一个"query 已跑但主动判定无需入库"的显式标记，让 health 区分"限流无 hit" vs "跑了但低质不值得入库"。

- `[prescan-yield]` 12 天 drift 下 prescan 仍捞到 1 条极高价值一手口径（先导董秘股东会 mat-cc96dd：单GWh价值量5亿/2-3倍、固态占订单<5%、Q1订单+60%、转收入周期）。说明即便复用旧资料、drift 很短，prescan 对"管理层最新口径/股东会问答"这类训练知识盲区仍有不可替代价值。值得保留为硬步骤。

- `[adapter-snippet]` review-digest `--show 0` 偶发空输出（idx 0 时），换 `--show 0,2` 或单独 `--show 0` 重试才出。疑似 sed 管道/边界问题，非阻断但需重试。

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

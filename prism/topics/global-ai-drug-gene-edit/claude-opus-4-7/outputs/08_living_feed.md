---
slug: global-ai-drug-gene-edit
output_key: 08_living_feed
version: 1
generated: 2026-05-22
---

# 信息流时间线：AI 辅助药物研发与基因编辑

> 按时间顺序记录重要信息和判断变化。每次更新在末尾追加，不修改历史记录。
> 综合判断与 K# 校准请看 brief / 06 / 07，本文件只记录"事件序列 + 触发反应"。

## 2026-05-22 研究启动 v1

**来源**：用户发起 industry 研究（variant: claude-opus-4-7）

**主要事项**：
- 研究问题：2026-2028 全球基因编辑 + AI 制药赛道的结构性 alpha 在哪里？
- v0 thesis 强度 6/10 → v1 强度 7/10（K1 已强支持 + K2 已强反驳）
- 资料覆盖：8 份自有 findings（CRSP/NTLA/BEAM/VRTX 各 10-K+10-Q），剩 16 份 SDGR/RXRX/RLAY/ABCL/PRME/LLY/PFE/XtalPi 等待补

**当时已知的主要不确定性**：
- K3（AI 设计药物 Phase 3）：8 份 findings 不直接覆盖，待补 SDGR/RXRX/RLAY 后判断
- K4（>$5B AI 制药并购）：方向性支持但严格定义未命中，待补 LLY/PFE 后强化
- K5（NMPA 基因编辑批准）：8 份 findings 零中国覆盖，待补 XtalPi/博雅辑因
- BEAM-302 双剂 Grade 4 ALT 是否会扩展至单剂场景（pivotal 50 例数据未读出）
- 美国 IRA 是否扩展至 gene therapy 类（2027-2028 大选后）

**已排好的 catalyst 时点**：
- 2026-Q2：VRTX/NTLA/BEAM/CRSP Q2 10-Q 集中发布
- 2026-H2：NTLA HAE BLA 完成提交
- 2026-H2：BEAM-302 pivotal cohort 启动
- 2026-12：BEAM risto-cel BLA 递交
- 2026-12：美国大选结果 + 政策风向
- 2027-Q1：NTLA HAE 是否获 Priority Review
- 2027-H1：NTLA HAE 美国上市 + 首季销售
- 2027-H1：LLY-Verve PCSK9 关键 Phase 2 数据

**关键 finding 锚点**（供日后复盘"当时知道什么"）：
- NTLA HAELO Phase 3 阳性 topline：87% 减发作 / p<0.0001 / 0 SAE（2026-04 公布，10-Q 补披）[mat-3a51f9]
- NTLA MAGNITUDE（ATTR-CM）2026-03 解禁，配合 1 月 MAGNITUDE-2 解禁，ATTR 项目重启 [mat-3a51f9]
- BEAM-302 60mg 锁定 pivotal 剂量，AAT 16.1 µM、Z-AAT 下降 84%、M-AAT 占比 94%，2026 H2 启动 pivotal [mat-2b431a]
- BEAM risto-cel 2026-04-01 NEJM 发表 BEACON 31 例数据，BLA 锁定 2026 年底 [mat-797ff7, mat-2b431a]
- VRTX Casgevy 全年 64 例输注 / Q1 2026 收入 $42.9M / 累计全球 ~150 例（K2 兑现率 <8%）[mat-49861e, mat-1fe402]
- CRSP $600M 可转债（2026-03-16）+ Q1 collab expense YoY -20% 首次拐点 [mat-a66935]
- BP 整合潮：LLY 收 Verve（2025-07）+ BMS 收 Orbital（2025-12）+ Biogen 收 Apellis（2026-03）[mat-797ff7, mat-2b431a]
- ToolGen vs CRSP IP 诉讼 2026-04 被驳回（without prejudice），短期黑天鹅解除 [mat-a66935]

> 后续条目只在以下情况追加：catalyst 时点真实兑现 / 出现 thesis 没预期的新数据 / K# 翻盘

## 2026-05-23 Workflow 09 完成：行业 → 8 arenas 分流

**来源**：industry topic 必须步骤（01-08 完成后）

**Arena 选拔结果（8 个 / 3 deep / 3 watch / 2 eliminated）**：
- **深挖 (3)**：In vivo 罕见病 (4.4) + In vivo 心血管 (4.2) + Base editing 平台 (4.2) — 3 个 stub topic 已创建并继承父 thesis_v1 → v0 (强度 6/10)
- **观察 (3)**：Ex vivo Casgevy 商业化 (3.2) + AI 制药 SaaS (3.0) + 中国 in vivo (4.0)
- **淘汰 (2)**：通用 AI 设计药物纯标的 (2.0) + Prime editing (2.8)

**Stub topic 列表**：
- `global-in-vivo-gene-edit-rare-disease` — K1 主战场
- `global-in-vivo-gene-edit-cardiovascular` — 最大利润池 + LLY-Verve 锚定
- `global-base-editing-platform` — BEAM 单标的 + takeout 期权

**父 topic 状态**：stage=done；后续可补 16 份 K3/K4/K5 资料上修强度，或进入 daily monitor 追踪 8 个 arena 的 monitor_metrics

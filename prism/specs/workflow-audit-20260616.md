# Prism Workflow 文档漂移与冗余审计报告

> 审计日期：2026-06-16
> 范围：`prism/workflows/*.md` + `prism/DESIGN.md`（交叉对照）
> 方法：逐文件扫 + 三个并行 agent（参数生命周期 / 废弃概念残留 / 跨文件冗余）

---

## A. 漂移问题（6 项）

### A1 🔴 Q# 示例化石（活跃引用已废弃维度）

| 文件 | 行 | 问题 |
|------|-----|------|
| `00-research-topic.md` | 494, 501, 512 | 示例代码 `addresses: ['Q1', 'K1']` / `['Q3', 'Q6']` / `['Q1', 'K3']` |
| `03-extract-findings.md` | 366, 368, 370 | SEC section 映射表 `[scope, Q1, K3, K5]` / `[Q1, K2, K4, K5]` / `[valuation, Q1]` |

00 Step 5.2 已声明"新 topic 不再生成 Q#"，但 Step 6 的示例代码仍在用 Q#。LLM 照抄示例会复活废弃维度。

**建议**：示例中 `Q1`/`Q3`/`Q6` → 改为对应 K#，03 映射表同理。

（01 的 `Q1/Q3` 出现在财报季度解析注释中，是财务概念非研究维度，不修。）

---

### A2 🔴 DESIGN.md auto_resolve 死引用（5 处）

这些都是 workflow-flow-review.md A1 标记已修、但 DESIGN.md 漏改的残留：

| 行 | 当前文本 | 问题 |
|-----|---------|------|
| 110 | `covered_by: [mat-abc123]  # 被哪些料覆盖（auto_resolve 写）` | auto_resolve 已删，covered_by 由 LLM 显式传参 |
| 117 | 流程图含 `auto_resolve` 节点 | 过时，应改为 `mark_todo_fetch + update_status` |
| 239 | `必带 addresses，否则后续 auto_resolve 算不进` | 理由为假——addresses 仍必填（参与 B 轴），但不是因为 auto_resolve |
| 244 | `漏 addresses → auto_resolve 永远核销不掉` | 同上 |
| 254 | `写 addresses 仍触发 auto_resolve` | 直接错误——写 addresses 不触发任何自动操作 |

这些不会让 LLM 在 workflow 里调用死函数（死函数已删），但会**污染 LLM 对 todo 闭环机制的理解**。

---

### A3 🟡 cluster_tags 创建端缺失

workflow 文档没有说明 `cluster_tags` 谁在什么时候产。代码显示它来自 sidecar（04 合成期），但 00/01/02/03/04 均未提及。唯一消费端说明在 dashboard.md（聚合展示）。

**建议**：在 `_decision_kit_spec.md` 或 `04-synthesize/_shared.md` 补一句"产 sidecar 时需填 cluster_tags，用于跨 topic 相似度 + dashboard 分组"。

---

### A4 🟡 extra_tickers 消费端缺失

00 Step 1 明确说"漏填 = 06-daily-monitor 拿不到第二市场资金/估值/公告"，但 `06-daily-monitor.md` 全文未提及 `extra_tickers`。形成黑箱消费——写的人知道、读的人不知道。

**建议**：06 Step 1（拿到期清单）补一句"对含 extra_tickers 的 topic，scan 会自动拉多市场行情"。

---

### A5 🟢 short_name 描述精度不足

00 Step 1 说 `short_name` 是"WebSearch 查询用"。实际代码中它是 `build_search_queries` hint 中的一个字段，脚本不代写 query。当前表述容易理解成"脚本自动拼 query"。

**建议**：改为"WebSearch 查询 hint（脚本不代写 query，由主 agent 参考）"。

---

### A6 🟢 depth 机械影响边界不清

00 Step 1 说 depth 决定研究时长，但代码中 depth 只在 F17 primer gate 有硬约束（deep → ≥9000 字 + 争议节 + 自检节 + critic_passed）。其他影响（收料优先级、todo 深度）都是软指导，非 gate。文档容易让人以为 depth 影响更大范围。

**建议**：在 00 Step 1 或 04 primer 补一句"depth=deep 的机械硬约束仅限 primer 质量门禁，其余影响为规划指导"。

---

## B. 冗余问题（5 项）

### B1 🔴 auto-fetch 阶梯重复 3 处（几乎相同）

| 文件 | 行 | 角色 |
|------|-----|------|
| `00-research-topic.md` | 547-559 | Step 6.5b：exa→semantic→WebFetch 阶梯 |
| `01-build-roadmap.md` | 341-365 | Step 5.6：同一阶梯 |
| `02-gather-materials.md` | 252-260 | Step 5.7：同一阶梯 |

三级阶梯（exa advanced → adapter semantic → WebFetch）+ `mark_todo_fetch` + `update_user_todo_status` 在三个文件中以几乎相同的文本重复。差异仅在 `triggered_by` 参数和 `addresses` 的默认值。

**建议**：
- 阶梯的「步骤」已在 `_autofetch_protocol.md` 定义——三处改为一行反链 + 本步特化参数
- 保留每处各自的"作用域说明"（00 抓 user_todos / 01 抓 roadmap / 02 抓 pending_unfetched_todos）

---

### B2 🔴 gap "诊断不是 gate" 重复 3 处

| 文件 | 行 | 原文 |
|------|-----|------|
| `02-gather-materials.md` | 291 | "这是诊断不是 gate——脚本不会拒绝你升 stage，但跳过等于把'论证薄弱'留给 04/05" |
| `03-extract-findings.md` | 36 | （几乎相同措辞） |
| `04-synthesize/_shared.md` | 45 | （几乎相同措辞） |

三处都是 ~60 字的同一段论述。DESIGN.md Part 3 有理念级定义，workflow 只需一句话反链。

**建议**：三处改为"gap 是诊断不是 gate（理念见 DESIGN.md §0.5），但跳过 = 把薄弱留给下游"。

---

### B3 🟡 todo 闭环键 = task/文档身份 重复 6 处

| 文件 | 行 |
|------|-----|
| `00-research-topic.md` | 418（5.3 闭环语义） |
| `_autofetch_protocol.md` | 42-51（权威定义） |
| `01-build-roadmap.md` | 330（产即收衔接） |
| `02-gather-materials.md` | 49 |
| `07-drilldown.md` | 117-118 |
| `DESIGN.md` | 123 |

同一核心概念在 6 处展开解释。权威定义在 `_autofetch_protocol.md`，其余为衍生引用。

**建议**：衍生引用改为"闭环键 = task/文档身份，详见 `_autofetch_protocol.md`"，只在本步有特化逻辑时追加。

---

### B4 🟡 产即收 重复 13 处

"谁产 todo 谁当场收，下游只消费不补抓"这条规则散布在：00 Step 5.3/6.5、01 Step 5.6、02 Step 1、03 Step 0a、DESIGN.md 等多处。每处都重述同一逻辑。

**建议**：不全部集中化（"产即收"是行为纪律，每次出现提醒 LLM 有价值），但把权威定义收敛到 `_autofetch_protocol.md`，其余改为"按 autofetch 产即收规约"。

---

### B5 🟢 primer↔case 分工 重复 ~6 处

| 文件 | 行 |
|------|-----|
| `_company_case.md` | 44-48 |
| `_industry_funnel.md` | 44-48 |
| `_arena_funnel.md` | 44-48 |
| `04-synthesize/00-primer.md` | 9, 38-40 |
| `04-synthesize/_shared.md` | 374 |

三个 funnel 文件的 primer↔case 分工表格结构相同、措辞不同。只有元目标（"门外人为了投资..."）是按 type 不同的——理应各自保留。但分工表可以抽到 `_shared.md` 统一定义。

**建议**：分工表统一到 `_shared.md`，各路径只写自己 type 的元目标 + 一行反链。

---

## 修复优先级汇总

| 优先级 | 编号 | 类型 | 内容 | 涉及文件数 |
|--------|------|------|------|-----------|
| 🔴 P0 | A1 | 漂移 | Q# 示例化石 | 2 |
| 🔴 P0 | A2 | 漂移 | DESIGN.md auto_resolve 死引用 | 1 |
| 🔴 P0 | B1 | 冗余 | auto-fetch 阶梯重复 | 3 |
| 🔴 P0 | B2 | 冗余 | gap 诊断不是 gate 重复 | 3 |
| 🟡 P1 | A3 | 漂移 | cluster_tags 创建端缺失 | 1 |
| 🟡 P1 | A4 | 漂移 | extra_tickers 消费端缺失 | 1 |
| 🟡 P1 | B3 | 冗余 | 闭环键重复 | 5 |
| 🟡 P1 | B4 | 冗余 | 产即收重复 | 8+ |
| 🟢 P2 | A5 | 漂移 | short_name 描述精度 | 1 |
| 🟢 P2 | A6 | 漂移 | depth 机械边界不清 | 1 |
| 🟢 P2 | B5 | 冗余 | primer↔case 分工重复 | 4 |

---

## 确认项

1. P0 四项（A1/A2/B1/B2）是否全部修？
2. P1 四项（A3/A4/B3/B4）是否修？其中 B4（产即收 13 处）建议只做反链化而非全部重写——13 处全改工作量大且收益递减，是否接受？
3. P2 三项（A5/A6/B5）是否修？
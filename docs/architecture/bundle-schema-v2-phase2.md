# Bundle Schema v2-phase2

> P1.1 新增字段规格。本文档为权威 schema reference，实施和 QA 均以此为准。

## 版本标识

- `bundle_version`: `"v2-phase1"`（不变，Phase 1 不改变版本号）
- 新字段通过 feature detection 识别：若任一 `insight_block` 含 `narrative_priority`，即为 P1.1+ bundle

---

## 新增字段

### insight_blocks[*].narrative_priority

| 属性 | 值 |
|---|---|
| **类型** | `integer` 1-5 |
| **必填** | 是（P1.1+ bundle） |
| **含义** | 叙事呈现顺序，决定 INSIGHTS.md 和 narrative .md 中该 ib 的展开位置 |

**5 级含义按 source_type：**

**industry_report:**
- 1 = 行业定位 / 当前阶段
- 2 = 核心催化剂 / 为什么现在
- 3 = 主导范式与竞争 / 产业链分析
- 4 = 公司敞口 / 推荐标的
- 5 = 风险与边界

**sell_side_report:**
- 1 = 公司定位 / 主营业务
- 2 = 本次报告核心判断 / 投资要点
- 3 = 竞争力分析 / 护城河
- 4 = 盈利预测 / 估值
- 5 = 风险

**annual_report / quarterly_report:**
- 1 = 公司主业定位
- 2 = 本期经营亮点 / 财务进展
- 3 = 业务分部 / 业绩驱动分析
- 4 = 管理层展望 / 资本开支 / 指引
- 5 = 风险与治理

**transcript:**
- 1 = 会议背景 / 发言人
- 2 = 核心观点 / 对当前形势判断
- 3 = 关键问答
- 4 = 前瞻性内容（指引、计划、展望）
- 5 = 风险或保留意见

### insight_blocks[*].transition_hint

| 属性 | 值 |
|---|---|
| **类型** | `enum` |
| **必填** | 否 |
| **枚举** | `therefore`, `however`, `further`, `specifically`, `but_note`, `meanwhile` |
| **含义** | 与前一个 narrative_priority 相同或相邻 ib 的逻辑连接关系 |

### claim_candidates[*].investment_implication

| 属性 | 值 |
|---|---|
| **类型** | `string` |
| **必填** | 是（P1.1+ bundle） |
| **长度上限** | 150 字 |
| **含义** | 把 claim_text 翻译为可直接写入叙事段落结尾的投资含义表达 |

不是复述 claim_text，而是说"这条 claim 对投资决策意味着什么"。

**示例：**
- claim_text: "磁体占比最大（24.9%），是 A 股金额敞口最集中的环节"
- investment_implication: "超导磁体供应商（如西部超导）在产业链价值量分配中拥有最高的金额敞口，磁体业务收入增长弹性最大。"

### atomic_facts[*].reviewer_notes

| 属性 | 值 |
|---|---|
| **类型** | `string` |
| **必填** | 否 |
| **含义** | 潜在问题标注，由 P0.2 的 suspicious_tokens 机制或 LLM 自我审视触发 |

**示例：** `"原文此处存在 unit_possible_m3 标记：科技文档中 m² 多为 m³ OCR 错"`

### narrative_arc

| 属性 | 值 |
|---|---|
| **类型** | `array` |
| **必填** | 否（0-2 条） |
| **含义** | 整篇报告的叙事结构骨架，消费层的 INSIGHTS.md 合成依赖此字段 |

**schema:**
```json
{
  "arc_id": "arc-001",
  "arc_type": "枚举见下",
  "title": "≤40 字",
  "sections": [
    {
      "section_name": "string",
      "block_ids": ["ib-xxx", ...]
    }
  ]
}
```

**arc_type 枚举：**

通用（任何 source_type 都可用）：
- `investment_thesis` — 投资论点
- `risk_scenario` — 风险情景

industry_report 常见：
- `technology_shift` — 技术路线更替
- `competitive_reshuffling` — 竞争格局重塑
- `demand_cycle` — 需求周期
- `consumption_upgrade` — 消费升级
- `supply_restructuring` — 供给重构
- `regulatory_shift` — 监管转向

sell_side_report 常见：
- `earnings_upgrade` — 盈利上调
- `earnings_downgrade` — 盈利下调
- `rating_initiation` — 首次覆盖
- `thesis_refresh` — 观点更新

annual/quarterly_report 常见：
- `business_progress` — 业务进展
- `earnings_review` — 业绩回顾
- `strategic_pivot` — 战略转向
- `guidance_update` — 指引更新

transcript:
- `outlook_statement` — 前瞻性陈述
- `qa_insights` — 问答洞察

---

## 硬约束（新增）

- **26.** 每个 insight_block 必须有 `narrative_priority` 值（1-5），用于下游叙事排序。
- **27.** 每条 claim 必须有 `investment_implication`（≤150 字），这是 claim 的投资含义翻译，不是 claim_text 的复述。
- **28.** bundle 顶层可产 `narrative_arc`（0-2 条），用于描述整篇报告的叙事骨架。

---

## 向后兼容

- 老 bundle（无 `narrative_priority` 字段）的 QA 只 warn 不 error
- `narrative_propose.py` 兼容缺字段的旧 bundle（缺 `narrative_priority` 时退回按 id 排序）
- 新字段全部 optional in data layer（jsonl 写入时缺失不报错）

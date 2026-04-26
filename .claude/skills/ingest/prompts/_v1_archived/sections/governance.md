# subagent: governance

**负责 section**：公司治理 / Item 10 Directors and Officers / Item 11 Executive Compensation / Item 12 Security Ownership / Item 14 Principal Accountant Fees / 第四节 公司治理 / 第七节 股份变动及股东情况 / Item 5 Market for Registrant's Common Equity

**targets**：`profile.§7`（主要）+ 少量 `claims`

---

## 你要产出的东西

### 1. `profile_fragments.§7_governance`

一份完整 markdown 块，按以下结构填。无披露的字段写 `未披露`，不要编。

```markdown
## 股本与治理

- **总股本（股数）**：{数字}
- **主要股东 / 实控人**：
  1. {姓名或机构}：持股 {X}%
  2. ...
  3. ...
- **董事会规模 / 独立董事比例**：{总人数} 人 / {独董人数} 人（{比例}%）
- **审计师**：{会计师事务所全称}
- **审计意见**：{标准无保留 | 带解释性说明段 | 保留 | 无法表示意见 | 其他}（原文引用）
- **薪酬结构（US 专属）**：CEO 年度总薪酬 ${数字}，其中固定 ${}、绩效 ${}、股权激励 ${}
- **关键治理事件（本期）**：{如董事会改组、首席法律官任命、重大股东变动}
```

**关键红旗雷达**（独立放在 §7 末尾的 `### 红旗标记`）：
- 审计意见**非标准无保留** → 标 🔴
- 前 1 大股东 > 50% 且非机构投资者 → 标 🟡
- 独董比例 < 1/3 → 标 🟡
- 本期更换审计师 → 标 🟡（标注新旧事务所名字）

### 2. `claims`（少量，仅治理红旗级别）

只在出现**具体可证伪的治理事件**时抽：

- 管理层变动：CEO/CFO/核心创始人离职或入职 → `subject_tag: management_credibility`
- 股权变动：大股东减持/增持具体比例 → `subject_tag: capital_allocation`
- 诉讼：对高管/公司已立案 → `subject_tag: regulatory_risk`
- 非标准审计意见 → `subject_tag: management_credibility`

**不抽**：
- 董事会换届（若是按期正常换届）
- 股权激励授予（日常规模）
- 薪酬委员会会议召开次数
- "我们致力于公司治理"这类口号

## subject_tag 使用指南

- `management_credibility` — 管理层变动、声誉事件
- `capital_allocation` — 分红、回购、增发、并购
- `related_party` — 关联方交易（部分内容和 related-party subagent 重叠，**优先让 related-party subagent 产出**，你只抽治理层面的）
- `regulatory_risk` — 针对公司或高管的监管诉讼

## 特有注意事项

1. **A 股年报第七节和第四节内容可能重叠**（股东情况 + 公司治理）—— 主 agent 会把两节都派给你，你合并处理，§7 是汇总输出
2. **US 10-K 的 Item 10-14 是 proxy statement 的 reference**，本身通常是"See our proxy statement dated XXX"占位。如果你看到的内容很短、大量指向 proxy —— 在 `flags` 里说明"§7 需从 proxy statement 补"，产出空 §7 fragment
3. **前五大股东的持股数**：
   - 原文可能是"持股比例"和"持股数"两列 —— 用比例（数字更稳定）
   - A 股"总股本 12.56 亿股"→ 股本数字进 profile.§7 时保留原单位"12.56 亿股"；同时主 agent 会看 `shares_outstanding`（那是 financials-tables 的活）
4. **审计意见原文引用**：
   - A 股："天健会计师事务所(特殊普通合伙)为本公司出具了标准无保留意见的审计报告" → 引用到 "标准无保留" 即可
   - US: "KPMG LLP has issued an unqualified opinion" → 同上

## 反例

- ❌ `§7_governance`: 把董事会成员名字全列一遍 —— 没价值，选实控人/董事长/CEO 即可
- ❌ claim: "公司有完善的治理结构" —— 空话
- ❌ claim 把高管的所有薪酬细节当成 claim —— 薪酬明细进 §7 表格，只对"薪酬异常高/低"起 claim
- ❌ `§7` 里硬列原文没有的字段（编一个 `未披露` 也行，千万不要编具体数字）

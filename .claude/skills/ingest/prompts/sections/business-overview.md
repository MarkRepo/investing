# subagent: business-overview

**负责 section**：业务概述 / 主营业务 / Item 1 Business / 第二节 公司简介和主要财务指标

**targets**：`meta` / `profile.§1-3` / `claims`（业务定位类）

---

## 你要产出的东西

### 1. `meta_updates`（可选）

从正文里找到能补 `meta.md` frontmatter 的字段：

- `website`：公司官网（如 "https://hims.com"）
- `listed_date`：上市日期（如 "2021-01-21"）

找不到就不返回这两个字段。**不要猜**。

### 2. `profile_fragments`

至少要出：

- `§1_business_essence`：用 2-3 句 markdown 描述「做什么、卖给谁、怎么交付、核心收入结算单位」。忠实原文。
- `§2_revenue_structure`：如有业务分部/产品线收入披露 → 产出 markdown 表格：

  ```
  | 业务线 | 收入 (单位) | 占比 | YoY |
  | --- | --- | --- | --- |
  | ... | ... | ... | ... |
  ```

  数字从本 section 或相邻段落抽。**不要**编表头里没有的列。
- `§3_geography`（如有）：地域分部表格。格式同上。

如果本 section 没披露分部/地域 → 省略对应 fragment（不要写"未披露"占位）。

### 3. `claims`

**抽业务定位层面的 atomic claim**：

- 收入结构事实（"数据中心业务 FY2025 收入 $115.2B，占总收入 88%"）
- 客户结构（"前五大客户占 X%"）
- 关键业务指标（"月活付费订户 220 万"）
- 业务模式变化（"2025 年推出订阅模式，当前订户 XXX"）
- 客观事实型陈述（不是分析师观点，也不是管理层展望）

**不抽**：
- 公司成立史、使命宣言、战略口号
- 管理层对未来的展望（交给 mdna subagent）
- 仅"我们致力于..."这类空话

## subject_tag 建议

- `revenue_growth`、`revenue_mix`、`pricing_power`、`volume_trend`
- `market_share`、`competitive_position`
- `customer_concentration`（若词表有；没有则用 `concentration_risk`）

**超出白名单请勿发明**——选最近的 tag 并在 claim_text 开头加 `[可能需要新增 tag]`。

## 特有注意事项

- 本 section 通常不涉及风险因素 —— 遇到风险描述交给 risk-factors subagent，本 agent 不重复抽
- 本 section 通常不涉及财务三表 —— 遇到财务数据除非是"收入分部"否则交给 financials-tables subagent
- A 股年报"第二节"里的"主要财务指标"**整体指标**（如全年营业收入、净利润）可以抽成 claim，但**三表细节**（资产负债明细）留给 financials-tables
- `§1_business_essence` 不能超过 200 字。超过说明你在总结管理层愿景，不是事实

## 反例

- ❌ `§1_business_essence`: "NVIDIA is a global technology leader dedicated to pioneering the future of computing." — 使命宣言，非事实层
- ❌ `claim_text`: "公司在高端白酒行业中占据领导地位" — 定性无数字
- ❌ `meta_updates.website`: "官网" — 不是 URL 格式
- ❌ `§2_revenue_structure`: 把不存在于原文的分部拍脑袋填上

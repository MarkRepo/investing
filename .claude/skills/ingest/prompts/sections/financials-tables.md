# subagent: financials-tables

**负责 section**：财务报告 / 合并财务报表 / Item 8 Financial Statements / 第十节（或第八/九节视公司） / 主要会计数据

**targets**：`financials` / `profile.§6`

---

## 你要产出的核心东西

### 1. `financial_rows`（主产出）

**一份 period 产一行**。从报表里抽最近几年的数据，通常：
- 10-K：本年度 + 可比期 1-2 年（总计 2-3 period）
- 20-F：同上
- A 股年报：本年度 + 上年度对比（2 period）

每行字段（严格按此命名，对应 SQLite `financials` 表列）：

```json
{
  "period": "2025A|FY2025|2024A",
  "period_type": "annual|quarterly",
  "revenue": <数字，基础货币单位>,
  "gross_profit": <>,
  "operating_income": <>,
  "net_income": <>,
  "total_assets": <>,
  "total_equity": <>,
  "operating_cashflow": <>,
  "shares_outstanding": <>
}
```

### Period 命名规范

- 年报 → `{YYYY}A`（如 `2025A`）；**US 财年非日历年**的（如 NVIDIA 财年 1 月底）→ `FY{YYYY}`（如 `FY2025`）
- 季度 → `{YYYY}Q{1-4}`
- 和预处理 meta 里的 fiscal_year 对齐

### 单位换算（关键，错了就毒整个数据库）

**所有数字必须换成基础货币的"元"或"美元"**，即**最小整数单位**。

- 原文 "$130,497 million" → `130497000000`
- 原文 "1,783.01 亿元" → `178301000000`（17830100 万，乘 10000；或 1,783.01 × 10^8）
- 原文 "100,497,483 千元" → `100497483000`

**规则**：
1. `million` = `× 1,000,000`
2. `thousand` = `× 1,000`
3. 中文"万元" = `× 10,000`
4. 中文"百万元" = `× 1,000,000`
5. 中文"亿元" = `× 100,000,000`

**换算不确定时**：把该字段留空（`null`），在 `flags` 里说明"revenue 单位不明，原文 {raw}"。

### 2. `profile_fragments`

- `§6_balance_sheet`：markdown 表格呈现本年末资产负债结构（现金 / 短期投资 / 有息负债 / 所有者权益），单位标原文单位不换算

## 你**不该**产出

- ❌ `claims` —— 三表数字本身不进 claims（进 financials）。如果正文里有"revenue 同比 +30%"这种分析型陈述，交给 mdna subagent
- ❌ `meta_updates`
- ❌ 任何 profile §1-§5 / §7-§9 内容

## 特有注意事项

1. **年报附注几乎永远在本 section 内**。附注里有大量细节（分部收入、关联方、股权激励、或有负债）—— **这些交给其它 subagent**。你只关心三表主表。
2. **A 股年报"合并"vs"母公司"**：只抽**合并**报表数据，母公司报表不进 financials。
3. **US 10-K 的 "Consolidated Statements of Operations / Balance Sheets / Cash Flows"**：对应 revenue/equity/operating_cashflow 三张主表。
4. **共用字段**：
   - `revenue` = 营业收入（A 股）/ Revenue / Net sales / Total revenues（US，取最顶层的汇总行）
   - `gross_profit` = 毛利（营业收入 - 营业成本）
   - `operating_income` = 营业利润 / Operating income
   - `net_income` = 净利润（归母或总利润？—— US 取 "Net income" 底线；A 股取**归母净利润**，因为这是投资人关心的）
   - `total_assets` = 资产总计
   - `total_equity` = 所有者权益合计（A 股）/ Total stockholders' equity（US）
   - `operating_cashflow` = 经营活动现金流量净额 / Net cash from operating activities
   - `shares_outstanding` = 股本（A 股单位：股）/ 加权平均流通股数（US：股，看 Basic weighted average shares outstanding）
5. **披露缺失**：公司没披露的字段 → `null`，不要插 0。
6. **shares_outstanding 的坑**：
   - A 股披露"总股本 12.56 亿股" → 转成股数 `1256000000`
   - US 通常披露 "Weighted average shares basic: 223,456,789" → 直接用这个数
   - **不要混淆 basic vs diluted**，优先 basic
7. **财报期末股数 vs 加权股数**：SQLite 里这一列无明确语义，优先填**期末**（对 A 股）或 **basic weighted average**（对 US）。在 flags 里标你用了哪个

## 反例

- ❌ `revenue: 130.5` —— 应是 `130497000000`，不要留"亿"或"million"单位
- ❌ `period: "2025"` —— 无 `A`/`Q` 后缀，会被 `PERIOD_RE = ^(\d{4})(Q[1-4]|A)$` 拒
- ❌ 从三表里抽"毛利率 75%"到 `financial_rows` —— ratios 是**派生**的，SQLite 会自动从 gross_profit/revenue 算，不要手工塞
- ❌ 抽公司的"上一年同期"数据到和本年同一行 —— 每年一行

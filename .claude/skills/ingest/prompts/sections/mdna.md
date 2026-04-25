# subagent: mdna

**负责 section**：管理层讨论与分析 / MD&A / Item 7 / 第三节 管理层讨论与分析 / 经营情况讨论与分析

**targets**：`profile.§1` / `profile.§2` / `profile.§4` / `claims`（大量）

---

## 你要产出的东西

### 1. `claims`（主产区，期望 10-30 条）

MD&A 是 claim 的富矿——**定性观察 + 定量数据**都密集。按以下优先级抽取：

1. **经营业绩解释**：收入/成本/利润率的 YoY 变化原因
   - "FY2025 gross margin 扩张到 75%（较 73% 提升 200bp），主因 Data Center 产品组合优化"
2. **分部表现**：各业务分部的增速、利润率、订单/ASP 变化
3. **运营指标**：订户数、留存率、渠道结构变化、产能利用率
4. **管理层指引**：对下一期/下一年的明确数字（营收指引、capex 指引）
5. **费用结构变化**：研发/销售/管理费用占比、招聘节奏
6. **Cash flow 叙述**：经营现金流与净利润的差异原因
7. **特殊/一次性项目**：重组、减值、资产处置、诉讼准备金

### 2. `profile_fragments`

如有以下内容可产出：

- `§1_business_essence` 补充（如 MD&A 里有更清晰的主业描述）
- `§2_revenue_structure`（若 MD&A 里有更新的分部收入明细，优先用这里）
- `§4_key_operating_metrics`：markdown 表格 or bullet list，列出 MD&A 里披露的关键 KPI

## subject_tag 使用指南

MD&A 最常用的 tag：
- **收入类**：`revenue_growth`、`revenue_mix`、`pricing_power`、`volume_trend`
- **盈利类**：`gross_margin`、`operating_leverage`、`margin_trend`
- **经营类**：`channel_inventory`、`working_capital`、`capex_cycle`
- **竞争类**：`competitive_position`、`new_entrants`
- **治理类**：`management_credibility`、`capital_allocation`
- **估值类**：`guidance_reliability`、`consensus_direction`、`catalyst`

## 特有注意事项

1. **区分事实 vs 展望**：
   - 本年度实际数字 → `claim_type: quantitative`，`timeframe: FY{year}` 或 `YYYYQN`
   - 管理层对下一年的指引 → `claim_type: quantitative`，`timeframe: FY{year+1}`，`subject_tag: guidance_reliability`
   - 模糊展望（"我们预计保持强劲增长"）→ **不抽**（不可证伪）
2. **YoY 数字要明确哪一期 vs 哪一期**：不要丢 timeframe
3. **大段文字里混入多条独立事实** → 拆成多条 claim，不要合并
4. **MD&A 常提到"影响因素"是否抽**：
   - 具体可观察："汇率不利影响拖累 revenue 约 $50M" → 抽（quantitative）
   - 虚描述："宏观环境充满不确定性" → 不抽

## 🔢 MD&A 抽数前必做的两步（血泪教训）

A 股 MD&A 是单位错的重灾区。历史上出过"把 72.53 亿写成 7.25 亿"这种 10× 低估整批 claim 的事故。抽任何含"亿元/万元/元"的数字前，**两步自查**：

### 第一步：找表头单位
抽数字前，**找这个数字所在表的表头或文前标注**。A 股年报 MD&A 里，表头几乎必有"**单位：元**"或"**单位：万元**"或"**单位：百万元**"的明示。确认表头单位后再开始读数字。

### 第二步：对照营收锚点
主 agent 传给你的 company context 里一般会含 FY{year} 营业收入的参考值（如茅台 1,688.38 亿元）。对你抽的每条量化 claim，心里算一下它与营收的比例：

| 项目 | 典型占营收比例 | 示例（营收 1,688 亿） |
|---|---|---|
| 营业成本 | 10-90%（看行业） | 茅台 ~9%（高毛利白酒）→ 148 亿级 |
| 销售费用 | 1-30% | 茅台 ~4% → 70 亿级 |
| 管理费用 | 2-10% | 茅台 ~5% → 84 亿级 |
| 研发投入 | 0.5-25% | 茅台 ~0.5% → 8 亿级 |
| 经营现金流 | 0.5-1.5×净利润 | 茅台 ~0.75× → 615 亿级 |
| 任一分部收入 | ≤ 总营收 | 永远不会超过总营收 |

如果你的 claim 比例掉出上面区间，先怀疑单位读错——**回去看表头**。

### 典型陷阱（茅台 FY2025 实例）

- 原文（单位：元）："销售费用 7,253,499,600.68"
  - ❌ 错：claim_text = "销售费用 7.25 亿元"（把 10 位整数误当成"十亿"级，实际 = 72.53 亿）
  - ✅ 对：claim_text = "销售费用 72.53 亿元"
- 原文（单位：元）："营业成本 14,892,277,570.91"
  - ❌ 错："营业成本 14.89 亿元" → 14.89 / 1688 = 0.88%（毛利率 99%，不合理）
  - ✅ 对："营业成本 148.92 亿元" → 148.92 / 1688 = 8.8%（毛利率 91.2%，合理）
- 原文（单位：万元）："16,883,810.25"
  - ❌ 错："168.8 亿元"（把"万元"当"十万"）
  - ✅ 对："1,688.38 亿元"（N 万元 ÷ 10,000 = N 亿元）

## confidence 判断

- `high`：数字+时期+方向都原文明写
- `medium`：原文给了数字但时期或方向要推
- `low`：管理层定性表述、需要你推断方向或幅度 —— 这种最好不抽，若抽必标 low

## 反例

- ❌ `claim_text`: "管理层对下一年充满信心" — 空话
- ❌ `claim_text`: "收入、利润和毛利率均有改善" — 复合句，必须拆 3 条
- ❌ `timeframe`: 省略 — MD&A 的 claim 几乎全都有时期，省略会导致 period_consistency 校验失败
- ❌ `subject_tag`: "business_performance" — 不在白名单
- ❌ 从 MD&A 抽三表细分数据写进 `financial_rows` — 那是 financials-tables subagent 的活

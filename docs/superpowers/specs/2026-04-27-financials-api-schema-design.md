# 财务数据 API 化：双市场宽表 + 财报页面手动刷新

日期：2026-04-27

## 背景与决策

现有 `financials` 表有 54 列，靠 LLM 从 PDF 抽取 CSV 导入，字段覆盖率约 10/54。
两个 API 可完整覆盖：

- **A 股**：`akshare.stock_financial_report_sina`（利润表 83 列 / 资产负债表 147 列 / 现金流量表 71 列，28 年历史）
- **美股**：`yfinance`（income_stmt 39 列 / balance_sheet 69 列 / cashflow 53 列，5 年年报 + 季报）

两市场字段体系差异大（A 股中文、US GAAP 英文），可双向映射的核心字段约 66 个。
**决策：两张独立宽表，全量保留各自字段，共有概念用相同 snake_case 列名（`operating_income`、`net_income`、`total_assets` 等），方便 ratios SQL 复用。**

FMP 免费版对中小盘 402，yfinance 字段更多（161 vs 139）且覆盖全量，选 yfinance。

---

## §1 表结构

### 删除

- `financials` 表（54 列旧 schema）
- `app/config.py` 里的 `INCOME_STATEMENT_LINES` / `BALANCE_SHEET_LINES` / `CASHFLOW_LINES` / `FINANCIAL_COLUMNS`

### 新建 `financials_cn`（A 股）

来源：`akshare.stock_financial_report_sina`（`sh`/`sz`/`bj` 前缀）

```sql
CREATE TABLE financials_cn (
    ticker        TEXT NOT NULL,
    report_date   DATE NOT NULL,      -- 报告日，如 2024-03-31
    period        TEXT NOT NULL,      -- YYYYQ1/Q2/Q3/Q4 或 YYYYA
    period_type   TEXT NOT NULL,      -- quarterly / annual
    is_audited    INTEGER,            -- 是否审计（0/1）
    announced_date DATE,             -- 公告日期
    currency      TEXT,

    -- 利润表（~60 数据列，中文→snake_case）
    total_revenue             REAL,   -- 营业总收入
    operating_revenue         REAL,   -- 营业收入
    total_operating_cost      REAL,   -- 营业总成本
    cost_of_revenue           REAL,   -- 营业成本
    rd_expense                REAL,   -- 研发费用
    selling_expense           REAL,   -- 销售费用
    admin_expense             REAL,   -- 管理费用
    finance_expense           REAL,   -- 财务费用（净，含利息+汇兑）
    interest_expense          REAL,   -- 利息费用（单独披露时）
    investment_income         REAL,   -- 投资收益
    fair_value_change_income  REAL,   -- 公允价值变动收益
    fx_gain                   REAL,   -- 汇兑收益
    other_income              REAL,   -- 其他收益
    asset_impairment_loss     REAL,   -- 资产减值损失
    credit_impairment_loss    REAL,   -- 信用减值损失
    operating_income          REAL,   -- 营业利润
    non_operating_income      REAL,   -- 营业外收入
    non_operating_expense     REAL,   -- 营业外支出
    pretax_income             REAL,   -- 利润总额
    income_tax                REAL,   -- 所得税费用
    net_income                REAL,   -- 净利润
    net_income_to_parent      REAL,   -- 归属母公司净利润
    minority_interest_income  REAL,   -- 少数股东损益
    other_comprehensive_income REAL,  -- 其他综合收益
    total_comprehensive_income REAL,  -- 综合收益总额
    eps_basic                 REAL,   -- 基本每股收益
    eps_diluted               REAL,   -- 稀释每股收益
    -- 保险/银行特有字段（空则 NULL）
    interest_income           REAL,   -- 利息收入
    premium_earned            REAL,   -- 已赚保费
    commission_income         REAL,   -- 手续费及佣金收入
    commission_expense        REAL,   -- 手续费及佣金支出

    -- 资产负债表（~100 数据列）
    cash_and_equivalents      REAL,   -- 货币资金
    trading_financial_assets  REAL,   -- 交易性金融资产
    notes_and_accounts_receivable REAL, -- 应收票据及应收账款
    accounts_receivable       REAL,   -- 应收账款
    prepayments               REAL,   -- 预付款项
    other_receivables         REAL,   -- 其他应收款
    inventory                 REAL,   -- 存货
    other_current_assets      REAL,   -- 其他流动资产
    total_current_assets      REAL,   -- 流动资产合计
    long_term_equity_investment REAL, -- 长期股权投资
    investment_property       REAL,   -- 投资性房地产
    gross_ppe                 REAL,   -- 固定资产原值
    accumulated_depreciation  REAL,   -- 累计折旧
    net_ppe                   REAL,   -- 固定资产净额
    construction_in_progress  REAL,   -- 在建工程
    intangible_assets         REAL,   -- 无形资产
    goodwill                  REAL,   -- 商誉
    deferred_tax_assets       REAL,   -- 递延所得税资产
    other_non_current_assets  REAL,   -- 其他非流动资产
    total_non_current_assets  REAL,   -- 非流动资产合计
    total_assets              REAL,   -- 资产总计
    short_term_debt           REAL,   -- 短期借款
    notes_and_accounts_payable REAL,  -- 应付票据及应付账款
    accounts_payable          REAL,   -- 应付账款
    contract_liabilities      REAL,   -- 合同负债
    employee_benefits_payable REAL,   -- 应付职工薪酬
    taxes_payable             REAL,   -- 应交税费
    other_current_liab        REAL,   -- 其他流动负债
    total_current_liab        REAL,   -- 流动负债合计
    long_term_debt            REAL,   -- 长期借款
    bonds_payable             REAL,   -- 应付债券
    deferred_tax_liabilities  REAL,   -- 递延所得税负债
    other_non_current_liab    REAL,   -- 其他非流动负债
    total_non_current_liab    REAL,   -- 非流动负债合计
    total_liabilities         REAL,   -- 负债合计
    paid_in_capital           REAL,   -- 实收资本（或股本）
    capital_surplus           REAL,   -- 资本公积
    retained_earnings         REAL,   -- 未分配利润
    treasury_stock            REAL,   -- 减：库存股
    other_comprehensive_equity REAL,  -- 其他综合收益（权益）
    equity_to_parent          REAL,   -- 归属母公司股东权益合计
    minority_equity           REAL,   -- 少数股东权益
    total_equity              REAL,   -- 所有者权益合计

    -- 现金流量表（~50 数据列）
    cash_from_customers       REAL,   -- 销售商品收到的现金
    cash_paid_to_employees    REAL,   -- 支付给职工的现金
    taxes_paid                REAL,   -- 支付的各项税费
    operating_cashflow        REAL,   -- 经营活动现金流量净额
    capex                     REAL,   -- 购建固定资产等支付的现金
    investment_purchased      REAL,   -- 投资所支付的现金
    investment_recovered      REAL,   -- 收回投资所收到的现金
    investing_cashflow        REAL,   -- 投资活动现金流量净额
    proceeds_from_borrowings  REAL,   -- 取得借款收到的现金
    repayment_of_debt         REAL,   -- 偿还债务支付的现金
    dividends_paid            REAL,   -- 分配股利等支付的现金
    financing_cashflow        REAL,   -- 筹资活动现金流量净额
    fx_effect_on_cash         REAL,   -- 汇率变动对现金的影响
    net_change_in_cash        REAL,   -- 现金及现金等价物净增加额
    begin_cash                REAL,   -- 期初现金及现金等价物余额
    end_cash                  REAL,   -- 期末现金及现金等价物余额

    source TEXT,
    PRIMARY KEY (ticker, period)
);
```

### 新建 `financials_us`（美股）

来源：`yfinance.Ticker.income_stmt` / `balance_sheet` / `cashflow`（年报）和对应 `quarterly_*` 属性（季报）

```sql
CREATE TABLE financials_us (
    ticker        TEXT NOT NULL,
    report_date   DATE NOT NULL,
    period        TEXT NOT NULL,      -- YYYYQ1..Q4 / YYYYA
    period_type   TEXT NOT NULL,      -- quarterly / annual
    currency      TEXT,

    -- 利润表（yfinance Title Case → snake_case）
    total_revenue             REAL,   -- 总营收
    operating_revenue         REAL,   -- 经营性营收（排除非经常项）
    cost_of_revenue           REAL,   -- 营业成本
    gross_profit              REAL,   -- 毛利润
    research_and_development  REAL,   -- 研发费用
    selling_general_and_administration REAL, -- 销售及管理费用（SG&A 合并）
    operating_expense         REAL,   -- 营业费用合计（含 SG&A + R&D）
    operating_income          REAL,   -- 营业利润（EBIT 前）
    ebit                      REAL,   -- 息税前利润
    ebitda                    REAL,   -- 息税折旧摊销前利润
    interest_income           REAL,   -- 利息收入
    interest_expense          REAL,   -- 利息支出
    net_interest_income       REAL,   -- 净利息收支（收入 - 支出）
    pretax_income             REAL,   -- 税前利润
    tax_provision             REAL,   -- 所得税费用
    net_income                REAL,   -- 净利润
    net_income_common_stockholders REAL, -- 归属普通股股东净利润
    basic_eps                 REAL,   -- 基本每股收益
    diluted_eps               REAL,   -- 摊薄每股收益
    basic_average_shares      REAL,   -- 基本加权平均股数
    diluted_average_shares    REAL,   -- 摊薄加权平均股数
    normalized_income         REAL,   -- 调整后净利润（剔除特殊项）
    normalized_ebitda         REAL,   -- 调整后 EBITDA
    reconciled_depreciation   REAL,   -- 调节后折旧摊销额
    stock_based_compensation  REAL,   -- 股权激励费用（从现金流量表取）

    -- 资产负债表
    cash_and_cash_equivalents REAL,   -- 现金及现金等价物
    accounts_receivable       REAL,   -- 应收账款
    inventory                 REAL,   -- 存货
    current_assets            REAL,   -- 流动资产合计
    net_ppe                   REAL,   -- 固定资产净值（PP&E net）
    gross_ppe                 REAL,   -- 固定资产原值（PP&E gross）
    accumulated_depreciation  REAL,   -- 累计折旧
    goodwill                  REAL,   -- 商誉
    goodwill_and_intangible_assets REAL, -- 商誉及无形资产合计（yfinance 不单独拆分）
    deferred_tax_assets       REAL,   -- 递延所得税资产
    total_non_current_assets  REAL,   -- 非流动资产合计
    total_assets              REAL,   -- 资产总计
    accounts_payable          REAL,   -- 应付账款
    current_debt              REAL,   -- 短期借款及一年内到期长债
    current_liabilities       REAL,   -- 流动负债合计
    long_term_debt            REAL,   -- 长期债务
    total_liabilities_net_minority_interest REAL, -- 负债合计（不含少数股东权益）
    retained_earnings         REAL,   -- 留存收益（未分配利润）
    stockholders_equity       REAL,   -- 普通股股东权益
    total_equity              REAL,   -- 股东权益合计（含少数股东）
    total_debt                REAL,   -- 有息负债合计（短期 + 长期）
    net_debt                  REAL,   -- 净负债（有息负债 - 现金）
    working_capital           REAL,   -- 营运资本（流动资产 - 流动负债）
    capital_lease_obligations REAL,   -- 融资租赁负债
    common_stock              REAL,   -- 普通股面值
    treasury_shares_number    REAL,   -- 库存股股数

    -- 现金流量表
    operating_cash_flow       REAL,   -- 经营活动现金流量净额
    investing_cash_flow       REAL,   -- 投资活动现金流量净额
    financing_cash_flow       REAL,   -- 筹资活动现金流量净额
    capital_expenditure       REAL,   -- 资本支出（购建固定资产等，负值）
    free_cash_flow            REAL,   -- 自由现金流（OCF + CapEx）
    depreciation_and_amortization REAL, -- 折旧与摊销
    change_in_working_capital REAL,   -- 营运资本变动
    changes_in_cash           REAL,   -- 现金净增加额
    end_cash_position         REAL,   -- 期末现金余额
    begin_cash_position       REAL,   -- 期初现金余额
    issuance_of_debt          REAL,   -- 借款净增加（发行债务）
    repayment_of_debt         REAL,   -- 偿还债务支付的现金
    repurchase_of_capital_stock REAL, -- 回购股票支付的现金
    cash_dividends_paid       REAL,   -- 支付股息
    net_income_from_continuing_operations REAL, -- 持续经营净利润（OCF 调节起点）
    deferred_income_tax       REAL,   -- 递延所得税（非现金调整项）
    other_non_cash_items      REAL,   -- 其他非现金调整项

    source TEXT,
    PRIMARY KEY (ticker, period)
);
```

---

## §2 Period 推导规则

**A 股（akshare）**：`报告日` 字段是日期，月份决定季度；年报通过 `类型` 字段含 "年报" 或直接对应完整财年判断。

```
MM=03 → Q1   MM=06 → Q2   MM=09 → Q3
MM=12 且 是年报 → A       MM=12 且 非年报 → Q4
```

period 格式：`2024Q1`、`2024A`

**美股（yfinance）**：
- `income_stmt`（4列 Timestamp）→ `period_type=annual`
- `quarterly_income_stmt`（4列）→ `period_type=quarterly`
- 日期月份推 Q1..Q4（财年末为 Q4/A）

---

## §3 Ratios 表保留

`ratios` 表结构不变，`recompute_ratios(conn, ticker, market)` 接受 market 参数：

- `market` 为 A 股市场（SSE/SZSE/BSE）→ 读 `financials_cn`，使用 `operating_cashflow`、`income_tax`、`total_current_liab` 等 CN 列名
- `market` 为 US → 读 `financials_us`，使用 `operating_cash_flow`、`tax_provision`、`current_liabilities` 等 US 列名

两张表都含 ratios 所需的 15 个核心字段（`operating_income`、`net_income`、`total_assets`、`total_equity`、`accounts_receivable`、`inventory`、`accounts_payable` 等使用相同列名）。

---

## §4 财报页面（`/companies/{key}/financials`）

### 4.1 页面结构

```
[公司名] · 财务报表
← 返回公司

[刷新财务数据] 按钮                    上次更新：2026-04-20
[年报 | 季报] 切换 Tab

── 利润表 ──────────────────────────────
期间        营收    毛利率  营业利润  净利润  EPS
2024A       ...
2023A       ...
...

── 资产负债表 ────────────────────────────
期间        总资产  总负债  股东权益  资产负债率
...

── 现金流量表 ────────────────────────────
期间        经营CFO  资本开支  自由现金流  筹资CFF
...

── 关键比率 ──────────────────────────────
期间        毛利率  净利率  ROE  ROA  D/E
...
```

展示最近 8 期年报或最近 12 期季报。

### 4.2 刷新按钮

- `POST /companies/{key}/financials/refresh`
- 路由调 `fetch_financials_cn` 或 `fetch_financials_us` 的 `run_for_ticker(ticker, market)` 函数（复用 EOD 脚本的模式）
- 返回 JSON `{ok, periods_added, error}`
- 成功时 `location.reload()`；失败时页面顶部 alert
- 节流 30s（避免频繁调 API）
- 按钮 disabled 期间显示"正在刷新…"

### 4.3 年报/季报切换

纯前端：切换时显示/隐藏对应 `period_type` 的行（服务端一次性返回全部，JS 过滤）。

### 4.4 CSV 导入入口

**删除**。财务数据改由 API 获取，不再支持手动 CSV 导入。

---

## §5 导入脚本

### `scripts/fetch_financials_cn.py`

```
python -m scripts.fetch_financials_cn SSE_600519        # 单票
python -m scripts.fetch_financials_cn --all              # 所有 A 股公司
python -m scripts.fetch_financials_cn --market SZSE      # 按市场
```

- 调 akshare 三张报表（利润表 / 资产负债表 / 现金流量表）
- 用 `app/config.py` 里的 `CN_COL_MAP` dict（~200 条，中文→snake_case）做列名翻译
- 三张表按 `报告日` join，同一 period 合并为一行
- upsert `financials_cn` → `recompute_ratios`
- 导出 `run_for_ticker(ticker, market)` 供路由 refresh 调用

### `scripts/fetch_financials_us.py`

```
python -m scripts.fetch_financials_us US_HIMS
python -m scripts.fetch_financials_us --all
```

- 调 `yfinance.Ticker.income_stmt` / `balance_sheet` / `cashflow`（年报）
- 调 `quarterly_income_stmt` / `quarterly_balance_sheet` / `quarterly_cashflow`（季报）
- `US_COL_MAP`：yfinance Title Case → snake_case（`str.lower().replace(' ', '_')` 为基础，少量手工修正）
- upsert `financials_us` → `recompute_ratios`
- 导出 `run_for_ticker(ticker, market)` 同上

---

## §6 Ingest 流程变更

### 预处理（`scripts/preprocess_report.py`）

- **删除** `extract_financial_line_rows()` 函数
- **删除** `build_result()` 里的 `financial_line_rows` 键
- 四个模板新增 `skip_rules.sections` 条目，让财务报表 section 直接标记 `action: skip`（不传 LLM，省 token）：

| 模板 | 新增 skip section |
|---|---|
| `a-share-annual.yaml` | `财务报告`、`主要财务数据` |
| `a-share-quarterly.yaml` | `季度财务报表`、`主要财务数据` |
| `us-10k.yaml` | `Item_8_Financial_Statements` |
| `us-10q.yaml` | `Part_I_Item_1_Financial_Statements` |

### Aggregate（`scripts/ingest_aggregate.py`）

- **删除** `financial_rows` 字段聚合逻辑
- **删除** `write_financials()` 函数
- **删除** `check_financials_required()` 调用

### QA（`scripts/ingest_qa.py`）

- **删除** `check_financials_required()` 函数

---

## §7 完整代码变更范围

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `app/config.py` | 改 | 删 4 个旧 tuple；新增 `CN_COL_MAP` dict（~200 条） |
| `app/io/financials.py` | 重写 | 新 schema、新 upsert、ratios 接受 market 参数 |
| `app/routes/financials.py` | 改 | 删 CSV import 路由；新增 `/refresh` POST；列名改新 schema |
| `app/templates/companies/financials.html` | 重写 | 三张报表 + 比率 + 刷新按钮；删 CSV 上传表单 |
| `controlled-vocab/financial-aliases.yaml` | 改 | 映射目标改为新 snake_case 列名 |
| `scripts/preprocess_report.py` | 改 | 删 `extract_financial_line_rows` + `financial_line_rows` |
| `scripts/ingest_aggregate.py` | 改 | 删 `financial_rows` 聚合 + `write_financials` + `check_financials_required` |
| `scripts/ingest_qa.py` | 改 | 删 `check_financials_required` |
| `.claude/skills/ingest/templates/*.yaml`（4 个）| 改 | 新增财务 section skip |
| `scripts/fetch_financials_cn.py` | 新增 | A 股财务 API 拉取 + upsert |
| `scripts/fetch_financials_us.py` | 新增 | 美股财务 API 拉取 + upsert |
| `tests/test_financials_io.py` | 重写 | 新 schema API |
| `tests/test_financials_extended.py` | 重写 | ratios + market 参数 |
| `tests/test_preprocess_financial_lines.py` | 删除 | 测试已删函数 |

---

## 不做

- 不做财务数据的自动定时拉取（手动刷新 + 季报后手跑脚本已足够）
- 不做跨市场财务数据归一化视图（66 个共有字段通过 alias map 按需查，不建 materialized view）
- 不做财务数据版本历史（akshare 返回的就是最新修订版，直接覆盖）
- 不做财务数据的 LLM 分析页面（属于 `/brief` 功能范围，单独设计）
- 不迁移旧 `financials` 表数据（覆盖率 10/54，API 重拉更完整）

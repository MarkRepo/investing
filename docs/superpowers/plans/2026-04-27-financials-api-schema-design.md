# 财务数据 API 化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用两张独立宽表（`financials_cn` / `financials_us`）替换现有 54 列 `financials` 表；财务数据从 API（akshare/yfinance）获取；新增手动刷新的财报页面；从 ingest 流程里彻底删除财务数字抽取。

**Architecture:** 两市场两张表，共有概念用相同 snake_case 列名；`recompute_ratios(conn, ticker, market)` 按 market 分派读对应表；页面纯前端过滤（Tab + 期数下拉），刷新按钮调脚本 `run_for_ticker`。ingest 只产 claims + MD&A 叙述，不再产 financial_rows。

**Tech Stack:** Python 3.11 · SQLite · FastAPI · Jinja2 · akshare · yfinance · pytest

Spec: `docs/superpowers/specs/2026-04-27-financials-api-schema-design.md`

---

## 文件结构

| 文件 | 动作 | 责任 |
|---|---|---|
| `app/config.py` | 改 | 删 4 个旧 tuple + `FINANCIAL_ALIASES_PATH`；加 `CN_COL_MAP` + `US_COL_MAP` |
| `app/io/financials.py` | 重写 | 两表 schema、upsert、`recompute_ratios(conn, ticker, market)`、list 查询 |
| `app/io/earnings_review.py` | 改 | `list_financials` 调用改 market 分派 |
| `app/routes/financials.py` | 改 | 删 `/import`，加 `/refresh` POST |
| `app/templates/companies/financials.html` | 重写 | 三报表 + 比率 + 刷新按钮 + Tab + 期数下拉 |
| `scripts/fetch_financials_cn.py` | 新增 | akshare → `financials_cn`，导出 `run_for_ticker` |
| `scripts/fetch_financials_us.py` | 新增 | yfinance → `financials_us`，导出 `run_for_ticker` |
| `scripts/preprocess_report.py` | 改 | 删 `extract_financial_line_rows` + `financial_line_rows` key |
| `scripts/ingest_aggregate.py` | 改 | 删 `financial_rows`、`write_financials`、`check_financials_required`、`check_revenue_consistency` |
| `scripts/ingest_qa.py` | 改 | 删 `check_financials_required` |
| `.claude/skills/ingest/section-routing.yaml` | 改 | 财务 section `extract` → `skip` |
| `.claude/skills/ingest/templates/*.yaml` (4) | 改 | 加财务 section skip 规则 |
| `.claude/skills/ingest/workflows/*.md` (3) | 改 | 删财务流程步骤 |
| `.claude/skills/ingest/prompts/digest/*.md` (2) | 改 | 删 `financial_rows`；`financial_profile` 来源改 MD&A |
| `.claude/skills/ingest/SKILL.md` | 改 | 删财务流程描述 |
| `.claude/skills/ingest/cross-checks.yaml` | 改 | 删 financial_rows 规则 |
| `controlled-vocab/financial-aliases.yaml` | 删 | 新流程不用 |
| `tests/test_financials_io.py` | 重写 | 新两表 schema API |
| `tests/test_financials_extended.py` | 删 | 测试已删 alias_map 等功能 |
| `tests/test_preprocess_financial_lines.py` | 删 | 测试已删函数 |
| `tests/test_ingest_aggregate.py` | 改 | 删 financial_rows / write_financials 测试 |
| `tests/test_digest_prompt_contracts.py` | 改 | 删 `test_annual_digest_declares_financial_rows` |
| `tests/test_config_dimensions.py` | 改 | 删 INCOME/BALANCE/CASHFLOW 断言 |
| `tests/test_preprocess_industry_type.py` | 改 | 删 `financial_line_rows == []` 断言 |
| `tests/test_fetch_financials_cn.py` | 新增 | akshare adapter 测试 |
| `tests/test_fetch_financials_us.py` | 新增 | yfinance adapter 测试 |

---

## Task 1: 重写 `app/config.py` —— 删旧财务 tuple，加 `CN_COL_MAP` + `US_COL_MAP`

**Files:**
- Modify: `app/config.py:86-121`（删 `INCOME_STATEMENT_LINES`/`BALANCE_SHEET_LINES`/`CASHFLOW_LINES`/`FINANCIAL_ALIASES_PATH`；新增 2 个 map）

- [ ] **Step 1: 删除 4 个旧常量**

编辑 `app/config.py`，删除第 86–121 行的 4 个 tuple / path 常量。保留上方 `COMPANY_DIMENSIONS` 等不动。

- [ ] **Step 2: 在文件末尾追加 `CN_COL_MAP` + `US_COL_MAP`**

```python
# app/config.py (append at end of file)

# CN_COL_MAP: akshare stock_financial_report_sina 返回的中文列名 → financials_cn snake_case
# 三张表共用一个 map；同名 key 若两表语义不同，按资产负债表优先（goodwill 等只出现在 BS）
# 未在 map 里的列由 fetch_financials_cn 忽略（仅 WARN，不 fail）
CN_COL_MAP: dict[str, str] = {
    # 元信息
    "报告日": "report_date",
    "类型": "_report_type",  # 内部用于判断 年报/季报
    # 利润表
    "营业总收入": "total_revenue",
    "营业收入": "operating_revenue",
    "营业总成本": "total_operating_cost",
    "营业成本": "cost_of_revenue",
    "研发费用": "rd_expense",
    "销售费用": "selling_expense",
    "管理费用": "admin_expense",
    "财务费用": "finance_expense",
    "利息费用": "interest_expense",
    "利息收入": "interest_income",
    "投资收益": "investment_income",
    "公允价值变动收益": "fair_value_change_income",
    "汇兑收益": "fx_gain",
    "其他收益": "other_income",
    "资产减值损失": "asset_impairment_loss",
    "信用减值损失": "credit_impairment_loss",
    "营业利润": "operating_income",
    "营业外收入": "non_operating_income",
    "营业外支出": "non_operating_expense",
    "利润总额": "pretax_income",
    "所得税费用": "income_tax",
    "净利润": "net_income",
    "归属于母公司股东的净利润": "net_income_to_parent",
    "归属于母公司所有者的净利润": "net_income_to_parent",
    "少数股东损益": "minority_interest_income",
    "其他综合收益": "other_comprehensive_income",
    "综合收益总额": "total_comprehensive_income",
    "基本每股收益": "eps_basic",
    "稀释每股收益": "eps_diluted",
    "已赚保费": "premium_earned",
    "手续费及佣金收入": "commission_income",
    "手续费及佣金支出": "commission_expense",
    # 资产负债表 - 资产
    "货币资金": "cash_and_equivalents",
    "交易性金融资产": "trading_financial_assets",
    "应收票据及应收账款": "notes_and_accounts_receivable",
    "应收账款": "accounts_receivable",
    "预付款项": "prepayments",
    "其他应收款": "other_receivables",
    "存货": "inventory",
    "其他流动资产": "other_current_assets",
    "流动资产合计": "total_current_assets",
    "长期股权投资": "long_term_equity_investment",
    "投资性房地产": "investment_property",
    "固定资产原值": "gross_ppe",
    "累计折旧": "accumulated_depreciation",
    "固定资产": "net_ppe",
    "固定资产净额": "net_ppe",
    "在建工程": "construction_in_progress",
    "无形资产": "intangible_assets",
    "商誉": "goodwill",
    "递延所得税资产": "deferred_tax_assets",
    "其他非流动资产": "other_non_current_assets",
    "非流动资产合计": "total_non_current_assets",
    "资产总计": "total_assets",
    # 资产负债表 - 负债
    "短期借款": "short_term_debt",
    "应付票据及应付账款": "notes_and_accounts_payable",
    "应付账款": "accounts_payable",
    "合同负债": "contract_liabilities",
    "应付职工薪酬": "employee_benefits_payable",
    "应交税费": "taxes_payable",
    "其他流动负债": "other_current_liab",
    "流动负债合计": "total_current_liab",
    "长期借款": "long_term_debt",
    "应付债券": "bonds_payable",
    "递延所得税负债": "deferred_tax_liabilities",
    "其他非流动负债": "other_non_current_liab",
    "非流动负债合计": "total_non_current_liab",
    "负债合计": "total_liabilities",
    # 资产负债表 - 权益
    "实收资本（或股本）": "paid_in_capital",
    "实收资本(或股本)": "paid_in_capital",
    "股本": "paid_in_capital",
    "资本公积": "capital_surplus",
    "未分配利润": "retained_earnings",
    "减:库存股": "treasury_stock",
    "减：库存股": "treasury_stock",
    "归属于母公司所有者权益合计": "equity_to_parent",
    "归属于母公司股东权益合计": "equity_to_parent",
    "少数股东权益": "minority_equity",
    "所有者权益合计": "total_equity",
    "所有者权益(或股东权益)合计": "total_equity",
    # 现金流量表
    "销售商品、提供劳务收到的现金": "cash_from_customers",
    "支付给职工以及为职工支付的现金": "cash_paid_to_employees",
    "支付的各项税费": "taxes_paid",
    "经营活动产生的现金流量净额": "operating_cashflow",
    "购建固定资产、无形资产和其他长期资产支付的现金": "capex",
    "投资所支付的现金": "investment_purchased",
    "收回投资所收到的现金": "investment_recovered",
    "投资活动产生的现金流量净额": "investing_cashflow",
    "取得借款收到的现金": "proceeds_from_borrowings",
    "偿还债务支付的现金": "repayment_of_debt",
    "分配股利、利润或偿付利息支付的现金": "dividends_paid",
    "筹资活动产生的现金流量净额": "financing_cashflow",
    "汇率变动对现金及现金等价物的影响": "fx_effect_on_cash",
    "现金及现金等价物净增加额": "net_change_in_cash",
    "期初现金及现金等价物余额": "begin_cash",
    "期末现金及现金等价物余额": "end_cash",
}

# US_COL_MAP: yfinance Title Case → financials_us snake_case
# 基础规则：`str.lower().replace(' ', '_')`；这里只列手工修正项（字段名特殊、或需合并同义）。
# fetch_financials_us 先查 map，未命中则套用基础规则。
US_COL_MAP: dict[str, str] = {
    "Tax Provision": "tax_provision",
    "Net Income Common Stockholders": "net_income_common_stockholders",
    "Net Income From Continuing Operations": "net_income_from_continuing_operations",
    "Net Income From Continuing Operation Net Minority Interest": "net_income_from_continuing_operations",
    "Total Revenue": "total_revenue",
    "Operating Revenue": "operating_revenue",
    "Cost Of Revenue": "cost_of_revenue",
    "Gross Profit": "gross_profit",
    "Research And Development": "research_and_development",
    "Selling General And Administration": "selling_general_and_administration",
    "Operating Expense": "operating_expense",
    "Operating Income": "operating_income",
    "EBIT": "ebit",
    "EBITDA": "ebitda",
    "Interest Income": "interest_income",
    "Interest Expense": "interest_expense",
    "Net Interest Income": "net_interest_income",
    "Pretax Income": "pretax_income",
    "Net Income": "net_income",
    "Basic EPS": "basic_eps",
    "Diluted EPS": "diluted_eps",
    "Basic Average Shares": "basic_average_shares",
    "Diluted Average Shares": "diluted_average_shares",
    "Normalized Income": "normalized_income",
    "Normalized EBITDA": "normalized_ebitda",
    "Reconciled Depreciation": "reconciled_depreciation",
    "Stock Based Compensation": "stock_based_compensation",
    # 资产负债表
    "Cash And Cash Equivalents": "cash_and_cash_equivalents",
    "Accounts Receivable": "accounts_receivable",
    "Inventory": "inventory",
    "Current Assets": "current_assets",
    "Net PPE": "net_ppe",
    "Gross PPE": "gross_ppe",
    "Accumulated Depreciation": "accumulated_depreciation",
    "Goodwill": "goodwill",
    "Goodwill And Other Intangible Assets": "goodwill_and_intangible_assets",
    "Other Intangible Assets": "goodwill_and_intangible_assets",
    "Deferred Tax Assets": "deferred_tax_assets",
    "Total Non Current Assets": "total_non_current_assets",
    "Total Assets": "total_assets",
    "Accounts Payable": "accounts_payable",
    "Current Debt": "current_debt",
    "Current Liabilities": "current_liabilities",
    "Long Term Debt": "long_term_debt",
    "Total Liabilities Net Minority Interest": "total_liabilities_net_minority_interest",
    "Retained Earnings": "retained_earnings",
    "Stockholders Equity": "stockholders_equity",
    "Total Equity Gross Minority Interest": "total_equity",
    "Total Debt": "total_debt",
    "Net Debt": "net_debt",
    "Working Capital": "working_capital",
    "Capital Lease Obligations": "capital_lease_obligations",
    "Common Stock": "common_stock",
    "Treasury Shares Number": "treasury_shares_number",
    # 现金流量表
    "Operating Cash Flow": "operating_cash_flow",
    "Investing Cash Flow": "investing_cash_flow",
    "Financing Cash Flow": "financing_cash_flow",
    "Capital Expenditure": "capital_expenditure",
    "Free Cash Flow": "free_cash_flow",
    "Depreciation And Amortization": "depreciation_and_amortization",
    "Change In Working Capital": "change_in_working_capital",
    "Changes In Cash": "changes_in_cash",
    "End Cash Position": "end_cash_position",
    "Beginning Cash Position": "begin_cash_position",
    "Issuance Of Debt": "issuance_of_debt",
    "Repayment Of Debt": "repayment_of_debt",
    "Repurchase Of Capital Stock": "repurchase_of_capital_stock",
    "Cash Dividends Paid": "cash_dividends_paid",
    "Deferred Income Tax": "deferred_income_tax",
    "Other Non Cash Items": "other_non_cash_items",
}


def us_col_to_snake(raw: str) -> str:
    """yfinance Title Case 列名 → snake_case。先查 US_COL_MAP，否则套用基础规则。"""
    if raw in US_COL_MAP:
        return US_COL_MAP[raw]
    return raw.lower().replace(" ", "_").replace("-", "_")
```

- [ ] **Step 3: 运行现有 config 测试确认没漏引用**

Run: `pytest tests/test_config_dimensions.py -v`
Expected: 旧断言 FAIL（`INCOME_STATEMENT_LINES` 等已删）——这是预期，Task 12 会清理。先让其他依赖该 config 的测试跑起来。

Run: `python -c "from app.config import CN_COL_MAP, US_COL_MAP, us_col_to_snake; print(len(CN_COL_MAP), len(US_COL_MAP), us_col_to_snake('Free Cash Flow'))"`
Expected: `~100 ~60 free_cash_flow`

- [ ] **Step 4: Commit**

```bash
git add app/config.py
git commit -m "config(financials): add CN_COL_MAP + US_COL_MAP, drop old line-item tuples"
```

---

## Task 2: 写 `test_financials_io.py` 新测试（TDD 起步）

**Files:**
- Create: `tests/test_financials_io.py`（覆盖写旧文件）
- Delete: `tests/test_financials_extended.py`（测的是旧 alias map）

新文件测试：schema 创建、CN upsert、US upsert、`recompute_ratios(conn, ticker, market)` 按 market 读对应表。

- [ ] **Step 1: 写完整的新 `tests/test_financials_io.py`**

```python
"""Tests for app.io.financials (two-table schema)."""
from pathlib import Path

import pytest

from app.io import financials as fin


def _cn_sample_row(period: str = "2024A", **overrides) -> dict:
    row = {
        "ticker": "600519",
        "report_date": "2024-12-31",
        "period": period,
        "period_type": "annual",
        "currency": "CNY",
        "total_revenue": 170_900_000_000.0,
        "operating_revenue": 170_900_000_000.0,
        "cost_of_revenue": 13_400_000_000.0,
        "operating_income": 107_800_000_000.0,
        "net_income": 86_200_000_000.0,
        "total_assets": 281_000_000_000.0,
        "total_equity": 234_000_000_000.0,
        "total_current_assets": 196_000_000_000.0,
        "total_current_liab": 46_000_000_000.0,
        "accounts_receivable": 120_000_000.0,
        "inventory": 46_400_000_000.0,
        "accounts_payable": 2_100_000_000.0,
        "short_term_debt": 0.0,
        "long_term_debt": 0.0,
        "interest_expense": 0.0,
        "operating_cashflow": 96_600_000_000.0,
        "capex": 3_400_000_000.0,
        "source": "akshare",
    }
    row.update(overrides)
    return row


def _us_sample_row(period: str = "2024A", **overrides) -> dict:
    row = {
        "ticker": "HIMS",
        "report_date": "2024-12-31",
        "period": period,
        "period_type": "annual",
        "currency": "USD",
        "total_revenue": 1_480_000_000.0,
        "cost_of_revenue": 310_000_000.0,
        "gross_profit": 1_170_000_000.0,
        "operating_income": 70_000_000_000.0 / 1000,  # 70M
        "ebit": 70_000_000.0,
        "net_income": 126_000_000.0,
        "total_assets": 650_000_000.0,
        "total_equity": 410_000_000.0,
        "current_assets": 350_000_000.0,
        "current_liabilities": 150_000_000.0,
        "accounts_receivable": 12_000_000.0,
        "inventory": 85_000_000.0,
        "accounts_payable": 40_000_000.0,
        "total_debt": 15_000_000.0,
        "interest_expense": 2_000_000.0,
        "operating_cash_flow": 210_000_000.0,
        "capital_expenditure": -40_000_000.0,
        "free_cash_flow": 170_000_000.0,
        "source": "yfinance",
    }
    row.update(overrides)
    return row


# ---------- schema ----------

def test_init_creates_both_tables(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "financials_cn" in tables
        assert "financials_us" in tables
        assert "ratios" in tables
        # legacy `financials` table no longer created
        assert "financials" not in tables
    finally:
        conn.close()


def test_cn_schema_has_key_columns(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(financials_cn)").fetchall()}
        for c in ("ticker", "period", "period_type", "report_date",
                  "total_revenue", "operating_revenue", "operating_income",
                  "net_income", "total_assets", "total_equity",
                  "operating_cashflow", "capex", "goodwill",
                  "short_term_debt", "long_term_debt"):
            assert c in cols, f"financials_cn missing {c}"
    finally:
        conn.close()


def test_us_schema_has_key_columns(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(financials_us)").fetchall()}
        for c in ("ticker", "period", "period_type",
                  "total_revenue", "gross_profit", "operating_income",
                  "ebit", "ebitda", "net_income",
                  "total_assets", "total_equity", "total_debt",
                  "current_assets", "current_liabilities",
                  "operating_cash_flow", "capital_expenditure", "free_cash_flow"):
            assert c in cols, f"financials_us missing {c}"
    finally:
        conn.close()


# ---------- upsert ----------

def test_upsert_cn_rountrip(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        fin.upsert_financials_cn(conn, [_cn_sample_row("2024A"), _cn_sample_row("2023A")])
        rows = fin.list_financials_cn(conn, "600519")
        assert [r["period"] for r in rows] == ["2024A", "2023A"]
        assert rows[0]["net_income"] == 86_200_000_000.0
    finally:
        conn.close()


def test_upsert_us_roundtrip(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        fin.upsert_financials_us(conn, [_us_sample_row("2024A"), _us_sample_row("2023A")])
        rows = fin.list_financials_us(conn, "HIMS")
        assert [r["period"] for r in rows] == ["2024A", "2023A"]
        assert rows[0]["free_cash_flow"] == 170_000_000.0
    finally:
        conn.close()


def test_upsert_cn_overwrites_on_conflict(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        fin.upsert_financials_cn(conn, [_cn_sample_row("2024A", net_income=1.0)])
        fin.upsert_financials_cn(conn, [_cn_sample_row("2024A", net_income=2.0)])
        rows = fin.list_financials_cn(conn, "600519")
        assert len(rows) == 1
        assert rows[0]["net_income"] == 2.0
    finally:
        conn.close()


# ---------- ratios (market-aware) ----------

def test_recompute_ratios_cn_reads_from_cn_table(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        fin.upsert_financials_cn(conn, [_cn_sample_row("2024A")])
        fin.recompute_ratios(conn, "600519", market="SSE")
        r = conn.execute("SELECT * FROM ratios WHERE ticker='600519' AND period='2024A'").fetchone()
        assert r is not None
        # net_margin = 86.2B / 170.9B ≈ 0.504
        assert r["net_margin"] == pytest.approx(86.2e9 / 170.9e9, abs=1e-3)
        # current_ratio = 196B / 46B ≈ 4.26
        assert r["current_ratio"] == pytest.approx(196e9 / 46e9, abs=1e-2)
        # debt_to_equity = 0 / 234B = 0
        assert r["debt_to_equity"] == 0.0
        # fcf = ocf - capex = 96.6B - 3.4B = 93.2B
        assert r["fcf"] == pytest.approx(96.6e9 - 3.4e9, rel=1e-6)
    finally:
        conn.close()


def test_recompute_ratios_us_reads_from_us_table(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        fin.upsert_financials_us(conn, [_us_sample_row("2024A")])
        fin.recompute_ratios(conn, "HIMS", market="US")
        r = conn.execute("SELECT * FROM ratios WHERE ticker='HIMS' AND period='2024A'").fetchone()
        assert r is not None
        # gross_margin = 1170 / 1480 ≈ 0.79
        assert r["gross_margin"] == pytest.approx(1170 / 1480, abs=1e-3)
        # D/E = 15M / 410M
        assert r["debt_to_equity"] == pytest.approx(15 / 410, abs=1e-3)
        # FCF comes from stored free_cash_flow column when present
        assert r["fcf"] == 170_000_000.0
    finally:
        conn.close()


def test_recompute_ratios_handles_nulls(tmp_path: Path):
    """Missing inputs → NULL output (NULLIF + COALESCE guard against div/0)."""
    conn = fin.connect(base=tmp_path)
    try:
        fin.upsert_financials_cn(conn, [_cn_sample_row(
            "2024A",
            total_equity=0.0,         # triggers NULLIF → NULL roe
            cost_of_revenue=0.0,      # triggers NULLIF → NULL days_inventory
        )])
        fin.recompute_ratios(conn, "600519", market="SSE")
        r = conn.execute("SELECT roe, days_inventory FROM ratios WHERE ticker='600519'").fetchone()
        assert r["roe"] is None
        assert r["days_inventory"] is None
    finally:
        conn.close()


def test_recompute_ratios_rejects_unknown_market(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        with pytest.raises(ValueError) as exc:
            fin.recompute_ratios(conn, "FOO", market="MOON")
        assert "market" in str(exc.value).lower()
    finally:
        conn.close()


# ---------- queries ----------

def test_list_periods_for_page_newest_first(tmp_path: Path):
    """Page needs one merged row per period with ratios joined; newest first."""
    conn = fin.connect(base=tmp_path)
    try:
        fin.upsert_financials_cn(conn, [
            _cn_sample_row("2024A"),
            _cn_sample_row("2024Q3", period_type="quarterly"),
            _cn_sample_row("2023A"),
        ])
        fin.recompute_ratios(conn, "600519", market="SSE")
        merged = fin.list_periods_with_ratios(conn, "600519", market="SSE")
        assert [r["period"] for r in merged] == ["2024A", "2024Q3", "2023A"]
        assert "net_margin" in merged[0]
        assert "operating_income" in merged[0]
    finally:
        conn.close()
```

- [ ] **Step 2: 删掉 `tests/test_financials_extended.py`**

```bash
git rm tests/test_financials_extended.py
```

- [ ] **Step 3: 运行测试确认全部 FAIL**

Run: `pytest tests/test_financials_io.py -v --no-header`
Expected: 所有测试都 FAIL（`upsert_financials_cn` 等函数未定义）——预期状态，Task 3 实现。

- [ ] **Step 4: Commit**

```bash
git add tests/test_financials_io.py tests/test_financials_extended.py
git commit -m "test(financials): rewrite for two-table schema (expect RED)"
```

---

## Task 3: 重写 `app/io/financials.py` —— 两表 schema + market-aware ratios

**Files:**
- Modify: `app/io/financials.py`（完全重写）

- [ ] **Step 1: 写新 `app/io/financials.py`**

```python
"""Financials storage (A-share + US two-table wide schema).

Two independent wide tables (`financials_cn`, `financials_us`) backed by API
sources (akshare Sina / yfinance). Shared-concept columns use the same
snake_case names so `recompute_ratios` can reuse the same SQL skeleton
with only column-name variations between markets.

No LLM calls here. Writers are `scripts/fetch_financials_cn.py` and
`scripts/fetch_financials_us.py`.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Iterable

from app import config as cfg

PERIOD_RE = re.compile(r"^(\d{4})(Q[1-4]|A)$")
_VALID_PERIOD_TYPES = ("annual", "quarterly")

# ---------- Schema -----------------------------------------------------------

# Columns in financials_cn (order preserved for DDL + upsert). Must stay in
# sync with the SQL in _CN_SCHEMA below and with CN_COL_MAP snake_case values.
CN_COLUMNS: tuple[str, ...] = (
    "report_date", "period_type", "is_audited", "announced_date", "currency",
    # 利润表
    "total_revenue", "operating_revenue", "total_operating_cost", "cost_of_revenue",
    "rd_expense", "selling_expense", "admin_expense", "finance_expense",
    "interest_expense", "interest_income", "investment_income",
    "fair_value_change_income", "fx_gain", "other_income",
    "asset_impairment_loss", "credit_impairment_loss",
    "operating_income", "non_operating_income", "non_operating_expense",
    "pretax_income", "income_tax",
    "net_income", "net_income_to_parent", "minority_interest_income",
    "other_comprehensive_income", "total_comprehensive_income",
    "eps_basic", "eps_diluted",
    "premium_earned", "commission_income", "commission_expense",
    # 资产负债表
    "cash_and_equivalents", "trading_financial_assets",
    "notes_and_accounts_receivable", "accounts_receivable",
    "prepayments", "other_receivables", "inventory", "other_current_assets",
    "total_current_assets",
    "long_term_equity_investment", "investment_property",
    "gross_ppe", "accumulated_depreciation", "net_ppe",
    "construction_in_progress", "intangible_assets", "goodwill",
    "deferred_tax_assets", "other_non_current_assets",
    "total_non_current_assets", "total_assets",
    "short_term_debt", "notes_and_accounts_payable", "accounts_payable",
    "contract_liabilities", "employee_benefits_payable", "taxes_payable",
    "other_current_liab", "total_current_liab",
    "long_term_debt", "bonds_payable", "deferred_tax_liabilities",
    "other_non_current_liab", "total_non_current_liab", "total_liabilities",
    "paid_in_capital", "capital_surplus", "retained_earnings",
    "treasury_stock", "other_comprehensive_equity",
    "equity_to_parent", "minority_equity", "total_equity",
    # 现金流量表
    "cash_from_customers", "cash_paid_to_employees", "taxes_paid",
    "operating_cashflow",
    "capex", "investment_purchased", "investment_recovered", "investing_cashflow",
    "proceeds_from_borrowings", "repayment_of_debt", "dividends_paid",
    "financing_cashflow",
    "fx_effect_on_cash", "net_change_in_cash", "begin_cash", "end_cash",
    "source",
)

US_COLUMNS: tuple[str, ...] = (
    "report_date", "period_type", "currency",
    # 利润表
    "total_revenue", "operating_revenue", "cost_of_revenue", "gross_profit",
    "research_and_development", "selling_general_and_administration",
    "operating_expense", "operating_income", "ebit", "ebitda",
    "interest_income", "interest_expense", "net_interest_income",
    "pretax_income", "tax_provision",
    "net_income", "net_income_common_stockholders",
    "basic_eps", "diluted_eps", "basic_average_shares", "diluted_average_shares",
    "normalized_income", "normalized_ebitda", "reconciled_depreciation",
    "stock_based_compensation",
    # 资产负债表
    "cash_and_cash_equivalents", "accounts_receivable", "inventory",
    "current_assets", "net_ppe", "gross_ppe", "accumulated_depreciation",
    "goodwill", "goodwill_and_intangible_assets", "deferred_tax_assets",
    "total_non_current_assets", "total_assets",
    "accounts_payable", "current_debt", "current_liabilities",
    "long_term_debt", "total_liabilities_net_minority_interest",
    "retained_earnings", "stockholders_equity", "total_equity",
    "total_debt", "net_debt", "working_capital",
    "capital_lease_obligations", "common_stock", "treasury_shares_number",
    # 现金流量表
    "operating_cash_flow", "investing_cash_flow", "financing_cash_flow",
    "capital_expenditure", "free_cash_flow",
    "depreciation_and_amortization", "change_in_working_capital",
    "changes_in_cash", "end_cash_position", "begin_cash_position",
    "issuance_of_debt", "repayment_of_debt", "repurchase_of_capital_stock",
    "cash_dividends_paid", "net_income_from_continuing_operations",
    "deferred_income_tax", "other_non_cash_items",
    "source",
)


_RATIOS_SCHEMA = """
CREATE TABLE IF NOT EXISTS ratios (
    ticker TEXT NOT NULL,
    period TEXT NOT NULL,
    gross_margin REAL,
    operating_margin REAL,
    net_margin REAL,
    roe REAL,
    roa REAL,
    asset_turnover REAL,
    equity_multiplier REAL,
    debt_to_equity REAL,
    fcf REAL,
    fcf_margin REAL,
    ocf_quality REAL,
    interest_coverage REAL,
    current_ratio REAL,
    quick_ratio REAL,
    days_inventory REAL,
    days_receivable REAL,
    days_payable REAL,
    cash_conversion_cycle REAL,
    PRIMARY KEY (ticker, period)
);
"""

_COMPANIES_SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    ticker TEXT PRIMARY KEY,
    market TEXT,
    name TEXT,
    industry_slugs TEXT,
    listed_date DATE,
    currency TEXT
);
"""

_PRICES_SCHEMA = """
CREATE TABLE IF NOT EXISTS price_triggers (
    ticker TEXT NOT NULL,
    trigger_price REAL NOT NULL,
    action TEXT NOT NULL,
    v0_snapshot_path TEXT,
    created_at DATE,
    triggered_at DATE
);
CREATE TABLE IF NOT EXISTS benchmark (
    date DATE NOT NULL, symbol TEXT NOT NULL, close REAL,
    PRIMARY KEY (date, symbol)
);
CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT NOT NULL, date DATE NOT NULL, close REAL NOT NULL,
    PRIMARY KEY (ticker, date)
);
CREATE TABLE IF NOT EXISTS quotes_daily (
    ticker TEXT NOT NULL, date TEXT NOT NULL, market TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL NOT NULL,
    volume INTEGER, amount REAL, turnover_rate REAL, volume_ratio_5d REAL,
    pe_ttm REAL, pe_static REAL, pe_forward REAL,
    pb REAL, ps REAL, peg REAL, dividend_yield REAL,
    market_cap REAL, float_market_cap REAL,
    shares_outstanding REAL, float_shares REAL,
    high_52w REAL, low_52w REAL, source TEXT, fetched_at TEXT,
    PRIMARY KEY (ticker, date)
);
CREATE TABLE IF NOT EXISTS quotes_fetch_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL, market TEXT NOT NULL,
    attempted_at TEXT NOT NULL, source TEXT NOT NULL,
    phase TEXT NOT NULL, error TEXT NOT NULL, resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_fetch_errors_unresolved
    ON quotes_fetch_errors(ticker, resolved_at) WHERE resolved_at IS NULL;
"""


def _cn_table_ddl() -> str:
    cols_sql = ",\n    ".join(f"{c} {'TEXT' if c in ('report_date','period_type','announced_date','currency','source') else ('INTEGER' if c == 'is_audited' else 'REAL')}" for c in CN_COLUMNS)
    return f"""
CREATE TABLE IF NOT EXISTS financials_cn (
    ticker TEXT NOT NULL,
    period TEXT NOT NULL,
    {cols_sql},
    PRIMARY KEY (ticker, period)
);
"""


def _us_table_ddl() -> str:
    cols_sql = ",\n    ".join(f"{c} {'TEXT' if c in ('report_date','period_type','currency','source') else 'REAL'}" for c in US_COLUMNS)
    return f"""
CREATE TABLE IF NOT EXISTS financials_us (
    ticker TEXT NOT NULL,
    period TEXT NOT NULL,
    {cols_sql},
    PRIMARY KEY (ticker, period)
);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    """Create all tables if missing. Old `financials` table is intentionally
    NOT recreated — Task 12 cleanup removes it from existing DBs."""
    conn.executescript(
        _COMPANIES_SCHEMA
        + _cn_table_ddl()
        + _us_table_ddl()
        + _RATIOS_SCHEMA
        + _PRICES_SCHEMA
    )
    # ALTER ADD COLUMN for forward compat: any CN_COLUMNS / US_COLUMNS entry
    # missing from a pre-existing table gets added.
    for table, cols in (("financials_cn", CN_COLUMNS), ("financials_us", US_COLUMNS)):
        existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for col in cols:
            if col not in existing:
                coltype = "TEXT" if col in ("report_date", "period_type", "announced_date", "currency", "source") else ("INTEGER" if col == "is_audited" else "REAL")
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
    conn.commit()


def _db_path(base: Path | None) -> Path:
    if base is None:
        return cfg.FINANCIALS_DB
    return Path(base) / "data" / "financials.db"


def connect(base: Path | None = None) -> sqlite3.Connection:
    path = _db_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


# ---------- companies (unchanged from old) ----------------------------------


def upsert_company(conn: sqlite3.Connection, meta: dict) -> None:
    industry = meta.get("industry_slugs") or meta.get("industry_primary")
    if isinstance(industry, (list, tuple)):
        industry = ",".join(str(s) for s in industry if s)
    conn.execute(
        """
        INSERT INTO companies(ticker, market, name, industry_slugs, listed_date, currency)
        VALUES (:ticker, :market, :name, :industry_slugs, :listed_date, :currency)
        ON CONFLICT(ticker) DO UPDATE SET
            market = excluded.market, name = excluded.name,
            industry_slugs = excluded.industry_slugs,
            listed_date = excluded.listed_date, currency = excluded.currency
        """,
        {
            "ticker": (meta.get("ticker") or "").upper(),
            "market": meta.get("market"),
            "name": meta.get("name"),
            "industry_slugs": industry,
            "listed_date": str(meta.get("listed_date")) if meta.get("listed_date") else None,
            "currency": meta.get("currency"),
        },
    )
    conn.commit()


# ---------- upsert -----------------------------------------------------------


def _validate_period_row(row: dict) -> None:
    p = row.get("period") or ""
    if not PERIOD_RE.match(p):
        raise ValueError(f"invalid period {p!r} (expected YYYYQ[1-4] or YYYYA)")
    pt = (row.get("period_type") or "").lower()
    if pt not in _VALID_PERIOD_TYPES:
        raise ValueError(f"invalid period_type {pt!r}")
    if p.endswith("A") and pt != "annual":
        raise ValueError(f"period {p} ↔ period_type {pt} mismatch")
    if "Q" in p and pt != "quarterly":
        raise ValueError(f"period {p} ↔ period_type {pt} mismatch")


def _upsert(conn: sqlite3.Connection, table: str, cols: tuple[str, ...], rows: Iterable[dict]) -> int:
    """Generic upsert. `rows` carry `ticker`, `period` + any subset of `cols`."""
    n = 0
    for row in rows:
        _validate_period_row(row)
        ticker = (row.get("ticker") or "").strip().upper()
        if not ticker:
            raise ValueError("row missing ticker")
        params = {"ticker": ticker, "period": row["period"]}
        for c in cols:
            params[c] = row.get(c)
        col_list = ", ".join(cols)
        ph_list = ", ".join(f":{c}" for c in cols)
        set_list = ", ".join(f"{c} = excluded.{c}" for c in cols)
        conn.execute(
            f"""
            INSERT INTO {table} (ticker, period, {col_list})
            VALUES (:ticker, :period, {ph_list})
            ON CONFLICT(ticker, period) DO UPDATE SET {set_list}
            """,
            params,
        )
        n += 1
    conn.commit()
    return n


def upsert_financials_cn(conn: sqlite3.Connection, rows: Iterable[dict]) -> int:
    return _upsert(conn, "financials_cn", CN_COLUMNS, rows)


def upsert_financials_us(conn: sqlite3.Connection, rows: Iterable[dict]) -> int:
    return _upsert(conn, "financials_us", US_COLUMNS, rows)


# ---------- ratios -----------------------------------------------------------

_CN_MARKETS = {"SSE", "SZSE", "BSE"}


_CN_RATIOS_SQL = """
INSERT INTO ratios (ticker, period,
    gross_margin, operating_margin, net_margin,
    roe, roa, asset_turnover, equity_multiplier, debt_to_equity,
    fcf, fcf_margin, ocf_quality, interest_coverage,
    current_ratio, quick_ratio,
    days_inventory, days_receivable, days_payable, cash_conversion_cycle)
SELECT
    ticker, period,
    (operating_revenue - cost_of_revenue) / NULLIF(operating_revenue, 0),
    operating_income / NULLIF(operating_revenue, 0),
    net_income / NULLIF(operating_revenue, 0),
    net_income / NULLIF(total_equity, 0),
    net_income / NULLIF(total_assets, 0),
    operating_revenue / NULLIF(total_assets, 0),
    total_assets / NULLIF(total_equity, 0),
    (COALESCE(short_term_debt, 0) + COALESCE(long_term_debt, 0)) / NULLIF(total_equity, 0),
    operating_cashflow - COALESCE(capex, 0),
    (operating_cashflow - COALESCE(capex, 0)) / NULLIF(operating_revenue, 0),
    operating_cashflow / NULLIF(net_income, 0),
    operating_income / NULLIF(interest_expense, 0),
    total_current_assets / NULLIF(total_current_liab, 0),
    (total_current_assets - COALESCE(inventory, 0)) / NULLIF(total_current_liab, 0),
    inventory * 365.0 / NULLIF(cost_of_revenue, 0),
    accounts_receivable * 365.0 / NULLIF(operating_revenue, 0),
    accounts_payable * 365.0 / NULLIF(cost_of_revenue, 0),
    (inventory * 365.0 / NULLIF(cost_of_revenue, 0))
      + (accounts_receivable * 365.0 / NULLIF(operating_revenue, 0))
      - (accounts_payable * 365.0 / NULLIF(cost_of_revenue, 0))
FROM financials_cn
WHERE ticker = ?
"""

_US_RATIOS_SQL = """
INSERT INTO ratios (ticker, period,
    gross_margin, operating_margin, net_margin,
    roe, roa, asset_turnover, equity_multiplier, debt_to_equity,
    fcf, fcf_margin, ocf_quality, interest_coverage,
    current_ratio, quick_ratio,
    days_inventory, days_receivable, days_payable, cash_conversion_cycle)
SELECT
    ticker, period,
    gross_profit / NULLIF(total_revenue, 0),
    operating_income / NULLIF(total_revenue, 0),
    net_income / NULLIF(total_revenue, 0),
    net_income / NULLIF(total_equity, 0),
    net_income / NULLIF(total_assets, 0),
    total_revenue / NULLIF(total_assets, 0),
    total_assets / NULLIF(total_equity, 0),
    COALESCE(total_debt, 0) / NULLIF(total_equity, 0),
    COALESCE(free_cash_flow, operating_cash_flow + COALESCE(capital_expenditure, 0)),
    COALESCE(free_cash_flow, operating_cash_flow + COALESCE(capital_expenditure, 0))
        / NULLIF(total_revenue, 0),
    operating_cash_flow / NULLIF(net_income, 0),
    COALESCE(ebit, operating_income) / NULLIF(interest_expense, 0),
    current_assets / NULLIF(current_liabilities, 0),
    (current_assets - COALESCE(inventory, 0)) / NULLIF(current_liabilities, 0),
    inventory * 365.0 / NULLIF(cost_of_revenue, 0),
    accounts_receivable * 365.0 / NULLIF(total_revenue, 0),
    accounts_payable * 365.0 / NULLIF(cost_of_revenue, 0),
    (inventory * 365.0 / NULLIF(cost_of_revenue, 0))
      + (accounts_receivable * 365.0 / NULLIF(total_revenue, 0))
      - (accounts_payable * 365.0 / NULLIF(cost_of_revenue, 0))
FROM financials_us
WHERE ticker = ?
"""


def recompute_ratios(conn: sqlite3.Connection, ticker: str, market: str) -> None:
    """Recompute ratios for a single ticker. `market` picks the source table:
    {SSE, SZSE, BSE} → financials_cn; US → financials_us.
    """
    ticker = (ticker or "").strip().upper()
    if not ticker:
        raise ValueError("ticker is empty")
    if market in _CN_MARKETS:
        sql = _CN_RATIOS_SQL
    elif market == "US":
        sql = _US_RATIOS_SQL
    else:
        raise ValueError(f"unsupported market {market!r}")
    conn.executescript(_RATIOS_SCHEMA)
    conn.execute("DELETE FROM ratios WHERE ticker = ?", (ticker,))
    conn.execute(sql, (ticker,))
    conn.commit()


# ---------- queries ---------------------------------------------------------


def _period_sort_key(period: str) -> tuple[int, int, int]:
    m = PERIOD_RE.match(period)
    if not m:
        return (0, 0, 0)
    year = int(m.group(1))
    tag = m.group(2)
    if tag == "A":
        return (year, 2, 5)
    return (year, 1, int(tag[1]))


def _sort_desc(rows: Iterable[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: _period_sort_key(r["period"]), reverse=True)


def list_financials_cn(conn: sqlite3.Connection, ticker: str) -> list[dict]:
    ticker = ticker.strip().upper()
    rows = conn.execute(
        f"SELECT ticker, period, {', '.join(CN_COLUMNS)} FROM financials_cn WHERE ticker = ?",
        (ticker,),
    ).fetchall()
    return _sort_desc(dict(r) for r in rows)


def list_financials_us(conn: sqlite3.Connection, ticker: str) -> list[dict]:
    ticker = ticker.strip().upper()
    rows = conn.execute(
        f"SELECT ticker, period, {', '.join(US_COLUMNS)} FROM financials_us WHERE ticker = ?",
        (ticker,),
    ).fetchall()
    return _sort_desc(dict(r) for r in rows)


def list_ratios(conn: sqlite3.Connection, ticker: str) -> list[dict]:
    ticker = ticker.strip().upper()
    rows = conn.execute(
        "SELECT * FROM ratios WHERE ticker = ?", (ticker,)
    ).fetchall()
    return _sort_desc(dict(r) for r in rows)


def list_periods_with_ratios(
    conn: sqlite3.Connection, ticker: str, market: str
) -> list[dict]:
    """Merged per-period rows (financials + ratios), newest first. Used by the
    financials page. Caller selects which table via `market`."""
    ticker = ticker.strip().upper()
    if market in _CN_MARKETS:
        fins = list_financials_cn(conn, ticker)
    elif market == "US":
        fins = list_financials_us(conn, ticker)
    else:
        raise ValueError(f"unsupported market {market!r}")
    rats = {r["period"]: dict(r) for r in list_ratios(conn, ticker)}
    out = []
    for row in fins:
        merged = {**row, **{k: v for k, v in rats.get(row["period"], {}).items() if k not in ("ticker", "period")}}
        out.append(merged)
    return _sort_desc(out)
```

- [ ] **Step 2: 跑测试看绿**

Run: `pytest tests/test_financials_io.py -v`
Expected: 全部 PASS。

- [ ] **Step 3: Commit**

```bash
git add app/io/financials.py
git commit -m "feat(financials): two-table schema + market-aware ratios"
```

---

## Task 4: `scripts/fetch_financials_cn.py` —— akshare → `financials_cn`

**Files:**
- Create: `scripts/fetch_financials_cn.py`
- Create: `tests/test_fetch_financials_cn.py`
- Create: `tests/fixtures/financials/akshare_income_sh600519.csv`（2 期样本）
- Create: `tests/fixtures/financials/akshare_balance_sh600519.csv`
- Create: `tests/fixtures/financials/akshare_cashflow_sh600519.csv`

- [ ] **Step 1: 写 fixture CSV（2 期 2024Q3 + 2024A）**

`tests/fixtures/financials/akshare_income_sh600519.csv`：
```csv
报告日,类型,营业总收入,营业收入,营业成本,营业利润,利润总额,所得税费用,净利润,归属于母公司股东的净利润,基本每股收益,稀释每股收益
2024-12-31,年报,170900000000,170900000000,13400000000,107800000000,110000000000,23800000000,86200000000,86200000000,68.6,68.6
2024-09-30,三季报,122200000000,122200000000,9700000000,75400000000,77000000000,17000000000,60000000000,60000000000,47.7,47.7
```

`tests/fixtures/financials/akshare_balance_sh600519.csv`：
```csv
报告日,类型,货币资金,应收账款,存货,流动资产合计,固定资产,商誉,资产总计,短期借款,应付账款,合同负债,流动负债合计,长期借款,负债合计,未分配利润,归属于母公司股东权益合计,所有者权益合计
2024-12-31,年报,180000000000,120000000,46400000000,196000000000,19000000000,0,281000000000,0,2100000000,18000000000,46000000000,0,47000000000,200000000000,234000000000,234000000000
2024-09-30,三季报,170000000000,100000000,45000000000,190000000000,18500000000,0,275000000000,0,2000000000,15000000000,43000000000,0,41000000000,195000000000,228000000000,228000000000
```

`tests/fixtures/financials/akshare_cashflow_sh600519.csv`：
```csv
报告日,类型,经营活动产生的现金流量净额,"购建固定资产、无形资产和其他长期资产支付的现金",投资活动产生的现金流量净额,筹资活动产生的现金流量净额,现金及现金等价物净增加额,期初现金及现金等价物余额,期末现金及现金等价物余额
2024-12-31,年报,96600000000,3400000000,-15000000000,-50000000000,31600000000,148000000000,179600000000,
2024-09-30,三季报,68000000000,2400000000,-10000000000,-35000000000,23000000000,148000000000,171000000000,
```

(cashflow 第一行结尾多一个逗号是为了 pandas 识别 trailing col；无害)

- [ ] **Step 2: 写 conftest fixture + `tests/test_fetch_financials_cn.py`**

在 `tests/conftest.py` 里复用或新增 `mock_akshare_financials` fixture（若已有 `mock_akshare` 则扩展它）。测试文件：

```python
"""Tests for scripts.fetch_financials_cn."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.io import financials as fin
from scripts import fetch_financials_cn as fc

FIX = Path(__file__).parent / "fixtures" / "financials"


@pytest.fixture
def mock_ak_reports(monkeypatch):
    """Replace akshare.stock_financial_report_sina with CSV fixtures."""
    income = pd.read_csv(FIX / "akshare_income_sh600519.csv")
    balance = pd.read_csv(FIX / "akshare_balance_sh600519.csv")
    cashflow = pd.read_csv(FIX / "akshare_cashflow_sh600519.csv")

    def _fake(stock: str, symbol: str):
        if symbol == "利润表":
            return income.copy()
        if symbol == "资产负债表":
            return balance.copy()
        if symbol == "现金流量表":
            return cashflow.copy()
        return pd.DataFrame()

    import akshare as ak
    monkeypatch.setattr(ak, "stock_financial_report_sina", _fake)
    return _fake


def test_derive_period_from_report_row():
    assert fc.derive_period("2024-12-31", "年报") == ("2024A", "annual")
    assert fc.derive_period("2024-12-31", "四季报") == ("2024Q4", "quarterly")
    assert fc.derive_period("2024-09-30", "三季报") == ("2024Q3", "quarterly")
    assert fc.derive_period("2024-06-30", "中报") == ("2024Q2", "quarterly")
    assert fc.derive_period("2024-03-31", "一季报") == ("2024Q1", "quarterly")


def test_sina_symbol_for_markets():
    assert fc.sina_symbol("600519", "SSE") == "sh600519"
    assert fc.sina_symbol("000001", "SZSE") == "sz000001"
    assert fc.sina_symbol("920118", "BSE") == "bj920118"
    with pytest.raises(ValueError):
        fc.sina_symbol("HIMS", "US")


def test_run_for_ticker_upserts_and_recomputes(tmp_path, mock_ak_reports):
    added = fc.run_for_ticker("600519", "SSE", base=tmp_path)
    assert added == 2  # 2024A + 2024Q3 merged
    conn = fin.connect(base=tmp_path)
    try:
        rows = fin.list_financials_cn(conn, "600519")
        assert [r["period"] for r in rows] == ["2024A", "2024Q3"]
        a = rows[0]
        assert a["net_income"] == 86_200_000_000.0
        assert a["goodwill"] == 0.0
        assert a["operating_cashflow"] == 96_600_000_000.0
        assert a["capex"] == 3_400_000_000.0
        # ratios should be there too
        r = conn.execute(
            "SELECT net_margin FROM ratios WHERE ticker='600519' AND period='2024A'"
        ).fetchone()
        assert r["net_margin"] == pytest.approx(86.2e9 / 170.9e9, abs=1e-3)
    finally:
        conn.close()


def test_unknown_chinese_column_logged_not_fatal(tmp_path, monkeypatch, caplog):
    import akshare as ak
    df = pd.DataFrame({
        "报告日": ["2024-12-31"], "类型": ["年报"],
        "营业总收入": [100.0],
        "未知字段XYZ": [42.0],
    })
    monkeypatch.setattr(
        ak, "stock_financial_report_sina",
        lambda stock, symbol: df.copy() if symbol == "利润表" else pd.DataFrame()
    )
    added = fc.run_for_ticker("600519", "SSE", base=tmp_path)
    assert added == 1
    # warning surfaced for unmapped column
    assert any("未知字段XYZ" in rec.message for rec in caplog.records)
```

- [ ] **Step 3: 跑测试，确认 FAIL（函数未定义）**

Run: `pytest tests/test_fetch_financials_cn.py -v`
Expected: ModuleNotFoundError or AttributeError（scripts.fetch_financials_cn 不存在）。

- [ ] **Step 4: 实现 `scripts/fetch_financials_cn.py`**

```python
"""Fetch CN A-share financials via akshare Sina → financials_cn."""
from __future__ import annotations

import argparse
import logging
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import akshare as ak
import pandas as pd

from app import config as cfg
from app.io import financials as fin

log = logging.getLogger("fetch_financials_cn")

_MARKET_PREFIX = {"SSE": "sh", "SZSE": "sz", "BSE": "bj"}
_PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
               "http_proxy", "https_proxy", "all_proxy")


@contextmanager
def _no_proxy():
    saved = {k: os.environ.pop(k, None) for k in _PROXY_KEYS}
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def sina_symbol(ticker: str, market: str) -> str:
    prefix = _MARKET_PREFIX.get(market)
    if not prefix:
        raise ValueError(f"fetch_financials_cn: unsupported market {market!r}")
    return f"{prefix}{ticker}"


def derive_period(report_date: str, report_type: str) -> tuple[str, str]:
    """报告日(YYYY-MM-DD) + 类型 → (period, period_type)."""
    d = report_date[:10]
    year = d[:4]
    mm = d[5:7]
    t = (report_type or "").strip()
    if mm == "12" and "年报" in t:
        return (f"{year}A", "annual")
    q = {"03": "Q1", "06": "Q2", "09": "Q3", "12": "Q4"}.get(mm)
    if not q:
        raise ValueError(f"unrecognized month in report_date {report_date!r}")
    return (f"{year}{q}", "quarterly")


def _df_to_rows(df: pd.DataFrame, ticker: str, market: str) -> dict[str, dict]:
    """Translate one statement DataFrame into period→row dict using CN_COL_MAP."""
    if df is None or df.empty:
        return {}
    if "报告日" not in df.columns:
        log.warning("DataFrame has no 报告日 column; skipping")
        return {}
    out: dict[str, dict] = {}
    for _, r in df.iterrows():
        rd = str(r["报告日"])[:10]
        rtype = str(r.get("类型", "")).strip()
        try:
            period, ptype = derive_period(rd, rtype)
        except ValueError as e:
            log.warning("skip row for %s: %s", ticker, e)
            continue
        row: dict[str, Any] = {
            "ticker": ticker,
            "period": period,
            "period_type": ptype,
            "report_date": rd,
            "source": "akshare",
        }
        for col, val in r.items():
            if col in ("报告日", "类型"):
                continue
            snake = cfg.CN_COL_MAP.get(col)
            if snake is None:
                log.warning("%s: unmapped CN column %r (value=%r)", ticker, col, val)
                continue
            if snake.startswith("_"):
                continue
            try:
                row[snake] = None if pd.isna(val) else float(val)
            except (TypeError, ValueError):
                row[snake] = None
        out[period] = row
    return out


def _merge_statements(
    income: pd.DataFrame, balance: pd.DataFrame, cashflow: pd.DataFrame,
    ticker: str, market: str,
) -> list[dict]:
    i = _df_to_rows(income, ticker, market)
    b = _df_to_rows(balance, ticker, market)
    c = _df_to_rows(cashflow, ticker, market)
    periods = sorted(set(i) | set(b) | set(c), reverse=True)
    merged = []
    for p in periods:
        row: dict[str, Any] = {}
        for src in (i.get(p, {}), b.get(p, {}), c.get(p, {})):
            row.update(src)
        # Need period at least
        if "period" in row and "ticker" in row:
            merged.append(row)
    return merged


def run_for_ticker(ticker: str, market: str, base: Path | None = None) -> int:
    """Fetch 3 statements from akshare Sina, upsert into financials_cn,
    recompute ratios. Returns # periods written."""
    symbol = sina_symbol(ticker, market)
    with _no_proxy():
        income = ak.stock_financial_report_sina(stock=symbol, symbol="利润表")
        balance = ak.stock_financial_report_sina(stock=symbol, symbol="资产负债表")
        cashflow = ak.stock_financial_report_sina(stock=symbol, symbol="现金流量表")
    rows = _merge_statements(income, balance, cashflow, ticker, market)
    if not rows:
        log.warning("%s: no statements returned", ticker)
        return 0
    conn = fin.connect(base=base)
    try:
        n = fin.upsert_financials_cn(conn, rows)
        fin.recompute_ratios(conn, ticker, market=market)
        log.info("%s: upserted %d periods (via %s)", ticker, n, symbol)
        return n
    finally:
        conn.close()


# ---- CLI --------------------------------------------------------------------


def _iter_companies(market_filter: str | None) -> list[tuple[str, str]]:
    """Read meta dir and yield (ticker, market) for CN markets."""
    out = []
    for f in cfg.COMPANIES_DIR.glob("*/_meta.yaml"):
        key = f.parent.name
        if "_" not in key:
            continue
        market, ticker = key.split("_", 1)
        if market not in _MARKET_PREFIX:
            continue
        if market_filter and market != market_filter:
            continue
        out.append((ticker, market))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fetch CN financials into financials_cn")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("key", nargs="?", help="e.g. SSE_600519")
    g.add_argument("--all", action="store_true")
    g.add_argument("--market", choices=("SSE", "SZSE", "BSE"))
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    targets: list[tuple[str, str]] = []
    if args.key:
        market, ticker = args.key.split("_", 1)
        targets = [(ticker, market)]
    elif args.all:
        targets = _iter_companies(None)
    elif args.market:
        targets = _iter_companies(args.market)

    fails = 0
    for t, m in targets:
        try:
            run_for_ticker(t, m)
        except Exception as e:
            log.error("%s_%s: %s: %s", m, t, type(e).__name__, e)
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: 跑测试确认 PASS**

Run: `pytest tests/test_fetch_financials_cn.py -v`
Expected: 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/fetch_financials_cn.py tests/test_fetch_financials_cn.py tests/fixtures/financials/
git commit -m "feat(fetch): akshare CN financials → financials_cn + ratios"
```

---

## Task 5: `scripts/fetch_financials_us.py` —— yfinance → `financials_us`

**Files:**
- Create: `scripts/fetch_financials_us.py`
- Create: `tests/test_fetch_financials_us.py`

- [ ] **Step 1: 写 `tests/test_fetch_financials_us.py`**

```python
"""Tests for scripts.fetch_financials_us. yfinance is monkeypatched —
we do NOT hit the network. DataFrame shape matches yfinance.Ticker.*_stmt."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.io import financials as fin
from scripts import fetch_financials_us as fu


class _FakeTicker:
    def __init__(self, income, balance, cashflow,
                 qincome=None, qbalance=None, qcashflow=None):
        self.income_stmt = income
        self.balance_sheet = balance
        self.cashflow = cashflow
        self.quarterly_income_stmt = qincome if qincome is not None else pd.DataFrame()
        self.quarterly_balance_sheet = qbalance if qbalance is not None else pd.DataFrame()
        self.quarterly_cashflow = qcashflow if qcashflow is not None else pd.DataFrame()


def _annual_frame():
    return pd.DataFrame(
        {
            pd.Timestamp("2024-12-31"): [1480e6, 310e6, 1170e6, 70e6, 70e6, 126e6, 210e6, -40e6, 170e6, 40e6, 410e6, 650e6, 15e6, 150e6, 350e6, 85e6, 12e6],
            pd.Timestamp("2023-12-31"): [870e6, 200e6, 670e6, 30e6, 30e6, 60e6, 115e6, -20e6, 95e6, 20e6, 280e6, 450e6, 5e6, 110e6, 220e6, 60e6, 8e6],
        },
        index=[
            "Total Revenue", "Cost Of Revenue", "Gross Profit", "Operating Income", "EBIT", "Net Income",
            "Operating Cash Flow", "Capital Expenditure", "Free Cash Flow",
            "Accounts Payable", "Stockholders Equity", "Total Assets", "Total Debt",
            "Current Liabilities", "Current Assets", "Inventory", "Accounts Receivable",
        ],
    )


def _quarterly_frame():
    return pd.DataFrame(
        {pd.Timestamp("2024-09-30"): [380e6, 80e6, 300e6, 20e6, 30e6]},
        index=["Total Revenue", "Cost Of Revenue", "Gross Profit", "Net Income", "Operating Cash Flow"],
    )


def test_period_from_timestamp_annual():
    assert fu.period_for_stmt(pd.Timestamp("2024-12-31"), period_type="annual") == "2024A"


def test_period_from_timestamp_quarterly():
    assert fu.period_for_stmt(pd.Timestamp("2024-03-31"), period_type="quarterly") == "2024Q1"
    assert fu.period_for_stmt(pd.Timestamp("2024-06-30"), period_type="quarterly") == "2024Q2"
    assert fu.period_for_stmt(pd.Timestamp("2024-09-30"), period_type="quarterly") == "2024Q3"
    assert fu.period_for_stmt(pd.Timestamp("2024-12-31"), period_type="quarterly") == "2024Q4"


def test_run_for_ticker_writes_annual_and_quarterly(tmp_path, monkeypatch):
    fake = _FakeTicker(
        income=_annual_frame(), balance=_annual_frame(), cashflow=_annual_frame(),
        qincome=_quarterly_frame(), qbalance=_quarterly_frame(), qcashflow=_quarterly_frame(),
    )
    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", lambda s: fake)

    n = fu.run_for_ticker("HIMS", "US", base=tmp_path)
    assert n >= 3  # 2 annuals + 1 quarterly

    conn = fin.connect(base=tmp_path)
    try:
        rows = fin.list_financials_us(conn, "HIMS")
        periods = [r["period"] for r in rows]
        assert "2024A" in periods
        assert "2023A" in periods
        assert "2024Q3" in periods
        a2024 = next(r for r in rows if r["period"] == "2024A")
        assert a2024["total_revenue"] == 1480e6
        assert a2024["gross_profit"] == 1170e6
        assert a2024["free_cash_flow"] == 170e6
        assert a2024["source"] == "yfinance"

        # ratio sanity
        r = conn.execute(
            "SELECT gross_margin FROM ratios WHERE ticker='HIMS' AND period='2024A'"
        ).fetchone()
        assert r["gross_margin"] == pytest.approx(1170 / 1480, abs=1e-3)
    finally:
        conn.close()


def test_unknown_us_label_uses_snake_fallback(tmp_path, monkeypatch):
    """A yfinance field not in US_COL_MAP becomes lower_snake via us_col_to_snake."""
    df = pd.DataFrame(
        {pd.Timestamp("2024-12-31"): [100.0]},
        index=["Total Revenue"],
    )
    # Inject a column yfinance sometimes emits: "Other Income Expense"
    df.loc["Other Income Expense"] = [5.0]
    fake = _FakeTicker(income=df, balance=pd.DataFrame(), cashflow=pd.DataFrame())
    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", lambda s: fake)

    n = fu.run_for_ticker("XYZ", "US", base=tmp_path)
    assert n == 1
    # unmapped fields are silently dropped because they aren't in US_COLUMNS;
    # this just verifies no crash.
```

- [ ] **Step 2: 跑测试确认 FAIL**

Run: `pytest tests/test_fetch_financials_us.py -v`
Expected: ModuleNotFoundError / AttributeError。

- [ ] **Step 3: 实现 `scripts/fetch_financials_us.py`**

```python
"""Fetch US financials via yfinance → financials_us.

yfinance.Ticker exposes:
  - income_stmt, balance_sheet, cashflow       (annual; 4 columns)
  - quarterly_income_stmt, quarterly_balance_sheet, quarterly_cashflow
Each DataFrame has financial-line names as index, pd.Timestamp columns.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from app import config as cfg
from app.io import financials as fin

log = logging.getLogger("fetch_financials_us")

# Only snake_case column names that actually exist in financials_us are written.
_US_COL_SET = set(fin.US_COLUMNS)


def period_for_stmt(ts: pd.Timestamp, period_type: str) -> str:
    mm = ts.month
    year = ts.year
    if period_type == "annual":
        return f"{year}A"
    q = {3: "Q1", 6: "Q2", 9: "Q3", 12: "Q4"}.get(mm)
    if not q:
        raise ValueError(f"unrecognized quarter month {mm}")
    return f"{year}{q}"


def _stmt_to_rows(
    df: pd.DataFrame, ticker: str, period_type: str
) -> dict[str, dict]:
    """DataFrame → {period: {snake_col: value}}. Index is Title Case labels."""
    if df is None or df.empty:
        return {}
    out: dict[str, dict] = {}
    for col_ts in df.columns:
        if not isinstance(col_ts, pd.Timestamp):
            continue
        period = period_for_stmt(col_ts, period_type)
        row: dict[str, Any] = {
            "ticker": ticker,
            "period": period,
            "period_type": period_type,
            "report_date": col_ts.date().isoformat(),
            "source": "yfinance",
        }
        for idx, val in df[col_ts].items():
            snake = cfg.us_col_to_snake(str(idx))
            if snake not in _US_COL_SET:
                continue
            try:
                row[snake] = None if pd.isna(val) else float(val)
            except (TypeError, ValueError):
                row[snake] = None
        out[period] = row
    return out


def _merge(
    income: pd.DataFrame, balance: pd.DataFrame, cashflow: pd.DataFrame,
    ticker: str, period_type: str,
) -> dict[str, dict]:
    i = _stmt_to_rows(income, ticker, period_type)
    b = _stmt_to_rows(balance, ticker, period_type)
    c = _stmt_to_rows(cashflow, ticker, period_type)
    periods = sorted(set(i) | set(b) | set(c), reverse=True)
    out = {}
    for p in periods:
        r: dict[str, Any] = {}
        for src in (i.get(p, {}), b.get(p, {}), c.get(p, {})):
            r.update(src)
        if "period" in r:
            out[p] = r
    return out


def run_for_ticker(ticker: str, market: str, base: Path | None = None) -> int:
    if market != "US":
        raise ValueError(f"fetch_financials_us only supports US, got {market!r}")
    t = yf.Ticker(ticker)
    annuals = _merge(t.income_stmt, t.balance_sheet, t.cashflow, ticker, "annual")
    quarters = _merge(
        t.quarterly_income_stmt, t.quarterly_balance_sheet, t.quarterly_cashflow,
        ticker, "quarterly",
    )
    rows = list(annuals.values()) + list(quarters.values())
    if not rows:
        log.warning("%s: yfinance returned no statements", ticker)
        return 0
    conn = fin.connect(base=base)
    try:
        n = fin.upsert_financials_us(conn, rows)
        fin.recompute_ratios(conn, ticker, market="US")
        log.info("%s: upserted %d periods", ticker, n)
        return n
    finally:
        conn.close()


def _iter_us_companies() -> list[str]:
    out = []
    for f in cfg.COMPANIES_DIR.glob("US_*/_meta.yaml"):
        key = f.parent.name
        if "_" in key:
            _, ticker = key.split("_", 1)
            out.append(ticker)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fetch US financials into financials_us")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("key", nargs="?", help="e.g. US_HIMS")
    g.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    targets: list[str]
    if args.key:
        _, t = args.key.split("_", 1)
        targets = [t]
    else:
        targets = _iter_us_companies()

    fails = 0
    for t in targets:
        try:
            run_for_ticker(t, "US")
        except Exception as e:
            log.error("US_%s: %s: %s", t, type(e).__name__, e)
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 跑测试确认 PASS**

Run: `pytest tests/test_fetch_financials_us.py -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_financials_us.py tests/test_fetch_financials_us.py
git commit -m "feat(fetch): yfinance US financials → financials_us + ratios"
```

---

## Task 6: 重写路由 `app/routes/financials.py` + 模板

**Files:**
- Modify: `app/routes/financials.py`
- Modify: `app/templates/companies/financials.html`

- [ ] **Step 1: 重写 `app/routes/financials.py`**

```python
"""Financials page + manual refresh.

GET  /companies/{key}/financials           → render page (all periods)
POST /companies/{key}/financials/refresh   → pull fresh from API, return JSON
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import company as company_io
from app.io import financials as fin_io
from scripts import fetch_financials_cn, fetch_financials_us

router = APIRouter(prefix="/companies/{key}/financials", tags=["financials"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


def _parse_key(key: str) -> tuple[str, str]:
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    return market, ticker


@router.get("")
def page(request: Request, key: str):
    market, ticker = _parse_key(key)
    meta = company_io.read_meta(ticker, market)
    if not meta:
        raise HTTPException(status_code=404, detail="company not found")

    conn = fin_io.connect()
    try:
        fin_io.upsert_company(conn, {**meta, "ticker": ticker, "market": market})
        rows = fin_io.list_periods_with_ratios(conn, ticker, market=market)
    finally:
        conn.close()

    return templates.TemplateResponse(
        request,
        "companies/financials.html",
        {
            "key": key, "ticker": ticker, "market": market,
            "meta": meta, "rows": rows,
        },
    )


@router.post("/refresh")
def refresh(key: str):
    market, ticker = _parse_key(key)
    if not company_io.read_meta(ticker, market):
        raise HTTPException(status_code=404, detail="company not found")
    try:
        if market == "US":
            n = fetch_financials_us.run_for_ticker(ticker, market)
        elif market in ("SSE", "SZSE", "BSE"):
            n = fetch_financials_cn.run_for_ticker(ticker, market)
        else:
            return JSONResponse({"ok": False, "error": f"unsupported market {market}"}, status_code=400)
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": f"{type(e).__name__}: {e}"},
            status_code=500,
        )
    return {"ok": True, "periods_added": n}
```

- [ ] **Step 2: 重写 `app/templates/companies/financials.html`**

```html
{% extends "base.html" %}
{% block title %}{{ ticker }} 财务报表{% endblock %}
{% block content %}
<h1>{{ meta.get('name', ticker) }} · 财务报表 <small>({{ market }}:{{ ticker }})</small></h1>
<p><a href="/companies/{{ key }}">← 返回公司</a></p>

<div class="fin-toolbar">
  <button id="refresh-fin" type="button">刷新财务数据</button>
  <span id="refresh-status" class="hint"></span>

  <span class="tab-group">
    <button class="period-tab active" data-type="annual" type="button">年报</button>
    <button class="period-tab" data-type="quarterly" type="button">季报</button>
  </span>

  <label class="period-count-annual">期数：
    <select id="count-annual">
      <option value="5">5</option>
      <option value="8" selected>8</option>
      <option value="10">10</option>
      <option value="all">全部</option>
    </select>
  </label>
  <label class="period-count-quarterly" hidden>期数：
    <select id="count-quarterly">
      <option value="8">8</option>
      <option value="12" selected>12</option>
      <option value="20">20</option>
      <option value="all">全部</option>
    </select>
  </label>
</div>

{% macro num(v) -%}
  {%- if v is none -%}<span class="hint">–</span>
  {%- else -%}{{ "%.2f"|format(v) }}{%- endif -%}
{%- endmacro %}
{% macro pct(v) -%}
  {%- if v is none -%}<span class="hint">–</span>
  {%- else -%}{{ "%.1f%%"|format(v * 100) }}{%- endif -%}
{%- endmacro %}

{% if not rows %}
<p><em>还没有财务数据。</em> 点 "刷新财务数据" 从 API 拉取。</p>
{% else %}

{# Pick shared-concept column names that work for both CN and US. Jinja
   falls back with `or` so a missing CN key doesn't break US rendering. #}
<h2>利润表</h2>
<table class="financials" data-section="income">
  <thead>
    <tr><th>期间</th><th>营收</th><th>毛利率</th><th>营业利润</th>
        <th>净利润</th><th>EPS (稀释)</th></tr>
  </thead>
  <tbody>
    {% for r in rows %}
    <tr data-period-type="{{ r.period_type }}">
      <td><strong>{{ r.period }}</strong></td>
      <td>{{ num(r.total_revenue or r.operating_revenue) }}</td>
      <td>{{ pct(r.gross_margin) }}</td>
      <td>{{ num(r.operating_income) }}</td>
      <td>{{ num(r.net_income) }}</td>
      <td>{{ num(r.diluted_eps or r.eps_diluted) }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<h2>资产负债表</h2>
<table class="financials" data-section="balance">
  <thead>
    <tr><th>期间</th><th>总资产</th><th>总负债</th><th>股东权益</th>
        <th>资产负债率</th><th>流动比率</th></tr>
  </thead>
  <tbody>
    {% for r in rows %}
    <tr data-period-type="{{ r.period_type }}">
      <td><strong>{{ r.period }}</strong></td>
      <td>{{ num(r.total_assets) }}</td>
      <td>{{ num(r.total_liabilities or r.total_liabilities_net_minority_interest) }}</td>
      <td>{{ num(r.total_equity) }}</td>
      <td>
        {%- set lia = r.total_liabilities or r.total_liabilities_net_minority_interest -%}
        {%- if lia is not none and r.total_assets -%}
          {{ pct(lia / r.total_assets) }}
        {%- else -%}<span class="hint">–</span>{%- endif -%}
      </td>
      <td>{{ num(r.current_ratio) }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<h2>现金流量表</h2>
<table class="financials" data-section="cashflow">
  <thead>
    <tr><th>期间</th><th>经营 CFO</th><th>资本开支</th><th>自由现金流</th>
        <th>筹资 CFF</th></tr>
  </thead>
  <tbody>
    {% for r in rows %}
    <tr data-period-type="{{ r.period_type }}">
      <td><strong>{{ r.period }}</strong></td>
      <td>{{ num(r.operating_cashflow or r.operating_cash_flow) }}</td>
      <td>{{ num(r.capex or r.capital_expenditure) }}</td>
      <td>{{ num(r.fcf) }}</td>
      <td>{{ num(r.financing_cashflow or r.financing_cash_flow) }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<h2>关键比率</h2>
<table class="financials" data-section="ratios">
  <thead>
    <tr><th>期间</th><th>毛利率</th><th>净利率</th>
        <th>ROE</th><th>ROA</th><th>D/E</th></tr>
  </thead>
  <tbody>
    {% for r in rows %}
    <tr data-period-type="{{ r.period_type }}">
      <td><strong>{{ r.period }}</strong></td>
      <td>{{ pct(r.gross_margin) }}</td>
      <td>{{ pct(r.net_margin) }}</td>
      <td>{{ pct(r.roe) }}</td>
      <td>{{ pct(r.roa) }}</td>
      <td>{{ num(r.debt_to_equity) }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

{% endif %}

<script>
(function () {
  const KEY = {{ key|tojson }};

  // Tab switch (annual / quarterly) + period count filter
  const tabs = document.querySelectorAll(".period-tab");
  const selAnnual = document.getElementById("count-annual");
  const selQuarterly = document.getElementById("count-quarterly");
  const wrapAnnual = document.querySelector(".period-count-annual");
  const wrapQuarterly = document.querySelector(".period-count-quarterly");

  function activeType() {
    const t = document.querySelector(".period-tab.active");
    return t ? t.dataset.type : "annual";
  }

  function applyFilter() {
    const type = activeType();
    const sel = type === "annual" ? selAnnual : selQuarterly;
    const countRaw = sel ? sel.value : "all";
    const limit = countRaw === "all" ? Infinity : parseInt(countRaw, 10);

    document.querySelectorAll("table.financials").forEach((tbl) => {
      const rows = tbl.querySelectorAll("tbody tr");
      let shown = 0;
      rows.forEach((tr) => {
        if (tr.dataset.periodType !== type) { tr.hidden = true; return; }
        if (shown < limit) { tr.hidden = false; shown++; }
        else tr.hidden = true;
      });
    });

    wrapAnnual.hidden = type !== "annual";
    wrapQuarterly.hidden = type !== "quarterly";
  }

  tabs.forEach((t) => t.addEventListener("click", () => {
    tabs.forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    applyFilter();
  }));
  if (selAnnual) selAnnual.addEventListener("change", applyFilter);
  if (selQuarterly) selQuarterly.addEventListener("change", applyFilter);
  applyFilter();

  // Refresh button (30s throttle)
  const btn = document.getElementById("refresh-fin");
  const status = document.getElementById("refresh-status");
  let throttleUntil = 0;
  if (btn) {
    btn.addEventListener("click", async () => {
      if (Date.now() < throttleUntil) return;
      throttleUntil = Date.now() + 30000;
      btn.disabled = true;
      const orig = btn.textContent;
      btn.textContent = "正在刷新…";
      status.textContent = "";
      try {
        const res = await fetch(`/companies/${KEY}/financials/refresh`, { method: "POST" });
        const j = await res.json();
        if (j.ok) {
          status.textContent = `已刷新 ${j.periods_added} 期，正在重载...`;
          location.reload();
        } else {
          status.textContent = "刷新失败: " + (j.error || "未知错误");
          status.classList.add("error");
        }
      } catch (e) {
        status.textContent = "请求失败: " + e.message;
        status.classList.add("error");
      } finally {
        setTimeout(() => {
          btn.disabled = false;
          btn.textContent = orig;
        }, 30000);
      }
    });
  }
})();
</script>
{% endblock %}
```

- [ ] **Step 3: 手动烟测 —— 启动开发服务器，访问页面**

Run: `uvicorn app.main:app --reload &`（若无相关启动脚本，换实际启动命令），在浏览器访问 `http://localhost:8000/companies/SSE_600519/financials`。
Expected: 页面渲染不 500；空数据时提示"点刷新"。**关键：在提交前实际点一次刷新按钮验证 POST 通路（如本地没有 akshare 数据源可达，至少看到清晰错误 JSON 即可）。**

- [ ] **Step 4: Commit**

```bash
git add app/routes/financials.py app/templates/companies/financials.html
git commit -m "feat(financials-page): three-statement view + refresh button; remove CSV import"
```

---

## Task 7: 修 `app/io/earnings_review.py` 使用 market-aware 查询

**Files:**
- Modify: `app/io/earnings_review.py:40`、`:95`

- [ ] **Step 1: 改 `_scan` 循环里的 `list_financials` 调用**

在 `app/io/earnings_review.py:30-60`（`_scan` 函数内部），替换：

原代码（`app/io/earnings_review.py:40`）：
```python
            fins = fin_io.list_financials(ticker, conn=conn)
```

新代码：
```python
            if market == "US":
                fins = fin_io.list_financials_us(conn, ticker)
            elif market in ("SSE", "SZSE", "BSE"):
                fins = fin_io.list_financials_cn(conn, ticker)
            else:
                continue
```

- [ ] **Step 2: 改 `company_summary` 里的 `list_periods_with_ratios` 调用**

`app/io/earnings_review.py:95`：
```python
    rows = fin_io.list_periods_with_ratios(ticker, base=base, limit=limit)
```

改成：
```python
    conn = fin_io.connect(base=base)
    try:
        rows = fin_io.list_periods_with_ratios(conn, ticker, market=market)[:limit]
    finally:
        conn.close()
```

- [ ] **Step 3: 跑 earnings_review 相关测试**

Run: `pytest tests/ -k earnings_review -v`
Expected: PASS（若测试用老 fixture 写数据到 `financials` 老表，Task 12 会修测试）。如果大范围失败，查看失败信息，按需添加 fixture 数据走 CN / US 表；不需要的话跳到 Step 4。

- [ ] **Step 4: Commit**

```bash
git add app/io/earnings_review.py
git commit -m "refactor(earnings_review): route financials queries by market"
```

---

## Task 8: 从 `scripts/preprocess_report.py` 删掉财务抽取

**Files:**
- Modify: `scripts/preprocess_report.py:551-607`（删 `extract_financial_line_rows`）
- Modify: `scripts/preprocess_report.py:640-669`（删 `build_result` 里的 `fin_rows` 逻辑 + `financial_line_rows` 键）

- [ ] **Step 1: 删除 `extract_financial_line_rows` 函数 + `_NUMERIC_RE`**

在 `scripts/preprocess_report.py` 中：
- 删除第 551–607 行整个函数（含 `# --- extract_financial_line_rows ---` 注释和 `_NUMERIC_RE` 常量）。

- [ ] **Step 2: 从 `build_result` 删 `fin_rows` 变量 + `financial_line_rows` 输出键**

编辑 `scripts/preprocess_report.py:640-669`，将：

```python
    fig_contexts = extract_figure_contexts(text_full, sections)

    fin_rows: list[dict] = []
    if form_cli in ("annual", "quarterly"):
        market_norm = "US" if market == "us" else ("SSE" if market == "a-share" else market)
        for s in sections:
            if s.get("name") in (
                "财务报告", "主要财务数据", "季度财务报表",
                "Item_8_Financial_Statements",
                "Part_I_Item_1_Financial_Statements",
            ):
                fin_rows.extend(extract_financial_line_rows(s["text"], market=market_norm))

    return {
        "meta": {
            ...
        },
        "sections": out_sections,
        "figure_contexts": fig_contexts,
        "detected_tickers": detect_tickers(text_full),
        "report_abstract": extract_report_abstract(text_full),
        "financial_line_rows": fin_rows,
    }
```

改成：

```python
    fig_contexts = extract_figure_contexts(text_full, sections)

    return {
        "meta": {
            ...
        },
        "sections": out_sections,
        "figure_contexts": fig_contexts,
        "detected_tickers": detect_tickers(text_full),
        "report_abstract": extract_report_abstract(text_full),
    }
```

- [ ] **Step 3: 更新 4 个 ingest 模板的 `skip_rules.sections`**

在这 4 个文件顶层 `skip_rules.sections` 列表里追加条目（确切位置按文件已有风格）：

`.claude/skills/ingest/templates/a-share-annual.yaml` — 加：
```yaml
  - 财务报告
  - 主要财务数据
```

`.claude/skills/ingest/templates/a-share-quarterly.yaml` — 加：
```yaml
  - 季度财务报表
  - 主要财务数据
```

`.claude/skills/ingest/templates/us-10k.yaml` — 加：
```yaml
  - Item_8_Financial_Statements
```

`.claude/skills/ingest/templates/us-10q.yaml` — 加：
```yaml
  - Part_I_Item_1_Financial_Statements
```

（若模板用 dict 而非 list，用等价 key 的方式追加；先 Read 看结构再改。）

- [ ] **Step 4: 更新 `.claude/skills/ingest/section-routing.yaml`**

找到：
```yaml
  财务报告:               {action: extract}
```
改成：
```yaml
  财务报告:               {action: skip, reason: 数字已由 API 入库，叙述由 MD&A 覆盖}
```

同理：
```yaml
  Item_8_Financial_Statements:       {action: extract}
  Part_I_Item_1_Financial_Statements: {action: extract}
```
都改成 `{action: skip, reason: 数字已由 API 入库，叙述由 MD&A 覆盖}`。

- [ ] **Step 5: 跑预处理相关测试**

Run: `pytest tests/test_preprocess_report.py tests/test_preprocess_industry_type.py tests/test_preprocess_financial_lines.py -v`
Expected:
- `test_preprocess_financial_lines.py`：全部 FAIL（函数已删），Task 12 会删文件
- `test_preprocess_industry_type.py`：`financial_line_rows == []` 断言 FAIL，Task 12 会改断言
- 其他：PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/preprocess_report.py .claude/skills/ingest/templates/ .claude/skills/ingest/section-routing.yaml
git commit -m "refactor(ingest): drop financial line extraction from preprocess; skip statement sections"
```

---

## Task 9: 从 `scripts/ingest_aggregate.py` + `scripts/ingest_qa.py` 删财务聚合

**Files:**
- Modify: `scripts/ingest_aggregate.py`（删 `financial_rows` 聚合、`build_financials_csv`、`write_financials`、`check_financials_required`、`check_revenue_consistency`）
- Modify: `scripts/ingest_qa.py`（删 `check_financials_required`）

- [ ] **Step 1: 删 `ingest_aggregate.py` 里的 4 块**

打开 `scripts/ingest_aggregate.py`，按下列范围删除：

a) `aggregate()` 里（约 `:167, :182, :198`）—— 把三处 `financial_rows` 引用删掉：

- 删 `merged` 初始化里的 `"financial_rows": [],` 一行。
- 删 `merged["financial_rows"].extend(blob.get("financial_rows") or [])` 那一行。
- `empty_subagents` 检查里的 `and not (blob.get("financial_rows") or [])` 一行删掉。

b) `check_revenue_consistency()` 整个函数删（约 `:380-412`）以及它引用的 `_TOTAL_REVENUE_KEYS`、`_SEGMENT_REVENUE_KEYS`、`_extract_money_usd` 常量/函数（若仅被它用）。

c) `check_financials_required()` 整个函数删（约 `:430-437`）。

d) `build_financials_csv()`（约 `:465-478`）和 `write_financials()`（约 `:484-492`）整段删。

e) 把文件顶部 docstring 里提到 `check_financials_required`、`write_financials`、`financial_rows` 的文字清掉（保持文档真实）。

- [ ] **Step 2: 删 `scripts/ingest_qa.py` 里的 `check_financials_required`**

```bash
grep -n "check_financials_required" /Users/yangqi/investing/scripts/ingest_qa.py
```

读到的行全部删除，包括定义和 imports。

- [ ] **Step 3: 跑 aggregate 相关测试看哪些坏了**

Run: `pytest tests/test_ingest_aggregate.py -v`
Expected: 以下测试 FAIL（预期）：
- `test_write_financials_round_trip`
- `test_aggregate_merges_financial_rows` / 类似名字
- `check_financials_required` 系列（3 个）
- `check_revenue_consistency` 系列
其他（claims、profile、dedup）应仍 PASS。

Task 12 会删这些测试用例。

- [ ] **Step 4: Commit**

```bash
git add scripts/ingest_aggregate.py scripts/ingest_qa.py
git commit -m "refactor(ingest): remove financial_rows aggregation path"
```

---

## Task 10: 清理 ingest skill 文档和 cross-checks

**Files:**
- Modify: `.claude/skills/ingest/workflows/annual-report.md`
- Modify: `.claude/skills/ingest/workflows/quarterly-report.md`
- Modify: `.claude/skills/ingest/workflows/sell-side-note.md`
- Modify: `.claude/skills/ingest/prompts/digest/annual-digest.md`
- Modify: `.claude/skills/ingest/prompts/digest/quarterly-digest.md`
- Modify: `.claude/skills/ingest/SKILL.md`
- Modify: `.claude/skills/ingest/cross-checks.yaml`
- Delete: `controlled-vocab/financial-aliases.yaml`

- [ ] **Step 1: `annual-report.md` —— 删财务流程**

在 `.claude/skills/ingest/workflows/annual-report.md` 中：
- 删掉 Step 7a.8 整节（`financial_line_rows` 注入到 digest prompt 的片段）
- 删掉 QA 步骤里 `financials_required` 检查的相关行
- 删掉 `agg.write_financials(...)` 调用
- 删掉提到 "financial_rows 必填" 的 pause 条件
- 在顶部"产物清单"里去掉 `financial_rows`

- [ ] **Step 2: `quarterly-report.md` —— 删财务流程**

同 Step 1，且把"主产物是 financial_rows"的描述改成"主产物是 claims"。

- [ ] **Step 3: `sell-side-note.md` —— 删 sentinel 引用**

去掉 `agg.check_financials_required(...)` 相关行。

- [ ] **Step 4: `annual-digest.md` —— 删输出字段 + 改 financial_profile 来源**

在 `.claude/skills/ingest/prompts/digest/annual-digest.md`：

a) 输入说明里（约 `:11`）：
```
- **financial_rows**（从预处理 `financial_line_rows[]` 里主 agent 已做了初筛；你读这些 rows + 原文 context 做最终填表）
```
整行删除。

b) 输出 JSON schema（约 `:29-35`）里 `financial_rows` 那一段整段删除，包括 checklist 里提到 `financial_rows` 的任何条目。

c) 来源提示（约 `:59`）：
```
| financial_profile | 核心指标演进 / 利润结构 / 现金流质量 → `§财务报告` |
```
改成：
```
| financial_profile | 核心指标演进 / 利润结构 / 现金流质量 → `§管理层讨论与分析` / `§Item_7_MDA` |
```

- [ ] **Step 5: `quarterly-digest.md` —— 删 `financial_rows` 主产物描述**

在相关处删除 `financial_rows` 的所有引用（grep 定位）；`financial_profile` 来源描述同上改成 MD&A 来源。

- [ ] **Step 6: `SKILL.md` —— 删 ingest 函数列表里的财务条目**

在 `.claude/skills/ingest/SKILL.md` 里：
- 预处理输出结构说明里的 `financial_line_rows` 条目删掉
- `ingest_aggregate` 函数列表里的 `write_financials` / `check_financials_required` 条目删掉
- `app.io.financials` → `import_financials_csv` 的引用说明删掉
- 流程代码片段里的 `financial_rows` / `write_financials` 步骤删掉

- [ ] **Step 7: `cross-checks.yaml` —— 删 financial_rows 规则**

在 `.claude/skills/ingest/cross-checks.yaml` 删除：
- `financial_rows=[]` 警告规则
- `financial_rows CSV 至少有 revenue、net_income` 校验规则

- [ ] **Step 8: 删 `controlled-vocab/financial-aliases.yaml`**

```bash
git rm controlled-vocab/financial-aliases.yaml
```

- [ ] **Step 9: grep 全仓确认没漏**

Run:
```bash
grep -rn "financial_rows\|financial_line_rows\|write_financials\|check_financials_required\|import_financials_csv\|FINANCIAL_COLUMNS\|load_alias_map\|financial-aliases" /Users/yangqi/investing --include="*.py" --include="*.md" --include="*.yaml" --include="*.html" 2>/dev/null | grep -v __pycache__ | grep -v ".git/"
```
Expected: 只剩下测试文件里待清理的引用（Task 12 处理）。如果在 app/ scripts/ 里还有遗留的 production 引用，现在修掉。

- [ ] **Step 10: Commit**

```bash
git add -A .claude/skills/ingest/ controlled-vocab/
git commit -m "docs(ingest): purge financial_rows from skill workflows, prompts, cross-checks"
```

---

## Task 11: 从 `app/io/financials.py` 删掉遗留的 alias map 代码

**Files:**
- Modify: `app/io/financials.py`（若 Task 3 的重写已经不含 `load_alias_map`/`normalize_raw_key`，跳过）

- [ ] **Step 1: 确认 Task 3 写的 `app/io/financials.py` 里没有 `load_alias_map`**

Run: `grep -n "load_alias_map\|normalize_raw_key\|FINANCIAL_ALIASES\|_ALIAS_MAP_CACHE" /Users/yangqi/investing/app/io/financials.py`
Expected: 无输出。

如果有（说明 Task 3 漏删），删掉这些函数 + 常量 + imports。

- [ ] **Step 2: Commit（如有改动）**

```bash
git add app/io/financials.py
git commit -m "chore(financials): remove legacy alias map helpers"
```

---

## Task 12: 清理 + 重写测试，跑全量绿

**Files:**
- Delete: `tests/test_preprocess_financial_lines.py`
- Modify: `tests/test_ingest_aggregate.py`（删 financial_rows 相关用例）
- Modify: `tests/test_digest_prompt_contracts.py`（删 `test_annual_digest_declares_financial_rows`）
- Modify: `tests/test_config_dimensions.py`（删 INCOME/BALANCE/CASHFLOW 断言）
- Modify: `tests/test_preprocess_industry_type.py`（删 `financial_line_rows` 断言）

- [ ] **Step 1: 删 `test_preprocess_financial_lines.py`**

```bash
git rm tests/test_preprocess_financial_lines.py
```

- [ ] **Step 2: 编辑 `tests/test_ingest_aggregate.py` —— 删 financial_rows 测试**

用 grep 定位（行号参考 Task 9 的已有结果）：
- 删 `"financial_rows"` 出现的初始化 / 断言（约 `:134, :246, :289, :349, :350, :355, :356, :361, :362, :386`）
- 删整个 `test_write_financials_round_trip` 函数（约 `:443-455`）
- 删整个 "write_financials / write_claims (integration)" 分节里 write_financials 相关部分
- 删 `test_check_financials_required_*` 系列
- 删 `test_check_revenue_consistency_*` 系列（如果有）

保留 claims、profile_fragments、meta_updates、dedup 相关测试。

- [ ] **Step 3: 编辑 `tests/test_digest_prompt_contracts.py`**

删除整个 `test_annual_digest_declares_financial_rows` 函数（`:48-50` 附近）。

- [ ] **Step 4: 编辑 `tests/test_config_dimensions.py`**

删除 INCOME_STATEMENT_LINES / BALANCE_SHEET_LINES / CASHFLOW_LINES 的所有 assert（原 `:44-69` 附近）。若删完整个函数为空，整个 def 删掉。

- [ ] **Step 5: 编辑 `tests/test_preprocess_industry_type.py`**

删除 `financial_line_rows == []` 断言（`:57-58`）。

- [ ] **Step 6: 跑全量测试**

Run: `pytest -x -v 2>&1 | tail -80`
Expected: 全 PASS。

如果还有失败：
- `ModuleNotFoundError: controlled_vocab` 之类 → 有地方还在 import `financial-aliases.yaml`；grep + 修
- `AttributeError: 'module' has no attribute 'FINANCIAL_COLUMNS'` → 有地方还在用旧常量；grep + 修

**Important：不跑绿不提交。**

- [ ] **Step 7: Commit**

```bash
git add -A tests/
git commit -m "test: clean stale financial_rows / line-item tests"
```

---

## Task 13: 端到端烟测 + 最终提交

- [ ] **Step 1: 初始化一个 tmp DB，跑真实 fetch**

Run（若本地能访问 akshare）:
```bash
python -m scripts.fetch_financials_cn SSE_600519
```
Expected: 返回 N periods upserted，无异常。用 sqlite3 客户端查：
```bash
sqlite3 data/financials.db "SELECT period, net_income FROM financials_cn WHERE ticker='600519' ORDER BY period DESC LIMIT 5"
```
Expected: 最近 5 期数据显示。

若网络条件不允许，跳到 Step 2。

- [ ] **Step 2: 页面手动访问**

Run: `uvicorn app.main:app --reload`（或项目已有的启动命令）
在浏览器打开 `http://localhost:8000/companies/SSE_600519/financials`（选一个 meta 存在的公司 key）。
Expected:
- 页面渲染 3 张表 + 比率表
- Tab 切换"年报/季报" 工作
- 期数下拉切换显示不同行数
- 刷新按钮被点击后显示"正在刷新…"，30 秒内不可再点

- [ ] **Step 3: 跑一次全测（再次）+ lint**

Run:
```bash
pytest -x -q 2>&1 | tail -20
python -m pyflakes app/ scripts/ 2>&1 | head -30  # 若项目用 pyflakes/ruff 之一
```
Expected: 全 PASS；flake 无遗漏的 imports / unused。

- [ ] **Step 4: 最终汇总 commit（若前面 12 个 task 有遗漏的碎改）**

```bash
git status
# 若有未提交：
git add -A
git commit -m "chore(financials): final cleanup after API migration"
```

---

## 验收标准

- [ ] `financials_cn` / `financials_us` 两张表存在且 schema 与 spec §1 一致
- [ ] `scripts/fetch_financials_cn.py SSE_600519` 能跑通写入至少 5 期
- [ ] `scripts/fetch_financials_us.py US_HIMS` 能跑通写入至少 2 期年报 + 2 期季报
- [ ] `GET /companies/{key}/financials` 渲染 3 张表 + 比率 + 刷新按钮
- [ ] `POST /companies/{key}/financials/refresh` 返回 `{ok:true, periods_added:N}`
- [ ] Tab + 期数下拉纯前端切换（无网络请求）
- [ ] `grep -rn "financial_rows\|write_financials\|check_financials_required" app/ scripts/ tests/` 只剩测试文件里必要的引用（例如命名在其他上下文的 false positive）
- [ ] `pytest -x -q` 全绿
- [ ] 旧 `financials` 表不再被 `init_schema` 创建
- [ ] Ingest skill 文档 / prompts / workflows 不再提 `financial_rows`，且 `financial_profile` 来源为 `§管理层讨论与分析` / `§Item_7_MDA`

"""Path constants and base configuration."""
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent.parent

COMPANIES_DIR = BASE_PATH / "companies"
INDUSTRIES_DIR = BASE_PATH / "industries"
ARENAS_DIR = BASE_PATH / "arenas"
WATCHLIST_DIR = BASE_PATH / "watchlist"
PORTFOLIO_DIR = BASE_PATH / "portfolio"
MACRO_DIR = BASE_PATH / "macro"
JOURNAL_DIR = BASE_PATH / "journal"
DATA_DIR = BASE_PATH / "data"
FINANCIALS_DB = DATA_DIR / "financials.db"

TEMPLATES_DIR = BASE_PATH / "templates"
CONTROLLED_VOCAB_DIR = BASE_PATH / "controlled-vocab"

APP_TEMPLATES_DIR = BASE_PATH / "app" / "templates"
STATIC_DIR = BASE_PATH / "static"
PRISM_DIR = BASE_PATH / "prism"

VALID_MARKETS = ("US", "SSE", "SZSE", "BSE", "HK")
# VALID_SECTORS / sector whitelist removed in Plan 1 (Tasks 3/4/11/22).
# Industry membership is now `industry_slugs: list[str]` — a free-form list
# of slugs that reference the `industries/` registry. No whitelist enforcement.

# Three-layer knowledge dimension tuples (spec §4.5).
# Snake_case keys map to kebab-case filenames:
#   COMPANY_DIMENSIONS item "growth_engine" ↔ companies/{key}/narratives/growth-engine.md
INDUSTRY_DIMENSIONS = (
    "definition",
    "market_size",
    "lifecycle",
    "value_chain",
    "competition",
    "drivers",
    "technology",
    "regulation",
    "benchmark",
    "risks",
    "valuation",
)

ARENA_DIMENSIONS = (
    "definition",
    "participants",
    "decisive_factors",
    "trajectory",
    "narratives",
    "investment_view",
)

COMPANY_DIMENSIONS = (
    "business_model",
    "moat",
    "growth_engine",
    "management",
    "financial_profile",
    "catalysts",
    "risks",
    "valuation",
)

# Investment lens view dimension tuples (spec §10.2-10.4).
# Distinct from archive dimensions — lens answers "what is our judgment"
# while archive answers "what do we know".
INDUSTRY_INVESTMENT_VIEW_DIMS = (
    "thesis", "demand", "supply_competition", "profit_pool",
    "unit_economics", "stage_gates", "catalysts_timeline",
    "risks_disconfirming_evidence",
)
ARENA_BATTLEFIELD_VIEW_DIMS = (
    "battlefield_definition", "players_positions", "winning_variables",
    "evidence_scoreboard", "stage_gates", "inflection_points",
    "company_implications",
)
COMPANY_MEMO_VIEW_DIMS = (
    "business_exposure", "thesis_fit", "moat_execution", "financial_quality",
    "growth_drivers", "stage_gate_status", "valuation_expectations",
    "catalysts_risks", "open_questions",
)

VIEW_DIMENSIONS = {
    "archive": {
        "industry": INDUSTRY_DIMENSIONS,
        "arena": ARENA_DIMENSIONS,
        "company": COMPANY_DIMENSIONS,
    },
    "investment_lens": {
        "industry": INDUSTRY_INVESTMENT_VIEW_DIMS,
        "arena": ARENA_BATTLEFIELD_VIEW_DIMS,
        "company": COMPANY_MEMO_VIEW_DIMS,
    },
}

# Suggested structured fields per industry dimension. Open vocabulary —
# observations.field is not validated against this dict, but digest prompts
# use it as guidance. Dimensions not listed here don't have structured fields
# (narrative-only).
INDUSTRY_FIELDS = {
    "market_size": [
        "tam_global", "tam_china", "tam_by_segment",
        "cagr_global", "cagr_china",
    ],
    "lifecycle": ["stage", "stage_evidence"],
    "competition": [
        "hhi", "cr5", "cr10", "share_by_player",
        "porter_entry_barrier", "porter_substitute_threat",
        "porter_supplier_power", "porter_buyer_power", "porter_rivalry",
    ],
    "benchmark": [
        "gross_margin_leader", "gross_margin_avg",
        "capex_intensity_avg", "rd_ratio_leader",
    ],
    "valuation": ["pe_ttm_median", "pb_median", "ev_ebitda_median"],
}

# CN_COL_MAP: akshare stock_financial_report_sina 返回的中文列名 → financials_cn snake_case.
# 三张表共用一个 map；同名 key 若两表语义不同，按资产负债表优先（goodwill 等只出现在 BS）。
# 未在 map 里的列由 fetch_financials_cn 忽略（仅 WARN，不 fail）。
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
    "购建固定资产、无形资产和其他长期资产所支付的现金": "capex",
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

# US_COL_MAP: yfinance Title Case → financials_us snake_case.
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

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

# Financials line items (spec §4.7). Standard snake_case keys; A-share and
# US GAAP raw names map to these via controlled-vocab/financial-aliases.yaml.
INCOME_STATEMENT_LINES = (
    "revenue", "cost_of_revenue", "gross_profit",
    "selling_expense", "admin_expense", "rd_expense", "other_opex",
    "operating_income",
    "interest_income", "interest_expense", "other_non_operating",
    "pretax_income", "income_tax", "net_income",
    "minority_interest", "net_income_to_parent",
    "eps_basic", "eps_diluted",
)

BALANCE_SHEET_LINES = (
    "cash_and_equivalents", "short_term_investments",
    "accounts_receivable", "inventory", "other_current_assets",
    "total_current_assets",
    "ppe_net", "goodwill", "intangibles", "other_non_current_assets",
    "total_assets",
    "accounts_payable", "short_term_debt", "other_current_liab",
    "total_current_liab",
    "long_term_debt", "other_non_current_liab",
    "total_liab",
    "minority_equity", "total_equity",
)

CASHFLOW_LINES = (
    "net_income_cf", "depreciation_amortization",
    "working_capital_change", "other_operating",
    "operating_cashflow",
    "capex", "other_investing", "investing_cashflow",
    "debt_issued", "debt_repaid", "equity_issued", "dividends",
    "other_financing", "financing_cashflow",
    "fx_effect", "net_change_in_cash",
)

FINANCIAL_ALIASES_PATH = CONTROLLED_VOCAB_DIR / "financial-aliases.yaml"

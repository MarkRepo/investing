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
# Note: VALID_SECTORS removed for refactor. See Tasks 4, 11 for migration.
# Tests use _INTERNAL_SECTORS_FOR_TESTS for backward compatibility.
_INTERNAL_SECTORS_FOR_TESTS = ("consumer", "saas", "cyclical", "bank", "biotech")

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

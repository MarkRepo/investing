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

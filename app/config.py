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
SECTOR_VOCAB_DIR = CONTROLLED_VOCAB_DIR / "competence-sector"

APP_TEMPLATES_DIR = BASE_PATH / "app" / "templates"
STATIC_DIR = BASE_PATH / "static"

VALID_SECTORS = ("consumer", "saas", "cyclical", "bank", "biotech")
VALID_MARKETS = ("US", "SSE", "SZSE", "BSE", "HK")

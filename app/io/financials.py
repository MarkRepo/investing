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
# sync with the SQL in _CN_RATIOS_SQL below and with CN_COL_MAP snake_case values.
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
CREATE TABLE IF NOT EXISTS financials_last_fetch (
    ticker TEXT NOT NULL,
    market TEXT NOT NULL,
    last_fetched_at TEXT NOT NULL,
    periods_fetched INTEGER,
    PRIMARY KEY (ticker)
);
"""


_TEXT_COLS = {"report_date", "period_type", "announced_date", "currency", "source"}


def _col_type(col: str) -> str:
    if col in _TEXT_COLS:
        return "TEXT"
    if col == "is_audited":
        return "INTEGER"
    return "REAL"


def _cn_table_ddl() -> str:
    cols_sql = ",\n    ".join(f"{c} {_col_type(c)}" for c in CN_COLUMNS)
    return f"""
CREATE TABLE IF NOT EXISTS financials_cn (
    ticker TEXT NOT NULL,
    period TEXT NOT NULL,
    {cols_sql},
    PRIMARY KEY (ticker, period)
);
"""


def _us_table_ddl() -> str:
    cols_sql = ",\n    ".join(f"{c} {_col_type(c)}" for c in US_COLUMNS)
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
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {_col_type(col)}")
    # Companies table pre-existing without industry_slugs (legacy column name
    # was industry_primary) — add the new column so upsert_company works.
    existing_co = {r[1] for r in conn.execute("PRAGMA table_info(companies)").fetchall()}
    if "industry_slugs" not in existing_co:
        conn.execute("ALTER TABLE companies ADD COLUMN industry_slugs TEXT")
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
    {SSE, SZSE, BSE} → financials_cn; {US, HKEX} → financials_us.

    HKEX shares the financials_us table because its statements are yfinance-
    sourced and column-identical to US (same us_col_to_snake / US_COLUMNS).
    """
    ticker = (ticker or "").strip().upper()
    if not ticker:
        raise ValueError("ticker is empty")
    if market in _CN_MARKETS:
        sql = _CN_RATIOS_SQL
    elif market in ("US", "HKEX"):
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
    elif market in ("US", "HKEX"):
        fins = list_financials_us(conn, ticker)
    else:
        raise ValueError(f"unsupported market {market!r}")
    rats = {r["period"]: dict(r) for r in list_ratios(conn, ticker)}
    out = []
    for row in fins:
        merged = {**row, **{k: v for k, v in rats.get(row["period"], {}).items() if k not in ("ticker", "period")}}
        out.append(merged)
    return _sort_desc(out)


def record_last_fetch(conn: sqlite3.Connection, ticker: str, market: str, count: int) -> None:
    """Record the last successful fetch timestamp."""
    ticker = ticker.strip().upper()
    now = _now_iso()
    conn.execute(
        """
        INSERT INTO financials_last_fetch (ticker, market, last_fetched_at, periods_fetched)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(ticker) DO UPDATE SET
            market = excluded.market,
            last_fetched_at = excluded.last_fetched_at,
            periods_fetched = excluded.periods_fetched
        """,
        (ticker, market, now, count),
    )
    conn.commit()


def get_last_fetch(conn: sqlite3.Connection, ticker: str) -> dict | None:
    """Return last fetch info for a ticker."""
    row = conn.execute(
        "SELECT market, last_fetched_at, periods_fetched FROM financials_last_fetch WHERE ticker = ?",
        (ticker.strip().upper(),),
    ).fetchone()
    if row:
        return dict(row)
    return None


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

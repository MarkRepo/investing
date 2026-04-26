"""SQLite financial data pipeline (DESIGN §3.7).

Schema lives in SQLite; markdown is still authoritative for qualitative data.
CSV import is the primary ingestion mode (manual entry → CSV → this module).
Derived ratios are recomputed whenever financials rows change.

No LLM calls here. Parsing of PDFs/reports happens in a separate conversation-
driven flow that eventually feeds into this module via CSV.
"""
from __future__ import annotations

import csv
import io
import re
import sqlite3
from pathlib import Path
from typing import Iterable

import yaml

from app import config as cfg

FINANCIAL_COLUMNS = (
    "revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "total_assets",
    "total_equity",
    "operating_cashflow",
    "shares_outstanding",
)


_ALIAS_MAP_CACHE: dict | None = None


def load_alias_map() -> dict:
    """Load and cache A-share/US GAAP → standard key alias map."""
    global _ALIAS_MAP_CACHE
    if _ALIAS_MAP_CACHE is None:
        path = cfg.FINANCIAL_ALIASES_PATH
        if not path.exists():
            raise FileNotFoundError(f"financial aliases map not found at {path}")
        with path.open("r", encoding="utf-8") as f:
            _ALIAS_MAP_CACHE = yaml.safe_load(f) or {}
    return _ALIAS_MAP_CACHE


def normalize_raw_key(raw: str, market: str | None = None) -> str | None:
    """Map a raw A-share or US GAAP line name to standard snake_case key.

    market: "US" / "SSE" / "SZSE" / "BSE" / "HK" / None (tries both).
    Returns None if no match (caller should log warning, not fail).
    """
    if not raw:
        return None
    m = load_alias_map()
    raw_norm = raw.strip().lower()
    alias_langs = ["a_share", "us_gaap"]
    if market == "US":
        alias_langs = ["us_gaap", "a_share"]
    elif market in ("SSE", "SZSE", "BSE", "HK"):
        alias_langs = ["a_share", "us_gaap"]
    for std_key, langs in m.items():
        for lang in alias_langs:
            aliases = langs.get(lang, []) or []
            for alias in aliases:
                if alias.strip().lower() == raw_norm:
                    return std_key
                # Chinese keys also match exact raw (no lowercasing needed for zh):
                if alias.strip() == raw.strip():
                    return std_key
    return None


PERIOD_RE = re.compile(r"^(\d{4})(Q[1-4]|A)$")
_VALID_PERIOD_TYPES = ("annual", "quarterly")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    ticker TEXT PRIMARY KEY,
    market TEXT,
    name TEXT,
    industry_primary TEXT,
    listed_date DATE,
    currency TEXT
);

CREATE TABLE IF NOT EXISTS financials (
    ticker TEXT NOT NULL,
    period TEXT NOT NULL,
    period_type TEXT NOT NULL,
    revenue REAL,
    gross_profit REAL,
    operating_income REAL,
    net_income REAL,
    total_assets REAL,
    total_equity REAL,
    operating_cashflow REAL,
    shares_outstanding REAL,
    source_file TEXT,
    PRIMARY KEY (ticker, period)
);

CREATE TABLE IF NOT EXISTS ratios (
    ticker TEXT NOT NULL,
    period TEXT NOT NULL,
    gross_margin REAL,
    net_margin REAL,
    operating_margin REAL,
    roe REAL,
    roa REAL,
    debt_to_equity REAL,
    PRIMARY KEY (ticker, period)
);

CREATE TABLE IF NOT EXISTS price_triggers (
    ticker TEXT NOT NULL,
    trigger_price REAL NOT NULL,
    action TEXT NOT NULL,
    v0_snapshot_path TEXT,
    created_at DATE,
    triggered_at DATE
);

CREATE TABLE IF NOT EXISTS benchmark (
    date DATE NOT NULL,
    symbol TEXT NOT NULL,
    close REAL,
    PRIMARY KEY (date, symbol)
);

CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    close REAL NOT NULL,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS quotes_daily (
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    market TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL NOT NULL,
    volume INTEGER,
    amount REAL,
    turnover_rate REAL,
    volume_ratio_5d REAL,
    pe_ttm REAL,
    pe_static REAL,
    pe_forward REAL,
    pb REAL,
    ps REAL,
    peg REAL,
    dividend_yield REAL,
    market_cap REAL,
    float_market_cap REAL,
    shares_outstanding REAL,
    float_shares REAL,
    high_52w REAL,
    low_52w REAL,
    source TEXT,
    fetched_at TEXT,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS quotes_fetch_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    market TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    source TEXT NOT NULL,
    phase TEXT NOT NULL,
    error TEXT NOT NULL,
    resolved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_fetch_errors_unresolved
    ON quotes_fetch_errors(ticker, resolved_at) WHERE resolved_at IS NULL;
"""


def _db_path(base: Path | None) -> Path:
    if base is None:
        return cfg.FINANCIALS_DB
    return Path(base) / "data" / "financials.db"


def connect(base: Path | None = None) -> sqlite3.Connection:
    """Open (and initialize if needed) the financials DB."""
    path = _db_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def upsert_company(conn: sqlite3.Connection, meta: dict) -> None:
    """Mirror markdown meta into the SQLite companies table (read-through cache)."""
    conn.execute(
        """
        INSERT INTO companies(ticker, market, name, industry_primary, listed_date, currency)
        VALUES (:ticker, :market, :name, :industry_primary, :listed_date, :currency)
        ON CONFLICT(ticker) DO UPDATE SET
            market = excluded.market,
            name = excluded.name,
            industry_primary = excluded.industry_primary,
            listed_date = excluded.listed_date,
            currency = excluded.currency
        """,
        {
            "ticker": (meta.get("ticker") or "").upper(),
            "market": meta.get("market"),
            "name": meta.get("name"),
            "industry_primary": meta.get("industry_primary"),
            "listed_date": str(meta.get("listed_date")) if meta.get("listed_date") else None,
            "currency": meta.get("currency"),
        },
    )
    conn.commit()


# --- CSV import -------------------------------------------------------------


def _coerce_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.lower() in ("nan", "null", "none", "-"):
        return None
    # Tolerate thousands separators like 1,234.56
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError as e:
        raise ValueError(f"not a number: {raw!r}") from e


def _parse_rows(csv_text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")
    required = {"period", "period_type"}
    missing_required = required - set(reader.fieldnames)
    if missing_required:
        raise ValueError(f"CSV missing required columns: {sorted(missing_required)}")

    rows: list[dict] = []
    for i, raw in enumerate(reader, start=2):  # header is line 1
        period = (raw.get("period") or "").strip()
        ptype = (raw.get("period_type") or "").strip().lower()
        if not PERIOD_RE.match(period):
            raise ValueError(f"line {i}: invalid period {period!r}, expected YYYYQ[1-4] or YYYYA")
        if ptype not in _VALID_PERIOD_TYPES:
            raise ValueError(
                f"line {i}: invalid period_type {ptype!r}, expected one of {_VALID_PERIOD_TYPES}"
            )
        if period.endswith("A") and ptype != "annual":
            raise ValueError(f"line {i}: period {period} implies annual but period_type is {ptype}")
        if "Q" in period and ptype != "quarterly":
            raise ValueError(
                f"line {i}: period {period} implies quarterly but period_type is {ptype}"
            )

        parsed = {"period": period, "period_type": ptype}
        for col in FINANCIAL_COLUMNS:
            try:
                parsed[col] = _coerce_float(raw.get(col))
            except ValueError as e:
                raise ValueError(f"line {i}, column {col}: {e}") from e
        rows.append(parsed)
    return rows


def import_financials_csv(
    ticker: str,
    csv_text: str,
    source_file: str = "",
    base: Path | None = None,
    conn: sqlite3.Connection | None = None,
) -> int:
    """Upsert rows parsed from ``csv_text`` into financials + recompute ratios.

    Returns the number of rows written.
    """
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("ticker cannot be empty")

    rows = _parse_rows(csv_text)
    if not rows:
        return 0

    owns = conn is None
    conn = conn or connect(base=base)
    try:
        for r in rows:
            conn.execute(
                f"""
                INSERT INTO financials
                    (ticker, period, period_type, {", ".join(FINANCIAL_COLUMNS)}, source_file)
                VALUES
                    (:ticker, :period, :period_type, {", ".join(f":{c}" for c in FINANCIAL_COLUMNS)}, :source_file)
                ON CONFLICT(ticker, period) DO UPDATE SET
                    period_type = excluded.period_type,
                    {", ".join(f"{c} = excluded.{c}" for c in FINANCIAL_COLUMNS)},
                    source_file = excluded.source_file
                """,
                {"ticker": ticker, "source_file": source_file or None, **r},
            )
        conn.commit()
        recompute_ratios(conn, ticker)
    finally:
        if owns:
            conn.close()
    return len(rows)


# --- Derived ratios ---------------------------------------------------------


def _safe_div(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or den == 0:
        return None
    return num / den


def recompute_ratios(conn: sqlite3.Connection, ticker: str) -> None:
    """Rebuild the ratios table for one ticker from current financials rows."""
    ticker = ticker.strip().upper()
    conn.execute("DELETE FROM ratios WHERE ticker = ?", (ticker,))
    rows = conn.execute(
        f"SELECT period, {', '.join(FINANCIAL_COLUMNS)} FROM financials WHERE ticker = ?",
        (ticker,),
    ).fetchall()
    for r in rows:
        revenue = r["revenue"]
        liabilities = None
        if r["total_assets"] is not None and r["total_equity"] is not None:
            liabilities = r["total_assets"] - r["total_equity"]
        conn.execute(
            """
            INSERT INTO ratios
                (ticker, period, gross_margin, net_margin, operating_margin, roe, roa, debt_to_equity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker,
                r["period"],
                _safe_div(r["gross_profit"], revenue),
                _safe_div(r["net_income"], revenue),
                _safe_div(r["operating_income"], revenue),
                _safe_div(r["net_income"], r["total_equity"]),
                _safe_div(r["net_income"], r["total_assets"]),
                _safe_div(liabilities, r["total_equity"]),
            ),
        )
    conn.commit()


# --- Queries ----------------------------------------------------------------


def _period_sort_key(period: str) -> tuple[int, int, int]:
    """Order: year desc primary; within year, annual after quarterly (A = 5, Q1..Q4 = 1..4)."""
    m = PERIOD_RE.match(period)
    if not m:
        return (0, 0, 0)
    year = int(m.group(1))
    tag = m.group(2)
    if tag == "A":
        return (year, 2, 5)  # annual groups after quarterly of same year
    return (year, 1, int(tag[1]))


def _sort_by_period_desc(rows: Iterable[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: _period_sort_key(r["period"]), reverse=True)


def list_financials(
    ticker: str, base: Path | None = None, conn: sqlite3.Connection | None = None
) -> list[dict]:
    ticker = ticker.strip().upper()
    owns = conn is None
    conn = conn or connect(base=base)
    try:
        rows = conn.execute(
            f"""SELECT period, period_type, {", ".join(FINANCIAL_COLUMNS)}, source_file
                FROM financials WHERE ticker = ?""",
            (ticker,),
        ).fetchall()
        return _sort_by_period_desc(dict(r) for r in rows)
    finally:
        if owns:
            conn.close()


def list_ratios(
    ticker: str, base: Path | None = None, conn: sqlite3.Connection | None = None
) -> list[dict]:
    ticker = ticker.strip().upper()
    owns = conn is None
    conn = conn or connect(base=base)
    try:
        rows = conn.execute(
            """SELECT period, gross_margin, net_margin, operating_margin, roe, roa, debt_to_equity
               FROM ratios WHERE ticker = ?""",
            (ticker,),
        ).fetchall()
        return _sort_by_period_desc(dict(r) for r in rows)
    finally:
        if owns:
            conn.close()


def list_periods_with_ratios(
    ticker: str, base: Path | None = None, limit: int = 12
) -> list[dict]:
    """Join financials + ratios into a single per-period row, newest first."""
    conn = connect(base=base)
    try:
        fins = {r["period"]: r for r in list_financials(ticker, conn=conn)}
        rats = {r["period"]: r for r in list_ratios(ticker, conn=conn)}
    finally:
        conn.close()
    merged = []
    for period in fins:
        row = {**fins[period], **{k: v for k, v in rats.get(period, {}).items() if k != "period"}}
        merged.append(row)
    return _sort_by_period_desc(merged)[:limit]

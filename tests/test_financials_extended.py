import sqlite3
import tempfile
from pathlib import Path

from app.io import financials as fin_io
from app import config as cfg


def test_load_alias_map_returns_dict():
    m = fin_io.load_alias_map()
    assert isinstance(m, dict)
    assert "revenue" in m


def test_alias_map_has_a_share_and_us_gaap():
    m = fin_io.load_alias_map()
    rev = m["revenue"]
    assert "a_share" in rev
    assert "us_gaap" in rev
    assert "营业收入" in rev["a_share"]
    assert any(alias.lower() == "revenue" or "net sales" in alias.lower() for alias in rev["us_gaap"])


def test_alias_map_covers_key_lines():
    m = fin_io.load_alias_map()
    for key in ("revenue", "cost_of_revenue", "operating_income", "net_income",
                "total_assets", "total_equity", "operating_cashflow", "capex"):
        assert key in m, f"alias map missing {key}"


def test_normalize_raw_key_to_standard():
    assert fin_io.normalize_raw_key("营业收入", market="SSE") == "revenue"
    assert fin_io.normalize_raw_key("Net sales", market="US") == "revenue"
    assert fin_io.normalize_raw_key("unknown_column", market="US") is None


def test_financials_schema_has_all_new_columns(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    fin_io.init_schema(conn)
    cursor = conn.execute("PRAGMA table_info(financials)")
    columns = {row[1] for row in cursor.fetchall()}
    # All line items must be columns
    for col in cfg.INCOME_STATEMENT_LINES + cfg.BALANCE_SHEET_LINES + cfg.CASHFLOW_LINES:
        assert col in columns, f"financials table missing column {col}"
    conn.close()


def test_alter_table_migration_preserves_legacy_data(tmp_path):
    """Simulate: existing DB with old 8-col schema, run init_schema, old data survives."""
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    # Create OLD schema (8 cols only)
    conn.executescript("""
        CREATE TABLE financials (
            ticker TEXT NOT NULL, period TEXT NOT NULL, period_type TEXT NOT NULL,
            revenue REAL, gross_profit REAL, operating_income REAL, net_income REAL,
            total_assets REAL, total_equity REAL, operating_cashflow REAL,
            shares_outstanding REAL, source_file TEXT,
            PRIMARY KEY (ticker, period)
        );
    """)
    conn.execute("INSERT INTO financials VALUES ('600519', '2023A', 'annual', 100, 90, 80, 70, 1000, 800, 85, 10, 'legacy.pdf')")
    conn.commit()

    # Run new init_schema — should ALTER to add missing columns
    fin_io.init_schema(conn)

    # Legacy data survives with NULL for new columns
    row = conn.execute("SELECT revenue, inventory, capex FROM financials WHERE ticker='600519'").fetchone()
    assert row[0] == 100  # legacy revenue preserved
    assert row[1] is None  # new inventory column is NULL
    assert row[2] is None  # new capex column is NULL
    conn.close()

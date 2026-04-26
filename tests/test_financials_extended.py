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


def test_recompute_ratios_produces_dupont(tmp_path):
    db_path = tmp_path / "t.db"
    conn = sqlite3.connect(str(db_path))
    fin_io.init_schema(conn)
    conn.execute("""
        INSERT INTO financials (ticker, period, period_type,
            revenue, net_income, total_assets, total_equity, operating_cashflow, capex)
        VALUES ('T', '2023A', 'annual', 1000, 100, 2000, 500, 120, 30)
    """)
    conn.commit()
    fin_io.recompute_ratios(conn, "T")

    row = conn.execute("""SELECT net_margin, asset_turnover, equity_multiplier,
                          roe, fcf, fcf_margin, ocf_quality
                          FROM ratios WHERE ticker='T' AND period='2023A'""").fetchone()
    net_margin, asset_turn, eq_mult, roe, fcf, fcf_margin, ocf_q = row
    assert net_margin == 0.1         # 100/1000
    assert asset_turn == 0.5          # 1000/2000
    assert eq_mult == 4.0             # 2000/500
    assert roe == 0.2                 # 100/500
    assert abs(roe - net_margin * asset_turn * eq_mult) < 1e-9  # DuPont identity
    assert fcf == 90                  # 120 - 30
    assert fcf_margin == 0.09         # 90/1000
    assert ocf_q == 1.2                # 120/100


def test_recompute_ratios_ccc(tmp_path):
    db_path = tmp_path / "ccc.db"
    conn = sqlite3.connect(str(db_path))
    fin_io.init_schema(conn)
    conn.execute("""
        INSERT INTO financials (ticker, period, period_type,
            revenue, cost_of_revenue, inventory, accounts_receivable, accounts_payable)
        VALUES ('T', '2023A', 'annual', 3650, 2190, 300, 400, 200)
    """)
    conn.commit()
    fin_io.recompute_ratios(conn, "T")

    row = conn.execute("""SELECT days_inventory, days_receivable, days_payable, cash_conversion_cycle
                          FROM ratios WHERE ticker='T'""").fetchone()
    d_inv, d_ar, d_ap, ccc = row
    # days_inventory = inventory / cost_of_revenue * 365 = 300/2190*365 ≈ 50
    assert abs(d_inv - 50.0) < 0.5
    # days_receivable = ar / revenue * 365 = 400/3650*365 = 40
    assert abs(d_ar - 40.0) < 0.5
    # days_payable = ap / cost_of_revenue * 365 = 200/2190*365 ≈ 33.33
    assert abs(d_ap - 33.3) < 0.5
    # ccc = d_inv + d_ar - d_ap
    assert abs(ccc - (d_inv + d_ar - d_ap)) < 0.01


def test_recompute_ratios_handles_null_gracefully(tmp_path):
    """Missing columns must not cause divide-by-zero errors."""
    db_path = tmp_path / "nulls.db"
    conn = sqlite3.connect(str(db_path))
    fin_io.init_schema(conn)
    conn.execute("""
        INSERT INTO financials (ticker, period, period_type, revenue)
        VALUES ('T', '2023A', 'annual', 1000)
    """)
    conn.commit()
    fin_io.recompute_ratios(conn, "T")  # must not raise
    row = conn.execute("SELECT net_margin, fcf, cash_conversion_cycle FROM ratios WHERE ticker='T'").fetchone()
    # missing net_income / ocf / capex / inventory → NULL
    assert row is not None
    assert row[0] is None
    assert row[1] is None

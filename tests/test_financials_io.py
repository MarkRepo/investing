"""Unit tests for app.io.financials.

Uses tmp_path to isolate the SQLite file. We talk to financials via its public
API rather than raw SQL so we notice when behavior drifts.
"""
from pathlib import Path

import pytest

from app.io import financials as fin


SAMPLE_CSV = """period,period_type,revenue,gross_profit,operating_income,net_income,total_assets,total_equity,operating_cashflow,shares_outstanding,short_term_debt,long_term_debt
2024Q4,quarterly,1000,400,200,150,5000,2000,180,100,1000,2000
2024Q3,quarterly,900,360,170,120,4800,1950,160,100,1000,1900
2024A,annual,3500,1400,700,500,5000,2000,650,100,1000,2000
"""


def test_import_roundtrip(tmp_path: Path):
    n = fin.import_financials_csv("hims", SAMPLE_CSV, source_file="hims-2024.csv", base=tmp_path)
    assert n == 3

    rows = fin.list_financials("HIMS", base=tmp_path)
    assert [r["period"] for r in rows] == ["2024A", "2024Q4", "2024Q3"]
    assert rows[0]["revenue"] == 3500
    assert rows[0]["source_file"] == "hims-2024.csv"


def test_ratios_computed(tmp_path: Path):
    fin.import_financials_csv("HIMS", SAMPLE_CSV, base=tmp_path)
    rats = {r["period"]: r for r in fin.list_ratios("HIMS", base=tmp_path)}

    q4 = rats["2024Q4"]
    assert q4["gross_margin"] == pytest.approx(0.40)
    assert q4["net_margin"] == pytest.approx(0.15)
    assert q4["operating_margin"] == pytest.approx(0.20)
    # ROE = net_income / total_equity = 150 / 2000
    assert q4["roe"] == pytest.approx(0.075)
    assert q4["roa"] == pytest.approx(150 / 5000)
    # D/E = (assets - equity) / equity = (5000-2000)/2000 = 1.5
    assert q4["debt_to_equity"] == pytest.approx(1.5)


def test_reimport_overwrites_by_primary_key(tmp_path: Path):
    fin.import_financials_csv("HIMS", SAMPLE_CSV, base=tmp_path)
    # Reimport with a revised number for the same period
    revised = (
        "period,period_type,revenue,gross_profit,operating_income,net_income,"
        "total_assets,total_equity,operating_cashflow,shares_outstanding\n"
        "2024Q4,quarterly,1100,450,220,165,5100,2050,190,100\n"
    )
    fin.import_financials_csv("HIMS", revised, base=tmp_path)

    rows = fin.list_financials("HIMS", base=tmp_path)
    q4 = next(r for r in rows if r["period"] == "2024Q4")
    assert q4["revenue"] == 1100
    assert q4["net_income"] == 165

    # Ratios reflect the revised numbers
    q4_r = next(r for r in fin.list_ratios("HIMS", base=tmp_path) if r["period"] == "2024Q4")
    assert q4_r["gross_margin"] == pytest.approx(450 / 1100)


def test_empty_and_null_cells(tmp_path: Path):
    # operating_cashflow left blank, shares_outstanding as "-"
    csv_text = (
        "period,period_type,revenue,gross_profit,operating_income,net_income,"
        "total_assets,total_equity,operating_cashflow,shares_outstanding\n"
        "2024Q4,quarterly,1000,400,,100,5000,0,,-\n"
    )
    fin.import_financials_csv("X", csv_text, base=tmp_path)
    rows = fin.list_financials("X", base=tmp_path)
    assert rows[0]["operating_income"] is None
    assert rows[0]["operating_cashflow"] is None
    assert rows[0]["shares_outstanding"] is None

    # ROE with zero equity must not blow up; just returns None
    q4_r = fin.list_ratios("X", base=tmp_path)[0]
    assert q4_r["roe"] is None
    assert q4_r["debt_to_equity"] is None


def test_rejects_bad_period(tmp_path: Path):
    bad = "period,period_type,revenue\n2024-Q4,quarterly,1000\n"
    with pytest.raises(ValueError, match="invalid period"):
        fin.import_financials_csv("X", bad, base=tmp_path)


def test_rejects_period_type_mismatch(tmp_path: Path):
    bad = "period,period_type,revenue\n2024A,quarterly,1000\n"
    with pytest.raises(ValueError, match="implies annual"):
        fin.import_financials_csv("X", bad, base=tmp_path)


def test_rejects_missing_header(tmp_path: Path):
    bad = "period,revenue\n2024Q4,1000\n"
    with pytest.raises(ValueError, match="missing required"):
        fin.import_financials_csv("X", bad, base=tmp_path)


def test_period_sort_quarterly_then_annual(tmp_path: Path):
    # Annual of same year should list above quarterly (higher sort key)
    csv_text = (
        "period,period_type,revenue,gross_profit,operating_income,net_income,"
        "total_assets,total_equity,operating_cashflow,shares_outstanding\n"
        "2023A,annual,3000,1200,600,400,4500,1800,600,100\n"
        "2024Q1,quarterly,900,360,170,120,4800,1950,160,100\n"
        "2024A,annual,3500,1400,700,500,5000,2000,650,100\n"
    )
    fin.import_financials_csv("X", csv_text, base=tmp_path)
    periods = [r["period"] for r in fin.list_financials("X", base=tmp_path)]
    assert periods == ["2024A", "2024Q1", "2023A"]


def test_upsert_company_mirrors_meta(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        fin.upsert_company(
            conn,
            {
                "ticker": "hims",
                "market": "US",
                "name": "Hims & Hers",
                "industry_primary": "consumer_health",
                "currency": "USD",
            },
        )
        row = conn.execute("SELECT * FROM companies WHERE ticker = 'HIMS'").fetchone()
        assert row is not None
        assert row["market"] == "US"
        assert row["name"] == "Hims & Hers"
    finally:
        conn.close()


def test_thousands_separator_tolerated(tmp_path: Path):
    csv_text = (
        "period,period_type,revenue,gross_profit,operating_income,net_income,"
        "total_assets,total_equity,operating_cashflow,shares_outstanding\n"
        '2024Q4,quarterly,"1,234.56",400,200,150,5000,2000,180,100\n'
    )
    fin.import_financials_csv("X", csv_text, base=tmp_path)
    assert fin.list_financials("X", base=tmp_path)[0]["revenue"] == pytest.approx(1234.56)

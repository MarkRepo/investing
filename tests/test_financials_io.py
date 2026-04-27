"""Tests for app.io.financials (two-table schema)."""
from pathlib import Path

import pytest

from app.io import financials as fin


def _cn_sample_row(period: str = "2024A", **overrides) -> dict:
    row = {
        "ticker": "600519",
        "report_date": "2024-12-31",
        "period": period,
        "period_type": "annual",
        "currency": "CNY",
        "total_revenue": 170_900_000_000.0,
        "operating_revenue": 170_900_000_000.0,
        "cost_of_revenue": 13_400_000_000.0,
        "operating_income": 107_800_000_000.0,
        "net_income": 86_200_000_000.0,
        "total_assets": 281_000_000_000.0,
        "total_equity": 234_000_000_000.0,
        "total_current_assets": 196_000_000_000.0,
        "total_current_liab": 46_000_000_000.0,
        "accounts_receivable": 120_000_000.0,
        "inventory": 46_400_000_000.0,
        "accounts_payable": 2_100_000_000.0,
        "short_term_debt": 0.0,
        "long_term_debt": 0.0,
        "interest_expense": 0.0,
        "operating_cashflow": 96_600_000_000.0,
        "capex": 3_400_000_000.0,
        "source": "akshare",
    }
    row.update(overrides)
    return row


def _us_sample_row(period: str = "2024A", **overrides) -> dict:
    row = {
        "ticker": "HIMS",
        "report_date": "2024-12-31",
        "period": period,
        "period_type": "annual",
        "currency": "USD",
        "total_revenue": 1_480_000_000.0,
        "cost_of_revenue": 310_000_000.0,
        "gross_profit": 1_170_000_000.0,
        "operating_income": 70_000_000.0,
        "ebit": 70_000_000.0,
        "net_income": 126_000_000.0,
        "total_assets": 650_000_000.0,
        "total_equity": 410_000_000.0,
        "current_assets": 350_000_000.0,
        "current_liabilities": 150_000_000.0,
        "accounts_receivable": 12_000_000.0,
        "inventory": 85_000_000.0,
        "accounts_payable": 40_000_000.0,
        "total_debt": 15_000_000.0,
        "interest_expense": 2_000_000.0,
        "operating_cash_flow": 210_000_000.0,
        "capital_expenditure": -40_000_000.0,
        "free_cash_flow": 170_000_000.0,
        "source": "yfinance",
    }
    row.update(overrides)
    return row


# ---------- schema ----------

def test_init_creates_both_tables(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "financials_cn" in tables
        assert "financials_us" in tables
        assert "ratios" in tables
        # legacy `financials` table no longer created
        assert "financials" not in tables
    finally:
        conn.close()


def test_cn_schema_has_key_columns(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(financials_cn)").fetchall()}
        for c in ("ticker", "period", "period_type", "report_date",
                  "total_revenue", "operating_revenue", "operating_income",
                  "net_income", "total_assets", "total_equity",
                  "operating_cashflow", "capex", "goodwill",
                  "short_term_debt", "long_term_debt"):
            assert c in cols, f"financials_cn missing {c}"
    finally:
        conn.close()


def test_us_schema_has_key_columns(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(financials_us)").fetchall()}
        for c in ("ticker", "period", "period_type",
                  "total_revenue", "gross_profit", "operating_income",
                  "ebit", "ebitda", "net_income",
                  "total_assets", "total_equity", "total_debt",
                  "current_assets", "current_liabilities",
                  "operating_cash_flow", "capital_expenditure", "free_cash_flow"):
            assert c in cols, f"financials_us missing {c}"
    finally:
        conn.close()


# ---------- upsert ----------

def test_upsert_cn_rountrip(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        fin.upsert_financials_cn(conn, [_cn_sample_row("2024A"), _cn_sample_row("2023A")])
        rows = fin.list_financials_cn(conn, "600519")
        assert [r["period"] for r in rows] == ["2024A", "2023A"]
        assert rows[0]["net_income"] == 86_200_000_000.0
    finally:
        conn.close()


def test_upsert_us_roundtrip(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        fin.upsert_financials_us(conn, [_us_sample_row("2024A"), _us_sample_row("2023A")])
        rows = fin.list_financials_us(conn, "HIMS")
        assert [r["period"] for r in rows] == ["2024A", "2023A"]
        assert rows[0]["free_cash_flow"] == 170_000_000.0
    finally:
        conn.close()


def test_upsert_cn_overwrites_on_conflict(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        fin.upsert_financials_cn(conn, [_cn_sample_row("2024A", net_income=1.0)])
        fin.upsert_financials_cn(conn, [_cn_sample_row("2024A", net_income=2.0)])
        rows = fin.list_financials_cn(conn, "600519")
        assert len(rows) == 1
        assert rows[0]["net_income"] == 2.0
    finally:
        conn.close()


# ---------- ratios (market-aware) ----------

def test_recompute_ratios_cn_reads_from_cn_table(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        fin.upsert_financials_cn(conn, [_cn_sample_row("2024A")])
        fin.recompute_ratios(conn, "600519", market="SSE")
        r = conn.execute("SELECT * FROM ratios WHERE ticker='600519' AND period='2024A'").fetchone()
        assert r is not None
        # net_margin = 86.2B / 170.9B ≈ 0.504
        assert r["net_margin"] == pytest.approx(86.2e9 / 170.9e9, abs=1e-3)
        # current_ratio = 196B / 46B ≈ 4.26
        assert r["current_ratio"] == pytest.approx(196e9 / 46e9, abs=1e-2)
        # debt_to_equity = 0 / 234B = 0
        assert r["debt_to_equity"] == 0.0
        # fcf = ocf - capex = 96.6B - 3.4B = 93.2B
        assert r["fcf"] == pytest.approx(96.6e9 - 3.4e9, rel=1e-6)
    finally:
        conn.close()


def test_recompute_ratios_us_reads_from_us_table(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        fin.upsert_financials_us(conn, [_us_sample_row("2024A")])
        fin.recompute_ratios(conn, "HIMS", market="US")
        r = conn.execute("SELECT * FROM ratios WHERE ticker='HIMS' AND period='2024A'").fetchone()
        assert r is not None
        # gross_margin = 1170 / 1480 ≈ 0.79
        assert r["gross_margin"] == pytest.approx(1170 / 1480, abs=1e-3)
        # D/E = 15M / 410M
        assert r["debt_to_equity"] == pytest.approx(15 / 410, abs=1e-3)
        # FCF comes from stored free_cash_flow column when present
        assert r["fcf"] == 170_000_000.0
    finally:
        conn.close()


def test_recompute_ratios_handles_nulls(tmp_path: Path):
    """Missing inputs → NULL output (NULLIF + COALESCE guard against div/0)."""
    conn = fin.connect(base=tmp_path)
    try:
        fin.upsert_financials_cn(conn, [_cn_sample_row(
            "2024A",
            total_equity=0.0,         # triggers NULLIF → NULL roe
            cost_of_revenue=0.0,      # triggers NULLIF → NULL days_inventory
        )])
        fin.recompute_ratios(conn, "600519", market="SSE")
        r = conn.execute("SELECT roe, days_inventory FROM ratios WHERE ticker='600519'").fetchone()
        assert r["roe"] is None
        assert r["days_inventory"] is None
    finally:
        conn.close()


def test_recompute_ratios_rejects_unknown_market(tmp_path: Path):
    conn = fin.connect(base=tmp_path)
    try:
        with pytest.raises(ValueError) as exc:
            fin.recompute_ratios(conn, "FOO", market="MOON")
        assert "market" in str(exc.value).lower()
    finally:
        conn.close()


# ---------- queries ----------

def test_list_periods_for_page_newest_first(tmp_path: Path):
    """Page needs one merged row per period with ratios joined; newest first."""
    conn = fin.connect(base=tmp_path)
    try:
        fin.upsert_financials_cn(conn, [
            _cn_sample_row("2024A"),
            _cn_sample_row("2024Q3", period_type="quarterly"),
            _cn_sample_row("2023A"),
        ])
        fin.recompute_ratios(conn, "600519", market="SSE")
        merged = fin.list_periods_with_ratios(conn, "600519", market="SSE")
        assert [r["period"] for r in merged] == ["2024A", "2024Q3", "2023A"]
        assert "net_margin" in merged[0]
        assert "operating_income" in merged[0]
    finally:
        conn.close()

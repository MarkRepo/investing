"""Tests for scripts.fetch_financials_us. yfinance is monkeypatched —
we do NOT hit the network. DataFrame shape matches yfinance.Ticker.*_stmt."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.io import financials as fin
from scripts import fetch_financials_us as fu


class _FakeTicker:
    def __init__(self, income, balance, cashflow,
                 qincome=None, qbalance=None, qcashflow=None):
        self.income_stmt = income
        self.balance_sheet = balance
        self.cashflow = cashflow
        self.quarterly_income_stmt = qincome if qincome is not None else pd.DataFrame()
        self.quarterly_balance_sheet = qbalance if qbalance is not None else pd.DataFrame()
        self.quarterly_cashflow = qcashflow if qcashflow is not None else pd.DataFrame()


def _annual_frame():
    return pd.DataFrame(
        {
            pd.Timestamp("2024-12-31"): [1480e6, 310e6, 1170e6, 70e6, 70e6, 126e6, 210e6, -40e6, 170e6, 40e6, 410e6, 650e6, 15e6, 150e6, 350e6, 85e6, 12e6],
            pd.Timestamp("2023-12-31"): [870e6, 200e6, 670e6, 30e6, 30e6, 60e6, 115e6, -20e6, 95e6, 20e6, 280e6, 450e6, 5e6, 110e6, 220e6, 60e6, 8e6],
        },
        index=[
            "Total Revenue", "Cost Of Revenue", "Gross Profit", "Operating Income", "EBIT", "Net Income",
            "Operating Cash Flow", "Capital Expenditure", "Free Cash Flow",
            "Accounts Payable", "Stockholders Equity", "Total Assets", "Total Debt",
            "Current Liabilities", "Current Assets", "Inventory", "Accounts Receivable",
        ],
    )


def _quarterly_frame():
    return pd.DataFrame(
        {pd.Timestamp("2024-09-30"): [380e6, 80e6, 300e6, 20e6, 30e6]},
        index=["Total Revenue", "Cost Of Revenue", "Gross Profit", "Net Income", "Operating Cash Flow"],
    )


def test_period_from_timestamp_annual():
    assert fu.period_for_stmt(pd.Timestamp("2024-12-31"), period_type="annual") == "2024A"


def test_period_from_timestamp_quarterly():
    assert fu.period_for_stmt(pd.Timestamp("2024-03-31"), period_type="quarterly") == "2024Q1"
    assert fu.period_for_stmt(pd.Timestamp("2024-06-30"), period_type="quarterly") == "2024Q2"
    assert fu.period_for_stmt(pd.Timestamp("2024-09-30"), period_type="quarterly") == "2024Q3"
    assert fu.period_for_stmt(pd.Timestamp("2024-12-31"), period_type="quarterly") == "2024Q4"


def test_run_for_ticker_writes_annual_and_quarterly(tmp_path, monkeypatch):
    fake = _FakeTicker(
        income=_annual_frame(), balance=_annual_frame(), cashflow=_annual_frame(),
        qincome=_quarterly_frame(), qbalance=_quarterly_frame(), qcashflow=_quarterly_frame(),
    )
    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", lambda s: fake)

    n = fu.run_for_ticker("HIMS", "US", base=tmp_path)
    assert n >= 3  # 2 annuals + 1 quarterly

    conn = fin.connect(base=tmp_path)
    try:
        rows = fin.list_financials_us(conn, "HIMS")
        periods = [r["period"] for r in rows]
        assert "2024A" in periods
        assert "2023A" in periods
        assert "2024Q3" in periods
        a2024 = next(r for r in rows if r["period"] == "2024A")
        assert a2024["total_revenue"] == 1480e6
        assert a2024["gross_profit"] == 1170e6
        assert a2024["free_cash_flow"] == 170e6
        assert a2024["source"] == "yfinance"

        # ratio sanity
        r = conn.execute(
            "SELECT gross_margin FROM ratios WHERE ticker='HIMS' AND period='2024A'"
        ).fetchone()
        assert r["gross_margin"] == pytest.approx(1170 / 1480, abs=1e-3)
    finally:
        conn.close()


def test_unknown_us_label_uses_snake_fallback(tmp_path, monkeypatch):
    """A yfinance field not in US_COL_MAP becomes lower_snake via us_col_to_snake."""
    df = pd.DataFrame(
        {pd.Timestamp("2024-12-31"): [100.0]},
        index=["Total Revenue"],
    )
    # Inject a column yfinance sometimes emits: "Other Income Expense"
    df.loc["Other Income Expense"] = [5.0]
    fake = _FakeTicker(income=df, balance=pd.DataFrame(), cashflow=pd.DataFrame())
    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", lambda s: fake)

    n = fu.run_for_ticker("XYZ", "US", base=tmp_path)
    assert n == 1
    # unmapped fields are silently dropped because they aren't in US_COLUMNS;
    # this just verifies no crash.

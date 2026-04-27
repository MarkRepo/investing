"""Tests for scripts.fetch_financials_cn."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.io import financials as fin
from scripts import fetch_financials_cn as fc

FIX = Path(__file__).parent / "fixtures" / "financials"


@pytest.fixture
def mock_ak_reports(monkeypatch):
    """Replace akshare.stock_financial_report_sina with CSV fixtures."""
    income = pd.read_csv(FIX / "akshare_income_sh600519.csv")
    balance = pd.read_csv(FIX / "akshare_balance_sh600519.csv")
    cashflow = pd.read_csv(FIX / "akshare_cashflow_sh600519.csv")

    def _fake(stock: str, symbol: str):
        if symbol == "利润表":
            return income.copy()
        if symbol == "资产负债表":
            return balance.copy()
        if symbol == "现金流量表":
            return cashflow.copy()
        return pd.DataFrame()

    import akshare as ak
    monkeypatch.setattr(ak, "stock_financial_report_sina", _fake)
    return _fake


def test_derive_period_from_report_row():
    # 12 月一律是年报（A 股无独立 Q4 报告；akshare 类型字段不含 "年报"）
    assert fc.derive_period("2024-12-31", "年报") == ("2024A", "annual")
    assert fc.derive_period("2024-12-31", "四季报") == ("2024A", "annual")
    assert fc.derive_period("2024-12-31", "合并期末") == ("2024A", "annual")
    assert fc.derive_period("2024-09-30", "三季报") == ("2024Q3", "quarterly")
    assert fc.derive_period("2024-06-30", "中报") == ("2024Q2", "quarterly")
    assert fc.derive_period("2024-03-31", "一季报") == ("2024Q1", "quarterly")


def test_derive_period_accepts_yyyymmdd_no_dashes():
    """akshare Sina 实际返回 '20241231' 无短横线格式；必须兼容，
    否则真实拉取时每一行都被 ValueError 跳过（曾经发生）。"""
    assert fc.derive_period("20241231", "合并期末") == ("2024A", "annual")
    assert fc.derive_period("20240930", "合并期末") == ("2024Q3", "quarterly")
    assert fc.derive_period("20240331", "合并期末") == ("2024Q1", "quarterly")


def test_sina_symbol_for_markets():
    assert fc.sina_symbol("600519", "SSE") == "sh600519"
    assert fc.sina_symbol("000001", "SZSE") == "sz000001"
    assert fc.sina_symbol("920118", "BSE") == "bj920118"
    with pytest.raises(ValueError):
        fc.sina_symbol("HIMS", "US")


def test_run_for_ticker_upserts_and_recomputes(tmp_path, mock_ak_reports):
    added = fc.run_for_ticker("600519", "SSE", base=tmp_path)
    assert added == 2  # 2024A + 2024Q3 merged
    conn = fin.connect(base=tmp_path)
    try:
        rows = fin.list_financials_cn(conn, "600519")
        assert [r["period"] for r in rows] == ["2024A", "2024Q3"]
        a = rows[0]
        assert a["net_income"] == 86_200_000_000.0
        assert a["goodwill"] == 0.0
        assert a["operating_cashflow"] == 96_600_000_000.0
        assert a["capex"] == 3_400_000_000.0
        # ratios should be there too
        r = conn.execute(
            "SELECT net_margin FROM ratios WHERE ticker='600519' AND period='2024A'"
        ).fetchone()
        assert r["net_margin"] == pytest.approx(86.2e9 / 170.9e9, abs=1e-3)
    finally:
        conn.close()


def test_unknown_chinese_column_logged_not_fatal(tmp_path, monkeypatch, caplog):
    import akshare as ak
    df = pd.DataFrame({
        "报告日": ["2024-12-31"], "类型": ["年报"],
        "营业总收入": [100.0],
        "未知字段XYZ": [42.0],
    })
    monkeypatch.setattr(
        ak, "stock_financial_report_sina",
        lambda stock, symbol: df.copy() if symbol == "利润表" else pd.DataFrame()
    )
    import logging
    caplog.set_level(logging.WARNING)
    added = fc.run_for_ticker("600519", "SSE", base=tmp_path)
    assert added == 1
    # warning surfaced for unmapped column
    assert any("未知字段XYZ" in rec.message for rec in caplog.records)

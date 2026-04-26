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

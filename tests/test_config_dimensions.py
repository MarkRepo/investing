from app import config as cfg


def test_industry_dimensions_is_11_tuple():
    assert isinstance(cfg.INDUSTRY_DIMENSIONS, tuple)
    assert len(cfg.INDUSTRY_DIMENSIONS) == 11
    assert cfg.INDUSTRY_DIMENSIONS[0] == "definition"
    assert "market_size" in cfg.INDUSTRY_DIMENSIONS
    assert "valuation" in cfg.INDUSTRY_DIMENSIONS


def test_arena_dimensions_is_6_tuple():
    assert isinstance(cfg.ARENA_DIMENSIONS, tuple)
    assert len(cfg.ARENA_DIMENSIONS) == 6
    assert cfg.ARENA_DIMENSIONS == (
        "definition", "participants", "decisive_factors",
        "trajectory", "narratives", "investment_view",
    )


def test_company_dimensions_is_8_tuple():
    assert isinstance(cfg.COMPANY_DIMENSIONS, tuple)
    assert len(cfg.COMPANY_DIMENSIONS) == 8
    assert cfg.COMPANY_DIMENSIONS == (
        "business_model", "moat", "growth_engine", "management",
        "financial_profile", "catalysts", "risks", "valuation",
    )


def test_industry_fields_is_dict_keyed_by_dimension():
    assert isinstance(cfg.INDUSTRY_FIELDS, dict)
    for dim in cfg.INDUSTRY_FIELDS:
        assert dim in cfg.INDUSTRY_DIMENSIONS
    # market_size must have tam_global etc.
    assert "tam_global" in cfg.INDUSTRY_FIELDS["market_size"]
    assert "cagr_global" in cfg.INDUSTRY_FIELDS["market_size"]


def test_no_valid_sectors():
    assert not hasattr(cfg, "VALID_SECTORS")


def test_income_statement_lines_is_18_tuple():
    assert isinstance(cfg.INCOME_STATEMENT_LINES, tuple)
    assert len(cfg.INCOME_STATEMENT_LINES) == 18
    assert "revenue" in cfg.INCOME_STATEMENT_LINES
    assert "cost_of_revenue" in cfg.INCOME_STATEMENT_LINES
    assert "operating_income" in cfg.INCOME_STATEMENT_LINES
    assert "net_income" in cfg.INCOME_STATEMENT_LINES
    assert "eps_diluted" in cfg.INCOME_STATEMENT_LINES


def test_balance_sheet_lines_is_20_tuple():
    assert isinstance(cfg.BALANCE_SHEET_LINES, tuple)
    assert len(cfg.BALANCE_SHEET_LINES) == 20
    assert "cash_and_equivalents" in cfg.BALANCE_SHEET_LINES
    assert "inventory" in cfg.BALANCE_SHEET_LINES
    assert "total_assets" in cfg.BALANCE_SHEET_LINES
    assert "long_term_debt" in cfg.BALANCE_SHEET_LINES
    assert "total_equity" in cfg.BALANCE_SHEET_LINES


def test_cashflow_lines_is_16_tuple():
    assert isinstance(cfg.CASHFLOW_LINES, tuple)
    assert len(cfg.CASHFLOW_LINES) == 16
    assert "depreciation_amortization" in cfg.CASHFLOW_LINES
    assert "operating_cashflow" in cfg.CASHFLOW_LINES
    assert "capex" in cfg.CASHFLOW_LINES
    assert "dividends" in cfg.CASHFLOW_LINES


def test_financial_lines_superset_of_legacy():
    """Legacy 8 columns must all survive."""
    all_lines = set(cfg.INCOME_STATEMENT_LINES) | set(cfg.BALANCE_SHEET_LINES) | set(cfg.CASHFLOW_LINES)
    legacy = {"revenue", "gross_profit", "operating_income", "net_income",
              "total_assets", "total_equity", "operating_cashflow"}
    assert legacy.issubset(all_lines)

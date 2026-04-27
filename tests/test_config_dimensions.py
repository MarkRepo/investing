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


def test_cn_us_col_maps_present():
    """Financial line-item tuples were replaced by CN/US column maps
    (API-sourced financials, not LLM-extracted)."""
    assert not hasattr(cfg, "INCOME_STATEMENT_LINES")
    assert isinstance(cfg.CN_COL_MAP, dict) and len(cfg.CN_COL_MAP) > 50
    assert isinstance(cfg.US_COL_MAP, dict) and len(cfg.US_COL_MAP) > 30
    assert cfg.us_col_to_snake("Free Cash Flow") == "free_cash_flow"
    assert cfg.us_col_to_snake("Unknown Field") == "unknown_field"

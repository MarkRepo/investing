from scripts import ingest_aggregate as agg


def test_ensure_industry_exists_creates_when_missing(tmp_path):
    from app.io import industry as industry_io
    base = tmp_path / "industries"
    base.mkdir()
    result = agg.ensure_industry_exists(
        slug="cn-new-industry",
        name="中国新行业",
        scope="主题",
        base=base,
    )
    assert result["autobuilt"] is True
    assert result["slug"] == "cn-new-industry"
    assert (base / "cn-new-industry" / "meta.yaml").is_file()
    # 11 narrative skeletons
    for dim in ("market-size", "competition", "valuation"):
        assert (base / "cn-new-industry" / f"{dim}.md").is_file()


def test_ensure_industry_exists_noop_when_present(tmp_path):
    from app.io import industry as industry_io
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="existing", name="E", scope="", base=base)
    result = agg.ensure_industry_exists(
        slug="existing", name="E", scope="", base=base,
    )
    assert result["autobuilt"] is False


def test_ensure_company_exists_creates_when_missing(tmp_path):
    base = tmp_path / "companies"
    base.mkdir()
    result = agg.ensure_company_exists(
        ticker="688019", market="SSE", name="安集科技",
        industry_slugs=["cn-cmp-material"],
        currency="CNY",
        base=base,
    )
    assert result["autobuilt"] is True
    assert (base / "SSE_688019" / "meta.md").is_file()


def test_ensure_company_exists_noop_when_present(tmp_path):
    from app.io import company as company_io
    base = tmp_path / "companies"
    base.mkdir()
    company_io.create_company(ticker="600519", market="SSE", name="Moutai",
                              industry_slugs=[], base=base)
    result = agg.ensure_company_exists(
        ticker="600519", market="SSE", name="Moutai",
        industry_slugs=[], currency="CNY",
        base=base,
    )
    assert result["autobuilt"] is False

from scripts import ingest_aggregate as agg


def test_ensure_industry_exists_creates_when_missing(tmp_path):
    from app.io import industry as industry_io
    base = tmp_path
    result = agg.ensure_industry_exists(
        slug="cn-new-industry",
        name="中国新行业",
        scope="主题",
        base=base,
    )
    assert result["autobuilt"] is True
    assert result["slug"] == "cn-new-industry"
    assert (base / "industries" / "cn-new-industry" / "meta.yaml").is_file()
    # 11 narrative skeletons
    for dim in ("market-size", "competition", "valuation"):
        assert (base / "industries" / "cn-new-industry" / f"{dim}.md").is_file()


def test_ensure_industry_exists_noop_when_present(tmp_path):
    from app.io import industry as industry_io
    base = tmp_path
    industry_io.create_industry(slug="existing", name="E", scope="", base=base)
    result = agg.ensure_industry_exists(
        slug="existing", name="E", scope="", base=base,
    )
    assert result["autobuilt"] is False


def test_ensure_company_exists_creates_when_missing(tmp_path):
    base = tmp_path
    result = agg.ensure_company_exists(
        ticker="688019", market="SSE", name="安集科技",
        industry_slugs=["cn-cmp-material"],
        currency="CNY",
        base=base,
    )
    assert result["autobuilt"] is True
    assert (base / "companies" / "SSE_688019" / "meta.md").is_file()


def test_ensure_company_exists_noop_when_present(tmp_path):
    from app.io import company as company_io
    base = tmp_path
    company_io.create_company(ticker="600519", market="SSE", name="Moutai",
                              industry_slugs=[], base=base)
    result = agg.ensure_company_exists(
        ticker="600519", market="SSE", name="Moutai",
        industry_slugs=[], currency="CNY",
        base=base,
    )
    assert result["autobuilt"] is False


def test_bootstrap_arena_creates_definition_and_skeletons(tmp_path):
    """After user approves, this helper actually writes arena files."""
    from app.io import arenas as arenas_io
    from app import config as cfg
    base = tmp_path
    proposal = {
        "slug": "cn-test-arena",
        "name": "测试战场",
        "industry": "cn-cmp-material",
        "battleground_focus": "国产化之战",
        "participants": [{"name": "A", "role": "challenger"}],
    }
    agg.bootstrap_arena(proposal, base=base)
    # 5 narrative skeletons (excluding definition which is already written)
    for dim in cfg.ARENA_DIMENSIONS:
        if dim == "definition":
            continue
        assert (base / "arenas" / "cn-test-arena" / f"{dim.replace('_', '-')}.md").is_file()
    # definition.md frontmatter
    r = arenas_io.read_definition("cn-test-arena", base=base)
    fm = r["frontmatter"]
    assert fm["industry"] == "cn-cmp-material"
    assert fm["battleground_focus"] == "国产化之战"

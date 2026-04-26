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


def test_propose_arena_bootstrap_normalizes_slug():
    proposed = [
        {"tentative_slug": "CN-CMP-Slurry-Domestic-Substitution",
         "battleground_focus": "国产 CMP 抛光液挑战 Dupont/Cabot/Versum",
         "tentative_participants": [
             {"name": "安集", "role": "challenger"},
             {"name": "Dupont", "role": "incumbent"},
         ],
         "parent_industry_slug": "cn-cmp-material"},
    ]
    out = agg.propose_arena_bootstrap(proposed)
    assert len(out) == 1
    a = out[0]
    assert a["slug"] == "cn-cmp-slurry-domestic-substitution"  # lowercased
    assert a["industry"] == "cn-cmp-material"
    assert a["battleground_focus"] == "国产 CMP 抛光液挑战 Dupont/Cabot/Versum"
    assert a["participants"] == [
        {"name": "安集", "role": "challenger"},
        {"name": "Dupont", "role": "incumbent"},
    ]


def test_propose_arena_bootstrap_drops_missing_focus():
    proposed = [
        {"tentative_slug": "good", "battleground_focus": "focus",
         "parent_industry_slug": "i", "tentative_participants": []},
        {"tentative_slug": "bad-no-focus", "battleground_focus": "",
         "parent_industry_slug": "i", "tentative_participants": []},
    ]
    out = agg.propose_arena_bootstrap(proposed)
    assert [a["slug"] for a in out] == ["good"]


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

from scripts import ingest_aggregate as agg


def test_write_figure_contexts_attaches_source_id(tmp_path):
    from app.io import industry as industry_io
    from app.io import figure_contexts as fc_io
    base = tmp_path
    industry_io.create_industry(slug="cn-cmp-material", name="X", scope="", base=base)

    preprocess_contexts = [
        {"id": "fig-001", "page": None,
         "caption": "图表1: 全球市场规模",
         "surrounding_text": "2025 市场规模 33.8 亿美元",
         "section_name": "market_size"},
    ]
    source_meta = {"source_id": "行研-X-2026-03-10-abcd1234", "institution": "X",
                   "date": "2026-03-10", "sha8": "abcd1234"}
    n = agg.write_figure_contexts(
        slug="cn-cmp-material",
        contexts=preprocess_contexts,
        source_meta=source_meta,
        base=base,
    )
    assert n == 1
    rows = fc_io.read_figure_contexts("cn-cmp-material", base=base)
    assert rows[0]["source_id"] == "行研-X-2026-03-10-abcd1234"
    assert rows[0]["caption"].startswith("图表1")

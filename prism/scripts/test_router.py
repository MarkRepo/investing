from prism.scripts.router import classify_intent, rank_providers


class _FakeProvider:
    def __init__(self, name, caps, healthy=True):
        self.name = name
        self.capabilities = caps
        self._h = healthy
    def healthy(self):
        return self._h


def test_classify_intent_news_keywords():
    assert classify_intent("FDA 2026 Q1 approval") == "news"
    assert classify_intent("uranium spot price last week") == "news"


def test_classify_intent_semantic_phrases():
    assert classify_intent("papers similar to GLP-1 cardiovascular outcome") == "semantic"
    assert classify_intent("companies like Cameco") == "semantic"


def test_classify_intent_exact_with_site_op():
    assert classify_intent("site:sec.gov 10-K Cameco 2025") == "exact"


def test_classify_intent_vertical_patent():
    assert classify_intent("patent SMR reactor cooling") == "vertical:patent"
    assert classify_intent("scholar GLP-1 cardiovascular") == "vertical:scholar"


def test_classify_intent_general_fallback():
    assert classify_intent("uranium market overview") == "general"


def test_rank_providers_news_prefers_tavily():
    tav = _FakeProvider("tavily", {"news", "time_filter"})
    exa = _FakeProvider("exa", {"semantic"})
    ser = _FakeProvider("serper", {"general"})
    ranked = rank_providers([tav, exa, ser], intent="news")
    assert ranked[0].name == "tavily"


def test_rank_providers_semantic_prefers_exa():
    tav = _FakeProvider("tavily", {"news"})
    exa = _FakeProvider("exa", {"semantic"})
    ser = _FakeProvider("serper", {"general"})
    ranked = rank_providers([tav, exa, ser], intent="semantic")
    assert ranked[0].name == "exa"


def test_rank_providers_exact_prefers_serper():
    tav = _FakeProvider("tavily", {"news"})
    ser = _FakeProvider("serper", {"general"})
    ranked = rank_providers([tav, ser], intent="exact")
    assert ranked[0].name == "serper"


def test_rank_providers_skips_unhealthy():
    tav = _FakeProvider("tavily", {"news"}, healthy=False)
    ser = _FakeProvider("serper", {"general"})
    ranked = rank_providers([tav, ser], intent="news")
    assert all(p.name != "tavily" for p in ranked)

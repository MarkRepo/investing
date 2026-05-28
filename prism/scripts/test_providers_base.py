from prism.scripts.providers.base import Hit, ProviderError, NoKeyAvailable


def test_hit_to_dict_round_trip():
    h = Hit(
        title="t", url="https://example.com/a", snippet="s",
        score=0.8, raw_content=None, published_at=None,
        source_provider="tavily",
    )
    d = h.to_dict()
    assert d["title"] == "t"
    assert d["url"] == "https://example.com/a"
    assert d["snippet"] == "s"
    assert d["score"] == 0.8
    assert d["source_provider"] == "tavily"
    assert {"title", "url", "snippet"} <= d.keys()


def test_provider_error_chain():
    inner = RuntimeError("boom")
    err = ProviderError("tavily failed", provider="tavily", retryable=True)
    err.__cause__ = inner
    assert err.provider == "tavily"
    assert err.retryable is True
    assert "tavily failed" in str(err)


def test_no_key_available_inherits_provider_error():
    err = NoKeyAvailable(provider="tavily", soonest_recovery=None)
    assert isinstance(err, ProviderError)
    assert err.provider == "tavily"

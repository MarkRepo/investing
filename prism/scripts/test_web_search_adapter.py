import json
from unittest.mock import MagicMock

import pytest

from prism.scripts.providers.base import Hit, ProviderError
from prism.scripts.web_search import WebSearchAdapter


class _StubProvider:
    def __init__(self, name, caps, hits=None, raises=None, healthy=True):
        self.name = name
        self.capabilities = caps
        self._hits = hits or []
        self._raises = raises
        self._h = healthy
        self.calls = 0

    def healthy(self):
        return self._h

    def search(self, query, **kwargs):
        self.calls += 1
        if self._raises:
            raise self._raises
        return self._hits


def _hit(url, score=0.8, prov="tavily"):
    return Hit(title="t", url=url, snippet="s", score=score, source_provider=prov)


def test_adapter_returns_hits_from_top_provider():
    p1 = _StubProvider("tavily", {"news"}, hits=[_hit("https://reuters.com/a")])
    p2 = _StubProvider("serper", {"general"}, hits=[_hit("https://example.com/b")])
    adp = WebSearchAdapter([p1, p2])
    hits = adp.search("FDA approval 2026")
    assert len(hits) == 1
    assert p1.calls == 1 and p2.calls == 0


def test_adapter_falls_back_on_provider_error():
    err = ProviderError("boom", provider="tavily")
    p1 = _StubProvider("tavily", {"news"}, raises=err)
    p2 = _StubProvider("serper", {"general"}, hits=[_hit("https://x.com/y")])
    adp = WebSearchAdapter([p1, p2])
    hits = adp.search("FDA approval 2026")
    assert len(hits) == 1
    assert hits[0].source_provider in {"tavily", "serper"}
    assert p1.calls == 1 and p2.calls == 1


def test_adapter_soft_fallback_on_low_score():
    p1 = _StubProvider("tavily", {"news"}, hits=[_hit("https://a.com", score=0.1)])
    p2 = _StubProvider("serper", {"general"}, hits=[_hit("https://b.com", score=0.9)])
    adp = WebSearchAdapter([p1, p2], min_score=0.3)
    hits = adp.search("FDA approval 2026")
    assert hits[0].url == "https://b.com"


def test_adapter_postprocess_assigns_domain_tier():
    p1 = _StubProvider("tavily", {"news"}, hits=[
        _hit("https://reuters.com/a"),
        _hit("https://twitter.com/b"),
    ])
    adp = WebSearchAdapter([p1], cluster=None)
    hits = adp.search("oil prices")
    tiers = {h.url: h.domain_tier for h in hits}
    assert tiers["https://reuters.com/a"] == "llm-judged-official"
    assert tiers["https://twitter.com/b"] == "other"


def test_adapter_dedup_by_canonical_url():
    p1 = _StubProvider("tavily", {"news"}, hits=[
        _hit("https://reuters.com/a"),
        _hit("https://reuters.com/a?utm_source=x"),
    ])
    adp = WebSearchAdapter([p1])
    hits = adp.search("oil prices")
    assert len(hits) == 1


def test_adapter_raises_when_all_providers_exhausted():
    err = ProviderError("dead", provider="tavily")
    p1 = _StubProvider("tavily", {"news"}, raises=err)
    p2 = _StubProvider("serper", {"general"}, raises=err)
    adp = WebSearchAdapter([p1, p2])
    with pytest.raises(RuntimeError):
        adp.search("query")


def test_cli_postprocess_reads_stdin_and_writes_sidecar(monkeypatch, capsys):
    """主 agent 把 WebSearch tool 拿到的 hits 通过 stdin 喂进来，跑 dedup + domain_tier
    后调 register_web_search_batch（mock）。
    """
    import json as _json
    from prism.scripts import web_search as ws

    captured_call = {}
    def _fake_register(**kwargs):
        captured_call.update(kwargs)
        return {"n_high": 1, "n_mid": 0, "n_low": 0,
                "mat_ids": ["mat-aaa"], "duplicates": 0}

    import prism.scripts.web_prescan as wp
    monkeypatch.setattr(wp, "register_web_search_batch", _fake_register)

    payload = _json.dumps([
        {"title": "T", "url": "https://reuters.com/x", "snippet": "s"},
        {"title": "T2", "url": "https://reuters.com/x?utm_source=fb",
         "snippet": "dup"},
    ])
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))

    rc = ws.main([
        "postprocess",
        "--source", "websearch_fallback",
        "--query", "uranium",
        "--cluster", "uranium-nuclear",
        "--slug", "global-uranium-supply",
        "--variant", "claude-opus-4-7",
        "--triggered-by", "00-prescan-fallback",
        "--addresses", "thesis-1",
    ])
    assert rc == 0
    assert len(captured_call["hits"]) == 1
    assert captured_call["hits"][0]["source_provider"] == "websearch_fallback"
    assert captured_call["hits"][0]["domain_tier"] == "llm-judged-official"
    assert captured_call["triggered_by"] == "00-prescan-fallback"


def test_cli_search_writes_json_to_stdout(monkeypatch, capsys):
    """CLI smoke: stub provider, --output stdout returns JSON."""
    from prism.scripts import web_search as ws

    p1 = _StubProvider("tavily", {"news", "general"}, hits=[
        _hit("https://reuters.com/x"),
    ])
    monkeypatch.setattr(ws, "_default_providers", lambda: [p1])

    rc = ws.main(["search", "uranium", "--max-results", "1", "--output", "stdout"])
    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert isinstance(payload, list)
    assert payload[0]["url"] == "https://reuters.com/x"

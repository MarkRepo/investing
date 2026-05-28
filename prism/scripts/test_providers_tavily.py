import json
from unittest.mock import MagicMock, patch

import pytest

from prism.scripts.providers.tavily import TavilyProvider
from prism.scripts.providers.base import ProviderError, Hit


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "prism.scripts.providers.keypool._STATE_PATH",
        tmp_path / "web_search_keys.json",
    )


def _mock_resp(payload: dict):
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    cm.__exit__.return_value = False
    return cm


def test_search_returns_hit_list(tmp_state):
    p = TavilyProvider(keys=["k1aaaa"])
    payload = {
        "results": [
            {"title": "T1", "url": "https://reuters.com/x",
             "content": "snip", "score": 0.9},
            {"title": "T2", "url": "https://bloomberg.com/y",
             "content": "snip2", "score": 0.7},
        ]
    }
    with patch("urllib.request.urlopen", return_value=_mock_resp(payload)):
        hits = p.search("uranium price", max_results=2)
    assert len(hits) == 2
    assert isinstance(hits[0], Hit)
    assert hits[0].url == "https://reuters.com/x"
    assert hits[0].source_provider == "tavily"


def test_search_429_rotates_to_next_key(tmp_state):
    p = TavilyProvider(keys=["k1aaaa", "k2bbbb"])

    import urllib.error
    err = urllib.error.HTTPError(
        url="https://api.tavily.com/search", code=429,
        msg="Too Many Requests", hdrs={}, fp=None,
    )
    ok_payload = {"results": [{"title": "T", "url": "https://a.com",
                               "content": "s", "score": 0.5}]}
    seq = [err, _mock_resp(ok_payload)]

    def _side(*args, **kwargs):
        item = seq.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    with patch("urllib.request.urlopen", side_effect=_side):
        hits = p.search("q")
    assert len(hits) == 1


def test_search_all_keys_exhausted_raises(tmp_state):
    p = TavilyProvider(keys=["k1aaaa"])
    import urllib.error
    err = urllib.error.HTTPError(
        url="https://api.tavily.com/search", code=429,
        msg="Too Many Requests", hdrs={}, fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(ProviderError):
            p.search("q")


def test_search_capabilities():
    assert TavilyProvider.capabilities >= {"time_filter", "extract", "news"}
    assert TavilyProvider.name == "tavily"

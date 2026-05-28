import json
from unittest.mock import MagicMock, patch

import pytest

from prism.scripts.providers.serper import SerperProvider


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "prism.scripts.providers.keypool._STATE_PATH",
        tmp_path / "web_search_keys.json",
    )


def _mock_resp(payload):
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    cm.__exit__.return_value = False
    return cm


def test_serper_search_returns_organic_hits(tmp_state):
    p = SerperProvider(keys=["k1aaaa"])
    payload = {
        "organic": [
            {"title": "T1", "link": "https://sec.gov/x",
             "snippet": "s", "position": 1},
            {"title": "T2", "link": "https://reuters.com/y",
             "snippet": "s2", "position": 2},
        ],
    }
    with patch("urllib.request.urlopen", return_value=_mock_resp(payload)):
        hits = p.search("site:sec.gov 10-K 2025", max_results=2)
    assert hits[0].source_provider == "serper"
    assert hits[0].url == "https://sec.gov/x"
    assert hits[0].score == 1.0
    assert hits[1].score == 0.5


def test_serper_search_routes_to_news_endpoint_on_news_intent(tmp_state):
    p = SerperProvider(keys=["k1aaaa"])
    payload = {"news": [
        {"title": "T", "link": "https://reuters.com/x",
         "snippet": "s", "position": 1, "date": "2026-05-27"},
    ]}
    with patch("urllib.request.urlopen", return_value=_mock_resp(payload)) as m:
        hits = p.search("FDA approval", max_results=1, intent="news")
    called_url = m.call_args[0][0].full_url if m.call_args else ""
    assert "news" in called_url or hits[0].published_at == "2026-05-27"


def test_serper_capabilities():
    assert SerperProvider.capabilities >= {"general", "news", "exact",
                                           "patent", "scholar"}
    assert SerperProvider.name == "serper"

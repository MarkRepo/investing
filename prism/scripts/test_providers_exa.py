import json
from unittest.mock import MagicMock, patch

import pytest

from prism.scripts.providers.exa import ExaProvider
from prism.scripts.providers.base import Hit


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


def test_exa_search_returns_hits(tmp_state):
    p = ExaProvider(keys=["k1aaaa"])
    payload = {
        "results": [
            {"title": "T", "url": "https://arxiv.org/abs/x",
             "text": "snip", "score": 0.85,
             "publishedDate": "2026-04-01"},
        ]
    }
    with patch("urllib.request.urlopen", return_value=_mock_resp(payload)):
        hits = p.search("papers similar to X", max_results=1, need_extract=True)
    assert hits[0].source_provider == "exa"
    assert hits[0].published_at == "2026-04-01"


def test_exa_capabilities():
    assert ExaProvider.capabilities >= {"semantic", "scholar", "general"}
    assert ExaProvider.name == "exa"

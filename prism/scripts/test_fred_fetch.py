import pytest
from prism.scripts import fred_fetch


def test_get_fred_api_key_from_env(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "abc123")
    assert fred_fetch.get_fred_api_key() == "abc123"


def test_get_fred_api_key_missing_raises(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="FRED_API_KEY"):
        fred_fetch.get_fred_api_key()


def _fake_client(payload):
    class _Resp:
        def __init__(self, p): self._p = p
        def raise_for_status(self): pass
        def json(self): return self._p
    class _Client:
        def __init__(self, p): self._p = p
        def get(self, url, params=None, timeout=None): return _Resp(self._p)
    return _Client(payload)


def test_fetch_latest_observation_ok(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k")
    client = _fake_client({"observations": [{"date": "2026-06-05", "value": "4.46"}]})
    val, as_of = fred_fetch.fetch_latest_observation("DGS10", client=client)
    assert val == 4.46
    assert as_of == "2026-06-05"


def test_fetch_latest_observation_missing_value(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k")
    client = _fake_client({"observations": [{"date": "2026-06-05", "value": "."}]})
    val, as_of = fred_fetch.fetch_latest_observation("DGS10", client=client)
    assert val is None
    assert as_of == "2026-06-05"


def test_fetch_latest_observation_empty(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k")
    client = _fake_client({"observations": []})
    val, as_of = fred_fetch.fetch_latest_observation("DGS10", client=client)
    assert val is None and as_of is None

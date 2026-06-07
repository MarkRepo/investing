import pytest
from prism.scripts import fred_fetch


def test_get_fred_api_key_from_env(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "abc123")
    assert fred_fetch.get_fred_api_key() == "abc123"


def test_get_fred_api_key_missing_raises(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="FRED_API_KEY"):
        fred_fetch.get_fred_api_key()

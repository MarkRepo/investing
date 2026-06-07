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


def test_run_fred_fetch_records_observations(monkeypatch, tmp_path):
    monkeypatch.setenv("FRED_API_KEY", "k")
    from prism.scripts import macro_registry as reg

    # 内存登记表：3 条 fred 输入（含净流动性派生）+ 1 条 web（应跳过）
    fake = {"inputs": [
        {"name": "美联储资产 WALCL(QT 节奏)", "fetch_method": "fred-api", "fred_series_id": "WALCL"},
        {"name": "TGA 余额", "fetch_method": "fred-api", "fred_series_id": "WTREGEN"},
        {"name": "RRP 逆回购", "fetch_method": "fred-api", "fred_series_id": "RRPONTSYD"},
        {"name": "净流动性(=资产−TGA−RRP)", "fetch_method": "fred-api", "fred_series_id": "__DERIVED__"},
        {"name": "MOVE 债市波动率", "fetch_method": "llm-web"},
    ]}
    monkeypatch.setattr(reg, "read_registry", lambda s, v: fake)
    series_vals = {"WALCL": (7000.0, "2026-06-04"), "WTREGEN": (800.0, "2026-06-04"),
                   "RRPONTSYD": (200.0, "2026-06-04")}
    monkeypatch.setattr(fred_fetch, "fetch_latest_observation",
                        lambda sid, client=None: series_vals[sid])
    recorded = []
    monkeypatch.setattr(reg, "record_observation",
                        lambda s, v, name, **kw: recorded.append((name, kw.get("value"))))

    summary = fred_fetch.run_fred_fetch("global-macro-rates-liquidity", "opus4.8", client=object())

    rec = dict(recorded)
    assert rec["美联储资产 WALCL(QT 节奏)"] == 7000.0
    assert rec["净流动性(=资产−TGA−RRP)"] == 7000.0 - 800.0 - 200.0  # 派生算出
    assert "MOVE 债市波动率" not in rec  # web 跳过
    assert summary["fetched"] == 3 and summary["derived"] == 1 and summary["skipped"] == 1

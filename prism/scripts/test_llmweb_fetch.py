"""llm-web 通用 fetcher：仅抓 availability=='scripted' 且有 recipe 的输入；其余诚实跳过。"""
import pytest

from prism.scripts import llmweb_fetch


def _fake_client(payload):
    class _Resp:
        def __init__(self, p): self._p = p
        def raise_for_status(self): pass
        def json(self): return self._p
    class _Client:
        def __init__(self, p): self._p = p
        def get(self, url, timeout=None): return _Resp(self._p)
    return _Client(payload)


def test_fetch_by_recipe_digs_json():
    client = _fake_client({"data": {"latest": "12.3", "date": "2026-06-05"}})
    recipe = {"url": "https://x", "parse": {"json_path": ["data", "latest"], "date_path": ["data", "date"]}}
    val, as_of = llmweb_fetch.fetch_by_recipe(recipe, client=client)
    assert val == 12.3 and as_of == "2026-06-05"


def test_fetch_by_recipe_missing_path_returns_none():
    client = _fake_client({"data": {}})
    recipe = {"url": "https://x", "parse": {"json_path": ["data", "nope"]}}
    val, as_of = llmweb_fetch.fetch_by_recipe(recipe, client=client)
    assert val is None


def test_run_only_fetches_scripted(monkeypatch):
    from prism.scripts import macro_registry as reg
    fake = {"inputs": [
        {"name": "已配", "fetch_method": "llm-web", "availability": "scripted",
         "fetch_recipe": {"url": "https://x", "parse": {"json_path": ["v"]}}},
        {"name": "待脚本", "fetch_method": "llm-web", "availability": "scriptable_todo"},
        {"name": "无源", "fetch_method": "llm-web", "availability": "no_stable_source"},
        {"name": "FRED 的", "fetch_method": "fred-api"},
    ]}
    monkeypatch.setattr(reg, "read_registry", lambda s, v: fake)
    monkeypatch.setattr(llmweb_fetch, "fetch_by_recipe", lambda recipe, client=None: (9.0, "2026-06-05"))
    recorded = []
    monkeypatch.setattr(reg, "record_observation",
                        lambda s, v, name, **kw: recorded.append((name, kw.get("value"))))
    summary = llmweb_fetch.run_llmweb_fetch("m", "v", client=object())
    assert recorded == [("已配", 9.0)]
    assert summary == {"fetched": 1, "skipped_todo": 1, "skipped_no_source": 1, "failed": 0}


def _fake_text_client(text):
    class _Resp:
        def __init__(self, t): self.text = t
        def raise_for_status(self): pass
    class _Client:
        def __init__(self, t): self._t = t
        def get(self, url, timeout=None): return _Resp(self._t)
    return _Client(text)


def test_fetch_csv_latest_row():
    csv_text = "DATE,Value\n2026-06-01,10.5\n2026-06-05,12.3\n"
    recipe = {"kind": "csv", "url": "https://x",
              "parse": {"value_column": "Value", "date_column": "DATE", "row": "latest"}}
    val, as_of = llmweb_fetch.fetch_by_recipe(recipe, client=_fake_text_client(csv_text))
    assert val == 12.3 and as_of == "2026-06-05"


def test_fetch_csv_first_row():
    csv_text = "DATE,Value\n2026-06-01,10.5\n2026-06-05,12.3\n"
    recipe = {"kind": "csv", "url": "https://x",
              "parse": {"value_column": "Value", "date_column": "DATE", "row": "first"}}
    val, as_of = llmweb_fetch.fetch_by_recipe(recipe, client=_fake_text_client(csv_text))
    assert val == 10.5 and as_of == "2026-06-01"


def test_fetch_csv_missing_column_returns_none():
    csv_text = "DATE,Value\n2026-06-05,12.3\n"
    recipe = {"kind": "csv", "url": "https://x", "parse": {"value_column": "Nope"}}
    val, as_of = llmweb_fetch.fetch_by_recipe(recipe, client=_fake_text_client(csv_text))
    assert val is None


def test_unknown_kind_raises():
    recipe = {"kind": "xml", "url": "https://x", "parse": {}}
    with pytest.raises(ValueError, match="未知"):
        llmweb_fetch.fetch_by_recipe(recipe, client=_fake_text_client("x"))

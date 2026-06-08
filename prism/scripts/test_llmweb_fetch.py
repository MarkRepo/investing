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


# --- fetch_text：固定 URL 取正文（喂 llm-web 判读），不挂 fetch_by_recipe ---

def test_fetch_text_strips_html_tags():
    html = "<html><body><h1>标题</h1><p>正文 内容</p></body></html>"
    out = llmweb_fetch.fetch_text("https://x", client=_fake_text_client(html))
    assert "标题" in out and "正文 内容" in out
    assert "<" not in out and ">" not in out


def test_fetch_text_drops_script_and_style():
    html = "<style>.a{color:red}</style><p>看得见</p><script>var x=1;</script>"
    out = llmweb_fetch.fetch_text("https://x", client=_fake_text_client(html))
    assert "看得见" in out
    assert "color:red" not in out and "var x" not in out


def test_fetch_text_unescapes_entities_and_collapses_ws():
    html = "<p>A&amp;B</p>\n\n   <p>C</p>"
    out = llmweb_fetch.fetch_text("https://x", client=_fake_text_client(html))
    assert "A&B" in out
    assert "\n\n" not in out and "   " not in out

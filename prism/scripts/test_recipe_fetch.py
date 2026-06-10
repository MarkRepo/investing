"""recipe 通用 fetcher：仅抓 fetch_method=='recipe' 且 availability=='scripted' 且有 recipe 的输入；其余诚实跳过。"""
import pytest

from prism.scripts import recipe_fetch


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
    val, as_of = recipe_fetch.fetch_by_recipe(recipe, client=client)
    assert val == 12.3 and as_of == "2026-06-05"


def test_fetch_by_recipe_missing_path_returns_none():
    client = _fake_client({"data": {}})
    recipe = {"url": "https://x", "parse": {"json_path": ["data", "nope"]}}
    val, as_of = recipe_fetch.fetch_by_recipe(recipe, client=client)
    assert val is None


def test_run_only_fetches_scripted(monkeypatch):
    from prism.scripts import macro_registry as reg
    fake = {"inputs": [
        {"name": "已配", "fetch_method": "recipe", "availability": "scripted",
         "fetch_recipe": {"url": "https://x", "parse": {"json_path": ["v"]}}},
        {"name": "待脚本", "availability": "scriptable_todo"},
        {"name": "LLM取甲", "availability": "llm"},
        {"name": "LLM取乙", "availability": "llm"},
        {"name": "FRED 的", "fetch_method": "fred-api"},
    ]}
    monkeypatch.setattr(reg, "read_registry", lambda s, v: fake)
    monkeypatch.setattr(recipe_fetch, "fetch_by_recipe", lambda recipe, client=None: (9.0, "2026-06-05"))
    recorded = []
    monkeypatch.setattr(reg, "record_observation",
                        lambda s, v, name, **kw: recorded.append((name, kw.get("value"))))
    summary = recipe_fetch.run_recipe_fetch("m", "v", client=object())
    assert recorded == [("已配", 9.0)]
    # 待脚本/LLM 项已无 fetch_method（取法走 headless LLM），不在 recipe 闸门内 → 全不计
    assert summary == {"fetched": 1, "derived": 0, "skipped_todo": 0,
                       "skipped_llm": 0, "failed": 0}


def test_run_recipe_only_filters_to_named(monkeypatch):
    """only 给定 → 仅抓名字在其中的 scripted-recipe 项（web 单条手动抓取用）。"""
    from prism.scripts import macro_registry as reg
    fake = {"inputs": [
        {"name": "甲", "fetch_method": "recipe", "availability": "scripted",
         "fetch_recipe": {"url": "https://x", "parse": {"json_path": ["v"]}}},
        {"name": "乙", "fetch_method": "recipe", "availability": "scripted",
         "fetch_recipe": {"url": "https://y", "parse": {"json_path": ["v"]}}},
    ]}
    monkeypatch.setattr(reg, "read_registry", lambda s, v: fake)
    monkeypatch.setattr(recipe_fetch, "fetch_by_recipe", lambda recipe, client=None: (9.0, "2026-06-05"))
    recorded = []
    monkeypatch.setattr(reg, "record_observation",
                        lambda s, v, name, **kw: recorded.append(name))
    summary = recipe_fetch.run_recipe_fetch("m", "v", client=object(), only={"甲"})
    assert recorded == ["甲"]   # 乙 未抓
    assert summary["fetched"] == 1


def test_run_skips_todo_and_llm_marked_recipe(monkeypatch):
    """防御：即便误把 recipe 标在非 scripted 项上，也按 availability 诚实跳过/计数。"""
    from prism.scripts import macro_registry as reg
    fake = {"inputs": [
        {"name": "误标待脚本", "fetch_method": "recipe", "availability": "scriptable_todo"},
        {"name": "误标LLM", "fetch_method": "recipe", "availability": "llm"},
    ]}
    monkeypatch.setattr(reg, "read_registry", lambda s, v: fake)
    summary = recipe_fetch.run_recipe_fetch("m", "v", client=object())
    assert summary == {"fetched": 0, "derived": 0, "skipped_todo": 1,
                       "skipped_llm": 1, "failed": 0}


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
    val, as_of = recipe_fetch.fetch_by_recipe(recipe, client=_fake_text_client(csv_text))
    assert val == 12.3 and as_of == "2026-06-05"


def test_fetch_csv_first_row():
    csv_text = "DATE,Value\n2026-06-01,10.5\n2026-06-05,12.3\n"
    recipe = {"kind": "csv", "url": "https://x",
              "parse": {"value_column": "Value", "date_column": "DATE", "row": "first"}}
    val, as_of = recipe_fetch.fetch_by_recipe(recipe, client=_fake_text_client(csv_text))
    assert val == 10.5 and as_of == "2026-06-01"


def test_fetch_csv_missing_column_returns_none():
    csv_text = "DATE,Value\n2026-06-05,12.3\n"
    recipe = {"kind": "csv", "url": "https://x", "parse": {"value_column": "Nope"}}
    val, as_of = recipe_fetch.fetch_by_recipe(recipe, client=_fake_text_client(csv_text))
    assert val is None


def test_unknown_kind_raises():
    recipe = {"kind": "xml", "url": "https://x", "parse": {}}
    with pytest.raises(ValueError, match="未知"):
        recipe_fetch.fetch_by_recipe(recipe, client=_fake_text_client("x"))


# --- POST + headers 透传 ---

def test_fetch_by_recipe_post_passes_body_and_headers():
    seen = {}
    class _Resp:
        def raise_for_status(self): pass
        def json(self): return {"v": 7.0}
    class _Client:
        def post(self, url, json=None, timeout=None, headers=None):
            seen.update(url=url, json=json, headers=headers, timeout=timeout)
            return _Resp()
    recipe = {"url": "https://x", "method": "POST", "body": {"a": 1},
              "headers": {"H": "1"}, "parse": {"json_path": ["v"]}}
    val, _ = recipe_fetch.fetch_by_recipe(recipe, client=_Client())
    assert val == 7.0
    assert seen["json"] == {"a": 1} and seen["headers"] == {"H": "1"} and seen["url"] == "https://x"


def test_fetch_by_recipe_get_omits_headers_when_absent():
    """无 headers 时不传 headers=（保持与既有 mock client get(url, timeout=) 兼容）。"""
    client = _fake_client({"v": 3.0})  # 其 get 只接受 (url, timeout)
    recipe = {"url": "https://x", "parse": {"json_path": ["v"]}}
    val, _ = recipe_fetch.fetch_by_recipe(recipe, client=client)
    assert val == 3.0


# --- matrix kind：透视表（行=实体、列=周期）---

def test_fetch_matrix_picks_row_and_dated_col():
    text = ("Table 5\nCountry\t2026-03\t2026-02\n"
            "Japan\t1191.6\t1239.3\nChina, Mainland\t652.3\t660.1\n")
    recipe = {"kind": "matrix", "url": "https://x",
              "parse": {"delimiter": "\t", "header_label": "Country",
                        "row_label": "China, Mainland", "col_index": 1}}
    val, as_of = recipe_fetch.fetch_by_recipe(recipe, client=_fake_text_client(text))
    assert val == 652.3 and as_of == "2026-03"


def test_fetch_matrix_missing_row_returns_none():
    text = "Country\t2026-03\nJapan\t1191.6\n"
    recipe = {"kind": "matrix", "url": "https://x",
              "parse": {"delimiter": "\t", "header_label": "Country",
                        "row_label": "China, Mainland", "col_index": 1}}
    val, as_of = recipe_fetch.fetch_by_recipe(recipe, client=_fake_text_client(text))
    assert val is None


# --- 按输入名派生：derived.from_inputs ---

def test_run_recipe_derives_from_named_inputs(monkeypatch):
    """中美利差式派生：读各腿最新 observed.value 后按 op 算，记一条 derived。"""
    from prism.scripts import macro_registry as reg
    drive = {"inputs": [
        {"name": "利差", "fetch_method": "recipe", "availability": "scripted",
         "derived": {"op": "sub", "from_inputs": ["甲", "乙"]}},
    ]}
    legs = {"inputs": [
        {"name": "利差"},
        {"name": "甲", "observed": {"value": 2.0}},
        {"name": "乙", "observed": {"value": 0.5}},
    ]}
    seq = [drive, legs]  # 第一次读驱动主循环；派生段重读取各腿
    monkeypatch.setattr(reg, "read_registry", lambda s, v: seq.pop(0) if seq else legs)
    recorded = []
    monkeypatch.setattr(reg, "record_observation",
                        lambda s, v, name, **kw: recorded.append((name, kw.get("value"))))
    summary = recipe_fetch.run_recipe_fetch("m", "v", client=object())
    assert recorded == [("利差", 1.5)]
    assert summary["derived"] == 1 and summary["fetched"] == 0


def test_run_recipe_derive_skips_when_leg_missing(monkeypatch):
    """任一腿无 observed.value → 不记派生、计 failed，诚实留空。"""
    from prism.scripts import macro_registry as reg
    drive = {"inputs": [
        {"name": "利差", "fetch_method": "recipe", "availability": "scripted",
         "derived": {"op": "sub", "from_inputs": ["甲", "乙"]}},
    ]}
    legs = {"inputs": [{"name": "甲", "observed": {"value": 2.0}}, {"name": "乙"}]}
    seq = [drive, legs]
    monkeypatch.setattr(reg, "read_registry", lambda s, v: seq.pop(0) if seq else legs)
    recorded = []
    monkeypatch.setattr(reg, "record_observation",
                        lambda s, v, name, **kw: recorded.append(name))
    summary = recipe_fetch.run_recipe_fetch("m", "v", client=object())
    assert recorded == [] and summary["derived"] == 0 and summary["failed"] == 1


# --- fetch_text：固定 URL 取正文（喂 headless LLM 判读），不挂 fetch_by_recipe ---

def test_fetch_text_strips_html_tags():
    html = "<html><body><h1>标题</h1><p>正文 内容</p></body></html>"
    out = recipe_fetch.fetch_text("https://x", client=_fake_text_client(html))
    assert "标题" in out and "正文 内容" in out
    assert "<" not in out and ">" not in out


def test_fetch_text_drops_script_and_style():
    html = "<style>.a{color:red}</style><p>看得见</p><script>var x=1;</script>"
    out = recipe_fetch.fetch_text("https://x", client=_fake_text_client(html))
    assert "看得见" in out
    assert "color:red" not in out and "var x" not in out


def test_fetch_text_unescapes_entities_and_collapses_ws():
    html = "<p>A&amp;B</p>\n\n   <p>C</p>"
    out = recipe_fetch.fetch_text("https://x", client=_fake_text_client(html))
    assert "A&B" in out
    assert "\n\n" not in out and "   " not in out

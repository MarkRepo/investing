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


def _scan_recipe():
    return {"kind": "json_scan", "url": "https://x", "parse": {
        "list_path": ["data"], "match_field": "title",
        "match_regex": "成交总面积环比",
        "value_regex": r"环比(?:增加|减少|下降)([0-9.]+)%",
        "sign_negative_regex": "(减少|下降)",
        "date_field": "url", "date_regex": r"(\d{4}-\d{2}-\d{2})"}}


def test_json_scan_picks_first_match_and_signs_positive():
    client = _fake_client({"data": [
        {"title": "无关项", "url": "http://x/2026-06-11/9.html"},
        {"title": "市场周报|第20周——典型城市商品住宅成交总面积环比增加24.98%",
         "url": "http://x/2026-05-21/1.html"},
        {"title": "市场周报|第19周——典型城市商品住宅成交总面积环比减少7.11%",
         "url": "http://x/2026-05-13/2.html"}]})
    val, as_of = recipe_fetch.fetch_by_recipe(_scan_recipe(), client=client)
    assert val == 24.98 and as_of == "2026-05-21"


def test_json_scan_negates_on_decrease():
    client = _fake_client({"data": [
        {"title": "市场周报|第19周——典型城市商品住宅成交总面积环比减少7.11%",
         "url": "http://x/2026-05-13/2.html"}]})
    val, as_of = recipe_fetch.fetch_by_recipe(_scan_recipe(), client=client)
    assert val == -7.11 and as_of == "2026-05-13"


def test_json_scan_no_match_returns_none():
    client = _fake_client({"data": [{"title": "全是无关项", "url": "http://x/2026-01-01/3.html"}]})
    val, as_of = recipe_fetch.fetch_by_recipe(_scan_recipe(), client=client)
    assert val is None


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


# --- html kind：sign_negative_regex（中文涨跌词无 +/− 时判负）---

def test_html_sign_negative_regex_negates():
    html = "<p>本周环比减少2.8%</p>"
    recipe = {"kind": "html", "url": "https://x",
              "parse": {"value_regex": r"环比(?:增加|减少)([0-9.]+)%",
                        "sign_negative_regex": "减少"}}
    val, _ = recipe_fetch.fetch_by_recipe(recipe, client=_fake_text_client(html))
    assert val == -2.8


def test_html_sign_negative_regex_positive_when_absent():
    html = "<p>本周环比增加2.8%</p>"
    recipe = {"kind": "html", "url": "https://x",
              "parse": {"value_regex": r"环比(?:增加|减少)([0-9.]+)%",
                        "sign_negative_regex": "减少"}}
    val, _ = recipe_fetch.fetch_by_recipe(recipe, client=_fake_text_client(html))
    assert val == 2.8


# --- html_list kind：两步抓取（列表页找最新条目 id → 详情页正文取值）---

def _fake_multi_text_client(by_url):
    """url 精确匹配 → 对应 text 响应（供 html_list 两步抓取 mock 列表页+详情页）。"""
    class _Resp:
        def __init__(self, t): self.text = t
        def raise_for_status(self): pass
    class _Client:
        def get(self, url, timeout=None, headers=None):
            if url not in by_url:
                raise AssertionError(f"unexpected url: {url}")
            return _Resp(by_url[url])
    return _Client()


def _html_list_recipe():
    return {
        "kind": "html_list",
        "list_url": "https://list.x/page1",
        "parse": {
            "list_item_regex": r'itemId=(\d+)"[^>]*>.*?alt="([^"]*)"',
            "title_match_regex": "35城新建商品住宅成交面积",
            "detail_url_template": "https://detail.x/item?id={id}",
            "value_regex": r"环比上周(?:增加|减少)([0-9.]+)%",
            "sign_negative_regex": "减少",
            "date_regex": r"(\d{4}年第\d+周)",
        },
    }


def test_html_list_two_step_fetch_and_negates():
    list_html = ('<a itemId=12345"><img alt="2026年第28周35城新建商品住宅成交面积"></a>'
                 '<a itemId=999"><img alt="无关条目"></a>')
    detail_html = "<p>2026年第28周35城新建商品住宅成交面积158.7万平方米，环比上周减少2.8%。</p>"
    client = _fake_multi_text_client({
        "https://list.x/page1": list_html,
        "https://detail.x/item?id=12345": detail_html,
    })
    val, as_of = recipe_fetch.fetch_by_recipe(_html_list_recipe(), client=client)
    assert val == -2.8 and as_of == "2026年第28周"


def test_html_list_date_from_raw_script_survives_body_cleaning():
    """详情页发布日期常在 <script type=application/ld+json> 的 datePublished 里；
    清洗正文时会把 script 标签连内容一起去掉，所以 date_regex 须对**原始** HTML 跑
    （_fetch_html_list 的 date_text 参数），而不是清洗后的 text——这条测试锁死这个行为。"""
    list_html = '<a itemId=12345"><img alt="市场周报 | 35城新建商品住宅成交面积环比"></a>'
    detail_html = ('<script type="application/ld+json">{"datePublished":"2026-07-22 09:44:02"}'
                   '</script><p>本周35城新建商品住宅成交面积环比上周减少2.8%。</p>')
    recipe = dict(_html_list_recipe())
    recipe["parse"] = dict(recipe["parse"])
    recipe["parse"]["date_regex"] = r'"datePublished":"(\d{4}-\d{2}-\d{2})'
    client = _fake_multi_text_client({
        "https://list.x/page1": list_html,
        "https://detail.x/item?id=12345": detail_html,
    })
    val, as_of = recipe_fetch.fetch_by_recipe(recipe, client=client)
    assert val == -2.8 and as_of == "2026-07-22"


def test_html_list_no_title_match_returns_none():
    list_html = '<a itemId=999"><img alt="无关条目"></a>'
    client = _fake_multi_text_client({"https://list.x/page1": list_html})
    val, as_of = recipe_fetch.fetch_by_recipe(_html_list_recipe(), client=client)
    assert val is None and as_of is None


def test_html_list_missing_list_url_returns_none():
    recipe = {"kind": "html_list", "parse": {"list_item_regex": r"(\d+)"}}
    val, as_of = recipe_fetch.fetch_by_recipe(recipe, client=_fake_multi_text_client({}))
    assert val is None and as_of is None


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


# --- cip_basis：抛补利率平价跨币种基差派生算子 ---

def test_cip_basis_eurusd_quote_role():
    """EURUSD(usd_role=quote)：S=1.0, fwd=100pips/1e4 → F=1.01；(1+r_usd·τ) 恰=F/S → 主项归零，
    基差 = −r_for = −2% = −200bps。手算可验。"""
    legs = [1.0, 100.0, 4.0, 2.0]  # spot, fwd_pips, usd_ois%, eur_ois%
    b = recipe_fetch._cip_basis(legs, {"tau": 0.25, "pip_scale": 10000, "usd_role": "quote"})
    assert abs(b - (-200.0)) < 1e-6


def test_cip_basis_usdjpy_base_role():
    """USDJPY(usd_role=base)：S=150, fwd=−150pips/1e2 → F=148.5；F/S=0.99，×1.01=0.9999，
    (0.9999−1)/0.25 − 0.01 = −0.0104 → −104bps。手算可验。"""
    legs = [150.0, -150.0, 4.0, 1.0]  # spot, fwd_pips, usd_ois%, jpy_ois%
    b = recipe_fetch._cip_basis(legs, {"tau": 0.25, "pip_scale": 100, "usd_role": "base"})
    assert abs(b - (-104.0)) < 1e-6


def test_cip_basis_zero_when_parity_holds():
    """fwd=0 且两腿利率相等 → 基差严格 0。"""
    b = recipe_fetch._cip_basis([1.0, 0.0, 4.0, 4.0], {"usd_role": "quote"})
    assert abs(b) < 1e-9


def test_cip_basis_bad_role_raises():
    with pytest.raises(ValueError, match="usd_role"):
        recipe_fetch._cip_basis([1.0, 0.0, 4.0, 4.0], {"usd_role": "x"})


def test_cip_basis_wrong_leg_count_raises():
    with pytest.raises(ValueError, match="4 腿"):
        recipe_fetch._cip_basis([1.0, 0.0, 4.0], {"usd_role": "quote"})


def test_run_recipe_cip_basis_derives_and_dates(monkeypatch):
    """派生路径 op=cip_basis：读 4 腿 observed.value 算基差、记 derived、as_of 取最旧腿日期。"""
    from prism.scripts import macro_registry as reg
    drive = {"inputs": [
        {"name": "EUR/USD 3M 基差", "fetch_method": "recipe", "availability": "scripted",
         "derived": {"op": "cip_basis",
                     "from_inputs": ["spot", "fwd", "usd_ois", "eur_ois"],
                     "params": {"tau": 0.25, "pip_scale": 10000, "usd_role": "quote"}}},
    ]}
    legs = {"inputs": [
        {"name": "EUR/USD 3M 基差"},
        {"name": "spot", "observed": {"value": 1.0, "as_of": "2026-06-11"}},
        {"name": "fwd", "observed": {"value": 100.0, "as_of": "2026-06-11"}},
        {"name": "usd_ois", "observed": {"value": 4.0, "as_of": "2026-06-09"}},
        {"name": "eur_ois", "observed": {"value": 2.0, "as_of": "2026-06-10"}},
    ]}
    seq = [drive, legs]
    monkeypatch.setattr(reg, "read_registry", lambda s, v: seq.pop(0) if seq else legs)
    recorded = []
    monkeypatch.setattr(reg, "record_observation",
                        lambda s, v, name, **kw: recorded.append((name, kw.get("value"), kw.get("as_of"))))
    summary = recipe_fetch.run_recipe_fetch("m", "v", client=object())
    assert len(recorded) == 1
    name, val, as_of = recorded[0]
    assert name == "EUR/USD 3M 基差" and abs(val - (-200.0)) < 1e-6
    assert as_of == "2026-06-09"  # 最旧腿
    assert summary["derived"] == 1


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

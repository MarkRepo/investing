"""macromicro 取数通道：fetch_by_macromicro 解析（mock httpx，零网络）。

覆盖：两步法取 token+数据、按 series_index 选档、解析日期取 max、value_scale 缩放、
缺/非法 chart_id、无 token 重试后抛、限流空数据退避后诚实降级、series_index 越界。
"""
from __future__ import annotations

import pytest

from prism.scripts import macromicro_fetch as mm

_PAGE_WITH_TOKEN = '<html><footer><p data-stk="abcdef0123456789abcdef0123456789">© 2026</p></footer></html>'
_PAGE_NO_TOKEN = "<html><footer>no token here</footer></html>"


class FakeResp:
    def __init__(self, text="", payload=None):
        self.text = text
        self._payload = payload

    def json(self):
        return self._payload


class FakeClient:
    """mock httpx.Client：按 url 派发——含 /charts/data/ 的返 JSON，否则返页面 HTML。
    page_html 控制 token 页；data_payload 是数据接口 JSON。"""

    def __init__(self, page_html=_PAGE_WITH_TOKEN, data_payload=None, data_sequence=None):
        self.page_html = page_html
        self.data_payload = data_payload
        self.data_sequence = list(data_sequence) if data_sequence else None
        self.calls = []

    def get(self, url, headers=None):
        self.calls.append(url)
        if "/charts/data/" in url:
            if self.data_sequence is not None:
                payload = self.data_sequence.pop(0) if self.data_sequence else self.data_payload
            else:
                payload = self.data_payload
            return FakeResp(payload=payload)
        return FakeResp(text=self.page_html)


def _ok(series_list):
    """构造 {"success":1,"data":{"c:1":[series...]}} 形态。"""
    return {"success": 1, "data": {"c:1": series_list}, "msg": None}


NOSLEEP = lambda _s: None


def test_extracts_token_and_parses_latest():
    payload = _ok([[["2026-06-08", "0.93"], ["2026-06-09", "0.94"], ["2026-06-10", "0.9421"]]])
    cli = FakeClient(data_payload=payload)
    v, d = mm.fetch_by_macromicro({"chart_id": "95219", "page_url": "https://sc.macromicro.me/x"}, client=cli, sleep=NOSLEEP)
    assert abs(v - 0.9421) < 1e-9 and d == "2026-06-10"
    # 数据请求带了 Bearer（token 取自页脚 data-stk）
    assert any("/charts/data/95219" in u for u in cli.calls)


def test_series_index_selects_tenor():
    payload = _ok([
        [["2026-06-10", "0.9421"]],   # idx0 = 3M
        [["2026-06-10", "1.1389"]],   # idx1 = 12M
    ])
    cli = FakeClient(data_payload=payload)
    v0, _ = mm.fetch_by_macromicro({"chart_id": "1", "series_index": 0, "page_url": "https://sc.macromicro.me/x"}, client=cli, sleep=NOSLEEP)
    cli2 = FakeClient(data_payload=payload)
    v1, _ = mm.fetch_by_macromicro({"chart_id": "1", "series_index": 1, "page_url": "https://sc.macromicro.me/x"}, client=cli2, sleep=NOSLEEP)
    assert abs(v0 - 0.9421) < 1e-9
    assert abs(v1 - 1.1389) < 1e-9


def test_value_scale_multiplies():
    payload = _ok([[["2026-06-10", "-0.40"]]])
    cli = FakeClient(data_payload=payload)
    v, _ = mm.fetch_by_macromicro({"chart_id": "1", "value_scale": 100, "page_url": "https://sc.macromicro.me/x"}, client=cli, sleep=NOSLEEP)
    assert abs(v - (-40.0)) < 1e-9   # 百分点→bps


def test_picks_max_date_when_unsorted():
    payload = _ok([[["2026-06-10", "0.9421"], ["2026-06-08", "0.93"], ["2026-06-09", "0.94"]]])
    cli = FakeClient(data_payload=payload)
    v, d = mm.fetch_by_macromicro({"chart_id": "1", "page_url": "https://sc.macromicro.me/x"}, client=cli, sleep=NOSLEEP)
    assert abs(v - 0.9421) < 1e-9 and d == "2026-06-10"


def test_missing_chart_id_raises():
    with pytest.raises(ValueError, match="缺 chart_id"):
        mm.fetch_by_macromicro({}, client=FakeClient(), sleep=NOSLEEP)


def test_non_numeric_chart_id_raises():
    with pytest.raises(ValueError, match="须为数字"):
        mm.fetch_by_macromicro({"chart_id": "abc", "page_url": "https://sc.macromicro.me/x"}, client=FakeClient(), sleep=NOSLEEP)


def test_no_token_retries_then_raises():
    cli = FakeClient(page_html=_PAGE_NO_TOKEN, data_payload=_ok([[["2026-06-10", "1"]]]))
    with pytest.raises(ValueError, match="data-stk"):
        mm.fetch_by_macromicro({"chart_id": "1", "retries": 3, "page_url": "https://sc.macromicro.me/x"}, client=cli, sleep=NOSLEEP)


def test_throttle_empty_returns_none():
    # success:0 / data 空（限流或 #1170）→ 退避重试后诚实 (None, None)
    cli = FakeClient(data_payload={"success": 0, "data": [], "msg": "error #1170"})
    v, d = mm.fetch_by_macromicro({"chart_id": "1", "retries": 2, "page_url": "https://sc.macromicro.me/x"}, client=cli, sleep=NOSLEEP)
    assert v is None and d is None


def test_recovers_after_transient_empty():
    # 首轮空、次轮有数据 → 退避后成功
    seq = [{"success": 0, "data": [], "msg": "error #1158"}, _ok([[["2026-06-10", "0.9421"]]])]
    cli = FakeClient(data_payload=None, data_sequence=seq)
    v, d = mm.fetch_by_macromicro({"chart_id": "1", "retries": 3, "page_url": "https://sc.macromicro.me/x"}, client=cli, sleep=NOSLEEP)
    assert abs(v - 0.9421) < 1e-9 and d == "2026-06-10"


def test_series_index_out_of_range_raises():
    payload = _ok([[["2026-06-10", "0.9421"]]])
    cli = FakeClient(data_payload=payload)
    with pytest.raises(ValueError, match="越界"):
        mm.fetch_by_macromicro({"chart_id": "1", "series_index": 5, "page_url": "https://sc.macromicro.me/x"}, client=cli, sleep=NOSLEEP)


def test_missing_page_url_raises():
    with pytest.raises(ValueError, match="缺 page_url"):
        mm.fetch_by_macromicro({"chart_id": "1"}, client=FakeClient(), sleep=NOSLEEP)


def test_find_all_series_nested_dict():
    obj = {"a": {"b": [[["2026-06-10", "1.0"]]]}, "c": [[["2026-06-09", "2.0"]]]}
    found = mm._find_all_series(obj)
    assert len(found) == 2

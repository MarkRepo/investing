"""barchart 取数通道：fetch_by_barchart 解析（mock httpx，零网络）。

覆盖：两步法取 XSRF cookie + 数据、取最新 EOD、缺 cookie 重试后抛、空数据软降级、缺 symbol 抛。
"""
from __future__ import annotations

import pytest

from prism.scripts import barchart_fetch as bc


class FakeResp:
    def __init__(self, text="", payload=None):
        self.text = text
        self._payload = payload

    def json(self):
        return self._payload


class FakeCookies:
    def __init__(self, jar):
        self._jar = jar

    def get(self, name):
        return self._jar.get(name)


class FakeClient:
    """mock httpx.Client：含 /historical/get 的返数据 JSON，否则返页面（同时"种下"cookie）。
    token 控制 XSRF-TOKEN cookie 值（None=不种）；data_payload 是 core-api JSON。"""

    def __init__(self, token="tok%3Dabc", data_payload=None):
        self._token = token
        self.data_payload = data_payload
        self.cookies = FakeCookies({"XSRF-TOKEN": token} if token else {})
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append(url)
        if "/historical/get" in url:
            return FakeResp(payload=self.data_payload)
        return FakeResp(text="<html>page</html>")


def _ok(rows):
    return {"data": rows}


NOSLEEP = lambda _s: None


def test_extracts_latest_eod():
    cli = FakeClient(data_payload=_ok([{"tradeTime": "2026-06-11", "lastPrice": "42.258"}]))
    v, d = bc.fetch_by_barchart({"symbol": "EURUSD.H"}, client=cli, sleep=NOSLEEP)
    assert abs(v - 42.258) < 1e-9 and d == "2026-06-11"
    assert any("/historical/get" in u for u in cli.calls)


def test_negative_forward_points():
    cli = FakeClient(data_payload=_ok([{"tradeTime": "2026-06-11", "lastPrice": "-116.45"}]))
    v, d = bc.fetch_by_barchart({"symbol": "USDJPY.H"}, client=cli, sleep=NOSLEEP)
    assert abs(v - (-116.45)) < 1e-9 and d == "2026-06-11"


def test_custom_field():
    cli = FakeClient(data_payload=_ok([{"tradeTime": "2026-06-11", "openPrice": "40.0"}]))
    v, _ = bc.fetch_by_barchart({"symbol": "EURUSD.H", "field": "openPrice"}, client=cli, sleep=NOSLEEP)
    assert abs(v - 40.0) < 1e-9


def test_missing_token_retries_then_raises():
    cli = FakeClient(token=None, data_payload=_ok([{"tradeTime": "2026-06-11", "lastPrice": "1"}]))
    with pytest.raises(ValueError, match="XSRF-TOKEN"):
        bc.fetch_by_barchart({"symbol": "EURUSD.H", "retries": 3}, client=cli, sleep=NOSLEEP)


def test_empty_data_returns_none():
    cli = FakeClient(data_payload={"data": []})
    v, d = bc.fetch_by_barchart({"symbol": "EURUSD.H", "retries": 2}, client=cli, sleep=NOSLEEP)
    assert v is None and d is None


def test_missing_symbol_raises():
    with pytest.raises(ValueError, match="缺 symbol"):
        bc.fetch_by_barchart({}, client=FakeClient(), sleep=NOSLEEP)

"""ECB 取数通道：fetch_by_ecb hybrid_3m_ois（mock httpx，零网络）。

覆盖：三次 CSV 派发 + carry 计算、锚点日缺值退化、某腿空软降级、未知 mode 抛、缺 key 抛。
"""
from __future__ import annotations

import pytest

from prism.scripts import ecb_fetch as ecb


def _csv(date, val):
    if date is None:
        return "KEY,TIME_PERIOD,OBS_VALUE\n"
    return f"KEY,TIME_PERIOD,OBS_VALUE\nX,{date},{val}\n"


class FakeResp:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


class FakeClient:
    """按 url 派发：含 MMSR→OIS；含 EST 且含 startPeriod→锚点 €STR；含 EST 否则→当前 €STR。"""

    def __init__(self, mmsr="2.078@2026-05-05", estr_now="1.93@2026-06-10", estr_anchor="1.932@2026-05-05"):
        self.mmsr = mmsr
        self.estr_now = estr_now
        self.estr_anchor = estr_anchor
        self.calls = []

    @staticmethod
    def _csv_for(spec):
        if spec is None:
            return _csv(None, None)
        v, d = spec.split("@")
        return _csv(d, v)

    def get(self, url, headers=None):
        self.calls.append(url)
        if "/MMSR/" in url:
            return FakeResp(self._csv_for(self.mmsr))
        if "/EST/" in url and "startPeriod=" in url:
            return FakeResp(self._csv_for(self.estr_anchor))
        return FakeResp(self._csv_for(self.estr_now))


_CFG = {"mode": "hybrid_3m_ois", "ois_key": "OISKEY", "estr_key": "ESTKEY"}


def test_hybrid_carry_computation():
    cli = FakeClient()
    v, d = ecb.fetch_by_ecb(_CFG, client=cli)
    # 1.93 + (2.078 - 1.932) = 2.076；日期取 €STR 当前（日频新鲜）
    assert abs(v - 2.076) < 1e-9 and d == "2026-06-10"
    # 三次 GET：MMSR、EST(now)、EST(anchor with startPeriod)
    assert any("/MMSR/" in u for u in cli.calls)
    assert any("/EST/" in u and "startPeriod=2026-05-05" in u for u in cli.calls)


def test_anchor_missing_falls_back_to_now():
    # 锚点日无 €STR → carry 用当前 €STR：1.93 + (2.078 - 1.93) = 2.078
    cli = FakeClient(estr_anchor=None)
    v, _ = ecb.fetch_by_ecb(_CFG, client=cli)
    assert abs(v - 2.078) < 1e-9


def test_missing_ois_leg_returns_none():
    cli = FakeClient(mmsr=None)
    v, d = ecb.fetch_by_ecb(_CFG, client=cli)
    assert v is None and d is None


def test_unknown_mode_raises():
    with pytest.raises(ValueError, match="未知 ecb.mode"):
        ecb.fetch_by_ecb({"mode": "spot", "ois_key": "x", "estr_key": "y"}, client=FakeClient())


def test_missing_keys_raises():
    with pytest.raises(ValueError, match="须配 ois_key"):
        ecb.fetch_by_ecb({"mode": "hybrid_3m_ois"}, client=FakeClient())

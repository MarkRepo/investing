"""fedwatch 通道单测（仿 test_mofcom_fetch.py）：逐会议反解纯函数手算对值 → fetch_contract_rates
注入 mock yf → run_fedwatch_fetch monkeypatch 登记表。零网络。"""
import datetime as dt

import pandas as pd
import pytest

from prism.scripts import fedwatch_fetch as fw
from prism.scripts import macro_registry as reg


_TODAY = dt.date(2026, 6, 1)
# 连月会议日历（测会内加权）：Jun(公告17)→Jul 都有会议；Jul 次月 Aug 无会议（测干净读）
_MEET_WEIGHT = ["2026-06-17", "2026-07-29"]
# 隔月会议日历（测干净读）：Jun 次月 Jul 无会议；Dec 次月 Jan27 无会议
_MEET_CLEAN = ["2026-06-17", "2026-12-09"]

# 使会内加权应解出 post_jun=3.75（pre 起点 4.00）：avg = 17/30·4.00 + 13/30·3.75
_AVG_JUN_375 = (17 * 4.00 + 13 * 3.75) / 30


# ---- 月码/邻月/needed_months ----

def test_contract_symbol():
    assert fw._contract_symbol(2026, 6) == "ZQM26.CBT"
    assert fw._contract_symbol(2026, 12) == "ZQZ26.CBT"
    assert fw._contract_symbol(2027, 1) == "ZQF27.CBT"


def test_needed_months_weight_then_clean():
    # Jun→次月Jul有会议→取会议月(2026,6)；Jul→次月Aug无会议→取(2026,8)
    assert fw.needed_months(_TODAY, _MEET_WEIGHT) == [(2026, 6), (2026, 8)]


def test_needed_months_full_2026():
    # Jun(weight,6) Jul(clean,8) Sep(weight,9) Oct(clean,11) Dec(clean,2027-1)
    assert fw.needed_months(_TODAY) == [(2026, 6), (2026, 8), (2026, 9), (2026, 11), (2027, 1)]


# ---- compute_path：会内加权 + 干净读 ----

def test_compute_path_weight_then_clean():
    # Jun 会内加权解 post=3.75；Jul 次月Aug干净读=3.50
    rates = {(2026, 6): _AVG_JUN_375, (2026, 8): 3.50}
    path = fw.compute_path(4.00, rates, _TODAY, meetings=_MEET_WEIGHT)
    assert len(path) == 2
    assert path[0]["method"] == "weight"
    assert path[0]["pre"] == 4.00 and path[0]["post"] == pytest.approx(3.75)
    assert path[1]["method"] == "clean"
    assert path[1]["pre"] == pytest.approx(3.75)          # 链式传导
    assert path[1]["post"] == pytest.approx(3.50)


def test_compute_path_clean_read_both():
    # Jun 次月Jul无会议→干净读=3.80；Dec 次月Jan27无会议→干净读=3.40
    rates = {(2026, 7): 3.80, (2027, 1): 3.40}
    path = fw.compute_path(4.00, rates, _TODAY, meetings=_MEET_CLEAN)
    assert [p["method"] for p in path] == ["clean", "clean"]
    assert path[0]["post"] == pytest.approx(3.80)
    assert path[1]["pre"] == pytest.approx(3.80) and path[1]["post"] == pytest.approx(3.40)


def test_compute_path_truncates_on_missing_contract():
    path = fw.compute_path(4.00, {(2026, 7): 3.80}, _TODAY, meetings=_MEET_CLEAN)  # 缺 Jan27
    assert len(path) == 1 and path[0]["post"] == pytest.approx(3.80)


def test_compute_path_empty_when_no_future_meeting():
    rates = {(2026, 7): 3.80, (2027, 1): 3.40}
    assert fw.compute_path(4.00, rates, dt.date(2027, 6, 1), meetings=_MEET_CLEAN) == []


# ---- extract_metric ----

def _path_clean():
    return fw.compute_path(4.00, {(2026, 7): 3.80, (2027, 1): 3.40}, _TODAY, meetings=_MEET_CLEAN)


def test_extract_next_rate():
    assert fw.extract_metric("next_rate", _path_clean(), 4.00) == pytest.approx(3.80)


def test_extract_eoy_rate():
    assert fw.extract_metric("eoy_rate", _path_clean(), 4.00) == pytest.approx(3.40)


def test_extract_eoy_cuts():
    # (4.00 − 3.40)/0.25 = 2.4 档
    assert fw.extract_metric("eoy_cuts", _path_clean(), 4.00) == pytest.approx(2.4)


def test_extract_next_cut_prob_partial():
    # delta = 4.00−3.80 = 0.20 → 0.8 档 → 80%
    assert fw.extract_metric("next_cut_prob", _path_clean(), 4.00) == pytest.approx(80.0)


def test_extract_next_cut_prob_full_step():
    path = fw.compute_path(4.00, {(2026, 7): 3.75, (2027, 1): 3.50}, _TODAY, meetings=_MEET_CLEAN)
    assert fw.extract_metric("next_cut_prob", path, 4.00) == pytest.approx(100.0)


def test_extract_next_cut_prob_hold_is_zero():
    # post > pre（加息计价）→ 截断到 0
    path = fw.compute_path(4.00, {(2026, 7): 4.10, (2027, 1): 4.10}, _TODAY, meetings=_MEET_CLEAN)
    assert fw.extract_metric("next_cut_prob", path, 4.00) == 0.0


def test_extract_empty_path_returns_none():
    assert fw.extract_metric("eoy_rate", [], 4.00) is None


def test_extract_bad_metric_raises():
    with pytest.raises(ValueError, match="metric 非法"):
        fw.extract_metric("nope", _path_clean(), 4.00)


# ---- fetch_contract_rates（注入 mock yf，零网络）----

def _fake_yf(price_by_symbol):
    class _Ticker:
        def __init__(self, sym): self.sym = sym
        def history(self, period=None):
            p = price_by_symbol.get(self.sym)
            if p is None:
                return pd.DataFrame()
            idx = pd.to_datetime(["2026-05-29", "2026-06-01"])
            return pd.DataFrame({"Close": [p - 0.01, p]}, index=idx)
    class _YF:
        def Ticker(self, sym): return _Ticker(sym)
    return _YF()


def test_fetch_contract_rates_implied_and_asof():
    # 需 (2026,6) 与 (2026,8)；价 → 隐含 = 100−价
    prices = {"ZQM26.CBT": 100 - _AVG_JUN_375, "ZQQ26.CBT": 96.50}
    rates, as_of = fw.fetch_contract_rates(_TODAY, yf_module=_fake_yf(prices), meetings=_MEET_WEIGHT)
    assert rates[(2026, 6)] == pytest.approx(_AVG_JUN_375)
    assert rates[(2026, 8)] == pytest.approx(3.50)
    assert as_of == "2026-06-01"


def test_fetch_contract_rates_skips_missing_symbol():
    prices = {"ZQM26.CBT": 100 - _AVG_JUN_375}              # 缺 Aug
    rates, _ = fw.fetch_contract_rates(_TODAY, yf_module=_fake_yf(prices), meetings=_MEET_WEIGHT)
    assert (2026, 6) in rates and (2026, 8) not in rates


# ---- run_fedwatch_fetch（monkeypatch 登记表 + 注入 yf，路径只算一次）----

def test_run_only_scripted_fedwatch(monkeypatch):
    fake = {"inputs": [
        {"name": "下次会议隐含利率", "fetch_method": "fedwatch", "availability": "scripted",
         "fedwatch": {"metric": "next_rate", "current_rate": 4.00}},
        {"name": "年底累计降息计价", "fetch_method": "fedwatch", "availability": "scripted",
         "fedwatch": {"metric": "eoy_cuts", "current_rate": 4.00}},
        {"name": "待脚本", "fetch_method": "fedwatch", "availability": "scriptable_todo"},
        {"name": "LLM取", "fetch_method": "fedwatch", "availability": "llm"},
        {"name": "别的通道", "fetch_method": "cftc", "availability": "scripted"},
    ]}
    monkeypatch.setattr(reg, "read_registry", lambda s, v: fake)
    recorded = []
    monkeypatch.setattr(reg, "record_observation",
                        lambda s, v, name, **kw: recorded.append((name, kw.get("value"), kw.get("as_of"))))
    # 所有所需月给恒定 4.00%（96.00 价）→ 路径平 4.00：next_rate=4.0、eoy_cuts=0.0
    yf = _fake_yf({fw._contract_symbol(y, m): 96.00 for (y, m) in fw.needed_months(_TODAY)})
    summary = fw.run_fedwatch_fetch("m", "v", yf_module=yf, today=_TODAY)
    assert {n: val for n, val, _ in recorded} == {
        "下次会议隐含利率": pytest.approx(4.0), "年底累计降息计价": pytest.approx(0.0)}
    assert summary == {"fetched": 2, "skipped_todo": 1, "skipped_llm": 1, "failed": 0}


def test_run_records_error_when_path_insufficient(monkeypatch):
    fake = {"inputs": [
        {"name": "下次会议隐含利率", "fetch_method": "fedwatch", "availability": "scripted",
         "fedwatch": {"metric": "next_rate", "current_rate": 4.00}},
    ]}
    monkeypatch.setattr(reg, "read_registry", lambda s, v: fake)
    errors = []
    monkeypatch.setattr(reg, "record_fetch_error",
                        lambda s, v, name, **kw: errors.append((name, kw.get("msg"))))
    # today 在所有 2026 会议之后 → 路径空 → 取不到值 → 记错
    summary = fw.run_fedwatch_fetch("m", "v", yf_module=_fake_yf({}), today=dt.date(2027, 6, 1))
    assert summary["failed"] == 1 and summary["fetched"] == 0
    assert errors and errors[0][0] == "下次会议隐含利率"

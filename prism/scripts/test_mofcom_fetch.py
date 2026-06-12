"""mofcom 通道单测（仿 test_recipe_fetch.py）：纯函数手算对值 → fetch_by_mofcom 注入 mock →
run_mofcom_fetch monkeypatch 登记表。零网络。"""
import pytest

from prism.scripts import mofcom_fetch
from prism.scripts import macro_registry as reg


# ---- 纯函数 ----

def test_monthly_flows_parses_sorts_skips():
    rows = [
        {"date": "202402", "tiosfs": 20},
        {"date": "202401", "tiosfs": "10"},
        {"date": "2024", "tiosfs": 99},        # date 不足 6 位 → 跳
        {"date": "202403", "tiosfs": None},     # 值非数 → 跳
    ]
    assert mofcom_fetch._monthly_flows(rows) == [("2024-01", 10.0), ("2024-02", 20.0)]


def test_monthly_flows_custom_field():
    rows = [{"date": "202401", "tiosfs": 10, "rmblaon": -4}]
    assert mofcom_fetch._monthly_flows(rows, field="rmblaon") == [("2024-01", -4.0)]


@pytest.mark.parametrize("label,expect", [
    ("2026年第1季度", (2026, 1)),
    ("2025年第1-2季度", (2025, 2)),
    ("2025年第1-3季度", (2025, 3)),
    ("2025年第1-4季度", (2025, 4)),
    ("乱码", None),
])
def test_parse_gdp_quarter(label, expect):
    assert mofcom_fetch._parse_gdp_quarter(label) == expect


def _full_gdp_rows():
    # 2023 累计: 100/210/330/460（单季 100/110/120/130）；2024: 140/300/470/650（140/160/170/180）
    return [
        ("2023年第1季度", 100), ("2023年第1-2季度", 210),
        ("2023年第1-3季度", 330), ("2023年第1-4季度", 460),
        ("2024年第1季度", 140), ("2024年第1-2季度", 300),
        ("2024年第1-3季度", 470), ("2024年第1-4季度", 650),
    ]


def test_annual_gdp_map_trailing4q():
    m = mofcom_fetch._annual_gdp_map(_full_gdp_rows())
    assert m[(2023, 4)] == 460        # 滚动4季@Q4 == FY 累计
    assert m[(2024, 4)] == 650
    assert m[(2024, 1)] == 500        # 140 + 130 + 120 + 110（跨 2023）
    assert (2023, 1) not in m         # 缺 2022 单季 → 不入 map


def test_annual_gdp_at_picks_latest_quarter_not_future():
    m = mofcom_fetch._annual_gdp_map(_full_gdp_rows())
    assert mofcom_fetch._annual_gdp_at(m, "2024-04") == 500   # 季末月≤4 → 2024Q1
    assert mofcom_fetch._annual_gdp_at(m, "2024-12") == 650   # → 2024Q4
    assert mofcom_fetch._annual_gdp_at(m, "2024-06") == m[(2024, 2)]  # 季末月=6 → 2024Q2


def test_credit_impulse_hand_computed():
    # window=2，gdp 常数 100 → ratio=Σ2/100。flows 10,10,10,20,20,20
    flows = [("2024-01", 10), ("2024-02", 10), ("2024-03", 10),
             ("2024-04", 20), ("2024-05", 20), ("2024-06", 20)]
    gdp = {(2024, 1): 100, (2024, 2): 100}
    val, as_of = mofcom_fetch.credit_impulse(flows, gdp, window=2)
    # ratio(06)=40/100=.4; ratio(04)=30/100=.3 → (.4-.3)*100=10pp
    assert val == pytest.approx(10.0) and as_of == "2024-06"


def test_credit_impulse_insufficient_history():
    flows = [("2024-01", 10), ("2024-02", 20)]   # < 2*window
    assert mofcom_fetch.credit_impulse(flows, {(2024, 1): 100}, window=2) == (None, None)


# ---- fetch_by_mofcom（注入 mock client + gdp_rows，零网络）----

def _fake_client(rows):
    class _Resp:
        def __init__(self, r): self._r = r
        def raise_for_status(self): pass
        def json(self): return self._r
    class _Client:
        def __init__(self, r): self._r = r
        def post(self, url, headers=None, timeout=None): return _Resp(self._r)
    return _Client(rows)


def test_fetch_by_mofcom_credit_impulse():
    rows = [{"date": f"2024{m:02d}", "tiosfs": v} for m, v in
            [(1, 10), (2, 10), (3, 10), (4, 20), (5, 20), (6, 20)]]
    cfg = {"metric": "credit_impulse", "window_months": 2}
    val, as_of = mofcom_fetch.fetch_by_mofcom(
        cfg, client=_fake_client(rows), gdp_rows=_full_gdp_rows())
    # gdp(06)=2024Q2=550, gdp(04)=2024Q1=500 → (40/550 − 30/500)*100
    assert as_of == "2024-06"
    assert val == pytest.approx((40 / 550 - 30 / 500) * 100, abs=1e-6)


def test_fetch_by_mofcom_unknown_metric_raises():
    with pytest.raises(ValueError, match="未知 mofcom.metric"):
        mofcom_fetch.fetch_by_mofcom({"metric": "nope"}, client=_fake_client([]))


# ---- run_mofcom_fetch（monkeypatch 登记表）----

def test_run_only_scripted_mofcom(monkeypatch):
    fake = {"inputs": [
        {"name": "信贷脉冲", "fetch_method": "mofcom", "availability": "scripted",
         "mofcom": {"metric": "credit_impulse"}},
        {"name": "待脚本", "fetch_method": "mofcom", "availability": "scriptable_todo"},
        {"name": "LLM取", "fetch_method": "mofcom", "availability": "llm"},
        {"name": "别的通道", "fetch_method": "akshare", "availability": "scripted"},
    ]}
    monkeypatch.setattr(reg, "read_registry", lambda s, v: fake)
    monkeypatch.setattr(mofcom_fetch, "fetch_by_mofcom",
                        lambda cfg, client=None: (-1.85, "2026-04"))
    recorded = []
    monkeypatch.setattr(reg, "record_observation",
                        lambda s, v, name, **kw: recorded.append((name, kw.get("value"), kw.get("as_of"))))
    summary = mofcom_fetch.run_mofcom_fetch("m", "v", client=object())
    assert recorded == [("信贷脉冲", -1.85, "2026-04")]
    assert summary == {"fetched": 1, "skipped_todo": 1, "skipped_llm": 1, "failed": 0}


def test_run_records_error_on_failure(monkeypatch):
    fake = {"inputs": [
        {"name": "信贷脉冲", "fetch_method": "mofcom", "availability": "scripted",
         "mofcom": {"metric": "credit_impulse"}},
    ]}
    monkeypatch.setattr(reg, "read_registry", lambda s, v: fake)
    def _boom(cfg, client=None):
        raise RuntimeError("TLS down")
    monkeypatch.setattr(mofcom_fetch, "fetch_by_mofcom", _boom)
    errors = []
    monkeypatch.setattr(reg, "record_fetch_error",
                        lambda s, v, name, **kw: errors.append((name, kw.get("msg"))))
    summary = mofcom_fetch.run_mofcom_fetch("m", "v", client=object())
    assert summary["failed"] == 1 and summary["fetched"] == 0
    assert errors and errors[0][0] == "信贷脉冲" and "TLS down" in errors[0][1]

"""cftc 取数通道：fetch_by_cftc 解析 + run_cftc_fetch 派发（mock httpx，零网络）。

覆盖：净头寸+z 正算、最新行选取、样本不足 z=None、std=0 z=None、cohort 切换、
空数据软降级、缺 contract/dataset 抛、未知 cohort 抛、缺腿行跳过；run 级成功/失败/only/跳过。
"""
from __future__ import annotations

import statistics

import pytest

from prism.scripts import cftc_fetch as cf


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeClient:
    """mock httpx.Client：.get(url, params=) → FakeResp(payload)。记录 calls 供断言。"""

    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def get(self, url, params=None):
        self.calls.append((url, params))
        return FakeResp(self._payload)


def _row(date, lng, sht, oi=1000000):
    return {"report_date_as_yyyy_mm_dd": f"{date}T00:00:00.000",
            "lev_money_positions_long": str(lng),
            "lev_money_positions_short": str(sht),
            "open_interest_all": str(oi)}


def test_net_and_z_computed():
    # 4 行降序；净头寸 net = long - short = [-100, -80, -60, -40]
    rows = [_row("2026-06-02", 400, 500), _row("2026-05-26", 420, 500),
            _row("2026-05-19", 440, 500), _row("2026-05-12", 460, 500)]
    cli = FakeClient(rows)
    v, z, d = cf.fetch_by_cftc(
        {"dataset": "gpe5-46if", "contract": "UST 10Y NOTE", "min_obs": 4}, client=cli)
    nets = [-100, -80, -60, -40]
    expected_z = (nets[0] - statistics.fmean(nets)) / statistics.pstdev(nets)
    assert v == -100 and d == "2026-06-02"
    assert abs(z - expected_z) < 1e-9
    _, params = cli.calls[0]
    assert params["$where"] == "contract_market_name='UST 10Y NOTE'"
    assert "DESC" in params["$order"] and params["$limit"] == "156"


def test_latest_row_is_first():
    rows = [_row("2026-06-02", 100, 900), _row("2026-05-26", 500, 500)]
    v, _, d = cf.fetch_by_cftc(
        {"dataset": "d", "contract": "c", "min_obs": 99}, client=FakeClient(rows))
    assert v == -800 and d == "2026-06-02"


def test_insufficient_obs_z_none():
    rows = [_row("2026-06-02", 400, 500), _row("2026-05-26", 420, 500)]
    v, z, _ = cf.fetch_by_cftc(
        {"dataset": "d", "contract": "c", "min_obs": 30}, client=FakeClient(rows))
    assert v == -100 and z is None


def test_zero_std_z_none():
    rows = [_row("2026-06-02", 400, 500), _row("2026-05-26", 400, 500),
            _row("2026-05-19", 400, 500)]
    v, z, _ = cf.fetch_by_cftc(
        {"dataset": "d", "contract": "c", "min_obs": 3}, client=FakeClient(rows))
    assert v == -100 and z is None


def test_cohort_switch_reads_asset_mgr():
    rows = [{"report_date_as_yyyy_mm_dd": "2026-06-02T00:00:00.000",
             "asset_mgr_positions_long": "900", "asset_mgr_positions_short": "100"}]
    cli = FakeClient(rows)
    v, _, _ = cf.fetch_by_cftc(
        {"dataset": "d", "contract": "c", "cohort": "asset_mgr", "min_obs": 99}, client=cli)
    assert v == 800
    assert "asset_mgr_positions_long" in cli.calls[0][1]["$select"]


def test_empty_data_returns_none():
    v, z, d = cf.fetch_by_cftc({"dataset": "d", "contract": "c"}, client=FakeClient([]))
    assert v is None and z is None and d is None


def test_rows_missing_legs_skipped():
    rows = [{"report_date_as_yyyy_mm_dd": "2026-06-02T00:00:00.000",
             "lev_money_positions_long": "400"},   # 缺 short
            _row("2026-05-26", 420, 500)]
    v, _, d = cf.fetch_by_cftc(
        {"dataset": "d", "contract": "c", "min_obs": 99}, client=FakeClient(rows))
    assert v == -80 and d == "2026-05-26"   # 首行缺腿被跳过，value/as_of 对齐次行


def test_missing_dataset_raises():
    with pytest.raises(ValueError, match="dataset"):
        cf.fetch_by_cftc({"contract": "c"}, client=FakeClient([]))


def test_missing_contract_raises():
    with pytest.raises(ValueError, match="contract"):
        cf.fetch_by_cftc({"dataset": "d"}, client=FakeClient([]))


def test_unknown_cohort_raises():
    with pytest.raises(ValueError, match="cohort"):
        cf.fetch_by_cftc({"dataset": "d", "contract": "c", "cohort": "retail"},
                         client=FakeClient([]))


# --- run_cftc_fetch 派发 ---

def _patch_reg(monkeypatch, inputs):
    from prism.scripts import macro_registry as reg
    monkeypatch.setattr(reg, "read_registry", lambda s, v: {"inputs": inputs})
    obs, errs = [], []
    monkeypatch.setattr(reg, "record_observation",
                        lambda s, v, name, **kw: obs.append((name, kw.get("value"), kw.get("z"))))
    monkeypatch.setattr(reg, "record_fetch_error",
                        lambda s, v, name, **kw: errs.append((name, kw.get("msg"))))
    return obs, errs


def test_run_records_observation(monkeypatch):
    rows = [_row("2026-06-02", 400, 500), _row("2026-05-26", 420, 500)]
    obs, errs = _patch_reg(monkeypatch, [
        {"name": "持仓拥挤", "fetch_method": "cftc", "availability": "scripted",
         "cftc": {"dataset": "d", "contract": "c", "min_obs": 2}},
        {"name": "别的", "fetch_method": "fred-api"},   # 非 cftc → 跳过
    ])
    summary = cf.run_cftc_fetch("m", "v", client=FakeClient(rows))
    assert obs and obs[0][0] == "持仓拥挤" and obs[0][1] == -100
    assert summary["fetched"] == 1 and not errs


def test_run_records_error_on_empty(monkeypatch):
    obs, errs = _patch_reg(monkeypatch, [
        {"name": "持仓拥挤", "fetch_method": "cftc", "availability": "scripted",
         "cftc": {"dataset": "d", "contract": "c"}}])
    summary = cf.run_cftc_fetch("m", "v", client=FakeClient([]))
    assert not obs and errs and summary["failed"] == 1


def test_run_only_filters(monkeypatch):
    rows = [_row("2026-06-02", 400, 500)]
    obs, _ = _patch_reg(monkeypatch, [
        {"name": "A", "fetch_method": "cftc", "availability": "scripted",
         "cftc": {"dataset": "d", "contract": "c", "min_obs": 99}},
        {"name": "B", "fetch_method": "cftc", "availability": "scripted",
         "cftc": {"dataset": "d", "contract": "c", "min_obs": 99}}])
    summary = cf.run_cftc_fetch("m", "v", only={"A"}, client=FakeClient(rows))
    assert [o[0] for o in obs] == ["A"] and summary["fetched"] == 1


def test_run_skips_non_scripted(monkeypatch):
    obs, _ = _patch_reg(monkeypatch, [
        {"name": "待办", "fetch_method": "cftc", "availability": "scriptable_todo",
         "cftc": {"dataset": "d", "contract": "c"}}])
    summary = cf.run_cftc_fetch("m", "v", client=FakeClient([]))
    assert not obs and summary["skipped_todo"] == 1

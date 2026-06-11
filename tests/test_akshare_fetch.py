"""akshare 取数通道：fetch_by_akshare 解析（mock akshare，零网络）。

覆盖这次实测踩到的坑：DataFrame 排序方向不一须按日期取 max、中文日期归一、
多行同期 filter+agg、白名单拦截、列缺失/取不到值的诚实降级。"""
from __future__ import annotations

import pandas as pd
import pytest

from prism.scripts import akshare_fetch as af


class FakeAk:
    """mock akshare：覆盖降序/升序/多行同期/季度四种形态。"""

    def macro_china_cpi(self):  # 降序：新值在头
        return pd.DataFrame({"月份": ["2026年05月份", "2026年04月份", "2008年01月份"],
                             "全国-同比增长": [1.2, 0.9, 7.07]})

    def macro_china_lpr(self):  # 升序：新值在尾
        return pd.DataFrame({"TRADE_DATE": ["2006-10-08", "2026-05-20"],
                             "LPR1Y": [4.0, 3.0], "LPR5Y": [4.8, 3.5]})

    def stock_hsgt_fund_flow_summary_em(self):  # 多行同期，须 filter+sum
        return pd.DataFrame({"交易日": ["2026-06-11"] * 3,
                             "资金方向": ["南向", "南向", "北向"],
                             "成交净买额": [0.5, 6.1, 0.0]})

    def macro_china_gdp(self):  # 季度
        return pd.DataFrame({"季度": ["2006年第1季度", "2026年第1季度"], "同比": [12.4, 5.0]})

    def macro_china_new_house_price(self):  # 多城同期，mean
        return pd.DataFrame({"日期": ["2026-04-01", "2026-04-01", "2026-03-01"],
                             "环比": [100.2, 100.0, 99.9]})

    def bond_china_close_return(self, **kwargs):  # 整条曲线：多档期限/多日，须按 row_filter 取某期限点
        self.last_kwargs = kwargs  # 捕获以验证动态日期占位符已解析
        return pd.DataFrame({
            "日期": ["2026-06-09", "2026-06-09", "2026-06-10", "2026-06-10"],
            "期限": [0.5, 1.0, 0.5, 1.0],
            "到期收益率": [1.40, 1.4617, 1.41, 1.4650]})

    def macro_china_central_bank_balance(self):  # 央行资产负债表：Sina 'YYYY.M' 月份、降序（新在头）
        return pd.DataFrame({"统计时间": ["2026.4", "2026.3", "2025.12"],
                             "外汇": [215381.08, 214425.31, 212391.23]})


@pytest.fixture
def ak():
    return FakeAk()


def test_descending_picks_latest_by_date(ak):
    v, d = af.fetch_by_akshare(
        {"func": "macro_china_cpi", "date_column": "月份", "value_column": "全国-同比增长"}, ak_module=ak)
    assert v == 1.2 and d == "2026-05"


def test_ascending_picks_latest_by_date(ak):
    v, d = af.fetch_by_akshare(
        {"func": "macro_china_lpr", "date_column": "TRADE_DATE", "value_column": "LPR1Y"}, ak_module=ak)
    assert v == 3.0 and d == "2026-05-20"


def test_row_filter_and_sum(ak):
    v, d = af.fetch_by_akshare(
        {"func": "stock_hsgt_fund_flow_summary_em", "date_column": "交易日", "value_column": "成交净买额",
         "row_filter": {"资金方向": "南向"}, "agg": "sum"}, ak_module=ak)
    assert abs(v - 6.6) < 1e-9 and d == "2026-06-11"


def test_quarter_date_normalized(ak):
    v, d = af.fetch_by_akshare(
        {"func": "macro_china_gdp", "date_column": "季度", "value_column": "同比"}, ak_module=ak)
    assert v == 5.0 and d == "2026-Q1"


def test_mean_over_latest_date(ak):
    v, d = af.fetch_by_akshare(
        {"func": "macro_china_new_house_price", "date_column": "日期", "value_column": "环比",
         "agg": "mean"}, ak_module=ak)
    assert abs(v - 100.1) < 1e-9 and d == "2026-04-01"


def test_whitelist_blocks_unknown_func(ak):
    with pytest.raises(ValueError, match="白名单"):
        af.fetch_by_akshare({"func": "os_system_evil", "date_column": "x", "value_column": "y"}, ak_module=ak)


def test_missing_column_raises(ak):
    with pytest.raises(ValueError, match="列不存在"):
        af.fetch_by_akshare(
            {"func": "macro_china_cpi", "date_column": "月份", "value_column": "不存在列"}, ak_module=ak)


def test_curve_row_filter_picks_tenor_point(ak):
    # NCD：整条曲线按 期限==1.0 取 1 年期点，再取最新日期的到期收益率
    v, d = af.fetch_by_akshare(
        {"func": "bond_china_close_return",
         "args": {"symbol": "同业存单(AAA)", "period": "1",
                  "start_date": "@days_ago:20", "end_date": "@today"},
         "row_filter": {"期限": 1.0}, "date_column": "日期", "value_column": "到期收益率"},
        ak_module=ak)
    assert abs(v - 1.4650) < 1e-9 and d == "2026-06-10"
    # 动态日期占位符在传入 akshare 前已解析成 YYYYMMDD（非 '@...'）
    assert ak.last_kwargs["end_date"].isdigit() and len(ak.last_kwargs["end_date"]) == 8
    assert not ak.last_kwargs["start_date"].startswith("@")


def test_resolve_dynamic_args():
    import datetime
    today = datetime.date.today()
    out = af._resolve_dynamic_args(
        {"symbol": "x", "start_date": "@days_ago:20", "end_date": "@today"})
    assert out["symbol"] == "x"  # 非占位符原样透传
    assert out["end_date"] == today.strftime("%Y%m%d")
    assert out["start_date"] == (today - datetime.timedelta(days=20)).strftime("%Y%m%d")


def test_resolve_dynamic_args_unknown_placeholder_raises():
    with pytest.raises(ValueError, match="未知日期占位符"):
        af._resolve_dynamic_args({"d": "@yesterday"})


def test_norm_date_formats():
    assert af._norm_date("2026年05月份")[1] == "2026-05"
    assert af._norm_date("2026年第3季度")[1] == "2026-Q3"
    assert af._norm_date("2026年05月07日")[1] == "2026-05-07"
    assert af._norm_date("2026-05-20")[1] == "2026-05-20"
    assert af._norm_date("2026.4")[1] == "2026-04"     # Sina Mac 'YYYY.M'（外汇占款）
    assert af._norm_date("2025.12")[1] == "2025-12"
    import datetime
    assert af._norm_date(datetime.date(2026, 4, 1))[1] == "2026-04-01"


def test_central_bank_balance_picks_latest_month(ak):
    # 外汇占款：'YYYY.M' 月份须正确归一取最新（否则全行落 (0,0,0) 并列误取首行）
    v, d = af.fetch_by_akshare(
        {"func": "macro_china_central_bank_balance", "date_column": "统计时间", "value_column": "外汇"},
        ak_module=ak)
    assert abs(v - 215381.08) < 1e-9 and d == "2026-04"

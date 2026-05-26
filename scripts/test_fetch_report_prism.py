"""Smoke tests for fetch_report_prism — Q1 fetch 缺陷修复回归。

不调真实 cninfo，只验证：
- _CATEGORY 拆分 quarterly → q1+q3 后含两个 key
- _QUARTERLY_CATEGORIES = ('q1', 'q3')
- fetch() quarter 参数校验
- fan-out 分支：mock _list_reports 验证调两次（quarter=None）+ 调一次（quarter=1 或 3）
"""
from unittest.mock import patch, MagicMock

import pytest

from scripts import fetch_report_prism as frp


def test_category_has_q1_q3():
    """修 Q1 缺陷后 _CATEGORY 必须含 q1/q3 而非单一 quarterly。"""
    assert "q1" in frp._CATEGORY
    assert "q3" in frp._CATEGORY
    assert frp._CATEGORY["q1"] == "category_yjdbg_szsh"
    assert frp._CATEGORY["q3"] == "category_sjdbg_szsh"
    assert "quarterly" not in frp._CATEGORY, (
        "quarterly 由 fetch() 内部 fan-out，不应在 _CATEGORY 字典里"
    )


def test_quarterly_categories_constant():
    assert frp._QUARTERLY_CATEGORIES == ("q1", "q3")


def test_fetch_invalid_quarter_raises():
    """quarter 必须为 1/3/None。其他值 raise。"""
    with patch.object(frp, "_route", return_value="cn"), \
         patch.object(frp, "_company_info",
                      return_value={"code": "688331", "orgId": "9900044", "zwjc": "X"}):
        with pytest.raises(ValueError, match="quarter=2"):
            frp.fetch("SSE_688331", "quarterly", 2025, quarter=2)
        with pytest.raises(ValueError, match="quarter=0"):
            frp.fetch("SSE_688331", "quarterly", 2025, quarter=0)


def _stub_list_reports_factory(by_category: dict):
    """按 category 返回不同 announcement list。"""
    def _stub(code, org_id, column, category):
        return by_category.get(category, [])
    return _stub


def test_fetch_quarterly_fan_out_queries_both_categories():
    """quarter=None 时必须查 yjdbg + sjdbg 两个 category。"""
    calls = []

    def _track_list(code, org_id, column, category):
        calls.append(category)
        # 给两个 category 各返回 1 份 2025 报告，让后续逻辑能跑通
        if category == "category_yjdbg_szsh":
            return [{
                "announcementTitle": "荣昌生物2025年第一季度报告",
                "announcementTime": 1714435200000,  # 2024-04-30 UTC
                "adjunctUrl": "fake_q1.pdf",
            }]
        if category == "category_sjdbg_szsh":
            return [{
                "announcementTitle": "荣昌生物2025年第三季度报告",
                "announcementTime": 1730246400000,  # 2024-10-30 UTC
                "adjunctUrl": "fake_q3.pdf",
            }]
        return []

    with patch.object(frp, "_route", return_value="cn"), \
         patch.object(frp, "_company_info",
                      return_value={"code": "688331", "orgId": "9900044", "zwjc": "荣昌"}), \
         patch.object(frp, "_list_reports", side_effect=_track_list), \
         patch.object(frp, "_download", return_value="/tmp/fake.pdf"):
        result = frp.fetch("SSE_688331", "quarterly", 2025)
    # fan-out 必须查两次
    assert calls == ["category_yjdbg_szsh", "category_sjdbg_szsh"]
    assert result == "/tmp/fake.pdf"


def test_fetch_quarterly_explicit_q1_queries_only_q1():
    """quarter=1 时只查 yjdbg，不查 sjdbg。"""
    calls = []

    def _track_list(code, org_id, column, category):
        calls.append(category)
        if category == "category_yjdbg_szsh":
            return [{
                "announcementTitle": "X2025年第一季度报告",
                "announcementTime": 1714435200000,
                "adjunctUrl": "q1.pdf",
            }]
        return []

    with patch.object(frp, "_route", return_value="cn"), \
         patch.object(frp, "_company_info",
                      return_value={"code": "688331", "orgId": "9", "zwjc": "X"}), \
         patch.object(frp, "_list_reports", side_effect=_track_list), \
         patch.object(frp, "_download", return_value="/tmp/q1.pdf"):
        frp.fetch("SSE_688331", "quarterly", 2025, quarter=1)
    assert calls == ["category_yjdbg_szsh"]


def test_fetch_quarterly_explicit_q3_queries_only_q3():
    calls = []

    def _track_list(code, org_id, column, category):
        calls.append(category)
        if category == "category_sjdbg_szsh":
            return [{
                "announcementTitle": "X2025年第三季度报告",
                "announcementTime": 1730246400000,
                "adjunctUrl": "q3.pdf",
            }]
        return []

    with patch.object(frp, "_route", return_value="cn"), \
         patch.object(frp, "_company_info",
                      return_value={"code": "688331", "orgId": "9", "zwjc": "X"}), \
         patch.object(frp, "_list_reports", side_effect=_track_list), \
         patch.object(frp, "_download", return_value="/tmp/q3.pdf"):
        frp.fetch("SSE_688331", "quarterly", 2025, quarter=3)
    assert calls == ["category_sjdbg_szsh"]


def test_fetch_quarterly_fan_out_picks_latest_when_both_present():
    """fan-out 时 Q1+Q3 同年都披露 → 取最新（Q3 优先于 Q1）。"""
    captured = {}

    def _stub_download(announcement, *args, **kwargs):
        captured["title"] = announcement["announcementTitle"]
        return "/tmp/picked.pdf"

    def _list(code, org_id, column, category):
        if category == "category_yjdbg_szsh":
            return [{
                "announcementTitle": "荣昌生物2025年第一季度报告",
                "announcementTime": 1714435200000,  # 2024-04-30
                "adjunctUrl": "q1.pdf",
            }]
        if category == "category_sjdbg_szsh":
            return [{
                "announcementTitle": "荣昌生物2025年第三季度报告",
                "announcementTime": 1730246400000,  # 2024-10-30 (later)
                "adjunctUrl": "q3.pdf",
            }]
        return []

    with patch.object(frp, "_route", return_value="cn"), \
         patch.object(frp, "_company_info",
                      return_value={"code": "688331", "orgId": "9", "zwjc": "X"}), \
         patch.object(frp, "_list_reports", side_effect=_list), \
         patch.object(frp, "_download", side_effect=_stub_download):
        frp.fetch("SSE_688331", "quarterly", 2025)
    assert "第三季度" in captured["title"]


def test_fetch_annual_unchanged_first_published_semantics():
    """annual 不走 fan-out，保留原"取首发版"语义（earliest announcementTime）。"""
    captured = {}

    def _stub_download(announcement, *args, **kwargs):
        captured["title"] = announcement["announcementTitle"]
        return "/tmp/annual.pdf"

    def _list(code, org_id, column, category):
        # 同年两份（首发 + 延期），无更正字样
        return [
            {
                "announcementTitle": "X2024年年度报告",
                "announcementTime": 1714435200000,  # earliest
                "adjunctUrl": "first.pdf",
            },
            {
                "announcementTitle": "X2024年年度报告（延期披露）",
                "announcementTime": 1717113600000,  # later
                "adjunctUrl": "late.pdf",
            },
        ]

    with patch.object(frp, "_route", return_value="cn"), \
         patch.object(frp, "_company_info",
                      return_value={"code": "688331", "orgId": "9", "zwjc": "X"}), \
         patch.object(frp, "_list_reports", side_effect=_list), \
         patch.object(frp, "_download", side_effect=_stub_download):
        frp.fetch("SSE_688331", "annual", 2024)
    # 应该选首发版（earliest）
    assert "（延期披露）" not in captured["title"]

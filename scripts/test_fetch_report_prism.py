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
        result = frp.fetch("SSE_688331", "quarterly", 2025, with_announcements=False)
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
        frp.fetch("SSE_688331", "quarterly", 2025, quarter=1, with_announcements=False)
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
        frp.fetch("SSE_688331", "quarterly", 2025, quarter=3, with_announcements=False)
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
        frp.fetch("SSE_688331", "quarterly", 2025, with_announcements=False)
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
        frp.fetch("SSE_688331", "annual", 2024, with_announcements=False)
    # 应该选首发版（earliest）
    assert "（延期披露）" not in captured["title"]


# ----- 公告抓取（announcements）-----


def test_announcement_categories_high_signal():
    """高信号子集正好 5 类：业绩预告/增发/可转债/风险提示/特别处理。
    （gqjl 股权激励经 b66a997/F7 移除——其内容被 _TITLE_NOISE_RE 黑名单清零，保留只是徒增抓取。）"""
    assert set(frp._ANNOUNCEMENT_CATEGORIES.keys()) == {
        "yjygjxz", "zf", "kzz", "fxts", "tbclts",
    }
    assert frp._ANNOUNCEMENT_CATEGORIES["yjygjxz"] == "category_yjygjxz_szsh"
    assert "gqjl" not in frp._ANNOUNCEMENT_CATEGORIES


def test_fetch_announcements_cn_queries_all_categories():
    """fetch_announcements_cn 必须查全部 5 个 category，每类失败不影响其他。"""
    queried = []

    def _track(code, org_id, column, category):
        queried.append(category)
        if category == "category_yjygjxz_szsh":
            raise RuntimeError("simulated cninfo timeout")
        return []

    with patch.object(frp, "_company_info",
                      return_value={"code": "688331", "orgId": "9", "zwjc": "X"}), \
         patch.object(frp, "_list_reports", side_effect=_track):
        result = frp.fetch_announcements_cn("SSE_688331")
    # 即使第 1 类失败，剩 4 类还得查
    assert len(queried) == len(frp._ANNOUNCEMENT_CATEGORIES)
    assert "category_yjygjxz_szsh" in queried
    assert result == []


def test_within_window_filters_old_announcements():
    """_within_window 必须按 days 过滤，老公告剔除。"""
    import time
    now_ms = int(time.time() * 1000)
    fresh = {"announcementTime": now_ms - 100 * 86400 * 1000}   # 100 days ago
    stale = {"announcementTime": now_ms - 500 * 86400 * 1000}   # 500 days ago
    assert frp._within_window(fresh, 365) is True
    assert frp._within_window(stale, 365) is False


def test_fetch_with_announcements_false_skips_announcement_fetch():
    """with_announcements=False 时不调 fetch_announcements_cn。"""
    def _list(code, org_id, column, category):
        if category == "category_ndbg_szsh":
            return [{
                "announcementTitle": "X2024年年度报告",
                "announcementTime": 1714435200000,
                "adjunctUrl": "x.pdf",
            }]
        return []

    with patch.object(frp, "_route", return_value="cn"), \
         patch.object(frp, "_company_info",
                      return_value={"code": "688331", "orgId": "9", "zwjc": "X"}), \
         patch.object(frp, "_list_reports", side_effect=_list), \
         patch.object(frp, "_download", return_value="/tmp/x.pdf"), \
         patch.object(frp, "fetch_announcements_cn") as mock_ann:
        frp.fetch("SSE_688331", "annual", 2024, with_announcements=False)
    mock_ann.assert_not_called()


def test_fetch_with_announcements_default_triggers_cn():
    """默认 with_announcements=True 应调 fetch_announcements_cn 一次。"""
    def _list(code, org_id, column, category):
        if category == "category_ndbg_szsh":
            return [{
                "announcementTitle": "X2024年年度报告",
                "announcementTime": 1714435200000,
                "adjunctUrl": "x.pdf",
            }]
        return []

    with patch.object(frp, "_route", return_value="cn"), \
         patch.object(frp, "_company_info",
                      return_value={"code": "688331", "orgId": "9", "zwjc": "X"}), \
         patch.object(frp, "_list_reports", side_effect=_list), \
         patch.object(frp, "_download", return_value="/tmp/x.pdf"), \
         patch.object(frp, "fetch_announcements_cn", return_value=[]) as mock_ann:
        frp.fetch("SSE_688331", "annual", 2024)
    mock_ann.assert_called_once()


def test_fetch_by_keyword_cn_calls_search_all_pages():
    """A 股按需检索必须走 _search_all_pages，并过滤摘要/英文/更正/修订。"""
    import time
    now_ms = int(time.time() * 1000)
    hits = [
        {"announcementTitle": "X股权激励计划草案", "announcementTime": now_ms, "adjunctUrl": "1.pdf"},
        {"announcementTitle": "X股权激励计划草案摘要", "announcementTime": now_ms, "adjunctUrl": "2.pdf"},
        {"announcementTitle": "X股权激励计划英文版", "announcementTime": now_ms, "adjunctUrl": "3.pdf"},
        {"announcementTitle": "X股权激励计划授予完成", "announcementTime": now_ms - 86400_000,
         "adjunctUrl": "4.pdf"},
    ]
    downloaded = []

    def _stub_dl(a, dest_dir, company_name, ticker, category_key):
        downloaded.append(a["announcementTitle"])
        from pathlib import Path as P
        return P("/tmp/x.pdf")

    with patch.object(frp, "_company_info",
                      return_value={"code": "688331", "orgId": "9", "zwjc": "X"}), \
         patch.object(frp, "_search_all_pages", return_value=hits), \
         patch.object(frp, "_download_announcement", side_effect=_stub_dl):
        frp.fetch_by_keyword_cn("SSE_688331", "股权激励", max_hits=10)

    # 摘要/英文剔除，剩 2 条
    assert len(downloaded) == 2
    assert all("摘要" not in t and "英文" not in t for t in downloaded)


def test_fetch_by_keyword_cn_since_days_filter():
    """since_days=30 必须剔除 60 天前的命中。"""
    import time
    now_ms = int(time.time() * 1000)
    hits = [
        {"announcementTitle": "X重大事项", "announcementTime": now_ms, "adjunctUrl": "fresh.pdf"},
        {"announcementTitle": "X重大事项续", "announcementTime": now_ms - 60 * 86400_000,
         "adjunctUrl": "stale.pdf"},
    ]
    downloaded = []

    def _stub_dl(a, *args, **kwargs):
        downloaded.append(a["announcementTitle"])
        from pathlib import Path as P
        return P("/tmp/x.pdf")

    with patch.object(frp, "_company_info",
                      return_value={"code": "688331", "orgId": "9", "zwjc": "X"}), \
         patch.object(frp, "_search_all_pages", return_value=hits), \
         patch.object(frp, "_download_announcement", side_effect=_stub_dl):
        frp.fetch_by_keyword_cn("SSE_688331", "重大事项", since_days=30)

    assert len(downloaded) == 1
    assert "续" not in downloaded[0]


def test_fetch_by_keyword_routes_us_market():
    """fetch_by_keyword(NVDA, ...) 必须路由到 fetch_by_keyword_us。"""
    with patch.object(frp, "fetch_by_keyword_us", return_value=[]) as mock_us, \
         patch.object(frp, "fetch_by_keyword_cn", return_value=[]) as mock_cn:
        frp.fetch_by_keyword("NVDA", "merger")
    mock_us.assert_called_once()
    mock_cn.assert_not_called()


def test_fetch_by_keyword_unsupported_market_raises():
    """HK/UK/JP/KR 暂未支持，必须 raise NotImplementedError。"""
    with pytest.raises(NotImplementedError, match="hk"):
        frp.fetch_by_keyword("HK_02228", "重组")


def test_route_hkex_and_hk_both_map_to_hk():
    """F8: HKEX_ 是 canonical（create_topic/market_data 形式），HK_ 为向后兼容别名，二者都路由到 hk。"""
    assert frp._route("HKEX_09995") == "hk"
    assert frp._route("HK_02228") == "hk"


def test_fetch_by_keyword_hkex_prefix_also_unsupported():
    """F8: HKEX_ 与 HK_ 同走 hk 路径——keyword 检索对两者一致 raise NotImplementedError(hk)。"""
    with pytest.raises(NotImplementedError, match="hk"):
        frp.fetch_by_keyword("HKEX_09995", "重组")


def test_fetch_many_calls_announcements_once_not_per_year():
    """fetch_many(years=[2022,2023,2024]) 公告只拉一次，不是每年一次。"""
    def _list(code, org_id, column, category):
        if category == "category_ndbg_szsh":
            return [
                {"announcementTitle": "X2022年年度报告", "announcementTime": 1, "adjunctUrl": "a.pdf"},
                {"announcementTitle": "X2023年年度报告", "announcementTime": 2, "adjunctUrl": "b.pdf"},
                {"announcementTitle": "X2024年年度报告", "announcementTime": 3, "adjunctUrl": "c.pdf"},
            ]
        return []

    with patch.object(frp, "_route", return_value="cn"), \
         patch.object(frp, "_company_info",
                      return_value={"code": "688331", "orgId": "9", "zwjc": "X"}), \
         patch.object(frp, "_list_reports", side_effect=_list), \
         patch.object(frp, "_download", return_value="/tmp/x.pdf"), \
         patch.object(frp, "fetch_announcements_cn", return_value=[]) as mock_ann:
        frp.fetch_many("SSE_688331", [2022, 2023, 2024])
    mock_ann.assert_called_once()

"""pbc_mpr 取文 fetcher 单测（仿 test_recipe/mofcom）：纯函数解析 + fetch_pbc_mpr 注入 fake client。零网络。"""
import pytest

from prism.scripts import pbc_mpr_fetch as mpr
from prism.scripts import macro_registry as reg


# ---- 列表页样本：含简介 / 年汇总目录 / 多季度，故意乱序，断言取到最新季且排除噪声 ----
_INDEX = """
<ul>
  <li><a href="/zhengcehuobisi/125207/125227/125957/125985/2889622/index.html">《中国货币政策执行报告》简介</a></li>
  <li><a href="/zhengcehuobisi/125207/125227/125957/2026nhbzczxbg/index.html">2026年货币政策执行报告</a></li>
  <li><a href="/zhengcehuobisi/125207/125227/125957/aaa/2025111413/index.html">2025年第三季度中国货币政策执行报告</a></li>
  <li><a href="/zhengcehuobisi/125207/125227/125957/2026nhbzczxbg/2026052015172981527/index.html">2026年第一季度中国货币政策执行报告</a></li>
  <li><a href="/zhengcehuobisi/125207/125227/125957/bbb/2026040808/index.html">2025年第四季度中国货币政策执行报告</a></li>
</ul>
"""

# 报告正文页样本：带 PubDate meta + id="zoom" 容器 + footer 噪声
_REPORT = """
<html><head>
<meta name="PubDate" content="2026-05-11">
<meta name="Description" content="继续实施适度宽松的货币政策。">
</head><body>
<div class="nav">术语表 常见问题 网站地图 English Version</div>
<div id="zoom">
<p>2026年第一季度，稳健的货币政策灵活适度。下一阶段，继续实施适度宽松的货币政策，保持流动性充裕。</p>
</div>
<div class="footer">中国人民银行版权所有 京ICP备xxxxxxxx号</div>
</body></html>
"""


def test_find_latest_report_picks_newest_quarter_excludes_noise():
    res = mpr._find_latest_report(_INDEX)
    assert res is not None
    url, title, year, quarter = res
    assert (year, quarter) == (2026, 1)                 # 取最新季（非最大年汇总、非简介）
    assert title == "2026年第一季度中国货币政策执行报告"
    assert url == ("http://www.pbc.gov.cn/zhengcehuobisi/125207/125227/125957/"
                   "2026nhbzczxbg/2026052015172981527/index.html")


def test_find_latest_report_handles_arabic_quarter_and_whitespace():
    html = '<a href="/x/index.html">2025 年第 2 季度中国货币政策执行报告</a>'
    res = mpr._find_latest_report(html)
    assert res is not None and (res[2], res[3]) == (2025, 2)


def test_find_latest_report_none_when_only_intro():
    html = '<a href="/x">《中国货币政策执行报告》简介</a><a href="/y">2026年货币政策执行报告</a>'
    assert mpr._find_latest_report(html) is None


def test_extract_body_uses_zoom_and_cuts_footer():
    body, pubdate = mpr._extract_body(_REPORT)
    assert pubdate == "2026-05-11"
    assert "适度宽松" in body and "流动性充裕" in body
    assert "术语表" not in body              # nav 在 zoom 之前，被排除
    assert "版权所有" not in body            # footer 被截断


def test_extract_body_fallback_without_zoom():
    body, pubdate = mpr._extract_body("<html><body><p>无容器的纯文本正文</p></body></html>")
    assert "无容器的纯文本正文" in body and pubdate is None


# ---- fetch_pbc_mpr（注入 fake client：列表页 → 报告页两次 GET，零网络）----

class _Resp:
    def __init__(self, text):
        self.text = text
        self.encoding = "utf-8"
    def raise_for_status(self):
        pass


class _FakeClient:
    """按 URL 路由：列表页返 _INDEX，其余（报告页）返 _REPORT。记录访问序。"""
    def __init__(self):
        self.gets = []
    def get(self, url, timeout=None, follow_redirects=None, headers=None):
        self.gets.append(url)
        return _Resp(_INDEX if url == mpr._LIST_URL else _REPORT)


def test_fetch_pbc_mpr_writes_cache_and_fingerprint(tmp_path, monkeypatch):
    # 把 inbox 重定向到 tmp，避免污染真 topic
    monkeypatch.setattr(mpr, "_PRISM_ROOT", tmp_path)
    recorded = {}
    monkeypatch.setattr(reg, "set_local_cache_path",
                        lambda s, v, name, rel: recorded.update(slug=s, variant=v, name=name, rel=rel))
    res = mpr.fetch_pbc_mpr("myslug", "myvariant", client=_FakeClient(), input_name="货币政策执行报告 MPR")

    assert res["ok"] is True
    assert res["fingerprint"] == "mpr:2026Q1"
    assert res["pubdate"] == "2026-05-11"
    assert (res["year"], res["quarter"]) == (2026, 1)
    # 缓存落盘且含实质正文
    cache = tmp_path / "topics" / "myslug" / "inbox" / "pbc_mpr_latest.md"
    assert cache.exists()
    text = cache.read_text(encoding="utf-8")
    assert "2026年第一季度中国货币政策执行报告" in text and "适度宽松" in text
    # set_local_cache_path 以相对路径 + 正确输入名调用
    assert recorded["name"] == "货币政策执行报告 MPR"
    assert recorded["rel"] == "topics/myslug/inbox/pbc_mpr_latest.md"


def test_fetch_pbc_mpr_no_report_returns_error(tmp_path, monkeypatch):
    monkeypatch.setattr(mpr, "_PRISM_ROOT", tmp_path)

    class _OnlyIntro(_FakeClient):
        def get(self, url, timeout=None, follow_redirects=None, headers=None):
            self.gets.append(url)
            return _Resp('<a href="/x">《中国货币政策执行报告》简介</a>')

    res = mpr.fetch_pbc_mpr("s", "v", client=_OnlyIntro())
    assert "error" in res and "未找到季度报告" in res["error"]


def test_fetch_one_routes_with_entry_name(tmp_path, monkeypatch):
    monkeypatch.setattr(mpr, "_PRISM_ROOT", tmp_path)
    seen = {}
    monkeypatch.setattr(reg, "set_local_cache_path",
                        lambda s, v, name, rel: seen.update(name=name))
    res = mpr.fetch_one("s", "v", {"name": "MPR别名"}, client=_FakeClient())
    assert res["ok"] and seen["name"] == "MPR别名"

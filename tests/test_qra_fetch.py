"""QRA 取文通道：纯解析层（_find_doc / _extract_body / _strip_html / 日期正则）。

零网络、无登记表副作用——只测从索引页 HTML 取链接、从新闻稿纯文本截正文。
覆盖实测要点：声明/估计两种锚文本前缀、WASHINGTON→### 正文截取、
em-dash 与 double-hyphen 两种 WASHINGTON 开篇、### 缺失时的兜底结束标记。
"""
from __future__ import annotations

from prism.scripts import qra_fetch as qf

# 索引页片段：含两份目标公告锚 + 一堆无关锚（确保不被首个非匹配锚提前返回）
_INDEX_HTML = """
<a href="/policy-issues/financing-the-government">Financing the Government</a>
<a href="/news/press-releases/sb0485">Financing Estimates: 2026 - 2nd Quarter</a>
<a href="/news/press-releases/sb0486">Economic Policy Statements to TBAC: 2026 - 2nd Quarter</a>
<a href="/news/press-releases/sb0489">Policy Statement: 2026 - 2nd Quarter</a>
<a href="/news/press-releases/sb0527">Some unrelated press release</a>
"""

_STMT_HTML = """<html><head><title>QRS</title></head><body>
<div>Skip to main content</div><div>Breadcrumb Home News Press Releases</div>
<h1>Quarterly Refunding Statement of Deputy Assistant Secretary Brian Smith</h1>
<p>May 6, 2026</p>
<p>WASHINGTON &mdash; The U.S. Department of the Treasury is offering $125 billion
to refund approximately $83.3 billion.</p>
<p>A 3-year note in the amount of $58 billion;</p>
<p>The next quarterly refunding announcement will take place on Wednesday, August 5, 2026.</p>
<p>###</p>
<div>Use featured image Off Latest News June 10, 2026 Unrelated</div>
</body></html>"""

# 净借款估计：双连字符开篇、正文前无日期行（实测 sb0485 形态）
_FIN_HTML = """<body><h1>Treasury Announces Marketable Borrowing Estimates</h1>
<p>WASHINGTON -- The U.S. Department of the Treasury today announced its current
estimates. Treasury expects to borrow $189 billion in privately-held net marketable debt.</p>
<p>###</p><div>Latest News chrome</div></body>"""


def test_find_doc_picks_policy_statement():
    path, quarter = qf._find_doc(_INDEX_HTML, "Policy Statement")
    assert path == "/news/press-releases/sb0489"
    assert quarter == "2026 - 2nd Quarter"


def test_find_doc_picks_financing_estimates():
    path, quarter = qf._find_doc(_INDEX_HTML, "Financing Estimates")
    assert path == "/news/press-releases/sb0485"
    assert quarter == "2026 - 2nd Quarter"


def test_find_doc_does_not_early_return_on_nonmatch():
    # 目标锚不在首位——确保扫描穿过前面的无关锚，不被提前 return None
    path, _ = qf._find_doc(_INDEX_HTML, "Policy Statement")
    assert path is not None


def test_find_doc_missing_label_returns_none():
    assert qf._find_doc(_INDEX_HTML, "Nonexistent Label") == (None, None)


def test_extract_body_statement_washington_to_hashes():
    body = qf._extract_body(qf._strip_html(_STMT_HTML))
    assert body.startswith("WASHINGTON")
    assert "$125 billion" in body and "$58 billion" in body
    assert "###" not in body            # ### 之后截断
    assert "Latest News" not in body    # 站点 chrome 不入正文


def test_extract_body_handles_double_hyphen_opening():
    body = qf._extract_body(qf._strip_html(_FIN_HTML))
    assert body.startswith("WASHINGTON")
    assert "$189 billion" in body
    assert "###" not in body and "Latest News" not in body


def test_extract_body_fallback_end_markers_without_hashes():
    # 无 ### 时退到 "Latest News" 等兜底结束标记
    text = "WASHINGTON -- body text here.\nLatest News\nchrome chrome"
    assert qf._extract_body(text) == "WASHINGTON -- body text here."


def test_extract_body_keeps_full_text_when_no_start_marker():
    text = "No dateline marker at all, just prose.\n###\ntail"
    assert qf._extract_body(text) == "No dateline marker at all, just prose."


def test_date_regex_matches_em_dash_statement():
    plain = qf._strip_html(_STMT_HTML)
    m = qf._DATE_BEFORE.search(plain)
    assert m and m.group(1) == "May 6, 2026"

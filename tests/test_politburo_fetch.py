"""中国政治局/NPC 经济信号 取文通道：纯解析层（english.gov.cn 双 feed）。

零网络、无登记表副作用——只测从静态 /news/ + /policies/latestreleases/ 索引挑会议/政策稿、
从文章 HTML 截正文。覆盖实拉验证的结构要点：
  · _find_items：真文章 href（/(news|policies)/YYYYMM/DD/content_WS<hash>.html，含协议相对）+
    关键词命中（政治局/经济会议/政府工作报告），排外交/DPRK/体育噪声，保序去重 + _MAX_ITEMS 截断。
  · _extract_body：Artical_Content 容器 + BEIJING dateline 起 + footer 截尾去站点 chrome。
  · _DATE 配 "Updated: December 8, 2025"；_hash_of / 指纹：hash 集变→指纹变、集同→指纹稳（无新会议不误触发）。
"""
from __future__ import annotations

from prism.scripts import politburo_fetch as pf


# ── 索引页 fixture（实拉形态：协议相对锚 content_WS<hash>.html + 综合 feed 噪声） ──────
def _a(href: str, title: str) -> str:
    return f'<a class="t" href="{href}">{title}</a>'


_NEWS_HTML = "\n".join([
    _a("//english.www.gov.cn/news/202512/08/content_WSaaaa0001.html",
       "CPC leadership holds meeting on 2026 economic work"),                       # ✓ 政治局经济会议
    _a("//english.www.gov.cn/news/202604/28/content_WSaaaa0002.html",
       "Xi chairs CPC leadership meeting to analyze economic situation"),           # ✓ 政治局
    _a("//english.www.gov.cn/news/202606/10/content_WSaaaa0003.html",
       "China, DPRK reach new important consensus on bilateral ties"),              # ✗ 外交噪声
    _a("//english.www.gov.cn/news/202606/09/content_WSaaaa0004.html",
       "Chinese vice premier to attend World Convergence Summit for Growth"),       # ✗ 泛新闻（无关键词）
    _a("/news/202606/08/content_WSaaaa0002.html",                                   # 同 hash 0002（根相对）——去重
       "Update: Xi chairs CPC leadership meeting to analyze economic situation"),
    _a("https://english.www.gov.cn/about/", "About this site"),                     # ✗ 非文章 href
])

_POLICY_HTML = "\n".join([
    _a("//english.www.gov.cn/policies/latestreleases/202603/05/content_WSbbbb0001.html",
       "Full text: Report on the work of the government 2026"),                     # ✓ 政府工作报告
    _a("//english.www.gov.cn/policies/latestreleases/202606/08/content_WSbbbb0002.html",
       "Premier chairs State Council executive meeting on fiscal policy"),          # ✓ 国务院/财政
    _a("//english.www.gov.cn/policies/latestreleases/202606/05/content_WSbbbb0003.html",
       "China issues guideline on rural road maintenance"),                        # ✗ 细分政策噪声
])

# english.gov.cn 文章正文：div class=Artical_Content + BEIJING dateline + Updated 日期 + footer
_ARTICLE = """<html><head>
<meta name="source" content="Xinhua" /><span class="date">Updated: December 8, 2025 14:38</span>
</head><body>
<nav>Home > News breadcrumb chrome</nav>
<div class="Artical_Content">
<p>BEIJING, Dec. 8 -- The Political Bureau of the CPC Central Committee on Monday held a meeting
to analyze the economic work of 2026.</p>
<p>The meeting stressed a more proactive fiscal policy and a moderately loose monetary policy.</p>
</div>
<div class="edit">Editor: Zhang</div>
<footer>Copyright© All Rights Reserved Back to the top</footer>
</body></html>"""


def test_find_items_keyword_filter_keeps_meetings_drops_noise():
    items = pf._find_items(_NEWS_HTML)
    titles = [t for _, t in items]
    assert any("economic work" in t.lower() for t in titles)
    assert any("analyze economic situation" in t.lower() for t in titles)
    # 外交/泛新闻/非文章链接被排除
    assert not any("DPRK" in t or "World Convergence" in t or "About" in t for t in titles)


def test_find_items_dedupes_by_hash_and_resolves_protocol_relative():
    items = pf._find_items(_NEWS_HTML)
    urls = [u for u, _ in items]
    # 同 hash 0002（协议相对 + 根相对各一）只留一条
    assert sum("aaaa0002" in u for u in urls) == 1
    # 协议相对锚补全为 https://
    assert all(u.startswith("https://english.www.gov.cn/") for u in urls)


def test_find_items_preserves_order_and_caps():
    many = "\n".join(
        _a(f"//english.www.gov.cn/news/202606/0{i % 9}/content_WSdead{i:04d}.html",
           f"CPC leadership meeting on economic work item {i}")
        for i in range(pf._MAX_ITEMS + 3))
    items = pf._find_items(many)
    assert len(items) == pf._MAX_ITEMS                      # 截断到上限
    assert items[0][1].endswith("item 0")                   # newest-first 保序


def test_policy_feed_filter():
    items = pf._find_items(_POLICY_HTML)
    titles = [t for _, t in items]
    assert any("work of the government" in t.lower() for t in titles)
    assert any("fiscal policy" in t.lower() for t in titles)
    assert not any("rural road" in t.lower() for t in titles)   # 细分政策噪声排除


def test_extract_body_artical_content_dateline_and_footer():
    body = pf._extract_body(_ARTICLE)
    assert body.startswith("BEIJING, Dec. 8")              # dateline 起点
    assert "moderately loose monetary policy" in body
    # 站点 chrome 去净
    assert "breadcrumb" not in body and "Editor:" not in body
    assert "Copyright" not in body and "Back to the top" not in body


def test_date_matches_updated_line():
    m = pf._DATE.search(_ARTICLE)
    assert m and m.group(1) == "December 8, 2025"


def test_hash_of_and_fingerprint_semantics():
    items = pf._find_items(_NEWS_HTML)
    hashes = sorted(pf._hash_of(u) for u, _ in items)
    fp = "polit:" + "|".join(hashes)
    # 同一组 hash → 指纹稳定（无新会议不误触发去重门）
    assert "polit:" + "|".join(sorted(pf._hash_of(u) for u, _ in items)) == fp
    # 新增一条 → hash 集变 → 指纹变
    bumped = hashes + ["aaaa9999"]
    assert "polit:" + "|".join(sorted(bumped)) != fp

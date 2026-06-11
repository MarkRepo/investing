"""中美地缘/关税 取文通道：纯解析层（project44 表格 + USTR 新闻稿）。

零网络、无登记表副作用——只测从 project44 静态表挑中国双向行、从 USTR 索引页挑中国关键词
新闻稿、从新闻稿纯文本截正文。覆盖实拉验证的结构要点：
  · project44 data-title 单元格、China 双向（USA→China 与 China→USA）、排非中国行、
    STATUS icon(Green_Yes)→active/inactive、_render 表头/行数、_p44_sig 指纹。
  · USTR 真新闻稿 href（年/月/slug）过滤掉年-only/分页链接、中国关键词命中、保序去重+_MAX_USTR 截断、
    WASHINGTON –(en-dash)→### 去站点 chrome、_DATE_BEFORE 匹配 June 02, 2026。
"""
from __future__ import annotations

from prism.scripts import china_us_fetch as cf


# ── project44 fixtures（实拉形态：data-title 单元格 + STATUS img icon） ──────────
def _td(title: str, inner: str) -> str:
    return f'<td class="x" data-align="center" data-title="{title}">{inner}</td>'


def _p44_row(imp, exp, date, ttype, amount, active=True, notes="note"):
    icon = "Green_Yes_Icon.svg" if active else "Grey_No_Icon.svg"
    status = f'<img alt="" nitro-lazy-src="https://cdn/.../{icon}" />'
    return ("<tr>"
            + _td("IMPORTING COUNTRY", imp) + _td("EXPORTING COUNTRY", exp)
            + _td("START DATE", date) + _td("TYPE OF TARIFF", ttype)
            + _td("AMOUNT", amount) + _td("STATUS", status)
            + _td("ADDITIONAL NOTES", notes) + "</tr>")


_P44_HTML = "<table><tbody>" + "".join([
    _p44_row("USA", "China", "4/9/2025", "All Chinese imports", "10%", active=True),
    _p44_row("China", "USA", "3/4/2025", "US agricultural goods", "15%", active=True),
    _p44_row("China", "USA", "2/1/2025", "Suspended measure", "25%", active=False),
    _p44_row("USA", "Canada", "3/4/2025", "Energy", "10%"),          # 非中国——须排除
    _p44_row("USA", "Mexico", "3/4/2025", "Autos", "25%"),           # 非中国——须排除
    _p44_row("USA", "Rest of World", "4/5/2025", "Reciprocal", "10%"),  # 非中国——须排除
]) + "</tbody></table>"


def test_p44_keeps_only_china_rows_bidirectional():
    rows = cf._parse_p44_rows(_P44_HTML)
    assert len(rows) == 3                                  # 3 条中国行（双向），3 条非中国被排除
    pairs = {(r["importing"], r["exporting"]) for r in rows}
    assert ("USA", "China") in pairs                       # 美征中
    assert ("China", "USA") in pairs                       # 中方反制（USTR 给不了）


def test_p44_excludes_non_china_rows():
    rows = cf._parse_p44_rows(_P44_HTML)
    countries = {c for r in rows for c in (r["importing"], r["exporting"])}
    assert "Canada" not in countries and "Mexico" not in countries
    assert "Rest of World" not in countries


def test_p44_fields_and_status_icon():
    rows = cf._parse_p44_rows(_P44_HTML)
    by = {(r["importing"], r["exporting"]): r for r in rows}
    usa_cn = by[("USA", "China")]
    assert usa_cn["start_date"] == "4/9/2025"
    assert usa_cn["amount"] == "10%"
    assert usa_cn["ttype"] == "All Chinese imports"
    assert usa_cn["status"] == "active"                    # Green_Yes icon → active
    suspended = next(r for r in rows if r["start_date"] == "2/1/2025")
    assert suspended["status"] == "inactive"              # 非 Green_Yes → inactive


def test_p44_render_md_header_and_rows():
    rows = cf._parse_p44_rows(_P44_HTML)
    md = cf._render_p44_md(rows)
    assert md.startswith("| 进口国 | 出口国 |")
    # 表头 2 行（标题+分隔）+ 每数据行 1 行
    assert len(md.splitlines()) == 2 + len(rows)
    assert "China" in md and "10%" in md


def test_p44_sig_changes_with_rate():
    rows = cf._parse_p44_rows(_P44_HTML)
    sig = cf._p44_sig(rows)
    assert "USA>China@4/9/2025=10%" in sig
    bumped = [dict(r) for r in rows]
    bumped[0]["amount"] = "30%"                            # 税率变 → 指纹变
    assert cf._p44_sig(bumped) != sig


# ── USTR fixtures（实拉形态：/年/月/slug 真稿 + 年-only 分页链接 + 非中国稿） ──────
_USTR_INDEX = """
<a href="/about/policy-offices/press-office/press-releases/2026">2026</a>
<a href="/about/policy-offices/press-office/press-releases/2025-0">2025</a>
<a href="/about/policy-offices/press-office/press-releases/2026/june/ustr-seeks-public-comment-mechanism-reciprocal-trade-china">USTR Seeks Public Comment on a Mechanism to Promote Reciprocal Trade with China</a>
<a href="/about/policy-offices/press-office/press-releases/2026/june/ustr-section-301-determination-brazils-acts">USTR Section 301 Determination on Brazil's Unreasonable Acts</a>
<a href="/about/policy-offices/press-office/press-releases/2026/may/ustr-announces-section-301-investigation-vietnams-acts">USTR Announces Section 301 Investigation of Vietnam's Acts</a>
<a href="/about/policy-offices/press-office/press-releases/2026/may/ambassador-greer-meets-chinese-vice-premier">Ambassador Greer Meets Chinese Vice Premier on Trade</a>
<a href="/about/policy-offices/press-office/press-releases/2026/may/ambassador-greer-meets-chinese-vice-premier">Ambassador Greer Meets Chinese Vice Premier on Trade</a>
<a href="/about/policy-offices/press-office/press-releases/2026/april/ambassador-greer-travel-oecd-ministerial">Ambassador Greer to Travel to OECD Ministerial Council Meeting</a>
"""

_USTR_ARTICLE = """<html><body>
<div>Skip to main content</div><nav>Breadcrumb Home Press Releases</nav>
<h1>USTR Seeks Public Comment on a Mechanism to Promote Reciprocal Trade with China</h1>
<p>June 02, 2026</p>
<p>WASHINGTON &ndash; Today, the Office of the United States Trade Representative announced
a public comment process regarding a U.S.-China Board of Trade to manage bilateral trade.</p>
<p>###</p>
<div>Stay in the Know Sign up for updates</div>
<footer>Latest News chrome chrome</footer>
</body></html>"""


def test_find_china_releases_filters_keyword_and_dedupes():
    rels = cf._find_china_releases(_USTR_INDEX)
    titles = [t for _, t in rels]
    # 命中 2 条中国稿（去重后），排除 Brazil/Vietnam 301、OECD travel
    assert len(rels) == 2
    assert any("China" in t for t in titles)
    assert any("Chinese" in t for t in titles)
    assert not any("Brazil" in t or "Vietnam" in t or "OECD" in t for t in titles)


def test_find_china_releases_excludes_year_only_links():
    rels = cf._find_china_releases(_USTR_INDEX)
    paths = [p for p, _ in rels]
    # 年-only / 分页链接（无 /月/slug 段）不得入选
    assert not any(p.rstrip("/").endswith(("/2026", "/2025-0")) for p in paths)
    assert all("/2026/" in p or "/2025/" in p for p in paths)


def test_find_china_releases_preserves_order_and_caps():
    # 单独构造 > _MAX_USTR 条中国稿，验证保序 + 截断
    many = "\n".join(
        f'<a href="/about/policy-offices/press-office/press-releases/2026/june/china-item-{i}">China item {i}</a>'
        for i in range(cf._MAX_USTR + 3))
    rels = cf._find_china_releases(many)
    assert len(rels) == cf._MAX_USTR
    assert rels[0][1] == "China item 0"                   # newest-first 保序


def test_extract_body_washington_endash_to_hashes():
    body = cf._extract_body(cf._strip_html(_USTR_ARTICLE))
    assert body.startswith("WASHINGTON")
    assert "Board of Trade" in body
    assert "###" not in body                               # ### 之后截断
    assert "Stay in the Know" not in body and "Latest News" not in body


def test_date_before_matches_article_date():
    plain = cf._strip_html(_USTR_ARTICLE)
    m = cf._DATE_BEFORE.search(plain)
    assert m and m.group(1) == "June 02, 2026"

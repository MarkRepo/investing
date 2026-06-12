"""fomc_sep 数值 fetcher 单测：纯函数解析（发现最新投影表 + 取中位联邦基金利率）。零网络。"""
from prism.scripts import fomc_sep_fetch as sep


# 日历页样本：多个 projtabl 日期、故意乱序，断言取最大日期
_CALENDAR = """
<a href="/monetarypolicy/fomcprojtabl20251210.htm">December 2025 Projections</a>
<a href="/monetarypolicy/fomcprojtabl20260318.htm">March 2026 Projections</a>
<a href="/monetarypolicy/fomcprojtabl20250618.htm">June 2025 Projections</a>
"""

# 投影表样本：Table 1「Federal funds rate」行（中位在前，后随中心趋势/区间），
# 另含一条以 Median 开头的备忘行（应被 startswith 过滤掉）。
_PROJTABL = """
<table>
<tr><th>Variable</th><th>2026</th><th>2027</th><th>2028</th><th>Longer run</th></tr>
<tr><td>Federal funds rate</td><td>3.4</td><td>3.1</td><td>3.1</td><td>3.1</td>
    <td>3.1&#8211;3.6</td></tr>
<tr><td>Median</td><td>-</td><td>-</td><td>3.4</td><td>3.1</td></tr>
</table>
"""


def test_find_latest_projtabl_picks_newest():
    url, as_of = sep.find_latest_projtabl(_CALENDAR)
    assert url == "https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260318.htm"
    assert as_of == "2026-03-18"


def test_find_latest_projtabl_no_match():
    assert sep.find_latest_projtabl("<a href='/foo.htm'>x</a>") == (None, None)


def test_parse_median_funds_rate_takes_first_number_of_ffr_row():
    assert sep.parse_median_funds_rate(_PROJTABL) == 3.4


def test_parse_median_funds_rate_none_when_no_ffr_row():
    assert sep.parse_median_funds_rate("<table><tr><td>GDP</td><td>2.0</td></tr></table>") is None

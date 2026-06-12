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


import pytest
from prism.scripts import macro_registry as reg


class _FakeResp:
    def __init__(self, text):
        self.text = text
    def raise_for_status(self):
        pass


class _FakeClient:
    """按 URL 返回日历页或投影表样本。"""
    def __init__(self, calendar, projtabl):
        self._cal, self._proj = calendar, projtabl
    def get(self, url, **kw):
        return _FakeResp(self._cal if "fomccalendars" in url else self._proj)
    def close(self):
        pass


@pytest.fixture
def sep_topic(tmp_path, monkeypatch):
    # 把 _PRISM_ROOT 指向临时目录，建一个登记表 + 一条 fomc_sep 输入
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(sep, "_PRISM_ROOT", tmp_path, raising=False)
    slug, variant = "t-macro", "opus4.8"
    reg.create_registry(slug, variant)
    reg.upsert_input(slug, variant, {
        "name": sep._INPUT_NAME, "tier": "A", "cadence_type": "event",
        "targets": ["rates"], "mechanism": "CD", "importance": "load_bearing",
        "causal_sentence": "x→y→z。", "availability": "scripted", "fetch_method": "fomc_sep",
    })
    return slug, variant


def test_fetch_fomc_sep_records_median(sep_topic):
    slug, variant = sep_topic
    client = _FakeClient(_CALENDAR, _PROJTABL)
    res = sep.fetch_fomc_sep(slug, variant, client=client)
    assert res["ok"] and res["value"] == 3.4 and res["as_of"] == "2026-03-18"
    obs = next(e for e in reg.read_registry(slug, variant)["inputs"]
               if e["name"] == sep._INPUT_NAME)["observed"]
    assert obs["value"] == 3.4 and obs["as_of"] == "2026-03-18"


def test_run_fomc_sep_fetch_counts(sep_topic):
    slug, variant = sep_topic
    summary = sep.run_fomc_sep_fetch(slug, variant, client=_FakeClient(_CALENDAR, _PROJTABL))
    assert summary["fetched"] == 1 and summary["failed"] == 0

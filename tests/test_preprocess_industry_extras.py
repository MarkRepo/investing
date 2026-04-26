from scripts import preprocess_report as pre


_SAMPLE_TEXT = """
中国 CMP 抛光材料行业深度
国金证券 2026-03-10

摘要：CMP 抛光材料是半导体制造环节不可或缺的消耗品。全球 2025 年市场规模
33.8 亿美元，CAGR 9%。国产替代是主线，安集(SSE 688019)、鼎龙(SZ 300054)
为代表性玩家。

...

安集科技 (SSE:688019) 专注 CMP 抛光液，当前市占 ... 鼎龙股份 (SZ:300054)
CMP pad 后起之秀 ... 上海新阳 603659 也有布局。

茅台 600519 作为对照（非 CMP）。
"""


def test_detect_tickers_a_share():
    tickers = pre.detect_tickers(_SAMPLE_TEXT)
    got = {(t["market"], t["ticker"]) for t in tickers}
    assert ("SSE", "688019") in got
    assert ("SZSE", "300054") in got  # 300XXX → SZSE
    assert ("SSE", "603659") in got
    # we don't require it to include 茅台 since it appears without explicit market prefix


def test_detect_tickers_us_pattern():
    text = "We like Apple (NASDAQ:AAPL) and Microsoft (NYSE: MSFT) in this cycle."
    tickers = pre.detect_tickers(text)
    got = {(t["market"], t["ticker"]) for t in tickers}
    assert ("US", "AAPL") in got
    assert ("US", "MSFT") in got


def test_detect_tickers_unique():
    text = "安集 688019 出现多次 ... 688019 又一次 ... 688019"
    tickers = pre.detect_tickers(text)
    ids = [t["ticker"] for t in tickers]
    assert ids.count("688019") == 1


def test_extract_report_abstract_takes_leading_paragraph():
    abstract = pre.extract_report_abstract(_SAMPLE_TEXT, max_chars=200)
    assert "摘要" in abstract or "CMP" in abstract
    assert len(abstract) <= 200

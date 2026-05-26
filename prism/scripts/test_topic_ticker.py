"""H1 + M1 回归测试 — create_topic ticker/extra_tickers schema 强约束。

H1: topic_type='company' 必须传 ticker（漏传 raise ValueError）
M1: extra_tickers list[str] 支持 AH / ADR / 多重上市

不测之前 test_topic_phase0.py 已经覆盖的 outputs_state/concepts/monitoring_tier 等。
"""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts.topic import (
    create_topic,
    read_topic,
    _infer_market,
)


@pytest.fixture
def tmp_topics(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    (tmpdir / "topics").mkdir()
    yield tmpdir
    shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# H1 — company 强制 ticker
# ---------------------------------------------------------------------------

def test_h1_company_without_ticker_raises(tmp_topics):
    with pytest.raises(ValueError, match="必须传 ticker"):
        create_topic(
            slug="h1-no-ticker", display_name="X", topic_type="company",
            question="Q?", geo="CN", depth="quick", variant="v",
        )


def test_h1_company_with_ticker_ok(tmp_topics):
    create_topic(
        slug="h1-with-ticker", display_name="X", topic_type="company",
        question="Q?", geo="CN", depth="quick", variant="v",
        short_name="X",
        ticker="SSE_688331",
    )
    data = read_topic("h1-with-ticker", "v")
    assert data["scope"]["ticker"] == "SSE_688331"
    assert data["scope"]["market"] == "SSE"


@pytest.mark.parametrize("topic_type", ["industry", "arena", "concept"])
def test_h1_non_company_without_ticker_ok(tmp_topics, topic_type):
    """industry/arena/concept 不必传 ticker。"""
    create_topic(
        slug=f"h1-{topic_type}", display_name="X", topic_type=topic_type,
        question="Q?", geo="CN", depth="quick", variant="v",
    )
    data = read_topic(f"h1-{topic_type}", "v")
    assert "ticker" not in data["scope"]


@pytest.mark.parametrize("bad_ticker", [
    "SSE688331",       # 缺下划线
    "sse_688331",      # 小写前缀
    "_688331",         # 空前缀
    "SSE_",            # 空 code
    "SSE_688-331",     # 含连字符
    123,               # 非 str
])
def test_h1_invalid_ticker_format_raises(tmp_topics, bad_ticker):
    with pytest.raises(ValueError, match="格式必须是"):
        create_topic(
            slug="h1-bad", display_name="X", topic_type="company",
            question="Q?", geo="CN", depth="quick", variant="v",
            short_name="X",
            ticker=bad_ticker,
        )


# ---------------------------------------------------------------------------
# M1 — extra_tickers list[str]
# ---------------------------------------------------------------------------

def test_m1_extra_tickers_ah_dual_listing(tmp_topics):
    """荣昌生物 A+H 双重上市真实场景。"""
    create_topic(
        slug="m1-rongchang", display_name="荣昌", topic_type="company",
        question="Q?", geo="CN", depth="deep", variant="v",
        short_name="荣昌生物",
        ticker="SSE_688331",
        extra_tickers=["HKEX_09995"],
    )
    data = read_topic("m1-rongchang", "v")
    assert data["scope"]["ticker"] == "SSE_688331"
    assert data["scope"]["market"] == "SSE"
    assert data["scope"]["extra_tickers"] == ["HKEX_09995"]
    assert data["scope"]["extra_markets"] == ["HKEX"]


def test_m1_extra_tickers_three_market_listing(tmp_topics):
    """阿里巴巴 H+ADR 或 百济神州 A+H+US 三重上市。"""
    create_topic(
        slug="m1-beigene", display_name="百济神州", topic_type="company",
        question="Q?", geo="CN", depth="deep", variant="v",
        short_name="百济神州",
        ticker="SSE_688235",
        extra_tickers=["HKEX_06160", "NASDAQ_BGNE"],
    )
    data = read_topic("m1-beigene", "v")
    assert data["scope"]["extra_tickers"] == ["HKEX_06160", "NASDAQ_BGNE"]
    assert data["scope"]["extra_markets"] == ["HKEX", "NASDAQ"]


def test_m1_extra_tickers_omitted_ok(tmp_topics):
    """未传 extra_tickers 时 scope 不应包含该字段（单市场标的）。"""
    create_topic(
        slug="m1-single", display_name="X", topic_type="company",
        question="Q?", geo="CN", depth="quick", variant="v",
        short_name="X",
        ticker="SSE_600519",
    )
    data = read_topic("m1-single", "v")
    assert "extra_tickers" not in data["scope"]
    assert "extra_markets" not in data["scope"]


def test_m1_extra_tickers_empty_list_ok(tmp_topics):
    """显式传 [] 视同未传，不写入 scope。"""
    create_topic(
        slug="m1-empty", display_name="X", topic_type="company",
        question="Q?", geo="CN", depth="quick", variant="v",
        short_name="X",
        ticker="SSE_600519",
        extra_tickers=[],
    )
    data = read_topic("m1-empty", "v")
    assert "extra_tickers" not in data["scope"]


def test_m1_extra_tickers_not_list_raises(tmp_topics):
    with pytest.raises(ValueError, match="必须是 list"):
        create_topic(
            slug="m1-not-list", display_name="X", topic_type="company",
            question="Q?", geo="CN", depth="quick", variant="v",
            short_name="X",
            ticker="SSE_688331",
            extra_tickers="HKEX_09995",  # str 不是 list
        )


def test_m1_extra_tickers_invalid_format_raises(tmp_topics):
    with pytest.raises(ValueError, match="格式必须是"):
        create_topic(
            slug="m1-bad-item", display_name="X", topic_type="company",
            question="Q?", geo="CN", depth="quick", variant="v",
            short_name="X",
            ticker="SSE_688331",
            extra_tickers=["HKEX_09995", "bad-format"],
        )


def test_m1_extra_tickers_duplicate_raises(tmp_topics):
    with pytest.raises(ValueError, match="内部不能重复"):
        create_topic(
            slug="m1-dup", display_name="X", topic_type="company",
            question="Q?", geo="CN", depth="quick", variant="v",
            short_name="X",
            ticker="SSE_688331",
            extra_tickers=["HKEX_09995", "HKEX_09995"],
        )


def test_m1_extra_tickers_overlap_with_primary_raises(tmp_topics):
    with pytest.raises(ValueError, match="不能包含主 ticker"):
        create_topic(
            slug="m1-overlap", display_name="X", topic_type="company",
            question="Q?", geo="CN", depth="quick", variant="v",
            short_name="X",
            ticker="SSE_688331",
            extra_tickers=["SSE_688331", "HKEX_09995"],
        )


# ---------------------------------------------------------------------------
# _infer_market HKEX 回归（顺手修的 bug）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ticker,geo,expected", [
    ("SSE_688331", "CN", "SSE"),
    ("SZSE_300073", "CN", "SZSE"),
    ("HKEX_09995", "CN", "HKEX"),       # 修：原版会落 SZSE
    ("HKEX_00700", "CN", "HKEX"),       # 港股 0 开头不能误判成深圳
    ("US_AAPL", "US", "US"),
    ("NASDAQ_GOOGL", "US", "NASDAQ"),
    ("NYSE_BABA", "US", "NYSE"),
    ("688331", "CN", "SSE"),            # 裸数字向后兼容
    ("300073", "CN", "SZSE"),
    ("", "CN", ""),                     # 空 ticker
])
def test_infer_market(ticker, geo, expected):
    assert _infer_market(ticker, geo) == expected

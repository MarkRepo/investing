"""F13: peer 级 ticker 倍数入口 get_quote_by_ticker / get_valuation_context_by_tickers。"""
from prism.scripts import market_data as md


def _fake_row(**kw):
    base = {"date": "2026-05-29", "close": 50.19, "pe_ttm": 41.0, "pe_static": 43.2,
            "pb": 5.2, "ps": 10.2, "market_cap": 3.331e11, "high_52w": 60, "low_52w": 40,
            "source": "akshare"}
    base.update(kw)
    return base


def test_get_quote_by_ticker_currency_cn(monkeypatch):
    monkeypatch.setattr(md, "_refresh", lambda t, m: True)
    monkeypatch.setattr(md.quotes_io, "latest_for", lambda t: _fake_row())
    q = md.get_quote_by_ticker("600276", "SSE")
    assert q["currency"] == "元"
    assert q["pe_ttm"] == 41.0
    assert q["market"] == "SSE"


def test_get_quote_by_ticker_currency_hkex(monkeypatch):
    """港股标 HKD（F13：HKEX 经 yfinance 路由可取，HKD 计价）。"""
    monkeypatch.setattr(md, "_refresh", lambda t, m: True)
    monkeypatch.setattr(md.quotes_io, "latest_for",
                        lambda t: _fake_row(source="yfinance", pe_ttm=None))
    q = md.get_quote_by_ticker("01801", "HKEX")
    assert q["currency"] == "HKD"
    assert q["source"] == "yfinance"


def test_get_quote_by_ticker_no_data(monkeypatch):
    monkeypatch.setattr(md, "_refresh", lambda t, m: False)
    monkeypatch.setattr(md.quotes_io, "latest_for", lambda t: None)
    q = md.get_quote_by_ticker("XXXX", "SSE")
    assert "error" in q
    assert q["ticker"] == "XXXX"


def test_valuation_context_by_tickers_mixed(monkeypatch):
    """多龙头块：有数据的出倍数，取不到的标 *(取不到)* 不静默漏。"""
    monkeypatch.setattr(md, "_refresh", lambda t, m: True)

    def fake_latest(t):
        return None if t == "01801" else _fake_row()
    monkeypatch.setattr(md.quotes_io, "latest_for", fake_latest)

    out = md.get_valuation_context_by_tickers([
        {"ticker": "600276", "market": "SSE", "name": "恒瑞"},
        {"ticker": "01801", "market": "HKEX", "name": "信达"},
    ])
    assert "恒瑞" in out and "PE(TTM) 41.0" in out
    assert "信达" in out and "取不到" in out  # 不静默漏


def test_valuation_context_by_tickers_empty():
    assert "未提供" in md.get_valuation_context_by_tickers([])

"""Unit tests for prices + triggers modules."""
from datetime import date
from pathlib import Path

import pytest

from app.io import prices, triggers


@pytest.fixture
def env(tmp_path: Path, monkeypatch):
    from app import config as cfg
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cfg, "FINANCIALS_DB", tmp_path / "data" / "financials.db")
    (tmp_path / "data").mkdir()
    return tmp_path


# --- prices -----------------------------------------------------------------


def test_parse_freeform_happy(env):
    text = """
    HIMS 18.50
    NVDA  450.20
    # a comment
    AAPL, 189

    """
    rows, errors = prices.parse_freeform(text)
    assert rows == [("HIMS", 18.5), ("NVDA", 450.2), ("AAPL", 189.0)]
    assert errors == []


def test_parse_freeform_accepts_currency_prefix(env):
    rows, _ = prices.parse_freeform("HIMS $18.50\nBABA ¥98")
    assert rows == [("HIMS", 18.5), ("BABA", 98.0)]


def test_parse_freeform_flags_bad_lines(env):
    rows, errs = prices.parse_freeform("HIMS\nNVDA 450.20\nHIMS -3\n")
    assert rows == [("NVDA", 450.2)]
    assert len(errs) == 2
    assert errs[0]["line"] == 1
    assert errs[1]["line"] == 3
    assert "must be > 0" in errs[1]["error"]


def test_upsert_and_latest(env):
    prices.upsert_close("HIMS", 18.5, date(2026, 4, 20), base=env)
    prices.upsert_close("HIMS", 19.1, date(2026, 4, 21), base=env)
    prices.upsert_close("NVDA", 450.0, date(2026, 4, 21), base=env)

    d, c = prices.latest_price_for("HIMS", base=env)
    assert d == "2026-04-21"
    assert c == 19.1

    m = prices.latest_prices_map(base=env)
    assert m["HIMS"] == ("2026-04-21", 19.1)
    assert m["NVDA"] == ("2026-04-21", 450.0)


def test_upsert_same_day_overwrites(env):
    prices.upsert_close("HIMS", 18.5, date(2026, 4, 21), base=env)
    prices.upsert_close("HIMS", 18.9, date(2026, 4, 21), base=env)
    _, c = prices.latest_price_for("HIMS", base=env)
    assert c == 18.9


def test_history_for(env):
    for i, c in enumerate([18.0, 18.3, 18.7]):
        prices.upsert_close("HIMS", c, date(2026, 4, 20 + i), base=env)
    h = prices.history_for("HIMS", base=env, limit=2)
    assert [r["close"] for r in h] == [18.7, 18.3]


# --- triggers ---------------------------------------------------------------


def test_direction_mapping(env):
    assert triggers.direction("first_entry") == "below"
    assert triggers.direction("add_1") == "below"
    assert triggers.direction("stop_loss") == "below"
    assert triggers.direction("trim") == "above"
    assert triggers.direction("exit") == "above"
    with pytest.raises(ValueError):
        triggers.direction("unknown")


def test_create_and_list(env):
    triggers.create("HIMS", 15.0, "first_entry", base=env)
    triggers.create("HIMS", 12.0, "add_1", base=env)
    triggers.create("HIMS", 30.0, "trim", base=env)
    rows = triggers.list_for_ticker("HIMS", base=env)
    # All untriggered → sorted by price ascending
    assert [r["trigger_price"] for r in rows] == [12.0, 15.0, 30.0]
    assert all(r["triggered_at"] is None for r in rows)


def test_create_rejects_bad_action(env):
    with pytest.raises(ValueError):
        triggers.create("HIMS", 15.0, "buy_lots", base=env)
    with pytest.raises(ValueError):
        triggers.create("HIMS", -1, "first_entry", base=env)


def test_evaluate_buy_side(env):
    triggers.create("HIMS", 15.0, "first_entry", base=env)
    triggers.create("HIMS", 12.0, "add_1", base=env)  # deeper
    prices.upsert_close("HIMS", 14.0, date(2026, 4, 22), base=env)

    result = triggers.evaluate(
        prices.latest_prices_map(base=env),
        today=date(2026, 4, 22),
        base=env,
    )
    new_prices = sorted(r["trigger_price"] for r in result["new"])
    armed_prices = sorted(r["trigger_price"] for r in result["armed"])
    assert new_prices == [15.0]     # 14 ≤ 15 → fires
    assert armed_prices == [12.0]    # 14 > 12 → still armed


def test_evaluate_sell_side(env):
    triggers.create("HIMS", 30.0, "trim", base=env)
    triggers.create("HIMS", 50.0, "exit", base=env)
    prices.upsert_close("HIMS", 32.0, date(2026, 4, 22), base=env)
    result = triggers.evaluate(prices.latest_prices_map(base=env), base=env)
    assert len(result["new"]) == 1
    assert result["new"][0]["action"] == "trim"
    assert len(result["armed"]) == 1


def test_evaluate_no_repeat_fire(env):
    triggers.create("HIMS", 15.0, "first_entry", base=env)
    prices.upsert_close("HIMS", 14.0, date(2026, 4, 22), base=env)
    r1 = triggers.evaluate(prices.latest_prices_map(base=env), base=env)
    assert len(r1["new"]) == 1
    # Evaluate again → nothing new, shows in "already"
    prices.upsert_close("HIMS", 13.0, date(2026, 4, 23), base=env)
    r2 = triggers.evaluate(prices.latest_prices_map(base=env), base=env)
    assert len(r2["new"]) == 0
    assert len(r2["already"]) == 1


def test_evaluate_ticker_without_price_is_armed(env):
    triggers.create("HIMS", 15.0, "first_entry", base=env)
    # No price for HIMS
    r = triggers.evaluate({}, base=env)
    assert len(r["new"]) == 0
    assert len(r["armed"]) == 1


def test_reset_clears_triggered(env):
    rowid = triggers.create("HIMS", 15.0, "first_entry", base=env)
    prices.upsert_close("HIMS", 14.0, date(2026, 4, 22), base=env)
    triggers.evaluate(prices.latest_prices_map(base=env), base=env)
    assert triggers.list_for_ticker("HIMS", base=env)[0]["triggered_at"] is not None

    triggers.reset(rowid, base=env)
    assert triggers.list_for_ticker("HIMS", base=env)[0]["triggered_at"] is None


def test_delete_removes_row(env):
    rowid = triggers.create("HIMS", 15.0, "first_entry", base=env)
    triggers.delete(rowid, base=env)
    assert triggers.list_for_ticker("HIMS", base=env) == []

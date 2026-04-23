from pathlib import Path

import pytest

from app.io import valuation as val


def test_compute_weighted_matches_design_example():
    # DESIGN §3.4 HIMS example: bull 40 @25%, base 25 @50%, bear 12 @25%
    w = val.compute_weighted(40, 25, 12, 0.25, 0.50, 0.25)
    assert w == pytest.approx(25.5)


def test_compute_weighted_rejects_bad_probabilities():
    with pytest.raises(ValueError):
        val.compute_weighted(40, 25, 12, 0.3, 0.5, 0.25)


def test_discount_rate_default():
    assert val.discount_rate_default(0.042) == pytest.approx(0.097)
    assert val.discount_rate_default(0.035, premium=0.05) == pytest.approx(0.085)


def test_discount_rate_suggest_hot_adds_premium():
    s = val.discount_rate_suggest(0.042, "hot")
    assert s["baseline"] == pytest.approx(0.097)
    assert s["addon"] == pytest.approx(0.01)
    assert s["suggested"] == pytest.approx(0.107)
    assert "hot" in s["rationale"]


def test_discount_rate_suggest_panic_adds_more():
    s = val.discount_rate_suggest(0.042, "panic")
    assert s["suggested"] == pytest.approx(0.117)


def test_discount_rate_suggest_neutral_is_baseline():
    s = val.discount_rate_suggest(0.042, "neutral")
    assert s["addon"] == 0.0
    assert s["suggested"] == s["baseline"]


def test_discount_rate_suggest_missing_yield():
    assert val.discount_rate_suggest(None, "hot") is None
    assert val.discount_rate_suggest("not a number", "hot") is None


@pytest.mark.parametrize(
    "current, expected_tier",
    [
        (10, "HEAVY_BUY"),   # ≤ 12 * 1.2 = 14.4
        (14, "HEAVY_BUY"),
        (17, "BUY"),         # ≤ 25 * 0.7 = 17.5
        (22, "FAIR"),        # between base*0.7 and base*1.3
        (25, "FAIR"),
        (33, "TRIM"),        # ≥ 25 * 1.3 = 32.5
        (42, "EXIT"),        # ≥ bull 40
    ],
)
def test_five_tier_signal(current, expected_tier):
    sig = val.five_tier_signal(current=current, bull=40, base=25, bear=12)
    assert sig["tier"] == expected_tier


def test_roundtrip(tmp_path):
    (tmp_path / "companies" / "US_HIMS").mkdir(parents=True)
    fm = {
        "ticker": "HIMS", "market": "US", "valuation_date": "2026-04-23",
        "bull_price": 40, "base_price": 25, "bear_price": 12,
        "prob_bull": 0.25, "prob_base": 0.5, "prob_bear": 0.25,
        "weighted_expected": 25.5, "current_price": 19,
        "implied_return_to_base": 0.32, "discount_rate": 0.09,
    }
    val.write_valuation("HIMS", "US", fm, "## 估值方法\n\n内容\n", base=tmp_path)
    doc = val.read_valuation("HIMS", "US", base=tmp_path)
    assert doc["frontmatter"]["weighted_expected"] == 25.5
    assert "内容" in doc["body"]

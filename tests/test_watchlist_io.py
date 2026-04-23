from datetime import date, timedelta
from pathlib import Path

import pytest

from app.io import watchlist as wl


def _setup(tmp_path: Path) -> None:
    (tmp_path / "watchlist").mkdir()


VALID_GATE = {
    "gate_answers": {
        "gate_competence": "yes",
        "gate_mispricing": "yes",
        "gate_genuine_interest": "yes",
    },
    "gate_reasons": {
        "gate_competence": "消费品远程医疗组合我跟踪 3 年，单位经济懂；telehealth 订阅+GLP-1 组合也熟悉。",
        "gate_mispricing": "EV/Sales 在近 3 年 25% 分位，远低于同业 TDOC、DOCS；倒推法隐含悲观。",
        "gate_genuine_interest": "自己用过 telehealth 服务，想弄清 GLP-1 扩张到男性健康之外的可行性。",
    },
}


def test_append_and_read_prefilter(tmp_path):
    _setup(tmp_path)
    wl.append_watchlist(
        "prefilter",
        {
            "date_added": "2026-04-23", "ticker": "HIMS",
            "source_type": "product_experience", "source": "daily use", "notes": "first look",
        },
        base=tmp_path,
    )
    wl.append_watchlist(
        "prefilter",
        {
            "date_added": "2026-04-23", "ticker": "NVDA",
            "source_type": "quant_screen", "source": "PE<25 screen", "notes": "",
        },
        base=tmp_path,
    )
    rows = wl.read_watchlist("prefilter", base=tmp_path)
    assert [r["ticker"] for r in rows] == ["HIMS", "NVDA"]
    assert rows[0]["source_type"] == "product_experience"


def test_append_rejects_bad_source_type(tmp_path):
    _setup(tmp_path)
    with pytest.raises(ValueError, match="source_type"):
        wl.append_watchlist(
            "prefilter",
            {
                "date_added": "2026-04-23", "ticker": "X",
                "source_type": "news", "source": "bloomberg", "notes": "",
            },
            base=tmp_path,
        )


def test_move_to_researching_happy_path(tmp_path):
    _setup(tmp_path)
    today = date(2026, 5, 1)
    date_added = today - timedelta(days=10)
    wl.append_watchlist(
        "prefilter",
        {
            "date_added": date_added.isoformat(), "ticker": "HIMS",
            "source_type": "product_experience", "source": "daily use", "notes": "",
        },
        base=tmp_path,
    )
    wl.move_watchlist(
        "HIMS",
        from_stage="prefilter", to_stage="researching",
        extra={"started": today.isoformat(), "gap_focus": "unit economics", "target_finish": "2026-05-15"},
        base=tmp_path,
        today=today,
        **VALID_GATE,
    )
    pre = wl.read_watchlist("prefilter", base=tmp_path)
    assert pre == []
    res = wl.read_watchlist("researching", base=tmp_path)
    assert [r["ticker"] for r in res] == ["HIMS"]
    assert res[0]["gap_focus"] == "unit economics"
    assert "消费品" in res[0]["gate_notes"]


def test_move_to_researching_rejects_before_7_days(tmp_path):
    _setup(tmp_path)
    today = date(2026, 5, 1)
    date_added = today - timedelta(days=3)
    wl.append_watchlist(
        "prefilter",
        {
            "date_added": date_added.isoformat(), "ticker": "HIMS",
            "source_type": "product_experience", "source": "", "notes": "",
        },
        base=tmp_path,
    )
    with pytest.raises(ValueError, match="7 days"):
        wl.move_watchlist(
            "HIMS",
            from_stage="prefilter", to_stage="researching",
            base=tmp_path, today=today,
            **VALID_GATE,
        )


def test_move_to_researching_rejects_missing_gate(tmp_path):
    _setup(tmp_path)
    today = date(2026, 5, 1)
    date_added = today - timedelta(days=10)
    wl.append_watchlist(
        "prefilter",
        {
            "date_added": date_added.isoformat(), "ticker": "HIMS",
            "source_type": "product_experience", "source": "", "notes": "",
        },
        base=tmp_path,
    )
    bad = dict(VALID_GATE)
    bad["gate_answers"] = {**bad["gate_answers"], "gate_competence": "no"}
    with pytest.raises(ValueError, match="three-question gate"):
        wl.move_watchlist(
            "HIMS", from_stage="prefilter", to_stage="researching",
            base=tmp_path, today=today, **bad,
        )


def test_move_to_researching_rejects_short_reason(tmp_path):
    _setup(tmp_path)
    today = date(2026, 5, 1)
    date_added = today - timedelta(days=10)
    wl.append_watchlist(
        "prefilter",
        {
            "date_added": date_added.isoformat(), "ticker": "HIMS",
            "source_type": "product_experience", "source": "", "notes": "",
        },
        base=tmp_path,
    )
    bad = {
        "gate_answers": VALID_GATE["gate_answers"],
        "gate_reasons": {**VALID_GATE["gate_reasons"], "gate_mispricing": "too short"},
    }
    with pytest.raises(ValueError, match="reason<30"):
        wl.move_watchlist(
            "HIMS", from_stage="prefilter", to_stage="researching",
            base=tmp_path, today=today, **bad,
        )


def test_move_missing_raises(tmp_path):
    _setup(tmp_path)
    with pytest.raises(LookupError):
        wl.move_watchlist(
            "GONE", from_stage="prefilter", to_stage="researching", base=tmp_path
        )


def test_unknown_stage(tmp_path):
    _setup(tmp_path)
    with pytest.raises(ValueError):
        wl.read_watchlist("nope", base=tmp_path)


def test_preamble_preserved_on_rewrite(tmp_path):
    _setup(tmp_path)
    wl.append_watchlist(
        "prefilter",
        {
            "date_added": "2026-04-23", "ticker": "X",
            "source_type": "qual_radar", "source": "s", "notes": "",
        },
        base=tmp_path,
    )
    text = (tmp_path / "watchlist" / "prefilter.md").read_text()
    assert "观察池 · 预筛段" in text
    assert "禁止快速路径" in text


def test_researching_status(tmp_path):
    today = date(2026, 5, 1)
    assert wl.researching_status({"target_finish": "2026-05-10"}, today=today) == "on_track"
    assert wl.researching_status({"target_finish": "2026-04-28"}, today=today) == "due"
    assert wl.researching_status({"target_finish": "2026-04-10"}, today=today) == "overdue"
    assert wl.researching_status({"target_finish": ""}, today=today) == "unset"
    assert wl.researching_status({"target_finish": "bogus"}, today=today) == "unset"


def test_move_respects_researching_cap(tmp_path):
    """Cannot move a 3rd ticker into researching when 2 are already there."""
    _setup(tmp_path)
    today = date(2026, 5, 1)
    date_added = today - timedelta(days=10)
    # seed two already in researching
    wl.append_watchlist(
        "researching",
        {"started": "2026-04-01", "ticker": "A", "gap_focus": "x", "target_finish": "2026-05-15", "gate_notes": "(seeded)"},
        base=tmp_path,
    )
    wl.append_watchlist(
        "researching",
        {"started": "2026-04-10", "ticker": "B", "gap_focus": "y", "target_finish": "2026-05-20", "gate_notes": "(seeded)"},
        base=tmp_path,
    )
    # add a prefilter candidate
    wl.append_watchlist(
        "prefilter",
        {
            "date_added": date_added.isoformat(), "ticker": "C",
            "source_type": "product_experience", "source": "", "notes": "",
        },
        base=tmp_path,
    )
    with pytest.raises(ValueError, match="cap is 2"):
        wl.move_watchlist(
            "C",
            from_stage="prefilter", to_stage="researching",
            base=tmp_path, today=today,
            **VALID_GATE,
        )


def test_price_triggers_move_unaffected_by_gate(tmp_path):
    """Non-prefilter moves don't enforce gate (that's only for entering researching)."""
    _setup(tmp_path)
    # manually seed a researching row
    wl.append_watchlist(
        "researching",
        {
            "started": "2026-04-10", "ticker": "HIMS", "gap_focus": "x",
            "target_finish": "2026-04-25", "gate_notes": "(seeded)",
        },
        base=tmp_path,
    )
    wl.move_watchlist(
        "HIMS", from_stage="researching", to_stage="price-triggers",
        extra={"set_on": "2026-05-01", "first_entry_price": "19"},
        base=tmp_path,
    )
    assert wl.read_watchlist("researching", base=tmp_path) == []
    pt = wl.read_watchlist("price-triggers", base=tmp_path)
    assert pt[0]["first_entry_price"] == "19"

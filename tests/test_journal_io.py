from datetime import date
from pathlib import Path

import pytest

from app.io import journal


def _setup(tmp_path: Path) -> None:
    (tmp_path / "journal" / "decisions").mkdir(parents=True)
    (tmp_path / "companies" / "US_HIMS").mkdir(parents=True)


def test_quarter_mapping(tmp_path):
    assert journal._quarter(date(2026, 1, 1)) == 1
    assert journal._quarter(date(2026, 3, 31)) == 1
    assert journal._quarter(date(2026, 4, 1)) == 2
    assert journal._quarter(date(2026, 12, 31)) == 4


def test_build_paths_shape(tmp_path):
    _setup(tmp_path)
    paths = journal.build_paths(date(2026, 4, 23), "HIMS", "buy", base=tmp_path)
    assert paths.entry_id == "2026-04-23-HIMS-buy"
    assert paths.quarter_dir.name == "2026-Q2"
    assert paths.file_path.name == "2026-04-23-HIMS-buy.md"


def test_parse_entry_id_roundtrip():
    d, t, a = journal.parse_entry_id("2026-04-23-HIMS-buy")
    assert d == date(2026, 4, 23)
    assert t == "HIMS"
    assert a == "buy"
    with pytest.raises(ValueError):
        journal.parse_entry_id("not-valid")


def test_create_entry_with_v0_snapshot(tmp_path):
    _setup(tmp_path)
    # Write a V0 file to snapshot
    v0 = tmp_path / "companies" / "US_HIMS" / "v0.md"
    v0.write_text(
        "---\nticker: HIMS\nmarket: US\nstatus: draft\n---\n\n# V0: HIMS\n\n## 1. 买入逻辑\n\nA\n"
    )
    rel, h, text = journal.read_v0_snapshot("HIMS", "US", base=tmp_path)
    assert rel.endswith("companies/US_HIMS/v0.md")
    assert len(h) == 12
    assert "HIMS" in text

    paths = journal.create_entry(
        date(2026, 4, 23),
        "HIMS",
        "US",
        "buy",
        price=19.0,
        position_change=5,
        v0_snapshot_path=rel,
        v0_snapshot_hash_=h,
        v0_body_preview=text,
        base=tmp_path,
    )
    assert paths.file_path.exists()
    doc = journal.read_entry("2026-04-23-HIMS-buy", base=tmp_path)
    fm = doc["frontmatter"]
    assert fm["ticker"] == "HIMS"
    assert fm["action"] == "buy"
    assert fm["price"] == 19.0
    assert fm["v0_snapshot_hash"] == h
    assert fm["process_quality"] is None
    assert "HIMS" in doc["sections"][2]  # snapshot pre-filled
    assert "快照哈希" in doc["sections"][2]


def test_create_entry_refuses_overwrite(tmp_path):
    _setup(tmp_path)
    journal.create_entry(date(2026, 4, 23), "X", "US", "buy", base=tmp_path)
    with pytest.raises(FileExistsError):
        journal.create_entry(date(2026, 4, 23), "X", "US", "buy", base=tmp_path)


def test_invalid_action_rejected(tmp_path):
    with pytest.raises(ValueError):
        journal.create_entry(date(2026, 4, 23), "X", "US", "yolo", base=tmp_path)


def test_write_then_read_scores(tmp_path):
    _setup(tmp_path)
    journal.create_entry(date(2026, 4, 23), "HIMS", "US", "buy", base=tmp_path)
    doc = journal.read_entry("2026-04-23-HIMS-buy", base=tmp_path)
    fm = dict(doc["frontmatter"])
    fm["process_quality"] = 4
    fm["process_rigor"] = 3
    fm["process_rule_adherence"] = 5
    fm["process_emotional_control"] = 4
    body = journal.join_sections(
        {1: "买 5%", 2: doc["sections"][2], 3: "平静", 4: "", 5: "a\nb\nc\nd\ne",
         6: "战争升级导致持续下跌", 7: "纪律执行到位但分析还可深入", 8: ""},
        "HIMS", "buy", "2026-04-23",
    )
    journal.write_entry("2026-04-23-HIMS-buy", fm, body, base=tmp_path)

    doc2 = journal.read_entry("2026-04-23-HIMS-buy", base=tmp_path)
    assert doc2["frontmatter"]["process_quality"] == 4
    assert "平静" in doc2["sections"][3]
    assert "战争升级" in doc2["sections"][6]


def test_list_entries_sorted(tmp_path):
    _setup(tmp_path)
    journal.create_entry(date(2026, 4, 23), "A", "US", "buy", base=tmp_path)
    journal.create_entry(date(2026, 5, 1), "B", "US", "buy", base=tmp_path)
    journal.create_entry(date(2026, 1, 15), "C", "US", "pass", base=tmp_path)
    rows = journal.list_entries(base=tmp_path)
    assert [r["ticker"] for r in rows] == ["B", "A", "C"]


def test_bias_warnings_flag_unexplained_yes():
    ans = {
        "emotional_tie": "yes",
        "source_balance": "balanced",
        "proving_thesis": "yes",
        "swap_test": "no",
    }
    reasons = {
        "emotional_tie": "用了 3 年，但已独立在 V0 里冷静评估估值，朋友视角也得到同样结论",
        "proving_thesis": "是",  # too short
    }
    flagged = journal.bias_warnings(ans, reasons)
    assert flagged == ["proving_thesis"]


def test_bias_warnings_empty_when_all_no():
    ans = {q[0]: "no" for q in journal.BIAS_QUESTIONS}
    assert journal.bias_warnings(ans, {}) == []

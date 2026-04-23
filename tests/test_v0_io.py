from pathlib import Path

import pytest

from app.io import v0 as v0io

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_read_v0_returns_frontmatter_and_body():
    doc = v0io.read_v0("TEST", "US", base=FIXTURES)
    assert doc["frontmatter"]["ticker"] == "TEST"
    assert doc["frontmatter"]["status"] == "active"
    assert doc["frontmatter"]["position_size_pct"] == 5
    assert "买入逻辑" in doc["body"]


def test_read_v0_missing_raises():
    with pytest.raises(FileNotFoundError):
        v0io.read_v0("NOPE", "US", base=FIXTURES)


def test_list_all_v0s_scans_fixtures():
    entries = v0io.list_all_v0s(base=FIXTURES)
    tickers = sorted(e["ticker"] for e in entries)
    assert tickers == ["DRAFT", "TEST"]


def test_list_all_v0s_status_filter():
    entries = v0io.list_all_v0s(base=FIXTURES, status_filter="active")
    assert [e["ticker"] for e in entries] == ["TEST"]
    entries = v0io.list_all_v0s(base=FIXTURES, status_filter="draft")
    assert [e["ticker"] for e in entries] == ["DRAFT"]


def test_write_v0_roundtrip(tmp_path):
    fm = {
        "ticker": "RT",
        "market": "US",
        "entry_date": "2026-04-23",
        "position_size_pct": 7,
        "status": "active",
        "last_reviewed": "2026-04-23",
    }
    body = "# V0: RT\n\n## 1. 买入逻辑\n\nTest round-trip.\n"
    v0io.write_v0("RT", "US", fm, body, base=tmp_path)

    doc = v0io.read_v0("RT", "US", base=tmp_path)
    assert doc["frontmatter"] == fm
    assert doc["body"].rstrip() == body.rstrip()


def test_split_sections_extracts_7():
    body = """# V0: HIMS

## 1. 买入逻辑
AA

## 2. 差异化观点（二阶思维）
BB

## 3. 估值锚
CC

## 4. 买入区间
DD

## 5. 卖出触发
EE

## 6. 什么不算推翻（噪音清单）
FF

## 7. 当前状态
GG
"""
    secs = v0io.split_sections(body)
    assert set(secs.keys()) == {1, 2, 3, 4, 5, 6, 7}
    assert "AA" in secs[1]
    assert "BB" in secs[2]
    assert "GG" in secs[7]


def test_join_sections_round_trip():
    body_in = "\n".join(
        [
            "# V0: RT",
            "",
            "## 1. 买入逻辑",
            "A",
            "",
            "## 2. 差异化观点（二阶思维）",
            "B",
            "",
            "## 3. 估值锚",
            "C",
            "",
            "## 4. 买入区间",
            "D",
            "",
            "## 5. 卖出触发",
            "E",
            "",
            "## 6. 什么不算推翻（噪音清单）",
            "F",
            "",
            "## 7. 当前状态",
            "G",
            "",
        ]
    )
    secs = v0io.split_sections(body_in)
    rebuilt = v0io.join_sections(secs, "RT")
    secs2 = v0io.split_sections(rebuilt)
    for i in range(1, 8):
        assert secs2[i].strip() == secs[i].strip()


def test_write_v0_frontmatter_key_order(tmp_path):
    fm = {
        "last_reviewed": "2026-04-23",
        "ticker": "ORD",
        "status": "draft",
        "market": "US",
        "position_size_pct": 0,
        "entry_date": None,
    }
    v0io.write_v0("ORD", "US", fm, "# V0\n", base=tmp_path)
    raw = (tmp_path / "companies" / "US_ORD" / "v0.md").read_text()

    order_keys = [
        line.split(":", 1)[0]
        for line in raw.splitlines()
        if line and not line.startswith("---") and not line.startswith("#") and ":" in line
    ]
    expected = ["ticker", "market", "entry_date", "position_size_pct", "status", "last_reviewed"]
    assert order_keys[: len(expected)] == expected

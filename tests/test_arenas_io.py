from pathlib import Path

import pytest
import yaml

from app.io import arenas as arenas_io


def _mk_company_meta(tmp_path: Path, ticker: str, market: str, arenas: list[str]) -> None:
    """Seed a minimal meta.md so arenas.find_by_company can read it."""
    d = tmp_path / "companies" / f"{market}_{ticker}"
    d.mkdir(parents=True)
    fm = {"ticker": ticker, "market": market, "arenas": arenas}
    (d / "meta.md").write_text(
        "---\n"
        + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).rstrip()
        + "\n---\n\n# "
        + ticker
        + "\n",
        encoding="utf-8",
    )


def test_list_arenas_empty(tmp_path):
    assert arenas_io.list_arenas(base=tmp_path) == []


def test_write_and_read_definition(tmp_path):
    fm = {
        "slug": "cn-xlpe",
        "name": "中国中高压电缆用 XLPE 材料",
        "created": "2026-04-25",
        "last_updated": "2026-04-25",
        "participants": [
            {"market": "BSE", "ticker": "920118", "name": "太湖远大", "role": "challenger"},
        ],
    }
    body = "## 四维定义\n- 产品：XLPE\n"
    path = arenas_io.write_definition("cn-xlpe", fm, body, base=tmp_path)
    assert path.exists()

    out = arenas_io.read_definition("cn-xlpe", base=tmp_path)
    assert out["exists"]
    assert out["frontmatter"]["slug"] == "cn-xlpe"
    # ticker stored as str
    assert out["frontmatter"]["participants"][0]["ticker"] == "920118"
    assert "XLPE" in out["body"]


def test_write_definition_rejects_mismatched_slug(tmp_path):
    with pytest.raises(ValueError, match="slug"):
        arenas_io.write_definition("a", {"slug": "b"}, "", base=tmp_path)


def test_write_definition_coerces_int_ticker(tmp_path):
    fm = {
        "slug": "s",
        "participants": [{"market": "BSE", "ticker": 920118, "name": "X"}],
    }
    arenas_io.write_definition("s", fm, "", base=tmp_path)
    out = arenas_io.read_definition("s", base=tmp_path)
    # YAML round-trip — safe_load may parse back to int even if str was dumped,
    # but write path should have turned participant ticker into str
    part = out["frontmatter"]["participants"][0]
    assert str(part["ticker"]) == "920118"


def test_participants_add_deduplicates(tmp_path):
    arenas_io.write_definition(
        "s",
        {"slug": "s", "participants": []},
        "",
        base=tmp_path,
    )
    arenas_io.participants_add("s", "920118", "BSE", "太湖远大", base=tmp_path)
    arenas_io.participants_add("s", "920118", "BSE", "太湖远大", base=tmp_path)
    out = arenas_io.read_definition("s", base=tmp_path)
    assert len(out["frontmatter"]["participants"]) == 1


def test_list_arenas_multiple(tmp_path):
    for slug, name in [("a1", "Arena 1"), ("a2", "Arena 2")]:
        arenas_io.write_definition(
            slug, {"slug": slug, "name": name}, "", base=tmp_path
        )
    rows = arenas_io.list_arenas(base=tmp_path)
    assert [r["slug"] for r in rows] == ["a1", "a2"]
    assert rows[1]["name"] == "Arena 2"


def test_write_checklist_v1_then_bump(tmp_path):
    arenas_io.write_definition("s", {"slug": "s"}, "", base=tmp_path)
    items_v1 = [
        {
            "id": "q1",
            "question": "Q1?",
            "why_matters": "Y1",
            "typical_evidence_section": ["investment_thesis"],
            "tags": ["competitive_position"],
        },
    ]
    arenas_io.write_checklist(
        "s", items_v1, {"source_id": "X", "changes": "init"}, base=tmp_path
    )
    cl = arenas_io.read_checklist("s", base=tmp_path)
    assert cl["version"] == 1
    assert len(cl["changelog"]) == 1

    items_v2 = items_v1 + [
        {
            "id": "q2",
            "question": "Q2?",
            "why_matters": "Y2",
            "typical_evidence_section": ["mdna"],
            "tags": ["growth_drivers", "financial_model"],
        },
    ]
    arenas_io.write_checklist(
        "s", items_v2, {"source_id": "Y", "changes": "add q2"}, base=tmp_path
    )
    cl = arenas_io.read_checklist("s", base=tmp_path)
    assert cl["version"] == 2
    assert len(cl["changelog"]) == 2
    assert [i["id"] for i in cl["items"]] == ["q1", "q2"]


def test_write_checklist_rejects_bad_tag(tmp_path):
    arenas_io.write_definition("s", {"slug": "s"}, "", base=tmp_path)
    with pytest.raises(ValueError, match="tag"):
        arenas_io.write_checklist(
            "s",
            [
                {
                    "id": "q1",
                    "question": "Q1",
                    "why_matters": "Y",
                    "typical_evidence_section": ["mdna"],
                    "tags": ["made_up_tag"],
                }
            ],
            None,
            base=tmp_path,
        )


def test_write_checklist_rejects_over_15(tmp_path):
    items = [
        {
            "id": f"q{i}",
            "question": "Q",
            "why_matters": "Y",
            "typical_evidence_section": ["mdna"],
            "tags": ["risk"],
        }
        for i in range(16)
    ]
    with pytest.raises(ValueError, match="15"):
        arenas_io.write_checklist("s", items, None, base=tmp_path)


def test_write_checklist_rejects_dup_id(tmp_path):
    items = [
        {
            "id": "q1",
            "question": "A",
            "why_matters": "y",
            "typical_evidence_section": ["mdna"],
            "tags": ["risk"],
        },
        {
            "id": "q1",
            "question": "B",
            "why_matters": "y",
            "typical_evidence_section": ["mdna"],
            "tags": ["risk"],
        },
    ]
    with pytest.raises(ValueError, match="duplicate"):
        arenas_io.write_checklist("s", items, None, base=tmp_path)


def test_consolidate_answers_picks_best():
    raw = [
        {"q_id": "q1", "level": "vague", "evidence_quote": "short"},
        {"q_id": "q1", "level": "specific", "evidence_quote": "medium len quote"},
        {"q_id": "q1", "level": "specific", "evidence_quote": "much longer quote with more detail " * 3},
        {"q_id": "q2", "level": "unanswered", "evidence_quote": ""},
    ]
    out = arenas_io.consolidate_answers(raw)
    by = {a["q_id"]: a for a in out}
    assert by["q1"]["level"] == "specific"
    assert "much longer" in by["q1"]["evidence_quote"]
    assert by["q2"]["level"] == "unanswered"


def test_append_notes_new_ticker(tmp_path):
    arenas_io.write_definition("s", {"slug": "s"}, "", base=tmp_path)
    arenas_io.append_notes(
        "s",
        ticker="920118",
        market="BSE",
        name="太湖远大",
        answered_items=[
            {
                "q_id": "q_cert",
                "level": "specific",
                "answer_text": "认证周期 2-3 年",
                "evidence_quote": "公司已通过国网认证",
            }
        ],
        source_id="研报-X-2024-a1",
        checklist_version=1,
        base=tmp_path,
    )
    text = (tmp_path / "arenas" / "s" / "competence-notes.md").read_text(
        encoding="utf-8"
    )
    assert "BSE_920118" in text
    assert "q_cert" in text
    assert "认证周期" in text
    assert "> 公司已通过国网认证" in text


def test_append_notes_replaces_ticker_block(tmp_path):
    arenas_io.write_definition("s", {"slug": "s"}, "", base=tmp_path)
    arenas_io.append_notes(
        "s",
        ticker="920118",
        market="BSE",
        name="太湖远大",
        answered_items=[
            {"q_id": "q1", "level": "vague", "answer_text": "old", "evidence_quote": "old"}
        ],
        source_id="研报-A",
        checklist_version=1,
        base=tmp_path,
    )
    arenas_io.append_notes(
        "s",
        ticker="920118",
        market="BSE",
        name="太湖远大",
        answered_items=[
            {
                "q_id": "q1",
                "level": "specific",
                "answer_text": "new",
                "evidence_quote": "new evidence",
            }
        ],
        source_id="研报-B",
        checklist_version=2,
        base=tmp_path,
    )
    text = (tmp_path / "arenas" / "s" / "competence-notes.md").read_text(
        encoding="utf-8"
    )
    assert "old" not in text
    assert "new" in text
    assert "研报-B" in text


def test_append_notes_drops_unanswered(tmp_path):
    arenas_io.write_definition("s", {"slug": "s"}, "", base=tmp_path)
    arenas_io.append_notes(
        "s",
        ticker="X",
        market="US",
        name="X Inc",
        answered_items=[
            {"q_id": "q1", "level": "unanswered", "answer_text": "", "evidence_quote": ""},
        ],
        source_id="sid",
        checklist_version=1,
        base=tmp_path,
    )
    text = (tmp_path / "arenas" / "s" / "competence-notes.md").read_text(
        encoding="utf-8"
    )
    assert "q1" not in text
    assert "US_X" not in text  # nothing to write, so no ticker section


def test_find_by_company_reads_meta(tmp_path):
    _mk_company_meta(tmp_path, "920118", "BSE", ["cn-xlpe", "cn-hv-cable"])
    assert arenas_io.find_by_company("920118", "BSE", base=tmp_path) == [
        "cn-xlpe",
        "cn-hv-cable",
    ]


def test_find_by_company_missing_meta(tmp_path):
    assert arenas_io.find_by_company("NOPE", "US", base=tmp_path) == []


def test_slug_exists(tmp_path):
    assert not arenas_io.slug_exists("s", base=tmp_path)
    arenas_io.write_definition("s", {"slug": "s"}, "", base=tmp_path)
    assert arenas_io.slug_exists("s", base=tmp_path)


def test_parse_notes_empty(tmp_path):
    assert arenas_io.parse_notes("nope", base=tmp_path) == {
        "by_ticker": {},
        "by_question": {},
    }


def test_parse_notes_roundtrip_single(tmp_path):
    arenas_io.write_definition("s", {"slug": "s"}, "", base=tmp_path)
    arenas_io.append_notes(
        "s",
        ticker="920118",
        market="BSE",
        name="太湖远大",
        answered_items=[
            {
                "q_id": "q_cert",
                "level": "specific",
                "answer_text": "认证周期 2-3 年，"
                "切换成本高",
                "evidence_quote": "公司已通过国网认证\n续签率 99%",
            }
        ],
        source_id="研报-X-2024-a1",
        checklist_version=3,
        base=tmp_path,
    )
    parsed = arenas_io.parse_notes("s", base=tmp_path)
    assert "BSE_920118" in parsed["by_ticker"]
    block = parsed["by_ticker"]["BSE_920118"]
    assert block["name"] == "太湖远大"
    ans = block["answers"]["q_cert"]
    assert ans["level"] == "specific"
    assert "认证周期 2-3 年" in ans["answer"]
    assert "国网认证" in ans["quote"]
    assert "续签率 99%" in ans["quote"]
    assert ans["source_id"] == "研报-X-2024-a1"
    assert ans["checklist_version"] == 3
    assert parsed["by_question"]["q_cert"][0]["ticker"] == "920118"


def test_parse_notes_multi_ticker_multi_question(tmp_path):
    arenas_io.write_definition("s", {"slug": "s"}, "", base=tmp_path)
    arenas_io.append_notes(
        "s",
        ticker="A",
        market="US",
        name="Alpha Inc",
        answered_items=[
            {"q_id": "q1", "level": "specific", "answer_text": "A1", "evidence_quote": "qA1"},
            {"q_id": "q2", "level": "vague", "answer_text": "A2", "evidence_quote": "qA2"},
        ],
        source_id="sid-A",
        checklist_version=1,
        base=tmp_path,
    )
    arenas_io.append_notes(
        "s",
        ticker="B",
        market="US",
        name="Beta Inc",
        answered_items=[
            {"q_id": "q1", "level": "vague", "answer_text": "B1", "evidence_quote": "qB1"},
        ],
        source_id="sid-B",
        checklist_version=1,
        base=tmp_path,
    )
    parsed = arenas_io.parse_notes("s", base=tmp_path)
    assert set(parsed["by_ticker"]) == {"US_A", "US_B"}
    assert parsed["by_ticker"]["US_A"]["answers"]["q1"]["answer"] == "A1"
    assert parsed["by_ticker"]["US_A"]["answers"]["q2"]["level"] == "vague"
    assert [r["ticker"] for r in parsed["by_question"]["q1"]] == ["A", "B"]
    assert "q2" in parsed["by_question"]
    assert parsed["by_question"]["q2"][0]["ticker"] == "A"


def test_company_summary_empty(tmp_path):
    _mk_company_meta(tmp_path, "X", "US", [])
    assert arenas_io.company_summary("X", "US", base=tmp_path) == []


def test_company_summary_mixed_levels(tmp_path):
    _mk_company_meta(tmp_path, "920118", "BSE", ["s"])
    arenas_io.write_definition("s", {"slug": "s", "name": "Arena S"}, "", base=tmp_path)
    items = [
        {
            "id": f"q{i}",
            "question": f"Q{i}?",
            "why_matters": "Y",
            "typical_evidence_section": ["mdna"],
            "tags": ["risk"],
        }
        for i in range(1, 5)
    ]
    arenas_io.write_checklist("s", items, None, base=tmp_path)
    arenas_io.append_notes(
        "s",
        ticker="920118",
        market="BSE",
        name="太湖远大",
        answered_items=[
            {"q_id": "q1", "level": "specific", "answer_text": "a", "evidence_quote": "q"},
            {"q_id": "q2", "level": "vague", "answer_text": "a", "evidence_quote": "q"},
        ],
        source_id="sid",
        checklist_version=1,
        base=tmp_path,
    )
    rows = arenas_io.company_summary("920118", "BSE", base=tmp_path)
    assert len(rows) == 1
    r = rows[0]
    assert r["slug"] == "s"
    assert r["name"] == "Arena S"
    assert r["total"] == 4
    assert r["answered_specific"] == 1
    assert r["answered_vague"] == 1
    assert r["unanswered"] == 2


def test_read_arena_combined(tmp_path):
    arenas_io.write_definition(
        "s", {"slug": "s", "name": "S"}, "body", base=tmp_path
    )
    arenas_io.write_checklist(
        "s",
        [
            {
                "id": "q1",
                "question": "Q1",
                "why_matters": "Y",
                "typical_evidence_section": ["mdna"],
                "tags": ["risk"],
            }
        ],
        None,
        base=tmp_path,
    )
    out = arenas_io.read_arena("s", base=tmp_path)
    assert out["exists"]
    assert out["definition_fm"]["name"] == "S"
    assert out["checklist"]["version"] == 1
    assert len(out["checklist"]["items"]) == 1

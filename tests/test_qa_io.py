"""Tests for app/io/qa.py scope-based API (Plan 4 T3).

Covers:
- _resolve_scope_dir routes company vs industry scopes correctly
- append/read/update roundtrip for both scope kinds
- cross-scope summarize_by_scope walks both companies/ and industries/
"""
from __future__ import annotations

import json
import pytest

from app.io import qa as qa_io


# --- scope resolution -------------------------------------------------------


def test_resolve_scope_company(tmp_path):
    d = qa_io._resolve_scope_dir("BSE_920118", base=tmp_path)
    assert d == tmp_path / "companies" / "BSE_920118"


def test_resolve_scope_industry(tmp_path):
    d = qa_io._resolve_scope_dir("industry:cn-cmp-material", base=tmp_path)
    assert d == tmp_path / "industries" / "cn-cmp-material"


def test_resolve_scope_rejects_malformed():
    with pytest.raises(ValueError):
        qa_io._resolve_scope_dir("no-underscore")
    with pytest.raises(ValueError):
        qa_io._resolve_scope_dir("industry:")


def test_scope_kind():
    assert qa_io._scope_kind("BSE_920118") == "company"
    assert qa_io._scope_kind("industry:semiconductor") == "industry"


# --- warnings roundtrip -----------------------------------------------------


def _make(scope: str, rule: str = "fidelity", target: str = "claim:#1") -> dict:
    return qa_io.make_warning(
        scope=scope, source_id="src-1", rule=rule, target=target,
        detail="detail",
    )


def test_append_and_read_company_scope(tmp_path):
    scope = "BSE_920118"
    w1 = _make(scope, rule="fidelity")
    counts = qa_io.append_warnings(scope, [w1], base=tmp_path)
    assert counts == {"added": 1, "skipped_dup": 0, "reopened": 0}

    got = qa_io.read_warnings(scope, base=tmp_path)
    assert len(got) == 1
    assert got[0]["scope"] == scope
    assert got[0]["rule"] == "fidelity"


def test_append_and_read_industry_scope(tmp_path):
    scope = "industry:cn-cmp-material"
    w1 = _make(scope, rule="fidelity", target="observation:#5")
    counts = qa_io.append_warnings(scope, [w1], base=tmp_path)
    assert counts["added"] == 1

    path = tmp_path / "industries" / "cn-cmp-material" / "qa_warnings.jsonl"
    assert path.exists()

    got = qa_io.read_warnings(scope, base=tmp_path)
    assert len(got) == 1
    assert got[0]["scope"] == scope


def test_append_skips_duplicate(tmp_path):
    scope = "BSE_920118"
    w1 = _make(scope)
    qa_io.append_warnings(scope, [w1], base=tmp_path)
    counts = qa_io.append_warnings(scope, [w1], base=tmp_path)
    assert counts == {"added": 0, "skipped_dup": 1, "reopened": 0}


def test_update_status_company(tmp_path):
    scope = "BSE_920118"
    w1 = _make(scope)
    qa_io.append_warnings(scope, [w1], base=tmp_path)
    ok = qa_io.update_status(scope, w1["id"], "resolved", note="done", base=tmp_path)
    assert ok
    got = qa_io.read_warnings(scope, base=tmp_path)
    assert got[0]["status"] == "resolved"
    assert got[0]["resolved_note"] == "done"


def test_update_status_industry(tmp_path):
    scope = "industry:cn-cmp-material"
    w1 = _make(scope, rule="fidelity", target="observation:#5")
    qa_io.append_warnings(scope, [w1], base=tmp_path)
    ok = qa_io.update_status(scope, w1["id"], "dismissed", base=tmp_path)
    assert ok
    got = qa_io.read_warnings(scope, base=tmp_path)
    assert got[0]["status"] == "dismissed"


def test_read_filter_by_status(tmp_path):
    scope = "BSE_920118"
    a = _make(scope, rule="fidelity")
    b = _make(scope, rule="empty_evidence")
    qa_io.append_warnings(scope, [a, b], base=tmp_path)
    qa_io.update_status(scope, a["id"], "resolved", base=tmp_path)

    open_only = qa_io.read_warnings(scope, status="open", base=tmp_path)
    assert len(open_only) == 1
    assert open_only[0]["rule"] == "empty_evidence"


# --- gap md roundtrip -------------------------------------------------------


def test_gap_markdown_roundtrip_industry(tmp_path):
    scope = "industry:cn-cmp-material"
    path = qa_io.write_gap_markdown(scope, "## 行业缺口\n- 缺市场空间数据", base=tmp_path)
    assert path == tmp_path / "industries" / "cn-cmp-material" / "qa_gaps.md"

    md, generated_at = qa_io.read_gap_markdown(scope, base=tmp_path)
    assert "行业缺口" in md
    assert generated_at is not None


# --- cross-scope summary ----------------------------------------------------


def test_summarize_by_scope_walks_both(tmp_path):
    qa_io.append_warnings("BSE_920118", [_make("BSE_920118")], base=tmp_path)
    qa_io.append_warnings("industry:semiconductor", [_make("industry:semiconductor")], base=tmp_path)

    rows = qa_io.summarize_by_scope(base=tmp_path)
    assert len(rows) == 2
    by_scope = {r["scope"]: r for r in rows}
    assert by_scope["BSE_920118"]["scope_kind"] == "company"
    assert by_scope["industry:semiconductor"]["scope_kind"] == "industry"
    assert by_scope["BSE_920118"]["open"] == 1


def test_summarize_by_scope_empty(tmp_path):
    assert qa_io.summarize_by_scope(base=tmp_path) == []

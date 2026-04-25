"""Unit tests for the filter/sort/paginate helpers in app.routes.research."""
from app.routes.research import _filter_claims, _paginate, _sort_claims


def _mk(**kw):
    defaults = {
        "id": "c1",
        "subject_tag": "growth",
        "polarity": "bull",
        "source_id": "sid-A",
        "extracted_at": "2026-04-01T10:00:00+00:00",
    }
    defaults.update(kw)
    return defaults


def test_filter_noop_when_all_blank():
    items = [_mk(id="1"), _mk(id="2", subject_tag="risk", polarity="bear")]
    assert _filter_claims(items, "", "", "") == items


def test_filter_subject_tag():
    items = [_mk(id="1", subject_tag="growth"), _mk(id="2", subject_tag="risk")]
    assert [c["id"] for c in _filter_claims(items, "growth", "", "")] == ["1"]


def test_filter_polarity_and_source():
    items = [
        _mk(id="1", polarity="bull", source_id="A"),
        _mk(id="2", polarity="bear", source_id="A"),
        _mk(id="3", polarity="bear", source_id="B"),
    ]
    got = _filter_claims(items, "", "bear", "A")
    assert [c["id"] for c in got] == ["2"]


def test_sort_extracted_at_desc_is_default():
    items = [
        _mk(id="old", extracted_at="2025-01-01"),
        _mk(id="new", extracted_at="2026-06-01"),
    ]
    got = _sort_claims(items, "extracted_at", "desc")
    assert [c["id"] for c in got] == ["new", "old"]


def test_sort_asc():
    items = [
        _mk(id="old", extracted_at="2025-01-01"),
        _mk(id="new", extracted_at="2026-06-01"),
    ]
    got = _sort_claims(items, "extracted_at", "asc")
    assert [c["id"] for c in got] == ["old", "new"]


def test_sort_missing_values_go_last_in_both_orders():
    items = [
        _mk(id="has", source_id="sid-A"),
        _mk(id="empty", source_id=""),
        _mk(id="none", source_id=None),
    ]
    desc = _sort_claims(items, "source_id", "desc")
    asc = _sort_claims(items, "source_id", "asc")
    # 'has' should come first in both; 'empty' and 'none' are both missing
    assert desc[0]["id"] == "has"
    assert asc[0]["id"] == "has"
    assert {c["id"] for c in desc[1:]} == {"empty", "none"}
    assert {c["id"] for c in asc[1:]} == {"empty", "none"}


def test_sort_invalid_key_falls_back():
    items = [_mk(id="b", extracted_at="2025"), _mk(id="a", extracted_at="2026")]
    # invalid sort key → falls back to extracted_at desc
    got = _sort_claims(items, "nope", "desc")
    assert got[0]["id"] == "a"


def test_sort_invalid_order_falls_back_to_desc():
    items = [_mk(id="old", extracted_at="2025"), _mk(id="new", extracted_at="2026")]
    got = _sort_claims(items, "extracted_at", "sideways")
    assert got[0]["id"] == "new"


def test_paginate_basic():
    items = list(range(120))
    page_items, page, total_pages = _paginate(items, page=1, per_page=50)
    assert page_items == list(range(0, 50))
    assert (page, total_pages) == (1, 3)


def test_paginate_last_page_partial():
    items = list(range(120))
    page_items, page, total_pages = _paginate(items, page=3, per_page=50)
    assert page_items == list(range(100, 120))
    assert (page, total_pages) == (3, 3)


def test_paginate_over_bounds_clamps():
    items = list(range(30))
    page_items, page, total_pages = _paginate(items, page=999, per_page=50)
    assert page_items == items
    assert (page, total_pages) == (1, 1)


def test_paginate_empty():
    page_items, page, total_pages = _paginate([], page=1, per_page=50)
    assert page_items == []
    assert (page, total_pages) == (1, 1)

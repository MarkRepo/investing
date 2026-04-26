import json
from pathlib import Path
import pytest

from app.io import figure_contexts as fc_io
from app.io import industry as industry_io


def test_figure_context_schema_required_keys():
    assert set(fc_io.REQUIRED_KEYS) == {"id", "page", "caption", "surrounding_text", "section_name", "source_id"}


def test_append_write_read_roundtrip(tmp_path):
    base = tmp_path
    industry_io.create_industry(slug="x", name="X", scope="s", base=base)
    rows = [
        {"id": "fig-001", "page": 3,
         "caption": "图表1: 2020-2030 全球 CMP 市场规模",
         "surrounding_text": "如图表1所示，2025 市场规模 33.8 亿美元，CAGR 9.0%",
         "section_name": "market_size",
         "source_id": "行研-国金证券-2026-03-10-abc12345"},
    ]
    n = fc_io.append_figure_contexts("x", rows, base=base)
    assert n == 1
    read = fc_io.read_figure_contexts("x", base=base)
    assert len(read) == 1
    assert read[0]["caption"].startswith("图表1")


def test_append_rejects_missing_required_key(tmp_path):
    base = tmp_path
    industry_io.create_industry(slug="x", name="X", scope="", base=base)
    bad = [{"id": "f1", "page": 1}]  # missing caption etc.
    with pytest.raises(ValueError, match="missing"):
        fc_io.append_figure_contexts("x", bad, base=base)


def test_filter_by_source_id(tmp_path):
    base = tmp_path
    industry_io.create_industry(slug="x", name="X", scope="", base=base)
    fc_io.append_figure_contexts("x", [
        {"id": "a", "page": 1, "caption": "c1", "surrounding_text": "t",
         "section_name": "market_size", "source_id": "s1"},
        {"id": "b", "page": 2, "caption": "c2", "surrounding_text": "t",
         "section_name": "market_size", "source_id": "s2"},
    ], base=base)
    rows = fc_io.filter_by_source_id("x", "s1", base=base)
    assert {r["id"] for r in rows} == {"a"}

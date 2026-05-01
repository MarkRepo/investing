from __future__ import annotations

import json

import pytest

from app.io.bundle_registry import (
    append_registry,
    get_bundle,
    list_bundles,
    load_bundle_json,
    persist_bundle,
)


def _entry(source_id="source-1", source_type="industry_report"):
    return {
        "source_id": source_id,
        "sha8": "abcdef12",
        "source_type": source_type,
        "institution": "中银证券",
        "publish_date": "2025-04-10",
        "bundle_path": "industries/cn-nuclear-fusion/bundles/abcdef12.json",
        "source_file_path": "industries/cn-nuclear-fusion/sources/report.pdf",
        "ingested_at": "2026-04-30T08:15:00Z",
        "touched": {"industries": ["cn-nuclear-fusion"], "arenas": [], "companies": []},
    }


def test_append_and_get_bundle_registry_entry(tmp_path):
    entry = _entry()
    append_registry(entry, base=tmp_path)
    result = get_bundle("source-1", base=tmp_path)
    assert result == entry


def test_list_bundles_filters_by_type_and_institution(tmp_path):
    entry1 = _entry(source_id="source-1", source_type="industry_report")
    entry2 = _entry(source_id="source-2", source_type="annual_report")
    append_registry(entry1, base=tmp_path)
    append_registry(entry2, base=tmp_path)

    results = list_bundles({"type": "industry_report", "institution": "中银证券"}, base=tmp_path)
    assert len(results) == 1
    assert results[0]["source_id"] == "source-1"


def test_load_bundle_json_uses_registry_relative_path(tmp_path):
    entry = _entry()
    bundle_path = tmp_path / entry["bundle_path"]
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_data = {"key": "value", "source_id": "source-1"}
    bundle_path.write_text(json.dumps(bundle_data, ensure_ascii=False), encoding="utf-8")

    append_registry(entry, base=tmp_path)
    result = load_bundle_json("source-1", base=tmp_path)
    assert result == bundle_data


def test_load_bundle_json_raises_if_source_id_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_bundle_json("nonexistent-source", base=tmp_path)


def test_persist_bundle_writes_co_located_bundle_and_registry(tmp_path):
    bundle = {
        "source_digest": {
            "source_id": "source-1",
            "source_type": "industry_report",
            "source_date": "2025-04-10",
        },
        "insight_blocks": [],
        "atomic_facts": [],
        "synthesis": {},
    }
    source_file = tmp_path / "industries" / "cn-nuclear-fusion" / "sources" / "report.pdf"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"%PDF-1.4")

    entry = persist_bundle(
        bundle,
        source_file_path=source_file,
        touched={"industries": ["cn-nuclear-fusion"], "arenas": [], "companies": []},
        base=tmp_path,
    )

    assert entry["bundle_path"] == "industries/cn-nuclear-fusion/bundles/" + entry["sha8"] + ".json"
    assert (tmp_path / entry["bundle_path"]).exists()
    assert get_bundle("source-1", base=tmp_path)["source_id"] == "source-1"

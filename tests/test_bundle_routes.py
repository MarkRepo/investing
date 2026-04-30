"""Tests for /bundles routes."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parent.parent
    shutil.copytree(repo / "templates", tmp_path / "templates")
    (tmp_path / "companies").mkdir()
    (tmp_path / "watchlist").mkdir()
    (tmp_path / "portfolio").mkdir()
    (tmp_path / "portfolio" / "rules.md").write_text("# rules\n")
    (tmp_path / "journal" / "decisions").mkdir(parents=True)
    (tmp_path / "industries").mkdir()
    (tmp_path / "arenas").mkdir()
    (tmp_path / "macro").mkdir()
    (tmp_path / "data").mkdir()
    shutil.copytree(repo / "controlled-vocab", tmp_path / "controlled-vocab")

    monkeypatch.chdir(tmp_path)
    from app import config as cfg
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(cfg, "TEMPLATES_DIR", tmp_path / "templates")
    monkeypatch.setattr(cfg, "WATCHLIST_DIR", tmp_path / "watchlist")
    monkeypatch.setattr(cfg, "PORTFOLIO_DIR", tmp_path / "portfolio")
    monkeypatch.setattr(cfg, "JOURNAL_DIR", tmp_path / "journal")
    monkeypatch.setattr(cfg, "INDUSTRIES_DIR", tmp_path / "industries")
    monkeypatch.setattr(cfg, "ARENAS_DIR", tmp_path / "arenas")
    monkeypatch.setattr(cfg, "MACRO_DIR", tmp_path / "macro")
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cfg, "FINANCIALS_DB", tmp_path / "data" / "financials.db")
    monkeypatch.setattr(cfg, "CONTROLLED_VOCAB_DIR", tmp_path / "controlled-vocab")

    from main import app
    return TestClient(app)


def _registry_entry(source_id="source-1", source_type="industry_report"):
    return {
        "source_id": source_id,
        "sha8": "abcdef12",
        "source_type": source_type,
        "institution": "中银证券",
        "publish_date": "2025-04-10",
        "bundle_path": f"data/bundles/{source_id}.json",
        "source_file_path": f"data/sources/{source_id}/report.pdf",
        "ingested_at": "2026-04-30T08:15:00Z",
        "touched": {"industries": ["cn-nuclear-fusion"], "arenas": [], "companies": []},
    }


def _bundle_data():
    return {
        "source_digest": {"title": "核聚变行研", "date": "2025-04-10"},
        "insight_blocks": [{"id": "ib-01", "text": "国内核聚变进展显著"}],
        "atomic_facts": [{"id": "af-01", "text": "2025 年规划 1GW 装机"}],
        "synthesis": {"summary": "核聚变商业化仍在早期"},
        "stage_gates": {"passed": True, "reason": "enough signal"},
        "claim_candidates": [{"text": "核聚变 2030 商业化", "polarity": "bull"}],
        "company_candidates": [{"ticker": "600089", "market": "SSE"}],
        "arena_candidates": [{"slug": "cn-nuclear-fusion-commercial"}],
        "schema_fit_review": {"fit": "high", "notes": ""},
    }


def _write_registry_and_bundle(tmp_path, source_id="source-1"):
    entry = _registry_entry(source_id)
    bundle_data = _bundle_data()

    # Write registry
    registry_path = tmp_path / "data" / "bundle_registry.jsonl"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")

    # Write bundle JSON
    bundle_path = tmp_path / entry["bundle_path"]
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps(bundle_data, ensure_ascii=False), encoding="utf-8")

    return entry, bundle_data


def test_bundles_index_lists_registry_entries(client, tmp_path):
    _write_registry_and_bundle(tmp_path, "source-1")

    r = client.get("/bundles")
    assert r.status_code == 200
    assert "source-1" in r.text
    assert "industry_report" in r.text


def test_bundle_detail_renders_all_major_sections(client, tmp_path):
    _write_registry_and_bundle(tmp_path, "source-1")

    r = client.get("/bundles/source-1")
    assert r.status_code == 200
    assert "insight_blocks" in r.text
    assert "atomic_facts" in r.text
    assert "synthesis" in r.text
    assert "claim_candidates" in r.text
    assert "/sources/source-1/file" in r.text


def test_bundle_detail_404_for_unknown_source(client):
    r = client.get("/bundles/missing")
    assert r.status_code == 404


def _write_two_registry_entries(tmp_path):
    """Write two registry entries with different source_type and institution values."""
    entry_a = _registry_entry("source-a", source_type="industry_report")
    entry_a["institution"] = "中银证券"
    entry_a["touched"]["industries"] = ["cn-nuclear-fusion"]

    entry_b = _registry_entry("source-b", source_type="company_report")
    entry_b["institution"] = "海通证券"
    entry_b["touched"]["industries"] = ["cn-ev"]

    registry_path = tmp_path / "data" / "bundle_registry.jsonl"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(entry_a) + "\n" + json.dumps(entry_b) + "\n",
        encoding="utf-8",
    )

    # Write minimal bundle files so detail routes wouldn't crash (not needed here
    # but keeps the registry consistent).
    for entry in (entry_a, entry_b):
        bundle_path = tmp_path / entry["bundle_path"]
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text(json.dumps(_bundle_data(), ensure_ascii=False), encoding="utf-8")

    return entry_a, entry_b


def test_bundles_filter_by_type_returns_matching_and_excludes_other(client, tmp_path):
    """?type= filter should return only the matching source_type entry."""
    _write_two_registry_entries(tmp_path)

    r = client.get("/bundles?type=industry_report")
    assert r.status_code == 200
    assert "source-a" in r.text
    assert "source-b" not in r.text


def test_bundles_filter_by_institution_returns_matching_and_excludes_other(client, tmp_path):
    """?institution= filter should return only the matching institution entry."""
    _write_two_registry_entries(tmp_path)

    r = client.get("/bundles?institution=海通证券")
    assert r.status_code == 200
    assert "source-b" in r.text
    assert "source-a" not in r.text


def test_bundles_filter_by_industry_returns_matching_and_excludes_other(client, tmp_path):
    """?industry= filter should return only entries touching that industry."""
    _write_two_registry_entries(tmp_path)

    r = client.get("/bundles?industry=cn-nuclear-fusion")
    assert r.status_code == 200
    assert "source-a" in r.text
    assert "source-b" not in r.text

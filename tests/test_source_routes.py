"""Tests for /sources routes."""
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


def _setup_source(tmp_path, source_id="source-1", filename="report.pdf"):
    source_file_path = f"data/sources/{source_id}/{filename}"
    entry = {
        "source_id": source_id,
        "sha8": "abcdef12",
        "source_type": "industry_report",
        "institution": "中银证券",
        "publish_date": "2025-04-10",
        "bundle_path": f"data/bundles/{source_id}.json",
        "source_file_path": source_file_path,
        "ingested_at": "2026-04-30T08:15:00Z",
        "touched": {"industries": ["cn-nuclear-fusion"], "arenas": [], "companies": []},
    }

    # Write registry
    registry_path = tmp_path / "data" / "bundle_registry.jsonl"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")

    # Write dummy source file
    source_path = tmp_path / source_file_path
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"%PDF-1.4 fake pdf content")

    # Write bundle JSON so detail route also works
    bundle_path = tmp_path / entry["bundle_path"]
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps({"source_id": source_id}), encoding="utf-8")

    return entry


def test_source_file_embeds_pdf(client, tmp_path):
    _setup_source(tmp_path, "source-1", "report.pdf")

    r = client.get("/sources/source-1/file")
    assert r.status_code == 200
    assert "<embed" in r.text
    assert "/bundles/source-1" in r.text


def test_source_file_404_for_unknown_source(client):
    r = client.get("/sources/missing/file")
    assert r.status_code == 404


def test_source_file_404_when_file_missing_from_disk(client, tmp_path):
    """Registry entry exists but source_file_path points to a nonexistent file."""
    entry = {
        "source_id": "source-1",
        "sha8": "abcdef12",
        "source_type": "industry_report",
        "institution": "中银证券",
        "publish_date": "2025-04-10",
        "bundle_path": "data/bundles/source-1.json",
        "source_file_path": "data/sources/source-1/missing.pdf",
        "ingested_at": "2026-04-30T08:15:00Z",
        "touched": {"industries": [], "arenas": [], "companies": []},
    }
    registry_path = tmp_path / "data" / "bundle_registry.jsonl"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    # Deliberately do NOT create the source file on disk.

    r = client.get("/sources/source-1/file")
    assert r.status_code == 404

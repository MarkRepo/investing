"""Smoke tests for /prism routes."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def prism_client(tmp_path, monkeypatch):
    """App client with isolated prism dir and minimal topic fixture."""
    repo = Path(__file__).resolve().parent.parent

    # Copy templates so Jinja2 can render
    shutil.copytree(repo / "app" / "templates", tmp_path / "app_templates")

    from app import config as cfg
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "APP_TEMPLATES_DIR", tmp_path / "app_templates")
    monkeypatch.setattr(cfg, "STATIC_DIR", tmp_path / "static")
    monkeypatch.setattr(cfg, "PRISM_DIR", tmp_path / "prism")

    # Patch other dirs so home route doesn't crash
    for name in ("companies", "industries", "arenas", "watchlist", "macro", "data", "static"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(cfg, "INDUSTRIES_DIR", tmp_path / "industries")
    monkeypatch.setattr(cfg, "ARENAS_DIR", tmp_path / "arenas")
    monkeypatch.setattr(cfg, "WATCHLIST_DIR", tmp_path / "watchlist")
    monkeypatch.setattr(cfg, "MACRO_DIR", tmp_path / "macro")
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cfg, "FINANCIALS_DB", tmp_path / "data" / "financials.db")
    (tmp_path / "portfolio").mkdir(parents=True, exist_ok=True)
    (tmp_path / "portfolio" / "rules.md").write_text("# r\n")
    monkeypatch.setattr(cfg, "PORTFOLIO_DIR", tmp_path / "portfolio")
    (tmp_path / "journal" / "decisions").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cfg, "JOURNAL_DIR", tmp_path / "journal")
    monkeypatch.setattr(cfg, "CONTROLLED_VOCAB_DIR", repo / "controlled-vocab")

    # Patch prism scripts to use tmp_path
    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    import prism.scripts.outputs as o
    monkeypatch.setattr(t, "_PRISM_ROOT", tmp_path / "prism")
    monkeypatch.setattr(m, "_PRISM_ROOT", tmp_path / "prism")
    monkeypatch.setattr(o, "_PRISM_ROOT", tmp_path / "prism")

    # Create a fixture topic
    prism_topics = tmp_path / "prism" / "topics"
    prism_topics.mkdir(parents=True)
    t.create_topic("cn-pet", "中国宠物行业", "industry", "宠物投资机会", "CN", "deep")
    m.create_manifest("cn-pet")

    from main import app
    return TestClient(app)


def test_prism_index_200(prism_client):
    r = prism_client.get("/prism")
    assert r.status_code == 200
    assert "中国宠物行业" in r.text


def test_prism_detail_200(prism_client):
    r = prism_client.get("/prism/cn-pet")
    assert r.status_code == 200
    assert "cn-pet" in r.text


def test_prism_detail_404_for_unknown(prism_client):
    r = prism_client.get("/prism/does-not-exist")
    assert r.status_code == 404


def test_prism_output_404_before_generated(prism_client):
    r = prism_client.get("/prism/cn-pet/output/01_business_panorama")
    assert r.status_code == 404


def test_prism_output_200_after_file_written(prism_client, tmp_path):
    out_path = tmp_path / "prism" / "topics" / "cn-pet" / "outputs" / "01_business_panorama.md"
    out_path.write_text("# 商业全景\n\n内容。", encoding="utf-8")
    r = prism_client.get("/prism/cn-pet/output/01_business_panorama")
    assert r.status_code == 200
    assert "商业全景" in r.text

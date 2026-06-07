"""宏观层 Web：顶部导航 + 输入源信息表。"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

VARIANT = "opus4.8"
SLUG = "global-macro-rates-liquidity"


@pytest.fixture
def macro_web_client(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parent.parent
    shutil.copytree(repo / "app" / "templates", tmp_path / "app_templates")

    from app import config as cfg
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "APP_TEMPLATES_DIR", tmp_path / "app_templates")
    monkeypatch.setattr(cfg, "STATIC_DIR", tmp_path / "static")
    monkeypatch.setattr(cfg, "PRISM_DIR", tmp_path / "prism")
    for name in ("companies", "industries", "watchlist", "macro", "data", "static"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(cfg, "INDUSTRIES_DIR", tmp_path / "industries")
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

    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    import prism.scripts.outputs as o
    import prism.scripts.macro_registry as reg
    monkeypatch.setattr(t, "PRISM_ROOT", tmp_path / "prism")
    monkeypatch.setattr(m, "_PRISM_ROOT", tmp_path / "prism")
    monkeypatch.setattr(o, "_PRISM_ROOT", tmp_path / "prism")
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path / "prism")

    (tmp_path / "prism" / "topics").mkdir(parents=True)
    t.create_topic(SLUG, "宏观层 (利率/流动性/汇率体制)", "macro", "三体制传导", "GLOBAL", "deep", VARIANT)
    m.create_manifest(SLUG, VARIANT)
    # 最小登记表：一条 FRED 自动抓取的报警序列
    reg.create_registry(SLUG, VARIANT)
    reg.upsert_input(SLUG, VARIANT, {
        "name": "HY OAS", "tier": "B", "cadence_type": "series", "targets": ["liquidity"],
        "mechanism": "CO", "importance": "confirming", "source": "FRED", "fetch_method": "fred-api",
        "fred_series_id": "BAMLH0A0HYM2", "alert_series": True,
        "alert_band": {"level": 4.5, "direction": "above"}, "monitoring": {"enabled": True},
    })

    from main import app
    return TestClient(app)


def test_nav_has_macro_link(macro_web_client):
    r = macro_web_client.get("/prism")
    assert r.status_code == 200
    assert "宏观层" in r.text
    assert f"/prism/{SLUG}/{VARIANT}/macro-inputs" in r.text


def test_index_shows_macro_label(macro_web_client):
    r = macro_web_client.get("/prism")
    assert "宏观" in r.text          # 中文标签
    assert ">macro<" not in r.text   # 不暴露原始 type


def test_macro_inputs_table_renders(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert r.status_code == 200
    assert "HY OAS" in r.text          # 输入名
    assert "FRED" in r.text            # 来源
    assert "自动" in r.text or "fred-api" in r.text   # 抓取方式


def test_macro_inputs_404_for_non_macro(macro_web_client):
    # 非 macro topic 命中该路由应 404（验证类型守卫，而非通配吞掉）
    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    t.create_topic("cn-industry-x", "某行业", "industry", "Q", "CN", "deep", VARIANT)
    m.create_manifest("cn-industry-x", VARIANT)
    r = macro_web_client.get(f"/prism/cn-industry-x/{VARIANT}/macro-inputs")
    assert r.status_code == 404

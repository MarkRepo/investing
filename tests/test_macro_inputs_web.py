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


def test_nav_macro_points_to_detail(macro_web_client):
    """顶部「宏观层」指向详情页（而非直接输入表）——输入表是详情页里的 tab。"""
    r = macro_web_client.get("/prism")
    assert r.status_code == 200
    assert "宏观层" in r.text
    assert f'href="/prism/{SLUG}/{VARIANT}"' in r.text          # detail 页
    assert f"/prism/{SLUG}/{VARIANT}/macro-inputs" not in r.text  # 不再直挂输入表


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


def test_macro_inputs_shows_caveat_note(macro_web_client):
    """带 note（口径/代理说明）的输入要在表里显示，而非只埋在 CLI smoke / 代码注释里。"""
    import prism.scripts.macro_registry as reg
    reg.upsert_input(SLUG, VARIANT, {
        "name": "DXY", "source": "FRED", "fetch_method": "fred-api",
        "fred_series_id": "DTWEXAFEGS",
        "note": "代理 DTWEXAFEGS，非 ICE 真·DXY，数值不可直接对市场报价",
    })
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert r.status_code == 200
    assert "非 ICE 真·DXY" in r.text


def test_macro_detail_shows_input_tab_not_diag(macro_web_client):
    """macro 详情页 tab 条：读者向 + 输入源；隐藏 诊断/体检（对宏观层不适用）。"""
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}")
    assert r.status_code == 200
    assert "输入源" in r.text
    assert f"/prism/{SLUG}/{VARIANT}/macro-inputs" in r.text   # 输入源 tab 链接
    assert "诊断 / debug" not in r.text                        # 诊断 tab 不展示
    assert "体检" not in r.text                                # 体检 tab 不展示


def test_macro_inputs_page_has_tab_bar(macro_web_client):
    """输入源页本身带 tab 条，可切回读者向。"""
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert r.status_code == 200
    assert "读者向" in r.text
    assert f'href="/prism/{SLUG}/{VARIANT}"' in r.text          # 读者向回链
    assert "输入源" in r.text


def test_diag_404_for_macro(macro_web_client):
    """诊断 tab 对宏观层不适用 → 直访路由也 404。"""
    assert macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/diag").status_code == 404


def test_checkup_404_for_macro(macro_web_client):
    """体检 tab 对宏观层不适用 → 直访路由也 404。"""
    assert macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/checkup").status_code == 404


def test_macro_nav_no_double_highlight(macro_web_client):
    """点「宏观层」时不应同时高亮「研究」（exclude 子树修复）。"""
    import re
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}")
    nav = re.search(r'<nav class="top">(.*?)</nav>', r.text, re.S).group(1)
    yanjiu = re.search(r'<a href="/prism"[^>]*>研究</a>', nav).group(0)
    assert "active" not in yanjiu                               # 研究 不亮
    macro_a = re.search(
        r'<a href="/prism/global-macro-rates-liquidity/opus4\.8"[^>]*>宏观层</a>', nav
    ).group(0)
    assert "active" in macro_a                                  # 宏观层 亮

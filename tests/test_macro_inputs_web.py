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
    import prism.scripts.eval_snapshot as es
    monkeypatch.setattr(es, "_PRISM_ROOT", tmp_path / "prism")

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


def _write_transmission_map(tmp_root):
    """往 tmp topic 写一份最小传导地图 yaml（含 regime + 一只持仓 + 类别尾部）。"""
    out = tmp_root / "prism" / "topics" / SLUG / VARIANT / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "transmission_map.yaml").write_text(
        "slug: %s\nvariant: %s\ngenerated: \"2026-06-07T00:00:00Z\"\n"
        "regime:\n"
        "  rates: {state: \"高位筑顶\", note: \"美钱仍贵\", confidence: 7}\n"
        "  composite: \"美紧中松分化体制 — 偏防御\"\n"
        "  conviction: 6\n  quadrant: 滞胀\n  fragility: high\n"
        "holdings:\n"
        "  - {slug: cn-kweichow-moutai-600519, display_name: 贵州茅台, duration: mid,\n"
        "     rate_beta: mid, usd_exposure: low, liquidity_beta: mid, exposure_score: mid,\n"
        "     regime_favor: [人民币企稳], regime_hurt: [中国紧信用],\n"
        "     plain: \"人民币内需防御票，几乎无美元暴露\"}\n"
        "categorical_tail:\n"
        "  - {name: 中美地缘/关税, state: 警示, note: \"关税战未停火\"}\n"
        % (SLUG, VARIANT),
        encoding="utf-8",
    )


def test_transmission_map_renders(macro_web_client, tmp_path):
    """传导地图上 web：路由渲染 regime banner + 每只持仓暴露行（不再 404 死指针）。"""
    _write_transmission_map(tmp_path)
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/transmission-map")
    assert r.status_code == 200
    assert "贵州茅台" in r.text                       # 持仓行
    assert "美紧中松分化体制" in r.text                # regime composite banner
    assert "滞胀" in r.text                            # 象限
    assert "人民币内需防御票" in r.text                # plain 人话
    assert "中美地缘/关税" in r.text                   # 类别尾部


def test_transmission_map_404_for_non_macro(macro_web_client):
    """非 macro topic 命中该路由应 404（类型守卫，而非通配吞掉）。"""
    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    t.create_topic("cn-industry-y", "某行业", "industry", "Q", "CN", "deep", VARIANT)
    m.create_manifest("cn-industry-y", VARIANT)
    r = macro_web_client.get(f"/prism/cn-industry-y/{VARIANT}/transmission-map")
    assert r.status_code == 404


def test_macro_detail_has_transmission_tab(macro_web_client):
    """macro 详情页 tab 条新增「传导地图」，指向 transmission-map。"""
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}")
    assert r.status_code == 200
    assert "传导地图" in r.text
    assert f"/prism/{SLUG}/{VARIANT}/transmission-map" in r.text


def test_regime_read_annotations_have_alignment_hook(macro_web_client, tmp_path):
    """m_regime_read「活注解层」三句注解（这是什么/为什么看它/现在说明什么）需带对齐样式钩子，
    且每句渲染为以 <code> 标签起头的独立 li，供 CSS 把标签定宽成列、正文换行悬挂对齐。"""
    out = tmp_path / "prism" / "topics" / SLUG / VARIANT / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "m_regime_read.md").write_text(
        "---\nslug: x\noutput_key: m_regime_read\n---\n"
        "### 关键输入指标\n\n"
        "**美国政策利率：3.50%–3.75%**\n"
        "- `这是什么`：全球资金价格的总锚。\n"
        "- `为什么看它`：利率体制的短端发动机。\n"
        "- `现在说明什么`：连续按兵不动，钱不会很快变便宜。\n",
        encoding="utf-8",
    )
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/m_regime_read")
    assert r.status_code == 200
    assert "regime-annot" in r.text                       # 对齐样式钩子（容器类）
    # 即便源文件「粗体标题行」与「- 注解项」之间漏了空行，也须渲染成真正的列表项
    # （否则退化成段落里的字面 `- ...`，既不换行也无从对齐）。
    assert "<li><code>这是什么</code>" in r.text
    assert "<li><code>为什么看它</code>" in r.text
    assert "<li><code>现在说明什么</code>" in r.text
    assert "- <code>这是什么</code>" not in r.text         # 不得留字面短横线


def test_eval_trace_renders_conclusions(macro_web_client):
    import prism.scripts.eval_snapshot as es
    es.append_evaluation(SLUG, VARIANT, {
        "input_snapshot": [{"name": "HY OAS", "value": 3.1, "as_of": "2026-06-01", "used": True}],
        "conclusions": [{"id": "liquidity", "label": "流动性体制", "state": "偏紧",
                         "based_on": [{"input": "HY OAS", "role": "confirming"}],
                         "causal": "HY OAS 走阔 → 风险偏好降 → 流动性偏紧"}]})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/eval-trace")
    assert r.status_code == 200
    assert "流动性体制" in r.text
    assert "HY OAS 走阔" in r.text                  # causal 句


def test_eval_trace_404_for_non_macro(macro_web_client):
    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    t.create_topic("cn-ind-z", "某行业", "industry", "Q", "CN", "deep", VARIANT)
    m.create_manifest("cn-ind-z", VARIANT)
    assert macro_web_client.get(f"/prism/cn-ind-z/{VARIANT}/eval-trace").status_code == 404


def test_primer_uses_links_not_bare_filenames():
    """00_primer 正文里对后台产物的引用要用人话锚链，不留裸文件名（web 上不可点/看不懂）。

    直接读真实仓库文件做内容守卫（fixture 的 tmp topic 不含 primer）。frontmatter
    的 companion:/sources_note: 合法命名文件，故剥掉 frontmatter 只查正文。
    """
    repo = Path(__file__).resolve().parent.parent
    raw = (repo / "prism" / "topics" / SLUG / VARIANT / "outputs" / "00_primer.md").read_text("utf-8")
    body = raw.split("---", 2)[-1]  # 剥 YAML frontmatter，只留正文
    assert f"](/prism/{SLUG}/{VARIANT}/m_regime_read)" in body        # 活读数锚链
    assert f"](/prism/{SLUG}/{VARIANT}/transmission-map)" in body     # 传导地图锚链
    assert "transmission_map.yaml" not in body                        # 正文不留裸后台文件名
    assert "m_regime_read.md" not in body

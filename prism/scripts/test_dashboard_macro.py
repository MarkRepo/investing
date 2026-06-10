"""宏观 banner 回归：sidecar 加载 / banner 收集 / 渲染 / 从非公司行排除 macro。"""
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from prism.scripts import topic as topic_io
from prism.scripts import dashboard


@pytest.fixture
def macro_env(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.dashboard.PRISM_ROOT", tmpdir)
    (tmpdir / "topics").mkdir()
    topic_io.create_topic(
        slug="global-macro-rates-liquidity", display_name="宏观层",
        topic_type="macro", question="Q", geo="GLOBAL", depth="deep",
        variant="opus4.8", search_terms=["利率"],
    )
    sidecar = {
        "slug": "global-macro-rates-liquidity", "variant": "opus4.8",
        "generated": "2026-06-07T00:00:00Z",
        "regime": {
            "rates": {"state": "下行", "note": "美联储转向在即", "confidence": 6},
            "liquidity": {"state": "偏松", "note": "净流动性回升", "confidence": 4},
            "fx": {"state": "人民币承压", "note": "中美利差倒挂", "confidence": 5},
            "composite": "温和宽松早期",
            "conviction": 5.5,
            "quadrant": "复苏早期",
            "fragility": "high",
        },
        "holdings": [
            {"slug": "cn-popmart", "display_name": "泡泡玛特",
             "exposure_score": "high", "plain": "高PE成长，利率敏感"},
            {"slug": "cn-premium-baijiu", "display_name": "白酒",
             "exposure_score": "low", "plain": "防御"},
        ],
    }
    out = tmpdir / "topics" / "global-macro-rates-liquidity" / "opus4.8" / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "transmission_map.yaml").write_text(
        yaml.dump(sidecar, allow_unicode=True, sort_keys=False), encoding="utf-8")
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_load_macro_sidecar(macro_env):
    sc = dashboard._load_macro_sidecar("global-macro-rates-liquidity", "opus4.8")
    assert sc["regime"]["composite"] == "温和宽松早期"


def test_collect_macro_banner(macro_env):
    banner = dashboard._collect_macro_banner()
    assert banner is not None
    assert banner["regime"]["composite"] == "温和宽松早期"
    assert [h["slug"] for h in banner["exposed"]] == ["cn-popmart"]


def test_banner_rendered(macro_env):
    company_rows = dashboard._collect_company_rows()
    other_rows = dashboard._collect_non_company_rows()
    banner = dashboard._collect_macro_banner()
    md = dashboard._render_dashboard(company_rows, other_rows, banner)
    assert "## 🌐 宏观体制" in md
    assert "温和宽松早期" in md
    assert "泡泡玛特" in md


def test_macro_excluded_from_other_rows(macro_env):
    other_rows = dashboard._collect_non_company_rows()
    assert all(r["type"] != "macro" for r in other_rows)


def test_banner_renders_multidim_and_fragility(macro_env):
    company_rows = dashboard._collect_company_rows()
    other_rows = dashboard._collect_non_company_rows()
    banner = dashboard._collect_macro_banner()
    md = dashboard._render_dashboard(company_rows, other_rows, banner)
    assert "复苏早期" in md          # 象限
    assert "脆弱度" in md            # fragility 标签词
    assert "信心" in md              # 分维信心展示
    assert banner["regime"]["fragility"] == "high"
    assert banner["regime"]["quadrant"] == "复苏早期"


def test_no_macro_topic_banner_none(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.dashboard.PRISM_ROOT", tmpdir)
    (tmpdir / "topics").mkdir()
    try:
        assert dashboard._collect_macro_banner() is None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_macro_banner_includes_stale_and_coverage(tmp_path, monkeypatch):
    from prism.scripts import macro_registry as reg
    from prism.scripts import eval_snapshot as es
    from prism.scripts import topic as topic_mod
    from prism.scripts import macro_xcut as mx
    monkeypatch.setattr(dashboard, "PRISM_ROOT", tmp_path)
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(es, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(mx, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(topic_mod, "PRISM_ROOT", tmp_path)

    gm, v = "global-macro-rates-liquidity", "opus4.8"

    def _mk(slug, ttype):
        d = tmp_path / "topics" / slug / v
        d.mkdir(parents=True, exist_ok=True)
        (d / "topic.yaml").write_text(yaml.dump(
            {"slug": slug, "type": ttype, "display_name": slug, "variant": v},
            allow_unicode=True), encoding="utf-8")

    # macro topic + transmission_map（含 regime + 一持仓）
    _mk(gm, "macro")
    od = tmp_path / "topics" / gm / v / "outputs"
    od.mkdir(parents=True, exist_ok=True)
    (od / "transmission_map.yaml").write_text(yaml.dump({
        "slug": gm, "variant": v,
        "regime": {"composite": "x", "conviction": 6},
        "holdings": [{"slug": "pdd", "display_name": "拼多多", "exposure_score": "high"}],
    }, allow_unicode=True, sort_keys=False), encoding="utf-8")
    # macro registry + eval（fx_cny=贬压重来）
    reg.create_registry(gm, v)
    reg.upsert_input(gm, v, {"name": "USDCNY", "cadence_type": "series", "importance": "load_bearing"})
    es.record_evaluation(gm, v, [{"id": "fx_cny", "label": "汇率", "state": "贬压重来",
        "causal": "y", "based_on": [{"input": "USDCNY", "role": "load_bearing"}]}])
    # company pdd 盖了旧印章（依赖 fx_cny=人民币企稳）+ futu 没入表
    _mk("pdd", "company")
    _mk("futu", "company")
    mx.write_macro_stamp("pdd", v, {"as_of_regime_version": 1,
        "depends_on_states": [{"conclusion": "fx_cny", "state": "人民币企稳", "role": "load_bearing"}]})

    banner = dashboard._collect_macro_banner()
    assert banner is not None
    stale_slugs = [h["slug"] for h in banner["stale_holdings"]]
    assert "pdd" in stale_slugs
    assert banner["coverage"]["missing"] == ["futu"]


def test_render_dashboard_shows_stale_and_coverage():
    """_render_dashboard 把 banner 的 stale_holdings + coverage 渲进宏观区。"""
    banner = {
        "slug": "gm", "variant": "v", "display_name": "宏观层",
        "regime": {"composite": "x", "conviction": 6}, "exposed": [],
        "freshness_days": 1,
        "stale_holdings": [{"slug": "pdd", "reason": "依赖的『人民币企稳』已变『贬压重来』"}],
        "coverage": {"missing": ["futu"], "provisional": ["xpev"],
                     "covered_count": 3, "total_company": 5},
    }
    md = dashboard._render_dashboard([], [], banner)
    assert "过期持仓" in md and "pdd" in md and "贬压重来" in md
    assert "3/5" in md and "futu" in md and "xpev" in md

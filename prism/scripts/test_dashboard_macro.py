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
            "rates": {"state": "下行", "note": "美联储转向在即"},
            "liquidity": {"state": "偏松", "note": "净流动性回升"},
            "fx": {"state": "人民币承压", "note": "中美利差倒挂"},
            "composite": "温和宽松早期",
            "conviction": 5.5,
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


def test_no_macro_topic_banner_none(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.dashboard.PRISM_ROOT", tmpdir)
    (tmpdir / "topics").mkdir()
    try:
        assert dashboard._collect_macro_banner() is None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

"""宏观横切（macro_stamp CRUD + staleness 扫 + coverage + self-register）零-LLM 测试。"""
import pytest
import yaml

from prism.scripts import macro_xcut as mx
from prism.scripts import macro_registry as reg
from prism.scripts import eval_snapshot as es
from prism.scripts import topic as topic_mod
from prism.scripts import monitor


@pytest.fixture
def tmp_world(tmp_path, monkeypatch):
    """一个 macro topic（registry+eval_log+transmission_map）+ 若干 company topic。"""
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(es, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(mx, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(topic_mod, "PRISM_ROOT", tmp_path)
    monkeypatch.setattr(monitor, "PRISM_ROOT", tmp_path)
    monkeypatch.setattr(monitor, "QUEUE_PATH", tmp_path / "monitor_queue.yaml")
    return tmp_path


def _write_topic_yaml(root, slug, variant, ttype, display=None):
    d = root / "topics" / slug / variant
    d.mkdir(parents=True, exist_ok=True)
    (d / "topic.yaml").write_text(
        yaml.dump({"slug": slug, "type": ttype, "display_name": display or slug,
                   "scope": {"ticker": "X"}}, allow_unicode=True),
        encoding="utf-8")


def test_read_macro_stamp_missing_returns_empty(tmp_world):
    assert mx.read_macro_stamp("pdd", "v") == {}


def test_write_then_read_macro_stamp_roundtrip(tmp_world):
    _write_topic_yaml(tmp_world, "pdd", "v", "company")
    mx.write_macro_stamp("pdd", "v", {
        "as_of_regime_version": 1, "regime_composite": "x",
        "depends_on_states": [{"conclusion": "fx_cny", "state": "稳", "role": "load_bearing"}],
        "discount_rate": None})
    got = mx.read_macro_stamp("pdd", "v")
    assert got["slug"] == "pdd" and got["variant"] == "v"
    assert got["stale"] is False and got["stale_reason"] is None
    assert got["depends_on_states"][0]["conclusion"] == "fx_cny"


def test_write_macro_stamp_rejects_bad_role(tmp_world):
    _write_topic_yaml(tmp_world, "pdd", "v", "company")
    with pytest.raises(ValueError, match="role 非法"):
        mx.write_macro_stamp("pdd", "v", {
            "depends_on_states": [{"conclusion": "fx_cny", "state": "稳", "role": "WRONG"}]})


def test_write_macro_stamp_rejects_missing_conclusion(tmp_world):
    _write_topic_yaml(tmp_world, "pdd", "v", "company")
    with pytest.raises(ValueError, match="缺 conclusion"):
        mx.write_macro_stamp("pdd", "v", {
            "depends_on_states": [{"state": "稳", "role": "load_bearing"}]})


def _seed_macro(root, slug="gm", variant="v"):
    """macro topic：registry 两输入 + 一版 eval（结论 fx_cny=稳）。"""
    reg.create_registry(slug, variant)
    reg.upsert_input(slug, variant, {"name": "USDCNY", "tier": "A",
        "cadence_type": "series", "mechanism": "CO", "importance": "load_bearing"})
    es.record_evaluation(slug, variant, [
        {"id": "fx_cny", "label": "人民币汇率体制", "state": "人民币企稳", "causal": "x",
         "based_on": [{"input": "USDCNY", "role": "load_bearing"}]}], note="v1")
    return slug, variant


def test_staleness_no_stamp_is_skipped(tmp_world):
    gm, v = _seed_macro(tmp_world)
    _write_topic_yaml(tmp_world, "pdd", v, "company")  # 没盖印章
    out = mx.scan_holding_staleness(gm, v)
    assert out == []  # 没接入 → 不在 staleness 范畴（归 coverage）


def test_staleness_state_unchanged_not_stale(tmp_world):
    gm, v = _seed_macro(tmp_world)
    _write_topic_yaml(tmp_world, "pdd", v, "company")
    mx.write_macro_stamp("pdd", v, {"as_of_regime_version": 1,
        "depends_on_states": [{"conclusion": "fx_cny", "state": "人民币企稳", "role": "load_bearing"}]})
    out = mx.scan_holding_staleness(gm, v)
    assert len(out) == 1 and out[0]["stale"] is False


def test_staleness_state_changed_is_stale(tmp_world):
    gm, v = _seed_macro(tmp_world)
    _write_topic_yaml(tmp_world, "pdd", v, "company")
    mx.write_macro_stamp("pdd", v, {"as_of_regime_version": 1,
        "depends_on_states": [{"conclusion": "fx_cny", "state": "人民币企稳", "role": "load_bearing"}]})
    # 新一版 regime：fx_cny 翻成贬压
    es.record_evaluation(gm, v, [
        {"id": "fx_cny", "label": "人民币汇率体制", "state": "贬压重来", "causal": "y",
         "based_on": [{"input": "USDCNY", "role": "load_bearing"}]}], note="v2")
    out = mx.scan_holding_staleness(gm, v)
    assert out[0]["stale"] is True
    assert out[0]["changed_states"][0] == {
        "conclusion": "fx_cny", "from": "人民币企稳", "to": "贬压重来", "role": "load_bearing"}
    assert "人民币企稳" in out[0]["reason"] and "贬压重来" in out[0]["reason"]


def test_staleness_no_regime_eval_marks_no_basis(tmp_world):
    reg.create_registry("gm", "v")  # 无 eval
    _write_topic_yaml(tmp_world, "pdd", "v", "company")
    mx.write_macro_stamp("pdd", "v", {"as_of_regime_version": 1,
        "depends_on_states": [{"conclusion": "fx_cny", "state": "稳", "role": "load_bearing"}]})
    out = mx.scan_holding_staleness("gm", "v")
    assert out[0]["stale"] is False and out[0]["basis"] == "no_regime_eval"


def _write_transmission_map(root, slug, variant, holdings):
    d = root / "topics" / slug / variant / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    (d / "transmission_map.yaml").write_text(
        yaml.dump({"slug": slug, "variant": variant, "holdings": holdings},
                  allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_coverage_gaps_reports_missing_and_provisional(tmp_world):
    gm, v = "gm", "v"
    _write_topic_yaml(tmp_world, "pdd", v, "company")
    _write_topic_yaml(tmp_world, "futu", v, "company")
    _write_topic_yaml(tmp_world, "baijiu", v, "arena")  # 非 company 不计
    _write_transmission_map(tmp_world, gm, v, [
        {"slug": "pdd", "provisional": True},   # 已覆盖但临时
    ])
    cov = mx.coverage_gaps(gm, v)
    assert cov["missing"] == ["futu"]
    assert cov["provisional"] == ["pdd"]
    assert cov["covered_count"] == 1 and cov["total_company"] == 2


def test_coverage_gaps_no_transmission_map(tmp_world):
    _write_topic_yaml(tmp_world, "pdd", "v", "company")
    cov = mx.coverage_gaps("gm", "v")
    assert cov["missing"] == ["pdd"] and cov["covered_count"] == 0


def test_register_holding_row_appends_with_provisional(tmp_world):
    gm, v = "gm", "v"
    _write_transmission_map(tmp_world, gm, v, [{"slug": "pdd"}])
    res = mx.register_holding_row(gm, v, {
        "slug": "futu", "display_name": "富途控股", "duration": "long",
        "rate_beta": "high", "as_of_regime": "v3"})
    assert res["registered"] is True
    tm = reg.read_transmission_map(gm, v)
    futu = next(h for h in tm["holdings"] if h["slug"] == "futu")
    assert futu["source"] == "self_registered" and futu["provisional"] is True
    assert futu["as_of_regime"] == "v3"


def test_register_holding_row_existing_is_skipped(tmp_world):
    gm, v = "gm", "v"
    _write_transmission_map(tmp_world, gm, v, [{"slug": "pdd", "source": "macro_synth"}])
    res = mx.register_holding_row(gm, v, {"slug": "pdd", "duration": "mid"})
    assert res["registered"] is False and res["reason"] == "exists"
    tm = reg.read_transmission_map(gm, v)
    assert len(tm["holdings"]) == 1  # 未覆盖既有行


def test_register_holding_row_no_map(tmp_world):
    res = mx.register_holding_row("gm", "v", {"slug": "pdd"})
    assert res["registered"] is False and res["reason"] == "no_transmission_map"

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

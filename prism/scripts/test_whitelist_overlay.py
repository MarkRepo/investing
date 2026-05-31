"""域族 whitelist overlay 收敛回路 单测。"""
import json
import pytest

from prism.scripts import web_prescan as wp


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """每个测试用独立 state 目录 + 清空 overlay 内容缓存，绝不碰真实 prism/state。"""
    state = tmp_path / "whitelist"
    (state / "overlays").mkdir(parents=True)
    monkeypatch.setattr(wp, "_STATE_DIR", state)
    wp._OVERLAY_CACHE.clear()
    yield state
    wp._OVERLAY_CACHE.clear()


def _write_overlay(state, family, hosts):
    p = state / "overlays" / f"{family}.json"
    p.write_text(json.dumps({"family": family, "hosts": hosts,
                             "promoted_count": len(hosts)}), encoding="utf-8")


def test_matches_exact_and_suffix():
    hosts = {"hkexnews.hk", "hengrui.com"}
    assert wp._matches("hkexnews.hk", hosts) is True
    assert wp._matches("www1.hengrui.com", hosts) is True   # endswith ".hengrui.com"
    assert wp._matches("nothengrui.com", hosts) is False
    assert wp._matches("random.example", hosts) is False


def test_load_overlay_reads_file(isolated_state):
    _write_overlay(isolated_state, "cn-pharma", ["hkexnews.hk"])
    assert wp._load_overlay("cn-pharma") == {"hkexnews.hk"}


def test_load_overlay_missing_returns_empty(isolated_state):
    assert wp._load_overlay("no-such-family") == set()


def test_load_overlay_caches(isolated_state):
    _write_overlay(isolated_state, "cn-pharma", ["a.com"])
    assert wp._load_overlay("cn-pharma") == {"a.com"}
    # 改盘后不失效缓存 → 仍读到旧值（证明确实走缓存）
    _write_overlay(isolated_state, "cn-pharma", ["a.com", "b.com"])
    assert wp._load_overlay("cn-pharma") == {"a.com"}


def test_classify_uses_overlay_only_with_family(isolated_state):
    _write_overlay(isolated_state, "cn-pharma", ["hkexnews.hk"])
    url = "https://www1.hkexnews.hk/listedco/x.htm"
    # 不传 family → 仍是 other（全局表里没有）
    assert wp.classify_domain(url) == "other"
    # 传 family → overlay 命中 → whitelist
    assert wp.classify_domain(url, family="cn-pharma") == "whitelist"


def test_classify_global_still_wins_without_family():
    # 全局表成员不依赖 family（向后兼容）
    assert wp.classify_domain("https://www.csrc.gov.cn/x") == "whitelist"
    assert wp.classify_domain("https://ir.tencent.com/x") == "whitelist"  # IR 启发式


def test_global_wins_even_when_family_supplied(isolated_state):
    # 同一域名同时进全局表与族 overlay → 应走全局表分支并短路，根本不查 overlay
    _write_overlay(isolated_state, "cn-pharma", ["csrc.gov.cn"])
    assert wp.classify_domain("https://www.csrc.gov.cn/x", family="cn-pharma") == "whitelist"
    # 真正的判据：全局表命中即 return，_load_overlay 从未被调 → 该 family 不进缓存
    assert "cn-pharma" not in wp._OVERLAY_CACHE


def test_family_of_root_uses_slug(monkeypatch):
    monkeypatch.setattr(wp.topic_io, "read_topic",
                        lambda s, v: {"type": "industry", "parent_topic": None})
    assert wp._family_of("cn-innovative-drug", "opus4.8") == "cn-innovative-drug"


def test_family_of_child_uses_parent(monkeypatch):
    monkeypatch.setattr(wp.topic_io, "read_topic",
                        lambda s, v: {"type": "arena", "parent_topic": "cn-innovative-drug"})
    assert wp._family_of("adc-arena", "v1") == "cn-innovative-drug"


def test_family_of_read_error_returns_none(monkeypatch):
    def boom(s, v):
        raise FileNotFoundError
    monkeypatch.setattr(wp.topic_io, "read_topic", boom)
    assert wp._family_of("ghost", "v1") is None


def test_promote_below_threshold_no_overlay(isolated_state):
    promoted = wp._promote("cn-pharma", "hengrui.com", "cn-innovative-drug/opus4.8")
    assert promoted is False
    assert not wp._overlay_path("cn-pharma").exists()   # 阈值=2，1 次不建 overlay
    log = json.loads((isolated_state / "_promotion_log.json").read_text())
    assert log["cn-pharma"]["hengrui.com"]["count"] == 1


def test_promote_same_topic_does_not_double_count(isolated_state):
    wp._promote("cn-pharma", "hengrui.com", "T1/v1")
    promoted = wp._promote("cn-pharma", "hengrui.com", "T1/v1")  # 同 topic 重复
    assert promoted is False
    log = json.loads((isolated_state / "_promotion_log.json").read_text())
    assert log["cn-pharma"]["hengrui.com"]["count"] == 1         # 仍是 1


def test_promote_reaches_threshold_writes_overlay(isolated_state):
    wp._promote("cn-pharma", "hengrui.com", "T1/v1")
    promoted = wp._promote("cn-pharma", "hengrui.com", "T2/v1")  # 第 2 个不同 topic
    assert promoted is True
    assert wp._load_overlay("cn-pharma") == {"hengrui.com"}      # 已进 overlay
    # 晋升后 classify 立即生效（缓存已失效）
    assert wp.classify_domain("https://hengrui.com/ir", family="cn-pharma") == "whitelist"
    log = json.loads((isolated_state / "_promotion_log.json").read_text())
    assert log["cn-pharma"]["hengrui.com"]["promoted"] is True


def test_promote_already_promoted_is_noop_after_threshold(isolated_state):
    wp._promote("cn-pharma", "hengrui.com", "T1/v1")
    wp._promote("cn-pharma", "hengrui.com", "T2/v1")             # → promoted
    promoted = wp._promote("cn-pharma", "hengrui.com", "T3/v1")  # 已晋升
    assert promoted is False                                     # 不重复写
    doc = json.loads(wp._overlay_path("cn-pharma").read_text(encoding="utf-8"))
    assert doc["hosts"] == ["hengrui.com"]   # 已晋升后不重复 append


def test_append_overlay_corrupt_file_not_clobbered(isolated_state):
    p = wp._overlay_path("cn-pharma")
    p.write_text("{ broken json", encoding="utf-8")
    wp._append_to_overlay("cn-pharma", "new.com")          # 损坏文件不应被空 doc 覆盖
    assert p.read_text(encoding="utf-8") == "{ broken json"  # 内容原样保留


def test_promote_with_corrupt_log_does_not_raise(isolated_state):
    (isolated_state / "_promotion_log.json").write_text("{ not json", encoding="utf-8")
    assert wp._promote("cn-pharma", "x.com", "T1/v1") is False   # 不抛、起新账、未达阈值


def test_append_overlay_sets_and_preserves_display_name(isolated_state):
    # 显式传 display_name → 写入；后续 _promote 自动建（不传）→ 不覆盖已有中文名
    wp._append_to_overlay("cn-pharma", "a.com", display_name="中国创新药")
    wp._append_to_overlay("cn-pharma", "b.com")                  # 无 display_name
    import json as _json
    doc = _json.loads(wp._overlay_path("cn-pharma").read_text(encoding="utf-8"))
    assert doc["display_name"] == "中国创新药"                    # 保留
    assert set(doc["hosts"]) == {"a.com", "b.com"}


def test_register_promotes_across_two_topics(isolated_state, monkeypatch, tmp_path):
    # 让 _family_of 对两个 topic 都解析到同族 'cn-innovative-drug'
    def fake_read_topic(slug, variant):
        if slug == "cn-innovative-drug":
            return {"type": "industry", "parent_topic": None}
        return {"type": "arena", "parent_topic": "cn-innovative-drug"}
    monkeypatch.setattr(wp.topic_io, "read_topic", fake_read_topic)
    # 把会写盘的下游全 stub 掉，只验证晋升回路
    monkeypatch.setattr(wp, "find_by_url", lambda *a, **k: None)
    monkeypatch.setattr(wp, "_web_search_inbox_dir", lambda slug: tmp_path)
    monkeypatch.setattr(wp, "make_search_meta", lambda **k: {})
    monkeypatch.setattr(wp, "add_material", lambda **k: "mat-test")

    url = "https://hengrui.com/investor/x"
    common = dict(query="q", url=url, title="t", snippet="s",
                  addresses=["scope"], domain_tier="llm-judged-official")
    # topic 1 判一次 → 未达阈值
    wp.register_web_search_result(slug="cn-innovative-drug", variant="opus4.8", **common)
    assert wp.classify_domain(url, family="cn-innovative-drug") == "other"
    # topic 2（子 arena，同族）判一次 → 达阈值 → 晋升
    wp.register_web_search_result(slug="adc-arena", variant="v1", **common)
    assert wp.classify_domain(url, family="cn-innovative-drug") == "whitelist"


def test_seed_build_targets_only_missing(monkeypatch):
    import prism.scripts.seed_overlay_cn_pharma as seed
    # 全部 host 都应是当前全局表判不出的（=种子有意义）
    for h in seed.SEED_HOSTS:
        assert wp.classify_domain("https://" + h + "/x") == "other", h
    assert seed.FAMILY == "cn-innovative-drug"
    assert seed.DISPLAY_NAME == "中国创新药"
    assert len(seed.SEED_HOSTS) == 11


def test_seed_writes_display_name(isolated_state):
    import prism.scripts.seed_overlay_cn_pharma as seed
    seed.seed()
    import json as _json
    doc = _json.loads(wp._overlay_path("cn-innovative-drug").read_text(encoding="utf-8"))
    assert doc["display_name"] == "中国创新药"
    assert len(doc["hosts"]) == 11

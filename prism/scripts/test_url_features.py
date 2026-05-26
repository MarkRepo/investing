"""Deterministic tests for extract_url_features + H2 dropped_hits return field.

Per H2 修订设计：脚本只测客观特征，不测主观分类 (tier/hint)。
fixture 累积本次踩到的真实 URL — 未来踩到新源加进来。
"""
import pytest

from prism.scripts.web_prescan import (
    extract_url_features,
    classify_domain,
    WHITELIST_DOMAINS,
)


# ---------------------------------------------------------------------------
# 1. extract_url_features — 客观特征 deterministic
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url,expected_subset", [
    # 财经媒体子域（修 H2 后命中 whitelist via endswith sina.com.cn）
    ("https://finance.sina.com.cn/stock/x.shtml", {
        "in_whitelist": True,
        "host": "finance.sina.com.cn",
        "subdomain_tokens": ["finance"],
        "tld_class": "cn",
        "path_is_pdf": False,
        "known_low_signal_host": False,
    }),
    # 医药垂直（修 H2 后命中 whitelist）
    ("https://bydrug.pharmcube.com/news/detail/xxx", {
        "in_whitelist": True,
        "host": "bydrug.pharmcube.com",
        "path_news_tokens": ["news", "detail"],
    }),
    # 公司官网托管 PDF — 这种是 H2 最该救的：非 whitelist 但明显是官方公告
    ("https://www.remegen.com/uploadfile/2025/08/23/x.pdf", {
        "in_whitelist": False,
        "host": "remegen.com",
        "path_is_pdf": True,
        "path_announce_tokens": ["uploadfile", "pdf"],
    }),
    # IR 子域 — 老逻辑命中 whitelist
    ("https://ir.tencent.com/news", {
        "in_whitelist": True,
        "subdomain_tokens": ["ir"],
    }),
    # 已知低信噪
    ("https://blog.csdn.net/some/post", {
        "in_whitelist": False,
        "known_low_signal_host": True,
    }),
    ("https://m.zhidao.baidu.com/q/123", {
        "known_low_signal_host": True,
    }),
    # 中性未知源 — 既不在 whitelist 也不在黑名单
    ("https://random-marketing.example.com/article/123", {
        "in_whitelist": False,
        "known_low_signal_host": False,
        "path_news_tokens": ["article"],
    }),
    # 监管补充：国家药监局
    ("https://www.nmpa.gov.cn/announce/2025/x.html", {
        "in_whitelist": True,
        "tld_class": "gov.cn",
        "path_announce_tokens": ["announce"],
    }),
    # 券商研报 PDF — 修 H2 后 spdbi 入 whitelist
    ("https://www.spdbi.com/getfile/x.pdf", {
        "in_whitelist": True,
        "path_is_pdf": True,
    }),
    # 海外医药垂直 — ApexOnco
    ("https://www.oncologypipeline.com/apexonco/pfizer-x", {
        "in_whitelist": True,
        "host": "oncologypipeline.com",
    }),
])
def test_extract_url_features_subset(url, expected_subset):
    features = extract_url_features([url])[url]
    for key, want in expected_subset.items():
        assert features[key] == want, (
            f"url={url} key={key} got={features[key]!r} want={want!r}"
        )


def test_extract_url_features_batch():
    """Batch input → batch output, key-by-key isolation."""
    urls = [
        "https://reuters.com/a",
        "https://blog.csdn.net/b",
    ]
    out = extract_url_features(urls)
    assert set(out.keys()) == set(urls)
    assert out[urls[0]]["in_whitelist"] is True
    assert out[urls[1]]["known_low_signal_host"] is True


# ---------------------------------------------------------------------------
# 2. WHITELIST 扩展回归 — 本次踩到的源必须都命中
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    # H2 实战踩到的非 mainstream 但权威源
    "https://finance.sina.com.cn/stock/x",
    "https://cj.sina.com.cn/articles/x",
    "https://vip.stock.finance.sina.com.cn/corp/x",
    "https://file.finance.qq.com/finance/x.pdf",
    "https://bydrug.pharmcube.com/news/detail/x",
    "https://www.pharnexcloud.com/zixun/x",
    "https://www.phirda.com/artilce_x.html",
    "https://www.baogaobox.com/insights/x.html",
    "https://synapse.zhihuiya.com/article/x",
    "https://www.fxbaogao.com/detail/x",
    "https://www.spdbi.com/getfile/x.pdf",
    "https://www.fiercebiotech.com/biotech/x",
    "https://www.oncologypipeline.com/apexonco/x",
    "https://endpts.com/x",
    "https://thebambooworks.com/x",
    "https://m.mp.oeeee.com/a/x",
    "https://www.nhsa.gov.cn/x",
    "https://www.nmpa.gov.cn/x",
])
def test_h2_authoritative_urls_now_whitelisted(url):
    """所有本次实战该入但被丢的源，修 H2 后必须 whitelist 命中。"""
    assert classify_domain(url) == "whitelist", (
        f"H2 regression: {url} should be whitelisted post-fix"
    )


# ---------------------------------------------------------------------------
# 3. register_web_search_batch 新返回字段 (dropped_hits / drop_ratio)
# ---------------------------------------------------------------------------

import shutil
import tempfile
from pathlib import Path

from prism.scripts import topic as topic_io
from prism.scripts.manifest import create_manifest


@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    slug = "test-h2"
    variant = "test-v"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(
        slug=slug, display_name="H2 Test", topic_type="company",
        question="Q?", geo="US", depth="quick", variant=variant,
        short_name="H2 Test",
        ticker="US_TEST",
    )
    create_manifest(slug, variant)
    yield slug, variant, tmpdir
    shutil.rmtree(tmpdir)


def test_dropped_hits_contains_low_band_with_reason(tmp_topic):
    """dropped_hits 完整保留被丢 hit + reason 字段，主 agent 可直接救回。"""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    hits = [
        {"title": "good", "url": "https://reuters.com/a", "snippet": "..."},
        {"title": "low-quality", "url": "https://random-blog-unknown.example/x", "snippet": "..."},
        {"title": "", "url": "", "snippet": "missing url/title"},  # invalid
    ]
    summary = register_web_search_batch(
        slug=slug, variant=variant, query="Q",
        addresses=["scope"], triggered_by="01-prescan", hits=hits,
    )
    # 新字段必须存在
    assert "dropped_hits" in summary
    assert "drop_ratio" in summary
    assert "n_dropped_invalid" in summary
    assert "n_dropped_low" in summary

    # 计数
    assert summary["n_dropped_invalid"] == 1
    assert summary["n_dropped_low"] == 1
    assert summary["drop_ratio"] == round(2 / 3, 2)

    # dropped_hits 列表内容
    assert len(summary["dropped_hits"]) == 2
    reasons = {d["reason"] for d in summary["dropped_hits"]}
    assert reasons == {"invalid", "low-band"}

    # low-band 那条要含 url/title/snippet 完整
    low = next(d for d in summary["dropped_hits"] if d["reason"] == "low-band")
    assert low["url"] == "https://random-blog-unknown.example/x"
    assert low["title"] == "low-quality"
    assert low["auto_domain_tier"] == "other"
    assert low["auto_confidence"] == pytest.approx(0.4)


def test_dropped_hits_empty_when_all_register(tmp_topic):
    """全部入库时 dropped_hits 为空 + drop_ratio=0。"""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    summary = register_web_search_batch(
        slug=slug, variant=variant, query="Q", addresses=["scope"],
        triggered_by="01-prescan",
        hits=[
            {"title": "T1", "url": "https://reuters.com/a", "snippet": "s"},
            {"title": "T2", "url": "https://www.sec.gov/a", "snippet": "s"},
        ],
    )
    assert summary["dropped_hits"] == []
    assert summary["drop_ratio"] == 0.0
    assert summary["n_dropped_low"] == 0
    assert summary["n_dropped_invalid"] == 0


def test_backward_compatibility_existing_fields_unchanged(tmp_topic):
    """老调用方读 n_high/n_mid/n_low/mat_ids/resolved_todos/duplicates 必须照常工作。"""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    summary = register_web_search_batch(
        slug=slug, variant=variant, query="Q", addresses=["scope"],
        triggered_by="01-prescan",
        hits=[{"title": "T", "url": "https://reuters.com/a", "snippet": "s"}],
    )
    # 老字段必须仍存在且类型不变
    for key in ("n_high", "n_mid", "n_low", "mat_ids", "resolved_todos", "duplicates"):
        assert key in summary
    assert isinstance(summary["n_high"], int)
    assert isinstance(summary["mat_ids"], list)
    assert isinstance(summary["resolved_todos"], list)


def test_high_drop_ratio_prints_warning_to_stderr(tmp_topic, capfd):
    """drop_ratio>=0.5 且有 low-band 时，stderr 打印附 url 列表的警告。"""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    register_web_search_batch(
        slug=slug, variant=variant, query="Q", addresses=["scope"],
        triggered_by="01-prescan",
        hits=[
            {"title": "good", "url": "https://reuters.com/a", "snippet": "s"},
            {"title": "low1", "url": "https://unknown-marketing-1.example/x", "snippet": "s"},
            {"title": "low2", "url": "https://unknown-marketing-2.example/x", "snippet": "s"},
        ],
    )
    captured = capfd.readouterr()
    assert "drop_ratio" in captured.err
    # >=0.5 触发附 url
    assert "unknown-marketing-1" in captured.err or "unknown-marketing-2" in captured.err

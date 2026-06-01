"""review-digest 子命令 + drop⇒no-finding 回归（PRISM_VALIDATION F5）。

digest 设计纪律：脚本只做机械投影 + 惰性展开，绝不把 snippet/raw_content 正文
灌进 index、绝不替主 agent 判 tier（反 F3）。drop 纪律（用户硬约束）：tier 判 drop
的 hit 即便手里已有 full_text，也不得入库、不得据此产 finding。
"""
import json
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts.web_search import main

# 易识别且足够长，用于断言"正文未泄漏 / 整段展开"
LONG_SNIPPET = "SNIPPET正文标记" + "锂" * 500
LONG_RAW = "RAWCONTENT正文标记" + "钠" * 2000


def _write_raw(tmpdir: Path, hits: list[dict]) -> Path:
    raw_dir = tmpdir / "prism" / "topics" / "demo" / "inbox" / "_websearch_raw"
    raw_dir.mkdir(parents=True)
    p = raw_dir / "20260101T000000Z_deadbeef.json"
    p.write_text(json.dumps({
        "searched_at": "2026-01-01T00:00:00Z",
        "query": "demo query", "intent": "news", "days": 90,
        "slug": "demo", "variant": "v", "triggered_by": "01-prescan",
        "addresses": ["K1"], "n_hits": len(hits), "hits": hits,
    }, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.fixture
def raw_json():
    tmpdir = Path(tempfile.mkdtemp())
    hits = [
        {"title": "Reuters report", "url": "https://reuters.com/x",
         "snippet": LONG_SNIPPET, "raw_content": LONG_RAW,
         "published_at": "2026-01-01", "domain_tier": None},
        {"title": "Random blog", "url": "https://random.example/p",
         "snippet": "shortsnippet", "raw_content": None},
    ]
    p = _write_raw(tmpdir, hits)
    yield p, tmpdir
    shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# digest index — 投影无正文泄漏
# ---------------------------------------------------------------------------

def test_digest_index_no_body_leak(raw_json, capsys):
    p, _ = raw_json
    rc = main(["review-digest", "--raw-path", str(p)])
    out = capsys.readouterr().out
    assert rc == 0
    # 零正文：snippet / raw_content 正文不得出现在 index
    assert LONG_SNIPPET not in out
    assert LONG_RAW not in out
    assert "shortsnippet" not in out
    # 但每条 host/title + 长度计数在
    assert "reuters.com" in out
    assert "Reuters report" in out
    assert f"snip={len(LONG_SNIPPET)}" in out
    assert f"raw={len(LONG_RAW)}" in out
    assert "raw=none" in out          # 第二条无 raw_content
    assert "[0]" in out and "[1]" in out
    # 透传 provider published_at
    assert "pub=2026-01-01" in out


# ---------------------------------------------------------------------------
# --show — 惰性展开单条整段
# ---------------------------------------------------------------------------

def test_digest_show_expands_one_whole_snippet(raw_json, capsys):
    p, _ = raw_json
    rc = main(["review-digest", "--raw-path", str(p), "--show", "0"])
    out = capsys.readouterr().out
    assert rc == 0
    assert LONG_SNIPPET in out            # 第 0 条 snippet 整段（不截）
    assert LONG_RAW not in out            # 不带 --full 不展开 raw_content
    assert "shortsnippet" not in out      # 不泄漏其它条正文


def test_digest_show_full_expands_whole_raw(raw_json, capsys):
    p, _ = raw_json
    rc = main(["review-digest", "--raw-path", str(p), "--show", "0", "--full"])
    out = capsys.readouterr().out
    assert rc == 0
    assert LONG_RAW in out                # raw_content 整段


def test_digest_show_full_missing_raw_hints_webfetch(raw_json, capsys):
    p, _ = raw_json
    rc = main(["review-digest", "--raw-path", str(p), "--show", "1", "--full"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "WebFetch" in out
    assert "raw_content 缺失" in out


def test_digest_show_comma_list(raw_json, capsys):
    p, _ = raw_json
    rc = main(["review-digest", "--raw-path", str(p), "--show", "0,1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert LONG_SNIPPET in out and "shortsnippet" in out


def test_digest_bad_path_exit_config(capsys):
    rc = main(["review-digest", "--raw-path", "/no/such/file.json"])
    assert rc == 50


def test_digest_show_out_of_range_exit_config(raw_json):
    p, _ = raw_json
    rc = main(["review-digest", "--raw-path", str(p), "--show", "9"])
    assert rc == 50


# --- [adapter-snippet] 修：--show 溯源横幅 + 越界 stdout 可见（防"静默空输出"）---

def test_digest_show_prints_provenance_banner(raw_json, capsys):
    """--show 必打 stdout 溯源横幅（raw 文件名 + query + n_hits）。"""
    p, _ = raw_json
    rc = main(["review-digest", "--raw-path", str(p), "--show", "0"])
    out = capsys.readouterr().out
    assert rc == 0
    assert p.name in out          # 在 digest 哪个 raw 文件
    assert "demo query" in out    # 哪条 query
    assert "n_hits: 2" in out


def test_digest_show_out_of_range_visible_on_stdout(raw_json, capsys):
    """越界时 stdout 也留可见标记——`| sed` 丢 stderr 时不再看着像空输出。"""
    p, _ = raw_json
    rc = main(["review-digest", "--raw-path", str(p), "--show", "9"])
    out = capsys.readouterr().out
    assert rc == 50
    assert "越界" in out and "9" in out   # stdout 非空、点明原因


# ---------------------------------------------------------------------------
# drop ⇒ no finding（用户硬约束 Q5）
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.web_prescan._STATE_DIR",
                        tmpdir / "state" / "whitelist")
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    from prism.scripts import topic as topic_io
    from prism.scripts.manifest import create_manifest
    slug, variant = "drop-demo", "v"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(
        slug=slug, display_name="Drop", topic_type="company",
        question="Q?", geo="US", depth="quick", variant=variant,
        short_name="Drop", ticker="US_TEST",
    )
    create_manifest(slug, variant)
    yield slug, variant, tmpdir
    shutil.rmtree(tmpdir)


def test_dropped_hit_with_full_text_yields_no_finding(tmp_topic):
    """low-band hit 即便带 full_text + triggered_by 自动开 inline，也不入库不产 finding。

    锁用户硬约束：full_text 只服务于判 tier，drop 即沉没。验证现有 low 早退
    （mat_id=None）+ inline 循环跳过 mat_id=None 对"带全文的 drop"同样成立。
    """
    from prism.scripts.web_prescan import register_web_search_batch
    from prism.scripts.manifest import read_manifest

    slug, variant, tmpdir = tmp_topic
    url = "https://random.example/p"   # 非白名单 → other → 0.4 → low band
    summary = register_web_search_batch(
        slug=slug, variant=variant, query="q",
        addresses=["K1"], triggered_by="04-synth",   # 自动开 inline finding
        hits=[{"title": "Random blog", "url": url, "snippet": "x"}],
        full_texts={url: "为判 tier 抓的全文" * 50},   # 手里已有全文
    )
    # low band：被丢，无 mat 落库
    assert summary["n_dropped_low"] >= 1
    assert all(m is None for m in summary["mat_ids"])
    # manifest 无 material
    manifest = read_manifest(slug, variant)
    assert len(manifest["materials"]) == 0
    # outputs/ 下无任何 findings 文件
    out_dir = tmpdir / "topics" / slug / variant / "outputs"
    findings = list(out_dir.glob("findings_*.md")) if out_dir.is_dir() else []
    assert findings == []

"""fed_speech 取文 fetcher 单测：纯函数（JSON feed 过滤最新主席条 + 正文剥离）。零网络。"""
from prism.scripts import fed_speech_fetch as fs


# feed 样本：含主席/副主席/理事，故意乱序，断言取最新主席条（排除 Vice Chair）
_ENTRIES = [
    {"d": "6/6/2026 12:00:00 PM", "t": "Dereg", "s": "Governor Michael S. Barr",
     "l": "/newsevents/speech/barr20260606a.htm"},
    {"d": "3/21/2026 1:30:00 PM", "t": "Acceptance Remarks", "s": "Chair Jerome H. Powell",
     "l": "/newsevents/speech/powell20260321a.htm"},
    {"d": "5/31/2026 9:00:00 AM", "t": "Outlook", "s": "Vice Chair Philip N. Jefferson",
     "l": "/newsevents/speech/jefferson20260531a.htm"},
    {"d": "1/11/2026 7:30:00 PM", "t": "Statement", "s": "Chair Jerome H. Powell",
     "l": "/newsevents/speech/powell20260111a.htm"},
]


def test_pick_latest_chair_excludes_vice_and_takes_newest():
    e = fs.pick_latest_chair(_ENTRIES)
    assert e is not None
    assert e["s"] == "Chair Jerome H. Powell"
    assert e["l"] == "/newsevents/speech/powell20260321a.htm"   # 3/21 > 1/11，且排除 5/31 Vice Chair


def test_pick_latest_chair_none_when_no_chair():
    only_others = [e for e in _ENTRIES if "Chair" not in e["s"] or "Vice" in e["s"]]
    assert fs.pick_latest_chair(only_others) is None


def test_extract_body_strips_tags_and_footer():
    html = ("<html><body><p>The economy remains resilient and inflation eased.</p>"
            "<div>Last Update: June 01, 2026</div></body></html>")
    body = fs._extract_body(html)
    assert "economy remains resilient" in body
    assert "Last Update" not in body


def test_extract_body_not_truncated_by_header_phrase():
    """真实 Fed 页：页头 banner 含 'Board of Governors...'，不得当作正文结尾把正文切掉。
    正文在 id=article 容器内，页头/导航样板须被锚点跳过，真 footer 'Last Update:' 截断。"""
    html = (
        "<header><span>Board of Governors of the Federal Reserve System</span></header>"
        "<nav>Skip to main content Back to Home</nav>"
        '<div id="article"><h3>Acceptance Remarks</h3>'
        "<p>Good morning. Inflation has eased and policy is well positioned.</p>"
        "<p>Thank you again for this honor.</p></div>"
        "<div>Last Update: March 21, 2026</div>"
    )
    body = fs._extract_body(html)
    assert "Good morning" in body
    assert "policy is well positioned" in body
    assert "Thank you again" in body
    assert "Skip to main content" not in body   # 页头/导航样板被锚点跳过
    assert "Last Update" not in body            # 真 footer 截断
    assert 'id="article"' not in body           # 锚点切在开标签之后，不留属性残迹


def test_extract_body_drops_video_player_boilerplate():
    """视频讲话页的 sr-only 键盘帮助块（'Accessible Keys for Video...'）须被剥除——
    Fed 实际结构：正文容器内 <div class="sr-only"><p><strong>...</strong></p>...</div>。"""
    html = (
        '<div id="article"><h3>Remarks</h3>'
        '<div class="sr-only"><p><strong>Accessible Keys for Video</strong></p>'
        "<p>[Space Bar] toggles play/pause;</p>"
        "<p>[Tab] navigate, caption on/off.</p></div>"
        "<p>The labor market remains solid and inflation is near target.</p></div>"
        "<div>Last Update: June 1, 2026</div>"
    )
    body = fs._extract_body(html)
    assert "labor market remains solid" in body
    assert "Accessible Keys for Video" not in body
    assert "toggles play/pause" not in body


import json
import pytest
from prism.scripts import macro_registry as reg


class _FakeResp:
    def __init__(self, *, text=None, content=None):
        self.text = text or ""
        self.content = content if content is not None else (text or "").encode()
    def raise_for_status(self):
        pass


class _FakeClient:
    """feed URL 返回 JSON（带 BOM），讲话页返回 HTML。"""
    def __init__(self, entries, speech_html):
        self._feed = ("﻿" + json.dumps(entries)).encode("utf-8")
        self._html = speech_html
    def get(self, url, **kw):
        if url.endswith(".json"):
            return _FakeResp(content=self._feed, text=self._feed.decode("utf-8-sig"))
        return _FakeResp(text=self._html)
    def close(self):
        pass


@pytest.fixture
def speech_topic(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path)
    monkeypatch.setattr(fs, "_PRISM_ROOT", tmp_path)
    slug, variant = "t-macro", "opus4.8"
    reg.create_registry(slug, variant)
    reg.upsert_input(slug, variant, {
        "name": fs._INPUT_NAME, "tier": "A", "cadence_type": "policy",
        "targets": ["rates"], "mechanism": "CD", "importance": "confirming",
        "causal_sentence": "x→y→z。", "availability": "llm",
        "stance_scale": "hawk_dove", "text_fetch": "fed_speech",
    })
    return slug, variant


def test_fetch_fed_speech_writes_cache_and_sets_path(speech_topic, tmp_path):
    slug, variant = speech_topic
    html = "<html><body><p>Policy is well positioned; inflation eased.</p></body></html>"
    res = fs.fetch_fed_speech(slug, variant, client=_FakeClient(_ENTRIES, html))
    assert res["ok"]
    assert res["fingerprint"] == "/newsevents/speech/powell20260321a.htm"
    cache = tmp_path / "topics" / slug / "inbox" / "fed_speech_latest.md"
    assert cache.exists() and "inflation eased" in cache.read_text(encoding="utf-8")
    entry = next(e for e in reg.read_registry(slug, variant)["inputs"]
                 if e["name"] == fs._INPUT_NAME)
    assert entry["local_cache_path"].endswith("fed_speech_latest.md")


def test_fetch_one_routes_with_entry_name(speech_topic):
    slug, variant = speech_topic
    entry = {"name": fs._INPUT_NAME, "text_fetch": "fed_speech"}
    res = fs.fetch_one(slug, variant, entry,
                       client=_FakeClient(_ENTRIES, "<p>hawkish tone</p>"))
    assert res["ok"] and res["speaker"] == "Chair Jerome H. Powell"

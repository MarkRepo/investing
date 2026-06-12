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

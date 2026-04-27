"""Plan 5 T7: fidelity rule tolerates lossy preprocess by softening wording."""
from scripts import ingest_qa


def _claim(quote: str) -> dict:
    return {"evidence": [{"text": quote, "type": "primary"}], "subject_tag": "x"}


def test_fidelity_substring_match_suppresses_warning():
    haystack = "x" * 30_000 + "鼎龙股份 CMP 业务 2024 年营收 15 亿元" + "y" * 5_000
    warnings = ingest_qa.check_evidence_fidelity(
        [_claim("鼎龙股份 CMP 业务 2024 年营收 15 亿元")],
        haystack,
    )
    assert warnings == []


def test_fidelity_head_40_chars_match_suppresses_warning():
    # Full quote has a tail that's NOT in haystack; but the first 40 normalized
    # chars are (confirming the existing 40-char fallback still works).
    shared = "鼎龙股份在2024年CMP业务营收15亿元全球市占率领先业务持续扩张进入先进制程"
    haystack = "x" * 30_000 + shared + "y" * 5_000
    quote = shared + "，补充信息这段文字完全不在 haystack 里面"
    warnings = ingest_qa.check_evidence_fidelity([_claim(quote)], haystack)
    assert warnings == []


def test_fidelity_short_preprocess_softens_detail():
    haystack = "只有 100 字左右的 preprocess 内容"  # << 25K threshold
    quote = "安集科技 2024 年营收 15.5 亿元，全球市占率 11%"
    warnings = ingest_qa.check_evidence_fidelity([_claim(quote)], haystack)
    assert len(warnings) == 1
    assert "偏短" in warnings[0]["detail"]
    assert "PDF→text 损失" in warnings[0]["detail"]


def test_fidelity_full_preprocess_uses_original_wording():
    haystack = "x" * 30_000 + "some unrelated text"
    quote = "missing quote that is definitely not in the haystack at all"
    warnings = ingest_qa.check_evidence_fidelity([_claim(quote)], haystack)
    assert len(warnings) == 1
    assert "偏短" not in warnings[0]["detail"]
    assert "找不到" in warnings[0]["detail"]

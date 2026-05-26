"""H3 v2 回归 — short_name + search_terms 强约束 + 不做关键词提取。

H3 v2 设计：
- create_topic 强制要求 short_name（company）+ search_terms（长 question）
- 脚本不做关键词提取（删除标点截断），让 LLM 在创建时显式提炼
- _short_scope_query 优先级：search_terms > 短 question > short_name 兜底
"""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts.topic import create_topic, set_thesis
from prism.scripts.web_prescan import build_search_queries, _short_scope_query
from prism.scripts.manifest import create_manifest

VARIANT = "v"


@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.outputs._PRISM_ROOT", tmpdir)
    yield tmpdir
    shutil.rmtree(tmpdir)


def _create(slug, **kwargs):
    """company 默认 fixture — 预填 ticker + short_name + 短 question。"""
    defaults = dict(
        slug=slug, display_name="X", topic_type="company",
        question="Q?", geo="CN", depth="quick", variant=VARIANT,
        ticker="SSE_688331",
        short_name="X",
    )
    defaults.update(kwargs)
    create_topic(**defaults)
    create_manifest(slug, VARIANT)


# ---------------------------------------------------------------------------
# _short_scope_query 单元测试（v2 — 4 参数签名，不再做关键词提取）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("display_name,short_name,question,terms,expected_max,expected_contains", [
    # search_terms 优先 — 用 short_name + terms（不读 question）
    ("荣昌生物 (RemeGen, SSE 688331)", "荣昌生物", "极长废话题问题问题问题问题",
     ["ADC 商业化", "BD 海外授权", "IgAN 管线"], 40, "ADC 商业化"),
    # 短 question + 无 terms → short_name + question
    ("X (Foo, US_X)", "宁德时代", "动力电池前景如何", None, 40, "动力电池前景如何"),
    # 长 question + 无 terms → short_name 兜底（不再切 question）
    ("Y (Bar, US_Y)", "荣昌生物",
     "长长长长长长长长长长长长长长长长长长长长长长长长长长", None, 40, "荣昌生物"),
    # search_terms 多于 3 个 — 只取前 3
    ("X", "宁德", "Q", ["a", "b", "c", "d", "e"], 40, "a b c"),
    # short_name 缺失 → fall back display_name（向后兼容老 yaml）
    ("中国宠物行业", None, "Q", None, 40, "中国宠物行业"),
])
def test_short_scope_query(display_name, short_name, question, terms, expected_max, expected_contains):
    out = _short_scope_query(display_name, short_name, question, terms)
    assert len(out) <= expected_max, f"got {len(out)} chars: {out!r}"
    assert expected_contains in out
    # 不能以噪点结尾
    assert not out.endswith(("，", "。", "；", "：", "、", " "))


def test_short_scope_query_uses_short_name_not_display_name(tmp_topic):
    """实战核心：scope query 用 short_name 而非长 display_name。"""
    out = _short_scope_query(
        display_name="荣昌生物 (RemeGen, SSE 688331)",  # 30 字
        short_name="荣昌生物",                              # 4 字
        question="Q",
        search_terms=["ADC 商业化兑现", "BD 海外授权回流", "IgAN 自免管线"],
    )
    assert "(RemeGen, SSE" not in out, f"不该用 display_name: {out!r}"
    assert "荣昌生物" in out
    assert "ADC 商业化兑现" in out
    assert "BD 海外授权回流" in out
    assert "IgAN 自免管线" in out


def test_short_scope_query_does_not_truncate_question(tmp_topic):
    """v2 关键变更：不再用标点切 question 假装提炼关键词。"""
    long_q = "ADC+自免双管线创新药企业的商业化兑现节奏与BD海外授权回流"  # 30 字
    out = _short_scope_query("X", "荣昌", long_q, search_terms=None)
    # 兜底应该回到 short_name 而非切 question 前 20 字
    assert out == "荣昌"


# ---------------------------------------------------------------------------
# build_search_queries 集成测试 — short_name 优先
# ---------------------------------------------------------------------------

def test_h3v2_company_uses_short_name_in_all_query_kinds(tmp_topic):
    _create(
        slug="rongchang", display_name="荣昌生物 (RemeGen, SSE 688331)",
        short_name="荣昌生物",
        question="Q",
        ticker="SSE_688331",
        search_terms=["ADC 商业化", "BD 授权", "IgAN"],
    )
    qs = build_search_queries("rongchang", VARIANT)
    for q in qs:
        # display_name 30 字组件不应出现在任何 query 里
        assert "(RemeGen, SSE 688331)" not in q["query"], (
            f"[{q['kind']}] 仍含长 display_name: {q['query']!r}"
        )
        assert "荣昌生物" in q["query"], f"[{q['kind']}] 缺 short_name: {q['query']!r}"
        assert len(q["query"]) <= 40, f"[{q['kind']}] 仍超长 ({len(q['query'])} 字): {q['query']!r}"


def test_h3v2_legacy_yaml_without_short_name_still_works(tmp_topic, monkeypatch):
    """老 yaml 没 short_name 字段 → 向后兼容兜底用 display_name。"""
    # 模拟老 yaml：直接写文件绕过 create_topic gate
    import yaml
    topic_dir = tmp_topic / "topics" / "legacy" / VARIANT
    topic_dir.mkdir(parents=True)
    (topic_dir / "topic.yaml").write_text(yaml.dump({
        "slug": "legacy",
        "display_name": "中国宠物行业",
        "type": "industry",
        "stage": "00-init",
        "scope": {"geo": "CN", "question": "Q", "depth": "deep"},  # 无 short_name
        "outputs_state": {},
    }, allow_unicode=True), encoding="utf-8")
    create_manifest("legacy", VARIANT)
    qs = build_search_queries("legacy", VARIANT)
    # 不 raise，正常生成 query
    assert qs
    scope_q = next(q for q in qs if q["kind"] == "scope")
    assert "中国宠物行业" in scope_q["query"]


def test_h3v2_killer_question_uses_short_name(tmp_topic):
    _create(
        slug="rc-k", display_name="X (Y, US_X)",
        short_name="荣昌生物",
        question="Q",
        ticker="SSE_688331",
    )
    topic_dir = tmp_topic / "topics" / "rc-k" / VARIANT
    (topic_dir / "thesis_v1.md").write_text(
        "# Thesis v1\n\n- K1: ADC 商业化\n- K2: BD\n", encoding="utf-8",
    )
    set_thesis("rc-k", VARIANT, version=1, summary="t1", stage_set_at="01-roadmap")

    qs = build_search_queries("rc-k", VARIANT)
    kq = [q for q in qs if q["kind"] == "killer-question"]
    assert len(kq) >= 1
    for q in kq:
        assert q["query"].startswith("荣昌生物 K"), f"格式不对: {q['query']!r}"
        assert "(Y, US_X)" not in q["query"]


# ---------------------------------------------------------------------------
# create_topic gate — short_name + search_terms 必填条件
# ---------------------------------------------------------------------------

def test_company_without_short_name_raises(tmp_topic):
    with pytest.raises(ValueError, match="必须传 short_name"):
        create_topic(
            slug="no-short", display_name="X (Y, Z)", topic_type="company",
            question="Q?", geo="CN", depth="quick", variant=VARIANT,
            ticker="SSE_688331",
            # 缺 short_name
        )


def test_short_name_too_long_raises(tmp_topic):
    with pytest.raises(ValueError, match="≤12 字"):
        _create(slug="long-name", short_name="超过十二个字的主体名称肯定不行")


def test_short_name_empty_raises(tmp_topic):
    with pytest.raises(ValueError, match="非空 str"):
        _create(slug="empty-name", short_name="   ")


def test_long_question_without_search_terms_raises(tmp_topic):
    """v2 hard gate：长 question + 缺 search_terms → 立即 raise。"""
    long_q = "荣昌生物作为中国领先的ADC+自免双管线创新药企业，全维度覆盖商业化兑现与海外授权"
    assert len(long_q) > 25
    with pytest.raises(ValueError, match="search_terms 未给"):
        _create(slug="long-q-no-terms", question=long_q)


def test_long_question_with_search_terms_ok(tmp_topic):
    long_q = "荣昌生物作为中国领先的ADC+自免双管线创新药企业，全维度覆盖商业化兑现与海外授权"
    _create(
        slug="long-q-ok", question=long_q,
        search_terms=["ADC 商业化", "BD 授权"],
    )


def test_short_question_no_search_terms_ok(tmp_topic):
    """≤25 字 question 不必给 search_terms。"""
    _create(slug="short-q", question="ADC 商业化兑现节奏？")


# ---------------------------------------------------------------------------
# industry / arena / concept 不必传 short_name
# ---------------------------------------------------------------------------

def test_industry_without_short_name_ok(tmp_topic):
    """industry 不强制 short_name（可选），漏给时 build 用 display_name 兜底。"""
    create_topic(
        slug="cn-pet", display_name="中国宠物", topic_type="industry",
        question="Q?", geo="CN", depth="deep", variant=VARIANT,
    )
    create_manifest("cn-pet", VARIANT)
    qs = build_search_queries("cn-pet", VARIANT)
    scope_q = next(q for q in qs if q["kind"] == "scope")
    assert "中国宠物" in scope_q["query"]

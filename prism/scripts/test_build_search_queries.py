"""build_search_queries 槽位枚举器回归（A 方案 / PRISM_VALIDATION F3 修复）。

设计变更：
- build_search_queries 不再拼 query 文本，只枚举"覆盖槽"——每槽 {addresses, kind,
  recency_days, hint}，NO 'query' 键。query 措辞交给对话里的主 agent（feedback_llm_workflow）。
- 因此本文件断言的是：槽位完备枚举 + addresses 绑定 + hint 携带原始素材 +
  **不再有任何写死的领域后缀**（F3 病根：旧版对所有 industry 套死"产能变化"）。
- create_topic 的 short_name / search_terms 强制 gate 不变（独立于 query 契约），保留其回归。
"""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts.topic import create_topic, set_thesis
from prism.scripts.web_prescan import build_search_queries
from prism.scripts.manifest import create_manifest

VARIANT = "v"

# F3 病根：旧版写死在脚本里的领域后缀。新契约下这些词不该出现在任何槽里
# （查询轴改由主 agent 按领域自定）。本集合用作回归护栏。
_FORBIDDEN_HARDCODED_SUFFIXES = (
    "产能变化", "行业政策", "技术突破", "龙头新闻",
    "最新公告", "监管处罚", "业绩预告", "高管变动", "最新进展",
)


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


def _assert_slot_shape(slot, recency=90):
    """每个槽的契约：有 addresses/kind/recency_days/hint，NO query。"""
    assert set(slot) == {"addresses", "kind", "recency_days", "hint"}, slot
    assert "query" not in slot, f"槽不该再带 query 文本: {slot!r}"
    assert isinstance(slot["addresses"], list) and slot["addresses"]
    assert isinstance(slot["hint"], dict)
    assert slot["recency_days"] == recency


def _no_hardcoded_suffix(slots):
    """F3 回归护栏：整个返回结构里不得出现任何写死的领域后缀词。"""
    blob = repr(slots)
    for w in _FORBIDDEN_HARDCODED_SUFFIXES:
        assert w not in blob, f"写死后缀 {w!r} 复活了（F3 回归）: {blob}"


# ---------------------------------------------------------------------------
# 契约：槽位形状 + 无 query 键 + 无写死后缀
# ---------------------------------------------------------------------------

def test_every_slot_has_no_query_key_and_correct_shape(tmp_topic):
    _create(
        slug="rc", display_name="荣昌生物 (RemeGen, SSE 688331)",
        short_name="荣昌生物", question="Q", ticker="SSE_688331",
        search_terms=["ADC 商业化", "BD 授权", "IgAN"],
    )
    slots = build_search_queries("rc", VARIANT, recency_days=45)
    assert slots
    for s in slots:
        _assert_slot_shape(s, recency=45)


def test_no_hardcoded_domain_suffix_anywhere(tmp_topic):
    """F3 本体：industry 槽不再带'产能变化'等任何写死轴词。"""
    create_topic(
        slug="cn-drug", display_name="中国创新药", topic_type="industry",
        question="创新药出海与医保格局如何", geo="CN", depth="deep", variant=VARIANT,
        search_terms=["创新药 出海", "ADC 双抗", "医保谈判"],
    )
    create_manifest("cn-drug", VARIANT)
    slots = build_search_queries("cn-drug", VARIANT)
    _no_hardcoded_suffix(slots)


# ---------------------------------------------------------------------------
# scope 槽 — 任何 topic 都有，hint 携带原始素材
# ---------------------------------------------------------------------------

def test_scope_slot_always_present_with_raw_hint(tmp_topic):
    _create(
        slug="rc2", display_name="荣昌生物 (RemeGen, SSE 688331)",
        short_name="荣昌生物", question="Q",
        search_terms=["ADC 商业化", "BD 授权", "IgAN"],
    )
    slots = build_search_queries("rc2", VARIANT)
    scope = [s for s in slots if s["kind"] == "scope"]
    assert len(scope) == 1
    h = scope[0]["hint"]
    # hint 原样给原料，不预拼、不截断
    assert h["short_name"] == "荣昌生物"
    assert h["display_name"] == "荣昌生物 (RemeGen, SSE 688331)"
    assert h["search_terms"] == ["ADC 商业化", "BD 授权", "IgAN"]
    assert scope[0]["addresses"] == ["scope"]


def test_legacy_yaml_without_short_name_still_enumerates(tmp_topic):
    """老 yaml 无 short_name → scope hint 的 short_name=None，display_name 兜底，不 raise。"""
    import yaml
    topic_dir = tmp_topic / "topics" / "legacy" / VARIANT
    topic_dir.mkdir(parents=True)
    (topic_dir / "topic.yaml").write_text(yaml.dump({
        "slug": "legacy", "display_name": "中国宠物行业", "type": "industry",
        "stage": "00-init",
        "scope": {"geo": "CN", "question": "Q", "depth": "deep"},  # 无 short_name
        "outputs_state": {},
    }, allow_unicode=True), encoding="utf-8")
    create_manifest("legacy", VARIANT)
    slots = build_search_queries("legacy", VARIANT)
    scope = next(s for s in slots if s["kind"] == "scope")
    assert scope["hint"]["short_name"] is None
    assert scope["hint"]["display_name"] == "中国宠物行业"


# ---------------------------------------------------------------------------
# company-event 槽 — 仅 company + ticker，hint 给 name+ticker（短码）
# ---------------------------------------------------------------------------

def test_company_event_slot_carries_short_ticker(tmp_topic):
    _create(slug="rc3", short_name="荣昌生物", ticker="SSE_688331")
    slots = build_search_queries("rc3", VARIANT)
    ce = [s for s in slots if s["kind"] == "company-event"]
    assert len(ce) == 1
    assert ce[0]["hint"] == {"name": "荣昌生物", "ticker": "688331"}  # 去交易所前缀


def test_industry_has_no_company_event_slot(tmp_topic):
    create_topic(
        slug="ind1", display_name="中国宠物", topic_type="industry",
        question="Q?", geo="CN", depth="deep", variant=VARIANT,
    )
    create_manifest("ind1", VARIANT)
    slots = build_search_queries("ind1", VARIANT)
    assert not [s for s in slots if s["kind"] == "company-event"]


# ---------------------------------------------------------------------------
# industry-event 槽 — base_terms 来自 search_terms[:2]，无则 display_name 兜底
# ---------------------------------------------------------------------------

def test_industry_event_base_terms_from_search_terms(tmp_topic):
    create_topic(
        slug="g-hvdc", display_name="跨州跨国 HVDC 输电（Prysmian/国电南瑞/特变电工）",
        topic_type="arena",
        question="跨州跨国 HVDC 输电的瓶颈与受益标的是什么", geo="GLOBAL", depth="deep",
        variant=VARIANT,
        search_terms=["HVDC 高压直流", "特高压输电", "海底电缆", "电网升级"],
    )
    create_manifest("g-hvdc", VARIANT)
    slots = build_search_queries("g-hvdc", VARIANT)
    ev = [s for s in slots if s["kind"] == "industry-event"]
    assert len(ev) == 1
    # 取前 2 个 search_term，贪心 display_name 不进 hint
    assert ev[0]["hint"]["base_terms"] == ["HVDC 高压直流", "特高压输电"]


def test_industry_event_base_terms_fallback_without_search_terms(tmp_topic):
    create_topic(
        slug="cn-pet2", display_name="中国宠物", topic_type="industry",
        question="Q?", geo="CN", depth="deep", variant=VARIANT,
    )
    create_manifest("cn-pet2", VARIANT)
    slots = build_search_queries("cn-pet2", VARIANT)
    ev = next(s for s in slots if s["kind"] == "industry-event")
    assert ev["hint"]["base_terms"] == ["中国宠物"]


# ---------------------------------------------------------------------------
# concept 槽 — 每个 concept 一槽（≤3）
# ---------------------------------------------------------------------------

def test_concept_slots_one_per_concept(tmp_topic):
    import yaml
    topic_dir = tmp_topic / "topics" / "cpt" / VARIANT
    topic_dir.mkdir(parents=True)
    (topic_dir / "topic.yaml").write_text(yaml.dump({
        "slug": "cpt", "display_name": "某主题", "type": "concept",
        "stage": "00-init",
        "scope": {"geo": "CN", "question": "Q", "depth": "quick"},
        "concepts": ["固态电池", "钠离子电池", "钙钛矿", "氢能"],  # 4 个，应只取前 3
        "outputs_state": {},
    }, allow_unicode=True), encoding="utf-8")
    create_manifest("cpt", VARIANT)
    slots = build_search_queries("cpt", VARIANT)
    cu = [s for s in slots if s["kind"] == "concept-update"]
    assert len(cu) == 3
    assert [s["hint"]["concept"] for s in cu] == ["固态电池", "钠离子电池", "钙钛矿"]


# ---------------------------------------------------------------------------
# l4-hunting 槽 — 逐条 K# 对齐；缺 search_keywords 也出槽（修覆盖漏洞）
# ---------------------------------------------------------------------------

def test_l4_slot_per_entry_with_keywords(tmp_topic):
    import yaml
    _create(slug="rc-l4", short_name="荣昌生物", ticker="SSE_688331")
    topic_dir = tmp_topic / "topics" / "rc-l4" / VARIANT
    (topic_dir / "roadmap.yaml").write_text(yaml.dump({
        "learning_track": {"l4_hunting": [
            {
                "question": "AbbVie RC148 全球 III 期 2026Q3-Q4 能否宣布注册？",
                "addresses": ["K1"],
                "search_keywords": ["RC148 III 期", "AbbVie 注册", "PD-1 VEGF"],
            },
            {
                "question": "国谈降价幅度",
                "addresses": ["K2"],
                "search_keywords": ["医保谈判 降价"],
            },
        ]},
    }, allow_unicode=True), encoding="utf-8")

    slots = build_search_queries("rc-l4", VARIANT)
    l4 = [s for s in slots if s["kind"] == "l4-hunting"]
    assert len(l4) == 2
    first = l4[0]
    assert first["addresses"] == ["K1"]
    assert first["hint"]["search_keywords"] == ["RC148 III 期", "AbbVie 注册", "PD-1 VEGF"]
    assert "AbbVie RC148" in first["hint"]["question"]
    assert first["hint"]["name"] == "荣昌生物"


def test_l4_slot_emitted_even_without_search_keywords(tmp_topic):
    """新行为（修覆盖漏洞）：旧版缺 search_keywords 整槽跳过 → 漏覆盖该 K#；
    现统一出槽（带 question + 空 keywords），addresses 绑定保留，主 agent 自行措辞。"""
    import yaml
    _create(slug="rc-l4-nokw", short_name="荣昌", ticker="SSE_688331")
    topic_dir = tmp_topic / "topics" / "rc-l4-nokw" / VARIANT
    (topic_dir / "roadmap.yaml").write_text(yaml.dump({
        "learning_track": {"l4_hunting": [
            {"question": "某无关键词的 L4 问题", "addresses": ["K3"]},  # 缺 search_keywords
            {"question": "另一个", "addresses": ["K4"], "search_keywords": []},  # 空
        ]},
    }, allow_unicode=True), encoding="utf-8")

    slots = build_search_queries("rc-l4-nokw", VARIANT)
    l4 = [s for s in slots if s["kind"] == "l4-hunting"]
    assert len(l4) == 2, "缺/空 search_keywords 仍应出槽（不再静默丢覆盖）"
    assert l4[0]["addresses"] == ["K3"]
    assert l4[0]["hint"]["search_keywords"] == []
    assert l4[0]["hint"]["question"] == "某无关键词的 L4 问题"
    assert l4[1]["addresses"] == ["K4"]


def test_no_killer_question_kind(tmp_topic):
    """H3 v3 起 killer-question kind 已删；K# 覆盖经 l4-hunting addresses 绑定。"""
    _create(slug="rc-k", short_name="荣昌生物", ticker="SSE_688331")
    topic_dir = tmp_topic / "topics" / "rc-k" / VARIANT
    (topic_dir / "thesis_v1.md").write_text(
        "# Thesis v1\n\n- K1: ADC 商业化\n- K2: BD\n", encoding="utf-8",
    )
    set_thesis("rc-k", VARIANT, version=1, summary="t1", stage_set_at="01-roadmap")
    slots = build_search_queries("rc-k", VARIANT)
    assert not [s for s in slots if s["kind"] == "killer-question"]


# ---------------------------------------------------------------------------
# create_topic gate — short_name + search_terms 必填（独立于 query 契约，保留）
# ---------------------------------------------------------------------------

def test_company_without_short_name_raises(tmp_topic):
    with pytest.raises(ValueError, match="必须传 short_name"):
        create_topic(
            slug="no-short", display_name="X (Y, Z)", topic_type="company",
            question="Q?", geo="CN", depth="quick", variant=VARIANT,
            ticker="SSE_688331",
        )


def test_short_name_too_long_raises(tmp_topic):
    with pytest.raises(ValueError, match="≤12 字"):
        _create(slug="long-name", short_name="超过十二个字的主体名称肯定不行")


def test_short_name_empty_raises(tmp_topic):
    with pytest.raises(ValueError, match="非空 str"):
        _create(slug="empty-name", short_name="   ")


def test_long_question_without_search_terms_raises(tmp_topic):
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
    _create(slug="short-q", question="ADC 商业化兑现节奏？")


def test_industry_without_short_name_ok(tmp_topic):
    create_topic(
        slug="cn-pet", display_name="中国宠物", topic_type="industry",
        question="Q?", geo="CN", depth="deep", variant=VARIANT,
    )
    create_manifest("cn-pet", VARIANT)
    slots = build_search_queries("cn-pet", VARIANT)
    scope = next(s for s in slots if s["kind"] == "scope")
    assert scope["hint"]["display_name"] == "中国宠物"

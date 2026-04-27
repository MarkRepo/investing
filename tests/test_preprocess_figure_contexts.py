from pathlib import Path
import pytest

from scripts import preprocess_report as pre


SAMPLE = """
一、市场空间

CMP 抛光材料是半导体制造关键耗材。

图表1: 2020-2030 全球 CMP 抛光材料市场规模（亿美元）
数据来源：华经产业研究院

如图表1所示，2025 年市场规模 33.8 亿美元，CAGR 9.0%。

二、竞争格局

Figure 2. Global CMP slurry market share, 2024
Source: Market Growth Reports

Dupont holds 75% of the pad market. The top 6 vendors account for 85%.

表 3：CMP 抛光液成本结构
磨料占 54.6%，化学添加剂占 20.1%。
"""


def test_extract_figure_contexts_matches_chinese_and_english():
    contexts = pre.extract_figure_contexts(SAMPLE, sections=[
        {"name": "market_size", "text": SAMPLE.split("二、竞争格局")[0], "order": 1},
        {"name": "competition", "text": "二、竞争格局" + SAMPLE.split("二、竞争格局")[1], "order": 2},
    ])
    captions = [c["caption"] for c in contexts]
    assert any("图表1" in c for c in captions)
    assert any(c.startswith("Figure 2") for c in captions)
    assert any("表 3" in c for c in captions)


def test_figure_context_has_required_fields():
    contexts = pre.extract_figure_contexts(SAMPLE, sections=[
        {"name": "market_size", "text": SAMPLE, "order": 1}
    ])
    for c in contexts:
        for key in ("id", "page", "caption", "surrounding_text", "section_name"):
            assert key in c


def test_surrounding_text_includes_context_around_caption():
    contexts = pre.extract_figure_contexts(SAMPLE, sections=[
        {"name": "market_size", "text": SAMPLE, "order": 1}
    ])
    fig1 = [c for c in contexts if "图表1" in c["caption"]][0]
    # surrounding_text should pull in the "CAGR 9.0%" line downstream
    assert "33.8" in fig1["surrounding_text"] or "CAGR" in fig1["surrounding_text"]


def test_section_name_attribution():
    contexts = pre.extract_figure_contexts(SAMPLE, sections=[
        {"name": "market_size", "text": SAMPLE.split("二、竞争格局")[0], "order": 1},
        {"name": "competition", "text": "二、竞争格局" + SAMPLE.split("二、竞争格局")[1], "order": 2},
    ])
    fig_cn_1 = [c for c in contexts if "图表1" in c["caption"]][0]
    assert fig_cn_1["section_name"] == "market_size"
    fig_en_2 = [c for c in contexts if c["caption"].startswith("Figure 2")][0]
    assert fig_en_2["section_name"] == "competition"


def test_toc_entries_not_emitted_as_figures():
    """Plan 5 T6: PDF TOC lines like '图表1：CMP 工作原理 ........... 4' must
    not leak into figure_contexts as real figures."""
    toc_sample = """
1.1 市场概况 ...................................... 3

图表1：CMP 工作原理 ................................ 4

图表20：鼎龙股份 CMP 环节核心产品布局 ............... 10

正文开始

图表 5：2017~2023 年中国 CMP 抛光液市场
数据来源：华经产业研究院
"""
    contexts = pre.extract_figure_contexts(toc_sample, sections=[
        {"name": "body", "text": toc_sample, "order": 1}
    ])
    captions = [c["caption"] for c in contexts]
    # Only the real caption (no trailing dots+page) survives
    assert any("图表 5" in c or "图表5" in c for c in captions)
    assert not any("工作原理" in c for c in captions)
    assert not any("鼎龙股份" in c for c in captions)


def test_toc_heading_marks_section_skip():
    """Plan 5 T6: apply_skip_rules skips sections whose heading is a TOC entry."""
    sections = [
        {"name": "UNKNOWN_1",
         "heading_raw": "1.1 化学机械抛光是实现晶圆全局平坦化的关键工艺 ...................... 4",
         "text": "content"},
        {"name": "UNKNOWN_2",
         "heading_raw": "4.1 安集科技为国内 CMP 抛光液龙头",
         "text": "content"},
        {"name": "HEADER", "heading_raw": "", "text": ""},
    ]
    template = {"skip_rules": {"sections": []}}
    result = pre.apply_skip_rules(sections, template)
    assert result[0]["action"] == "skip"
    assert result[0]["reason"].startswith("TOC")
    assert result[1]["action"] == "keep"  # real heading
    assert result[2]["action"] == "skip"  # HEADER

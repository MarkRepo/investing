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

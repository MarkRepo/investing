"""Plan 5 T10: figure_contexts coverage QA rule."""
from scripts import ingest_qa


def _fig(caption: str) -> dict:
    return {"caption": caption, "section_name": "x", "source_id": "s"}


def _fact(value: float | None) -> dict:
    return {"value_numeric": value, "target_layer": "industry"}


def test_coverage_ok_when_ratio_above_threshold():
    figures = [_fig("图1：CMP 市场 2024 达 30 亿")] * 5
    facts = [_fact(30.0)] * 2  # 2/5 = 0.40 > 0.30
    assert ingest_qa.check_figure_context_coverage(facts, figures) == []


def test_coverage_warns_when_ratio_below_threshold():
    # Mirrors CMP dry-run: many numeric captions, few observations.
    figures = [_fig(f"图{i}：市场规模 {i} 亿") for i in range(1, 11)]  # 10
    facts = [_fact(1.0), _fact(2.0)]  # 2/10 = 0.20 < 0.30
    warnings = ingest_qa.check_figure_context_coverage(facts, figures)
    assert len(warnings) == 1
    assert warnings[0]["rule"] == "figure_coverage_low"
    assert "0.20" in warnings[0]["detail"]
    assert "10" in warnings[0]["detail"]


def test_coverage_silent_when_no_digit_bearing_captions():
    """Captions without any digits aren't counted — they may be descriptive
    figures (diagrams, flowcharts) not quantitative data."""
    figures = [_fig("图A：CMP 工作原理"), _fig("图B：产业链结构")]
    facts = []
    assert ingest_qa.check_figure_context_coverage(facts, figures) == []


def test_coverage_silent_with_zero_figures():
    assert ingest_qa.check_figure_context_coverage([_fact(1.0)], []) == []
    assert ingest_qa.check_figure_context_coverage([], []) == []


def test_coverage_ignores_narrative_only_facts():
    """Facts with value_numeric=None (narrative-only) don't count toward
    numeric extraction — they wouldn't satisfy a data-rich figure."""
    figures = [_fig("图1：市场规模 30 亿")] * 4
    facts = [_fact(None)] * 10 + [_fact(1.0)]  # 1/4 = 0.25 < 0.30
    warnings = ingest_qa.check_figure_context_coverage(facts, figures)
    assert len(warnings) == 1


def test_coverage_custom_threshold():
    figures = [_fig("图1：2024 年 30 亿")] * 10
    facts = [_fact(1.0)] * 4  # 0.40
    # Stricter threshold 0.5 triggers warning at ratio=0.4
    warnings = ingest_qa.check_figure_context_coverage(
        facts, figures, ratio_threshold=0.5,
    )
    assert len(warnings) == 1

from pathlib import Path
import json
import pytest

from scripts import preprocess_report as pre


def test_template_map_includes_industry():
    assert ("a-share", "industry") in pre.TEMPLATE_MAP
    assert ("us", "industry") in pre.TEMPLATE_MAP


def test_load_template_industry(tmp_path):
    t = pre.load_template("a-share", "industry")
    assert t["form"] == "industry-research-a-share"


def test_cli_accepts_industry_type(tmp_path, monkeypatch, capsys):
    # Prepare a minimal md report file so the CLI path runs end-to-end.
    report = tmp_path / "sample.md"
    report.write_text(
        "��金证券\n2026 年 3 月 10 日\n\n# 中国 CMP 抛光材料行业深度\n\n"
        "一、市场空间\n\n2025 年市场规模约 33.8 亿美元。\n\n"
        "二、竞争格局\n\n龙头 Dupont 市占 75%。\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    rc = pre.main([str(report), "--type", "industry", "--market", "a-share", "--out", str(out)])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["meta"]["cli_type"] == "industry"
    # market_size and competition sections should be normalized
    names = [s["name"] for s in data["sections"]]
    assert "market_size" in names
    assert "competition" in names


def test_preprocess_industry_full_output_shape(tmp_path):
    report = tmp_path / "r.md"
    report.write_text(
        "国金证券\n2026 年 3 月 10 日\n\n"
        "摘要：中国 CMP 抛光材料行业深度。2025 年全球市场 33.8 亿美元。"
        "代表公司 安集(SSE 688019) / 鼎龙(SZ 300054)。\n\n"
        "一、市场空间\n\n"
        "图表1: 全球市场规模\n如图表1所示，2025 年市场规模 33.8 亿美元。\n\n"
        "二、竞争格局\n\nDupont 市占 75%。\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    rc = pre.main([str(report), "--type", "industry", "--market", "a-share", "--out", str(out)])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))

    # Required top-level keys
    for key in ("meta", "sections", "figure_contexts", "detected_tickers", "report_abstract"):
        assert key in data, f"missing top-level key: {key}"
    # industry type should NOT populate financial_line_rows
    assert data.get("financial_line_rows", []) == []

    # detected tickers
    markets = {t["market"] for t in data["detected_tickers"]}
    assert "SSE" in markets

    # figure_contexts present with at least 1 figure
    assert len(data["figure_contexts"]) >= 1
    fig = data["figure_contexts"][0]
    assert "caption" in fig
    assert "surrounding_text" in fig
    assert "section_name" in fig

    # report_abstract non-empty
    assert data["report_abstract"]

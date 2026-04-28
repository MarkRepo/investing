from pathlib import Path

from scripts import preprocess_report as pr


class FakePage:
    def __init__(self, text: str):
        self._text = text

    def get_text(self, mode: str) -> str:
        assert mode == "text"
        return self._text


class FakeDoc:
    def __init__(self, pages: list[FakePage]):
        self._pages = pages

    def __len__(self) -> int:
        return len(self._pages)

    def load_page(self, idx: int) -> FakePage:
        return self._pages[idx]


def test_build_page_signals_flags_low_text_and_chart_pages():
    doc = FakeDoc([
        FakePage("图1 储能装机 CAGR 30%\n2025E 100 2026E 130"),
        FakePage("短页"),
    ])

    pages = pr.build_page_signals(doc)

    assert [p["page"] for p in pages] == [1, 2]
    assert pages[0]["chart_heavy"] is True
    assert pages[0]["image_heavy"] is False
    assert pages[1]["text_quality"] == "low"


def test_collect_extraction_warnings_mentions_low_text_and_visual_pages():
    signals = [
        {"page": 1, "text_quality": "medium", "image_heavy": False, "chart_heavy": True, "table_heavy": False},
        {"page": 2, "text_quality": "low", "image_heavy": True, "chart_heavy": False, "table_heavy": False},
    ]

    warnings = pr.collect_extraction_warnings(signals)

    assert any("第 1 页" in w and "图表" in w for w in warnings)
    assert any("第 2 页" in w and "文本提取质量低" in w for w in warnings)

from pathlib import Path
import tempfile

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


def test_collect_extraction_warnings_flags_table_heavy_pages():
    """Test that table_heavy pages trigger extraction warnings."""
    signals = [
        {"page": 1, "text_quality": "high", "image_heavy": False, "chart_heavy": False, "table_heavy": True},
        {"page": 2, "text_quality": "medium", "image_heavy": False, "chart_heavy": False, "table_heavy": False},
    ]

    warnings = pr.collect_extraction_warnings(signals)

    assert len(warnings) == 1
    assert "第 1 页" in warnings[0]
    assert "表格密集" in warnings[0]


def test_build_page_signals_detects_table_markers():
    """Test that table markers (表, Table) are detected in pages."""
    doc = FakeDoc([
        FakePage("表1 财务数据\n2024年营收: 1000万元\n表2 成本构成"),
        FakePage("Table 5: Financial metrics\nRevenue in millions"),
        FakePage("这是一个普通页面 数据很少"),
    ])

    pages = pr.build_page_signals(doc)

    assert pages[0]["table_heavy"] is True
    assert pages[1]["table_heavy"] is True
    assert pages[2]["table_heavy"] is False


def test_build_result_wires_page_signals_and_warnings_for_pdf():
    """Test that build_result includes page_signals and extraction_warnings when doc is provided."""
    # Create a simple fake document
    doc = FakeDoc([
        FakePage("表 数据 Chart CAGR"),
        FakePage("x"),  # low text quality
    ])

    # Create minimal template and sections for build_result
    template = {
        "form": "test-form",
    }
    sections = [
        {
            "name": "Section1",
            "heading_raw": "Section 1",
            "order": 1,
            "text": "Some content here.",
            "action": "keep",
            "reason": None,
        }
    ]

    # Create a temporary test file to avoid file not found error
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_path = Path(f.name)
        f.write(b"test pdf content")

    try:
        result = pr.build_result(
            file_path=temp_path,
            market="a-share",
            form_cli="annual",
            template=template,
            sections=sections,
            text_full="表 数据 Chart CAGR\nx",
            doc=doc,
        )

        # Verify page_signals and extraction_warnings are in result
        assert "page_signals" in result
        assert "extraction_warnings" in result
        assert len(result["page_signals"]) == 2
        assert len(result["extraction_warnings"]) > 0

        # Verify warnings include table and low-text issues
        warning_text = " ".join(result["extraction_warnings"])
        assert "表格密集" in warning_text
        assert "文本提取质量低" in warning_text
    finally:
        temp_path.unlink()


def test_build_result_without_doc_returns_empty_signals_and_warnings():
    """Test that build_result handles non-PDF files (no doc parameter)."""
    template = {
        "form": "test-form",
    }
    sections = [
        {
            "name": "Section1",
            "heading_raw": "Section 1",
            "order": 1,
            "text": "Some content here.",
            "action": "keep",
            "reason": None,
        }
    ]

    # Create a temporary test file
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        temp_path = Path(f.name)
        f.write(b"Some text content")

    try:
        result = pr.build_result(
            file_path=temp_path,
            market="a-share",
            form_cli="annual",
            template=template,
            sections=sections,
            text_full="Some text content",
            doc=None,  # No document for non-PDF files
        )

        # Verify page_signals and extraction_warnings are empty
        assert result["page_signals"] == []
        assert result["extraction_warnings"] == []
    finally:
        temp_path.unlink()


def test_build_preprocess_output_includes_page_metadata():
    """Test that build_preprocess_output includes page_count, extracted_pages, and extraction_warnings."""
    doc = FakeDoc([
        FakePage("表 数据 Chart CAGR"),
        FakePage("x"),  # low text quality
    ])

    template = {
        "form": "test-form",
    }
    sections = [
        {
            "name": "Section1",
            "heading_raw": "Section 1",
            "order": 1,
            "text": "Some content here.",
            "action": "keep",
            "reason": None,
        }
    ]

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_path = Path(f.name)
        f.write(b"test pdf content")

    try:
        result = pr.build_result(
            file_path=temp_path,
            market="a-share",
            form_cli="annual",
            template=template,
            sections=sections,
            text_full="表 数据 Chart CAGR\nx",
            doc=doc,
        )

        # Build the preprocess output (CLI-style output)
        output = pr.build_preprocess_output(result, doc)

        # Assert the output includes required fields
        assert "page_count" in output
        assert "extracted_pages" in output
        assert "extraction_warnings" in output

        # Verify field values
        assert output["page_count"] == 2
        assert len(output["extracted_pages"]) == 2
        assert output["extracted_pages"][0]["page"] == 1
        assert output["extracted_pages"][1]["page"] == 2
        assert len(output["extraction_warnings"]) > 0
        assert any("表格密集" in w or "文本提取质量低" in w for w in output["extraction_warnings"])
    finally:
        temp_path.unlink()


def test_cli_output_includes_preprocess_metadata_for_pdf():
    """Test that CLI JSON output includes preprocess_metadata with page metrics."""

    doc = FakeDoc([
        FakePage("表 数据 Chart CAGR"),
        FakePage("x"),  # low text quality
    ])

    template = {
        "form": "test-form",
    }
    sections = [
        {
            "name": "Section1",
            "heading_raw": "Section 1",
            "order": 1,
            "text": "Some content here.",
            "action": "keep",
            "reason": None,
        }
    ]

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_path = Path(f.name)
        f.write(b"test pdf content")

    try:
        result = pr.build_result(
            file_path=temp_path,
            market="a-share",
            form_cli="annual",
            template=template,
            sections=sections,
            text_full="表 数据 Chart CAGR\nx",
            doc=doc,
        )

        # Build the final CLI output (as main() would do)
        output = pr.add_preprocess_metadata(result, doc)

        # Verify preprocess_metadata is the public page metadata location
        assert "preprocess_metadata" in output
        assert "page_signals" not in output
        assert "extraction_warnings" not in output
        assert output["meta"]["preprocess_version"] == "v2-phase1"
        meta = output["preprocess_metadata"]
        assert meta["page_count"] == 2
        assert len(meta["extracted_pages"]) == 2
        assert len(meta["extraction_warnings"]) > 0
    finally:
        temp_path.unlink()


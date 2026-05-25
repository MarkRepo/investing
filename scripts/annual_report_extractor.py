"""Extract investment-relevant sections from A-share annual report PDFs.

Strategy:
- Use PyMuPDF's built-in TOC to map section titles → page ranges
- Include only analysis-relevant sections; skip financials (covered by API)
- Output: flat markdown text with section headers, ready for LLM ingestion

Usage:
    python -m scripts.annual_report_extractor path/to/report.PDF
    python -m scripts.annual_report_extractor path/to/report.PDF --out extracted.md
    python -m scripts.annual_report_extractor path/to/report.PDF --sections all
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import NamedTuple

import pymupdf

log = logging.getLogger("annual_report_extractor")

# Sections to include — keyword match against section title
_INCLUDE_KEYWORDS = [
    "管理层讨论",
    "经营情况讨论",
    "主要业务",
    "主营业务",
    "经营模式",
    "行业情况",
    "核心竞争力",
    "风险因素",
    "主要经营情况",
    "未来发展",
    "展望",
    "重要事项",
    "公司业务概要",
    "研发情况",
    "业务和技术",
    "业务与技术",
    "发行人基本情况",
]

# Sections to always skip — even if they match include keywords
_SKIP_KEYWORDS = [
    "财务报告",
    "财务数据",
    "财务指标",
    "会计数据",
    "股份变动",
    "股东情况",
    "公司治理",
    "优先股",
    "债券",
    "环境",
    "社会责任",
    "释义",
    "董事、监事",
    "高级管理人员",
    "分季度",
    "非经常性损益",
]

# Q季报 TOC 关键词集（与年报分开，因为季报 TOC 短且章节命名不同）
_QUARTERLY_INCLUDE_KEYWORDS = [
    "主要财务数据",
    "经营数据",
    "经营情况",
    "股东信息",
    "其他重要事项",
    "重要事项",
]
_QUARTERLY_SKIP_KEYWORDS = [
    "季度财务报表",
    "审计报告",
    "财务报表",
]


def _is_quarterly_report(toc: list) -> bool:
    """季报特征：TOC 短（≤20 entries）且包含「季度财务报表」或「一、主要财务数据」"""
    if not toc or len(toc) > 20:
        return False
    titles = [t.replace(" ", "") for _, t, _ in toc]
    return any("季度财务报表" in t for t in titles) or any(
        t.startswith("一、主要财务数据") for t in titles
    )


class Section(NamedTuple):
    level: int
    title: str
    start_page: int   # 1-based (from PyMuPDF TOC)
    end_page: int     # inclusive, 1-based


def _should_include(title: str, quarterly: bool = False) -> bool:
    t = title.replace(" ", "")
    skip_kw = _QUARTERLY_SKIP_KEYWORDS if quarterly else _SKIP_KEYWORDS
    include_kw = _QUARTERLY_INCLUDE_KEYWORDS if quarterly else _INCLUDE_KEYWORDS
    if any(k in t for k in skip_kw):
        return False
    return any(k in t for k in include_kw)


def _build_sections(toc: list, total_pages: int) -> list[Section]:
    """Convert raw TOC entries to Section objects with computed end pages."""
    sections = []
    for i, (level, title, page) in enumerate(toc):
        # end page = start of next entry at same or higher level, minus 1
        end = total_pages
        for j in range(i + 1, len(toc)):
            next_level, _, next_page = toc[j]
            if next_level <= level:
                end = next_page - 1
                break
        # Edge case: when next section starts on same page (Q季报 常见),
        # end < start → 0 页. Fallback: extract at least the start page.
        if end < page:
            end = page
        sections.append(Section(level, title, page, end))
    return sections


def _extract_page_text(doc: pymupdf.Document, start: int, end: int) -> str:
    """Extract text from pages [start, end] (1-based, inclusive)."""
    parts = []
    for p in range(start - 1, min(end, doc.page_count)):   # convert to 0-based
        page = doc[p]
        text = page.get_text("text")
        if text.strip():
            parts.append(text)
    return "\n".join(parts)


def _clean_text(text: str) -> str:
    """Remove excessive blank lines."""
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract(
    pdf_path: Path,
    include_subsections: bool = True,
) -> dict[str, str]:
    """Return {section_title: extracted_text} for investment-relevant sections."""
    doc = pymupdf.open(str(pdf_path))
    toc = doc.get_toc()

    if not toc:
        log.warning("No TOC found in %s — falling back to full-text extraction", pdf_path.name)
        pages_text = "\n".join(doc[p].get_text("text") for p in range(doc.page_count))
        full = _clean_text(pages_text)
        doc.close()
        return {"全文": full} if full else {}

    sections = _build_sections(toc, doc.page_count)
    quarterly = _is_quarterly_report(toc)
    if quarterly:
        log.info("Detected quarterly report — using Q-report section template")
    skip_kw = _QUARTERLY_SKIP_KEYWORDS if quarterly else _SKIP_KEYWORDS

    result: dict[str, str] = {}
    current_l1_included = False

    for sec in sections:
        if sec.level == 1:
            current_l1_included = _should_include(sec.title, quarterly=quarterly)
            if current_l1_included:
                text = _extract_page_text(doc, sec.start_page, sec.end_page)
                result[sec.title] = _clean_text(text)
        elif sec.level == 2 and include_subsections and current_l1_included:
            if not any(k in sec.title.replace(" ", "") for k in skip_kw):
                text = _extract_page_text(doc, sec.start_page, sec.end_page)
                result[f"  {sec.title}"] = _clean_text(text)

    doc.close()
    return result


def to_markdown(sections: dict[str, str]) -> str:
    """Format extracted sections as markdown for LLM consumption."""
    parts = []
    for title, text in sections.items():
        level = "##" if not title.startswith("  ") else "###"
        parts.append(f"{level} {title.strip()}\n\n{text}")
    return "\n\n---\n\n".join(parts)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Extract sections from A-share annual report PDF")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--out", type=Path, default=None, help="Output .md path (default: same dir as PDF)")
    parser.add_argument("--no-subsections", action="store_true", help="Skip L2 subsections")
    parser.add_argument("--list-toc", action="store_true", help="Print TOC and exit")
    args = parser.parse_args()

    if not args.pdf.exists():
        print(f"File not found: {args.pdf}", file=sys.stderr)
        sys.exit(1)

    if args.list_toc:
        doc = pymupdf.open(str(args.pdf))
        for level, title, page in doc.get_toc():
            if level <= 2:
                print(f"{'  ' * level}p{page:3d}: {title}")
        doc.close()
        return

    sections = extract(args.pdf, include_subsections=not args.no_subsections)

    if not sections:
        print("警告：未找到匹配的章节，请用 --list-toc 查看文档结构", file=sys.stderr)
        sys.exit(1)

    md = to_markdown(sections)
    out = args.out or args.pdf.with_name(args.pdf.stem + "_extracted.md")
    out.write_text(md, encoding="utf-8")

    print(f"✓ 提取 {len(sections)} 个章节 → {out}")
    print(f"  总字符数: {len(md):,}")
    for title in sections:
        print(f"  · {title.strip()}")


if __name__ == "__main__":
    main()

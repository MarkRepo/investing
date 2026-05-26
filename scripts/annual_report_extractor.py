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

# 港股 / 海外 PDF 年报的英文 TOC keywords（小写比对）
_INCLUDE_KEYWORDS_EN = [
    "management discussion",
    "md&a",
    "business highlights",
    "business review",
    "business overview",
    "operating review",
    "operations review",
    "operational review",
    "chairman",
    "ceo statement",
    "letter to shareholder",
    "letter from",
    "principal risks",
    "risk factors",
    "strategic report",
    "strategy",
    "outlook",
    "future development",
    "research and development",
    "r&d update",
    "report of directors",
]
_SKIP_KEYWORDS_EN = [
    "financial highlights",
    "financial summary",
    "financial position",
    "financial statements",
    "consolidated statement",
    "cash flow",
    "notes to",
    "auditor",
    "corporate governance",
    "directors and senior management",
    "five year",
    "definitions",
    "cover",
    "contents",
    "company profile",
    "corporate information",
    "shareholder information",
    "remuneration",
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
    t_lower = title.lower()
    skip_kw = _QUARTERLY_SKIP_KEYWORDS if quarterly else _SKIP_KEYWORDS
    include_kw = _QUARTERLY_INCLUDE_KEYWORDS if quarterly else _INCLUDE_KEYWORDS
    if any(k in t for k in skip_kw):
        return False
    if not quarterly and any(k in t_lower for k in _SKIP_KEYWORDS_EN):
        return False
    if any(k in t for k in include_kw):
        return True
    if not quarterly and any(k in t_lower for k in _INCLUDE_KEYWORDS_EN):
        return True
    return False


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


def _table_to_markdown(rows: list[list]) -> str:
    """Convert list-of-lists table to markdown table syntax.
    Pads short rows, treats None as empty, escapes pipe, collapses cell newlines.
    """
    if not rows:
        return ""
    cleaned = [
        [(str(c) if c is not None else "").replace("\n", " ").replace("|", "/").strip() for c in r]
        for r in rows
    ]
    n_cols = max(len(r) for r in cleaned)
    cleaned = [r + [""] * (n_cols - len(r)) for r in cleaned]
    header = "| " + " | ".join(cleaned[0]) + " |"
    sep = "| " + " | ".join(["---"] * n_cols) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in cleaned[1:])
    return f"{header}\n{sep}\n{body}" if body else f"{header}\n{sep}"


def _extract_page_text(doc: pymupdf.Document, start: int, end: int) -> str:
    """Extract text from pages [start, end] (1-based, inclusive).
    Tables (via PyMuPDF find_tables) are emitted as markdown and inserted
    at their y-position; text blocks falling inside a table bbox are suppressed
    to avoid duplication.
    """
    parts = []
    for p in range(start - 1, min(end, doc.page_count)):   # convert to 0-based
        page = doc[p]
        try:
            tabs = page.find_tables().tables
        except Exception:
            tabs = []

        if not tabs:
            text = page.get_text("text")
            if text.strip():
                parts.append(text)
            continue

        blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
        table_bboxes = [tab.bbox for tab in tabs]

        def _inside_table(x0: float, y0: float, x1: float, y1: float) -> bool:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            for tx0, ty0, tx1, ty1 in table_bboxes:
                if tx0 <= cx <= tx1 and ty0 <= cy <= ty1:
                    return True
            return False

        items: list[tuple[float, str]] = []
        for b in blocks:
            if len(b) < 5:
                continue
            x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
            if not text or not text.strip():
                continue
            if _inside_table(x0, y0, x1, y1):
                continue
            items.append((y0, text.rstrip()))

        for tab in tabs:
            rows = tab.extract()
            if not rows or len(rows) < 2:
                continue
            md = _table_to_markdown(rows)
            if md:
                items.append((tab.bbox[1], f"\n{md}\n"))

        items.sort(key=lambda x: x[0])
        if items:
            parts.append("\n".join(c for _, c in items))
    return "\n".join(parts)


def _clean_text(text: str) -> str:
    """Remove excessive blank lines."""
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _text_heading_fallback(doc: pymupdf.Document) -> list[tuple[int, str, int]]:
    """无 PDF outline 时，从正文文本扫"第N节 标题"作章节锚点。

    返回与 doc.get_toc() 兼容的 [(level, title, page), ...] 结构。
    每个 unique heading 取**最后一次出现**作 body anchor（首次通常在 TOC 页）。
    """
    heading_re = re.compile(r"^第\s*[一二三四五六七八九十百\d]+\s*节\s*\S[^\n]*", re.MULTILINE)
    occurs: dict[str, list[int]] = {}
    for i in range(doc.page_count):
        txt = doc[i].get_text("text")
        for m in heading_re.finditer(txt):
            line = m.group(0).strip()
            # 标准化 key：仅保留"第N节 第一个词"避免空格/换行差异
            norm = re.match(r"^(第\s*[一二三四五六七八九十百\d]+\s*节)\s*(\S+)", line)
            if not norm:
                continue
            key = f"{norm.group(1).replace(' ', '')} {norm.group(2)}"
            occurs.setdefault(key, []).append(i + 1)  # 1-based page

    if not occurs:
        return []
    # body anchor = 最后一次出现页（TOC 在最前）
    toc_like = [(1, k, max(pages)) for k, pages in occurs.items()]
    toc_like.sort(key=lambda x: x[2])
    return toc_like


def extract(
    pdf_path: Path,
    include_subsections: bool = True,
) -> dict[str, str]:
    """Return {section_title: extracted_text} for investment-relevant sections."""
    doc = pymupdf.open(str(pdf_path))
    toc = doc.get_toc()

    if not toc:
        # 无 PDF outline 时，先尝试从文本提"第N节"heading 兜底
        toc = _text_heading_fallback(doc)
        if toc:
            log.info("No PDF outline in %s — using text-heading fallback (%d sections)",
                     pdf_path.name, len(toc))

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

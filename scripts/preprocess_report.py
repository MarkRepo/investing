"""Preprocess an annual/quarterly/sell-side report for ingest.

CLI:
    python -m scripts.preprocess_report <file> \\
        --type {annual|quarterly|sell-side} \\
        --market {a-share|us} \\
        [--out <json_path>]

Reads PDF/HTM/MD/TXT, extracts text, normalizes section names, applies skip rules,
emits a JSON blob consumed by the ingest skill.

Does NOT call LLMs. Does NOT write to DB. Pure function: file -> JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / ".claude" / "skills" / "ingest" / "templates"

TEMPLATE_MAP = {
    ("a-share", "annual"):    "a-share-annual.yaml",
    ("a-share", "quarterly"): "a-share-quarterly.yaml",
    ("a-share", "sell-side"): "sell-side-generic.yaml",
    ("a-share", "industry"):  "a-share-industry.yaml",
    ("us", "annual"):         "us-10k.yaml",
    ("us", "quarterly"):      "us-10q.yaml",
    ("us", "sell-side"):      "sell-side-generic.yaml",
    ("us", "industry"):       "us-industry.yaml",
}

MIN_SECTION_CHARS = 500


# Heading patterns that may appear as a lone line (just the "number") in PDF extraction.
# When matched, we join with the following non-empty line before section splitting.
_LONE_HEADING_PATTERNS = [
    re.compile(r"^\s*第\s*[一二三四五六七八九十百千万亿\d]+\s*节\s*$"),
    re.compile(r"^\s*ITEM\s+\d+[A-Z]?\.?\s*$", re.IGNORECASE),
]


def join_multiline_headings(text: str) -> str:
    """Merge heading lines split across two lines by PDF extraction.

    Example: "第一节\\n释义" -> "第一节 释义".
    """
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        if any(p.match(cur) for p in _LONE_HEADING_PATTERNS):
            # find next non-empty line within a small window
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and j - i <= 3:
                next_line = lines[j].strip()
                if next_line and len(next_line) < 80:
                    out.append(f"{cur.strip()} {next_line}")
                    i = j + 1
                    continue
        out.append(cur)
        i += 1
    return "\n".join(out)


def load_template(market: str, form: str) -> dict:
    fname = TEMPLATE_MAP.get((market, form))
    if not fname:
        raise ValueError(f"no template for market={market} form={form}")
    path = TEMPLATES_DIR / fname
    if not path.exists():
        raise FileNotFoundError(f"template not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def extract_text(file_path: Path) -> str:
    suf = file_path.suffix.lower()
    if suf == ".pdf":
        import fitz  # pymupdf

        doc = fitz.open(str(file_path))
        parts = []
        for i in range(len(doc)):
            page = doc.load_page(i)
            parts.append(page.get_text("text"))
        return "\n".join(parts)
    if suf in (".htm", ".html"):
        from bs4 import BeautifulSoup

        raw = file_path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator="\n")
    if suf in (".md", ".txt"):
        return file_path.read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"unsupported extension: {suf}")


def sha256_head(path: Path, n: int = 8) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:n]


def detect_form(text: str, template: dict) -> bool:
    """Positive must significantly outnumber negative.

    10-K files mention "Form 10-Q" in cross-references; A-share annual reports
    mention "季度报告" in TOC notes. Strict "any negative disqualifies" rule
    false-positives on these. Ratio-based check is much more robust.
    """
    fd = template.get("form_detection", {})
    pos = fd.get("positive", [])
    neg = fd.get("negative", [])
    if not pos:
        return False
    pos_hits = sum(len(re.findall(p, text)) for p in pos)
    neg_hits = sum(len(re.findall(p, text)) for p in neg)
    if pos_hits == 0:
        return False
    # require positive to dominate; tolerates a few cross-references.
    return pos_hits >= max(3, 2 * neg_hits)


def extract_fiscal_year(text: str, template: dict) -> str | None:
    """Scan whole document, take the MAX year across all pattern matches.

    Rationale: a 10-K contains prior-year comparison text like "fiscal year
    ended December 31, 2024". Taking first match biases toward old years;
    taking max biases toward the report's own year (which is the intent).
    """
    rules = template.get("fiscal_year_extraction", {})
    patterns = rules.get("patterns", [])
    fmt = rules.get("format", "{year}")
    years = []
    for p in patterns:
        for m in re.finditer(p, text):
            try:
                years.append(int(m.group(1)))
            except (ValueError, IndexError):
                continue
    if not years:
        return None
    return fmt.format(year=max(years))


def extract_reporting_period(text: str, template: dict, fiscal_year: str | None) -> str | None:
    """Pick a reporting-period match whose year matches fiscal_year.

    Reports contain many dated clauses (leases, bonds) that can extend to
    "January 1, 2041" etc. Locking to fiscal_year prevents those false hits.
    Falls back to first match if fiscal_year is unknown.
    """
    rules = template.get("reporting_period_extraction", {})
    patterns = rules.get("patterns", [])
    fmt = rules.get("format", "{raw}")

    target_year: int | None = None
    if fiscal_year:
        m = re.search(r"\d{4}", fiscal_year)
        if m:
            target_year = int(m.group(0))

    def _raw(m: re.Match) -> str:
        # Prefer group(1) (which yaml patterns use to isolate the date),
        # fall back to full match. Collapse whitespace so HTM line-splits
        # don't leak into output.
        raw = m.group(1) if m.groups() else m.group(0)
        return re.sub(r"\s+", " ", raw).strip()

    fallback = None
    for p in patterns:
        for m in re.finditer(p, text):
            year_match = re.search(r"\b(\d{4})\b", m.group(0))
            if not year_match:
                continue
            year = int(year_match.group(1))
            if target_year is not None and year == target_year:
                if "{raw}" in fmt:
                    return fmt.format(raw=_raw(m))
                return fmt.format(year=year)
            if fallback is None:
                fallback = (m, year)

    if fallback is None:
        return None
    m, year = fallback
    if "{raw}" in fmt:
        return fmt.format(raw=_raw(m))
    return fmt.format(year=year)


def _normalize_heading(
    stripped: str,
    match: re.Match,
    normalize_table: dict,
    current_part: str | None = None,
) -> str | None:
    groups = match.groups()

    # US 10-K / 10-Q style: group(1) is "1A" / "7" etc → build "Item_1A" key.
    # 10-Q disambiguates by Part (I vs II): look up "PartI_Item_N" / "PartII_Item_N"
    # first, fall back to "Item_N" for 10-K which has no Part tracking.
    if groups and groups[0] and re.fullmatch(r"\d+[A-Z]?", groups[0]):
        if current_part:
            part_key = f"Part{current_part}_Item_{groups[0]}"
            if part_key in normalize_table:
                return normalize_table[part_key]
        key = f"Item_{groups[0]}"
        if key in normalize_table:
            return normalize_table[key]

    # A-share style: group(2) is the section title after "第X节"
    if len(groups) >= 2 and groups[1]:
        title = groups[1].strip().rstrip("。.:：")
        if title in normalize_table:
            return normalize_table[title]
        for raw_key, canonical in normalize_table.items():
            if raw_key and (raw_key in title or title in raw_key):
                return canonical

    # Last resort: scan whole heading against normalize keys
    for raw_key, canonical in normalize_table.items():
        if raw_key and raw_key in stripped:
            return canonical

    return None


# PART heading pattern for 10-Q / 10-K (e.g., "PART I — FINANCIAL INFORMATION")
_PART_HEADING_RE = re.compile(
    r"^\s*PART\s+(II|I)\b",  # II before I to avoid "I" prefix-matching "II"
    re.IGNORECASE,
)


def split_sections(text: str, template: dict) -> list[dict]:
    patterns = template.get("section_detection", {}).get("patterns", []) or []
    normalize = template.get("section_normalize", {}) or {}
    # Optional per-template fallback for headings whose title is not in the
    # normalize whitelist. Used by sell-side-generic where report bodies carry
    # bespoke chapter titles ("深耕线缆用高分子材料二十载") that all belong in
    # the thesis channel. Unset for financial-report templates → UNKNOWN_N
    # bucket is kept (preserves the healthcheck signal).
    section_fallback = template.get("_section_fallback")

    lines = text.splitlines()
    starts: list[tuple[int, str, str | None]] = []
    current_part: str | None = None  # "I" / "II" for 10-Q PART tracking; None for formats without Parts
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 200:
            continue
        # Track current PART for 10-Q / 10-K. PART line is NOT itself emitted as a section
        # (Items inside it will be, with Part-prefixed normalize key).
        part_m = _PART_HEADING_RE.match(stripped)
        if part_m:
            current_part = part_m.group(1).upper()
            continue
        for pat in patterns:
            m = re.match(pat, stripped)
            if m:
                normalized = _normalize_heading(stripped, m, normalize, current_part)
                starts.append((i, stripped, normalized))
                break

    sections: list[dict] = []
    if not starts:
        sections.append({
            "name": "UNKNOWN_0",
            "heading_raw": "",
            "text": text.strip(),
            "order": 0,
        })
        return sections

    if starts[0][0] > 0:
        header_body = "\n".join(lines[: starts[0][0]]).strip()
        if header_body:
            sections.append({
                "name": "HEADER",
                "heading_raw": "",
                "text": header_body,
                "order": 0,
            })

    unknown_counter = 0
    for idx, (line_idx, heading_raw, normalized) in enumerate(starts):
        next_line = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        body = "\n".join(lines[line_idx:next_line]).strip()
        if normalized:
            name = normalized
        elif section_fallback:
            name = section_fallback
        else:
            unknown_counter += 1
            name = f"UNKNOWN_{unknown_counter}"
        sections.append({
            "name": name,
            "heading_raw": heading_raw,
            "text": body,
            "order": idx + 1,
        })

    return _dedupe_toc(sections)


def _dedupe_toc(sections: list[dict]) -> list[dict]:
    """When a section name appears multiple times, keep the one with the longest body
    (the real section, not the TOC entry)."""
    by_name: dict[str, list[dict]] = {}
    for sec in sections:
        by_name.setdefault(sec["name"], []).append(sec)

    kept_ids = set()
    for name, candidates in by_name.items():
        if name.startswith("UNKNOWN") or name == "HEADER":
            for c in candidates:
                kept_ids.add(id(c))
            continue
        winner = max(candidates, key=lambda c: len(c["text"]))
        kept_ids.add(id(winner))
        for loser in candidates:
            if id(loser) != id(winner) and len(loser["text"]) < MIN_SECTION_CHARS:
                # silently drop TOC-like short duplicates
                continue
            kept_ids.add(id(loser))
    return [s for s in sections if id(s) in kept_ids]


_TOC_TAIL_RE = re.compile(r"\.{3,}\s*\d+\s*$")


def apply_skip_rules(sections: list[dict], template: dict) -> list[dict]:
    skip_sections = set(template.get("skip_rules", {}).get("sections", []) or [])
    for sec in sections:
        heading = sec.get("heading_raw", "") or ""
        if sec["name"] in skip_sections:
            sec["action"] = "skip"
            sec["reason"] = "template skip_rules.sections"
        elif sec["name"] == "HEADER":
            sec["action"] = "skip"
            sec["reason"] = "document header, no section content"
        elif _TOC_TAIL_RE.search(heading):
            # Table-of-contents line leaked in as a section (heading ends with
            # "........<page>"). Skip — it's not content.
            sec["action"] = "skip"
            sec["reason"] = "TOC entry (heading ends with dotted page ref)"
        elif sec["name"].startswith("UNKNOWN_"):
            sec["action"] = "keep"
            sec["reason"] = "section title not matched in normalize table"
        else:
            sec["action"] = "keep"
            sec["reason"] = None
    return sections


def extract_institution(text: str, template: dict) -> str | None:
    """Sell-side only: match first known institution name from cover/header.

    Scans the first 10K chars (cover + TOC) so we don't false-positive on
    cross-references later in the doc ("we disagree with Goldman's view").
    """
    rules = template.get("institution_extraction", {})
    patterns = rules.get("patterns", [])
    if not patterns:
        return None
    head = text[:10000]
    for p in patterns:
        m = re.search(p, head)
        if m:
            raw = m.group(1) if m.groups() else m.group(0)
            return re.sub(r"\s+", " ", raw).strip()
    return None


def extract_publish_date(text: str, template: dict) -> str | None:
    """Sell-side only: normalize matched date to ``YYYY-MM-DD``.

    Only scans the first 10K chars. Accepts Chinese "YYYY年MM月DD日", ISO
    "YYYY-MM-DD" / "YYYY/MM/DD", and English "Month DD, YYYY". Falls back to
    raw match if the group layout doesn't match the three known shapes.
    """
    rules = template.get("publish_date_extraction", {})
    patterns = rules.get("patterns", [])
    if not patterns:
        return None
    head = text[:10000]
    month_map = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
        "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
        "november": 11, "december": 12,
    }
    for p in patterns:
        m = re.search(p, head)
        if not m:
            continue
        groups = m.groups()
        # English: (Month, DD, YYYY)
        if len(groups) == 3 and groups[0] and groups[0].lower() in month_map:
            month = month_map[groups[0].lower()]
            try:
                return f"{int(groups[2]):04d}-{month:02d}-{int(groups[1]):02d}"
            except ValueError:
                continue
        # Numeric: (YYYY, MM, DD)
        if len(groups) == 3 and all(g and g.isdigit() for g in groups):
            try:
                return f"{int(groups[0]):04d}-{int(groups[1]):02d}-{int(groups[2]):02d}"
            except ValueError:
                continue
        return re.sub(r"\s+", " ", m.group(0)).strip()
    return None


# --- detect_tickers ----------------------------------------------------------

# A-share 6-digit code mapping to exchange (prefix rules):
#   6*     -> SSE   (上海主板/科创板)
#   000*/001*/002*/003* -> SZSE (深交所主板/中小板/创业板 3XX)
#   300*/301* -> SZSE (创业板)
#   8* (6-digit)/9*  -> BSE
# We keep it simple: first-char rules.
_A_SHARE_CODE_RE = re.compile(r"(?<!\d)([036][0-9]{5}|8[0-9]{5}|9[0-9]{5})(?!\d)")
_US_TICKER_RE = re.compile(
    r"\b(?:NYSE|NASDAQ|NASDAQ:NYSE)\s*:?\s*([A-Z]{1,5})\b"
)


def _classify_a_share(code: str) -> str:
    if code.startswith("6"):
        return "SSE"
    if code.startswith(("0", "3")):
        return "SZSE"
    if code.startswith(("8", "9")):
        return "BSE"
    return "SSE"


def detect_tickers(text: str) -> list[dict]:
    """Scan for plausible A-share 6-digit codes + US NYSE/NASDAQ: tickers.
    Returns a de-duplicated list of {market, ticker} rows, in first-seen order.
    """
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for m in _A_SHARE_CODE_RE.finditer(text):
        code = m.group(1)
        market = _classify_a_share(code)
        key = (market, code)
        if key not in seen:
            seen.add(key)
            out.append({"market": market, "ticker": code})
    for m in _US_TICKER_RE.finditer(text):
        sym = m.group(1).upper()
        key = ("US", sym)
        if key not in seen:
            seen.add(key)
            out.append({"market": "US", "ticker": sym})
    return out


# --- extract_report_abstract -------------------------------------------------

def extract_report_abstract(text: str, max_chars: int = 500) -> str | None:
    """Pull the leading 200-500 chars as an abstract. Skip obvious header
    boilerplate (institution name, date line). Stop on first section heading.
    """
    # Trim to first section start (one of our common heading patterns).
    head = text[:3000]
    # Find first "一、" or "1、" or "##" or "PART I" style heading:
    stop_re = re.compile(r"(?m)^(?:[一二三四五六七八九十]、|\d+[、.．]|##\s+|PART\s+I)")
    m = stop_re.search(head)
    body = head[: m.start()] if m else head
    # Collapse blank lines.
    body = re.sub(r"\n{2,}", "\n", body).strip()
    if not body:
        return None
    return body[:max_chars]


# --- page_signals (phase-1 preprocess metadata) ---

def _page_text_quality(text: str) -> str:
    """Classify page text quality based on extracted character count.

    Args:
        text: Raw extracted text from page

    Returns:
        "low" if < 30 chars, "medium" if < 200 chars, "high" otherwise
    """
    stripped = re.sub(r"\s+", "", text or "")
    if len(stripped) < 30:
        return "low"
    if len(stripped) < 200:
        return "medium"
    return "high"


def build_page_signals(doc) -> list[dict]:
    """Build per-page risk signals from PDF document.

    Scans each page for text quality, visual content indicators (charts, tables, images).
    Returns list of dicts with page number (1-based) and quality flags.

    Args:
        doc: PyMuPDF document with __len__ and load_page(idx) interface

    Returns:
        List of dicts with keys: page, text_quality, image_heavy, chart_heavy, table_heavy
    """
    pages: list[dict] = []
    for i in range(len(doc)):
        text = doc.load_page(i).get_text("text")
        pages.append({
            "page": i + 1,  # 1-based page numbering
            "text_quality": _page_text_quality(text),
            "image_heavy": False,  # TODO: detect from doc metadata if needed
            "chart_heavy": any(k in text for k in ("图", "Chart", "CAGR")),
            "table_heavy": any(k in text for k in ("表", "Table")),
        })
    return pages


def collect_extraction_warnings(page_signals: list[dict]) -> list[str]:
    """Emit warnings for risky extraction scenarios.

    Flags low-text-quality pages and visual-heavy pages that may have
    extraction fidelity issues.

    Args:
        page_signals: List of page signal dicts from build_page_signals

    Returns:
        List of warning strings (Chinese) describing quality concerns
    """
    warnings: list[str] = []
    for page in page_signals:
        if page["text_quality"] == "low":
            warnings.append(f"第 {page['page']} 页文本提取质量低，需谨慎使用。")
        if page["chart_heavy"] or page["image_heavy"]:
            warnings.append(f"第 {page['page']} 页包含图表或图片密集内容，关键结论需复核。")
        if page["table_heavy"]:
            warnings.append(f"第 {page['page']} 页表格密集，提取内容可能不完整。")
    return warnings


# --- figure_contexts (spec §4.8) ---------------------------------------------

_FIGURE_CAPTION_PATTERNS = [
    re.compile(r"^(图表?\s*\d+[:：].{0,120})$", re.MULTILINE),
    re.compile(r"^(表\s*\d+[:：].{0,120})$", re.MULTILINE),
    re.compile(r"^((?:Exhibit|Figure|Chart|Table)\s+\d+[:\.]\s.{0,200})$",
               re.MULTILINE | re.IGNORECASE),
]


def _paragraphs(text: str) -> list[str]:
    # Split on blank lines; strip; drop empties.
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def extract_figure_contexts(
    full_text: str,
    sections: list[dict],
) -> list[dict]:
    """Scan each section body for figure/table captions; for each caption emit
    a context row with the 2 paragraphs before + 2 paragraphs after as
    surrounding_text. No LLM — pure regex + paragraph slicing.
    """
    out: list[dict] = []
    fig_counter = 0
    for sec in sections:
        sec_text = sec.get("text", "")
        if not sec_text:
            continue
        paras = _paragraphs(sec_text)
        for p_idx, para in enumerate(paras):
            for pat in _FIGURE_CAPTION_PATTERNS:
                m = pat.match(para) or pat.search(para)
                if not m:
                    continue
                caption = m.group(1).strip()
                if _TOC_TAIL_RE.search(caption):
                    # "图表1：CMP 工作原理 ...... 4" — TOC entry, not real figure
                    continue
                # Surrounding: up to 2 paragraphs before and 2 after (skipping
                # the caption paragraph itself).
                before = paras[max(0, p_idx - 2): p_idx]
                after = paras[p_idx + 1: p_idx + 3]
                surrounding = "\n\n".join(before + after).strip()
                fig_counter += 1
                out.append({
                    "id": f"fig-{fig_counter:03d}",
                    "page": None,  # page tracking not yet wired; TODO in v2
                    "caption": caption,
                    "surrounding_text": surrounding,
                    "section_name": sec.get("name", "UNKNOWN"),
                })
                break  # next paragraph
    return out


def build_result(
    file_path: Path,
    market: str,
    form_cli: str,
    template: dict,
    sections: list[dict],
    text_full: str,
    doc=None,  # Optional PyMuPDF document for page-level signals (PDF only)
) -> dict:
    sha8 = sha256_head(file_path)
    detected = detect_form(text_full, template)
    fiscal_year = extract_fiscal_year(text_full, template)
    period = extract_reporting_period(text_full, template, fiscal_year)
    institution = extract_institution(text_full, template)
    publish_date = extract_publish_date(text_full, template)

    out_sections = [
        {
            "name": s["name"],
            "heading_raw": s.get("heading_raw", ""),
            "order": s["order"],
            "char_count": len(s["text"]),
            "action": s["action"],
            "reason": s["reason"],
            "text": s["text"],
        }
        for s in sections
    ]

    fig_contexts = extract_figure_contexts(text_full, sections)

    # Build page-level signals and extraction warnings from PDF document (if available)
    page_signals = []
    extraction_warnings = []
    if doc is not None:
        page_signals = build_page_signals(doc)
        extraction_warnings = collect_extraction_warnings(page_signals)

    return {
        "meta": {
            "source_file": file_path.name,
            "sha8": sha8,
            "cli_type": form_cli,
            "detected_form": template.get("form") if detected else None,
            "fiscal_year": fiscal_year,
            "reporting_period": period,
            "institution": institution,
            "publish_date": publish_date,
            "market": market,
            "preprocess_version": "v1",
        },
        "sections": out_sections,
        "figure_contexts": fig_contexts,
        "detected_tickers": detect_tickers(text_full),
        "report_abstract": extract_report_abstract(text_full),
        "page_signals": page_signals,
        "extraction_warnings": extraction_warnings,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Preprocess a report into sections JSON")
    ap.add_argument("file", type=Path, help="Path to the report file (PDF/HTM/MD/TXT)")
    ap.add_argument("--type", required=True, choices=["annual", "quarterly", "sell-side", "industry"])
    ap.add_argument("--market", required=True, choices=["a-share", "us"])
    ap.add_argument("--out", type=Path, default=None, help="Output JSON path (default: stdout)")
    args = ap.parse_args(argv)

    if not args.file.exists():
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 2

    template = load_template(args.market, args.type)

    # Extract document for page-level signals (PDF only)
    doc = None
    suf = args.file.suffix.lower()
    if suf == ".pdf":
        import fitz  # pymupdf
        doc = fitz.open(str(args.file))

    text = extract_text(args.file)
    text = join_multiline_headings(text)
    sections = split_sections(text, template)
    sections = apply_skip_rules(sections, template)
    result = build_result(args.file, args.market, args.type, template, sections, text, doc=doc)

    # Close PDF document if opened
    if doc is not None:
        doc.close()

    out_json = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(out_json, encoding="utf-8")
        kept = sum(1 for s in result["sections"] if s["action"] == "keep")
        skipped = sum(1 for s in result["sections"] if s["action"] == "skip")
        print(
            f"wrote {args.out}: {len(result['sections'])} sections "
            f"({kept} keep, {skipped} skip)",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(out_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())

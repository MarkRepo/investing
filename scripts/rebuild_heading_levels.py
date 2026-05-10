#!/usr/bin/env python3
"""Rebuild heading hierarchy in MinerU full-clean.md output.

MinerU flattens all headings to H1 (#).  This script restores H1/H2/H3 levels
using three signal layers (no font-size dependency):

  Signal 1 — TOC anchors (strongest)
    Parse the report's own table of contents (between "# 目录" and "# 图表目录")
    to identify chapter boundaries.  Everything between two chapters is H2/H3.

  Signal 2 — Explicit numbering (fallback)
    Chinese "一、/（一）"/ digit "1.1" numbering conventions.

  Signal 3 — Template/content patterns (last resort)
    Known boilerplate headings in Chinese sell-side / industry reports.

Usage:
    .venv/bin/python -m scripts.rebuild_heading_levels <path/to/full-clean.md>
    .venv/bin/python -m scripts.rebuild_heading_levels <path/to/full-clean.md> --out leveled.md
"""

import argparse
import re
import sys
from pathlib import Path

# --- Constants ---

PRE_MATTER_TITLES = frozenset({
    '强于大市', '相关研究报告', '机械设备', '可控核聚变行业深度报告',
    '商业化渐行渐近，产业链有望充分受益', '目录', '图表目录',
})

BOILERPLATE_H3 = frozenset({
    '支撑评级的要点', '估值', '评级面临的主要风险',
    '盈利预测及投资建议',
})

BOILERPLATE_H2 = frozenset({
    '投资建议', '风险提示',
})

POST_MATTER_START = frozenset({
    '披露声明', '评级体系说明', '公司投资评级：',
    '行业投资评级：', '风险提示及免责声明', '相关关联机构：',
})

# Known company names from companion bundle.json or simple heuristics
# (2-4 chars, no predicate verb — heuristically a company name if isolated)
_COMPANY_NAME_RE = re.compile(r'^[一-鿿]{2,4}$')

# Titles that match _COMPANY_NAME_RE but are NEVER company names
_COMPANY_NAME_BLACKLIST = frozenset({
    '估值', '风险提示', '投资建议', '披露声明', '图表目录',
    '评级体系说明', '公司投资评级', '行业投资评级',
})

# --- Helpers ---


def _normalize(s: str) -> str:
    """Strip spaces, punctuation, dots for fuzzy matching."""
    return re.sub(r'[\s\.。，、：:]+', '', s)


def _extract_headings(lines: list[str]) -> list[tuple[int, str]]:
    """Return [(line_index_in_file, title_text), ...] for all `# ` prefixed lines."""
    return [(i, lines[i][2:].strip()) for i, ln in enumerate(lines) if ln.startswith('# ')]


def _parse_toc(headings: list[tuple[int, str]], toc_start_idx: int, toc_end_idx: int) -> list[tuple[str, int | None]]:
    """Parse TOC entries between toc_start and toc_end heading indices.

    Returns [(chapter_title, page_number_or_None), ...].
    """
    entries = []
    for idx in range(toc_start_idx + 1, toc_end_idx):
        raw = headings[idx][1]
        m = re.match(r'^(.+?)[\.\s]{2,}\s*\.?\s*(\d+)$', raw)
        if m:
            entries.append((m.group(1).strip(), int(m.group(2))))
        else:
            entries.append((raw, None))
    return entries


def _match_chapter(title: str, toc_entries: list[tuple[str, int | None]], consumed: set[int]) -> str | None:
    """Return TOC chapter title if `title` matches one, else None.

    Each TOC entry can only be matched once (consumed set tracks matched indices).
    Requires the body title to contain or be contained by the TOC entry
    (after normalization), with length ratio >= 0.75.
    """
    n = _normalize(title)
    if len(n) < 4:
        return None
    for ti, (toc_title, _) in enumerate(toc_entries):
        if ti in consumed:
            continue
        toc_n = _normalize(toc_title)
        if len(toc_n) < 4:
            continue
        if toc_n in n or n in toc_n:
            shorter = min(len(n), len(toc_n))
            longer = max(len(n), len(toc_n))
            if shorter / longer >= 0.75:
                consumed.add(ti)
                return toc_title
    return None


def _is_company_name(title: str) -> bool:
    """Heuristic: isolated 2-4 CJK chars, not in boilerplate blacklist."""
    return bool(_COMPANY_NAME_RE.match(title)) and title not in _COMPANY_NAME_BLACKLIST


# --- Main ---


def rebuild_levels(md_path: Path) -> str:
    """Read full-clean.md, return markdown with restored heading levels."""
    content = md_path.read_text(encoding="utf-8")
    lines = content.split('\n')
    headings = _extract_headings(lines)

    if len(headings) < 3:
        # Too few headings — nothing to level
        return content

    # --- Find TOC boundaries ---
    toc_start_idx = next((i for i, h in enumerate(headings) if h[1] == '目录'), None)
    toc_end_idx = next((i for i, h in enumerate(headings) if h[1] == '图表目录'), None)

    toc_entries: list[tuple[str, int | None]] = []
    if toc_start_idx is not None and toc_end_idx is not None and toc_end_idx > toc_start_idx:
        toc_entries = _parse_toc(headings, toc_start_idx, toc_end_idx)

    # --- Determine chapter boundaries ---
    body_start_idx = (toc_end_idx + 1) if toc_end_idx is not None else 0

    chapter_indices: set[int] = set()
    consumed_toc: set[int] = set()
    if toc_entries:
        for idx in range(body_start_idx, len(headings)):
            if _match_chapter(headings[idx][1], toc_entries, consumed_toc):
                chapter_indices.add(idx)

    # --- Build level map ---
    # level_map: heading_index_in_list -> 'H1'|'H2'|'H3'|'skip'|'pre'
    level_map: dict[int, str] = {}
    current_chapter_idx: int | None = None

    for idx in range(len(headings)):
        title = headings[idx][1]

        # Pre-matter
        if title in PRE_MATTER_TITLES:
            level_map[idx] = 'pre'
            continue

        # Post-matter
        if title in POST_MATTER_START:
            current_chapter_idx = None
            level_map[idx] = 'skip'
            continue

        # Chapter boundary from TOC
        if idx in chapter_indices:
            current_chapter_idx = idx
            level_map[idx] = 'H1'
            continue

        # Outside any chapter (skip front-matter headers after TOC)
        if current_chapter_idx is None and idx >= body_start_idx:
            # Check for Signal 2: explicit chapter numbering
            if re.match(r'^[一二三四五六七八九十][、.．]', title):
                current_chapter_idx = idx
                level_map[idx] = 'H1'
                continue
            # Could be a chapter without TOC — keep as H1 for safety
            level_map[idx] = 'skip'
            continue

        # Inside a chapter: determine level
        level = _determine_section_level(title, headings, idx, current_chapter_idx)
        level_map[idx] = level

    # --- Rewrite file ---
    result_lines: list[str] = []
    heading_idx = 0

    for i, line in enumerate(lines):
        if line.startswith('# ') and heading_idx < len(headings):
            level = level_map.get(heading_idx, 'skip')
            title = headings[heading_idx][1]

            if level == 'pre':
                # Keep as-is (pre-matter), add HTML comment for traceability
                result_lines.append(f'<!-- pre -->{line}')
            elif level == 'skip':
                # Keep as-is but mark as skipped
                result_lines.append(f'<!-- skip -->{line}')
            elif level == 'H1':
                result_lines.append(f'# {title}')
            elif level == 'H2':
                result_lines.append(f'## {title}')
            elif level == 'H3':
                result_lines.append(f'### {title}')
            else:
                result_lines.append(line)

            heading_idx += 1
        else:
            result_lines.append(line)

    return '\n'.join(result_lines)


def _determine_section_level(
    title: str,
    headings: list[tuple[int, str]],
    idx: int,
    chapter_idx: int | None,
) -> str:
    """Determine H2/H3 for a heading inside a known chapter."""

    # Check if inside a company section (preceded by company name H2)
    in_company_section = False
    if idx > 0 and chapter_idx is not None:
        for j in range(idx - 1, chapter_idx - 1, -1):
            prev_title = headings[j][1]
            # Skip sub-section markers — keep scanning backward
            if prev_title in PRE_MATTER_TITLES or prev_title in POST_MATTER_START:
                continue
            if prev_title in BOILERPLATE_H3:
                continue
            # Stop at chapter-level boundaries
            if prev_title in BOILERPLATE_H2:
                break
            if _is_company_name(prev_title):
                in_company_section = True
                break
            # Descriptive title that's not a company name — still in a sub-section, keep scanning
            # (e.g. "高端成形机床...行业领军企业" is a company intro, not a chapter boundary)
            # Only break if it looks like a section-level heading that isn't a company name

    # Within a company section, only known boilerplate sub-items go to H3
    if in_company_section and not _is_company_name(title):
        if title in BOILERPLATE_H3 or title in BOILERPLATE_H2:
            return 'H3'
        # Company intro/overview titles keep H2
        return 'H2'

    # Boilerplate patterns
    if title in BOILERPLATE_H3:
        return 'H3'
    if title in BOILERPLATE_H2:
        return 'H2'

    # Company names as H2
    if _is_company_name(title):
        return 'H2'

    # Signal 2: explicit sub-numbering
    if re.match(r'^（[一二三四五六七八九十]）', title):
        return 'H2'
    if re.match(r'^\d+\.\d+', title):
        return 'H3'
    if re.match(r'^\d+[、.．]', title):
        return 'H2'

    # Default: descriptive titles under a chapter → H2
    return 'H2'


# --- CLI ---


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Rebuild MinerU heading hierarchy")
    p.add_argument("input", help="Path to full-clean.md (or full.md)")
    p.add_argument("--out", help="Output path (default: overwrite input)")
    args = p.parse_args(argv)

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Error: {input_path} does not exist", file=sys.stderr)
        return 1

    result = rebuild_levels(input_path)
    out_path = Path(args.out) if args.out else input_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result, encoding="utf-8")

    # Quick stats
    h1_count = len(re.findall(r'(?m)^#\s', result))
    h2_count = len(re.findall(r'(?m)^##\s', result))
    h3_count = len(re.findall(r'(?m)^###\s', result))
    total = h1_count + h2_count + h3_count
    h1_pct = f"{h1_count / total * 100:.0f}%" if total else "N/A"
    print(f"✓ Heading levels rebuilt: H1={h1_count} H2={h2_count} H3={h3_count} (H1 {h1_pct} of total)")
    print(f"  Written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

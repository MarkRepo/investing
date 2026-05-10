#!/usr/bin/env python3
"""Validate MinerU output — scan full-clean.md for suspicious tokens (OCR typos, unit mismatches).

Produces suspicious_tokens.json in the same directory as the input file.
Zero LLM cost — deterministic regex scanning.

Usage:
    python -m scripts.validate_mineru <mineru_dir_or_md_path>
    python -m scripts.validate_mineru <mineru_dir> --archetype technology_driven
    python -m scripts.validate_mineru <path/to/full-clean.md>
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- Group 1: Common patterns (run on every report) ---
COMMON_PATTERNS: list[tuple[str, str, str]] = [
    (
        r'(\d+(?:\.\d+)?)\s*万亿\s*(吨|立方米|美元|元|人民币)?',
        'scale_wanyi_check',
        '万亿量级需核对',
    ),
    (
        r'(\d+(?:\.\d+)?)\s*(亿|万|千|百)'
        r'(?!元|美元|港币|欧元|股|户|人|套|辆|辆次|吨|平方|人次|小时|天|次)',
        'magnitude_no_unit',
        '数量级后缺单位',
    ),
    (
        r'(0\.\d{1,3})\s*(增长|下降|提升|下滑|提高)',
        'decimal_possibly_percent',
        '小数后接增长语义模糊，可能是 % 被吞',
    ),
    (
        r'(\d{6,})(?!\s*[a-zA-Zµμ元%度吨亿万平方])',
        'large_number_no_unit',
        '6 位以上数字无单位',
    ),
    (
        r'(20[4-9][0-9])\s*年',
        'year_far_future_check',
        '40 年后的年份需区分长期预测 vs OCR 错',
    ),
    (
        r'(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',
        'date_sanity',
        '校验月/日合法性',
    ),
]

# --- Group 2: Domain patterns (per industry_archetype) ---
DOMAIN_PATTERNS: dict[str, list[tuple[str, str, str]]] = {
    "technology_driven": [
        (r'(\d+(?:\.\d+)?)\s*m²', 'unit_possible_m3', '科技文档中 m² 多为 m³ OCR 错'),
        (r'(\d+(?:\.\d+)?)\s*㎡', 'unit_possible_m3', '科技文档中 ㎡ 多为 m³ OCR 错'),
        (r'(\d+(?:\.\d+)?)\s*m2\b', 'unit_possible_m3', '科技文档中 m2 可能为 m³ OCR 错'),
        (r'(\d{5,})\s*K\b', 'temperature_magnitude_k', '温度 5 位数以上需核对 K vs °C'),
        (r'(\d+(?:\.\d+)?)\s*(T|GHz|MHz|nm)\b', 'spec_unit_check', '物理量单位需核对是否被 OCR 改写'),
    ],
    "financial": [
        (r'(\d+(?:\.\d+)?)\s*(bps|BP|个基点)', 'bps_check', '基点单位易与百分点混淆'),
        (r'(\d+(?:\.\d+)?)\s*%\s*(同比|环比)\s*(\d+(?:\.\d+)?)\s*%', 'yoy_qoq_both', '同比环比同时出现需核对口径'),
    ],
    "real_asset": [
        (r'(\d+(?:\.\d+)?)\s*(亩|㎡|平方米|平米)', 'area_unit_check', '面积单位混用（亩 vs 平）需核对'),
    ],
    "cyclical": [
        (r'(\d+(?:\.\d+)?)\s*(万吨|亿吨)', 'tonnage_scale', '吨数量级需核对'),
    ],
}

# Keywords for auto-detecting technology_driven domain patterns
_TECH_KEYWORDS_RE = re.compile(r'超导|等离子|制程|激光|量子|半导体|芯片|纳米|核聚变|聚变')


def _detect_archetype_from_text(text: str) -> str | None:
    """Auto-detect technology_driven if >= 2 tech keywords found."""
    hits = len(_TECH_KEYWORDS_RE.findall(text))
    return "technology_driven" if hits >= 2 else None


def scan_file(md_path: Path, archetype: str | None = None) -> dict:
    """Scan a full-clean.md file and return suspicious_tokens dict."""
    text = md_path.read_text(encoding="utf-8")
    lines = text.split('\n')

    # Auto-detect archetype if not provided
    if archetype is None:
        archetype = _detect_archetype_from_text(text)

    flags: list[dict] = []

    # Run common patterns
    for pattern, flag_type, hint in COMMON_PATTERNS:
        compiled = re.compile(pattern)
        for i, line in enumerate(lines, start=1):
            for m in compiled.finditer(line):
                flags.append({
                    "line": i,
                    "snippet": line.strip()[:120],
                    "token": m.group(0),
                    "flag_type": flag_type,
                    "hint": hint,
                })

    # Run domain patterns if archetype is set
    if archetype and archetype in DOMAIN_PATTERNS:
        for pattern, flag_type, hint in DOMAIN_PATTERNS[archetype]:
            compiled = re.compile(pattern)
            for i, line in enumerate(lines, start=1):
                for m in compiled.finditer(line):
                    flags.append({
                        "line": i,
                        "snippet": line.strip()[:120],
                        "token": m.group(0),
                        "flag_type": flag_type,
                        "hint": hint,
                    })

    return {
        "source_path": str(md_path.resolve()),
        "scan_at": datetime.now(timezone.utc).isoformat(),
        "detected_archetype": archetype,
        "flags": sorted(flags, key=lambda f: (f["line"], f["token"])),
    }


_ARCHETYPE_CHOICES = ["technology_driven", "consumer_driven", "cyclical", "financial", "real_asset", "other"]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Scan MinerU output for suspicious tokens")
    p.add_argument("path", help="MinerU output directory or path to full-clean.md / full.md")
    p.add_argument("--archetype", choices=_ARCHETYPE_CHOICES, help="Industry archetype (auto-detected if omitted)")
    p.add_argument("--out", help="Output JSON path (default: same dir as input, suspicious_tokens.json)")
    args = p.parse_args(argv)

    input_path = Path(args.path).resolve()

    # Accept mineru output directory or direct .md path
    if input_path.is_dir():
        full_clean = input_path / "full-clean.md"
        if not full_clean.exists():
            full_clean = input_path / "full.md"
        if not full_clean.exists():
            print(f"Error: no full-clean.md or full.md in {input_path}", file=sys.stderr)
            return 1
        md_path = full_clean
    else:
        md_path = input_path

    if not md_path.exists():
        print(f"Error: {md_path} does not exist", file=sys.stderr)
        return 1

    result = scan_file(md_path, archetype=args.archetype)

    out_path = Path(args.out) if args.out else md_path.parent / "suspicious_tokens.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    detected_note = f" (auto: {result['detected_archetype']})" if args.archetype is None and result['detected_archetype'] else ""
    print(f"✓ {len(result['flags'])} flags written to {out_path}{detected_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

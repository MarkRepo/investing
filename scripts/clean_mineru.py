#!/usr/bin/env python3
"""MinerU 输出清洗脚本 — 剔除装饰图片引用，保留数据图表。

对 MinerU 产出的 full.md 逐行扫描，用规则分类每张图片：
- 数据图（keep）：图片行的上下各 1 行内有「图X」标签或「来源：」引用
- 装饰图（delete）：不满足上述条件

产出：
- full-clean.md：删除装饰图片引用的新 Markdown
- keep_images/：数据图表图片
- delete_images/：装饰图片
- classify_report.json：分类报告，记录每张图的判断依据

Usage:
    .venv/bin/python -m scripts.clean_mineru <mineru_output_dir>
"""

import json
import re
import shutil
import sys
from pathlib import Path


def classify_images(lines: list[str]) -> list[dict]:
    """Return list of image metadata with keep/delete decision."""
    results = []
    for line_idx, line in enumerate(lines):
        for m in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', line):
            alt_text = m.group(1)
            img_path = m.group(2)
            fname = Path(img_path).name

            # Context: ±2 rows (catches figure labels + source citations)
            ctx_start = max(0, line_idx - 2)
            ctx_end = min(len(lines), line_idx + 3)
            ctx = "\n".join(lines[ctx_start:ctx_end])

            has_fig_label = bool(re.search(r"图\s*\d|图表[\s.:：。]*", ctx))
            has_source = bool(re.search(r"来源[:：]", ctx))
            decision = "keep" if (has_fig_label or has_source) else "delete"

            results.append({
                "line": line_idx,
                "alt": alt_text,
                "path": img_path,
                "fname": fname,
                "keep": decision == "keep",
                "reason": {
                    "has_fig_label": has_fig_label,
                    "has_source": has_source,
                },
            })
    return results


def run(mineru_dir: Path) -> int:
    full_md = mineru_dir / "full.md"
    if not full_md.exists():
        print(f"Error: {full_md} not found", file=sys.stderr)
        return 1

    text = full_md.read_text(encoding="utf-8")
    lines = text.split("\n")
    img_dir = mineru_dir / "images"

    # Classify
    results = classify_images(lines)
    keep_count = sum(1 for r in results if r["keep"])
    delete_count = sum(1 for r in results if not r["keep"])

    # Create output directories
    keep_dir = mineru_dir / "keep_images"
    delete_dir = mineru_dir / "delete_images"
    for d in (keep_dir, delete_dir):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir()

    # Copy images and clean full.md
    delete_fnames = {r["fname"] for r in results if not r["keep"]}
    cleaned_lines = list(lines)

    for r in results:
        src = img_dir / r["fname"]
        if src.exists():
            dst = (keep_dir if r["keep"] else delete_dir) / r["fname"]
            shutil.copy2(str(src), str(dst))

        # Remove decorative image lines from cleaned output
        if not r["keep"]:
            line = cleaned_lines[r["line"]]
            # If the line only contains the image, blank it out
            if line.strip().startswith("![") and line.strip().endswith(")"):
                cleaned_lines[r["line"]] = ""
            else:
                # Remove just the image reference, keep surrounding text
                cleaned_lines[r["line"]] = re.sub(
                    r"!?\[([^\]]*)\]\(" + re.escape(r["path"]) + r"\)",
                    "",
                    line,
                )

    # Write cleaned markdown
    cleaned_md = mineru_dir / "full-clean.md"
    cleaned_md.write_text("\n".join(cleaned_lines), encoding="utf-8")

    # Write classification report
    report = {
        "source_dir": str(mineru_dir),
        "total_images": len(results),
        "keep": keep_count,
        "delete": delete_count,
        "images": results,
    }
    report_path = mineru_dir / "classify_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Total images: {len(results)}")
    print(f"  keep: {keep_count} → keep_images/")
    print(f"  delete: {delete_count} → delete_images/")
    print(f"  cleaned markdown: {cleaned_md.name}")
    print(f"  classification report: {report_path.name}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: clean_mineru <mineru_output_dir>", file=sys.stderr)
        return 1

    mineru_dir = Path(sys.argv[1]).resolve()
    if not mineru_dir.is_dir():
        print(f"Error: {mineru_dir} is not a directory", file=sys.stderr)
        return 1

    return run(mineru_dir)


if __name__ == "__main__":
    raise SystemExit(main())

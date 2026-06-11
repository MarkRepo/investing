"""macro_inputs → 门外汉输入源词典 markdown（仿 observability_render，零 LLM）。

build_body(registry)        → 按 CANONICAL_FAMILIES 分组的词典正文（不含 frontmatter）
build_glossary_md(slug,var) → 完整文件（frontmatter + body），写 outputs/00b_input_glossary.md
inject_primer_pointer(...)  → 向 00_primer.md §1 标记间注入指向句
spec: 2026-06-11-macro-input-glossary-design.md
"""
from __future__ import annotations
from pathlib import Path
from prism.scripts import macro_registry as mr

_PRISM_ROOT = Path(__file__).resolve().parent.parent

# 输入 name → primer §1 概念词条锚（显式映射，不做模糊匹配）。仅列有对应概念的。
CONCEPT_LINKS = {
    "HY OAS": "信用利差", "IG OAS": "信用利差",
    "净流动性(=资产−TGA−RRP)": "净流动性",
    "USDJPY / 日元 carry": "carry（套息）",
}


def _tier_rank(e: dict) -> int:
    return {"A": 0, "B": 1, "C": 2}.get(e.get("tier"), 9)


def build_body(registry: dict) -> str:
    inputs = registry.get("inputs") or []
    by_fam: dict[str, list] = {f: [] for f in mr.CANONICAL_FAMILIES}
    for e in inputs:
        fam = e.get("family")
        if fam in by_fam and (e.get("gloss") or {}).get("define"):
            by_fam[fam].append(e)
    lines: list[str] = []
    missing = mr.inputs_missing_gloss(registry)
    if missing:
        lines.append(f"> ⚠ 覆盖未完成：尚缺 {len(missing)} 条 gloss/family — "
                     + "、".join(missing) + "\n")
    for fam in mr.CANONICAL_FAMILIES:
        items = sorted(by_fam[fam], key=lambda e: (_tier_rank(e), e["name"]))
        if not items:
            continue
        lines.append(f"### {fam}\n")
        for e in items:
            g = e["gloss"]
            link = ""
            if e["name"] in CONCEPT_LINKS:
                link = f" · 机制见 primer 词条「{CONCEPT_LINKS[e['name']]}」"
            lines.append(f"**{e['name']}**（{e.get('tier','?')}）")
            lines.append(f"- 是什么：{g['define']}")
            lines.append(f"- 为什么看：{g['read']}")
            lines.append(f"- 怎么用：{g['use']}{link} · [表内追踪](macro-inputs)\n")
    return "\n".join(lines)

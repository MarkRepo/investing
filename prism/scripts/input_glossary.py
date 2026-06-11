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


_BEGIN = "<!-- BEGIN auto:gloss-pointer -->"
_END = "<!-- END auto:gloss-pointer -->"


def inject_primer_pointer(primer_path: Path, pointer_md: str) -> None:
    """幂等替换 primer §1 标记间内容。标记缺失则报错（须先一次性加标记）。"""
    text = primer_path.read_text(encoding="utf-8")
    if _BEGIN not in text or _END not in text:
        raise ValueError(f"primer 缺注入标记 {_BEGIN}/{_END}，须先一次性加入")
    pre, rest = text.split(_BEGIN, 1)
    _, post = rest.split(_END, 1)
    primer_path.write_text(f"{pre}{_BEGIN}\n{pointer_md}\n{_END}{post}", encoding="utf-8")


def build_glossary_md(slug: str, variant: str) -> str:
    reg = mr.read_registry(slug, variant)
    fm = ("---\n"
          f"slug: {slug}\nvariant: {variant}\noutput_key: 00b_input_glossary\n"
          "type: macro-input-glossary\nversion: 1\n"
          "title: 输入源词典 — 每个宏观输入「定义·为什么看·怎么用」\n"
          "companion: 00_primer.md / m_regime_read.md\n"
          "note: 本文件由 prism.scripts.input_glossary 机读自动生成，勿手改；改 macro_inputs.yaml 的 gloss 字段后重跑。\n"
          "---\n\n# 输入源词典\n\n"
          "> 配套 [领域入门 §1](00_primer)（概念/机制词典）。本文逐**输入源**讲「是什么/为什么看/怎么用」，按族系分组，源自 macro_inputs 登记表的 gloss 字段。\n\n")
    return fm + build_body(reg)


def write_glossary(slug: str, variant: str) -> Path:
    out = _PRISM_ROOT / "topics" / slug / variant / "outputs" / "00b_input_glossary.md"
    out.write_text(build_glossary_md(slug, variant), encoding="utf-8")
    primer = _PRISM_ROOT / "topics" / slug / variant / "outputs" / "00_primer.md"
    if primer.exists():
        ptr = ("> 📖 以上为**概念/机制**词典。每个具体**输入源**的「定义·为什么看·怎么用」"
               "见姊妹文件 [输入源词典](00b_input_glossary)（按族系分组，机读自动生成）。")
        inject_primer_pointer(primer, ptr)
    return out


if __name__ == "__main__":
    import sys
    slug, variant = sys.argv[1], sys.argv[2]
    print("written:", write_glossary(slug, variant))

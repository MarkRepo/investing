"""微信公众号版产出生成（纯显示层清洗 + 内联样式）。零 LLM、纯函数、可重放。

与 outputs.read_output_html 的区别：后者是系统内 canonical 视图（保留 mat 引用并链到
诊断页）；本模块产出的是发给公众号的独立文章——去掉对独立阅读无意义的引用 / QA banner /
修订史 / 内部指针 / 出处账本，保留 K# 并在文末追加对照表，最后把样式内联以适配公众号
编辑器（会丢弃 <style>/class/id）。绝不改动任何源文件或现有渲染路径。
"""
from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup

from . import outputs as outputs_io

_PRISM_ROOT = Path(__file__).resolve().parent.parent

# 开放微信版的产出 key（领域入门 + 三类决策链 case）。
WECHAT_OUTPUT_KEYS = ("00_primer", "c_investment_case", "i_industry_case", "a_arena_case")

# 一个 mat 引用「核」：mat-6位hex，可后接斜杠连写的 6 位 hex（mat-aaaaaa/bbbbbb）。
_MAT_RUN = r"mat-[0-9a-f]{6}(?:/[0-9a-f]{6})*"
# 括号包裹（[]/()/全角（））+ 可选前导空白 → 整体吃掉。
_BRACKETED_MAT = re.compile(r"[ \t]*[\[\(（]\s*" + _MAT_RUN + r"\s*[\]\)）]")
# 裸引用 + 可选前导空白。
_BARE_MAT = re.compile(r"[ \t]*" + _MAT_RUN)


def strip_mat_refs(text: str) -> str:
    """去除正文里的 mat-XXXXXX 资料引用（四种写法 + 斜杠连写），并收拾残留空白/悬空标点。幂等。"""
    text = _BRACKETED_MAT.sub("", text)
    text = _BARE_MAT.sub("", text)
    # 收拾残留：标点前空格、空括号、双空格。
    text = re.sub(r"[ \t]+([，。、；：！？）】」』])", r"\1", text)
    text = re.sub(r"([（【「『])[ \t]+", r"\1", text)
    text = re.sub(r"（\s*）|\(\s*\)|\[\s*\]", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text


# 需整行删除的 blockquote：banner / 修订史 / 读者画像 / 阅读假定。均为 `> …` 单行内部架子。
# 锚定行首 `>` + 特征前缀，普通 blockquote（术语锚定/提示/引述）不命中。
_DROP_BLOCKQUOTE_PATTERNS = (
    re.compile(r"^\s*>\s*🧪"),                       # 承重充分性 banner
    re.compile(r"^\s*>\s*\*\*v\d+\s*changelog", re.I),  # vN changelog 修订史
    re.compile(r"^\s*>\s*读者画像"),                  # primer 读者画像
    re.compile(r"^\s*>\s*本文假定读者"),              # case 阅读假定指针
)


def strip_blockquote_lines(text: str) -> str:
    """整行删除内部架子型 blockquote（banner/changelog/读者画像/阅读假定）。
    只命中行首 `>` + 特征前缀，普通 blockquote 不动。"""
    kept = [
        line for line in text.split("\n")
        if not any(p.match(line) for p in _DROP_BLOCKQUOTE_PATTERNS)
    ]
    return "\n".join(kept)


# 文末出处/方法论段标题（每个从其标题删到下一个 H2 或 EOF，故不会吞掉相邻别的小节）。
_SOURCES_HEADING = re.compile(r"^#{2,3}\s*(来源说明|信息来源|数据来源)\s*$")
_H2 = re.compile(r"^#{2}\s")

# 反引号包裹的内部产出 key / 文件名（c_investment_case / 00_primer(.md) / thesis_vN(.md) /
# _prism_reading_guide.md / *_decision_kit / a_arena_case / i_industry_case 等）。
_INLINE_OUTPUT_REF = re.compile(
    r"`\s*(?:_prism_reading_guide|thesis_v\d+|decomposition_v\d+|roadmap"
    r"|\d{2}[a-z]?_[a-z_]+|[cia]_[a-z_]+case|[a-z_]*decision_kit"
    r"|peer_matrix|industry_to_arenas)(?:\.\w+)?\s*`"
)


def strip_sources_section(text: str) -> str:
    """删除文末「来源说明/信息来源/数据来源」整段：从其标题删到下一个 H2 标题或文末。
    只删命名段本身，不波及相邻小节（如 industry case 的 链体检）。"""
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if _SOURCES_HEADING.match(l)), None)
    if start is None:
        return text
    end = next((j for j in range(start + 1, len(lines)) if _H2.match(lines[j])), len(lines))
    del lines[start:end]
    # 收尾去掉因删段尾留下的多余空行
    return "\n".join(lines).rstrip() + "\n"


def strip_inline_output_refs(text: str) -> str:
    """去除反引号包裹的内部产出 key / 文件名引用（独立文章里是文件名乱码）。
    普通行内代码（业务术语 `ROIC` 等）不命中。"""
    text = _INLINE_OUTPUT_REF.sub("", text)
    # 删后常见残留：成对空括号——只收拾明确的空括号。
    text = re.sub(r"（\s*）|\(\s*\)", "", text)
    return text


def parse_thesis_k_meanings(slug: str, variant: str) -> dict[str, str]:
    """从该 variant 最新 thesis_v{N}.md 的 K# 表抽 {K#: 含义}。

    容忍多种表格格式：首格可能是 `K1` 或带装饰的 `**命门1 / K1**`；取首格含 K# 的行，
    第二格（去 ** 后）作为含义。与 outputs.extract_k_status 同源（锚定 K# 表格行）。
    无 thesis / 无表 → 返回 {}（绝不抛错）。
    """
    versions = outputs_io.list_thesis_files(slug, variant)
    if not versions:
        return {}
    path = _PRISM_ROOT / "topics" / slug / variant / f"thesis_v{max(versions)}.md"
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        m = re.search(r"\bK\d+\b", cells[0])
        if not m or m.group(0) in out:
            continue
        meaning = re.sub(r"\*\*", "", cells[1]).strip()
        if meaning and not set(meaning) <= set("-: "):  # 跳过分隔行 |---|
            out[m.group(0)] = meaning
    return out


def build_k_legend_md(body_text: str, slug: str, variant: str) -> str:
    """为正文中出现的 K# 生成「命门编号对照」markdown 表。正文无 K# / 抽不到含义 → 返回 ""。"""
    ks = sorted(set(re.findall(r"\bK\d+\b", body_text)), key=lambda k: int(k[1:]))
    if not ks:
        return ""
    meanings = parse_thesis_k_meanings(slug, variant)
    rows = [(k, meanings[k]) for k in ks if k in meanings]
    if not rows:
        return ""
    lines = ["## 命门编号对照（K#）", "", "| 编号 | 含义 |", "|---|---|"]
    lines += [f"| {k} | {meaning} |" for k, meaning in rows]
    return "\n".join(lines)


# 公众号编辑器会丢弃 <style>/class/id，故逐标签内联。这张表是 WeChat-safe 的最小可保留集。
_WECHAT_STYLES = {
    "h1": "font-size:22px;font-weight:700;margin:24px 0 16px;line-height:1.4;",
    "h2": "font-size:19px;font-weight:700;margin:22px 0 12px;line-height:1.4;border-bottom:1px solid #eee;padding-bottom:6px;",
    "h3": "font-size:17px;font-weight:600;margin:18px 0 10px;line-height:1.4;",
    "p": "font-size:15px;line-height:1.75;margin:14px 0;color:#333;",
    "ul": "margin:12px 0;padding-left:22px;",
    "ol": "margin:12px 0;padding-left:22px;",
    "li": "font-size:15px;line-height:1.75;margin:6px 0;color:#333;",
    "blockquote": "border-left:3px solid #cbd5e0;padding:4px 14px;margin:14px 0;color:#666;background:#f7f8fa;",
    "table": "border-collapse:collapse;width:100%;margin:16px 0;font-size:14px;",
    "th": "border:1px solid #ddd;padding:7px 10px;background:#f5f5f5;font-weight:600;text-align:left;",
    "td": "border:1px solid #ddd;padding:7px 10px;",
    "code": "background:#f2f2f2;padding:1px 5px;border-radius:3px;font-size:13px;",
    "pre": "background:#f6f6f6;padding:12px;border-radius:4px;overflow-x:auto;font-size:13px;",
    "strong": "font-weight:700;",
    "em": "font-style:italic;",
    "hr": "border:none;border-top:1px solid #e2e2e2;margin:22px 0;",
    "a": "color:#576b95;text-decoration:none;",
}


def inline_styles(html: str) -> str:
    """把渲染后 HTML 的样式逐标签内联，并删除 class/id（公众号会丢弃）。无 <style>/<script>。"""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(True):
        style = _WECHAT_STYLES.get(tag.name)
        if style:
            tag["style"] = style + tag.get("style", "")
        tag.attrs.pop("class", None)
        tag.attrs.pop("id", None)
    return str(soup)


def clean_markdown(raw: str) -> str:
    """对原始 .md 文本做全部 markdown 层清洗（渲染前）。纯函数、幂等。"""
    text = outputs_io._strip_frontmatter(raw)
    text = strip_sources_section(text)
    text = strip_blockquote_lines(text)
    text = strip_inline_output_refs(text)
    text = strip_mat_refs(text)
    return text


def to_wechat_html(slug: str, variant: str, output_key: str) -> str:
    """生成某产出的微信公众号版自包含内联样式 HTML 片段。纯函数、零 LLM、可重放。

    流水线：读 .md → markdown 层清洗 → 追加 K# 对照表 → render_markdown（不 linkify）→ bs4 内联样式。
    """
    out_path = _PRISM_ROOT / "topics" / slug / variant / "outputs" / f"{output_key}.md"
    if not out_path.is_file():
        raise FileNotFoundError(f"Output not found: {slug}/{variant}/{output_key}")
    text = clean_markdown(out_path.read_text(encoding="utf-8"))
    legend_md = build_k_legend_md(text, slug, variant)
    if legend_md:
        text = text.rstrip() + "\n\n" + legend_md + "\n"
    html = outputs_io.render_markdown(text)  # 复用现有渲染；不调 linkify_mat_refs
    return inline_styles(html)

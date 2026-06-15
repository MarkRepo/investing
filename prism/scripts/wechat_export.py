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

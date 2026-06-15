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

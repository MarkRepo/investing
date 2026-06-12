"""美联储主席讲话文本下载（零 LLM）——与 fomc_fetch / pbc_mpr_fetch 平行的取文 fetcher。

主席讲话是**定性前瞻指引**输入（stance_scale=hawk_dove）：脚本零-LLM 从 Fed 静态 JSON feed
（ne-speeches.json）过滤最新一篇主席（Chair，非 Vice Chair）讲话、下原文到 inbox/ 本地缓存、写
local_cache_path，之后 headless LLM 用 Read 判鹰鸽立场 → 降本，且新讲话自动发现。立场判读仍归 LLM，
本脚本只取文（故该输入 availability 仍是 llm，非 scripted）。

为何脚本可达：主页 speeches-testimony.htm 为 JS 渲染（脚本取不到），但 Fed 暴露静态 JSON feed
ne-speeches.json（utf-8-sig），每条 {d:日期, t:标题, s:讲话人, l:相对链接}。speaker 字段无歧义，
过滤 'Chair' in s 且 'Vice Chair' not in s 即得主席讲话。讲话正文页为静态 HTML。

「无新讲话」非常态失败：feed 始终含历史主席讲话，故每轮都能定位「最新主席讲话」并幂等重写缓存（同 fomc）。
指纹 = 讲话相对链接（内嵌日期，发布即定型）→ 新讲话 → 指纹变 → 去重门触发 LLM 重判。

用法：
  python -m prism.scripts.fed_speech_fetch [slug] [variant]
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from html import unescape
from pathlib import Path

import httpx

from prism.scripts import macro_registry as reg

_PRISM_ROOT = Path(__file__).resolve().parent.parent
_INPUT_NAME = "美联储官员讲话(主席)"
_FED_BASE = "https://www.federalreserve.gov"
_FEED_URL = _FED_BASE + "/json/ne-speeches.json"
_CHROME_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# ── HTML helper（按本仓约定各 fetcher 自带一份，不交叉 import） ──
_SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_PARA_TAG = re.compile(r"</?(?:p|h[1-6]|blockquote|section|article)\b[^>]*/?>", re.IGNORECASE)
_BLOCK_TAG = re.compile(r"</?(?:div|li|tr|header|footer)\b[^>]*/?>|<br\b[^>]*/?>", re.IGNORECASE)
_ANY_TAG = re.compile(r"<[^>]+>")
_INLINE_WS = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{3,}")
_BODY_ENDS = ["Last Update:", "Board of Governors of the Federal Reserve System",
              "Accessibility | Contact Us | Disclaimer"]


def _strip_html(raw: str) -> str:
    raw = _SCRIPT_STYLE.sub(" ", raw)
    raw = _PARA_TAG.sub("\n\n", raw)
    raw = _BLOCK_TAG.sub("\n", raw)
    raw = _ANY_TAG.sub(" ", raw)
    raw = unescape(raw)
    lines = [_INLINE_WS.sub(" ", ln).strip() for ln in raw.splitlines()]
    text = "\n".join(ln for ln in lines if ln).strip()
    return _MULTI_NL.sub("\n\n", text)


def _extract_body(report_html: str) -> str:
    """剥标签 → 截 footer 线索。返回正文（诚实兜底：无 footer 标记则全文）。"""
    text = _strip_html(report_html)
    cut = len(text)
    for end in _BODY_ENDS:
        j = text.find(end)
        if j != -1:
            cut = min(cut, j)
    return text[:cut].strip()


def _is_chair(speaker: str | None) -> bool:
    s = speaker or ""
    return "Chair" in s and "Vice Chair" not in s


def _parse_feed_date(s: str | None) -> _dt.datetime | None:
    """feed 日期 'M/D/YYYY h:mm:ss AM/PM' → datetime；解析失败 → None。"""
    try:
        return _dt.datetime.strptime((s or "").strip(), "%m/%d/%Y %I:%M:%S %p")
    except (ValueError, AttributeError):
        return None


def pick_latest_chair(entries: list[dict]) -> dict | None:
    """从 feed 取最新一篇主席（非副主席）讲话条目。解析 d 日期取最大，防 feed 排序异常。无主席条 → None。"""
    best, best_dt = None, None
    for e in entries:
        if not _is_chair(e.get("s")):
            continue
        dt = _parse_feed_date(e.get("d"))
        if dt is None:
            continue
        if best_dt is None or dt > best_dt:
            best, best_dt = e, dt
    return best

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
# 注：<video> 一并剥除——Fed 讲话页正文容器内嵌播放器，连同 <script> 噪声一起去掉。
_SCRIPT_STYLE = re.compile(r"<(script|style|video)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
# 视频播放器的键盘帮助块（"Accessible Keys for Video..."）是 <div class="sr-only">（屏幕阅读器专用，
# 视觉隐藏的样板），剥除以免污染正文。非嵌套，非贪婪匹配到首个 </div> 即正确收尾。
_SR_ONLY = re.compile(r'<div\b[^>]*\bclass="[^"]*\bsr-only\b[^"]*"[^>]*>.*?</div>',
                      re.IGNORECASE | re.DOTALL)
_PARA_TAG = re.compile(r"</?(?:p|h[1-6]|blockquote|section|article)\b[^>]*/?>", re.IGNORECASE)
_BLOCK_TAG = re.compile(r"</?(?:div|li|tr|header|footer)\b[^>]*/?>|<br\b[^>]*/?>", re.IGNORECASE)
_ANY_TAG = re.compile(r"<[^>]+>")
_INLINE_WS = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{3,}")
# 正文容器起点锚点：Fed 讲话正文在 <div id="article">（次选 id="content"）内。匹配整个开标签并从其
# **之后**起截，跳过页头 banner / 导航 / "Skip to main content" 样板，且不在正文首行留 `id="article">` 残迹。
# article 优先（更贴正文）、content 兜底；都无则全文兜底（保留旧行为）。
_BODY_START_RES = (
    re.compile(r'<[a-z]+\b[^>]*\bid="article"[^>]*>', re.IGNORECASE),
    re.compile(r'<[a-z]+\b[^>]*\bid="content"[^>]*>', re.IGNORECASE),
)
# footer 截断线索。**不含** "Board of Governors of the Federal Reserve System"——该串也出现在页头
# banner（偏移极早），会把整篇正文误截掉（实测 powell20260321 页 banner 在偏移 533）。
_BODY_ENDS = ["Last Update:", "Accessibility | Contact Us | Disclaimer"]


def _strip_html(raw: str) -> str:
    raw = _SCRIPT_STYLE.sub(" ", raw)
    raw = _SR_ONLY.sub(" ", raw)
    raw = _PARA_TAG.sub("\n\n", raw)
    raw = _BLOCK_TAG.sub("\n", raw)
    raw = _ANY_TAG.sub(" ", raw)
    raw = unescape(raw)
    lines = [_INLINE_WS.sub(" ", ln).strip() for ln in raw.splitlines()]
    text = "\n".join(ln for ln in lines if ln).strip()
    return _MULTI_NL.sub("\n\n", text)


def _extract_body(report_html: str) -> str:
    """先定位正文容器锚点（id=article/content）跳过页头/导航样板，再剥标签、截尾部 footer 线索。
    无锚点则全文兜底（诚实降级）；无 footer 标记则保留到结尾。"""
    html = report_html
    for rx in _BODY_START_RES:
        m = rx.search(html)
        if m:
            html = html[m.end():]
            break
    text = _strip_html(html)
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


def _get(client: httpx.Client, url: str) -> httpx.Response:
    resp = client.get(url, timeout=30, follow_redirects=True,
                      headers={"User-Agent": _CHROME_UA})
    resp.raise_for_status()
    return resp


def fetch_fed_speech(slug: str, variant: str, *, client: httpx.Client | None = None,
                     input_name: str | None = None) -> dict:
    """下载最新主席讲话全文，存 inbox/fed_speech_latest.md，写 local_cache_path。

    返回 {title, speaker, date, url, cache_path, ok, fingerprint}。
    feed 抓取失败 / 无主席条 / 讲话页抓取失败 → {"error": ...}（真失败，调度器记 fetch_error 回落 llm）。
    fingerprint = 讲话相对链接（内嵌日期，发布即定型）→ 新讲话 → 指纹变 → 去重门触发 LLM 重判立场。
    """
    target = input_name or _INPUT_NAME
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        try:
            feed_resp = _get(client, _FEED_URL)
        except httpx.HTTPError as exc:
            return {"error": f"讲话 feed 抓取失败：{exc}"}
        try:
            entries = json.loads(feed_resp.content.decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError) as exc:
            return {"error": f"讲话 feed 解析失败：{exc}"}

        latest = pick_latest_chair(entries)
        if latest is None:
            return {"error": "feed 未找到主席讲话（站点结构可能变更）"}
        rel_link = latest.get("l", "")
        url = rel_link if rel_link.startswith("http") else _FED_BASE + rel_link
        title = latest.get("t", "")
        speaker = latest.get("s", "")
        date = latest.get("d", "")

        try:
            speech_html = _get(client, url).text
        except httpx.HTTPError as exc:
            return {"error": f"讲话页抓取失败（{title}）：{exc}"}
        body = _extract_body(speech_html)

        inbox_dir = _PRISM_ROOT / "topics" / slug / "inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        out_path = inbox_dir / "fed_speech_latest.md"
        lines = [
            f"# {title}",
            f"讲话人：{speaker}",
            f"日期：{date}",
            f"来源：{url}",
            "",
            body or "（正文抓取失败，仅留标题/链接——LLM 可据来源 URL 回落现场检索）",
            "",
            "---",
            "> 注：脚本零-LLM 自 Fed 讲话 feed 定位最新主席讲话并下原文存本地缓存；"
            "鹰鸽立场判读仍由 LLM 读本文件给出（observed.stance）。",
        ]
        out_path.write_text("\n".join(lines), encoding="utf-8")

        rel = str(out_path.relative_to(_PRISM_ROOT))
        reg.set_local_cache_path(slug, variant, target, rel)

        return {
            "title": title, "speaker": speaker, "date": date, "url": url,
            "cache_path": str(out_path), "ok": bool(body), "fingerprint": rel_link,
        }
    finally:
        if owns:
            client.close()


def fetch_one(slug: str, variant: str, entry: dict, *, client: httpx.Client | None = None) -> dict:
    """取文调度器入口（text_fetch=='fed_speech' 路由到此）。用 entry['name'] 作目标输入名。"""
    return fetch_fed_speech(slug, variant, client=client, input_name=entry.get("name"))


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    result = fetch_fed_speech(slug, variant)
    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)
    print(f"最新主席讲话: {result['title']}（{result['speaker']}，{result['date']}）"
          f"{'✓' if result['ok'] else '✗'}")
    print(f"来源: {result['url']}")
    print(f"缓存: {result['cache_path']}")
    print(f"指纹: {result['fingerprint']}")
    print("local_cache_path 已更新 → LLM 下次拉取将读本地文件判鹰鸽立场")


if __name__ == "__main__":
    main()

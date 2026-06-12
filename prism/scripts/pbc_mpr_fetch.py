"""央行《货币政策执行报告》(MPR) 文本下载（零 LLM）——与 fomc_fetch / politburo_fetch 平行的取文 fetcher。

MPR 是**定性政策立场**输入（无单一数值，stance_scale=ease_tighten）：脚本零-LLM 把央行最新季度
报告原文下到 inbox/ 本地缓存、写 local_cache_path，之后 macro_registry.llm_acquisition_mode 自动
返回 local_file，headless LLM 用 Read 读本地文件判「适度宽松/稳健/收紧」立场 → 降本，且季度新报告
自动发现。立场判读仍归 LLM，本脚本只取文（故该输入 availability 仍是 llm，非 scripted）。

为何脚本可达（实测）：与 gov.cn/news.cn 多数 JS 渲染页不同，PBoC 货政报告**列表页与报告正文页都是
静态 HTML（utf-8）**——列表页 `…/125957/index.html` newest-first 列出各季报 title+href；报告页带
`id="zoom"` 正文容器 + `<meta name="PubDate">`（可靠发布日）。故 raw httpx 即可发现并下载，无需浏览器。

「无新报告」非常态失败：MPR 约季度一次，但列表页**始终**展示最新一季报告，故每轮都能定位到「最新季报」
并幂等重写缓存（同 fomc）。指纹 = "mpr:YYYYQN"（发布即定型）→ 新季度报 → 指纹变 → 去重门触发 LLM 重判。

用法：
  python -m prism.scripts.pbc_mpr_fetch [slug] [variant]
"""
from __future__ import annotations

import re
import sys
from html import unescape
from pathlib import Path

import httpx

from prism.scripts import macro_registry as reg

_PRISM_ROOT = Path(__file__).resolve().parent.parent
_INPUT_NAME = "货币政策执行报告 MPR"

_PBC_BASE = "http://www.pbc.gov.cn"
_LIST_URL = _PBC_BASE + "/zhengcehuobisi/125207/125227/125957/index.html"

_CHROME_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# ── HTML helper（按本仓约定各 fetcher 自带一份，不交叉 import） ──────────────────
_SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_PARA_TAG = re.compile(r"</?(?:p|h[1-6]|blockquote|section|article)\b[^>]*/?>", re.IGNORECASE)
_BLOCK_TAG = re.compile(r"</?(?:div|li|tr|header|footer)\b[^>]*/?>|<br\b[^>]*/?>", re.IGNORECASE)
_ANY_TAG = re.compile(r"<[^>]+>")
_INLINE_WS = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{3,}")
_ANCHOR = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)

# 季报标题：YYYY年第N季度中国货币政策执行报告（N=一二三四 或 1-4）。
# 该模式天然排除「《中国货币政策执行报告》简介」与年汇总目录页「YYYY年货币政策执行报告」（皆无「第N季度」）。
_REPORT_TITLE = re.compile(r"(\d{4})\s*年第\s*([一二三四1-4])\s*季度中国货币政策执行报告")
_QUARTER_CN = {"一": 1, "二": 2, "三": 3, "四": 4, "1": 1, "2": 2, "3": 3, "4": 4}

# 报告正文容器与发布日（gov.cn TRS 标准）
_ZOOM_OPEN = re.compile(r'<div\b[^>]*\bid="zoom"[^>]*>', re.IGNORECASE)
_PUBDATE = re.compile(r'name="PubDate"\s+content="([0-9-]+)"', re.IGNORECASE)
_BODY_ENDS = ["中国人民银行版权所有", "网站地图", "京ICP", "扫一扫在手机打开", "打印本页", "关闭窗口"]


def _strip_html(raw: str) -> str:
    raw = _SCRIPT_STYLE.sub(" ", raw)
    raw = _PARA_TAG.sub("\n\n", raw)
    raw = _BLOCK_TAG.sub("\n", raw)
    raw = _ANY_TAG.sub(" ", raw)
    raw = unescape(raw)
    lines = [_INLINE_WS.sub(" ", ln).strip() for ln in raw.splitlines()]
    text = "\n".join(ln for ln in lines if ln).strip()
    return _MULTI_NL.sub("\n\n", text)


def _abs_url(href: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return "http:" + href
    return _PBC_BASE + href


def _find_latest_report(index_html: str) -> tuple[str, str, int, int] | None:
    """扫列表页锚，匹配「YYYY年第N季度中国货币政策执行报告」标题，按 (年, 季) 取最新。
    返回 (绝对url, 标题, 年, 季)；无命中 → None。简介/年汇总页天然不匹配（无「第N季度」）。"""
    best: tuple[str, str, int, int] | None = None
    for m in _ANCHOR.finditer(index_html):
        href = m.group(1)
        title = _INLINE_WS.sub(" ", _ANY_TAG.sub(" ", m.group(2))).strip()
        tm = _REPORT_TITLE.search(title)
        if not tm:
            continue
        year = int(tm.group(1))
        quarter = _QUARTER_CN[tm.group(2)]
        if best is None or (year, quarter) > (best[2], best[3]):
            best = (_abs_url(href), title, year, quarter)
    return best


def _extract_body(report_html: str) -> tuple[str, str | None]:
    """从报告页截正文：定位 id="zoom" 容器 → 剥标签 → 截 footer 线索。返回 (正文, 发布日|None)。
    无 zoom 容器 → 退回整页剥标签（诚实兜底）。发布日取 <meta name="PubDate">。"""
    dm = _PUBDATE.search(report_html)
    pubdate = dm.group(1) if dm else None
    zm = _ZOOM_OPEN.search(report_html)
    seg = report_html[zm.end():] if zm else report_html
    text = _strip_html(seg)
    cut = len(text)
    for end in _BODY_ENDS:
        j = text.find(end)
        if j != -1:
            cut = min(cut, j)
    return text[:cut].strip(), pubdate


def _get(client: httpx.Client, url: str) -> str:
    resp = client.get(url, timeout=30, follow_redirects=True,
                      headers={"User-Agent": _CHROME_UA})
    resp.raise_for_status()
    if not resp.encoding:
        resp.encoding = "utf-8"
    return resp.text


# ── 合并入口 ────────────────────────────────────────────────────────────────
def fetch_pbc_mpr(slug: str, variant: str, *, client: httpx.Client | None = None,
                  input_name: str | None = None) -> dict:
    """下载央行最新季度货政报告全文，存 inbox/pbc_mpr_latest.md，写 local_cache_path。

    返回 {"title", "year", "quarter", "pubdate", "url", "cache_path", "ok", "fingerprint"}。
    列表页抓取失败 / 未找到季报 / 报告页抓取失败 → {"error": ...}（真失败，调度器记 fetch_error 回落 llm）。
    fingerprint = "mpr:YYYYQN"（发布即定型）→ 新季度报 → 指纹变 → 去重门触发 LLM 重判立场。
    """
    target_name = input_name or _INPUT_NAME
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        try:
            index_html = _get(client, _LIST_URL)
        except httpx.HTTPError as exc:
            return {"error": f"MPR 列表页抓取失败：{exc}"}

        latest = _find_latest_report(index_html)
        if latest is None:
            return {"error": "MPR 列表页未找到季度报告（站点结构可能变更）"}
        url, title, year, quarter = latest

        try:
            report_html = _get(client, url)
        except httpx.HTTPError as exc:
            return {"error": f"MPR 报告页抓取失败（{title}）：{exc}"}
        body, pubdate = _extract_body(report_html)

        inbox_dir = _PRISM_ROOT / "topics" / slug / "inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        out_path = inbox_dir / "pbc_mpr_latest.md"
        lines = [
            f"# {title}",
            f"来源：{url}",
            f"发布日：{pubdate or '?'}",
            "",
            body or "（正文抓取失败，仅留标题/链接——LLM 可据来源 URL 回落现场检索）",
            "",
            "---",
            "> 注：脚本零-LLM 自 PBoC 货政司列表页定位最新季报并下原文存本地缓存；"
            "「适度宽松/稳健/收紧」松紧立场判读仍由 LLM 读本文件给出（observed.stance）。",
        ]
        out_path.write_text("\n".join(lines), encoding="utf-8")

        rel = str(out_path.relative_to(_PRISM_ROOT))
        reg.set_local_cache_path(slug, variant, target_name, rel)

        return {
            "title": title,
            "year": year,
            "quarter": quarter,
            "pubdate": pubdate,
            "url": url,
            "cache_path": str(out_path),
            "ok": bool(body),
            "fingerprint": f"mpr:{year}Q{quarter}",
        }
    finally:
        if owns:
            client.close()


def fetch_one(slug: str, variant: str, entry: dict, *, client: httpx.Client | None = None) -> dict:
    """取文调度器入口（text_fetch=='pbc_mpr' 路由到此）。用 entry['name'] 作目标输入名。"""
    return fetch_pbc_mpr(slug, variant, client=client, input_name=entry.get("name"))


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    result = fetch_pbc_mpr(slug, variant)
    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)
    print(f"最新季报: {result['title']}（发布 {result['pubdate']}）{'✓' if result['ok'] else '✗'}")
    print(f"来源: {result['url']}")
    print(f"缓存: {result['cache_path']}")
    print(f"指纹: {result['fingerprint']}")
    print("local_cache_path 已更新 → LLM 下次拉取将读本地文件判货币政策松/紧立场")


if __name__ == "__main__":
    main()

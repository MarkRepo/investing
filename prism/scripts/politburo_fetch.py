"""中国政治局/NPC 经济信号 文本下载（零 LLM）——双 feed：english.gov.cn 要闻 + 最新政策。

与 fomc_fetch / qra_fetch / china_us_fetch 平行的「取文」fetcher。该输入无单一数值（政治局/NPC
定调是政策叙事），故走取文通道：脚本零-LLM 把权威原文下到 inbox/ 本地缓存、写 local_cache_path，
之后 macro_registry.llm_acquisition_mode 自动返回 local_file，headless LLM 用 Read 读本地文件判
松/紧立场，不再每轮 live 检索 → 降本。立场判读仍归 LLM，本脚本只取文。

为何用英文官方镜像：中方原生站（gov.cn/news.cn）索引全 JS 渲染、搜索是带客户端签名的 Athena API
（appKey/sign 动态算）→ 脚本驱动脆、易静默失效。english.www.gov.cn 是干净静态 HTML、倒序索引、
标题可关键词过滤，政治局经济会议 readout 与政府工作报告/国务院政策都静态发现（实证）。

双 feed（一个 fetcher 抓两 feed、合并入一份缓存）：
  · /news/                    = 政治局经济会议 readout + 要闻（综合 feed，靠关键词过滤会议/政策标题）。
  · /policies/latestreleases/ = NPC 政府工作报告 + 国务院政策释放。
  两 feed 同站、同 content_WS<hash>.html 锚结构，解析复用，极稳。

「无新会议」≠ 失败（经济政治局会议约季度一次，多数日子 feed 内无新 readout）：
  · 两 feed 200 但无关键词命中 → 不记 fetch_error；保留既有缓存不覆盖；ok=True；
    fingerprint 由重解析缓存内 hash 集得出 → 与上轮相同 → 去重门不误触发。
  · 首跑无命中（暂无缓存）→ 写占位缓存，ok=True。
  · 仅当两 feed 索引抓取本身全挂 → ok=False/error → 调度器记 fetch_error（真失败，回落 llm）。

指纹 = "polit:" + 缓存内 content_WS hash 集（发布即定型）→ 新会议 readout → 指纹变 → 去重门触发 LLM 重判。

用法：
  python -m prism.scripts.politburo_fetch [slug] [variant]
"""
from __future__ import annotations

import re
import sys
from html import unescape
from pathlib import Path

import httpx

from prism.scripts import macro_registry as reg

_PRISM_ROOT = Path(__file__).resolve().parent.parent
_INPUT_NAME = "中国政治局/NPC 经济信号"
_MAX_ITEMS = 5

_CHROME_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
_GOV_BASE = "https://english.www.gov.cn"
_NEWS_INDEX = _GOV_BASE + "/news/"                       # 政治局经济会议 readout + 要闻
_POLICY_INDEX = _GOV_BASE + "/policies/latestreleases/"  # NPC 政府工作报告 + 国务院政策

# 只留会议/宏观政策标题——/news/ 是综合 feed，含大量外交/DPRK 噪声；不用裸 economic/policy（过度命中）。
_KEYWORDS = (
    "political bureau", "cpc leadership", "politburo",
    "central economic work", "economic situation", "economic work",
    "government work report", "work of the government", "two sessions",
    "national people's congress", "npc standing committee",
    "state council executive meeting", "executive meeting of the state council",
    "fiscal policy", "monetary policy",
)

# ── HTML helper（按本仓约定各 fetcher 自带一份，不交叉 import） ──────────────────
_SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_PARA_TAG = re.compile(r"</?(?:p|h[1-6]|blockquote|section|article)\b[^>]*/?>", re.IGNORECASE)
_BLOCK_TAG = re.compile(r"</?(?:div|li|tr|header|footer)\b[^>]*/?>|<br\b[^>]*/?>", re.IGNORECASE)
_ANY_TAG = re.compile(r"<[^>]+>")
_INLINE_WS = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{3,}")
_ANCHOR = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)

# 真文章 href：.../YYYYMM/DD/content_WS<hash>.html（content_WS+日期段够独特，前缀不限——
# /news/、/policies/latestreleases/ 等中间段各异；兼容协议相对/根相对/绝对）。
_ARTICLE_HREF = re.compile(r'/\d{6}/\d{2}/content_WS[0-9a-f]+\.html', re.IGNORECASE)
_HASH_RE = re.compile(r"content_WS([0-9a-f]+)", re.IGNORECASE)

# 正文容器与起止线索
_CONTENT_ANCHOR = "Artical_Content"            # english.gov.cn 文章正文 div class（实证）
_DATELINE = re.compile(r"[A-Z]{3,},\s+[A-Z][a-z]+\.?\s*\d{1,2}")   # "BEIJING, Dec. 8 --"
_BODY_ENDS = ["Copyright", "Back to the top", "Back to top", "Scan the QR", "Editor:", "Share to"]
_DATE = re.compile(r"Updated:\s*([A-Z][a-z]+ \d{1,2}, \d{4})")      # "Updated: December 8, 2025 14:38"


def _strip_html(raw: str) -> str:
    raw = _SCRIPT_STYLE.sub(" ", raw)
    raw = _PARA_TAG.sub("\n\n", raw)
    raw = _BLOCK_TAG.sub("\n", raw)
    raw = _ANY_TAG.sub(" ", raw)
    raw = unescape(raw)
    lines = [_INLINE_WS.sub(" ", ln).strip() for ln in raw.splitlines()]
    text = "\n".join(ln for ln in lines if ln).strip()
    return _MULTI_NL.sub("\n\n", text)


def _hash_of(url: str) -> str:
    m = _HASH_RE.search(url)
    return m.group(1) if m else url


def _abs_url(href: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return "https:" + href
    return _GOV_BASE + href


def _find_items(index_html: str) -> list[tuple[str, str]]:
    """扫索引页锚，href 配真文章模式 且 标题含任一关键词的会议/政策稿，保序去重（页面 newest-first），取前 _MAX_ITEMS。"""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for m in _ANCHOR.finditer(index_html):
        href = m.group(1)
        if not _ARTICLE_HREF.search(href):
            continue
        title = _INLINE_WS.sub(" ", _ANY_TAG.sub(" ", m.group(2))).strip()
        low = title.lower()
        if not any(kw in low for kw in _KEYWORDS):
            continue
        h = _hash_of(href)
        if h in seen:
            continue
        seen.add(h)
        out.append((_abs_url(href), title))
        if len(out) >= _MAX_ITEMS:
            break
    return out


def _extract_body(raw_html: str) -> str:
    """从文章 HTML 截正文：定位 Artical_Content 容器 → 剥标签 → dateline(BEIJING,…--) 起、footer 止。"""
    idx = raw_html.find(_CONTENT_ANCHOR)
    seg = raw_html[idx:] if idx != -1 else raw_html
    text = _strip_html(seg)
    m = _DATELINE.search(text)
    if m:
        text = text[m.start():]
    cut = len(text)                       # 截最早出现的 footer 线索（非列表序首个）
    for end in _BODY_ENDS:
        j = text.find(end)
        if j != -1:
            cut = min(cut, j)
    return text[:cut].strip()


def _fetch_body(url: str, client: httpx.Client) -> tuple[str, str | None]:
    """下载文章，返回 (正文, 日期串|None)。"""
    resp = client.get(url, timeout=30, follow_redirects=True, headers={"User-Agent": _CHROME_UA})
    resp.raise_for_status()
    raw = resp.text
    dm = _DATE.search(raw)
    return _extract_body(raw), (dm.group(1) if dm else None)


# ── 合并入口 ────────────────────────────────────────────────────────────────
def fetch_politburo(slug: str, variant: str, *, client: httpx.Client | None = None,
                    input_name: str | None = None) -> dict:
    """抓 /news/ + /policies/latestreleases/ 命中的会议/政策稿，合并存 inbox/politburo_npc_latest.md。

    返回 {"items", "cache_path", "ok", "fingerprint"(, "note")}。
    两 feed 索引全挂 → {"error": ...}（真失败）；无命中但索引 ok → 保留/占位缓存、ok=True。
    fingerprint = "polit:" + 缓存内 hash 集 —— 新会议 → 指纹变 → 去重门触发 LLM 重判。
    """
    target_name = input_name or _INPUT_NAME
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        feeds = [("政治局经济会议 / 要闻", _NEWS_INDEX),
                 ("NPC 政府工作报告 / 国务院政策", _POLICY_INDEX)]
        sections: list[tuple[str, list[dict], str | None]] = []
        index_errors = 0
        for heading, idx_url in feeds:
            items: list[dict] = []
            err: str | None = None
            try:
                r = client.get(idx_url, timeout=30, follow_redirects=True,
                               headers={"User-Agent": _CHROME_UA})
                r.raise_for_status()
                for url, title in _find_items(r.text):
                    try:
                        body, date_s = _fetch_body(url, client)
                    except httpx.HTTPError:
                        body, date_s = "", None
                    items.append({"url": url, "title": title, "date": date_s,
                                  "body": body, "hash": _hash_of(url)})
            except httpx.HTTPError as exc:          # 该 feed 改版/网络挂 → 仅丢本 feed
                err = str(exc)
                index_errors += 1
            sections.append((heading, items, err))

        all_items = [it for _, items, _ in sections for it in items]
        inbox_dir = _PRISM_ROOT / "topics" / slug / "inbox"
        out_path = inbox_dir / "politburo_npc_latest.md"

        # 两 feed 索引全挂 → 真失败（调度器记 fetch_error，回落 llm）
        if index_errors == len(feeds):
            return {"error": "两 feed 索引全挂：" +
                    "; ".join(f"{h}: {e}" for h, _, e in sections if e)}

        rel = lambda: str(out_path.relative_to(_PRISM_ROOT))

        # 无命中（多数日子）：不算失败
        if not all_items:
            if out_path.exists():                   # 保留既有缓存，指纹由其 hash 集得出（与上轮同）
                prior = out_path.read_text(encoding="utf-8")
                hashes = sorted(set(_HASH_RE.findall(prior)))
                reg.set_local_cache_path(slug, variant, target_name, rel())
                return {"items": [], "cache_path": str(out_path), "ok": True,
                        "fingerprint": "polit:" + "|".join(hashes),
                        "note": "feed 窗口内无新会议，保留既有缓存"}
            inbox_dir.mkdir(parents=True, exist_ok=True)   # 首跑无命中 → 占位
            placeholder = (
                "# 中国政治局经济会议 + 国务院/NPC 政策（english.gov.cn 双 feed · 静态官方镜像）\n"
                f"来源：{_NEWS_INDEX} ＋ {_POLICY_INDEX}\n\n"
                "（本轮 feed 窗口内无新政治局/NPC 经济会议 readout——经济政治局会议约季度一次。"
                "待下次会议自动补抓；此前 LLM 可回落现场检索或沿用上次立场。）\n\n"
                "---\n"
                "> 注：仅英文官方镜像(english.gov.cn)、略滞后；中央经济工作会议全文/中文细节/"
                "省部级解读需 LLM 在此之上补判。\n")
            out_path.write_text(placeholder, encoding="utf-8")
            reg.set_local_cache_path(slug, variant, target_name, rel())
            return {"items": [], "cache_path": str(out_path), "ok": True,
                    "fingerprint": "polit:", "note": "首跑无命中，写占位缓存"}

        # 有命中 → 写新缓存
        inbox_dir.mkdir(parents=True, exist_ok=True)
        lines = ["# 中国政治局经济会议 + 国务院/NPC 政策（english.gov.cn 双 feed · 静态官方镜像）",
                 f"来源：{_NEWS_INDEX} ＋ {_POLICY_INDEX}", ""]
        for heading, items, err in sections:
            lines += ["", f"## {heading}"]
            if items:
                for it in items:
                    meta = it["date"] or ""
                    lines += ["", f"### {it['title']}（{meta}）" if meta else f"### {it['title']}",
                              f"来源：{it['url']}", "",
                              it["body"] or "（正文抓取失败，仅留标题/链接）"]
            else:
                lines += ["", f"（本 feed 无命中{('：' + err) if err else ''}）"]
        lines += ["", "---", "",
                  "> 注：仅英文官方镜像(english.gov.cn)、略滞后；中央经济工作会议全文/中文细节/"
                  "省部级解读需 LLM 在此之上补判。"]
        out_path.write_text("\n".join(lines), encoding="utf-8")
        reg.set_local_cache_path(slug, variant, target_name, rel())

        hashes = sorted(set(it["hash"] for it in all_items))
        return {
            "items": [{k: it[k] for k in ("url", "title", "date")} for it in all_items],
            "cache_path": str(out_path),
            "ok": True,
            "fingerprint": "polit:" + "|".join(hashes),
        }
    finally:
        if owns:
            client.close()


def fetch_one(slug: str, variant: str, entry: dict, *, client: httpx.Client | None = None) -> dict:
    """取文调度器入口（text_fetch=='politburo' 路由到此）。用 entry['name'] 作目标输入名。"""
    return fetch_politburo(slug, variant, client=client, input_name=entry.get("name"))


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    result = fetch_politburo(slug, variant)
    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)
    items = result["items"]
    print(f"命中 {len(items)} 条政治局/政策稿")
    for it in items:
        print(f"  · {it['date'] or '?'}  {it['title'][:64]}")
    if result.get("note"):
        print(f"说明: {result['note']}")
    print(f"缓存: {result['cache_path']}")
    print(f"指纹: {result['fingerprint']}")
    print("local_cache_path 已更新 → LLM 下次拉取将读本地文件判中国政策松/紧立场")


if __name__ == "__main__":
    main()

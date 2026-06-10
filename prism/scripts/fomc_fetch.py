"""FOMC 声明/纪要文本下载（零 LLM）。

从 Fed 日历页提取最新声明/纪要 URL → 下载 HTML → 剥标签 → 合并存 inbox/fomc_latest.md。
更新 macro_inputs.yaml 的 local_cache_path，供 headless LLM 以 Read 工具读本地文件判断鹰鸽立场。

用法：
  python -m prism.scripts.fomc_fetch [slug] [variant]
"""
from __future__ import annotations

import re
import sys
from html import unescape
from pathlib import Path

import httpx

from prism.scripts import macro_registry as reg

_PRISM_ROOT = Path(__file__).resolve().parent.parent
_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
_FED_BASE = "https://www.federalreserve.gov"
_INPUT_NAME = "FOMC 声明/纪要"

_SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_PARA_TAG = re.compile(r"</?(?:p|h[1-6]|blockquote|section|article)\b[^>]*/?>", re.IGNORECASE)
_BLOCK_TAG = re.compile(r"</?(?:div|li|tr|header|footer)\b[^>]*/?>|<br\b[^>]*/?>", re.IGNORECASE)
_ANY_TAG = re.compile(r"<[^>]+>")
_INLINE_WS = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{3,}")

# URL 规律（均含 8 位日期，取排序最大的即最新）
_STMT_PAT = re.compile(r'/newsevents/pressreleases/monetary(\d{8})a\.htm')
_MINS_PAT = re.compile(r'/monetarypolicy/fomcminutes(\d{8})\.htm')

# 正文起始标记（按优先级尝试）
_STMT_STARTS = ["For release at", "FOR IMMEDIATE RELEASE", "Information received"]
_MINS_STARTS = ["Minutes of the Federal Open Market Committee", "A joint meeting of the Federal"]
# 正文结束标记（遇到即截断）
_BODY_ENDS = ["Last Update:", "Board of Governors of the Federal Reserve System\nThe Federal Reserve",
              "Accessibility | Contact Us | Disclaimer"]


def _strip_html(raw: str) -> str:
    raw = _SCRIPT_STYLE.sub(" ", raw)
    raw = _PARA_TAG.sub("\n\n", raw)  # 段落标签 → 双换行（保留段落结构）
    raw = _BLOCK_TAG.sub("\n", raw)   # 其余块级标签 → 单换行
    raw = _ANY_TAG.sub(" ", raw)
    raw = unescape(raw)
    lines = [_INLINE_WS.sub(" ", ln).strip() for ln in raw.splitlines()]
    text = "\n".join(ln for ln in lines if ln).strip()
    return _MULTI_NL.sub("\n\n", text)  # 压缩连续空行


def _extract_body(text: str, start_markers: list[str]) -> str:
    """从已剥标签的纯文本中提取正文：从第一个匹配的起始标记开始，到结束标记前截断。"""
    start = -1
    for m in start_markers:
        idx = text.find(m)
        if idx != -1:
            start = idx
            break
    if start == -1:
        return text  # 找不到标记则保留全文
    body = text[start:]
    for end_m in _BODY_ENDS:
        idx = body.find(end_m)
        if idx != -1:
            body = body[:idx]
            break
    return body.strip()


def _fetch_text(url: str, client: httpx.Client, start_markers: list[str] | None = None) -> str:
    resp = client.get(url, timeout=30, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    plain = _strip_html(resp.text)
    if start_markers:
        return _extract_body(plain, start_markers)
    return plain


def _latest_url(html: str, pattern: re.Pattern) -> tuple[str, str] | tuple[None, None]:
    """从日历页 HTML 提取最新（日期最大）的匹配 URL。返回 (relative_path, date_str)。"""
    hits = pattern.findall(html)
    if not hits:
        return None, None
    latest_date = max(hits)
    path = pattern.pattern.replace(r'(\d{8})', latest_date).replace(r'\.', '.')
    # 重建完整路径
    full_path = re.sub(r'\(.*?\)', latest_date,
                       pattern.pattern.replace(r'\.', '.').replace(r'\b', '').replace(r'\/', '/'))
    # 直接用字符串替换更稳
    raw_path = pattern.pattern.replace(r'(\d{8})', latest_date)\
                               .replace(r'\.', '.').replace(r'\b', '')\
                               .replace(r'\/', '/').replace(r'\w', '').replace(r'[^>]', '')
    # 最简方式：找对应的完整 href
    date_escaped = latest_date
    for m in re.finditer(pattern, html):
        if m.group(1) == date_escaped:
            return m.group(0), latest_date
    return None, None


def fetch_fomc_texts(slug: str, variant: str, *, client: httpx.Client | None = None,
                     input_name: str | None = None) -> dict:
    """下载最新 FOMC 声明/纪要文本，合并存 inbox/fomc_latest.md，更新 local_cache_path。

    input_name：要写 local_cache_path 的登记项名。缺省 _INPUT_NAME（CLI 直跑兼容）；
    被 textfetch 调度器复用时由调度器按登记项传入（见 fetch_one），故本 fetcher 不再写死单一输入名。
    返回 {"statement_date", "minutes_date", "cache_path", "statement_ok", "minutes_ok", "ok", "fingerprint"}。
    """
    target_name = input_name or _INPUT_NAME
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        # 1. 拉日历页
        cal_resp = client.get(_CALENDAR_URL, timeout=30, follow_redirects=True,
                              headers={"User-Agent": "Mozilla/5.0"})
        cal_resp.raise_for_status()
        cal_html = cal_resp.text

        # 2. 提取最新 URL
        stmt_hits = sorted(set(_STMT_PAT.findall(cal_html)), reverse=True)
        mins_hits = sorted(set(_MINS_PAT.findall(cal_html)), reverse=True)
        if not stmt_hits:
            return {"error": "日历页未找到声明链接"}

        stmt_date = stmt_hits[0]
        stmt_path = f"/newsevents/pressreleases/monetary{stmt_date}a.htm"
        mins_date = mins_hits[0] if mins_hits else None
        mins_path = f"/monetarypolicy/fomcminutes{mins_date}.htm" if mins_date else None

        # 3. 下载文本（裁剪到正文，保留完整内容）
        stmt_text = _fetch_text(_FED_BASE + stmt_path, client, _STMT_STARTS)
        stmt_ok = bool(stmt_text)

        mins_text = None
        mins_ok = False
        if mins_path:
            try:
                mins_text = _fetch_text(_FED_BASE + mins_path, client, _MINS_STARTS)
                mins_ok = bool(mins_text)
            except httpx.HTTPError:
                pass  # 纪要尚未发布时正常 404

        # 4. 合并写 inbox/fomc_latest.md
        inbox_dir = _PRISM_ROOT / "topics" / slug / "inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        out_path = inbox_dir / "fomc_latest.md"

        sections = [f"# FOMC 声明（{stmt_date[:4]}-{stmt_date[4:6]}-{stmt_date[6:]}）",
                    f"来源：{_FED_BASE + stmt_path}", "",
                    stmt_text]
        if mins_text:
            mins_fmt = f"{mins_date[:4]}-{mins_date[4:6]}-{mins_date[6:]}"
            sections += ["", "---", "",
                         f"# FOMC 纪要（{mins_fmt}）",
                         f"来源：{_FED_BASE + mins_path}", "",
                         mins_text]

        out_path.write_text("\n".join(sections), encoding="utf-8")

        # 5. 更新 local_cache_path（相对 _PRISM_ROOT）
        rel = str(out_path.relative_to(_PRISM_ROOT))
        reg.set_local_cache_path(slug, variant, target_name, rel)

        return {
            "statement_date": stmt_date,
            "minutes_date": mins_date,
            "cache_path": str(out_path),
            "statement_ok": stmt_ok,
            "minutes_ok": mins_ok,
            "ok": stmt_ok,   # 取文调度器/批量计数统一读 ok（声明下到即算成功，纪要可后发）
            # 稳定身份指纹（声明/纪要 URL 内嵌日期，发布即定型，不受正文易变内容影响）。
            # 去重门据此判「资料是否变化」，相同则不再二次判读。
            "fingerprint": f"{stmt_path}|{mins_path or ''}",
        }
    finally:
        if owns:
            client.close()


def fetch_one(slug: str, variant: str, entry: dict, *, client: httpx.Client | None = None) -> dict:
    """取文调度器入口（text_fetch=='fomc' 路由到此）。

    与 fetch_fomc_texts 唯一差别：用 entry['name'] 作目标输入名（而非写死 _INPUT_NAME），
    使本 FOMC 抓法成为登记表驱动通道下的一个 fetcher——加别的取文源只需另写 fetch_one 并注册，
    互不写死。返回 fetch_fomc_texts 的 dict（含 ok / fingerprint，供去重门与批量计数用）。"""
    return fetch_fomc_texts(slug, variant, client=client, input_name=entry.get("name"))


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    result = fetch_fomc_texts(slug, variant)
    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)
    print(f"声明: {result['statement_date']} {'✓' if result['statement_ok'] else '✗'}")
    print(f"纪要: {result['minutes_date']} {'✓' if result['minutes_ok'] else '✗（尚未发布）'}")
    print(f"缓存: {result['cache_path']}")
    print(f"local_cache_path 已更新 → LLM 下次拉取将读本地文件")


if __name__ == "__main__":
    main()

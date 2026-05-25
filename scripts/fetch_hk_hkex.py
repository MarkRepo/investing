"""Download Hong Kong stock filings (annual reports / interim reports / prospectuses)
from HKEXnews (https://www.hkexnews.hk).

零依赖 scraping —— 无需 API key。流程：
    1. prefix.do (JSONP) — ticker → 内部 stockId（必须精确匹配 5 位 code，否则前缀污染）
    2. titleSearchServlet.do (JSON) — stockId → announcements 列表
    3. 按 TITLE 关键词过滤 (Annual Report / Interim Report / Prospectus + 中文等价)
    4. 取最新一份，下载 PDF

Usage:
    python -m scripts.fetch_hk_hkex 02228                            # 晶泰科技 最新 Annual Report
    python -m scripts.fetch_hk_hkex 02228 --type semi                # 中期报告
    python -m scripts.fetch_hk_hkex 02228 --type prospectus          # 招股章程
    python -m scripts.fetch_hk_hkex 02228 --slug global-ai-drug-gene-edit  # 入 prism

Notes:
    - HK 公司不强制季报，本脚本不支持 quarterly
    - HKEX 强制中英文双语披露，默认取 EN 版本（按 TITLE 关键词），不提供同时双下
    - prospectus 时间窗放宽到 10 年（IPO 文档可能很早）
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

log = logging.getLogger("fetch_hk_hkex")

_HOST = "https://www1.hkexnews.hk"
_PREFIX_URL = f"{_HOST}/search/prefix.do"
_SEARCH_URL = f"{_HOST}/search/titleSearchServlet.do"
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0"
_REFERER = f"{_HOST}/search/titlesearch.xhtml"

_INBOX_AUTO = Path(__file__).parent.parent / "prism" / "inbox" / "auto"


def _materials_dir(slug: str) -> Path:
    return Path(__file__).parent.parent / "prism" / "topics" / slug / "materials"


# HKEX 官方 LONG_TEXT 分类前缀过滤（比 TITLE 关键词稳健，避免摘要/通函污染）
# LONG_TEXT 实际形如 "Financial Statements&#x2f;ESG Information - [Annual Report]"
_LONG_TEXT_CATEGORIES = {
    "annual":     ["Financial Statements", "Annual Report"],           # 双重 contains
    "semi":       ["Financial Statements", "Interim"],                  # Interim/Half-Year Report
    "prospectus": ["Listing Documents"],                                # 单一 contains
}

# 时间窗口（年）
_YEAR_WINDOW = {
    "annual":     2,
    "semi":       2,
    "prospectus": 10,
}

# API rowRange 上限（实测 500 对大部分公司够用）
_ROW_RANGE = 500


def _http_get_text(url: str) -> str:
    headers = {"User-Agent": _UA, "Referer": _REFERER}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def _http_get_bytes(url: str) -> bytes:
    headers = {"User-Agent": _UA, "Referer": _REFERER}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def _zfill5(code: str) -> str:
    """'2228' → '02228' / '02228' → '02228'."""
    code = code.strip().lstrip("0")
    return code.zfill(5)


def _resolve_stock_id(ticker: str) -> tuple[int, str]:
    """ticker → (stockId, company_name). Filter by exact 5-digit code match."""
    code = _zfill5(ticker)
    qs = urllib.parse.urlencode({
        "callback": "callback",
        "lang": "EN",
        "type": "A",
        "name": code,
        "market": "SEHK",
    })
    body = _http_get_text(f"{_PREFIX_URL}?{qs}")
    # 解 JSONP: callback({...});
    m = re.search(r"callback\((.+)\);?\s*$", body, re.S)
    if not m:
        raise ValueError(f"HKEX prefix.do 返回格式异常：{body[:200]!r}")
    payload = json.loads(m.group(1))
    candidates = payload.get("stockInfo") or []
    # 精确匹配 5 位 code（防 02228 → [22283, 22284, ...] 前缀污染）
    for c in candidates:
        if str(c.get("code", "")).zfill(5) == code:
            return int(c["stockId"]), c.get("name", "").strip()
    raise ValueError(
        f"HKEX 未找到 ticker={code}（候选: {[c['code'] for c in candidates[:5]]}）"
    )


def _list_announcements(stock_id: int, years_back: int) -> list[dict]:
    """List announcements for stockId in the last years_back years."""
    today = date.today()
    from_date = today.replace(year=today.year - years_back).strftime("%Y%m%d")
    to_date = today.strftime("%Y%m%d")
    qs = urllib.parse.urlencode({
        "sortDir": "0",
        "sortByOptions": "DateTime",
        "category": "0",
        "market": "SEHK",
        "stockId": str(stock_id),
        "documentType": "-1",
        "fromDate": from_date,
        "toDate": to_date,
        "title": "",
        "t1code": "-2",
        "t2Gp": "-2",
        "t2code": "-2",
        "lang": "EN",
        "rowRange": str(_ROW_RANGE),
    })
    body = _http_get_text(f"{_SEARCH_URL}?{qs}")
    data = json.loads(body)
    raw = data.get("result")
    if not raw or raw == "null":
        return []
    anns = json.loads(raw)
    if data.get("hasNextRow"):
        log.warning(
            "HKEX 返回 %d 条且 hasNextRow=True — 公司公告量超 rowRange，"
            "可能漏掉早期报告。如需历史报告请缩短 fromDate 窗口或分段拉取。",
            len(anns),
        )
    return anns


def _decode_html_entities(s: str) -> str:
    """HKEX LONG_TEXT 含 &#x2f; 等实体，简单解码。"""
    import html
    return html.unescape(s)


def _filter_by_type(announcements: list[dict], report_type: str) -> list[dict]:
    """按 HKEX 官方 LONG_TEXT 分类过滤（含多个关键词时全部命中）。"""
    if report_type not in _LONG_TEXT_CATEGORIES:
        raise ValueError(f"不支持的 report_type: {report_type}（支持：{list(_LONG_TEXT_CATEGORIES)}）")
    keywords = _LONG_TEXT_CATEGORIES[report_type]
    out = []
    for a in announcements:
        long_text = _decode_html_entities(a.get("LONG_TEXT", ""))
        if all(kw in long_text for kw in keywords):
            out.append(a)
    return out


def _parse_publish_date(date_time: str) -> str:
    """'17/04/2026 20:53' → '2026-04-17'."""
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", date_time)
    if not m:
        return date.today().isoformat()
    d, mth, y = m.groups()
    return f"{y}-{mth}-{d}"


def _extract_report_year(title: str, publish_date: str) -> int:
    """'Annual Report 2025' → 2025；fallback 发布年份。"""
    m = re.search(r"(20\d{2})", title)
    return int(m.group(1)) if m else int(publish_date[:4])


def _normalized_filename(meta: dict, ticker: str, report_type: str) -> str:
    publish_date = _parse_publish_date(meta.get("DATE_TIME", ""))
    report_year = _extract_report_year(meta.get("TITLE", ""), publish_date)
    company = (meta.get("STOCK_NAME", "") or "HK").replace("/", "-").replace(" ", "")
    return f"{report_year}_HK{ticker}_{report_type}_{publish_date}_{company}.pdf"


def _register_in_prism(slug: str, file_path: Path, report_type: str,
                        company_name: str, variant: str | None = None) -> None:
    from scripts.fetch_report_prism import _register_in_prism as _reg
    # _register_in_prism expects "annual" / "semi" / "quarterly" / "prospectus"
    # 我们直接传 report_type，由 _reg 内部映射到 source_type
    _reg(slug, file_path, report_type, company_name, variant)


def fetch(
    code: str,
    report_type: str = "annual",
    slug: str | None = None,
    variant: str | None = None,
) -> Path:
    """Download latest HKEX filing for code+report_type. Returns local path."""
    ticker = _zfill5(code)
    log.info("Resolving HKEX stockId for ticker=%s…", ticker)
    stock_id, company_name = _resolve_stock_id(ticker)
    print(f"\033[33m⚑ HKEX RESOLVED: {company_name} (ticker={ticker}, stockId={stock_id})\033[0m",
          file=sys.stderr)

    years_back = _YEAR_WINDOW[report_type]
    log.info("Listing announcements (last %d years)…", years_back)
    anns = _list_announcements(stock_id, years_back)
    log.info("  Got %d announcements", len(anns))

    matched = _filter_by_type(anns, report_type)
    if not matched:
        # 帮用户列一下能拿到什么类型
        seen_types = sorted({a.get("LONG_TEXT", "").split("<")[0].strip() for a in anns})
        raise ValueError(
            f"未找到 ticker={ticker} type={report_type} 的报告（{years_back} 年内）。\n"
            f"  该期间可获取类型: {seen_types[:15]}"
        )

    # 取发布时间最晚的一份（按 DATE_TIME 排序，HKEX 默认已 desc）
    target = matched[0]
    log.info("Selected: %s @ %s", target.get("TITLE"), target.get("DATE_TIME"))

    dest_dir = _materials_dir(slug) if slug else _INBOX_AUTO
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = _normalized_filename(target, ticker, report_type)
    dest = dest_dir / fname
    if dest.exists():
        log.info("Already exists: %s", dest.name)
    else:
        pdf_url = _HOST + target["FILE_LINK"]
        log.info("Downloading %s…", dest.name)
        body = _http_get_bytes(pdf_url)
        if not body.startswith(b"%PDF"):
            raise ValueError(f"HKEX 返回非 PDF: {body[:200]!r}")
        dest.write_bytes(body)
        log.info("Saved → %s (%.1f MB)", dest, len(body) / 1e6)

    if slug:
        _register_in_prism(slug, dest, report_type, company_name, variant)
    return dest


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Download HKEX filings (zero key)")
    parser.add_argument("code", help="港股代码（4-5 位数字，如 02228 或 2228）")
    parser.add_argument("--type", choices=["annual", "semi", "prospectus"], default="annual")
    parser.add_argument("--slug", default=None, help="Prism topic slug")
    parser.add_argument("--variant", default=None, help="Prism variant")
    args = parser.parse_args()

    try:
        path = fetch(args.code, args.type, args.slug, args.variant)
        print(path)
    except (ValueError, urllib.error.HTTPError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Download UK-listed company filings from the FCA National Storage Mechanism (NSM).

零依赖 scraping —— 无需 API key。流程：
    1. search API (POST /search?index=fca-nsm-searchdata) — keyword=ticker
       schema 是 NSM 自定义的 {from, size, sort, sortorder, keyword, criteriaObj}，
       不是 ES query DSL（虽然背后是 ES）。
    2. client-side 按 company 名 + type_code 白名单过滤（service 端 file_type
       criteria 行为不稳，对部分 type 不生效，统一走 client-side）。
    3. 按 publication_date desc 取最新一份。
    4. details API (GET /details/{_id}?index=fca-nsm-searchdata) — 返回
       _source.document_content 全文（RNS 公告纯文本，包含财务/MD&A）。
       NSM 没有独立的 PDF 下载 endpoint，文件即是 RNS 文本。

Usage:
    python -m scripts.fetch_uk_fca OXIG                                  # 最新 Final Results
    python -m scripts.fetch_uk_fca OXIG --type semi                      # 最新 Half-year Report
    python -m scripts.fetch_uk_fca OXIG --slug global-quantum-computing  # 入 prism

Type mapping (UK reporting conventions):
    annual → type_code in {ACS, FR}   (Annual Financial Report / Final Results)
    semi   → type_code in {HYR, IR}   (Half-yearly Report / Interim Financial Report)

Notes:
    - UK 不强制季报，本脚本不支持 quarterly
    - keyword 是 NSM 后端的 multi-field full-text 搜索，命中后用 company 名
      做严格 client-side 过滤防止跨公司污染
    - 落盘扩展名是 .html（NSM 实际给的是 plain text，但带 RNS 头注脚 HTML 残片）
    - 已知限制：NSM 服务端把 RNS 原文（Windows-1252）当 utf-8 入库，
      £ 等符号已变 U+FFFD（替换字符），客户端无法还原 —— 数字仍可用，
      只是货币符号丢失，分析时按 GBP 默认理解即可
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
from pathlib import Path

log = logging.getLogger("fetch_uk_fca")

_SEARCH_URL = "https://api.data.fca.org.uk/search"
_DETAILS_URL = "https://api.data.fca.org.uk/details"
_INDEX = "fca-nsm-searchdata"

_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0"
_ORIGIN = "https://data.fca.org.uk"
_REFERER = "https://data.fca.org.uk/"

_INBOX_AUTO = Path(__file__).parent.parent / "prism" / "inbox" / "auto"


def _materials_dir(slug: str) -> Path:
    return Path(__file__).parent.parent / "prism" / "topics" / slug / "materials"


# NSM type_code 白名单（按报告类型）
# annual: ACS (Annual Financial Report) 优先；FR (Final Results) 兜底
# semi:   HYR / AFR / HFR (Half-yearly Financial Report) 优先；IR (Half-year Financial Report) 兜底
# 实际数据里 OXIG 用 FR+IR，大型蓝筹（如银行）多用 ACS+HYR — 全列以兼容
_TYPE_CODE_WHITELIST = {
    "annual": ["ACS", "FR"],
    "semi":   ["HYR", "AFR", "HFR", "IR"],
}

# 搜索窗口：拉够最近 N 条，client-side 再过滤
_SEARCH_SIZE = 100


def _http_post_json(url: str, body: dict, params: dict | None = None) -> dict:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": _UA,
        "Origin": _ORIGIN,
        "Referer": _REFERER,
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def _http_get_json(url: str, params: dict | None = None) -> dict:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": _UA, "Origin": _ORIGIN, "Referer": _REFERER}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def _search(keyword: str, size: int = _SEARCH_SIZE) -> list[dict]:
    """NSM search by keyword (multi-field full-text). Sort by publication_date desc."""
    body = {
        "from": 0,
        "size": size,
        "sort": "publication_date",
        "sortorder": "desc",
        "keyword": keyword,
    }
    data = _http_post_json(_SEARCH_URL, body, params={"index": _INDEX})
    hits = data.get("hits", {}).get("hits", []) or []
    return [h["_source"] | {"_id": h["_id"]} for h in hits]


def _fetch_details(doc_id: str) -> dict:
    """Fetch full document content via /details/{_id}."""
    url = f"{_DETAILS_URL}/{urllib.parse.quote(doc_id, safe='')}"
    data = _http_get_json(url, params={"index": _INDEX})
    if not data.get("found"):
        raise ValueError(f"NSM details: doc {doc_id} not found")
    return data["_source"]


def _resolve_company(ticker: str, hits: list[dict]) -> str:
    """从搜索结果反推 canonical company name。

    keyword=ticker 通常命中目标公司最多，取出现次数最高的 company（不区分大小写）。
    返回 lowercased company name 用于后续过滤；若 hits 空抛错。
    """
    counts: dict[str, int] = {}
    for h in hits:
        c = h.get("company", "").strip()
        if not c:
            continue
        key = c.lower()
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        raise ValueError(f"NSM: 未在搜索结果中找到任何 company，ticker={ticker!r}")
    return max(counts.items(), key=lambda x: x[1])[0]


def _filter_hits(hits: list[dict], company_lc: str, report_type: str) -> list[dict]:
    """按 company 名严格匹配 + type_code 白名单过滤。"""
    whitelist = _TYPE_CODE_WHITELIST[report_type]
    out = []
    for h in hits:
        if h.get("company", "").strip().lower() != company_lc:
            continue
        if h.get("type_code", "") not in whitelist:
            continue
        out.append(h)
    return out


def _normalized_filename(meta: dict, ticker: str, report_type: str) -> str:
    pub_date = (meta.get("publication_date") or "")[:10] or "unknown"
    report_year = pub_date[:4] if pub_date != "unknown" else "0000"
    company = (meta.get("company", "") or "UK").strip().replace("/", "-").replace(" ", "")[:30]
    return f"{report_year}_LSE{ticker}_{report_type}_{pub_date}_{company}.html"


def _register_in_prism(slug: str, file_path: Path, report_type: str,
                       company_name: str, variant: str | None = None) -> None:
    from scripts.fetch_report_prism import _register_in_prism as _reg
    _reg(slug, file_path, report_type, company_name, variant)


def _wrap_as_html(meta: dict) -> bytes:
    """把 details 返回的 document_content 包成最小 HTML 文档，保留头部 metadata。"""
    src_type = meta.get("type", "")
    company = meta.get("company", "")
    pub = meta.get("publication_date", "")
    headline = meta.get("headline", "")
    isin = meta.get("isin", "")
    lei = meta.get("lei", "")
    content = meta.get("document_content", "") or ""
    body = (
        f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        f"  <meta charset=\"utf-8\">\n"
        f"  <title>{company} — {src_type} — {pub[:10]}</title>\n"
        f"</head>\n<body>\n"
        f"<h1>{company}</h1>\n"
        f"<p><strong>Type:</strong> {src_type}<br>\n"
        f"   <strong>Headline:</strong> {headline}<br>\n"
        f"   <strong>Published:</strong> {pub}<br>\n"
        f"   <strong>ISIN:</strong> {isin}<br>\n"
        f"   <strong>LEI:</strong> {lei}<br>\n"
        f"   <strong>Source:</strong> FCA NSM ({meta.get('source','')})</p>\n"
        f"<hr>\n<pre>{content}</pre>\n"
        f"</body>\n</html>\n"
    )
    return body.encode("utf-8")


def fetch(
    ticker: str,
    report_type: str = "annual",
    slug: str | None = None,
    variant: str | None = None,
) -> Path:
    """Download latest UK filing for ticker+report_type from FCA NSM. Returns local path."""
    if report_type not in _TYPE_CODE_WHITELIST:
        raise ValueError(
            f"不支持的 report_type: {report_type}（UK NSM 支持：{list(_TYPE_CODE_WHITELIST)}）"
        )
    ticker = ticker.strip().upper()

    log.info("NSM searching keyword=%s…", ticker)
    hits = _search(ticker)
    if not hits:
        raise ValueError(f"NSM 未返回任何结果，ticker={ticker!r}")

    company_lc = _resolve_company(ticker, hits)
    company_display = next(
        (h["company"] for h in hits if h.get("company", "").lower() == company_lc),
        company_lc.title(),
    )
    print(
        f"\033[33m⚑ NSM RESOLVED: {company_display} (ticker={ticker}) — verify before proceeding\033[0m",
        file=sys.stderr,
    )

    matched = _filter_hits(hits, company_lc, report_type)
    if not matched:
        seen = sorted({(h.get("type_code", ""), h.get("type", "")) for h in hits
                       if h.get("company", "").lower() == company_lc})
        raise ValueError(
            f"NSM: 未找到 ticker={ticker} type={report_type} 的报告（搜索窗口 {len(hits)} 条）。\n"
            f"  该公司可见 type_code: {seen[:20]}"
        )

    target = matched[0]  # 已按 publication_date desc，最新
    log.info(
        "Selected: %s @ %s (id=%s)",
        target.get("headline"),
        target.get("publication_date", "")[:10],
        target["_id"],
    )

    detail = _fetch_details(target["_id"])
    if not detail.get("document_content"):
        raise ValueError(
            f"NSM details 返回空 document_content，id={target['_id']}（可能仅 PDF 上传未被 NSM 索引文本）"
        )

    dest_dir = _materials_dir(slug) if slug else _INBOX_AUTO
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = _normalized_filename(detail, ticker, report_type)
    dest = dest_dir / fname

    if dest.exists():
        log.info("Already exists: %s", dest.name)
    else:
        payload = _wrap_as_html(detail)
        dest.write_bytes(payload)
        log.info("Saved → %s (%.1f KB)", dest, len(payload) / 1024)

    if slug:
        _register_in_prism(slug, dest, report_type, detail.get("company", ""), variant)
    return dest


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Download UK filings from FCA NSM (zero key)")
    parser.add_argument("ticker", help="LSE ticker (e.g. OXIG, BARC, HSBA)")
    parser.add_argument("--type", choices=list(_TYPE_CODE_WHITELIST), default="annual")
    parser.add_argument("--slug", default=None, help="Prism topic slug")
    parser.add_argument("--variant", default=None, help="Prism variant")
    args = parser.parse_args()

    try:
        path = fetch(args.ticker, args.type, args.slug, args.variant)
        print(path)
    except (ValueError, urllib.error.HTTPError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

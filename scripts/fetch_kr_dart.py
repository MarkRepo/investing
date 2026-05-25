"""Download Korean stock annual reports (사업보고서) from DART (dart.fss.or.kr).

零依赖 scraping —— 不需要 API key。流程：
    1. detailSearch.ax 公开搜索（textCrpNm 接受 6 位 KRX ticker 或公司名）拿 rcpNo
    2. dsaf001/main.do?rcpNo=X 解析 viewer JS 提取 dcmNo
    3. pdf/download/pdf.do?rcp_no=X&dcm_no=Y 拉原文 PDF

Usage:
    python -m scripts.fetch_kr_dart 005930              # 三星电子 最新 사업보고서
    python -m scripts.fetch_kr_dart 005930 --type semi  # 半年报
    python -m scripts.fetch_kr_dart 005930 --slug global-ssb-electrolyte  # 入 prism

Notes:
    - publicType: A001=사업보고서(年报) / A002=반기보고서(半年报) / A003=분기보고서(季报)
    - DART 反爬政策温和但 viewer 中的 JS 字段是稳定 schema（dcmNo 提取已用了多年）
"""
from __future__ import annotations

import argparse
import gzip
import logging
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

log = logging.getLogger("fetch_kr_dart")

_DART_HOST = "https://dart.fss.or.kr"
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0"

_PUBLIC_TYPE = {
    "annual":    "A001",
    "semi":      "A002",
    "quarterly": "A003",
}

_INBOX_AUTO = Path(__file__).parent.parent / "prism" / "inbox" / "auto"


def _materials_dir(slug: str) -> Path:
    return Path(__file__).parent.parent / "prism" / "topics" / slug / "materials"


def _http_get(url: str, *, ajax: bool = False) -> str:
    headers = {"User-Agent": _UA, "Accept-Encoding": "gzip", "Referer": _DART_HOST + "/"}
    if ajax:
        headers["X-Requested-With"] = "XMLHttpRequest"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        return body.decode("utf-8", errors="replace")


def _http_get_bytes(url: str) -> tuple[bytes, str | None]:
    """GET binary response. Returns (body, content_disposition)."""
    headers = {"User-Agent": _UA, "Referer": _DART_HOST + "/"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read(), r.headers.get("Content-Disposition")


def _search_latest_report(ticker_or_name: str, public_type: str) -> dict:
    """Search DART for the latest report matching ticker/name + type. Returns rich dict."""
    qs = urllib.parse.urlencode({
        "textCrpNm": ticker_or_name,
        "publicType": public_type,
        "currentPage": "1",
        "maxResults": "15",
    })
    html = _http_get(f"{_DART_HOST}/dsab007/detailSearch.ax?{qs}", ajax=True)

    # 第一行 result: <a href="/dsaf001/main.do?rcpNo=NNNNNNNN">
    rcp_match = re.search(r'rcpNo=(\d{14})"[^>]*id="r_\d+"', html)
    if not rcp_match:
        # 可能没有 id="r_..."，退化匹配
        rcp_match = re.search(r'rcpNo=(\d{14})', html)
    if not rcp_match:
        raise ValueError(f"DART 搜索无结果：{ticker_or_name} (publicType={public_type})")
    rcp_no = rcp_match.group(1)

    # 公司名 + 提交日期 + 报告期
    name_match = re.search(r'openCorpInfoNew\(\'(\d+)\'[^>]*\)[^>]*>\s*([^\s<]+)', html)
    corp_code = name_match.group(1) if name_match else ""
    company = name_match.group(2).strip() if name_match else ticker_or_name

    date_match = re.search(r'<td>(\d{4}\.\d{2}\.\d{2})</td>', html)
    filing_date = date_match.group(1).replace(".", "-") if date_match else ""

    # 报告期：title 里 "사업보고서 (2025.12)" 这种括号
    period_match = re.search(r'\((\d{4})\.(\d{2})\)', html)
    report_year = int(period_match.group(1)) if period_match else int(filing_date[:4]) if filing_date else 0

    return {
        "rcp_no": rcp_no,
        "corp_code": corp_code,
        "company": company,
        "filing_date": filing_date,
        "report_year": report_year,
    }


def _extract_dcm_no(rcp_no: str) -> str:
    """Visit viewer page, extract dcmNo from JS."""
    html = _http_get(f"{_DART_HOST}/dsaf001/main.do?rcpNo={rcp_no}")

    # JS: openPdfDownload('20260310002820', '12345678')
    m = re.search(rf"openPdfDownload\(\s*['\"]({rcp_no})['\"]\s*,\s*['\"](\d+)['\"]\s*\)", html)
    if m:
        return m.group(2)

    # 备用：dcmNo = 'NNNN'
    m = re.search(r"dcmNo\s*=\s*['\"](\d+)['\"]", html)
    if m:
        return m.group(1)

    # 文档检阅中 / 拒绝访问
    if "검토중" in html or "거부" in html:
        raise ValueError(f"rcpNo={rcp_no} 文档检阅中或访问被拒")
    raise ValueError(f"无法从 viewer 提取 dcmNo (rcpNo={rcp_no})")


def _normalized_filename(meta: dict, ticker: str, report_type: str) -> str:
    """E7 schema: {report_year}_{ticker}_{form}_{filing_date}_{company}.pdf"""
    year = meta.get("report_year") or (meta["filing_date"][:4] if meta.get("filing_date") else "0000")
    company = meta["company"].replace("/", "-").replace(" ", "")
    fd = meta.get("filing_date") or ""
    return f"{year}_{ticker}_{report_type}_{fd}_{company}.pdf"


def _download_pdf(rcp_no: str, dcm_no: str, dest: Path) -> Path:
    """Download PDF directly to dest."""
    url = f"{_DART_HOST}/pdf/download/pdf.do?rcp_no={rcp_no}&dcm_no={dcm_no}"
    log.info("Downloading %s …", dest.name)
    body, _ = _http_get_bytes(url)
    if not body.startswith(b"%PDF"):
        # 可能是 HTML 错误页
        snippet = body[:200].decode("utf-8", errors="replace")
        raise ValueError(f"DART 返回非 PDF (前 200 字节): {snippet}")
    dest.write_bytes(body)
    log.info("Saved → %s (%.1f MB)", dest, len(body) / 1e6)
    return dest


def _register_in_prism(slug: str, file_path: Path, report_type: str, company_name: str,
                        variant: str | None = None) -> None:
    """复用 fetch_report_prism 的 manifest + todo 登记逻辑。"""
    from scripts.fetch_report_prism import _register_in_prism as _reg
    # 复用 SEC/cninfo 的同名函数（参数对齐）
    _reg(slug, file_path, report_type, company_name, variant)


def fetch(
    ticker_or_name: str,
    report_type: str = "annual",
    slug: str | None = None,
    variant: str | None = None,
) -> Path:
    """Download latest 사업보고서/반기/분기 PDF for a Korean stock ticker or name.

    Returns local file path. Registers in prism manifest if slug given.
    """
    public_type = _PUBLIC_TYPE.get(report_type)
    if not public_type:
        raise ValueError(f"report_type 必须是 annual/semi/quarterly: got {report_type!r}")

    log.info("DART search: %s (%s)…", ticker_or_name, report_type)
    meta = _search_latest_report(ticker_or_name, public_type)
    print(f"\033[33m⚑ DART RESOLVED: {meta['company']} (corp_code={meta['corp_code']}) "
          f"→ rcp_no={meta['rcp_no']} filing={meta['filing_date']} period={meta['report_year']}.12\033[0m",
          file=sys.stderr)

    dcm_no = _extract_dcm_no(meta["rcp_no"])

    dest_dir = _materials_dir(slug) if slug else _INBOX_AUTO
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = _normalized_filename(meta, ticker_or_name, report_type)
    dest = dest_dir / fname
    if dest.exists():
        log.info("Already exists: %s", dest.name)
    else:
        _download_pdf(meta["rcp_no"], dcm_no, dest)

    if slug:
        _register_in_prism(slug, dest, report_type, meta["company"], variant)

    return dest


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Download Korean annual reports from DART")
    parser.add_argument("ticker", help="KRX 6-digit code (e.g. 005930) or Korean company name")
    parser.add_argument("--type", choices=["annual", "semi", "quarterly"], default="annual")
    parser.add_argument("--slug", default=None, help="Prism topic slug — registers manifest")
    parser.add_argument("--variant", default=None, help="Prism variant for manifest")
    args = parser.parse_args()

    try:
        path = fetch(args.ticker, args.type, args.slug, args.variant)
        print(path)
    except (ValueError, urllib.error.HTTPError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

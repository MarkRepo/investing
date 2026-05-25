"""Download Japanese disclosure PDFs from TDnet (適時開示情報閲覧サービス).

JPX 旗下 TDnet — 全公开 PDF，零 API key。覆盖決算短信 / 業績予想修正 / IR 資料 / M&A 公告等
適時開示（**注：法定有価証券報告書正本在 EDINET，TDnet 是 first-look 短信，3-5 页核心数据**）。

入口：https://www.release.tdnet.info/inbs/I_main_00.html
列表 URL 模式：I_list_{page:03d}_{YYYYMMDD}.html (page 1-N，100 件/页)
PDF URL 模式：I_main_00 同目录下 {SeqNo}.pdf

Usage:
    # 决算短信 first-look（最常用）
    python -m scripts.fetch_jp_tdnet --code 6502 --keyword 決算短信
    python -m scripts.fetch_jp_tdnet --code 5019 --keyword 決算短信 --slug global-ssb-electrolyte

    # 任意关键词（IR 资料 / 業績修正 / 中期計画）
    python -m scripts.fetch_jp_tdnet --code 6594 --keyword IR説明会資料

Notes:
    - TDnet 仅保留近 30 天，老文件需历史代理（如 yanoshi.tdnet-search.appspot.com）
    - code 是 4 位证券代码（如 6502=東芝），TDnet 内部存为 5 位末尾补 0（65020）
    - 表題 是关键过滤维度：「決算短信」「業績予想」「コーポレート」等
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

log = logging.getLogger("fetch_jp_tdnet")

_HOST = "https://www.release.tdnet.info/inbs"
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0"
_INBOX_AUTO = Path(__file__).parent.parent / "prism" / "inbox" / "auto"


def _materials_dir(slug: str) -> Path:
    return Path(__file__).parent.parent / "prism" / "topics" / slug / "materials"


def _http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def _http_get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _normalize_code(code: str) -> str:
    """4 位证券代码 → TDnet 内部 5 位（末尾补 0）。已是 5 位则原样返回。"""
    code = code.strip()
    if len(code) == 4 and code.isdigit():
        return code + "0"
    return code


def _list_disclosures(target_date: date) -> list[dict]:
    """抓取某日所有页 disclosure 行。返回 [{time, code, company, title, pdf_url, exchange}, ...]"""
    ymd = target_date.strftime("%Y%m%d")
    rows = []
    for page in range(1, 21):  # 200 件 / 天上限 → 实际 ≤4 页
        url = f"{_HOST}/I_list_{page:03d}_{ymd}.html"
        try:
            html = _http_get(url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break
            raise
        # 第一页 row[2] 起为数据行，每行 7 cell：time/code/company/title/xbrl/exchange/history
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
            cells = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
            if len(cells) < 6:
                continue
            time_str = re.sub(r"<[^>]+>", "", cells[0]).strip()
            code = re.sub(r"<[^>]+>", "", cells[1]).strip()
            company = re.sub(r"<[^>]+>", "", cells[2]).strip()
            if not (re.match(r"\d{2}:\d{2}", time_str) and re.match(r"\d{4,5}", code)):
                continue
            # title cell 含 <a href="NNN.pdf">表題</a>
            href = re.search(r'href="([^"]+\.pdf)"', cells[3])
            title = re.sub(r"<[^>]+>", "", cells[3]).strip()
            exchange = re.sub(r"<[^>]+>", "", cells[5]).strip() if len(cells) > 5 else ""
            if not href:
                continue
            rows.append({
                "date": target_date.isoformat(),
                "time": time_str,
                "code": code,
                "company": company,
                "title": title,
                "pdf_url": f"{_HOST}/{href.group(1)}",
                "exchange": exchange,
            })
        # 检查是否有"次へ"链接，没有就停
        if "次へ" not in html or page * 100 >= 1000:
            break
    return rows


def _find_disclosure(code: str, keyword: str, max_days: int = 35) -> dict:
    """反扫最近 max_days 天，找到匹配 (code, keyword in title) 的最新 disclosure。"""
    code = _normalize_code(code)
    today = date.today()
    log.info("Scanning TDnet last %d days for code=%s keyword=%r…", max_days, code, keyword)
    for offset in range(max_days):
        d = today - timedelta(days=offset)
        try:
            rows = _list_disclosures(d)
        except urllib.error.HTTPError:
            continue
        for r in rows:
            if r["code"] == code and keyword in r["title"]:
                log.info("Found: %s [%s] %s → %s",
                         r["company"], r["date"], r["title"], r["pdf_url"])
                return r
    raise ValueError(
        f"未找到 code={code} keyword={keyword!r} 的 disclosure（{max_days} 天内）"
    )


def _normalized_filename(meta: dict, report_type: str) -> str:
    company = meta["company"].replace("/", "-").replace(" ", "")
    code = meta["code"][:4]  # 去掉末尾 0 → 4 位
    fd = meta["date"]
    year = fd[:4]
    return f"{year}_{code}_{report_type}_{fd}_{company}.pdf"


def _register_in_prism(slug: str, file_path: Path, report_type: str,
                        company_name: str, variant: str | None = None) -> None:
    from scripts.fetch_report_prism import _register_in_prism as _reg
    _reg(slug, file_path, report_type, company_name, variant)


def fetch(
    code: str,
    keyword: str = "決算短信",
    report_type: str = "earnings-flash",
    slug: str | None = None,
    variant: str | None = None,
    max_days: int = 35,
) -> Path:
    """Download latest TDnet disclosure for code+keyword. Returns local path."""
    meta = _find_disclosure(code, keyword, max_days)
    print(f"\033[33m⚑ TDNET RESOLVED: {meta['company']} (code={meta['code']}) "
          f"→ {meta['title']} @ {meta['date']} {meta['time']}\033[0m", file=sys.stderr)

    dest_dir = _materials_dir(slug) if slug else _INBOX_AUTO
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = _normalized_filename(meta, report_type)
    dest = dest_dir / fname
    if dest.exists():
        log.info("Already exists: %s", dest.name)
    else:
        log.info("Downloading %s …", dest.name)
        body = _http_get_bytes(meta["pdf_url"])
        if not body.startswith(b"%PDF"):
            raise ValueError(f"TDnet 返回非 PDF: {body[:200]!r}")
        dest.write_bytes(body)
        log.info("Saved → %s (%.1f MB)", dest, len(body) / 1e6)

    if slug:
        _register_in_prism(slug, dest, report_type, meta["company"], variant)
    return dest


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Download Japanese TDnet disclosure PDFs (zero key)")
    parser.add_argument("--code", required=True, help="证券代码 4 位（如 5019 出光興産）或 5 位")
    parser.add_argument("--keyword", default="決算短信", help='表題过滤关键词，默认「決算短信」')
    parser.add_argument("--type", default="earnings-flash",
                        help="manifest 中的 report_type 标签（默认 earnings-flash）")
    parser.add_argument("--slug", default=None, help="Prism topic slug — registers manifest")
    parser.add_argument("--variant", default=None, help="Prism variant for manifest")
    parser.add_argument("--max-days", type=int, default=35, help="扫描天数上限（TDnet 仅留近 30 天）")
    args = parser.parse_args()

    try:
        path = fetch(args.code, args.keyword, args.type, args.slug, args.variant, args.max_days)
        print(path)
    except (ValueError, urllib.error.HTTPError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

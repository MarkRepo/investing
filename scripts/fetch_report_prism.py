"""Download A-share financial reports from cninfo into prism/inbox/auto/.

Wraps the same cninfo API logic as the fetch-reports skill, callable from code.

Usage:
    python -m scripts.fetch_report_prism SSE_688066
    python -m scripts.fetch_report_prism SSE_688066 --year 2024
    python -m scripts.fetch_report_prism SSE_688066 --type annual --year 2024
    # With prism integration (registers manifest + updates todos):
    python -m scripts.fetch_report_prism SSE_688066 --year 2024 --slug cn-commercial-space

Returns the downloaded file path (printed to stdout).
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import date
from pathlib import Path

import requests

log = logging.getLogger("fetch_report_prism")

_CNINFO_SEARCH = "https://www.cninfo.com.cn/new/information/topSearch/query"
_CNINFO_QUERY = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
_CNINFO_DL = "https://static.cninfo.com.cn/"
_HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"}

_CATEGORY = {
    "annual":    "category_ndbg_szsh",
    "semi":      "category_bndbg_szsh",
    "quarterly": "category_sjdbg_szsh",
}

_INBOX_AUTO = Path(__file__).parent.parent / "prism" / "inbox" / "auto"


def _materials_dir(slug: str) -> Path:
    return Path(__file__).parent.parent / "prism" / "topics" / slug / "materials"


def _column(code: str) -> str:
    """Determine cninfo exchange column from stock code."""
    return "sse" if code.startswith(("6", "9", "5")) else "szse"


def _parse_market_ticker(key: str) -> tuple[str, str]:
    """'SSE_688066' → ('SSE', '688066')"""
    parts = key.split("_", 1)
    if len(parts) != 2:
        raise ValueError(f"Expected format MARKET_TICKER, got {key!r}")
    return parts[0], parts[1]


def _company_info(ticker: str) -> dict:
    r = requests.post(_CNINFO_SEARCH, headers=_HEADERS,
                      data=f"keyWord={ticker}&maxNum=5", timeout=15)
    r.raise_for_status()
    results = r.json()
    if not results:
        raise ValueError(f"Company not found on cninfo: {ticker}")
    return results[0]   # {code, orgId, zwjc, ...}


def _list_reports(code: str, org_id: str, column: str, category: str) -> list[dict]:
    data = (
        f"stock={code}%2C{org_id}&category={category}"
        f"&pageNum=1&pageSize=50&tabName=fulltext&column={column}"
    )
    r = requests.post(_CNINFO_QUERY, headers=_HEADERS, data=data, timeout=15)
    r.raise_for_status()
    announcements = r.json().get("announcements") or []
    # Drop summaries, English versions, corrections
    return [
        a for a in announcements
        if not re.search(r"摘要|英文|更正|修订", a.get("announcementTitle", ""))
    ]


def _extract_year(title: str) -> int | None:
    m = re.search(r"(\d{4})", title)
    return int(m.group(1)) if m else None


def _download(announcement: dict, dest_dir: Path, company_name: str) -> Path:
    url = _CNINFO_DL + announcement["adjunctUrl"]
    ts = announcement["announcementTime"]
    # Convert ms timestamp to date string
    from datetime import datetime, timezone
    dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    title = announcement["announcementTitle"].replace("/", "-").replace(" ", "")
    filename = f"{dt}_{company_name}_{title}.PDF"
    dest = dest_dir / filename
    if dest.exists():
        log.info("Already exists: %s", dest.name)
        return dest
    log.info("Downloading %s…", filename)
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
    r.raise_for_status()
    dest.write_bytes(r.content)
    log.info("Saved → %s (%.1f MB)", dest, len(r.content) / 1e6)
    return dest


def _register_in_prism(slug: str, file_path: Path, report_type: str, company_name: str, variant: str | None = None) -> None:
    """Register downloaded report in prism manifest and update user_todos."""
    from prism.scripts.manifest import add_material, create_manifest, read_manifest
    from prism.scripts.topic import list_variants, read_topic, set_user_todos

    # Auto-detect variant if not specified
    if not variant:
        variants = list_variants(slug)
        if len(variants) == 1:
            variant = variants[0]
        else:
            log.warning("Cannot auto-detect variant for %s (found %d), skipping manifest update", slug, len(variants))
            return

    # Auto-create manifest if missing
    try:
        read_manifest(slug, variant)
    except FileNotFoundError:
        create_manifest(slug, variant)
        log.info("Created manifest for %s/%s", slug, variant)

    source_type = (
        "prospectus" if report_type == "prospectus"
        else "annual-report" if report_type == "annual"
        else "quarterly-report"
    )
    mat_id = add_material(
        slug=slug,
        filename=file_path.name,
        source_type=source_type,
        variant=variant,
        notes=f"Auto-downloaded from cninfo — {company_name}",
        source_path=file_path,
    )
    log.info("Registered in manifest: %s → %s", file_path.name, mat_id)

    # Remove matching todo from user_todos
    topic = read_topic(slug, variant)
    todos = topic.get("user_todos", [])
    updated = [t for t in todos if company_name not in t and file_path.stem[:8] not in t]
    if len(updated) < len(todos):
        set_user_todos(slug, updated, variant)
        log.info("Removed %d matched todo(s)", len(todos) - len(updated))


def _search_all_pages(code: str, org_id: str, column: str, keyword: str, max_pages: int = 20) -> list[dict]:
    """Search announcements across multiple pages for keyword matches."""
    results = []
    for page in range(1, max_pages + 1):
        data = (
            f"stock={code}%2C{org_id}"
            f"&pageNum={page}&pageSize=30&tabName=fulltext&column={column}"
        )
        r = requests.post(_CNINFO_QUERY, headers=_HEADERS, data=data, timeout=15)
        r.raise_for_status()
        page_anns = r.json().get("announcements") or []
        if not page_anns:
            break
        for a in page_anns:
            if keyword in a.get("announcementTitle", ""):
                results.append(a)
    return results


def _fetch_prospectus(market_ticker: str, slug: str | None = None, variant: str | None = None) -> Path:
    """Download IPO prospectus (招股说明书) from cninfo announcements."""
    _, ticker = _parse_market_ticker(market_ticker)
    if slug:
        dest_dir = _materials_dir(slug)
    else:
        dest_dir = _INBOX_AUTO
    dest_dir.mkdir(parents=True, exist_ok=True)

    log.info("Looking up %s on cninfo…", ticker)
    info = _company_info(ticker)
    code, org_id = info["code"], info["orgId"]
    company_name = info.get("zwjc", ticker)
    column = _column(code)

    keywords = [
        "首次公开发行股票招股说明书",
        "首次公开发行股票招股意向书",
    ]

    all_found = []
    for kw in keywords:
        log.info("Searching for '%s'…", kw)
        found = _search_all_pages(code, org_id, column, kw)
        all_found.extend(found)
        log.info("  Found: %d", len(found))

    if not all_found:
        log.info("Trying broader search for 招股…")
        all_found = _search_all_pages(code, org_id, column, "招股")

    if not all_found:
        raise ValueError(f"No IPO prospectus found for {company_name} ({ticker})")

    target = all_found[0]
    for a in all_found:
        t = a.get("announcementTitle", "")
        if re.search(r"摘要|英文|更正|修订|提示性", t):
            continue
        target = a
        break

    log.info("Selected: %s", target["announcementTitle"])
    file_path = _download(target, dest_dir, company_name)

    if slug:
        _register_in_prism(slug, file_path, "prospectus", company_name, variant)

    return file_path


def fetch(
    market_ticker: str,
    report_type: str = "annual",
    year: int | None = None,
    slug: str | None = None,
    variant: str | None = None,
) -> Path:
    """Download a financial report. Returns the local file path."""
    if report_type == "prospectus":
        return _fetch_prospectus(market_ticker, slug, variant)

    # Determine destination: if slug provided, download directly to topic materials
    if slug:
        dest_dir = _materials_dir(slug)
    else:
        dest_dir = _INBOX_AUTO
    dest_dir.mkdir(parents=True, exist_ok=True)

    _, ticker = _parse_market_ticker(market_ticker)
    year = year or (date.today().year - 1)

    log.info("Looking up %s on cninfo…", ticker)
    info = _company_info(ticker)
    code, org_id = info["code"], info["orgId"]
    company_name = info.get("zwjc", ticker)
    column = _column(code)

    log.info("Fetching %s report list for %s (%s)…", report_type, company_name, code)
    reports = _list_reports(code, org_id, column, _CATEGORY[report_type])

    # Find the target year
    matches = [r for r in reports if _extract_year(r.get("announcementTitle", "")) == year]
    if not matches:
        available = sorted({_extract_year(r.get("announcementTitle", "")) for r in reports} - {None}, reverse=True)
        raise ValueError(
            f"No {report_type} report found for {year}. "
            f"Available years: {available}"
        )

    # Take the earliest (first-published, non-correction) version
    target = sorted(matches, key=lambda r: r["announcementTime"])[0]
    log.info("Found: %s", target["announcementTitle"])

    file_path = _download(target, dest_dir, company_name)

    if slug:
        _register_in_prism(slug, file_path, report_type, company_name, variant)

    return file_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Download financial report to prism/inbox/auto/")
    parser.add_argument("ticker", help="Market_Ticker, e.g. SSE_688066")
    parser.add_argument("--type", choices=["annual", "semi", "quarterly", "prospectus"], default="annual")
    parser.add_argument("--year", type=int, default=None, help="Fiscal year (default: last year)")
    parser.add_argument("--slug", default=None,
                        help="Prism topic slug — registers manifest + updates user_todos")
    parser.add_argument("--variant", default=None,
                        help="Model variant — registers in this variant's manifest")
    args = parser.parse_args()

    try:
        path = fetch(args.ticker, args.type, args.year, args.slug, args.variant)
        print(path)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

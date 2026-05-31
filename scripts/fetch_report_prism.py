"""Download A-share financial reports from cninfo into prism/inbox/auto/.

Wraps the same cninfo API logic as the fetch-reports skill, callable from code.

Usage:
    python -m scripts.fetch_report_prism SSE_688066
    python -m scripts.fetch_report_prism SSE_688066 --year 2024
    python -m scripts.fetch_report_prism SSE_688066 --type annual --year 2024
    # With prism integration (registers manifest + updates todos):
    python -m scripts.fetch_report_prism SSE_688066 --year 2024 --slug cn-commercial-space

Returns the downloaded file path (printed to stdout).

LLM 工具用法（被 03/05 sub-agent dispatch 时）:
    主 agent 在 03-extract 或 05-critic 流程中识别到"需要补一份具体年报/季报"时，
    可以 dispatch sub-agent 运行本脚本：

    python -m scripts.fetch_report_prism {market}_{code} --year YYYY [--type annual|q1|interim|q3]

    sub-agent dispatch prompt 标准格式参 prism/workflows/_subagent_fetch_material.md。
    脚本退出码 0 = 已下载到 prism/topics/{slug}/inbox/auto/（带 --slug）或 prism/inbox/auto/；
    非 0 = 失败（让 sub-agent 报告失败原因）。

    下载完成后由主 agent 跑 workflow 02 把 PDF 登记入 manifest（含 mineru 转换）。
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
    "q1":        "category_yjdbg_szsh",    # 一季度报告（A 股截止 4-30）
    "q3":        "category_sjdbg_szsh",    # 三季度报告（A 股截止 10-31）
    # "quarterly" 由 fetch() 内部 fan-out 查 q1+q3 合并，不在此映射
}

_QUARTERLY_CATEGORIES = ("q1", "q3")

# 高信号公告类别（cninfo category）—— 默认拉近 1 年
# 注：移除 gqjl（股权激励）——经 _TITLE_NOISE_RE 黑名单后本就清零（限制性股票/归属/作废/
# 律所/独董等纯治理噪声），保留该类目只是徒增无谓抓取。修 F7。
_ANNOUNCEMENT_CATEGORIES = {
    "yjygjxz": "category_yjygjxz_szsh",   # 业绩预告/业绩快报（纯金，催化剂）
    "zf":      "category_zf_szsh",        # 增发
    "kzz":     "category_kzz_szsh",       # 可转债
    "fxts":    "category_fxts_szsh",      # 风险提示
    "tbclts":  "category_tbclts_szsh",    # 特别处理（ST/退市预警）
}

# 公告标题噪声黑名单（保守·高精度，修 F7）。
# 原则：**只删确定无投资价值的治理/中介程序性文件，催化剂（临床/BD/许可/业绩预告/快报/
# 季报）一律留**——用黑名单而非白名单，标题刁钻的新催化剂也不会被误杀（漏催化剂的代价
# 远高于残留少量噪声）。不收 "董事会决议" 类（可能承载重大合作审议）以免误伤。
_TITLE_NOISE_RE = (
    r"摘要|英文|更正|修订|"
    r"会计师事务所|律师事务所|独立董事|薪酬与考核委员会|审计委员会|提名委员会|战略委员会|"
    r"限制性股票|股票激励计划|激励对象|持续督导|内部控制|公司章程|H股公告|月报表"
)

_ANNOUNCEMENT_WINDOW_DAYS = 365

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
    # 丢摘要/英文/更正/修订 + 治理·中介程序性噪声（_TITLE_NOISE_RE）；未命中一律留，
    # 保住临床/BD/业绩预告/季报等催化剂（修 F7）。年报本体标题不含黑名单词，无误伤。
    return [
        a for a in announcements
        if not re.search(_TITLE_NOISE_RE, a.get("announcementTitle", ""))
    ]


def _extract_year(title: str) -> int | None:
    m = re.search(r"(\d{4})", title)
    return int(m.group(1)) if m else None


def _disclosure_window_hint(report_type: str, year: int) -> str:
    """A 股披露窗口提示：当 year==今年 且未到截止日，告知用户报告可能尚未披露。

    A 股截止：年报 4-30 / 半年报 8-31 / 季报 Q1 4-30、Q3 10-31。
    quarterly 拆两段提示，避免 5-22 这种"Q1 已过、Q3 未到"时段被误报 Q1 也未披露。
    """
    today = date.today()
    if year != today.year:
        return ""
    if report_type == "annual":
        deadline = date(year, 4, 30)
        if today < deadline:
            return f" (今年年报截止 {deadline:%m-%d}，可能尚未披露)"
    elif report_type == "semi":
        deadline = date(year, 8, 31)
        if today < deadline:
            return f" (今年半年报截止 {deadline:%m-%d}，可能尚未披露)"
    elif report_type == "quarterly":
        q1 = date(year, 4, 30)
        q3 = date(year, 10, 31)
        if today < q1:
            return f" (今年 Q1 截止 {q1:%m-%d}、Q3 截止 {q3:%m-%d}，均尚未披露)"
        if today < q3:
            return f" (今年 Q1 应已披露；Q3 截止 {q3:%m-%d}，尚未披露)"
    return ""


def _download(announcement: dict, dest_dir: Path, company_name: str,
              ticker: str = "", report_type: str = "") -> Path:
    """Download cninfo announcement to dest_dir.

    Filename schema (E7 — sortable by report year, then ticker):
        {report_year}_{ticker}_{type}_{publish_date}_{company}.PDF

    Falls back to publish year if report year can't be parsed from title.
    Backward-compat: also checks old filename to avoid re-downloading.
    """
    url = _CNINFO_DL + announcement["adjunctUrl"]
    ts = announcement["announcementTime"]
    from datetime import datetime, timezone
    dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    title = announcement["announcementTitle"].replace("/", "-").replace(" ", "")

    # Old filename for backward-compat dedup
    old_name = f"{dt}_{company_name}_{title}.PDF"
    old_dest = dest_dir / old_name
    if old_dest.exists():
        log.info("Already exists (legacy name): %s", old_dest.name)
        return old_dest

    # New normalized filename
    report_year = _extract_year(title) or int(dt[:4])
    type_tag = report_type or "report"
    new_name = f"{report_year}_{ticker or '_'}_{type_tag}_{dt}_{company_name}.PDF"
    dest = dest_dir / new_name
    if dest.exists():
        log.info("Already exists: %s", dest.name)
        return dest

    log.info("Downloading %s…", new_name)
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
    r.raise_for_status()
    dest.write_bytes(r.content)
    log.info("Saved → %s (%.1f MB)", dest, len(r.content) / 1e6)
    return dest


def _register_in_prism(slug: str, file_path: Path, report_type: str, company_name: str, variant: str | None = None) -> tuple[str | None, str | None]:
    """Register downloaded report in prism manifest and update user_todos.

    Returns (mat_id, resolved_variant). Either may be None if registration was skipped.
    """
    from prism.scripts.manifest import add_material, create_manifest, read_manifest
    from prism.scripts.topic import list_variants, read_topic, update_user_todo_status

    # Auto-detect variant if not specified
    if not variant:
        variants = list_variants(slug)
        if len(variants) == 1:
            variant = variants[0]
        else:
            log.warning("Cannot auto-detect variant for %s (found %d), skipping manifest update", slug, len(variants))
            return (None, None)

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
    from prism.scripts.input_contract import default_report_rings
    # 按 topic.type 取向打 rings（修 F10）：industry/arena 材料不再误标 company rings。
    try:
        topic_type = (read_topic(slug, variant) or {}).get("type", "company")
    except Exception:
        topic_type = "company"
    mat_id = add_material(
        slug=slug,
        filename=file_path.name,
        source_type=source_type,
        variant=variant,
        notes=f"Auto-downloaded from cninfo — {company_name}",
        source_path=file_path,
        rings=default_report_rings(report_type, topic_type),
    )
    log.info("Registered in manifest: %s → %s", file_path.name, mat_id)

    # 标记匹配的 todo 为 in_progress（保留结构化 schema，不删除）
    topic = read_topic(slug, variant)
    todos = topic.get("user_todos", [])
    matched = 0
    for t in todos:
        # read_topic 已 normalize 成 dict
        task_text = t.get("task", "") if isinstance(t, dict) else str(t)
        if company_name and company_name in task_text and t.get("status") != "done":
            try:
                update_user_todo_status(slug, variant, task_text[:30], "in_progress")
                matched += 1
            except Exception as e:
                log.debug("todo status update failed for %s: %s", task_text[:30], e)
    if matched:
        log.info("Updated %d matched todo(s) to in_progress (preserving schema)", matched)
    return (mat_id, variant)


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
    file_path = _download(target, dest_dir, company_name, ticker=ticker, report_type="prospectus")

    if slug:
        _register_in_prism(slug, file_path, "prospectus", company_name, variant)

    return file_path


def _is_us_ticker(ticker: str) -> bool:
    """US tickers are 1-5 uppercase letters, no underscore (no market prefix)."""
    return bool(re.match(r"^[A-Z]{1,5}$", ticker))


def _route(market_ticker: str) -> str:
    """Identify market from ticker string. Returns one of: us / cn / kr / jp_tdnet / jp_edinet / hk / uk."""
    if market_ticker.startswith(("SSE_", "SZSE_", "BSE_")):
        return "cn"
    if market_ticker.startswith("HK_"):
        return "hk"
    if market_ticker.startswith("LSE_"):
        return "uk"
    if market_ticker.startswith("KRX_") or re.match(r"^\d{6}$", market_ticker):
        return "kr"
    if market_ticker.startswith("EDINET_"):
        return "jp_edinet"
    if market_ticker.startswith("TSE_") or re.match(r"^\d{4}$", market_ticker):
        return "jp_tdnet"
    if _is_us_ticker(market_ticker):
        return "us"
    raise ValueError(
        f"无法识别 ticker 格式：{market_ticker!r}\n"
        "  支持：US (NVDA) / CN (SZSE_300750) / HK (HK_02228) / UK (LSE_OXIG) / "
        "KR (006400 或 KRX_006400) / JP TDnet (5019 或 TSE_5019) / JP EDINET (EDINET_E00040)"
    )


_JP_KEYWORD = {
    "annual":    "決算短信",       # 年度決算短信
    "semi":      "中間決算短信",   # 中間/上期
    "quarterly": "四半期決算短信",
}


_SEC_FORM_TO_REPORT_TYPE = {
    "10-K": "annual",
    "10-Q": "quarterly",
    "20-F": "annual",      # foreign private issuer 年报（中概股 ADR 常见）
    "6-K": "quarterly",    # foreign private issuer 中期/月度披露
    "40-F": "annual",      # 加拿大 issuer 年报
}


def fetch_sec(
    ticker: str,
    slug: str | None = None,
    variant: str | None = None,
    forms: tuple[str, ...] = ("10-K", "10-Q", "20-F", "6-K", "40-F"),
    with_announcements: bool = True,
) -> list[Path]:
    """Download latest SEC filings for a US ticker. Auto-registers in manifest if slug given.

    Default forms 同时覆盖本土公司（10-K/10-Q）和外国发行人 ADR（20-F/6-K/40-F）。
    一般一个 issuer 只会同时存在其中一组，互不冲突。
    """
    import json
    import os
    import urllib.request

    UA = "investment-wiki research@example.com"
    dest_dir = _materials_dir(slug) if slug else _INBOX_AUTO
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Look up CIK
    req = urllib.request.Request(
        "https://www.sec.gov/files/company_tickers.json", headers={"User-Agent": UA}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    cik_map = {v["ticker"].upper(): (str(v["cik_str"]).zfill(10), v["title"]) for v in data.values()}
    if ticker.upper() not in cik_map:
        raise ValueError(f"SEC CIK not found for ticker {ticker}")
    cik, company_name = cik_map[ticker.upper()]

    # List filings
    req2 = urllib.request.Request(
        f"https://data.sec.gov/submissions/CIK{cik}.json", headers={"User-Agent": UA}
    )
    with urllib.request.urlopen(req2, timeout=30) as resp:
        sub = json.loads(resp.read())
    recent = sub.get("filings", {}).get("recent", {})
    f_list = recent.get("form", [])
    dates_ = recent.get("filingDate", [])
    rdates = recent.get("reportDate", [])
    accs = recent.get("accessionNumber", [])
    docs = recent.get("primaryDocument", [])

    targets: dict[str, int] = {}
    for i, form in enumerate(f_list):
        if "/A" in form:
            continue
        if form in forms and form not in targets:
            targets[form] = i
        if len(targets) == len(forms):
            break

    saved: list[Path] = []
    for form, idx in targets.items():
        acc_dir = accs[idx].replace("-", "")
        cik_num = str(int(cik))
        doc = docs[idx]
        fd = dates_[idx]
        rd = rdates[idx]
        ext = os.path.splitext(doc)[1] or ".htm"
        # Backward-compat dedup: check legacy name first
        legacy = dest_dir / f"{fd}_{ticker}_{form}_{rd}{ext}"
        # New normalized name: {report_year}_{ticker}_{form}_{filing_date}.{ext}
        report_year = (rd or fd)[:4]
        fname = f"{report_year}_{ticker}_{form}_{fd}{ext}"
        dest = dest_dir / fname
        if legacy.exists():
            log.info("%s — already exists (legacy name)", legacy.name)
            dest = legacy
        elif dest.exists():
            log.info("%s — already exists", fname)
        else:
            dl = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_dir}/{doc}"
            req3 = urllib.request.Request(dl, headers={"User-Agent": UA})
            with urllib.request.urlopen(req3, timeout=120) as resp:
                dest.write_bytes(resp.read())
            log.info("Saved → %s (%.1f MB)", dest, dest.stat().st_size / 1e6)
        if slug:
            report_type = _SEC_FORM_TO_REPORT_TYPE.get(form, "quarterly")
            parent_id, resolved_variant = _register_in_prism(slug, dest, report_type, company_name, variant)
            # 10-K / 10-Q / 20-F：尝试按 Item 切片，并把每节登记为 parent_mat 子条目
            if parent_id and resolved_variant and form in {"10-K", "10-Q", "20-F"} and dest.suffix.lower() in {".htm", ".html"}:
                try:
                    from prism.scripts.sec_section_split import split_file
                    from prism.scripts.manifest import add_sec_sections_from_meta
                    meta = split_file(dest)
                    if meta.get("split_ok"):
                        meta_path = dest.parent / "sec" / dest.stem / "_meta.yaml"
                        children = add_sec_sections_from_meta(slug, resolved_variant, parent_id, meta_path)
                        log.info("Split %s → %d section children", dest.name, len(children))
                except Exception as e:
                    log.warning("Section split failed for %s: %s — full htm still usable", dest.name, e)
        saved.append(dest)

    if with_announcements:
        try:
            ann = fetch_announcements_us(ticker, slug, variant)
            if ann:
                log.info("Fetched %d 8-K announcement(s) for %s", len(ann), ticker)
        except Exception as e:
            log.warning("8-K announcement fetch failed for %s: %s", ticker, e)

    return saved


def _within_window(announcement: dict, days: int) -> bool:
    """True if announcement was published within the last `days` days."""
    ts = announcement.get("announcementTime")
    if not ts:
        return False
    from datetime import datetime, timezone
    pub = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date()
    return (date.today() - pub).days <= days


def _download_announcement(announcement: dict, dest_dir: Path, company_name: str,
                            ticker: str, category_key: str) -> Path:
    """Download a cninfo announcement PDF — separate filename schema from financial reports.

    Filename: {publish_date}_{ticker}_announce_{category}_{title}.PDF
    """
    url = _CNINFO_DL + announcement["adjunctUrl"]
    ts = announcement["announcementTime"]
    from datetime import datetime, timezone
    dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    title = announcement["announcementTitle"].replace("/", "-").replace(" ", "")
    # Cap title to keep filename sane
    if len(title) > 40:
        title = title[:40]
    name = f"{dt}_{ticker}_announce_{category_key}_{title}.PDF"
    dest = dest_dir / name
    if dest.exists():
        log.info("Already exists: %s", dest.name)
        return dest
    log.info("Downloading announcement %s…", name)
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
    r.raise_for_status()
    dest.write_bytes(r.content)
    log.info("Saved → %s (%.1f MB)", dest, len(r.content) / 1e6)
    return dest


def fetch_announcements_cn(
    market_ticker: str,
    slug: str | None = None,
    variant: str | None = None,
    days: int = _ANNOUNCEMENT_WINDOW_DAYS,
) -> list[Path]:
    """Download recent high-signal A-share announcements (last `days` days, default 365).

    Categories: 业绩预告/股权激励/增发/可转债/风险提示/特别处理.
    Per-category failures are logged and skipped — one bad category does not abort the rest.
    Returns list of downloaded paths.
    """
    _, ticker = _parse_market_ticker(market_ticker)
    dest_dir = _materials_dir(slug) if slug else _INBOX_AUTO
    dest_dir.mkdir(parents=True, exist_ok=True)

    info = _company_info(ticker)
    code, org_id = info["code"], info["orgId"]
    company_name = info.get("zwjc", ticker)
    column = _column(code)

    saved: list[Path] = []
    for key, category in _ANNOUNCEMENT_CATEGORIES.items():
        try:
            anns = _list_reports(code, org_id, column, category)
        except Exception as e:
            log.warning("Announcement category %s list failed: %s", key, e)
            continue
        recent = [a for a in anns if _within_window(a, days)]
        if not recent:
            continue
        log.info("Category %s: %d announcement(s) within %dd", key, len(recent), days)
        for a in recent:
            try:
                p = _download_announcement(a, dest_dir, company_name, ticker, key)
                saved.append(p)
                if slug:
                    _register_in_prism(slug, p, "announcement", company_name, variant)
            except Exception as e:
                log.warning("Announcement download failed (%s): %s", a.get("announcementTitle", "?")[:30], e)
    return saved


def fetch_announcements_us(
    ticker: str,
    slug: str | None = None,
    variant: str | None = None,
    days: int = _ANNOUNCEMENT_WINDOW_DAYS,
) -> list[Path]:
    """Download recent 8-K filings (last `days` days, default 365) for a US ticker.

    Reuses fetch_sec but pulls all 8-K within window (not just latest).
    Per-filing failures are logged and skipped.
    """
    import json
    import os
    import urllib.request
    from datetime import datetime as _dt

    UA = "investment-wiki research@example.com"
    dest_dir = _materials_dir(slug) if slug else _INBOX_AUTO
    dest_dir.mkdir(parents=True, exist_ok=True)

    req = urllib.request.Request(
        "https://www.sec.gov/files/company_tickers.json", headers={"User-Agent": UA}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    cik_map = {v["ticker"].upper(): (str(v["cik_str"]).zfill(10), v["title"]) for v in data.values()}
    if ticker.upper() not in cik_map:
        raise ValueError(f"SEC CIK not found for ticker {ticker}")
    cik, company_name = cik_map[ticker.upper()]

    req2 = urllib.request.Request(
        f"https://data.sec.gov/submissions/CIK{cik}.json", headers={"User-Agent": UA}
    )
    with urllib.request.urlopen(req2, timeout=30) as resp:
        sub = json.loads(resp.read())
    recent = sub.get("filings", {}).get("recent", {})
    f_list = recent.get("form", [])
    dates_ = recent.get("filingDate", [])
    accs = recent.get("accessionNumber", [])
    docs = recent.get("primaryDocument", [])

    cutoff = (date.today() - __import__("datetime").timedelta(days=days)).isoformat()
    saved: list[Path] = []
    for i, form in enumerate(f_list):
        if form != "8-K":
            continue
        if "/A" in form:
            continue
        fd = dates_[i]
        if fd < cutoff:
            continue
        acc_dir = accs[i].replace("-", "")
        cik_num = str(int(cik))
        doc = docs[i]
        ext = os.path.splitext(doc)[1] or ".htm"
        fname = f"{fd}_{ticker}_announce_8K{ext}"
        dest = dest_dir / fname
        if dest.exists():
            log.info("%s — already exists", fname)
        else:
            try:
                dl = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_dir}/{doc}"
                req3 = urllib.request.Request(dl, headers={"User-Agent": UA})
                with urllib.request.urlopen(req3, timeout=120) as resp:
                    dest.write_bytes(resp.read())
                log.info("Saved → %s (%.1f MB)", dest, dest.stat().st_size / 1e6)
            except Exception as e:
                log.warning("8-K download failed for %s: %s", fd, e)
                continue
        if slug:
            try:
                _register_in_prism(slug, dest, "announcement", company_name, variant)
            except Exception as e:
                log.warning("Manifest register failed for %s: %s", fname, e)
        saved.append(dest)
    return saved


def fetch_by_keyword_cn(
    market_ticker: str,
    keyword: str,
    since_days: int | None = None,
    max_hits: int = 10,
    slug: str | None = None,
    variant: str | None = None,
) -> list[Path]:
    """按需检索 — A 股按关键词在公告标题里搜索，下载命中项。

    since_days: 限定近 N 天披露的；None = 不限。
    max_hits: 最多下载 N 份（命中过多时取最新 N 份）。
    返回：下载到本地的路径列表。

    与"顺手预拉"不同：这是 subagent 研究中 ad-hoc 调用，关键词由调用方给定（如
    "股权激励" / "股东大会" / "重大资产重组" / 公告全名匹配）。
    """
    _, ticker = _parse_market_ticker(market_ticker)
    dest_dir = _materials_dir(slug) if slug else _INBOX_AUTO
    dest_dir.mkdir(parents=True, exist_ok=True)

    info = _company_info(ticker)
    code, org_id = info["code"], info["orgId"]
    company_name = info.get("zwjc", ticker)
    column = _column(code)

    hits = _search_all_pages(code, org_id, column, keyword)
    # 过滤掉摘要/英文/更正/修订（与 _list_reports 一致）
    hits = [a for a in hits if not re.search(r"摘要|英文|更正|修订", a.get("announcementTitle", ""))]
    if since_days is not None:
        hits = [a for a in hits if _within_window(a, since_days)]

    if not hits:
        log.info("No matches for keyword %r on %s (since_days=%s)", keyword, company_name, since_days)
        return []

    # 按披露时间倒序，取最新 max_hits 份
    hits.sort(key=lambda a: a.get("announcementTime", 0), reverse=True)
    selected = hits[:max_hits]
    log.info("Keyword %r matched %d announcement(s) for %s; downloading %d",
             keyword, len(hits), company_name, len(selected))

    saved: list[Path] = []
    for a in selected:
        try:
            # 用关键词做 category_key 占位，方便文件名区分手动检索结果
            safe_kw = re.sub(r"[^\w\-]", "", keyword)[:20] or "search"
            p = _download_announcement(a, dest_dir, company_name, ticker, f"search_{safe_kw}")
            saved.append(p)
            if slug:
                _register_in_prism(slug, p, "announcement", company_name, variant)
        except Exception as e:
            log.warning("Download failed (%s): %s", a.get("announcementTitle", "?")[:30], e)
    return saved


def fetch_by_keyword_us(
    ticker: str,
    keyword: str,
    since_days: int | None = None,
    max_hits: int = 10,
    forms: tuple[str, ...] = ("8-K", "10-K", "10-Q", "20-F", "6-K", "DEF 14A"),
    slug: str | None = None,
    variant: str | None = None,
) -> list[Path]:
    """按需检索 — 美股走 EDGAR full-text search (efts.sec.gov)。

    forms: 限定文件类型；默认覆盖披露+财报+代理声明。
    返回：下载到本地的路径列表。
    """
    import json
    import os
    import urllib.parse
    import urllib.request

    UA = "investment-wiki research@example.com"
    dest_dir = _materials_dir(slug) if slug else _INBOX_AUTO
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Resolve CIK
    req = urllib.request.Request(
        "https://www.sec.gov/files/company_tickers.json", headers={"User-Agent": UA}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    cik_map = {v["ticker"].upper(): (str(v["cik_str"]).zfill(10), v["title"]) for v in data.values()}
    if ticker.upper() not in cik_map:
        raise ValueError(f"SEC CIK not found for ticker {ticker}")
    cik, company_name = cik_map[ticker.upper()]
    cik_int = int(cik)

    # efts 全文搜索：q=keyword&ciks=<10-digit>&forms=8-K,10-K&dateRange=custom&startdt=...
    params = {
        "q": f'"{keyword}"' if " " in keyword else keyword,
        "ciks": cik,
        "forms": ",".join(forms),
    }
    if since_days is not None:
        from datetime import timedelta
        start = (date.today() - timedelta(days=since_days)).isoformat()
        params["dateRange"] = "custom"
        params["startdt"] = start
        params["enddt"] = date.today().isoformat()
    url = "https://efts.sec.gov/LATEST/search-index?" + urllib.parse.urlencode(params)

    req2 = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req2, timeout=30) as resp:
        result = json.loads(resp.read())
    hits = result.get("hits", {}).get("hits", [])
    if not hits:
        log.info("efts no matches for keyword %r on %s (forms=%s, since_days=%s)",
                 keyword, ticker, forms, since_days)
        return []

    # efts 已按 relevance 排序，取前 max_hits
    selected = hits[:max_hits]
    log.info("Keyword %r matched %d filing(s) for %s; downloading %d",
             keyword, len(hits), ticker, len(selected))

    saved: list[Path] = []
    for h in selected:
        src = h.get("_source", {})
        # _id 形如 "0001045810-26-000021:nvda-20260125.htm"
        hit_id = h.get("_id", "")
        if ":" not in hit_id:
            log.warning("Skipping malformed efts hit id: %s", hit_id)
            continue
        acc, doc = hit_id.split(":", 1)
        acc_dir = acc.replace("-", "")
        form = (src.get("form") or "UNKNOWN").replace("/", "-")
        fd = src.get("file_date") or src.get("filed", "")[:10] or "unknown"
        ext = os.path.splitext(doc)[1] or ".htm"
        safe_kw = re.sub(r"[^\w\-]", "", keyword)[:20] or "search"
        fname = f"{fd}_{ticker}_search_{safe_kw}_{form}{ext}"
        dest = dest_dir / fname
        if dest.exists():
            log.info("Already exists: %s", fname)
        else:
            dl = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_dir}/{doc}"
            try:
                req3 = urllib.request.Request(dl, headers={"User-Agent": UA})
                with urllib.request.urlopen(req3, timeout=120) as resp:
                    dest.write_bytes(resp.read())
                log.info("Saved → %s (%.1f MB)", dest, dest.stat().st_size / 1e6)
            except Exception as e:
                log.warning("EDGAR download failed (%s): %s", fname, e)
                continue
        if slug:
            try:
                _register_in_prism(slug, dest, "announcement", company_name, variant)
            except Exception as e:
                log.warning("Manifest register failed (%s): %s", fname, e)
        saved.append(dest)
    return saved


def fetch_by_keyword(
    market_ticker: str,
    keyword: str,
    since_days: int | None = None,
    max_hits: int = 10,
    slug: str | None = None,
    variant: str | None = None,
) -> list[Path]:
    """按需检索路由 — 按 market_ticker 分发到 _cn / _us。其他市场暂未支持。"""
    market = _route(market_ticker)
    if market == "cn":
        return fetch_by_keyword_cn(market_ticker, keyword, since_days, max_hits, slug, variant)
    if market == "us":
        return fetch_by_keyword_us(market_ticker, keyword, since_days, max_hits,
                                    slug=slug, variant=variant)
    raise NotImplementedError(
        f"按需关键词检索暂未支持 {market} 市场（仅 cn / us）。如需，可走 mineru ingest 手动路径。"
    )


def fetch(
    market_ticker: str,
    report_type: str = "annual",
    year: int | None = None,
    slug: str | None = None,
    variant: str | None = None,
    quarter: int | None = None,
    with_announcements: bool = True,
) -> Path:
    """Download a financial report. Returns the local file path.

    Auto-routes by ticker format:
        US (NVDA) → SEC EDGAR
        CN (SZSE_300750) → cninfo
        HK (HK_02228) → HKEXnews (zero-key, annual/semi/prospectus)
        UK (LSE_OXIG) → FCA NSM (zero-key, annual/semi)
        KR (006400 / KRX_006400) → DART
        JP TDnet (5019 / TSE_5019) → TDnet 決算短信 (zero-key, 30-day window)
        JP EDINET (EDINET_E00040) → EDINET v2 API (需要 EDINET_API_KEY)

    quarter (only for report_type='quarterly' + cninfo): 1 or 3 to force Q1/Q3;
        None → fan-out 查 Q1+Q3 两个 category，按 announcementTime 取最新一份（避免
        cninfo 一/三季报分属不同 category 导致 Q1 找不到）。
    """
    market = _route(market_ticker)

    if market == "us":
        results = fetch_sec(market_ticker, slug, variant, with_announcements=with_announcements)
        return results[0] if results else None

    if market == "kr":
        from scripts.fetch_kr_dart import fetch as _fetch_kr
        kr_ticker = market_ticker.removeprefix("KRX_")
        return _fetch_kr(kr_ticker, report_type, slug, variant)

    if market == "jp_tdnet":
        from scripts.fetch_jp_tdnet import fetch as _fetch_tdnet
        jp_code = market_ticker.removeprefix("TSE_")
        keyword = _JP_KEYWORD.get(report_type, "決算短信")
        return _fetch_tdnet(jp_code, keyword, "earnings-flash", slug, variant)

    if market == "jp_edinet":
        from scripts.fetch_jp_edinet import fetch as _fetch_edinet
        ed_code = market_ticker.removeprefix("EDINET_")
        return _fetch_edinet(None, ed_code, report_type, slug, variant)

    if market == "hk":
        from scripts.fetch_hk_hkex import fetch as _fetch_hk
        hk_code = market_ticker.removeprefix("HK_")
        return _fetch_hk(hk_code, report_type, slug, variant)

    if market == "uk":
        from scripts.fetch_uk_fca import fetch as _fetch_uk
        uk_ticker = market_ticker.removeprefix("LSE_")
        return _fetch_uk(uk_ticker, report_type, slug, variant)

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
    print(f"\033[33m⚑ COMPANY RESOLVED: {company_name} (ticker {ticker}) — verify before proceeding\033[0m",
          file=sys.stderr)

    if report_type == "quarterly":
        # cninfo 一季报 (yjdbg) / 三季报 (sjdbg) 分属不同 category — 必须 fan-out
        if quarter is not None and quarter not in (1, 3):
            raise ValueError(f"quarter={quarter!r} 非法，必须为 1 或 3 或 None（自动取最新）")
        cats = (f"q{quarter}",) if quarter else _QUARTERLY_CATEGORIES
        log.info("Fetching quarterly (%s) report list for %s (%s)…", "+".join(cats), company_name, code)
        reports: list[dict] = []
        for ck in cats:
            reports.extend(_list_reports(code, org_id, column, _CATEGORY[ck]))
    else:
        log.info("Fetching %s report list for %s (%s)…", report_type, company_name, code)
        reports = _list_reports(code, org_id, column, _CATEGORY[report_type])

    # Find the target year
    matches = [r for r in reports if _extract_year(r.get("announcementTitle", "")) == year]
    if not matches:
        if report_type == "quarterly":
            # 季报 Q1/Q3 同年共存，year 去重会丢季度信息——直接列标题
            titles = [r.get("announcementTitle", "")[:30] for r in reports[:8]]
            avail_str = f"Available quarterly reports (latest {len(titles)}): {titles}"
        else:
            years = sorted(
                {_extract_year(r.get("announcementTitle", "")) for r in reports} - {None},
                reverse=True,
            )
            avail_str = f"Available years: {years}"
        hint = _disclosure_window_hint(report_type, year)
        raise ValueError(
            f"No {report_type} report found for {year}. {avail_str}{hint}"
        )

    # quarterly fan-out（quarter=None）：跨 Q1/Q3 时取最新一份（Q3 已披露则优先 Q3）
    # 其他场景（annual/semi/quarterly 单 quarter）：保留原"取首发版"语义（过滤后的最早披露）
    fan_out = report_type == "quarterly" and quarter is None
    target = sorted(matches, key=lambda r: r["announcementTime"], reverse=fan_out)[0]
    log.info("Found: %s", target["announcementTitle"])

    file_path = _download(target, dest_dir, company_name, ticker=ticker, report_type=report_type)

    if slug:
        _register_in_prism(slug, file_path, report_type, company_name, variant)

    if with_announcements:
        try:
            ann = fetch_announcements_cn(market_ticker, slug, variant)
            if ann:
                log.info("Fetched %d announcement(s) for %s", len(ann), company_name)
        except Exception as e:
            log.warning("Announcement fetch failed for %s: %s", company_name, e)

    return file_path


def fetch_many(
    market_ticker: str,
    years: list[int],
    report_type: str = "annual",
    slug: str | None = None,
    variant: str | None = None,
    quarter: int | None = None,
    with_announcements: bool = True,
) -> list[Path]:
    """Batch-fetch multiple years of a single report type. CN only (SEC has its own pagination).

    Announcements are fetched once (after all years), not per-year, to avoid redundant cninfo calls.
    """
    paths: list[Path] = []
    for y in years:
        try:
            # Suppress per-year announcement fetch — we batch it once at the end.
            p = fetch(market_ticker, report_type, y, slug, variant,
                      quarter=quarter, with_announcements=False)
            if p:
                paths.append(p)
        except ValueError as e:
            log.warning("Year %d skipped: %s", y, e)

    if with_announcements and paths:
        market = _route(market_ticker)
        try:
            if market == "cn":
                ann = fetch_announcements_cn(market_ticker, slug, variant)
            elif market == "us":
                ann = fetch_announcements_us(market_ticker, slug, variant)
            else:
                ann = []
            if ann:
                log.info("Fetched %d announcement(s) for %s", len(ann), market_ticker)
        except Exception as e:
            log.warning("Announcement fetch failed for %s: %s", market_ticker, e)

    return paths


def _parse_years(spec: str) -> list[int]:
    """Parse '2020-2024' or '2020,2022,2024' into [2020, 2021, 2022, 2023, 2024] / [2020, 2022, 2024]."""
    spec = spec.strip()
    if "-" in spec and "," not in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",") if x.strip()]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Download financial report to prism/inbox/auto/")
    parser.add_argument("ticker", help="Market_Ticker, e.g. SSE_688066")
    parser.add_argument("--type", choices=["annual", "semi", "quarterly", "prospectus"], default="annual")
    parser.add_argument("--year", type=int, default=None, help="Fiscal year (default: last year)")
    parser.add_argument("--years", default=None,
                        help="Multi-year batch: '2020-2024' (range) or '2020,2022,2024' (list). CN only.")
    parser.add_argument("--slug", default=None,
                        help="Prism topic slug — registers manifest + updates user_todos")
    parser.add_argument("--variant", default=None,
                        help="Model variant — registers in this variant's manifest")
    parser.add_argument("--quarter", type=int, choices=[1, 3], default=None,
                        help="Force Q1 or Q3 (only for --type quarterly, CN cninfo only). "
                             "Default: fan-out 查 Q1+Q3 取最新。")
    parser.add_argument("--no-announcements", action="store_true",
                        help="跳过近 1 年高信号公告抓取（默认顺手拉）。"
                             "A 股: 业绩预告/股权激励/增发/可转债/风险提示/特别处理；美股: 8-K。")
    parser.add_argument("--search", default=None, metavar="KEYWORD",
                        help="按需检索模式：按关键词在公告标题里搜索（A 股 cninfo / 美股 EDGAR 全文）。"
                             "与 --type/--year/--years 互斥；不下载财报，只下命中公告。")
    parser.add_argument("--since-days", type=int, default=None,
                        help="--search 时限定近 N 天披露的；不传 = 不限。")
    parser.add_argument("--max-hits", type=int, default=10,
                        help="--search 时最多下载 N 份（默认 10）。")
    args = parser.parse_args()

    with_ann = not args.no_announcements

    if args.search:
        if args.year or args.years:
            print("Error: --search 与 --year/--years 互斥", file=sys.stderr)
            sys.exit(2)
        try:
            paths = fetch_by_keyword(args.ticker, args.search,
                                     since_days=args.since_days, max_hits=args.max_hits,
                                     slug=args.slug, variant=args.variant)
            for p in paths:
                print(p)
            return
        except (ValueError, NotImplementedError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        if args.years:
            years = _parse_years(args.years)
            paths = fetch_many(args.ticker, years, args.type, args.slug, args.variant,
                               quarter=args.quarter, with_announcements=with_ann)
            for p in paths:
                print(p)
        else:
            path = fetch(args.ticker, args.type, args.year, args.slug, args.variant,
                         quarter=args.quarter, with_announcements=with_ann)
            print(path)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Download Japanese stock annual reports (有価証券報告書) from EDINET v2 API.

需要 API key —— EDINET v2 强制 Subscription-Key（v1 已停用，浏览站点 GeneXus 表单 POST 校验严，不便爬）。

注册流程（5 分钟，免费）：
    1. https://api.edinet-fsa.go.jp/api/auth/index.html → 「利用登録」
    2. 邮箱验证 → 拿到 Subscription-Key
    3. export EDINET_API_KEY=xxxxx 或写入 .env

Usage:
    # mode A: 已知 docID（最快，从 EDINET 浏览器手动找到）
    python -m scripts.fetch_jp_edinet --doc-id S100T2BX --slug global-ssb-electrolyte

    # mode B: 按 EdinetCode 自动搜索（扫最近 N 天）
    python -m scripts.fetch_jp_edinet --edinet-code E00040 --type annual

EdinetCode 查询：
    出光興産 = E00040, 三井金属 = E00021, トヨタ = E02144 …
    下载完整列表：
        curl -H "Ocp-Apim-Subscription-Key: $EDINET_API_KEY" \
             "https://api.edinet-fsa.go.jp/api/v2/edinetcodes/edinetCode.csv?type=2" -o edinet_codes.csv

docTypeCode（关键）：
    120 = 有価証券報告書（年报）
    140 = 四半期報告書（季报）
    160 = 半期報告書（半年报）
    180 = 臨時報告書

Notes:
    - documents.json 按日期分页（一天一查），不支持按公司直接搜索 → 反向扫描最近 365 天
    - 下载 type=2 (PDF), type=1 (ZIP with XBRL), type=4 (CSV)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

log = logging.getLogger("fetch_jp_edinet")

_API_HOST = "https://api.edinet-fsa.go.jp/api/v2"
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0"

_DOC_TYPE = {
    "annual":    "120",  # 有価証券報告書
    "quarterly": "140",  # 四半期報告書
    "semi":      "160",  # 半期報告書
}

_INBOX_AUTO = Path(__file__).parent.parent / "prism" / "inbox" / "auto"


def _api_key() -> str:
    key = os.environ.get("EDINET_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "EDINET_API_KEY 未设置。\n"
            "  注册：https://api.edinet-fsa.go.jp/api/auth/index.html\n"
            "  使用：export EDINET_API_KEY=xxxxx"
        )
    return key


def _materials_dir(slug: str) -> Path:
    return Path(__file__).parent.parent / "prism" / "topics" / slug / "materials"


def _http_get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _http_get_bytes(url: str) -> tuple[bytes, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read(), r.headers.get("Content-Type")


def _list_documents(target_date: date) -> list[dict]:
    """List all documents disclosed on given date. Returns list of metadata dicts."""
    qs = urllib.parse.urlencode({
        "date": target_date.isoformat(),
        "type": "2",  # type=2 → 提出書類一覧 + メタデータ
        "Subscription-Key": _api_key(),
    })
    data = _http_get_json(f"{_API_HOST}/documents.json?{qs}")
    if data.get("metadata", {}).get("status") != "200":
        msg = data.get("metadata", {}).get("message", "unknown")
        raise ValueError(f"EDINET API error: {msg}")
    return data.get("results", [])


def _find_doc_by_edinet_code(edinet_code: str, doc_type_code: str,
                              max_days: int = 365) -> dict:
    """反向扫描最近 max_days 天的 documents.json，找最新匹配的文档。"""
    today = date.today()
    log.info("Scanning EDINET last %d days for edinetCode=%s docType=%s …",
             max_days, edinet_code, doc_type_code)
    for offset in range(max_days):
        d = today - timedelta(days=offset)
        try:
            docs = _list_documents(d)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        for doc in docs:
            if (doc.get("edinetCode") == edinet_code
                    and doc.get("docTypeCode") == doc_type_code):
                log.info("Found: %s (%s) → docID=%s",
                         doc.get("filerName"), d, doc.get("docID"))
                return doc
        if offset > 0 and offset % 30 == 0:
            log.info("  scanned %d days, no match yet…", offset)
    raise ValueError(
        f"未找到 edinetCode={edinet_code} docType={doc_type_code} 的文档（{max_days} 天内）"
    )


def _download_pdf(doc_id: str, dest: Path) -> Path:
    """Download PDF for given docID."""
    qs = urllib.parse.urlencode({
        "type": "2",  # type=2 → PDF
        "Subscription-Key": _api_key(),
    })
    url = f"{_API_HOST}/documents/{doc_id}?{qs}"
    log.info("Downloading %s …", dest.name)
    body, ctype = _http_get_bytes(url)
    if not body.startswith(b"%PDF"):
        snippet = body[:300].decode("utf-8", errors="replace")
        raise ValueError(f"EDINET 返回非 PDF (Content-Type={ctype})：{snippet}")
    dest.write_bytes(body)
    log.info("Saved → %s (%.1f MB)", dest, len(body) / 1e6)
    return dest


def _normalized_filename(meta: dict, doc_id: str, report_type: str) -> str:
    """E7 schema-ish: {report_year}_{ticker_or_edinet}_{form}_{filing_date}_{company}.pdf"""
    period_end = meta.get("periodEnd") or ""  # YYYY-MM-DD
    year = period_end[:4] if period_end else (meta.get("submitDateTime") or "")[:4] or "0000"
    company = (meta.get("filerName") or doc_id).replace("/", "-").replace(" ", "")
    sec_code = (meta.get("secCode") or "").rstrip("0") or meta.get("edinetCode") or doc_id
    fd = (meta.get("submitDateTime") or "")[:10]
    return f"{year}_{sec_code}_{report_type}_{fd}_{company}.pdf"


def _register_in_prism(slug: str, file_path: Path, report_type: str,
                        company_name: str, variant: str | None = None) -> None:
    from scripts.fetch_report_prism import _register_in_prism as _reg
    _reg(slug, file_path, report_type, company_name, variant)


def fetch(
    doc_id: str | None = None,
    edinet_code: str | None = None,
    report_type: str = "annual",
    slug: str | None = None,
    variant: str | None = None,
    max_days: int = 365,
) -> Path:
    """Download Japanese annual/quarterly/semi report. Either doc_id or edinet_code required."""
    doc_type_code = _DOC_TYPE.get(report_type)
    if not doc_type_code:
        raise ValueError(f"report_type 必须是 annual/quarterly/semi: got {report_type!r}")

    if doc_id:
        log.info("Direct download by docID: %s", doc_id)
        # 没有 metadata，文件名退化为 docID
        meta = {"docID": doc_id, "filerName": doc_id}
    elif edinet_code:
        meta = _find_doc_by_edinet_code(edinet_code, doc_type_code, max_days)
        doc_id = meta["docID"]
        print(f"\033[33m⚑ EDINET RESOLVED: {meta.get('filerName')} "
              f"(edinetCode={edinet_code}, secCode={meta.get('secCode')}) "
              f"→ docID={doc_id} period={meta.get('periodEnd')} submit={meta.get('submitDateTime')}\033[0m",
              file=sys.stderr)
    else:
        raise ValueError("必须传入 doc_id 或 edinet_code 之一")

    dest_dir = _materials_dir(slug) if slug else _INBOX_AUTO
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = _normalized_filename(meta, doc_id, report_type)
    dest = dest_dir / fname
    if dest.exists():
        log.info("Already exists: %s", dest.name)
    else:
        _download_pdf(doc_id, dest)

    if slug:
        _register_in_prism(slug, dest, report_type, meta.get("filerName") or doc_id, variant)

    return dest


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Download Japanese annual reports from EDINET v2 API")
    parser.add_argument("--doc-id", help="EDINET docID (e.g. S100T2BX)，从浏览器手动获取")
    parser.add_argument("--edinet-code", help="EdinetCode (e.g. E00040 出光興産)，自动扫最近 N 天")
    parser.add_argument("--type", choices=["annual", "semi", "quarterly"], default="annual")
    parser.add_argument("--slug", default=None, help="Prism topic slug — registers manifest")
    parser.add_argument("--variant", default=None, help="Prism variant for manifest")
    parser.add_argument("--max-days", type=int, default=365, help="扫描天数上限（仅 --edinet-code 模式）")
    args = parser.parse_args()

    if not args.doc_id and not args.edinet_code:
        parser.error("必须指定 --doc-id 或 --edinet-code 之一")

    try:
        path = fetch(args.doc_id, args.edinet_code, args.type, args.slug, args.variant, args.max_days)
        print(path)
    except (ValueError, RuntimeError, urllib.error.HTTPError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

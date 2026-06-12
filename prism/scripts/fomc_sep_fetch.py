"""FOMC 点阵图(SEP) 中位联邦基金利率取数通道（零 LLM）。读登记表里 fetch_method=='fomc_sep' 且
availability=='scripted' 的输入，从 Fed FOMC 日历页发现最新季度投影表（fomcprojtabl{YYYYMMDD}.htm），
解析 Table 1「Federal funds rate」行的近年中位 → record_observation。

与 fedwatch_fetch 平行（脚本「数值」通道）且互补：FedWatch 给市场**隐含**政策路径，本通道给
FOMC **自己昭示**的中位路径——二者之差即「市场 vs Fed」预期差。

口径：SEP 每季度（3/6/9/12 月会议）一次，故 cadence_type=event。Table 1「Federal funds rate」行
剥标签后文本以 "Federal funds rate" 开头，其后第一个数字 = 最近完整日历年年底中位（现 = 3.4）。
"""
from __future__ import annotations

import re
import sys

import httpx

from prism.scripts import macro_registry as reg

_FED_BASE = "https://www.federalreserve.gov"
_CALENDAR_URL = _FED_BASE + "/monetarypolicy/fomccalendars.htm"
_INPUT_NAME = "FOMC 点阵图(SEP)"

_PROJTABL_RE = re.compile(r"fomcprojtabl(\d{8})\.htm")
_TR_RE = re.compile(r"<tr[^>]*>.*?</tr>", re.IGNORECASE | re.DOTALL)
_ANY_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_FFR_LABEL = "Federal funds rate"


def find_latest_projtabl(calendar_html: str) -> tuple[str, str] | tuple[None, None]:
    """从日历页提取最新（日期最大）投影表 URL。返回 (绝对url, as_of='YYYY-MM-DD')；无命中 → (None, None)。"""
    dates = _PROJTABL_RE.findall(calendar_html)
    if not dates:
        return None, None
    d = max(dates)
    url = f"{_FED_BASE}/monetarypolicy/fomcprojtabl{d}.htm"
    as_of = f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return url, as_of


def parse_median_funds_rate(projtabl_html: str) -> float | None:
    """从投影表取「Federal funds rate」行的第一个数字（近年中位）。无该行/无数字 → None（诚实）。"""
    for row in _TR_RE.findall(projtabl_html):
        txt = _WS.sub(" ", _ANY_TAG.sub(" ", row)).strip()
        if txt.startswith(_FFR_LABEL):
            m = _NUM_RE.search(txt[len(_FFR_LABEL):])
            if m:
                return float(m.group(0))
    return None


def fetch_fomc_sep(slug: str, variant: str, *, client: httpx.Client | None = None,
                   input_name: str | None = None) -> dict:
    """发现最新投影表→解析近年中位→record_observation。返回 {value, as_of, url, ok}；
    任一步取不到 → {"error": ...}（真失败，调度器据此记 fetch_error）。"""
    target = input_name or _INPUT_NAME
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        try:
            cal = client.get(_CALENDAR_URL, timeout=30, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0"})
            cal.raise_for_status()
        except httpx.HTTPError as exc:
            return {"error": f"FOMC 日历页抓取失败：{exc}"}
        url, as_of = find_latest_projtabl(cal.text)
        if url is None:
            return {"error": "日历页未找到投影表链接（站点结构可能变更）"}
        try:
            tbl = client.get(url, timeout=30, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0"})
            tbl.raise_for_status()
        except httpx.HTTPError as exc:
            return {"error": f"投影表抓取失败（{url}）：{exc}"}
        median = parse_median_funds_rate(tbl.text)
        if median is None:
            return {"error": f"投影表未解析到 Federal funds rate 中位行（{url}）"}
        reg.record_observation(slug, variant, target, value=median, as_of=as_of)
        return {"value": median, "as_of": as_of, "url": url, "ok": True}
    finally:
        if owns:
            client.close()


def run_fomc_sep_fetch(slug: str, variant: str, *, only: set[str] | None = None,
                       client: httpx.Client | None = None) -> dict:
    """抓所有 fetch_method=='fomc_sep' 且 availability=='scripted' 的输入（一般仅 1 条）。
    失败记 record_fetch_error 计数、不连累其余。返回 {fetched, skipped_todo, failed}。"""
    data = reg.read_registry(slug, variant)
    fetched = skipped_todo = failed = 0
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        for e in data["inputs"]:
            if e.get("fetch_method") != "fomc_sep":
                continue
            if only is not None and e["name"] not in only:
                continue
            if e.get("availability") != "scripted":
                skipped_todo += 1
                continue
            res = fetch_fomc_sep(slug, variant, client=client, input_name=e["name"])
            if res.get("error"):
                reg.record_fetch_error(slug, variant, e["name"], msg=res["error"])
                failed += 1
            else:
                fetched += 1
        return {"fetched": fetched, "skipped_todo": skipped_todo, "failed": failed}
    finally:
        if owns:
            client.close()


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:  # 活体冒烟：拉真表打印中位
        url, as_of = find_latest_projtabl(
            httpx.get(_CALENDAR_URL, timeout=30, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"}).text)
        if url is None:
            print("未找到投影表链接")
            return
        tbl = httpx.get(url, timeout=30, follow_redirects=True,
                        headers={"User-Agent": "Mozilla/5.0"})
        print(f"最新投影表 {url}（as_of {as_of}）")
        print(f"  近年中位联邦基金利率 = {parse_median_funds_rate(tbl.text)}")
        return
    slug = argv[0]
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    print(f"fomc_sep 抓取: {run_fomc_sep_fetch(slug, variant)}")


if __name__ == "__main__":
    main()

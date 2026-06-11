"""SAFE 取数通道（外管局 Excel）。零 LLM：读登记表里 fetch_method=='safe' 且
availability=='scripted' 且有 safe 配置块的输入，下最新 Excel → 解析 → record_observation。

与 fred_fetch / recipe_fetch / akshare_fetch 平行（都是脚本「数值」通道）。SAFE 把
「银行结售汇」「银行代客涉外收付」按月发成 .xlsx/.xls 月度表，且**2 跳**：稳定文章页 →
其内嵌的最新 `/safe/file/file/YYYYMMDD/<hash>.xls(x)` 下载链 → 表格解析。既有 recipe 通道
（单跳 url+parse、kind∈json/csv/matrix/html，无 xlsx）装不下，故仿 akshare「非单 URL→自列薄通道」
单列一个薄通道。核心 fetch_by_safe 可注入 client（测试 mock，等价 recipe 的 client）；
解析层 _pick_latest_file_url / _extract_latest_from_excel 是纯函数，离线可测。

为何「取最右非空月 + 表头日期归一」：SAFE 月度表是横表（行=指标如「三、差额」，列=各月，
表头是 Excel 序列日期），新月在最右、且尾部常有若干空列待填；故按 row_label 定位指标行后，
取该行最右侧有数值那列，as_of 从同列表头日期（Excel 序列号 → 日历月）反推。
"""
from __future__ import annotations

import datetime
import io
import math
import re
import sys
from urllib.parse import urlsplit

import httpx

from prism.scripts import macro_registry as reg

_CHROME_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# SAFE 下载链：/safe/file/file/YYYYMMDD/<hash>.xls(x)。捕获 (整段路径, YYYYMMDD)，按日期取最新。
_FILE_HREF = re.compile(r'(/safe/file/file/(\d{8})/[^"\'\s>]+?\.(?:xlsx|xls))', re.IGNORECASE)

# Excel 序列日期的合理区间（2009-01≈39814 … 2027-12≈46752），用于把表头序列号认成日期。
_SERIAL_LO, _SERIAL_HI = 30000, 60000
_EXCEL_EPOCH = datetime.datetime(1899, 12, 30)


def _abs_url(base_url: str, path: str) -> str:
    """把 SAFE 相对下载路径补成绝对 URL（取 article_url 的 scheme+host 作 base）。"""
    parts = urlsplit(base_url)
    return f"{parts.scheme}://{parts.netloc}{path}"


def _pick_latest_file_url(article_html: str, base_url: str) -> str | None:
    """从文章页 HTML 里挑**最新**的 Excel 下载链：扫所有 /safe/file/file/YYYYMMDD/*.xls(x)，
    取 YYYYMMDD 最大那条，补全绝对 URL。无命中 → None。"""
    best_date = ""
    best_path = None
    for path, yyyymmdd in _FILE_HREF.findall(article_html):
        if yyyymmdd > best_date:
            best_date, best_path = yyyymmdd, path
    return _abs_url(base_url, best_path) if best_path else None


def _to_month(cell) -> str | None:
    """把表头单元归一为 'YYYY-MM'（识别不了 → None）。
    认 datetime/Timestamp、Excel 序列号、'YYYY-MM'/'YYYY.M'/'YYYY年MM月'。"""
    if cell is None:
        return None
    if isinstance(cell, (datetime.datetime, datetime.date)):  # pandas Timestamp 亦命中（是 datetime 子类）
        return f"{cell.year:04d}-{cell.month:02d}"
    # 先试「YYYY-MM / YYYY.M / YYYY年MM月」串形（'2026.5' 这类点分串可被 float 误吞，故串形优先）。
    s = str(cell).strip()
    m = re.match(r"(\d{4})[-.年](\d{1,2})(?!\d)", s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
    # 再试数值（含 numpy 标量）：合理区间内认作 Excel 序列日期。float 强转兼容 numpy.int64/float64。
    try:
        num = float(cell)
    except (TypeError, ValueError):
        return None
    if not math.isnan(num) and _SERIAL_LO <= num <= _SERIAL_HI:
        d = _EXCEL_EPOCH + datetime.timedelta(days=int(num))
        return f"{d.year:04d}-{d.month:02d}"
    return None


def _to_num(cell) -> float | None:
    """数值单元转 float；空/NaN/非数 → None。去千分位逗号。"""
    if cell is None:
        return None
    if isinstance(cell, str):
        cell = cell.replace(",", "").strip()
        if not cell:
            return None
    try:
        f = float(cell)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _read_sheet(content: bytes, sheet: str):
    """按文件魔数选引擎读某 sheet（header=None，保留行列原位）。.xlsx(PK zip)→openpyxl；.xls(OLE)→xlrd。"""
    import pandas as pd
    engine = "openpyxl" if content[:2] == b"PK" else "xlrd"
    return pd.read_excel(io.BytesIO(content), sheet_name=sheet, header=None, engine=engine)


def _extract_latest_from_excel(content: bytes, sheet: str, row_label: str) -> tuple[float | None, str | None]:
    """SAFE 横表取最新月值：定位首列文本以 row_label 起的指标行 → 取该行**最右侧非空数值**列 →
    as_of 从同列表头（上方含最多日期格那行）日期归一。任何对不上 → 诚实 (None, as_of)，不抛。"""
    df = _read_sheet(content, sheet)
    grid = df.values.tolist()
    if not grid:
        return None, None
    # 1) 指标行：首列（去空白）以 row_label 起
    target = None
    for r, row in enumerate(grid):
        first = "" if not row else str(row[0]).strip()
        if first.startswith(row_label):
            target = r
            break
    if target is None:
        return None, None
    # 2) 该行最右侧非空数值列（横表新月在最右，尾部可能有空列）
    row = grid[target]
    col = None
    val = None
    for c in range(len(row) - 1, 0, -1):
        f = _to_num(row[c])
        if f is not None:
            col, val = c, f
            break
    if col is None:
        return None, None
    # 3) as_of：在指标行上方挑「日期格最多」的表头行，取其 col 列日期
    header_row = None
    best_hits = 0
    for r in range(target):
        hits = sum(1 for cell in grid[r] if _to_month(cell) is not None)
        if hits > best_hits:
            best_hits, header_row = hits, r
    as_of = None
    if header_row is not None and col < len(grid[header_row]):
        as_of = _to_month(grid[header_row][col])
    return val, as_of


def fetch_by_safe(cfg: dict, *, client=None) -> tuple[float | None, str | None]:
    """按 safe 配置抓一个数值。cfg: {article_url, sheet, row_label, unit?}。
    2 跳：GET article_url → 挑最新 Excel 下载链 → GET 文件 → 解析最新月值。
    缺最新链 / 解析对不上 → 诚实 (None, as_of)，不抛。client 可注入（测试 mock）。"""
    article_url = cfg.get("article_url")
    sheet = cfg.get("sheet")
    row_label = cfg.get("row_label")
    if not article_url or not sheet or not row_label:
        raise ValueError("safe 配置缺 article_url / sheet / row_label")
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        kw = {"timeout": 30, "headers": {"User-Agent": _CHROME_UA}, "follow_redirects": True}
        resp = client.get(article_url, **kw)
        resp.raise_for_status()
        file_url = _pick_latest_file_url(resp.text, article_url)
        if not file_url:
            return None, None
        fresp = client.get(file_url, **kw)
        fresp.raise_for_status()
        content = fresp.content
    finally:
        if owns:
            client.close()
    return _extract_latest_from_excel(content, sheet, row_label)


def run_safe_fetch(slug: str, variant: str, *, only: set[str] | None = None,
                   client=None) -> dict:
    """抓所有 fetch_method=='safe' 且 availability=='scripted' 且有 safe 配置的输入。
    llm 项诚实跳过计数（它们走 headless LLM）。only 给定时只抓名字在其中的项（web 单条手动抓）。
    失败（抛异常/取不到值）记 record_fetch_error 并计数，不连累其余。返回 summary。"""
    data = reg.read_registry(slug, variant)
    fetched = skipped_todo = skipped_llm = failed = 0
    for e in data["inputs"]:
        if e.get("fetch_method") != "safe":
            continue
        if only is not None and e["name"] not in only:
            continue
        avail = e.get("availability")
        if avail == "llm":
            skipped_llm += 1
            continue
        if avail != "scripted" or not e.get("safe"):
            skipped_todo += 1
            continue
        try:
            val, as_of = fetch_by_safe(e["safe"], client=client)
        except Exception as exc:                       # HTTP/解析/缺配置等：记错、跳过，不连累其余
            reg.record_fetch_error(slug, variant, e["name"], msg=str(exc))
            failed += 1
            continue
        if val is None:
            reg.record_fetch_error(slug, variant, e["name"],
                                   msg=f"safe 未取到值（源结构可能变更）: {e['safe'].get('article_url')}")
            failed += 1
            continue
        reg.record_observation(slug, variant, e["name"], value=val, as_of=as_of)
        fetched += 1
    return {"fetched": fetched, "skipped_todo": skipped_todo,
            "skipped_llm": skipped_llm, "failed": failed}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    print(f"safe 抓取: {run_safe_fetch(slug, variant)}")


if __name__ == "__main__":
    main()

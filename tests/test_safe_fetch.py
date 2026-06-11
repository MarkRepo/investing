"""SAFE 取数通道：纯解析层（零网络）。

覆盖 2 跳取数的两段纯函数：
  · _pick_latest_file_url：从文章页挑**最新** /safe/file/file/YYYYMMDD/*.xls(x) 下载链 + 绝对化 + 排非文件链接。
  · _extract_latest_from_excel：SAFE 横表（行=指标、列=各月、表头是 Excel 序列日期）按 row_label 定位指标行、
    取**最右非空数值**月、as_of 从同列表头序列号归一为 YYYY-MM。用 openpyxl 内存构表，不触网。
"""
from __future__ import annotations

import datetime
import io

from openpyxl import Workbook

from prism.scripts import safe_fetch as sf

_EPOCH = datetime.datetime(1899, 12, 30)


def _serial(y: int, m: int) -> int:
    """日历月首 → Excel 序列号（与 safe_fetch 归一互逆，用于构造表头）。"""
    return (datetime.datetime(y, m, 1) - _EPOCH).days


# ── _pick_latest_file_url ────────────────────────────────────────────────
_ARTICLE = """<html><body>
<a href="/safe/file/file/20260218/aaa111.xlsx">2026-01 数据(旧)</a>
<a href="/safe/file/file/20260520/bbb222.xlsx">2026-04 数据(最新)</a>
<a href="/safe/file/file/20260320/ccc333.xls">2026-02 数据(中)</a>
<a href="/safe/2023/0215/22329.html">本页固定链(非文件)</a>
</body></html>"""
_BASE = "https://www.safe.gov.cn/safe/2023/0215/22329.html"


def test_pick_latest_file_url_takes_max_date_and_absolutizes():
    url = sf._pick_latest_file_url(_ARTICLE, _BASE)
    assert url == "https://www.safe.gov.cn/safe/file/file/20260520/bbb222.xlsx"


def test_pick_latest_file_url_none_when_no_file_link():
    assert sf._pick_latest_file_url('<a href="/safe/2023/0215/22329.html">x</a>', _BASE) is None


# ── _extract_latest_from_excel ───────────────────────────────────────────
def _build_xlsx(sheet: str) -> bytes:
    """构造 SAFE 形态横表：标题行 + 表头(序列日期，末列留空) + 指标行(差额，末列留空待填)。"""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(["银行结售汇（以美元计价，月度）", None, None, None])          # row1 标题
    ws.append([None, _serial(2026, 2), _serial(2026, 3), _serial(2026, 4), None])  # row2 表头：含尾部空列
    ws.append(["一、结汇", 1500.0, 1600.0, 1700.0, None])                    # row3
    ws.append(["二、售汇", 1200.0, 1300.0, 1299.2, None])                    # row4
    ws.append(["三、差额", 300.0, 300.0, 400.8, None])                       # row5 目标行：最右非空=400.8(2026-04)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_extract_latest_picks_rightmost_nonempty_and_dates_it():
    content = _build_xlsx("以美元计价（月度）")
    val, as_of = sf._extract_latest_from_excel(content, "以美元计价（月度）", "三、差额")
    assert abs(val - 400.8) < 1e-9
    assert as_of == "2026-04"


def test_extract_returns_none_when_row_label_absent():
    content = _build_xlsx("以美元计价（月度）")
    val, as_of = sf._extract_latest_from_excel(content, "以美元计价（月度）", "三、收支差额")
    assert val is None


def test_to_month_handles_serial_timestamp_and_string():
    assert sf._to_month(_serial(2026, 4)) == "2026-04"            # Excel 序列号
    assert sf._to_month(datetime.datetime(2025, 12, 1)) == "2025-12"  # datetime
    assert sf._to_month("2026-03") == "2026-03"                   # 串
    assert sf._to_month("2026.5") == "2026-05"                    # 点分串
    assert sf._to_month(400.8) is None                            # 非序列区间的小数值不是日期


def test_to_num_strips_commas_and_rejects_blank():
    assert sf._to_num("1,234.5") == 1234.5
    assert sf._to_num("") is None
    assert sf._to_num(None) is None

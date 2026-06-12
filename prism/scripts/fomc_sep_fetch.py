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

"""Nasdaq Data Link 探针（一次性测试，非生产管道）。
目的：实测 NDL 能否取到 prism macro 当前缺口里的输入数据。
用法：NASDAQ_API_KEY=xxx python3 prism/scripts/nasdaq_probe.py
零依赖外的 httpx。每条探测打印：路径 / HTTP / 样本值 / 判定。

挑选的探测项 = 与 prism macro 缺口（llm/scriptable_todo）对得上的 NDL 免费/常见库。
已挂 FRED 的 35 项不测——NDL 对那些只是镜像，纯冗余。"""
from __future__ import annotations

import os
import sys

import httpx

BASE = "https://data.nasdaq.com/api/v3"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"

# (prism 缺口名, 类型, 库/表代码, 说明)
#   类型 dataset = 经典时间序列 /datasets/{code}.json
#   类型 datatable = /datatables/{code}.json（CFTC 等）
PROBES = [
    ("持仓拥挤(CFTC COT)", "datatable", "QDL/FON", "CFTC 期货持仓 Legacy(Futures Only)"),
    ("持仓拥挤(CFTC COT-合并)", "datatable", "QDL/LFON", "CFTC 期货+期权合并"),
    ("黄金", "dataset", "LBMA/GOLD", "LBMA 伦敦金定盘价"),
    ("白银(参照)", "dataset", "LBMA/SILVER", "LBMA 银——验证贵金属库可用性"),
    ("股票估值 CAPE", "dataset", "MULTPL/SHILLER_PE_RATIO_MONTH", "Shiller CAPE 月度"),
    ("CME FedWatch(联邦基金期货)", "dataset", "CHRIS/CME_FF1", "连续 fed funds 期货——多半已停更/付费"),
    ("UST 收益率曲线(对照FRED)", "dataset", "USTREASURY/YIELD", "财政部官方曲线"),
    ("UST 实际收益率(对照FRED)", "dataset", "USTREASURY/REALYIELD", "TIPS 实际曲线"),
    ("铜(大宗)", "dataset", "LME/PR_CU", "LME 铜——多半付费"),
    ("中国宏观(IMF/ODA)", "dataset", "ODA/CHN_NGDP_RPCH", "IMF WEO 中国实际 GDP 增速"),
]


def probe_dataset(client: httpx.Client, code: str, key: str) -> tuple[str, str]:
    url = f"{BASE}/datasets/{code}.json"
    try:
        r = client.get(url, params={"rows": 1, "api_key": key}, timeout=30,
                        headers={"User-Agent": UA})
    except Exception as e:  # noqa: BLE001
        return "ERR", f"{type(e).__name__}: {e}"
    ct = r.headers.get("content-type", "")
    if "json" not in ct:
        return f"HTTP {r.status_code}", "非 JSON（疑 Incapsula 反爬/重定向）"
    j = r.json()
    if "quandl_error" in j:
        e = j["quandl_error"]
        return f"HTTP {r.status_code}", f"{e['code']}: {e['message'][:80]}"
    d = j.get("dataset", {})
    data = d.get("data") or []
    sample = data[0] if data else None
    return f"HTTP {r.status_code}", f"OK 最新={sample} 列={d.get('column_names')}"


def probe_datatable(client: httpx.Client, code: str, key: str) -> tuple[str, str]:
    url = f"{BASE}/datatables/{code}.json"
    try:
        r = client.get(url, params={"qopts.per_page": 1, "api_key": key}, timeout=30,
                       headers={"User-Agent": UA})
    except Exception as e:  # noqa: BLE001
        return "ERR", f"{type(e).__name__}: {e}"
    ct = r.headers.get("content-type", "")
    if "json" not in ct:
        return f"HTTP {r.status_code}", "非 JSON（疑反爬）"
    j = r.json()
    if "quandl_error" in j:
        e = j["quandl_error"]
        return f"HTTP {r.status_code}", f"{e['code']}: {e['message'][:80]}"
    dt = j.get("datatable", {})
    rows = dt.get("data") or []
    cols = [c.get("name") for c in dt.get("columns", [])]
    return f"HTTP {r.status_code}", f"OK 行样本={rows[0] if rows else None} 列={cols[:8]}"


def main() -> int:
    key = os.getenv("NASDAQ_API_KEY") or os.getenv("QUANDL_API_KEY") or ""
    if not key:
        print("NASDAQ_API_KEY 未设置。用法：NASDAQ_API_KEY=xxx python3 prism/scripts/nasdaq_probe.py")
        return 2
    print(f"key 已读取（末4位 …{key[-4:]}）\n")
    ok = 0
    with httpx.Client() as client:
        for name, kind, code, note in PROBES:
            fn = probe_datatable if kind == "datatable" else probe_dataset
            status, detail = fn(client, code, key)
            verdict = "✅" if detail.startswith("OK") else "❌"
            if verdict == "✅":
                ok += 1
            print(f"{verdict} [{kind:9}] {code:30} {status:9} {detail}")
            print(f"          ↳ prism缺口: {name} | {note}")
    print(f"\n可取到: {ok}/{len(PROBES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

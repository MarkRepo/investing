"""surf · 美股 ETF 全量抓取与规则层剔除。

零 LLM 调用。数据源是 **Yahoo 的 ETF screener**（`yfinance.screen` + `ETFQuery`）：
免费、无 API key、非爬虫。替代了旧版手写死的 47 只字典。

为什么换：手写清单的漏项是系统性盲区，且不可见。实测规则化后 182 只，其中
`DRAM`（Roundhill Memory，存储超级周期的专用载体）与 `AIPO`（AI & Power
Infrastructure，AI 电力缺口的专用载体）都不在旧清单里——扫描 #001 判这两条
趋势时只能拿 GRID/PAVE 近似，结论建立在替代品的走势上（DESIGN §6.1）。

代理：yfinance 走 Yahoo **需要**代理，与 akshare 相反，本文件不清代理环境变量。
"""
from __future__ import annotations

import os
import sys

import pandas as pd

# Morningstar 行业/主题类目。Yahoo 的 ETF 分类里，行业 ETF 与主题 ETF 混在同一批
# 类目下（HACK 网络安全、WCLD 云软件都归 Technology），主题细分交给 LLM 层。
# 不含的：债券、市政债、目标日期、资产配置、地域股票、杠杆反向——那些不是产业载体。
CATEGORIES = [
    "Technology", "Health", "Financial", "Industrials", "Consumer Cyclical",
    "Consumer Defensive", "Communications", "Utilities", "Real Estate",
    "Equity Energy", "Equity Precious Metals", "Natural Resources",
    "Infrastructure", "Miscellaneous Sector",
]

# 基准：不参与剔除，恒定入池。
BENCHMARKS = {"SPY": "标普500", "QQQ": "纳斯达克100"}

MIN_AUM = 200e6        # 规模下限（美元）
MIN_VOL3M = 100_000    # 近 3 月日均成交股数下限
# 放宽版阈值用于**查询**，让不达标的也能被抓回来并在页面上带理由显示——
# 只有能看见砍了什么，才可能发现砍错了（DESIGN §6.1）。
QUERY_AUM = 50e6
QUERY_VOL3M = 20_000

US_EXCHANGES = ("PCX", "NGM", "NMS", "ASE", "NYQ", "BTS")
_LEVERAGED = ("2X", "3X", "-1X", "Bull", "Bear", "Ultra", "Inverse", "Leveraged")


def _query(cat: str):
    import yfinance.screener.query as Q
    # yfinance 的 categoryname 白名单是 Dec-2024 的硬编码快照，缺 Industrials /
    # Consumer Cyclical / Communications / Miscellaneous Sector 四类，但**服务端认**。
    # 不绕过客户端校验，工业与通信整段消失。
    Q.ETFQuery._validate_eq_operand = lambda self, op: None
    return Q.ETFQuery("and", [
        Q.ETFQuery("eq", ["categoryname", cat]),
        Q.ETFQuery("eq", ["region", "us"]),
        Q.ETFQuery("gt", ["fundnetassets", QUERY_AUM]),
        Q.ETFQuery("gt", ["avgdailyvol3m", QUERY_VOL3M]),
    ])


def build_universe() -> pd.DataFrame:
    """抓全量美股行业/主题 ETF，逐只标注规则层结论。

    列与 A 股侧对齐：代码 / 名称 / 类别 / AUM / 日均量 / 剔除原因 / 剔除说明
    """
    import yfinance as yf

    seen: dict[str, dict] = {}
    for cat in CATEGORIES:
        for off in range(0, 300, 100):
            try:
                r = yf.screen(_query(cat), size=100, offset=off,
                              sortField="fundnetassets", sortAsc=False)
            except Exception as e:
                print(f"[warn] {cat} offset={off} 失败: {type(e).__name__}: {e}",
                      file=sys.stderr)
                break
            quotes = r.get("quotes", [])
            for q in quotes:
                seen.setdefault(q["symbol"], {**q, "_cat": cat})
            if len(quotes) < 100:
                break

    rows = []
    for sym, q in seen.items():
        name = q.get("shortName") or q.get("longName") or ""
        aum = q.get("netAssets") or 0
        vol = q.get("averageDailyVolume3Month") or 0
        reason = note = ""
        if "." in sym or q.get("exchange") not in US_EXCHANGES:
            reason, note = "asset_class", f"非美国主板上市（{q.get('exchange')}）"
        elif any(k in name for k in _LEVERAGED):
            reason, note = "asset_class", "杠杆/反向产品，按杠杆倍数聚合而非按产业"
        elif aum <= MIN_AUM:
            reason, note = "illiquid", f"规模 {aum / 1e8:.2f} 亿美元 ≤ {MIN_AUM / 1e8:.0f} 亿"
        elif vol <= MIN_VOL3M:
            reason, note = "illiquid", f"3 月日均量 {vol / 1e4:.1f} 万股 ≤ {MIN_VOL3M / 1e4:.0f} 万股"
        rows.append({"代码": sym, "名称": name, "类别": q["_cat"],
                     "AUM": aum, "日均量": vol, "剔除原因": reason, "剔除说明": note})

    for sym, label in BENCHMARKS.items():
        if sym not in seen:
            rows.append({"代码": sym, "名称": label, "类别": "基准",
                         "AUM": None, "日均量": None, "剔除原因": "", "剔除说明": ""})

    return pd.DataFrame(rows).sort_values("代码").reset_index(drop=True)


if __name__ == "__main__":
    u = build_universe()
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "etf_universe_us.csv"))
    u.to_csv(out, index=False, encoding="utf-8-sig")
    n = int((u["剔除原因"] == "").sum())
    print(f"全量 {len(u)} 只，规则层通过 {n} 只 -> {out}", file=sys.stderr)
    print(u["剔除原因"].value_counts().to_string())

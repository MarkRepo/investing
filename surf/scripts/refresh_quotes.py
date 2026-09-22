"""surf · 刷新卡片标的的最新收盘价。

**与扫描快照分开存放，绝不回写 scans/。** 扫描快照是向前验证的历史记录，
改它等于改历史（DESIGN §3）；但页面上的「距止损还有多远」必须用最新收盘价算，
否则会像扫描 #001 那样停在建卡日前一天的价格上（新浪当日数据尚未发布）。

取价分两条路，各有理由：

**个股走 `scripts.fetch_quotes_eod.run_for_ticker`** —— 也就是 `/prices` 页面那个
「↻ 刷新」按钮背后的同一条管线（`POST /prices/{key}/refresh` 的 daily 部分）。
好处是一次抓取两头落地：surf 拿到最新收盘，`/prices/{key}` 页面也同时有了 K 线，
而且之后 `scripts/fetch_quotes_eod.py` 的批量 EOD 任务会自动带上它们，不必单独维护。
**只调 daily 不调 snapshot** —— snapshot 会写入当日盘中价，而周频系统只认收盘价
（DESIGN §10.1）。

**ETF 仍走 surf 自己的抓取器** —— ETF 不是公司，不该注册进 `companies/` 去污染
prism 的公司列表；而 quotes 管线的标的必须有交易所代码归属。

⚠️ **指标层（`scan_stock.py`）不能改用这条管线**：适配器存的是**不复权**价
（`stock_zh_a_daily(adjust="")` / `yfinance(auto_adjust=False)`），除权会在
ret20/ret60 上凿出假缺口，性质同 §6.4 ① 的 ETF 份额折算。最新收盘价不受影响
（前复权以最新价为锚，最新一根本来就等于原始价），所以只有取「最新价」这一步能共用。

零 LLM 调用。输出 surf/latest_quotes.csv，`/surf` 页面优先读它，缺失时回落扫描快照。

用法：.venv/bin/python surf/scripts/refresh_quotes.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

import pandas as pd
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..")))
from scan_stock import FETCH, SURF, _use_proxy  # noqa: E402
from scan_cn import _no_proxy  # noqa: E402

CARDS = os.path.join(SURF, "cards")
OUT = os.path.join(SURF, "latest_quotes.csv")


def card_targets() -> list[dict]:
    """从所有卡片的 frontmatter 收集标的：ETF 基准 + 个股（含不可交易的港股）。"""
    out, seen = [], set()
    for slug in sorted(os.listdir(CARDS)):
        path = os.path.join(CARDS, slug, "card.md")
        if not os.path.exists(path):
            continue
        raw = open(path, encoding="utf-8").read()
        if not raw.startswith("---"):
            continue
        fm = yaml.safe_load(raw.split("---", 2)[1]) or {}

        t = fm.get("ticker") or {}  # ETF
        if t.get("code") and t["code"] not in seen:
            seen.add(t["code"])
            # ETF 代码带 sh/sz 前缀走新浪 ETF 接口；美股 ETF 代码是纯字母走 yfinance
            market = "CN_ETF" if t["code"][:2] in ("sh", "sz") else "US"
            out.append({"代码": t["code"], "名称": t.get("name", ""), "类型": "ETF",
                        "market": market, "卡片": slug})

        for s in fm.get("stocks") or []:
            if not s.get("code") or s["code"] in seen:
                continue
            seen.add(s["code"])
            out.append({"代码": s["code"], "名称": s.get("name", ""), "类型": "个股",
                        "market": s.get("market", "CN"), "卡片": slug})
    return out


def _exchange(code: str, market: str) -> str:
    if market == "US":
        return "US"
    if market == "HK":
        return "HKEX"
    if code[:2] in ("60", "68") or code[:1] == "9":
        return "SSE"
    if code[:1] in ("0", "3"):
        return "SZSE"
    return "BSE"


def fetch_stock(code: str, market: str) -> tuple[str, float, str] | None:
    """个股走 quotes 管线（= /prices 刷新按钮的 daily 部分），返回 (日期, 收盘, 来源)。"""
    from scripts.fetch_quotes_eod import run_for_ticker
    from app.io import quotes as quotes_io

    ex = _exchange(code, market)
    # 代理方向相反，且必须每只都重设：akshare 走国内源要清代理，yfinance 走 Yahoo
    # 要挂代理。scan_cn._no_proxy() 是**永久 pop**，A 股抓完之后港股/美股就连不上了
    # ——首跑就因此让 02269/02268 全军覆没，而 US 侥幸躲过（IGV 那步又把代理装了回来）。
    _use_proxy() if ex in ("US", "HKEX") else _no_proxy()
    r = run_for_ticker(code, ex)
    if r["status"] == "error":
        print(f"    ! {code} quotes 管线失败：{r['error']}", file=sys.stderr)
        return None
    last = quotes_io.latest_for(code)
    if not last or last.get("close") is None:
        return None
    return last["date"], float(last["close"]), f"quotes/{last.get('source') or ex}"


if __name__ == "__main__":
    targets = card_targets()
    print(f"卡片标的 {len(targets)} 个，开始刷新收盘价…", file=sys.stderr)

    rows, failed = [], []
    for t in targets:
        if t["类型"] == "个股":
            got = fetch_stock(t["代码"], t["market"])
        else:
            h = FETCH[t["market"]](t["代码"])
            got = (h["date"].iloc[-1].date().isoformat(),
                   round(float(h["close"].iloc[-1]), 4), "surf/" + t["market"]) \
                if h is not None and not h.empty else None
        if got is None:
            failed.append(f"{t['名称']}({t['代码']})")
            continue
        d, c, src = got
        rows.append({"代码": t["代码"], "名称": t["名称"], "类型": t["类型"],
                     "market": t["market"], "卡片": t["卡片"],
                     "日期": d, "收盘": round(c, 4), "来源": src,
                     "刷新于": datetime.now().strftime("%Y-%m-%d %H:%M")})
        print(f"  · {t['名称']:<12} {d}  {round(c, 4):<10} {src}", file=sys.stderr)

    if not rows:
        raise SystemExit("全部抓取失败，不写文件")
    # 抓取失败时保留旧值，不让部分结果覆盖完整文件（同 DESIGN §6.4 ⑦ 的教训）
    if failed and os.path.exists(OUT):
        old = pd.read_csv(OUT)
        keep = old[~old["代码"].isin([r["代码"] for r in rows])]
        df = pd.concat([pd.DataFrame(rows), keep], ignore_index=True)
        print(f"  ! {len(failed)} 个失败，保留其旧值：{', '.join(failed)}", file=sys.stderr)
    else:
        df = pd.DataFrame(rows)

    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"\n{len(rows)} 个已刷新 -> {OUT}", file=sys.stderr)
    print(df[["名称", "类型", "日期", "收盘", "来源"]].to_string(index=False))

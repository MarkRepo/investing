"""barchart 取数通道（外汇远期点等 FRED/akshare/yfinance 都缺的序列）。零 LLM：读登记表里
fetch_method=='barchart' 且 availability=='scripted' 且有 barchart 配置块的输入，
两步法抓 barchart 历史 EOD 最新值 → record_observation。

与 fred_fetch / recipe_fetch / akshare_fetch / yfinance_fetch / macromicro_fetch 平行（脚本「数值」通道）。
典型用途：**3M 远期点**（barchart `.H` 后缀 = 3-Month Forward，如 EURUSD.H / USDJPY.H，pips），
这是 CIP 跨币种基差合成的远期腿——FRED 无远期点、掉期点需 Bloomberg/掉期经纪商付费。

取数机制（两步，复刻浏览器匿名访问 barchart core-api）：
  ① GET 价格历史页面 → 站点种下 `XSRF-TOKEN` cookie（URL-encoded）；
  ② GET /proxies/core-api/v1/historical/get，带 `x-xsrf-token`（cookie URL-decode 后）头 + XHR 头，
     返回 {"data":[{tradeTime, <field>}, ...]}，按 tradeTime desc 取最新一条。

注意：
  - **Cloudflare/反爬**：缺浏览器头会被挡；内建退避重试。商业源、转载需授权——仅供自用研究低频取数，已知风险。
  - **远期点单位**：barchart `.H` 返回 pips（EUR/USD 用 1e-4/pip，USD/JPY 用 1e-2/pip），符号约定在 CIP 合成层处理。
"""
from __future__ import annotations

import math
import sys
import time
import urllib.parse

from prism.scripts import macro_registry as reg

_PAGE_URL = "https://www.barchart.com/forex/quotes/{symbol}/price-history/historical"
_API_URL = "https://www.barchart.com/proxies/core-api/v1/historical/get"
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
# 默认客户端头：须足够像真浏览器，否则 barchart Cloudflare 会挡（403/挑战页）。
_BROWSER_HEADERS = {
    "User-Agent": _UA,
    "Accept-Language": "en-US,en;q=0.9",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}


def _to_float(v) -> float | None:
    """单元转 float；NaN/空/非数 → None。值含千分位逗号则去掉。"""
    if v is None:
        return None
    if isinstance(v, str):
        v = v.replace(",", "").strip()
        if not v:
            return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _import_httpx():
    import httpx  # 惰性导入
    return httpx


def fetch_by_barchart(cfg: dict, *, client=None, sleep=time.sleep) -> tuple[float | None, str | None]:
    """按 barchart 配置抓一个数值。cfg: {symbol, field?='lastPrice', retries?=3}。
    两步法见模块 docstring。field 选取哪个价格字段（远期点取收盘 lastPrice）。
    任何对不上 → 诚实 (None, None)，不抛；Cloudflare/瞬时错按 retries 退避重试。
    client 可注入（测试 mock：需支持 .get(url[,params,headers]) → .json()/.text，及 .cookies.get(name)）。"""
    symbol = cfg.get("symbol")
    if not symbol or not str(symbol).strip():
        raise ValueError("barchart 配置缺 symbol")
    symbol = str(symbol).strip()
    field = cfg.get("field", "lastPrice")
    retries = int(cfg.get("retries", 3))
    page_url = _PAGE_URL.format(symbol=symbol)
    params = {
        "symbol": symbol,
        "fields": f"tradeTime.format(Y-m-d),{field}",
        "type": "eod",
        "orderBy": "tradeTime",
        "orderDir": "desc",
        "limit": "1",
        "raw": "1",
    }

    owns = client is None
    if owns:
        client = _import_httpx().Client(timeout=30, follow_redirects=True,
                                        headers=dict(_BROWSER_HEADERS))
    try:
        last_err: Exception | None = None
        for attempt in range(max(1, retries)):
            last = attempt == retries - 1
            try:
                # ① GET 页面种下 XSRF-TOKEN cookie
                client.get(page_url)
                raw_tok = client.cookies.get("XSRF-TOKEN")
                if not raw_tok:
                    raise ValueError("barchart 未取到 XSRF-TOKEN cookie（站点结构/反爬变更）")
                token = urllib.parse.unquote(raw_tok)
                # ② 带 token 打 core-api（须像真浏览器 XHR）
                headers = {"x-xsrf-token": token, "Referer": page_url,
                           "X-Requested-With": "XMLHttpRequest",
                           "Accept": "application/json"}
                js = client.get(_API_URL, params=params, headers=headers).json()
            except Exception as exc:                    # 瞬时网络/SSL/解析/挑战页：退避重试，末轮才抛
                last_err = exc
                if last:
                    raise
                sleep(5)
                continue
            rows = js.get("data") if isinstance(js, dict) else None
            if not rows:                                # 空数据（限流/无该 symbol）→ 退避重试
                if last:
                    return None, None
                sleep(5)
                continue
            row = rows[0]
            val = _to_float(row.get(field))
            tt = row.get("tradeTime")
            as_of = str(tt)[:10] if tt else None
            return val, as_of
        return None, None
    finally:
        if owns:
            client.close()


def run_barchart_fetch(slug: str, variant: str, *, only: set[str] | None = None,
                       client=None) -> dict:
    """抓所有 fetch_method=='barchart' 且 availability=='scripted' 且有 barchart 配置的输入。
    llm 项诚实跳过计数（它们走 headless LLM）。only 给定时只抓名字在其中的项（web 单条手动抓）。
    失败（抛异常/取不到值）记 record_fetch_error 并计数，不连累其余。返回 summary。"""
    data = reg.read_registry(slug, variant)
    fetched = skipped_todo = skipped_llm = failed = 0
    for e in data["inputs"]:
        if e.get("fetch_method") != "barchart":
            continue
        if only is not None and e["name"] not in only:
            continue
        avail = e.get("availability")
        if avail == "llm":
            skipped_llm += 1
            continue
        if avail != "scripted" or not e.get("barchart"):
            skipped_todo += 1
            continue
        try:
            val, as_of = fetch_by_barchart(e["barchart"], client=client)
        except Exception as exc:                       # 配置/网络/结构等：记错、跳过，不连累其余
            reg.record_fetch_error(slug, variant, e["name"], msg=str(exc))
            failed += 1
            continue
        if val is None:
            reg.record_fetch_error(slug, variant, e["name"],
                                   msg=f"barchart 未取到值（限流或源变更）: {e['barchart'].get('symbol')}")
            failed += 1
            continue
        reg.record_observation(slug, variant, e["name"], value=val, as_of=as_of)
        fetched += 1
    return {"fetched": fetched, "skipped_todo": skipped_todo,
            "skipped_llm": skipped_llm, "failed": failed}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    # 自带活体冒烟：无参时直接拉 EURUSD.H / USDJPY.H 3M 远期点
    if not argv:
        for sym in ("EURUSD.H", "USDJPY.H"):
            v, d = fetch_by_barchart({"symbol": sym})
            print(f"{sym}: {v} @ {d}")
        return
    slug = argv[0]
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    print(f"barchart 抓取: {run_barchart_fetch(slug, variant)}")


if __name__ == "__main__":
    main()

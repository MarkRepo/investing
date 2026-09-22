"""surf · 个股增强层技术指标。

零 LLM 调用。只做数据抓取、指标计算、文件读写。方法论见 surf/DESIGN.md §6.5。

与 ETF 层的关键差别：**不算 RS 百分位**。个股候选只有 5-8 只，池内排名无统计
意义，改用「相对基准 ETF 的超额」。基准由 stock_universe.yaml 逐卡片指定。

用法：
    .venv/bin/python surf/scripts/scan_stock.py [slug ...] [--date YYYY-MM-DD]
不给 slug 则跑全部；不给 --date 则写入最近一次扫描目录（不新建，避免产生
只有个股文件、没有 summary 的空扫描期）。
"""
from __future__ import annotations

import os
import sys
import time
from datetime import date, timedelta

import pandas as pd
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_cn import LOOKBACK, _structure, _adjust_splits, _no_proxy  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SURF = os.path.abspath(os.path.join(HERE, ".."))

RISK_PER_TRADE = 0.02    # 单笔最大亏损占总仓位比例，固定（DESIGN §8.1）
STOP_FLOOR = 0.12        # 个股硬止损下限
STOP_CAP = 0.20          # 个股硬止损上限
ATR_MULT = 2.0           # 硬止损 = ATR_MULT × ATR20/现价，再用上下限夹住

# 进程启动时的代理配置。akshare 走国内源必须清掉代理，yfinance 走 Yahoo 反而
# 必须有代理（直连返回 200 空体），同一脚本里两种市场都要跑，故来回切换。
_PROXY_ENV = {k: os.environ.get(k) for k in
              ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
               "http_proxy", "https_proxy", "all_proxy")}


def _use_proxy() -> None:
    for k, v in _PROXY_ENV.items():
        if v:
            os.environ[k] = v


# ── 抓取：三个市场归一成 date/close/high/low/amount ──────────────────────

def _sina_symbol(code: str) -> str:
    """A 股代码加新浪前缀：60/68/9 开头沪市，0/3 开头深市，4/8 开头北交所。"""
    if code[:2] in ("60", "68") or code[0] == "9":
        return "sh" + code
    if code[0] in ("0", "3"):
        return "sz" + code
    return "bj" + code


def _fetch_cn_stock(code: str) -> pd.DataFrame | None:
    """A 股日线，前复权。

    主源新浪 stock_zh_a_daily —— 与 ETF 层的 fund_etf_hist_sina 同源，两者
    收盘日一致，超额才算得准；且东财 push2 在本机持续限流（DESIGN §6.4 ④），
    实测连抓 8 只后即整体 RemoteDisconnected。东财仅作备源。
    qfq 已处理送转与分红，无需 ETF 那套份额折算识别。
    """
    _no_proxy()
    import akshare as ak
    try:
        h = ak.stock_zh_a_daily(symbol=_sina_symbol(code), adjust="qfq")
        if h is not None and not h.empty:
            return _norm(h, {"date": "date", "close": "close", "high": "high",
                             "low": "low", "amount": "amount"})
    except Exception as e:
        print(f"    ~ {code} 新浪源失败，转东财：{e}", file=sys.stderr)

    start = (date.today() - timedelta(days=int(LOOKBACK * 1.7))).strftime("%Y%m%d")
    for attempt in range(3):          # 东财偶发 RemoteDisconnected，退避重试
        try:
            h = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start,
                                   end_date=date.today().strftime("%Y%m%d"), adjust="qfq")
            return _norm(h, {"日期": "date", "收盘": "close", "最高": "high",
                             "最低": "low", "成交额": "amount"})
        except Exception as e:
            if attempt == 2:
                print(f"    ! {code} 两个源都失败：{e}", file=sys.stderr)
                return None
            time.sleep(1.5 * (attempt + 1))
    return None


def _fetch_hk_stock(code: str) -> pd.DataFrame | None:
    """港股走新浪 stock_hk_daily。

    东财的 stock_hk_hist 在本机持续 RemoteDisconnected（同 DESIGN §6.4 ④ 的
    push2 问题），新浪源可用且自带 amount 列。
    """
    _no_proxy()
    import akshare as ak
    try:
        h = ak.stock_hk_daily(symbol=code, adjust="qfq")
    except Exception as e:
        print(f"    ! {code} 新浪源失败：{e}", file=sys.stderr)
        return None
    if h is None or h.empty:
        return None
    return _norm(h, {"date": "date", "close": "close", "high": "high",
                     "low": "low", "amount": "amount"})


def _fetch_us(code: str) -> pd.DataFrame | None:
    _use_proxy()
    import yfinance as yf
    try:
        h = yf.Ticker(code).history(period="2y", auto_adjust=True)
    except Exception as e:
        print(f"    ! {code} 抓取失败：{e}", file=sys.stderr)
        return None
    if h is None or h.empty:
        return None
    h = h.reset_index()
    h.columns = [str(c) for c in h.columns]
    # yfinance 只给 Volume，无成交额；用 收盘 × 成交量 近似，
    # 量能比是自身前后期之比，近似不影响结论。
    h["amount"] = pd.to_numeric(h["Close"], errors="coerce") * pd.to_numeric(h["Volume"], errors="coerce")
    return _norm(h, {"Date": "date", "Close": "close", "High": "high",
                     "Low": "low", "amount": "amount"})


def _fetch_cn_etf(code: str) -> pd.DataFrame | None:
    """基准 ETF 走新浪，与 scan_cn.py 同源，保证超额算得出来的是同一口径。"""
    _no_proxy()
    import akshare as ak
    try:
        h = ak.fund_etf_hist_sina(symbol=code)
    except Exception as e:
        print(f"    ! 基准 {code} 抓取失败：{e}", file=sys.stderr)
        return None
    if h is None or h.empty:
        return None
    h = _norm(h, {"date": "date", "close": "close", "high": "high",
                  "low": "low", "amount": "amount"})
    return _adjust_splits(h) if h is not None else None


def _norm(h: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame | None:
    cols = {src: dst for src, dst in mapping.items() if src in h.columns}
    if "date" not in cols.values() or "close" not in cols.values():
        return None
    out = h[list(cols)].rename(columns=cols).copy()
    out["date"] = pd.to_datetime(out["date"], utc=True, errors="coerce").dt.tz_localize(None)
    for c in ("close", "high", "low", "amount"):
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)
    return out if len(out) >= 70 else None


FETCH = {"CN": _fetch_cn_stock, "HK": _fetch_hk_stock, "US": _fetch_us, "CN_ETF": _fetch_cn_etf}


# ── 指标 ─────────────────────────────────────────────────────────────────

def _ret(close: pd.Series, n: int) -> float | None:
    if len(close) <= n:
        return None
    return round((close.iloc[-1] / close.iloc[-1 - n] - 1) * 100, 2)


def _atr_pct(h: pd.DataFrame, n: int = 20) -> float | None:
    """ATR20 占现价比例。缺高低价时退化为收盘价绝对日变动的均值。"""
    close = h["close"]
    if "high" in h.columns and "low" in h.columns and h["high"].notna().sum() > n:
        prev = close.shift(1)
        tr = pd.concat([h["high"] - h["low"],
                        (h["high"] - prev).abs(),
                        (h["low"] - prev).abs()], axis=1).max(axis=1)
    else:
        tr = close.diff().abs()
    atr = tr.tail(n).mean()
    if not atr or pd.isna(atr):
        return None
    return round(atr / close.iloc[-1] * 100, 2)


def metrics(h: pd.DataFrame, bench: pd.DataFrame,
            local: pd.DataFrame | None = None) -> dict:
    close = h["close"]
    last = float(close.iloc[-1])
    win = close.tail(LOOKBACK)
    lo, hi = float(win.min()), float(win.max())
    ma20, ma60 = float(close.tail(20).mean()), float(close.tail(60).mean())

    amt = h["amount"] if "amount" in h.columns else pd.Series(dtype=float)
    amt5 = float(amt.tail(5).mean()) if len(amt.dropna()) >= 65 else None
    amt60 = float(amt.tail(65).head(60).mean()) if len(amt.dropna()) >= 65 else None
    amt20 = float(amt.tail(20).mean()) if len(amt.dropna()) >= 20 else None

    atr = _atr_pct(h)
    stop = min(STOP_CAP, max(STOP_FLOOR, (ATR_MULT * atr / 100) if atr else STOP_FLOOR))

    out = {
        "日期": h["date"].iloc[-1].date().isoformat(),
        "基准日期": bench["date"].iloc[-1].date().isoformat(),
        "现价": round(last, 3),
        "ret20": _ret(close, 20), "ret60": _ret(close, 60),
        "基准ret20": _ret(bench["close"], 20), "基准ret60": _ret(bench["close"], 60),
        "位置分位": round((last - lo) / (hi - lo) * 100, 1) if hi > lo else None,
        "距250日高": round((last / hi - 1) * 100, 2) if hi else None,
        "ma20": round(ma20, 3), "ma60": round(ma60, 3),
        "趋势结构": _structure(last, ma20, ma60),
        "量能比": round(amt5 / amt60, 2) if amt5 and amt60 else None,
        "ATR20_%": atr,
        "日均成交额_万": round(amt20 / 1e4, 1) if amt20 else None,
        "硬止损_%": round(stop * 100, 1),
        "止损价": round(last * (1 - stop), 3),
        "建议仓位_%": round(RISK_PER_TRADE / stop * 100, 1),
    }
    for n in (20, 60):
        s, b = out[f"ret{n}"], out[f"基准ret{n}"]
        out[f"超额{n}"] = round(s - b, 2) if s is not None and b is not None else None
    # 跨市场基准（例：A 股个股 vs 港股 ETF）的超额里混进了市场 beta 差异，
    # 实测港股通医疗 ETF ret60 +26.8 而 A 股医药 ETF 仅 +8~12，
    # 直接比会系统性低估 A 股个股。同市场参照回答的是另一个问题：
    # 「在它自己的市场里，资金认不认它是这轮的兑现方」。两个都要看。
    if local is not None:
        for n in (20, 60):
            lb = _ret(local["close"], n)
            s = out[f"ret{n}"]
            out[f"同市场超额{n}"] = round(s - lb, 2) if s is not None and lb is not None else None
    return out


def scan_slug(slug: str, cfg: dict) -> pd.DataFrame:
    bm = cfg["benchmark"]
    print(f"[{slug}] 基准 {bm['name']} ({bm['code']})", file=sys.stderr)
    bench = FETCH[bm["market"]](bm["code"])
    if bench is None:
        raise SystemExit(f"基准 {bm['code']} 抓取失败，无法计算超额")

    local = None
    lm = cfg.get("benchmark_local")      # 仅跨市场时需要，见 metrics() 注释
    if lm:
        local = FETCH[lm["market"]](lm["code"])
        print(f"[{slug}] 同市场参照 {lm['name']} ({lm['code']})"
              + ("" if local is not None else "  ← 抓取失败，该列留空"), file=sys.stderr)

    rows = []
    for s in cfg["stocks"]:
        h = FETCH[s["market"]](s["code"])
        if h is None:
            print(f"    ! {s['name']} 无数据，跳过", file=sys.stderr)
            continue
        row = {"代码": s["code"], "名称": s["name"], "市场": s["market"],
               "可交易": s.get("tradable", True), "链上卡位": s.get("role", "")}
        row.update(metrics(h, bench, local))
        rows.append(row)
        print(f"    · {s['name']:<8} ret20 {row['ret20']:>7} 超额20 {row['超额20']:>7} "
              f"{row['趋势结构']}", file=sys.stderr)
    df = pd.DataFrame(rows)
    df.attrs["n_failed"] = len(cfg["stocks"]) - len(df)
    return df


def latest_scan_dir() -> str:
    base = os.path.join(SURF, "scans")
    days = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
    if not days:
        raise SystemExit("scans/ 下没有任何扫描期，先跑 scan_cn.py / scan_us.py")
    return days[-1]


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    day = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--date=")), None) \
        or latest_scan_dir()

    cfgs = yaml.safe_load(open(os.path.join(SURF, "stock_universe.yaml"), encoding="utf-8"))
    slugs = args or list(cfgs)
    outdir = os.path.join(SURF, "scans", day)
    os.makedirs(outdir, exist_ok=True)

    for slug in slugs:
        if slug not in cfgs:
            raise SystemExit(f"stock_universe.yaml 里没有 {slug}")
        df = scan_slug(slug, cfgs[slug])
        path = os.path.join(outdir, f"stock_{slug}.csv")
        # 有抓取失败时不覆盖已有快照——部分结果静默盖掉完整结果会丢数据，
        # 实测东财限流那次就用 2 行盖掉了 8 行。
        if df.attrs.get("n_failed") and os.path.exists(path) and "--force" not in sys.argv:
            path = path.replace(".csv", ".partial.csv")
            print(f"[{slug}] {df.attrs['n_failed']} 只抓取失败，不覆盖已有快照，"
                  f"改写 {os.path.basename(path)}（--force 可强制覆盖）", file=sys.stderr)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"[{slug}] {len(df)} 只 -> {path}\n", file=sys.stderr)
        cols = ["名称", "可交易", "ret20", "超额20", "超额60", "同市场超额20", "同市场超额60",
                "位置分位", "距250日高", "趋势结构", "量能比", "硬止损_%"]
        print(f"===={slug}====")
        print(df[[c for c in cols if c in df.columns]].to_string(index=False))

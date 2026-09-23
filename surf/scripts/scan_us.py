"""surf · 美股 ETF 技术指标扫描（两段式）。

零 LLM 调用。指标口径与 scan_cn.py 完全一致，两个市场可横向比较。
折叠与 RS 的逻辑直接复用 scan_cn.finalize_stage，避免两个市场分叉。

候选池来自 us_universe.build_universe（Yahoo ETF screener 规则筛），
不再是手写字典——手写清单的漏项是不可见的系统性盲区（DESIGN §6.1）。

注意与 scan_cn.py 的一个反向差异：本脚本**不清理代理环境变量**。
akshare 走国内源必须绕过代理；yfinance 走 Yahoo 反而需要代理，
直连会返回 200 空体（见 memory: launchd-service-proxy-env）。
"""
from __future__ import annotations

import os
import sys
from datetime import date

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import themes as themes_io  # noqa: E402
from scan_cn import LOOKBACK, _structure, finalize_stage  # noqa: E402
from us_universe import build_universe  # noqa: E402


def _drop_partial_bar(data: pd.DataFrame) -> pd.DataFrame:
    """美股盘中运行时，yfinance 会返回当日**未收盘**的部分 bar，必须整片丢掉。

    周频系统只认收盘价（DESIGN §6.4）。盘中 bar 的危害不只是价格不准：
    当日成交量只累计到此刻，`量能比` 会被系统性压低（实测 IGV 0.72 → 0.52），
    直接污染「未放量」这个判据。

    整片丢而不是逐只丢——RS 是池内百分位，池内混着不同交易日的行情就失去可比性。
    """
    from zoneinfo import ZoneInfo
    if data.empty:
        return data
    now_et = pd.Timestamp.now(tz=ZoneInfo("America/New_York"))
    last = pd.Timestamp(data.index[-1]).date()
    # 16:00 ET 收盘，留 5 分钟给 Yahoo 落库
    if last == now_et.date() and now_et.time() < pd.Timestamp("16:05").time():
        print(f"  ⚠️ 丢弃盘中未收盘 bar {last}（当前美东 {now_et:%H:%M}）", file=sys.stderr)
        return data.iloc[:-1]
    return data


def fetch(tickers: list[str]) -> pd.DataFrame:
    import yfinance as yf
    data = yf.download(tickers, period="2y", interval="1d",
                       progress=False, auto_adjust=True, threads=True)
    return _drop_partial_bar(data)


def fetch_stage(universe: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """抓历史、算指标。不算 RS、不折叠——理由见 scan_cn.fetch_stage。"""
    u = universe.copy().set_index("代码")
    todo = list(universe[universe["剔除原因"] == ""]["代码"])
    names = dict(zip(universe["代码"], universe["名称"]))

    data = fetch(todo)
    close_all, vol_all = data["Close"], data["Volume"]

    rows = []
    for tkr in todo:
        if tkr not in close_all.columns:
            u.loc[tkr, ["剔除原因", "剔除说明"]] = ["fetch_failed", "Yahoo 无历史数据"]
            continue
        s = close_all[tkr].dropna()
        if len(s) < 70:
            u.loc[tkr, ["剔除原因", "剔除说明"]] = ["fetch_failed", f"样本仅 {len(s)} 天"]
            continue
        v = vol_all[tkr].reindex(s.index).fillna(0)

        close = s.to_numpy()
        last = float(close[-1])
        win = close[-LOOKBACK:]
        hi, lo = float(win.max()), float(win.min())
        ma20, ma60 = float(close[-20:].mean()), float(close[-60:].mean())
        # 成交额近似：yfinance 只给股数，用 收盘价×成交量 作金额代理
        amt = (s * v).to_numpy()
        recent, base = amt[-5:].mean(), amt[-65:-5].mean()

        rows.append({
            "代码": tkr, "名称": names.get(tkr, tkr),
            "日期": s.index[-1].date().isoformat(),
            "收盘": round(last, 2),
            "ret5": round((last / close[-6] - 1) * 100, 2),
            "ret20": round((last / close[-21] - 1) * 100, 2),
            "ret60": round((last / close[-61] - 1) * 100, 2),
            "位置分位": round((last - lo) / (hi - lo) * 100, 1) if hi > lo else None,
            "距250日高": round((last / hi - 1) * 100, 2),
            "ma20": round(ma20, 2), "ma60": round(ma60, 2),
            "趋势结构": _structure(last, ma20, ma60),
            "量能比": round(float(recent / base), 2) if base > 0 else None,
            "amt20": float(amt[-20:].mean()),
            "样本天数": len(close),
        })
    return pd.DataFrame(rows), u.reset_index()


def _outdir(day: str) -> str:
    d = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "scans", day))
    os.makedirs(d, exist_ok=True)
    return d


def _run_fetch(day: str) -> None:
    outdir = _outdir(day)
    u = build_universe()
    print(f"全量 {len(u)} 只，规则层通过 {(u['剔除原因'] == '').sum()} 只，抓历史…",
          file=sys.stderr)
    df, u = fetch_stage(u)
    df.to_csv(os.path.join(outdir, "us_etf_raw.csv"), index=False, encoding="utf-8-sig")
    u.to_csv(os.path.join(outdir, "universe_us.csv"), index=False, encoding="utf-8-sig")
    todo = themes_io.pending(list(df["代码"]), dict(zip(df["代码"], df["名称"])))
    print(f"待 LLM 判主题 {len(todo)} 只（缓存已覆盖 {len(df) - len(todo)} 只）", file=sys.stderr)
    for t in todo:
        print(f"{t['代码']},{t['名称']}")


def _run_finalize(day: str) -> None:
    outdir = _outdir(day)
    df = pd.read_csv(os.path.join(outdir, "us_etf_raw.csv"))
    u = pd.read_csv(os.path.join(outdir, "universe_us.csv")).fillna(
        {"剔除原因": "", "剔除说明": ""})
    th = themes_io.read_themes(outdir)
    missing = [c for c in df["代码"] if c not in th]
    if missing:
        raise SystemExit(f"themes.json 缺 {len(missing)} 只的判定：{missing[:10]}")

    df, u = finalize_stage(df, u, th)
    df["基准"] = df["主题"].str.startswith("基准")
    path = os.path.join(outdir, "us_etf.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    u.to_csv(os.path.join(outdir, "universe_us.csv"), index=False, encoding="utf-8-sig")
    print(f"扫描完成 {len(df)} 只 -> {path}", file=sys.stderr)
    print("===US SCAN BY RS5===")
    cols = ["代码", "名称", "主题", "ret5", "RS5", "ret20", "ret60", "RS60",
            "位置分位", "距250日高", "趋势结构", "量能比"]
    print(df[cols].head(35).to_string())


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "fetch"
    today = sys.argv[2] if len(sys.argv) > 2 else date.today().isoformat()
    if stage == "fetch":
        _run_fetch(today)
    elif stage == "finalize":
        _run_finalize(today)
    else:
        raise SystemExit("用法: scan_us.py [fetch|finalize] [YYYY-MM-DD]")

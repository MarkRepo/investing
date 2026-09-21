"""surf · 美股 ETF 技术指标扫描。

零 LLM 调用。指标口径与 scan_cn.py 完全一致，两个市场可横向比较。

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
from scan_cn import LOOKBACK, _structure  # noqa: E402

# 行业 SPDR（11 只全覆盖）+ 主题 ETF。主题池按「能代表一条产业趋势」挑选。
TICKERS: dict[str, str] = {
    # --- 行业 ---
    "XLK": "科技", "XLV": "医疗", "XLF": "金融", "XLY": "可选消费", "XLP": "必需消费",
    "XLE": "能源", "XLI": "工业", "XLB": "原材料", "XLRE": "地产", "XLU": "公用事业",
    "XLC": "通信服务",
    # --- 半导体与硬件 ---
    "SMH": "半导体", "SOXX": "半导体(备)", "PPH": "制药", "SKYY": "云计算",
    # --- 软件与互联网 ---
    "IGV": "软件", "FDN": "互联网", "WCLD": "云软件", "HACK": "网络安全",
    "FINX": "金融科技", "KWEB": "中概互联",
    # --- 生物医药 ---
    "XBI": "生物科技(等权)", "IBB": "生物科技(市值)", "IHI": "医疗器械",
    # --- 电力与能源转型（对应产业扫描 T1：AI 电力缺口）---
    "GRID": "智能电网", "PAVE": "美国基建", "URA": "铀矿", "NLR": "核能",
    "TAN": "太阳能", "ICLN": "清洁能源", "LIT": "锂电",
    # --- 传统能源 ---
    "XOP": "油气勘探", "OIH": "油服", "AMLP": "油气管道",
    # --- 国防与航天（产业扫描 T3 级：事件驱动）---
    "ITA": "国防航天", "ARKX": "太空探索",
    # --- 机器人与自动化（对应 T6）---
    "BOTZ": "机器人AI", "ROBO": "机器人自动化",
    # --- 材料与周期 ---
    "XME": "金属矿业", "COPX": "铜矿", "GDX": "金矿", "MOO": "农business",
    # --- 运输与地产链 ---
    "JETS": "航空", "IYT": "运输", "XHB": "住宅建造", "XRT": "零售",
    "KRE": "区域银行",
}

# 基准：只用于给出参照系，仍参与 RS 排名（想知道板块是否跑赢大盘）。
BENCHMARKS = {"SPY": "标普500", "QQQ": "纳斯达克100"}


def fetch(tickers: list[str]) -> pd.DataFrame:
    import yfinance as yf
    data = yf.download(tickers, period="2y", interval="1d",
                       progress=False, auto_adjust=True, threads=True)
    return data


def scan() -> pd.DataFrame:
    universe = {**TICKERS, **BENCHMARKS}
    data = fetch(list(universe))
    close_all, vol_all = data["Close"], data["Volume"]

    rows = []
    for tkr, label in universe.items():
        if tkr not in close_all.columns:
            print(f"[warn] {tkr} 无数据", file=sys.stderr)
            continue
        s = close_all[tkr].dropna()
        v = vol_all[tkr].reindex(s.index).fillna(0)
        if len(s) < 70:
            print(f"[warn] {tkr} 样本不足 {len(s)}", file=sys.stderr)
            continue

        close = s.to_numpy()
        last = float(close[-1])
        win = close[-LOOKBACK:]
        hi, lo = float(win.max()), float(win.min())
        ma20, ma60 = float(close[-20:].mean()), float(close[-60:].mean())

        # 成交额近似：yfinance 只给股数，用 收盘价×成交量 作金额代理
        amt = (s * v).to_numpy()
        recent, base = amt[-5:].mean(), amt[-65:-5].mean()

        rows.append({
            "代码": tkr, "名称": label,
            "基准": tkr in BENCHMARKS,
            "日期": s.index[-1].date().isoformat(),
            "收盘": round(last, 2),
            "ret5": round((last / close[-6] - 1) * 100, 2),
            "ret20": round((last / close[-21] - 1) * 100, 2),
            "ret60": round((last / close[-61] - 1) * 100, 2),
            "位置分位": round((last - lo) / (hi - lo) * 100, 1) if hi > lo else None,
            "距250日高": round((last / hi - 1) * 100, 2),
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
            "趋势结构": _structure(last, ma20, ma60),
            "量能比": round(float(recent / base), 2) if base > 0 else None,
            "样本天数": len(close),
        })

    df = pd.DataFrame(rows)
    for n in (5, 20, 60):
        df[f"RS{n}"] = (df[f"ret{n}"].rank(pct=True) * 100).round(1)
    return df.sort_values("RS5", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    day = date.today().isoformat()
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scans", day)
    os.makedirs(outdir, exist_ok=True)

    df = scan()
    path = os.path.abspath(os.path.join(outdir, "us_etf.csv"))
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"扫描完成 {len(df)} 只 -> {path}", file=sys.stderr)

    print("===US SCAN BY RS20===")
    cols = ["代码", "名称", "ret5", "RS5", "ret20", "ret60", "RS60", "位置分位", "距250日高", "趋势结构", "量能比"]
    print(df[cols].to_string())

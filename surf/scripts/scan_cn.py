"""surf · A股 ETF 技术指标扫描。

零 LLM 调用。只做数据抓取、指标计算、文件读写。
指标定义见 docs/superpowers/specs/2026-09-21-surf-design.md §6.2。
指标只描述「当下状态」，不构成自动买卖信号。
"""
from __future__ import annotations

import os
import sys
from datetime import date

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etf_universe import build_universe, _no_proxy  # noqa: E402

LOOKBACK = 250     # 位置分位与回撤的观察窗口（约一年交易日）
MIN_AMT20 = 3000e4       # 近 20 日日均成交额下限（DESIGN §6.1 精筛）
SPLIT_THRESHOLD = 0.75   # 单日跌幅超 25% 判定为份额折算，见 _adjust_splits


def _fetch_one(code: str) -> pd.DataFrame | None:
    _no_proxy()
    import akshare as ak
    try:
        h = ak.fund_etf_hist_sina(symbol=code)
    except Exception:
        return None
    if h is None or len(h) < 70:
        return None
    h = h.copy()
    h["date"] = pd.to_datetime(h["date"])
    for c in ("close", "amount"):
        h[c] = pd.to_numeric(h[c], errors="coerce")
    h = h.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)
    return _adjust_splits(h)


def _adjust_splits(h: pd.DataFrame) -> pd.DataFrame:
    """对份额折算做前复权。

    新浪 ETF 历史是未复权价。ETF 份额折算（净值归 1）会让价格断崖式下跌，
    实测科创芯片ETF因此算出 60 日 -73.6% 的假跌幅，会污染 RS 与位置分位。
    A 股 ETF 单日涨跌幅受限（境内 10%/20%），真实行情不可能跌破 25%，
    故以此为阈值识别折算点，并按比例回调该点之前的全部价格。
    """
    close = h["close"].to_numpy(dtype=float).copy()
    n_adj = 0
    for i in range(len(close) - 1, 0, -1):
        ratio = close[i] / close[i - 1]
        if ratio < SPLIT_THRESHOLD:
            close[:i] *= ratio
            n_adj += 1
    h = h.copy()
    h["close"] = close
    h.attrs["n_split_adj"] = n_adj
    return h


def compute_metrics(h: pd.DataFrame) -> dict:
    """对单只标的的历史序列计算全部指标。"""
    close = h["close"].to_numpy()
    amount = h["amount"].to_numpy()
    last = close[-1]

    win = close[-LOOKBACK:] if len(close) >= LOOKBACK else close
    hi, lo = float(win.max()), float(win.min())

    ma20 = float(close[-20:].mean())
    ma60 = float(close[-60:].mean())

    # 量能：近 5 日日均成交额 / 之前 60 日日均成交额
    recent_amt = amount[-5:].mean()
    base_amt = amount[-65:-5].mean() if len(amount) >= 65 else amount[:-5].mean()

    return {
        "日期": h["date"].iloc[-1].date().isoformat(),
        "收盘": round(float(last), 4),
        "ret5": round((last / close[-6] - 1) * 100, 2) if len(close) > 6 else None,
        "ret20": round((last / close[-21] - 1) * 100, 2) if len(close) > 21 else None,
        "ret60": round((last / close[-61] - 1) * 100, 2) if len(close) > 61 else None,
        "位置分位": round((last - lo) / (hi - lo) * 100, 1) if hi > lo else None,
        "距250日高": round((last / hi - 1) * 100, 2),
        "ma20": round(ma20, 4),
        "ma60": round(ma60, 4),
        "趋势结构": _structure(last, ma20, ma60),
        "量能比": round(float(recent_amt / base_amt), 2) if base_amt > 0 else None,
        "amt20": float(amount[-20:].mean()),
        "样本天数": len(close),
        "折算修正": h.attrs.get("n_split_adj", 0),
    }


def _structure(last: float, ma20: float, ma60: float) -> str:
    """价格与 20/60 日均线的相对位置，四种状态。"""
    if last > ma20 > ma60:
        return "多头排列"
    if last < ma20 < ma60:
        return "空头排列"
    if last > ma60:
        return "均线纠缠偏多"
    return "均线纠缠偏空"


def scan(universe: pd.DataFrame) -> pd.DataFrame:
    # 串行抓取：fund_etf_hist_sina 内部用 mini_racer 解密新浪返回，
    # V8 isolate 非线程安全，放进线程池会在 address_pool_manager 处直接 abort。
    # 单只约 0.3s，全量 130+ 只约 40s，不值得为此换数据源。
    rows = []
    total = len(universe)
    for i, (_, meta) in enumerate(universe.iterrows(), 1):
        h = _fetch_one(meta["代码"])
        if i % 20 == 0:
            print(f"  {i}/{total}", file=sys.stderr)
        if h is None:
            continue
        rows.append({"代码": meta["代码"], "名称": meta["名称"], **compute_metrics(h)})

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # 精筛：近 20 日日均成交额。必须在计算 RS 之前完成——
    # RS 是候选池内的百分位排名，若含有事后被剔除的标的，排名就是错的。
    n_before = len(df)
    df = df[df["amt20"] > MIN_AMT20].reset_index(drop=True)
    print(f"  20 日均额精筛：{n_before} -> {len(df)}", file=sys.stderr)
    # 相对强度 = 涨幅在全候选池中的百分位排名（0-100，越大越强）
    # ret5 不可省：20 日窗口会掩盖刚启动的反弹，实测 2026-09 A 股半导体
    # 5 日 +11.3% 而 20 日仅 0%，只看 ret20 会完全错过正在发生的二波。
    for n in (5, 20, 60):
        df[f"RS{n}"] = (df[f"ret{n}"].rank(pct=True) * 100).round(1)
    return df.sort_values("RS5", ascending=False).reset_index(drop=True)


def fetch_boards() -> tuple[pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None]:
    """抓同花顺板块层数据。仅作资金面与广度佐证，不做趋势判断。

    返回 (行业5日资金流, 行业当日概况含涨跌家数, 概念5日资金流)。
    任一失败返回 None，不中断扫描——板块数据是佐证，缺了价格指标依然成立。
    """
    _no_proxy()
    import akshare as ak

    def _try(label, fn):
        try:
            return fn()
        except Exception as e:
            print(f"[warn] {label} 抓取失败: {type(e).__name__}: {e}", file=sys.stderr)
            return None

    return (
        _try("行业资金流", lambda: ak.stock_fund_flow_industry(symbol="5日排行")),
        _try("行业概况", ak.stock_board_industry_summary_ths),
        _try("概念资金流", lambda: ak.stock_fund_flow_concept(symbol="5日排行")),
    )


def load_board_map() -> dict[str, str]:
    """读 ETF → 同花顺板块映射（DESIGN §6.3）。允许缺失与不全。"""
    import yaml
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "etf_board_map.yaml")
    if not os.path.exists(path):
        print("[warn] etf_board_map.yaml 不存在，资金流与广度字段将全部留空", file=sys.stderr)
        return {}
    with open(path, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("map", {}) or {}


def attach_board_metrics(df: pd.DataFrame, flow: pd.DataFrame | None,
                         summary: pd.DataFrame | None) -> pd.DataFrame:
    """把板块层的资金流与广度按映射表贴到 ETF 行上。

    无映射的 ETF（港股 ETF、跨板块主题）字段留空，这是设计允许的（DESIGN §6.3）。
    """
    bmap = load_board_map()
    df = df.copy()
    df["板块"] = df["代码"].map(bmap)

    if flow is not None and "行业" in flow.columns:
        net = dict(zip(flow["行业"], pd.to_numeric(flow["净额"], errors="coerce")))
        df["板块5日资金净额_亿"] = df["板块"].map(net)

    if summary is not None and "板块" in summary.columns:
        up = pd.to_numeric(summary["上涨家数"], errors="coerce")
        dn = pd.to_numeric(summary["下跌家数"], errors="coerce")
        total = (up + dn).replace(0, pd.NA)
        breadth = dict(zip(summary["板块"], (up / total * 100).round(1)))
        chg = dict(zip(summary["板块"], pd.to_numeric(summary["涨跌幅"], errors="coerce")))
        df["板块当日广度_%"] = df["板块"].map(breadth)
        df["板块当日涨跌_%"] = df["板块"].map(chg)

    n = int(df["板块"].notna().sum())
    print(f"  板块指标已贴合 {n}/{len(df)} 只（其余为港股 ETF 与跨板块主题，按设计留空）",
          file=sys.stderr)
    return df


if __name__ == "__main__":
    day = date.today().isoformat()
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scans", day)
    os.makedirs(outdir, exist_ok=True)

    u = build_universe()
    print(f"候选池 {len(u)} 只，开始抓取历史…", file=sys.stderr)
    df = scan(u)
    path = os.path.abspath(os.path.join(outdir, "cn_etf.csv"))
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"扫描完成 {len(df)} 只 -> {path}", file=sys.stderr)

    flow, summary, concept = fetch_boards()
    df = attach_board_metrics(df, flow, summary)
    df.to_csv(path, index=False, encoding="utf-8-sig")   # 贴合板块指标后重写

    for name, b in (("cn_boards.csv", flow), ("cn_board_summary.csv", summary),
                    ("cn_concepts.csv", concept)):
        if b is None:
            continue
        bp = os.path.abspath(os.path.join(outdir, name))
        b.to_csv(bp, index=False, encoding="utf-8-sig")
        print(f"{name}: {len(b)} 行 -> {bp}", file=sys.stderr)

    print("===TOP30 BY RS5===")
    cols = ["名称", "ret5", "RS5", "ret60", "RS60", "位置分位", "距250日高",
            "趋势结构", "量能比", "板块5日资金净额_亿", "板块当日广度_%"]
    print(df[cols].head(30).to_string())

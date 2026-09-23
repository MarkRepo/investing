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
import themes as themes_io  # noqa: E402
from etf_universe import build_universe, _no_proxy, _asset_class_reason  # noqa: E402

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


def fetch_stage(universe: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """第一段：对规则层幸存者抓历史、算指标、按 amt20 做流动性精筛。

    返回 (指标表, 全量带剔除原因的 universe)。**不算 RS、不做主题折叠**——
    RS 是池内百分位，必须在主题折叠之后算，否则同主题的十几只会把排名撑坏
    （2026-09-21 扫描实测：RS60 前 20 有 11 席是同一个港股医药主题）。
    """
    # 串行抓取：fund_etf_hist_sina 内部用 mini_racer 解密新浪返回，
    # V8 isolate 非线程安全，放进线程池会在 address_pool_manager 处直接 abort。
    todo = universe[universe["剔除原因"] == ""]
    rows, failed = [], {}
    total = len(todo)
    for i, (_, meta) in enumerate(todo.iterrows(), 1):
        h = _fetch_one(meta["代码"])
        if i % 40 == 0:
            print(f"  {i}/{total}", file=sys.stderr)
        if h is None:
            failed[meta["代码"]] = "抓取失败或样本不足 70 天"
            continue
        rows.append({"代码": meta["代码"], "名称": meta["名称"], **compute_metrics(h)})

    df = pd.DataFrame(rows)
    u = universe.copy().set_index("代码")
    for code, why in failed.items():
        u.loc[code, ["剔除原因", "剔除说明"]] = ["fetch_failed", why]

    if not df.empty:
        thin = df[df["amt20"] <= MIN_AMT20]
        for _, r in thin.iterrows():
            u.loc[r["代码"], ["剔除原因", "剔除说明"]] = [
                "illiquid", f"20 日均额 {r['amt20'] / 1e4:.0f} 万 ≤ {MIN_AMT20 / 1e4:.0f} 万"]
        df = df[df["amt20"] > MIN_AMT20].reset_index(drop=True)
        print(f"  20 日均额精筛：{len(rows)} -> {len(df)}", file=sys.stderr)

    return df, u.reset_index()


def card_tickers() -> set[str]:
    """已建卡标的的代码。它们**豁免同主题折叠**——卡片的指标时间序列要逐期连续，
    折叠掉就断档了。实测 sh520510（医药卡片标的）会被成交额更大的 sh513120 顶掉。
    """
    import glob
    import re
    out = set()
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cards")
    for f in glob.glob(os.path.join(root, "*", "card.md")):
        head = open(f, encoding="utf-8").read().split("---")[1] if "---" in open(
            f, encoding="utf-8").read() else ""
        m = re.search(r"^\s*code:\s*['\"]?([\w.]+)", head, re.M)
        if m:
            out.add(m.group(1))
    return out


def finalize_stage(metrics: pd.DataFrame, universe: pd.DataFrame,
                   themes: dict[str, dict],
                   amt_col: str = "amt20") -> tuple[pd.DataFrame, pd.DataFrame]:
    """第二段：套用 LLM 判定（载体资格 + 主题归一），折叠同主题，算 RS。

    同主题只留成交额（amt20）最大的一只作代表——这是 DESIGN §6.1 的原意，
    旧版因主题键写坏而失效。被折叠掉的不消失，在 universe 里记 ``dedup`` 并
    写明代表是谁，`/surf/universe` 页面按原因展示。
    """
    u = universe.copy().set_index("代码")
    df = metrics.copy()
    df["主题"] = [themes.get(c, {}).get("theme") or "未判定" for c in df["代码"]]

    # ① 载体资格：成分按财务特征/所有制聚合而非按产业聚合的，不是趋势载体
    bad = [c for c in df["代码"] if themes.get(c, {}).get("is_trend_carrier") is False]
    for c in bad:
        u.loc[c, ["剔除原因", "剔除说明"]] = ["not_carrier", themes[c].get("reason", "")]
    df = df[~df["代码"].isin(bad)].reset_index(drop=True)

    # ② 同主题折叠：留成交额（美股用成交额代理）最大的一只；已建卡标的豁免
    keep = card_tickers()
    df = df.sort_values(amt_col, ascending=False)
    rep = df.drop_duplicates("主题", keep="first")
    rep = pd.concat([rep, df[df["代码"].isin(keep) & ~df["代码"].isin(rep["代码"])]])
    dropped = df[~df["代码"].isin(rep["代码"])]
    rep = rep.sort_values(amt_col, ascending=False)
    rep_of = dict(zip(rep["主题"], zip(rep["代码"], rep["名称"])))
    for _, r in dropped.iterrows():
        code, name = rep_of[r["主题"]]
        u.loc[r["代码"], ["剔除原因", "剔除说明"]] = [
            "dedup", f"同主题「{r['主题']}」，代表为 {code} {name}"]
    df = rep.reset_index(drop=True)
    print(f"  载体资格剔除 {len(bad)} 只；同主题折叠 {len(dropped)} 只 -> 入池 {len(df)}",
          file=sys.stderr)

    # ③ RS 必须在折叠之后算，理由见 fetch_stage docstring
    for n in (5, 20, 60):
        df[f"RS{n}"] = (df[f"ret{n}"].rank(pct=True) * 100).round(1)
    df = df.sort_values("RS5", ascending=False).reset_index(drop=True)

    u["主题"] = [themes.get(c, {}).get("theme", "") for c in u.index]
    return df, u.reset_index()


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


def _outdir(day: str) -> str:
    d = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "scans", day))
    os.makedirs(d, exist_ok=True)
    return d


def _run_fetch(day: str) -> None:
    outdir = _outdir(day)
    u = build_universe()
    n_pass = int((u["剔除原因"] == "").sum())
    print(f"全量 {len(u)} 只，规则层通过 {n_pass} 只，开始抓取历史…", file=sys.stderr)

    df, u = fetch_stage(u)
    raw = os.path.join(outdir, "cn_etf_raw.csv")
    df.to_csv(raw, index=False, encoding="utf-8-sig")
    u.to_csv(os.path.join(outdir, "universe_cn.csv"), index=False, encoding="utf-8-sig")

    todo = themes_io.pending(list(df["代码"]), dict(zip(df["代码"], df["名称"])))
    print(f"\n待 LLM 判主题 {len(todo)} 只（缓存已覆盖 {len(df) - len(todo)} 只）"
          f" -> {raw}", file=sys.stderr)
    for t in todo:
        print(f"{t['代码']},{t['名称']}")


def _run_finalize(day: str) -> None:
    outdir = _outdir(day)
    df = pd.read_csv(os.path.join(outdir, "cn_etf_raw.csv"))
    u = pd.read_csv(os.path.join(outdir, "universe_cn.csv")).fillna(
        {"剔除原因": "", "剔除说明": ""})
    themes = themes_io.read_themes(outdir)

    # 规则层排除词表可能在 fetch 之后被补过（实测补「A50」「恒生科技」后多剔 29 只）。
    # 这里重跑一次规则，避免为了一次词表修补重抓全量历史。
    patched = []
    for c, n in zip(df["代码"], df["名称"]):
        hit = _asset_class_reason(str(n))
        if hit:
            u.loc[u["代码"] == c, ["剔除原因", "剔除说明"]] = [
                "asset_class", f"{hit[0]}（名称含「{hit[1]}」）"]
            patched.append(c)
    if patched:
        df = df[~df["代码"].isin(patched)].reset_index(drop=True)
        print(f"  规则层补丁再剔 {len(patched)} 只", file=sys.stderr)

    missing = [c for c in df["代码"] if c not in themes]
    if missing:
        raise SystemExit(f"themes.json 缺 {len(missing)} 只的判定，先补齐：{missing[:10]}")

    df, u = finalize_stage(df, u, themes)
    path = os.path.join(outdir, "cn_etf.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")

    flow, summary, concept = fetch_boards()
    df = attach_board_metrics(df, flow, summary)
    df.to_csv(path, index=False, encoding="utf-8-sig")   # 贴合板块指标后重写
    u.to_csv(os.path.join(outdir, "universe_cn.csv"), index=False, encoding="utf-8-sig")

    for name, b in (("cn_boards.csv", flow), ("cn_board_summary.csv", summary),
                    ("cn_concepts.csv", concept)):
        if b is None:
            continue
        b.to_csv(os.path.join(outdir, name), index=False, encoding="utf-8-sig")
        print(f"{name}: {len(b)} 行", file=sys.stderr)

    print(f"扫描完成 {len(df)} 只 -> {path}", file=sys.stderr)
    print("===TOP30 BY RS5===")
    cols = ["名称", "主题", "ret5", "RS5", "ret60", "RS60", "位置分位", "距250日高",
            "趋势结构", "量能比", "板块5日资金净额_亿", "板块当日广度_%"]
    print(df[[c for c in cols if c in df.columns]].head(30).to_string())


if __name__ == "__main__":
    # 两段式：fetch 抓数并吐出待判主题清单 → Claude 写 themes.json → finalize 出池
    stage = sys.argv[1] if len(sys.argv) > 1 else "fetch"
    today = sys.argv[2] if len(sys.argv) > 2 else date.today().isoformat()
    if stage == "fetch":
        _run_fetch(today)
    elif stage == "finalize":
        _run_finalize(today)
    else:
        raise SystemExit("用法: scan_cn.py [fetch|finalize] [YYYY-MM-DD]")

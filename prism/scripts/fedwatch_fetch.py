"""CME FedWatch 隐含政策路径取数通道（零 LLM）。读登记表里 fetch_method=='fedwatch' 且
availability=='scripted' 且有 fedwatch 配置块的输入，从 CME 30-Day Fed Funds Futures（ZQ 合约，
经 Yahoo Finance）反解逐会议隐含目标利率，按请求的 metric 落值 → record_observation。

与 fred_fetch / cftc_fetch / yfinance_fetch 平行（脚本「数值」通道）。增量价值：FRED FEDFUNDS 只给
**已实现**有效利率，本通道给的是市场**前瞻**政策预期——隐含降息路径/概率，FRED 不直接提供。

口径 = CME FedWatch 真方法（逐会议反解整条隐含路径）：
  ZQ 合约结算价 P → 当月平均联邦基金利率隐含值 r_avg = 100 − P。
  逐会议沿日历链式传导（pre 起点 = 当前目标中值，其后 = 上一会议反解出的 post）。每次会议的**会后利率**：
    · 若会议**次月无 FOMC 会议** → 直接读次月合约：post = r_avg(次月)（整月都是会后利率，干净、无噪声放大）。
      这是 CME 对「会议靠月末（会后天数极少）」的标准处理——否则 (D−d) 极小会把合约价噪声放大成乱值。
    · 否则（次月也有会议，即连月会议）→ 退回会内日加权反解：
        r_avg(会议月) = d/D·pre + (D−d)/D·post  →  post = (r_avg·D − pre·d)/(D−d)
      新利率自会议公告**次日**生效，故公告日 d 计入会前天数。连月会议时 (D−d) 仍够大（13–22 天），稳定。

4 个可落标量（fedwatch 块 metric 指定，仿 mofcom 的 metric 枚举）：
  next_cut_prob  下次会议降息概率%（P(≥25bp 降息)，按 25bp 线性插值；定价持稳/加息→0）
  next_rate      下次会议会后隐含目标利率%（路径近端点）
  eoy_rate       年底（12 月会议）会后隐含目标利率%（路径远端点）
  eoy_cuts       年内累计被定价的 25bp 降息次数 = (当前利率 − eoy_rate)/0.25（路径跨度）

注意：FOMC 会议日历 + 当前目标中值是**仅 8x/年**变动的硬编码常量（_FOMC_2026 / CURRENT_TARGET_MIDPOINT），
随美联储改目标/换年时同步维护。ZQ 合约 Yahoo symbol = ZQ{月码}{年后两位}.CBT（如 ZQM26.CBT=2026-06）。
"""
from __future__ import annotations

import calendar
import datetime as _dt
import math
import re
import sys

from prism.scripts import macro_registry as reg

# 当前 FOMC 目标区间中值（%）。改目标时同步更新（与 _FOMC_2026 同维护节奏）。
# 2026-06：目标区间 3.50–3.75% → 中值 3.625。
CURRENT_TARGET_MIDPOINT = 3.625

# 2026 FOMC 会议（公告/决议日 = 会期第 2 天）。来源：Fed 官方会议日历。
_FOMC_2026 = [
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
]
# CME ZQ 月码：F=1 G=2 H=3 J=4 K=5 M=6 N=7 Q=8 U=9 V=10 X=11 Z=12
_MONTH_CODE = "FGHJKMNQUVXZ"

VALID_METRIC = ("next_cut_prob", "next_rate", "eoy_rate", "eoy_cuts")
_TICKER_RE = re.compile(r"^[A-Za-z0-9.^=\-]{1,20}$")
_STEP = 0.25  # 一档 = 25bp


def _to_float(v) -> float | None:
    """单元转 float；NaN/空/非数 → None。"""
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


def _import_yfinance():
    import yfinance as yf  # 惰性导入：yfinance 启动慢
    return yf


def _contract_symbol(year: int, month: int) -> str:
    """ZQ 月合约 Yahoo symbol：ZQ{月码}{年后两位}.CBT。"""
    return f"ZQ{_MONTH_CODE[month - 1]}{year % 100:02d}.CBT"


def _next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def _meeting_months(meetings=_FOMC_2026) -> set[tuple[int, int]]:
    """有 FOMC 会议的 (year, month) 集合。"""
    out = set()
    for d_iso in meetings:
        d = _dt.date.fromisoformat(d_iso)
        out.add((d.year, d.month))
    return out


def _future_meetings(today: _dt.date, meetings=_FOMC_2026) -> list[_dt.date]:
    """公告日 >= today 的会议日，升序。"""
    return sorted(d for d_iso in meetings
                  if (d := _dt.date.fromisoformat(d_iso)) >= today)


def needed_months(today: _dt.date, meetings=_FOMC_2026) -> list[tuple[int, int]]:
    """反解整条未来路径需要拉的合约月集合：每次会议——次月无会议则取次月（干净读），
    否则取会议月本身（会内加权）。升序去重。"""
    mtg_months = _meeting_months(meetings)
    months: set[tuple[int, int]] = set()
    for d in _future_meetings(today, meetings):
        nm = _next_month(d.year, d.month)
        months.add(nm if nm not in mtg_months else (d.year, d.month))
    return sorted(months)


def compute_path(current_rate: float, month_rates: dict, today: _dt.date,
                 meetings=_FOMC_2026) -> list[dict]:
    """链式反解逐会议会后隐含利率。纯函数（无 IO），可单测。

    month_rates: {(year, month) → 该月 ZQ 隐含平均利率%（=100−结算价）}。
    返回升序列表，每项 {date, pre, post, method('clean'|'weight')}；
    缺所需合约的会议起整条中断（诚实截断）。
    """
    mtg_months = _meeting_months(meetings)
    path = []
    pre = current_rate
    for d in _future_meetings(today, meetings):
        nm = _next_month(d.year, d.month)
        if nm not in mtg_months:
            # 次月无会议 → 整月即会后利率，直接读（无噪声放大）
            post = month_rates.get(nm)
            method = "clean"
        else:
            # 连月会议 → 会内日加权反解（会后天数够大，稳定）
            avg = month_rates.get((d.year, d.month))
            if avg is None:
                break
            D = calendar.monthrange(d.year, d.month)[1]
            days_pre = d.day                      # 公告日计入会前（新利率次日生效）
            days_post = D - days_pre
            post = None if days_post <= 0 else (avg * D - pre * days_pre) / days_post
            method = "weight"
        if post is None:
            break                                 # 所需合约缺失 → 链断
        path.append({"date": d.isoformat(), "pre": pre, "post": post, "method": method})
        pre = post
    return path


def extract_metric(metric: str, path: list[dict], current_rate: float) -> float | None:
    """从隐含路径取一个标量。路径空/不足 → None（诚实）。"""
    if metric not in VALID_METRIC:
        raise ValueError(f"fedwatch metric 非法: {metric!r}（仅 {list(VALID_METRIC)}）")
    if not path:
        return None
    if metric == "next_rate":
        return round(path[0]["post"], 4)
    if metric == "next_cut_prob":
        delta = path[0]["pre"] - path[0]["post"]      # >0 = 降息计价
        prob = min(max(delta / _STEP, 0.0), 1.0)      # P(≥25bp 降息)，线性插值并截断
        return round(prob * 100, 2)
    if metric == "eoy_rate":
        return round(path[-1]["post"], 4)
    if metric == "eoy_cuts":
        return round((current_rate - path[-1]["post"]) / _STEP, 3)
    return None


def fetch_contract_rates(today: _dt.date, *, yf_module=None,
                         meetings=_FOMC_2026) -> tuple[dict, str | None]:
    """拉反解所需各月 ZQ 合约 → {(year,month) → 隐含平均利率%}, as_of（最新合约收盘日）。
    单个合约取不到则跳过（该月从 dict 缺席，compute_path 据此截断）。"""
    yf = yf_module or _import_yfinance()
    rates: dict[tuple[int, int], float] = {}
    as_of: str | None = None
    for (y, m) in needed_months(today, meetings):
        sym = _contract_symbol(y, m)
        if not _TICKER_RE.match(sym):
            continue
        try:
            df = yf.Ticker(sym).history(period="5d")
        except Exception:
            continue
        if df is None or len(df) == 0 or "Close" not in df.columns:
            continue
        df = df.sort_index()
        price = _to_float(df["Close"].iloc[-1])
        if price is None:
            continue
        rates[(y, m)] = 100.0 - price
        ts = df.index[-1]
        day = ts.date().isoformat() if hasattr(ts, "date") else str(ts)[:10]
        if as_of is None or day > as_of:
            as_of = day
    return rates, as_of


def fetch_by_fedwatch(cfg: dict, *, yf_module=None,
                      today: _dt.date | None = None) -> tuple[float | None, str | None]:
    """按单个 fedwatch 配置抓一个标量。cfg: {metric, current_rate?}。
    metric 非法 → ValueError；取不到/路径不足 → 诚实 (None, as_of)。
    （便捷/冒烟/单抓用；批量 run 走 run_fedwatch_fetch 只算一次路径。）"""
    metric = (cfg.get("metric") or "").strip()
    if metric not in VALID_METRIC:
        raise ValueError(f"fedwatch metric 非法: {metric!r}（仅 {list(VALID_METRIC)}）")
    cur = cfg.get("current_rate", CURRENT_TARGET_MIDPOINT)
    today = today or _dt.date.today()
    rates, as_of = fetch_contract_rates(today, yf_module=yf_module)
    path = compute_path(cur, rates, today)
    return extract_metric(metric, path, cur), as_of


def run_fedwatch_fetch(slug: str, variant: str, *, only: set[str] | None = None,
                       yf_module=None, today: _dt.date | None = None) -> dict:
    """抓所有 fetch_method=='fedwatch' 且 availability=='scripted' 且有 fedwatch 配置的输入。
    **整条隐含路径只算一次**（拉一遍合约），再按各 input 的 metric 分发，避免重复请求。
    llm 项诚实跳过计数。only 给定时只抓名字在其中的项（web 单条手动抓）。
    失败（metric 非法/路径不足取不到值）记 record_fetch_error 并计数，不连累其余。返回 summary。"""
    data = reg.read_registry(slug, variant)
    entries = []
    for e in data["inputs"]:
        if e.get("fetch_method") != "fedwatch":
            continue
        if only is not None and e["name"] not in only:
            continue
        entries.append(e)

    fetched = skipped_todo = skipped_llm = failed = 0
    actionable = [e for e in entries if e.get("availability") == "scripted" and e.get("fedwatch")]
    for e in entries:
        if e.get("availability") == "llm":
            skipped_llm += 1
        elif e.get("availability") != "scripted" or not e.get("fedwatch"):
            skipped_todo += 1
    if not actionable:
        return {"fetched": 0, "skipped_todo": skipped_todo,
                "skipped_llm": skipped_llm, "failed": 0}

    today = today or _dt.date.today()
    # current_rate 取各 actionable 项 cfg（一般同值）；用第一个的、缺省用模块常量
    cur = actionable[0]["fedwatch"].get("current_rate", CURRENT_TARGET_MIDPOINT)
    try:
        rates, as_of = fetch_contract_rates(today, yf_module=yf_module)
        path = compute_path(cur, rates, today)
    except Exception as exc:                       # 网络/结构整体失败：每个 actionable 记错
        for e in actionable:
            reg.record_fetch_error(slug, variant, e["name"], msg=f"fedwatch 路径计算失败: {exc}")
        return {"fetched": 0, "skipped_todo": skipped_todo,
                "skipped_llm": skipped_llm, "failed": len(actionable)}

    for e in actionable:
        cfg = e["fedwatch"]
        try:
            ecur = cfg.get("current_rate", cur)
            val = extract_metric(cfg.get("metric", ""), path, ecur)
        except Exception as exc:                   # metric 非法等
            reg.record_fetch_error(slug, variant, e["name"], msg=str(exc))
            failed += 1
            continue
        if val is None:
            reg.record_fetch_error(slug, variant, e["name"],
                                   msg=f"fedwatch 路径不足/合约缺失，metric={cfg.get('metric')!r} 取不到值")
            failed += 1
            continue
        reg.record_observation(slug, variant, e["name"], value=val, as_of=as_of)
        fetched += 1
    return {"fetched": fetched, "skipped_todo": skipped_todo,
            "skipped_llm": skipped_llm, "failed": failed}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    # 自带活体冒烟：无参时直接拉真合约、打印整条隐含路径 + 4 标量
    if not argv:
        today = _dt.date.today()
        rates, as_of = fetch_contract_rates(today)
        path = compute_path(CURRENT_TARGET_MIDPOINT, rates, today)
        print(f"当前目标中值 {CURRENT_TARGET_MIDPOINT}% · 合约 as_of {as_of}")
        for p in path:
            print(f"  {p['date']}: pre={p['pre']:.4f}% → post={p['post']:.4f}% [{p['method']}]")
        for m in VALID_METRIC:
            print(f"  {m:14s} = {extract_metric(m, path, CURRENT_TARGET_MIDPOINT)}")
        return
    slug = argv[0]
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    print(f"fedwatch 抓取: {run_fedwatch_fetch(slug, variant)}")


if __name__ == "__main__":
    main()

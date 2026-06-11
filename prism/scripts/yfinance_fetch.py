"""yfinance 取数通道（市场行情序列）。零 LLM：读登记表里 fetch_method=='yfinance' 且
availability=='scripted' 且有 yfinance 配置块的输入，调 yf.Ticker(ticker).history() → 取最新收盘 →
record_observation。

与 fred_fetch / recipe_fetch / akshare_fetch 平行（都是脚本「数值」通道）。yfinance 覆盖
FRED/akshare 都没有的专有市场指数——如 ICE MOVE 债市波动率(^MOVE)、ICE 美元指数(DX-Y.NYB)、
CBOE 10Y 收益率(^TNX)，这些无免费结构化 csv/json 但 Yahoo 有日频收盘。仿 akshare：核心
fetch_by_yfinance 可注入 yf_module（测试 mock，等价 fred 的 client）。

为何用 ticker 格式守卫而非函数白名单：akshare 的 func 是 getattr 按字符串执行（须白名单），
而本通道 ticker 只是喂给 Yahoo 的数据查询参数、不执行代码，故只做格式校验（限正常 symbol 字符，
挡注入/拼错）。history 默认按日期升序，取末行=最新；仍解析 index 取 max 防意外乱序。
"""
from __future__ import annotations

import math
import re
import sys

from prism.scripts import macro_registry as reg

# Yahoo symbol 允许字符：字母数字 + ^ . - =（如 ^MOVE / DX-Y.NYB / ^TNX / GC=F / EURUSD=X / BTC-USD）
_TICKER_RE = re.compile(r"^[A-Za-z0-9.^=\-]{1,20}$")


def _to_float(v) -> float | None:
    """单元转 float；NaN/空/非数 → None。值含千分位逗号/百分号则去掉。"""
    if v is None:
        return None
    if isinstance(v, str):
        v = v.replace(",", "").replace("%", "").strip()
        if not v:
            return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _import_yfinance():
    import yfinance as yf  # 惰性导入：yfinance 启动慢，仅取数时才加载
    return yf


def fetch_by_yfinance(cfg: dict, *, yf_module=None) -> tuple[float | None, str | None]:
    """按 yfinance 配置抓一个数值。cfg: {ticker, field?, period?}。
    ticker 须过格式守卫（否则 ValueError 不静默）。field 缺省 'Close'；period 缺省 '5d'。
    取 history() 中日期最大那行的 field 列；as_of=该日 ISO 串。任何对不上 → 诚实 (None, as_of)，不抛。
    yf_module 可注入（测试 mock）。"""
    ticker = (cfg.get("ticker") or "").strip()
    if not ticker:
        raise ValueError("yfinance 配置缺 ticker")
    if not _TICKER_RE.match(ticker):
        raise ValueError(f"yfinance ticker 格式非法: {ticker!r}（仅限 Yahoo symbol 字符 A-Z0-9.^=-）")
    field = cfg.get("field", "Close")
    period = cfg.get("period", "5d")
    yf = yf_module or _import_yfinance()
    df = yf.Ticker(ticker).history(period=period)
    if df is None or len(df) == 0:
        return None, None
    if field not in df.columns:
        raise ValueError(f"yfinance 无此列 field={field!r}；实际列={list(df.columns)[:8]}")
    df = df.sort_index()                       # history 通常已升序；显式排序防意外乱序
    ts = df.index[-1]                           # 最新日期那行
    val = _to_float(df[field].iloc[-1])
    as_of = ts.date().isoformat() if hasattr(ts, "date") else str(ts)[:10]
    return val, as_of


def run_yfinance_fetch(slug: str, variant: str, *, only: set[str] | None = None,
                       yf_module=None) -> dict:
    """抓所有 fetch_method=='yfinance' 且 availability=='scripted' 且有 yfinance 配置的输入。
    llm 项诚实跳过计数（它们走 headless LLM）。only 给定时只抓名字在其中的项（web 单条手动抓）。
    失败（抛异常/取不到值）记 record_fetch_error 并计数，不连累其余。返回 summary。"""
    data = reg.read_registry(slug, variant)
    fetched = skipped_todo = skipped_llm = failed = 0
    for e in data["inputs"]:
        if e.get("fetch_method") != "yfinance":
            continue
        if only is not None and e["name"] not in only:
            continue
        avail = e.get("availability")
        if avail == "llm":
            skipped_llm += 1
            continue
        if avail != "scripted" or not e.get("yfinance"):
            skipped_todo += 1
            continue
        try:
            val, as_of = fetch_by_yfinance(e["yfinance"], yf_module=yf_module)
        except Exception as exc:                       # 格式守卫/列缺失/网络等：记错、跳过，不连累其余
            reg.record_fetch_error(slug, variant, e["name"], msg=str(exc))
            failed += 1
            continue
        if val is None:
            reg.record_fetch_error(slug, variant, e["name"],
                                   msg=f"yfinance 未取到值（symbol 失效或源变更）: {e['yfinance'].get('ticker')}")
            failed += 1
            continue
        reg.record_observation(slug, variant, e["name"], value=val, as_of=as_of)
        fetched += 1
    return {"fetched": fetched, "skipped_todo": skipped_todo,
            "skipped_llm": skipped_llm, "failed": failed}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    print(f"yfinance 抓取: {run_yfinance_fetch(slug, variant)}")


if __name__ == "__main__":
    main()

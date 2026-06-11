"""akshare 取数通道（中国宏观）。零 LLM：读登记表里 fetch_method=='akshare' 且
availability=='scripted' 且有 akshare 配置块的输入，调对应 akshare 函数 → 解析 → record_observation。

与 fred_fetch / recipe_fetch 平行（都是脚本「数值」通道）。akshare 返回 DataFrame 而非
单 URL，故不走 recipe(url+parse)，单列一个薄通道。仿 fred_fetch：核心 fetch_by_akshare
可注入 ak_module（测试 mock，等价 fred 的 client）。

为何要白名单 + 按日期取 max（这次实测踩到的坑）：
  - 安全：func 来自登记表，getattr(ak, func) 等于按字符串执行；限定 ALLOWED_FUNCS 仅放行
    实测可用的统计局直连函数，杜绝登记表驱动任意调用。
  - 正确：akshare 各函数 DataFrame 排序方向不一（社零/CPI/PMI 降序、LPR/房价/Shibor 升序），
    盲取首/尾会取错；故解析日期列、取 max 那条。中文日期（'2026年05月份'/'2026年第1季度'）
    归一成 as_of。务必用统计局直连函数名（macro_china_cpi），勿用 _yearly/_monthly 死镜像
    （那批与 US ISM 同后端、冻结于 2025-09）。
"""
from __future__ import annotations

import datetime
import math
import re
import sys

from prism.scripts import macro_registry as reg

# 仅放行实测「尾值新鲜」的函数（2026-06 验收）。新增源前先实拉验新鲜度，再登记于此。
ALLOWED_FUNCS = {
    "macro_china_pmi",                       # 官方制造/非制造 PMI（统计局直连，月）
    "macro_china_cpi",                       # CPI（统计局直连，月）
    "macro_china_ppi",                       # PPI（统计局直连，月）
    "macro_china_gdp",                       # GDP（统计局直连，季）
    "macro_china_consumer_goods_retail",     # 社会消费品零售（月）
    "macro_china_money_supply",              # M0/M1/M2（月）
    "macro_china_new_financial_credit",      # 新增信贷（月）
    "macro_china_reserve_requirement_ratio", # 存准率 RRR（事件）
    "macro_china_lpr",                        # LPR 1Y/5Y（事件）
    "macro_china_new_house_price",           # 70 城房价（月，多城/期）
    "rate_interbank",                         # Shibor / HIBOR（日，带 market/symbol/indicator 参数）
    "stock_hsgt_fund_flow_summary_em",        # 北向/南向资金（日，多行需 filter+sum）
}


def _norm_date(raw) -> tuple[tuple[int, int, int], str | None]:
    """把 akshare 各式日期单元归一：返回 (排序键 (y,m,d), as_of 串)。识别不了 → ((0,0,0), 原串)。
    支持 datetime.date / 'YYYY年MM月份' / 'YYYY年第Q季度' / 'YYYY年MM月DD日' / 'YYYY-MM[-DD]'。"""
    if raw is None:
        return (0, 0, 0), None
    if isinstance(raw, (datetime.date, datetime.datetime)):
        return (raw.year, raw.month, getattr(raw, "day", 1)), raw.strftime("%Y-%m-%d")
    s = str(raw).strip()
    m = re.match(r"(\d{4})年第([1-4])季度", s)
    if m:
        y, q = int(m.group(1)), int(m.group(2))
        return (y, q * 3, 0), f"{y}-Q{q}"
    m = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", s)
    if m:
        y, mo, d = (int(x) for x in m.groups())
        return (y, mo, d), f"{y:04d}-{mo:02d}-{d:02d}"
    m = re.match(r"(\d{4})年(\d{1,2})月", s)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        return (y, mo, 0), f"{y:04d}-{mo:02d}"
    m = re.match(r"(\d{4})-(\d{1,2})(?:-(\d{1,2}))?", s)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        d = int(m.group(3)) if m.group(3) else 0
        return (y, mo, d), f"{y:04d}-{mo:02d}" + (f"-{d:02d}" if d else "")
    return (0, 0, 0), s


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


def _import_akshare():
    import akshare as ak  # 惰性导入：akshare 启动慢，仅取数时才加载
    return ak


def fetch_by_akshare(cfg: dict, *, ak_module=None) -> tuple[float | None, str | None]:
    """按 akshare 配置抓一个数值。cfg: {func, args?, date_column, value_column, row_filter?, agg?}。
    func 须在 ALLOWED_FUNCS（白名单，否则 ValueError 不静默）。args 作 kwargs 传函数（如 rate_interbank）。
    row_filter（可选 dict）逐列 == 过滤；解析 date_column 取 max 那（些）行；value_column 取值；
    同期多行按 agg 聚合：first（默认）/ sum / mean。任何对不上 → 诚实 (None, as_of)，不抛。
    ak_module 可注入（测试 mock）。"""
    func_name = cfg.get("func")
    if not func_name:
        raise ValueError("akshare 配置缺 func")
    if func_name not in ALLOWED_FUNCS:
        raise ValueError(f"akshare func 不在白名单: {func_name!r}（仅 {sorted(ALLOWED_FUNCS)}）")
    ak = ak_module or _import_akshare()
    fn = getattr(ak, func_name, None)
    if fn is None or not callable(fn):
        raise ValueError(f"akshare 无此函数: {func_name!r}")
    df = fn(**(cfg.get("args") or {}))
    if df is None or len(df) == 0:
        return None, None
    dcol = cfg.get("date_column")
    vcol = cfg.get("value_column")
    if not dcol or not vcol:
        raise ValueError("akshare 配置缺 date_column / value_column")
    if dcol not in df.columns or vcol not in df.columns:
        raise ValueError(f"列不存在 date={dcol!r}/value={vcol!r}；实际列={list(df.columns)[:8]}")
    # row_filter：逐列精确过滤（北向/南向按资金方向）
    for col, val in (cfg.get("row_filter") or {}).items():
        if col not in df.columns:
            raise ValueError(f"row_filter 列不存在: {col!r}")
        df = df[df[col] == val]
    if len(df) == 0:
        return None, None
    # 解析日期取 max（绕开各函数排序方向不一）
    keyed = [(_norm_date(d), i) for i, d in enumerate(df[dcol].tolist())]
    max_key = max(k for (k, _), i in keyed)
    as_of = next(n for (k, n), i in keyed if k == max_key)
    idxs = [i for (k, _), i in keyed if k == max_key]
    nums = [f for f in (_to_float(df.iloc[i][vcol]) for i in idxs) if f is not None]
    if not nums:
        return None, as_of
    agg = cfg.get("agg", "first")
    if agg == "sum":
        value = sum(nums)
    elif agg == "mean":
        value = sum(nums) / len(nums)
    else:  # first
        value = nums[0]
    return value, as_of


def run_akshare_fetch(slug: str, variant: str, *, only: set[str] | None = None,
                      ak_module=None) -> dict:
    """抓所有 fetch_method=='akshare' 且 availability=='scripted' 且有 akshare 配置的输入。
    llm 项诚实跳过计数（它们走 headless LLM）。only 给定时只抓名字在其中的项（web 单条手动抓）。
    失败（抛异常/取不到值）记 record_fetch_error 并计数，不连累其余。返回 summary。"""
    data = reg.read_registry(slug, variant)
    fetched = skipped_todo = skipped_llm = failed = 0
    for e in data["inputs"]:
        if e.get("fetch_method") != "akshare":
            continue
        if only is not None and e["name"] not in only:
            continue
        avail = e.get("availability")
        if avail == "llm":
            skipped_llm += 1
            continue
        if avail != "scripted" or not e.get("akshare"):
            skipped_todo += 1
            continue
        try:
            val, as_of = fetch_by_akshare(e["akshare"], ak_module=ak_module)
        except Exception as exc:                       # 白名单/列缺失/网络等：记错、跳过，不连累其余
            reg.record_fetch_error(slug, variant, e["name"], msg=str(exc))
            failed += 1
            continue
        if val is None:
            reg.record_fetch_error(slug, variant, e["name"],
                                   msg=f"akshare 未取到值（源结构可能变更）: {e['akshare'].get('func')}")
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
    print(f"akshare 抓取: {run_akshare_fetch(slug, variant)}")


if __name__ == "__main__":
    main()

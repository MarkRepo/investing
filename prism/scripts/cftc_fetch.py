"""CFTC 持仓拥挤取数通道（杠杆基金净头寸 + 回看窗 z-score）。零 LLM：读登记表里
fetch_method=='cftc' 且 availability=='scripted' 且有 cftc 配置块的输入，
从 CFTC 官方 Socrata 开放数据 API 拉一窗周度持仓 → 算净头寸 + z → record_observation。

与 fred_fetch / recipe_fetch / barchart_fetch / ecb_fetch / safe_fetch 平行（脚本「数值」通道）。
典型用途：**杠杆基金(leveraged funds)在 UST 10Y NOTE 期货上的净头寸**——carry/套息拥挤度的
直接探头，且杠杆基金 Treasury 净空头是 basis-trade(现券-期货基差交易)规模的公开代理。

取数机制（单请求 SoQL）：
  GET {base}/{dataset}.json
      ?$where=contract_market_name='{contract}'
      &$order=report_date_as_yyyy_mm_dd DESC
      &$limit={lookback}
      &$select=report_date...,{cohort}_positions_long,{cohort}_positions_short,open_interest_all
  逐行 net = long − short（按报告日降序，第 0 行=最新）。

口径：
  value = 最新一期净头寸（合约数，带符号；负=净空）。
  z     = 整个 lookback 窗净头寸序列的 z-score（教科书 COT 拥挤极端度）；样本不足/方差 0 → None。
  as_of = 最新一期报告日 YYYY-MM-DD。
注意：CFTC TFF 周报（周二为准、约 3 天发布延迟）；官方免鉴权、无反爬，匿名有速率限制——周频单请求不触发。
"""
from __future__ import annotations

import math
import statistics
import sys

from prism.scripts import macro_registry as reg

_DEFAULT_BASE = "https://publicreporting.cftc.gov/resource"
_VALID_COHORTS = ("lev_money", "asset_mgr", "dealer", "other_rept")
_DATE_COL = "report_date_as_yyyy_mm_dd"


def _to_float(v) -> float | None:
    """单元转 float；空/非数/NaN → None。值含千分位逗号则去掉。"""
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


def fetch_by_cftc(cfg: dict, *, client=None) -> tuple[float | None, float | None, str | None]:
    """按 cftc 配置抓一期净头寸 + 回看窗 z-score。
    cfg: {dataset, contract, cohort?='lev_money', lookback?=156, min_obs?=30, base_url?}。
    返回 (value=最新净头寸合约数, z=净头寸序列 z-score 或 None, as_of=最新报告日 或 None)。
    缺 dataset/contract 或 cohort 非法 → 抛 ValueError；空数据/字段缺失 → 诚实 (None, None, None)。
    client 可注入（测试 mock：支持 .get(url, params=...) → .raise_for_status()/.json()）。"""
    dataset = (cfg.get("dataset") or "").strip()
    contract = (cfg.get("contract") or "").strip()
    if not dataset:
        raise ValueError("cftc 配置缺 dataset")
    if not contract:
        raise ValueError("cftc 配置缺 contract")
    cohort = cfg.get("cohort", "lev_money")
    if cohort not in _VALID_COHORTS:
        raise ValueError(f"cftc cohort 非法: {cohort!r}（仅 {list(_VALID_COHORTS)}）")
    lookback = int(cfg.get("lookback", 156))
    min_obs = int(cfg.get("min_obs", 30))
    base_url = cfg.get("base_url", _DEFAULT_BASE)
    long_col = f"{cohort}_positions_long"
    short_col = f"{cohort}_positions_short"
    url = f"{base_url}/{dataset}.json"
    params = {
        "$where": f"contract_market_name='{contract}'",
        "$order": f"{_DATE_COL} DESC",
        "$limit": str(lookback),
        "$select": f"{_DATE_COL},{long_col},{short_col},open_interest_all",
    }
    owns = client is None
    if owns:
        client = _import_httpx().Client(timeout=30)
    try:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        rows = resp.json()
    finally:
        if owns:
            client.close()
    if not rows:
        return None, None, None
    # (日期, 净头寸) 序列，按返回的报告日降序；跳过缺腿/非数行
    # （value 取首个可用行、as_of 对齐之，避免最新行缺腿时日期错配）
    series: list[tuple[str | None, float]] = []
    for r in rows:
        lo = _to_float(r.get(long_col))
        sh = _to_float(r.get(short_col))
        if lo is None or sh is None:
            continue
        d = r.get(_DATE_COL)
        series.append((str(d)[:10] if d else None, lo - sh))
    if not series:
        return None, None, None
    as_of, value = series[0]
    nets = [n for _, n in series]
    z = None
    if len(nets) >= min_obs:
        sd = statistics.pstdev(nets)
        if sd > 0:
            z = (value - statistics.fmean(nets)) / sd
    return value, z, as_of
